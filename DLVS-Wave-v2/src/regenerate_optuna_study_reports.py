#!/usr/bin/env python3
"""Regenerate Optuna microstudy and ensemble reports with forecast horizons.

Existing winning validation streams remain the source of validation evidence.
Because the historical run did not persist model checkpoints, each winning
model is deterministically refitted on its saved pretreated training set solely
to produce the missing pure-future forecast page.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from models.deep_learning import DeepLearningForecastingModel
from models.kan import KANForecastingModel
from models.lcs import LCSForecastingModel
from models.plotting import ForecastingVisualizer
from temporal_validation import build_progressive_horizon_metrics, derive_temporal_ensemble_weights

logger = logging.getLogger("dlvs_wave.report_regenerator")
MODEL_TYPES = ("kan", "deep_learning", "lcs")
DEFAULT_EPOCHS = {"kan": 50, "deep_learning": 60, "lcs": 30}


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    os.replace(temporary, path)


def _atomic_json(payload: dict[str, Any] | list[dict[str, Any]], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
    os.replace(temporary, path)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _make_model(model_type: str, params: dict[str, Any], device: str):
    if model_type == "kan":
        return KANForecastingModel(
            grid_size=int(params["grid_size"]), spline_order=int(params["spline_order"]),
            learning_rate=float(params["learning_rate"]), device=device,
        )
    if model_type == "deep_learning":
        return DeepLearningForecastingModel(
            hidden_dim=int(params["hidden_dim"]), num_layers=int(params["num_layers"]),
            dropout=float(params["dropout"]), learning_rate=float(params["learning_rate"]), device=device,
        )
    return LCSForecastingModel(
        population_size=int(params["population_size"]), learning_rate=float(params["learning_rate"]),
        crossover_rate=float(params["crossover_rate"]), mutation_rate=float(params["mutation_rate"]),
    )


def _model_feature_columns(training: pd.DataFrame, target_col: str) -> list[str]:
    excluded = {"date", "datetime", "time", target_col}
    return [
        column for column in training.columns
        if column not in excluded and pd.api.types.is_numeric_dtype(training[column])
    ]


def _global_ensemble_weights(metrics_by_model: dict[str, dict[str, Any]]) -> dict[str, float]:
    raw = {
        model: (float(metrics.get("f1_score", 0.0)) + 0.1) / (float(metrics.get("mse", 1.0)) + 1e-4)
        for model, metrics in metrics_by_model.items()
    }
    denominator = sum(raw.values())
    return {model: value / denominator for model, value in raw.items()}


def _compact_params(model_type: str, params: dict[str, Any]) -> str:
    shared = (
        f"train={params.get('train_start_date')}, W={params.get('window_before')}/{params.get('window_after')}, "
        f"background={float(params.get('background_sample_ratio', 0.0)):.2f}"
    )
    if model_type == "kan":
        specific = (
            f"grid={params.get('grid_size')}, spline={params.get('spline_order')}, "
            f"lr={float(params.get('learning_rate', 0.0)):.5g}"
        )
    elif model_type == "deep_learning":
        specific = (
            f"hidden={params.get('hidden_dim')}, layers={params.get('num_layers')}, "
            f"dropout={float(params.get('dropout', 0.0)):.2f}, lr={float(params.get('learning_rate', 0.0)):.5g}"
        )
    else:
        specific = (
            f"population={params.get('population_size')}, lr={float(params.get('learning_rate', 0.0)):.2f}, "
            f"crossover={float(params.get('crossover_rate', 0.0)):.2f}, mutation={float(params.get('mutation_rate', 0.0)):.2f}"
        )
    return f"{shared}; {specific}"


def _stage_for_date(date: pd.Timestamp, boundaries: pd.Series) -> int:
    parsed = pd.to_datetime(boundaries).tolist()
    for index, boundary in enumerate(parsed):
        if date <= boundary:
            return index
    return len(parsed) - 1


def _temporal_ensemble_validation(
    validations: dict[str, pd.DataFrame], weights: pd.DataFrame, target_col: str
) -> pd.DataFrame:
    reference = validations["kan"][["date", "actual"]].copy()
    reference["date"] = pd.to_datetime(reference["date"])
    merged = reference
    prediction_columns: dict[str, str] = {}
    for model, frame in validations.items():
        local = frame.copy()
        local["date"] = pd.to_datetime(local["date"])
        prediction = next(column for column in local.columns if column.startswith("predicted_"))
        renamed = f"predicted_{model}"
        prediction_columns[model] = renamed
        merged = merged.merge(local[["date", prediction]].rename(columns={prediction: renamed}), on="date", how="inner")
    boundaries = pd.to_datetime(weights["forecast_equivalent_end_date"])
    # Validation stage assignment uses the corresponding validation window end, not forecast dates.
    validation_boundaries = pd.to_datetime(
        next(iter(validations.values())).attrs.get("validation_window_end_dates", [])
    )
    if not len(validation_boundaries):
        raise ValueError("Validation window boundaries were not attached")
    predictions: list[float] = []
    stages: list[int] = []
    for _, row in merged.iterrows():
        stage_index = _stage_for_date(pd.Timestamp(row["date"]), pd.Series(validation_boundaries))
        weight_row = weights.iloc[stage_index]
        prediction = sum(float(weight_row[f"weight_{model}"]) * float(row[column]) for model, column in prediction_columns.items())
        predictions.append(prediction)
        stages.append(stage_index + 1)
    output = merged[["date", "actual"]].copy()
    output[f"predicted_{target_col}"] = predictions
    output["temporal_weight_stage"] = stages
    output["residual_gap"] = np.abs(output["actual"] - output[f"predicted_{target_col}"])
    return output


def regenerate_existing_study_reports(
    study_dir: str | Path,
    input_master: str | Path,
    target_col: str = "seis_core_magnitude",
    peak_threshold: float = 6.9,
    eval_events: int = 3,
    forecast_steps: int = 150,
    device: str = "cpu",
    seed: int = 42,
    model_epochs_override: int | None = None,
    roi_name: str = "Japan Area (7D Compacted Astro)",
) -> dict[str, Any]:
    """Refit winners, add micro forecasts, and rebuild four-page reports."""
    root = Path(study_dir)
    master = pd.read_csv(input_master, low_memory=False)
    date_col = "date" if "date" in master.columns else master.columns[0]
    master[date_col] = pd.to_datetime(master[date_col])
    master.sort_values(date_col, inplace=True)
    master.reset_index(drop=True, inplace=True)
    visualizer = ForecastingVisualizer(dpi=300)

    validations: dict[str, pd.DataFrame] = {}
    forecasts: dict[str, pd.DataFrame] = {}
    temporal_metrics: dict[str, pd.DataFrame] = {}
    global_metrics: dict[str, dict[str, Any]] = {}
    report_paths: dict[str, str] = {}

    for model_index, model_type in enumerate(MODEL_TYPES):
        model_dir = root / f"study_{model_type}"
        validation_path = model_dir / f"best_validation_{model_type}.csv"
        training_path = model_dir / f"best_train_pretreated_{model_type}.csv"
        params_path = model_dir / f"best_params_{model_type}.json"
        metrics_path = model_dir / f"best_metrics_{model_type}.json"
        for path in (validation_path, training_path, params_path, metrics_path):
            if not path.exists():
                raise FileNotFoundError(f"Required microstudy artifact is missing: {path}")

        validation = pd.read_csv(validation_path)
        training = pd.read_csv(training_path, low_memory=False)
        params = _load_json(params_path)
        metrics = _load_json(metrics_path)
        validation["date"] = pd.to_datetime(validation["date"])
        training_date_col = "date" if "date" in training.columns else training.columns[0]
        training[training_date_col] = pd.to_datetime(training[training_date_col])
        features = _model_feature_columns(training, target_col)
        if not features:
            raise ValueError(f"No numeric features found for {model_type}")

        np.random.seed(seed + model_index)
        torch.manual_seed(seed + model_index)
        model = _make_model(model_type, params, device)
        epochs = model_epochs_override if model_epochs_override is not None else DEFAULT_EPOCHS[model_type]
        logger.info("Refitting %s winner on %s for %d epochs", model_type, device, epochs)
        model.fit(
            training[features], training[target_col], feature_names=features,
            target_name=target_col, epochs=epochs,
        )

        validation_end = validation["date"].max()
        future = master.loc[master[date_col] > validation_end].head(forecast_steps).copy()
        missing = [column for column in model.feature_names if column not in future.columns]
        if missing:
            raise ValueError(f"Master lacks {len(missing)} fitted features for {model_type}: {missing[:5]}")
        prediction = model.predict(future[model.feature_names])
        forecast = pd.DataFrame(
            {"date": future[date_col].values, f"forecasted_{target_col}": prediction}
        )
        forecast_path = model_dir / f"best_forecast_{model_type}.csv"
        _atomic_csv(forecast, forecast_path)

        horizon_metrics = build_progressive_horizon_metrics(
            validation,
            forecast,
            peak_threshold=peak_threshold,
            max_events=eval_events,
            window_span=4,
        )
        horizon_path = model_dir / f"temporal_horizon_metrics_{model_type}.csv"
        _atomic_csv(horizon_metrics, horizon_path)
        _atomic_json(horizon_metrics.to_dict(orient="records"), model_dir / f"temporal_horizon_metrics_{model_type}.json")

        report_png = model_dir / f"study_{model_type}_report.png"
        report_pdf = model_dir / f"study_{model_type}_report.pdf"
        common_render = dict(
            input_csv_or_df=validation,
            training_csv_or_df=training,
            metrics_dict_or_path=metrics,
            forecast_csv_or_df=forecast,
            temporal_metrics_csv_or_df=horizon_metrics,
            temporal_forecast_csv_or_df=forecast,
            title=f"DLVS-Wave v2.0 Microstudy: {model_type.upper()} Validation Report",
            subtitle=f"ROI: {roi_name} | Best Params: {_compact_params(model_type, params)}",
            target_name=target_col,
            roi_name=roi_name,
            model_name=model_type.upper(),
            eval_window_mode="corridors",
            eval_max_events=eval_events,
            eval_min_mag=peak_threshold,
            show_eval_dot_tags=True,
            show_train_dot_tags=True,
        )
        figure = visualizer.render(output_path=report_png, **common_render)
        plt.close(figure)
        figure = visualizer.render(output_path=report_pdf, **common_render)
        plt.close(figure)

        validations[model_type] = validation
        validations[model_type].attrs["validation_window_end_dates"] = horizon_metrics["window_end_date"].tolist()
        forecasts[model_type] = forecast
        temporal_metrics[model_type] = horizon_metrics
        global_metrics[model_type] = metrics
        report_paths[model_type] = str(report_pdf)

    ensemble_dir = root / "ensemble"
    ensemble_dir.mkdir(parents=True, exist_ok=True)
    global_weights = _global_ensemble_weights(global_metrics)
    member_forecast = forecasts["kan"][["date"]].copy()
    for model_type, forecast in forecasts.items():
        prediction_col = next(column for column in forecast.columns if column.startswith("forecasted_"))
        member_forecast[f"forecasted_{model_type}"] = forecast[prediction_col].to_numpy()
    member_forecast[f"forecasted_{target_col}"] = sum(
        global_weights[model] * member_forecast[f"forecasted_{model}"] for model in MODEL_TYPES
    )
    classic_forecast = member_forecast[["date", f"forecasted_{target_col}"]].copy()
    _atomic_csv(classic_forecast, ensemble_dir / "ensemble_pure_future_forecast.csv")
    _atomic_csv(member_forecast, ensemble_dir / "ensemble_member_forecasts.csv")
    classic_title = "DLVS-Wave v2.0 Weighted Multi-Model Pure Future Forecast Trajectory"
    classic_subtitle = (
        f"ROI: {roi_name} | Global weights: KAN={global_weights['kan']:.2f}, "
        f"Deep={global_weights['deep_learning']:.2f}, LCS={global_weights['lcs']:.2f}"
    )
    for classic_path in (
        ensemble_dir / "ensemble_future_forecast_plot.png",
        ensemble_dir / "ensemble_future_forecast_plot.pdf",
    ):
        figure = visualizer.render(
            input_csv_or_df=classic_forecast,
            output_path=classic_path,
            title=classic_title,
            subtitle=classic_subtitle,
            target_name=target_col,
            roi_name=roi_name,
            model_name="Weighted Multi-Model Ensemble",
            eval_window_mode="continuous",
        )
        plt.close(figure)

    weights = derive_temporal_ensemble_weights(temporal_metrics)
    # Attach true validation-window boundaries for temporal validation assignment.
    reference_boundaries = temporal_metrics["kan"]["window_end_date"].tolist()
    for frame in validations.values():
        frame.attrs["validation_window_end_dates"] = reference_boundaries
    temporal_validation = _temporal_ensemble_validation(validations, weights, target_col)
    _atomic_csv(temporal_validation, ensemble_dir / "ensemble_temporal_validation_comparison.csv")
    _atomic_csv(weights, ensemble_dir / "ensemble_temporal_weights.csv")

    staged_forecast = member_forecast.copy()
    staged_values: list[float] = []
    stages: list[int] = []
    for _, row in staged_forecast.iterrows():
        stage_index = _stage_for_date(pd.Timestamp(row["date"]), weights["forecast_equivalent_end_date"])
        weight_row = weights.iloc[stage_index]
        staged_values.append(
            sum(float(weight_row[f"weight_{model}"]) * float(row[f"forecasted_{model}"]) for model in MODEL_TYPES)
        )
        stages.append(stage_index + 1)
    staged_forecast["forecasted_classic_ensemble"] = classic_forecast[f"forecasted_{target_col}"].to_numpy()
    staged_forecast["forecasted_temporal_ensemble"] = staged_values
    staged_forecast["horizon_stage"] = stages

    temporal_validation_for_metrics = temporal_validation.rename(
        columns={f"predicted_{target_col}": f"predicted_temporal_{target_col}"}
    )
    ensemble_horizon_metrics = build_progressive_horizon_metrics(
        temporal_validation_for_metrics,
        staged_forecast[["date", "forecasted_temporal_ensemble"]],
        peak_threshold=peak_threshold,
        max_events=eval_events,
        window_span=4,
    )
    support_by_stage = {
        int(row["stage"]): bool(row["consecutive_supported"])
        for _, row in ensemble_horizon_metrics.iterrows()
    }
    final_boundary = pd.to_datetime(ensemble_horizon_metrics["forecast_equivalent_end_date"]).max()
    staged_forecast["certification_status"] = [
        (
            "validation_supported_equivalent_horizon"
            if pd.Timestamp(date) <= final_boundary and support_by_stage.get(stage, False)
            else "tested_stage_not_supported"
            if pd.Timestamp(date) <= final_boundary
            else "uncertified_extrapolation"
        )
        for date, stage in zip(staged_forecast["date"], staged_forecast["horizon_stage"])
    ]
    _atomic_csv(staged_forecast, ensemble_dir / "ensemble_temporal_staged_forecast.csv")
    _atomic_csv(ensemble_horizon_metrics, ensemble_dir / "ensemble_temporal_horizon_metrics.csv")
    _atomic_json(
        ensemble_horizon_metrics.to_dict(orient="records"),
        ensemble_dir / "ensemble_temporal_horizon_metrics.json",
    )

    ensemble_validation_path = ensemble_dir / "ensemble_validation_comparison.csv"
    ensemble_metrics_path = ensemble_dir / "ensemble_metrics.json"
    ensemble_validation = pd.read_csv(ensemble_validation_path)
    ensemble_metrics_global = _load_json(ensemble_metrics_path)
    ensemble_render_forecast = staged_forecast[
        ["date", "forecasted_classic_ensemble", "forecasted_temporal_ensemble"]
    ].copy()
    ensemble_title = "DLVS-Wave v2.0 Weighted Multi-Model Ensemble Report"
    ensemble_subtitle = (
        f"ROI: {roi_name} | Global weights: KAN={global_weights['kan']:.2f}, "
        f"Deep={global_weights['deep_learning']:.2f}, LCS={global_weights['lcs']:.2f}"
    )
    ensemble_common = dict(
        input_csv_or_df=ensemble_validation,
        training_csv_or_df=pd.read_csv(root / "study_kan" / "best_train_pretreated_kan.csv", low_memory=False),
        metrics_dict_or_path=ensemble_metrics_global,
        forecast_csv_or_df=classic_forecast,
        temporal_metrics_csv_or_df=ensemble_horizon_metrics,
        temporal_forecast_csv_or_df=ensemble_render_forecast,
        title=ensemble_title,
        subtitle=ensemble_subtitle,
        target_name=target_col,
        roi_name=roi_name,
        model_name="Weighted Multi-Model Ensemble",
        eval_window_mode="corridors",
        eval_max_events=eval_events,
        eval_min_mag=peak_threshold,
        show_eval_dot_tags=True,
        show_train_dot_tags=True,
    )
    figure = visualizer.render(output_path=ensemble_dir / "ensemble_validation_report.png", **ensemble_common)
    plt.close(figure)
    ensemble_pdf = ensemble_dir / "ensemble_validation_report.pdf"
    figure = visualizer.render(output_path=ensemble_pdf, **ensemble_common)
    plt.close(figure)
    report_paths["ensemble"] = str(ensemble_pdf)

    manifest_lines = [
        "# Temporal Horizon Validation Manifest",
        "",
        "The following horizons are translated from progressive validation-window lead times. ",
        "`supported` means the declared backtest thresholds passed; it is not a guarantee of a future earthquake.",
        "",
        "| Model | Stage | Validation window end | Equivalent forecast end | Supported | Recall | Peak mag MAE | Timing error |",
        "| :--- | ---: | :--- | :--- | :---: | ---: | ---: | ---: |",
    ]
    for model, frame in {**temporal_metrics, "ensemble": ensemble_horizon_metrics}.items():
        for _, row in frame.iterrows():
            manifest_lines.append(
                f"| {model} | H{int(row['stage'])} | {row['window_end_date']} | {row['forecast_equivalent_end_date']} | "
                f"{'yes' if row['cumulative_supported'] else 'no'} | {row['cumulative_recall']:.2%} | "
                f"{row['cumulative_peak_magnitude_mae']:.3f} | {row['cumulative_peak_timing_error_steps']:.2f} |"
            )
    (root / "TEMPORAL_HORIZON_VALIDATION_MANIFEST.md").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    return {
        "reports": report_paths,
        "global_weights": global_weights,
        "temporal_weights_path": str(ensemble_dir / "ensemble_temporal_weights.csv"),
        "staged_forecast_path": str(ensemble_dir / "ensemble_temporal_staged_forecast.csv"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Regenerate Optuna study reports with pure forecast and temporal-horizon pages",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--study-dir", required=True)
    parser.add_argument("--input-master", required=True)
    parser.add_argument("--target-col", default="seis_core_magnitude")
    parser.add_argument("--peak-threshold", type=float, default=6.9)
    parser.add_argument("--eval-events", type=int, default=3)
    parser.add_argument("--forecast-steps", type=int, default=150)
    parser.add_argument("--device", choices=["cpu", "cuda", "xpu"], default="cpu")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model-epochs-override", type=int, default=None)
    parser.add_argument("--roi-name", default="Japan Area (7D Compacted Astro)")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    result = regenerate_existing_study_reports(
        study_dir=args.study_dir,
        input_master=args.input_master,
        target_col=args.target_col,
        peak_threshold=args.peak_threshold,
        eval_events=args.eval_events,
        forecast_steps=args.forecast_steps,
        device=args.device,
        seed=args.seed,
        model_epochs_override=args.model_epochs_override,
        roi_name=args.roi_name,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
