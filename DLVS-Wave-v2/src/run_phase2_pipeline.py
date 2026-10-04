#!/usr/bin/env python3
"""Run and finalize CPU-only Phase 2 microstudies or their temporal ensemble.

The micro mode performs the deep-surrogate search and then deterministically
refits the overall winner (Phase 1 is retained when Phase 2 did not improve it)
to emit a complete validation/forecast/report subset.  Ensemble mode consumes
three such subsets and creates both classic and horizon-dependent forecasts.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.meta_optimizer.engine import DeepMetaOptimizer
from src.meta_optimizer.plotting import plot_phase2_convergence_report
from src.models.plotting import ForecastingVisualizer
from src.regenerate_optuna_study_reports import (
    _atomic_csv,
    _atomic_json,
    _compact_params,
    _global_ensemble_weights,
    _stage_for_date,
)
from src.temporal_validation import (
    build_progressive_horizon_metrics,
    compute_fixed_threshold_metrics,
    derive_temporal_ensemble_weights,
)

logger = logging.getLogger("dlvs_wave.phase2_pipeline")
MODELS = ("kan", "deep_learning", "lcs")


def _normalize_model(model_type: str) -> str:
    normalized = model_type.lower().strip()
    return "deep_learning" if normalized == "deep" else normalized


def _metrics_for_report(metrics: dict[str, Any]) -> dict[str, Any]:
    output = dict(metrics)
    output.setdefault("peak_timing_error", output.get("peak_timing_error_steps", 0.0))
    output.setdefault("peak_hit_rate", output.get("recall", 0.0))
    return output


def _selection_record(optimizer: DeepMetaOptimizer, winner: str) -> tuple[dict[str, Any], int]:
    if winner == "phase2":
        successful = optimizer._successful_meta_records()
        record = min(successful, key=lambda row: float(row["objective_loss"]))
        return record, int(record.get("meta_trial_number", 0))
    record = optimizer.phase1_best_record
    return record, int(record.get("trial_number", 0))


def _write_micro_readme(
    output_dir: Path,
    model_type: str,
    comparison: dict[str, Any],
    selection: dict[str, Any],
) -> None:
    phase2_loss = comparison["phase2"].get("best_objective_loss")
    phase2_text = f"{float(phase2_loss):.6f}" if phase2_loss is not None else "N/A"
    text = f"""# Phase 2 finalized subset — {model_type.upper()}

This directory is a self-contained second-level result selected from the Phase 1 and Phase 2 candidates.

- Compute: **CPU only** (`{comparison['actual_device']}`).
- Selection policy: **{selection['selection_policy']}**; finalized source: **{selection['selected_source']}**.
- Phase 1 objective: `{comparison['phase1']['best_objective_loss']:.6f}`.
- Phase 2 objective: `{phase2_text}`.
- Selected objective: `{selection['selected_objective_loss']:.6f}`.
- Training rows: `{selection['train_samples']}`; validation rows: `{selection['validation_samples']}`.
- Forecast rows: `{selection['forecast_samples']}`.

## Main artifacts

- `selected_best_params_{model_type}.json`: selected legal hyperparameters.
- `selected_best_metrics_{model_type}.json`: refitted validation metrics.
- `selected_train_pretreated_{model_type}.csv`: training subset used for the final refit.
- `selected_validation_{model_type}.csv`: dated actual/predicted validation rows.
- `selected_forecast_{model_type}.csv`: pure future projection.
- `selected_temporal_horizon_metrics_{model_type}.csv`: progressive horizon evidence.
- `phase2_selected_report.pdf`: validation, metrics, forecast and temporal-horizon pages.

`supported` in a temporal table means only that the declared historical backtest thresholds passed. It is not a guarantee of an earthquake or of future precision. Phase 2 reused the Phase 1 validation protocol for selection; an untouched later holdout remains necessary for unbiased confirmation.
"""
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def run_micro(args: argparse.Namespace) -> dict[str, Any]:
    model_type = _normalize_model(args.model_type)
    if model_type not in MODELS:
        raise ValueError(f"Unsupported model type: {args.model_type}")
    if args.device != "cpu":
        raise ValueError("This Phase 2 launcher is intentionally CPU-only; use --device cpu")

    phase1_dir = Path(args.phase1_dir).resolve()
    trials_path = (
        Path(args.input_trials_csv).resolve()
        if args.input_trials_csv
        else phase1_dir / f"optuna_trials_{model_type}.csv"
    )
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else phase1_dir / "phase2_deep_meta_opt"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    total_started = time.monotonic()
    reserve = min(max(0.0, args.finalization_reserve_seconds), max(0.0, args.timeout_seconds - 1.0))
    search_timeout = max(1.0, args.timeout_seconds - reserve)

    optimizer = DeepMetaOptimizer(
        input_trials_csv=trials_path,
        master_df=args.input_master,
        model_type=model_type,
        target_col=args.target_col,
        min_mag_threshold=args.peak_threshold,
        eval_events=args.eval_events,
        timeout_seconds=search_timeout,
        output_dir=output_dir,
        device="cpu",
        retrain_frequency=args.retrain_frequency,
        seed=args.seed,
        max_meta_trials=args.max_meta_trials,
        surrogate_epochs=args.surrogate_epochs,
        retrain_epochs=args.retrain_epochs,
        candidate_batch_size=args.candidate_batch_size,
        model_epochs=args.model_epochs,
        resume=not args.no_resume,
    )
    optimizer.run()
    comparison_path = output_dir / f"phase2_comparison_{model_type}.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    if args.selection_policy == "phase2":
        if comparison["phase2"].get("best_params") is None:
            raise RuntimeError("--selection-policy phase2 requires at least one successful Phase 2 candidate")
        selected_source = "phase2"
        selected_params = dict(comparison["phase2"]["best_params"])
        selected_objective = float(comparison["phase2"]["best_objective_loss"])
    else:
        selected_source = str(comparison["overall_winner"])
        selected_params = dict(comparison["overall_best_params"])
        selected_objective = float(comparison["overall_best_objective_loss"])
    selected_record, selected_trial_number = _selection_record(optimizer, selected_source)

    # Reuse the candidate's deterministic trial seed so the final validation
    # and future model are traceable to the selected configuration.
    train_metrics, validation_metrics, evaluated, result, model = optimizer._fit_and_evaluate(
        selected_params, selected_trial_number
    )
    date_col = str(result.metadata.get("date_col", "date"))
    if date_col not in result.eval_df.columns:
        date_col = result.eval_df.columns[0]
    validation = pd.DataFrame(
        {
            "date": result.eval_df[date_col].values,
            "actual": evaluated["actual"].values,
            f"predicted_{args.target_col}": evaluated["predicted"].values,
            "error": evaluated["error"].values,
            "abs_error": evaluated["abs_error"].values,
        }
    )

    master = pd.read_csv(args.input_master, low_memory=False)
    master_date_col = "date" if "date" in master.columns else master.columns[0]
    master[master_date_col] = pd.to_datetime(master[master_date_col])
    master.sort_values(master_date_col, inplace=True)
    future = master.loc[master[master_date_col] > pd.to_datetime(validation["date"]).max()].head(args.forecast_steps)
    if len(future) == 0:
        raise ValueError("No rows exist after the selected validation interval; cannot create a future forecast")
    missing = [column for column in model.feature_names if column not in future.columns]
    if missing:
        raise ValueError(f"Master lacks fitted forecast features: {missing[:8]}")
    forecast = pd.DataFrame(
        {
            "date": future[master_date_col].values,
            f"forecasted_{args.target_col}": model.predict(future[model.feature_names]),
        }
    )
    horizons = build_progressive_horizon_metrics(
        validation,
        forecast,
        peak_threshold=args.peak_threshold,
        max_events=args.eval_events,
        window_span=args.eval_window_span,
    )

    params_path = output_dir / f"selected_best_params_{model_type}.json"
    metrics_path = output_dir / f"selected_best_metrics_{model_type}.json"
    train_path = output_dir / f"selected_train_pretreated_{model_type}.csv"
    validation_path = output_dir / f"selected_validation_{model_type}.csv"
    forecast_path = output_dir / f"selected_forecast_{model_type}.csv"
    horizon_path = output_dir / f"selected_temporal_horizon_metrics_{model_type}.csv"
    _atomic_json(selected_params, params_path)
    _atomic_json(_metrics_for_report(validation_metrics.to_dict()), metrics_path)
    _atomic_csv(result.train_df, train_path)
    _atomic_csv(validation, validation_path)
    _atomic_csv(forecast, forecast_path)
    _atomic_csv(horizons, horizon_path)
    _atomic_json(horizons.to_dict(orient="records"), horizon_path.with_suffix(".json"))

    selection = {
        "model_type": model_type,
        "selection_policy": args.selection_policy,
        "selected_source": selected_source,
        "selected_trial_number": selected_trial_number,
        "selected_objective_loss": selected_objective,
        "selected_record_objective_loss": float(selected_record["objective_loss"]),
        "train_samples": len(result.train_df),
        "validation_samples": len(validation),
        "forecast_samples": len(forecast),
        "train_metrics": train_metrics.to_dict(),
        "validation_metrics": validation_metrics.to_dict(),
        "elapsed_seconds": time.monotonic() - total_started,
        "requested_timeout_seconds": args.timeout_seconds,
        "search_timeout_seconds": search_timeout,
        "device": "cpu",
    }
    _atomic_json(selection, output_dir / f"selected_manifest_{model_type}.json")

    visualizer = ForecastingVisualizer(dpi=args.dpi)
    render_kwargs = dict(
        input_csv_or_df=validation,
        training_csv_or_df=result.train_df,
        metrics_dict_or_path=_metrics_for_report(validation_metrics.to_dict()),
        forecast_csv_or_df=forecast,
        temporal_metrics_csv_or_df=horizons,
        temporal_forecast_csv_or_df=forecast,
        title=f"DLVS-Wave Phase 2 Selected {model_type.upper()} Report",
        subtitle=(
            f"ROI: {args.roi_name} | source={selected_source}; policy={args.selection_policy}; "
            f"objective={selected_objective:.6f}; {_compact_params(model_type, selected_params)}"
        ),
        target_name=args.target_col,
        roi_name=args.roi_name,
        model_name=f"{model_type.upper()} Phase 2 selected",
        eval_window_mode="corridors",
        eval_max_events=args.eval_events,
        eval_min_mag=args.peak_threshold,
        eval_window_span=args.eval_window_span,
        forecast_peak_min=args.forecast_peak_min,
        forecast_max_peak_labels=args.forecast_max_peak_labels,
    )
    for suffix in ("png", "pdf"):
        figure = visualizer.render(output_path=output_dir / f"phase2_selected_report.{suffix}", **render_kwargs)
        plt.close(figure)
    if optimizer._successful_meta_records():
        plot_phase2_convergence_report(
            phase1_trials_csv=trials_path,
            phase2_dir=output_dir,
            model_type=model_type,
            output_png=output_dir / f"phase2_{model_type}_convergence_report.png",
            output_pdf=output_dir / f"phase2_{model_type}_convergence_report.pdf",
        )
    _write_micro_readme(output_dir, model_type, comparison, selection)
    logger.info("Finalized %s Phase 2 subset in %s", model_type, output_dir)
    return {"output_dir": str(output_dir), "selection": selection}


def _resolve_subset(directory: str | Path, model_type: str) -> Path:
    supplied = Path(directory).resolve()
    candidates = (supplied, supplied / "phase2_deep_meta_opt")
    filename = f"selected_validation_{model_type}.csv"
    for candidate in candidates:
        if (candidate / filename).exists():
            return candidate
    raise FileNotFoundError(f"Could not find {filename} in {supplied} or its phase2_deep_meta_opt child")


def _load_phase2_members(args: argparse.Namespace) -> tuple[
    dict[str, Path], dict[str, pd.DataFrame], dict[str, pd.DataFrame],
    dict[str, pd.DataFrame], dict[str, dict[str, Any]],
]:
    supplied = {
        "kan": args.kan_dir,
        "deep_learning": args.deep_learning_dir,
        "lcs": args.lcs_dir,
    }
    roots: dict[str, Path] = {}
    validations: dict[str, pd.DataFrame] = {}
    forecasts: dict[str, pd.DataFrame] = {}
    horizons: dict[str, pd.DataFrame] = {}
    metrics: dict[str, dict[str, Any]] = {}
    for model_type in MODELS:
        root = _resolve_subset(supplied[model_type], model_type)
        roots[model_type] = root
        validations[model_type] = pd.read_csv(root / f"selected_validation_{model_type}.csv")
        forecasts[model_type] = pd.read_csv(root / f"selected_forecast_{model_type}.csv")
        horizons[model_type] = pd.read_csv(root / f"selected_temporal_horizon_metrics_{model_type}.csv")
        metrics[model_type] = json.loads(
            (root / f"selected_best_metrics_{model_type}.json").read_text(encoding="utf-8")
        )
    return roots, validations, forecasts, horizons, metrics


def _align_member_streams(
    frames: dict[str, pd.DataFrame], prefix: str, actual: bool = False
) -> pd.DataFrame:
    first = MODELS[0]
    base_columns = ["date", "actual"] if actual else ["date"]
    merged = frames[first][base_columns].copy()
    merged["date"] = pd.to_datetime(merged["date"])
    for model_type, frame in frames.items():
        local = frame.copy()
        local["date"] = pd.to_datetime(local["date"])
        source_col = next(column for column in local.columns if column.startswith(prefix))
        merged = merged.merge(
            local[["date", source_col]].rename(columns={source_col: f"{prefix}{model_type}"}),
            on="date",
            how="inner",
        )
    if len(merged) == 0:
        raise ValueError("Phase 2 member streams have no dates in common")
    return merged


def _temporal_validation(
    merged: pd.DataFrame,
    weights: pd.DataFrame,
    validation_boundaries: pd.Series,
    target_col: str,
) -> pd.DataFrame:
    values: list[float] = []
    stages: list[int] = []
    for _, row in merged.iterrows():
        stage_index = _stage_for_date(pd.Timestamp(row["date"]), validation_boundaries)
        weight_row = weights.iloc[stage_index]
        values.append(sum(float(weight_row[f"weight_{model}"]) * float(row[f"predicted_{model}"]) for model in MODELS))
        stages.append(stage_index + 1)
    output = merged[["date", "actual"]].copy()
    output[f"predicted_{target_col}"] = values
    output["temporal_weight_stage"] = stages
    output["residual_gap"] = np.abs(output["actual"] - output[f"predicted_{target_col}"])
    return output


def _write_ensemble_readme(
    output_dir: Path,
    roots: dict[str, Path],
    global_weights: dict[str, float],
) -> None:
    source_lines = "\n".join(f"- `{model}`: `{root}`" for model, root in roots.items())
    weight_lines = ", ".join(f"{model}={weight:.4f}" for model, weight in global_weights.items())
    text = f"""# Phase 2 temporal ensemble

This subset was built automatically from three finalized Phase 2 model directories.

## Inputs

{source_lines}

Global validation weights: `{weight_lines}`.

## Outputs

- `ensemble_validation_comparison.csv` and `ensemble_metrics.json`: classic weighted validation.
- `ensemble_pure_future_forecast.csv`: classic future projection.
- `ensemble_temporal_validation_comparison.csv`: stage-dependent validation.
- `ensemble_temporal_weights.csv`: weights learned independently for every progressive horizon.
- `ensemble_temporal_staged_forecast.csv`: validation-equivalent stage weights translated into forecast time.
- `ensemble_temporal_horizon_metrics.csv`: support/non-support evidence per horizon.
- `phase2_ensemble_report.pdf`: four-page validation and forecast report.

Temporal support is historical backtest evidence, not a guarantee of future seismic events. Stages that fail the declared recall, magnitude and timing thresholds remain explicitly marked as unsupported.
"""
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def run_ensemble(args: argparse.Namespace) -> dict[str, Any]:
    roots, validations, forecasts, horizons, model_metrics = _load_phase2_members(args)
    output_dir = Path(args.ensemble_output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    global_weights = _global_ensemble_weights(model_metrics)

    merged_validation = _align_member_streams(validations, "predicted_", actual=True)
    ensemble_prediction = sum(
        global_weights[model] * merged_validation[f"predicted_{model}"] for model in MODELS
    )
    classic_validation = merged_validation[["date", "actual"]].copy()
    classic_validation[f"predicted_{args.target_col}"] = ensemble_prediction
    classic_validation["residual_gap"] = np.abs(classic_validation["actual"] - ensemble_prediction)
    classic_metrics = _metrics_for_report(
        compute_fixed_threshold_metrics(
            classic_validation["actual"], ensemble_prediction, peak_threshold=args.peak_threshold
        )
    )

    member_forecast = _align_member_streams(forecasts, "forecasted_", actual=False)
    member_forecast[f"forecasted_{args.target_col}"] = sum(
        global_weights[model] * member_forecast[f"forecasted_{model}"] for model in MODELS
    )
    classic_forecast = member_forecast[["date", f"forecasted_{args.target_col}"]].copy()
    temporal_weights = derive_temporal_ensemble_weights(horizons)
    validation_boundaries = pd.to_datetime(horizons[MODELS[0]]["window_end_date"])
    temporal_validation = _temporal_validation(
        merged_validation, temporal_weights, pd.Series(validation_boundaries), args.target_col
    )

    staged = member_forecast.copy()
    staged_values: list[float] = []
    stages: list[int] = []
    for _, row in staged.iterrows():
        stage_index = _stage_for_date(
            pd.Timestamp(row["date"]), temporal_weights["forecast_equivalent_end_date"]
        )
        weight_row = temporal_weights.iloc[stage_index]
        staged_values.append(
            sum(float(weight_row[f"weight_{model}"]) * float(row[f"forecasted_{model}"]) for model in MODELS)
        )
        stages.append(stage_index + 1)
    staged["forecasted_classic_ensemble"] = classic_forecast[f"forecasted_{args.target_col}"].to_numpy()
    staged["forecasted_temporal_ensemble"] = staged_values
    staged["horizon_stage"] = stages

    ensemble_horizons = build_progressive_horizon_metrics(
        temporal_validation,
        staged[["date", "forecasted_temporal_ensemble"]],
        peak_threshold=args.peak_threshold,
        max_events=args.eval_events,
        window_span=args.eval_window_span,
    )
    support = {int(row["stage"]): bool(row["consecutive_supported"]) for _, row in ensemble_horizons.iterrows()}
    final_boundary = pd.to_datetime(ensemble_horizons["forecast_equivalent_end_date"]).max()
    staged["certification_status"] = [
        (
            "validation_supported_equivalent_horizon"
            if pd.Timestamp(date) <= final_boundary and support.get(stage, False)
            else "tested_stage_not_supported"
            if pd.Timestamp(date) <= final_boundary
            else "uncertified_extrapolation"
        )
        for date, stage in zip(staged["date"], staged["horizon_stage"])
    ]

    _atomic_csv(classic_validation, output_dir / "ensemble_validation_comparison.csv")
    _atomic_json(classic_metrics, output_dir / "ensemble_metrics.json")
    _atomic_csv(member_forecast, output_dir / "ensemble_member_forecasts.csv")
    _atomic_csv(classic_forecast, output_dir / "ensemble_pure_future_forecast.csv")
    _atomic_csv(temporal_validation, output_dir / "ensemble_temporal_validation_comparison.csv")
    _atomic_csv(temporal_weights, output_dir / "ensemble_temporal_weights.csv")
    _atomic_csv(staged, output_dir / "ensemble_temporal_staged_forecast.csv")
    _atomic_csv(ensemble_horizons, output_dir / "ensemble_temporal_horizon_metrics.csv")
    _atomic_json(ensemble_horizons.to_dict(orient="records"), output_dir / "ensemble_temporal_horizon_metrics.json")

    training = pd.read_csv(roots["kan"] / "selected_train_pretreated_kan.csv", low_memory=False)
    visualizer = ForecastingVisualizer(dpi=args.dpi)
    weight_text = ", ".join(f"{model}={weight:.2f}" for model, weight in global_weights.items())
    report_forecast = staged[["date", "forecasted_classic_ensemble", "forecasted_temporal_ensemble"]]
    render_kwargs = dict(
        input_csv_or_df=classic_validation,
        training_csv_or_df=training,
        metrics_dict_or_path=classic_metrics,
        forecast_csv_or_df=classic_forecast,
        temporal_metrics_csv_or_df=ensemble_horizons,
        temporal_forecast_csv_or_df=report_forecast,
        title="DLVS-Wave Phase 2 Weighted Temporal Ensemble",
        subtitle=f"ROI: {args.roi_name} | global weights: {weight_text}",
        target_name=args.target_col,
        roi_name=args.roi_name,
        model_name="Phase 2 ensemble",
        eval_window_mode="corridors",
        eval_max_events=args.eval_events,
        eval_min_mag=args.peak_threshold,
        eval_window_span=args.eval_window_span,
        forecast_peak_min=args.forecast_peak_min,
        forecast_max_peak_labels=args.forecast_max_peak_labels,
    )
    for suffix in ("png", "pdf"):
        figure = visualizer.render(output_path=output_dir / f"phase2_ensemble_report.{suffix}", **render_kwargs)
        plt.close(figure)
    _write_ensemble_readme(output_dir, roots, global_weights)
    logger.info("Created Phase 2 ensemble in %s", output_dir)
    return {"output_dir": str(output_dir), "global_weights": global_weights}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CPU-only Phase 2 microstudy finalizer and optional temporal ensemble",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--make-ensemble", action="store_true", help="Build the Phase 2 ensemble instead of running one microstudy")
    parser.add_argument("--phase1-dir", help="Phase 1 microstudy directory")
    parser.add_argument("--input-trials-csv", help="Optional explicit Phase 1 trials CSV")
    parser.add_argument("--input-master", help="Packed summarized master CSV")
    parser.add_argument("--model-type", choices=["kan", "deep_learning", "deep", "lcs"])
    parser.add_argument("--output-dir", help="Nested Phase 2 microstudy output directory")
    parser.add_argument("--timeout-seconds", type=float, default=2400.0, help="Total microstudy budget; three defaults total 7200 seconds")
    parser.add_argument("--finalization-reserve-seconds", type=float, default=300.0, help="Time reserved from the budget for winner refit and reports")
    parser.add_argument("--device", choices=["cpu"], default="cpu")
    parser.add_argument(
        "--selection-policy", choices=["phase2", "overall"], default="phase2",
        help="Finalize the best Phase 2 candidate even when Phase 1 scored better, or retain the overall winner",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-meta-trials", type=int)
    parser.add_argument("--candidate-batch-size", type=int, default=4)
    parser.add_argument("--retrain-frequency", type=int, default=5)
    parser.add_argument("--surrogate-epochs", type=int, default=100)
    parser.add_argument("--retrain-epochs", type=int, default=40)
    parser.add_argument("--model-epochs", type=int, help="Final and candidate training epoch override, primarily for smoke tests")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--forecast-steps", type=int, default=150)
    parser.add_argument("--eval-events", type=int, default=3)
    parser.add_argument("--eval-window-span", type=int, default=4)
    parser.add_argument("--target-col", default="seis_core_magnitude")
    parser.add_argument("--peak-threshold", type=float, default=6.9)
    parser.add_argument("--forecast-peak-min", type=float, default=6.0)
    parser.add_argument("--forecast-max-peak-labels", type=int, default=8)
    parser.add_argument("--roi-name", default="Japan Area (7D Compacted Astro)")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--kan-dir", help="KAN Phase 2 directory or its Phase 1 parent")
    parser.add_argument("--deep-learning-dir", help="Deep-learning Phase 2 directory or its Phase 1 parent")
    parser.add_argument("--lcs-dir", help="LCS Phase 2 directory or its Phase 1 parent")
    parser.add_argument("--ensemble-output-dir", help="Directory to create for the Phase 2 ensemble")
    return parser


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.make_ensemble:
        required = {
            "--kan-dir": args.kan_dir,
            "--deep-learning-dir": args.deep_learning_dir,
            "--lcs-dir": args.lcs_dir,
            "--ensemble-output-dir": args.ensemble_output_dir,
        }
    else:
        required = {
            "--phase1-dir": args.phase1_dir,
            "--input-master": args.input_master,
            "--model-type": args.model_type,
        }
        if args.timeout_seconds <= 0 or args.timeout_seconds > 7200:
            parser.error("--timeout-seconds must be in (0, 7200]")
    missing = [name for name, value in required.items() if not value]
    if missing:
        parser.error(f"Missing required arguments: {', '.join(missing)}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_args(parser, args)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    result = run_ensemble(args) if args.make_ensemble else run_micro(args)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
