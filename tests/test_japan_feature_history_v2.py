from __future__ import annotations

import json
import unittest
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO / "DB/japan-m79plus-7d-aug2026-feature-history-v2"
SYSTEMS = {
    "lcs_only",
    "kan_only",
    "deep_only",
    "lcs_kan",
    "lcs_deep",
    "kan_deep",
    "lcs_kan_deep",
}


class JapanFeatureHistoryV2Tests(unittest.TestCase):
    def test_each_system_has_its_own_bounded_feature_winner(self):
        timing = json.loads(
            (PROJECT / "03_research/timing_feature_best_by_system.json").read_text()
        )
        location = json.loads(
            (PROJECT / "03_research/location_feature_best_by_system.json").read_text()
        )
        self.assertEqual(set(timing), SYSTEMS)
        self.assertEqual(set(location), SYSTEMS)
        for payload in (timing, location):
            for winner in payload.values():
                self.assertGreaterEqual(winner["feature_count"], 5)
                self.assertLessEqual(winner["feature_count"], 24)
                self.assertEqual(winner["feature_count"], len(winner["features"]))

    def test_timing_validation_is_exactly_two_isolated_windows(self):
        validation = pd.read_csv(
            PROJECT / "07_ensemble/timing/validation_predictions.csv"
        )
        self.assertEqual(len(validation), 26)
        self.assertEqual(int(validation["actual"].sum()), 2)
        self.assertEqual(validation.groupby("segment_id").size().tolist(), [13, 13])
        self.assertEqual(
            validation.loc[validation["actual"].eq(1), "date"].tolist(),
            ["2003-09-20", "2011-03-05"],
        )

    def test_location_validation_has_only_five_threshold_bands(self):
        for system in SYSTEMS:
            validation = pd.read_csv(
                PROJECT / f"06_location_models/{system}/validation_predictions.csv"
            )
            self.assertEqual(len(validation), 5)
            self.assertTrue(
                (
                    (validation["predicted_latitude_low"] <= validation["predicted_latitude"])
                    & (
                        validation["predicted_latitude"]
                        <= validation["predicted_latitude_high"]
                    )
                    & (
                        validation["predicted_longitude_low"]
                        <= validation["predicted_longitude"]
                    )
                    & (
                        validation["predicted_longitude"]
                        <= validation["predicted_longitude_high"]
                    )
                ).all()
            )

    def test_final_stack_keeps_best_one_hot_candidate(self):
        summary = json.loads(
            (PROJECT / "07_ensemble/timing/summary.json").read_text()
        )
        best_system = max(
            item["decision_objective_25train_75validation"]
            for item in summary["systems"].values()
        )
        self.assertGreaterEqual(
            summary["decision_objective_25train_75validation"], best_system
        )
        self.assertTrue(
            summary["stack_search"]["guarantees_best_one_hot_is_a_candidate"]
        )

    def test_tied_august_scores_are_not_called_unique(self):
        summary = json.loads(
            (PROJECT / "07_ensemble/timing/summary.json").read_text()
        )
        forecast = pd.read_csv(
            PROJECT / "07_ensemble/timing/forecast_predictions.csv"
        )
        if forecast["score"].nunique() == 1:
            self.assertFalse(summary["forecast_selection"]["unique_maximum"])
            self.assertEqual(summary["forecast_selection"]["tied_slot_count"], 5)


if __name__ == "__main__":
    unittest.main()
