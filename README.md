# TaiGeotrans

TaiGeotrans 是一個台灣地址與座標轉換工具，提供以下功能：

- 中文地址轉座標（透過 TGOS）
- WGS84（EPSG:4326）轉 TWD97（EPSG:3826）
- 單筆與批量處理
- 輸出 `list[GeocodeResult]` 或 `pandas.DataFrame`

本專案為純轉換元件，設計上不使用任何資料庫，也不做持久化儲存。

## 安裝

```bash
git clone https://github.com/KageRyo/TaiGeotrans.git
cd TaiGeotrans
pip install -e .
```

開發環境：

```bash
pip install -e ".[dev]"
```

## 使用方式

### Python API

```python
from taigeotrans import TaiGeotrans

tg = TaiGeotrans()

# 1) 地址 -> TWD97
r1 = tg.geocode("嘉義縣民雄鄉中樂路55號")
print(r1.twd97_x, r1.twd97_y, r1.status)

# 2) WGS84 -> TWD97
r2 = tg.transform_lonlat(120.4278, 23.5521)
print(r2.twd97_x, r2.twd97_y, r2.status)

# 3) 批量地址
addresses = [
    "嘉義縣民雄鄉中樂路55號",
    "台北市信義區市府路1號",
]
batch_a = tg.batch_geocode(addresses)

# 4) 批量座標
coords = [
    (120.4278, 23.5521),
    (121.5654, 25.0330),
]
batch_c = tg.batch_transform_lonlat(coords)
```

### 與 pandas 整合

```python
df1 = tg.batch_geocode_to_dataframe(addresses)
print(df1[["input_address", "twd97_x", "twd97_y", "status"]])

df2 = tg.batch_transform_lonlat_to_dataframe(coords)
print(df2[["input_lon", "input_lat", "twd97_x", "twd97_y", "status"]])
```

### CLI

單筆：

```bash
taigeotrans geocode "嘉義縣民雄鄉中樂路55號"
taigeotrans transform 120.4278 23.5521
```

批量（地址文字檔）：

```bash
taigeotrans batch-geocode addresses.txt -o geocode_result.csv
taigeotrans batch-geocode addresses.txt -o geocode_result.json --format json
```

`addresses.txt` 範例：

```text
嘉義縣民雄鄉中樂路55號
台北市信義區市府路1號
```

批量（座標 CSV）：

```bash
taigeotrans batch-transform coords.csv -o transform_result.csv
```

`coords.csv` 範例：

```csv
lon,lat
120.4278,23.5521
121.5654,25.0330
```

## GeocodeResult 欄位

| 欄位 | 說明 |
|---|---|
| `input_address` | 輸入地址 |
| `input_lon` / `input_lat` | 輸入經緯度 |
| `twd97_x` / `twd97_y` | TWD97 座標 |
| `wgs84_lon` / `wgs84_lat` | WGS84 座標 |
| `status` | `success` / `failed` / `invalid` / `out_of_bounds` |
| `confidence` | 信心值（0~1） |
| `source` | 資料來源（`TGOS` / `PYPROJ`） |
| `matched_address` | TGOS 回傳的匹配地址 |
| `error_message` | 錯誤訊息 |

## 座標範圍檢查

台灣本島 TWD97 合理範圍：

- X: `140000 ~ 350000`
- Y: `2400000 ~ 2800000`

超出範圍時會以 `out_of_bounds` 標示，不會寫入任何資料庫。

## 測試

```bash
pytest -v
pytest --cov=taigeotrans --cov-report=term-missing
```

## 注意事項

- 地址查詢使用 TGOS 公開服務，請遵守其使用規範。
- 本專案不包含資料庫或快取層。
- 轉換核心為 `pyproj`，地址精度受 TGOS 回傳品質影響。

## 授權

MIT License，請參考 `LICENSE`。