#!/usr/bin/env python3
"""Audit location reliability and create a tempered timing-location forecast."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--run-dir", type=Path, required=True)
    value.add_argument(
        "--single-class-holdout-reliability-cap", type=float, default=0.40
    )
    value.add_argument(
        "--negative-control-reliability-cap",
        type=float,
        default=0.25,
        help=(
            "Maximum conditional-location weight when randomized-label "
            "validation quality is not below the primary model."
        ),
    )
    value.add_argument(
        "--small-sample-validation-threshold",
        type=int,
        default=4,
        help="Apply the small-sample cap below this validation-event count.",
    )
    value.add_argument(
        "--small-sample-reliability-cap",
        type=float,
        default=0.15,
    )
    value.add_argument(
        "--timing-forecast-csv",
        default=(
            "05_ensemble/timing/metric_specialist_fusion/"
            "metric_specialist_fusion_forecast.csv"
        ),
        help="Project-relative or absolute timing forecast selected for the joint output.",
    )
    value.add_argument(
        "--timing-score-column",
        default="metric_specialist_score_not_probability",
    )
    return value


def main() -> None:
    args = parser().parse_args()
    run = args.run_dir.expanduser().resolve()
    location_summary = json.loads(
        (run / "05_ensemble/location_zone_summary.json").read_text()
    )
    random_summary = json.loads(
        (run / "07_randomized_control/location/summary.json").read_text()
    )
    validation = pd.read_csv(run / "05_ensemble/location_zone_validation.csv")
    random_validation = pd.read_csv(
        run / "07_randomized_control/location/validation.csv"
    )
    events = pd.read_csv(run / "05_ensemble/location_zone_event_catalog.csv")
    location_forecast = pd.read_csv(
        run / "05_ensemble/location_zone_forecast.csv"
    )
    timing_path = Path(args.timing_forecast_csv).expanduser()
    if not timing_path.is_absolute():
        timing_path = run / timing_path
    timing_path = timing_path.resolve()
    timing_forecast = pd.read_csv(timing_path)
    if args.timing_score_column not in timing_forecast:
        raise KeyError(
            f"Timing score column {args.timing_score_column!r} is absent from "
            f"{timing_path}"
        )

    training_count = int(location_summary["training_events"])
    zone_count = int(location_summary["zone_count"])
    train_labels = events.iloc[:training_count]["zone"].to_numpy(int)
    priors = np.bincount(train_labels - 1, minlength=zone_count).astype(float)
    priors /= priors.sum()
    actual = validation["actual_zone"].to_numpy(int)
    majority_zone = int(np.argmax(priors) + 1)
    majority_exact = float(np.mean(actual == majority_zone))
    primary_true_confidence = float(
        np.mean(
            [
                validation.loc[index, f"zone_{zone}_vote"]
                for index, zone in enumerate(actual)
            ]
        )
    )
    randomized_true_confidence = float(
        random_validation["predicted_zone_confidence"].where(
            random_validation["predicted_zone"].to_numpy(int) == actual,
            0.0,
        ).mean()
    )
    majority_true_confidence = float(np.mean(priors[actual - 1]))

    def normalized_lift(candidate: float, baseline: float) -> float:
        return float(
            np.clip((candidate - baseline) / max(1.0 - baseline, 1e-12), 0, 1)
        )

    lift_majority = normalized_lift(
        primary_true_confidence, majority_true_confidence
    )
    lift_randomized = normalized_lift(
        primary_true_confidence, randomized_true_confidence
    )
    distinct_holdout_zones = int(validation["actual_zone"].nunique())
    raw_reliability = float(np.mean([lift_majority, lift_randomized]))
    primary_quality = float(
        location_summary["validation_metrics"]["quality_higher_is_better"]
    )
    randomized_quality = float(
        random_summary["validation_metrics"]["quality_higher_is_better"]
    )
    negative_control_not_below_primary = randomized_quality >= primary_quality
    if distinct_holdout_zones < 2:
        reliability_cap = args.single_class_holdout_reliability_cap
        limitation_reason = (
            f"all {len(validation)} chronological validation events occupy "
            f"Zone {int(actual[0])}, so exact accuracy cannot measure "
            "multi-zone discrimination"
        )
    elif negative_control_not_below_primary:
        reliability_cap = args.negative_control_reliability_cap
        limitation_reason = (
            "randomized-label validation quality is not below the primary "
            f"location model ({randomized_quality:.3f} versus "
            f"{primary_quality:.3f}); conditional location influence remains "
            "capped despite the multi-zone holdout"
        )
    else:
        reliability_cap = 1.0
        limitation_reason = None
    if len(validation) < args.small_sample_validation_threshold:
        reliability_cap = min(reliability_cap, args.small_sample_reliability_cap)
        sample_reason = (
            f"only {len(validation)} chronological location events are held out; "
            f"below the configured small-sample threshold of "
            f"{args.small_sample_validation_threshold}"
        )
        limitation_reason = (
            sample_reason
            if limitation_reason is None
            else limitation_reason + "; " + sample_reason
        )
    reliability_weight = float(min(raw_reliability, reliability_cap))

    joined = timing_forecast.merge(
        location_forecast,
        on=["date", "slot_end_inclusive"],
        how="inner",
        validate="one_to_one",
    )
    if len(joined) != len(timing_forecast):
        raise RuntimeError("Timing and location forecast grids do not match")
    joined["conditional_location_reliability_weight"] = reliability_weight
    joined["location_validation_scope"] = (
        "limited_single_zone_chronological_holdout"
        if distinct_holdout_zones < 2
        else "multi_zone_chronological_holdout"
    )
    score = joined[args.timing_score_column].to_numpy(float)
    joined["primary_timing_score_not_probability"] = score
    # Compatibility alias for report consumers written before selectable
    # primary timing sources were introduced.
    joined["metric_specialist_score_not_probability"] = score
    for zone in range(1, zone_count + 1):
        model_vote = joined[f"zone_{zone}_vote"].to_numpy(float)
        tempered = reliability_weight * model_vote + (
            1.0 - reliability_weight
        ) * priors[zone - 1]
        joined[f"tempered_zone_{zone}_share"] = tempered
        joined[f"joint_zone_{zone}_experimental_score"] = score * tempered
    joint_columns = [
        f"joint_zone_{zone}_experimental_score"
        for zone in range(1, zone_count + 1)
    ]
    joined["joint_score_sum_check"] = joined[joint_columns].sum(axis=1)
    output = run / "05_ensemble/timing_location_joint_forecast.csv"
    joined.to_csv(output, index=False)

    assessment = {
        "status": "LIMITED"
        if limitation_reason is not None
        else "QUALIFIED_EXPERIMENTAL",
        "conditional_semantics": (
            "zone shares are conditional on an event occurring in the configured "
            "timing bin; they do not change the timing score"
        ),
        "validation_events": len(validation),
        "distinct_validation_zones": distinct_holdout_zones,
        "majority_zone": majority_zone,
        "training_zone_priors": {
            str(zone): float(priors[zone - 1])
            for zone in range(1, zone_count + 1)
        },
        "exact_zone_accuracy": float(
            location_summary["validation_metrics"]["exact_zone_accuracy"]
        ),
        "majority_exact_zone_accuracy": majority_exact,
        "randomized_exact_zone_accuracy": float(
            random_summary["validation_metrics"]["exact_zone_accuracy"]
        ),
        "validation_quality": {
            "primary": primary_quality,
            "randomized_label_control": randomized_quality,
            "randomized_control_below_primary": bool(
                randomized_quality < primary_quality
            ),
        },
        "true_zone_confidence": {
            "primary_soft_fusion": primary_true_confidence,
            "training_prior_baseline": majority_true_confidence,
            "randomized_label_control": randomized_true_confidence,
        },
        "normalized_confidence_lift": {
            "over_training_prior": lift_majority,
            "over_randomized_labels": lift_randomized,
        },
        "raw_reliability": raw_reliability,
        "reliability_cap": reliability_cap,
        "applied_reliability_weight": reliability_weight,
        "reason_for_cap": limitation_reason,
        "soft_fusion_guard": location_summary["fusion_gate"].get(
            "validation_zone_diversity_guard"
        ),
        "selected_location_fusion": location_summary["fusion_gate"]["selected"],
        "joint_forecast": {
            "path": str(output),
            "timing_source": {
                "path": str(timing_path),
                "score_column": args.timing_score_column,
            },
            "rows": len(joined),
            "formula": (
                "joint_zone_score = timing_score * "
                "(w * model_zone_vote + (1-w) * training_zone_prior)"
            ),
            "score_is_probability": False,
            "sum_check_max_absolute_error": float(
                np.max(
                    np.abs(
                        joined["joint_score_sum_check"].to_numpy(float) - score
                    )
                )
            ),
        },
    }
    write_json(run / "05_ensemble/location_reliability_assessment.json", assessment)
    print(json.dumps(assessment, indent=2))


if __name__ == "__main__":
    main()
