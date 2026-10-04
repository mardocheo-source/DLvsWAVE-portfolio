#!/usr/bin/env python3
"""Broaden V14 compact-master and non-Japan hard-negative screening.

Every requested configuration keeps at least one world non-Japan training
control. The chronological Japan holdouts and world-control validation events
are frozen across variants; a mismatch aborts the comparison.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd


SOURCE = Path(__file__).resolve().parent


def csv_values(values: list[object]) -> str:
    return ",".join(str(value) for value in values)


def parse_ints(text: str) -> list[int]:
    return sorted({int(item.strip()) for item in text.split(",") if item.strip()})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(*parts: object, environment: dict[str, str]) -> None:
    command = [sys.executable, *map(str, parts)]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True, env=environment)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def baseline_snapshot(project: Path) -> dict:
    summary = read_json(project / "05_ensemble/timing/final_summary.json")
    fusion = read_json(
        project
        / "05_ensemble/timing/metric_specialist_fusion/metric_specialist_fusion_summary.json"
    )
    compact = read_json(project / "02_master_search/compact_k_factor_selection.json")
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "timing_validation_gate": summary.get("validation_gate"),
        "outer_validation_events": summary.get("outer_validation_events"),
        "final_features": summary.get("final_features"),
        "final_history": summary.get("final_history"),
        "metric_fusion_status": fusion.get("status"),
        "metric_fusion_standard_validation": fusion.get("standard_fusion_validation"),
        "metric_fusion_selected_trial": fusion.get("selected_trial"),
        "compact_selected": compact.get("selected"),
        "artifact_sha256": {
            "timing_master": sha256(project / "01_inputs/timing_master.csv"),
            "final_summary": sha256(project / "05_ensemble/timing/final_summary.json"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--hard-negative-training-counts",
        default="8,16,24,36,48",
    )
    parser.add_argument("--k-events", default="3,4,5,6,8,10,12,16,24")
    parser.add_argument("--k-between", default="0,1,2,3,4,6,8,12,16,24")
    parser.add_argument("--proximity-fractions", default="0,0.25,0.5,0.75,1")
    parser.add_argument("--progress-every", type=int, default=50)
    args = parser.parse_args()

    project = args.project_dir.expanduser().resolve()
    output = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else project / "08_extended_search/master_screen"
    )
    output.mkdir(parents=True, exist_ok=True)
    config = read_json(project / "00_config/pipeline_request.json")
    counts = parse_ints(args.hard_negative_training_counts)
    if not counts or min(counts) < 1:
        raise ValueError("Every hard-negative training count must be positive")
    (output / "baseline_snapshot.json").write_text(
        json.dumps(baseline_snapshot(project), indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    bounds = config["japan_bounds"]
    controls = config["hard_negatives"]
    timing = config["timing"]
    interval = int(config["interval_days"])
    environment = os.environ.copy()
    environment["DLVSWAVE_PROJECT_DIR"] = str(project)
    environment["DLVSWAVE_REPO_DIR"] = str(Path(__file__).resolve().parents[2])
    environment.setdefault("MPLCONFIGDIR", "/tmp/v14-extended-master-search")
    all_rows: list[dict] = []
    validation_signature: tuple[tuple[str, str, str], ...] | None = None

    for count in counts:
        variant = output / f"hard_negative_{count:03d}"
        variant.mkdir(parents=True, exist_ok=True)
        full = variant / "timing_master_full.csv"
        audit_csv = variant / "hard_negatives.csv"
        run(
            SOURCE / "prepare_v14_timing_master.py",
            "--source-master", project / "01_inputs/master_180d_jpl_sanitized.csv",
            "--catalog-csv", project / "01_inputs/mega_quakes_of_japan_v14.csv",
            "--output-master", full,
            "--output-safe-features", variant / "safe_features.json",
            "--output-selection-json", variant / "master_selection.json",
            "--output-bin-audit-csv", variant / "event_bin_membership.csv",
            "--world-events-csv", project / "01_inputs/usgs_world_m79_1900_20260731.csv",
            "--output-hard-negative-audit-csv", audit_csv,
            "--output-hard-negative-audit-json", variant / "hard_negatives.json",
            "--hard-negative-mode", controls["mode"],
            "--hard-negative-minimum-magnitude", config["world_hard_negative_minimum_magnitude"],
            "--hard-negative-training-count", count,
            "--hard-negative-validation-per-fold", controls["validation_per_fold"],
            "--hard-negative-validation-radius-slots", controls["validation_radius_slots"],
            "--hard-negative-seed", controls["seed"],
            "--japan-latitude-min", bounds["latitude_min"],
            "--japan-latitude-max", bounds["latitude_max"],
            "--japan-longitude-min", bounds["longitude_min"],
            "--japan-longitude-max", bounds["longitude_max"],
            "--anchor-date", config["anchor_date"],
            "--forecast-start", config["forecast_start"],
            "--forecast-end", config["forecast_end"],
            "--step-days", interval,
            environment=environment,
        )
        controls_frame = pd.read_csv(audit_csv)
        validation_rows = controls_frame[
            controls_frame["scope"].astype(str).str.startswith("validation_fold_")
        ]
        signature = tuple(
            sorted(
                zip(
                    validation_rows["scope"].astype(str),
                    validation_rows["event_id"].astype(str),
                    validation_rows["slot_start"].astype(str),
                )
            )
        )
        if validation_signature is None:
            validation_signature = signature
        elif signature != validation_signature:
            raise RuntimeError("Hard-negative validation controls changed across variants")

        run(
            SOURCE / "search_compact_k_factors.py",
            "--full-master", full,
            "--output-compact-master", variant / "timing_master.csv",
            "--output-trials-csv", variant / "compact_trials.csv",
            "--output-selection-json", variant / "compact_selection.json",
            "--output-selected-indices-csv", variant / "selected_rows.csv",
            "--outer-validation-slots", csv_values(timing["validation_slots"]),
            "--k-events", args.k_events,
            "--k-between", args.k_between,
            "--proximity-fractions", args.proximity_fractions,
            "--event-radius", config["compact_search"]["event_radius"],
            "--random-seed", config["compact_search"]["seed"],
            "--progress-every", args.progress_every,
            environment=environment,
        )
        trial_frame = pd.read_csv(variant / "compact_trials.csv")
        actual_training = int((controls_frame["scope"] == "training").sum())
        for row in trial_frame.to_dict(orient="records"):
            row["hard_negative_training_requested"] = count
            row["hard_negative_training_actual"] = actual_training
            row["variant_dir"] = str(variant)
            all_rows.append(row)

    ranking = pd.DataFrame(all_rows).sort_values(
        [
            "fast_objective",
            "validation_quality_mean",
            "exact_validation_peak_count",
            "selected_historical_rows",
        ],
        ascending=[False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    ranking.insert(0, "global_rank", range(1, len(ranking) + 1))
    ranking.to_csv(output / "all_master_candidates.csv", index=False)
    winner = ranking.iloc[0].to_dict()
    winner_dir = Path(winner["variant_dir"])
    selected_dir = output / "selected"
    selected_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "timing_master_full.csv",
        "timing_master.csv",
        "safe_features.json",
        "master_selection.json",
        "hard_negatives.csv",
        "hard_negatives.json",
        "event_bin_membership.csv",
    ):
        shutil.copy2(winner_dir / name, selected_dir / name)
    summary = {
        "status": "COMPLETE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(ranking),
        "hard_negative_counts": counts,
        "negative_controls_retained": True,
        "frozen_validation_controls": [
            {"scope": scope, "event_id": event_id, "slot_start": slot}
            for scope, event_id, slot in (validation_signature or ())
        ],
        "selection_rule": (
            "Fast Logistic+ExtraTrees proxy; 25% training and 75% chronological "
            "validation per fold; 80% mean and 20% worst-fold objective."
        ),
        "winner": winner,
        "top_20": ranking.head(20).to_dict(orient="records"),
        "selected_master_sha256": sha256(selected_dir / "timing_master.csv"),
    }
    (output / "extended_master_search_summary.json").write_text(
        json.dumps(summary, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary["winner"], indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
