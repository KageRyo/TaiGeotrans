"""Typer implementation for the optional TaiGeotrans CLI extra."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from taigeotrans.core import TaiGeotrans
from taigeotrans.models import GeocodeResult, TransformStatus

app = typer.Typer(
    name="taigeotrans",
    help="TaiGeotrans - Taiwan address and coordinate transformation tool",
    add_completion=False,
)
console = Console()


@app.command()
def geocode(
    address: str = typer.Argument(..., help="Taiwan address to geocode"),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json, csv",
    ),
) -> None:
    """Geocode a Taiwan address to TWD97 coordinates."""
    result = TaiGeotrans().geocode(address)
    _print_single_result(result, output_format)


@app.command()
def batch_geocode(
    input_file: Path = typer.Argument(..., help="Input file with one address per line"),
    output_file: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path",
    ),
    output_format: str = typer.Option(
        "csv",
        "--format",
        "-f",
        help="Output format: csv, json, geojson",
    ),
) -> None:
    """Geocode multiple Taiwan addresses."""
    if not input_file.exists():
        raise typer.BadParameter(f"File not found: {input_file}")

    addresses = [
        line.strip() for line in input_file.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if not addresses:
        console.print("[yellow]No valid addresses in file[/yellow]")
        return

    converter = TaiGeotrans()
    results = converter.batch_geocode(addresses, show_progress=True)
    _save_batch_results(results, output_file, output_format, converter)


@app.command()
def transform(
    lon: float = typer.Argument(..., help="WGS84 longitude"),
    lat: float = typer.Argument(..., help="WGS84 latitude"),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json, csv",
    ),
) -> None:
    """Transform WGS84 coordinates to TWD97."""
    result = TaiGeotrans().transform_lonlat(lon, lat)
    _print_single_result(result, output_format)


@app.command()
def batch_transform(
    input_file: Path = typer.Argument(..., help="CSV file with lon and lat columns"),
    output_file: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path",
    ),
    output_format: str = typer.Option(
        "csv",
        "--format",
        "-f",
        help="Output format: csv, json, geojson",
    ),
) -> None:
    """Transform multiple WGS84 coordinate pairs."""
    if not input_file.exists():
        raise typer.BadParameter(f"File not found: {input_file}")

    df = pd.read_csv(input_file)
    if "lon" not in df.columns or "lat" not in df.columns:
        raise typer.BadParameter("CSV file must contain 'lon' and 'lat' columns")

    coords = [(row.lon, row.lat) for row in df.itertuples(index=False)]
    converter = TaiGeotrans()
    results = converter.batch_transform_lonlat(coords, show_progress=True)
    _save_batch_results(results, output_file, output_format, converter)


@app.command()
def version() -> None:
    """Display version information."""
    from taigeotrans import __version__

    console.print(f"TaiGeotrans version {__version__}")


def _print_single_result(result: GeocodeResult, output_format: str) -> None:
    if output_format == "json":
        console.print_json(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    elif output_format == "csv":
        frame = pd.DataFrame([result.to_dict()])
        console.print(frame.to_csv(index=False))
    elif output_format == "table":
        table = Table(title="Transformation Result")
        for key, value in result.to_dict().items():
            table.add_row(key, str(value))
        console.print(table)
        _print_status(result)
    else:
        raise typer.BadParameter(f"Unsupported output format: {output_format}")


def _print_status(result: GeocodeResult) -> None:
    if result.status == TransformStatus.SUCCESS:
        console.print("[green]Success[/green]")
    elif result.status == TransformStatus.OUT_OF_BOUNDS:
        console.print(
            "[yellow]Warning: coordinates are outside supported Taiwan-area bounds[/yellow]"
        )
    else:
        console.print(f"[red]Failed: {result.error_message}[/red]")


def _save_batch_results(
    results: list[GeocodeResult],
    output_file: Path | None,
    output_format: str,
    converter: TaiGeotrans,
) -> None:
    if output_file is None:
        for result in results[:10]:
            console.print_json(json.dumps(result.to_dict(), ensure_ascii=False))
        return

    if output_format == "json":
        output_file.write_text(
            json.dumps([result.to_dict() for result in results], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    elif output_format == "geojson":
        output_file.write_text(
            json.dumps(
                converter.to_geojson(results, filter_failed=False), ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )
    elif output_format == "csv":
        pd.DataFrame([result.to_dict() for result in results]).to_csv(
            output_file,
            index=False,
            encoding="utf-8-sig",
        )
    else:
        raise typer.BadParameter(f"Unsupported output format: {output_format}")

    console.print(f"[green]Saved to {output_file} ({output_format})[/green]")
