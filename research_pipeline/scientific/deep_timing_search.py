#!/usr/bin/env python3
"""Run auditable feature/model/hybrid research on screened V14 masters."""
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
from typing import Any

import numpy as np
import pandas as pd


SOURCE = Path(__file__).resolve().parent
REPO = SOURCE.parents[1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_inputs(master_variant: Path, destination: Path, spec: dict) -> None:
    (destination / "00_config").mkdir(parents=True, exist_ok=True)
    (destination / "01_inputs").mkdir(parents=True, exist_ok=True)
    (destination / "02_audit").mkdir(parents=True, exist_ok=True)
    (destination / "02_master_search").mkdir(parents=True, exist_ok=True)
    shutil.copy2(master_variant / "timing_master.csv", destination / "01_inputs/timing_master.csv")
    shutil.copy2(master_variant / "safe_features.json", destination / "01_inputs/v4_native_safe_features.json")
    shutil.copy2(master_variant / "compact_selection.json", destination / "02_master_search/compact_k_factor_selection.json")
    shutil.copy2(master_variant / "master_selection.json", destination / "02_master_search/master_search_selection.json")
    shutil.copy2(master_variant / "hard_negatives.csv", destination / "02_audit/world_non_japan_hard_negatives.csv")
    write_json(destination / "00_config/experiment.json", spec)


def run_logged(command: list[str], environment: dict[str, str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as stream:
        stream.write("+ " + " ".join(command) + "\n")
        stream.flush()
        subprocess.run(
            command,
            check=True,
            env=environment,
            stdout=stream,
            stderr=subprocess.STDOUT,
        )


def extract_result(destination: Path, spec: dict) -> dict[str, Any]:
    summary = read_json(destination / "05_ensemble/timing/final_summary.json")
    fusion = read_json(
        destination
        / "05_ensemble/timing/metric_specialist_fusion/metric_specialist_fusion_summary.json"
    )
    isolation = read_json(destination / "05_ensemble/timing/peak_isolation_gate.json")
    selected = fusion["selected_trial"]
    profiles = isolation["selected"]["profiles"]
    exact_fraction = float(np.mean([item["exact_peak"] for item in profiles]))
    return {
        **spec,
        "status": "COMPLETE",
        "validation_gate": summary["validation_gate"],
        "feature_count": summary["final_features"]["feature_count"],
        "training_rows": summary["training_rows"],
        "training_events": summary["training_events"],
        "base_quality_mean": float(np.mean(list(summary["base_quality"].values()))),
        "base_quality_max": float(np.max(list(summary["base_quality"].values()))),
        "best_base": max(summary["base_quality"], key=summary["base_quality"].get),
        "fusion_status": fusion["status"],
        "fusion_validation_mean": selected["validation_quality_mean"],
        "fusion_validation_worst": selected["validation_quality_worst"],
        "fusion_exact_peak_count": selected["exact_peak_count"],
        "fusion_false_positive_mean": selected["false_positive_quality_mean"],
        "fusion_false_positive_worst": selected["false_positive_quality_worst"],
        "hard_negative_below_event_count": selected[
            "hard_negative_below_event_count"
        ],
        "fusion_trial": selected["trial_id"],
        "fusion_metric_set": selected["metric_set"],
        "isolation_objective": isolation["selected"]["total_objective_higher_is_better"],
        "isolation_exact_fraction": exact_fraction,
        "timing_master_sha256": sha256(destination / "01_inputs/timing_master.csv"),
        "experiment_dir": str(destination),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True, type=Path)
    parser.add_argument("--experiment-names", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--refresh-fusion-only",
        action="store_true",
        help=(
            "Reuse persisted model predictions, rerun the current fusion "
            "search, and rebuild the cross-experiment ranking."
        ),
    )
    args = parser.parse_args()
    project = args.project_dir.expanduser().resolve()
    config = read_json(project / "00_config/pipeline_request.json")
    research = config["extended_research"]
    names = {item.strip() for item in args.experiment_names.split(",") if item.strip()}
    experiments = [
        item
        for item in research["timing_model_experiments"]
        if not names or item["name"] in names
    ]
    if names.difference({item["name"] for item in experiments}):
        raise ValueError(f"Unknown experiment names: {sorted(names)}")
    root = project / "08_extended_search/timing_models"
    master_root = project / "08_extended_search/master_screen"
    root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for position, spec in enumerate(experiments, start=1):
        destination = root / spec["name"]
        result_path = destination / "experiment_result.json"
        print(
            f"[{position}/{len(experiments)}] {spec['name']}: "
            f"HN={spec['hard_negative_count']} profile={spec['model_profile']} "
            f"epochs={spec['epochs_scale']}",
            flush=True,
        )
        if result_path.is_file() and not args.force and not args.refresh_fusion_only:
            result = read_json(result_path)
            results.append(result)
            print("  reused completed experiment", flush=True)
            continue
        master_variant = master_root / f"hard_negative_{int(spec['hard_negative_count']):03d}"
        if not args.refresh_fusion_only:
            copy_inputs(master_variant, destination, spec)
        elif not (destination / "04_models/timing").is_dir():
            raise FileNotFoundError(
                f"Cannot refresh fusion; model artifacts are absent: {destination}"
            )
        master_hash = sha256(destination / "01_inputs/timing_master.csv")
        environment = os.environ.copy()
        environment["DLVSWAVE_PROJECT_DIR"] = str(destination)
        environment["DLVSWAVE_REPO_DIR"] = str(REPO)
        environment["MPLCONFIGDIR"] = f"/tmp/v14-{spec['name']}"
        compact = read_json(master_variant / "compact_selection.json")["selected"]
        timing = config["timing"]
        common = [
            sys.executable,
            str(SOURCE / "run_pipeline.py"),
            "--outer-validation-slots", ",".join(timing["validation_slots"]),
            "--precompacted-master",
            "--interval-days", str(config["interval_days"]),
            "--history-start-years", "685",
            "--history-event-radii", str(compact["k_event"]),
            "--history-between-records", str(compact["k_between"]),
            "--event-radius", str(config["compact_search"]["event_radius"]),
            "--forecast-start", config["forecast_start"],
            "--forecast-grid-start", config["forecast_start"],
            "--forecast-end", config["forecast_end"],
            "--region-label", "Japan",
            "--timing-magnitude-threshold", str(config["japan_target_minimum_magnitude"]),
            "--location-magnitude-threshold", str(config["japan_target_minimum_magnitude"]),
            "--expected-master-sha256", master_hash,
            "--training-objective-weight", str(config["compact_search"]["training_objective_weight"]),
            "--validation-objective-weight", str(config["compact_search"]["validation_objective_weight"]),
            "--probe-budget", str(timing["probe_budget"]),
            "--probe-block-size", str(timing["probe_block_size"]),
            "--epochs-scale", str(spec["epochs_scale"]),
            "--actual-guard-epochs-scale", str(spec["actual_guard_epochs_scale"]),
            "--model-profile", spec["model_profile"],
            "--calibration-mode", spec.get(
                "calibration_mode",
                timing.get("calibration_mode", "midrank_ecdf"),
            ),
            "--hard-negative-replay", str(
                spec.get(
                    "hard_negative_replay",
                    timing.get("hard_negative_replay", 1),
                )
            ),
            "--alias-max-lag", str(timing["alias_max_lag"]),
        ]
        if not args.refresh_fusion_only:
            run_logged(common, environment, destination / "logs/sequential.log")
        else:
            print("  reusing persisted model predictions", flush=True)
        fusion = config["fusion"]
        fusion_command = [
            sys.executable,
            str(SOURCE / "metric_specialist_fusion.py"),
            "--run-dir", str(destination),
            "--output-dir", str(destination / "05_ensemble/timing/metric_specialist_fusion"),
            "--minimum-core-overall", str(fusion["minimum_core_overall"]),
            "--minimum-specialist-overall", str(fusion["minimum_specialist_overall"]),
            "--maximum-core-systems", str(fusion["maximum_core_systems"]),
            "--specialists-per-metric", str(fusion["specialists_per_metric"]),
            "--event-radius", str(config["compact_search"]["event_radius"]),
            "--interval-days", str(config["interval_days"]),
            "--metric-config-json", str(project / "00_config/metric_specialist_config.json"),
            "--candidate-core-shares", ",".join(map(str, fusion["candidate_core_shares"])),
            "--selection-mean-weight", str(fusion["selection_mean_weight"]),
            "--selection-quality-weight", str(fusion["selection_quality_weight"]),
            "--selection-false-positive-weight", str(fusion["selection_false_positive_weight"]),
            "--selection-exact-peak-weight", str(fusion["selection_exact_peak_weight"]),
            "--false-positive-mean-weight", str(fusion["false_positive_mean_weight"]),
            "--event-control-margin-scale", str(fusion["event_control_margin_scale"]),
            "--minimum-event-control-margin", str(fusion["minimum_event_control_margin"]),
            "--random-metric-mix-trials", str(fusion["random_metric_mix_trials"]),
            "--random-metric-mix-seed", str(fusion["random_metric_mix_seed"]),
            "--random-metric-concentration", str(fusion["random_metric_concentration"]),
            "--direct-system-mix-trials", str(fusion["direct_system_mix_trials"]),
            "--direct-system-mix-seed", str(fusion["direct_system_mix_seed"]),
            "--direct-system-pool-per-criterion", str(fusion["direct_system_pool_per_criterion"]),
            "--direct-system-maximum-members", str(fusion["direct_system_maximum_members"]),
            (
                "--require-controls-below-event"
                if fusion["require_controls_below_event"]
                else "--no-require-controls-below-event"
            ),
            "--minimum-fusion-validation-mean", str(fusion["minimum_validation_mean"]),
            "--minimum-fusion-validation-worst", str(fusion["minimum_validation_worst"]),
        ]
        run_logged(fusion_command, environment, destination / "logs/fusion.log")
        result = extract_result(destination, spec)
        write_json(result_path, result)
        results.append(result)
        print(
            "  validation mean/worst "
            f"{result['fusion_validation_mean']:.4f}/"
            f"{result['fusion_validation_worst']:.4f}; "
            f"exact {result['fusion_exact_peak_count']}/2; "
            f"features {result['feature_count']}",
            flush=True,
        )

    weights = research["selection_weights"]
    tie_tolerance = float(research.get("selection_tie_tolerance", 0.0))
    for result in results:
        result["research_selection_score"] = (
            weights["validation_mean"] * result["fusion_validation_mean"]
            + weights["validation_worst"] * result["fusion_validation_worst"]
            + weights["exact_peak_fraction"] * (result["fusion_exact_peak_count"] / 2.0)
            + weights["peak_isolation_objective"] * result["isolation_objective"]
            + weights.get("false_positive_mean", 0.0)
            * result["fusion_false_positive_mean"]
            + weights.get("false_positive_worst", 0.0)
            * result["fusion_false_positive_worst"]
            + weights.get("hard_negative_below_event_fraction", 0.0)
            * (result["hard_negative_below_event_count"] / 2.0)
        )
    ranking = pd.DataFrame(results)
    best_score = float(ranking["research_selection_score"].max())
    ranking["selection_score_delta_from_best"] = (
        best_score - ranking["research_selection_score"]
    )
    ranking["selection_equivalent_to_best"] = ranking[
        "selection_score_delta_from_best"
    ].le(tie_tolerance)
    ranking["parsimony_epochs_scale"] = ranking["epochs_scale"].astype(float)
    ranking["effective_selection_score"] = np.where(
        ranking["selection_equivalent_to_best"],
        best_score,
        ranking["research_selection_score"],
    )
    ranking = ranking.sort_values(
        [
            "effective_selection_score",
            "parsimony_epochs_scale",
            "fusion_validation_worst",
            "feature_count",
        ],
        ascending=[False, True, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    ranking.insert(0, "rank", range(1, len(ranking) + 1))
    ranking.to_csv(root / "timing_model_research_ranking.csv", index=False)
    payload = {
        "status": "COMPLETE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "experiment_count": len(results),
        "selection_weights": weights,
        "selection_tie_tolerance": tie_tolerance,
        "tie_break_rule": (
            "scores within the configured tolerance are equivalent; choose "
            "the lower epochs scale, then higher worst-fold quality, then "
            "fewer features"
        ),
        "winner": ranking.iloc[0].to_dict(),
        "ranking": ranking.to_dict(orient="records"),
    }
    write_json(root / "timing_model_research_summary.json", payload)
    print("Current winner:", payload["winner"]["name"], flush=True)


if __name__ == "__main__":
    main()
