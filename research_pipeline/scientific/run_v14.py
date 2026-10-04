#!/usr/bin/env python3
"""Reproduce a parameter-driven deep-history Japan experiment.

The historical filename is retained for compatibility.  Request JSON selects
stride or direct Horizons masters, thresholds, hard-negative controls,
fold-contextual fusion, optional conditional-magnitude calibration and the
universal professional report; no study-specific values are embedded here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.request import urlretrieve


SOURCE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = SOURCE_ROOT.parent
PROJECT: Path
REPO: Path
PIPELINE = SOURCE_ROOT / "scientific"
STANDARD = SOURCE_ROOT / "reporting"


def csv(values: list[object]) -> str:
    return ",".join(str(value) for value in values)


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def execute(python: Path, script: Path, *arguments: object) -> None:
    command = [str(python), str(script), *map(str, arguments)]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True, env=os.environ.copy())


def main() -> None:
    global PROJECT, REPO
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-dir",
        type=Path,
        required=True,
        help="Study output directory containing the parameter JSON and artifacts.",
    )
    parser.add_argument("--repo-dir", type=Path, default=DEFAULT_REPO)
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
    )
    parser.add_argument("--refresh-downloads", action="store_true")
    parser.add_argument(
        "--reuse-hyperparameter-screen",
        action="store_true",
        help=(
            "Reuse an existing complete parameter-screen selection, trial table "
            "and runtime audit instead of repeating the expensive fast screen."
        ),
    )
    parser.add_argument(
        "--reuse-compact-search",
        action="store_true",
        help=(
            "Reuse an existing complete compact master, k-factor trial table, "
            "selection JSON and selected-row audit."
        ),
    )
    parser.add_argument(
        "--reuse-timing-final",
        action="store_true",
        help=(
            "Reuse a complete chronological timing ensemble and forecast while "
            "continuing with specialist fusion, controls, location and reporting."
        ),
    )
    parser.add_argument(
        "--reuse-one-shot-timing",
        action="store_true",
        help="Reuse the complete real-label one-shot validation and forecast refit.",
    )
    parser.add_argument(
        "--reuse-metric-fusion",
        action="store_true",
        help=(
            "Reuse a complete metric-specialist fusion and continue with null "
            "controls, contextual fusion, location and reporting."
        ),
    )
    parser.add_argument(
        "--reuse-randomized-timing",
        action="store_true",
        help=(
            "Reuse a complete target-label randomized timing control. This "
            "control never contributes to the promoted forecast."
        ),
    )
    parser.add_argument(
        "--reuse-historical-shuffle",
        action="store_true",
        help=(
            "Reuse a complete intact-record historical-order sensitivity "
            "control and its forecast projection."
        ),
    )
    parser.add_argument(
        "--reuse-contextual-fusion",
        action="store_true",
        help=(
            "Reuse complete contextual fold-fusion outputs while continuing "
            "with magnitude, location, diagnostics and reporting."
        ),
    )
    parser.add_argument(
        "--reuse-threshold-projection",
        action="store_true",
        help="Reuse the validation-derived discrete timing forecast artifacts.",
    )
    parser.add_argument(
        "--reuse-location",
        action="store_true",
        help=(
            "Reuse complete sequential, randomized-control and finalized "
            "location artifacts while regenerating diagnostics and the report."
        ),
    )
    args = parser.parse_args()
    PROJECT = args.project_dir.expanduser().resolve()
    REPO = args.repo_dir.expanduser().resolve()
    config_path = args.config or PROJECT / "00_config/pipeline_request.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    pipeline_version = str(config.get("pipeline_version", "v14")).lower()
    python = REPO / ".venv/bin/python"
    interval = int(config["interval_days"])
    anchor = config["anchor_date"]
    forecast_start = config["forecast_start"]
    forecast_end = config["forecast_end"]
    target_floor = float(
        config.get(
            "japan_training_minimum_magnitude",
            config["japan_target_minimum_magnitude"],
        )
    )
    timing_validation_floor = float(
        config.get(
            "japan_timing_validation_minimum_magnitude",
            config.get("japan_validation_minimum_magnitude", target_floor),
        )
    )
    location_validation_floor = float(
        config.get(
            "japan_location_validation_minimum_magnitude",
            config.get(
                "japan_validation_minimum_magnitude", timing_validation_floor
            ),
        )
    )
    world_training_floor = float(
        config.get(
            "world_hard_negative_training_minimum_magnitude",
            config["world_hard_negative_minimum_magnitude"],
        )
    )
    world_validation_floor = float(
        config.get(
            "world_hard_negative_validation_minimum_magnitude",
            config["world_hard_negative_minimum_magnitude"],
        )
    )
    world_discovery_floor = min(world_training_floor, world_validation_floor)
    japan_discovery_floor = min(
        target_floor, timing_validation_floor, location_validation_floor
    )
    bounds = config["japan_bounds"]
    controls = config["hard_negatives"]
    compact = config["compact_search"]
    timing = config["timing"]
    fusion = config["fusion"]
    location = config["location"]
    preprocessing = config.get("preprocessing", {})
    quantile_bins = int(preprocessing.get("quantile_bins", 0))
    validation_slots = csv(timing["validation_slots"])

    os.environ["DLVSWAVE_PROJECT_DIR"] = str(PROJECT)
    os.environ["DLVSWAVE_REPO_DIR"] = str(REPO)
    os.environ.setdefault(
        "MPLCONFIGDIR", f"/tmp/dlvswave-deephistory-{pipeline_version}"
    )
    for relative in (
        "00_config", "01_inputs", "02_audit", "02_master_search",
        "03_feature_research", "04_models", "05_ensemble", "06_report",
    ):
        (PROJECT / relative).mkdir(parents=True, exist_ok=True)

    snapshot = config.get("data_snapshot", {})
    query_start = str(snapshot.get("query_start", "1900-01-01"))
    query_end = str(snapshot.get("query_end_exclusive", "2026-08-01"))
    japan_source = PROJECT / snapshot.get(
        "japan_csv", "01_inputs/usgs_japan_bbox_m79_1900_20260731.csv"
    )
    world_source = PROJECT / snapshot.get(
        "world_csv", "01_inputs/usgs_world_m79_1900_20260731.csv"
    )
    japan_url = (
        "https://earthquake.usgs.gov/fdsnws/event/1/query.csv?"
        f"starttime={query_start}&endtime={query_end}&minlatitude="
        f"{bounds['latitude_min']}&maxlatitude={bounds['latitude_max']}"
        f"&minlongitude={bounds['longitude_min']}&maxlongitude={bounds['longitude_max']}"
        f"&minmagnitude={japan_discovery_floor:g}&orderby=time-asc"
    )
    world_url = (
        "https://earthquake.usgs.gov/fdsnws/event/1/query.csv?"
        f"starttime={query_start}&endtime={query_end}&minmagnitude={world_discovery_floor:g}"
        "&orderby=time-asc"
    )
    downloads = [(japan_source, japan_url), (world_source, world_url)]
    supplemental_location_source = None
    if location.get("indirect_validation_magnitude_threshold", 0) > 0:
        supplemental_location_source = PROJECT / snapshot.get(
            "location_supplemental_csv",
            "01_inputs/usgs_japan_location_supplemental.csv",
        )
        supplemental_floor = float(
            location["indirect_validation_magnitude_threshold"]
        )
        supplemental_url = (
            "https://earthquake.usgs.gov/fdsnws/event/1/query.csv?"
            f"starttime={query_start}&endtime={query_end}&minlatitude="
            f"{bounds['latitude_min']}&maxlatitude={bounds['latitude_max']}"
            f"&minlongitude={bounds['longitude_min']}&maxlongitude={bounds['longitude_max']}"
            f"&minmagnitude={supplemental_floor:g}&orderby=time-asc"
        )
        downloads.append((supplemental_location_source, supplemental_url))
    recent_source = None
    if config.get("magnitude_recalibration") and snapshot.get(
        "recent_japan_csv"
    ):
        recent_source = PROJECT / snapshot["recent_japan_csv"]
        recent_floor = float(
            snapshot.get("recent_japan_minimum_magnitude", target_floor)
        )
        recent_start = str(snapshot.get("recent_japan_start", query_start))
        recent_url = (
            "https://earthquake.usgs.gov/fdsnws/event/1/query.csv?"
            f"starttime={recent_start}&endtime={query_end}&minlatitude="
            f"{bounds['latitude_min']}&maxlatitude={bounds['latitude_max']}"
            f"&minlongitude={bounds['longitude_min']}&maxlongitude={bounds['longitude_max']}"
            f"&minmagnitude={recent_floor:g}&orderby=time-asc"
        )
        downloads.append((recent_source, recent_url))
    for path, url in downloads:
        if args.refresh_downloads or not path.is_file():
            print(f"Downloading {url}", flush=True)
            urlretrieve(url, path)

    catalog = PROJECT / f"01_inputs/mega_quakes_of_japan_{pipeline_version}.csv"
    execute(
        python, PIPELINE / "build_megaquake_catalog.py",
        "--usgs-csv", japan_source,
        "--historical-csv", REPO / "DB/japan/terremoti_giappone_maggiore_8_prima_1900.csv",
        "--output-csv", catalog,
        "--output-audit-json", PROJECT / "02_audit/mega_quake_catalog_audit.json",
        "--output-markdown", PROJECT / f"01_inputs/MEGA_QUAKES_OF_JAPAN_{pipeline_version.upper()}.md",
        "--usgs-discovery-floor", japan_discovery_floor,
        "--catalog-minimum-magnitude", japan_discovery_floor,
        "--usgs-query-url", japan_url,
        "--catalog-label", (
            f"Mega earthquakes of Japan — {pipeline_version.upper()} "
            f"M≥{japan_discovery_floor:g} discovery catalogue; "
            f"timing training/holdout M≥{target_floor:g}/"
            f"{timing_validation_floor:g}; location holdout M≥"
            f"{location_validation_floor:g}"
        ),
    )
    jpl = config.get("jpl_master", {})
    if jpl.get("mode") == "direct_horizons_shifted_grid":
        direct_master = PROJECT / jpl["output_master"]
        jpl_manifest = PROJECT / jpl["manifest_json"]
        interval_features = config.get("interval_features")
        horizons_step = int(
            interval_features.get("source_step_days", interval)
            if interval_features
            else interval
        )
        if args.refresh_downloads or not direct_master.is_file():
            execute(
                python, REPO / "build_jpl_safe_360d_master.py",
                "--safe-ephemerides-csv", PROJECT / jpl["body_csv"],
                "--events-csv", catalog,
                "--output-float-csv", direct_master,
                "--manifest-json", jpl_manifest,
                "--start-date", jpl["start_date"],
                "--end-date", jpl["end_date"],
                "--step-days", horizons_step,
                "--chunk-size", jpl.get("chunk_size", 60),
                "--sleep-seconds", jpl.get("sleep_seconds", 0.05),
                "--max-retries", jpl.get("max_retries", 4),
                "--moon-center", jpl.get("moon_center", "earth"),
                "--refplane", jpl.get("refplane", "earth"),
                "--auto-clip", jpl.get("auto_clip", "vertical"),
            )
        if not jpl_manifest.is_file():
            raise FileNotFoundError(
                f"Direct JPL manifest is missing: {jpl_manifest}"
            )
        if interval_features:
            derived_master = PROJECT / interval_features["output_master"]
            execute(
                python,
                PIPELINE / "interval_feature_operators.py",
                "--input-fine-master", direct_master,
                "--output-master", derived_master,
                "--audit-json", PROJECT / interval_features["audit_json"],
                "--anchor-date", anchor,
                "--start-date", interval_features.get(
                    "start_date", jpl["start_date"]
                ),
                "--end-date", forecast_end,
                "--source-step-days", interval_features["source_step_days"],
                "--target-step-days", interval,
                "--operators", csv(interval_features["operators"]),
                "--ephemerides", csv(interval_features["ephemerides"]),
                "--bodies", csv(interval_features.get("bodies", ["*"])),
            )
        else:
            derived_master = direct_master
    else:
        source_master = PROJECT / "01_inputs/master_source_60d_jpl_sanitized.csv"
        if not source_master.is_file():
            source_master = REPO / "DB/japan-m79plus-60d-2026-2028-deephistory-v13/01_inputs/master_60d_jpl_sanitized.csv"
        derived_master = PROJECT / "01_inputs/master_180d_jpl_sanitized.csv"
        execute(
            python, PIPELINE / "derive_aligned_jpl_master.py",
            "--source-master", source_master,
            "--output-master", derived_master,
            "--audit-json", PROJECT / "02_audit/master_180d_derivation.json",
            "--source-step-days", 60,
            "--target-step-days", interval,
            "--anchor-date", anchor,
        )
    full_master = PROJECT / "01_inputs/timing_master_full.csv"
    feature_controls = config.get("feature_controls", {})
    execute(
        python, PIPELINE / "prepare_v14_timing_master.py",
        "--source-master", derived_master,
        "--catalog-csv", catalog,
        "--output-master", full_master,
        "--output-safe-features", PROJECT / "01_inputs/v4_native_safe_features.json",
        "--output-selection-json", PROJECT / "02_master_search/master_search_selection.json",
        "--output-bin-audit-csv", PROJECT / "02_audit/event_bin_membership.csv",
        "--world-events-csv", world_source,
        "--output-hard-negative-audit-csv", PROJECT / "02_audit/world_non_japan_hard_negatives.csv",
        "--output-hard-negative-audit-json", PROJECT / "02_audit/world_non_japan_hard_negatives.json",
        "--hard-negative-mode", controls["mode"],
        "--hard-negative-minimum-magnitude", world_discovery_floor,
        "--hard-negative-training-minimum-magnitude", world_training_floor,
        "--hard-negative-validation-minimum-magnitude", world_validation_floor,
        "--hard-negative-training-count", controls["training_count"],
        "--hard-negative-validation-per-fold", controls["validation_per_fold"],
        "--hard-negative-validation-radius-slots", controls["validation_radius_slots"],
        "--hard-negative-seed", controls["seed"],
        "--outer-validation-slots", validation_slots,
        "--japan-training-minimum-magnitude", target_floor,
        "--japan-validation-minimum-magnitude", timing_validation_floor,
        "--japan-latitude-min", bounds["latitude_min"],
        "--japan-latitude-max", bounds["latitude_max"],
        "--japan-longitude-min", bounds["longitude_min"],
        "--japan-longitude-max", bounds["longitude_max"],
        "--anchor-date", anchor,
        "--forecast-start", forecast_start,
        "--forecast-end", forecast_end,
        "--step-days", interval,
        "--calendar-features", csv(
            feature_controls.get("calendar_features", ["doy_sin", "doy_cos"])
        ),
        "--calendar-system", feature_controls.get(
            "calendar_system", "proleptic_gregorian"
        ),
        "--catalog-outside-master-policy",
        config.get("catalog_outside_master_policy", "error"),
    )
    compact_master = PROJECT / "01_inputs/timing_master.csv"
    compact_artifacts = (
        compact_master,
        PROJECT / "02_master_search/compact_k_factor_trials.csv",
        PROJECT / "02_master_search/compact_k_factor_selection.json",
        PROJECT / "02_master_search/compact_selected_historical_rows.csv",
    )
    if args.reuse_compact_search and all(
        path.is_file() and path.stat().st_size > 0 for path in compact_artifacts
    ):
        print(
            "+ reusing complete compact-search artifacts: "
            + ", ".join(str(path) for path in compact_artifacts),
            flush=True,
        )
    else:
        execute(
            python, PIPELINE / "search_compact_k_factors.py",
            "--full-master", full_master,
            "--output-compact-master", compact_master,
            "--output-trials-csv", PROJECT / "02_master_search/compact_k_factor_trials.csv",
            "--output-selection-json", PROJECT / "02_master_search/compact_k_factor_selection.json",
            "--output-selected-indices-csv", PROJECT / "02_master_search/compact_selected_historical_rows.csv",
            "--outer-validation-slots", validation_slots,
            "--k-events", csv(compact["k_events"]),
            "--k-between", csv(compact["k_between"]),
            "--proximity-fractions", csv(compact["proximity_fractions"]),
            "--history-start-dates", csv(
                compact.get("history_start_dates", [])
            ),
            "--minimum-prevalidation-events",
            compact.get(
                "minimum_prevalidation_events",
                5 + int(timing.get("inner_validation_events", 3)),
            ),
            "--event-radius", compact["event_radius"],
            "--quantile-bins", quantile_bins,
            "--training-objective-weight", compact["training_objective_weight"],
            "--validation-objective-weight", compact["validation_objective_weight"],
            "--selection-training-weight",
            compact.get("selection_training_weight", 0.20),
            "--selection-validation-mean-weight",
            compact.get("selection_validation_mean_weight", 0.60),
            "--selection-validation-worst-weight",
            compact.get("selection_validation_worst_weight", 0.20),
            "--selection-exact-peak-weight",
            compact.get("selection_exact_peak_weight", 0.0),
            "--random-seed", compact["seed"],
        )
    compact_selection = json.loads(
        (PROJECT / "02_master_search/compact_k_factor_selection.json").read_text(
            encoding="utf-8"
        )
    )["selected"]
    hyper_screen = config.get("hyperparameter_screen")
    model_overrides = None
    if hyper_screen:
        model_overrides = PROJECT / hyper_screen["output_selection_json"]
        screen_artifacts = (
            model_overrides,
            PROJECT / hyper_screen["output_trials_csv"],
            PROJECT / hyper_screen["output_runtime_json"],
        )
        if args.reuse_hyperparameter_screen and all(
            path.is_file() and path.stat().st_size > 0
            for path in screen_artifacts
        ):
            print(
                "+ reusing complete hyperparameter-screen artifacts: "
                + ", ".join(str(path) for path in screen_artifacts),
                flush=True,
            )
        else:
            execute(
                python,
                PIPELINE / "fast_model_parameter_screen.py",
                "--timing-master", compact_master,
                "--safe-features-json", PROJECT / "01_inputs/v4_native_safe_features.json",
                "--candidate-config-json", PROJECT / hyper_screen["candidate_config_json"],
                "--validation-slots", validation_slots,
                "--forecast-start", forecast_start,
                "--event-radius", compact["event_radius"],
                "--feature-limit", hyper_screen.get("feature_limit", 32),
                "--quantile-bins", quantile_bins,
                "--epochs-scale", hyper_screen.get("epochs_scale", 1.0),
                "--random-seed", hyper_screen.get("random_seed", 617171),
                "--quality-weight", hyper_screen.get("quality_weight", 0.85),
                "--speed-weight", hyper_screen.get("speed_weight", 0.15),
                "--output-trials-csv", PROJECT / hyper_screen["output_trials_csv"],
                "--output-selection-json", model_overrides,
                "--output-runtime-json", PROJECT / hyper_screen["output_runtime_json"],
            )
    history_start_year = int(
        str(
            compact_selection.get(
                "history_start_date",
                config.get(
                    "history_start_year",
                    str(jpl.get("start_date", "0685-01-01"))[:4],
                ),
            )
        )[:4]
    )
    master_hash = sha256(compact_master)
    common = [
        "--outer-validation-slots", validation_slots,
        "--precompacted-master",
        "--resume-completed-folds",
        "--interval-days", interval,
        "--history-start-years", history_start_year,
        "--history-event-radii", compact_selection["k_event"],
        "--history-between-records", compact_selection["k_between"],
        "--event-radius", compact["event_radius"],
        "--forecast-start", forecast_start,
        "--forecast-grid-start", forecast_start,
        "--forecast-end", forecast_end,
        "--region-label", "Japan",
        "--timing-magnitude-threshold", target_floor,
        "--timing-validation-magnitude-threshold", timing_validation_floor,
        "--hard-negative-training-magnitude-threshold", world_training_floor,
        "--hard-negative-validation-magnitude-threshold", world_validation_floor,
        "--location-magnitude-threshold", target_floor,
        "--location-validation-magnitude-threshold", location_validation_floor,
        "--expected-master-sha256", master_hash,
        "--training-objective-weight", compact["training_objective_weight"],
        "--validation-objective-weight", compact["validation_objective_weight"],
        "--probe-budget", timing["probe_budget"],
        "--probe-block-size", timing["probe_block_size"],
        "--inner-validation-events", timing.get("inner_validation_events", 3),
        "--epochs-scale", timing["epochs_scale"],
        "--final-attempt-time-limit-seconds", timing.get(
            "final_attempt_time_limit_seconds", 0
        ),
        "--model-profile", timing.get("model_profile", "standard"),
        "--actual-guard-epochs-scale", timing["actual_guard_epochs_scale"],
        "--calibration-mode", timing.get("calibration_mode", "midrank_ecdf"),
        "--quantile-bins", quantile_bins,
        "--hard-negative-replay", timing.get("hard_negative_replay", 1),
        "--alias-max-lag", timing["alias_max_lag"],
    ]
    if model_overrides:
        common.extend(["--model-overrides-json", model_overrides])
    timing_final_artifacts = (
        PROJECT / "05_ensemble/timing/final_summary.json",
        PROJECT / "05_ensemble/timing/forecast_predictions.csv",
        PROJECT / "05_ensemble/timing/validation_predictions.csv",
        PROJECT / "05_ensemble/timing/peak_isolation_gate.json",
        PROJECT / "00_config/completion.json",
    )
    if args.reuse_timing_final and all(
        path.is_file() and path.stat().st_size > 0
        for path in timing_final_artifacts
    ):
        print(
            "+ reusing complete chronological timing artifacts: "
            + ", ".join(str(path) for path in timing_final_artifacts),
            flush=True,
        )
    else:
        execute(python, PIPELINE / "run_pipeline.py", *common)
    one_shot = config.get("one_shot_timing", {})
    if one_shot.get("enabled", False):
        one_shot_artifacts = (
            PROJECT / "05_ensemble/timing/one_shot/summary.json",
            PROJECT / "05_ensemble/timing/one_shot/validation.csv",
            PROJECT / "05_ensemble/timing/one_shot/forecast.csv",
            PROJECT / "05_ensemble/timing/one_shot/completion.json",
        )
        if args.reuse_one_shot_timing and all(
            path.is_file() and path.stat().st_size > 0
            for path in one_shot_artifacts
        ):
            print(
                "+ reusing complete real-label one-shot timing artifacts: "
                + ", ".join(str(path) for path in one_shot_artifacts),
                flush=True,
            )
        else:
            execute(
                python,
                PIPELINE / "run_pipeline.py",
                *common,
                "--training-mode",
                "one_shot",
                "--random-seed",
                one_shot.get("seed", 619019),
            )
    metric_fusion_dir = PROJECT / "05_ensemble/timing/metric_specialist_fusion"
    metric_fusion_artifacts = (
        metric_fusion_dir / "metric_specialist_fusion_summary.json",
        metric_fusion_dir / "metric_specialist_fusion_forecast.csv",
        metric_fusion_dir / "false_positive_aware_validation_predictions.csv",
        metric_fusion_dir / "metric_fusion_contribution_trace.json",
    )
    if args.reuse_metric_fusion and all(
        path.is_file() and path.stat().st_size > 0
        for path in metric_fusion_artifacts
    ):
        print(
            "+ reusing complete metric-fusion artifacts: "
            + ", ".join(str(path) for path in metric_fusion_artifacts),
            flush=True,
        )
    else:
        execute(
            python, PIPELINE / "metric_specialist_fusion.py",
            "--run-dir", PROJECT,
            "--output-dir", metric_fusion_dir,
            "--minimum-core-overall", fusion["minimum_core_overall"],
            "--minimum-specialist-overall", fusion["minimum_specialist_overall"],
            "--maximum-core-systems", fusion["maximum_core_systems"],
            "--specialists-per-metric", fusion["specialists_per_metric"],
            "--event-radius", compact["event_radius"],
            "--interval-days", interval,
            "--metric-config-json", PROJECT / "00_config/metric_specialist_config.json",
            "--candidate-core-shares", csv(fusion["candidate_core_shares"]),
            "--selection-mean-weight", fusion["selection_mean_weight"],
            "--selection-quality-weight", fusion["selection_quality_weight"],
            "--selection-false-positive-weight", fusion["selection_false_positive_weight"],
            "--selection-exact-peak-weight", fusion["selection_exact_peak_weight"],
            "--false-positive-mean-weight", fusion["false_positive_mean_weight"],
            "--event-control-margin-scale", fusion["event_control_margin_scale"],
            "--minimum-event-control-margin", fusion["minimum_event_control_margin"],
            "--random-metric-mix-trials", fusion["random_metric_mix_trials"],
            "--random-metric-mix-seed", fusion["random_metric_mix_seed"],
            "--random-metric-concentration", fusion["random_metric_concentration"],
            "--direct-system-mix-trials", fusion["direct_system_mix_trials"],
            "--direct-system-mix-seed", fusion["direct_system_mix_seed"],
            "--direct-system-pool-per-criterion", fusion["direct_system_pool_per_criterion"],
            "--direct-system-maximum-members", fusion["direct_system_maximum_members"],
            (
                "--require-controls-below-event"
                if fusion["require_controls_below_event"]
                else "--no-require-controls-below-event"
            ),
            "--minimum-fusion-validation-mean", fusion["minimum_validation_mean"],
            "--minimum-fusion-validation-worst", fusion["minimum_validation_worst"],
        )
    randomized_artifacts = (
        PROJECT / "07_randomized_control/timing/summary.json",
        PROJECT / "07_randomized_control/timing/validation.csv",
        PROJECT / "07_randomized_control/timing/forecast.csv",
        PROJECT / "07_randomized_control/timing/completion.json",
    )
    if args.reuse_randomized_timing and all(
        path.is_file() and path.stat().st_size > 0
        for path in randomized_artifacts
    ):
        print(
            "+ reusing complete target-label randomized timing control: "
            + ", ".join(str(path) for path in randomized_artifacts),
            flush=True,
        )
    else:
        execute(
            python,
            PIPELINE / "run_pipeline.py",
            *common,
            "--training-mode",
            "randomized",
        )
    historical_shuffle_artifacts = (
        PROJECT / "07_historical_record_shuffle/timing/summary.json",
        PROJECT / "07_historical_record_shuffle/timing/validation.csv",
        PROJECT / "07_historical_record_shuffle/timing/forecast.csv",
        PROJECT / "07_historical_record_shuffle/timing/repeat_metrics.csv",
    )
    if args.reuse_historical_shuffle and all(
        path.is_file() and path.stat().st_size > 0
        for path in historical_shuffle_artifacts
    ):
        print(
            "+ reusing complete historical-record shuffle control: "
            + ", ".join(str(path) for path in historical_shuffle_artifacts),
            flush=True,
        )
    else:
        execute(
            python, PIPELINE / "run_pipeline.py", *common,
            "--training-mode", "historical_record_shuffle",
            "--historical-record-repeats", timing["historical_record_repeats"],
            "--historical-record-aggregation", timing["historical_record_aggregation"],
        )
    contextual = config.get("contextual_fusion")
    if pipeline_version.startswith("v16"):
        execute(
            python,
            PIPELINE / "self_check_v16.py",
            "--project-dir", PROJECT,
        )
    elif contextual:
        contextual_directory = PROJECT / contextual["output_directory"]
        contextual_artifacts = (
            contextual_directory / "contextual_fold_fusion_summary.json",
            contextual_directory / "contextual_fold_fusion_forecast.csv",
            contextual_directory / "contextual_fold_validation_predictions.csv",
            contextual_directory / "contextual_fold_contribution_trace.json",
        )
        if args.reuse_contextual_fusion and all(
            path.is_file() and path.stat().st_size > 0
            for path in contextual_artifacts
        ):
            print(
                "+ reusing complete contextual fold-fusion artifacts: "
                + ", ".join(str(path) for path in contextual_artifacts),
                flush=True,
            )
        else:
            execute(
                python,
                PIPELINE / "contextual_fold_fusion.py",
                "--run-dir", PROJECT,
                "--output-dir", contextual_directory,
                "--config-json", PROJECT / contextual["config_json"],
            )
    threshold_projection = config.get("validation_threshold_projection", {})
    if threshold_projection.get("enabled", False):
        threshold_directory = PROJECT / threshold_projection.get(
            "output_directory",
            "05_ensemble/timing/validation_threshold_projection",
        )
        threshold_artifacts = (
            threshold_directory / "validation_peak_threshold.json",
            threshold_directory / "validation_peak_threshold_trials.csv",
            threshold_directory / "discretized_forecast.csv",
            threshold_directory
            / f"{pipeline_version}_timing_forecast_discretized.png",
        )
        if args.reuse_threshold_projection and all(
            path.is_file() and path.stat().st_size > 0
            for path in threshold_artifacts
        ):
            print(
                "+ reusing validation-derived threshold projection: "
                + ", ".join(str(path) for path in threshold_artifacts),
                flush=True,
            )
        else:
            execute(
                python,
                PIPELINE / "validation_peak_threshold.py",
                "--validation-csv",
                PROJECT
                / "05_ensemble/timing/contextual_fold_fusion/contextual_fold_validation_predictions.csv",
                "--forecast-csv",
                PROJECT
                / "05_ensemble/timing/contextual_fold_fusion/contextual_fold_fusion_forecast.csv",
                "--output-dir",
                threshold_directory,
                "--score-column",
                threshold_projection.get(
                    "score_column",
                    "contextual_promoted_score_not_probability",
                ),
                "--interval-days",
                interval,
                "--weak-peak-minimum-retention",
                threshold_projection.get("weak_peak_minimum_retention", 0.72),
                "--minimum-event-recall",
                threshold_projection.get("minimum_event_recall", 1.0),
                "--dpi",
                config.get("report", {}).get("image_dpi", 600),
                "--figure-tag",
                pipeline_version,
            )
    magnitude = config.get("magnitude_recalibration")
    if magnitude:
        if recent_source is None:
            raise RuntimeError(
                "magnitude_recalibration requires data_snapshot.recent_japan_csv"
            )
        execute(
            python,
            PIPELINE / "conditional_magnitude_recalibration.py",
            "--project-dir", PROJECT,
            "--config-json", PROJECT / magnitude["config_json"],
            "--catalog-csv", catalog,
            "--recent-events-csv", recent_source,
            "--output-dir", PROJECT / magnitude["output_directory"],
        )

    location_master = PROJECT / "01_inputs/location_master.csv"
    prepare_location_arguments: list[object] = [
        "--catalog-csv", catalog,
        "--full-timing-master", full_master,
        "--compact-timing-master", compact_master,
        "--timing-safe-features", PROJECT / "01_inputs/v4_native_safe_features.json",
        "--bin-membership-csv", PROJECT / "02_audit/event_bin_membership.csv",
        "--output-master", location_master,
        "--output-safe-features", PROJECT / "01_inputs/v4_location_native_safe_features.json",
        "--output-audit-json", PROJECT / "02_audit/location_master_audit.json",
        "--forecast-start", forecast_start,
        "--forecast-end", forecast_end,
        "--map-latitude-min", bounds["latitude_min"],
        "--map-latitude-max", bounds["latitude_max"],
        "--map-longitude-min", bounds["longitude_min"],
        "--map-longitude-max", bounds["longitude_max"],
        "--anchor-date", anchor,
        "--interval-days", interval,
        "--catalog-outside-master-policy",
        config.get("catalog_outside_master_policy", "error"),
    ]
    if supplemental_location_source is not None:
        prepare_location_arguments.extend(
            [
                "--supplemental-catalog-csv", supplemental_location_source,
                "--supplemental-minimum-magnitude",
                location["indirect_validation_magnitude_threshold"],
            ]
        )
    execute(
        python, PIPELINE / "prepare_v14_location_master.py",
        *prepare_location_arguments,
    )
    location_hash = sha256(location_master)
    location_args = [
        "--interval-days", interval,
        "--magnitude-threshold", target_floor,
        "--validation-magnitude-threshold", location_validation_floor,
        "--validation-events", location["validation_events"],
        "--inner-validation-events", location["inner_validation_events"],
        "--indirect-validation-magnitude-threshold", location.get(
            "indirect_validation_magnitude_threshold", 0
        ),
        "--indirect-validation-events", location.get(
            "indirect_validation_events", 0
        ),
        "--minimum-validation-zones", location["minimum_validation_zones"],
        "--minimum-predictive-construction-events", location["minimum_predictive_construction_events"],
        "--minimum-zones", location["minimum_zones"],
        "--maximum-zones", location["maximum_zones"],
        "--minimum-zone-events", location["minimum_zone_events"],
        "--zone-catalog", REPO / "constant_explorer/japan_usgs_m6_1900_20260517.csv",
        "--zone-construction-magnitude-threshold", location["zone_construction_magnitude_threshold"],
        "--zone-catalog-start", "1900-01-01",
        "--map-latitude-min", bounds["latitude_min"],
        "--map-latitude-max", bounds["latitude_max"],
        "--map-longitude-min", bounds["longitude_min"],
        "--map-longitude-max", bounds["longitude_max"],
        "--feature-min", 5,
        "--probe-budget", timing["probe_budget"],
        "--probe-block-size", timing["probe_block_size"],
        "--quantile-bins", quantile_bins,
        "--forecast-grid-start", forecast_start,
        "--forecast-visible-start", forecast_start,
        "--forecast-end", forecast_end,
        "--expected-location-master-sha256", location_hash,
        "--expected-timing-master-sha256", master_hash,
    ]
    if model_overrides:
        location_args.extend(["--model-overrides-json", model_overrides])
    location_artifacts = (
        PROJECT / "05_ensemble/location_zone_summary.json",
        PROJECT / "05_ensemble/location_zone_validation.csv",
        PROJECT / "05_ensemble/location_zone_forecast.csv",
        PROJECT / "05_ensemble/location_zone_indirect_validation.json",
        PROJECT / "05_ensemble/location_zone_indirect_validation.csv",
        PROJECT / "07_randomized_control/location/summary.json",
        PROJECT / "07_randomized_control/location/completion.json",
        PROJECT / "05_ensemble/location_reliability_assessment.json",
        PROJECT / "05_ensemble/timing_location_joint_forecast.csv",
    )
    reuse_complete_location = args.reuse_location and all(
        path.is_file() and path.stat().st_size > 0
        for path in location_artifacts
    )
    if reuse_complete_location:
        print(
            "+ reusing complete location artifacts: "
            + ", ".join(str(path) for path in location_artifacts),
            flush=True,
        )
    else:
        execute(
            python,
            PIPELINE / "run_v14_location.py",
            *location_args,
            "--training-mode",
            "sequential",
        )
        execute(
            python, PIPELINE / "run_v14_location.py", *location_args,
            "--training-mode", "randomized", "--random-seed", location["random_seed"],
        )
    finalize_arguments: list[object] = [
        "--run-dir", PROJECT,
        "--small-sample-validation-threshold", location["small_sample_validation_threshold"],
        "--small-sample-reliability-cap", location["small_sample_reliability_cap"],
    ]
    if contextual:
        finalize_arguments.extend(
            [
                "--timing-forecast-csv",
                PROJECT
                / contextual["output_directory"]
                / "contextual_fold_fusion_forecast.csv",
                "--timing-score-column",
                "contextual_promoted_score_not_probability",
            ]
        )
    if not reuse_complete_location:
        execute(
            python,
            PIPELINE / "finalize_v14_location.py",
            *finalize_arguments,
        )
    if hyper_screen:
        execute(
            python,
            PIPELINE / "build_v17_diagnostics.py",
            "--project-dir", PROJECT,
            "--interval-days", interval,
            "--dpi", config["report"]["dpi"],
            "--figure-tag", pipeline_version,
            "--final-time-budget-seconds", timing.get(
                "final_attempt_time_limit_seconds", 0
            ),
        )
    frontier_arguments: list[object] = []
    if jpl.get("mode") == "direct_horizons_shifted_grid":
        frontier_arguments.extend(
            [
                "--jpl-manifest-json", PROJECT / jpl["manifest_json"],
                "--anchor-date", anchor,
                "--forecast-end", forecast_end,
            ]
        )
    else:
        frontier_arguments.extend(
            [
                "--source-frontier-json", REPO / "DB/japan-m79plus-60d-2026-2028-deephistory-v13/02_audit/jpl_history_frontier.json",
                "--derivation-json", PROJECT / "02_audit/master_180d_derivation.json",
            ]
        )
    execute(
        python, PIPELINE / "build_v14_frontier_audit.py",
        *frontier_arguments,
        "--catalog-csv", catalog,
        "--body-csv", PROJECT / "00_config/jpl_stable_body_set.csv",
        "--output-json", PROJECT / "02_audit/jpl_history_frontier.json",
    )
    if not contextual:
        execute(
            python, PIPELINE / "render_v14_timing_report.py",
            "--run-dir", PROJECT,
            "--output-dir", PROJECT / "06_report",
            "--report-stem", "V14_REPORT",
            "--figure-tag", "v14",
            "--report-title", "Japan M8.3+ mega-earthquake timing forecast — V14 180-day deep-history",
            "--region-label", "Japan",
            "--interval-days", interval,
            "--forecast-end", forecast_end,
            "--highlight-count", 4,
            "--top-table-count", 7,
            "--image-dpi", config["report"]["dpi"],
        )
    execute(python, PIPELINE / "build_v14_standard_report_inputs.py", "--project-dir", PROJECT)
    execute(
        python, STANDARD / "generate_standard_report.py",
        "--project-dir", PROJECT,
        "--repo-dir", REPO,
        "--template-pipeline-dir", STANDARD,
        "--python", python,
        "--report-config-json", PROJECT / config["report"]["config_json"],
    )
    if pipeline_version.startswith("v19"):
        execute(
            python,
            PIPELINE / "self_check_v19.py",
            "--project-dir", PROJECT,
        )
    elif pipeline_version.startswith("v18"):
        execute(
            python,
            PIPELINE / "self_check_v18.py",
            "--project-dir", PROJECT,
        )
    elif pipeline_version.startswith("v17"):
        execute(
            python,
            PIPELINE / "self_check_v17.py",
            "--project-dir", PROJECT,
        )
    elif contextual:
        execute(
            python,
            PIPELINE / "self_check_v15.py",
            "--project-dir", PROJECT,
        )
    else:
        execute(python, PIPELINE / "self_check_v14.py")


if __name__ == "__main__":
    main()
