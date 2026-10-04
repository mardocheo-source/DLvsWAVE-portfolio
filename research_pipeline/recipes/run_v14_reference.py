#!/usr/bin/env python3
"""Launch the canonical pipeline against the existing V14 study directory."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parents[2]
PROJECT = REPO / "DB/japan-m79plus-180d-2026-2028-deephistory-v14"


def main() -> None:
    command = [
        str(REPO / ".venv/bin/python"),
        str(REPO / "research_pipeline/scientific/run_v14.py"),
        "--project-dir",
        str(PROJECT),
        *sys.argv[1:],
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
