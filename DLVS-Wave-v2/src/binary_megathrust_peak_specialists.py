"""Generate one non-degenerate peak-timing specialist for every L1/L2 microstudy."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.binary_megathrust_data import BinaryDataConfig, DATE_COLUMN
from src.binary_megathrust_report import create_model_plot
from src.run_binary_megathrust_pipeline import MODELS, _finalize_model, _write_stage_readme


def _select_peak_specialist(frame: pd.DataFrame) -> dict[str, Any]:
    candidates = frame.loc[frame["status"].eq("success")].copy()
    candidates = candidates.loc[
        candidates["event_peak_count"].eq(2)
        & candidates["train_recall"].ge(0.25)
        & candidates["event_peak_mae_weeks"].notna()
    ]
    if candidates.empty:
        candidates = frame.loc[frame["status"].eq("success") & frame["event_peak_mae_weeks"].notna()].copy()
    if candidates.empty:
        raise ValueError("No successful trial contains event-peak diagnostics")
    within_fp_budget = candidates.loc[candidates["val_fp"].le(1)]
    if not within_fp_budget.empty:
        candidates = within_fp_budget
    ordered = candidates.sort_values(
        [
            "event_peak_mae_weeks",
            "event_peak_max_error_weeks",
            "classification_objective_loss",
            "val_fp",
            "trial_number",
        ],
        ascending=[True, True, True, True, True],
    )
    return ordered.iloc[0].where(pd.notna(ordered.iloc[0]), None).to_dict()


def run(run_dir: Path) -> dict[str, Any]:
    root = run_dir.resolve()
    manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    arguments = manifest["configuration"]
    clean = pd.read_csv(root / "01_data" / "clean_master_binary_7d.csv", low_memory=False)
    clean[DATE_COLUMN] = pd.to_datetime(clean[DATE_COLUMN])
    features = [column for column in clean if column.startswith("packed_astro_container_")]
    config = BinaryDataConfig(
        magnitude_threshold=float(arguments["magnitude_threshold"]),
        cutoff_utc=str(arguments["cutoff_utc"]),
        forecast_start=str(arguments["forecast_start"]),
        forecast_end=str(arguments["forecast_end"]),
        validation_event_count=2,
        validation_weeks_before=int(arguments["validation_weeks_before"]),
        validation_weeks_after=int(arguments["validation_weeks_after"]),
    )
    rows: list[dict[str, Any]] = []
    for stage, directory, filename in (
        ("Level 1", "02_level1", "optuna_trials_{model}.csv"),
        ("Level 2", "03_level2", "meta_trials_{model}.csv"),
    ):
        for model in MODELS:
            study = root / directory / f"study_{model}"
            trials_path = study / filename.format(model=model)
            if not trials_path.exists():
                continue
            selected = _select_peak_specialist(pd.read_csv(trials_path, low_memory=False))
            output = study / "best_peak_timing_output"
            validation, forecast, training, details = _finalize_model(
                model,
                selected,
                clean,
                features,
                output,
                config,
                float(arguments["decision_threshold"]),
                arguments.get("model_epochs"),
            )
            graph = create_model_plot(
                validation,
                forecast,
                training,
                details["holdout_metrics"],
                output / f"{stage.lower().replace(' ', '')}_best_peak_timing_{model}.png",
                model_name=model,
                stage_name=f"{stage} Peak-Timing Specialist",
                threshold=float(arguments["decision_threshold"]),
                magnitude_threshold=float(arguments["magnitude_threshold"]),
                params=details["params"],
                validation_event_count=2,
                validation_window_span=max(config.validation_weeks_before, config.validation_weeks_after),
            )
            _write_stage_readme(
                output,
                stage=f"{stage} Peak-Timing Specialist",
                model_type=model,
                selected_record=selected,
                details=details,
                graph_path=graph,
            )
            metric = details["holdout_metrics"]
            rows.append({
                "stage": stage,
                "model": model,
                "trial_number": int(selected["trial_number"]),
                "train_recall": float(selected.get("train_recall", 0.0)),
                "precision": float(metric["precision"]),
                "recall": float(metric["recall"]),
                "f1": float(metric["f1"]),
                "fp": int(metric["fp"]),
                "fn": int(metric["fn"]),
                "event_peak_mae_weeks": float(metric["event_peak_mae_weeks"]),
                "event_peak_max_error_weeks": int(metric["event_peak_max_error_weeks"]),
                "graph": str(graph),
                "output_dir": str(output),
            })
    summary = pd.DataFrame(rows)
    summary.to_csv(root / "04_final" / "peak_timing_specialists.csv", index=False)
    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "selection": (
            "Among successful trials with both event diagnostics and train recall >= 0.25, first retain FP <= 1 when "
            "at least one such candidate exists; then minimize mean absolute event-peak error, maximum peak error, "
            "classification objective, false positives, and trial number."
        ),
        "specialists": rows,
    }
    (root / "04_final" / "peak_timing_specialists.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    lines = [
        "# Peak-timing specialists", "",
        f"Generated UTC: `{payload['created_utc']}`", "",
        "These outputs are separate from the classification-objective winners. They preserve trials whose predicted",
        "corridor maximum is closest to each held-out event while excluding training-collapse candidates when possible.",
        "", "| Stage | Model | Trial | Train R | Val P | Val R | F1 | FP | FN | Peak MAE (w) | Peak max error (w) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['stage']} | {row['model']} | {row['trial_number']} | {row['train_recall']:.3f} | "
            f"{row['precision']:.3f} | {row['recall']:.3f} | {row['f1']:.3f} | {row['fp']} | {row['fn']} | "
            f"{row['event_peak_mae_weeks']:.2f} | {row['event_peak_max_error_weeks']} |"
        )
    lines.extend([
        "", "A timing-aligned but sub-threshold maximum is not counted as a detected event. Both timing and amplitude",
        "metrics remain visible; these scores are experimental and not operational earthquake predictions.", "",
    ])
    (root / "05_report" / "PEAK_TIMING_SPECIALISTS.md").write_text("\n".join(lines), encoding="utf-8")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(run(args.run_dir), indent=2))
