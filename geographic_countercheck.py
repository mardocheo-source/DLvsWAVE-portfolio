#!/usr/bin/env python3
"""Prepare and summarize geographic counter-check forecast runs.

The heavy training remains in the existing shell pipelines.  This script builds
a reproducible macro script that runs:

- the main target zone with horizontal history;
- optionally the same target without horizontal history;
- nearby geographic counter-zones.

After runs finish it can summarize best-trial and fusion artifacts into a
credibility-oriented report.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import os
import re
import shlex
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


@dataclass
class Zone:
    zone_id: str
    name: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    depth_min: str = ""
    depth_max: str = ""
    notes: str = ""

    @property
    def lat_center(self) -> float:
        return (self.lat_min + self.lat_max) / 2.0

    @property
    def lon_center(self) -> float:
        return (self.lon_min + self.lon_max) / 2.0

    @property
    def lat_span(self) -> float:
        return self.lat_max - self.lat_min

    @property
    def lon_span(self) -> float:
        return self.lon_max - self.lon_min


@dataclass
class Event:
    day: date
    mag: float
    latitude: float
    longitude: float
    depth: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Geographic counter-check run planner/reporter.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    plan = sub.add_parser("plan", help="Create counter-check macro script.")
    plan.add_argument("--output-root", required=True)
    plan.add_argument("--base-run-label", default="geo-countercheck")
    plan.add_argument("--zones-csv", default="resources/seismic_zones.csv")
    plan.add_argument("--target-zones", required=True)
    plan.add_argument("--counter-count", type=int, default=3)
    plan.add_argument("--proximity-deg", type=float, default=45.0,
                      help="Max center distance for catalog-zone counters, or shift scale for synthetic counters.")
    plan.add_argument("--proximity-gap-deg", type=float, default=1.0,
                      help="Gap between target bbox and synthetic proximity counter bboxes.")
    plan.add_argument("--proximity-directions", default="east,west,north,south,ne,nw,se,sw",
                      help="Directions used by --counter-source proximity/shifted.")
    plan.add_argument("--proximity-lateral-fracs", default="0,0.25,0.5,0.75,1,-0.25,-0.5,-0.75,-1",
                      help="Lateral offsets, in fractions of target span, for cardinal proximity scans.")
    plan.add_argument("--counter-source", choices=["auto", "zones", "shifted", "proximity"], default="proximity",
                      help=("proximity creates non-overlapping nearby synthetic zones; zones uses only zones-csv; "
                            "shifted uses center shifts; auto tries non-overlapping zones then proximity."))
    plan.add_argument("--allow-overlap-counters", action="store_true",
                      help="Allow counter zones that overlap the target bbox. Off by default for false-positive tests.")
    plan.add_argument("--counter-min-events", default="auto",
                      help=("Minimum historical events required in a counter-zone before it is preferred. "
                            "Use auto to derive it from the target zone history."))
    plan.add_argument("--counter-min-event-frac", type=float, default=0.35,
                      help="Auto minimum counter events as this fraction of target-zone events.")
    plan.add_argument("--counter-min-year-span", type=float, default=5.0,
                      help="Minimum first-to-last event span in years for preferred counter-zones.")
    plan.add_argument("--counter-min-target-span-frac", type=float, default=0.75,
                      help="Require counter year span to cover this fraction of target-zone span.")
    plan.add_argument("--counter-min-decades", type=int, default=1,
                      help="Minimum distinct event decades for preferred counter-zones.")
    plan.add_argument("--counter-min-target-decades-frac", type=float, default=0.60,
                      help="Require counter decades to cover this fraction of target-zone decade count.")
    plan.add_argument("--counter-max-main-date-overlap-frac", type=float, default=0.35,
                      help="Max fraction of counter event dates that may coincide with main-zone event dates.")
    plan.add_argument("--proximity-rings", type=int, default=4,
                      help="How many adjacent rings to scan when building synthetic proximity counters.")
    plan.add_argument("--counter-overlap-relax-frac", type=float, default=0.75,
                      help="If not enough clean counters exist, allow this max overlap fraction between counters.")
    plan.add_argument("--src-events", default="/mnt/git0/git/repository/astro-USGS2/DB/WORLD-MAG7.7-1900-2026-06/earthquakes.RAW.csv")
    plan.add_argument("--min-mag", type=float, default=7.9)
    plan.add_argument("--binary-threshold", type=float, default=7.9)
    plan.add_argument("--device", choices=["xpu", "cpu"], default="xpu")
    plan.add_argument("--python-bin", default="")
    plan.add_argument("--include-no-history", action="store_true", default=True)
    plan.add_argument("--no-no-history", dest="include_no_history", action="store_false")
    plan.add_argument("--variant-mode", choices=["all", "main-history-only", "no-history-only"], default="all",
                      help="Which target/counter variants to generate.")
    plan.add_argument("--out-of-region-mode", default="neutralize-seismic")
    plan.add_argument("--row-filter", default="none",
                      help="Downstream row filter. Default none preserves sparse non-event context for binary detection.")
    plan.add_argument("--history-negative-sampling-mode", default="none")
    plan.add_argument("--pipeline-wrapper", default="",
                      help="Optional shell wrapper for history-enabled variants.")
    plan.add_argument("--step-interval", default="", help="Forecast/master cadence, e.g. 7d.")
    plan.add_argument("--forecast-start", default="", help="Forecast grid start date.")
    plan.add_argument("--forecast-end", default="", help="Forecast grid end date.")
    plan.add_argument("--events-end-date", default="", help="Anti-leak event cutoff date.")
    plan.add_argument("--forecast-label", default="", help="Human-readable forecast label.")
    plan.add_argument("--time-before", default="", help="nasaDb event window before each event.")
    plan.add_argument("--time-after", default="", help="nasaDb event window after each event.")
    plan.add_argument("--rebuild-master", choices=["0", "1"], default="",
                      help="Pass REBUILD_MASTER to the downstream pipeline.")
    plan.add_argument("--nasa-daily-master-mode", choices=["0", "1"], default="",
                      help="Pass NASA_DAILY_MASTER_MODE to the downstream pipeline.")
    plan.add_argument("--nasa-slot-advanced-stats", choices=["0", "1"], default="",
                      help="Pass NASA_SLOT_ADVANCED_STATS to the downstream pipeline.")
    plan.add_argument("--extra-env", action="append", default=[], help="Extra KEY=VALUE env assignment, repeatable.")
    plan.add_argument("--risk-adjudication", action="store_true", default=True,
                      help="Run target risk adjudication after the countercheck report.")
    plan.add_argument("--no-risk-adjudication", dest="risk_adjudication", action="store_false",
                      help="Skip downstream target risk adjudication in the generated macro.")
    plan.add_argument("--risk-adjudicator", default="geographic_risk_adjudicator.py",
                      help="Python helper used for downstream target risk adjudication.")

    report = sub.add_parser("report", help="Summarize completed counter-check runs.")
    report.add_argument("--plan-json", required=True)
    report.add_argument("--output-md", default="")
    report.add_argument("--output-json", default="")
    return parser.parse_args()


def read_zones(path: Path) -> list[Zone]:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    zones = []
    for row in rows:
        zones.append(
            Zone(
                zone_id=row["zone_id"].strip(),
                name=row.get("name", "").strip(),
                lat_min=float(row["latitude_min"]),
                lat_max=float(row["latitude_max"]),
                lon_min=float(row["longitude_min"]),
                lon_max=float(row["longitude_max"]),
                depth_min=row.get("depth_min", "").strip(),
                depth_max=row.get("depth_max", "").strip(),
                notes=row.get("notes", "").strip(),
            )
        )
    return zones


def write_zones(path: Path, zones: Iterable[Zone]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["zone_id", "name", "latitude_min", "latitude_max", "longitude_min", "longitude_max", "depth_min", "depth_max", "notes"]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for z in zones:
            w.writerow(
                {
                    "zone_id": z.zone_id,
                    "name": z.name,
                    "latitude_min": z.lat_min,
                    "latitude_max": z.lat_max,
                    "longitude_min": z.lon_min,
                    "longitude_max": z.lon_max,
                    "depth_min": z.depth_min,
                    "depth_max": z.depth_max,
                    "notes": z.notes,
                }
            )


def parse_event_date(value: str) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def read_events(path: Path, min_mag: float) -> list[Event]:
    if not path.exists():
        return []
    out: list[Event] = []
    with path.open(newline="") as f:
        rows = csv.DictReader(f)
        for row in rows:
            try:
                day = parse_event_date(row.get("time", ""))
                mag = float(row.get("mag", "nan"))
                lat = float(row.get("latitude", "nan"))
                lon = float(row.get("longitude", "nan"))
                depth = float(row.get("depth", "nan"))
            except ValueError:
                continue
            if day is None or not all(math.isfinite(x) for x in (mag, lat, lon, depth)):
                continue
            if mag < min_mag:
                continue
            out.append(Event(day=day, mag=mag, latitude=lat, longitude=lon, depth=depth))
    return out


def zone_lookup(zones: list[Zone]) -> dict[str, Zone]:
    out = {}
    for z in zones:
        out[z.zone_id.lower()] = z
        if z.name:
            out[z.name.lower()] = z
    return out


def split_tokens(text: str) -> list[str]:
    return [x.strip() for x in str(text or "").split(",") if x.strip()]


def wrap_lon(lon: float) -> float:
    while lon > 180:
        lon -= 360
    while lon < -180:
        lon += 360
    return lon


def clamp_lon(lon: float) -> float:
    return max(-180.0, min(180.0, lon))


def clamp_lat(lat: float) -> float:
    return max(-89.9, min(89.9, lat))


def distance_deg(a: Zone, b: Zone) -> float:
    dx = wrap_lon(a.lon_center - b.lon_center)
    dy = a.lat_center - b.lat_center
    return math.hypot(dx, dy)


def zone_contains_event(zone: Zone, event: Event) -> bool:
    if not (zone.lat_min <= event.latitude <= zone.lat_max):
        return False
    if not (zone.lon_min <= event.longitude <= zone.lon_max):
        return False
    if str(zone.depth_min).strip() and event.depth < float(zone.depth_min):
        return False
    if str(zone.depth_max).strip() and event.depth > float(zone.depth_max):
        return False
    return True


def zone_event_stats(zone: Zone, events: list[Event], reference_days: set[date] | None = None) -> dict:
    hits = [ev for ev in events if zone_contains_event(zone, ev)]
    days = sorted(ev.day for ev in hits)
    decades = sorted({(d.year // 10) * 10 for d in days})
    year_span = 0.0
    if len(days) >= 2:
        year_span = (days[-1] - days[0]).days / 365.25
    overlap_count = 0
    overlap_frac = 0.0
    if reference_days and days:
        overlap_count = len(set(days) & reference_days)
        overlap_frac = overlap_count / len(set(days))
    return {
        "event_count": len(hits),
        "first_event": days[0].isoformat() if days else "",
        "last_event": days[-1].isoformat() if days else "",
        "year_span": round(year_span, 3),
        "decade_count": len(decades),
        "decades": decades,
        "main_date_overlap_count": overlap_count,
        "main_date_overlap_frac": round(overlap_frac, 3),
    }


def zone_event_days(zone: Zone, events: list[Event]) -> set[date]:
    return {ev.day for ev in events if zone_contains_event(zone, ev)}


def resolve_auto_min_events(raw: str, target_events: int, event_frac: float) -> int:
    text = str(raw or "auto").strip().lower()
    if text != "auto":
        return max(0, int(float(text)))
    if target_events >= 8:
        return max(8, math.ceil(target_events * event_frac))
    return max(2, math.ceil(target_events * max(event_frac, 0.5)))


def stats_pass(stats: dict, min_events: int, min_year_span: float, min_decades: int,
               max_main_date_overlap_frac: float) -> bool:
    return (
        int(stats.get("event_count", 0)) >= min_events
        and float(stats.get("year_span", 0.0)) >= min_year_span
        and int(stats.get("decade_count", 0)) >= min_decades
        and float(stats.get("main_date_overlap_frac", 0.0)) <= max_main_date_overlap_frac
    )


def macro_zone(targets: list[Zone]) -> Zone:
    depth_mins = [float(z.depth_min) for z in targets if str(z.depth_min).strip()]
    depth_maxs = [float(z.depth_max) for z in targets if str(z.depth_max).strip()]
    return Zone(
        zone_id="macro_target",
        name="Macro target",
        lat_min=min(z.lat_min for z in targets),
        lat_max=max(z.lat_max for z in targets),
        lon_min=min(z.lon_min for z in targets),
        lon_max=max(z.lon_max for z in targets),
        depth_min=str(min(depth_mins)) if depth_mins else "",
        depth_max=str(max(depth_maxs)) if depth_maxs else "",
        notes="Union bbox of requested target zones",
    )


def shifted_counter_zones(base: Zone, count: int, step_deg: float) -> list[Zone]:
    shifts = [
        ("east", 0.0, step_deg),
        ("west", 0.0, -step_deg),
        ("north", step_deg, 0.0),
        ("south", -step_deg, 0.0),
        ("ne", step_deg, step_deg),
        ("sw", -step_deg, -step_deg),
        ("nw", step_deg, -step_deg),
        ("se", -step_deg, step_deg),
    ]
    out = []
    for label, dlat, dlon in shifts[: max(0, count)]:
        lat_c = clamp_lat(base.lat_center + dlat)
        lon_c = wrap_lon(base.lon_center + dlon)
        lat_half = base.lat_span / 2.0
        lon_half = base.lon_span / 2.0
        out.append(
            Zone(
                zone_id=f"counter_shift_{label}",
                name=f"Counter shifted {label}",
                lat_min=clamp_lat(lat_c - lat_half),
                lat_max=clamp_lat(lat_c + lat_half),
                lon_min=wrap_lon(lon_c - lon_half),
                lon_max=wrap_lon(lon_c + lon_half),
                depth_min=base.depth_min,
                depth_max=base.depth_max,
                notes="Synthetic nearby counter-zone",
            )
        )
    return out


def zones_overlap(a: Zone, b: Zone) -> bool:
    lat_overlap = max(a.lat_min, b.lat_min) <= min(a.lat_max, b.lat_max)
    lon_overlap = max(a.lon_min, b.lon_min) <= min(a.lon_max, b.lon_max)
    return bool(lat_overlap and lon_overlap)


def zone_area(zone: Zone) -> float:
    return max(0.0, zone.lat_span) * max(0.0, zone.lon_span)


def overlap_fraction(a: Zone, b: Zone) -> float:
    lat = max(0.0, min(a.lat_max, b.lat_max) - max(a.lat_min, b.lat_min))
    lon = max(0.0, min(a.lon_max, b.lon_max) - max(a.lon_min, b.lon_min))
    inter = lat * lon
    denom = min(zone_area(a), zone_area(b))
    if denom <= 0:
        return 0.0
    return inter / denom


def direction_tokens(text: str) -> list[str]:
    allowed = {"east", "west", "north", "south", "ne", "nw", "se", "sw"}
    tokens = split_tokens(text)
    return [t.lower() for t in tokens if t.lower() in allowed]


def parse_float_tokens(text: str) -> list[float]:
    out = []
    for token in split_tokens(text):
        try:
            out.append(float(token))
        except ValueError:
            continue
    return out or [0.0]


def fraction_suffix(value: float) -> str:
    if abs(value) < 1e-12:
        return ""
    sign = "p" if value > 0 else "m"
    return f"_{sign}{str(abs(value)).replace('.', '')}"


def raw_proximity_counter_zones(base: Zone, gap_deg: float, directions: str, rings: int,
                                lateral_fracs: str) -> list[Zone]:
    """Create nearby synthetic bboxes around the target bbox.

    They keep the target shape/depth and scan multiple adjacent rings.  The
    selector decides later which ones have enough historical events and whether
    limited overlap between counter-zones is needed as a fallback.
    """
    lat_span = base.lat_span
    lon_span = base.lon_span
    gap = max(0.0, float(gap_deg))
    out: list[Zone] = []
    laterals = parse_float_tokens(lateral_fracs)
    for ring in range(1, max(1, rings) + 1):
        for label in direction_tokens(directions):
            offsets = laterals if label in {"east", "west", "north", "south"} else [0.0]
            for lateral in offsets:
                dlat = 0.0
                dlon = 0.0
                if "north" == label:
                    dlat = ring * (lat_span + gap)
                    dlon = lateral * lon_span
                elif "south" == label:
                    dlat = -ring * (lat_span + gap)
                    dlon = lateral * lon_span
                elif "east" == label:
                    dlon = ring * (lon_span + gap)
                    dlat = lateral * lat_span
                elif "west" == label:
                    dlon = -ring * (lon_span + gap)
                    dlat = lateral * lat_span
                else:
                    dlat = ring * (lat_span + gap) * (1.0 if "n" in label else -1.0)
                    dlon = ring * (lon_span + gap) * (1.0 if "e" in label else -1.0)

                lat_min = clamp_lat(base.lat_min + dlat)
                lat_max = clamp_lat(base.lat_max + dlat)
                lon_min = clamp_lon(base.lon_min + dlon)
                lon_max = clamp_lon(base.lon_max + dlon)
                if lat_min >= lat_max or lon_min >= lon_max:
                    continue
                suffix = fraction_suffix(lateral) if label in {"east", "west", "north", "south"} else ""
                out.append(
                    Zone(
                        zone_id=f"counter_prox_{label}_r{ring}{suffix}",
                        name=f"Counter proximity {label} ring {ring}{suffix}",
                        lat_min=lat_min,
                        lat_max=lat_max,
                        lon_min=lon_min,
                        lon_max=lon_max,
                        depth_min=base.depth_min,
                        depth_max=base.depth_max,
                        notes=f"Synthetic proximity counter-zone, gap_deg={gap}, ring={ring}, lateral={lateral}",
                    )
                )
    return out


def candidate_sort_key(item: dict) -> tuple:
    stats = item["stats"]
    return (
        0 if item["stats_ok"] else 1,
        -int(stats.get("event_count", 0)),
        -int(stats.get("decade_count", 0)),
        -float(stats.get("year_span", 0.0)),
        float(item.get("distance_deg", 999999.0)),
    )


def selection_overlap_ok(zone: Zone, selected: list[dict], max_frac: float) -> bool:
    return all(overlap_fraction(zone, item["zone"]) <= max_frac for item in selected)


def select_counter_zones(zones: list[Zone], target_zones: list[Zone], count: int,
                         proximity_deg: float, source: str, *, gap_deg: float,
                         directions: str, allow_overlap: bool, events: list[Event],
                         min_events: int, min_year_span: float, min_decades: int,
                         max_main_date_overlap_frac: float, rings: int,
                         lateral_fracs: str, overlap_relax_frac: float) -> tuple[list[Zone], list[dict]]:
    target_ids = {z.zone_id.lower() for z in target_zones}
    base = macro_zone(target_zones)
    main_days = zone_event_days(base, events)
    candidates: list[dict] = []
    if source in {"auto", "zones"}:
        for z in zones:
            if z.zone_id.lower() in target_ids:
                continue
            if not allow_overlap and zones_overlap(base, z):
                continue
            d = distance_deg(base, z)
            if proximity_deg <= 0 or d <= proximity_deg:
                stats = zone_event_stats(z, events, main_days)
                candidates.append(
                    {
                        "zone": z,
                        "source": "zones",
                        "distance_deg": round(d, 3),
                        "stats": stats,
                        "stats_ok": stats_pass(
                            stats, min_events, min_year_span, min_decades, max_main_date_overlap_frac
                        ),
                    }
                )
    if source in {"auto", "proximity"}:
        for z in raw_proximity_counter_zones(base, gap_deg, directions, rings, lateral_fracs):
            if not allow_overlap and zones_overlap(base, z):
                continue
            stats = zone_event_stats(z, events, main_days)
            candidates.append(
                {
                    "zone": z,
                    "source": "proximity",
                    "distance_deg": round(distance_deg(base, z), 3),
                    "stats": stats,
                    "stats_ok": stats_pass(
                        stats, min_events, min_year_span, min_decades, max_main_date_overlap_frac
                    ),
                }
            )
    if source == "shifted":
        shifted = shifted_counter_zones(base, count, max(5.0, proximity_deg / 2.0))
        for z in shifted:
            if not allow_overlap and zones_overlap(base, z):
                continue
            stats = zone_event_stats(z, events, main_days)
            candidates.append(
                {
                    "zone": z,
                    "source": "shifted",
                    "distance_deg": round(distance_deg(base, z), 3),
                    "stats": stats,
                    "stats_ok": stats_pass(
                        stats, min_events, min_year_span, min_decades, max_main_date_overlap_frac
                    ),
                }
            )

    deduped: dict[str, dict] = {}
    for item in candidates:
        zone_id = item["zone"].zone_id.lower()
        if zone_id not in deduped or candidate_sort_key(item) < candidate_sort_key(deduped[zone_id]):
            deduped[zone_id] = item
    ranked = sorted(deduped.values(), key=candidate_sort_key)

    selected: list[dict] = []
    selected_ids: set[str] = set()
    passes = [
        ("strict_stats_no_counter_overlap", True, 0.0),
        ("stats_relaxed_counter_overlap", True, max(0.0, overlap_relax_frac)),
        ("fallback_best_available_no_counter_overlap", False, 0.0),
        ("fallback_best_available_relaxed_counter_overlap", False, max(0.0, overlap_relax_frac)),
    ]
    for reason, require_stats, max_overlap in passes:
        for item in ranked:
            if len(selected) >= count:
                break
            zone_id = item["zone"].zone_id.lower()
            if zone_id in selected_ids:
                continue
            if require_stats and not item["stats_ok"]:
                continue
            if not selection_overlap_ok(item["zone"], selected, max_overlap):
                continue
            item = dict(item)
            item["selection_reason"] = reason
            item["max_counter_overlap_allowed"] = max_overlap
            selected.append(item)
            selected_ids.add(zone_id)
        if len(selected) >= count:
            break

    selected_zones = [item["zone"] for item in selected[:count]]
    selected_stats = []
    for item in selected[:count]:
        z = item["zone"]
        selected_stats.append(
            {
                "zone_id": z.zone_id,
                "name": z.name,
                "source": item["source"],
                "distance_deg": item["distance_deg"],
                "stats_ok": item["stats_ok"],
                "selection_reason": item["selection_reason"],
                "max_counter_overlap_allowed": item["max_counter_overlap_allowed"],
                "latitude_min": z.lat_min,
                "latitude_max": z.lat_max,
                "longitude_min": z.lon_min,
                "longitude_max": z.lon_max,
                "depth_min": z.depth_min,
                "depth_max": z.depth_max,
                **item["stats"],
            }
        )
    return selected_zones, selected_stats


def shell_env(assignments: dict[str, str]) -> str:
    return " ".join(f"{k}={shlex.quote(str(v))}" for k, v in assignments.items() if str(v) != "")


def variant_command(variant: dict, args: argparse.Namespace, zones_csv: Path) -> str:
    repo = Path.cwd()
    row_filter = args.row_filter or "none"
    from artifacts import get_pipeline_serial
    serial_num = get_pipeline_serial()
    common_env = {
        "SRC_EVENTS": args.src_events,
        "MIN_MAG": args.min_mag,
        "RUN_LABEL": variant["run_label"],
        "OUT_DIR": variant["out_dir"],
        "HISTORY_NEGATIVE_SAMPLING_MODE": args.history_negative_sampling_mode,
        "DLVSWAVE_SERIAL": serial_num,
    }
    optional_env = {
        "STEP_INTERVAL": args.step_interval,
        "FORECAST_START": args.forecast_start,
        "FORECAST_END": args.forecast_end,
        "EVENTS_END_DATE": args.events_end_date,
        "FORECAST_LABEL": args.forecast_label,
        "TIME_BEFORE": args.time_before,
        "TIME_AFTER": args.time_after,
        "REBUILD_MASTER": args.rebuild_master,
        "NASA_DAILY_MASTER_MODE": args.nasa_daily_master_mode,
        "NASA_SLOT_ADVANCED_STATS": args.nasa_slot_advanced_stats,
    }
    common_env.update({k: v for k, v in optional_env.items() if str(v or "").strip()})
    for item in args.extra_env:
        if "=" not in item:
            raise ValueError(f"--extra-env must be KEY=VALUE: {item}")
        key, value = item.split("=", 1)
        common_env[key] = value

    common_args = [
        "--target-col", "mag",
        "--binary-threshold", str(args.binary_threshold),
        "--zones-csv", str(zones_csv),
        "--target-zones", variant["target_zones"],
        "--out-of-region-mode", args.out_of_region_mode,
        "--row-filter", row_filter,
    ]
    if variant["history"]:
        wrapper = Path(args.pipeline_wrapper) if args.pipeline_wrapper else repo / "commands" / f"run_world_mag85_30d_may_dec_horizontal_binary_{args.device}.sh"
        if not wrapper.is_absolute():
            wrapper = repo / wrapper
        return f"{shell_env(common_env)} {shlex.quote(str(wrapper))} " + " ".join(shlex.quote(x) for x in common_args)

    env = dict(common_env)
    env.update(
        {
            "ENABLE_BINARY_TARGET": "1",
            "ENABLE_HORIZONTAL_HISTORY": "0",
            "BINARY_TARGET_COL": "target",
            "BINARY_SOURCE_COL": "mag",
            "BINARY_THRESHOLD": str(args.binary_threshold),
        }
    )
    env.setdefault("KAN_DEVICE", args.device)
    env.setdefault("KAN_QUIET", "1" if args.device == "xpu" else "0")
    env.setdefault("JOBS", "1" if args.device == "xpu" else "3")
    env.setdefault(
        "PYTHON_BIN",
        args.python_bin or (
            str(Path.home() / "venvs" / "dlvswave-xpu" / "bin" / "python")
            if args.device == "xpu"
            else str(repo / ".venv" / "bin" / "python")
        ),
    )
    base = repo / "commands" / "run_world_mag85_30d_may_dec_nasadb_kan_base.sh"
    return f"{shell_env(env)} {shlex.quote(str(base))} " + " ".join(shlex.quote(x) for x in common_args)


def make_plan(args: argparse.Namespace) -> None:
    from artifacts import get_pipeline_serial
    serial_num = get_pipeline_serial()
    out_root = Path(args.output_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    zones_path = Path(args.zones_csv).resolve()
    zones = read_zones(zones_path)
    lookup = zone_lookup(zones)
    target_tokens = split_tokens(args.target_zones)
    targets = []
    for token in target_tokens:
        key = token.lower()
        if key not in lookup:
            raise ValueError(f"Target zone not found: {token}")
        targets.append(lookup[key])
    events = read_events(Path(args.src_events), args.min_mag)
    target_macro = macro_zone(targets)
    target_stats = zone_event_stats(target_macro, events)
    effective_min_events = resolve_auto_min_events(
        args.counter_min_events,
        int(target_stats.get("event_count", 0)),
        args.counter_min_event_frac,
    )
    effective_min_year_span = max(
        float(args.counter_min_year_span),
        float(target_stats.get("year_span", 0.0)) * float(args.counter_min_target_span_frac),
    )
    effective_min_decades = max(
        int(args.counter_min_decades),
        math.ceil(int(target_stats.get("decade_count", 0)) * float(args.counter_min_target_decades_frac)),
    )
    counters, counter_stats = select_counter_zones(
        zones,
        targets,
        args.counter_count,
        args.proximity_deg,
        args.counter_source,
        gap_deg=args.proximity_gap_deg,
        directions=args.proximity_directions,
        allow_overlap=args.allow_overlap_counters,
        events=events,
        min_events=effective_min_events,
        min_year_span=effective_min_year_span,
        min_decades=effective_min_decades,
        max_main_date_overlap_frac=args.counter_max_main_date_overlap_frac,
        rings=args.proximity_rings,
        lateral_fracs=args.proximity_lateral_fracs,
        overlap_relax_frac=args.counter_overlap_relax_frac,
    )

    generated_zones = out_root / "countercheck_zones.csv"
    all_zones = list(zones)
    existing = {z.zone_id.lower() for z in all_zones}
    for z in counters:
        if z.zone_id.lower() not in existing:
            all_zones.append(z)
            existing.add(z.zone_id.lower())
    write_zones(generated_zones, all_zones)

    variants = []
    if args.variant_mode in ("all", "main-history-only"):
        variants.append(
            {
                "kind": "main_history",
                "history": True,
                "target_zones": ",".join(z.zone_id for z in targets),
                "run_label": f"{args.base_run_label}__main_history",
                "out_dir": str(out_root / "main_history"),
            }
        )
    if args.variant_mode in ("all", "no-history-only") and args.include_no_history:
        variants.append(
            {
                "kind": "main_no_history",
                "history": False,
                "target_zones": ",".join(z.zone_id for z in targets),
                "run_label": f"{args.base_run_label}__main_no_history",
                "out_dir": str(out_root / "main_no_history"),
            }
        )
    if args.variant_mode == "all":
        for i, z in enumerate(counters, 1):
            variants.append(
                {
                    "kind": f"counter_{i}",
                    "history": True,
                    "target_zones": z.zone_id,
                    "run_label": f"{args.base_run_label}__counter_{i}_{z.zone_id}",
                    "out_dir": str(out_root / f"counter_{i}_{z.zone_id}"),
                }
            )

    plan = {
        "output_root": str(out_root),
        "zones_csv": str(generated_zones),
        "source_zones_csv": str(zones_path),
        "target_zones": [z.zone_id for z in targets],
        "target_stats": target_stats,
        "counter_zones": [z.zone_id for z in counters],
        "counter_stats": counter_stats,
        "counter_source": args.counter_source,
        "variant_mode": args.variant_mode,
        "proximity_gap_deg": args.proximity_gap_deg,
        "proximity_directions": args.proximity_directions,
        "proximity_lateral_fracs": args.proximity_lateral_fracs,
        "proximity_rings": args.proximity_rings,
        "allow_overlap_counters": args.allow_overlap_counters,
        "counter_min_events": args.counter_min_events,
        "counter_min_event_frac": args.counter_min_event_frac,
        "counter_min_year_span": args.counter_min_year_span,
        "counter_min_target_span_frac": args.counter_min_target_span_frac,
        "counter_min_decades": args.counter_min_decades,
        "counter_min_target_decades_frac": args.counter_min_target_decades_frac,
        "counter_max_main_date_overlap_frac": args.counter_max_main_date_overlap_frac,
        "effective_counter_min_events": effective_min_events,
        "effective_counter_min_year_span": round(effective_min_year_span, 3),
        "effective_counter_min_decades": effective_min_decades,
        "counter_overlap_relax_frac": args.counter_overlap_relax_frac,
        "risk_adjudication": args.risk_adjudication,
        "risk_adjudicator": args.risk_adjudicator,
        "pipeline_wrapper": args.pipeline_wrapper,
        "step_interval": args.step_interval,
        "forecast_start": args.forecast_start,
        "forecast_end": args.forecast_end,
        "events_end_date": args.events_end_date,
        "forecast_label": args.forecast_label,
        "time_before": args.time_before,
        "time_after": args.time_after,
        "rebuild_master": args.rebuild_master,
        "event_catalog_rows_mag_filtered": len(events),
        "binary_threshold": args.binary_threshold,
        "min_mag": args.min_mag,
        "src_events": args.src_events,
        "device": args.device,
        "serial_number": serial_num,
        "variants": variants,
    }
    plan_json = out_root / "countercheck_plan.json"
    plan_json.write_text(json.dumps(plan, indent=2) + "\n")
    with (out_root / "countercheck_plan.csv").open("w", newline="") as f:
        fields = ["kind", "history", "target_zones", "run_label", "out_dir"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for v in variants:
            w.writerow({k: v[k] for k in fields})
    with (out_root / "countercheck_counter_stats.csv").open("w", newline="") as f:
        fields = [
            "zone_id", "name", "source", "distance_deg", "stats_ok", "selection_reason",
            "max_counter_overlap_allowed", "event_count", "first_event", "last_event",
        "year_span", "decade_count", "decades", "latitude_min", "latitude_max",
            "longitude_min", "longitude_max", "depth_min", "depth_max",
            "main_date_overlap_count", "main_date_overlap_frac",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in counter_stats:
            out = dict(row)
            out["decades"] = " ".join(str(x) for x in out.get("decades", []))
            w.writerow({k: out.get(k, "") for k in fields})

    macro = out_root / "RUN_GEOGRAPHIC_COUNTERCHECK.sh"
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"cd {shlex.quote(str(Path.cwd()))}",
        "",
        f"export DLVSWAVE_SERIAL={serial_num}",
        f"echo 'Geographic countercheck: {args.base_run_label} (Serial: {serial_num})'",
        f"echo 'Plan: {plan_json}'",
        "",
    ]
    for v in variants:
        lines.extend([
            f"echo '======================================================================'",
            f"echo 'Run {v['kind']}: zones={v['target_zones']} history={v['history']}'",
            variant_command(v, args, generated_zones),
            "",
        ])
    report_cmd = [
        shlex.quote(args.python_bin or "python3"),
        "geographic_countercheck.py",
        "report",
        "--plan-json", str(plan_json),
    ]
    lines.extend([
        "echo '======================================================================'",
        "echo 'Summarize countercheck results'",
        " ".join(shlex.quote(x) for x in report_cmd),
    ])
    if args.risk_adjudication:
        risk_cmd = [
            shlex.quote(args.python_bin or "python3"),
            args.risk_adjudicator,
            "--plan-json", str(plan_json),
        ]
        lines.extend([
            "",
            "echo '======================================================================'",
            "echo 'Adjudicate target-zone risk with proximity false-positive pressure'",
            " ".join(shlex.quote(x) for x in risk_cmd),
        ])
    macro.write_text("\n".join(lines) + "\n")
    macro.chmod(0o755)
    print(f"[countercheck] plan: {plan_json}")
    print(f"[countercheck] zones: {generated_zones}")
    print(f"[countercheck] macro: {macro}")


def latest_run_dir(out_dir: Path) -> Path | None:
    dirs = sorted(out_dir.glob("pulsar_train*_best_trials_*"))
    return dirs[-1] if dirs else None


def run_dir_label(run_dir: str | Path | None) -> str:
    if not run_dir:
        return "none"
    return Path(str(run_dir)).name


def read_best_overall(run_dir: Path | None) -> dict:
    if run_dir is None:
        return {"available": False}
    idx = run_dir / "best_trials_index.csv"
    if not idx.exists():
        return {"available": False, "run_dir": str(run_dir)}
    with idx.open(newline="") as f:
        rows = list(csv.DictReader(f))
    best_overall = None
    best_generalized = None

    def row_float(row: dict, key: str, default: float | None = None) -> float | None:
        value = score_or_none(row.get(key))
        return default if value is None else value

    def row_generalization_score(row: dict, overall: float) -> float:
        overall_mean = row_float(row, "overall_mean", overall) or overall
        overall_std = row_float(row, "overall_std", 0.0) or 0.0
        mse_mean = row_float(row, "mse_mean", row_float(row, "mse_test", 1.0)) or 1.0
        mse_std = row_float(row, "mse_std", 0.0) or 0.0
        event_f1 = row_float(row, "event_f1", 0.0) or 0.0
        event_bal = row_float(row, "event_bal_acc", 0.5) or 0.5
        validation_gap = max(0.0, overall - overall_mean)
        mse_quality = 1.0 / (1.0 + max(0.0, mse_mean))
        stability_penalty = min(0.5, max(0.0, overall_std) + 0.25 * max(0.0, mse_std))
        return clamp01(
            0.35 * overall
            + 0.30 * overall_mean
            + 0.15 * event_bal
            + 0.10 * event_f1
            + 0.10 * mse_quality
            - 0.20 * validation_gap
            - 0.10 * stability_penalty
        )

    for row in rows:
        try:
            overall = float(row.get("overall") or row.get("score") or "nan")
        except ValueError:
            continue
        if not math.isfinite(overall):
            continue
        gen_score = row_generalization_score(row, overall)
        if best_overall is None or overall > best_overall[0]:
            best_overall = (overall, row)
        if best_generalized is None or gen_score > best_generalized[0]:
            best_generalized = (gen_score, row, overall)
    if best_overall is None or best_generalized is None:
        return {"available": False, "run_dir": str(run_dir), "best_trials_index": str(idx)}
    gen_score, gen_row, gen_overall = best_generalized
    overall_mean = row_float(gen_row, "overall_mean", gen_overall)
    overall_std = row_float(gen_row, "overall_std", 0.0)
    mse_mean = row_float(gen_row, "mse_mean", row_float(gen_row, "mse_test", None))
    mse_std = row_float(gen_row, "mse_std", 0.0)
    event_f1 = row_float(gen_row, "event_f1", None)
    event_bal = row_float(gen_row, "event_bal_acc", None)
    return {
        "available": True,
        "run_dir": str(run_dir),
        "best_trials_index": str(idx),
        "best_overall": best_overall[0],
        "best_readout": best_overall[1].get("readout"),
        "best_seed": best_overall[1].get("seed"),
        "best_generalization_score": gen_score,
        "best_generalization_overall": gen_overall,
        "best_generalization_readout": gen_row.get("readout"),
        "best_generalization_seed": gen_row.get("seed"),
        "best_overall_mean": overall_mean,
        "best_overall_std": overall_std,
        "best_mse_mean": mse_mean,
        "best_mse_std": mse_std,
        "best_event_f1": event_f1,
        "best_event_bal_acc": event_bal,
        "best_validation_generalization_gap": max(0.0, gen_overall - (overall_mean or gen_overall)),
    }


def read_fusion(run_dir: Path | None) -> dict:
    if run_dir is None:
        return {"available": False}
    candidates = sorted(run_dir.glob("**/*strength_fusion/*.json"))
    if not candidates:
        return {"available": False}
    path = candidates[-1]
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {"available": False, "path": str(path)}
    peak = data.get("selected_peak") or {}
    outputs = data.get("outputs") or {}
    return {
        "available": True,
        "path": str(path),
        "csv": outputs.get("csv") or str(path.with_suffix(".csv")),
        "png": outputs.get("png"),
        "selected_date": peak.get("date"),
        "window_end": peak.get("window_end"),
        "fused_score": peak.get("fused_score"),
        "consensus_fraction": peak.get("consensus_fraction"),
        "selected_peaks": data.get("selected_peaks") or [],
    }


def read_json_if_exists(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {"path": str(path), "read_error": True}
    if isinstance(data, dict):
        data.setdefault("path", str(path))
        return data
    return {"path": str(path), "unexpected_type": type(data).__name__}


def parse_validation_segments(out_dir: Path) -> list[tuple[date, date]]:
    logs = sorted(out_dir.glob("*.log"), key=lambda p: p.stat().st_mtime if p.exists() else 0.0)
    if not logs:
        return []
    text = logs[-1].read_text(errors="ignore")
    pattern = re.compile(
        r"Test period segment\s+\d+:\s+\d+\s+record,\s+"
        r"(\d{4}-\d{2}-\d{2})\s+->\s+(\d{4}-\d{2}-\d{2})"
    )
    seen: set[tuple[date, date]] = set()
    out: list[tuple[date, date]] = []
    for a, b in pattern.findall(text):
        try:
            item = (date.fromisoformat(a), date.fromisoformat(b))
        except ValueError:
            continue
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def summarize_variant(v: dict) -> dict:
    out_dir = Path(v["out_dir"])
    run_dir = latest_run_dir(out_dir)
    summary = dict(v)
    summary["latest_run_dir"] = str(run_dir) if run_dir else ""
    summary["best"] = read_best_overall(run_dir)
    summary["fusion"] = read_fusion(run_dir)
    summary["target_report"] = read_json_if_exists(out_dir / "target_selection_report.json")
    summary["history_manifest"] = read_json_if_exists(out_dir / "horizontal_history_manifest.json")
    summary["filtered_events_manifest"] = read_json_if_exists(out_dir / "filtered_events_manifest.json")
    summary["validation_segments"] = [
        {"start": a.isoformat(), "end": b.isoformat()} for a, b in parse_validation_segments(out_dir)
    ]
    return summary


def score_or_none(value) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def parse_date_value(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def annotate_peak_deltas(summaries: list[dict]) -> None:
    main = next((s for s in summaries if s["kind"] == "main_history"), None)
    main_peak = parse_date_value((main or {}).get("fusion", {}).get("selected_date"))
    for s in summaries:
        peak = parse_date_value(s.get("fusion", {}).get("selected_date"))
        s["peak_delta_days_vs_main"] = None
        if main_peak is not None and peak is not None:
            s["peak_delta_days_vs_main"] = abs((peak - main_peak).days)


def credibility_score(summary: dict | None) -> float | None:
    if not summary:
        return None
    fusion_score = score_or_none(summary.get("fusion", {}).get("fused_score"))
    generalized = score_or_none(summary.get("best", {}).get("best_generalization_score"))
    best_overall = score_or_none(summary.get("best", {}).get("best_overall"))
    if fusion_score is not None and generalized is not None:
        return clamp01(0.60 * fusion_score + 0.40 * generalized)
    if fusion_score is not None and best_overall is not None:
        return clamp01(0.70 * fusion_score + 0.30 * best_overall)
    if fusion_score is not None:
        return fusion_score
    if generalized is not None:
        return generalized
    return best_overall


def grade_report(summaries: list[dict]) -> tuple[str, dict]:
    main = next((s for s in summaries if s["kind"] == "main_history"), None)
    nohist = next((s for s in summaries if s["kind"] == "main_no_history"), None)
    counters = [s for s in summaries if s["kind"].startswith("counter_")]

    main_score = credibility_score(main)
    nohist_score = credibility_score(nohist)
    counter_scores = []
    strongest_counter = None
    for c in counters:
        s = credibility_score(c)
        if s is not None:
            counter_scores.append(s)
            if strongest_counter is None or s > strongest_counter[0]:
                strongest_counter = (s, c)
    max_counter = max(counter_scores) if counter_scores else None
    horizontal_gain = None if main_score is None or nohist_score is None else main_score - nohist_score
    geo_margin = None if main_score is None or max_counter is None else main_score - max_counter
    no_history_stronger = (
        main_score is not None and nohist_score is not None and nohist_score > main_score
    )
    counter_stronger = (
        main_score is not None and max_counter is not None and max_counter > main_score
    )

    grade = "incomplete"
    if main_score is not None:
        grade = "C"
        if main_score >= 0.65:
            grade = "B"
        if main_score >= 0.75 and (horizontal_gain is None or horizontal_gain >= 0.05) and (geo_margin is None or geo_margin >= 0.05):
            grade = "A"
        if counter_stronger:
            grade = "C"
        elif no_history_stronger and main_score >= 0.65:
            grade = "B-"
        if main_score < 0.5:
            grade = "D"
    return grade, {
        "score_policy": "credibility_score = 0.60*fused_forecast_validation_score + 0.40*trial_generalization_score when both are available",
        "main_score": main_score,
        "main_fused_score": score_or_none((main or {}).get("fusion", {}).get("fused_score")),
        "main_generalization_score": score_or_none((main or {}).get("best", {}).get("best_generalization_score")),
        "no_history_score": nohist_score,
        "no_history_fused_score": score_or_none((nohist or {}).get("fusion", {}).get("fused_score")) if nohist else None,
        "no_history_generalization_score": score_or_none((nohist or {}).get("best", {}).get("best_generalization_score")) if nohist else None,
        "max_counter_score": max_counter,
        "strongest_counter_kind": strongest_counter[1]["kind"] if strongest_counter else None,
        "strongest_counter_zones": strongest_counter[1]["target_zones"] if strongest_counter else None,
        "strongest_counter_peak_delta_days_vs_main": strongest_counter[1].get("peak_delta_days_vs_main") if strongest_counter else None,
        "horizontal_gain": horizontal_gain,
        "geographic_margin": geo_margin,
        "no_history_stronger_than_history": no_history_stronger,
        "counter_stronger_than_main": counter_stronger,
    }


def fmt_num(value, digits: int = 3) -> str:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(x):
        return ""
    return f"{x:.{digits}f}".rstrip("0").rstrip(".")


def variant_zones(variant: dict, lookup: dict[str, Zone]) -> list[Zone]:
    out = []
    for token in split_tokens(variant.get("target_zones", "")):
        z = lookup.get(token.lower())
        if z is not None:
            out.append(z)
    return out


def event_in_segments(ev: Event, segments: list[tuple[date, date]]) -> bool:
    return any(a <= ev.day <= b for a, b in segments)


def escape_xml(value) -> str:
    return html.escape(str(value), quote=True)


def svg_text_lines(lines: list[str], x: float, y: float, *, size: int = 13,
                   fill: str = "#263238", step: int = 18) -> list[str]:
    out = []
    for i, line in enumerate(lines):
        out.append(
            f'<text x="{x:.1f}" y="{(y + i * step):.1f}" '
            f'font-size="{size}" fill="{fill}">{escape_xml(line)}</text>'
        )
    return out


def wrap_text(text: str, max_chars: int) -> list[str]:
    raw_words = str(text or "").replace("\n", " ").split()
    words: list[str] = []
    for word in raw_words:
        if len(word) <= max_chars:
            words.append(word)
            continue
        chunk = ""
        for ch in word:
            chunk += ch
            if len(chunk) >= max_chars:
                words.append(chunk)
                chunk = ""
        if chunk:
            words.append(chunk)
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def svg_wrapped_text(text: str, x: float, y: float, max_chars: int, *,
                     size: int = 12, fill: str = "#263238", step: int = 15,
                     max_lines: int = 5, weight: str = "") -> tuple[list[str], float]:
    lines = wrap_text(text, max_chars)[:max_lines]
    if len(wrap_text(text, max_chars)) > max_lines and lines:
        lines[-1] = lines[-1].rstrip(".") + "..."
    weight_attr = f' font-weight="{weight}"' if weight else ""
    out = [
        f'<text x="{x:.1f}" y="{(y + i * step):.1f}" font-size="{size}" fill="{fill}"{weight_attr}>{escape_xml(line)}</text>'
        for i, line in enumerate(lines)
    ]
    return out, y + max(1, len(lines)) * step


def append_kv_table(pieces: list[str], *, x: float, y: float, w: float, title: str,
                    rows: list[tuple[str, str]], row_h: float = 38.0) -> float:
    title_h = 34.0
    h = title_h + len(rows) * row_h
    label_w = min(190.0, w * 0.26)
    pieces.append(f'<text x="{x:.1f}" y="{y - 12:.1f}" font-size="18" font-weight="700" fill="#111827">{escape_xml(title)}</text>')
    pieces.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#ffffff" stroke="#c7d0d9" stroke-width="1"/>')
    pieces.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{title_h:.1f}" fill="#f7f9fc"/>')
    pieces.append(f'<text x="{x + 12:.1f}" y="{y + 22:.1f}" font-size="13" font-weight="700" fill="#374151">Field</text>')
    pieces.append(f'<text x="{x + label_w + 18:.1f}" y="{y + 22:.1f}" font-size="13" font-weight="700" fill="#374151">Value</text>')
    pieces.append(f'<line x1="{x + label_w:.1f}" y1="{y:.1f}" x2="{x + label_w:.1f}" y2="{y + h:.1f}" stroke="#e1e7ef"/>')
    pieces.append(f'<line x1="{x:.1f}" y1="{y + title_h:.1f}" x2="{x + w:.1f}" y2="{y + title_h:.1f}" stroke="#c7d0d9"/>')
    yy = y + title_h
    value_chars = max(24, int((w - label_w - 28) / 6.6))
    for i, (label, value) in enumerate(rows):
        if i % 2:
            pieces.append(f'<rect x="{x:.1f}" y="{yy:.1f}" width="{w:.1f}" height="{row_h:.1f}" fill="#fbfcfd"/>')
        pieces.append(f'<line x1="{x:.1f}" y1="{yy + row_h:.1f}" x2="{x + w:.1f}" y2="{yy + row_h:.1f}" stroke="#edf1f5"/>')
        pieces.append(f'<text x="{x + 12:.1f}" y="{yy + 23:.1f}" font-size="11.5" font-weight="700" fill="#374151">{escape_xml(label)}</text>')
        wrapped, _ = svg_wrapped_text(value, x + label_w + 18, yy + 16, value_chars, size=11.3, step=14, max_lines=2)
        pieces.extend(wrapped)
        yy += row_h
    return y + h


def load_world_basemap() -> dict:
    path = Path(__file__).resolve().parent / "resources" / "world_basemap_gshhs_c.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def segment_overlaps(seg: list[list[float]], lon_min: float, lon_max: float,
                     lat_min: float, lat_max: float) -> bool:
    if not seg:
        return False
    xs = [float(p[0]) for p in seg]
    ys = [float(p[1]) for p in seg]
    return not (max(xs) < lon_min or min(xs) > lon_max or max(ys) < lat_min or min(ys) > lat_max)


def svg_geo_paths(segments: list[list[list[float]]], px, py, *,
                  lon_min: float, lon_max: float, lat_min: float, lat_max: float,
                  stroke: str, width: float, opacity: float, max_segments: int = 220) -> list[str]:
    out = []
    used = 0
    margin = 1.5
    for seg in segments:
        if used >= max_segments:
            break
        if not segment_overlaps(seg, lon_min, lon_max, lat_min, lat_max):
            continue
        d = []
        for lon, lat in seg:
            lon = float(lon)
            lat = float(lat)
            inside = (lon_min - margin <= lon <= lon_max + margin and lat_min - margin <= lat <= lat_max + margin)
            if inside:
                cmd = "M" if not d else "L"
                d.append(f"{cmd}{px(lon):.1f},{py(lat):.1f}")
            elif len(d) >= 2:
                out.append(
                    f'<path d="{" ".join(d)}" fill="none" stroke="{stroke}" '
                    f'stroke-width="{width}" opacity="{opacity}" vector-effect="non-scaling-stroke"/>'
                )
                used += 1
                d = []
                if used >= max_segments:
                    break
            else:
                d = []
        if len(d) >= 2 and used < max_segments:
            out.append(
                f'<path d="{" ".join(d)}" fill="none" stroke="{stroke}" '
                f'stroke-width="{width}" opacity="{opacity}" vector-effect="non-scaling-stroke"/>'
            )
            used += 1
    return out


def write_variant_map_svg(path: Path, csv_path: Path, *, variant: dict, zone: Zone,
                          main_zone: Zone | None, events: list[Event],
                          plan: dict, all_reference_zones: list[Zone],
                          fixed_extent: tuple[float, float, float, float] | None = None) -> dict:
    segments = []
    for item in variant.get("validation_segments", []):
        try:
            segments.append((date.fromisoformat(item["start"]), date.fromisoformat(item["end"])))
        except Exception:
            continue
    inside = [ev for ev in events if zone_contains_event(zone, ev)]
    validation = [ev for ev in inside if event_in_segments(ev, segments)]
    historical = [ev for ev in inside if not event_in_segments(ev, segments)]

    if fixed_extent is None:
        lon_values = [zone.lon_min, zone.lon_max]
        lat_values = [zone.lat_min, zone.lat_max]
        if main_zone is not None:
            lon_values += [main_zone.lon_min, main_zone.lon_max]
            lat_values += [main_zone.lat_min, main_zone.lat_max]
        for ev in inside:
            lon_values.append(ev.longitude)
            lat_values.append(ev.latitude)
        lon_min, lon_max = min(lon_values), max(lon_values)
        lat_min, lat_max = min(lat_values), max(lat_values)
        lon_pad = max(2.0, (lon_max - lon_min) * 0.18)
        lat_pad = max(2.0, (lat_max - lat_min) * 0.18)
        lon_min = max(-180.0, lon_min - lon_pad)
        lon_max = min(180.0, lon_max + lon_pad)
        lat_min = max(-90.0, lat_min - lat_pad)
        lat_max = min(90.0, lat_max + lat_pad)
    else:
        lon_min, lon_max, lat_min, lat_max = fixed_extent
    if abs(lon_max - lon_min) < 1e-9:
        lon_min -= 1.0
        lon_max += 1.0
    if abs(lat_max - lat_min) < 1e-9:
        lat_min -= 1.0
        lat_max += 1.0

    width, height = 1500, 1360
    map_x, map_y, map_w, map_h = 58, 86, 940, 560
    panel_x, panel_y, panel_w, panel_h = 1030, 86, 410, 560
    lon_span = lon_max - lon_min
    lat_span = lat_max - lat_min
    scale = min(map_w / lon_span, map_h / lat_span)
    plot_w = lon_span * scale
    plot_h = lat_span * scale
    plot_x = map_x + (map_w - plot_w) / 2.0
    plot_y = map_y + (map_h - plot_h) / 2.0
    scale_note = f"map scale: common extent, 1 deg lon = 1 deg lat = {scale:.2f}px"

    def px(lon: float) -> float:
        return plot_x + (lon - lon_min) * scale

    def py(lat: float) -> float:
        return plot_y + (lat_max - lat) * scale

    def rect_for(z: Zone, color: str, stroke_width: float, dash: str = "", opacity: float = 1.0) -> str:
        x1, x2 = px(z.lon_min), px(z.lon_max)
        y1, y2 = py(z.lat_max), py(z.lat_min)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        return (
            f'<rect x="{min(x1, x2):.1f}" y="{min(y1, y2):.1f}" '
            f'width="{abs(x2 - x1):.1f}" height="{abs(y2 - y1):.1f}" '
            f'fill="none" stroke="{color}" stroke-width="{stroke_width}"{dash_attr} opacity="{opacity}"/>'
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["role", "date", "mag", "latitude", "longitude", "depth"])
        w.writeheader()
        for ev in historical:
            w.writerow({"role": "historical", "date": ev.day.isoformat(), "mag": ev.mag,
                        "latitude": ev.latitude, "longitude": ev.longitude, "depth": ev.depth})
        for ev in validation:
            w.writerow({"role": "validation", "date": ev.day.isoformat(), "mag": ev.mag,
                        "latitude": ev.latitude, "longitude": ev.longitude, "depth": ev.depth})

    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfcfd"/>',
        '<defs>',
        f'<clipPath id="mapClip"><rect x="{map_x}" y="{map_y}" width="{map_w}" height="{map_h}"/></clipPath>',
        '</defs>',
        f'<text x="58" y="38" font-size="24" font-weight="700" fill="#111827">{escape_xml(variant["kind"])} geographic validation map</text>',
        f'<text x="58" y="63" font-size="13" fill="#4b5563">Fixed-scale diagnostic map; detailed filters and metrics are tabulated below.</text>',
        f'<rect x="{map_x}" y="{map_y}" width="{map_w}" height="{map_h}" fill="#eef6fb" stroke="#263238" stroke-width="1.2"/>',
    ]

    lon_step = max(1, int(math.ceil((lon_max - lon_min) / 6.0 / 5.0)) * 5)
    lat_step = max(1, int(math.ceil((lat_max - lat_min) / 6.0 / 5.0)) * 5)
    lon_grid_start = math.ceil(lon_min / lon_step) * lon_step
    lat_grid_start = math.ceil(lat_min / lat_step) * lat_step
    lon = lon_grid_start
    while lon <= lon_max + 1e-9:
        x = px(lon)
        pieces.append(f'<line x1="{x:.1f}" y1="{map_y}" x2="{x:.1f}" y2="{map_y + map_h}" stroke="#d7dde3" stroke-width="0.8"/>')
        pieces.append(f'<text x="{x:.1f}" y="{map_y + map_h + 22}" text-anchor="middle" font-size="11" fill="#52616b">{fmt_num(lon, 1)} lon</text>')
        lon += lon_step
    lat = lat_grid_start
    while lat <= lat_max + 1e-9:
        y = py(lat)
        pieces.append(f'<line x1="{map_x}" y1="{y:.1f}" x2="{map_x + map_w}" y2="{y:.1f}" stroke="#d7dde3" stroke-width="0.8"/>')
        pieces.append(f'<text x="{map_x - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="#52616b">{fmt_num(lat, 1)} lat</text>')
        lat += lat_step

    basemap = load_world_basemap()
    pieces.append('<g clip-path="url(#mapClip)">')
    pieces.extend(svg_geo_paths(
        basemap.get("coastlines", []),
        px,
        py,
        lon_min=lon_min,
        lon_max=lon_max,
        lat_min=lat_min,
        lat_max=lat_max,
        stroke="#667085",
        width=1.15,
        opacity=0.68,
        max_segments=260,
    ))
    pieces.extend(svg_geo_paths(
        basemap.get("countries", []),
        px,
        py,
        lon_min=lon_min,
        lon_max=lon_max,
        lat_min=lat_min,
        lat_max=lat_max,
        stroke="#98a2b3",
        width=0.65,
        opacity=0.45,
        max_segments=360,
    ))
    for ref in all_reference_zones:
        if ref.zone_id != zone.zone_id and (main_zone is None or ref.zone_id != main_zone.zone_id):
            pieces.append(rect_for(ref, "#9ca3af", 1.0, "4 4", 0.35))
    if main_zone is not None and main_zone.zone_id != zone.zone_id:
        pieces.append(rect_for(main_zone, "#374151", 2.0, "8 5", 0.75))
    pieces.append(rect_for(zone, "#d62728", 3.0))

    for ev in historical:
        r = 3.5 + max(0.0, ev.mag - float(plan.get("min_mag", 0.0))) * 1.8
        pieces.append(
            f'<circle cx="{px(ev.longitude):.1f}" cy="{py(ev.latitude):.1f}" r="{r:.1f}" '
            f'fill="#1f77b4" stroke="#0f3d66" stroke-width="0.7" opacity="0.78"/>'
        )
    for ev in validation:
        r = 5.2 + max(0.0, ev.mag - float(plan.get("min_mag", 0.0))) * 2.0
        pieces.append(
            f'<circle cx="{px(ev.longitude):.1f}" cy="{py(ev.latitude):.1f}" r="{r:.1f}" '
            f'fill="#f2c94c" stroke="#3f3200" stroke-width="1.2" opacity="0.95"/>'
        )
    pieces.append("</g>")

    pieces.extend([
        f'<rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" fill="#ffffff" stroke="#c7d0d9" stroke-width="1"/>',
        f'<text x="{panel_x + 18}" y="{panel_y + 32}" font-size="17" font-weight="700" fill="#111827">Map summary</text>',
    ])
    depth_range = f"{zone.depth_min or '-inf'}..{zone.depth_max or '+inf'} km"
    event_range = ""
    if inside:
        event_range = f"{min(ev.day for ev in inside).isoformat()}..{max(ev.day for ev in inside).isoformat()}"
    validation_range = "; ".join(f"{a.isoformat()}..{b.isoformat()}" for a, b in segments) or "not found in log"
    filtered_manifest = variant.get("filtered_events_manifest") or {}
    target_report = variant.get("target_report") or {}
    catalog_range = (
        f"{filtered_manifest.get('start_date', '')}..{filtered_manifest.get('end_date', '')}"
        if filtered_manifest else ""
    )
    kept_range = (
        f"{str(filtered_manifest.get('first_kept_time', ''))[:10]}..{str(filtered_manifest.get('last_kept_time', ''))[:10]}"
        if filtered_manifest else ""
    )
    panel_lines = [
        f"Variant: {variant['kind']}",
        f"Zones: {variant.get('target_zones')}",
        f"History enabled: {variant.get('history')}",
        f"Run selected: latest subrun ({run_dir_label(variant.get('latest_run_dir'))})",
        scale_note,
        f"Events inside zone: {len(inside)}",
        f"Historical blue: {len(historical)}",
        f"Validation yellow: {len(validation)}",
    ]
    ty = panel_y + 62
    for line in panel_lines:
        wrapped, ty = svg_wrapped_text(line, panel_x + 18, ty, 46, size=12, step=15, max_lines=2)
        pieces.extend(wrapped)
        ty += 5

    legend_y = max(ty + 28, panel_y + 265)
    pieces.extend([
        f'<text x="{panel_x + 18}" y="{legend_y}" font-size="17" font-weight="700" fill="#111827">Legend</text>',
        f'<circle cx="{panel_x + 28}" cy="{legend_y + 28}" r="6" fill="#1f77b4" stroke="#0f3d66" stroke-width="0.7" opacity="0.78"/>',
        f'<text x="{panel_x + 48}" y="{legend_y + 32}" font-size="12" fill="#263238">Historical in-zone event</text>',
        f'<circle cx="{panel_x + 28}" cy="{legend_y + 56}" r="7" fill="#f2c94c" stroke="#3f3200" stroke-width="1.2"/>',
        f'<text x="{panel_x + 48}" y="{legend_y + 60}" font-size="12" fill="#263238">Validation-window event</text>',
        f'<rect x="{panel_x + 20}" y="{legend_y + 78}" width="18" height="13" fill="none" stroke="#d62728" stroke-width="3"/>',
        f'<text x="{panel_x + 48}" y="{legend_y + 90}" font-size="12" fill="#263238">Active target/counter rectangle</text>',
        f'<rect x="{panel_x + 20}" y="{legend_y + 106}" width="18" height="13" fill="none" stroke="#374151" stroke-width="2" stroke-dasharray="8 5"/>',
        f'<text x="{panel_x + 48}" y="{legend_y + 118}" font-size="12" fill="#263238">Main target rectangle when different</text>',
        f'<text x="{panel_x + 18}" y="{legend_y + 154}" font-size="11" fill="#52616b">Point radius scales mildly with magnitude.</text>',
    ])
    best = variant.get("best", {})
    fusion = variant.get("fusion", {})
    variant_run_dir = variant.get('latest_run_dir')
    if variant_run_dir:
        vrp = Path(variant_run_dir)
        run_folder = str(vrp.parent)
        run_name = str(vrp.name)
    else:
        run_folder = "none"
        run_name = "none"

    spec_rows = [
        ("variant", str(variant.get("kind", ""))),
        ("run folder", run_folder),
        ("run name", run_name),
        ("zone", str(variant.get("target_zones", ""))),
        ("lat / lon", f"{fmt_num(zone.lat_min)}..{fmt_num(zone.lat_max)} / {fmt_num(zone.lon_min)}..{fmt_num(zone.lon_max)}"),
        ("depth", depth_range),
        ("target", f"mag >= {plan.get('binary_threshold', plan.get('min_mag'))}"),
        ("row filter", str(target_report.get("row_filter", "unknown"))),
        ("catalog dates", catalog_range or "unknown"),
        ("kept event time", kept_range or "unknown"),
        ("validation windows", validation_range),
    ]
    metric_rows = [
        ("best overall", fmt_num(best.get("best_overall"), 6)),
        ("best model", f"{best.get('best_readout', '')} seed={best.get('best_seed', '')}"),
        ("generalization score", fmt_num(best.get("best_generalization_score"), 6)),
        ("generalized model", f"{best.get('best_generalization_readout', '')} seed={best.get('best_generalization_seed', '')}"),
        ("trial mean/std", f"{fmt_num(best.get('best_overall_mean'), 6)} / {fmt_num(best.get('best_overall_std'), 6)}"),
        ("mse mean/std", f"{fmt_num(best.get('best_mse_mean'), 6)} / {fmt_num(best.get('best_mse_std'), 6)}"),
        ("fused score", fmt_num(fusion.get("fused_score"), 6)),
        ("peak window", f"{fusion.get('selected_date', '')}->{fusion.get('window_end', '')}"),
        ("consensus", str(fusion.get("consensus_fraction", ""))),
        ("map events", f"total={len(inside)} hist={len(historical)} val={len(validation)}"),
        ("target rows", f"positive={target_report.get('positive_rows_by_threshold', '')} total={target_report.get('finite_target_rows', '')}"),
        ("features", str(target_report.get("feature_count", "unknown"))),
        ("fusion json", str(fusion.get("path", ""))),
    ]
    tables_y = map_y + map_h + 78
    append_kv_table(pieces, x=58, y=tables_y, w=670, title="Zone / Filter Specification", rows=spec_rows, row_h=39)
    append_kv_table(pieces, x=770, y=tables_y, w=670, title="Run Metrics", rows=metric_rows, row_h=39)
    pieces.append("</svg>")
    path.write_text("\n".join(pieces) + "\n")
    return {
        "svg": str(path),
        "csv": str(csv_path),
        "zone_id": zone.zone_id,
        "event_count": len(inside),
        "historical_count": len(historical),
        "validation_count": len(validation),
        "validation_windows": [{"start": a.isoformat(), "end": b.isoformat()} for a, b in segments],
    }


def zone_summary_for_map(zone: Zone, events: list[Event], validation_segments: list[tuple[date, date]]) -> dict:
    inside = [ev for ev in events if zone_contains_event(zone, ev)]
    validation = [ev for ev in inside if event_in_segments(ev, validation_segments)]
    historical = [ev for ev in inside if not event_in_segments(ev, validation_segments)]
    return {
        "event_count": len(inside),
        "historical_count": len(historical),
        "validation_count": len(validation),
        "first_event": min((ev.day for ev in inside), default=None),
        "last_event": max((ev.day for ev in inside), default=None),
    }


def metric_text(summary: dict | None, title: str) -> list[str]:
    if not summary:
        return [f"{title}: unavailable"]
    best = summary.get("best", {})
    fusion = summary.get("fusion", {})
    cred = credibility_score(summary)
    return [
        f"{title}",
        f"cred={fmt_num(cred, 3)}",
        f"fused={fusion.get('fused_score', '')}",
        f"best={fmt_num(best.get('best_overall'), 3)}",
        f"gen={fmt_num(best.get('best_generalization_score'), 3)}",
        f"peak={fusion.get('selected_date', '')}->{fusion.get('window_end', '')}",
        f"cons={fusion.get('consensus_fraction', '')}",
    ]


def read_forecast_series(summary: dict | None) -> list[dict]:
    if not summary:
        return []
    fusion = summary.get("fusion") or {}
    csv_path = fusion.get("csv")
    if not csv_path and fusion.get("path"):
        csv_path = str(Path(fusion["path"]).with_suffix(".csv"))
    if not csv_path or not Path(csv_path).exists():
        rows = fusion.get("selected_peaks") or []
        out = []
        for row in rows:
            day = parse_event_date(str(row.get("date", "")))
            score = score_or_none(row.get("fused_score"))
            if day is not None and score is not None:
                out.append({
                    "date": day,
                    "date_label": day.isoformat(),
                    "score": clamp01(score),
                    "selected": bool(row.get("selected_peak")),
                })
        return sorted(out, key=lambda r: r["date"])
    out = []
    try:
        with Path(csv_path).open(newline="") as f:
            rows = list(csv.DictReader(f))
    except Exception:
        return []
    for row in rows:
        day = parse_event_date(str(row.get("date", "")))
        score = score_or_none(row.get("fused_score"))
        if day is None or score is None:
            continue
        out.append({
            "date": day,
            "date_label": day.isoformat(),
            "score": clamp01(score),
            "selected": str(row.get("selected_peak", "")).strip() in {"1", "true", "True", "yes"},
        })
    return sorted(out, key=lambda r: r["date"])


def append_forecast_sparkline(
    pieces: list[str],
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    summary: dict | None,
    color: str,
    comparison: dict | None = None,
) -> None:
    primary = read_forecast_series(summary)
    secondary = read_forecast_series(comparison)
    pieces.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#fbfcfd" stroke="#e1e7ef" stroke-width="1"/>')
    pieces.append(f'<text x="{x + 8:.1f}" y="{y + 15:.1f}" font-size="10.5" font-weight="700" fill="#374151">forecast trend</text>')
    if not primary and not secondary:
        pieces.append(f'<text x="{x + 8:.1f}" y="{y + 38:.1f}" font-size="10.5" fill="#6b7280">forecast CSV unavailable</text>')
        return

    plot_x = x + 30
    plot_y = y + 22
    plot_w = w - 44
    plot_h = h - 52
    axis_y = plot_y + plot_h
    pieces.append(f'<line x1="{plot_x:.1f}" y1="{plot_y:.1f}" x2="{plot_x:.1f}" y2="{axis_y:.1f}" stroke="#9aa4b2" stroke-width="0.8"/>')
    pieces.append(f'<line x1="{plot_x:.1f}" y1="{axis_y:.1f}" x2="{plot_x + plot_w:.1f}" y2="{axis_y:.1f}" stroke="#9aa4b2" stroke-width="0.8"/>')
    pieces.append(f'<text x="{plot_x - 5:.1f}" y="{plot_y + 4:.1f}" text-anchor="end" font-size="8.5" fill="#6b7280">1</text>')
    pieces.append(f'<text x="{plot_x - 5:.1f}" y="{axis_y + 3:.1f}" text-anchor="end" font-size="8.5" fill="#6b7280">0</text>')

    all_days = sorted({r["date"] for r in primary + secondary})
    if len(all_days) <= 1:
        day_to_x = {all_days[0]: plot_x + plot_w / 2.0} if all_days else {}
    else:
        min_day, max_day = all_days[0], all_days[-1]
        span = max(1, (max_day - min_day).days)
        day_to_x = {d: plot_x + ((d - min_day).days / span) * plot_w for d in all_days}

    for d in all_days:
        tx = day_to_x[d]
        pieces.append(f'<line x1="{tx:.1f}" y1="{plot_y:.1f}" x2="{tx:.1f}" y2="{axis_y:.1f}" stroke="#edf1f5" stroke-width="0.7"/>')
        label = d.strftime("%m-%d")
        pieces.append(
            f'<text x="{tx:.1f}" y="{axis_y + 15:.1f}" text-anchor="end" '
            f'font-size="8.2" fill="#52616b" transform="rotate(-42 {tx:.1f} {axis_y + 15:.1f})">{label}</text>'
        )

    def mark_local_peaks(rows: list[dict]) -> list[dict]:
        marked = []
        for idx, row in enumerate(rows):
            item = dict(row)
            item["local_peak"] = (
                0 < idx < len(rows) - 1
                and float(rows[idx]["score"]) > float(rows[idx - 1]["score"])
                and float(rows[idx]["score"]) > float(rows[idx + 1]["score"])
            )
            marked.append(item)
        return marked

    def draw_series(rows: list[dict], stroke: str, opacity: float, dash: str = "") -> None:
        if not rows:
            return
        rows = mark_local_peaks(rows)
        pts = []
        for row in rows:
            tx = day_to_x.get(row["date"], plot_x)
            ty = plot_y + (1.0 - clamp01(row["score"])) * plot_h
            pts.append((tx, ty, row))
        if len(pts) >= 2:
            path = " ".join(f"{tx:.1f},{ty:.1f}" for tx, ty, _ in pts)
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            pieces.append(f'<polyline points="{path}" fill="none" stroke="{stroke}" stroke-width="1.8" opacity="{opacity}"{dash_attr}/>')
        for tx, ty, row in pts:
            is_peak = row.get("local_peak")
            r = 3.8 if is_peak else 2.1
            fill = "#ffffff" if is_peak else stroke
            sw = 1.45 if is_peak else 0.8
            pieces.append(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>')

    draw_series(secondary, "#64748b", 0.55, "4 3")
    draw_series(primary, color, 0.95)
    if secondary:
        pieces.append(f'<line x1="{x + w - 78:.1f}" y1="{y + 14:.1f}" x2="{x + w - 54:.1f}" y2="{y + 14:.1f}" stroke="#64748b" stroke-width="1.4" stroke-dasharray="4 3" opacity="0.6"/>')
        pieces.append(f'<text x="{x + w - 49:.1f}" y="{y + 17:.1f}" font-size="8.8" fill="#64748b">no hist</text>')


def write_overview_map_svg(path: Path, *, plan: dict, summaries: list[dict],
                           zones: list[Zone], lookup: dict[str, Zone],
                           events: list[Event],
                           common_extent: tuple[float, float, float, float]) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1600, 1470
    map_x, map_y, map_w, map_h = 58, 86, 1040, 555
    legend_x, legend_y = 1130, 96
    lon_min, lon_max, lat_min, lat_max = common_extent
    scale = min(map_w / (lon_max - lon_min), map_h / (lat_max - lat_min))
    plot_w = (lon_max - lon_min) * scale
    plot_h = (lat_max - lat_min) * scale
    plot_x = map_x + (map_w - plot_w) / 2.0
    plot_y = map_y + (map_h - plot_h) / 2.0

    def px(lon: float) -> float:
        return plot_x + (lon - lon_min) * scale

    def py(lat: float) -> float:
        return plot_y + (lat_max - lat) * scale

    def rect_for(z: Zone, color: str, stroke_width: float = 2.4, dash: str = "") -> str:
        x1, x2 = px(z.lon_min), px(z.lon_max)
        y1, y2 = py(z.lat_max), py(z.lat_min)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        return (
            f'<rect x="{min(x1, x2):.1f}" y="{min(y1, y2):.1f}" '
            f'width="{abs(x2 - x1):.1f}" height="{abs(y2 - y1):.1f}" '
            f'fill="none" stroke="{color}" stroke-width="{stroke_width}"{dash_attr}/>'
        )

    main_summary = next((s for s in summaries if s.get("kind") == "main_history"), None)
    nohist_summary = next((s for s in summaries if s.get("kind") == "main_no_history"), None)
    counter_summaries = [s for s in summaries if str(s.get("kind", "")).startswith("counter_")]
    main_zones = [lookup[z.lower()] for z in plan.get("target_zones", []) if str(z).lower() in lookup]
    main_zone = macro_zone(main_zones) if main_zones else None
    plotted: list[tuple[str, Zone, str, dict | None]] = []
    if main_zone is not None:
        plotted.append(("Main", main_zone, "#d62728", main_summary))
    palette = ["#2f80ed", "#27ae60", "#9b51e0", "#f2994a", "#00a6a6"]
    for i, summary in enumerate(counter_summaries, 1):
        zs = variant_zones(summary, lookup)
        if not zs:
            continue
        z = macro_zone(zs) if len(zs) > 1 else zs[0]
        plotted.append((f"C{i}", z, palette[(i - 1) % len(palette)], summary))

    basemap = load_world_basemap()
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfcfd"/>',
        '<defs>',
        f'<clipPath id="overviewClip"><rect x="{map_x}" y="{map_y}" width="{map_w}" height="{map_h}"/></clipPath>',
        '</defs>',
        '<text x="58" y="38" font-size="25" font-weight="700" fill="#111827">Geographic Countercheck Overview</text>',
        '<text x="58" y="63" font-size="13" fill="#4b5563">Main target and proximity counter-zones in one fixed-scale frame.</text>',
        f'<rect x="{map_x}" y="{map_y}" width="{map_w}" height="{map_h}" fill="#eef6fb" stroke="#263238" stroke-width="1.2"/>',
    ]
    lon_step = max(5, int(math.ceil((lon_max - lon_min) / 7.0 / 5.0)) * 5)
    lat_step = max(5, int(math.ceil((lat_max - lat_min) / 6.0 / 5.0)) * 5)
    lon = math.ceil(lon_min / lon_step) * lon_step
    while lon <= lon_max + 1e-9:
        x = px(lon)
        pieces.append(f'<line x1="{x:.1f}" y1="{map_y}" x2="{x:.1f}" y2="{map_y + map_h}" stroke="#d7dde3" stroke-width="0.8"/>')
        pieces.append(f'<text x="{x:.1f}" y="{map_y + map_h + 19}" text-anchor="middle" font-size="10.5" fill="#52616b">{fmt_num(lon, 1)} lon</text>')
        lon += lon_step
    lat = math.ceil(lat_min / lat_step) * lat_step
    while lat <= lat_max + 1e-9:
        y = py(lat)
        pieces.append(f'<line x1="{map_x}" y1="{y:.1f}" x2="{map_x + map_w}" y2="{y:.1f}" stroke="#d7dde3" stroke-width="0.8"/>')
        pieces.append(f'<text x="{map_x - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="10.5" fill="#52616b">{fmt_num(lat, 1)} lat</text>')
        lat += lat_step
    pieces.append('<g clip-path="url(#overviewClip)">')
    pieces.extend(svg_geo_paths(
        basemap.get("coastlines", []), px, py,
        lon_min=lon_min, lon_max=lon_max, lat_min=lat_min, lat_max=lat_max,
        stroke="#667085", width=1.1, opacity=0.68, max_segments=260,
    ))
    pieces.extend(svg_geo_paths(
        basemap.get("countries", []), px, py,
        lon_min=lon_min, lon_max=lon_max, lat_min=lat_min, lat_max=lat_max,
        stroke="#98a2b3", width=0.6, opacity=0.45, max_segments=360,
    ))
    for label, zone, color, _summary in plotted:
        pieces.append(rect_for(zone, color, 3.0 if label == "Main" else 2.5, "" if label == "Main" else "7 4"))
        cx, cy = px(zone.lon_center), py(zone.lat_center)
        pieces.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="13" fill="#ffffff" stroke="{color}" stroke-width="2"/>')
        pieces.append(f'<text x="{cx:.1f}" y="{cy + 4:.1f}" text-anchor="middle" font-size="11" font-weight="700" fill="{color}">{escape_xml(label)}</text>')
    pieces.append("</g>")

    pieces.extend([
        f'<rect x="{legend_x}" y="{legend_y}" width="410" height="300" fill="#ffffff" stroke="#c7d0d9" stroke-width="1"/>',
        f'<text x="{legend_x + 18}" y="{legend_y + 30}" font-size="17" font-weight="700" fill="#111827">Overview legend</text>',
        f'<text x="{legend_x + 18}" y="{legend_y + 58}" font-size="12" fill="#263238">Scale: common extent; 1 deg lon = 1 deg lat = {scale:.2f}px.</text>',
        f'<text x="{legend_x + 18}" y="{legend_y + 78}" font-size="12" fill="#263238">Map includes main history target plus proximity counters.</text>',
        f'<text x="{legend_x + 18}" y="{legend_y + 98}" font-size="12" fill="#263238">Run selection: latest pulsar_train*_best_trials_* per variant.</text>',
    ])
    ly = legend_y + 130
    for label, zone, color, summary in plotted:
        pieces.append(f'<rect x="{legend_x + 20}" y="{ly - 12}" width="24" height="15" fill="none" stroke="{color}" stroke-width="2.5"/>')
        score = fmt_num(credibility_score(summary), 6)
        pieces.append(f'<text x="{legend_x + 54}" y="{ly}" font-size="12" fill="#263238">{escape_xml(label)}: {escape_xml(zone.zone_id)} cred={escape_xml(score)}</text>')
        ly += 24
    pieces.append(f'<text x="{legend_x + 18}" y="{legend_y + 272}" font-size="11" fill="#52616b">No-history main metrics are shown in the metric table, not as a separate rectangle.</text>')

    spec_y = 690
    table_x = 58
    table_w = 1484
    col_w = table_w / max(1, len(plotted))
    header_h = 34
    spec_h = 320
    metric_y = spec_y + spec_h + 44
    metric_h = 365
    pieces.append(f'<text x="{table_x}" y="{spec_y - 16}" font-size="19" font-weight="700" fill="#111827">Zone specification table</text>')
    pieces.append(f'<rect x="{table_x}" y="{spec_y}" width="{table_w}" height="{spec_h}" fill="#ffffff" stroke="#c7d0d9" stroke-width="1"/>')
    pieces.append(f'<line x1="{table_x}" y1="{spec_y + header_h}" x2="{table_x + table_w}" y2="{spec_y + header_h}" stroke="#c7d0d9"/>')
    for i, (label, zone, color, summary) in enumerate(plotted):
        x = table_x + i * col_w
        if i:
            pieces.append(f'<line x1="{x:.1f}" y1="{spec_y}" x2="{x:.1f}" y2="{spec_y + spec_h}" stroke="#e1e7ef"/>')
        pieces.append(f'<rect x="{x:.1f}" y="{spec_y}" width="{col_w:.1f}" height="{header_h}" fill="#f7f9fc"/>')
        pieces.append(f'<text x="{x + 10:.1f}" y="{spec_y + 22}" font-size="13" font-weight="700" fill="{color}">{escape_xml(label)} - {escape_xml(zone.zone_id)}</text>')
        segs = []
        for item in (summary or {}).get("validation_segments", []):
            try:
                segs.append((date.fromisoformat(item["start"]), date.fromisoformat(item["end"])))
            except Exception:
                pass
        zstats = zone_summary_for_map(zone, events, segs)
        run_dir_str = (summary or {}).get('latest_run_dir')
        if run_dir_str:
            rp = Path(run_dir_str)
            folder_part = f"folder: {rp.parent}"
            name_part = f"run name: {rp.name}"
        else:
            folder_part = "folder: none"
            name_part = "run name: none"
        lines = [
            f"name: {zone.name or zone.zone_id}",
            folder_part,
            name_part,
            f"lat: {fmt_num(zone.lat_min)}..{fmt_num(zone.lat_max)}",
            f"lon: {fmt_num(zone.lon_min)}..{fmt_num(zone.lon_max)}",
            f"depth: {zone.depth_min or '-inf'}..{zone.depth_max or '+inf'} km",
            f"events: {zstats['event_count']} hist={zstats['historical_count']} val={zstats['validation_count']}",
            f"time: {zstats['first_event'] or ''}..{zstats['last_event'] or ''}",
        ]
        ty = spec_y + header_h + 22
        for line in lines:
            wrapped, ty = svg_wrapped_text(line, x + 10, ty, int(col_w / 7.2), size=11.2, step=15, max_lines=4)
            pieces.extend(wrapped)
            ty += 1

    pieces.append(f'<text x="{table_x}" y="{metric_y - 16}" font-size="19" font-weight="700" fill="#111827">Metric comparison table</text>')
    pieces.append(f'<rect x="{table_x}" y="{metric_y}" width="{table_w}" height="{metric_h}" fill="#ffffff" stroke="#c7d0d9" stroke-width="1"/>')
    pieces.append(f'<line x1="{table_x}" y1="{metric_y + header_h}" x2="{table_x + table_w}" y2="{metric_y + header_h}" stroke="#c7d0d9"/>')
    for i, (label, zone, color, summary) in enumerate(plotted):
        x = table_x + i * col_w
        if i:
            pieces.append(f'<line x1="{x:.1f}" y1="{metric_y}" x2="{x:.1f}" y2="{metric_y + metric_h}" stroke="#e1e7ef"/>')
        pieces.append(f'<rect x="{x:.1f}" y="{metric_y}" width="{col_w:.1f}" height="{header_h}" fill="#f7f9fc"/>')
        pieces.append(f'<text x="{x + 10:.1f}" y="{metric_y + 22}" font-size="13" font-weight="700" fill="{color}">{escape_xml(label)} metrics</text>')
        blocks = [metric_text(summary, "History")]
        if label == "Main" and nohist_summary is not None:
            blocks.append(metric_text(nohist_summary, "No history"))
        ty = metric_y + header_h + 21
        for bidx, block in enumerate(blocks):
            if bidx:
                pieces.append(f'<line x1="{x + 10:.1f}" y1="{ty - 8:.1f}" x2="{x + col_w - 10:.1f}" y2="{ty - 8:.1f}" stroke="#e5e7eb"/>')
            for j, line in enumerate(block):
                weight = "700" if j == 0 else ""
                wrapped, ty = svg_wrapped_text(line, x + 10, ty, int(col_w / 7.0), size=11.3, step=15, max_lines=2, weight=weight)
                pieces.extend(wrapped)
            ty += 8
        chart_y = metric_y + metric_h - 112
        chart_h = 92
        append_forecast_sparkline(
            pieces,
            x=x + 10,
            y=chart_y,
            w=col_w - 20,
            h=chart_h,
            summary=summary,
            color=color,
            comparison=nohist_summary if label == "Main" else None,
        )
    pieces.append("</svg>")
    path.write_text("\n".join(pieces) + "\n")
    return {"svg": str(path), "scale_px_per_degree": round(scale, 3), "columns": [item[0] for item in plotted]}


def generate_variant_maps(plan: dict, summaries: list[dict], plan_path: Path) -> dict:
    zones = read_zones(Path(plan["zones_csv"]))
    lookup = zone_lookup(zones)
    events = read_events(Path(plan["src_events"]), float(plan.get("min_mag", 0.0)))
    main_zs = [lookup[z.lower()] for z in plan.get("target_zones", []) if z.lower() in lookup]
    main_zone = macro_zone(main_zs) if main_zs else None
    all_reference = []
    for zid in list(plan.get("target_zones", [])) + list(plan.get("counter_zones", [])):
        z = lookup.get(str(zid).lower())
        if z is not None:
            all_reference.append(z)
    extent_lons: list[float] = []
    extent_lats: list[float] = []
    for ref in all_reference:
        extent_lons.extend([ref.lon_min, ref.lon_max])
        extent_lats.extend([ref.lat_min, ref.lat_max])
        for ev in events:
            if zone_contains_event(ref, ev):
                extent_lons.append(ev.longitude)
                extent_lats.append(ev.latitude)
    if not extent_lons or not extent_lats:
        extent_lons = [-180.0, 180.0]
        extent_lats = [-90.0, 90.0]
    lon_min, lon_max = min(extent_lons), max(extent_lons)
    lat_min, lat_max = min(extent_lats), max(extent_lats)
    lon_pad = max(3.0, (lon_max - lon_min) * 0.12)
    lat_pad = max(3.0, (lat_max - lat_min) * 0.12)
    common_extent = (
        max(-180.0, lon_min - lon_pad),
        min(180.0, lon_max + lon_pad),
        max(-90.0, lat_min - lat_pad),
        min(90.0, lat_max + lat_pad),
    )
    map_dir = plan_path.with_name("maps")
    from artifacts import get_pipeline_serial
    serial_num = plan.get("serial_number") or get_pipeline_serial()
    for s in summaries:
        zs = variant_zones(s, lookup)
        if not zs:
            continue
        zone = macro_zone(zs) if len(zs) > 1 else zs[0]
        slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{s['kind']}_{s['target_zones']}").strip("_")
        svg_path = map_dir / f"{slug}_{serial_num}.svg"
        csv_path = map_dir / f"{slug}_{serial_num}_events.csv"
        s["map"] = write_variant_map_svg(
            svg_path,
            csv_path,
            variant=s,
            zone=zone,
            main_zone=main_zone,
            events=events,
            plan=plan,
            all_reference_zones=all_reference,
            fixed_extent=common_extent,
        )
    overview = write_overview_map_svg(
        map_dir / f"geographic_countercheck_overview_{serial_num}.svg",
        plan=plan,
        summaries=summaries,
        zones=zones,
        lookup=lookup,
        events=events,
        common_extent=common_extent,
    )
    try:
        generic_path = map_dir / "geographic_countercheck_overview.svg"
        generic_path.write_text(Path(overview["svg"]).read_text())
    except Exception:
        pass
    return overview


def rel_md(path: str | Path, base: Path) -> str:
    try:
        return os.path.relpath(str(path), start=str(base.parent))
    except Exception:
        return str(path)


def feature_category_lines(summaries: list[dict], plan: dict) -> list[str]:
    main = next((s for s in summaries if s.get("kind") == "main_history"), summaries[0] if summaries else {})
    target = main.get("target_report") or {}
    hist = main.get("history_manifest") or {}
    region = hist.get("target_region") or {}
    added = hist.get("added_columns") or []
    stitch_count = len([c for c in added if str(c).startswith("tt_stitch_")])
    tt_astro_count = len([c for c in added if str(c).startswith("tt_astro_")])
    tt_seis_count = len([c for c in added if str(c).startswith("tt_seis_")])
    return [
        "## Feature categories used",
        "",
        "- Binary event target: generated from the selected source column, normally `mag`, with "
        f"threshold `{plan.get('binary_threshold')}` and operator `>=`.",
        "- Core seismic columns: magnitude, depth, latitude and longitude are retained in the master for "
        "target/filter/history construction, then skipped as direct training features when configured.",
        "- Astronomical ephemerides: compact numeric body fields from nasaDb/JPL, including apparent/ecliptic "
        "position and distance/rate categories.",
        "- Horizontal seismic history: previous-event ribbon fields such as prior-event availability, delta days, "
        "magnitude, depth and location.",
        "- Horizontal astro history: compact time-shifted body fields for selected bodies "
        f"`{', '.join(hist.get('astro_bodies', [])) or 'not enabled'}` and fields "
        f"`{', '.join(hist.get('astro_fields', [])) or 'not enabled'}`.",
        "- Stitch features: present-vs-ribbon comparison fields that summarize the relation between current and "
        f"historical astronomical states; count `{stitch_count}`.",
        "- Region and row selection: row filter "
        f"`{target.get('row_filter', 'unknown')}`, target zones `{target.get('target_zones', plan.get('target_zones'))}`, "
        f"out-of-region mode `{target.get('out_of_region_mode', 'unknown')}`.",
        "- Feature volume: training feature count reported by target selection "
        f"`{target.get('feature_count', 'unknown')}`; horizontal added columns "
        f"`{len(added)}` (`tt_seis={tt_seis_count}`, `tt_astro={tt_astro_count}`, `tt_stitch={stitch_count}`).",
        "- Target-region resolved rows: "
        f"`kept={region.get('kept_rows', 'unknown')}`, `dropped={region.get('dropped_rows', 'unknown')}`.",
        "",
    ]


def make_report(args: argparse.Namespace) -> None:
    plan_path = Path(args.plan_json)
    plan = json.loads(plan_path.read_text())
    summaries = [summarize_variant(v) for v in plan["variants"]]
    annotate_peak_deltas(summaries)
    overview_map = generate_variant_maps(plan, summaries, plan_path)
    grade, grade_info = grade_report(summaries)

    out_json = Path(args.output_json) if args.output_json else plan_path.with_name("countercheck_report.json")
    out_md = Path(args.output_md) if args.output_md else plan_path.with_name("countercheck_report.md")
    payload = {"plan": plan, "grade": grade, "grade_info": grade_info, "overview_map": overview_map, "variants": summaries}
    out_json.write_text(json.dumps(payload, indent=2) + "\n")

    lines = [
        "# Geographic Countercheck Report",
        "",
        f"- Grade: `{grade}`",
        "- Run selection: `latest pulsar_train*_best_trials_* per variant`; older subruns in the same variant folders are not aggregated into these maps.",
        f"- Score policy: `{grade_info.get('score_policy')}`",
        f"- Main score: `{grade_info.get('main_score')}`",
        f"- Main fused/generalization: `{grade_info.get('main_fused_score')}` / `{grade_info.get('main_generalization_score')}`",
        f"- No-history score: `{grade_info.get('no_history_score')}`",
        f"- No-history fused/generalization: `{grade_info.get('no_history_fused_score')}` / `{grade_info.get('no_history_generalization_score')}`",
        f"- Horizontal gain: `{grade_info.get('horizontal_gain')}`",
        f"- Max counter score: `{grade_info.get('max_counter_score')}`",
        f"- Geographic margin: `{grade_info.get('geographic_margin')}`",
        f"- No-history stronger than history: `{grade_info.get('no_history_stronger_than_history')}`",
        f"- Counter stronger than main: `{grade_info.get('counter_stronger_than_main')}`",
        f"- Strongest counter: `{grade_info.get('strongest_counter_kind')}` / `{grade_info.get('strongest_counter_zones')}`",
        f"- Strongest counter peak delta vs main: `{grade_info.get('strongest_counter_peak_delta_days_vs_main')}` days",
        f"- Overview map: [SVG]({rel_md(overview_map.get('svg', ''), out_md)})",
        "",
        "| kind | zones | history | credibility | generalization | best overall | fused score | peak | delta vs main | consensus | map |",
        "|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|",
    ]
    for s in summaries:
        best = s.get("best", {})
        fusion = s.get("fusion", {})
        map_info = s.get("map") or {}
        map_link = f"[SVG]({rel_md(map_info.get('svg', ''), out_md)})" if map_info.get("svg") else ""
        lines.append(
            "| {kind} | {zones} | {history} | {cred} | {gen} | {best} | {fused} | {peak} | {delta} | {consensus} | {map_link} |".format(
                kind=s["kind"],
                zones=s["target_zones"],
                history=s["history"],
                cred=fmt_num(credibility_score(s), 6),
                gen=fmt_num(best.get("best_generalization_score"), 6),
                best=best.get("best_overall", ""),
                fused=fusion.get("fused_score", ""),
                peak=f"{fusion.get('selected_date', '')}->{fusion.get('window_end', '')}",
                delta=s.get("peak_delta_days_vs_main", ""),
                consensus=fusion.get("consensus_fraction", ""),
                map_link=map_link,
            )
        )
    lines.extend([
        "",
        "## Geographic Evidence Maps",
        "",
        "Each SVG map is a diagnostic equirectangular plot. It shows the active target/counter rectangle, "
        "the main target rectangle when different, blue historical in-zone events, yellow validation-window "
        "events, and the exact lat/lon/depth/time filters used for that variant.",
        "",
        "| kind | events | historical blue | validation yellow | validation windows | event CSV |",
        "|---|---:|---:|---:|---|---|",
    ])
    for s in summaries:
        m = s.get("map") or {}
        windows = "; ".join(f"{w.get('start')}->{w.get('end')}" for w in m.get("validation_windows", []))
        event_csv = f"[CSV]({rel_md(m.get('csv', ''), out_md)})" if m.get("csv") else ""
        lines.append(
            f"| {s['kind']} | {m.get('event_count', '')} | {m.get('historical_count', '')} | "
            f"{m.get('validation_count', '')} | {windows or ''} | {event_csv} |"
        )
    lines.extend([""])
    lines.extend(feature_category_lines(summaries, plan))
    lines.extend([
        "## Interpretation",
        "",
        "- `credibility` is the score used for the countercheck grade; when possible it blends forecast fusion with trial generalization metrics.",
        "- `horizontal_gain` compares main horizontal-history vs same zone without horizontal history.",
        "- `geographic_margin` compares main target zone vs the strongest nearby counter-zone.",
        "- In proximity mode, counter-zone peaks close to the main peak are possible false positives unless a real nearby event exists.",
        "- A strong result should keep a high main score, positive horizontal gain, positive geographic margin, and weak nearby counters.",
    ])
    out_md.write_text("\n".join(lines) + "\n")
    print(f"[countercheck] report json: {out_json}")
    print(f"[countercheck] report md:   {out_md}")
    print(f"[countercheck] grade:       {grade}")


def main() -> None:
    args = parse_args()
    if args.cmd == "plan":
        make_plan(args)
    elif args.cmd == "report":
        make_report(args)


if __name__ == "__main__":
    main()
