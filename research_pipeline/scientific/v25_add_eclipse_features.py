#!/usr/bin/env python3
"""Add calculated weekly solar/lunar eclipse features using Swiss Ephemeris."""
from __future__ import annotations

import argparse
import bisect
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import swisseph as swe


JST = timezone(timedelta(hours=9))
UTC = timezone.utc


@dataclass(frozen=True)
class Eclipse:
    jd_ut: float
    family: str
    scope: str
    type_name: str
    type_code: int


def datetime_to_jd(value: datetime) -> float:
    value = value.astimezone(UTC)
    hour = value.hour + value.minute / 60 + value.second / 3600 + value.microsecond / 3.6e9
    return float(swe.julday(value.year, value.month, value.day, hour, swe.GREG_CAL))


def jd_to_iso(value: float) -> str:
    year, month, day, hour = swe.revjul(value, swe.GREG_CAL)
    base = datetime(year, month, day, tzinfo=UTC)
    return (base + timedelta(hours=float(hour))).isoformat()


def eclipse_type(retflag: int, family: str) -> tuple[str, int]:
    if family == "solar":
        if retflag & swe.ECL_ANNULAR_TOTAL:
            return "hybrid", 4
        if retflag & swe.ECL_TOTAL:
            return "total", 3
        if retflag & swe.ECL_ANNULAR:
            return "annular", 2
        return "partial", 1
    if retflag & swe.ECL_TOTAL:
        return "total", 3
    if retflag & swe.ECL_PARTIAL:
        return "partial", 2
    return "penumbral", 1


def collect_eclipses(start_jd: float, end_jd: float, family: str, scope: str, geopos: tuple[float, float, float]) -> list[Eclipse]:
    cursor = start_jd - 40.0
    events: list[Eclipse] = []
    while True:
        if family == "solar" and scope == "global":
            retflag, times = swe.sol_eclipse_when_glob(cursor, swe.FLG_MOSEPH, 0, False)
        elif family == "lunar" and scope == "global":
            retflag, times = swe.lun_eclipse_when(cursor, swe.FLG_MOSEPH, 0, False)
        elif family == "solar":
            retflag, times, _ = swe.sol_eclipse_when_loc(cursor, geopos, swe.FLG_MOSEPH, False)
        else:
            retflag, times, _ = swe.lun_eclipse_when_loc(cursor, geopos, swe.FLG_MOSEPH, False)
        maximum = float(times[0])
        if maximum > end_jd + 40.0:
            break
        if maximum >= start_jd - 40.0:
            name, code = eclipse_type(int(retflag), family)
            events.append(Eclipse(maximum, family, scope, name, code))
        cursor = maximum + 1.0
    return events


def in_interval(events: list[Eclipse], starts: list[float], left: float, right: float) -> list[Eclipse]:
    lo = bisect.bisect_left(starts, left)
    hi = bisect.bisect_left(starts, right)
    return events[lo:hi]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-master", required=True, type=Path)
    parser.add_argument("--output-master", required=True, type=Path)
    parser.add_argument("--output-eclipse-catalog", required=True, type=Path)
    parser.add_argument("--output-audit", required=True, type=Path)
    parser.add_argument("--observer-lat", type=float, default=42.5)
    parser.add_argument("--observer-lon", type=float, default=145.0)
    args = parser.parse_args()

    master = pd.read_csv(args.input_master, low_memory=False)
    dates = pd.to_datetime(master.date, errors="raise")
    first_local = datetime(dates.iloc[0].year, dates.iloc[0].month, dates.iloc[0].day, tzinfo=JST)
    last_date = dates.iloc[-1]
    last_local_end = datetime(last_date.year, last_date.month, last_date.day, tzinfo=JST) + timedelta(days=7)
    first_jd = datetime_to_jd(first_local)
    last_jd = datetime_to_jd(last_local_end)
    geopos = (float(args.observer_lon), float(args.observer_lat), 0.0)

    all_events: list[Eclipse] = []
    for family in ("solar", "lunar"):
        for scope in ("global", "corridor_visible"):
            all_events.extend(collect_eclipses(first_jd, last_jd, family, scope, geopos))
    all_events.sort(key=lambda item: (item.scope, item.family, item.jd_ut))
    groups: dict[tuple[str, str], tuple[list[Eclipse], list[float]]] = {}
    for scope in ("global", "corridor_visible"):
        for family in ("solar", "lunar"):
            values = sorted([event for event in all_events if event.scope == scope and event.family == family], key=lambda item: item.jd_ut)
            groups[(scope, family)] = (values, [event.jd_ut for event in values])

    global_all = sorted([event for event in all_events if event.scope == "global"], key=lambda item: item.jd_ut)
    global_jds = [event.jd_ut for event in global_all]
    features: list[dict[str, float | int]] = []
    for date in dates:
        local_start = datetime(date.year, date.month, date.day, tzinfo=JST)
        left = datetime_to_jd(local_start)
        right = datetime_to_jd(local_start + timedelta(days=7))
        midpoint = (left + right) / 2.0
        row: dict[str, float | int] = {}
        weekly_global: list[Eclipse] = []
        for scope in ("global", "corridor_visible"):
            for family in ("solar", "lunar"):
                values, starts = groups[(scope, family)]
                weekly = in_interval(values, starts, left, right)
                if scope == "global":
                    weekly_global.extend(weekly)
                prefix = f"eclipse:{family}_{scope}"
                row[prefix + "|op:any_in_week"] = int(bool(weekly))
                row[prefix + "|op:count_in_week"] = int(len(weekly))
                row[prefix + "|op:max_type_code"] = int(max((event.type_code for event in weekly), default=0))
        row["eclipse:any_global|op:any_in_week"] = int(bool(weekly_global))
        row["eclipse:any_global|op:count_in_week"] = int(len(weekly_global))
        pos = bisect.bisect_left(global_jds, midpoint)
        candidates = global_all[max(0, pos - 1):min(len(global_all), pos + 1)]
        nearest = min(candidates, key=lambda item: abs(item.jd_ut - midpoint))
        row["eclipse:nearest_global|op:signed_days_from_week_midpoint"] = float(nearest.jd_ut - midpoint)
        row["eclipse:nearest_global|op:absolute_days_from_week_midpoint"] = float(abs(nearest.jd_ut - midpoint))
        row["eclipse:nearest_global|op:is_solar"] = int(nearest.family == "solar")
        features.append(row)

    feature_frame = pd.DataFrame(features)
    output = pd.concat([master.reset_index(drop=True), feature_frame], axis=1)
    args.output_master.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output_master, index=False)
    catalog = pd.DataFrame([
        {"maximum_utc": jd_to_iso(event.jd_ut), "julian_day_ut": event.jd_ut, "family": event.family, "scope": event.scope, "type": event.type_name, "type_code": event.type_code}
        for event in all_events
    ])
    args.output_eclipse_catalog.parent.mkdir(parents=True, exist_ok=True)
    catalog.to_csv(args.output_eclipse_catalog, index=False)
    feature_columns = list(feature_frame.columns)
    audit = {
        "status": "PASS" if output[feature_columns].notna().all().all() else "FAIL",
        "engine": "Swiss Ephemeris",
        "engine_version": swe.version,
        "ephemeris_mode": "Moshier (FLG_MOSEPH)",
        "week_semantics": "[Saturday 00:00 JST, next Saturday 00:00 JST)",
        "observer_for_visible_columns": {"latitude": args.observer_lat, "longitude": args.observer_lon, "elevation_m": 0.0},
        "coverage": {"first_week": str(dates.iloc[0].date()), "last_week": str(dates.iloc[-1].date()), "row_count": len(output)},
        "event_counts": catalog.groupby(["scope", "family"]).size().rename("count").reset_index().to_dict(orient="records"),
        "feature_columns": feature_columns,
        "note": "Global and corridor-visible eclipse events are geometric calculations, not labels inferred from earthquake dates.",
    }
    args.output_audit.parent.mkdir(parents=True, exist_ok=True)
    args.output_audit.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(audit, indent=2, ensure_ascii=False))
    if audit["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
