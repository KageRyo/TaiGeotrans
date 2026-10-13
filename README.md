# TaiGeotrans

**English** | [繁體中文](https://github.com/KageRyo/TaiGeotrans/blob/main/README_ZH.md)

[![CI](https://github.com/KageRyo/TaiGeotrans/actions/workflows/ci.yml/badge.svg)](https://github.com/KageRyo/TaiGeotrans/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/taigeotrans?logo=pypi&logoColor=white)](https://pypi.org/project/taigeotrans/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

TaiGeotrans provides Taiwan address geocoding via TGOS and WGS84 ↔ TWD97 coordinate conversion, with a Python API and CLI.

- Convert between WGS84 (EPSG:4326) and TWD97 (EPSG:3826).
- Geocode Taiwan addresses through TGOS.
- Process batches and export pandas DataFrames or GeoJSON.
- Run conversions from the command line.

Region checks use approximate areas covering Taiwan, Penghu, Kinmen, and Matsu; they do not represent administrative boundaries. Output coordinates always use EPSG:4326 and EPSG:3826. Applying EPSG:3826 to areas such as Kinmen can produce negative X coordinates, which are valid projection results.

## Installation

For coordinate conversion:

```bash
python -m pip install taigeotrans
```

Install optional features as needed:

```bash
python -m pip install "taigeotrans[geocoding]"
python -m pip install "taigeotrans[dataframe]"
python -m pip install "taigeotrans[cli]"
```

Or install all runtime features:

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

### Address geocoding

Address geocoding requires the `geocoding` extra and a TGOS AppID/APIKey pair. Obtain these credentials from TGOS and provide them through environment variables:

```bash
export TGOS_APP_ID="your-app-id"
export TGOS_API_KEY="your-api-key"
```

Alternatively, pass them to `TaiGeotrans`:

```python
tg = TaiGeotrans(
    tgos_app_id="your-app-id",
    tgos_api_key="your-api-key",
)
result = tg.geocode("臺北市中山區松江路469巷4號")
print(result.matched_address, result.twd97_x, result.twd97_y)
```

The Python API does not automatically load `.env`. The CLI loads `.env` from the current working directory; use [.env.example](.env.example) as a template. Keep real credentials out of Git.

### Batch processing

```python
addresses = ["嘉義縣民雄鄉中樂路55號", "臺北市信義區市府路1號"]
coords = [(120.4278, 23.5521), (121.5654, 25.0330)]

address_results = tg.batch_geocode(addresses, show_progress=False)
coordinate_results = tg.batch_transform_lonlat(coords, show_progress=False)
df = tg.batch_transform_lonlat_to_dataframe(coords, show_progress=False)
```

Address batches require TGOS credentials and the `geocoding` extra. DataFrame methods require `taigeotrans[dataframe]`. Progress bars use `tqdm`, available with `taigeotrans[progress]`; batch methods still work without it, but do not display a progress bar.

### GeoJSON

```python
coords = [(120.4278, 23.5521), (121.5654, 25.0330)]
results = tg.batch_transform_lonlat(coords, show_progress=False)
geojson = tg.to_geojson(results)
print(geojson["type"])  # FeatureCollection
```

GeoJSON uses WGS84 coordinates in `[lon, lat]` order. By default, `failed` results are skipped; results without WGS84 coordinates are also skipped.

## CLI

```bash
python -m pip install "taigeotrans[cli]"

taigeotrans transform 121.5654 25.0330
taigeotrans transform 121.5654 25.0330 --format json
taigeotrans geocode "臺北市信義區市府路1號"
taigeotrans batch-geocode addresses.txt -o results.csv
taigeotrans batch-transform coords.csv -o results.csv
```

Use one address per line in `addresses.txt`; `coords.csv` must contain `lon,lat` columns. Run `taigeotrans --help` for all commands. Geocoding commands require TGOS credentials.

## Results

Single-address geocoding and coordinate conversion return a `GeocodeResult` containing input values, WGS84/TWD97 coordinates, source, and status. Status values are `success`, `out_of_bounds`, `invalid`, or `failed`.

| Methods | Return type |
|---|---|
| `geocode`, `transform_lonlat`, `transform_twd97` | `GeocodeResult` |
| `batch_geocode`, `batch_transform_lonlat` | `list[GeocodeResult]` |
| `batch_geocode_to_dataframe`, `batch_transform_lonlat_to_dataframe` | `pandas.DataFrame` |
| `to_geojson` | GeoJSON FeatureCollection dictionary |

## Development

```bash
python -m pip install -e ".[dev,all]"
python -m pytest
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
python -m build
python -m twine check dist/*
```

CI tests Python 3.11–3.13. Pushing a `TaiGeotrans-v.X.Y.Z` tag triggers the release workflow to build distributions, publish to PyPI, and create a GitHub Release. See [CONTRIBUTING.md](CONTRIBUTING.md) for release prerequisites.

## Documentation

- [Quick start (Traditional Chinese)](QUICKSTART.md)
- [Development notes (Traditional Chinese)](DEVELOPMENT.md)
- [Contributing (English)](CONTRIBUTING.md)
- [Security policy (English)](SECURITY.md)
- [Privacy and data handling (English)](PRIVACY.md)

## License

MIT License. See [LICENSE](LICENSE).

## Maintenance

See the [maintenance guide (Traditional Chinese)](docs/maintenance.md) for dependency updates, required CI checks, pinned GitHub Actions, and release verification.
