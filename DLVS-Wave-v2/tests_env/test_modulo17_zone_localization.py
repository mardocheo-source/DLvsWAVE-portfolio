"""Focused checks for the event-conditioned Japan zone pipeline."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from run_zone_forecast_study import (  # noqa: E402
    _member_zone_probability,
    _validate_args,
    build_parser,
    evaluate_zones,
)


def _definitions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "zone": [1, 2, 3, 4, 5],
            "center_latitude": [29.0, 32.0, 36.0, 40.0, 44.0],
            "center_longitude": [130.0, 138.0, 142.0, 139.0, 147.0],
        }
    )


class ZoneLocalizationTests(unittest.TestCase):
    def test_zone_metrics_round_clip_and_measure_adjacency(self) -> None:
        metrics = evaluate_zones(
            actual=np.array([1, 2, 4, 5]),
            predicted_continuous=np.array([0.1, 2.49, 2.6, 6.0]),
            definitions=_definitions(),
            recent_weight=3.0,
        )

        self.assertEqual(metrics["predicted_zone"], [1, 2, 3, 5])
        self.assertAlmostEqual(metrics["exact_zone_accuracy"], 0.75)
        self.assertAlmostEqual(metrics["adjacent_zone_accuracy"], 1.0)
        self.assertGreater(metrics["recent_weighted_mae_zone"], 0.0)

    def test_member_probability_is_normalized_and_centered(self) -> None:
        probability = _member_zone_probability(prediction=3.15, sigma=0.8, zone_count=5)

        self.assertAlmostEqual(float(probability.sum()), 1.0)
        self.assertEqual(int(np.argmax(probability)) + 1, 3)
        self.assertTrue(bool(np.all(probability > 0.0)))

    def test_cli_exposes_target_date_and_rejects_accelerators(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "--input-master",
                "master.csv",
                "--cluster-dir",
                "clusters",
                "--output-dir",
                "output",
                "--target-date",
                "2026-09-07",
            ]
        )

        _validate_args(args)
        self.assertEqual(args.target_date, "2026-09-07")
        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "--input-master",
                    "master.csv",
                    "--cluster-dir",
                    "clusters",
                    "--output-dir",
                    "output",
                    "--device",
                    "xpu",
                ]
            )


if __name__ == "__main__":
    unittest.main()
