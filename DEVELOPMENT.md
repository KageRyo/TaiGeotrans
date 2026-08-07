# TaiGeotrans 開發紀錄

## 專案定位

- 名稱：TaiGeotrans
- 型態：Python 套件
- 用途：台灣地址與座標轉換
- 設計原則：stateless、不使用資料庫
- Python：3.11+

## 已完成內容

### 核心功能

- 地址轉換：`geocode(address)`
- 批量地址轉換：`batch_geocode(addresses)`
- 座標轉換：`transform_lonlat(lon, lat)`
- 反向座標轉換：`transform_twd97(x, y)`
- 批量座標轉換：`batch_transform_lonlat(coords)`

### 輸出格式

- `GeocodeResult`（Pydantic）
- `list[GeocodeResult]`
- `pandas.DataFrame`
- CLI 可輸出 `table`、`json`、`csv`、`geojson`

### 模組分工

- `models.py`：資料模型
- `providers/tgos.py`：TGOS QueryAddr 客戶端、認證與 retry
- `utils/projection.py`：pyproj 座標轉換
- `core.py`：主流程整合
- `cli.py`：CLI optional dependency 入口
- `_cli_app.py`：Typer 命令列實作

## 技術選型

- `pyproj`：WGS84/TWD97 轉換
- `httpx`：TGOS HTTP 請求（`geocoding` extra）
- `pydantic`：資料模型（核心依賴）
- `pandas`：批量結果整合（`dataframe` extra）
- `tqdm`：批量進度顯示（`progress` extra）
- `typer`、`rich`、`python-dotenv`：CLI（`cli` extra）

## 錯誤處理與驗證

- TGOS `AppID` 與 `APIKey` 必須成對提供，且不寫入 package
- TGOS 呼叫失敗時最多重試 3 次
- 座標輸入會先檢查合法範圍
- TWD97 結果檢查台灣本島合理範圍：
  - X `140000~350000`
  - Y `2400000~2800000`
- 所有錯誤統一回傳到 `GeocodeResult.error_message`

## 測試狀態

- 測試檔：`tests/test_transformer.py`、`tests/test_tgos.py`
- 目前包含座標轉換、批量處理、模型輸出與 TGOS HTTP contract mock
- 測試不依賴真實 TGOS credentials 或外部網路

## 專案結構

```text
TaiGeotrans/
├── pyproject.toml
├── README.md
├── QUICKSTART.md
├── src/taigeotrans/
│   ├── __init__.py
│   ├── core.py
│   ├── models.py
│   ├── cli.py
│   ├── _cli_app.py
│   ├── py.typed
│   ├── providers/
│   │   └── tgos.py
│   └── utils/
│       └── projection.py
└── tests/
    ├── test_transformer.py
    └── test_tgos.py
```

## 備註

- 專案不包含 SQLite、SQLAlchemy、PostGIS 或其他資料庫元件。
- 若要整合到後端服務，可直接把 `TaiGeotrans` 當成純函式型轉換層使用。
