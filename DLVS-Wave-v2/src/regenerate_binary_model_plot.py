"""Regenerate a binary validation/forecast plot pair from an existing selected output."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.binary_megathrust_report import create_model_plot


def run(output_dir: Path, output_png: Path, stage_name: str) -> Path:
    directory = output_dir.resolve()
    manifests = sorted(directory.glob("selected_manifest_*.json"))
    if len(manifests) != 1:
        raise ValueError(f"Expected exactly one selected manifest in {directory}; found {len(manifests)}")
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    model = str(manifest["model"])
    validation = pd.read_csv(directory / f"selected_validation_{model}.csv", low_memory=False)
    forecast = pd.read_csv(directory / f"selected_forecast_{model}.csv", low_memory=False)
    training = pd.read_csv(directory / f"selected_training_context_{model}.csv", low_memory=False)
    return create_model_plot(
        validation,
        forecast,
        training,
        manifest["holdout_metrics"],
        output_png,
        model_name=model,
        stage_name=stage_name,
        threshold=float(manifest["holdout_metrics"].get("threshold", 0.70)),
        magnitude_threshold=7.7,
        params=manifest["params"],
        validation_event_count=2,
        validation_window_span=max(
            int(manifest.get("validation_weeks_before", 13)),
            int(manifest.get("validation_weeks_after", 13)),
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output-png", type=Path, required=True)
    parser.add_argument("--stage-name", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(run(args.output_dir, args.output_png, args.stage_name))
