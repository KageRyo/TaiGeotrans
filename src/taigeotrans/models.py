"""Data models for geocoding and coordinate transformation results."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class TransformStatus(StrEnum):
    """Transformation status enumeration"""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    INVALID = "invalid"
    OUT_OF_BOUNDS = "out_of_bounds"


class GeocodeResult(BaseModel):
    """Geocoding and transformation result model"""

    # Input data
    input_address: str | None = None
    input_lon: float | None = None
    input_lat: float | None = None
    input_twd97_x: float | None = None
    input_twd97_y: float | None = None

    # TWD97 座標 (EPSG:3826)
    twd97_x: float | None = None
    twd97_y: float | None = None

    # WGS84 coordinates (EPSG:4326)
    wgs84_lon: float | None = None
    wgs84_lat: float | None = None

    # Metadata
    status: TransformStatus = Field(..., description="轉換狀態")
    confidence: float | None = None
    source: str | None = None
    matched_address: str | None = None
    error_message: str | None = None

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float | None:
        """Validate the optional confidence score."""
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return v

    def is_in_taiwan_bounds(self) -> bool:
        """Check if coordinates are within Taiwan mainland bounds"""
        if self.twd97_x is None or self.twd97_y is None:
            return False
        return 140000 <= self.twd97_x <= 350000 and 2400000 <= self.twd97_y <= 2800000

    def to_dict(self) -> dict:
        """Convert to dictionary format"""
        return self.model_dump(mode="json", exclude_none=True)

    def to_geojson_feature(self) -> dict:
        """Convert to GeoJSON Feature format using WGS84 coordinates"""
        if self.wgs84_lon is None or self.wgs84_lat is None:
            raise ValueError("Missing WGS84 coordinates, cannot generate GeoJSON")

        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [self.wgs84_lon, self.wgs84_lat]},
            "properties": {
                "twd97_x": self.twd97_x,
                "twd97_y": self.twd97_y,
                "status": self.status.value,
                "confidence": self.confidence,
                "source": self.source,
                "matched_address": self.matched_address,
                "input_address": self.input_address,
            },
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
