#!/usr/bin/env python3
"""Prepare a seismic-only location/depth target CSV for DLvsWAVE.

This is a modular adapter: it does not change the main training code.  It keeps
historical rows only when they are real seismic rows (mag >= threshold), while
also keeping the requested forecast rows so cli.py can still emit a forecast.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path


SEISMIC_COLS = {"mag", "depth", "latitude", "longitude"}


def parse_dt(value: str) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.strptime(text[:10], "%Y-%m-%d")


def parse_optional_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return parse_dt(value)


def in_window(dt: datetime, start: datetime | None, end: datetime | None) -> bool:
    if start is not None and dt < start:
        return False
    if end is not None:
        # User-facing end dates are inclusive at day precision.
        if dt.date() > end.date():
            return False
    return True


def to_float(row: dict[str, str], col: str, default: float = 0.0) -> float:
    try:
        value = row.get(col, "")
        if value is None or str(value).strip() == "":
            return default
        out = float(value)
        if not math.isfinite(out):
            return default
        return out
    except Exception:
        return default


def clip(v: float, lo: float, hi: float) -> float:
    return min(max(v, lo), hi)


def median(values: list[float]) -> float:
    vals = sorted(float(v) for v in values)
    if not vals:
        raise ValueError("median of empty list")
    mid = len(vals) // 2
    if len(vals) % 2:
        return vals[mid]
    return 0.5 * (vals[mid - 1] + vals[mid])


def _binary_labels(values: list[float], threshold: float, direction: str) -> list[int]:
    if direction == "above":
        return [1 if v >= threshold else 0 for v in values]
    return [1 if v <= threshold else 0 for v in values]


def _balance_score(labels: list[int]) -> float:
    if not labels:
        return 0.0
    pos = sum(labels) / len(labels)
    return max(0.0, 1.0 - abs(pos - 0.5) * 2.0)


def resolve_decision_threshold(spec: str | None, values: list[float],
                               validation_count: int, direction: str) -> tuple[float, dict[str, object]]:
    text = str(spec or "").strip().lower()
    if text not in {"median", "auto", "auto_median", "balanced_median"}:
        if not text:
            raise ValueError("--decision-threshold is required in binary mode")
        return float(text), {"method": "explicit", "requested": spec}

    if len(values) < 2:
        raise ValueError("Need at least two historical values for median threshold")
    n_val = max(1, min(int(validation_count), len(values) - 1))
    train_vals = list(values[:-n_val])
    val_vals = list(values[-n_val:])
    if not train_vals:
        train_vals = list(values)
    unique = sorted(set(float(v) for v in values))
    candidates: set[float] = set(unique)
    candidates.add(median(train_vals))
    candidates.add(median(values))
    for a, b in zip(unique, unique[1:]):
        candidates.add(0.5 * (a + b))

    scale = max(max(values) - min(values), 1e-9)
    target = median(train_vals)
    scored = []
    for cand in sorted(candidates):
        train_labels = _binary_labels(train_vals, cand, direction)
        val_labels = _binary_labels(val_vals, cand, direction)
        all_labels = _binary_labels(values, cand, direction)
        train_bal = _balance_score(train_labels)
        val_bal = _balance_score(val_labels)
        all_bal = _balance_score(all_labels)
        distance_penalty = abs(float(cand) - target) / scale
        score = 0.40 * val_bal + 0.40 * train_bal + 0.20 * all_bal - 0.05 * distance_penalty
        item = (score, val_bal, train_bal, all_bal, -distance_penalty, float(cand))
        scored.append(item)
    viable = [x for x in scored if x[1] > 0.0 and x[2] > 0.0]
    if not viable:
        viable = [x for x in scored if x[2] > 0.0]
    if not viable:
        viable = scored
    best = max(viable)
    chosen = float(best[-1])
    return chosen, {
        "method": text,
        "requested": spec,
        "chosen": chosen,
        "validation_event_count": n_val,
        "train_median": median(train_vals),
        "all_median": median(values),
        "train_balance": best[2],
        "validation_balance": best[1],
        "all_balance": best[3],
        "note": (
            "Auto threshold is chosen from historical seismic rows only. It favors a "
            "balanced final validation split first, then train/all balance, so the last "
            "validation events are not accidentally all on the same side when avoidable."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-csv", required=True, type=Path)
    ap.add_argument("--output-csv", required=True, type=Path)
    ap.add_argument("--output-json", required=True, type=Path)
    ap.add_argument("--target-source", required=True,
                    choices=["latitude", "longitude", "depth"])
    ap.add_argument("--mode", required=True, choices=["analog", "binary"])
    ap.add_argument("--target-name", default="location_target")
    ap.add_argument("--event-mag-threshold", type=float, default=0.1)
    ap.add_argument("--forecast-start-date", required=True)
    ap.add_argument("--forecast-end-date", required=True)
    ap.add_argument("--focus-start-date", default="")
    ap.add_argument("--focus-end-date", default="")
    ap.add_argument("--analog-scale", default="minmax", choices=["minmax", "none"])
    ap.add_argument("--clip-min", type=float, default=None)
    ap.add_argument("--clip-max", type=float, default=None)
    ap.add_argument("--forecast-target-fill", type=float, default=-1.0)
    ap.add_argument("--decision-threshold", default=None,
                    help="number, or median/auto_median/balanced_median for binary mode")
    ap.add_argument("--binary-direction", default="above", choices=["above", "below"])
    ap.add_argument("--validation-event-count", type=int, default=4)
    args = ap.parse_args()

    with args.input_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(f"CSV without header: {args.input_csv}")
        rows = list(reader)
        header = list(reader.fieldnames)

    for col in ("date", "mag", args.target_source):
        if col not in header:
            raise SystemExit(f"Required column {col!r} not found in {args.input_csv}")

    forecast_start = parse_dt(args.forecast_start_date)
    forecast_end = parse_dt(args.forecast_end_date)
    focus_start = parse_optional_dt(args.focus_start_date)
    focus_end = parse_optional_dt(args.focus_end_date)

    selected: list[dict[str, str]] = []
    historical_values: list[float] = []
    historical_count = 0
    forecast_count = 0
    for row in rows:
        dt = parse_dt(row["date"])
        mag = to_float(row, "mag")
        is_forecast = in_window(dt, forecast_start, forecast_end)
        is_event = mag >= float(args.event_mag_threshold)
        if not is_event and not is_forecast:
            continue
        out = dict(row)
        raw_value = to_float(row, args.target_source)
        out["location_phase"] = "forecast" if is_forecast and not is_event else "event"
        out["location_source_value"] = f"{raw_value:.12g}"
        if is_forecast and not is_event:
            out[args.target_name] = f"{float(args.forecast_target_fill):.12g}"
            forecast_count += 1
        else:
            historical_values.append(raw_value)
            historical_count += 1
            # Filled after analog min/max are known.
            out[args.target_name] = ""
        selected.append(out)

    if historical_count == 0:
        raise SystemExit(
            f"No historical seismic rows found with mag >= {args.event_mag_threshold}"
        )
    if forecast_count == 0:
        raise SystemExit("No forecast rows found in requested forecast window")

    n_test = max(1, min(max(4, int(args.validation_event_count)), historical_count - 1))
    n_train = max(1, historical_count - n_test)
    lo = args.clip_min
    hi = args.clip_max
    threshold_info: dict[str, object] = {}
    resolved_decision_threshold = None
    if args.mode == "analog":
        if args.decision_threshold is not None and str(args.decision_threshold).strip():
            try:
                resolved_decision_threshold, threshold_info = resolve_decision_threshold(
                    args.decision_threshold,
                    historical_values,
                    n_test,
                    args.binary_direction,
                )
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc
        if lo is None:
            lo = min(historical_values)
        if hi is None:
            hi = max(historical_values)
        if hi <= lo:
            raise SystemExit(f"Invalid analog range: min={lo} max={hi}")
        for row in selected:
            if row[args.target_name] != "":
                continue
            raw_value = to_float(row, args.target_source)
            clipped = clip(raw_value, float(lo), float(hi))
            if args.analog_scale == "minmax":
                value = (clipped - float(lo)) / (float(hi) - float(lo))
            else:
                value = clipped
            row[args.target_name] = f"{value:.12g}"
    else:
        try:
            resolved_decision_threshold, threshold_info = resolve_decision_threshold(
                args.decision_threshold,
                historical_values,
                n_test,
                args.binary_direction,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        for row in selected:
            if row[args.target_name] != "":
                continue
            raw_value = to_float(row, args.target_source)
            if args.binary_direction == "above":
                value = 1.0 if raw_value >= float(resolved_decision_threshold) else 0.0
            else:
                value = 1.0 if raw_value <= float(resolved_decision_threshold) else 0.0
            row[args.target_name] = f"{value:.12g}"

    out_header = list(header)
    for extra in ("location_phase", "location_source_value", args.target_name):
        if extra not in out_header:
            out_header.append(extra)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_header)
        writer.writeheader()
        writer.writerows(selected)

    skip_cols = sorted((SEISMIC_COLS | {"date", "location_phase", "location_source_value"}) - {args.target_name})
    payload = {
        "input_csv": str(args.input_csv),
        "output_csv": str(args.output_csv),
        "target_source": args.target_source,
        "target_name": args.target_name,
        "mode": args.mode,
        "event_mag_threshold": float(args.event_mag_threshold),
        "historical_event_rows": int(historical_count),
        "forecast_rows": int(forecast_count),
        "total_rows": int(len(selected)),
        "forecast_start_date": args.forecast_start_date,
        "forecast_end_date": args.forecast_end_date,
        "focus_start_date": args.focus_start_date,
        "focus_end_date": args.focus_end_date,
        "recommended_n_train": int(n_train),
        "recommended_n_test": int(n_test),
        "skip_cols_list": ",".join(skip_cols),
        "analog_scale": args.analog_scale,
        "clip_min": None if lo is None else float(lo),
        "clip_max": None if hi is None else float(hi),
        "forecast_target_fill": float(args.forecast_target_fill),
        "decision_threshold": resolved_decision_threshold,
        "decision_threshold_requested": args.decision_threshold,
        "decision_threshold_info": threshold_info,
        "binary_direction": args.binary_direction,
        "note": (
            "Historical training/validation rows are seismic-only. Forecast rows are kept "
            "only to project the requested time grid; seismic columns are skipped as features."
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
