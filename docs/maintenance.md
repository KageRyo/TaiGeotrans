# 維護規範

Dependabot 每週分組提出 Python 與 GitHub Actions 更新，並限制同時開啟的 PR 數量。
合併前檢查行為差異與必要 CI；不要求人工 reviewer，也不啟用自動合併。
外部 Actions 固定完整 commit SHA，更新時一併修改版本註解。

`main` 應禁止 force push 與刪除，並要求 PR 和 `test (3.11)`、`test (3.12)`、
`test (3.13)` 通過。必要檢查不使用 workflow 層級的 PR 路徑過濾；修改 job 名稱時
也必須更新 repository ruleset。

## 可重現的依賴與發佈

提交 `uv.lock`，CI 使用固定版本 uv 和 `uv sync --locked --all-extras`。
鎖定所有 extras，包括 development 的 setuptools 建置後端；使用
`python -m build --no-isolation` 避免建置時再次解析後端依賴。
一般使用者仍可透過 pip 安裝，公開依賴範圍與 optional extras 維持相容。

```bash
uv sync --locked --all-extras
uv run --locked --all-extras python -m pytest
uv run --locked --all-extras python -m ruff check src tests
uv run --locked --all-extras python -m ruff format --check src tests
uv run --locked --all-extras python -m mypy src
uv run --locked --all-extras python -m build --no-isolation
uv run --locked --all-extras python -m twine check dist/*
```

CI 在 Python 3.11–3.13 檢查測試、lint、typing、建置與 metadata，並在獨立環境中
安裝 wheel 的所有 runtime extras，驗證座標轉換與 CLI。此 smoke install 依 wheel
metadata 解析消費者依賴，用來檢查發布套件的相容性；它不代表逐位元可重現的產物。
更新依賴時執行 `uv lock --upgrade`，檢閱 lock 差異，再跑上述驗證。

release tag 必須與 `pyproject.toml` 版本一致。PyPI Trusted Publishing 的環境名稱
維持 `release`；不覆寫已發佈版本或歷史 release assets。發布前需驗證 metadata、
wheel 安裝及 CLI。版本化的跨專案依賴另行明確更新，先驗證相容性再採用。

## TAG-Twin 使用邊界

TaiGeotrans 與 Platform `offline/pipelines/spatial/coord_utils.py` 都使用 pyproj、
EPSG:4326 ↔ EPSG:3826 和 `always_xy=True`。這是座標轉換的重複實作候選，
未來可用離線 fixture 與 parity test 比較結果，再由 Platform adapter 採用固定版本。

TaiGeotrans 的區域矩形只用於結果分類，不代表行政邊界、觀測支撐或資料精度。
Platform 的 20 m grid、資料庫 cell ID、空間索引、polygon 操作、地址候選確認與
geocoding 回應 provenance 屬於領域流程，不能直接以通用套件取代。
TGOS 的 optional extras、credentials 與回應語意保持各自契約。
