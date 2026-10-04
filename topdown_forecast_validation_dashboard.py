#!/usr/bin/env python3
"""Create a six-panel timing/location forecast and validation dashboard."""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    return rows


def parse_date(value: str) -> datetime:
    return datetime.fromisoformat(str(value)[:10])


def regression_metrics(actual: list[float], predicted: list[float]) -> dict[str, float]:
    y = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)
    errors = p - y
    mse = float(np.mean(errors**2))
    mae = float(np.mean(np.abs(errors)))
    rmse = math.sqrt(mse)
    denom = float(np.sum((y - np.mean(y)) ** 2))
    r2 = float(1.0 - np.sum(errors**2) / denom) if denom > 0 else float("nan")
    return {"mae": mae, "rmse": rmse, "r2": r2}


def timing_metrics(
    actual: list[float], predicted: list[float], threshold: float
) -> dict[str, float | int | None]:
    y = np.asarray(actual, dtype=float) >= 0.5
    p = np.asarray(predicted, dtype=float)
    detected = p >= threshold
    tp = int(np.sum(y & detected))
    fp = int(np.sum(~y & detected))
    fn = int(np.sum(y & ~detected))
    tn = int(np.sum(~y & ~detected))
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    specificity = tn / (tn + fp) if tn + fp else None
    balanced_accuracy = (
        0.5 * (recall + specificity)
        if recall is not None and specificity is not None
        else None
    )
    brier = float(np.mean((p - y.astype(float)) ** 2))
    return {
        "rows": len(y),
        "positive_rows": int(np.sum(y)),
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "balanced_accuracy": balanced_accuracy,
        "brier_score": brier,
        "max_validation_score": float(np.max(p)),
    }


def fmt_metric(value: float | int | None, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return str(value)
    if not math.isfinite(float(value)):
        return "n/a"
    return f"{float(value):.{digits}f}"


def seven_day_slot_labels(dates: list[datetime]) -> list[str]:
    return [
        f"{start:%m-%d}\n→{start + timedelta(days=6):%m-%d}"
        for start in dates
    ]


def validation_series(
    ax: plt.Axes,
    rows: list[dict[str, str]],
    title: str,
    unit: str,
    metrics: dict[str, float],
) -> None:
    dates = [parse_date(row["date"]) for row in rows]
    actual = [float(row["actual_value"]) for row in rows]
    predicted = [float(row["predicted_value"]) for row in rows]
    x = np.arange(len(rows))
    for idx, (a, p) in enumerate(zip(actual, predicted)):
        ax.plot([idx, idx], [a, p], color="#b8c2cc", linewidth=2, zorder=1)
    ax.scatter(x, actual, s=70, color="#d62728", marker="o", label="actual", zorder=3)
    ax.scatter(x, predicted, s=70, color="#1f77b4", marker="s", label="predicted", zorder=3)
    ax.axhline(0, color="#606770", linewidth=0.8, alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([day.strftime("%Y-%m-%d") for day in dates], rotation=25, ha="right")
    ax.set_ylabel(unit)
    ax.set_title(title, loc="left", fontweight="bold", pad=42)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0.0, 1.01),
        borderaxespad=0,
        frameon=False,
        ncol=2,
    )
    ax.text(
        0.99,
        1.01,
        f"n={len(rows)}  MAE={fmt_metric(metrics['mae'], 1)}°  "
        f"RMSE={fmt_metric(metrics['rmse'], 1)}°  R²={fmt_metric(metrics['r2'])}",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "#f4f6f8", "edgecolor": "#ccd3da"},
    )


def location_forecast(
    ax: plt.Axes,
    rows: list[dict[str, str]],
    title: str,
    unit: str,
) -> None:
    dates = [parse_date(row["date"]) for row in rows]
    values = [float(row["estimated_value"]) for row in rows]
    focus = [int(row.get("focus_window", "0") or 0) == 1 for row in rows]
    x = np.arange(len(rows))
    ax.plot(x, values, color="#1f77b4", linewidth=2.2, marker="o", markersize=6)
    for idx, value, selected in zip(x, values, focus):
        if selected:
            ax.scatter([idx], [value], s=130, color="#ff7f0e", edgecolor="black", zorder=4)
            ax.annotate(
                f"{value:.2f}°",
                (idx, value),
                xytext=(0, 12),
                textcoords="offset points",
                ha="center",
                fontweight="bold",
            )
    ax.axhline(0, color="#606770", linewidth=0.8, alpha=0.5)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.set_ylabel(unit)
    ax.set_xlabel("exact 7-day forecast slot")
    ax.set_xticks(x)
    ax.set_xticklabels(seven_day_slot_labels(dates))
    ax.set_xlim(-0.45, len(rows) - 0.55)
    ax.margins(y=0.14)
    ax.grid(axis="y", alpha=0.25)


def create_dashboard(args: argparse.Namespace) -> dict[str, object]:
    timing_validation = read_rows(args.timing_validation_csv)
    timing_forecast_all = read_rows(args.timing_forecast_csv)
    lat_validation = read_rows(args.latitude_validation_csv)
    lat_forecast = read_rows(args.latitude_forecast_csv)
    lon_validation = read_rows(args.longitude_validation_csv)
    lon_forecast = read_rows(args.longitude_forecast_csv)

    forecast_start = parse_date(args.forecast_start_date)
    forecast_end = parse_date(args.forecast_end_date)
    timing_forecast = [
        row
        for row in timing_forecast_all
        if forecast_start.date() <= parse_date(row["context"]).date() <= forecast_end.date()
    ]
    if not timing_forecast:
        raise ValueError("timing forecast has no rows inside requested display window")

    timing_actual = [float(row["actual"]) for row in timing_validation]
    timing_pred = [float(row["predicted"]) for row in timing_validation]
    timing_quality = timing_metrics(timing_actual, timing_pred, args.timing_threshold)
    lat_quality = regression_metrics(
        [float(row["actual_value"]) for row in lat_validation],
        [float(row["predicted_value"]) for row in lat_validation],
    )
    lon_quality = regression_metrics(
        [float(row["actual_value"]) for row in lon_validation],
        [float(row["predicted_value"]) for row in lon_validation],
    )

    fig, axes = plt.subplots(3, 2, figsize=(18, 16), constrained_layout=True)
    fig.suptitle(
        "August 2026 M8.5+ KAN — forecast and historical validation",
        fontsize=18,
        fontweight="bold",
    )

    ax = axes[0, 0]
    validation_dates = [parse_date(row["context"]) for row in timing_validation]
    validation_x = [0.0]
    for idx in range(1, len(validation_dates)):
        step = 1.0 if (validation_dates[idx] - validation_dates[idx - 1]).days == 7 else 3.0
        validation_x.append(validation_x[-1] + step)
    x = np.asarray(validation_x)
    segment_starts = [0]
    for idx in range(1, len(validation_dates)):
        if (validation_dates[idx] - validation_dates[idx - 1]).days != 7:
            segment_starts.append(idx)
    segment_ends = [idx - 1 for idx in segment_starts[1:]] + [len(validation_dates) - 1]
    for segment_no, (start, end) in enumerate(zip(segment_starts, segment_ends)):
        ax.plot(
            x[start : end + 1],
            timing_pred[start : end + 1],
            color="#1f77b4",
            linewidth=2,
            label="KAN event score" if segment_no == 0 else None,
        )
        if start > 0:
            separator_x = 0.5 * (x[start - 1] + x[start])
            ax.axvline(separator_x, color="#7f8c8d", linestyle=":", linewidth=1.4)
    positive_x = [x[idx] for idx, value in enumerate(timing_actual) if value >= 0.5]
    ax.scatter(
        positive_x,
        [1.0] * len(positive_x),
        color="#d62728",
        marker="|",
        s=180,
        linewidths=3,
        label="actual M≥8.5 event",
        zorder=4,
    )
    ax.axhline(
        args.timing_threshold,
        color="#ff7f0e",
        linestyle="--",
        linewidth=1.8,
        label=f"decision threshold {args.timing_threshold:g}",
    )
    tick_positions: list[int] = []
    for start, end in zip(segment_starts, segment_ends):
        tick_positions.extend(range(start, end + 1, 4))
        tick_positions.append(end)
    tick_positions = sorted(set(tick_positions))
    ax.set_xticks([x[idx] for idx in tick_positions])
    ax.set_xticklabels(
        [validation_dates[idx].strftime("%Y-%m-%d") for idx in tick_positions],
        rotation=35,
        ha="right",
        fontsize=8,
    )
    ax.set_ylim(-0.05, 1.05)
    ax.set_ylabel("event score / binary target")
    ax.set_xlabel("7-day validation slots; dotted separators = disconnected historical windows")
    ax.set_title("A. Timing validation", loc="left", fontweight="bold", pad=88)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0.0, 1.01),
        borderaxespad=0,
        frameon=False,
        fontsize=9,
        ncol=3,
    )
    ax.text(
        0.99,
        1.12,
        f"n={timing_quality['rows']}, positives={timing_quality['positive_rows']}  "
        f"TP={timing_quality['tp']} FP={timing_quality['fp']} "
        f"FN={timing_quality['fn']} TN={timing_quality['tn']}  "
        f"recall={fmt_metric(timing_quality['recall'])}  "
        f"balanced acc={fmt_metric(timing_quality['balanced_accuracy'])}",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "#fff4e5", "edgecolor": "#ffbf69"},
    )

    ax = axes[0, 1]
    timing_dates = [parse_date(row["context"]) for row in timing_forecast]
    timing_scores = [float(row["predicted"]) for row in timing_forecast]
    colors = ["#ff7f0e" if score >= args.timing_threshold else "#4c78a8" for score in timing_scores]
    forecast_x = np.arange(len(timing_forecast))
    ax.bar(forecast_x, timing_scores, width=0.68, color=colors)
    ax.axhline(args.timing_threshold, color="#d62728", linestyle="--", linewidth=1.8)
    for idx, score in zip(forecast_x, timing_scores):
        ax.text(idx, score + 0.025, f"{score:.3f}", ha="center", fontsize=9)
    ax.set_ylim(0, max(0.75, max(timing_scores) + 0.12))
    ax.set_ylabel("KAN event score (not calibrated probability)")
    ax.set_xlabel("exact 7-day forecast slot")
    ax.set_title("B. Timing forecast — exact 7-day slots", loc="left", fontweight="bold")
    ax.set_xticks(forecast_x)
    ax.set_xticklabels(seven_day_slot_labels(timing_dates))
    ax.set_xlim(-0.5, len(timing_forecast) - 0.5)
    ax.grid(axis="y", alpha=0.25)

    validation_series(
        axes[1, 0],
        lat_validation,
        "C. Latitude validation",
        "latitude (degrees)",
        lat_quality,
    )
    location_forecast(
        axes[1, 1],
        lat_forecast,
        "D. Latitude forecast (orange = selected timing slot)",
        "latitude (degrees)",
    )
    validation_series(
        axes[2, 0],
        lon_validation,
        "E. Longitude validation",
        "longitude (degrees)",
        lon_quality,
    )
    location_forecast(
        axes[2, 1],
        lon_forecast,
        "F. Longitude forecast (orange = selected timing slot)",
        "longitude (degrees)",
    )

    args.output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_png, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    payload: dict[str, object] = {
        "output_png": str(args.output_png),
        "timing_validation": timing_quality,
        "latitude_validation": lat_quality,
        "longitude_validation": lon_quality,
        "timing_validation_csv": str(args.timing_validation_csv),
        "timing_forecast_csv": str(args.timing_forecast_csv),
        "latitude_validation_csv": str(args.latitude_validation_csv),
        "latitude_forecast_csv": str(args.latitude_forecast_csv),
        "longitude_validation_csv": str(args.longitude_validation_csv),
        "longitude_forecast_csv": str(args.longitude_forecast_csv),
        "interpretation": (
            "At threshold 0.5 the timing validation detects no held-out positive event. "
            "The displayed latitude model is below a mean baseline; the displayed longitude "
            "model has positive R-squared but a very large angular error. Location remains weak."
        ),
    }
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    args.output_md.write_text(
        "# Forecast and validation dashboard\n\n"
        f"![dashboard]({args.output_png.name})\n\n"
        "## Validation summary\n\n"
        f"- timing @ {args.timing_threshold:g}: TP `{timing_quality['tp']}`, "
        f"FP `{timing_quality['fp']}`, FN `{timing_quality['fn']}`, "
        f"TN `{timing_quality['tn']}`, recall `{fmt_metric(timing_quality['recall'])}`\n"
        f"- latitude: MAE `{fmt_metric(lat_quality['mae'], 1)}°`, "
        f"RMSE `{fmt_metric(lat_quality['rmse'], 1)}°`, R² `{fmt_metric(lat_quality['r2'])}`\n"
        f"- longitude: MAE `{fmt_metric(lon_quality['mae'], 1)}°`, "
        f"RMSE `{fmt_metric(lon_quality['rmse'], 1)}°`, R² `{fmt_metric(lon_quality['r2'])}`\n\n"
        "The dashboard is a research diagnostic, not an operational earthquake warning. "
        "Timing scores are not calibrated probabilities; location has no uncertainty radius.\n"
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timing-validation-csv", required=True, type=Path)
    parser.add_argument("--timing-forecast-csv", required=True, type=Path)
    parser.add_argument("--latitude-validation-csv", required=True, type=Path)
    parser.add_argument("--latitude-forecast-csv", required=True, type=Path)
    parser.add_argument("--longitude-validation-csv", required=True, type=Path)
    parser.add_argument("--longitude-forecast-csv", required=True, type=Path)
    parser.add_argument("--forecast-start-date", default="2026-07-29")
    parser.add_argument("--forecast-end-date", default="2026-08-31")
    parser.add_argument("--timing-threshold", type=float, default=0.5)
    parser.add_argument("--output-png", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        payload = create_dashboard(args)
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"ERROR topdown_forecast_validation_dashboard: {exc}") from exc
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
