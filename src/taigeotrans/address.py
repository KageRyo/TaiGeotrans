"""Conservative, offline Taiwan house-address parsing and component matching.

This is a syntactic comparison, not a registry of real addresses. Unparsed
content prevents verification rather than being discarded to improve coverage.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from typing import Any

COUNTIES = tuple(
    "台北市 新北市 桃園市 台中市 台南市 高雄市 基隆市 新竹市 嘉義市 "
    "新竹縣 苗栗縣 彰化縣 南投縣 雲林縣 嘉義縣 屏東縣 宜蘭縣 花蓮縣 台東縣 "
    "澎湖縣 金門縣 連江縣".split()
)
_DIGITS = dict(zip("零〇一二三四五六七八九兩", (0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 2), strict=True))
_NUM = r"[0-9零〇一二三四五六七八九十百千兩]+"
_SUBNUM = rf"{_NUM}(?:(?:之|-){_NUM})?"


def normalize_address(value: str) -> str:
    """Normalize Unicode/spacing and 台/臺 without deleting address components."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).replace("臺", "台")


def _number(value: str) -> str:
    if re.fullmatch(r"\d+", value):
        return str(int(value))
    if all(char in _DIGITS for char in value):
        return str(int("".join(str(_DIGITS[char]) for char in value)))
    if not re.fullmatch(r"[零〇一二三四五六七八九十百千兩]+", value):
        raise ValueError("Mixed or unsupported numeral")
    total, digit = 0, 0
    for char in value:
        if char in _DIGITS:
            digit = _DIGITS[char]
        else:
            total += (digit or 1) * {"十": 10, "百": 100, "千": 1000}[char]
            digit = 0
    number = total + digit
    if not 0 < number < 10000:
        raise ValueError("Unsupported Chinese numeral")
    chars = "零一二三四五六七八九"
    rendered, zero = "", False
    digits = str(number)
    for index, char in enumerate(digits):
        current = int(char)
        if not current:
            zero = bool(rendered)
            continue
        if zero:
            rendered += "零"
            zero = False
        rendered += chars[current] + ("", "十", "百", "千")[len(digits) - index - 1]
    if rendered.startswith("一十"):
        rendered = rendered[1:]
    normalized = value.replace("兩", "二").replace("〇", "零")
    if normalized not in {rendered, "一" + rendered if rendered.startswith("十") else rendered}:
        raise ValueError("Ambiguous or malformed Chinese numeral")
    return str(number)


def _subnumber(value: str) -> str:
    parts = re.split(r"之|-", value)
    if len(parts) > 2:
        raise ValueError("Unsupported house subdivision")
    return "-".join(_number(part) for part in parts)


@dataclass(frozen=True)
class AddressContext:
    """Caller-supplied, independently trusted administrative context only."""

    county: str | None = None
    township: str | None = None

    def __post_init__(self) -> None:
        if self.county is not None:
            county = normalize_address(self.county)
            if county not in COUNTIES:
                raise ValueError("Unrecognized context county")
            object.__setattr__(self, "county", county)
        if self.township is not None:
            township = normalize_address(self.township)
            if not re.fullmatch(r"[^村鄰街段巷弄號\d]{1,8}[鄉鎮市區]", township):
                raise ValueError("Invalid context township")
            object.__setattr__(self, "township", township)


@dataclass(frozen=True)
class TaiwanAddress:
    original: str
    normalized: str
    county: str | None = None
    township: str | None = None
    village: str | None = None
    neighborhood: str | None = None
    road: str | None = None
    section: str | None = None
    lane: str | None = None
    alley: str | None = None
    house_number: str | None = None
    floor: str | None = None
    unparsed: str = ""
    completed_fields: tuple[str, ...] = ()

    @property
    def is_complete(self) -> bool:
        return bool(self.county and self.road and self.house_number and not self.unparsed)

    @property
    def query(self) -> str:
        pieces = [self.county, self.township, self.village]
        for field, suffix in [
            ("neighborhood", "鄰"),
            ("road", ""),
            ("section", "段"),
            ("lane", "巷"),
            ("alley", "弄"),
            ("house_number", "號"),
            ("floor", "樓"),
        ]:
            value = getattr(self, field)
            if value is not None:
                pieces.append(value.replace("-", "之") + suffix)
        return "".join(piece for piece in pieces if piece) + self.unparsed


def parse_address(value: str) -> TaiwanAddress:
    """Parse supported components, preserving unsupported remainder verbatim."""
    normalized = normalize_address(value)
    rest = normalized
    # Postal/country prefixes carry no house-level location inference.
    rest = re.sub(r"^(?:中華民國|台灣(?:省)?)", "", rest)
    rest = re.sub(r"^\d{3}(?:\d{2,3})?(?=[^\d])", "", rest)
    fields: dict[str, Any] = {}
    county = next((county for county in COUNTIES if rest.startswith(county)), None)
    fields["county"] = county
    if county:
        rest = rest[len(county) :]
    for name, pattern in [
        ("township", r"(?:[^村鄰街段巷弄號\d]{1,8}?[鄉鎮區]|[^村鄰路街段巷弄號\d]{1,8}?市)"),
        ("village", r"[^鄰路街段巷弄號\d]{1,8}[村里]"),
        ("neighborhood", rf"{_NUM}鄰"),
        ("road", r"[^號巷弄\d]+?(?:大道|路|街)"),
        ("section", rf"{_NUM}段"),
        ("lane", rf"{_SUBNUM}巷"),
        ("alley", rf"{_SUBNUM}弄"),
        ("house_number", rf"{_SUBNUM}號(?:之{_NUM})?"),
        ("floor", rf"{_NUM}樓"),
    ]:
        match = re.match(pattern, rest)
        if match is None:
            fields[name] = None
            continue
        fragment = match.group()
        rest = rest[len(fragment) :]
        try:
            if name == "house_number":
                numeric = fragment.replace("號之", "之").replace("號", "")
                fields[name] = _subnumber(numeric)
            elif name in {"neighborhood", "section", "lane", "alley", "floor"}:
                fields[name] = _subnumber(fragment[:-1])
            else:
                fields[name] = fragment
        except ValueError:
            fields[name] = None
            rest = fragment + rest
            break
    return TaiwanAddress(original=value, normalized=normalized, unparsed=rest, **fields)


def complete_address(value: str, context: AddressContext | None = None) -> TaiwanAddress:
    """Fill absent administrative components only; conflicts are errors."""
    result = parse_address(value)
    if context is None:
        return result
    completed = []
    for field in ("county", "township"):
        supplied, expected = getattr(result, field), getattr(context, field)
        if expected is None:
            continue
        if supplied is not None and supplied != expected:
            raise ValueError(f"Input {field} conflicts with trusted context")
        if supplied is None:
            result = replace(result, **{field: expected})
            completed.append(field)
    return replace(result, completed_fields=tuple(completed))


def address_mismatch(
    requested: TaiwanAddress,
    returned: TaiwanAddress,
    *,
    allow_extra_village: bool = False,
    allow_extra_township: bool = False,
) -> str | None:
    """Return a reason when supplied components cannot be independently confirmed."""
    if not requested.is_complete:
        return "insufficient_address"
    if not returned.is_complete:
        return "incomplete_candidate"
    # Additional road/house subdivisions change the address even if omitted in input.
    for field in ("county", "road", "section", "lane", "alley", "house_number"):
        if getattr(requested, field) != getattr(returned, field):
            return f"{field}_mismatch"
    if requested.township != returned.township and not (
        allow_extra_township and requested.township is None
    ):
        return "ambiguous_township_or_road"
    # A 村/里 prefix can also be part of a road name (美村南路). Without
    # an explicit neighbourhood separator, never drop it as optional annotation.
    if requested.village != returned.village and not (
        allow_extra_village and requested.village is None
    ):
        return "ambiguous_village_or_road"
    for field in ("township", "village", "neighborhood", "floor"):
        value = getattr(requested, field)
        if value is not None and value != getattr(returned, field):
            return f"{field}_not_confirmed"
    return None


def addresses_match(requested: TaiwanAddress, returned: TaiwanAddress) -> bool:
    """Compare address-level components; this does not validate survey accuracy."""
    return address_mismatch(requested, returned) is None
