#!/usr/bin/env python3
"""Run the parameterized one-shot location engine with the V14 model bank.

The location engine is shared with the audited V12 implementation, while this
entry point injects the V14 common layer. Consequently the same leakage guards,
zone construction, feature ablation and fusion search are retained, but the
candidate bank also includes V14 logistic and extra-trees systems.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

import numpy as np

import common_v14


def main() -> None:
    engine = Path(__file__).with_name("run_monthly_location.py")
    if not engine.is_file():
        raise FileNotFoundError(f"Shared location engine not found: {engine}")
    # The shared engine imports this name; aliasing keeps the engine generic
    # without duplicating its scientific implementation.
    sys.modules["common_v6"] = common_v14
    scope = runpy.run_path(str(engine), run_name="_v14_shared_location_engine")
    original_select_fusion = scope["select_fusion"]

    def diversity_guarded_select_fusion(
        systems,
        ranking,
        labels,
        latitude,
        longitude,
        validation,
        zones,
        training_labels,
    ):
        validation_probability, forecast_probability, audit = (
            original_select_fusion(
                systems,
                ranking,
                labels,
                latitude,
                longitude,
                validation,
                zones,
                training_labels,
            )
        )
        holdout_zones = np.unique(np.asarray(labels)[validation])
        if len(holdout_zones) >= 2 or "hard_vote" not in audit["selected"]["fusion"]:
            audit["validation_zone_diversity_guard"] = {
                "status": "NOT_REQUIRED",
                "distinct_holdout_zones": len(holdout_zones),
            }
            return validation_probability, forecast_probability, audit

        # A single-class chronological holdout can make a hard vote look
        # perfectly confident without testing geographic discrimination. Keep
        # a genuine top-three model fusion, but preserve its soft probabilities.
        members = ranking["system"].head(3).tolist()
        validation_probability = scope["weighted_system_probability"](
            systems, ranking, "validation", members, False
        )
        forecast_probability = scope["weighted_system_probability"](
            systems, ranking, "forecast", members, False
        )
        metrics = scope["zone_metrics"](
            np.asarray(labels)[validation],
            validation_probability,
            np.asarray(latitude)[validation],
            np.asarray(longitude)[validation],
            zones,
        )
        original_selection = audit["selected"]
        audit["selected"] = {
            "fusion": "top3_soft_probability_diversity_guard",
            "members": members,
            "quality_higher_is_better": metrics["quality_higher_is_better"],
            "exact_zone_accuracy": metrics["exact_zone_accuracy"],
            "top_two_zone_accuracy": metrics["top_two_zone_accuracy"],
            "mean_centroid_distance_km": metrics[
                "mean_centroid_distance_km"
            ],
            "unique_predicted_zones": len(set(metrics["predicted_zones"])),
        }
        audit["validation_zone_diversity_guard"] = {
            "status": "SOFT_FUSION_FORCED",
            "distinct_holdout_zones": len(holdout_zones),
            "reason": (
                "all chronological holdout events occupy one zone, so a hard "
                "vote would encode unjustified certainty"
            ),
            "rejected_automatic_selection": original_selection,
        }
        return validation_probability, forecast_probability, audit

    scope["main"].__globals__["select_fusion"] = diversity_guarded_select_fusion
    scope["main"]()


if __name__ == "__main__":
    main()
