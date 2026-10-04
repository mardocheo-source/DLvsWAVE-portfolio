"""Naming convention validation, parser and column reordering for DLVS-Wave v2.0.

Standard format:
  <prefix>_<group/body>_<metric/feature>_<suffix/aggregation>_<shift_tag>

Examples:
  - Seismic core:
      seis_core_magnitude
      seis_core_latitude
      seis_core_longitude
      seis_core_depth
  - Astronomical:
      astro_moon_ra_icrf
      astro_sun_dist
      astro_jupiter_eclipse_flag
  - Shifts (Historical Lag & Future Lead):
      astro_moon_dist_shift_m7d    (7 days past lag)
      astro_sun_dec_shift_p14d     (14 days future lead)
      seis_core_magnitude_shift_m30d (30 days past seismic lag)
  - Summaries:
      astro_moon_ra_icrf_mean
      astro_sun_dist_max
      seis_core_magnitude_max
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

import pandas as pd

DEFAULT_SEISMIC_CORE_FIELDS = (
    "seis_core_magnitude",
    "seis_core_latitude",
    "seis_core_longitude",
    "seis_core_depth",
)

SEISMIC_CORE_FIELDS = (
    "seis_core_magnitude",
    "seis_core_latitude",
    "seis_core_longitude",
    "seis_core_depth",
)

STANDARD_AGGREGATIONS = ("min", "max", "mean", "median")
INDEX_FIELDS = ("date", "time")
SHIFT_REGEX = re.compile(r"_shift_([mp])(\d+)([a-zA-Z]*)$")


@dataclass(frozen=True)
class ParsedField:
    original_name: str
    prefix: str
    group_or_body: str
    metric: str
    aggregation: str | None = None
    shift_direction: str | None = None  # "past" (m) or "future" (p)
    shift_steps: int = 0
    shift_unit: str = "d"

    @property
    def group_key(self) -> str:
        return f"{self.prefix}_{self.group_or_body}"

    @property
    def is_future_shift(self) -> bool:
        return self.shift_direction == "future"

    @property
    def is_past_shift(self) -> bool:
        return self.shift_direction == "past"

    @property
    def is_seismic(self) -> bool:
        return self.prefix == "seis"

    @property
    def is_astronomical(self) -> bool:
        return self.prefix == "astro"


def parse_field_name(name: str) -> ParsedField | None:
    """Parses standard field name into structured components."""
    if name in INDEX_FIELDS or name.startswith("packed_"):
        return None

    # 1. Extract and strip shift tag if present
    shift_dir = None
    shift_steps = 0
    shift_unit = "d"
    base_name = name

    shift_match = SHIFT_REGEX.search(name)
    if shift_match:
        dir_char, steps_str, unit_str = shift_match.groups()
        shift_dir = "future" if dir_char == "p" else "past"
        shift_steps = int(steps_str)
        shift_unit = unit_str if unit_str else "d"
        base_name = name[:shift_match.start()]

    parts = base_name.split("_")
    if len(parts) < 3:
        return None

    prefix = parts[0]
    group_or_body = parts[1]

    # Check aggregation suffix
    aggregation = None
    if parts[-1] in STANDARD_AGGREGATIONS and len(parts) >= 4:
        aggregation = parts[-1]
        metric = "_".join(parts[2:-1])
    else:
        metric = "_".join(parts[2:])

    return ParsedField(
        original_name=name,
        prefix=prefix,
        group_or_body=group_or_body,
        metric=metric,
        aggregation=aggregation,
        shift_direction=shift_dir,
        shift_steps=shift_steps,
        shift_unit=shift_unit,
    )


def build_field_name(
    prefix: str,
    body: str | None = None,
    metric: str = "",
    aggregation: str | None = None,
    shift_days: int | None = None,
    group_or_body: str | None = None,
) -> str:
    """Constructs standard field name."""
    clean_prefix = prefix.strip().lower()
    target_body = (group_or_body or body or "").strip().lower()
    clean_metric = metric.strip().lower()

    name = f"{clean_prefix}_{target_body}_{clean_metric}"
    if aggregation:
        name = f"{name}_{aggregation.strip().lower()}"

    if shift_days is not None and shift_days != 0:
        dir_tag = "p" if shift_days > 0 else "m"
        name = f"{name}_shift_{dir_tag}{abs(shift_days)}d"

    return name


def validate_column_names(columns: Sequence[str]) -> tuple[bool, list[str]]:
    """Validates list of columns against DLVS-Wave v2.0 standard."""
    invalid = []
    for col in columns:
        if col in INDEX_FIELDS or col.startswith("packed_") or col in SEISMIC_CORE_FIELDS:
            continue
        parsed = parse_field_name(col)
        if parsed is None or parsed.prefix not in ("astro", "seis", "custom"):
            invalid.append(col)
    return len(invalid) == 0, invalid


def order_master_columns(columns: Sequence[str]) -> list[str]:
    """Orders dataset columns so date and all seismic fields appear first for immediate inspection.

    Canonical Order:
      1. Index: date (and time if present)
      2. Primary Seismic Core: seis_core_magnitude, seis_core_latitude, seis_core_longitude, seis_core_depth
      3. Other Seismic Base / Summarized metrics (e.g. seis_core_magnitude_max, seis_core_magnitude_mean...)
      4. Seismic Historical Shift/Lag indices (e.g. seis_core_magnitude_shift_m7d...)
      5. Astronomical Base & Aggregated metrics (astro_*)
      6. Astronomical Shift features (astro_*_shift_*)
      7. Packed Astro Containers (packed_astro_container_*)
      8. Any remaining columns
    """
    col_set = set(columns)

    # 1. Index
    idx_cols = [c for c in ("date", "time") if c in col_set]

    # 2. Seismic Core Primary
    primary_seis = [
        c for c in ("seis_core_magnitude", "seis_core_latitude", "seis_core_longitude", "seis_core_depth")
        if c in col_set
    ]

    # 3. Other Seismic Base / Aggregated (non-shifted)
    other_seis = [
        c for c in columns
        if c.startswith("seis_") and c not in primary_seis and "_shift_" not in c
    ]

    # 4. Seismic Shifts / Historical Lags
    seis_shifts = [
        c for c in columns
        if c.startswith("seis_") and "_shift_" in c
    ]

    # 5. Astro Base / Aggregated
    astro_base = [
        c for c in columns
        if c.startswith("astro_") and "_shift_" not in c
    ]

    # 6. Astro Shifts
    astro_shifts = [
        c for c in columns
        if c.startswith("astro_") and "_shift_" in c
    ]

    # 7. Packed Containers
    packed_cols = [
        c for c in columns
        if c.startswith("packed_")
    ]

    # 8. Remaining
    used = set(idx_cols + primary_seis + other_seis + seis_shifts + astro_base + astro_shifts + packed_cols)
    remaining = [c for c in columns if c not in used]

    return idx_cols + primary_seis + other_seis + seis_shifts + astro_base + astro_shifts + packed_cols + remaining


def reorder_master_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Reorders DataFrame columns according to canonical master ordering."""
    ordered_cols = order_master_columns(df.columns)
    return df[ordered_cols].copy()
