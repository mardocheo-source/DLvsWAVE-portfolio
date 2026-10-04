#!/usr/bin/env python3
"""Combine latitude and longitude forecast reports into coordinate rows."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def read_by_date(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"empty location forecast: {path}")
    return {str(row["date"]): row for row in rows}


def combine(
    latitude_csv: Path,
    longitude_csv: Path,
    output_csv: Path,
    output_json: Path,
    output_md: Path,
) -> dict[str, object]:
    lat_rows = read_by_date(latitude_csv)
    lon_rows = read_by_date(longitude_csv)
    dates = sorted(set(lat_rows) & set(lon_rows))
    if not dates:
        raise ValueError("latitude and longitude forecasts have no common dates")

    rows: list[dict[str, object]] = []
    for day in dates:
        lat = lat_rows[day]
        lon = lon_rows[day]
        rows.append(
            {
                "date": day,
                "estimated_latitude": float(lat["estimated_value"]),
                "estimated_longitude": float(lon["estimated_value"]),
                "focus_window": int(lat.get("focus_window", "0") or 0)
                or int(lon.get("focus_window", "0") or 0),
                "latitude_predicted_raw": float(lat["predicted_raw"]),
                "longitude_predicted_raw": float(lon["predicted_raw"]),
            }
        )

    focus_rows = [row for row in rows if int(row["focus_window"]) == 1]
    selected = focus_rows or rows
    payload: dict[str, object] = {
        "latitude_csv": str(latitude_csv),
        "longitude_csv": str(longitude_csv),
        "rows": len(rows),
        "focus_rows": len(focus_rows),
        "focus_estimated_latitude_mean": sum(
            float(row["estimated_latitude"]) for row in selected
        )
        / len(selected),
        "focus_estimated_longitude_mean": sum(
            float(row["estimated_longitude"]) for row in selected
        )
        / len(selected),
        "semantics": (
            "Coordinates are independent experimental KAN estimates. Dates are starts "
            "of forecast slots; focus rows come from the first-stage timing forecast."
        ),
    }

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    output_md.write_text(
        "# August 2026 top-down location forecast\n\n"
        "Experimental KAN localization; this is not an operational earthquake alert.\n\n"
        f"- focus coordinate mean: `{payload['focus_estimated_latitude_mean']}, "
        f"{payload['focus_estimated_longitude_mean']}`\n"
        f"- focus rows: `{payload['focus_rows']}`\n"
        f"- combined CSV: `{output_csv}`\n"
        f"- latitude source: `{latitude_csv}`\n"
        f"- longitude source: `{longitude_csv}`\n\n"
        "Each date is the start of its 7-day slot. Historical location training "
        "uses earthquake rows only; future rows carry astronomical features solely "
        "for projection.\n"
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latitude-csv", required=True, type=Path)
    parser.add_argument("--longitude-csv", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        payload = combine(
            latitude_csv=args.latitude_csv,
            longitude_csv=args.longitude_csv,
            output_csv=args.output_csv,
            output_json=args.output_json,
            output_md=args.output_md,
        )
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"ERROR combine_location_coordinates: {exc}") from exc
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
