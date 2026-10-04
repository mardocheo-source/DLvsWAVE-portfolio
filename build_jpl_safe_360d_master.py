#!/usr/bin/env python3
"""Build a 360-day Japan/Nankai master from an explicit JPL-safe body CSV.

The safe ephemerides CSV is treated as the contract for astronomical fields:
each row defines the Horizons target id and the recommended center.  Output
dates are period starts; seismic events are assigned to the left bin.

Implementation note for the next pass:
this script intentionally does not call astro-USGS2/nasaDb.py because that
pipeline currently uses Horizons.ephemerides(..., quantities=...), while this
historical annual master needs Horizons.vectors(...) Cartesian state vectors
with body/center pairs declared in the safe CSV.  A good future cleanup would
be adding a nasaDb.py mode such as --safe-vectors-csv/--vectors-mode and moving
this logic there, keeping this file as a small wrapper or test fixture.

Coverage note:
Horizons can expose different historical lower bounds per target.  Mars
reported no vectors before A.D. 1600-01-02 during the Japan/Nankai 1498 run.
Use --exclude-bodies mars to preserve the full 1498 history without Mars, or
start at 1600-01-02 to keep Mars.  Use --probe-only to test all selected bodies
before launching a long master build.  Use --auto-clip vertical to remove
unavailable bodies automatically, or --auto-clip horizontal to shorten the date
range automatically when Horizons reports a parsable date bound.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import time
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


SEISMIC_COLUMNS = ("date", "mag", "depth", "latitude", "longitude")
VECTOR_COLUMNS = ("x", "y", "z", "vx", "vy", "vz", "lighttime", "range", "range_rate")
REQUIRED_VECTOR_COLUMNS = ("x", "y", "z", "vx", "vy", "vz")
JULIAN_DAY_TOLERANCE = 1e-6
MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


@dataclass(frozen=True)
class BodySpec:
    name: str
    command: str
    body_type: str
    center: str
    coordinates: str
    note: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build an annual/360d master using explicit JPL Horizons vector definitions."
    )
    p.add_argument("--safe-ephemerides-csv", required=True)
    p.add_argument("--events-csv")
    p.add_argument("--output-float-csv")
    p.add_argument("--manifest-json")
    p.add_argument("--start-date", default="1498-01-01")
    p.add_argument("--end-date", default="2035-12-31")
    p.add_argument("--step-days", type=int, default=360)
    p.add_argument(
        "--time-travel-mode",
        choices=("none", "constant-days", "constant-years", "geometric-archimede", "fibonacci-gold"),
        default="none",
        help="Shift astronomical Horizons epochs backward while keeping seismic row dates unchanged.",
    )
    p.add_argument(
        "--time-travel-value",
        type=float,
        default=0.0,
        help="Time-travel displacement value; interpreted according to --time-travel-mode.",
    )
    p.add_argument(
        "--moon-center",
        choices=("ssb", "earth"),
        default="ssb",
        help="For the ambiguous Moon row, use common SSB frame @0 or geocentric @399.",
    )
    p.add_argument("--refplane", default="earth", help="Horizons vectors refplane; 'earth' is J2000 equator.")
    p.add_argument("--chunk-size", type=int, default=80)
    p.add_argument("--sleep-seconds", type=float, default=0.5)
    p.add_argument("--max-retries", type=int, default=3)
    p.add_argument(
        "--exclude-bodies",
        default="",
        help="Comma-separated safe CSV body_name values to exclude, e.g. mars,neptune_system_barycenter.",
    )
    p.add_argument(
        "--on-body-error",
        choices=("fail", "skip"),
        default="fail",
        help="Fail on a JPL body error, or skip that body and continue writing the master.",
    )
    p.add_argument(
        "--auto-clip",
        choices=("none", "vertical", "horizontal"),
        default="none",
        help=(
            "Automatic preflight clipping. vertical drops unavailable bodies; "
            "horizontal clips date bounds when Horizons reports parsable date limits."
        ),
    )
    p.add_argument(
        "--probe-only",
        action="store_true",
        help="Only test Horizons vector access for all selected bodies over start/end epochs.",
    )
    return p.parse_args()


def parse_date(value: str) -> datetime:
    return datetime.strptime(value[:10], "%Y-%m-%d")


def format_date(value: datetime) -> str:
    """Return an ISO-like date with four-digit years, including pre-1000 dates."""
    return f"{value.year:04d}-{value.month:02d}-{value.day:02d}"


def parse_horizons_date(year: str, month: str, day: str) -> datetime:
    mon = MONTHS[month[:3].upper()]
    return datetime(int(year), mon, int(day))


def date_to_julian_day(dt: datetime) -> float:
    """Proleptic Gregorian Julian day at UTC midnight."""
    y = dt.year
    m = dt.month
    d = dt.day + (dt.hour + (dt.minute + dt.second / 60.0) / 60.0) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5


def period_starts(start: datetime, end: datetime, step_days: int) -> list[datetime]:
    out: list[datetime] = []
    cur = start
    delta = timedelta(days=step_days)
    while cur <= end:
        out.append(cur)
        cur += delta
    if not out:
        raise ValueError("No period starts generated; check start/end dates.")
    return out


def time_travel_offset_days(mode: str, value: float) -> float:
    """Return the backward astronomical epoch displacement in days."""
    if mode == "none":
        return 0.0
    if value < 0:
        raise ValueError("--time-travel-value must be non-negative because displacement is backward-only.")
    if mode == "constant-days":
        return value
    if mode == "constant-years":
        return value * 365.25
    if mode == "geometric-archimede":
        return value * math.pi
    if mode == "fibonacci-gold":
        phi = (1 + math.sqrt(5)) / 2
        return value * phi
    raise ValueError(f"Unsupported time-travel mode: {mode}")


def build_astro_epochs_jd(starts: list[datetime], mode: str, value: float) -> list[float]:
    """Map real seismic period starts to shifted Horizons Julian Day epochs."""
    days_back = time_travel_offset_days(mode, value)
    return [date_to_julian_day(dt) - days_back for dt in starts]


def time_travel_date_policy(step_days: int) -> dict[str, str]:
    return {
        "row_date_policy": (
            f"CSV date values remain real timeline period starts for {step_days}-day "
            "forecast/training periods."
        ),
        "astronomy_feature_policy": (
            "Only astronomical feature values are displaced backward for Horizons "
            "requests; shifted source dates are never written into the CSV date column."
        ),
    }


def probe_endpoint_epochs(epochs_jd: list[float]) -> list[float]:
    """Return first/last probe epochs without duplicating single-period requests."""
    if not epochs_jd:
        raise ValueError("No epochs available for Horizons probe.")
    if len(epochs_jd) == 1 or epochs_jd[0] == epochs_jd[-1]:
        return [epochs_jd[0]]
    return [epochs_jd[0], epochs_jd[-1]]


def resolve_center(raw_center: str, body_name: str, moon_center: str) -> str:
    text = (raw_center or "").strip()
    if body_name == "moon":
        return "@399" if moon_center == "earth" else "@0"
    if text.startswith("@"):
        return text.split()[0]
    raise ValueError(f"Cannot resolve Horizons center for {body_name!r}: {raw_center!r}")


def read_body_specs(path: Path, moon_center: str) -> list[BodySpec]:
    specs: list[BodySpec] = []
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        required = {"body_name", "horizons_command", "body_type", "recommended_center", "recommended_coordinates"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing columns in safe ephemerides CSV: {sorted(missing)}")
        for row in reader:
            name = (row["body_name"] or "").strip()
            command = (row["horizons_command"] or "").strip()
            if not name or not command:
                continue
            specs.append(
                BodySpec(
                    name=name,
                    command=command,
                    body_type=(row.get("body_type") or "").strip(),
                    center=resolve_center(row.get("recommended_center", ""), name, moon_center),
                    coordinates=(row.get("recommended_coordinates") or "").strip(),
                    note=(row.get("note") or "").strip(),
                )
            )
    if not specs:
        raise ValueError(f"No body specs found in {path}")
    return specs


def parse_exclude_bodies(raw: str) -> set[str]:
    return {part.strip() for part in str(raw or "").split(",") if part.strip()}


def filter_specs(specs: list[BodySpec], excluded: set[str]) -> tuple[list[BodySpec], list[dict[str, str]]]:
    kept: list[BodySpec] = []
    skipped: list[dict[str, str]] = []
    for spec in specs:
        if spec.name in excluded:
            skipped.append(
                {
                    "body_name": spec.name,
                    "horizons_command": spec.command,
                    "center_used": spec.center,
                    "reason": "excluded_by_user",
                }
            )
        else:
            kept.append(spec)
    return kept, skipped


def safe_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return None
        return out
    except Exception:
        return None


def assign_events(events_csv: Path, starts: list[datetime], step_days: int) -> tuple[list[dict[str, float]], dict]:
    defaults = {"mag": 0.0, "depth": 0.0, "latitude": 0.0, "longitude": 0.0}
    values_for_defaults = {k: [] for k in ("depth", "latitude", "longitude")}
    rows = [dict(defaults) for _ in starts]
    assigned = 0
    skipped = 0
    collisions = 0
    kept_events: list[dict[str, object]] = []
    last_end = starts[-1] + timedelta(days=step_days)

    with events_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        for event in reader:
            try:
                event_dt = parse_date(event.get("time", ""))
            except Exception:
                skipped += 1
                continue
            if event_dt < starts[0] or event_dt >= last_end:
                skipped += 1
                continue
            mag = safe_float(event.get("mag"))
            if mag is None:
                skipped += 1
                continue
            depth = safe_float(event.get("depth"))
            lat = safe_float(event.get("latitude"))
            lon = safe_float(event.get("longitude"))
            if depth is not None:
                values_for_defaults["depth"].append(depth)
            if lat is not None:
                values_for_defaults["latitude"].append(lat)
            if lon is not None:
                values_for_defaults["longitude"].append(lon)

            idx = bisect_right(starts, event_dt) - 1
            if idx < 0:
                skipped += 1
                continue
            if event_dt >= starts[idx] + timedelta(days=step_days):
                skipped += 1
                continue
            current_mag = rows[idx]["mag"]
            if current_mag > 0:
                collisions += 1
            if mag >= current_mag:
                rows[idx] = {
                    "mag": mag,
                    "depth": depth if depth is not None else 0.0,
                    "latitude": lat if lat is not None else 0.0,
                    "longitude": lon if lon is not None else 0.0,
                }
            assigned += 1
            kept_events.append(
                {
                    "id": event.get("id", ""),
                    "time": event.get("time", ""),
                    "period_start": format_date(starts[idx]),
                    "mag": mag,
                }
            )

    for key, vals in values_for_defaults.items():
        if vals:
            defaults[key] = sum(vals) / len(vals)
    for row in rows:
        if row["mag"] <= 0:
            row["depth"] = defaults["depth"]
            row["latitude"] = defaults["latitude"]
            row["longitude"] = defaults["longitude"]

    summary = {
        "assigned_events": assigned,
        "skipped_events": skipped,
        "collision_bins": collisions,
        "event_bins": sum(1 for row in rows if row["mag"] > 0),
        "non_event_defaults": defaults,
        "events": kept_events,
    }
    return rows, summary


def chunks(items: list[float], size: int) -> Iterable[list[float]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def validate_horizons_rows(
    spec: BodySpec,
    epochs_jd: list[float],
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Require an exact epoch match and finite Cartesian state vectors."""
    ordered = sorted(rows, key=lambda row: safe_float(row.get("datetime_jd")) or -1.0)
    if len(ordered) != len(epochs_jd):
        raise RuntimeError(
            f"Horizons returned {len(ordered)} rows for {spec.name}, expected {len(epochs_jd)}."
        )

    missing_columns = [
        col
        for col in ("datetime_jd", *REQUIRED_VECTOR_COLUMNS)
        if not ordered or col not in ordered[0]
    ]
    if missing_columns:
        raise RuntimeError(
            f"Horizons response for {spec.name} is missing required columns: "
            f"{', '.join(missing_columns)}."
        )

    for index, (expected_jd, row) in enumerate(zip(sorted(epochs_jd), ordered)):
        actual_jd = safe_float(row.get("datetime_jd"))
        if actual_jd is None or abs(actual_jd - expected_jd) > JULIAN_DAY_TOLERANCE:
            raise RuntimeError(
                f"Horizons epoch mismatch for {spec.name} at row {index}: "
                f"requested {expected_jd:.9f}, returned {actual_jd!r}."
            )
        invalid = [col for col in REQUIRED_VECTOR_COLUMNS if safe_float(row.get(col)) is None]
        if invalid:
            raise RuntimeError(
                f"Horizons returned non-finite state values for {spec.name} at "
                f"JD {actual_jd:.9f}: {', '.join(invalid)}."
            )
    return ordered


def fetch_vectors_for_body(
    spec: BodySpec,
    epochs_jd: list[float],
    refplane: str,
    chunk_size: int,
    sleep_seconds: float,
    max_retries: int,
) -> tuple[list[dict[str, float | None]], dict]:
    from astroquery.jplhorizons import Horizons

    all_rows: list[dict[str, object]] = []
    chunk_count = 0
    for epoch_chunk in chunks(epochs_jd, chunk_size):
        chunk_count += 1
        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                obj = Horizons(id=spec.command, location=spec.center, epochs=epoch_chunk)
                table = obj.vectors(refplane=refplane, aberrations="geometric", cache=False)
                all_rows.extend(table.to_pandas().to_dict("records"))
                break
            except Exception as exc:
                last_error = exc
                if attempt < max_retries:
                    time.sleep(sleep_seconds * attempt)
        else:
            raise RuntimeError(
                f"Horizons vectors failed for {spec.name} ({spec.command}) at {spec.center}: {last_error}"
            )
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    all_rows = validate_horizons_rows(spec, epochs_jd, all_rows)

    present_cols = [col for col in VECTOR_COLUMNS if col in all_rows[0]]
    if not present_cols:
        raise RuntimeError(f"No expected vector columns returned for {spec.name}.")

    vectors: list[dict[str, float | None]] = []
    for row in all_rows:
        vectors.append({col: safe_float(row.get(col)) for col in present_cols})
    meta = {
        "body_name": spec.name,
        "horizons_command": spec.command,
        "center_used": spec.center,
        "body_type": spec.body_type,
        "coordinates_requested": spec.coordinates,
        "vector_columns": present_cols,
        "chunks": chunk_count,
        "note": spec.note,
    }
    return vectors, meta


def probe_vectors_for_body(spec: BodySpec, epochs_jd: list[float], refplane: str) -> tuple[bool, str]:
    from astroquery.jplhorizons import Horizons

    try:
        obj = Horizons(id=spec.command, location=spec.center, epochs=epochs_jd)
        table = obj.vectors(refplane=refplane, aberrations="geometric", cache=False)
        rows = table.to_pandas().to_dict("records")
        validate_horizons_rows(spec, epochs_jd, rows)
        return True, f"ok rows={len(rows)} epochs_verified=yes"
    except Exception as exc:
        return False, str(exc)


def parse_horizons_time_bound(message: str) -> dict[str, object] | None:
    lower = str(message or "").lower()
    temporal_error_markers = (
        "no ephemeris",
        "no ephemerides",
        "ephemeris for target",
        "outside the range",
        "available",
    )
    if not any(marker in lower for marker in temporal_error_markers):
        return None
    pattern = re.compile(
        r"\b(prior to|after)\s+(?:A\.D\.\s*)?(\d{3,4})-([A-Za-z]{3})-(\d{1,2})\b",
        flags=re.IGNORECASE,
    )
    match = pattern.search(message)
    if not match:
        return None
    relation, year, month, day = match.groups()
    bound_date = parse_horizons_date(year, month, day)
    if relation.lower() == "prior to":
        return {"kind": "min_start", "date": bound_date, "raw": match.group(0)}
    return {"kind": "max_end", "date": bound_date, "raw": match.group(0)}


def classify_horizons_error(message: str) -> tuple[str, dict[str, object] | None]:
    bound = parse_horizons_time_bound(message)
    if bound:
        return f"temporal_{bound['kind']}", bound

    lower = str(message or "").lower()
    if "same as observer" in lower or ("target" in lower and "observer" in lower):
        return "observer_target_conflict", None
    if "unknown target" in lower or "cannot find" in lower or "not found" in lower:
        return "invalid_or_unknown_target", None
    if "ambiguous" in lower:
        return "ambiguous_target", None
    if "timeout" in lower or "temporarily" in lower or "connection" in lower:
        return "transient_horizons_error", None
    return "non_temporal_horizons_error", None


def auto_clip_error_groups(items: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[object, object, object], dict[str, object]] = {}
    for item in items:
        key = (
            item.get("error_type"),
            item.get("kind"),
            item.get("clip_date"),
        )
        group = grouped.setdefault(
            key,
            {
                "error_type": item.get("error_type"),
                "kind": item.get("kind"),
                "clip_date": item.get("clip_date"),
                "body_count": 0,
                "body_names": [],
                "horizons_commands": [],
                "sample_error": item.get("error"),
            },
        )
        group["body_count"] = int(group["body_count"]) + 1
        group["body_names"].append(item.get("body_name"))
        group["horizons_commands"].append(item.get("horizons_command"))
    return list(grouped.values())


def probe_specs(
    specs: list[BodySpec],
    start: datetime,
    end: datetime,
    step_days: int,
    refplane: str,
    time_travel_mode: str,
    time_travel_value: float,
) -> tuple[list[dict[str, object]], list[datetime], list[float]]:
    starts = period_starts(start, end, step_days)
    epochs_jd = build_astro_epochs_jd(starts, time_travel_mode, time_travel_value)
    probe_epochs = probe_endpoint_epochs(epochs_jd)
    results: list[dict[str, object]] = []
    for spec in specs:
        ok, msg = probe_vectors_for_body(spec, probe_epochs, refplane)
        results.append({"spec": spec, "ok": ok, "message": msg})
    return results, starts, epochs_jd


def print_probe_results(results: list[dict[str, object]]) -> None:
    for i, result in enumerate(results, start=1):
        spec = result["spec"]
        assert isinstance(spec, BodySpec)
        ok = bool(result["ok"])
        msg = str(result["message"])
        status = "OK" if ok else "FAIL"
        print(f"[{i}/{len(results)}] {status:4s} {spec.name} id={spec.command} center={spec.center}: {msg}")


def apply_auto_clip(
    specs: list[BodySpec],
    start: datetime,
    end: datetime,
    step_days: int,
    refplane: str,
    mode: str,
    time_travel_mode: str,
    time_travel_value: float,
) -> tuple[list[BodySpec], datetime, datetime, list[datetime], list[float], dict[str, object]]:
    starts = period_starts(start, end, step_days)
    epochs_jd = build_astro_epochs_jd(starts, time_travel_mode, time_travel_value)
    time_travel_days_back = time_travel_offset_days(time_travel_mode, time_travel_value)
    info: dict[str, object] = {
        "mode": mode,
        "requested_start_date": format_date(start),
        "requested_end_date": format_date(end),
        "effective_start_date": format_date(start),
        "effective_end_date": format_date(end),
        "probe_results": [],
        "date_clips": [],
        "body_clips": [],
        "error_groups": [],
        "horizontal_policy": (
            "temporal Horizons bounds shorten the global date range; "
            "non-temporal Horizons errors remove the affected bodies"
        ),
        "global_date_clip": None,
        "time_travel_mode": time_travel_mode,
        "time_travel_value": time_travel_value,
        "time_travel_offset_days": time_travel_days_back,
        **time_travel_date_policy(step_days),
    }
    if mode == "none":
        return specs, start, end, starts, epochs_jd, info

    print(f"[INFO] Auto-clip preflight mode: {mode}")
    results, starts, epochs_jd = probe_specs(
        specs, start, end, step_days, refplane, time_travel_mode, time_travel_value
    )
    info["probe_results"] = [
        {
            "body_name": result["spec"].name,
            "horizons_command": result["spec"].command,
            "center_used": result["spec"].center,
            "ok": bool(result["ok"]),
            "message": str(result["message"]),
        }
        for result in results
    ]
    failed = [result for result in results if not result["ok"]]
    if not failed:
        print("[INFO] Auto-clip preflight: all selected bodies are reachable.")
        return specs, start, end, starts, epochs_jd, info

    if mode == "vertical":
        failed_names = {result["spec"].name for result in failed}
        kept = [spec for spec in specs if spec.name not in failed_names]
        if not kept:
            raise RuntimeError("Auto-clip vertical would remove all bodies; refusing to build an empty astro master.")
        info["body_clips"] = [
            {
                "body_name": result["spec"].name,
                "horizons_command": result["spec"].command,
                "center_used": result["spec"].center,
                "reason": "auto_clip_vertical_probe",
                "error_type": classify_horizons_error(str(result["message"]))[0],
                "error": str(result["message"]),
            }
            for result in failed
        ]
        info["error_groups"] = auto_clip_error_groups(info["body_clips"])
        print(f"[INFO] Auto-clip vertical removed bodies: {', '.join(sorted(failed_names))}")
        return kept, start, end, starts, epochs_jd, info

    clipped_start = start
    clipped_end = end
    clips: list[dict[str, object]] = []
    body_clips: list[dict[str, object]] = []
    active_specs = list(specs)
    reprobe: list[dict[str, object]] = []
    for pass_index in range(1, 8):
        reprobe, starts, epochs_jd = probe_specs(
            active_specs,
            clipped_start,
            clipped_end,
            step_days,
            refplane,
            time_travel_mode,
            time_travel_value,
        )
        pass_failed = [result for result in reprobe if not result["ok"]]
        if not pass_failed:
            break

        changed = False
        drop_names: set[str] = set()
        for result in pass_failed:
            spec = result["spec"]
            assert isinstance(spec, BodySpec)
            error_type, bound = classify_horizons_error(str(result["message"]))
            if bound:
                bound_date = bound["date"]
                assert isinstance(bound_date, datetime)
                real_timeline_bound = bound_date + timedelta(days=time_travel_days_back)
                clip_date = real_timeline_bound
                if bound["kind"] == "min_start" and real_timeline_bound > clipped_start:
                    clipped_start = real_timeline_bound
                    changed = True
                elif bound["kind"] == "max_end" and real_timeline_bound < clipped_end:
                    clipped_end = real_timeline_bound
                    changed = True
                clips.append(
                    {
                        "body_name": spec.name,
                        "horizons_command": spec.command,
                        "center_used": spec.center,
                        "error_type": error_type,
                        "kind": bound["kind"],
                        "clip_date": format_date(clip_date),
                        "raw_bound": bound["raw"],
                        "astro_bound_date": format_date(bound_date),
                        "time_travel_offset_days": time_travel_days_back,
                        "error": str(result["message"]),
                        "preflight_pass": pass_index,
                    }
                )
            else:
                drop_names.add(spec.name)
                body_clips.append(
                    {
                        "body_name": spec.name,
                        "horizons_command": spec.command,
                        "center_used": spec.center,
                        "reason": "auto_clip_horizontal_vertical_fallback_non_temporal_error",
                        "error_type": error_type,
                        "error": str(result["message"]),
                        "preflight_pass": pass_index,
                    }
                )

        if clipped_start > clipped_end:
            raise RuntimeError(
                f"Auto-clip horizontal produced an empty date range: {clipped_start.date()} > {clipped_end.date()}"
            )
        if drop_names:
            active_specs = [spec for spec in active_specs if spec.name not in drop_names]
            if not active_specs:
                raise RuntimeError("Auto-clip horizontal vertical fallback would remove all bodies.")
            changed = True
        if not changed:
            names = ", ".join(result["spec"].name for result in pass_failed)
            raise RuntimeError(f"Auto-clip horizontal could not resolve unavailable bodies: {names}")
    else:
        raise RuntimeError("Auto-clip horizontal did not converge after 7 preflight passes.")

    starts = period_starts(clipped_start, clipped_end, step_days)
    epochs_jd = build_astro_epochs_jd(starts, time_travel_mode, time_travel_value)
    print(f"[INFO] Auto-clip horizontal date range: {start.date()} -> {end.date()} became {clipped_start.date()} -> {clipped_end.date()}")
    info["date_clips"] = clips
    info["body_clips"] = body_clips
    info["reprobe_results"] = [
        {
            "body_name": result["spec"].name,
            "horizons_command": result["spec"].command,
            "center_used": result["spec"].center,
            "ok": bool(result["ok"]),
            "message": str(result["message"]),
        }
        for result in reprobe
    ]
    info["effective_start_date"] = format_date(clipped_start)
    info["effective_end_date"] = format_date(clipped_end)
    info["global_date_clip"] = {
        "requested_start_date": format_date(start),
        "requested_end_date": format_date(end),
        "effective_start_date": format_date(clipped_start),
        "effective_end_date": format_date(clipped_end),
    }
    info["error_groups"] = auto_clip_error_groups(clips + body_clips)
    if body_clips:
        names = ", ".join(sorted({str(item["body_name"]) for item in body_clips}))
        print(f"[INFO] Auto-clip horizontal vertical fallback removed bodies: {names}")
    return active_specs, clipped_start, clipped_end, starts, epochs_jd, info


def feature_name(spec: BodySpec, vector_col: str) -> str:
    body = spec.name.replace(" ", "_")
    center = spec.center.replace("@", "at")
    return f"body:{body}|center:{center}|frame:ICRF_J2000|eph:{vector_col}|op:val"


def write_master(
    out_csv: Path,
    starts: list[datetime],
    seismic_rows: list[dict[str, float]],
    specs: list[BodySpec],
    body_vectors: dict[str, list[dict[str, float | None]]],
) -> list[str]:
    astro_columns: list[tuple[str, str, str]] = []
    for spec in specs:
        sample = body_vectors[spec.name][0]
        for vector_col in VECTOR_COLUMNS:
            if vector_col in sample:
                astro_columns.append((spec.name, vector_col, feature_name(spec, vector_col)))

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([*SEISMIC_COLUMNS, *[col_name for _, _, col_name in astro_columns]])
        for idx, start in enumerate(starts):
            seismic = seismic_rows[idx]
            row: list[object] = [
                format_date(start),
                f"{seismic['mag']:.6g}",
                f"{seismic['depth']:.6g}",
                f"{seismic['latitude']:.6g}",
                f"{seismic['longitude']:.6g}",
            ]
            for body_name, vector_col, _ in astro_columns:
                value = body_vectors[body_name][idx].get(vector_col)
                row.append("" if value is None else f"{value:.12g}")
            writer.writerow(row)
    return [col_name for _, _, col_name in astro_columns]


def main() -> None:
    args = parse_args()
    safe_csv = Path(args.safe_ephemerides_csv)
    if not args.probe_only:
        missing = [
            name
            for name, value in (
                ("--events-csv", args.events_csv),
                ("--output-float-csv", args.output_float_csv),
                ("--manifest-json", args.manifest_json),
            )
            if not value
        ]
        if missing:
            raise SystemExit(f"Missing required arguments outside --probe-only: {', '.join(missing)}")
    events_csv = Path(args.events_csv) if args.events_csv else None
    out_csv = Path(args.output_float_csv) if args.output_float_csv else None
    manifest_path = Path(args.manifest_json) if args.manifest_json else None

    start = parse_date(args.start_date)
    end = parse_date(args.end_date)
    specs_all = read_body_specs(safe_csv, args.moon_center)
    excluded = parse_exclude_bodies(args.exclude_bodies)
    specs, skipped_body_meta = filter_specs(specs_all, excluded)
    specs, start, end, starts, astro_epochs_jd, auto_clip_info = apply_auto_clip(
        specs,
        start,
        end,
        args.step_days,
        args.refplane,
        args.auto_clip,
        args.time_travel_mode,
        args.time_travel_value,
    )
    skipped_body_meta.extend(auto_clip_info.get("body_clips", []))

    if args.probe_only:
        print(f"[INFO] Probe period: {starts[0].date()} -> {starts[-1].date()} ({len(starts)} starts)")
        print(f"[INFO] Bodies selected: {len(specs)}; excluded: {sorted(excluded) if excluded else '-'}")
        if args.auto_clip != "none":
            print(f"[INFO] Auto-clip effective period: {auto_clip_info['effective_start_date']} -> {auto_clip_info['effective_end_date']}")
            if auto_clip_info.get("body_clips"):
                clipped = ", ".join(item["body_name"] for item in auto_clip_info["body_clips"])
                print(f"[INFO] Auto-clip removed bodies: {clipped}")
        probe_epochs = probe_endpoint_epochs(astro_epochs_jd)
        failed = 0
        for i, spec in enumerate(specs, start=1):
            ok, msg = probe_vectors_for_body(spec, probe_epochs, args.refplane)
            status = "OK" if ok else "FAIL"
            print(f"[{i}/{len(specs)}] {status:4s} {spec.name} id={spec.command} center={spec.center}: {msg}")
            if not ok:
                failed += 1
        if failed:
            raise SystemExit(2)
        return

    assert events_csv is not None
    assert out_csv is not None
    assert manifest_path is not None
    seismic_rows, event_summary = assign_events(events_csv, starts, args.step_days)

    body_vectors: dict[str, list[dict[str, float | None]]] = {}
    body_meta: list[dict] = []
    print(f"[INFO] Period starts: {len(starts)} ({starts[0].date()} -> {starts[-1].date()})")
    print(f"[INFO] Bodies from safe CSV: {len(specs_all)}")
    print(f"[INFO] Bodies selected: {len(specs)}")
    if excluded:
        print(f"[INFO] Bodies excluded by user: {', '.join(sorted(excluded))}")
    print(f"[INFO] Moon center mode: {args.moon_center}")
    if args.time_travel_mode != "none":
        days_back = time_travel_offset_days(args.time_travel_mode, args.time_travel_value)
        print(
            f"[INFO] Time-travel ribbon: mode={args.time_travel_mode} "
            f"value={args.time_travel_value:g} days_back={days_back:.12g}"
        )
    for i, spec in enumerate(specs, start=1):
        print(f"[{i}/{len(specs)}] JPL vectors {spec.name} id={spec.command} center={spec.center}", flush=True)
        try:
            vectors, meta = fetch_vectors_for_body(
                spec,
                astro_epochs_jd,
                args.refplane,
                args.chunk_size,
                args.sleep_seconds,
                args.max_retries,
            )
        except Exception as exc:
            if args.on_body_error != "skip":
                raise
            print(f"[WARN] Skipping {spec.name}: {exc}", flush=True)
            skipped_body_meta.append(
                {
                    "body_name": spec.name,
                    "horizons_command": spec.command,
                    "center_used": spec.center,
                    "reason": "horizons_error",
                    "error": str(exc),
                }
            )
            continue
        body_vectors[spec.name] = vectors
        body_meta.append(meta)

    specs_written = [spec for spec in specs if spec.name in body_vectors]

    astro_columns = write_master(out_csv, starts, seismic_rows, specs_written, body_vectors)
    manifest = {
        "builder": Path(__file__).name,
        "safe_ephemerides_csv": str(safe_csv),
        "events_csv": str(events_csv),
        "output_float_csv": str(out_csv),
        "requested_start_date": args.start_date,
        "requested_end_date": args.end_date,
        "start_date": format_date(start),
        "end_date": format_date(end),
        "step_days": args.step_days,
        "time_travel_mode": args.time_travel_mode,
        "time_travel_value": args.time_travel_value,
        "time_travel_offset_days": time_travel_offset_days(args.time_travel_mode, args.time_travel_value),
        **time_travel_date_policy(args.step_days),
        "date_semantics": (
            f"Each row date is the START of a {args.step_days}-day "
            "forecast/training period."
        ),
        "period_count": len(starts),
        "first_period_start": format_date(starts[0]),
        "last_period_start": format_date(starts[-1]),
        "julian_day_calendar_note": "Epoch requests use Julian Day values to avoid pre-1582 calendar-string ambiguity.",
        "refplane": args.refplane,
        "moon_center_mode": args.moon_center,
        "auto_clip": auto_clip_info,
        "body_specs": body_meta,
        "skipped_body_specs": skipped_body_meta,
        "astro_column_count": len(astro_columns),
        "astro_columns": astro_columns,
        "event_summary": event_summary,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"[OK] Wrote float master: {out_csv}")
    print(f"[OK] Wrote manifest:     {manifest_path}")
    print(f"[OK] Event bins:         {event_summary['event_bins']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[ABORTED] Interrupted.", file=sys.stderr)
        raise SystemExit(130)
