#!/usr/bin/env python3
"""Build a Japan earthquake catalog with one explicit magnitude floor.

The USGS input is assumed to have already been downloaded with the requested
discovery floor. Both USGS and historical rows are filtered on their normalized
representative magnitude so the effective target definition is reproducible.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUTPUT_FIELDS = [
    "time",
    "date",
    "latitude",
    "longitude",
    "depth",
    "mag",
    "magnitude_lower",
    "magnitude_upper",
    "magnitude_original",
    "magnitude_type",
    "event_name",
    "place",
    "event_id",
    "source",
    "inclusion_rule",
    "strictly_confirmed_above_8_0",
    "date_uncertainty_days",
    "date_resolution_requirement_met",
    "notes",
    "primary_source",
    "supporting_source",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def parse_historical_magnitude(value: str) -> tuple[float | None, float | None, float | None]:
    """Return representative/lower/upper values while preserving the source text.

    The first explicit estimate is the representative report value.  All
    numeric values are used to expose a conservative lower/upper audit range.
    The representative value is used by the optional catalog threshold.
    """
    values = [float(item) for item in re.findall(r"(?<!\d)(\d+(?:\.\d+)?)", value or "")]
    if not values:
        return None, None, None
    return values[0], min(values), max(values)


def normalize_usgs(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            time = str(row.get("time") or "").strip()
            mag = finite_float(row.get("mag"))
            if not time or mag is None:
                raise ValueError(f"Invalid USGS event row: time={time!r}, mag={row.get('mag')!r}")
            rows.append(
                {
                    "time": time,
                    "date": time[:10],
                    "latitude": row.get("latitude", ""),
                    "longitude": row.get("longitude", ""),
                    "depth": row.get("depth", ""),
                    "mag": mag,
                    "magnitude_lower": mag,
                    "magnitude_upper": mag,
                    "magnitude_original": row.get("mag", ""),
                    "magnitude_type": row.get("magType", ""),
                    "event_name": "",
                    "place": row.get("place", ""),
                    "event_id": row.get("id", ""),
                    "source": "USGS_FDSN",
                    "inclusion_rule": "usgs_discovery_floor",
                    "strictly_confirmed_above_8_0": "",
                    "date_uncertainty_days": "0",
                    "date_resolution_requirement_met": "yes",
                    "notes": (
                        f"status={row.get('status', '')}; type={row.get('type', '')}; "
                        f"net={row.get('net', '')}"
                    ),
                    "primary_source": (
                        "https://earthquake.usgs.gov/earthquakes/eventpage/"
                        + str(row.get("id") or "")
                    ),
                    "supporting_source": "",
                }
            )
    return rows


def normalize_historical(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for index, row in enumerate(csv.DictReader(handle), start=1):
            date = str(row.get("date_iso_proleptic_gregorian") or "").strip()
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                raise ValueError(f"Invalid historical date: {date!r}")
            original = str(row.get("magnitude_estimate") or "").strip()
            representative, lower, upper = parse_historical_magnitude(original)
            rows.append(
                {
                    "time": f"{date}T00:00:00.000Z",
                    "date": date,
                    "latitude": "",
                    "longitude": "",
                    "depth": "",
                    "mag": representative if representative is not None else "",
                    "magnitude_lower": lower if lower is not None else "",
                    "magnitude_upper": upper if upper is not None else "",
                    "magnitude_original": original,
                    "magnitude_type": row.get("magnitude_type", ""),
                    "event_name": row.get("event_name", ""),
                    "place": row.get("region_or_source_area", ""),
                    "event_id": f"historical_attachment_{date}_{index:02d}",
                    "source": "historical_attachment",
                    "inclusion_rule": "forced_historical_list_membership",
                    "strictly_confirmed_above_8_0": row.get(
                        "strictly_confirmed_above_8_0", ""
                    ),
                    "date_uncertainty_days": row.get("date_uncertainty_days", ""),
                    "date_resolution_requirement_met": row.get(
                        "date_resolution_requirement_met", ""
                    ),
                    "notes": row.get("notes", ""),
                    "primary_source": row.get("primary_source", ""),
                    "supporting_source": row.get("supporting_source", ""),
                }
            )
    return rows


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(
    path: Path,
    rows: list[dict[str, Any]],
    audit: dict[str, Any],
    catalog_label: str,
) -> None:
    lines = [
        f"# {catalog_label}",
        "",
        (
            f"Records: **{len(rows)}** "
            f"({audit['historical_rows']} historical attachment + "
            f"{audit['usgs_rows']} USGS)."
        ),
        "",
        (
            "The unified Japan target floor is **M≥"
            f"{audit['catalog_minimum_magnitude']:g}** and is applied to both "
            "USGS and historical representative magnitudes."
        ),
        "",
        "| date | magnitude | event/place | source | inclusion |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for row in rows:
        magnitude = row["magnitude_original"] or row["mag"]
        label = row["event_name"] or row["place"] or row["event_id"]
        lines.append(
            f"| {row['date']} | {magnitude} | {label} | {row['source']} | "
            f"{row['inclusion_rule']} |"
        )
    lines.extend(
        [
            "",
            "Historical magnitudes remain estimates with their original text and range. "
            "The normalized numeric value is for plotting/audit only.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usgs-csv", required=True, type=Path)
    parser.add_argument("--historical-csv", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--output-audit-json", required=True, type=Path)
    parser.add_argument("--output-markdown", required=True, type=Path)
    parser.add_argument("--usgs-discovery-floor", type=float, default=7.9)
    parser.add_argument("--catalog-minimum-magnitude", type=float, default=8.3)
    parser.add_argument("--usgs-query-url", default="")
    parser.add_argument(
        "--catalog-label",
        default="Mega Quakes of Japan",
        help="Reader-facing Markdown title; does not affect catalog contents.",
    )
    args = parser.parse_args()

    raw_usgs = normalize_usgs(args.usgs_csv)
    raw_historical = normalize_historical(args.historical_csv)
    floor = float(args.catalog_minimum_magnitude)
    usgs = [row for row in raw_usgs if float(row["mag"]) >= floor]
    historical = [
        row
        for row in raw_historical
        if (value := finite_float(row.get("mag"))) is not None and value >= floor
    ]
    for row in [*usgs, *historical]:
        row["inclusion_rule"] = f"representative_magnitude_ge_{floor:g}"
    rows = sorted([*historical, *usgs], key=lambda item: parse_time(str(item["time"])))
    identifiers = [str(row["event_id"]) for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate event_id values in unified catalog")

    numeric_magnitudes = [
        float(value)
        for row in rows
        if (value := finite_float(row.get("mag"))) is not None
    ]
    audit = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "usgs_discovery_floor": float(args.usgs_discovery_floor),
        "catalog_minimum_magnitude": floor,
        "effective_catalog_minimum_magnitude": min(numeric_magnitudes),
        "threshold_refilter_applied": True,
        "historical_events_forced_inclusion": False,
        "excluded_below_threshold": {
            "usgs": len(raw_usgs) - len(usgs),
            "historical": len(raw_historical) - len(historical),
        },
        "total_rows": len(rows),
        "usgs_rows": len(usgs),
        "historical_rows": len(historical),
        "unique_event_ids": len(set(identifiers)),
        "earliest_event": rows[0]["time"],
        "latest_event": rows[-1]["time"],
        "usgs_query_url": args.usgs_query_url,
        "inputs": {
            "usgs_csv": str(args.usgs_csv),
            "usgs_sha256": sha256(args.usgs_csv),
            "historical_csv": str(args.historical_csv),
            "historical_sha256": sha256(args.historical_csv),
        },
    }
    write_csv(args.output_csv, rows)
    args.output_audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_audit_json.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_markdown(args.output_markdown, rows, audit, args.catalog_label)
    print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
