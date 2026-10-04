"""Regression tests for the clean two-level M7.7 study contract."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.binary_megathrust_data import TARGET_COLUMN, build_trial_split
from src.indexing import HistoricalShiftEngine, ShiftParameters
from src.master_fusion import build_clean_binary_megathrust_master


class CleanTwoLevelContractTests(unittest.TestCase):
    def test_weekly_91_day_shift_is_thirteen_rows(self) -> None:
        frame = pd.DataFrame({
            "date": pd.date_range("2000-01-03", periods=30, freq="7D"),
            "astro_test_metric": np.arange(30, dtype=float),
        })
        shifted, audit = HistoricalShiftEngine(ShiftParameters(
            astro_min_step=-13,
            astro_max_step=13,
            astro_step_days=7,
            seis_min_step=0,
            seis_max_step=0,
            temporal_resolution="7d",
        )).apply_shifts(frame)
        self.assertEqual(shifted.loc[13, "astro_test_metric_shift_m91d"], 0.0)
        self.assertEqual(shifted.loc[0, "astro_test_metric_shift_p91d"], 13.0)
        self.assertEqual(audit["inferred_row_cadence_days"], 7)
        self.assertEqual((audit["astro_row_offsets"][0], audit["astro_row_offsets"][-1]), (-13, 13))

    def test_core_master_and_exact_two_event_split(self) -> None:
        daily_dates = pd.date_range("1999-01-04", "2012-12-31", freq="D")
        daily = pd.DataFrame({
            "date": daily_dates,
            "astro_test_metric": np.sin(np.arange(len(daily_dates)) / 37.0),
        })
        japan = pd.DataFrame({
            "time": [
                "2000-01-10T00:00:00Z",
                "2003-09-25T19:50:06Z",
                "2011-03-11T05:46:24Z",
            ],
            "mag": [7.8, 8.16, 9.1],
            "latitude": [35.0, 41.8, 38.3],
            "longitude": [140.0, 143.9, 142.4],
            "id": ["train", "tokachi", "tohoku"],
        })
        world = pd.DataFrame({
            "time": ["2001-06-04T00:00:00Z"],
            "mag": [8.0],
            "latitude": [-20.0],
            "longitude": [-70.0],
            "id": ["foreign"],
        })
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            daily.to_csv(root / "daily.csv", index=False)
            japan.to_csv(root / "japan.csv", index=False)
            world.to_csv(root / "world.csv", index=False)
            clean, features, summary = build_clean_binary_megathrust_master(
                root / "daily.csv",
                root / "japan.csv",
                root / "world.csv",
                root / "out",
                cutoff_utc="2012-07-31T23:59:59Z",
                forecast_start="2012-08-01",
                forecast_end="2012-12-31",
            )
        self.assertTrue(features)
        self.assertEqual(summary["validation_event_weeks"], ["2003-09-22", "2011-03-07"])
        self.assertEqual(summary["training_hard_end"], "2003-06-16")
        self.assertEqual(summary["quantile_fit"]["end"], "2003-06-16")
        self.assertEqual(int(clean["is_world_hard_negative"].sum()), 1)
        split = build_trial_split(
            clean,
            window_before=7,
            window_after=7,
            background_ratio=0.1,
            train_start_year=1999,
            validation_event_count=2,
            seed=19,
            background_chunk_weeks=3,
            validation_weeks_before=13,
            validation_weeks_after=13,
        )
        self.assertEqual(len(split.validation), 54)
        self.assertEqual(int(split.validation[TARGET_COLUMN].sum()), 2)
        self.assertLess(pd.to_datetime(split.train["date"]).max(), pd.Timestamp("2003-06-23"))
        self.assertEqual(split.validation_event_weeks, [pd.Timestamp("2003-09-22"), pd.Timestamp("2011-03-07")])


if __name__ == "__main__":
    unittest.main()
