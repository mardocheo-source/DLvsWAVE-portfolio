#!/usr/bin/env python3
"""Generate version-tagged runtime and indirect-location diagnostics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


COLORS = {
    "lcs": "#4e79a7",
    "kan": "#f28e2b",
    "deep_tiny": "#59a14f",
    "deep_wide": "#76b7b2",
    "deep_regularized": "#b07aa1",
    "logistic": "#e15759",
    "extra_trees": "#edc949",
}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--project-dir", type=Path, required=True)
    value.add_argument("--interval-days", type=int, required=True)
    value.add_argument("--dpi", type=int, default=600)
    value.add_argument(
        "--figure-tag",
        default="v17",
        help="Lower-case version tag used in diagnostic artifact filenames.",
    )
    value.add_argument(
        "--final-time-budget-seconds",
        type=float,
        default=0.0,
        help="Common hard time cap used by the final-attempt comparison.",
    )
    return value


def finish(fig, path: Path, dpi: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def runtime_figure(project: Path, dpi: int, figure_tag: str) -> dict:
    trials = pd.read_csv(
        project / "03_feature_research/model_parameter_screen_trials.csv"
    )
    selected = json.loads(
        (project / "03_feature_research/selected_model_overrides.json").read_text()
    )["selected_candidates"]
    selected = pd.DataFrame(selected)
    order = selected.sort_values("runtime_seconds_mean")["family"].tolist()
    selected = selected.set_index("family").loc[order].reset_index()
    x = np.arange(len(selected))
    colors = [COLORS.get(value, "#4e79a7") for value in selected["family"]]
    labels = [value.replace("_", "\n") for value in selected["family"]]
    fig, axes = plt.subplots(1, 2, figsize=(15.8, 6.4))
    bars = axes[0].bar(
        x,
        selected["runtime_seconds_mean"],
        color=colors,
        edgecolor="white",
        width=0.72,
    )
    axes[0].bar_label(bars, fmt="%.2fs", padding=3, fontsize=8)
    axes[0].set_yscale("log")
    axes[0].set_xticks(x, labels, fontsize=8)
    axes[0].set_ylabel("mean fit + inference wall time per validation fold (seconds, log scale)")
    axes[0].set_title("Measured speed of each promoted family", weight="bold")
    axes[0].grid(axis="y", alpha=0.24)

    height = 0.36
    axes[1].barh(
        x - height / 2,
        selected["scientific_quality"],
        height=height,
        color="#4e79a7",
        label="false-positive-aware scientific quality",
    )
    axes[1].barh(
        x + height / 2,
        selected["quality_speed_kpi"],
        height=height,
        color="#f28e2b",
        label="85% quality + 15% speed KPI",
    )
    axes[1].set_yticks(x, labels, fontsize=8)
    axes[1].set_xlim(0, 1.02)
    axes[1].set_xlabel("higher-is-better score")
    axes[1].set_title("Quality–speed compromise used within each family", weight="bold")
    axes[1].grid(axis="x", alpha=0.24)
    axes[1].legend(loc="lower right", frameon=False, fontsize=8)
    fig.suptitle(
        f"{figure_tag.upper()} fast hyperparameter screen — promoted configuration per model family\n"
        "Scientific quality explicitly includes false-peak and delayed-false-peak control",
        fontsize=14,
        weight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    output = project / f"06_report/{figure_tag}_model_runtime_quality.png"
    finish(fig, output, dpi)
    return {
        "figure": str(output.resolve()),
        "families": len(selected),
        "candidate_trials": len(trials),
        "selected": selected.to_dict("records"),
    }


def hybrid_runtime_figure(project: Path, dpi: int, figure_tag: str) -> dict:
    rows = []
    for path in sorted((project / "04_models/timing").glob("[0-9][0-9]_*/*/summary.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "fold": path.parents[1].name,
                "system": payload["system"],
                "members": " + ".join(payload["members"]),
                "quality": float(payload["origin_quality_25train_75validation"]),
                "runtime": float(payload["system_runtime_seconds_sum_members"]),
                "false_peak_control": float(
                    payload["validation_metrics"]["false_peak_control"]
                ),
                "delayed_false_peak_control": float(
                    payload["validation_metrics"]["delayed_false_peak_control"]
                ),
                "weak_peak_retention": float(
                    payload["validation_metrics"]["weak_peak_retention_skill"]
                ),
            }
        )
    if not rows:
        raise FileNotFoundError("No timing system summaries with runtime were found")
    frame = pd.DataFrame(rows)
    summary = (
        frame.groupby(["system", "members"], as_index=False)
        .agg(
            mean_quality=("quality", "mean"),
            worst_fold_quality=("quality", "min"),
            mean_runtime_seconds=("runtime", "mean"),
            folds=("fold", "nunique"),
            false_peak_control=("false_peak_control", "mean"),
            delayed_false_peak_control=("delayed_false_peak_control", "mean"),
            weak_peak_retention=("weak_peak_retention", "mean"),
        )
    )
    fastest = max(float(summary["mean_runtime_seconds"].min()), 1e-9)
    summary["speed_skill"] = np.clip(
        fastest / summary["mean_runtime_seconds"].clip(lower=fastest), 0.0, 1.0
    )
    summary["robust_scientific_quality"] = (
        0.70 * summary["mean_quality"] + 0.30 * summary["worst_fold_quality"]
    )
    summary["quality_speed_kpi"] = (
        0.85 * summary["robust_scientific_quality"] + 0.15 * summary["speed_skill"]
    )
    summary = summary.sort_values("quality_speed_kpi", ascending=False).reset_index(drop=True)
    summary.insert(0, "rank", np.arange(1, len(summary) + 1))
    output_csv = project / "03_feature_research/system_hybrid_runtime_quality.csv"
    summary.to_csv(output_csv, index=False)
    shown = summary.head(min(12, len(summary))).iloc[::-1]
    labels = ["\n".join(textwrap.wrap(value.replace("_", " "), 22)) for value in shown["system"]]
    y = np.arange(len(shown))
    fig, axes = plt.subplots(1, 2, figsize=(16.0, 7.2))
    runtime_bars = axes[0].barh(y, shown["mean_runtime_seconds"], color="#4e79a7")
    axes[0].bar_label(runtime_bars, fmt="%.1fs", padding=3, fontsize=7.4)
    axes[0].set_xscale("log")
    axes[0].set_yticks(y, labels, fontsize=7.2)
    axes[0].set_xlabel("mean member-fit runtime per fold (seconds, log scale)")
    axes[0].set_title("Base and hybrid computational cost", weight="bold")
    axes[0].grid(axis="x", alpha=0.24)
    width = 0.36
    axes[1].barh(
        y - width / 2,
        shown["robust_scientific_quality"],
        height=width,
        color="#59a14f",
        label="70% mean + 30% worst-fold quality",
    )
    axes[1].barh(
        y + width / 2,
        shown["quality_speed_kpi"],
        height=width,
        color="#f28e2b",
        label="85% robust quality + 15% speed",
    )
    axes[1].set_yticks(y, labels, fontsize=7.2)
    axes[1].set_xlim(0, 1.02)
    axes[1].set_xlabel("higher-is-better")
    axes[1].set_title("Validation–speed compromise for systems and hybrids", weight="bold")
    axes[1].grid(axis="x", alpha=0.24)
    axes[1].legend(loc="lower right", fontsize=7.5, frameon=False)
    fig.suptitle(
        f"{figure_tag.upper()} full-fold runtime audit — individual systems and hybrid combinations\n"
        "Hybrid cost is the measured sum of independently fitted members; aggregation overhead is negligible",
        fontsize=13.5,
        weight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    output = project / f"06_report/{figure_tag}_system_hybrid_runtime_quality.png"
    finish(fig, output, dpi)
    return {
        "figure": str(output.resolve()),
        "systems": len(summary),
        "folds": int(frame["fold"].nunique()),
        "ranking_csv": str(output_csv.resolve()),
        "top_system": summary.iloc[0].to_dict(),
    }


def training_start_figure(project: Path, dpi: int, figure_tag: str) -> dict | None:
    path = project / "02_master_search/compact_k_factor_trials.csv"
    if not path.is_file():
        return None
    trials = pd.read_csv(path)
    if "history_start_date" not in trials:
        return None
    selection_column = (
        "selection_objective"
        if "selection_objective" in trials
        else "fast_objective"
    )
    best = (
        trials.sort_values(
            [selection_column, "validation_quality_mean"],
            ascending=False,
        )
        .drop_duplicates("history_start_date", keep="first")
        .sort_values("history_start_date")
        .reset_index(drop=True)
    )
    membership_path = project / "02_audit/event_bin_membership.csv"
    if membership_path.is_file():
        membership = pd.read_csv(membership_path)
        event_dates = {
            str(row.slot_start): str(row.event_dates).split(";")[0]
            for row in membership.itertuples(index=False)
        }
        best["history_start_event_date"] = best["history_start_date"].map(
            event_dates
        ).fillna("not recorded")
    else:
        best["history_start_event_date"] = "not recorded"
    best.insert(0, "start_rank", np.arange(1, len(best) + 1))
    output_csv = project / "02_master_search/training_start_date_best_trials.csv"
    best.to_csv(output_csv, index=False)
    x = np.arange(len(best))
    labels = best["history_start_date"].astype(str).tolist()
    fig = plt.figure(figsize=(16.2, 9.0), facecolor="white")
    quality_axis = fig.add_axes([0.07, 0.49, 0.56, 0.36])
    size_axis = fig.add_axes([0.69, 0.49, 0.26, 0.36])
    width = 0.36
    quality_axis.bar(
        x - width / 2,
        best["validation_quality_mean"],
        width,
        color="#4e79a7",
        label="validation mean",
    )
    quality_axis.bar(
        x + width / 2,
        best["validation_quality_worst"],
        width,
        color="#f28e2b",
        label="worst validation fold",
    )
    quality_axis.set_ylim(0, 1.02)
    quality_axis.set_xticks(x, labels, rotation=28, ha="right", fontsize=8)
    quality_axis.set_ylabel("higher-is-better quality")
    quality_axis.set_title(
        "Best k-factor combination for each exact training start event",
        weight="bold",
    )
    quality_axis.grid(axis="y", alpha=0.24)
    quality_axis.legend(frameon=False, fontsize=8)
    bars = size_axis.bar(
        x,
        best["selected_historical_rows"],
        color="#59a14f",
        edgecolor="white",
    )
    size_axis.bar_label(bars, fmt="%d", padding=3, fontsize=7)
    size_axis.set_xticks(x, labels, rotation=28, ha="right", fontsize=7.5)
    size_axis.set_ylabel("selected historical rows")
    size_axis.set_title("Compact-master size", weight="bold")
    size_axis.grid(axis="y", alpha=0.24)

    table_axis = fig.add_axes([0.055, 0.06, 0.90, 0.29])
    table_axis.axis("off")
    table_frame = best[
        [
            "history_start_date",
            "history_start_event_date",
            "history_start_event_magnitude",
            "k_event",
            "k_between",
            "proximity_fraction",
            "validation_quality_mean",
            "validation_quality_worst",
            "exact_validation_peak_count",
            "selected_historical_rows",
        ]
    ].copy()
    table_frame.columns = [
        "start slot",
        "event date",
        "start M",
        "k event",
        "k between",
        "near share",
        "val mean",
        "val worst",
        "exact peaks",
        "rows",
    ]
    for column in ("start M", "near share", "val mean", "val worst"):
        table_frame[column] = table_frame[column].map(lambda value: f"{value:.3f}")
    table = table_axis.table(
        cellText=table_frame.values,
        colLabels=table_frame.columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7.2)
    table.scale(1.0, 1.35)
    for (row, column), cell in table.get_celld().items():
        cell.set_edgecolor("#cbd5e1")
        if row == 0:
            cell.set_facecolor("#1f4e79")
            cell.set_text_props(color="white", weight="bold")
        elif row % 2:
            cell.set_facecolor("#f8fafc")
    fig.suptitle(
        f"{figure_tag.upper()} exact training-start search — start event × temporal k-factors",
        fontsize=14,
        weight="bold",
    )
    output = project / f"06_report/{figure_tag}_training_start_search.png"
    finish(fig, output, dpi)
    selected = best.sort_values(selection_column, ascending=False).iloc[0]
    return {
        "figure": str(output.resolve()),
        "table_csv": str(output_csv.resolve()),
        "start_candidates": int(len(best)),
        "selected": selected.to_dict(),
    }


def final_time_budget_figure(
    project: Path,
    dpi: int,
    figure_tag: str,
    time_budget_seconds: float,
) -> dict | None:
    if time_budget_seconds <= 0:
        return None
    path = project / "03_feature_research/system_hybrid_runtime_quality.csv"
    if not path.is_file():
        return None
    systems = pd.read_csv(path)
    systems["time_budget_seconds"] = float(time_budget_seconds)
    systems["finished_within_time_limit"] = systems["mean_runtime_seconds"].le(
        time_budget_seconds
    )
    systems["time_budget_utilization"] = np.clip(
        systems["mean_runtime_seconds"] / time_budget_seconds, 0.0, 1.0
    )
    systems["quality_reached_under_equal_time_cap"] = np.where(
        systems["finished_within_time_limit"],
        0.50 * systems["robust_scientific_quality"]
        + 0.30 * systems["false_peak_control"]
        + 0.10 * systems["delayed_false_peak_control"]
        + 0.10 * systems["weak_peak_retention"],
        0.0,
    )
    systems = systems.sort_values(
        "quality_reached_under_equal_time_cap", ascending=False
    ).reset_index(drop=True)
    systems.insert(0, "equal_budget_rank", np.arange(1, len(systems) + 1))
    output_csv = project / "03_feature_research/final_attempt_equal_time_quality.csv"
    systems.to_csv(output_csv, index=False)
    shown = systems.head(min(10, len(systems))).iloc[::-1]
    y = np.arange(len(shown))
    labels = [
        "\n".join(textwrap.wrap(value.replace("_", " "), 20))
        for value in shown["system"]
    ]
    fig = plt.figure(figsize=(16.2, 9.2), facecolor="white")
    time_axis = fig.add_axes([0.08, 0.48, 0.40, 0.39])
    quality_axis = fig.add_axes([0.59, 0.48, 0.36, 0.39])
    used = shown["mean_runtime_seconds"].clip(upper=time_budget_seconds)
    unused = time_budget_seconds - used
    time_axis.barh(y, used, color="#4e79a7", label="measured fit time")
    time_axis.barh(
        y,
        unused,
        left=used,
        color="#e2e8f0",
        label="unused common budget",
    )
    time_axis.set_yticks(y, labels, fontsize=7.2)
    time_axis.set_xlabel("seconds")
    time_axis.set_title(
        f"Equal hard cap: {time_budget_seconds:g}s per final attempt",
        weight="bold",
    )
    time_axis.grid(axis="x", alpha=0.24)
    time_axis.legend(frameon=False, fontsize=7.5, loc="lower right")
    width = 0.28
    quality_axis.barh(
        y - width,
        shown["robust_scientific_quality"],
        width,
        color="#4e79a7",
        label="robust validation quality",
    )
    quality_axis.barh(
        y,
        shown["false_peak_control"],
        width,
        color="#59a14f",
        label="false-peak control",
    )
    quality_axis.barh(
        y + width,
        shown["quality_reached_under_equal_time_cap"],
        width,
        color="#f28e2b",
        label="quality reached under cap",
    )
    quality_axis.set_yticks(y, [""] * len(y))
    quality_axis.set_xlim(0, 1.02)
    quality_axis.set_xlabel("higher-is-better")
    quality_axis.set_title("Quality at the same maximum time", weight="bold")
    quality_axis.grid(axis="x", alpha=0.24)
    quality_axis.legend(frameon=False, fontsize=7.2, loc="lower right")

    table_axis = fig.add_axes([0.055, 0.055, 0.90, 0.29])
    table_axis.axis("off")
    table_frame = systems.head(min(10, len(systems)))[
        [
            "equal_budget_rank",
            "system",
            "mean_runtime_seconds",
            "robust_scientific_quality",
            "false_peak_control",
            "weak_peak_retention",
            "quality_reached_under_equal_time_cap",
        ]
    ].copy()
    table_frame.columns = [
        "rank",
        "system",
        "seconds",
        "robust quality",
        "false-peak control",
        "weak retention",
        "equal-cap quality",
    ]
    for column in table_frame.columns[2:]:
        table_frame[column] = table_frame[column].map(lambda value: f"{value:.3f}")
    table = table_axis.table(
        cellText=table_frame.values,
        colLabels=table_frame.columns,
        loc="center",
        cellLoc="center",
        colWidths=[0.06, 0.25, 0.10, 0.14, 0.15, 0.13, 0.15],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7.0)
    table.scale(1.0, 1.28)
    for (row, column), cell in table.get_celld().items():
        cell.set_edgecolor("#cbd5e1")
        if row == 0:
            cell.set_facecolor("#1f4e79")
            cell.set_text_props(color="white", weight="bold")
        elif row % 2:
            cell.set_facecolor("#f8fafc")
    fig.suptitle(
        f"{figure_tag.upper()} budgeted final attempts — runtime, real-peak quality and false-positive suppression",
        fontsize=13.5,
        weight="bold",
    )
    output = project / f"06_report/{figure_tag}_final_attempt_time_budget.png"
    finish(fig, output, dpi)
    return {
        "figure": str(output.resolve()),
        "table_csv": str(output_csv.resolve()),
        "time_budget_seconds": float(time_budget_seconds),
        "systems": int(len(systems)),
        "finished_within_limit": int(systems["finished_within_time_limit"].sum()),
        "top_system": systems.iloc[0].to_dict(),
    }


def one_shot_timing_figure(project: Path, dpi: int, figure_tag: str) -> dict | None:
    directory = project / "05_ensemble/timing/one_shot"
    validation_path = directory / "validation.csv"
    forecast_path = directory / "forecast.csv"
    summary_path = directory / "summary.json"
    if not all(path.is_file() for path in (validation_path, forecast_path, summary_path)):
        return None
    validation = pd.read_csv(validation_path)
    forecast = pd.read_csv(forecast_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    validation_score = validation["one_shot_score_not_probability"].to_numpy(float)
    forecast_score = forecast["one_shot_score_not_probability"].to_numpy(float)
    actual = validation["actual"].fillna(0).astype(int).to_numpy()
    hard = validation["hard_negative_control"].fillna(0).astype(int).to_numpy()
    fig, axes = plt.subplots(2, 1, figsize=(16.2, 8.8))
    xv = np.arange(len(validation), dtype=float) + 0.5
    axes[0].plot(
        xv,
        validation_score,
        color="#2b6cb0",
        marker="o",
        linewidth=2.1,
        label="one-shot real-label score",
    )
    axes[0].scatter(
        xv[actual == 1],
        validation_score[actual == 1],
        marker="*",
        s=130,
        color="#c53030",
        label="held-out Japan M≥7.9 event",
        zorder=4,
    )
    axes[0].scatter(
        xv[hard == 1],
        validation_score[hard == 1],
        marker="x",
        s=70,
        color="#dd6b20",
        label="selected non-Japan hard negative",
        zorder=4,
    )
    axes[0].set_title(
        "One-shot timing validation — one pre-first-holdout fit across every real event",
        weight="bold",
    )
    axes[0].set_ylabel("relative score\n(not a probability)")
    axes[0].legend(frameon=False, ncol=3, fontsize=8)
    axes[0].grid(axis="y", alpha=0.24)
    xf = np.arange(len(forecast), dtype=float) + 0.5
    axes[1].plot(
        xf,
        forecast_score,
        color="#6b46c1",
        marker="o",
        linewidth=2.4,
        label="one full-history forecast refit",
    )
    axes[1].set_title("One-shot timing forecast", weight="bold")
    axes[1].set_ylabel("relative score\n(not a probability)")
    axes[1].legend(frameon=False)
    axes[1].grid(axis="y", alpha=0.24)
    for axis, data, x in (
        (axes[0], validation, xv),
        (axes[1], forecast, xf),
    ):
        boundaries = np.arange(len(data) + 1, dtype=float)
        labels = [
            f"[{row.date},\n{row.slot_end_inclusive}]"
            for row in data.itertuples(index=False)
        ]
        axis.set_xlim(0, len(data))
        axis.set_xticks(boundaries)
        axis.set_xticklabels([""] * len(boundaries))
        axis.grid(axis="x", which="major", color="#94a3b8", alpha=0.32)
        axis.set_xticks(x, minor=True)
        axis.set_xticklabels(labels, minor=True, rotation=28, ha="right", fontsize=6.5)
        axis.tick_params(axis="x", which="minor", length=0)
    axes[1].set_xlabel(
        "vertical lines are exact slot boundaries; points and labels are centred"
    )
    fig.suptitle(
        f"{figure_tag.upper()} one-shot timing diagnostic — one validation fit and one forecast fit",
        fontsize=14,
        weight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    output = project / f"06_report/{figure_tag}_one_shot_timing.png"
    finish(fig, output, dpi)
    return {
        "figure": str(output.resolve()),
        "validation_events": int(summary["validation_events"]),
        "validation_quality": float(
            summary["validation_metrics"]["quality_higher_is_better"]
        ),
        "forecast_rows": int(summary["forecast_rows"]),
        "time_limit_seconds": float(summary["final_attempt_time_limit_seconds"]),
    }


def indirect_location_figure(
    project: Path, interval_days: int, dpi: int, figure_tag: str
) -> dict | None:
    path = project / "05_ensemble/location_zone_indirect_validation.csv"
    if not path.is_file():
        return None
    data = pd.read_csv(path)
    x = np.arange(len(data), dtype=float) + 0.5
    boundaries = np.arange(len(data) + 1, dtype=float)
    labels = []
    for row in data.itertuples():
        start = pd.Timestamp(row.slot_start)
        end = start + pd.Timedelta(days=interval_days)
        labels.append(
            f"[{start:%Y-%m-%d},\n{end:%Y-%m-%d})\nM{row.mag:.2f}"
        )
    actual = data["actual_zone"].to_numpy(int)
    predicted = data["predicted_zone"].to_numpy(int)
    fig, axis = plt.subplots(figsize=(15.8, 6.2))
    axis.plot(
        x,
        actual,
        color="#c53030",
        marker="o",
        linewidth=2.4,
        label="observed zone",
    )
    axis.plot(
        x,
        predicted,
        color="#2b6cb0",
        marker="s",
        linestyle="--",
        linewidth=2.2,
        label="primary model prediction (never tuned on these rows)",
    )
    for index, row in data.iterrows():
        status = "MATCH" if actual[index] == predicted[index] else "MISS"
        axis.annotate(
            f"{status}\n{str(row['event_id'])[:18]}",
            (x[index], predicted[index]),
            xytext=(0, 12 if index % 2 == 0 else -30),
            textcoords="offset points",
            ha="center",
            fontsize=7.2,
            color="#166534" if status == "MATCH" else "#9b2c2c",
            weight="bold",
        )
    axis.set_xticks(boundaries)
    axis.set_xticklabels([""] * len(boundaries))
    axis.set_xticks(x, minor=True)
    axis.set_xticklabels(labels, minor=True, rotation=28, ha="right", fontsize=7.5)
    axis.tick_params(axis="x", which="minor", length=0)
    axis.grid(axis="x", which="major", color="#94a3b8", alpha=0.30)
    axis.grid(axis="y", color="#94a3b8", alpha=0.24)
    axis.set_xlim(0, len(data))
    axis.set_yticks(range(1, int(max(actual.max(), predicted.max())) + 1))
    axis.set_ylabel("data-derived seismic zone")
    axis.set_xlabel("grid lines are true slot boundaries; points and labels are centred inside each interval")
    axis.set_title(
        "Indirect lower-magnitude localization audit\n"
        "Rows are evaluation-only and never influence feature, zone, model or fusion selection",
        weight="bold",
    )
    axis.legend(loc="upper center", ncol=2, frameon=False)
    fig.tight_layout()
    output = project / f"06_report/{figure_tag}_location_indirect_validation.png"
    finish(fig, output, dpi)
    return {
        "figure": str(output.resolve()),
        "events": len(data),
        "exact_matches": int(np.sum(actual == predicted)),
        "exact_accuracy": float(np.mean(actual == predicted)),
    }


def main() -> None:
    args = parser().parse_args()
    project = args.project_dir.expanduser().resolve()
    figure_tag = str(args.figure_tag).strip().lower()
    if not figure_tag or not all(
        character.isalnum() or character in {"-", "_"}
        for character in figure_tag
    ):
        raise ValueError("figure-tag must contain only letters, digits, '-' or '_'")
    runtime = runtime_figure(project, args.dpi, figure_tag)
    hybrids = hybrid_runtime_figure(project, args.dpi, figure_tag)
    training_start = training_start_figure(project, args.dpi, figure_tag)
    final_time_budget = final_time_budget_figure(
        project,
        args.dpi,
        figure_tag,
        args.final_time_budget_seconds,
    )
    one_shot = one_shot_timing_figure(project, args.dpi, figure_tag)
    indirect = indirect_location_figure(
        project, args.interval_days, args.dpi, figure_tag
    )
    payload = {
        "schema": f"{figure_tag}_diagnostics.audit.v1",
        "runtime_quality": runtime,
        "system_hybrid_runtime_quality": hybrids,
        "training_start_search": training_start,
        "final_attempt_time_budget": final_time_budget,
        "one_shot_timing": one_shot,
        "indirect_location": indirect,
        "plot_geometry_contract": (
            "Every interval time plot uses vertical major-grid lines at exact "
            "slot boundaries; observations, bars and interval labels are centred "
            "between those boundaries."
        ),
    }
    path = project / f"06_report/{figure_tag}_diagnostics.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2), flush=True)


if __name__ == "__main__":
    main()
