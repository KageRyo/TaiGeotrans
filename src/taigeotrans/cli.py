"""Command-line entry point with an actionable optional-dependency error."""

from __future__ import annotations

import sys


def main() -> int:
    """Run the Typer CLI and return a process exit code."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
        from taigeotrans._cli_app import app
    except ImportError as exc:
        print(
            "The CLI requires optional dependencies. Install them with "
            "`python -m pip install 'taigeotrans[cli]'`.",
            file=sys.stderr,
        )
        print(f"Missing dependency: {exc}", file=sys.stderr)
        return 1

    try:
        app()
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
