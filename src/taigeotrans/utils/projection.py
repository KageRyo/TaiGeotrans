"""
Coordinate transformation utilities using pyproj for high-precision conversions.
"""

import logging

from pyproj import Transformer
from pyproj.exceptions import ProjError

logger = logging.getLogger(__name__)

# Approximate rectangular regions used for result classification.  They are
# deliberately not administrative boundaries: the package uses them only to
# distinguish Taiwan-area coordinates from clearly unrelated coordinates.
# The supported scope includes Taiwan main island, Penghu, Kinmen, and Matsu.
TAIWAN_WGS84_BOUNDS: tuple[tuple[float, float, float, float], ...] = (
    (120.0, 122.5, 21.5, 25.5),  # Taiwan main island
    (119.0, 119.8, 23.0, 23.9),  # Penghu
    (118.0, 118.6, 24.2, 24.7),  # Kinmen
    (119.8, 120.6, 25.8, 26.5),  # Matsu
)

TAIWAN_TWD97_BOUNDS: tuple[tuple[float, float, float, float], ...] = (
    (146000.0, 401000.0, 2378000.0, 2823000.0),  # Taiwan main island
    (44000.0, 128000.0, 2545000.0, 2645000.0),  # Penghu
    (-55000.0, 8000.0, 2680000.0, 2735000.0),  # Kinmen
    (129000.0, 211000.0, 2854000.0, 2933000.0),  # Matsu
)


def _is_in_bounds(
    first: float,
    second: float,
    regions: tuple[tuple[float, float, float, float], ...],
) -> bool:
    return any(
        min_first <= first <= max_first and min_second <= second <= max_second
        for min_first, max_first, min_second, max_second in regions
    )


def is_in_taiwan_wgs84_bounds(lon: float, lat: float) -> bool:
    """Return whether WGS84 coordinates fall in a supported Taiwan region."""
    return _is_in_bounds(lon, lat, TAIWAN_WGS84_BOUNDS)


def is_in_taiwan_twd97_bounds(x: float, y: float) -> bool:
    """Return whether EPSG:3826 coordinates fall in a supported Taiwan region."""
    return _is_in_bounds(x, y, TAIWAN_TWD97_BOUNDS)


class CoordinateTransformer:
    """Coordinate transformer for WGS84 <-> TWD97 conversions"""

    # EPSG codes
    EPSG_WGS84 = 4326  # WGS84 - Global geographic coordinate system
    EPSG_TWD97 = 3826  # TWD97 - Taiwan Datum 1997

    # Historical main-island bounds retained for compatibility with callers
    # that accessed these constants directly.  Classification methods use
    # the region lists above, which also include Penghu, Kinmen, and Matsu.
    TWD97_X_MIN = 140000
    TWD97_X_MAX = 350000
    TWD97_Y_MIN = 2400000
    TWD97_Y_MAX = 2800000

    # Historical broad WGS84 bounds retained for compatibility.
    WGS84_LON_MIN = 119.0
    WGS84_LON_MAX = 122.5
    WGS84_LAT_MIN = 21.5
    WGS84_LAT_MAX = 25.5

    def __init__(self) -> None:
        """Initialize coordinate transformer"""
        try:
            # WGS84 -> TWD97 transformer
            self._wgs84_to_twd97 = Transformer.from_crs(
                f"EPSG:{self.EPSG_WGS84}",
                f"EPSG:{self.EPSG_TWD97}",
                always_xy=True,  # Force (lon, lat) order
            )

            # TWD97 -> WGS84 transformer
            self._twd97_to_wgs84 = Transformer.from_crs(
                f"EPSG:{self.EPSG_TWD97}", f"EPSG:{self.EPSG_WGS84}", always_xy=True
            )

            logger.info("Coordinate transformer initialized successfully")
        except ProjError as e:
            logger.error(f"Failed to initialize coordinate transformer: {e}")
            raise RuntimeError(f"Cannot initialize coordinate transformer: {e}")

    def wgs84_to_twd97(self, lon: float, lat: float, validate: bool = True) -> tuple[float, float]:
        """
        Convert WGS84 geographic coordinates to TWD97 projected coordinates.

        Args:
            lon: WGS84 longitude
            lat: WGS84 latitude
            validate: Whether to validate input coordinate range

        Returns:
            (x, y): TWD97 coordinates (easting, northing)

        Raises:
            ValueError: Invalid input coordinates
            RuntimeError: Transformation failed
        """
        if validate:
            self._validate_wgs84(lon, lat)

        try:
            x, y = self._wgs84_to_twd97.transform(lon, lat)
            logger.debug(f"WGS84 ({lon}, {lat}) -> TWD97 ({x:.2f}, {y:.2f})")
            return x, y
        except ProjError as e:
            error_msg = f"WGS84 to TWD97 conversion failed ({lon}, {lat}): {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def twd97_to_wgs84(self, x: float, y: float, validate: bool = True) -> tuple[float, float]:
        """
        Convert TWD97 projected coordinates to WGS84 geographic coordinates.

        Args:
            x: TWD97 X coordinate (easting)
            y: TWD97 Y coordinate (northing)
            validate: Whether to validate input coordinate range

        Returns:
            (lon, lat): WGS84 longitude and latitude

        Raises:
            ValueError: Invalid input coordinates
            RuntimeError: Transformation failed
        """
        if validate:
            self._validate_twd97(x, y)

        try:
            lon, lat = self._twd97_to_wgs84.transform(x, y)
            logger.debug(f"TWD97 ({x:.2f}, {y:.2f}) -> WGS84 ({lon}, {lat})")
            return lon, lat
        except ProjError as e:
            error_msg = f"TWD97 to WGS84 conversion failed ({x}, {y}): {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def _validate_wgs84(self, lon: float, lat: float) -> None:
        """Validate WGS84 coordinate range"""
        if not (-180 <= lon <= 180):
            raise ValueError(f"Longitude {lon} out of valid range [-180, 180]")
        if not (-90 <= lat <= 90):
            raise ValueError(f"Latitude {lat} out of valid range [-90, 90]")

        if not is_in_taiwan_wgs84_bounds(lon, lat):
            logger.warning(
                "Coordinates (%s, %s) may not be within the supported Taiwan-area "
                "bounds (Taiwan main island, Penghu, Kinmen, or Matsu)",
                lon,
                lat,
            )

    def _validate_twd97(self, x: float, y: float) -> None:
        """Validate TWD97 coordinate range"""
        if not is_in_taiwan_twd97_bounds(x, y):
            logger.warning(
                "TWD97 coordinates (%.2f, %.2f) may be outside the supported "
                "Taiwan-area bounds (Taiwan main island, Penghu, Kinmen, or Matsu)",
                x,
                y,
            )

    def is_in_taiwan_bounds_wgs84(self, lon: float, lat: float) -> bool:
        """Check if WGS84 coordinates are within Taiwan mainland approximate bounds"""
        return is_in_taiwan_wgs84_bounds(lon, lat)

    def is_in_taiwan_bounds_twd97(self, x: float, y: float) -> bool:
        """Check if TWD97 coordinates are within Taiwan mainland bounds"""
        return is_in_taiwan_twd97_bounds(x, y)
