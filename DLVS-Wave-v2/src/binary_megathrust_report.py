"""High-resolution validation and frozen prospective forecast reporting."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from src.models.plotting import ForecastingVisualizer


COLORS = {
    "kan": "#0b66c3",
    "deep_learning": "#c23b3b",
    "lcs": "#6f42c1",
    "ensemble": "#111827",
    "threshold": "#ef8a17",
}


def _date_axis(axis: plt.Axes, interval: int = 24) -> None:
    axis.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    for label in axis.get_xticklabels():
        label.set_rotation(90)
        label.set_ha("center")
    axis.grid(True, alpha=0.2, linestyle="--")


def _decorate_forecast_gate(
    figure: plt.Figure,
    forecast: pd.DataFrame,
    *,
    probability_column: str,
    threshold: float,
) -> None:
    """Make the digital decision rule visible without changing forecast values."""
    data_axes = [axis for axis in figure.axes if axis.has_data()]
    if not data_axes:
        return
    axis = max(data_axes, key=lambda item: len(item.lines))
    axis.axhline(
        threshold,
        color=COLORS["threshold"],
        linestyle="--",
        linewidth=1.6,
        label=f"digital gate p >= {threshold:.2f}",
        zorder=2,
    )
    if "event_signal" in forecast and probability_column in forecast:
        selected = forecast["event_signal"].eq(1)
        if selected.any():
            axis.scatter(
                pd.to_datetime(forecast.loc[selected, "date"]),
                forecast.loc[selected, probability_column],
                color="#dc2626",
                edgecolor="black",
                zorder=6,
                s=70,
                label="discrete gated signal",
            )
            for row in forecast.loc[selected].itertuples():
                axis.annotate(
                    pd.Timestamp(row.date).strftime("%Y-%m-%d"),
                    (pd.Timestamp(row.date), getattr(row, probability_column)),
                    xytext=(0, 12),
                    textcoords="offset points",
                    rotation=90,
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color="#991b1b",
                )
    axis.legend(fontsize=8, loc="upper right")


def create_model_plot(
    validation: pd.DataFrame,
    forecast: pd.DataFrame,
    training: pd.DataFrame,
    metrics: dict[str, Any],
    output_png: str | Path,
    *,
    model_name: str,
    stage_name: str,
    threshold: float,
    magnitude_threshold: float,
    params: dict[str, Any],
    validation_event_count: int,
    validation_window_span: int,
) -> Path:
    """Render the established DLVS-Wave corridor validation and companion forecast."""
    output = Path(output_png)
    output.parent.mkdir(parents=True, exist_ok=True)
    validation = validation.copy()
    forecast = forecast.copy()
    probability_column = f"probability_{model_name}"
    validation["predicted_binary_event_probability"] = validation[probability_column]
    if "event_magnitude" not in validation:
        validation["event_magnitude"] = np.where(validation["actual"].eq(1), magnitude_threshold, np.nan)
    validation_display = validation[["date", "actual", "predicted_binary_event_probability", "event_magnitude"]]
    forecast_display = forecast[["date", probability_column]].rename(
        columns={probability_column: "forecasted_binary_event_probability"}
    )
    training_display = training[["date", "japan_max_magnitude"]].copy()
    training_display["japan_max_magnitude"] = training_display["japan_max_magnitude"].fillna(0.0)

    def short_value(value: Any) -> str:
        return f"{value:.4g}" if isinstance(value, float) else str(value)

    common_params = [
        f"train={short_value(params.get('train_start_year'))}",
        f"W={short_value(params.get('window_before'))}/{short_value(params.get('window_after'))}",
        f"bg={short_value(params.get('background_ratio'))}",
        f"chunk={short_value(params.get('background_chunk_weeks'))}",
        f"F={short_value(params.get('feature_count'))}",
    ]
    model_keys = {
        "kan": (("grid_size", "grid"), ("spline_order", "spline"), ("hidden_dim", "h"), ("learning_rate", "lr")),
        "deep_learning": (("hidden_dim", "h"), ("num_layers", "L"), ("dropout", "drop"), ("learning_rate", "lr")),
        "lcs": (("population_size", "pop"), ("learning_rate", "lr"), ("crossover_rate", "cross"), ("mutation_rate", "mut")),
    }
    compact_params = ", ".join(
        common_params + [f"{label}={short_value(params.get(key))}" for key, label in model_keys[model_name]]
    )
    subtitle = (
        f"ROI: Japan Area (7D Compacted Astro) | Best Params: {compact_params}\n"
        f"Validation: P={float(metrics.get('precision', 0)):.3f}, R={float(metrics.get('recall', 0)):.3f}, "
        f"F1={float(metrics.get('f1', 0)):.3f}, FP={int(metrics.get('fp', 0))}, FN={int(metrics.get('fn', 0))}"
    )
    visualizer = ForecastingVisualizer(dpi=300)
    figure = visualizer.render(
        input_csv_or_df=validation_display,
        training_csv_or_df=training_display,
        output_path=output,
        forecast_csv_or_df=forecast_display,
        title=f"DLVS-Wave v2.0 Microstudy: {model_name.upper()} {stage_name} Validation Report",
        subtitle=subtitle,
        target_name="binary_target_0_1",
        roi_name="Japan Area (7D Compacted Astro)",
        model_name=model_name.upper(),
        eval_window_mode="corridors",
        eval_max_events=validation_event_count,
        eval_min_mag=0.5,
        eval_window_span=validation_window_span,
        eval_merge_overlapping=False,
        train_window_mode="corridors",
        train_max_events=12,
        train_min_mag=magnitude_threshold,
        train_window_span=3,
        training_target_name="japan_max_magnitude",
        eval_peak_label_column="event_magnitude",
        eval_peak_label_prefix="M",
        eval_peak_tag_offset=0.08,
        show_eval_dot_tags=True,
        show_train_dot_tags=True,
        forecast_peak_min=threshold,
        forecast_max_peak_labels=8,
        forecast_peak_label_prefix="p=",
        y_min=-0.05,
        y_max=1.80,
    )
    figure.savefig(output.with_suffix(".pdf"), dpi=300, bbox_inches="tight")
    plt.close(figure)
    return output


def _dashboard(
    validation: pd.DataFrame,
    forecast: pd.DataFrame,
    model_metrics: dict[str, dict[str, Any]],
    ensemble_metrics: dict[str, Any] | None,
    *,
    threshold: float,
    magnitude_threshold: float,
    cutoff_utc: str,
    certified: bool,
) -> plt.Figure:
    figure = plt.figure(figsize=(16, 11), constrained_layout=True)
    grid = figure.add_gridspec(3, 1, height_ratios=[1.35, 1.05, 0.72])
    val_axis = figure.add_subplot(grid[0])
    forecast_axis = figure.add_subplot(grid[1])
    table_axis = figure.add_subplot(grid[2])

    if not validation.empty:
        validation = validation.copy()
        validation["date"] = pd.to_datetime(validation["date"])
        positives = validation["actual"].eq(1)
        val_axis.vlines(
            validation.loc[positives, "date"], 0.0, 1.0, color="#dc2626", alpha=0.45, linewidth=1.2,
            label=f"Observed Japan M >= {magnitude_threshold:.1f} week",
        )
        for model, color in COLORS.items():
            column = f"probability_{model}"
            if column in validation:
                val_axis.plot(validation["date"], validation[column], color=color, linewidth=1.4, label=model)
        val_axis.axhline(threshold, color=COLORS["threshold"], linestyle="--", linewidth=1.4, label="digital gate")
        val_axis.set_ylim(-0.03, 1.04)
        val_axis.set_ylabel("Validation probability (0-1)")
        val_axis.set_title("Frozen temporal validation: event corridors, hard negatives, and fixed quiet controls")
        _date_axis(val_axis, interval=24)
        val_axis.legend(ncol=3, fontsize=8, loc="upper left")
    else:
        val_axis.text(0.5, 0.5, "No validation output is available", ha="center", va="center", fontsize=16)
        val_axis.set_axis_off()

    forecast = forecast.copy()
    forecast["date"] = pd.to_datetime(forecast["date"])
    if not forecast.empty:
        forecast_axis.set_xlim(
            mdates.date2num(forecast["date"].min().to_pydatetime()),
            mdates.date2num(forecast["date"].max().to_pydatetime()),
        )
    has_forecast_artists = False
    if "ensemble_probability" in forecast and forecast["ensemble_probability"].notna().any():
        forecast_axis.plot(
            forecast["date"], forecast["ensemble_probability"], color=COLORS["ensemble"], marker="o",
            markersize=3.5, linewidth=1.8, label="ensemble probability",
        )
        forecast_axis.axhline(threshold, color=COLORS["threshold"], linestyle="--", linewidth=1.4, label="digital gate")
        selected = forecast["event_signal"].eq(1)
        forecast_axis.scatter(
            forecast.loc[selected, "date"], forecast.loc[selected, "ensemble_probability"],
            color="#dc2626", edgecolor="black", zorder=5, s=65, label="discrete gated signal",
        )
        has_forecast_artists = True
        for row in forecast.loc[selected].itertuples():
            forecast_axis.annotate(
                pd.Timestamp(row.date).strftime("%Y-%m-%d"),
                (row.date, row.ensemble_probability), xytext=(0, 12), textcoords="offset points",
                rotation=90, ha="center", va="bottom", fontsize=8,
            )
    else:
        forecast_axis.text(
            0.5,
            0.5,
            "No prospective forecast output is available",
            transform=forecast_axis.transAxes,
            ha="center",
            va="center",
        )
    forecast_axis.set_ylim(-0.03, 1.12)
    forecast_axis.set_ylabel("Prospective score (0-1)")
    forecast_axis.set_title("Frozen prospective weekly projection: August through December 2026")
    _date_axis(forecast_axis, interval=1)
    if has_forecast_artists:
        forecast_axis.legend(fontsize=8, loc="upper left")

    table_axis.axis("off")
    headers = ["Model", "Precision", "Recall", "F1", "FP", "FN", "AUC"]
    rows = []
    for model, metrics in model_metrics.items():
        rows.append([
            model,
            f"{float(metrics.get('precision', 0)):.3f}",
            f"{float(metrics.get('recall', 0)):.3f}",
            f"{float(metrics.get('f1', 0)):.3f}",
            str(int(metrics.get("fp", 0))),
            str(int(metrics.get("fn", 0))),
            f"{float(metrics.get('auc', 0.5)):.3f}",
        ])
    if ensemble_metrics:
        rows.append([
            "ensemble",
            f"{float(ensemble_metrics.get('precision', 0)):.3f}",
            f"{float(ensemble_metrics.get('recall', 0)):.3f}",
            f"{float(ensemble_metrics.get('f1', 0)):.3f}",
            str(int(ensemble_metrics.get("fp", 0))),
            str(int(ensemble_metrics.get("fn", 0))),
            f"{float(ensemble_metrics.get('auc', 0.5)):.3f}",
        ])
    table = table_axis.table(cellText=rows, colLabels=headers, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.55)
    for (row, _column), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#dbeafe")
            cell.set_text_props(weight="bold")

    status = "QUALITY GATE PASSED" if certified else "BEST AVAILABLE - QUALITY GATE NOT PASSED"
    figure.suptitle(
        f"DLVS-Wave v2.0 | Japan-wide binary megathrust research study\n"
        f"Target: M >= {magnitude_threshold:.1f} | gate p >= {threshold:.2f} | cutoff: {cutoff_utc} | {status}",
        fontsize=15, fontweight="bold",
    )
    figure.text(
        0.5, 0.008,
        "RESEARCH ONLY. Scores are experimental model outputs, not calibrated physical earthquake probabilities "
        "and not an operational warning system.",
        ha="center", fontsize=9, color="#991b1b", weight="bold",
    )
    return figure


def _method_page(
    dataset_summary: dict[str, Any],
    selected_models: list[str],
    model_metrics: dict[str, dict[str, Any]],
    *,
    threshold: float,
) -> plt.Figure:
    figure, axis = plt.subplots(figsize=(16, 11))
    axis.axis("off")
    lines = [
        "METHOD AND AUDIT SUMMARY",
        "",
        f"Historical rows: {dataset_summary.get('historical_rows', 0):,}",
        f"Compacted astronomical predictors available: {dataset_summary.get('feature_count', 0):,}",
        f"Japan positive event weeks: {dataset_summary.get('japan_positive_weeks', 0):,}",
        f"Foreign hard-negative event weeks: {dataset_summary.get('foreign_hard_negative_weeks', 0):,}",
        f"Magnitude threshold: M >= {dataset_summary.get('magnitude_threshold', 0):.1f}",
        f"Informational cutoff: {dataset_summary.get('cutoff_utc', '')}",
        f"Forecast interval: {dataset_summary.get('forecast_start', '')} to {dataset_summary.get('forecast_end', '')}",
        "",
        "Leakage controls",
        "- Only packed_astro_container_* fields enter the models.",
        "- Contemporaneous magnitude, location, depth, and seismic-shift columns are excluded.",
        "- Prospective rows have a missing target; they are never labelled as quiet negatives.",
        "- Temporal validation contains only the two requested held-out event corridors,",
        f"  each with exactly {dataset_summary.get('validation_weeks_before', 13)} weekly indices before and "
        f"{dataset_summary.get('validation_weeks_after', 13)} after the event week.",
        "- Foreign high-magnitude weeks are forced to y=0 hard negatives.",
        "- Training-only quiet background is sampled as contiguous inter-event chunks using pi millesimi",
        "  mixed into each trial seed; validation never reuses this sampler.",
        "",
        "Optimization",
        "- Level 1: independent Optuna studies for KAN, tabular ResNet, and LCS.",
        "- Level 2: MC-dropout deep surrogate plus gradient ascent on Expected Improvement.",
        "- Objective = FocalLoss + 3(1-F1) + 3.5(FP rate) + 2.5(FN rate) + 0.5(Depression MAE).",
        "- Event-peak displacement is reported separately and is not a hidden objective addend.",
        "- The FP/recall quality gate is advisory: it never suppresses L1, L2, or prospective output.",
        "- Ensemble weights strongly favor higher validation F1, precision, recall, and AUC, while penalizing",
        "  false positives and objective loss; weights are normalized across the selected L2 models.",
        f"- Final discrete event gate: p >= {threshold:.2f}; consecutive exceedances collapse to one peak week.",
        "",
        f"Models included in the best-available forecast ensemble: {', '.join(selected_models) if selected_models else 'none'}",
        "",
        "Interpretation limit",
        "The separate QUALITY_GATE_REPORT.md records every gate failure without altering the forecast. Passing or failing "
        "the historical gate does not establish causal or prospective predictive skill. The score is not a "
        "frequency-calibrated probability and must not be used for public-safety decisions.",
    ]
    y = 0.96
    for index, line in enumerate(lines):
        size = 17 if index == 0 else (12 if line in {"Leakage controls", "Optimization", "Interpretation limit"} else 10.5)
        weight = "bold" if index == 0 or line in {"Leakage controls", "Optimization", "Interpretation limit"} else "normal"
        axis.text(0.04, y, line, transform=axis.transAxes, fontsize=size, weight=weight, va="top", wrap=True)
        y -= 0.045 if line else 0.025
    return figure


def create_binary_report(
    validation: pd.DataFrame,
    forecast: pd.DataFrame,
    training: pd.DataFrame,
    model_metrics: dict[str, dict[str, Any]],
    ensemble_metrics: dict[str, Any] | None,
    dataset_summary: dict[str, Any],
    selected_models: list[str],
    output_png: str | Path,
    output_pdf: str | Path,
    *,
    threshold: float,
    certified: bool,
) -> tuple[Path, Path]:
    png = Path(output_png)
    pdf = Path(output_pdf)
    png.parent.mkdir(parents=True, exist_ok=True)
    pdf.parent.mkdir(parents=True, exist_ok=True)
    magnitude_threshold = float(dataset_summary["magnitude_threshold"])
    required_validation = {"date", "actual", "probability_ensemble"}
    required_forecast = {"date", "ensemble_probability"}
    if not required_validation.issubset(validation.columns) or not required_forecast.issubset(forecast.columns):
        placeholder, axis = plt.subplots(figsize=(16, 11))
        axis.axis("off")
        axis.text(
            0.5, 0.56,
            "DLVS-Wave v2.0 — no technically successful model output",
            ha="center", va="center", fontsize=18, weight="bold",
        )
        axis.text(
            0.5, 0.46,
            "The data and quality audits were generated; no probability curve is fabricated.",
            ha="center", va="center", fontsize=12,
        )
        placeholder.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
        method = _method_page(dataset_summary, selected_models, model_metrics, threshold=threshold)
        with PdfPages(pdf) as pages:
            pages.savefig(placeholder, dpi=300, bbox_inches="tight", facecolor="white")
            pages.savefig(method, dpi=220, bbox_inches="tight", facecolor="white")
        plt.close(placeholder)
        plt.close(method)
        return png, pdf
    validation_display = validation[["date", "actual", "probability_ensemble"]].copy()
    validation_display.rename(columns={"probability_ensemble": "predicted_binary_event_probability"}, inplace=True)
    if "event_magnitude" in validation:
        validation_display["event_magnitude"] = validation["event_magnitude"]
    else:
        validation_display["event_magnitude"] = np.where(
            validation_display["actual"].eq(1), magnitude_threshold, np.nan
        )
    training_display = training[["date", "japan_max_magnitude"]].copy()
    training_display["japan_max_magnitude"] = training_display["japan_max_magnitude"].fillna(0.0)
    forecast_display = forecast[["date", "ensemble_probability"]].rename(
        columns={"ensemble_probability": "forecasted_binary_event_probability"}
    )
    metric_text = ""
    if ensemble_metrics:
        metric_text = (
            f" | P={float(ensemble_metrics.get('precision', 0)):.3f}, "
            f"R={float(ensemble_metrics.get('recall', 0)):.3f}, "
            f"F1={float(ensemble_metrics.get('f1', 0)):.3f}, "
            f"FP={int(ensemble_metrics.get('fp', 0))}, FN={int(ensemble_metrics.get('fn', 0))}"
        )
    subtitle = (
        f"ROI: Japan Area (7D Compacted Astro) | Models: {', '.join(selected_models)} | "
        f"cutoff={dataset_summary.get('cutoff_utc', '')} | policy=best-available advisory{metric_text}"
    )
    visualizer = ForecastingVisualizer(dpi=300)
    validation_figure = visualizer.render(
        input_csv_or_df=validation_display,
        training_csv_or_df=training_display,
        output_path=None,
        title="DLVS-Wave v2.0 Ensemble Validation Report",
        subtitle=subtitle,
        target_name="binary_target_0_1",
        roi_name="Japan Area (7D Compacted Astro)",
        model_name="VALIDATION-WEIGHTED ENSEMBLE",
        eval_window_mode="corridors",
        eval_max_events=int(dataset_summary.get("validation_event_count", 2)),
        eval_min_mag=0.5,
        eval_window_span=max(
            1,
            int(max(
                float(dataset_summary.get("validation_weeks_before", 13)),
                float(dataset_summary.get("validation_weeks_after", 13)),
            )),
        ),
        eval_merge_overlapping=False,
        train_window_mode="corridors",
        train_max_events=12,
        train_min_mag=magnitude_threshold,
        train_window_span=3,
        training_target_name="japan_max_magnitude",
        eval_peak_label_column="event_magnitude",
        eval_peak_label_prefix="M",
        eval_peak_tag_offset=0.08,
        show_eval_dot_tags=True,
        show_train_dot_tags=True,
        y_min=-0.05,
        y_max=1.80,
    )
    forecast_figure = visualizer.render(
        input_csv_or_df=forecast_display,
        output_path=None,
        title="DLVS-Wave v2.0 Ensemble Pure Forecast",
        subtitle=(
            f"ROI: Japan Area (7D Compacted Astro) | {dataset_summary.get('forecast_start', '')} to "
            f"{dataset_summary.get('forecast_end', '')} | no future ground truth used"
        ),
        target_name="binary_event_probability_0_1",
        roi_name="Japan Area (7D Compacted Astro)",
        model_name="VALIDATION-WEIGHTED ENSEMBLE",
        eval_window_mode="continuous",
        forecast_peak_min=threshold,
        forecast_max_peak_labels=8,
        forecast_peak_label_prefix="p=",
        y_min=-0.05,
        y_max=1.55,
    )
    _decorate_forecast_gate(
        forecast_figure,
        forecast,
        probability_column="ensemble_probability",
        threshold=threshold,
    )
    validation_figure.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    forecast_png = png.with_name(f"{png.stem}_forecast.png")
    forecast_figure.savefig(forecast_png, dpi=300, bbox_inches="tight", facecolor="white")
    method = _method_page(dataset_summary, selected_models, model_metrics, threshold=threshold)
    with PdfPages(pdf) as pages:
        pages.savefig(validation_figure, dpi=300, bbox_inches="tight", facecolor="white")
        pages.savefig(forecast_figure, dpi=300, bbox_inches="tight", facecolor="white")
        pages.savefig(method, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(validation_figure)
    plt.close(forecast_figure)
    plt.close(method)
    return png, pdf
