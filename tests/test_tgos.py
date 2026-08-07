"""Tests for the authenticated TGOS HTTP contract."""

import httpx
import pytest

from taigeotrans.providers.tgos import TGOSClient, TGOSConfigurationError, TGOSResponseError


def _client_with_response(
    payload: object,
    address: str = "臺北市中山區松江路469巷4號",
) -> TGOSClient:
    client = TGOSClient(app_id="test-app", api_key="test-key", max_retries=1)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["oAPPId"] == "test-app"
        assert request.url.params["oAPIKey"] == "test-key"
        assert request.url.params["oAddress"] == address
        assert request.url.params["oSRS"] == "EPSG:4326"
        return httpx.Response(200, json=payload, request=request)

    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_geocode_uses_documented_parameters() -> None:
    client = _client_with_response(
        {
            "Info": [{"OutMatchType": "完全比對"}],
            "AddressList": [
                {
                    "FULL_ADDR": "臺北市中山區松江路469巷4號",
                    "X": 121.532,
                    "Y": 25.064,
                }
            ],
        }
    )

    try:
        lon, lat, matched_address, confidence = client.geocode_address("臺北市中山區松江路469巷4號")
    finally:
        client.close()

    assert (lon, lat) == (121.532, 25.064)
    assert matched_address == "臺北市中山區松江路469巷4號"
    assert confidence == 1.0


def test_geocode_returns_empty_result_when_address_is_not_found() -> None:
    client = _client_with_response({"Info": [], "AddressList": []}, address="不存在的地址")
    try:
        result = client.geocode_address("不存在的地址")
    finally:
        client.close()

    assert result == (None, None, None, 0.0)


def test_geocode_rejects_missing_credentials() -> None:
    with pytest.raises(TGOSConfigurationError):
        TGOSClient().geocode_address("臺北市信義區市府路1號")


def test_geocode_rejects_unrecognized_response() -> None:
    client = _client_with_response(
        {"Info": []},
        address="臺北市信義區市府路1號",
    )
    try:
        with pytest.raises(TGOSResponseError):
            client.geocode_address("臺北市信義區市府路1號")
    finally:
        client.close()
