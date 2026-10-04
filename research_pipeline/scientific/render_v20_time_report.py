#!/usr/bin/env python3
"""Render the high-resolution English V20 time-connection report."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import textwrap
from zoneinfo import ZoneInfo

os.environ.setdefault("MPLCONFIGDIR", "/tmp/dlvswave-v20-matplotlib")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import ListedColormap
import numpy as np
import pandas as pd


NAVY = "#17324d"
BLUE = "#3278bd"
ORANGE = "#f28e2b"
GREEN = "#2e8b57"
RED = "#c93434"
PURPLE = "#7251c9"
GREY = "#607286"
LIGHT = "#eef3f8"
PALE = "#f8fafc"
BAND_COLORS = ["#4c78a8", "#72b7b2", "#f2cf5b", "#e45756"]
REPORT_ISSUE_TEXT = ""


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--project-dir", type=Path, required=True)
    value.add_argument("--config", type=Path, default=None)
    value.add_argument(
        "--issued-at",
        default=None,
        help="Optional ISO-8601 report issue datetime; naive values use report.issue_timezone.",
    )
    return value


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_project_path(project: Path, value: str | Path) -> Path:
    """Resolve a report input against the project without hard-coded study paths."""
    path = Path(value)
    return path if path.is_absolute() else (project / path).resolve()


def configured_time_band_sources(settings: dict) -> list[dict]:
    """Return configured comparison sources, with legacy single-source support."""
    sources = settings.get("time_band_forecast_sources")
    if sources:
        return [dict(source) for source in sources]
    if settings.get("time_band_forecast_csv"):
        return [
            {
                "label": "Sequential weighted",
                "forecast_csv": settings["time_band_forecast_csv"],
                "validation_summary_key": "nested_sequential_weighted",
                "color": BLUE,
            }
        ]
    raise ValueError("Historical comparison requires at least one time-band forecast source")


def resolve_issue_datetime(config: dict, explicit: str | None) -> datetime:
    """Resolve a reproducible issue time in the configured report timezone."""
    timezone = ZoneInfo(str(config["report"].get("issue_timezone", "UTC")))
    if not explicit:
        return datetime.now(timezone)
    value = explicit.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    issued = datetime.fromisoformat(value)
    if issued.tzinfo is None:
        issued = issued.replace(tzinfo=timezone)
    return issued.astimezone(timezone)


def clean_feature(value: str) -> str:
    value = str(value)
    body = re.search(r"body:([^|]+)", value)
    field = re.search(r"eph:([^|]+)", value)
    if body and field:
        name = body.group(1).replace("_system_barycenter", "")
        name = name.replace("_barycenter", "").replace("_", " ").title()
        measure = field.group(1).replace("_", " ")
        return f"{name} · {measure}"
    return value.replace("_at_band_center", "").replace("_", " ").title()


def setup_plot_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titlesize": 18,
            "axes.labelsize": 13,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
            "axes.edgecolor": NAVY,
            "axes.titleweight": "bold",
            "figure.facecolor": "white",
        }
    )


def save_figure(fig, path: Path, dpi: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def boundary_grid(ax, count: int) -> None:
    ax.set_xlim(-0.5, count - 0.5)
    ax.set_xticks(np.arange(-0.5, count, 1.0), minor=True)
    ax.grid(which="minor", axis="x", color="#b7c4d2", linewidth=0.8, alpha=0.75)
    ax.grid(which="major", axis="y", color="#d5dde6", linewidth=0.7, alpha=0.7)


def catalog_figure(project: Path, config: dict, summary: dict, dpi: int) -> Path:
    master = pd.read_csv(project / "01_inputs/event_time_master.csv")
    events = master[master["sample_kind"].eq("event")].copy()
    times = pd.to_datetime(events["sample_time_local"], utc=True, format="mixed")
    bands = events["target_band"].astype(int).to_numpy()
    labels = config["time_target"]["band_labels"]
    outer_count = int(config["time_target"]["required_outer_validation_events"])
    split = len(events) - outer_count
    fig, axes = plt.subplots(2, 1, figsize=(16, 9), gridspec_kw={"height_ratios": [1.35, 1]})
    fig.suptitle("V20 trusted event-time catalogue — same-day six-hour astronomical epochs", fontsize=23, fontweight="bold")
    ax = axes[0]
    for band in range(4):
        mask = bands == band
        ax.scatter(times[mask], bands[mask], s=85, color=BAND_COLORS[band], edgecolor="white", linewidth=0.8, label=labels[band], zorder=3)
    ax.scatter(times.iloc[split:], bands[split:], s=190, marker="*", facecolor="none", edgecolor=NAVY, linewidth=1.6, label="outer holdout", zorder=4)
    ax.axvline(times.iloc[split], color=RED, linestyle="--", linewidth=1.5, label="outer-validation frontier")
    ax.set_yticks(range(4), ["00–06", "06–12", "12–18", "18–24"])
    ax.set_ylabel("six-hour JST target band")
    ax.grid(axis="x", color="#c7d1dc", alpha=0.75)
    ax.grid(axis="y", color="#d9e0e8", alpha=0.7)
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.20))
    ax.set_title("24 USGS-timestamped Japan-region M≥7.9 events; stars are the nine chronological holdouts")

    ax = axes[1]
    train = events.iloc[:split]["target_band"].value_counts().reindex(range(4), fill_value=0)
    outer = events.iloc[split:]["target_band"].value_counts().reindex(range(4), fill_value=0)
    x = np.arange(4)
    ax.bar(x, train, color=BAND_COLORS, edgecolor="white", label="pre-holdout development")
    ax.bar(x, outer, bottom=train, color=BAND_COLORS, hatch="///", edgecolor=NAVY, alpha=0.75, label="outer validation")
    for index, (a, b) in enumerate(zip(train, outer)):
        ax.text(index, a + b + 0.15, f"{a+b} total", ha="center", fontweight="bold")
    ax.set_xticks(x, labels)
    ax.set_ylabel("event count")
    ax.grid(axis="y", color="#d9e0e8", alpha=0.75)
    ax.legend(loc="upper right")
    ax.set_title("Every target band is represented in development and outer validation")
    fig.text(0.5, 0.015, "No worldwide non-Japan hard-negative records are present. Historical conventional-midnight rows are excluded.", ha="center", color=GREY)
    fig.tight_layout(rect=[0.02, 0.04, 0.98, 0.94])
    path = project / "06_report/v20_event_time_catalog.png"
    save_figure(fig, path, dpi)
    return path


def search_figure(project: Path, dpi: int) -> Path:
    screen = pd.read_csv(project / "03_feature_research/time_band_hyperparameter_trials.csv")
    screen = screen[screen["status"].eq("COMPLETE")].copy()
    winners = screen.sort_values("selection_score", ascending=False).groupby("family", sort=False).head(1)
    feature = pd.read_csv(project / "03_feature_research/time_band_feature_count_trials.csv").sort_values("feature_count")
    systems = pd.read_csv(project / "03_feature_research/time_band_system_search.csv").sort_values("quality", ascending=False).head(10)
    fig, axes = plt.subplots(1, 3, figsize=(16, 8.8), gridspec_kw={"width_ratios": [1.15, 1, 1.15]})
    fig.suptitle("V20 nested feature and hyperparameter search", fontsize=23, fontweight="bold")
    ax = axes[0]
    order = winners.sort_values("quality")
    y = np.arange(len(order))
    ax.barh(y, order["quality"], color=BLUE, label="inner quality")
    ax.scatter(order["selection_score"], y, color=ORANGE, marker="D", s=55, label="quality + speed score", zorder=3)
    ax.set_yticks(y, [value.replace("_", " ") for value in order["family"]])
    ax.set_xlim(0, max(0.8, order[["quality", "selection_score"]].max().max() + 0.08))
    ax.set_xlabel("higher-is-better")
    ax.set_title("Promoted candidate per family")
    ax.grid(axis="x", color="#d5dde6", alpha=0.7)
    ax.legend(loc="lower right")

    ax = axes[1]
    ax.plot(feature["feature_count"], feature["quality"], color=PURPLE, marker="o", linewidth=2.4, label="inner quality")
    ax.plot(feature["feature_count"], feature["qualified_accuracy"], color=GREEN, marker="s", linewidth=1.8, label="qualified accuracy")
    best = feature.sort_values("quality", ascending=False).iloc[0]
    ax.axvline(best["feature_count"], color=ORANGE, linestyle="--")
    ax.text(best["feature_count"], min(0.98, best["quality"] + 0.08), f"selected {int(best['feature_count'])}", ha="center", color="#a54d0b", fontweight="bold")
    ax.set_xlabel("ranked feature count")
    ax.set_ylabel("higher-is-better")
    ax.set_ylim(0, 1.02)
    ax.set_title("Training-only feature-count search")
    ax.grid(color="#d5dde6", alpha=0.7)
    ax.legend(loc="lower right")

    ax = axes[2]
    order = systems.sort_values("quality")
    y = np.arange(len(order))
    ax.barh(y, order["quality"], color=GREEN)
    ax.scatter(order["qualified_accuracy"], y, color=ORANGE, s=45, marker="D", label="qualified accuracy")
    ax.set_yticks(y, [value.replace("_", " ") for value in order["system"]])
    ax.set_xlim(0, 1.02)
    ax.set_xlabel("higher-is-better")
    ax.set_title("Candidate hybrid systems")
    ax.grid(axis="x", color="#d5dde6", alpha=0.7)
    ax.legend(loc="lower right")
    fig.text(0.5, 0.015, "All selections use events before the outer-validation frontier. Outer holdouts do not select features or hyperparameters.", ha="center", color=GREY)
    fig.tight_layout(rect=[0.02, 0.04, 0.98, 0.94])
    path = project / "06_report/v20_model_search.png"
    save_figure(fig, path, dpi)
    return path


def validation_figure(project: Path, config: dict, method: str, title: str, filename: str, dpi: int) -> Path:
    data = pd.read_csv(project / "05_ensemble/time_band_validation.csv")
    data = data[data["method"].eq(method)].reset_index(drop=True)
    labels = config["time_target"]["band_labels"]
    probabilities = data[[f"band_{band}_score_not_probability" for band in range(4)]].to_numpy(float)
    actual = data["actual_band"].to_numpy(int)
    predicted = data["predicted_band"].to_numpy(int)
    x = np.arange(len(data))
    xticklabels = [f"{str(value)[:10]}\nM{mag:.2f}" for value, mag in zip(data["event_time_local"], data["mag"])]
    fig, axes = plt.subplots(2, 1, figsize=(16, 9), gridspec_kw={"height_ratios": [1, 1.4]})
    fig.suptitle(title, fontsize=23, fontweight="bold")
    ax = axes[0]
    ax.plot(x, actual, color=RED, marker="o", linewidth=2.0, markersize=8, label="actual JST band")
    ax.plot(x, predicted + 0.06, color=BLUE, marker="s", linestyle="--", linewidth=1.8, markersize=7, label="predicted band (offset +0.06 only for visibility)")
    for index in x:
        status = "MATCH" if actual[index] == predicted[index] else "weak" if bool(data.loc[index, "qualified_exact_or_weak"]) else "miss"
        color = GREEN if status == "MATCH" else ORANGE if status == "weak" else GREY
        ax.text(index, max(actual[index], predicted[index]) + 0.20, status.upper(), ha="center", fontsize=8, color=color, fontweight="bold")
    ax.set_yticks(range(4), ["00–06", "06–12", "12–18", "18–24"])
    ax.set_ylim(-0.45, 3.55)
    ax.set_xticks(x, xticklabels, rotation=28, ha="right")
    ax.set_ylabel("six-hour JST band")
    boundary_grid(ax, len(data))
    ax.legend(loc="upper center", ncol=2)
    ax.set_title("Chronological holdouts — actual and predicted classes")

    ax = axes[1]
    image = ax.imshow(probabilities.T, aspect="auto", cmap="Blues", vmin=0, vmax=max(0.5, probabilities.max()))
    for column in range(len(data)):
        for band in range(4):
            ax.text(column, band, f"{probabilities[column, band]:.2f}", ha="center", va="center", fontsize=8, color="white" if probabilities[column, band] > 0.36 else NAVY)
        ax.scatter(column, actual[column], marker="*", s=150, facecolor=ORANGE, edgecolor="white", linewidth=0.8)
    ax.set_yticks(range(4), labels)
    ax.set_xticks(x, xticklabels, rotation=28, ha="right")
    ax.set_xlabel("holdout event; stars mark the actual band")
    ax.set_title("Four-class score matrix (relative scores, not calibrated probabilities)")
    boundary_grid(ax, len(data))
    fig.colorbar(image, ax=ax, fraction=0.025, pad=0.015, label="relative class score")
    fig.tight_layout(rect=[0.02, 0.03, 0.98, 0.94])
    path = project / f"06_report/{filename}"
    save_figure(fig, path, dpi)
    return path


def comparison_figure(project: Path, summary: dict, dpi: int) -> Path:
    validation = summary["validation"]
    mapping = [
        ("nested_sequential_weighted", "sequential weighted", BLUE),
        ("one_shot_pre_holdout", "one-shot", PURPLE),
        ("target_label_permutation_null", "label-shuffle null", ORANGE),
    ]
    metrics = [
        ("exact_accuracy", "exact"),
        ("qualified_accuracy_exact_or_weak", "exact or weak"),
        ("adjacent_or_exact_accuracy", "within adjacent"),
        ("quality_higher_is_better", "overall quality"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(16, 8.6), gridspec_kw={"width_ratios": [1.35, 1]})
    fig.suptitle("V20 validation comparison — promoted model, one-shot and randomized-label null", fontsize=22, fontweight="bold")
    ax = axes[0]
    x = np.arange(len(metrics))
    width = 0.24
    for offset, (key, label, color) in enumerate(mapping):
        payload = validation.get(key)
        values = [float(payload[metric]) for metric, _ in metrics]
        bars = ax.bar(x + (offset - 1) * width, values, width, color=color, label=label)
        ax.bar_label(bars, fmt="%.2f", padding=2, fontsize=9)
    ax.set_xticks(x, [label for _, label in metrics])
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("higher-is-better")
    ax.grid(axis="y", color="#d5dde6", alpha=0.75)
    ax.legend(loc="upper right")
    ax.set_title("Nine outer holdouts across all four JST bands", fontsize=15, pad=10)

    ax = axes[1]
    ax.axis("off")
    rows = []
    for key, label, _ in mapping:
        payload = validation.get(key)
        rows.append(
            [
                label,
                f"{payload['exact_accuracy']:.3f}",
                f"{payload['adjacent_or_exact_accuracy']:.3f}",
                f"{payload['mean_circular_band_error']:.3f}",
                f"{payload['mean_true_band_probability']:.3f}",
            ]
        )
    table = ax.table(
        cellText=rows,
        colLabels=["method", "exact", "adjacent", "circular error", "true-band score"],
        cellLoc="center",
        loc="center",
        colWidths=[0.34, 0.15, 0.17, 0.18, 0.18],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1, 2.0)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#b7c7d8")
        if row == 0:
            cell.set_facecolor(NAVY)
            cell.get_text().set_color("white")
            cell.get_text().set_fontweight("bold")
        elif row % 2:
            cell.set_facecolor(LIGHT)
    ax.set_title(
        "Accuracy alone is not sufficient\n"
        "circular tolerance is reported separately",
        fontsize=14,
        pad=10,
    )
    fig.text(0.5, 0.025, "The one-shot result is weaker than the sequential fit; this limits confidence even where their future band ranking agrees.", ha="center", color=RED, fontweight="bold")
    fig.tight_layout(rect=[0.02, 0.06, 0.98, 0.93])
    path = project / "06_report/v20_validation_comparison.png"
    save_figure(fig, path, dpi)
    return path


def forecast_figure(project: Path, config: dict, summary: dict, dpi: int) -> Path:
    weighted = pd.read_csv(project / "05_ensemble/time_band_weighted_forecast.csv")
    one_shot = pd.read_csv(project / "05_ensemble/time_band_one_shot_forecast.csv")
    labels = config["time_target"]["band_labels"]
    x = np.arange(len(weighted))
    xticklabels = [f"{start}\n{end}" for start, end in zip(weighted["forecast_slot_start"], weighted["forecast_slot_end"])]
    fig, axes = plt.subplots(3, 1, figsize=(16, 10.2), gridspec_kw={"height_ratios": [1, 1, 0.9]})
    fig.suptitle("V20 conditional six-hour forecast — daily JPL sampling inside every 90-day timing slot", fontsize=22, fontweight="bold")
    for ax, frame, name in zip(axes[:2], [weighted, one_shot], ["Validation-weighted sequential ensemble", "Independent one-shot full-history refit"]):
        bottom = np.zeros(len(frame))
        for band in range(4):
            values = frame[f"band_{band}_score_not_probability"].to_numpy(float)
            ax.bar(x, values, bottom=bottom, width=0.76, color=BAND_COLORS[band], edgecolor="white", label=labels[band])
            bottom += values
        predicted = frame["predicted_band"].to_numpy(int)
        for index, band in enumerate(predicted):
            ax.text(index, 1.025, f"{band}: {labels[band].split()[0]}", ha="center", fontsize=8.5, color=NAVY, fontweight="bold")
        ax.set_ylim(0, 1.11)
        ax.set_ylabel("normalized relative share")
        ax.set_xticks(x, xticklabels, rotation=20, ha="right")
        boundary_grid(ax, len(frame))
        ax.set_title(name)
    axes[0].legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.35))

    ax = axes[2]
    primary = summary["forecast"]["weighted_focus"]["band_scores_not_probabilities"]
    single = summary["forecast"]["one_shot_focus"]["band_scores_not_probabilities"]
    groups = np.arange(4)
    width = 0.36
    b1 = ax.bar(groups - width / 2, primary, width, color=BLUE, label="weighted focus")
    b2 = ax.bar(groups + width / 2, single, width, color=PURPLE, label="one-shot focus")
    ax.bar_label(b1, fmt="%.3f", padding=2, fontsize=9)
    ax.bar_label(b2, fmt="%.3f", padding=2, fontsize=9)
    ax.set_xticks(groups, labels)
    ax.set_ylim(0, max(max(primary), max(single)) + 0.13)
    ax.set_ylabel("relative score")
    ax.grid(axis="y", color="#d5dde6", alpha=0.7)
    ax.legend(loc="upper left")
    ax.set_title("Timing-weighted focus: 3 June–29 November 2026 — both methods select 18:00–23:59 JST")
    fig.text(0.5, 0.012, "Conditional experimental scores only: these bars do not estimate whether, when, or with what probability an earthquake will occur.", ha="center", color=RED, fontweight="bold")
    fig.tight_layout(rect=[0.02, 0.035, 0.98, 0.95])
    path = project / "06_report/v20_time_band_forecast.png"
    save_figure(fig, path, dpi)
    return path


def historical_forecast_figure(project: Path, config: dict, summary: dict, dpi: int) -> Path:
    """Reproduce a configured historical timing forecast and add a V20 band overlay."""
    settings = config["report"]["historical_forecast_comparison"]
    source_label = str(settings["source_pipeline_label"])
    source_path = resolve_project_path(project, settings["source_forecast_csv"])
    source = pd.read_csv(source_path)
    date_column = settings.get("source_date_column", "date")
    end_column = settings.get("source_slot_end_inclusive_column", "slot_end_inclusive")
    score_column = settings.get("source_score_column", "score_percentile_not_probability")
    required = {date_column, score_column}
    missing = sorted(required.difference(source.columns))
    if missing:
        raise ValueError(f"Historical forecast is missing configured columns: {missing}")
    source = source.copy()
    source["_slot_start"] = pd.to_datetime(source[date_column]).dt.normalize()
    if end_column in source:
        source["_slot_end_exclusive"] = pd.to_datetime(source[end_column]).dt.normalize() + pd.Timedelta(days=1)
    else:
        source["_slot_end_exclusive"] = source["_slot_start"] + pd.to_timedelta(
            int(settings["source_resolution_days"]), unit="D"
        )
    source["_score"] = pd.to_numeric(source[score_column], errors="raise")
    source = source.sort_values("_slot_start").reset_index(drop=True)
    best_index = int(source["_score"].to_numpy(float).argmax())
    best = source.iloc[best_index]
    best_start = pd.Timestamp(best["_slot_start"])
    best_end = pd.Timestamp(best["_slot_end_exclusive"])

    match_policy = settings.get("time_band_match_policy", "forecast_slot_containing_historical_peak")
    if match_policy != "forecast_slot_containing_historical_peak":
        raise ValueError(f"Unsupported historical time-band match policy: {match_policy}")
    band_results = []
    for source_settings in configured_time_band_sources(settings):
        time_band_path = resolve_project_path(project, source_settings["forecast_csv"])
        time_bands = pd.read_csv(time_band_path)
        time_bands["_start"] = pd.to_datetime(time_bands["forecast_slot_start"]).dt.normalize()
        time_bands["_end_exclusive"] = pd.to_datetime(time_bands["forecast_slot_end"]).dt.normalize() + pd.Timedelta(days=1)
        matching = time_bands[
            time_bands["_start"].le(best_start)
            & time_bands["_end_exclusive"].ge(best_end)
        ]
        if len(matching) != 1:
            raise ValueError(
                "The historical peak must be wholly contained in exactly one configured V20 forecast slot; "
                f"source {source_settings['label']} found {len(matching)} matches for "
                f"[{best_start.date()}, {best_end.date()})."
            )
        band_row = matching.iloc[0]
        band = int(band_row["predicted_band"])
        validation_key = str(source_settings["validation_summary_key"])
        validation = summary["validation"][validation_key]
        band_results.append(
            {
                "label": str(source_settings["label"]),
                "forecast_csv": str(time_band_path),
                "validation_summary_key": validation_key,
                "color": str(source_settings.get("color", BLUE)),
                "start_inclusive": str(band_row["forecast_slot_start"]),
                "end_inclusive": str(band_row["forecast_slot_end"]),
                "predicted_band": band,
                "predicted_band_label": str(band_row["predicted_band_label"]),
                "conditional_relative_share_not_probability": float(
                    band_row[f"band_{band}_score_not_probability"]
                ),
                "validation_exact_accuracy": float(validation["exact_accuracy"]),
                "validation_adjacent_or_exact_accuracy": float(validation["adjacent_or_exact_accuracy"]),
                "validation_quality_higher_is_better": float(validation["quality_higher_is_better"]),
            }
        )

    count = len(source)
    x = np.arange(count, dtype=float) + 0.5
    scores = source["_score"].to_numpy(float)
    colors = [ORANGE if index == best_index else "#4e79a7" for index in range(count)]
    labels = [
        f"[{start:%Y-%m-%d},\n {end:%Y-%m-%d})"
        for start, end in zip(source["_slot_start"], source["_slot_end_exclusive"])
    ]
    fig, ax = plt.subplots(figsize=(16, 9))
    fig.suptitle(
        f"Previous {source_label} forecast — "
        f"{int(settings['source_resolution_days'])}-day resolution",
        fontsize=23,
        fontweight="bold",
        y=0.965,
    )
    ax.set_position([0.08, 0.25, 0.88, 0.58])
    bars = ax.bar(x, scores, width=0.72, color=colors, edgecolor="white", linewidth=0.9, zorder=3)
    ax.bar_label(bars, labels=[f"{score:.3f}" for score in scores], padding=4, fontsize=11, fontweight="bold")
    ax.set_xlim(0, count)
    ax.set_ylim(0, 1.06)
    ax.set_xticks(x, labels, rotation=27, ha="right")
    ax.set_xticks(np.arange(count + 1, dtype=float), minor=True)
    ax.grid(which="minor", axis="x", color="#b7c4d2", linewidth=0.9, alpha=0.8)
    ax.grid(which="major", axis="y", color="#cbd5df", linewidth=0.8, alpha=0.75)
    ax.set_ylabel(f"{source_label} empirical timing rank (0–1; not a calibrated probability)")
    ax.set_xlabel(
        f"Complete {int(settings['source_resolution_days'])}-day intervals [start, end); "
        "bars are centred between exact temporal boundaries"
    )
    ax.set_title(
        f"Historical {source_label} page {int(settings['source_report_page'])} result reproduced from its forecast CSV\n"
        f"Peak {scores[best_index]:.3f}: [{best_start:%Y-%m-%d}, {best_end:%Y-%m-%d})",
        fontsize=16,
        pad=12,
    )
    ax.text(
        x[best_index],
        max(0.06, scores[best_index] * 0.48),
        f"{source_label} HIGHEST-RANKED\nSEVEN-DAY SLOT",
        ha="center",
        va="center",
        color="white",
        fontsize=10,
        fontweight="bold",
    )
    annotation_x = min(count - 0.2, x[best_index] + 1.25)
    estimate_lines = ["V20 SAME-DAY TIME-BAND ESTIMATES"] + [
        f"{result['label']}: {result['predicted_band_label']} · "
        f"share {result['conditional_relative_share_not_probability']:.3f}"
        for result in band_results
    ]
    ax.annotate(
        "\n".join(estimate_lines),
        xy=(x[best_index], scores[best_index]),
        xytext=(annotation_x, 0.91),
        ha="center",
        va="center",
        fontsize=10.2,
        color=NAVY,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#fff5e8", "edgecolor": ORANGE, "linewidth": 1.5},
        arrowprops={"arrowstyle": "->", "color": ORANGE, "linewidth": 1.8},
        zorder=5,
    )
    fig.text(
        0.08,
        0.145,
        "Historical context",
        fontsize=12.5,
        fontweight="bold",
        color=NAVY,
    )
    fig.text(
        0.08,
        0.108,
        f"The orange slot is the previous {source_label} seven-day forecast peak. Each configured V20 method is matched to the forecast slot that wholly contains this seven-day interval; both currently select the same evening band.",
        fontsize=9.6,
        color="#304d68",
        wrap=True,
    )
    validation_note = "Validation reminder — " + "; ".join(
        f"{result['label']}: exact {result['validation_exact_accuracy']:.1%}, "
        f"adjacent/exact {result['validation_adjacent_or_exact_accuracy']:.1%}, "
        f"quality {result['validation_quality_higher_is_better']:.3f}"
        for result in band_results
    )
    fig.text(0.08, 0.073, validation_note, fontsize=9.4, color=NAVY, fontweight="bold", wrap=True)
    fig.text(
        0.08,
        0.03,
        "The overlay is a cross-study contextual annotation: it does not recalibrate the V10 timing score and does not turn either score into an earthquake probability.",
        fontsize=9.5,
        color=RED,
        fontweight="bold",
    )
    output = resolve_project_path(project, settings["output_png"])
    trace = {
        "source_pipeline_label": settings["source_pipeline_label"],
        "source_report_page": int(settings["source_report_page"]),
        "source_resolution_days": int(settings["source_resolution_days"]),
        "source_forecast_csv": str(source_path),
        "historical_peak": {
            "start_inclusive": f"{best_start:%Y-%m-%d}",
            "end_exclusive": f"{best_end:%Y-%m-%d}",
            "score_not_probability": float(scores[best_index]),
        },
        "v20_time_band_estimates": band_results,
        "semantics": "cross-study contextual annotation; no score recalibration",
        "output_png": str(output),
    }
    trace_path = resolve_project_path(project, settings["output_trace_json"])
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
    save_figure(fig, output, dpi)
    return output


def feature_figure(project: Path, dpi: int) -> Path:
    ranking = pd.read_csv(project / "03_feature_research/time_band_feature_ranking.csv")
    selected = ranking[ranking["selected"].astype(bool)].head(24).copy()
    selected = selected.iloc[::-1]
    score = 1.0 - selected["mean_rank"] / max(float(ranking["mean_rank"].max()), 1.0)
    fig, ax = plt.subplots(figsize=(16, 9))
    y = np.arange(len(selected))
    colors = [PURPLE if "Moon" in clean_feature(value) else BLUE for value in selected["feature"]]
    ax.barh(y, score, color=colors)
    ax.set_yticks(y, [clean_feature(value) for value in selected["feature"]])
    ax.set_xlabel("normalized consensus rank (higher is better)")
    ax.set_xlim(0, 1.02)
    ax.grid(axis="x", color="#d5dde6", alpha=0.75)
    ax.set_title("V20 selected astronomical features — top 24 of the selected 48", fontsize=22, pad=20)
    ax.text(0.99, 0.02, "Purple = lunar field", transform=ax.transAxes, ha="right", color=PURPLE, fontweight="bold")
    fig.tight_layout()
    path = project / "06_report/v20_feature_ranking.png"
    save_figure(fig, path, dpi)
    return path


def runtime_figure(project: Path, dpi: int) -> Path:
    runtime = pd.read_csv(project / "04_models/time_band_final_attempt_runtimes.csv")
    grouped = runtime.groupby(["phase", "family"], as_index=False)["seconds"].mean()
    phases = list(grouped["phase"].drop_duplicates())
    families = list(grouped["family"].drop_duplicates())
    fig, ax = plt.subplots(figsize=(16, 8.5))
    x = np.arange(len(families))
    width = 0.8 / max(len(phases), 1)
    for index, phase in enumerate(phases):
        subset = grouped[grouped["phase"].eq(phase)].set_index("family")
        values = [float(subset.loc[family, "seconds"]) if family in subset.index else 0.0 for family in families]
        ax.bar(x + (index - (len(phases) - 1) / 2) * width, values, width, label=phase.replace("_", " "))
    ax.axhline(180.0, color=RED, linestyle="--", label="hard limit 180s")
    ax.set_yscale("symlog", linthresh=0.01)
    ax.set_xticks(x, [value.replace("_", " ") for value in families], rotation=20, ha="right")
    ax.set_ylabel("mean seconds per multiclass family attempt — logarithmic above 0.01s")
    ax.set_title("V20 final-fit runtime audit — every attempt remained below the same hard cap", fontsize=22, pad=20)
    ax.grid(axis="y", color="#d5dde6", alpha=0.7)
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.10))
    fig.tight_layout()
    path = project / "06_report/v20_runtime_audit.png"
    save_figure(fig, path, dpi)
    return path


def page_header(fig, title: str, page: int) -> None:
    fig.text(0.055, 0.93, title, fontsize=25, fontweight="bold", color=NAVY)
    fig.add_artist(plt.Line2D([0.055, 0.945], [0.895, 0.895], color="#b8cadb", linewidth=1.0))
    fig.text(0.055, 0.035, "V20 TIME CONNECTION FINDER · EXPERIMENTAL", fontsize=8.5, color="#7c8da0")
    if REPORT_ISSUE_TEXT:
        fig.text(0.5, 0.035, f"Issued {REPORT_ISSUE_TEXT}", fontsize=8.0, color="#7c8da0", ha="center")
    fig.text(0.94, 0.035, str(page), fontsize=8.5, color="#7c8da0", ha="right")


def text_page(pdf: PdfPages, title: str, page: int, blocks: list[tuple[str, str]], accent: str = BLUE) -> None:
    fig = plt.figure(figsize=(11.7, 8.3))
    page_header(fig, title, page)
    y = 0.83
    for heading, body in blocks:
        lines = textwrap.wrap(body, width=115)
        height = 0.032 * max(len(lines), 1) + 0.075
        fig.add_artist(plt.Rectangle((0.065, y - height + 0.015), 0.87, height, facecolor=PALE, edgecolor="#d2deea", linewidth=0.8))
        fig.text(0.082, y - 0.015, heading, fontsize=13, fontweight="bold", color=accent)
        fig.text(0.082, y - 0.058, "\n".join(lines), fontsize=10.2, color="#304d68", va="top", linespacing=1.35)
        y -= height + 0.025
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def image_page(pdf: PdfPages, title: str, page: int, image_path: Path) -> None:
    fig = plt.figure(figsize=(11.7, 8.3))
    page_header(fig, title, page)
    ax = fig.add_axes([0.055, 0.075, 0.89, 0.79])
    ax.imshow(plt.imread(image_path))
    ax.axis("off")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def table_page(pdf: PdfPages, title: str, page: int, frame: pd.DataFrame, columns: list[str], labels: list[str], note: str, rows_per_page: int = 18) -> int:
    chunks = [frame.iloc[index:index + rows_per_page] for index in range(0, len(frame), rows_per_page)] or [frame]
    for chunk_id, chunk in enumerate(chunks):
        fig = plt.figure(figsize=(11.7, 8.3))
        page_header(fig, title + (f" — continued {chunk_id + 1}" if len(chunks) > 1 else ""), page)
        ax = fig.add_axes([0.055, 0.13, 0.89, 0.70])
        ax.axis("off")
        cells = [[str(value)[:42] for value in row] for row in chunk[columns].itertuples(index=False, name=None)]
        table = ax.table(cellText=cells, colLabels=labels, cellLoc="left", loc="upper center")
        table.auto_set_font_size(False)
        table.set_fontsize(7.7)
        table.scale(1, 1.45)
        for (row, col), cell in table.get_celld().items():
            cell.set_edgecolor("#bdcddd")
            if row == 0:
                cell.set_facecolor(NAVY)
                cell.get_text().set_color("white")
                cell.get_text().set_fontweight("bold")
            elif row % 2:
                cell.set_facecolor(LIGHT)
        fig.text(0.065, 0.085, textwrap.fill(note, 145), fontsize=8.5, color=GREY)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
        page += 1
    return page


def write_markdown(project: Path, config: dict, summary: dict, issued_at: datetime) -> Path:
    labels = config["time_target"]["band_labels"]
    weighted = summary["validation"]["nested_sequential_weighted"]
    one = summary["validation"]["one_shot_pre_holdout"]
    null = summary["validation"]["target_label_permutation_null"]
    wband = int(summary["forecast"]["weighted_focus"]["predicted_band"])
    oband = int(summary["forecast"]["one_shot_focus"]["predicted_band"])
    historical_section = ""
    historical = config["report"].get("historical_forecast_comparison", {})
    if historical.get("enabled", False):
        old = pd.read_csv(resolve_project_path(project, historical["source_forecast_csv"]))
        score_column = historical.get("source_score_column", "score_percentile_not_probability")
        date_column = historical.get("source_date_column", "date")
        end_column = historical.get("source_slot_end_inclusive_column", "slot_end_inclusive")
        peak = old.loc[pd.to_numeric(old[score_column]).idxmax()]
        peak_start = pd.Timestamp(peak[date_column]).normalize()
        if end_column in old:
            peak_end = pd.Timestamp(peak[end_column]).normalize() + pd.Timedelta(days=1)
        else:
            peak_end = peak_start + pd.Timedelta(days=int(historical["source_resolution_days"]))
        estimate_lines = []
        for source_settings in configured_time_band_sources(historical):
            bands = pd.read_csv(resolve_project_path(project, source_settings["forecast_csv"]))
            starts = pd.to_datetime(bands["forecast_slot_start"]).dt.normalize()
            ends = pd.to_datetime(bands["forecast_slot_end"]).dt.normalize() + pd.Timedelta(days=1)
            matching = bands[starts.le(peak_start) & ends.ge(peak_end)]
            if len(matching) != 1:
                raise ValueError(
                    f"Markdown historical comparison could not resolve one containing V20 slot for {source_settings['label']}"
                )
            band_row = matching.iloc[0]
            band = int(band_row["predicted_band"])
            validation = summary["validation"][source_settings["validation_summary_key"]]
            estimate_lines.append(
                f"- **{source_settings['label']}:** {band_row['predicted_band_label']}, conditional relative share "
                f"{float(band_row[f'band_{band}_score_not_probability']):.3f}; validation exact "
                f"{validation['exact_accuracy']:.1%}, adjacent/exact {validation['adjacent_or_exact_accuracy']:.1%}, "
                f"quality {validation['quality_higher_is_better']:.3f}."
            )
        estimates = "\n".join(estimate_lines)
        historical_section = f"""
## Previous {historical['source_pipeline_label']} seven-day forecast

The configured historical comparison reproduces page {int(historical['source_report_page'])} of the previous {historical['source_pipeline_label']} report from its source CSV. Its highest-ranked interval is **[{peak_start:%Y-%m-%d}, {peak_end:%Y-%m-%d})** with score **{float(peak[score_column]):.3f}**. The graph annotates every configured V20 conditional same-day estimate on the same peak bar:

{estimates}

This is a contextual overlay, not a recalibration. A smoother adjacent-band trend does not by itself imply better exact-band validation.
"""
    text = f"""# V20 Time Connection Finder — experimental report

**Report issued:** {issued_at.strftime(config['report']['issue_datetime_format'])}

**Issue timestamp:** `{issued_at.isoformat()}`

This experiment classifies the local Japan Standard Time band of an event, conditional on a trusted M≥7.9 Japan-region event timestamp. It does not predict earthquake occurrence.

## Data contract

- 24 trusted USGS-timestamped events; historical conventional-midnight rows excluded.
- Four six-hour bands in Asia/Tokyo.
- Same-day JPL feature epoch at the centre of the observed band.
- Daily forecast sampling, four candidate epochs per day.
- No worldwide non-Japan hard-negative rows.
- 97 available fields; {summary['feature_search']['selected_features']} selected without using outer holdouts.

## Validation

| Method | Exact | Exact or weak | Adjacent or exact | Quality |
|---|---:|---:|---:|---:|
| Sequential weighted | {weighted['exact_accuracy']:.3f} | {weighted['qualified_accuracy_exact_or_weak']:.3f} | {weighted['adjacent_or_exact_accuracy']:.3f} | {weighted['quality_higher_is_better']:.3f} |
| One-shot | {one['exact_accuracy']:.3f} | {one['qualified_accuracy_exact_or_weak']:.3f} | {one['adjacent_or_exact_accuracy']:.3f} | {one['quality_higher_is_better']:.3f} |
| Label-shuffle null | {null['exact_accuracy']:.3f} | {null['qualified_accuracy_exact_or_weak']:.3f} | {null['adjacent_or_exact_accuracy']:.3f} | {null['quality_higher_is_better']:.3f} |

The sequential method exceeds the shuffled-label control, but the weak one-shot result limits evidence of out-of-sample stability.

## Conditional forecast

The timing-weighted 3 June–29 November 2026 focus selects **{labels[wband]}** in the weighted experiment and **{labels[oband]}** in the one-shot refit. These are relative class scores, not calibrated probabilities.

{historical_section}

## Limitation

Astronomical associations in this experiment it's not enough to establish causation.
"""
    path = project / "06_report/V20_TIME_CONNECTION_REPORT.md"
    path.write_text(text, encoding="utf-8")
    return path


def main() -> None:
    global REPORT_ISSUE_TEXT
    args = parser().parse_args()
    project = args.project_dir.resolve()
    config_path = args.config or project / "00_config/pipeline_request.json"
    config = read_json(config_path)
    issued_at = resolve_issue_datetime(config, args.issued_at)
    REPORT_ISSUE_TEXT = issued_at.strftime(config["report"]["issue_datetime_format"])
    summary = read_json(project / "05_ensemble/time_band_summary.json")
    manifest = read_json(project / "02_audit/event_time_master_manifest.json")
    dpi = int(config["report"]["dpi"])
    setup_plot_style()
    figures = {
        "catalog": catalog_figure(project, config, summary, dpi),
        "search": search_figure(project, dpi),
        "weighted_validation": validation_figure(
            project, config, "nested_sequential_weighted",
            "V20 sequential weighted validation — nine untouched chronological events",
            "v20_weighted_validation.png", dpi,
        ),
        "one_shot_validation": validation_figure(
            project, config, "one_shot_pre_holdout",
            "V20 one-shot validation — one pre-frontier fit across all nine events",
            "v20_one_shot_validation.png", dpi,
        ),
        "comparison": comparison_figure(project, summary, dpi),
        "forecast": forecast_figure(project, config, summary, dpi),
        "historical_forecast": (
            historical_forecast_figure(project, config, summary, dpi)
            if config["report"].get("historical_forecast_comparison", {}).get("enabled", False)
            else None
        ),
        "features": feature_figure(project, dpi),
        "runtime": runtime_figure(project, dpi),
    }
    markdown = write_markdown(project, config, summary, issued_at)
    output = project / "06_report/V20_TIME_CONNECTION_REPORT.pdf"
    labels = config["time_target"]["band_labels"]
    weighted = summary["validation"]["nested_sequential_weighted"]
    one = summary["validation"]["one_shot_pre_holdout"]
    null = summary["validation"]["target_label_permutation_null"]
    selected_band = int(summary["forecast"]["weighted_focus"]["predicted_band"])
    page = 1
    with PdfPages(output) as pdf:
        fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
        fig.text(0.065, 0.78, "V20", fontsize=70, fontweight="bold", color=BLUE)
        fig.text(0.065, 0.64, "TIME CONNECTION FINDER", fontsize=32, fontweight="bold", color=NAVY)
        fig.text(0.065, 0.54, "Same-day astronomical feature experiment for six-hour JST bands", fontsize=17, color=GREY)
        fig.add_artist(plt.Line2D([0.065, 0.92], [0.49, 0.49], color="#aac2d8", linewidth=2))
        fig.text(0.065, 0.39, "Japan-region M≥7.9 · 24 trusted timestamps · 9 chronological holdouts", fontsize=14, color=NAVY)
        fig.text(0.065, 0.31, "EXPERIMENTAL — NOT AN EARTHQUAKE OCCURRENCE FORECAST", fontsize=13, color=RED, fontweight="bold")
        fig.text(0.065, 0.18, "Astronomical associations in this experiment it's not enough to establish causation.", fontsize=11, color=GREY)
        fig.text(0.065, 0.125, f"REPORT ISSUED · {REPORT_ISSUE_TEXT}", fontsize=11, color=NAVY, fontweight="bold")
        fig.text(0.92, 0.06, "1", ha="right", color=GREY)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
        page += 1

        text_page(pdf, "Executive finding", page, [
            ("Primary validation", f"The nested sequential weighted ensemble recovers {weighted['exact_accuracy']:.1%} of nine exact six-hour bands and {weighted['adjacent_or_exact_accuracy']:.1%} within one circularly adjacent band. Its quality is {weighted['quality_higher_is_better']:.3f}, versus {null['quality_higher_is_better']:.3f} for the target-label permutation control."),
            ("Independent stability check", f"The one-shot fit recovers only {one['exact_accuracy']:.1%} exactly and has quality {one['quality_higher_is_better']:.3f}. This is weak evidence of generalization and materially limits confidence in the primary result."),
            ("Conditional future band", f"For the timing-weighted 3 June–29 November 2026 focus, both refits rank {labels[selected_band]} first. The result is conditional on an event occurring and is not a calibrated probability."),
        ], accent=RED)
        page += 1
        image_page(pdf, "Trusted event timestamps and six-hour targets", page, figures["catalog"]); page += 1

        events = pd.read_csv(project / "01_inputs/event_time_master.csv")
        events = events[events["sample_kind"].eq("event")].copy()
        events["local"] = events["sample_time_local"].astype(str).str.slice(0, 19)
        events["M"] = events["mag"].map(lambda value: f"{value:.2f}")
        page = table_page(
            pdf, "Trusted same-day event catalogue", page, events,
            ["local", "M", "target_band_label", "event_id", "place"],
            ["local event time", "M", "six-hour target", "event id", "place"],
            "All records are USGS_FDSN rows inside the configured Japan seismic domain. The feature epoch is the centre of the event's observed local band, not the start of a 90-day interval.",
            rows_per_page=12,
        )

        text_page(pdf, "Leakage and sampling contract", page, [
            ("Same-day astronomy", "Training features are NASA/JPL Horizons vectors at the centre of the observed event's six-hour JST band. Forecast features are sampled every day at 03:00, 09:00, 15:00 and 21:00 JST."),
            ("What 90 days means here", "The 90-day dates are output grouping windows inherited from V19 timing. They are not the astronomical sampling interval and they never replace the event-day ephemeris."),
            ("Excluded inputs", "Hour, minute, second, target-band and candidate-band identifiers are forbidden model features. Historical conventional-midnight records and all worldwide non-Japan hard-negative records are absent."),
            ("Remaining circularity", "The astronomical epoch is necessarily selected from the event timestamp whose band is the target. This makes the study an association/compatibility experiment rather than an independent causal timing test."),
        ], accent=ORANGE)
        page += 1
        image_page(pdf, "Nested feature and model search", page, figures["search"]); page += 1
        image_page(pdf, "Selected feature evidence", page, figures["features"]); page += 1

        systems = pd.DataFrame(summary["selected_systems"])
        systems["members"] = systems["members"].map(lambda value: " + ".join(value))
        for column in ("inner_quality", "validation_weight", "forecast_weight", "outer_quality"):
            systems[column] = systems[column].map(lambda value: f"{value:.3f}")
        page = table_page(
            pdf, "Selected hybrid composition", page, systems,
            ["system", "members", "inner_quality", "validation_weight", "forecast_weight", "outer_quality"],
            ["system", "members", "inner quality", "validation weight", "forecast weight", "outer quality"],
            "Validation weights are chosen before the outer frontier. Forecast weights may use completed outer-validation reliability; the randomized-label null receives zero forecast weight.",
            rows_per_page=12,
        )
        image_page(pdf, "Sequential weighted outer validation", page, figures["weighted_validation"]); page += 1
        image_page(pdf, "One-shot outer validation", page, figures["one_shot_validation"]); page += 1
        image_page(pdf, "Conditional time-band forecast", page, figures["forecast"]); page += 1
        if figures["historical_forecast"] is not None:
            image_page(
                pdf,
                f"Previous {config['report']['historical_forecast_comparison']['source_pipeline_label']} seven-day forecast with V20 time-band overlay",
                page,
                figures["historical_forecast"],
            )
            page += 1
        image_page(pdf, "Validation and null-control comparison", page, figures["comparison"]); page += 1

        validation = pd.read_csv(project / "05_ensemble/time_band_validation.csv")
        compact = validation.copy()
        compact["event"] = compact["event_time_local"].astype(str).str.slice(0, 10)
        compact["true"] = compact["actual_band_label"]
        compact["predicted"] = compact["predicted_band_label"]
        compact["score"] = compact["true_band_score"].map(lambda value: f"{value:.3f}")
        compact["quality"] = compact["row_quality"].map(lambda value: f"{value:.3f}")
        page = table_page(
            pdf, "Point-by-point validation trace", page, compact,
            ["method", "event", "mag", "true", "predicted", "score", "quality"],
            ["method", "event", "M", "actual band", "predicted band", "true score", "row quality"],
            "The shuffled-label rows are a scientific null control only. No null-control score enters the forecast.",
            rows_per_page=15,
        )
        forecast = pd.read_csv(project / "05_ensemble/time_band_weighted_forecast.csv")
        display = forecast[["forecast_slot_start", "forecast_slot_end", "predicted_band_label"] + [f"band_{band}_score_not_probability" for band in range(4)]].copy()
        for column in [f"band_{band}_score_not_probability" for band in range(4)]:
            display[column] = display[column].map(lambda value: f"{value:.3f}")
        page = table_page(
            pdf, "Weighted forecast trace", page, display,
            list(display.columns),
            ["slot start", "slot end", "top band", "00–06", "06–12", "12–18", "18–24"],
            "Each row summarizes four same-day candidate epochs for every day in that output slot. Scores are normalized compatibility shares, not event probabilities.",
            rows_per_page=12,
        )
        image_page(pdf, "Runtime and equal-cap audit", page, figures["runtime"]); page += 1

        text_page(pdf, "Interpretation and limitations", page, [
            ("What is supported", f"The sequential weighted method exceeds the label-shuffle control and both future refits rank {labels[selected_band]} first for the June–November 2026 focus."),
            ("What is not supported", "The one-shot validation is weak, the sample contains only 24 events, and the target timestamp also defines the astronomical sampling epoch. The study does not establish stable out-of-sample hour prediction."),
            ("Operational prohibition", "Do not use these scores for warnings, evacuation, safety, financial or emergency decisions. They neither predict earthquake occurrence nor provide a calibrated conditional probability."),
            ("Causation statement", "Astronomical associations in this experiment it's not enough to establish causation."),
        ], accent=RED)
        page += 1

        text_page(pdf, "Reproducibility", page, [
            ("Configuration", str(config_path)),
            ("Event-time master", str(project / "01_inputs/event_time_master.csv")),
            ("Master checksum", manifest["output_sha256"]),
            ("Model summary", str(project / "05_ensemble/time_band_summary.json")),
            ("Source programs", "prepare_v20_time_master.py, run_v20_time_connection.py, render_v20_time_report.py and self_check_v20.py are parameter-driven reusable sources under research_pipeline/scientific."),
        ])
        page += 1

    result = {
        "status": "COMPLETE",
        "pdf": str(output),
        "markdown": str(markdown),
        "pages": page - 1,
        "issued_at_iso8601": issued_at.isoformat(),
        "issued_at_display": REPORT_ISSUE_TEXT,
        "issue_timezone": config["report"]["issue_timezone"],
        "figures": {key: (str(value) if value is not None else None) for key, value in figures.items()},
        "historical_forecast_comparison": config["report"].get("historical_forecast_comparison", {}),
    }
    (project / "06_report/v20_report_manifest.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
