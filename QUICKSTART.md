# TaiGeotrans 快速開始

## 安裝

```bash
git clone https://github.com/KageRyo/TaiGeotrans.git
cd TaiGeotrans
pip install -e .
```

## 最快上手

### Python

```python
from taigeotrans import TaiGeotrans

tg = TaiGeotrans()

# 座標轉換：WGS84 -> TWD97
r1 = tg.transform_lonlat(120.4278, 23.5521)
print(r1.twd97_x, r1.twd97_y, r1.status)

# 地址轉換：地址 -> TWD97
r2 = tg.geocode("嘉義縣民雄鄉中樂路55號")
print(r2.twd97_x, r2.twd97_y, r2.status)
```

### CLI

```bash
taigeotrans transform 120.4278 23.5521
taigeotrans geocode "嘉義縣民雄鄉中樂路55號"
```

## 批量處理

```bash
taigeotrans batch-geocode addresses.txt -o geocode_result.csv
taigeotrans batch-transform coords.csv -o transform_result.csv
```

`addresses.txt`：

```text
嘉義縣民雄鄉中樂路55號
台北市信義區市府路1號
```

`coords.csv`：

```csv
lon,lat
120.4278,23.5521
121.5654,25.0330
```

## pandas 整合

```python
addresses = ["嘉義縣民雄鄉中樂路55號", "台北市信義區市府路1號"]
coords = [(120.4278, 23.5521), (121.5654, 25.0330)]

df_a = tg.batch_geocode_to_dataframe(addresses)
df_c = tg.batch_transform_lonlat_to_dataframe(coords)

print(df_a[["input_address", "twd97_x", "twd97_y", "status"]])
print(df_c[["input_lon", "input_lat", "twd97_x", "twd97_y", "status"]])
```

## 測試

```bash
pip install -e ".[dev]"
pytest -v
```

## 補充

- 本專案為 stateless 轉換工具，不使用資料庫。
- 地址查詢仰賴 TGOS 服務，結果品質取決於 TGOS 回傳內容。
- 台灣本島範圍檢查：X `140000~350000`、Y `2400000~2800000`。
