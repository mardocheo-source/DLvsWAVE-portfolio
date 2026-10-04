#!/usr/bin/env python3
"""Create a reusable seismic-history master with a future projection grid.

Historical non-event rows are removed. Rows in the requested forecast window
are retained even though they are not earthquakes, because the model needs
their astronomical features to project location targets into the future.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path


def parse_dt(value: str) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    try:
        result = datetime.fromisoformat(text)
    except ValueError:
        result = datetime.strptime(text[:10], "%Y-%m-%d")
    return result.replace(tzinfo=None)


def finite_float(value: object, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def in_window(dt: datetime, start: datetime, end: datetime) -> bool:
    return start.date() <= dt.date() <= end.date()


def build_projection_master(
    input_csv: Path,
    output_csv: Path,
    manifest_json: Path,
    forecast_start: datetime,
    forecast_end: datetime,
    event_mag_threshold: float,
) -> dict[str, object]:
    if forecast_end < forecast_start:
        raise ValueError("forecast end must be on or after forecast start")

    with input_csv.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    required = {"date", "mag", "latitude", "longitude", "depth"}
    missing = sorted(required - set(fieldnames))
    if missing:
        raise ValueError(f"required columns not found: {', '.join(missing)}")

    selected: list[dict[str, str]] = []
    historical_events = 0
    forecast_rows = 0
    removed_historical_non_events = 0
    leaked_future_events = 0
    historical_event_dates: list[str] = []
    forecast_dates: list[str] = []

    for row in rows:
        dt = parse_dt(row["date"])
        mag = finite_float(row.get("mag"))
        is_event = mag >= event_mag_threshold
        is_forecast = in_window(dt, forecast_start, forecast_end)

        if dt < forecast_start:
            if not is_event:
                removed_historical_non_events += 1
                continue
            historical_events += 1
            historical_event_dates.append(dt.date().isoformat())
            selected.append(dict(row))
            continue

        if is_forecast:
            if is_event:
                leaked_future_events += 1
            forecast_rows += 1
            forecast_dates.append(dt.date().isoformat())
            selected.append(dict(row))

    if historical_events < 2:
        raise ValueError(
            f"need at least two historical seismic rows; found {historical_events}"
        )
    if forecast_rows == 0:
        raise ValueError("no projection rows found in the requested forecast window")
    if leaked_future_events:
        raise ValueError(
            f"anti-leak guard: found {leaked_future_events} positive event rows "
            "inside the forecast window"
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)

    payload: dict[str, object] = {
        "input_csv": str(input_csv),
        "output_csv": str(output_csv),
        "input_rows": len(rows),
        "output_rows": len(selected),
        "historical_event_rows": historical_events,
        "forecast_projection_rows": forecast_rows,
        "removed_historical_non_event_rows": removed_historical_non_events,
        "event_mag_threshold": event_mag_threshold,
        "forecast_start_date": forecast_start.date().isoformat(),
        "forecast_end_date": forecast_end.date().isoformat(),
        "historical_event_dates": historical_event_dates,
        "forecast_projection_dates": forecast_dates,
        "anti_leak_future_event_rows": leaked_future_events,
        "semantics": (
            "Historical rows are earthquakes only. Future non-event rows are retained "
            "only as an astronomical projection grid and are never location targets."
        ),
    }
    manifest_json.parent.mkdir(parents=True, exist_ok=True)
    manifest_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--manifest-json", required=True, type=Path)
    parser.add_argument("--forecast-start-date", required=True)
    parser.add_argument("--forecast-end-date", required=True)
    parser.add_argument("--event-mag-threshold", type=float, default=0.1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        payload = build_projection_master(
            input_csv=args.input_csv,
            output_csv=args.output_csv,
            manifest_json=args.manifest_json,
            forecast_start=parse_dt(args.forecast_start_date),
            forecast_end=parse_dt(args.forecast_end_date),
            event_mag_threshold=float(args.event_mag_threshold),
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"ERROR prepare_seismic_projection_master: {exc}") from exc
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
