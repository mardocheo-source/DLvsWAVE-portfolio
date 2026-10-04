from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.uncompressed_pipeline.fusion import compute_asymmetric_compound_forecast
from src.uncompressed_pipeline.metrics import evaluate_needle_predictions
from src.uncompressed_pipeline.l1_engine import temporal_shift_probability


class DualModeMultilevelContractTests(unittest.TestCase):
    def validation_frame(self) -> pd.DataFrame:
        rows = []
        for event_number, event_date in ((1, pd.Timestamp("2003-09-22")), (2, pd.Timestamp("2011-03-07"))):
            for relative_week in range(-13, 14):
                rows.append({
                    "date": event_date + pd.Timedelta(weeks=relative_week),
                    "event_number": event_number,
                    "relative_week": relative_week,
                    "japan_m77_event": int(relative_week == 0),
                })
        return pd.DataFrame(rows)

    def test_centered_peak_and_strict_calm_metrics(self) -> None:
        validation = self.validation_frame()
        probability = np.full(54, 0.001)
        probability[validation.index[validation["japan_m77_event"].eq(1)]] = 0.95
        metrics = evaluate_needle_predictions(
            validation["japan_m77_event"].to_numpy(), probability, validation,
            np.array([0, 0, 1, 0, 1]), np.array([0.01, 0.02, 0.9, 0.01, 0.9]), 0.1,
        )
        self.assertEqual(metrics.val_centered_peak_count, 2)
        self.assertEqual(metrics.val_peak_hit_rate, 1.0)
        self.assertEqual(metrics.val_quiescence_sparsity, 1.0)
        self.assertLess(metrics.val_calm_mean_prob, 0.05)

    def test_fusion_refuses_missing_candidate_predictions(self) -> None:
        validation = self.validation_frame()
        master = pd.DataFrame({
            "date": pd.date_range("1900-01-01", "2030-12-30", freq="7D"),
        })
        master["japan_m77_event"] = 0
        candidates = pd.DataFrame([{
            "trial_id": 1, "network_type": "kan", "composite_needle_loss": 1.0, "train_loss": 1.0,
            "val_peak_hit_rate": 0.0, "val_peak_timing_error_weeks": 1.0,
            "val_peak_tokachi_prob": 0.1, "val_peak_tohoku_prob": 0.1,
            "val_event1_max_prob": 0.1, "val_event2_max_prob": 0.1,
            "val_quiescence_sparsity": 1.0, "val_calm_mean_prob": 0.01, "val_false_positives": 0,
            "validation_prediction_csv": "/does/not/exist.csv", "forecast_prediction_csv": "/does/not/exist2.csv",
        }])
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                compute_asymmetric_compound_forecast(candidates, Path(directory), master, Path(directory) / "out")

    def test_temporal_shift_never_crosses_validation_corridors(self) -> None:
        values = np.zeros(54)
        values[26] = 0.8
        values[27] = 0.9
        shifted = temporal_shift_probability(values, 1, corridor_size=27)
        self.assertEqual(shifted[27], 0.001)
        self.assertEqual(shifted[28], 0.9)
        self.assertEqual(shifted[26], 0.0)


if __name__ == "__main__":
    unittest.main()
