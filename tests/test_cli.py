"""Tests for the optional command-line interface."""

import csv
import json
import tomllib
from pathlib import Path

from typer.testing import CliRunner

from taigeotrans import __version__, _cli_app
from taigeotrans.models import GeocodeResult, TransformStatus

runner = CliRunner()
PROJECT_FILE = Path(__file__).parents[1] / "pyproject.toml"


def _success_result(address: str = "臺北市信義區市府路1號") -> GeocodeResult:
    return GeocodeResult(
        input_address=address,
        input_lon=121.5654,
        input_lat=25.0330,
        twd97_x=307056.82,
        twd97_y=2769551.84,
        wgs84_lon=121.5654,
        wgs84_lat=25.0330,
        status=TransformStatus.SUCCESS,
        confidence=1.0,
        source="TEST",
    )


def test_version_command() -> None:
    result = runner.invoke(_cli_app.app, ["version"])

    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip() == f"TaiGeotrans version {__version__}"


def test_runtime_version_matches_project_metadata() -> None:
    project = tomllib.loads(PROJECT_FILE.read_text(encoding="utf-8"))

    assert __version__ == project["project"]["version"]


def test_transform_json() -> None:
    result = runner.invoke(
        _cli_app.app,
        ["transform", "121.5654", "25.0330", "--format", "json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert payload["source"] == "PYPROJ"
    assert payload["twd97_x"] > 300000


def test_batch_transform_writes_csv(tmp_path: Path) -> None:
    input_file = tmp_path / "coords.csv"
    output_file = tmp_path / "results.csv"
    input_file.write_text("lon,lat\n121.5654,25.0330\n120.3014,22.6273\n", encoding="utf-8")

    result = runner.invoke(
        _cli_app.app,
        [
            "batch-transform",
            str(input_file),
            "--output",
            str(output_file),
            "--format",
            "csv",
        ],
    )

    assert result.exit_code == 0, result.stdout
    with output_file.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 2
    assert rows[0]["status"] == "success"


def test_geocode_json_uses_configured_client(monkeypatch) -> None:
    class FakeTaiGeotrans:
        def geocode(self, address: str) -> GeocodeResult:
            return _success_result(address)

    monkeypatch.setattr(_cli_app, "TaiGeotrans", FakeTaiGeotrans)
    result = runner.invoke(
        _cli_app.app,
        ["geocode", "臺北市信義區市府路1號", "--format", "json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["input_address"] == "臺北市信義區市府路1號"
    assert payload["status"] == "success"


def test_batch_geocode_writes_geojson(tmp_path: Path, monkeypatch) -> None:
    class FakeTaiGeotrans:
        def batch_geocode(
            self,
            addresses: list[str],
            show_progress: bool = True,
        ) -> list[GeocodeResult]:
            return [_success_result(address) for address in addresses]

        def to_geojson(
            self,
            results: list[GeocodeResult],
            filter_failed: bool = True,
        ) -> dict[str, object]:
            return {
                "type": "FeatureCollection",
                "features": [result.to_geojson_feature() for result in results],
            }

    monkeypatch.setattr(_cli_app, "TaiGeotrans", FakeTaiGeotrans)
    input_file = tmp_path / "addresses.txt"
    output_file = tmp_path / "results.geojson"
    input_file.write_text("臺北市信義區市府路1號\n高雄市苓雅區四維三路2號\n", encoding="utf-8")

    result = runner.invoke(
        _cli_app.app,
        [
            "batch-geocode",
            str(input_file),
            "--output",
            str(output_file),
            "--format",
            "geojson",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 2
