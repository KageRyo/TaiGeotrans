"""Public high-level API for Taiwan coordinate and address transforms."""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, TypeVar, cast

from taigeotrans.address import (
    AddressContext,
    TaiwanAddress,
    _subnumber,
    address_mismatch,
    complete_address,
    normalize_address,
    parse_address,
)
from taigeotrans.models import GeocodeResult, TransformStatus
from taigeotrans.utils.projection import CoordinateTransformer

if TYPE_CHECKING:
    import pandas as pd

    from taigeotrans.providers.tgos import TGOSClient

logger = logging.getLogger(__name__)
_Item = TypeVar("_Item")


def _with_progress(
    items: Iterable[_Item],
    description: str,
    show_progress: bool,
) -> Iterable[_Item]:
    """Add a progress bar when requested and the optional dependency exists."""
    if not show_progress:
        return items

    try:
        from tqdm import tqdm
    except ImportError:
        logger.debug("tqdm is not installed; continuing without a progress bar")
        return items

    return cast(Iterable[_Item], tqdm(items, desc=description))


def _require_pandas() -> Any:
    """Import pandas only for callers that request DataFrame output."""
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "DataFrame output requires pandas. Install it with "
            "`pip install taigeotrans[dataframe]`."
        ) from exc
    return pd


def _verify_candidate(
    requested: TaiwanAddress, row: dict[str, Any]
) -> tuple[str | None, tuple[float, float] | None]:
    matched = row.get("FULL_ADDR")
    if not isinstance(matched, str):
        return "missing_matched_address", None
    returned = parse_address(matched)
    if returned.village is not None and (not row.get("VILLAGE") or not row.get("ROAD")):
        return "ambiguous_village_or_road", None
    for key, field, suffix in [
        ("COUNTY", "county", ""),
        ("TOWN", "township", ""),
        ("VILLAGE", "village", ""),
        ("ROAD", "road", ""),
        ("NEIGHBORHOOD", "neighborhood", "鄰"),
        ("SECTION", "section", "段"),
        ("LANE", "lane", "巷"),
        ("ALLEY", "alley", "弄"),
        ("NUMBER", "house_number", "號"),
    ]:
        value = row.get(key)
        if value is None or value == "":
            continue
        normalized = normalize_address(str(value))
        try:
            if suffix:
                normalized = _subnumber(normalized.replace("號之", "之").removesuffix(suffix))
        except (ValueError, KeyError):
            return "provider_component_conflict", None
        if normalized != getattr(returned, field):
            return "provider_component_conflict", None
    mismatch = address_mismatch(
        requested,
        returned,
        allow_extra_village=bool(row.get("VILLAGE") and row.get("ROAD")),
        allow_extra_township=bool(row.get("TOWN") and row.get("ROAD")),
    )
    if mismatch:
        return mismatch, None
    if row.get("SUB_ALLEY") or row.get("TONG"):
        return "unsupported_subdivision", None
    for key in ("precision", "spatial_precision", "location_type"):
        precision = row.get(key)
        if precision is not None and (
            not isinstance(precision, str)
            or precision not in {"address", "house_number", "house", "building", "rooftop", "point"}
        ):
            return "coarse_provider_precision", None
    try:
        if isinstance(row["X"], bool) or isinstance(row["Y"], bool):
            return "invalid_coordinates", None
        lon, lat = float(row["X"]), float(row["Y"])
    except (ValueError, TypeError, KeyError):
        return "invalid_coordinates", None
    if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
        return "invalid_coordinates", None
    return None, (lon, lat)


class TaiGeotrans:
    """Taiwan address geocoder and WGS84/TWD97 coordinate transformer.

    Coordinate transformation works without network access or TGOS
    credentials.  The TGOS client is created lazily only when ``geocode`` or
    ``batch_geocode`` is called.
    """

    def __init__(
        self,
        tgos_client: TGOSClient | None = None,
        transformer: CoordinateTransformer | None = None,
        tgos_app_id: str | None = None,
        tgos_api_key: str | None = None,
    ) -> None:
        """Initialize the transformer.

        Args:
            tgos_client: Optional preconfigured TGOS client, useful for tests
                and applications that manage their own HTTP client.
            transformer: Optional coordinate transformer implementation.
            tgos_app_id: TGOS application ID. Used when the client is created
                lazily; otherwise ``TGOS_APP_ID`` is read from the environment.
            tgos_api_key: TGOS API key. Used when the client is created lazily;
                otherwise ``TGOS_API_KEY`` is read from the environment.
        """
        if tgos_client is not None and (tgos_app_id is not None or tgos_api_key is not None):
            raise ValueError("Pass either tgos_client or tgos_app_id/tgos_api_key, not both")

        self.tgos_client = tgos_client
        self._tgos_app_id = tgos_app_id
        self._tgos_api_key = tgos_api_key
        self.transformer = transformer or CoordinateTransformer()
        logger.debug("TaiGeotrans initialized")

    def _get_tgos_client(self) -> TGOSClient:
        if self.tgos_client is None:
            try:
                from taigeotrans.providers.tgos import TGOSClient
            except ImportError as exc:
                raise ImportError(
                    "Address geocoding requires httpx. Install it with "
                    "`pip install taigeotrans[geocoding]`."
                ) from exc

            self.tgos_client = TGOSClient(
                app_id=self._tgos_app_id,
                api_key=self._tgos_api_key,
            )
        return self.tgos_client

    def geocode(
        self, address: str, *, context: AddressContext | None = None, candidate_limit: int = 9
    ) -> GeocodeResult:
        """Return coordinates only for one verified address-level TGOS candidate.

        Unlike 0.1.x, a fuzzy/provider-first coordinate is not successful address
        verification. The original input is retained, including its whitespace.
        """
        if not address or not address.strip():
            return GeocodeResult(
                input_address=address,
                status=TransformStatus.INVALID,
                match_status="insufficient",
                verification_reason="empty_address",
                error_message="Empty address",
            )
        try:
            requested = complete_address(address, context)
        except ValueError as exc:
            return GeocodeResult(
                input_address=address,
                status=TransformStatus.INVALID,
                match_status="unresolved",
                verification_reason="context_conflict",
                error_message=str(exc),
            )
        metadata: dict[str, Any] = {
            "input_address": address,
            "normalized_address": requested.normalized,
            "completed_query": requested.query,
            "completed_fields": list(requested.completed_fields),
            "source": "TGOS",
            "spatial_precision": "unknown",
        }
        if not requested.is_complete:
            return GeocodeResult(
                **metadata,
                status=TransformStatus.PARTIAL,
                match_status="insufficient",
                verification_reason="insufficient_address",
            )
        client = self._get_tgos_client()
        try:
            reply = client.geocode_candidates(requested.query, candidate_limit=candidate_limit)
        except Exception as exc:
            from taigeotrans.providers.tgos import TGOSConfigurationError

            if isinstance(exc, (TGOSConfigurationError, ValueError)):
                raise
            logger.debug("Geocoding provider failed (%s)", type(exc).__name__)
            return GeocodeResult(
                **metadata,
                status=TransformStatus.FAILED,
                match_status="unresolved",
                verification_reason="provider_error",
                error_message="TGOS request or response failed",
            )
        verified = []
        details = []
        for row in reply.candidates:
            reason, coordinates = _verify_candidate(requested, row)
            if reason is None and reply.match_type != "完全比對":
                reason = "provider_match_not_exact"
            item = {
                "matched_address": row.get("FULL_ADDR"),
                "provider_match_type": reply.match_type,
                "verification_reason": reason or "components_confirmed",
            }
            details.append(item)
            if reason is None and coordinates is not None:
                verified.append((row, coordinates))
        metadata.update(
            candidate_count=len(reply.candidates),
            provider_candidate_count=reply.reported_count,
            response_sha256=reply.response_sha256,
            candidates=details,
        )
        if reply.limit_reached or len(verified) > 1:
            state, reason = (
                "ambiguous",
                "candidate_limit_reached"
                if reply.limit_reached
                else "multiple_verified_candidates",
            )
        elif len(verified) == 1:
            selected, (lon, lat) = verified[0]
            try:
                x, y = self.transformer.wgs84_to_twd97(lon, lat, validate=False)
            except Exception:
                return GeocodeResult(
                    **metadata,
                    status=TransformStatus.FAILED,
                    match_status="unresolved",
                    verification_reason="coordinate_transform_failed",
                )
            in_bounds = self.transformer.is_in_taiwan_bounds_twd97(x, y)
            if not in_bounds:
                return GeocodeResult(
                    **metadata,
                    status=TransformStatus.OUT_OF_BOUNDS,
                    match_status="unresolved",
                    verification_reason="coordinates_outside_taiwan",
                )
            metadata["spatial_precision"] = "address"
            return GeocodeResult(
                **metadata,
                status=TransformStatus.SUCCESS if in_bounds else TransformStatus.OUT_OF_BOUNDS,
                match_status="verified_exact",
                verification_reason="components_confirmed",
                twd97_x=x,
                twd97_y=y,
                wgs84_lon=lon,
                wgs84_lat=lat,
                matched_address=selected["FULL_ADDR"],
                confidence=1.0,
            )
        elif reply.candidates and reply.match_type and reply.match_type != "完全比對":
            state, reason = "fuzzy", "provider_match_not_exact"
        else:
            state, reason = (
                "unresolved",
                "components_not_confirmed" if reply.candidates else "no_match",
            )
        return GeocodeResult(
            **metadata,
            status=TransformStatus.PARTIAL
            if state in {"ambiguous", "fuzzy"}
            else TransformStatus.FAILED,
            match_status=state,
            verification_reason=reason,
        )

    def batch_geocode(
        self,
        addresses: list[str],
        show_progress: bool = True,
        *,
        context: AddressContext | None = None,
        candidate_limit: int = 9,
    ) -> list[GeocodeResult]:
        """Geocode multiple addresses while preserving input order."""
        if not addresses:
            logger.warning("Empty address list")
            return []

        client = self._get_tgos_client()
        results: list[GeocodeResult] = []
        iterator = _with_progress(addresses, "Geocoding", show_progress)

        with client:
            for address in iterator:
                results.append(
                    self.geocode(address, context=context, candidate_limit=candidate_limit)
                )

        success_count = sum(1 for result in results if result.status == TransformStatus.SUCCESS)
        logger.info("Batch geocoding complete: %s/%s successful", success_count, len(results))
        return results

    def transform_lonlat(self, lon: float, lat: float) -> GeocodeResult:
        """Transform WGS84 longitude/latitude to TWD97 EPSG:3826."""
        if not math.isfinite(lon) or not -180 <= lon <= 180:
            return GeocodeResult(
                input_lon=lon,
                input_lat=lat,
                status=TransformStatus.INVALID,
                error_message=f"Longitude {lon} out of valid range [-180, 180]",
            )
        if not math.isfinite(lat) or not -90 <= lat <= 90:
            return GeocodeResult(
                input_lon=lon,
                input_lat=lat,
                status=TransformStatus.INVALID,
                error_message=f"Latitude {lat} out of valid range [-90, 90]",
            )

        try:
            x, y = self.transformer.wgs84_to_twd97(lon, lat, validate=False)
            in_bounds = self.transformer.is_in_taiwan_bounds_twd97(x, y)
            status = TransformStatus.SUCCESS if in_bounds else TransformStatus.OUT_OF_BOUNDS
            return GeocodeResult(
                input_lon=lon,
                input_lat=lat,
                twd97_x=x,
                twd97_y=y,
                wgs84_lon=lon,
                wgs84_lat=lat,
                status=status,
                confidence=1.0,
                source="PYPROJ",
                error_message=None
                if in_bounds
                else "Coordinates outside supported Taiwan-area bounds",
            )
        except Exception as exc:
            logger.debug("Coordinate transformation failed", exc_info=True)
            return GeocodeResult(
                input_lon=lon,
                input_lat=lat,
                status=TransformStatus.FAILED,
                source="PYPROJ",
                error_message=f"Transformation failed: {exc}",
            )

    def transform_twd97(self, x: float, y: float) -> GeocodeResult:
        """Transform TWD97 EPSG:3826 coordinates to WGS84."""
        if not math.isfinite(x) or not math.isfinite(y):
            return GeocodeResult(
                input_twd97_x=x,
                input_twd97_y=y,
                status=TransformStatus.INVALID,
                error_message="TWD97 coordinates must be finite numbers",
            )

        try:
            lon, lat = self.transformer.twd97_to_wgs84(x, y, validate=False)
            in_bounds = self.transformer.is_in_taiwan_bounds_twd97(x, y)
            status = TransformStatus.SUCCESS if in_bounds else TransformStatus.OUT_OF_BOUNDS
            return GeocodeResult(
                input_twd97_x=x,
                input_twd97_y=y,
                twd97_x=x,
                twd97_y=y,
                wgs84_lon=lon,
                wgs84_lat=lat,
                status=status,
                confidence=1.0,
                source="PYPROJ",
                error_message=None
                if in_bounds
                else "Coordinates outside supported Taiwan-area bounds",
            )
        except Exception as exc:
            logger.debug("Reverse coordinate transformation failed", exc_info=True)
            return GeocodeResult(
                input_twd97_x=x,
                input_twd97_y=y,
                status=TransformStatus.FAILED,
                source="PYPROJ",
                error_message=f"Transformation failed: {exc}",
            )

    def batch_transform_lonlat(
        self,
        coords: list[tuple[float, float]],
        show_progress: bool = True,
    ) -> list[GeocodeResult]:
        """Transform multiple WGS84 coordinate pairs."""
        if not coords:
            logger.warning("Empty coordinate list")
            return []

        iterator = _with_progress(coords, "Transforming", show_progress)
        results = [self.transform_lonlat(lon, lat) for lon, lat in iterator]
        success_count = sum(1 for result in results if result.status == TransformStatus.SUCCESS)
        logger.info(
            "Batch transformation complete: %s/%s successful",
            success_count,
            len(results),
        )
        return results

    def batch_geocode_to_dataframe(
        self,
        addresses: list[str],
        show_progress: bool = True,
    ) -> pd.DataFrame:
        """Geocode addresses and return a pandas DataFrame."""
        pd = _require_pandas()
        results = self.batch_geocode(addresses, show_progress=show_progress)
        return pd.DataFrame([result.to_dict() for result in results])

    def batch_transform_lonlat_to_dataframe(
        self,
        coords: list[tuple[float, float]],
        show_progress: bool = True,
    ) -> pd.DataFrame:
        """Transform WGS84 coordinates and return a pandas DataFrame."""
        pd = _require_pandas()
        results = self.batch_transform_lonlat(coords, show_progress=show_progress)
        return pd.DataFrame([result.to_dict() for result in results])

    def to_geojson(
        self,
        results: list[GeocodeResult],
        filter_failed: bool = True,
    ) -> dict[str, Any]:
        """Convert results to a GeoJSON FeatureCollection."""
        features: list[dict[str, Any]] = []
        for result in results:
            if filter_failed and result.status == TransformStatus.FAILED:
                continue
            try:
                features.append(result.to_geojson_feature())
            except ValueError:
                continue

        return {"type": "FeatureCollection", "features": features}


__all__ = ["TaiGeotrans"]
