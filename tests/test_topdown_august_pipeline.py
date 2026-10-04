from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from combine_location_coordinates import combine
from prepare_seismic_projection_master import build_projection_master
from select_forecast_focus_window import select_focus
from topdown_forecast_validation_dashboard import (
    regression_metrics,
    seven_day_slot_labels,
    timing_metrics,
)


class TopDownAugustPipelineTests(unittest.TestCase):
    def test_dashboard_quality_metrics(self) -> None:
        timing = timing_metrics([0, 1, 0, 1], [0.1, 0.4, 0.7, 0.8], 0.5)
        self.assertEqual((timing["tp"], timing["fp"], timing["fn"], timing["tn"]), (1, 1, 1, 1))
        regression = regression_metrics([0, 1, 2], [0, 1, 2])
        self.assertEqual(regression["mae"], 0)
        self.assertEqual(regression["r2"], 1)
        self.assertEqual(
            seven_day_slot_labels([datetime(2026, 7, 29), datetime(2026, 8, 5)]),
            ["07-29\n→08-04", "08-05\n→08-11"],
        )

    def test_projection_master_keeps_events_and_future_grid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "master.csv"
            with source.open("w", newline="") as stream:
                writer = csv.DictWriter(
                    stream,
                    fieldnames=["date", "mag", "depth", "latitude", "longitude", "astro"],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {"date": "2000-01-01", "mag": "0", "depth": "0", "latitude": "0", "longitude": "0", "astro": "1"},
                        {"date": "2001-01-01", "mag": "8.5", "depth": "10", "latitude": "1", "longitude": "2", "astro": "2"},
                        {"date": "2002-01-01", "mag": "8.6", "depth": "11", "latitude": "3", "longitude": "4", "astro": "3"},
                        {"date": "2026-08-05", "mag": "0", "depth": "0", "latitude": "0", "longitude": "0", "astro": "4"},
                        {"date": "2026-08-12", "mag": "0", "depth": "0", "latitude": "0", "longitude": "0", "astro": "5"},
                        {"date": "2026-09-02", "mag": "0", "depth": "0", "latitude": "0", "longitude": "0", "astro": "6"},
                    ]
                )
            output = root / "projection.csv"
            manifest = root / "projection.json"
            payload = build_projection_master(
                source,
                output,
                manifest,
                datetime(2026, 8, 1),
                datetime(2026, 8, 31),
                0.1,
            )
            self.assertEqual(payload["historical_event_rows"], 2)
            self.assertEqual(payload["forecast_projection_rows"], 2)
            with output.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(
                [row["date"] for row in rows],
                ["2001-01-01", "2002-01-01", "2026-08-05", "2026-08-12"],
            )

    def test_focus_selector_bounds_peak_to_august(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            forecast = root / "forecast.csv"
            with forecast.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["context", "row_index", "predicted"])
                writer.writeheader()
                writer.writerows(
                    [
                        {"context": "2026-07-29", "row_index": "1", "predicted": "0.99"},
                        {"context": "2026-08-05", "row_index": "2", "predicted": "0.20"},
                        {"context": "2026-08-12", "row_index": "3", "predicted": "0.80"},
                        {"context": "2026-08-19", "row_index": "4", "predicted": "0.40"},
                    ]
                )
            payload = select_focus(
                forecast,
                root / "focus.json",
                root / "focus.env",
                datetime(2026, 8, 1),
                datetime(2026, 8, 31),
                "auto",
                "auto",
                7,
            )
            self.assertEqual(payload["focus_start_date"], "2026-08-12")
            self.assertEqual(payload["focus_end_date"], "2026-08-18")

    def test_coordinate_combination_uses_focus_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lat = root / "lat.csv"
            lon = root / "lon.csv"
            fieldnames = ["date", "predicted_raw", "estimated_value", "focus_window"]
            for path, values in (
                (lat, [("2026-08-05", 10, 0), ("2026-08-12", 20, 1)]),
                (lon, [("2026-08-05", 30, 0), ("2026-08-12", 40, 1)]),
            ):
                with path.open("w", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=fieldnames)
                    writer.writeheader()
                    for day, value, focus in values:
                        writer.writerow(
                            {
                                "date": day,
                                "predicted_raw": value / 100,
                                "estimated_value": value,
                                "focus_window": focus,
                            }
                        )
            payload = combine(
                lat,
                lon,
                root / "coordinates.csv",
                root / "coordinates.json",
                root / "coordinates.md",
            )
            self.assertEqual(payload["focus_estimated_latitude_mean"], 20)
            self.assertEqual(payload["focus_estimated_longitude_mean"], 40)
            self.assertEqual(json.loads((root / "coordinates.json").read_text())["focus_rows"], 1)


if __name__ == "__main__":
    unittest.main()
