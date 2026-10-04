from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO / "DB/japan-m79plus-7d-aug2026-multimodel"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class JapanMultimodelPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.models = load_module(
            "japan_train_models", PROJECT / "pipeline/train_models.py"
        )

    def test_recent_timing_validation_isolated_windows(self) -> None:
        master = pd.read_csv(
            PROJECT / "02_timing_master/timing_master_m79_7d.csv",
            usecols=["date", "timing_target", "is_forecast"],
        )
        history = master.loc[master["is_forecast"].eq(0)].reset_index(drop=True)
        splits, segments = self.models.timing_splits(
            history["timing_target"].to_numpy(dtype=int)
        )
        event_dates = [
            history.loc[segment["event_index"], "date"]
            for segment in segments["validation"]
        ]
        self.assertEqual(event_dates, ["2003-09-20", "2011-03-05"])
        self.assertEqual(len(splits["validation"]), 26)
        self.assertEqual(int(history.loc[splits["validation"], "timing_target"].sum()), 2)
        self.assertGreaterEqual(history.loc[splits["holdout"], "date"].min(), "2011-04-23")

    def test_forecast_slots_are_exact_nonoverlapping_seven_day_bins(self) -> None:
        master = pd.read_csv(
            PROJECT / "02_timing_master/timing_master_m79_7d.csv",
            usecols=["date", "slot_end_inclusive", "is_forecast"],
        )
        forecast = master.loc[master["is_forecast"].eq(1)].reset_index(drop=True)
        starts = pd.to_datetime(forecast["date"])
        ends = pd.to_datetime(forecast["slot_end_inclusive"])
        np.testing.assert_array_equal(np.diff(starts).astype("timedelta64[D]"), 7)
        np.testing.assert_array_equal((ends - starts).dt.days.to_numpy(), 6)
        self.assertEqual(
            forecast["date"].tolist(),
            ["2026-08-01", "2026-08-08", "2026-08-15", "2026-08-22", "2026-08-29"],
        )

    def test_location_forecast_uses_ordered_bands(self) -> None:
        forecast = pd.read_csv(
            PROJECT / "06_ensemble/location/forecast_predictions.csv"
        )
        self.assertTrue(
            (
                (forecast["predicted_latitude_low"] <= forecast["predicted_latitude"])
                & (forecast["predicted_latitude"] <= forecast["predicted_latitude_high"])
                & (
                    forecast["predicted_longitude_low"]
                    <= forecast["predicted_longitude"]
                )
                & (
                    forecast["predicted_longitude"]
                    <= forecast["predicted_longitude_high"]
                )
            ).all()
        )
        self.assertTrue(
            (
                (forecast["conformal_latitude_low"] <= forecast["predicted_latitude_low"])
                & (
                    forecast["predicted_latitude_high"]
                    <= forecast["conformal_latitude_high"]
                )
            ).all()
        )


if __name__ == "__main__":
    unittest.main()
