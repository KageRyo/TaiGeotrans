# TaiGeotrans

[English](https://github.com/KageRyo/TaiGeotrans/blob/main/README.md) | **繁體中文**

[![CI](https://github.com/KageRyo/TaiGeotrans/actions/workflows/ci.yml/badge.svg)](https://github.com/KageRyo/TaiGeotrans/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/taigeotrans?logo=pypi&logoColor=white)](https://pypi.org/project/taigeotrans/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

TaiGeotrans 是一個台灣地址與座標轉換工具，支援：

- WGS84（EPSG:4326）與 TWD97（EPSG:3826）雙向轉換
- 透過 TGOS 將台灣地址轉成座標
- 批量處理、pandas DataFrame 與 GeoJSON
- 命令列操作

範圍判斷採用近似區域，包含台灣本島、澎湖、金門與馬祖；輸出座標仍固定使用WGS84（EPSG:4326）與 TWD97（EPSG:3826），不代表行政區界線。EPSG:3826 用於金門等區域時可能產生負 X 值，仍屬有效投影結果。

## 安裝

只使用座標轉換時：

```bash
python -m pip install taigeotrans
```

需要地址定位、DataFrame 或 CLI 時，再安裝對應功能：

```bash
python -m pip install "taigeotrans[geocoding]"
python -m pip install "taigeotrans[dataframe]"
python -m pip install "taigeotrans[cli]"
```

也可以一次安裝全部功能：

```bash
python -m pip install "taigeotrans[all]"
```

## Python API

```python
from taigeotrans import TaiGeotrans

tg = TaiGeotrans()

# WGS84 -> TWD97
result = tg.transform_lonlat(121.5654, 25.0330)
print(result.twd97_x, result.twd97_y)

# TWD97 -> WGS84
result = tg.transform_twd97(result.twd97_x, result.twd97_y)
print(result.wgs84_lon, result.wgs84_lat)
```

### 地址定位

地址定位需要 `geocoding` extra，使用 TGOS，需要 AppID 與 APIKey。請先在 TGOS 申請這兩項資料，再透過環境變數提供：

```bash
export TGOS_APP_ID="your-app-id"
export TGOS_API_KEY="your-api-key"
```

或直接傳給 `TaiGeotrans`：

```python
tg = TaiGeotrans(
    tgos_app_id="your-app-id",
    tgos_api_key="your-api-key",
)
result = tg.geocode("臺北市中山區松江路469巷4號")
print(result.matched_address, result.twd97_x, result.twd97_y)
```

Python API 不會自動讀取 `.env`。CLI 會讀取目前工作目錄的 `.env`，可以複製`.env.example` 作為範本；實際 key 不要提交到 Git。

### 批量處理

```python
addresses = ["嘉義縣民雄鄉中樂路55號", "臺北市信義區市府路1號"]
coords = [(120.4278, 23.5521), (121.5654, 25.0330)]

address_results = tg.batch_geocode(addresses, show_progress=False)
coordinate_results = tg.batch_transform_lonlat(coords, show_progress=False)
df = tg.batch_transform_lonlat_to_dataframe(coords, show_progress=False)
```

批量地址定位需要 TGOS 憑證與 `geocoding` extra。DataFrame 方法需要 `taigeotrans[dataframe]`。進度列使用 `tqdm`，可透過 `taigeotrans[progress]` 安裝；沒有安裝時，批量方法仍可執行，只是不顯示進度列。

### GeoJSON

```python
coords = [(120.4278, 23.5521), (121.5654, 25.0330)]
results = tg.batch_transform_lonlat(coords, show_progress=False)
geojson = tg.to_geojson(results)
print(geojson["type"])  # FeatureCollection
```

GeoJSON 使用 WGS84 經緯度，順序為 `[lon, lat]`。預設略過 `failed` 結果；缺少 WGS84 座標的結果也會略過。

## CLI

```bash
python -m pip install "taigeotrans[cli]"

taigeotrans transform 121.5654 25.0330
taigeotrans transform 121.5654 25.0330 --format json
taigeotrans geocode "臺北市信義區市府路1號"
taigeotrans batch-geocode addresses.txt -o results.csv
taigeotrans batch-transform coords.csv -o results.csv
```

`addresses.txt` 每行一個地址；`coords.csv` 需要包含 `lon,lat` 欄位。執行`taigeotrans --help` 查看完整指令。

## 結果

單筆地址定位與座標轉換回傳 `GeocodeResult`，包含輸入值、WGS84/TWD97 座標、來源與狀態。狀態可能是 `success`、`out_of_bounds`、`invalid` 或 `failed`。

| 方法 | 回傳型別 |
|---|---|
| `geocode`、`transform_lonlat`、`transform_twd97` | `GeocodeResult` |
| `batch_geocode`、`batch_transform_lonlat` | `list[GeocodeResult]` |
| `batch_geocode_to_dataframe`、`batch_transform_lonlat_to_dataframe` | `pandas.DataFrame` |
| `to_geojson` | GeoJSON FeatureCollection 字典 |

## 開發

```bash
python -m pip install -e ".[dev,all]"
python -m pytest
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
python -m build
python -m twine check dist/*
```

CI 會測試 Python 3.11–3.13。推送 `TaiGeotrans-v.X.Y.Z` tag 後，release workflow 會建置套件、發佈到 PyPI，並建立 GitHub Release。

## 文件

- [快速開始（繁體中文）](QUICKSTART.md)
- [開發紀錄（繁體中文）](DEVELOPMENT.md)
- [貢獻指南（英文）](CONTRIBUTING.md)
- [安全政策（英文）](SECURITY.md)
- [隱私權與資料處理說明（繁體中文）](PRIVACY_ZH.md)

## 授權

MIT License，請參考 [LICENSE](LICENSE)。

## 維護

依賴更新、必要 CI、GitHub Actions 固定版本及發佈驗證流程，請參考
[維護規範](docs/maintenance.md)。

## 可驗證的地址比對（0.2.0）

`geocode()` 與 `batch_geocode()` 現在只有在確認唯一、地址層級候選後才回傳成功座標。呼叫形式與原有結果狀態列舉保留，但 0.1.x 曾接受的模糊座標不再視為成功。資料不足、輸入衝突、缺少供應者比對證據、多筆通過驗證、候選遭截斷或僅有粗尺度定位，都不會輸出頂層座標。純座標轉換行為不變。

```python
from taigeotrans import AddressContext, TaiGeotrans, complete_address

context = AddressContext(county="嘉義縣")  # 只能提供有獨立證據支持的行政區資訊。
prepared = complete_address("民雄鄉大學路一段138號", context)
assert prepared.original == "民雄鄉大學路一段138號"
assert prepared.query == "嘉義縣民雄鄉大學路1段138號"
result = TaiGeotrans().geocode(prepared.original, context=context, candidate_limit=9)
```

以上字串是語法變體示例，不是已驗證的地址登錄或實測定位準確度。缺少縣市的道路門牌不會被擅自補成專案所在地；可信脈絡只能補上缺少的縣市、鄉鎮市區，衝突會在連線前拒絕。呼叫者必須保存脈絡的來源與證據。

離線解析會正規化 NFKC、空白、台／臺、中文／阿拉伯數字路段，以及 `138之1號`／`138號之1`，並保留道路、巷弄、門牌附號及輸入中的村里、鄰、樓層限制。供應者額外附上的村里、鄰可不在查詢中；輸入已提供的項目必須得到確認。不支援或有歧義的語法保留為未解析內容，不會猜測。無道路街名的鄉村地址、不支援的樓層／細分及不規範數字可能無法解析；此政策優先避免錯誤定位。

TGOS 使用 EPSG:4326、只做完全比對、鎖定已提供的地址元件，候選上限可設為 2–9，預設 9。達到上限或回報總筆數較多時保留歧義，不宣稱唯一。參數依照[官方 QueryAddr 說明](https://addr.tgos.tw/addrws/v30/QueryAddr.asmx?op=QueryAddr)，結果仍須通過本地元件比對。舊版低階 `TGOSClient.geocode_address()` tuple 仍是原始供應者查詢，不能表示驗證來源，且不再從多筆候選直接取第一筆；地址驗證應使用高階 API。

結果新增正規化地址、完成後查詢、補齊欄位、`match_status`（`verified_exact`／`fuzzy`／`ambiguous`／`insufficient`／`unresolved`）、驗證理由、空間精度、候選數與說明，以及供應者 canonical JSON 的 SHA-256。`input_address` 保留原始輸入。地址層級驗證不保證公尺級準確度，也不代表可以直接映射任意網格；`confidence=1.0` 表示供應者完全比對分類，並非校準過的位置可信度。消費端仍須維持自身的精度、來源與網格驗證。批次請求模型現在拒絕空白項目，不會靜默刪除它們。
