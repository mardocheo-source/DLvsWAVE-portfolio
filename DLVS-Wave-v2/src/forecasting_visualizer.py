"""Modulo 13: Top-level wrapper for ForecastingVisualizer."""
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from models.plotting import ForecastingVisualizer, main, build_cli_parser

__all__ = ["ForecastingVisualizer", "main", "build_cli_parser"]

if __name__ == "__main__":
    main()
