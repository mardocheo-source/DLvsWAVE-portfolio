#!/usr/bin/env python3
"""Infer reader-facing interval terminology from a report date grid.

The report renderer uses this module instead of embedding words such as
"weekly" or "monthly". Calendar-month grids are detected with calendar
offsets; fixed-duration grids are detected from the median exact difference.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class TimeScale:
    kind: str
    count: int
    unit: str
    display_singular: str
    display_plural: str
    resolution_text: str
    calendar_months: int = 0
    fixed_days: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def _number_word(value: int) -> str:
    words = {
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
        6: "six",
        7: "seven",
        8: "eight",
        9: "nine",
        10: "ten",
        11: "eleven",
        12: "twelve",
    }
    return words.get(value, str(value))


def _calendar_month_count(starts: list[pd.Timestamp]) -> int:
    if len(starts) < 2:
        return 0
    for months in range(1, 25):
        if all(
            right == left + pd.DateOffset(months=months)
            for left, right in zip(starts[:-1], starts[1:])
        ):
            return months
    return 0


def infer_time_scale(
    dates: Iterable,
    *,
    override_days: int | None = None,
    override_months: int | None = None,
) -> TimeScale:
    """Return terminology and interval arithmetic for an ordered date grid."""
    starts = sorted(set(pd.to_datetime(list(dates))))
    if override_months:
        months = int(override_months)
    else:
        months = _calendar_month_count(starts)
    if months:
        if months == 1:
            return TimeScale(
                kind="calendar_month",
                count=1,
                unit="month",
                display_singular="monthly interval",
                display_plural="monthly intervals",
                resolution_text="one calendar month",
                calendar_months=1,
            )
        word = _number_word(months)
        return TimeScale(
            kind="calendar_month",
            count=months,
            unit="months",
            display_singular=f"{word}-month interval",
            display_plural=f"{word}-month intervals",
            resolution_text=f"{word} calendar months",
            calendar_months=months,
        )

    if override_days:
        days = int(override_days)
    elif len(starts) >= 2:
        differences = pd.Series(starts).diff().dropna().dt.days
        days = int(round(float(differences.median())))
    else:
        days = 1
    if days <= 0:
        raise ValueError(f"Interval duration must be positive, received {days}")
    if days == 1:
        return TimeScale(
            kind="fixed_day",
            count=1,
            unit="day",
            display_singular="daily interval",
            display_plural="daily intervals",
            resolution_text="one day",
            fixed_days=1,
        )
    if days == 7:
        return TimeScale(
            kind="fixed_day",
            count=7,
            unit="days",
            display_singular="seven-day interval",
            display_plural="seven-day intervals",
            resolution_text="seven days",
            fixed_days=7,
        )
    word = _number_word(days)
    return TimeScale(
        kind="fixed_day",
        count=days,
        unit="days",
        display_singular=f"{word}-day interval",
        display_plural=f"{word}-day intervals",
        resolution_text=f"{word} days",
        fixed_days=days,
    )


def interval_end(start, scale: TimeScale) -> pd.Timestamp:
    value = pd.Timestamp(start)
    if scale.calendar_months:
        return value + pd.DateOffset(months=scale.calendar_months)
    return value + pd.Timedelta(days=scale.fixed_days)


def interval_label(start, scale: TimeScale, *, multiline: bool = False) -> str:
    beginning = pd.Timestamp(start)
    ending = interval_end(beginning, scale)
    separator = " –\n" if multiline else " – "
    return f"[{beginning:%Y-%m-%d}{separator}{ending:%Y-%m-%d})"

