"""Progressive validation-horizon metrics and temporal ensemble weighting.

The module treats the event corridors shown in DLVS-Wave reports as ordered
forecast-horizon stages.  It reports both isolated-window and cumulative
metrics, then translates each validation lead time to an equivalent future
forecast date.  A stage marked as supported is backtest evidence only; it is
never presented as a guarantee of future seismic predictability.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np
import pandas as pd


DEFAULT_CERTIFICATION_THRESHOLDS: dict[str, float] = {
    "min_peak_recall": 0.50,
    "max_peak_magnitude_mae": 1.00,
    "max_peak_timing_error_steps": 1.00,
}


def _safe_correlation(actual: np.ndarray, predicted: np.ndarray) -> float:
    if len(actual) < 2 or np.std(actual) <= 1e-8 or np.std(predicted) <= 1e-8:
        return 0.0
    correlation = float(np.corrcoef(actual, predicted)[0, 1])
    return correlation if math.isfinite(correlation) else 0.0


def compute_fixed_threshold_metrics(
    actual: np.ndarray | pd.Series,
    predicted: np.ndarray | pd.Series,
    peak_threshold: float = 6.9,
    segment_ids: np.ndarray | pd.Series | None = None,
) -> dict[str, Any]:
    """Compute regression and event metrics at one declared magnitude threshold."""
    y_true = np.asarray(actual, dtype=np.float64).reshape(-1)
    y_pred = np.asarray(predicted, dtype=np.float64).reshape(-1)
    if len(y_true) == 0 or len(y_true) != len(y_pred):
        raise ValueError("actual and predicted must be non-empty arrays of equal length")
    if not np.isfinite(y_true).all() or not np.isfinite(y_pred).all():
        raise ValueError("actual and predicted must contain only finite values")

    error = y_pred - y_true
    mse = float(np.mean(error ** 2))
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(error)))
    total_variance = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = float(1.0 - np.sum(error ** 2) / max(total_variance, 1e-8)) if total_variance > 1e-8 else 0.0

    actual_peak = y_true >= peak_threshold
    prediction_threshold = peak_threshold * 0.90
    predicted_peak = y_pred >= prediction_threshold
    tp = int(np.sum(actual_peak & predicted_peak))
    fp = int(np.sum((~actual_peak) & predicted_peak))
    fn = int(np.sum(actual_peak & (~predicted_peak)))
    tn = int(np.sum((~actual_peak) & (~predicted_peak)))
    precision = float(tp / (tp + fp)) if tp + fp else 0.0
    recall = float(tp / (tp + fn)) if tp + fn else 0.0
    f1_score = float(2.0 * precision * recall / (precision + recall)) if precision + recall else 0.0

    peak_errors = error[actual_peak]
    peak_magnitude_bias = float(np.mean(peak_errors)) if len(peak_errors) else 0.0
    peak_magnitude_mae = float(np.mean(np.abs(peak_errors))) if len(peak_errors) else 0.0
    calm = ~actual_peak
    depression_mae = float(np.mean(np.abs(error[calm]))) if np.any(calm) else 0.0

    if segment_ids is None:
        segments = np.zeros(len(y_true), dtype=np.int64)
    else:
        segments = np.asarray(segment_ids).reshape(-1)
        if len(segments) != len(y_true):
            raise ValueError("segment_ids must have the same length as actual")
    timing_errors: list[float] = []
    for segment in pd.unique(segments):
        indices = np.flatnonzero(segments == segment)
        actual_indices = indices[actual_peak[indices]]
        predicted_indices = indices[predicted_peak[indices]]
        if not len(actual_indices):
            continue
        if not len(predicted_indices):
            timing_errors.extend([float(len(indices))] * len(actual_indices))
        else:
            timing_errors.extend(float(np.min(np.abs(predicted_indices - index))) for index in actual_indices)
    peak_timing_error = float(np.mean(timing_errors)) if timing_errors else 0.0

    directional_accuracy = (
        float(np.mean(np.sign(np.diff(y_true)) == np.sign(np.diff(y_pred)))) if len(y_true) > 1 else 1.0
    )
    return {
        "sample_count": len(y_true),
        "mse": mse,
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "pearson_corr": _safe_correlation(y_true, y_pred),
        "peak_threshold": float(peak_threshold),
        "prediction_peak_threshold": float(prediction_threshold),
        "major_event_count": int(np.sum(actual_peak)),
        "predicted_peak_count": int(np.sum(predicted_peak)),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "peak_magnitude_bias": peak_magnitude_bias,
        "peak_magnitude_mae": peak_magnitude_mae,
        "peak_timing_error_steps": peak_timing_error,
        "depression_mae": depression_mae,
        "directional_accuracy": directional_accuracy,
    }


def _infer_cadence(dates: pd.Series) -> pd.Timedelta:
    ordered = pd.Series(pd.to_datetime(dates)).sort_values().drop_duplicates()
    differences = ordered.diff().dropna()
    positive = differences[differences > pd.Timedelta(0)]
    return positive.median() if len(positive) else pd.Timedelta(days=1)


def _certification(metrics: Mapping[str, Any], thresholds: Mapping[str, float]) -> tuple[bool, str]:
    failures: list[str] = []
    if int(metrics["major_event_count"]) < 1:
        failures.append("no major event in stage")
    if float(metrics["recall"]) < float(thresholds["min_peak_recall"]):
        failures.append(f"recall {metrics['recall']:.2f} < {thresholds['min_peak_recall']:.2f}")
    if float(metrics["peak_magnitude_mae"]) > float(thresholds["max_peak_magnitude_mae"]):
        failures.append(
            f"peak magnitude MAE {metrics['peak_magnitude_mae']:.2f} > {thresholds['max_peak_magnitude_mae']:.2f}"
        )
    if float(metrics["peak_timing_error_steps"]) > float(thresholds["max_peak_timing_error_steps"]):
        failures.append(
            f"timing error {metrics['peak_timing_error_steps']:.2f} > {thresholds['max_peak_timing_error_steps']:.2f} steps"
        )
    return not failures, "passes declared thresholds" if not failures else "; ".join(failures)


def temporal_quality_score(metrics: Mapping[str, Any]) -> float:
    """Event-centric score used only to derive per-stage ensemble weights."""
    recall = float(metrics.get("recall", 0.0))
    f1_score = float(metrics.get("f1_score", 0.0))
    magnitude_term = 1.0 / (1.0 + max(0.0, float(metrics.get("peak_magnitude_mae", 99.0))))
    timing_term = 1.0 / (1.0 + max(0.0, float(metrics.get("peak_timing_error_steps", 99.0))))
    calm_term = 1.0 / (1.0 + max(0.0, float(metrics.get("depression_mae", 99.0))))
    return max(1e-8, 0.35 * recall + 0.25 * f1_score + 0.20 * magnitude_term + 0.10 * timing_term + 0.10 * calm_term)


def build_progressive_horizon_metrics(
    validation_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    peak_threshold: float = 6.9,
    max_events: int = 3,
    window_span: int = 4,
    certification_thresholds: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Return isolated and cumulative metrics for the displayed event windows."""
    try:  # Local import avoids a module cycle and supports both CLI/package use.
        from .models.plotting import ForecastingVisualizer
    except ImportError:
        from models.plotting import ForecastingVisualizer

    validation = validation_df.copy()
    forecast = forecast_df.copy()
    date_col = "date" if "date" in validation.columns else validation.columns[0]
    forecast_date_col = "date" if "date" in forecast.columns else forecast.columns[0]
    predicted_cols = [column for column in validation.columns if column.startswith("predicted_")]
    if "actual" not in validation.columns or not predicted_cols:
        raise ValueError("validation_df requires actual and predicted_* columns")
    if len(forecast) == 0:
        raise ValueError("forecast_df must contain at least one row")
    predicted_col = predicted_cols[0]
    validation[date_col] = pd.to_datetime(validation[date_col])
    forecast[forecast_date_col] = pd.to_datetime(forecast[forecast_date_col])
    validation.sort_values(date_col, inplace=True)
    forecast.sort_values(forecast_date_col, inplace=True)

    segments, metadata = ForecastingVisualizer.extract_top_event_corridors(
        validation,
        target_col="actual",
        date_col=date_col,
        max_events=max_events,
        min_mag_threshold=peak_threshold,
        window_span=window_span,
    )
    if not segments:
        raise ValueError("No validation event corridor could be extracted")

    thresholds = dict(DEFAULT_CERTIFICATION_THRESHOLDS)
    if certification_thresholds:
        thresholds.update({key: float(value) for key, value in certification_thresholds.items()})
    cadence = _infer_cadence(validation[date_col])
    validation_origin = validation[date_col].min() - cadence
    forecast_origin = forecast[forecast_date_col].min() - cadence

    cumulative_frames: list[pd.DataFrame] = []
    rows: list[dict[str, Any]] = []
    consecutive_supported = True
    for stage_index, (segment, meta) in enumerate(zip(segments, metadata), start=1):
        segment = segment.copy()
        segment[date_col] = pd.to_datetime(segment[date_col])
        cumulative_frames.append(segment)
        cumulative = pd.concat(cumulative_frames, ignore_index=True)
        segment_ids = np.concatenate(
            [np.full(len(frame), index, dtype=np.int64) for index, frame in enumerate(cumulative_frames)]
        )
        window_metrics = compute_fixed_threshold_metrics(
            segment["actual"], segment[predicted_col], peak_threshold=peak_threshold
        )
        cumulative_metrics = compute_fixed_threshold_metrics(
            cumulative["actual"],
            cumulative[predicted_col],
            peak_threshold=peak_threshold,
            segment_ids=segment_ids,
        )
        supported, reason = _certification(cumulative_metrics, thresholds)
        consecutive_supported = consecutive_supported and supported
        stage_end = segment[date_col].max()
        lead = stage_end - validation_origin
        translated_end = forecast_origin + lead
        available_dates = forecast.loc[forecast[forecast_date_col] <= translated_end, forecast_date_col]
        matched_end = available_dates.max() if len(available_dates) else pd.NaT

        row: dict[str, Any] = {
            "stage": stage_index,
            "window_label": meta.get("label", f"W{stage_index}"),
            "window_start_date": segment[date_col].min().strftime("%Y-%m-%d"),
            "window_end_date": stage_end.strftime("%Y-%m-%d"),
            "validation_origin_date": validation_origin.strftime("%Y-%m-%d"),
            "validation_lead_days": int(lead / pd.Timedelta(days=1)),
            "validation_lead_steps": int(round(lead / cadence)),
            "forecast_origin_date": forecast_origin.strftime("%Y-%m-%d"),
            "forecast_equivalent_end_date": translated_end.strftime("%Y-%m-%d"),
            "forecast_available_end_date": matched_end.strftime("%Y-%m-%d") if pd.notna(matched_end) else None,
            "forecast_supported_steps": int(len(available_dates)),
            "cumulative_supported": bool(supported),
            "consecutive_supported": bool(consecutive_supported),
            "support_reason": reason,
            "evidence_scope": "backtest_equivalent_horizon_not_future_guarantee",
            "quality_score": temporal_quality_score(cumulative_metrics),
        }
        row.update({f"window_{key}": value for key, value in window_metrics.items()})
        row.update({f"cumulative_{key}": value for key, value in cumulative_metrics.items()})
        rows.append(row)
    return pd.DataFrame(rows)


def derive_temporal_ensemble_weights(metrics_by_model: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Create normalized, event-centric model weights for every horizon stage."""
    if not metrics_by_model:
        raise ValueError("metrics_by_model cannot be empty")
    stage_count = min(len(frame) for frame in metrics_by_model.values())
    rows: list[dict[str, Any]] = []
    for stage_index in range(stage_count):
        supported_models = {
            model for model, frame in metrics_by_model.items() if bool(frame.iloc[stage_index]["cumulative_supported"])
        }
        raw: dict[str, float] = {}
        for model, frame in metrics_by_model.items():
            row = frame.iloc[stage_index]
            score = float(row["quality_score"])
            if supported_models:
                score *= 8.0 if model in supported_models else 0.15
            raw[model] = max(score, 1e-8)
        denominator = sum(raw.values())
        output: dict[str, Any] = {
            "stage": stage_index + 1,
            "forecast_equivalent_end_date": next(iter(metrics_by_model.values())).iloc[stage_index][
                "forecast_equivalent_end_date"
            ],
            "supported_models": ",".join(sorted(supported_models)) if supported_models else "none",
        }
        for model in metrics_by_model:
            output[f"weight_{model}"] = raw[model] / denominator
            output[f"quality_{model}"] = float(metrics_by_model[model].iloc[stage_index]["quality_score"])
            output[f"supported_{model}"] = bool(
                metrics_by_model[model].iloc[stage_index]["cumulative_supported"]
            )
        rows.append(output)
    return pd.DataFrame(rows)
