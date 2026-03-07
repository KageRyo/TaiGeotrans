"""
Data models for geocoding and transformation results.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TransformStatus(str, Enum):
    """Transformation status enumeration"""
    
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    INVALID = "invalid"
    OUT_OF_BOUNDS = "out_of_bounds"


class GeocodeResult(BaseModel):
    """Geocoding and transformation result model"""
    
    # Input data
    input_address: Optional[str] = Field(None, description="輸入地址")
    input_lon: Optional[float] = Field(None, description="輸入經度 (WGS84)")
    input_lat: Optional[float] = Field(None, description="輸入緯度 (WGS84)")
    
    # TWD97 座標 (EPSG:3826)
    twd97_x: Optional[float] = Field(None, description="TWD97 X座標")
    twd97_y: Optional[float] = Field(None, description="TWD97 Y座標")
    
    # WGS84 coordinates (EPSG:4326)
    wgs84_lon: Optional[float] = Field(None, description="WGS84 經度")
    wgs84_lat: Optional[float] = Field(None, description="WGS84 緯度")
    
    # Metadata
    status: TransformStatus = Field(..., description="轉換狀態")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="信心度 (0-1)")
    source: Optional[str] = Field(None, description="資料來源 (TGOS/PYPROJ)")
    matched_address: Optional[str] = Field(None, description="匹配到的標準化地址")
    error_message: Optional[str] = Field(None, description="錯誤訊息")
    
    @field_validator("twd97_x")
    @classmethod
    def validate_twd97_x(cls, v: Optional[float]) -> Optional[float]:
        """Validate TWD97 X coordinate range for Taiwan mainland"""
        return v
    
    @field_validator("twd97_y")
    @classmethod
    def validate_twd97_y(cls, v: Optional[float]) -> Optional[float]:
        """Validate TWD97 Y coordinate range for Taiwan mainland"""
        return v
    
    def is_in_taiwan_bounds(self) -> bool:
        """Check if coordinates are within Taiwan mainland bounds"""
        if self.twd97_x is None or self.twd97_y is None:
            return False
        return (
            140000 <= self.twd97_x <= 350000
            and 2400000 <= self.twd97_y <= 2800000
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary format"""
        return self.model_dump(exclude_none=True)
    
    def to_geojson_feature(self) -> dict:
        """Convert to GeoJSON Feature format using WGS84 coordinates"""
        if self.wgs84_lon is None or self.wgs84_lat is None:
            raise ValueError("Missing WGS84 coordinates, cannot generate GeoJSON")
        
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.wgs84_lon, self.wgs84_lat]
            },
            "properties": {
                "twd97_x": self.twd97_x,
                "twd97_y": self.twd97_y,
                "status": self.status.value,
                "confidence": self.confidence,
                "source": self.source,
                "matched_address": self.matched_address,
                "input_address": self.input_address,
            }
        }


class BatchGeocodeRequest(BaseModel):
    """Batch geocoding request model"""
    
    addresses: list[str] = Field(..., min_length=1, description="地址列表")
    
    @field_validator("addresses")
    @classmethod
    def validate_addresses(cls, v: list[str]) -> list[str]:
        """Validate address list"""
        if not v:
            raise ValueError("Address list cannot be empty")
        return [addr.strip() for addr in v if addr.strip()]


class BatchTransformRequest(BaseModel):
    """Batch coordinate transformation request model"""
    
    coordinates: list[tuple[float, float]] = Field(
        ..., min_length=1, description="座標列表 (lon, lat)"
    )
    
    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v: list[tuple[float, float]]) -> list[tuple[float, float]]:
        """Validate coordinate list"""
        if not v:
            raise ValueError("Coordinate list cannot be empty")
        
        for lon, lat in v:
            if not (-180 <= lon <= 180):
                raise ValueError(f"Longitude {lon} out of valid range [-180, 180]")
            if not (-90 <= lat <= 90):
                raise ValueError(f"Latitude {lat} out of valid range [-90, 90]")
        
        return v
