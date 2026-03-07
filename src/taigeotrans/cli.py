"""
Command-line interface using Typer.
"""

import json
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from taigeotrans.core import TaiGeotrans
from taigeotrans.models import TransformStatus

app = typer.Typer(
    name="taigeotrans",
    help="TaiGeotrans - Taiwan address and coordinate transformation tool",
    add_completion=False
)
console = Console()


@app.command()
def geocode(
    address: str = typer.Argument(..., help="Taiwan address to geocode"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json, csv"),
) -> None:
    """
    Geocode Taiwan address to TWD97 coordinates.
    
    Examples:
        taigeotrans geocode "台北市信義區市府路1號"
        taigeotrans geocode "Taipei 101" --format json
    """
    converter = TaiGeotrans()
    result = converter.geocode(address)
    
    _print_single_result(result, output_format)


@app.command()
def batch_geocode(
    input_file: Path = typer.Argument(..., help="Input file with addresses (one per line)"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    output_format: str = typer.Option("csv", "--format", "-f", help="Output format: csv, json, geojson"),
) -> None:
    """
    Batch geocode multiple addresses.
    
    Examples:
        taigeotrans batch-geocode addresses.txt -o results.csv
        taigeotrans batch-geocode addresses.txt -o results.json --format json
    """
    if not input_file.exists():
        console.print(f"[red]Error: File not found: {input_file}[/red]")
        raise typer.Exit(code=1)
    
    # Read address list
    addresses = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                addresses.append(line)
    
    if not addresses:
        console.print("[yellow]Warning: No valid addresses in file[/yellow]")
        raise typer.Exit(code=0)
    
    console.print(f"[cyan]Read {len(addresses)} addresses[/cyan]")
    
    # Execute batch geocoding
    converter = TaiGeotrans()
    results = converter.batch_geocode(addresses, show_progress=True)
    
    # Output results
    _save_batch_results(results, output_file, output_format, converter)


@app.command()
def transform(
    lon: float = typer.Argument(..., help="WGS84 longitude"),
    lat: float = typer.Argument(..., help="WGS84 latitude"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json, csv"),
) -> None:
    """
    Transform WGS84 coordinates to TWD97.
    
    Examples:
        taigeotrans transform 121.5654 25.0330
        taigeotrans transform 121.5654 25.0330 --format json
    """
    converter = TaiGeotrans()
    result = converter.transform_lonlat(lon, lat)
    
    _print_single_result(result, output_format)


@app.command()
def batch_transform(
    input_file: Path = typer.Argument(..., help="CSV file with coordinates (columns: lon, lat)"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    output_format: str = typer.Option("csv", "--format", "-f", help="Output format: csv, json, geojson"),
) -> None:
    """
    Batch transform WGS84 coordinates to TWD97.
    
    Input CSV file must contain 'lon' and 'lat' columns.
    
    Examples:
        taigeotrans batch-transform coords.csv -o results.csv
        taigeotrans batch-transform coords.csv -o results.json --format json
    """
    if not input_file.exists():
        console.print(f"[red]Error: File not found: {input_file}[/red]")
        raise typer.Exit(code=1)
    
    # Read coordinate list
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        console.print(f"[red]Error: Cannot read CSV file: {e}[/red]")
        raise typer.Exit(code=1)
    
    if "lon" not in df.columns or "lat" not in df.columns:
        console.print("[red]Error: CSV file must contain 'lon' and 'lat' columns[/red]")
        raise typer.Exit(code=1)
    
    coords = [(row["lon"], row["lat"]) for _, row in df.iterrows()]
    
    console.print(f"[cyan]Read {len(coords)} coordinates[/cyan]")
    
    # Execute batch transformation
    converter = TaiGeotrans()
    results = converter.batch_transform_lonlat(coords, show_progress=True)
    
    # Output results
    _save_batch_results(results, output_file, output_format, converter)


@app.command()
def version() -> None:
    """Display version information"""
    from taigeotrans import __version__
    console.print(f"TaiGeotrans version {__version__}")


def _print_single_result(result, output_format: str) -> None:
    """Print single transformation result"""
    if output_format == "json":
        console.print_json(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    elif output_format == "csv":
        # CSV format (single row)
        df = pd.DataFrame([result.to_dict()])
        console.print(df.to_csv(index=False))
    else:  # table format
        table = Table(title="Transformation Result")
        
        for key, value in result.to_dict().items():
            table.add_row(key, str(value))
        
        console.print(table)
        
        # Status indicator
        if result.status == TransformStatus.SUCCESS:
            console.print("[green]Success[/green]")
        elif result.status == TransformStatus.OUT_OF_BOUNDS:
            console.print("[yellow]Warning: Coordinates outside Taiwan mainland bounds[/yellow]")
        else:
            console.print(f"[red]Failed: {result.error_message}[/red]")


def _save_batch_results(results, output_file, output_format: str, converter) -> None:
    """Save batch transformation results"""
    # Calculate statistics
    success_count = sum(1 for r in results if r.status == TransformStatus.SUCCESS)
    failed_count = sum(1 for r in results if r.status == TransformStatus.FAILED)
    out_of_bounds_count = sum(1 for r in results if r.status == TransformStatus.OUT_OF_BOUNDS)
    
    console.print(f"\n[cyan]Processing complete:[/cyan]")
    console.print(f"  Successful: {success_count}")
    console.print(f"  Failed: {failed_count}")
    console.print(f"  Out of bounds: {out_of_bounds_count}")
    console.print(f"  Total: {len(results)}\n")
    
    if output_file is None:
        # Output to terminal only (simplified)
        df = pd.DataFrame([r.to_dict() for r in results])
        console.print(df.head(10))  # Show first 10 rows
        if len(results) > 10:
            console.print(f"[dim]... and {len(results) - 10} more results[/dim]")
        return
    
    # Save to file
    if output_format == "json":
        data = [r.to_dict() for r in results]
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        console.print(f"[green]Saved to {output_file} (JSON)[/green]")
    
    elif output_format == "geojson":
        geojson = converter.to_geojson(results, filter_failed=False)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)
        console.print(f"[green]Saved to {output_file} (GeoJSON)[/green]")
    
    else:  # CSV format
        df = pd.DataFrame([r.to_dict() for r in results])
        df.to_csv(output_file, index=False, encoding="utf-8-sig")  # UTF-8 BOM for Excel compatibility
        console.print(f"[green]Saved to {output_file} (CSV)[/green]")


def main() -> None:
    """Main entry point"""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
