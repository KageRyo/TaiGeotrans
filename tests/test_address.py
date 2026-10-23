"""Address equivalence must preserve locality and house-number distinctions."""

import pytest

from taigeotrans.address import AddressContext, addresses_match, complete_address, parse_address


def test_normalization_preserves_original_and_canonicalizes_numeric_components():
    original = " 嘉義縣 民雄鄉三興村５鄰 大學路一段１０巷２弄１３８號之１ "
    address = parse_address(original)
    assert address.original == original
    assert address.road == "大學路" and address.section == "1"
    assert address.lane == "10" and address.alley == "2"
    assert address.house_number == "138-1"
    assert address.is_complete


def test_only_trusted_missing_components_are_completed():
    result = complete_address("民雄鄉大學路1段138號", AddressContext(county="嘉義縣"))
    assert result.query == "嘉義縣民雄鄉大學路1段138號"
    assert result.completed_fields == ("county",)
    assert result.original == "民雄鄉大學路1段138號"
    with pytest.raises(ValueError, match="county"):
        complete_address("嘉義市東區大學路1段138號", AddressContext(county="嘉義縣"))
    with pytest.raises(ValueError, match="township"):
        complete_address("嘉義縣民雄鄉大學路1段138號", AddressContext(township="新港鄉"))


@pytest.mark.parametrize(
    "address",
    [
        "大學路一段138號",
        "嘉義縣民雄鄉大學路",
        "台1線258.2K至258.5K民雄路段",
        "嘉義縣民雄鄉八掌溪湖內堤防",
    ],
)
def test_partial_and_coarse_inputs_are_not_complete_addresses(address):
    assert not parse_address(address).is_complete


@pytest.mark.parametrize(
    "query,matched",
    [
        ("臺北市中山區松江路1段138之1號", "台北市中山區行政里1鄰松江路一段138號之1"),
        ("嘉義縣民雄鄉大學路1段138號", "嘉義縣民雄鄉三興村5鄰大學路一段138號"),
    ],
)
def test_equivalent_sections_and_optional_administrative_annotations(query, matched):
    from taigeotrans import address_mismatch

    # Pure strings cannot independently distinguish 美村南路 from 美村 + 南路.
    assert not addresses_match(parse_address(query), parse_address(matched))
    assert (
        address_mismatch(parse_address(query), parse_address(matched), allow_extra_village=True)
        is None
    )


@pytest.mark.parametrize(
    "matched",
    [
        "嘉義縣民雄鄉大學路1段136號",
        "嘉義縣新港鄉大學路1段138號",
        "嘉義市東區大學路1段138號",
        "嘉義縣民雄鄉大學路2段138號",
        "嘉義縣民雄鄉大學路1段5巷138號",
        "嘉義縣民雄鄉大學路1段138之1號",
    ],
)
def test_near_miss_candidates_never_become_equivalent(matched):
    assert not addresses_match(parse_address("嘉義縣民雄鄉大學路1段138號"), parse_address(matched))


def test_supplied_village_neighborhood_and_alley_conflicts_are_rejected():
    query = parse_address("嘉義縣民雄鄉三興村5鄰大學路1段10巷2弄138號")
    for old, new in [("三興村", "東興村"), ("5鄰", "6鄰"), ("2弄", "3弄")]:
        assert not addresses_match(query, parse_address(query.query.replace(old, new)))


def test_township_names_with_internal_city_character_and_road_names_with_numerals():
    parsed = parse_address("臺南市新市區三民路一段一百三十八號")
    assert parsed.township == "新市區" and parsed.road == "三民路"
    assert parsed.house_number == "138" and parsed.section == "1"


@pytest.mark.parametrize("number", ["一百百", "一百三", "一二十", "12三", "138之1號之2"])
def test_malformed_or_ambiguous_numerals_are_preserved_without_guessing(number):
    parsed = parse_address(f"嘉義縣民雄鄉大學路{number}號")
    assert not parsed.is_complete
    assert parsed.unparsed


@pytest.mark.parametrize(
    "county,town,road",
    [
        ("臺中市", "大里區", "中山路"),
        ("高雄市", "路竹區", "中正路"),
        ("屏東縣", "里港鄉", "中山路"),
        ("臺東縣", "太麻里鄉", "中山路"),
        ("南投縣", "水里鄉", "中山路"),
        ("臺北市", "信義區", "市府路"),
        ("臺南市", "新市區", "中山路"),
    ],
)
def test_township_names_and_city_prefixed_roads(county, town, road):
    parsed = parse_address(county + town + road + "1號")
    assert parsed.township == town
    assert parsed.road == road
    assert AddressContext(township=town).township == town
    with pytest.raises(ValueError, match="conflicts"):
        complete_address(parsed.original, AddressContext(township="太平區"))


def test_road_prefix_cannot_be_dropped_as_optional_village():
    assert not addresses_match(
        parse_address("台中市南區南路1號"), parse_address("台中市南區美村南路1號")
    )


def test_road_prefix_cannot_be_dropped_as_optional_township():
    assert not addresses_match(parse_address("新北市一路1號"), parse_address("新北市新市一路1號"))
