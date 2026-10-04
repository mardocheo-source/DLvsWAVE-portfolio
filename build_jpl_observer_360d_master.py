#!/usr/bin/env python3
"""Build a 360-day Japan/Nankai master from topocentric JPL ephemerides.

This is the observer-frame counterpart of build_jpl_safe_360d_master.py.
It keeps the same ancient-date-safe event binning and CSV layout, but asks
Horizons for ephemerides as seen from a terrestrial observer instead of SSB
Cartesian vectors.

Default observer used by the companion shell script is the approximate center
of Japan: lat=34.5, lon=137.5, elevation=0 km, alias=japan_center.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from build_jpl_safe_360d_master import (
    BodySpec,
    SEISMIC_COLUMNS,
    assign_events,
    date_to_julian_day,
    filter_specs,
    auto_clip_error_groups,
    classify_horizons_error,
    parse_date,
    parse_exclude_bodies,
    parse_horizons_time_bound,
    period_starts,
    read_body_specs,
    safe_float,
)


DEFAULT_EPHEMERIDES_FIELDS = "1,2,3,4,13,19,31,43"
DEFAULT_EXCLUDE_FIELDS = "targetname,datetime_jd"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build a 360d master using JPL Horizons observer/topocentric ephemerides."
    )
    p.add_argument("--safe-ephemerides-csv", required=True)
    p.add_argument("--events-csv")
    p.add_argument("--output-float-csv")
    p.add_argument("--manifest-json")
    p.add_argument("--start-date", default="1498-01-01")
    p.add_argument("--end-date", default="2035-12-31")
    p.add_argument("--step-days", type=int, default=360)
    p.add_argument(
        "--sparse-event-windows",
        action="store_true",
        help="Generate starts only around event windows plus the requested forecast window.",
    )
    p.add_argument("--event-window-days-before", type=int, default=10)
    p.add_argument("--event-window-days-after", type=int, default=10)
    p.add_argument("--forecast-start-date")
    p.add_argument("--forecast-end-date")
    p.add_argument("--observer-lat", type=float, default=34.5)
    p.add_argument("--observer-lon", type=float, default=137.5)
    p.add_argument("--observer-elevation", type=float, default=0.0)
    p.add_argument("--observer-alias", default="japan_center")
    p.add_argument("--ephemerides-fields", default=DEFAULT_EPHEMERIDES_FIELDS)
    p.add_argument("--exclude-fields", default=DEFAULT_EXCLUDE_FIELDS)
    p.add_argument("--chunk-size", type=int, default=80)
    p.add_argument("--sleep-seconds", type=float, default=0.5)
    p.add_argument("--max-retries", type=int, default=3)
    p.add_argument(
        "--exclude-bodies",
        default="earth",
        help="Comma-separated safe CSV body_name values to exclude. Default excludes earth for terrestrial observer.",
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
        default="vertical",
        help=(
            "Automatic preflight clipping. vertical drops unavailable bodies; "
            "horizontal clips date bounds when Horizons reports parsable date limits."
        ),
    )
    p.add_argument("--probe-only", action="store_true")
    return p.parse_args()


def observer_location(args: argparse.Namespace) -> dict[str, float]:
    return {
        "lat": float(args.observer_lat),
        "lon": float(args.observer_lon),
        "elevation": float(args.observer_elevation),
    }


def observer_tag(args: argparse.Namespace) -> str:
    alias = str(args.observer_alias or "observer").strip()
    return alias.replace("@", "at").replace(",", "_").replace(" ", "_").replace(";", "_")


def sparse_period_starts(
    events_csv: Path,
    start: datetime,
    end: datetime,
    step_days: int,
    days_before: int,
    days_after: int,
    forecast_start: datetime | None,
    forecast_end: datetime | None,
) -> list[datetime]:
    starts: set[datetime] = set()
    delta = timedelta(days=step_days)

    def add_window(win_start: datetime, win_end: datetime) -> None:
        cur = max(win_start, start)
        stop = min(win_end, end)
        while cur <= stop:
            starts.add(datetime(cur.year, cur.month, cur.day))
            cur += delta

    with events_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                event_dt = parse_date(row.get("time", ""))
            except Exception:
                continue
            add_window(
                event_dt - timedelta(days=days_before),
                event_dt + timedelta(days=days_after),
            )

    if forecast_start is not None and forecast_end is not None:
        add_window(forecast_start, forecast_end)

    out = sorted(starts)
    if not out:
        raise ValueError("Sparse window generation produced no period starts.")
    return out


def clip_sparse_starts(starts: list[datetime], start: datetime, end: datetime) -> list[datetime]:
    out = [dt for dt in starts if start <= dt <= end]
    if not out:
        raise ValueError(f"No sparse period starts remain in clipped range {start.date()} -> {end.date()}.")
    return out


def excluded_fields(raw: str) -> set[str]:
    return {part.strip() for part in str(raw or "").split(",") if part.strip()}


def is_numeric_value(value: object) -> bool:
    return safe_float(value) is not None


def row_to_numeric_dict(row: object, colnames: list[str], skip_cols: set[str]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for col in colnames:
        if col in skip_cols:
            continue
        try:
            value = row[col]
        except Exception:
            continue
        numeric = safe_float(value)
        if numeric is not None:
            out[col] = numeric
    return out


def fetch_ephemerides_for_body(
    spec: BodySpec,
    epochs_jd: list[float],
    location: dict[str, float],
    ephemerides_fields: str,
    exclude_fields_raw: str,
    chunk_size: int,
    sleep_seconds: float,
    max_retries: int,
) -> tuple[list[dict[str, float | None]], dict[str, object]]:
    from astroquery.jplhorizons import Horizons

    skip_cols = excluded_fields(exclude_fields_raw)
    all_rows: list[dict[str, float | None]] = []
    all_numeric_cols: set[str] = set()
    chunks = [epochs_jd[i:i + chunk_size] for i in range(0, len(epochs_jd), chunk_size)]
    last_error: Exception | None = None

    for chunk in chunks:
        for attempt in range(1, max_retries + 1):
            try:
                obj = Horizons(id=spec.command, location=location, epochs=chunk)
                table = obj.ephemerides(quantities=ephemerides_fields, cache=False)
                colnames = list(getattr(table, "colnames", []))
                for row in table:
                    numeric_row = row_to_numeric_dict(row, colnames, skip_cols)
                    all_numeric_cols.update(k for k, v in numeric_row.items() if v is not None)
                    all_rows.append(numeric_row)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt < max_retries:
                    time.sleep(sleep_seconds * attempt)
        if last_error is not None:
            raise RuntimeError(
                f"Horizons ephemerides failed for {spec.name} ({spec.command}) "
                f"from observer {location}: {last_error}"
            )
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    if len(all_rows) != len(epochs_jd):
        raise RuntimeError(
            f"Horizons returned {len(all_rows)} rows for {spec.name}, expected {len(epochs_jd)}."
        )

    numeric_cols = sorted(all_numeric_cols)
    normalized_rows = [{col: row.get(col) for col in numeric_cols} for row in all_rows]
    meta = {
        "body_name": spec.name,
        "horizons_command": spec.command,
        "observer_location": location,
        "ephemerides_fields": ephemerides_fields,
        "columns": numeric_cols,
        "row_count": len(normalized_rows),
    }
    return normalized_rows, meta


def probe_ephemerides_for_body(
    spec: BodySpec,
    epochs_jd: list[float],
    location: dict[str, float],
    ephemerides_fields: str,
    exclude_fields_raw: str,
) -> tuple[bool, str]:
    from astroquery.jplhorizons import Horizons

    try:
        obj = Horizons(id=spec.command, location=location, epochs=epochs_jd)
        table = obj.ephemerides(quantities=ephemerides_fields, cache=False)
        usable = 0
        skip_cols = excluded_fields(exclude_fields_raw)
        colnames = list(getattr(table, "colnames", []))
        for row in table:
            if row_to_numeric_dict(row, colnames, skip_cols):
                usable += 1
        return True, f"ok rows={len(table)} usable_numeric_rows={usable}"
    except Exception as exc:
        return False, str(exc)


def apply_auto_clip(
    specs: list[BodySpec],
    start: datetime,
    end: datetime,
    step_days: int,
    location: dict[str, float],
    ephemerides_fields: str,
    exclude_fields_raw: str,
    mode: str,
    requested_starts: list[datetime] | None = None,
) -> tuple[list[BodySpec], datetime, datetime, list[datetime], list[float], dict[str, object]]:
    starts = clip_sparse_starts(requested_starts, start, end) if requested_starts is not None else period_starts(start, end, step_days)
    epochs_jd = [date_to_julian_day(dt) for dt in starts]
    info: dict[str, object] = {
        "mode": mode,
        "requested_start_date": start.strftime("%Y-%m-%d"),
        "requested_end_date": end.strftime("%Y-%m-%d"),
        "effective_start_date": start.strftime("%Y-%m-%d"),
        "effective_end_date": end.strftime("%Y-%m-%d"),
        "probe_results": [],
        "date_clips": [],
        "body_clips": [],
        "error_groups": [],
        "horizontal_policy": (
            "temporal Horizons bounds shorten the global date range; "
            "non-temporal Horizons errors remove the affected bodies"
        ),
        "global_date_clip": None,
    }
    if mode == "none":
        return specs, start, end, starts, epochs_jd, info

    print(f"[INFO] Observer auto-clip preflight mode: {mode}")
    probe_epochs = [epochs_jd[0], epochs_jd[-1]]
    results: list[dict[str, object]] = []
    for spec in specs:
        ok, msg = probe_ephemerides_for_body(
            spec, probe_epochs, location, ephemerides_fields, exclude_fields_raw
        )
        results.append({"spec": spec, "ok": ok, "message": msg})

    info["probe_results"] = [
        {
            "body_name": result["spec"].name,
            "horizons_command": result["spec"].command,
            "ok": bool(result["ok"]),
            "message": str(result["message"]),
        }
        for result in results
    ]
    failed = [result for result in results if not result["ok"]]
    if not failed:
        print("[INFO] Observer auto-clip preflight: all selected bodies are reachable.")
        return specs, start, end, starts, epochs_jd, info

    if mode == "vertical":
        failed_names = {result["spec"].name for result in failed}
        kept = [spec for spec in specs if spec.name not in failed_names]
        if not kept:
            raise RuntimeError("Auto-clip vertical would remove all bodies.")
        info["body_clips"] = [
            {
                "body_name": result["spec"].name,
                "horizons_command": result["spec"].command,
                "reason": "observer_auto_clip_vertical_probe",
                "error_type": classify_horizons_error(str(result["message"]))[0],
                "error": str(result["message"]),
            }
            for result in failed
        ]
        info["error_groups"] = auto_clip_error_groups(info["body_clips"])
        print(f"[INFO] Observer auto-clip vertical removed bodies: {', '.join(sorted(failed_names))}")
        return kept, start, end, starts, epochs_jd, info

    clipped_start = start
    clipped_end = end
    clips: list[dict[str, object]] = []
    body_clips: list[dict[str, object]] = []
    active_specs = list(specs)
    reprobe_results: list[dict[str, object]] = []
    for pass_index in range(1, 8):
        starts = clip_sparse_starts(requested_starts, clipped_start, clipped_end) if requested_starts is not None else period_starts(clipped_start, clipped_end, step_days)
        epochs_jd = [date_to_julian_day(dt) for dt in starts]
        probe_epochs = [epochs_jd[0], epochs_jd[-1]]
        reprobe_results = []
        for spec in active_specs:
            ok, msg = probe_ephemerides_for_body(
                spec, probe_epochs, location, ephemerides_fields, exclude_fields_raw
            )
            reprobe_results.append({"spec": spec, "ok": ok, "message": msg})
        pass_failed = [result for result in reprobe_results if not result["ok"]]
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
                if bound["kind"] == "min_start":
                    # Horizons observer errors can report bounds with a time inside the
                    # day, e.g. "prior to 1600-JAN-01 23:58".  We only parse the date
                    # token, so move to the next midnight to avoid starting too early.
                    clip_date = bound_date + timedelta(days=1)
                    if clip_date > clipped_start:
                        clipped_start = clip_date
                        changed = True
                else:
                    clip_date = bound_date
                    if bound_date < clipped_end:
                        clipped_end = bound_date
                        changed = True
                clips.append(
                    {
                        "body_name": spec.name,
                        "horizons_command": spec.command,
                        "error_type": error_type,
                        "kind": bound["kind"],
                        "clip_date": clip_date.strftime("%Y-%m-%d"),
                        "parsed_bound_date": bound_date.strftime("%Y-%m-%d"),
                        "raw_bound": bound["raw"],
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
                        "reason": "observer_auto_clip_horizontal_vertical_fallback_non_temporal_error",
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
                raise RuntimeError("Observer auto-clip horizontal vertical fallback would remove all bodies.")
            changed = True
        if not changed:
            names = ", ".join(result["spec"].name for result in pass_failed)
            raise RuntimeError(f"Observer auto-clip horizontal could not resolve unavailable bodies: {names}")
    else:
        raise RuntimeError("Observer auto-clip horizontal did not converge after 7 preflight passes.")

    starts = clip_sparse_starts(requested_starts, clipped_start, clipped_end) if requested_starts is not None else period_starts(clipped_start, clipped_end, step_days)
    epochs_jd = [date_to_julian_day(dt) for dt in starts]
    info["date_clips"] = clips
    info["body_clips"] = body_clips
    info["effective_start_date"] = clipped_start.strftime("%Y-%m-%d")
    info["effective_end_date"] = clipped_end.strftime("%Y-%m-%d")
    print(
        f"[INFO] Observer auto-clip horizontal date range: "
        f"{start.date()} -> {end.date()} became {clipped_start.date()} -> {clipped_end.date()}"
    )
    info["reprobe_results"] = [
        {
            "body_name": result["spec"].name,
            "horizons_command": result["spec"].command,
            "ok": bool(result["ok"]),
            "message": str(result["message"]),
        }
        for result in reprobe_results
    ]
    info["global_date_clip"] = {
        "requested_start_date": start.strftime("%Y-%m-%d"),
        "requested_end_date": end.strftime("%Y-%m-%d"),
        "effective_start_date": clipped_start.strftime("%Y-%m-%d"),
        "effective_end_date": clipped_end.strftime("%Y-%m-%d"),
    }
    info["error_groups"] = auto_clip_error_groups(clips + body_clips)
    if body_clips:
        names = ", ".join(sorted({str(item["body_name"]) for item in body_clips}))
        print(f"[INFO] Observer auto-clip horizontal vertical fallback removed bodies: {names}")
    return active_specs, clipped_start, clipped_end, starts, epochs_jd, info


def feature_name(spec: BodySpec, obs_tag: str, eph_col: str) -> str:
    body = spec.name.replace(" ", "_")
    eph = str(eph_col).replace(" ", "_")
    return f"body:{body}|obs:{obs_tag}|frame:topocentric|eph:{eph}|op:val"


def write_master(
    out_csv: Path,
    starts: list[datetime],
    seismic_rows: list[dict[str, float]],
    specs: list[BodySpec],
    body_ephemerides: dict[str, list[dict[str, float | None]]],
    obs_tag: str,
) -> list[str]:
    astro_columns: list[tuple[str, str, str]] = []
    for spec in specs:
        rows = body_ephemerides.get(spec.name) or []
        cols: set[str] = set()
        for row in rows:
            cols.update(k for k, value in row.items() if value is not None)
        for eph_col in sorted(cols):
            astro_columns.append((spec.name, eph_col, feature_name(spec, obs_tag, eph_col)))

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([*SEISMIC_COLUMNS, *[col_name for _, _, col_name in astro_columns]])
        for idx, start in enumerate(starts):
            seismic = seismic_rows[idx]
            row: list[object] = [
                start.strftime("%Y-%m-%d"),
                f"{seismic['mag']:.6g}",
                f"{seismic['depth']:.6g}",
                f"{seismic['latitude']:.6g}",
                f"{seismic['longitude']:.6g}",
            ]
            for body_name, eph_col, _ in astro_columns:
                value = body_ephemerides[body_name][idx].get(eph_col)
                row.append("" if value is None or math.isnan(float(value)) else f"{value:.12g}")
            writer.writerow(row)
    return [col_name for _, _, col_name in astro_columns]


def main() -> None:
    args = parse_args()
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

    safe_csv = Path(args.safe_ephemerides_csv)
    events_csv = Path(args.events_csv) if args.events_csv else None
    out_csv = Path(args.output_float_csv) if args.output_float_csv else None
    manifest_path = Path(args.manifest_json) if args.manifest_json else None

    start = parse_date(args.start_date)
    end = parse_date(args.end_date)
    location = observer_location(args)
    obs_tag = observer_tag(args)
    requested_starts = None
    if args.sparse_event_windows:
        if not events_csv:
            raise SystemExit("--sparse-event-windows requires --events-csv")
        forecast_start = parse_date(args.forecast_start_date) if args.forecast_start_date else None
        forecast_end = parse_date(args.forecast_end_date) if args.forecast_end_date else None
        requested_starts = sparse_period_starts(
            events_csv,
            start,
            end,
            args.step_days,
            args.event_window_days_before,
            args.event_window_days_after,
            forecast_start,
            forecast_end,
        )
        start = requested_starts[0]
        end = requested_starts[-1]

    specs_all = read_body_specs(safe_csv, moon_center="earth")
    excluded = parse_exclude_bodies(args.exclude_bodies)
    specs, skipped_body_meta = filter_specs(specs_all, excluded)
    specs, start, end, starts, epochs_jd, auto_clip_info = apply_auto_clip(
        specs,
        start,
        end,
        args.step_days,
        location,
        args.ephemerides_fields,
        args.exclude_fields,
        args.auto_clip,
        requested_starts=requested_starts,
    )
    skipped_body_meta.extend(auto_clip_info.get("body_clips", []))

    if args.probe_only:
        print(f"[INFO] Probe period: {starts[0].date()} -> {starts[-1].date()} ({len(starts)} starts)")
        print(f"[INFO] Observer: {obs_tag} lat={location['lat']} lon={location['lon']} elev={location['elevation']} km")
        print(f"[INFO] Bodies selected: {len(specs)}; excluded: {sorted(excluded) if excluded else '-'}")
        probe_epochs = [epochs_jd[0], epochs_jd[-1]]
        failed = 0
        for i, spec in enumerate(specs, start=1):
            ok, msg = probe_ephemerides_for_body(
                spec, probe_epochs, location, args.ephemerides_fields, args.exclude_fields
            )
            status = "OK" if ok else "FAIL"
            print(f"[{i}/{len(specs)}] {status:4s} {spec.name} id={spec.command}: {msg}")
            if not ok:
                failed += 1
        if failed:
            raise SystemExit(2)
        return

    assert events_csv is not None
    assert out_csv is not None
    assert manifest_path is not None
    seismic_rows, event_summary = assign_events(events_csv, starts, args.step_days)

    body_ephemerides: dict[str, list[dict[str, float | None]]] = {}
    body_meta: list[dict[str, object]] = []
    print(f"[INFO] Period starts: {len(starts)} ({starts[0].date()} -> {starts[-1].date()})")
    print(f"[INFO] Observer: {obs_tag} lat={location['lat']} lon={location['lon']} elev={location['elevation']} km")
    print(f"[INFO] Bodies from safe CSV: {len(specs_all)}")
    print(f"[INFO] Bodies selected: {len(specs)}")
    if excluded:
        print(f"[INFO] Bodies excluded by user: {', '.join(sorted(excluded))}")

    for i, spec in enumerate(specs, start=1):
        print(f"[{i}/{len(specs)}] JPL observer ephemerides {spec.name} id={spec.command}", flush=True)
        try:
            rows, meta = fetch_ephemerides_for_body(
                spec,
                epochs_jd,
                location,
                args.ephemerides_fields,
                args.exclude_fields,
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
                    "reason": "observer_horizons_error",
                    "error": str(exc),
                }
            )
            continue
        body_ephemerides[spec.name] = rows
        body_meta.append(meta)

    specs_written = [spec for spec in specs if spec.name in body_ephemerides]
    astro_columns = write_master(out_csv, starts, seismic_rows, specs_written, body_ephemerides, obs_tag)
    manifest = {
        "builder": Path(__file__).name,
        "safe_ephemerides_csv": str(safe_csv),
        "events_csv": str(events_csv),
        "output_float_csv": str(out_csv),
        "requested_start_date": args.start_date,
        "requested_end_date": args.end_date,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "step_days": args.step_days,
        "sparse_event_windows": bool(args.sparse_event_windows),
        "event_window_days_before": args.event_window_days_before if args.sparse_event_windows else None,
        "event_window_days_after": args.event_window_days_after if args.sparse_event_windows else None,
        "forecast_start_date": args.forecast_start_date,
        "forecast_end_date": args.forecast_end_date,
        "date_semantics": (
            f"Each row date is the START of a {args.step_days}-day "
            "forecast/training period."
        ),
        "observer_frame": "topocentric",
        "observer_alias": obs_tag,
        "observer_location": location,
        "ephemerides_fields": args.ephemerides_fields,
        "period_count": len(starts),
        "first_period_start": starts[0].strftime("%Y-%m-%d"),
        "last_period_start": starts[-1].strftime("%Y-%m-%d"),
        "julian_day_calendar_note": "Epoch requests use Julian Day values to avoid pre-1582 calendar-string ambiguity.",
        "auto_clip": auto_clip_info,
        "body_specs": body_meta,
        "skipped_body_specs": skipped_body_meta,
        "astro_column_count": len(astro_columns),
        "astro_columns": astro_columns,
        "event_summary": event_summary,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"[OK] Wrote observer float master: {out_csv}")
    print(f"[OK] Wrote manifest:              {manifest_path}")
    print(f"[OK] Event bins:                  {event_summary['event_bins']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[ABORTED] Interrupted.", file=sys.stderr)
        raise SystemExit(130)
