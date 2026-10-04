#!/usr/bin/env python3
"""Prepare a fixed-cadence V14 master with optional non-Japan hard negatives."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


META_SOURCE = {"date", "mag", "depth", "latitude", "longitude"}
TIMING_PREFIX = [
    "date",
    "slot_end_inclusive",
    "timing_target",
    "event_mag",
    "event_latitude",
    "event_longitude",
    "event_id",
    "is_forecast",
    "stress_target_m70",
    "stress_target_m68",
    "stress_target_m65",
    "complete_at_catalog_snapshot",
    "hard_negative_control",
    "hard_negative_scope",
    "hard_negative_event_ids",
    "hard_negative_places",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_date(value: str) -> datetime:
    return datetime.strptime(value[:10], "%Y-%m-%d")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def format_date(value: datetime) -> str:
    return f"{value.year:04d}-{value.month:02d}-{value.day:02d}"


def optional_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def parse_names(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def jpl_vector_columns(columns: list[str], body: str) -> list[str]:
    """Resolve one start-of-slot JPL x/y/z vector without fixed column names."""
    resolved: list[str] = []
    for coordinate in ("x", "y", "z"):
        matches = [
            column
            for column in columns
            if f"body:{body}|" in column
            and f"|eph:{coordinate}|" in column
            and ("|op:val" in column or "|op:" not in column)
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Expected one {body} {coordinate} start-value feature; found {matches}"
            )
        resolved.append(matches[0])
    return resolved


def grid_start(date: datetime, anchor: datetime, step_days: int) -> datetime:
    offset = (date - anchor).days // step_days
    return anchor + timedelta(days=offset * step_days)


def load_catalog(
    path: Path, anchor: datetime, step_days: int
) -> tuple[dict[datetime, list[dict[str, Any]]], list[dict[str, Any]]]:
    bins: dict[datetime, list[dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            event_time = parse_time(str(row["time"]))
            start = grid_start(event_time, anchor, step_days)
            normalized = {
                **row,
                "_event_time": event_time,
                "_slot_start": start,
                "_mag": optional_float(row.get("mag")),
            }
            bins.setdefault(start, []).append(normalized)
            rows.append(normalized)
    return bins, rows


def strongest_event(events: list[dict[str, Any]]) -> dict[str, Any]:
    return max(events, key=lambda row: (float(row["_mag"]), -row["_event_time"].timestamp()))


def load_world_non_japan_events(
    path: Path,
    anchor: datetime,
    step_days: int,
    minimum_magnitude: float,
    bounds: tuple[float, float, float, float],
) -> list[dict[str, Any]]:
    """Load worldwide USGS events outside the configured Japan rectangle."""
    lat_min, lat_max, lon_min, lon_max = bounds
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            event_time = parse_time(str(row.get("time") or ""))
            magnitude = optional_float(row.get("mag"), default=float("nan"))
            latitude = optional_float(row.get("latitude"), default=float("nan"))
            longitude = optional_float(row.get("longitude"), default=float("nan"))
            if not all(math.isfinite(value) for value in (magnitude, latitude, longitude)):
                continue
            if magnitude < minimum_magnitude:
                continue
            inside_japan = (
                lat_min <= latitude <= lat_max and lon_min <= longitude <= lon_max
            )
            if inside_japan:
                continue
            rows.append(
                {
                    "event_time": event_time,
                    "slot_start": grid_start(event_time, anchor, step_days),
                    "event_id": str(row.get("id") or ""),
                    "place": str(row.get("place") or "outside Japan"),
                    "magnitude": magnitude,
                    "latitude": latitude,
                    "longitude": longitude,
                    "depth": optional_float(row.get("depth"), default=float("nan")),
                }
            )
    return rows


def select_hard_negative_controls(
    events: list[dict[str, Any]],
    dates: list[datetime],
    positive_slots: set[datetime],
    validation_slots: list[datetime],
    validation_radius: int,
    validation_per_fold: int,
    training_count: int,
    training_minimum_magnitude: float,
    validation_minimum_magnitude: float,
    forecast_start: datetime,
    seed: int,
) -> tuple[dict[datetime, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Select reproducible training and outer-window non-Japan negatives.

    Selection changes which already-negative time bins are guaranteed to survive
    compaction; it never duplicates astronomical rows and never changes a Japan
    positive into a negative.
    """
    index_by_date = {date: index for index, date in enumerate(dates)}
    candidates = [
        row
        for row in events
        if row["slot_start"] in index_by_date
        and row["slot_start"] < forecast_start
        and row["slot_start"] not in positive_slots
    ]
    rng = np.random.default_rng(seed)
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    validation_indices = [index_by_date[slot] for slot in validation_slots]

    for fold, event_index in enumerate(validation_indices, start=1):
        pool = [
            row
            for row in candidates
            if row["magnitude"] >= validation_minimum_magnitude
            if abs(index_by_date[row["slot_start"]] - event_index) <= validation_radius
            and row["event_id"] not in selected_ids
        ]
        if len(pool) < validation_per_fold:
            raise RuntimeError(
                f"Only {len(pool)} non-Japan controls available for validation fold {fold}; "
                f"requested {validation_per_fold} within radius {validation_radius}"
            )
        chosen = rng.choice(len(pool), size=validation_per_fold, replace=False)
        for position in np.atleast_1d(chosen):
            row = {**pool[int(position)], "scope": f"validation_fold_{fold}"}
            selected.append(row)
            selected_ids.add(row["event_id"])

    earliest_validation_window = min(validation_indices) - validation_radius
    training_pool = [
        row
        for row in candidates
        if row["magnitude"] >= training_minimum_magnitude
        if index_by_date[row["slot_start"]] < earliest_validation_window
        and row["event_id"] not in selected_ids
    ]
    training_count = min(max(0, training_count), len(training_pool))
    if training_count:
        chosen = rng.choice(len(training_pool), size=training_count, replace=False)
        for position in np.atleast_1d(chosen):
            row = {**training_pool[int(position)], "scope": "training"}
            selected.append(row)
            selected_ids.add(row["event_id"])

    by_slot: dict[datetime, list[dict[str, Any]]] = {}
    for row in selected:
        by_slot.setdefault(row["slot_start"], []).append(row)
    return by_slot, selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-master", required=True, type=Path)
    parser.add_argument("--catalog-csv", required=True, type=Path)
    parser.add_argument("--output-master", required=True, type=Path)
    parser.add_argument("--output-safe-features", required=True, type=Path)
    parser.add_argument("--output-selection-json", required=True, type=Path)
    parser.add_argument("--output-bin-audit-csv", required=True, type=Path)
    parser.add_argument("--world-events-csv", type=Path)
    parser.add_argument("--output-hard-negative-audit-csv", type=Path)
    parser.add_argument("--output-hard-negative-audit-json", type=Path)
    parser.add_argument(
        "--hard-negative-mode",
        choices=("off", "world_non_japan"),
        default="off",
    )
    parser.add_argument("--hard-negative-minimum-magnitude", type=float, default=7.9)
    parser.add_argument(
        "--hard-negative-training-minimum-magnitude",
        type=float,
        default=None,
        help="Training-control floor; defaults to --hard-negative-minimum-magnitude.",
    )
    parser.add_argument(
        "--hard-negative-validation-minimum-magnitude",
        type=float,
        default=None,
        help="Validation-control floor; defaults to --hard-negative-minimum-magnitude.",
    )
    parser.add_argument("--hard-negative-training-count", type=int, default=24)
    parser.add_argument("--hard-negative-validation-per-fold", type=int, default=1)
    parser.add_argument("--hard-negative-validation-radius-slots", type=int, default=3)
    parser.add_argument("--hard-negative-seed", type=int, default=581403)
    parser.add_argument(
        "--outer-validation-slots",
        default="",
        help=(
            "Optional comma-separated exact positive slot starts. These same "
            "folds receive validation-local hard-negative controls."
        ),
    )
    parser.add_argument("--japan-latitude-min", type=float, default=28.0)
    parser.add_argument("--japan-latitude-max", type=float, default=47.0)
    parser.add_argument("--japan-longitude-min", type=float, default=128.0)
    parser.add_argument("--japan-longitude-max", type=float, default=149.5)
    parser.add_argument("--anchor-date", default="2026-01-01")
    parser.add_argument("--forecast-start", default="2026-01-01")
    parser.add_argument("--forecast-end", default="2028-12-31")
    parser.add_argument("--step-days", type=int, default=60)
    parser.add_argument(
        "--calendar-features",
        default="doy_sin,doy_cos",
        help=(
            "Comma-separated start-of-slot controls: month, month_sin, "
            "month_cos, doy_sin, doy_cos, moon_phase_fraction, "
            "moon_elongation_cos."
        ),
    )
    parser.add_argument(
        "--calendar-system",
        choices=("proleptic_gregorian",),
        default="proleptic_gregorian",
        help="Explicit civil-calendar convention used by Python date arithmetic.",
    )
    parser.add_argument(
        "--catalog-outside-master-policy",
        choices=("error", "drop"),
        default="error",
        help=(
            "Policy for catalogue events whose aligned slot is outside the "
            "astronomical master. The default is fail-closed; 'drop' records "
            "every omitted event in the master-selection audit."
        ),
    )
    parser.add_argument(
        "--japan-training-minimum-magnitude",
        type=float,
        default=0.0,
        help="Japan-event target floor outside explicitly configured holdout slots.",
    )
    parser.add_argument(
        "--japan-validation-minimum-magnitude",
        type=float,
        default=None,
        help="Allowed Japan holdout floor; defaults to the training target floor.",
    )
    args = parser.parse_args()

    japan_training_floor = float(args.japan_training_minimum_magnitude)
    japan_validation_floor = float(
        args.japan_validation_minimum_magnitude
        if args.japan_validation_minimum_magnitude is not None
        else japan_training_floor
    )
    hard_negative_training_floor = float(
        args.hard_negative_training_minimum_magnitude
        if args.hard_negative_training_minimum_magnitude is not None
        else args.hard_negative_minimum_magnitude
    )
    hard_negative_validation_floor = float(
        args.hard_negative_validation_minimum_magnitude
        if args.hard_negative_validation_minimum_magnitude is not None
        else args.hard_negative_minimum_magnitude
    )

    anchor = parse_date(args.anchor_date)
    forecast_start = parse_date(args.forecast_start)
    forecast_end = parse_date(args.forecast_end)
    source = pd.read_csv(args.source_master, low_memory=False)
    dates = [parse_date(str(value)) for value in source["date"]]
    if any((right - left).days != args.step_days for left, right in zip(dates, dates[1:])):
        raise ValueError(f"Source master is not an exact {args.step_days}-day grid")
    if forecast_start not in set(dates):
        raise ValueError("Forecast start is not an exact master grid start")
    if dates[-1] + timedelta(days=args.step_days - 1) < forecast_end:
        raise ValueError("Master does not fully cover the requested forecast end")

    catalog_bins, catalog_rows = load_catalog(
        args.catalog_csv, anchor, args.step_days
    )
    master_date_set = set(dates)
    outside = [
        row for row in catalog_rows if row["_slot_start"] not in master_date_set
    ]
    if outside and args.catalog_outside_master_policy == "error":
        raise ValueError(f"{len(outside)} catalog events fall outside the master")
    outside_audit = [
        {
            "event_time": row["_event_time"].isoformat(),
            "slot_start": format_date(row["_slot_start"]),
            "event_id": str(row.get("event_id") or row.get("id") or ""),
            "event_name": str(row.get("event_name") or ""),
            "magnitude": float(row["_mag"]),
            "position": (
                "before_master"
                if row["_slot_start"] < dates[0]
                else "after_master"
            ),
        }
        for row in outside
    ]
    if outside:
        catalog_rows = [
            row for row in catalog_rows if row["_slot_start"] in master_date_set
        ]
        catalog_bins = {
            slot: rows
            for slot, rows in catalog_bins.items()
            if slot in master_date_set
        }

    training_positive_slot_dates = [
        date
        for date in dates
        if date < forecast_start
        and any(
            float(row["_mag"]) >= japan_training_floor
            for row in catalog_bins.get(date, [])
        )
    ]
    validation_eligible_slot_dates = [
        date
        for date in dates
        if date < forecast_start
        and any(
            float(row["_mag"]) >= japan_validation_floor
            for row in catalog_bins.get(date, [])
        )
    ]
    requested_validation_slots = [
        parse_date(value.strip())
        for value in args.outer_validation_slots.split(",")
        if value.strip()
    ]
    validation_slot_dates = (
        requested_validation_slots
        if requested_validation_slots
        else validation_eligible_slot_dates[-2:]
    )
    if (
        not validation_slot_dates
        or len(validation_slot_dates) != len(set(validation_slot_dates))
        or any(value not in validation_eligible_slot_dates for value in validation_slot_dates)
    ):
        raise RuntimeError(
            "Outer validation slots must be distinct historical positive bins"
        )
    positive_slot_dates = sorted(
        set(training_positive_slot_dates) | set(validation_slot_dates)
    )
    hard_negative_by_slot: dict[datetime, list[dict[str, Any]]] = {}
    hard_negative_rows: list[dict[str, Any]] = []
    if args.hard_negative_mode == "world_non_japan":
        if args.world_events_csv is None:
            raise ValueError("--world-events-csv is required in world_non_japan mode")
        world_events = load_world_non_japan_events(
            args.world_events_csv,
            anchor,
            args.step_days,
            min(hard_negative_training_floor, hard_negative_validation_floor),
            (
                args.japan_latitude_min,
                args.japan_latitude_max,
                args.japan_longitude_min,
                args.japan_longitude_max,
            ),
        )
        hard_negative_by_slot, hard_negative_rows = select_hard_negative_controls(
            world_events,
            dates,
            set(catalog_bins),
            validation_slot_dates,
            args.hard_negative_validation_radius_slots,
            args.hard_negative_validation_per_fold,
            args.hard_negative_training_count,
            hard_negative_training_floor,
            hard_negative_validation_floor,
            forecast_start,
            args.hard_negative_seed,
        )

    timing_rows: list[dict[str, Any]] = []
    bin_audit: list[dict[str, Any]] = []
    for date in dates:
        events = catalog_bins.get(date, [])
        controls = hard_negative_by_slot.get(date, [])
        is_forecast = date >= forecast_start
        positive = bool(events) and not is_forecast and (
            date in validation_slot_dates
            or any(float(row["_mag"]) >= japan_training_floor for row in events)
        )
        strongest = strongest_event(events) if events else None
        timing_rows.append(
            {
                "date": format_date(date),
                "slot_end_inclusive": format_date(
                    date + timedelta(days=args.step_days - 1)
                ),
                "timing_target": int(positive),
                "event_mag": float(strongest["_mag"]) if positive and strongest else 0.0,
                "event_latitude": (
                    optional_float(strongest.get("latitude"))
                    if positive and strongest
                    else 0.0
                ),
                "event_longitude": (
                    optional_float(strongest.get("longitude"))
                    if positive and strongest
                    else 0.0
                ),
                "event_id": (
                    str(strongest.get("event_id") or "")
                    if positive and strongest
                    else ""
                ),
                "is_forecast": int(is_forecast),
                "stress_target_m70": 0,
                "stress_target_m68": 0,
                "stress_target_m65": 0,
                "complete_at_catalog_snapshot": int(not is_forecast),
                "hard_negative_control": int(bool(controls) and not positive),
                "hard_negative_scope": ";".join(
                    sorted({str(row["scope"]) for row in controls})
                ),
                "hard_negative_event_ids": ";".join(
                    str(row["event_id"]) for row in controls
                ),
                "hard_negative_places": ";".join(
                    str(row["place"]) for row in controls
                ),
            }
        )
        if events:
            bin_audit.append(
                {
                    "slot_start": format_date(date),
                    "slot_end_inclusive": format_date(
                        date + timedelta(days=args.step_days - 1)
                    ),
                    "event_count": len(events),
                    "target": int(positive),
                    "maximum_magnitude": max(float(row["_mag"]) for row in events),
                    "event_dates": ";".join(format_date(row["_event_time"]) for row in events),
                    "event_ids": ";".join(str(row.get("event_id") or "") for row in events),
                    "sources": ";".join(str(row.get("source") or "") for row in events),
                }
            )

    astro_columns = [column for column in source.columns if column not in META_SOURCE]
    astro = source[astro_columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(astro.to_numpy(float)).all():
        raise ValueError("Non-finite astronomical value in source master")
    # Python datetime uses the proleptic Gregorian calendar and supports the
    # deep-history years that pandas' nanosecond Timestamp cannot represent.
    requested_calendar = parse_names(args.calendar_features)
    supported_calendar = {
        "month",
        "month_sin",
        "month_cos",
        "doy_sin",
        "doy_cos",
        "moon_phase_fraction",
        "moon_elongation_cos",
    }
    unknown_calendar = sorted(set(requested_calendar) - supported_calendar)
    if unknown_calendar:
        raise ValueError(f"Unsupported calendar features: {unknown_calendar}")
    day_of_year = np.asarray(
        [value.timetuple().tm_yday for value in dates], dtype=float
    )
    month = np.asarray([value.month for value in dates], dtype=float)
    if "month" in requested_calendar:
        astro["calendar_month"] = month
    if "month_sin" in requested_calendar:
        astro["calendar_month_sin"] = np.sin(2.0 * np.pi * (month - 1.0) / 12.0)
    if "month_cos" in requested_calendar:
        astro["calendar_month_cos"] = np.cos(2.0 * np.pi * (month - 1.0) / 12.0)
    if "doy_sin" in requested_calendar:
        astro["calendar_doy_sin"] = np.sin(2.0 * np.pi * day_of_year / 365.2425)
    if "doy_cos" in requested_calendar:
        astro["calendar_doy_cos"] = np.cos(2.0 * np.pi * day_of_year / 365.2425)
    moon_phase_requested = bool(
        {"moon_phase_fraction", "moon_elongation_cos"}
        & set(requested_calendar)
    )
    if moon_phase_requested:
        source_columns = list(astro.columns)
        sun_columns = jpl_vector_columns(source_columns, "sun")
        moon_columns = jpl_vector_columns(source_columns, "moon")
        sun_vector = astro[sun_columns].to_numpy(float)
        moon_vector = astro[moon_columns].to_numpy(float)
        denominator = np.linalg.norm(sun_vector, axis=1) * np.linalg.norm(
            moon_vector, axis=1
        )
        elongation_cos = np.divide(
            np.sum(sun_vector * moon_vector, axis=1),
            denominator,
            out=np.zeros(len(astro), dtype=float),
            where=denominator > 0,
        )
        elongation_cos = np.clip(elongation_cos, -1.0, 1.0)
        if "moon_elongation_cos" in requested_calendar:
            astro["moon_elongation_cos_at_slot_start"] = elongation_cos
        if "moon_phase_fraction" in requested_calendar:
            astro["moon_phase_fraction_at_slot_start"] = (
                1.0 - elongation_cos
            ) / 2.0
    feature_names = list(astro.columns)

    timing = pd.DataFrame(timing_rows)
    output = pd.concat(
        [timing[TIMING_PREFIX].reset_index(drop=True), astro.reset_index(drop=True)],
        axis=1,
    )
    output = output.loc[
        [date <= forecast_end for date in dates]
    ].reset_index(drop=True)
    validation_bins = [format_date(value) for value in validation_slot_dates]

    safe_payload = {
        "domain": "timing",
        "feature_count": len(feature_names),
        "indices": list(range(len(feature_names))),
        "features": feature_names,
        "minimum_feature_limit": 5,
        "protected_features": [],
        "shared_by_all_systems": True,
        "selection": (
            "all complete JPL start-of-slot features plus the configured calendar "
            "and Moon-phase controls "
            "enter intelligent ablation; target membership follows the configured "
            "training and validation magnitude floors"
        ),
    }
    selection = {
        "status": "COMPLETE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection_policy": (
            f"Japan training positives require M≥{japan_training_floor:g}; explicitly "
            f"configured outer holdouts may use M≥{japan_validation_floor:g}. Multiple "
            f"events may overlap in one {args.step_days}-day bin. Outer validation uses "
            + (
                "the explicitly configured distinct positive bins."
                if requested_validation_slots
                else "the latest two distinct positive bins."
            )
        ),
        "catalog_rows": len(catalog_rows),
        "catalog_outside_master": {
            "policy": args.catalog_outside_master_policy,
            "excluded_count": len(outside_audit),
            "excluded_events": outside_audit,
        },
        "magnitude_thresholds": {
            "japan_training": japan_training_floor,
            "japan_validation": japan_validation_floor,
        },
        "positive_bins": sum(row["timing_target"] for row in timing_rows),
        "collision_bins": sum(row["event_count"] > 1 for row in bin_audit),
        "validation_slots": validation_bins,
        "hard_negative_controls": {
            "mode": args.hard_negative_mode,
            "world_discovery_minimum_magnitude": min(
                hard_negative_training_floor, hard_negative_validation_floor
            ),
            "training_minimum_magnitude": hard_negative_training_floor,
            "validation_minimum_magnitude": hard_negative_validation_floor,
            "training_count_requested": args.hard_negative_training_count,
            "validation_per_fold": args.hard_negative_validation_per_fold,
            "validation_radius_slots": args.hard_negative_validation_radius_slots,
            "seed": args.hard_negative_seed,
            "selected_events": len(hard_negative_rows),
            "selected_bins": len(hard_negative_by_slot),
            "training_events": sum(row["scope"] == "training" for row in hard_negative_rows),
            "validation_events": sum(row["scope"].startswith("validation_fold_") for row in hard_negative_rows),
            "model_encoding": (
                "timing_target=0; event_mag/event_latitude/event_longitude remain zero; "
                "original USGS coordinates and magnitude exist only in the separate audit"
            ),
        },
        "selected": {
            "history_start_year": dates[0].year,
            "history_event_radius": None,
            "history_between_records": None,
            "validation_radius": args.hard_negative_validation_radius_slots,
            "feature_count": len(feature_names),
        },
        "grid": {
            "anchor_date": args.anchor_date,
            "interval_days": args.step_days,
            "forecast_grid_start": args.forecast_start,
            "forecast_end": args.forecast_end,
        },
        "calendar_contract": {
            "system": args.calendar_system,
            "requested_features": requested_calendar,
            "moon_phase_source": (
                "geocentric Sun-Moon start-vector elongation from the JPL master"
                if moon_phase_requested
                else "disabled"
            ),
            "all_master_dates_after_gregorian_reform": bool(
                min(dates) >= datetime(1582, 10, 15)
            ),
            "date_arithmetic": "Python proleptic Gregorian datetime",
        },
        "source": {
            "master": str(args.source_master),
            "master_sha256": sha256(args.source_master),
            "catalog": str(args.catalog_csv),
            "catalog_sha256": sha256(args.catalog_csv),
        },
        "output_master": {
            "path": str(args.output_master),
            "rows": len(output),
            "features": len(feature_names),
        },
    }

    for path in (
        args.output_master,
        args.output_safe_features,
        args.output_selection_json,
        args.output_bin_audit_csv,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output_master, index=False)
    safe_payload["output_master_sha256"] = sha256(args.output_master)
    args.output_safe_features.write_text(
        json.dumps(safe_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    selection["output_master"]["sha256"] = sha256(args.output_master)
    args.output_selection_json.write_text(
        json.dumps(selection, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    pd.DataFrame(bin_audit).to_csv(args.output_bin_audit_csv, index=False)
    if args.output_hard_negative_audit_csv is not None:
        args.output_hard_negative_audit_csv.parent.mkdir(parents=True, exist_ok=True)
        audit_rows = []
        for row in hard_negative_rows:
            audit_rows.append(
                {
                    "scope": row["scope"],
                    "event_time": row["event_time"].isoformat(),
                    "slot_start": format_date(row["slot_start"]),
                    "event_id": row["event_id"],
                    "place": row["place"],
                    "original_magnitude_audit_only": row["magnitude"],
                    "original_latitude_audit_only": row["latitude"],
                    "original_longitude_audit_only": row["longitude"],
                    "original_depth_audit_only": row["depth"],
                    "model_timing_target": 0,
                    "model_event_mag": 0,
                    "model_event_latitude": 0,
                    "model_event_longitude": 0,
                }
            )
        pd.DataFrame(audit_rows).to_csv(args.output_hard_negative_audit_csv, index=False)
    if args.output_hard_negative_audit_json is not None:
        args.output_hard_negative_audit_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_hard_negative_audit_json.write_text(
            json.dumps(selection["hard_negative_controls"], indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(selection, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
