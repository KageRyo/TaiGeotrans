"""Public high-level API for Taiwan coordinate and address transforms."""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, TypeVar, cast

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

    def geocode(self, address: str) -> GeocodeResult:
        """Geocode a Taiwan address and return WGS84/TWD97 coordinates."""
        if not address or not address.strip():
            return GeocodeResult(
                input_address=address,
                status=TransformStatus.INVALID,
                error_message="Empty address",
            )

        address = address.strip()
        client = self._get_tgos_client()

        try:
            lon, lat, matched_address, confidence = client.geocode_address(address)

            if lon is None or lat is None:
                return GeocodeResult(
                    input_address=address,
                    status=TransformStatus.FAILED,
                    error_message="TGOS could not geocode this address",
                    source="TGOS",
                )

            try:
                x, y = self.transformer.wgs84_to_twd97(lon, lat, validate=False)
            except Exception as exc:
                logger.debug("Coordinate transformation failed", exc_info=True)
                return GeocodeResult(
                    input_address=address,
                    wgs84_lon=lon,
                    wgs84_lat=lat,
                    status=TransformStatus.FAILED,
                    matched_address=matched_address,
                    confidence=confidence,
                    source="TGOS",
                    error_message=f"Coordinate transformation failed: {exc}",
                )

            in_bounds = self.transformer.is_in_taiwan_bounds_twd97(x, y)
            status = TransformStatus.SUCCESS if in_bounds else TransformStatus.OUT_OF_BOUNDS
            return GeocodeResult(
                input_address=address,
                twd97_x=x,
                twd97_y=y,
                wgs84_lon=lon,
                wgs84_lat=lat,
                status=status,
                confidence=confidence,
                source="TGOS",
                matched_address=matched_address,
                error_message=None
                if in_bounds
                else "Coordinates outside supported Taiwan-area bounds",
            )
        except Exception as exc:
            from taigeotrans.providers.tgos import TGOSConfigurationError

            if isinstance(exc, TGOSConfigurationError):
                raise
            logger.debug("Geocoding failed for address", exc_info=True)
            return GeocodeResult(
                input_address=address,
                status=TransformStatus.FAILED,
                source="TGOS",
                error_message=f"Processing failed: {exc}",
            )

    def batch_geocode(
        self,
        addresses: list[str],
        show_progress: bool = True,
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
                results.append(self.geocode(address))

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
