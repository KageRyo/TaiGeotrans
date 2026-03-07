"""
TaiGeotrans - Taiwan Geospatial Transformer
台灣地址與座標轉換工具

基於內政地理資訊圖資雲整合服務平台 (TGOS) 實現的輕量級地址、
經緯度 (WGS84:EPSG:4326) 及 TWD97 (EPSG:3826) 轉換器。
"""

from taigeotrans.core import TaiGeotrans
from taigeotrans.models import GeocodeResult, TransformStatus

__version__ = "0.1.0"
__all__ = ["TaiGeotrans", "GeocodeResult", "TransformStatus"]
