#!/usr/bin/env python3
"""Select the strongest forecast slot and export its bounded focus window."""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


DATE_COLUMNS = ("date", "context", "time", "datetime")
SCORE_COLUMNS = ("predicted", "pred_recalibrated", "pred", "score")


def parse_dt(value: str) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    try:
        result = datetime.fromisoformat(text)
    except ValueError:
        result = datetime.strptime(text[:10], "%Y-%m-%d")
    return result.replace(tzinfo=None)


def choose_column(fieldnames: list[str], requested: str, candidates: tuple[str, ...]) -> str:
    if requested != "auto":
        if requested not in fieldnames:
            raise ValueError(f"column {requested!r} not found")
        return requested
    for candidate in candidates:
        if candidate in fieldnames:
            return candidate
    raise ValueError(f"none of the expected columns found: {', '.join(candidates)}")


def finite_float(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def select_focus(
    forecast_csv: Path,
    output_json: Path,
    output_env: Path,
    forecast_start: datetime,
    forecast_end: datetime,
    date_column: str,
    score_column: str,
    cadence_days: int | None,
) -> dict[str, object]:
    with forecast_csv.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if not rows:
        raise ValueError("forecast CSV is empty")

    dcol = choose_column(fieldnames, date_column, DATE_COLUMNS)
    scol = choose_column(fieldnames, score_column, SCORE_COLUMNS)
    candidates: list[tuple[datetime, float, dict[str, str]]] = []
    all_dates: list[datetime] = []
    for row in rows:
        dt = parse_dt(row[dcol])
        score = finite_float(row.get(scol))
        if score is None:
            continue
        all_dates.append(dt)
        if forecast_start.date() <= dt.date() <= forecast_end.date():
            candidates.append((dt, score, row))
    if not candidates:
        raise ValueError("no finite forecast rows fall inside the requested window")

    if cadence_days is None:
        unique_dates = sorted(set(all_dates))
        diffs = [
            (right.date() - left.date()).days
            for left, right in zip(unique_dates, unique_dates[1:])
            if (right.date() - left.date()).days > 0
        ]
        cadence_days = Counter(diffs).most_common(1)[0][0] if diffs else 7
    if cadence_days <= 0:
        raise ValueError("cadence days must be positive")

    peak_dt, peak_score, peak_row = max(candidates, key=lambda item: (item[1], -item[0].timestamp()))
    focus_end = min(
        peak_dt + timedelta(days=cadence_days - 1),
        forecast_end,
    )
    ranked = sorted(candidates, key=lambda item: (-item[1], item[0]))
    payload: dict[str, object] = {
        "forecast_csv": str(forecast_csv),
        "date_column": dcol,
        "score_column": scol,
        "forecast_start_date": forecast_start.date().isoformat(),
        "forecast_end_date": forecast_end.date().isoformat(),
        "cadence_days": cadence_days,
        "candidate_rows": len(candidates),
        "focus_start_date": peak_dt.date().isoformat(),
        "focus_end_date": focus_end.date().isoformat(),
        "peak_score": peak_score,
        "peak_row_index": peak_row.get("row_index", ""),
        "ranking": [
            {"date": dt.date().isoformat(), "score": score}
            for dt, score, _ in ranked
        ],
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    output_env.parent.mkdir(parents=True, exist_ok=True)
    output_env.write_text(
        f"FOCUS_START={payload['focus_start_date']}\n"
        f"FOCUS_END={payload['focus_end_date']}\n"
        f"TIMING_PEAK_SCORE={peak_score:.12g}\n"
        f"TIMING_CADENCE_DAYS={cadence_days}\n"
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forecast-csv", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-env", required=True, type=Path)
    parser.add_argument("--forecast-start-date", required=True)
    parser.add_argument("--forecast-end-date", required=True)
    parser.add_argument("--date-column", default="auto")
    parser.add_argument("--score-column", default="auto")
    parser.add_argument("--cadence-days", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        payload = select_focus(
            forecast_csv=args.forecast_csv,
            output_json=args.output_json,
            output_env=args.output_env,
            forecast_start=parse_dt(args.forecast_start_date),
            forecast_end=parse_dt(args.forecast_end_date),
            date_column=args.date_column,
            score_column=args.score_column,
            cadence_days=args.cadence_days,
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"ERROR select_forecast_focus_window: {exc}") from exc
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
