"""
TaiGeotrans 測試套件
"""

import pytest

from taigeotrans.core import TaiGeotrans
from taigeotrans.models import TransformStatus
from taigeotrans.utils.projection import CoordinateTransformer


class TestCoordinateTransformer:
    """Coordinate transformer tests"""

    def test_wgs84_to_twd97(self):
        """Test WGS84 to TWD97 conversion"""
        transformer = CoordinateTransformer()

        # Taipei 101 coordinates (WGS84)
        lon, lat = 121.5654, 25.0330
        x, y = transformer.wgs84_to_twd97(lon, lat)

        # Verify result is within valid range
        assert transformer.is_in_taiwan_bounds_twd97(x, y)
        assert 140000 <= x <= 350000
        assert 2400000 <= y <= 2800000

    def test_twd97_to_wgs84(self):
        """Test TWD97 to WGS84 conversion"""
        transformer = CoordinateTransformer()

        # Known TWD97 coordinates
        x, y = 300000, 2700000
        lon, lat = transformer.twd97_to_wgs84(x, y)

        # Verify result is within Taiwan bounds
        assert transformer.is_in_taiwan_bounds_wgs84(lon, lat)
        assert 119.0 <= lon <= 122.5
        assert 21.5 <= lat <= 25.5

    def test_round_trip_conversion(self):
        """Test round-trip conversion consistency"""
        transformer = CoordinateTransformer()

        # Original coordinates
        original_lon, original_lat = 121.5, 25.0

        # WGS84 -> TWD97 -> WGS84
        x, y = transformer.wgs84_to_twd97(original_lon, original_lat)
        result_lon, result_lat = transformer.twd97_to_wgs84(x, y)

        # Should be very close (allow small error)
        assert abs(result_lon - original_lon) < 0.000001
        assert abs(result_lat - original_lat) < 0.000001


class TestTaiGeotrans:
    """Main transformer tests"""

    def test_transform_lonlat_success(self):
        """Test successful coordinate transformation"""
        converter = TaiGeotrans()

        # Coordinates within Taipei area
        result = converter.transform_lonlat(121.5, 25.0)

        assert result.status == TransformStatus.SUCCESS
        assert result.twd97_x is not None
        assert result.twd97_y is not None
        assert result.wgs84_lon == 121.5
        assert result.wgs84_lat == 25.0
        assert result.confidence == 1.0
        assert result.source == "PYPROJ"

    def test_transform_lonlat_invalid_input(self):
        """Test invalid coordinate input"""
        converter = TaiGeotrans()

        # Longitude out of range
        result = converter.transform_lonlat(200.0, 25.0)
        assert result.status == TransformStatus.INVALID

        # Latitude out of range
        result = converter.transform_lonlat(121.5, 100.0)
        assert result.status == TransformStatus.INVALID

    def test_transform_twd97_success(self):
        """Test TWD97 to WGS84 through the public facade"""
        converter = TaiGeotrans()

        result = converter.transform_twd97(300000, 2700000)

        assert result.status == TransformStatus.SUCCESS
        assert result.wgs84_lon is not None
        assert result.wgs84_lat is not None
        assert result.source == "PYPROJ"

    def test_transform_lonlat_out_of_bounds(self):
        """Test coordinates outside Taiwan bounds"""
        converter = TaiGeotrans()

        # Tokyo, Japan coordinates (should be out of bounds)
        result = converter.transform_lonlat(139.6917, 35.6895)

        # Conversion executes but marked as out of bounds
        assert result.status == TransformStatus.OUT_OF_BOUNDS
        assert result.twd97_x is not None
        assert result.twd97_y is not None

    @pytest.mark.parametrize(
        ("lon", "lat"),
        [
            (119.566, 23.565),  # Penghu
            (118.32, 24.43),  # Kinmen
            (120.0, 26.15),  # Matsu
        ],
    )
    def test_outlying_islands_are_in_supported_bounds(self, lon, lat):
        """Test that supported outlying islands are not marked out of bounds."""
        converter = TaiGeotrans()

        result = converter.transform_lonlat(lon, lat)

        assert result.status == TransformStatus.SUCCESS
        assert result.is_in_taiwan_bounds()

    def test_batch_transform_lonlat(self):
        """Test batch coordinate transformation"""
        converter = TaiGeotrans()

        coords = [
            (121.5, 25.0),  # Taipei
            (120.3, 22.6),  # Kaohsiung
            (121.0, 24.8),  # Hsinchu
        ]

        results = converter.batch_transform_lonlat(coords, show_progress=False)

        assert len(results) == 3
        assert all(
            r.status in [TransformStatus.SUCCESS, TransformStatus.OUT_OF_BOUNDS] for r in results
        )
        assert all(r.twd97_x is not None for r in results)

    def test_batch_transform_to_dataframe(self):
        """Test batch transformation to DataFrame output"""
        converter = TaiGeotrans()

        coords = [(121.5, 25.0), (120.3, 22.6)]
        df = converter.batch_transform_lonlat_to_dataframe(coords, show_progress=False)

        assert len(df) == 2
        assert "twd97_x" in df.columns
        assert "twd97_y" in df.columns
        assert "status" in df.columns

    def test_geocode_invalid_address(self):
        """Test invalid address input"""
        converter = TaiGeotrans()

        # Empty string
        result = converter.geocode("")
        assert result.status == TransformStatus.INVALID

        # Whitespace only
        result = converter.geocode("   ")
        assert result.status == TransformStatus.INVALID

    def test_to_geojson(self):
        """Test GeoJSON output"""
        converter = TaiGeotrans()

        # Create test results
        results = [
            converter.transform_lonlat(121.5, 25.0),
            converter.transform_lonlat(120.3, 22.6),
        ]

        geojson = converter.to_geojson(results)

        assert geojson["type"] == "FeatureCollection"
        assert len(geojson["features"]) == 2
        assert all(f["type"] == "Feature" for f in geojson["features"])
        assert all(f["geometry"]["type"] == "Point" for f in geojson["features"])


class TestRealWorldAddresses:
    """Real-world address and coordinate tests"""

    def test_minxiong_township_office_coordinates(self):
        """Test Minxiong Township Office coordinates (Chiayi County)"""
        converter = TaiGeotrans()

        # Minxiong Township Office (嘉義縣民雄鄉公所)
        # Approximate coordinates: 120.4278, 23.5521
        lon, lat = 120.4278, 23.5521
        result = converter.transform_lonlat(lon, lat)

        assert result.status == TransformStatus.SUCCESS
        assert result.twd97_x is not None
        assert result.twd97_y is not None
        assert result.source == "PYPROJ"
        assert result.confidence == 1.0

        # Verify coordinates are in Taiwan bounds
        assert result.is_in_taiwan_bounds()

    def test_multiple_taiwan_cities(self):
        """Test coordinates from different Taiwan cities"""
        converter = TaiGeotrans()

        # Test various cities across Taiwan
        test_coords = [
            (121.5654, 25.0330),  # Taipei City Hall
            (120.4278, 23.5521),  # Minxiong Township Office
            (120.3014, 22.6273),  # Kaohsiung
            (121.0178, 24.8066),  # Hsinchu
            (120.6736, 24.1477),  # Taichung
        ]

        results = converter.batch_transform_lonlat(test_coords, show_progress=False)

        assert len(results) == 5
        for result in results:
            assert result.status == TransformStatus.SUCCESS
            assert result.is_in_taiwan_bounds()
            assert result.twd97_x is not None
            assert result.twd97_y is not None


class TestModels:
    """Data model tests"""

    def test_geocode_result_to_dict(self):
        """Test GeocodeResult to dict conversion"""
        from taigeotrans.models import GeocodeResult

        result = GeocodeResult(
            input_address="Test Address",
            twd97_x=300000,
            twd97_y=2700000,
            wgs84_lon=121.5,
            wgs84_lat=25.0,
            status=TransformStatus.SUCCESS,
            confidence=0.9,
            source="TGOS",
        )

        data = result.to_dict()
        assert data["input_address"] == "Test Address"
        assert data["twd97_x"] == 300000
        assert data["status"] == "success"

    def test_geocode_result_is_in_taiwan_bounds(self):
        """Test Taiwan bounds checking"""
        from taigeotrans.models import GeocodeResult

        # Within bounds
        result = GeocodeResult(twd97_x=300000, twd97_y=2700000, status=TransformStatus.SUCCESS)
        assert result.is_in_taiwan_bounds() is True

        # Out of bounds
        result = GeocodeResult(
            twd97_x=100000,  # Too small
            twd97_y=2700000,
            status=TransformStatus.SUCCESS,
        )
        assert result.is_in_taiwan_bounds() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
