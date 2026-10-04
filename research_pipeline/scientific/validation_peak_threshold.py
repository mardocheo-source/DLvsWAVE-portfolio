#!/usr/bin/env python3
"""Derive a timing-peak threshold from held-out real bins and project it forward."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, f1_score


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--validation-csv", type=Path, required=True)
    value.add_argument("--forecast-csv", type=Path, required=True)
    value.add_argument("--output-dir", type=Path, required=True)
    value.add_argument("--score-column", default="contextual_promoted_score_not_probability")
    value.add_argument("--interval-days", type=int, required=True)
    value.add_argument("--weak-peak-minimum-retention", type=float, default=0.72)
    value.add_argument("--minimum-event-recall", type=float, default=1.0)
    value.add_argument("--dpi", type=int, default=600)
    value.add_argument("--figure-tag", default="v19")
    return value


def threshold_candidates(scores: np.ndarray) -> np.ndarray:
    unique = np.unique(np.asarray(scores, float))
    if len(unique) == 1:
        return unique
    middle = (unique[:-1] + unique[1:]) / 2.0
    return np.unique(np.concatenate(([unique[0] - 1e-9], middle, [unique[-1]])))


def main() -> None:
    args = parser().parse_args()
    validation = pd.read_csv(args.validation_csv)
    forecast = pd.read_csv(args.forecast_csv)
    score_column = args.score_column
    if score_column not in validation or score_column not in forecast:
        raise ValueError(f"Missing score column: {score_column}")
    actual = validation["actual"].fillna(0).astype(int).to_numpy()
    scores = validation[score_column].to_numpy(float)
    if actual.sum() < 2:
        raise RuntimeError("At least two real validation peaks are required")
    hard_negative = validation.get(
        "hard_negative_control", pd.Series(0, index=validation.index)
    ).fillna(0).astype(int).to_numpy()
    rows = []
    for threshold in threshold_candidates(scores):
        predicted = scores >= threshold
        recall = float(np.mean(predicted[actual == 1]))
        specificity = float(np.mean(~predicted[actual == 0]))
        balanced = float(balanced_accuracy_score(actual, predicted))
        f1 = float(f1_score(actual, predicted, zero_division=0))
        hard_rejection = (
            float(np.mean(~predicted[hard_negative == 1]))
            if np.any(hard_negative == 1)
            else specificity
        )
        false_positive_rate = 1.0 - specificity
        event_margin = float(
            np.min(scores[actual == 1])
            - np.max(scores[actual == 0])
        )
        objective = (
            0.40 * balanced
            + 0.25 * f1
            + 0.20 * hard_rejection
            + 0.15 * specificity
        )
        rows.append(
            {
                "threshold": float(threshold),
                "event_recall": recall,
                "specificity_flat_background": specificity,
                "balanced_accuracy": balanced,
                "f1": f1,
                "hard_negative_rejection": hard_rejection,
                "false_positive_rate": false_positive_rate,
                "minimum_event_minus_maximum_background_margin": event_margin,
                "objective_higher_is_better": objective,
                "passes_minimum_event_recall": bool(
                    recall >= args.minimum_event_recall
                ),
            }
        )
    trials = pd.DataFrame(rows)
    eligible = trials.loc[trials["passes_minimum_event_recall"]].copy()
    if eligible.empty:
        raise RuntimeError("No threshold preserves the configured event recall")
    selected = eligible.sort_values(
        [
            "objective_higher_is_better",
            "specificity_flat_background",
            "threshold",
        ],
        ascending=[False, False, False],
    ).iloc[0]
    threshold = float(selected["threshold"])
    forecast_scores = forecast[score_column].to_numpy(float)
    discrete = (forecast_scores >= threshold).astype(int)
    output = forecast.copy()
    output["validation_derived_threshold"] = threshold
    output["discrete_peak"] = discrete
    output["threshold_margin"] = forecast_scores - threshold

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trials.to_csv(args.output_dir / "validation_peak_threshold_trials.csv", index=False)
    output.to_csv(args.output_dir / "discretized_forecast.csv", index=False)

    x = np.arange(len(output), dtype=float) + 0.5
    boundaries = np.arange(len(output) + 1, dtype=float)
    labels = [
        f"[{row.date},\n{row.slot_end_inclusive}]"
        for row in output.itertuples(index=False)
    ]
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(16.2, 8.8),
        sharex=True,
        gridspec_kw={"height_ratios": [1.35, 1.0]},
    )
    axes[0].plot(
        x,
        forecast_scores,
        color="#4c51bf",
        marker="o",
        linewidth=2.5,
        label="analog promoted timing score",
    )
    axes[0].axhline(
        threshold,
        color="#c05621",
        linestyle="--",
        linewidth=1.7,
        label=f"validation-derived threshold {threshold:.3f}",
    )
    for index, value in enumerate(forecast_scores):
        if discrete[index]:
            axes[0].scatter(x[index], value, s=90, color="#ed8936", zorder=4)
    axes[0].set_ylabel("relative score\n(not a probability)")
    axes[0].set_title(
        "Analog forecast and validation-derived decision threshold",
        weight="bold",
    )
    axes[0].legend(frameon=False, loc="best")
    axes[0].grid(axis="y", alpha=0.24)

    colors = np.where(discrete == 1, "#ed8936", "#cbd5e1")
    bars = axes[1].bar(x, discrete, width=0.72, color=colors, edgecolor="white")
    axes[1].bar_label(
        bars,
        labels=["PEAK" if value else "flat" for value in discrete],
        padding=3,
        fontsize=8,
        weight="bold",
    )
    axes[1].set_ylim(0, 1.22)
    axes[1].set_yticks([0, 1], ["flat", "peak"])
    axes[1].set_ylabel("thresholded state")
    axes[1].set_title(
        "Discretized projection — the same threshold is applied without forecast retuning",
        weight="bold",
    )
    for axis in axes:
        axis.set_xlim(0, len(output))
        axis.set_xticks(boundaries)
        axis.set_xticklabels([""] * len(boundaries))
        axis.grid(axis="x", which="major", color="#94a3b8", alpha=0.34)
    axes[1].set_xticks(x, minor=True)
    axes[1].set_xticklabels(labels, minor=True, rotation=25, ha="right", fontsize=8)
    axes[1].tick_params(axis="x", which="minor", length=0)
    axes[1].set_xlabel(
        "vertical lines are exact slot boundaries; bars and labels are centred"
    )
    fig.suptitle(
        f"{args.figure_tag.upper()} timing forecast — analog and validation-threshold views",
        fontsize=14,
        weight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    figure = args.output_dir / f"{args.figure_tag}_timing_forecast_discretized.png"
    fig.savefig(figure, dpi=args.dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    event_rows = validation.loc[validation["actual"].eq(1)].copy()
    event_rows["score"] = event_rows[score_column]
    event_rows["above_threshold"] = event_rows["score"].ge(threshold)
    summary = {
        "schema": "validation_peak_threshold.v1",
        "status": "COMPLETE",
        "score_semantics": "relative experimental score; not a calibrated probability",
        "selection_uses_validation_only": True,
        "forecast_was_not_used_for_threshold_selection": True,
        "selected_threshold": threshold,
        "selected_metrics": selected.to_dict(),
        "validation_event_count": int(actual.sum()),
        "validation_event_rows": event_rows[
            ["step", "date", "slot_end_inclusive", "event_mag", "event_id", "score", "above_threshold"]
        ].to_dict("records"),
        "weak_peak_operator": {
            "enabled": True,
            "minimum_retention": args.weak_peak_minimum_retention,
            "rule": (
                "an event bin can remain a real weak peak when it clears the "
                "validation-derived threshold even if smoothing prevents strict-local-maximum status"
            ),
        },
        "forecast_peak_bins": int(discrete.sum()),
        "forecast_rows": int(len(output)),
        "figure": str(figure.resolve()),
        "forecast_csv": str((args.output_dir / "discretized_forecast.csv").resolve()),
        "trial_csv": str((args.output_dir / "validation_peak_threshold_trials.csv").resolve()),
    }
    (args.output_dir / "validation_peak_threshold.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str), flush=True)


if __name__ == "__main__":
    main()
