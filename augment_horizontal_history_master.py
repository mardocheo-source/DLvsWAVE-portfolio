#!/usr/bin/env python3
"""Add compact horizontal-history features to a DLvsWAVE master CSV.

The row date stays real.  Time travel is represented only by extra numeric
columns sampled from a historical lookup date, so forecast rows remain readable
on the current timeline.
"""

from __future__ import annotations

import argparse
import bisect
import json
import math
import random
import re
import warnings
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import pandas as pd


PHI = (1.0 + math.sqrt(5.0)) / 2.0
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Add binary target and horizontal ribbon-history columns.")
    p.add_argument("--input-csv", required=True)
    p.add_argument("--output-csv", required=True)
    p.add_argument("--manifest-json", default="")
    p.add_argument("--events-csv", required=True, help="USGS-like CSV with time,mag,depth,latitude,longitude")
    p.add_argument("--min-mag", type=float, default=8.5)
    p.add_argument("--binary-target-col", default="target")
    p.add_argument("--binary-source-col", default="mag",
                   help="Analog column used to build the binary target; default: mag.")
    p.add_argument("--binary-threshold", type=float, default=None,
                   help="Threshold applied to --binary-source-col; default: --min-mag for mag, 0 for others.")
    p.add_argument("--binary-operator", default=">=", choices=[">=", ">", "<=", "<", "==", "!="],
                   help="Operator used to binarize source >= threshold by default.")
    p.add_argument("--row-filter", default="auto",
                   help=("Historical row filter for extra training rows. Sparse event context "
                         "is preserved automatically. Use auto, none, or expressions like "
                         "'latitude:(>11 and <23); longitude:(<150)'."))
    p.add_argument("--forecast-filter", default="none",
                   help="Optional filter applied also to forecast rows; default none keeps future rows free.")
    p.add_argument("--zones-csv", default="",
                   help="Optional CSV of named regions with lat/lon/depth bounds.")
    p.add_argument("--target-region", default="",
                   help=("Optional target region. Accepts a filter expression, or comma-separated "
                         "zone ids/names from --zones-csv. Target=1 requires source threshold and region match."))
    p.add_argument("--target-zones", default="",
                   help="Comma-separated zone ids/names from --zones-csv; treated as one macro region.")
    p.add_argument("--out-of-region-mode", default="keep",
                   choices=["keep", "neutralize-seismic"],
                   help="How to keep historical rows outside target region. Default keep; neutralize-seismic sets seismic cols to neutral.")
    p.add_argument("--out-of-region-neutralize-cols", default="mag,depth,latitude,longitude",
                   help="Columns neutralized by --out-of-region-mode neutralize-seismic.")

    p.add_argument("--history-mode", default="none",
                   choices=["none", "constant-days", "constant-years", "geometric-archimede", "fibonacci-gold"])
    p.add_argument("--history-value", type=float, default=1280.0)
    p.add_argument("--history-spacer-days", type=float, default=0.0)
    p.add_argument("--enable-seismic-history", action="store_true")
    p.add_argument("--enable-astro-history", action="store_true")
    p.add_argument("--astro-bodies", default="301,599,99942",
                   help="Comma/space-separated body ids present in master columns; default Moon,Jupiter,Apophis.")
    p.add_argument("--astro-fields", default="RA,DEC,r,r_rate,ObsEclLon,ObsEclLat")

    p.add_argument("--negative-sampling-mode", default="none", choices=["none", "random-sparse"])
    p.add_argument("--random-negatives-per-positive", type=int, default=8)
    p.add_argument("--random-negative-seed", type=int, default=20260608)
    p.add_argument("--keep-neighbor-records", type=int, default=2,
                   help="Keep this many rows before/after each positive before random negative sampling.")
    p.add_argument("--keep-recent-negatives", type=int, default=6,
                   help="Keep last N negative rows before forecast start when sparse sampling is active.")
    p.add_argument("--forecast-start-date", default="")
    p.add_argument("--forecast-end-date", default="")
    p.add_argument("--forecast-target-value", type=float, default=0.0,
                   help="Placeholder target value for forecast rows; default 0 keeps final plots readable.")
    return p.parse_args()


@dataclass
class FilterSpec:
    raw: str
    mode: str
    groups: list[dict[str, list[tuple[str, float]]]]

    @property
    def clauses(self) -> dict[str, list[tuple[str, float]]]:
        if not self.groups:
            return {}
        return self.groups[0]


def resolve_binary_threshold(source_col: str, threshold: float | None, min_mag: float) -> float:
    if threshold is not None:
        return float(threshold)
    if source_col.strip().lower() == "mag":
        return float(min_mag)
    return 0.0


def compare_values(series: pd.Series, op: str, threshold: float) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if op == ">=":
        return values >= threshold
    if op == ">":
        return values > threshold
    if op == "<=":
        return values <= threshold
    if op == "<":
        return values < threshold
    if op == "==":
        return values == threshold
    if op == "!=":
        return values != threshold
    raise ValueError(f"Unsupported operator: {op}")


def parse_filter_spec(text: str) -> FilterSpec:
    raw = str(text or "").strip()
    if not raw:
        raw = "auto"
    lower = raw.lower()
    if lower in {"auto", "none", "off", "false", "0"}:
        mode = "none" if lower in {"none", "off", "false", "0"} else "auto"
        return FilterSpec(raw=raw, mode=mode, groups=[])

    groups: list[dict[str, list[tuple[str, float]]]] = []
    pattern = re.compile(r"^(>=|<=|>|<|==|!=)\s*(-?\d+(?:\.\d+)?)$")
    group_texts = [g.strip() for g in re.split(r"\bor\b", raw, flags=re.IGNORECASE) if g.strip()]
    for group_text in group_texts:
        clauses: dict[str, list[tuple[str, float]]] = {}
        parts = [p.strip() for p in group_text.split(";") if p.strip()]
        for part in parts:
            if ":" not in part:
                raise ValueError(f"Invalid filter clause {part!r}; expected column:(>a and <b)")
            col, expr = part.split(":", 1)
            col = col.strip()
            expr = expr.strip().strip("()")
            conditions = [c.strip() for c in re.split(r"\band\b", expr, flags=re.IGNORECASE) if c.strip()]
            if not col or not conditions:
                raise ValueError(f"Invalid filter clause {part!r}")
            parsed = []
            for cond in conditions:
                m = pattern.match(cond)
                if not m:
                    raise ValueError(f"Invalid filter condition {cond!r} in {part!r}")
                parsed.append((m.group(1), float(m.group(2))))
            clauses[col] = parsed
        if clauses:
            groups.append(clauses)
    if not groups:
        raise ValueError(f"Invalid filter expression: {raw!r}")
    return FilterSpec(raw=raw, mode="expr", groups=groups)


def load_zone_specs(zones_csv: str) -> dict[str, dict]:
    if not zones_csv:
        return {}
    path = Path(zones_csv)
    if not path.exists():
        raise FileNotFoundError(f"Zones CSV not found: {path}")
    zones = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {"zone_id", "latitude_min", "latitude_max", "longitude_min", "longitude_max"}
    missing = required - set(zones.columns)
    if missing:
        raise ValueError(f"Zones CSV missing required columns: {sorted(missing)}")

    out: dict[str, dict] = {}
    for _, row in zones.iterrows():
        zone_id = str(row.get("zone_id", "")).strip()
        name = str(row.get("name", "")).strip()
        if not zone_id:
            continue
        spec = {
            "zone_id": zone_id,
            "name": name,
            "latitude_min": float(row["latitude_min"]),
            "latitude_max": float(row["latitude_max"]),
            "longitude_min": float(row["longitude_min"]),
            "longitude_max": float(row["longitude_max"]),
            "depth_min": None,
            "depth_max": None,
        }
        for key in ("depth_min", "depth_max"):
            raw = str(row.get(key, "")).strip()
            if raw:
                spec[key] = float(raw)
        out[zone_id.lower()] = spec
        if name:
            out[name.lower()] = spec
    return out


def zone_to_group(zone: dict) -> dict[str, list[tuple[str, float]]]:
    group: dict[str, list[tuple[str, float]]] = {
        "latitude": [
            (">=", float(zone["latitude_min"])),
            ("<=", float(zone["latitude_max"])),
        ],
        "longitude": [
            (">=", float(zone["longitude_min"])),
            ("<=", float(zone["longitude_max"])),
        ],
    }
    if zone.get("depth_min") is not None:
        group.setdefault("depth", []).append((">=", float(zone["depth_min"])))
    if zone.get("depth_max") is not None:
        group.setdefault("depth", []).append(("<=", float(zone["depth_max"])))
    return group


def resolve_region_spec(target_region: str, target_zones: str, zones_csv: str) -> tuple[FilterSpec, dict]:
    raw_region = str(target_region or "").strip()
    raw_zones = str(target_zones or "").strip()
    if not raw_region and not raw_zones:
        return FilterSpec(raw="", mode="none", groups=[]), {
            "mode": "none",
            "target_region": "",
            "target_zones": [],
            "zones_csv": zones_csv,
            "resolved_zones": [],
        }

    zones = load_zone_specs(zones_csv) if zones_csv else {}
    zone_tokens = split_tokens(raw_zones)
    expression = raw_region
    looks_like_expression = any(token in raw_region for token in (":", ">", "<", "==", "!="))
    if raw_region and not looks_like_expression:
        zone_tokens.extend(split_tokens(raw_region))
        expression = ""

    resolved_zones = []
    groups: list[dict[str, list[tuple[str, float]]]] = []
    if zone_tokens:
        if not zones:
            raise ValueError("--target-zones/zone-name --target-region requires --zones-csv")
        for token in zone_tokens:
            key = token.strip().lower()
            if key not in zones:
                raise ValueError(f"Zone not found in {zones_csv}: {token}")
            zone = zones[key]
            groups.append(zone_to_group(zone))
            resolved_zones.append(zone)

    if expression:
        spec = parse_filter_spec(expression)
        groups.extend(spec.groups)

    if not groups:
        return FilterSpec(raw="", mode="none", groups=[]), {
            "mode": "none",
            "target_region": raw_region,
            "target_zones": zone_tokens,
            "zones_csv": zones_csv,
            "resolved_zones": resolved_zones,
        }
    spec_raw = raw_region or raw_zones
    return FilterSpec(raw=spec_raw, mode="expr", groups=groups), {
        "mode": "expr",
        "target_region": raw_region,
        "target_zones": zone_tokens,
        "zones_csv": zones_csv,
        "resolved_zones": resolved_zones,
        "groups": groups,
    }


def apply_filter_spec(df: pd.DataFrame, spec: FilterSpec, *, source_col: str,
                      dates: pd.Series, forecast_start: str, forecast_end: str,
                      apply_to_forecast: bool) -> tuple[pd.Series, dict]:
    mask = pd.Series(True, index=df.index)
    details = {
        "raw": spec.raw,
        "mode": spec.mode,
        "apply_to_forecast": bool(apply_to_forecast),
        "groups": spec.groups,
        "clauses": spec.clauses,
        "auto_rule": "",
    }

    if spec.mode == "auto":
        if source_col.strip().lower() in {"latitude", "longitude", "depth"}:
            if "mag" not in df.columns:
                raise ValueError("row-filter auto for location targets requires mag column")
            mask &= pd.to_numeric(df["mag"], errors="coerce").fillna(0.0) > 0.0
            details["auto_rule"] = "location target: keep historical seismic rows where mag > 0"
        else:
            details["auto_rule"] = "no historical filter for this target source"
    elif spec.mode == "expr":
        mask = pd.Series(False, index=df.index)
        for group in spec.groups:
            group_mask = pd.Series(True, index=df.index)
            for col, conditions in group.items():
                if col not in df.columns:
                    raise ValueError(f"Filter column not found in master: {col}")
                for op, threshold in conditions:
                    group_mask &= compare_values(df[col], op, threshold).fillna(False)
            mask |= group_mask

    if not apply_to_forecast and forecast_start:
        start = pd.Timestamp(forecast_start)
        end = pd.Timestamp(forecast_end) if forecast_end else dates.max()
        forecast_mask = (dates >= start) & (dates <= end)
        mask |= forecast_mask
        details["forecast_rows_forced_kept"] = int(forecast_mask.sum())
    else:
        details["forecast_rows_forced_kept"] = 0
    details["kept_rows"] = int(mask.sum())
    details["dropped_rows"] = int((~mask).sum())
    return mask, details


def compute_days_back(mode: str, value: float, spacer_days: float) -> float:
    if mode == "none":
        return 0.0
    if mode == "constant-days":
        base = value
    elif mode == "constant-years":
        base = value * 365.25
    elif mode == "geometric-archimede":
        base = value * math.pi
    elif mode == "fibonacci-gold":
        base = value * PHI
    else:
        raise ValueError(f"Unsupported history mode: {mode}")
    return float(base + spacer_days)


def split_tokens(text: str) -> list[str]:
    return [x for x in re.split(r"[,\s]+", str(text or "").strip()) if x]


def safe_token(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", str(text)).strip("_")


def event_time_series(events_csv: Path) -> pd.DataFrame:
    usecols = ["time", "mag", "depth", "latitude", "longitude"]
    try:
        events = pd.read_csv(events_csv, usecols=usecols)
    except ValueError:
        events = pd.read_csv(events_csv)
        missing = [c for c in usecols if c not in events.columns]
        if missing:
            raise ValueError(f"Events CSV missing required columns: {missing}")
        events = events[usecols]

    events["time"] = pd.to_datetime(events["time"].astype(str), errors="coerce", utc=True).dt.tz_convert(None)
    for col in ["mag", "depth", "latitude", "longitude"]:
        events[col] = pd.to_numeric(events[col], errors="coerce")
    events = events.dropna(subset=usecols).sort_values("time").reset_index(drop=True)
    return events


def nearest_indices(dates: pd.Series, target_dates: pd.Series) -> np.ndarray:
    # Dates are expected sorted.  Pick the closest available master row to the
    # historical lookup date, so sparse masters still have deterministic history.
    values = dates.astype("int64").to_numpy()
    targets = target_dates.astype("int64").to_numpy()
    out = np.empty(len(targets), dtype=int)
    for i, target in enumerate(targets):
        pos = int(np.searchsorted(values, target, side="left"))
        if pos <= 0:
            out[i] = 0
        elif pos >= len(values):
            out[i] = len(values) - 1
        else:
            before = values[pos - 1]
            after = values[pos]
            out[i] = pos - 1 if abs(target - before) <= abs(after - target) else pos
    return out


def angular_sep_deg(ra1, dec1, ra2, dec2) -> np.ndarray:
    def numeric_array(values) -> np.ndarray:
        return pd.to_numeric(pd.Series(values), errors="coerce").fillna(0.0).to_numpy(dtype=float)

    ra1 = np.deg2rad(numeric_array(ra1))
    dec1 = np.deg2rad(numeric_array(dec1))
    ra2 = np.deg2rad(numeric_array(ra2))
    dec2 = np.deg2rad(numeric_array(dec2))
    cos_sep = np.sin(dec1) * np.sin(dec2) + np.cos(dec1) * np.cos(dec2) * np.cos(ra1 - ra2)
    cos_sep = np.clip(cos_sep, -1.0, 1.0)
    return np.rad2deg(np.arccos(cos_sep))


def find_astro_column(columns: list[str], body: str, field: str) -> str | None:
    """Resolve legacy and astrofmt column names for a body/ephemeris field."""
    body = str(body)
    field = str(field)
    exact = f"{body}_at0_{field}"
    if exact in columns:
        return exact

    astrofmt_re = re.compile(
        rf"^body:{re.escape(body)}\|.*\|eph:{re.escape(field)}\|op:val$"
    )
    matches = [col for col in columns if astrofmt_re.match(col)]
    if matches:
        return sorted(matches)[0]

    raw_suffix = f"_{field}"
    raw_matches = [
        col for col in columns
        if col.startswith(f"{body}_") and col.endswith(raw_suffix)
    ]
    if raw_matches:
        return sorted(raw_matches)[0]

    return None


def add_seismic_history(df: pd.DataFrame, dates: pd.Series, lookup_dates: pd.Series,
                        events: pd.DataFrame) -> list[str]:
    added = []
    event_times = list(events["time"])
    out = {
        "tt_seis_has_prior": [],
        "tt_seis_delta_days": [],
        "tt_seis_mag": [],
        "tt_seis_depth": [],
        "tt_seis_latitude": [],
        "tt_seis_longitude": [],
    }
    for lookup in lookup_dates:
        pos = bisect.bisect_right(event_times, pd.Timestamp(lookup)) - 1
        if pos < 0:
            out["tt_seis_has_prior"].append(0)
            out["tt_seis_delta_days"].append(999999.0)
            out["tt_seis_mag"].append(0.0)
            out["tt_seis_depth"].append(0.0)
            out["tt_seis_latitude"].append(0.0)
            out["tt_seis_longitude"].append(0.0)
            continue
        ev = events.iloc[pos]
        out["tt_seis_has_prior"].append(1)
        out["tt_seis_delta_days"].append(float((lookup - ev["time"]).total_seconds() / 86400.0))
        out["tt_seis_mag"].append(float(ev["mag"]))
        out["tt_seis_depth"].append(float(ev["depth"]))
        out["tt_seis_latitude"].append(float(ev["latitude"]))
        out["tt_seis_longitude"].append(float(ev["longitude"]))

    for col, values in out.items():
        df[col] = values
        added.append(col)
    return added


def add_astro_history(df: pd.DataFrame, past_idx: np.ndarray, bodies: list[str],
                      fields: list[str]) -> tuple[list[str], list[str]]:
    added: list[str] = []
    missing: list[str] = []
    source = df.copy()
    source_columns = list(source.columns)

    for body in bodies:
        body_safe = safe_token(body)
        copied_for_body = []
        for field in fields:
            col = find_astro_column(source_columns, body, field)
            if col is None:
                missing.append(f"{body}:{field}")
                continue
            out_col = f"tt_astro_{body_safe}_{field}"
            df[out_col] = pd.to_numeric(source[col].iloc[past_idx].to_numpy(), errors="coerce")
            added.append(out_col)
            copied_for_body.append((field, col, out_col))

        ra_col = find_astro_column(source_columns, body, "RA")
        dec_col = find_astro_column(source_columns, body, "DEC")
        az_col = find_astro_column(source_columns, body, "AZ")
        el_col = find_astro_column(source_columns, body, "EL")
        if ra_col is not None and dec_col is not None:
            stitch_col = f"tt_stitch_{body_safe}_radec_sep_deg"
            df[stitch_col] = angular_sep_deg(
                source[ra_col],
                source[dec_col],
                source[ra_col].iloc[past_idx].to_numpy(),
                source[dec_col].iloc[past_idx].to_numpy(),
            )
            added.append(stitch_col)
        elif az_col is not None and el_col is not None:
            stitch_col = f"tt_stitch_{body_safe}_azel_sep_deg"
            df[stitch_col] = angular_sep_deg(
                source[az_col],
                source[el_col],
                source[az_col].iloc[past_idx].to_numpy(),
                source[el_col].iloc[past_idx].to_numpy(),
            )
            added.append(stitch_col)
        elif copied_for_body:
            field, current_col, past_col = copied_for_body[0]
            stitch_col = f"tt_stitch_{body_safe}_{safe_token(field)}_delta"
            df[stitch_col] = (
                pd.to_numeric(source[current_col], errors="coerce").fillna(0.0).to_numpy(dtype=float)
                - pd.to_numeric(df[past_col], errors="coerce").fillna(0.0).to_numpy(dtype=float)
            )
            added.append(stitch_col)
        else:
            missing.append(f"{body}_at0_RA/DEC")

    return added, missing


def sparse_sample(df: pd.DataFrame, dates: pd.Series, binary_target_col: str, forecast_start: str,
                  forecast_end: str, per_positive: int, keep_neighbors: int,
                  keep_recent: int, seed: int) -> tuple[pd.DataFrame, dict]:
    target = pd.to_numeric(df[binary_target_col], errors="coerce").fillna(0.0)
    positive_idx = set(df.index[target >= 0.5].tolist())
    keep = set(positive_idx)
    event_context_idx = set(positive_idx)

    for idx in list(positive_idx):
        lo = max(0, int(idx) - keep_neighbors)
        hi = min(len(df) - 1, int(idx) + keep_neighbors)
        event_context_idx.update(range(lo, hi + 1))
    keep.update(event_context_idx)

    forecast_mask = pd.Series(False, index=df.index)
    if forecast_start:
        start = pd.Timestamp(forecast_start)
        end = pd.Timestamp(forecast_end) if forecast_end else dates.max()
        forecast_mask = (dates >= start) & (dates <= end)
        keep.update(df.index[forecast_mask].tolist())

    pre_forecast_mask = pd.Series(True, index=df.index)
    if forecast_start:
        pre_forecast_mask = dates < pd.Timestamp(forecast_start)

    neg_candidates = [
        int(i) for i in df.index[(target < 0.5) & pre_forecast_mask]
        if int(i) not in keep
    ]
    rng = random.Random(seed)
    rng.shuffle(neg_candidates)
    wanted = max(0, len(positive_idx) * int(per_positive))
    keep.update(neg_candidates[:wanted])

    if forecast_start and keep_recent > 0:
        recent = [
            int(i) for i in df.index[(target < 0.5) & pre_forecast_mask]
            if int(i) not in positive_idx
        ][-keep_recent:]
        keep.update(recent)

    kept_idx = sorted(keep)
    sampled = df.loc[kept_idx].reset_index(drop=True)
    stats = {
        "mode": "random-sparse",
        "input_rows": int(len(df)),
        "output_rows": int(len(sampled)),
        "positive_rows": int(len(positive_idx)),
        "forecast_rows_kept": int(forecast_mask.sum()),
        "random_negative_target": int(wanted),
        "keep_neighbor_records": int(keep_neighbors),
        "keep_recent_negatives": int(keep_recent),
        "seed": int(seed),
    }
    return sampled, stats


def sparse_context_preserve_mask(df: pd.DataFrame, dates: pd.Series, binary_target_col: str,
                                 forecast_start: str, forecast_end: str,
                                 keep_neighbors: int, keep_recent: int) -> tuple[pd.Series, dict]:
    """Rows that a row-filter must not remove before sparse sampling.

    This keeps the important "near but not event" teaching rows around each
    positive, plus forecast rows and the final pre-forecast negatives. Random
    in-between negatives are still chosen later by sparse_sample().
    """
    target = pd.to_numeric(df[binary_target_col], errors="coerce").fillna(0.0)
    positive_idx = set(df.index[target >= 0.5].tolist())
    keep = set(positive_idx)
    event_context_idx = set(positive_idx)

    for idx in list(positive_idx):
        lo = max(0, int(idx) - keep_neighbors)
        hi = min(len(df) - 1, int(idx) + keep_neighbors)
        event_context_idx.update(range(lo, hi + 1))
    keep.update(event_context_idx)

    forecast_mask = pd.Series(False, index=df.index)
    if forecast_start:
        start = pd.Timestamp(forecast_start)
        end = pd.Timestamp(forecast_end) if forecast_end else dates.max()
        forecast_mask = (dates >= start) & (dates <= end)
        keep.update(df.index[forecast_mask].tolist())

    pre_forecast_mask = pd.Series(True, index=df.index)
    if forecast_start:
        pre_forecast_mask = dates < pd.Timestamp(forecast_start)

    recent = []
    if forecast_start and keep_recent > 0:
        recent = [
            int(i) for i in df.index[(target < 0.5) & pre_forecast_mask]
            if int(i) not in positive_idx
        ][-keep_recent:]
        keep.update(recent)

    mask = pd.Series(False, index=df.index)
    if keep:
        mask.loc[sorted(keep)] = True
    stats = {
        "enabled": True,
        "positive_rows": int(len(positive_idx)),
        "event_context_rows": int(len(event_context_idx)),
        "forecast_rows": int(forecast_mask.sum()),
        "recent_negative_rows": int(len(recent)),
        "keep_neighbor_records": int(keep_neighbors),
        "keep_recent_negatives": int(keep_recent),
        "preserve_rows": int(mask.sum()),
    }
    return mask, stats


def main() -> None:
    args = parse_args()
    in_path = Path(args.input_csv)
    out_path = Path(args.output_csv)
    events_path = Path(args.events_csv)
    if not in_path.exists():
        raise FileNotFoundError(f"Input master not found: {in_path}")
    if not events_path.exists():
        raise FileNotFoundError(f"Events CSV not found: {events_path}")

    df = pd.read_csv(in_path)
    if "date" not in df.columns:
        raise ValueError("Input master must contain a date column.")
    if "mag" not in df.columns:
        raise ValueError("Input master must contain a mag column.")
    if args.binary_source_col not in df.columns:
        raise ValueError(f"Binary source column not found in master: {args.binary_source_col}")

    dates = pd.to_datetime(df["date"].astype(str), errors="coerce").dt.normalize()
    if dates.isna().any():
        raise ValueError("Input master contains invalid date values.")

    forecast_mask_for_target = pd.Series(False, index=df.index)
    if args.forecast_start_date:
        start = pd.Timestamp(args.forecast_start_date)
        end = pd.Timestamp(args.forecast_end_date) if args.forecast_end_date else dates.max()
        forecast_mask_for_target = (dates >= start) & (dates <= end)

    target_region_spec, target_region_stats = resolve_region_spec(
        args.target_region,
        args.target_zones,
        args.zones_csv,
    )
    if target_region_spec.mode == "expr":
        target_region_mask, region_apply_stats = apply_filter_spec(
            df,
            target_region_spec,
            source_col=args.binary_source_col,
            dates=dates,
            forecast_start="",
            forecast_end="",
            apply_to_forecast=True,
        )
        target_region_stats["kept_rows"] = int(target_region_mask.sum())
        target_region_stats["dropped_rows"] = int((~target_region_mask).sum())
        target_region_stats["apply_details"] = region_apply_stats
    else:
        target_region_mask = pd.Series(True, index=df.index)
        target_region_stats["kept_rows"] = int(len(df))
        target_region_stats["dropped_rows"] = 0

    binary_threshold = resolve_binary_threshold(args.binary_source_col, args.binary_threshold, args.min_mag)
    source_positive = compare_values(df[args.binary_source_col], args.binary_operator, binary_threshold).fillna(False)
    df[args.binary_target_col] = (source_positive & target_region_mask).astype(int)
    df.loc[forecast_mask_for_target, args.binary_target_col] = float(args.forecast_target_value)
    added_cols = [args.binary_target_col]

    days_back = compute_days_back(args.history_mode, args.history_value, args.history_spacer_days)
    lookup_dates = dates - pd.to_timedelta(days_back, unit="D")
    past_idx = nearest_indices(dates, lookup_dates)
    lookup_delta_days = (dates.iloc[past_idx].reset_index(drop=True) - lookup_dates.reset_index(drop=True)).dt.total_seconds() / 86400.0

    if args.history_mode != "none":
        df["tt_days_back"] = float(days_back)
        df["tt_lookup_delta_days"] = lookup_delta_days.to_numpy(dtype=float)
        added_cols.extend(["tt_days_back", "tt_lookup_delta_days"])

    events = event_time_series(events_path)
    if args.enable_seismic_history and args.history_mode != "none":
        added_cols.extend(add_seismic_history(df, dates, lookup_dates, events))

    missing_astro_cols: list[str] = []
    if args.enable_astro_history and args.history_mode != "none":
        bodies = split_tokens(args.astro_bodies)
        fields = split_tokens(args.astro_fields)
        astro_added, missing_astro_cols = add_astro_history(df, past_idx, bodies, fields)
        added_cols.extend(astro_added)

    row_filter_spec = parse_filter_spec(args.row_filter)
    row_mask, row_filter_stats = apply_filter_spec(
        df,
        row_filter_spec,
        source_col=args.binary_source_col,
        dates=dates,
        forecast_start=args.forecast_start_date,
        forecast_end=args.forecast_end_date,
        apply_to_forecast=False,
    )
    if args.negative_sampling_mode == "random-sparse":
        preserve_mask, preserve_stats = sparse_context_preserve_mask(
            df=df,
            dates=dates,
            binary_target_col=args.binary_target_col,
            forecast_start=args.forecast_start_date,
            forecast_end=args.forecast_end_date,
            keep_neighbors=args.keep_neighbor_records,
            keep_recent=args.keep_recent_negatives,
        )
        before_preserve = row_mask.copy()
        row_mask = row_mask | preserve_mask
        preserve_stats["forced_rows_after_row_filter"] = int((preserve_mask & ~before_preserve).sum())
        row_filter_stats["sparse_context_preserve"] = preserve_stats
        row_filter_stats["kept_rows_before_context_preserve"] = int(before_preserve.sum())
        row_filter_stats["kept_rows"] = int(row_mask.sum())
        row_filter_stats["dropped_rows"] = int((~row_mask).sum())
    else:
        row_filter_stats["sparse_context_preserve"] = {"enabled": False}
    forecast_filter_stats = {"raw": args.forecast_filter, "mode": "none", "applied": False}
    forecast_filter_spec = parse_filter_spec(args.forecast_filter)
    if forecast_filter_spec.mode != "none":
        if forecast_filter_spec.mode == "auto":
            forecast_filter_spec = FilterSpec(raw=args.forecast_filter, mode="none", groups=[])
        else:
            forecast_mask = pd.Series(False, index=df.index)
            if args.forecast_start_date:
                start = pd.Timestamp(args.forecast_start_date)
                end = pd.Timestamp(args.forecast_end_date) if args.forecast_end_date else dates.max()
                forecast_mask = (dates >= start) & (dates <= end)
            fc_mask, forecast_filter_stats = apply_filter_spec(
                df,
                forecast_filter_spec,
                source_col=args.binary_source_col,
                dates=dates,
                forecast_start="",
                forecast_end="",
                apply_to_forecast=True,
            )
            row_mask = (~forecast_mask & row_mask) | (forecast_mask & fc_mask)
            forecast_filter_stats["applied"] = True

    neutralized_cols: list[str] = []
    filtered_region_mask = target_region_mask.loc[row_mask].reset_index(drop=True)
    filtered_forecast_mask = forecast_mask_for_target.loc[row_mask].reset_index(drop=True)
    df = df.loc[row_mask].reset_index(drop=True)
    dates = dates.loc[row_mask].reset_index(drop=True)

    if target_region_spec.mode == "expr" and args.out_of_region_mode == "neutralize-seismic":
        neutralize_cols = split_tokens(args.out_of_region_neutralize_cols)
        neutralize_mask = (~filtered_region_mask) & (~filtered_forecast_mask)
        for col in neutralize_cols:
            if col in df.columns:
                df.loc[neutralize_mask, col] = 0.0
                neutralized_cols.append(col)

    sampling_stats = {"mode": "none", "input_rows": int(len(df)), "output_rows": int(len(df))}
    if args.negative_sampling_mode == "random-sparse":
        df, sampling_stats = sparse_sample(
            df=df,
            dates=dates,
            binary_target_col=args.binary_target_col,
            forecast_start=args.forecast_start_date,
            forecast_end=args.forecast_end_date,
            per_positive=args.random_negatives_per_positive,
            keep_neighbors=args.keep_neighbor_records,
            keep_recent=args.keep_recent_negatives,
            seed=args.random_negative_seed,
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    target = pd.to_numeric(df[args.binary_target_col], errors="coerce").fillna(0.0)
    manifest = {
        "input_csv": str(in_path),
        "output_csv": str(out_path),
        "events_csv": str(events_path),
        "min_mag": float(args.min_mag),
        "binary_target_col": args.binary_target_col,
        "binary_source_col": args.binary_source_col,
        "binary_threshold": float(binary_threshold),
        "binary_operator": args.binary_operator,
        "forecast_target_value": float(args.forecast_target_value),
        "forecast_target_rows": int(forecast_mask_for_target.sum()),
        "target_region": target_region_stats,
        "out_of_region_mode": args.out_of_region_mode,
        "out_of_region_neutralized_cols": neutralized_cols,
        "row_filter": row_filter_stats,
        "forecast_filter": forecast_filter_stats,
        "history_mode": args.history_mode,
        "history_value": float(args.history_value),
        "history_spacer_days": float(args.history_spacer_days),
        "days_back": float(days_back),
        "enable_seismic_history": bool(args.enable_seismic_history),
        "enable_astro_history": bool(args.enable_astro_history),
        "astro_bodies": split_tokens(args.astro_bodies),
        "astro_fields": split_tokens(args.astro_fields),
        "missing_astro_columns": missing_astro_cols,
        "added_columns": added_cols,
        "sampling": sampling_stats,
        "output_rows": int(len(df)),
        "output_positive_rows": int((target >= 0.5).sum()),
        "output_zero_or_negative_rows": int((target < 0.5).sum()),
    }
    if args.manifest_json:
        manifest_path = Path(args.manifest_json)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"[horizontal-history] input:  {in_path}")
    print(f"[horizontal-history] output: {out_path}")
    print(f"[horizontal-history] rows:   {len(df)}")
    print(
        f"[horizontal-history] target: {args.binary_target_col} = "
        f"{args.binary_source_col} {args.binary_operator} {binary_threshold} "
        f"positives={(target >= 0.5).sum()}"
    )
    print(f"[horizontal-history] row filter: {args.row_filter} kept={row_filter_stats['kept_rows']}")
    preserve = row_filter_stats.get("sparse_context_preserve", {})
    if preserve.get("enabled"):
        print(
            "[horizontal-history] sparse context preserved: "
            f"rows={preserve.get('preserve_rows', 0)} "
            f"forced={preserve.get('forced_rows_after_row_filter', 0)}"
        )
    if target_region_spec.mode != "none":
        print(f"[horizontal-history] target region: {target_region_stats['target_region'] or target_region_stats['target_zones']}")
    if neutralized_cols:
        print(f"[horizontal-history] out-of-region neutralized: {','.join(neutralized_cols)}")
    if forecast_filter_stats.get("applied"):
        print(f"[horizontal-history] forecast filter: {args.forecast_filter}")
    print(f"[horizontal-history] mode={args.history_mode} days_back={days_back:.6f}")
    print(f"[horizontal-history] added columns: {len(added_cols)}")
    if missing_astro_cols:
        print(f"[horizontal-history] missing astro columns: {len(missing_astro_cols)}")
    if args.manifest_json:
        print(f"[horizontal-history] manifest: {args.manifest_json}")


if __name__ == "__main__":
    main()
