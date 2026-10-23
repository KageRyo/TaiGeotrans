"""Provider coordinates cannot by themselves establish address-level precision."""

import httpx
import pytest

from taigeotrans import TaiGeotrans
from taigeotrans.address import AddressContext
from taigeotrans.providers.tgos import TGOSClient

ADDRESS = "嘉義縣民雄鄉大學路一段138號"


def candidate(address=ADDRESS, lon=120.472, lat=23.563):
    return {"FULL_ADDR": address, "X": lon, "Y": lat}


def converter(rows, match_type="完全比對", *, expected=ADDRESS.replace("一段", "1段")):
    client = TGOSClient(app_id="test-app", api_key="test-key", max_retries=1)

    def respond(request):
        assert request.url.params["oAddress"] == expected
        assert request.url.params["oReturnMaxCount"] == "9"
        assert request.url.params["oIsOnlyFullMatch"] == "true"
        assert request.url.params["oIsLockCounty"] == "true"
        assert request.url.params["oIsLockTown"] == "true"
        return httpx.Response(
            200, json={"Info": [{"OutMatchType": match_type}], "AddressList": rows}
        )

    client._client = httpx.Client(transport=httpx.MockTransport(respond))
    return TaiGeotrans(tgos_client=client)


def test_high_level_geocoding_verifies_one_matching_candidate_and_keeps_raw_input():
    original = "  嘉義縣民雄鄉大學路一段１３８號  "
    result = converter([candidate()]).geocode(original)
    assert result.status == "success" and result.match_status == "verified_exact"
    assert result.input_address == original
    assert result.completed_query == "嘉義縣民雄鄉大學路1段138號"
    assert result.matched_address == ADDRESS
    assert result.candidate_count == 1 and len(result.response_sha256) == 64
    assert result.spatial_precision == "address"
    assert result.twd97_x is not None and result.twd97_y is not None


def test_context_completion_does_not_change_original_input():
    result = converter([candidate()]).geocode(
        "民雄鄉大學路1段138號", context=AddressContext(county="嘉義縣")
    )
    assert result.match_status == "verified_exact"
    assert result.completed_fields == ["county"]
    assert result.input_address == "民雄鄉大學路1段138號"


@pytest.mark.parametrize(
    "address,context,status",
    [
        ("大學路1段138號", None, "insufficient"),
        ("嘉義縣民雄鄉大學路", None, "insufficient"),
        (ADDRESS, AddressContext(county="嘉義市"), "unresolved"),
    ],
)
def test_insufficient_or_conflicting_input_never_queries_provider(address, context, status):
    result = TaiGeotrans().geocode(address, context=context)
    assert result.match_status == status
    assert result.wgs84_lon is None and result.twd97_x is None


@pytest.mark.parametrize(
    "rows,match_type,status",
    [
        ([candidate()], "近似比對", "fuzzy"),
        ([candidate(), candidate(lon=120.49)], "完全比對", "ambiguous"),
        ([candidate(ADDRESS.replace("138", "136"))], "完全比對", "unresolved"),
        ([candidate(ADDRESS.replace("民雄鄉", "新港鄉"))], "完全比對", "unresolved"),
        ([], "", "unresolved"),
        ([candidate()] * 9, "完全比對", "ambiguous"),
    ],
)
def test_unverified_candidates_do_not_export_point_coordinates(rows, match_type, status):
    result = converter(rows, match_type).geocode(ADDRESS)
    assert result.match_status == status
    assert result.status != "success"
    assert result.wgs84_lon is None and result.twd97_x is None
    assert result.candidate_count == len(rows)
    assert len(result.response_sha256) == 64


def test_selection_validates_all_candidates_instead_of_choosing_index_zero():
    result = converter([candidate(ADDRESS.replace("138", "136")), candidate()]).geocode(ADDRESS)
    assert result.match_status == "verified_exact" and result.candidate_count == 2
    assert result.matched_address == ADDRESS


def test_conflicting_provider_structured_components_are_not_ignored():
    row = {**candidate(), "COUNTY": "嘉義市"}
    result = converter([row]).geocode(ADDRESS)
    assert result.match_status == "unresolved" and result.twd97_x is None


def test_provider_errors_remain_unresolved_without_live_credentials_or_network():
    client = TGOSClient(app_id="test-app", api_key="test-key", max_retries=1)
    client._client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(503))
    )
    result = TaiGeotrans(tgos_client=client).geocode(ADDRESS)
    assert result.match_status == "unresolved" and result.verification_reason == "provider_error"


def test_batch_keeps_order_and_context_conflicts_separate():
    result = converter([candidate()]).batch_geocode(
        ["民雄鄉大學路1段138號", "嘉義市東區大學路1段138號"],
        show_progress=False,
        context=AddressContext(county="嘉義縣"),
    )
    assert [r.match_status for r in result] == ["verified_exact", "unresolved"]


def test_missing_provider_match_metadata_is_unresolved():
    result = converter([candidate()], None).geocode(ADDRESS)
    assert result.match_status == "unresolved" and result.twd97_x is None


def test_advertised_unreturned_candidates_prevent_uniqueness():
    client = TGOSClient(app_id="test-app", api_key="test-key")
    client._client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "Info": [{"OutMatchType": "完全比對", "OutTotal": "20"}],
                    "AddressList": [candidate()],
                },
            )
        )
    )
    result = TaiGeotrans(tgos_client=client).geocode(ADDRESS)
    assert (
        result.match_status == "ambiguous"
        and result.verification_reason == "candidate_limit_reached"
    )
    assert result.candidate_count == 1 and result.twd97_x is None
    assert result.provider_candidate_count == 20


def test_exact_match_with_coarse_precision_or_outside_taiwan_has_no_point():
    for row in [{**candidate(), "precision": "village"}, candidate(lon=-74, lat=40)]:
        result = converter([row]).geocode(ADDRESS)
        assert result.match_status != "verified_exact"
        assert result.twd97_x is None and result.wgs84_lon is None


def test_batch_request_validation_preserves_input_instead_of_trimming_or_dropping():
    from pydantic import ValidationError

    from taigeotrans.models import BatchGeocodeRequest

    raw = "  嘉義縣民雄鄉大學路一段１３８號  "
    assert BatchGeocodeRequest(addresses=[raw]).addresses == [raw]
    with pytest.raises(ValidationError):
        BatchGeocodeRequest(addresses=[raw, "  "])


def test_legacy_tuple_does_not_select_first_of_multiple_candidates():
    client = TGOSClient(app_id="test-app", api_key="test-key")
    client._client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"Info": [], "AddressList": [candidate(), candidate()]}
            )
        )
    )
    assert client.geocode_address(ADDRESS) == (None, None, None, 0.0)
