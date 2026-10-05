# TaiGeotrans

[![CI](https://github.com/KageRyo/TaiGeotrans/actions/workflows/ci.yml/badge.svg)](https://github.com/KageRyo/TaiGeotrans/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/taigeotrans?logo=pypi&logoColor=white)](https://pypi.org/project/taigeotrans/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

TaiGeotrans 是一個台灣地址與座標轉換工具，支援：

- WGS84（EPSG:4326）與 TWD97（EPSG:3826）雙向轉換
- 透過 TGOS 將台灣地址轉成座標
- 批量處理、pandas DataFrame 與 GeoJSON
- 命令列操作

範圍判斷採用近似區域，包含台灣本島、澎湖、金門與馬祖；輸出座標仍固定使用
WGS84（EPSG:4326）與 TWD97（EPSG:3826），不代表行政區界線。

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
result = tg.transform_twd97(303891.54, 2773226.67)
print(result.wgs84_lon, result.wgs84_lat)
```

### 地址定位

地址定位使用 TGOS，需要 AppID 與 APIKey。請先在 TGOS 申請這兩項資料，
再透過環境變數提供：

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

Python API 不會自動讀取 `.env`。CLI 會讀取目前工作目錄的 `.env`，可以複製
`.env.example` 作為範本；實際 key 不要提交到 Git。

### 批量處理

```python
addresses = ["嘉義縣民雄鄉中樂路55號", "臺北市信義區市府路1號"]
coords = [(120.4278, 23.5521), (121.5654, 25.0330)]

address_results = tg.batch_geocode(addresses, show_progress=False)
coordinate_results = tg.batch_transform_lonlat(coords, show_progress=False)
df = tg.batch_transform_lonlat_to_dataframe(coords, show_progress=False)
```

DataFrame 方法需要 `taigeotrans[dataframe]`。進度列使用 `tqdm`；沒有安裝時，
批量方法仍可執行，只是不顯示進度列。

## CLI

```bash
python -m pip install "taigeotrans[cli]"

taigeotrans transform 121.5654 25.0330
taigeotrans transform 121.5654 25.0330 --format json
taigeotrans geocode "臺北市信義區市府路1號"
taigeotrans batch-geocode addresses.txt -o results.csv
taigeotrans batch-transform coords.csv -o results.csv
```

`addresses.txt` 每行一個地址；`coords.csv` 需要包含 `lon,lat` 欄位。執行
`taigeotrans --help` 查看完整指令。

## 結果

每個操作都回傳 `GeocodeResult`，包含輸入值、WGS84/TWD97 座標、來源與狀態。
狀態可能是 `success`、`out_of_bounds`、`invalid` 或 `failed`。

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

CI 會測試 Python 3.11–3.13。推送 `vMAJOR.MINOR.PATCH` tag 後，release workflow
會建置套件、發佈到 PyPI，並建立 GitHub Release。

## 授權

MIT License，請參考 [LICENSE](LICENSE)。

## 維護

依賴更新、必要 CI、GitHub Actions 固定版本及發佈驗證流程，請參考
[維護規範](docs/maintenance.md)。
