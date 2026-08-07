# TaiGeotrans 快速開始

## 安裝

```bash
python -m pip install taigeotrans
```

若需要地址定位或 CLI：

```bash
python -m pip install "taigeotrans[all]"
```

## 最快上手

```python
from taigeotrans import TaiGeotrans

tg = TaiGeotrans()

wgs84 = tg.transform_lonlat(121.5654, 25.0330)
print(wgs84.twd97_x, wgs84.twd97_y, wgs84.status)

twd97 = tg.transform_twd97(wgs84.twd97_x, wgs84.twd97_y)
print(twd97.wgs84_lon, twd97.wgs84_lat, twd97.status)
```

地址定位需要 TGOS credentials：

```bash
export TGOS_APP_ID="your-app-id"
export TGOS_API_KEY="your-api-key"
```

```python
result = tg.geocode("嘉義縣民雄鄉中樂路55號")
print(result.matched_address, result.twd97_x, result.twd97_y)
```

完整的 optional dependencies、CLI、批量、DataFrame 與 release 說明請參考
[README.md](README.md)。
