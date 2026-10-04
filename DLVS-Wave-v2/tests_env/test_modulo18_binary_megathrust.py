"""Focused tests for the binary Japan megathrust pipeline."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.binary_megathrust_data import (
    TARGET_COLUMN,
    BinaryDataConfig,
    build_clean_binary_master,
    build_trial_split,
)
from src.binary_megathrust_models import binary_metrics
from src.pretreatment import PI_DIGIT_TRIPLETS
from src.run_binary_megathrust_pipeline import _weights, collapse_gate_runs, event_peak_diagnostics


class BinaryMegathrustTests(unittest.TestCase):
    def test_clean_master_uses_only_compacted_fields_and_preserves_future_unknowns(self) -> None:
        dates = pd.date_range("2020-01-06", periods=40, freq="7D")
        master = pd.DataFrame(
            {
                "date": dates,
                "seis_core_magnitude": np.linspace(0, 9, len(dates)),
                "packed_astro_container_000": np.sin(np.arange(len(dates))),
                "packed_astro_container_001": np.cos(np.arange(len(dates))),
            }
        )
        japan = pd.DataFrame(
            {
                "time": ["2020-02-03T01:00:00Z", "2020-04-06T02:00:00Z", "2020-06-08T03:00:00Z"],
                "mag": [7.8, 8.0, 7.9],
                "latitude": [35.0, 40.0, 44.0],
                "longitude": [140.0, 145.0, 149.0],
                "id": ["jp1", "jp2", "jp3"],
            }
        )
        world = pd.DataFrame(
            {
                "time": ["2020-03-02T01:00:00Z", "2020-04-06T04:00:00Z"],
                "mag": [8.1, 8.2],
                "latitude": [-20.0, -30.0],
                "longitude": [-70.0, -75.0],
                "id": ["foreign", "same_week_as_japan"],
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            master.to_csv(root / "master.csv", index=False)
            japan.to_csv(root / "japan.csv", index=False)
            world.to_csv(root / "world.csv", index=False)
            clean, features, _ = build_clean_binary_master(
                root / "master.csv",
                root / "japan.csv",
                root / "world.csv",
                BinaryDataConfig(
                    cutoff_utc="2020-07-01T00:00:00Z",
                    forecast_start="2020-07-06",
                    forecast_end="2020-09-30",
                    validation_event_count=1,
                ),
            )

        self.assertEqual(features, ["packed_astro_container_000", "packed_astro_container_001"])
        self.assertNotIn("seis_core_magnitude", clean.columns)
        self.assertTrue(clean.loc[clean["date"].gt(pd.Timestamp("2020-07-01")), TARGET_COLUMN].isna().all())
        same_week = clean.loc[clean["date"].eq(pd.Timestamp("2020-04-06"))].iloc[0]
        self.assertEqual(same_week[TARGET_COLUMN], 1.0)
        self.assertEqual(same_week["is_world_hard_negative"], 0)
        foreign_week = clean.loc[clean["date"].eq(pd.Timestamp("2020-03-02"))].iloc[0]
        self.assertEqual(foreign_week[TARGET_COLUMN], 0.0)
        self.assertEqual(foreign_week["is_world_hard_negative"], 1)

        split = build_trial_split(
            clean,
            window_before=2,
            window_after=7,
            background_ratio=0.10,
            background_chunk_weeks=3,
            validation_weeks_before=3,
            validation_weeks_after=3,
            train_start_year=2020,
            validation_event_count=1,
            seed=7,
        )
        self.assertTrue(split.train["date"].max() < split.validation["date"].min())
        self.assertIn("foreign_hard_negative", set(split.train["sample_role"]))
        repeated = build_trial_split(
            clean,
            window_before=2,
            window_after=7,
            background_ratio=0.10,
            background_chunk_weeks=3,
            validation_weeks_before=3,
            validation_weeks_after=3,
            train_start_year=2020,
            validation_event_count=1,
            seed=7,
        )
        pd.testing.assert_frame_equal(
            split.training_background_chunks.reset_index(drop=True),
            repeated.training_background_chunks.reset_index(drop=True),
        )
        self.assertTrue(set(split.training_background_chunks["pi_triplet"]).issubset(set(PI_DIGIT_TRIPLETS)))
        if len(split.training_background_chunks):
            self.assertEqual(
                int(split.training_background_chunks.iloc[0]["pi_triplet"]),
                PI_DIGIT_TRIPLETS[7],
            )
        self.assertEqual(set(split.validation_corridor_index["event_number"]), {1})
        event_date = pd.Timestamp(split.validation_event_weeks[0])
        corridor = split.validation_corridor_index
        self.assertEqual(corridor["row_date"].min(), event_date - pd.Timedelta(weeks=3))
        self.assertEqual(corridor["row_date"].max(), event_date + pd.Timedelta(weeks=3))
        self.assertEqual(corridor["relative_week"].tolist(), list(range(-3, 4)))
        self.assertEqual(split.validation["date"].tolist(), corridor["row_date"].tolist())

    def test_asymmetric_objective_and_gate_run_collapse(self) -> None:
        metrics = binary_metrics(
            [1, 0, 1, 0],
            [0.90, 0.80, 0.20, 0.10],
            0.70,
        )
        expected = (
            metrics.focal_loss
            + 3.0 * (1.0 - metrics.f1)
            + 3.5 * metrics.fp_rate
            + 2.5 * metrics.fn_rate
            + 0.5 * metrics.depression_mae
        )
        self.assertAlmostEqual(metrics.objective_loss, expected)
        self.assertEqual((metrics.tp, metrics.fp, metrics.fn, metrics.tn), (1, 1, 1, 1))
        collapsed = collapse_gate_runs(pd.Series([0.1, 0.72, 0.84, 0.80, 0.2, 0.75]), 0.70)
        self.assertEqual(collapsed.tolist(), [0, 0, 1, 0, 0, 1])

    def test_ensemble_weights_favor_stronger_validation(self) -> None:
        weights = _weights(
            {
                "strong": {
                    "f1": 0.70, "precision": 0.80, "recall": 0.65, "auc": 0.75,
                    "fp": 1, "objective_loss": 1.5,
                },
                "weak": {
                    "f1": 0.20, "precision": 0.25, "recall": 0.20, "auc": 0.52,
                    "fp": 8, "objective_loss": 4.0,
                },
            }
        )
        self.assertGreater(weights["strong"], weights["weak"])
        self.assertAlmostEqual(sum(weights.values()), 1.0)

    def test_event_peak_diagnostics_measure_each_corridor_independently(self) -> None:
        first = pd.date_range("2000-01-03", periods=7, freq="7D")
        second = pd.date_range("2010-01-04", periods=7, freq="7D")
        dates = pd.Series([*first, *second])
        probabilities = np.full(14, 0.05)
        probabilities[4] = 0.9   # first event peak is +1 week
        probabilities[9] = 0.8   # second event peak is -1 week
        rows = []
        for number, (event_id, segment) in enumerate((("a", first), ("b", second)), start=1):
            for relative, date in zip(range(-3, 4), segment):
                rows.append({
                    "event_number": number,
                    "event_id": event_id,
                    "event_date": segment[3],
                    "event_magnitude": 8.0 + number / 10,
                    "row_date": date,
                    "relative_week": relative,
                })
        summary, detail = event_peak_diagnostics(dates, probabilities, pd.DataFrame(rows), 0.7)
        self.assertEqual(detail["signed_peak_error_weeks"].tolist(), [1, -1])
        self.assertEqual(summary["event_peak_mae_weeks"], 1.0)
        self.assertEqual(summary["event_peak_max_error_weeks"], 1)
        self.assertEqual(summary["event_gate_hit_plusminus_1week_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
