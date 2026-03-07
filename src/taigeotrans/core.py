"""
TaiGeotrans core transformer integrating all geocoding and coordinate conversion functionalities.
"""

import logging
from typing import Optional, Union

import pandas as pd
from tqdm import tqdm

from taigeotrans.models import GeocodeResult, TransformStatus
from taigeotrans.providers.tgos import TGOSClient
from taigeotrans.utils.projection import CoordinateTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TaiGeotrans:
    """
    Taiwan geospatial transformer for address geocoding and coordinate conversion.
    Completely stateless with no database dependencies.
    """
    
    def __init__(
        self,
        tgos_client: Optional[TGOSClient] = None,
        transformer: Optional[CoordinateTransformer] = None,
    ) -> None:
        """
        Initialize transformer.
        
        Args:
            tgos_client: TGOS API client (optional, uses default config if not provided)
            transformer: Coordinate transformer (optional, uses default config if not provided)
        """
        self.tgos_client = tgos_client or TGOSClient()
        self.transformer = transformer or CoordinateTransformer()
        logger.info("TaiGeotrans initialized")
    
    def geocode(self, address: str) -> GeocodeResult:
        """
        Geocode Taiwan address to TWD97 coordinates (EPSG:3826).
        
        Args:
            address: Taiwan address in Chinese
        
        Returns:
            GeocodeResult containing TWD97 coordinates, WGS84 coordinates and metadata
        """
        if not address or not address.strip():
            return GeocodeResult(
                input_address=address,
                status=TransformStatus.INVALID,
                error_message="Empty address"
            )
        
        address = address.strip()
        
        try:
            # 1. Use TGOS API to convert address to WGS84 coordinates
            lon, lat, matched_address, confidence = self.tgos_client.geocode_address(address)
            
            if lon is None or lat is None:
                return GeocodeResult(
                    input_address=address,
                    status=TransformStatus.FAILED,
                    error_message="TGOS unable to geocode this address",
                    source="TGOS"
                )
            
            # 2. Convert WGS84 to TWD97
            try:
                x, y = self.transformer.wgs84_to_twd97(lon, lat, validate=False)
            except Exception as e:
                logger.error(f"Coordinate transformation failed: {e}")
                return GeocodeResult(
                    input_address=address,
                    wgs84_lon=lon,
                    wgs84_lat=lat,
                    status=TransformStatus.FAILED,
                    matched_address=matched_address,
                    confidence=confidence,
                    source="TGOS",
                    error_message=f"Coordinate transformation failed: {e}"
                )
            
            # 3. Check if TWD97 coordinates are within valid bounds
            in_bounds = self.transformer.is_in_taiwan_bounds_twd97(x, y)
            status = TransformStatus.SUCCESS if in_bounds else TransformStatus.OUT_OF_BOUNDS
            
            return GeocodeResult(
                input_address=address,
                input_lon=None,
                input_lat=None,
                twd97_x=x,
                twd97_y=y,
                wgs84_lon=lon,
                wgs84_lat=lat,
                status=status,
                confidence=confidence,
                source="TGOS",
                matched_address=matched_address,
                error_message=None if in_bounds else "Coordinates outside Taiwan mainland bounds"
            )
        
        except Exception as e:
            logger.error(f"Geocoding failed for '{address}': {e}")
            return GeocodeResult(
                input_address=address,
                status=TransformStatus.FAILED,
                error_message=f"Processing failed: {e}"
            )
    
    def batch_geocode(
        self, 
        addresses: list[str],
        show_progress: bool = True
    ) -> list[GeocodeResult]:
        """
        Batch geocode multiple Taiwan addresses.
        
        Args:
            addresses: List of addresses
            show_progress: Whether to show progress bar
        
        Returns:
            List of GeocodeResult in same order as input
        """
        if not addresses:
            logger.warning("Empty address list")
            return []
        
        logger.info(f"Starting batch geocoding: {len(addresses)} addresses")
        
        results: list[GeocodeResult] = []
        
        iterator = tqdm(addresses, desc="Geocoding") if show_progress else addresses
        
        with self.tgos_client:  # Use context manager to reuse HTTP connection
            for address in iterator:
                result = self.geocode(address)
                results.append(result)
        
        success_count = sum(1 for r in results if r.status == TransformStatus.SUCCESS)
        logger.info(f"Batch geocoding complete: {success_count}/{len(addresses)} successful")
        
        return results
    
    def transform_lonlat(
        self, 
        lon: float, 
        lat: float
    ) -> GeocodeResult:
        """
        Transform WGS84 coordinates to TWD97 (EPSG:3826).
        
        Args:
            lon: WGS84 longitude
            lat: WGS84 latitude
        
        Returns:
            GeocodeResult containing TWD97 coordinates and metadata
        """
        try:
            # Validate input range
            if not (-180 <= lon <= 180):
                return GeocodeResult(
                    input_lon=lon,
                    input_lat=lat,
                    status=TransformStatus.INVALID,
                    error_message=f"Longitude {lon} out of valid range [-180, 180]"
                )
            
            if not (-90 <= lat <= 90):
                return GeocodeResult(
                    input_lon=lon,
                    input_lat=lat,
                    status=TransformStatus.INVALID,
                    error_message=f"Latitude {lat} out of valid range [-90, 90]"
                )
            
            # Convert coordinates
            x, y = self.transformer.wgs84_to_twd97(lon, lat, validate=False)
            
            # Check if within Taiwan bounds
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
                confidence=1.0,  # Coordinate transformation is precise
                source="PYPROJ",
                error_message=None if in_bounds else "Coordinates outside Taiwan mainland bounds"
            )
        
        except Exception as e:
            logger.error(f"Coordinate transformation failed ({lon}, {lat}): {e}")
            return GeocodeResult(
                input_lon=lon,
                input_lat=lat,
                status=TransformStatus.FAILED,
                error_message=f"Transformation failed: {e}"
            )
    
    def batch_transform_lonlat(
        self,
        coords: list[tuple[float, float]],
        show_progress: bool = True
    ) -> list[GeocodeResult]:
        """
        Batch transform WGS84 coordinates to TWD97.
        
        Args:
            coords: List of coordinate tuples [(lon, lat), ...]
            show_progress: Whether to show progress bar
        
        Returns:
            List of GeocodeResult in same order as input
        """
        if not coords:
            logger.warning("Empty coordinate list")
            return []
        
        logger.info(f"Starting batch coordinate transformation: {len(coords)} coordinates")
        
        results: list[GeocodeResult] = []
        
        iterator = tqdm(coords, desc="Transforming") if show_progress else coords
        
        for lon, lat in iterator:
            result = self.transform_lonlat(lon, lat)
            results.append(result)
        
        success_count = sum(1 for r in results if r.status == TransformStatus.SUCCESS)
        logger.info(f"Batch transformation complete: {success_count}/{len(coords)} successful")
        
        return results
    
    def batch_geocode_to_dataframe(
        self,
        addresses: list[str],
        show_progress: bool = True
    ) -> pd.DataFrame:
        """
        Batch geocode addresses and return as pandas DataFrame.
        
        Args:
            addresses: List of addresses
            show_progress: Whether to show progress bar
        
        Returns:
            DataFrame containing all result fields
        """
        results = self.batch_geocode(addresses, show_progress=show_progress)
        return pd.DataFrame([r.to_dict() for r in results])
    
    def batch_transform_lonlat_to_dataframe(
        self,
        coords: list[tuple[float, float]],
        show_progress: bool = True
    ) -> pd.DataFrame:
        """
        Batch transform coordinates and return as pandas DataFrame.
        
        Args:
            coords: List of coordinate tuples [(lon, lat), ...]
            show_progress: Whether to show progress bar
        
        Returns:
            DataFrame containing all result fields
        """
        results = self.batch_transform_lonlat(coords, show_progress=show_progress)
        return pd.DataFrame([r.to_dict() for r in results])
    
    def to_geojson(
        self,
        results: list[GeocodeResult],
        filter_failed: bool = True
    ) -> dict:
        """
        Convert results to GeoJSON FeatureCollection.
        
        Args:
            results: List of GeocodeResult
            filter_failed: Whether to filter out failed results
        
        Returns:
            GeoJSON FeatureCollection dict
        """
        features = []
        
        for result in results:
            if filter_failed and result.status == TransformStatus.FAILED:
                continue
            
            try:
                feature = result.to_geojson_feature()
                features.append(feature)
            except ValueError:
                # Missing WGS84 coordinates, skip
                continue
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
