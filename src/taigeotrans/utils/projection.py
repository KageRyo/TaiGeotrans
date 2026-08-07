"""
Coordinate transformation utilities using pyproj for high-precision conversions.
"""

import logging

from pyproj import Transformer
from pyproj.exceptions import ProjError

logger = logging.getLogger(__name__)


class CoordinateTransformer:
    """Coordinate transformer for WGS84 <-> TWD97 conversions"""

    # EPSG codes
    EPSG_WGS84 = 4326  # WGS84 - Global geographic coordinate system
    EPSG_TWD97 = 3826  # TWD97 - Taiwan Datum 1997

    # Taiwan mainland TWD97 coordinate bounds (meters)
    TWD97_X_MIN = 140000
    TWD97_X_MAX = 350000
    TWD97_Y_MIN = 2400000
    TWD97_Y_MAX = 2800000

    # Taiwan mainland WGS84 approximate bounds (degrees)
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

        # Warning: coordinates not in Taiwan mainland bounds
        if not (
            self.WGS84_LON_MIN <= lon <= self.WGS84_LON_MAX
            and self.WGS84_LAT_MIN <= lat <= self.WGS84_LAT_MAX
        ):
            logger.warning(
                f"Coordinates ({lon}, {lat}) may not be within Taiwan mainland bounds. "
                f"Suggested range: lon [{self.WGS84_LON_MIN}, {self.WGS84_LON_MAX}], "
                f"lat [{self.WGS84_LAT_MIN}, {self.WGS84_LAT_MAX}]"
            )

    def _validate_twd97(self, x: float, y: float) -> None:
        """Validate TWD97 coordinate range"""
        if not (self.TWD97_X_MIN <= x <= self.TWD97_X_MAX):
            logger.warning(
                f"TWD97 X coordinate {x:.2f} may be outside Taiwan mainland bounds "
                f"[{self.TWD97_X_MIN}, {self.TWD97_X_MAX}]"
            )
        if not (self.TWD97_Y_MIN <= y <= self.TWD97_Y_MAX):
            logger.warning(
                f"TWD97 Y coordinate {y:.2f} may be outside Taiwan mainland bounds "
                f"[{self.TWD97_Y_MIN}, {self.TWD97_Y_MAX}]"
            )

    def is_in_taiwan_bounds_wgs84(self, lon: float, lat: float) -> bool:
        """Check if WGS84 coordinates are within Taiwan mainland approximate bounds"""
        return (
            self.WGS84_LON_MIN <= lon <= self.WGS84_LON_MAX
            and self.WGS84_LAT_MIN <= lat <= self.WGS84_LAT_MAX
        )

    def is_in_taiwan_bounds_twd97(self, x: float, y: float) -> bool:
        """Check if TWD97 coordinates are within Taiwan mainland bounds"""
        return (
            self.TWD97_X_MIN <= x <= self.TWD97_X_MAX and self.TWD97_Y_MIN <= y <= self.TWD97_Y_MAX
        )
