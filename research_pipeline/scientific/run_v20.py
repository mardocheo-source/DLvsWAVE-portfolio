#!/usr/bin/env python3
"""Reproduce the special V20 same-day six-hour time-connection pipeline."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parents[2]
PIPELINE = Path(__file__).resolve().parent


def execute(python: Path, script: Path, *arguments: object) -> None:
    command = [str(python), str(script), *map(str, arguments)]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True, env=os.environ.copy())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--reuse-master", action="store_true")
    parser.add_argument("--reuse-model", action="store_true")
    parser.add_argument(
        "--issued-at",
        default=None,
        help="Optional ISO-8601 report issue datetime passed to the renderer.",
    )
    args = parser.parse_args()
    project = args.project_dir.resolve()
    config = (args.config or project / "00_config/pipeline_request.json").resolve()
    python = REPO / ".venv/bin/python"
    os.environ["DLVSWAVE_PROJECT_DIR"] = str(project)
    os.environ["DLVSWAVE_REPO_DIR"] = str(REPO)
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/dlvswave-v20-matplotlib")
    for relative in (
        "00_config", "01_inputs", "02_audit", "03_feature_research",
        "04_models", "05_ensemble", "06_report",
    ):
        (project / relative).mkdir(parents=True, exist_ok=True)

    master_artifacts = (
        project / "01_inputs/event_time_master.csv",
        project / "02_audit/event_time_master_manifest.json",
    )
    if not args.reuse_master or not all(path.is_file() for path in master_artifacts):
        execute(
            python,
            PIPELINE / "prepare_v20_time_master.py",
            "--project-dir", project,
            "--config", config,
        )
    model_artifacts = (
        project / "05_ensemble/time_band_summary.json",
        project / "05_ensemble/time_band_validation.csv",
        project / "05_ensemble/time_band_weighted_forecast.csv",
        project / "05_ensemble/time_band_one_shot_forecast.csv",
    )
    if not args.reuse_model or not all(path.is_file() for path in model_artifacts):
        execute(
            python,
            PIPELINE / "run_v20_time_connection.py",
            "--project-dir", project,
            "--config", config,
        )
    render_arguments: list[object] = ["--project-dir", project, "--config", config]
    if args.issued_at:
        render_arguments.extend(["--issued-at", args.issued_at])
    execute(python, PIPELINE / "render_v20_time_report.py", *render_arguments)
    execute(python, PIPELINE / "self_check_v20.py", "--project-dir", project)


if __name__ == "__main__":
    main()
