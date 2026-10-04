#!/usr/bin/env python3
"""Explore stable event-to-event seismic ratios and known-constant matches.

This runner is intentionally exploratory.  It does not claim that a stable
ratio is a new physical law; it produces ranked candidates with support,
robust dispersion and enough metadata to falsify them in later train/backtest
runs.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import shlex
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from tasks import parse_datetime_like


KNOWN_CONSTANTS = [
    ("phi", (1.0 + math.sqrt(5.0)) / 2.0, "golden ratio / Fibonacci limit"),
    ("sqrt_phi", math.sqrt((1.0 + math.sqrt(5.0)) / 2.0), "sqrt(golden ratio)"),
    ("inv_phi", 2.0 / (1.0 + math.sqrt(5.0)), "inverse golden ratio"),
    ("pi", math.pi, "pi"),
    ("e", math.e, "Euler number"),
    ("sqrt2", math.sqrt(2.0), "sqrt(2)"),
    ("sqrt3", math.sqrt(3.0), "sqrt(3)"),
    ("log2e", math.log2(math.e), "log2(e)"),
    ("b_value_1", 1.0, "Gutenberg-Richter b-value reference"),
    ("bp_df_1p6", 1.6, "common Baiesi-Paczuski/fractal-dimension reference"),
]

DIMENSIONLESS_METRICS = {
    "fibonacci_dt_ratio",
    "abs_mag_delta",
    "log10_energy_ratio_abs",
}

RESIDUAL_BASE_METRICS = {
    "energy_per_day_log10",
    "energy_ratio_per_day_log10",
    "energy_distance_balance",
    "bp_eta_log10_df1p6_b1",
}


@dataclass
class ExplorerConfig:
    csv_path: str
    output_dir: str = "seismic_constant_explorer"
    output_prefix: str = ""
    output_suffix: str = ""
    date_col: str = "auto"
    mag_col: str = "auto"
    lat_col: str = "auto"
    lon_col: str = "auto"
    depth_col: str = "auto"
    start_date: str = ""
    end_date: str = ""
    min_mag: float | None = None
    max_mag: float | None = None
    lags: str = "1,2,3,5,8"
    mag_bin_width: float = 0.5
    time_clusters: int = 4
    min_support: int = 10
    top_k: int = 40
    jobs: int = 1
    dimensionless_only: bool = False
    residual_mode: str = "none"
    residual_metrics_only: bool = False
    residual_group: str = "mag_bin,time_cluster,lag"
    residual_metrics: str = "energy_per_day_log10,energy_ratio_per_day_log10,energy_distance_balance,bp_eta_log10_df1p6_b1"
    focus_metric: str = ""
    focus_mag_delta_range: str = ""
    focus_only: bool = False
    event_source: str = "auto"
    master_min_mag: float = 0.0
    shuffle_controls: int = 0
    random_seed: int = 8675309
    write_pairs: bool = False
    max_pairs_csv: int = 200000
    make_png: bool = True
    command_line: str = ""


def _clean_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned.strip("._-")


def _truncate_slug(value: str, max_len: int = 72) -> str:
    value = _clean_name(value)
    if len(value) <= max_len:
        return value
    return value[:max_len].rstrip("._-")


def _lag_code(lags: str) -> str:
    parsed = _parse_lags(lags)
    if parsed == [1, 2, 3, 5, 8]:
        return "lagF"
    if len(parsed) <= 5:
        return "lag" + "-".join(str(v) for v in parsed)
    return f"lag{len(parsed)}x"


def _source_slug(path: Path, meta: dict[str, Any]) -> str:
    name = path.parent.name if meta.get("event_source") == "master_filtered" else path.stem
    return _truncate_slug(name, 72) or "source"


def _output_codes(cfg: ExplorerConfig, meta: dict[str, Any]) -> dict[str, str]:
    source_code = "masterevt" if meta.get("event_source") == "master_filtered" else "csv"
    metric_code = "dimless" if cfg.dimensionless_only else "all3d"
    if cfg.residual_mode != "none":
        metric_code = "resid" if cfg.residual_metrics_only else f"{metric_code}-resid"
    if cfg.focus_only or cfg.focus_metric or cfg.focus_mag_delta_range:
        metric_code = f"{metric_code}-focus"
    shuffle_code = f"shuf{int(cfg.shuffle_controls)}"
    return {
        "source": source_code,
        "metrics": metric_code,
        "lags": _lag_code(cfg.lags),
        "support": f"ms{int(cfg.min_support)}",
        "time_clusters": f"tc{int(cfg.time_clusters)}",
        "shuffle": shuffle_code,
    }


def _resolve_output_stem(cfg: ExplorerConfig, meta: dict[str, Any], out_dir: Path) -> tuple[str, dict[str, Any]]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = Path(cfg.csv_path)
    codes = _output_codes(cfg, meta)
    auto_suffix = "_".join(codes.values())
    explicit_prefix = bool(str(cfg.output_prefix or "").strip())
    explicit_suffix = bool(str(cfg.output_suffix or "").strip())

    if explicit_prefix:
        base = _truncate_slug(str(cfg.output_prefix), 96)
    else:
        base = _source_slug(path, meta)

    if explicit_suffix:
        suffix = _truncate_slug(str(cfg.output_suffix), 96)
    else:
        suffix = auto_suffix

    stem = _clean_name(f"{base}__{suffix}__{stamp}")
    # Timestamp should normally be enough, but keep a deterministic guard for
    # rapid repeated runs inside the same second.
    candidate = stem
    idx = 2
    while (out_dir / f"{candidate}_candidates.csv").exists():
        candidate = f"{stem}_r{idx:02d}"
        idx += 1

    legend = {
        "output_stem": candidate,
        "timestamp": stamp,
        "explicit_prefix": explicit_prefix,
        "explicit_suffix": explicit_suffix,
        "source_slug": _source_slug(path, meta),
        "codes": codes,
        "code_legend": {
            "masterevt": "master astro/USGS detected; only rows with mag > master_min_mag are treated as earthquakes",
            "csv": "plain event CSV; all parseable rows after date/magnitude filters are analyzed",
            "dimless": "dimensionless-only search: ratios/log-ratios suitable for known-constant comparison",
            "all3d": "all metric search: includes time, 3D distance, energy and combined physical proxies",
            "resid": "residual-only search after subtracting configured group medians",
            "all3d-resid": "all metric search with additional residual metrics",
            "dimless-resid": "dimensionless search with additional residual metrics",
            "focus": "pre-registered focus filter: only configured metric/range hypotheses are ranked",
            "resid-focus": "residual-only pre-registered focus search",
            "all3d-focus": "all-metric search with pre-registered focus filter",
            "all3d-resid-focus": "all-metric residual search with pre-registered focus filter",
            "dimless-focus": "dimensionless search with pre-registered focus filter",
            "dimless-resid-focus": "dimensionless residual search with pre-registered focus filter",
            "lagF": "Fibonacci-like lag set 1,2,3,5,8",
            "msN": "minimum support N per candidate group",
            "tcN": "N quantile-based time clusters",
            "shufN": "N interval-shuffled control catalogs",
        },
    }
    return candidate, legend


def _find_col(header: list[str], requested: str, candidates: tuple[str, ...]) -> str | None:
    if requested and requested != "auto":
        return requested if requested in header else None
    lower = {c.strip().lower(): c for c in header}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


def _optional_float(value: Any) -> float | None:
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except Exception:
        return None


def _parse_lags(value: str) -> list[int]:
    out: list[int] = []
    for token in str(value or "").split(","):
        token = token.strip()
        if not token:
            continue
        lag = int(token)
        if lag > 0 and lag not in out:
            out.append(lag)
    return out or [1]


def _parse_tokens(value: str) -> list[str]:
    return [token.strip() for token in str(value or "").split(",") if token.strip()]


def _parse_float_range(value: str) -> tuple[float, float] | None:
    tokens = _parse_tokens(value)
    if not tokens:
        return None
    if len(tokens) != 2:
        raise ValueError("--focus-mag-delta-range deve avere formato LO,HI, esempio 0.5,1.5")
    lo = float(tokens[0])
    hi = float(tokens[1])
    if not math.isfinite(lo) or not math.isfinite(hi) or hi <= lo:
        raise ValueError("--focus-mag-delta-range richiede valori finiti con HI > LO")
    return lo, hi


def _range_label(prefix: str, lo: float, hi: float) -> str:
    return f"{prefix}[{lo:.2f},{hi:.2f})"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return 2.0 * radius * math.asin(min(1.0, math.sqrt(a)))


def _mag_bin(value: float, width: float) -> str:
    if width <= 0:
        return "all_mag"
    lo = math.floor(value / width) * width
    hi = lo + width
    return f"M[{lo:.2f},{hi:.2f})"


def _safe_log10(value: float, floor: float = 1e-12) -> float:
    return math.log10(max(float(value), floor))


def _robust_stats(values: list[float]) -> dict[str, float] | None:
    arr = np.asarray([v for v in values if math.isfinite(v)], dtype=float)
    if arr.size == 0:
        return None
    med = float(np.median(arr))
    mad = float(np.median(np.abs(arr - med)))
    q25, q75 = np.percentile(arr, [25, 75])
    mean = float(np.mean(arr))
    std = float(np.std(arr))
    denom = max(abs(med), 1e-12)
    return {
        "n": float(arr.size),
        "median": med,
        "mean": mean,
        "std": std,
        "cv_abs": std / max(abs(mean), 1e-12),
        "mad_rel": mad / denom,
        "iqr_rel": float((q75 - q25) / denom),
        "q25": float(q25),
        "q75": float(q75),
    }


def _known_match(value: float) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    for name, constant, note in KNOWN_CONSTANTS:
        rel = abs(value - constant) / max(abs(constant), 1e-12)
        item = {
            "known_name": name,
            "known_value": constant,
            "known_note": note,
            "known_rel_error": rel,
        }
        if best is None or rel < float(best["known_rel_error"]):
            best = item
    return best or {
        "known_name": "",
        "known_value": "",
        "known_note": "",
        "known_rel_error": "",
    }


def _time_cluster_edges(values: list[float], n_clusters: int) -> list[float]:
    arr = np.asarray([v for v in values if math.isfinite(v) and v > 0], dtype=float)
    if arr.size == 0:
        return []
    n = max(1, int(n_clusters))
    if n == 1:
        return []
    qs = np.linspace(0, 100, n + 1)[1:-1]
    edges = sorted(set(float(v) for v in np.percentile(np.log10(arr), qs)))
    return edges


def _cluster_label(value: float, edges: list[float]) -> str:
    if not edges:
        return "dt_all"
    lv = _safe_log10(value)
    idx = 0
    while idx < len(edges) and lv > edges[idx]:
        idx += 1
    if idx == 0:
        return f"dt_q1<=10^{edges[0]:.2f}"
    if idx == len(edges):
        return f"dt_q{idx + 1}>10^{edges[-1]:.2f}"
    return f"dt_q{idx + 1}(10^{edges[idx - 1]:.2f},10^{edges[idx]:.2f}]"


def read_events(cfg: ExplorerConfig) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = Path(cfg.csv_path)
    if not path.exists():
        raise FileNotFoundError(
            f"CSV non trovato: {path}. Passa il path reale del catalogo USGS, "
            "non il placeholder `catalogo_usgs.csv`."
        )
    if path.is_dir():
        raise ValueError(f"Il path e' una directory, non un CSV: {path}")
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV senza header: {path}")
        header = list(reader.fieldnames)
        rows = list(reader)

    date_col = _find_col(header, cfg.date_col, ("date", "datetime", "timestamp", "time", "origin_time"))
    mag_col = _find_col(header, cfg.mag_col, ("mag", "magnitude", "mw", "ml"))
    lat_col = _find_col(header, cfg.lat_col, ("latitude", "lat"))
    lon_col = _find_col(header, cfg.lon_col, ("longitude", "lon", "lng"))
    depth_col = _find_col(header, cfg.depth_col, ("depth", "depth_km", "depthkm"))
    if date_col is None:
        raise ValueError("Colonna data non trovata; passa --date-col")
    if mag_col is None:
        raise ValueError("Colonna magnitudo non trovata; passa --mag-col")
    astro_like_cols = [c for c in header if "body:" in c or "|eph:" in c or "|op:" in c]
    source_mode = str(getattr(cfg, "event_source", "auto") or "auto")
    looks_like_master = (
        source_mode == "master"
        or (
            source_mode == "auto"
            and (
                "master" in path.name.lower()
                or bool(astro_like_cols)
            )
        )
    )

    start_dt = parse_datetime_like(cfg.start_date) if cfg.start_date else None
    end_dt = parse_datetime_like(cfg.end_date) if cfg.end_date else None
    events: list[dict[str, Any]] = []
    dropped = 0
    for row_no, row in enumerate(rows, start=2):
        dt = parse_datetime_like(row.get(date_col, ""))
        mag = _optional_float(row.get(mag_col))
        if dt is None or mag is None:
            dropped += 1
            continue
        if looks_like_master and mag <= float(getattr(cfg, "master_min_mag", 0.0)):
            continue
        if start_dt and dt < start_dt:
            continue
        if end_dt and dt > end_dt:
            continue
        if cfg.min_mag is not None and mag < cfg.min_mag:
            continue
        if cfg.max_mag is not None and mag > cfg.max_mag:
            continue
        lat = _optional_float(row.get(lat_col)) if lat_col else None
        lon = _optional_float(row.get(lon_col)) if lon_col else None
        depth = _optional_float(row.get(depth_col)) if depth_col else None
        events.append({
            "row_no": row_no,
            "date": dt,
            "date_raw": row.get(date_col, ""),
            "mag": float(mag),
            "lat": lat,
            "lon": lon,
            "depth_km": depth if depth is not None else 0.0,
        })
    events.sort(key=lambda item: item["date"])
    sibling_event_csvs: list[str] = []
    try:
        for sibling in sorted(path.parent.iterdir()):
            lower = sibling.name.lower()
            if sibling.is_file() and sibling.suffix.lower() == ".csv" and (
                "earth" in lower or "quake" in lower or "usgs" in lower or "raw" in lower
            ):
                sibling_event_csvs.append(str(sibling))
    except OSError:
        sibling_event_csvs = []
    meta = {
        "csv_path": str(path),
        "csv_name": path.name,
        "csv_dir": str(path.parent),
        "header": header,
        "date_col": date_col,
        "mag_col": mag_col,
        "lat_col": lat_col,
        "lon_col": lon_col,
        "depth_col": depth_col,
        "input_rows": len(rows),
        "usable_events": len(events),
        "dropped_unparseable": dropped,
        "event_source": "master_filtered" if looks_like_master else "csv",
        "looks_like_master": bool(looks_like_master),
        "master_min_mag": float(getattr(cfg, "master_min_mag", 0.0)),
        "astro_like_column_count": len(astro_like_cols),
        "sibling_event_csvs": sibling_event_csvs,
        "has_location": bool(lat_col and lon_col and all(e["lat"] is not None and e["lon"] is not None for e in events)),
    }
    return events, meta


def build_pairs(events: list[dict[str, Any]], cfg: ExplorerConfig) -> list[dict[str, Any]]:
    lags = _parse_lags(cfg.lags)
    focus_dmag = _parse_float_range(cfg.focus_mag_delta_range)
    focus_dmag_label = _range_label("dM", *focus_dmag) if focus_dmag else ""
    raw_pairs: list[dict[str, Any]] = []
    for lag in lags:
        for i in range(lag, len(events)):
            prev = events[i - lag]
            cur = events[i]
            dt_days = (cur["date"] - prev["date"]).total_seconds() / 86400.0
            if dt_days <= 0:
                continue
            r2d_km = None
            r3d_km = None
            if prev["lat"] is not None and prev["lon"] is not None and cur["lat"] is not None and cur["lon"] is not None:
                r2d_km = _haversine_km(float(prev["lat"]), float(prev["lon"]), float(cur["lat"]), float(cur["lon"]))
                dz = float(cur["depth_km"] or 0.0) - float(prev["depth_km"] or 0.0)
                r3d_km = math.sqrt(r2d_km ** 2 + dz ** 2)
            loge_prev = 1.5 * float(prev["mag"]) + 4.8
            loge_cur = 1.5 * float(cur["mag"]) + 4.8
            raw_pairs.append({
                "lag": lag,
                "from_row": prev["row_no"],
                "to_row": cur["row_no"],
                "from_date": prev["date"].isoformat(sep=" "),
                "to_date": cur["date"].isoformat(sep=" "),
                "dt_days": dt_days,
                "dt_hours": dt_days * 24.0,
                "mag_prev": float(prev["mag"]),
                "mag_cur": float(cur["mag"]),
                "mag_mid": (float(prev["mag"]) + float(cur["mag"])) / 2.0,
                "mag_abs_delta": abs(float(cur["mag"]) - float(prev["mag"])),
                "log10_energy_prev_j": loge_prev,
                "log10_energy_cur_j": loge_cur,
                "log10_energy_ratio": loge_cur - loge_prev,
                "r2d_km": r2d_km,
                "r3d_km": r3d_km,
            })
    edges = _time_cluster_edges([p["dt_days"] for p in raw_pairs], cfg.time_clusters)
    for pair in raw_pairs:
        r = pair["r3d_km"] if pair["r3d_km"] is not None else pair["r2d_km"]
        r_eff = max(float(r), 1e-6) if r is not None else None
        pair["time_cluster"] = _cluster_label(float(pair["dt_days"]), edges)
        pair["mag_bin"] = _mag_bin(float(pair["mag_mid"]), cfg.mag_bin_width)
        pair["parity_mag_range"] = _mag_bin(float(pair["mag_abs_delta"]), cfg.mag_bin_width)
        pair["focus_mag_delta_range"] = ""
        if focus_dmag:
            lo, hi = focus_dmag
            if lo <= float(pair["mag_abs_delta"]) < hi:
                pair["focus_mag_delta_range"] = focus_dmag_label
        pair["energy_per_day_log10"] = float(pair["log10_energy_cur_j"]) - _safe_log10(float(pair["dt_days"]))
        pair["energy_ratio_per_day_log10"] = float(pair["log10_energy_ratio"]) - _safe_log10(float(pair["dt_days"]))
        pair["fibonacci_dt_ratio"] = None
        pair["energy_distance_balance"] = None
        pair["bp_eta_log10_df1p6_b1"] = None
        if r_eff is not None:
            pair["energy_distance_balance"] = float(pair["log10_energy_cur_j"]) / (1.0 + _safe_log10(r_eff))
            pair["bp_eta_log10_df1p6_b1"] = _safe_log10(float(pair["dt_days"])) + 1.6 * _safe_log10(r_eff) - float(pair["mag_prev"])
    by_lag: dict[int, list[dict[str, Any]]] = {}
    for pair in raw_pairs:
        by_lag.setdefault(int(pair["lag"]), []).append(pair)
    for lag, rows in by_lag.items():
        rows.sort(key=lambda item: item["to_date"])
        prev_dt = None
        for row in rows:
            if prev_dt is not None and prev_dt > 0:
                row["fibonacci_dt_ratio"] = float(row["dt_days"]) / prev_dt
            prev_dt = float(row["dt_days"])
    return raw_pairs


def add_group_median_residuals(pairs: list[dict[str, Any]], cfg: ExplorerConfig) -> dict[str, Any]:
    if cfg.residual_mode == "none":
        return {"mode": "none", "added_metrics": []}
    if cfg.residual_mode != "group-median":
        raise ValueError(f"residual_mode non supportato: {cfg.residual_mode}")
    group_cols = _parse_tokens(cfg.residual_group)
    metric_names = _parse_tokens(cfg.residual_metrics)
    if not group_cols:
        raise ValueError("--residual-group deve contenere almeno una colonna")
    if not metric_names:
        raise ValueError("--residual-metrics deve contenere almeno una metrica")

    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for pair in pairs:
        key = tuple(pair.get(col) for col in group_cols)
        groups.setdefault(key, []).append(pair)

    added: list[str] = []
    baselines: dict[str, int] = {}
    for metric in metric_names:
        residual_name = f"{metric}_resid"
        added.append(residual_name)
        baselines[metric] = 0
        for rows in groups.values():
            values = [
                float(row[metric])
                for row in rows
                if row.get(metric) is not None and math.isfinite(float(row[metric]))
            ]
            if not values:
                continue
            expected = float(np.median(np.asarray(values, dtype=float)))
            baselines[metric] += 1
            for row in rows:
                value = row.get(metric)
                if value is not None and math.isfinite(float(value)):
                    row[residual_name] = float(value) - expected
                else:
                    row[residual_name] = None

    return {
        "mode": cfg.residual_mode,
        "group_cols": group_cols,
        "base_metrics": metric_names,
        "added_metrics": added,
        "baseline_group_counts": baselines,
    }


def interval_shuffled_events(events: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    """Shuffle inter-event intervals while preserving event attributes.

    This is a conservative null for temporal-ratio discoveries: it keeps the
    marginal waiting-time distribution but destroys serial order.
    """
    if len(events) < 2:
        return list(events)
    rng = np.random.default_rng(int(seed))
    deltas = [
        events[i]["date"] - events[i - 1]["date"]
        for i in range(1, len(events))
    ]
    order = rng.permutation(len(deltas))
    shuffled = [deltas[int(i)] for i in order]
    out: list[dict[str, Any]] = []
    current_dt = events[0]["date"]
    for idx, event in enumerate(events):
        clone = dict(event)
        if idx == 0:
            current_dt = events[0]["date"]
        else:
            current_dt = current_dt + shuffled[idx - 1]
        clone["date"] = current_dt
        clone["date_raw"] = current_dt.isoformat(sep=" ")
        out.append(clone)
    return out


def _candidate_series(pair: dict[str, Any]) -> dict[str, float]:
    dt = float(pair["dt_days"])
    mag_delta = max(float(pair["mag_abs_delta"]), 1e-9)
    out = {
        "dt_days": dt,
        "dt_hours": float(pair["dt_hours"]),
        "abs_mag_delta": mag_delta,
        "log10_energy_ratio_abs": abs(float(pair["log10_energy_ratio"])),
        "energy_per_day_log10": float(pair["energy_per_day_log10"]),
        "energy_ratio_per_day_log10": float(pair["energy_ratio_per_day_log10"]),
        "fibonacci_dt_ratio": pair["fibonacci_dt_ratio"],
        "bp_eta_log10_df1p6_b1": pair["bp_eta_log10_df1p6_b1"],
        "energy_distance_balance": pair["energy_distance_balance"],
        "dt_per_mag_delta": dt / mag_delta,
    }
    for key, value in pair.items():
        if str(key).endswith("_resid") and value is not None:
            out[str(key)] = value
    r3 = pair.get("r3d_km")
    if r3 is not None:
        out["r3d_km"] = float(r3)
        out["r3d_per_day"] = float(r3) / dt
        out["dt_per_r3d"] = dt / max(float(r3), 1e-9)
        out["energy_ratio_per_r3d_log10"] = abs(float(pair["log10_energy_ratio"])) / (1.0 + _safe_log10(float(r3)))
    return {k: float(v) for k, v in out.items() if v is not None and math.isfinite(float(v))}


def _score_candidate(stats: dict[str, float], known_rel_error: float | None) -> float:
    support = float(stats["n"])
    stability = 1.0 / (1.0 + float(stats["mad_rel"]) + 0.5 * float(stats["iqr_rel"]))
    support_factor = min(1.0, math.log1p(support) / math.log(101.0))
    if known_rel_error is None:
        known_factor = 1.0
    else:
        known_factor = 1.0 / (1.0 + 8.0 * min(known_rel_error, 1.0))
    return 100.0 * stability * support_factor * (0.75 + 0.25 * known_factor)


def _summarize_group(payload: tuple[str, str, str, list[dict[str, Any]], int, bool, bool]) -> list[dict[str, Any]]:
    scope, group_key, group_value, rows, min_support, dimensionless_only, residual_metrics_only = payload
    buckets: dict[str, list[float]] = {}
    for row in rows:
        for name, value in _candidate_series(row).items():
            if dimensionless_only and name not in DIMENSIONLESS_METRICS:
                continue
            if residual_metrics_only and not name.endswith("_resid"):
                continue
            buckets.setdefault(name, []).append(value)
    out: list[dict[str, Any]] = []
    for name, values in buckets.items():
        stats = _robust_stats(values)
        if stats is None or int(stats["n"]) < min_support:
            continue
        if name in DIMENSIONLESS_METRICS:
            match = _known_match(float(stats["median"]))
            known_rel_error = float(match["known_rel_error"])
        else:
            match = {
                "known_name": "",
                "known_value": "",
                "known_note": "unit-bearing metric; known-constant match skipped",
                "known_rel_error": "",
            }
            known_rel_error = None
        item: dict[str, Any] = {
            "scope": scope,
            "group_key": group_key,
            "group_value": group_value,
            "metric": name,
            "support": int(stats["n"]),
            "median": stats["median"],
            "mean": stats["mean"],
            "std": stats["std"],
            "cv_abs": stats["cv_abs"],
            "mad_rel": stats["mad_rel"],
            "iqr_rel": stats["iqr_rel"],
            "q25": stats["q25"],
            "q75": stats["q75"],
            "score": _score_candidate(stats, known_rel_error),
        }
        item.update(match)
        out.append(item)
    return out


def discover_candidates(pairs: list[dict[str, Any]], cfg: ExplorerConfig) -> list[dict[str, Any]]:
    group_payload = (cfg.min_support, bool(cfg.dimensionless_only), bool(cfg.residual_metrics_only))
    groups: list[tuple[str, str, str, list[dict[str, Any]], int, bool, bool]] = []
    focus_dmag = _parse_float_range(cfg.focus_mag_delta_range)
    if not cfg.focus_only:
        groups.append(("global", "all", "all", pairs, *group_payload))
        for key in ("lag", "time_cluster", "mag_bin", "parity_mag_range"):
            by_value: dict[str, list[dict[str, Any]]] = {}
            for pair in pairs:
                by_value.setdefault(str(pair.get(key, "")), []).append(pair)
            for value, rows in sorted(by_value.items()):
                groups.append((f"by_{key}", key, value, rows, *group_payload))
        by_cross: dict[str, list[dict[str, Any]]] = {}
        for pair in pairs:
            value = f"{pair.get('time_cluster')}|{pair.get('mag_bin')}|lag={pair.get('lag')}"
            by_cross.setdefault(value, []).append(pair)
        for value, rows in sorted(by_cross.items()):
            groups.append(("by_time_mag_lag", "time_cluster|mag_bin|lag", value, rows, *group_payload))

    if focus_dmag:
        by_focus: dict[str, list[dict[str, Any]]] = {}
        for pair in pairs:
            value = str(pair.get("focus_mag_delta_range", ""))
            if value:
                by_focus.setdefault(value, []).append(pair)
        for value, rows in sorted(by_focus.items()):
            groups.append(("by_focus_mag_delta_range", "focus_mag_delta_range", value, rows, *group_payload))

    if cfg.jobs and cfg.jobs > 1 and len(groups) > 1:
        candidates: list[dict[str, Any]] = []
        with ProcessPoolExecutor(max_workers=int(cfg.jobs)) as pool:
            futs = [pool.submit(_summarize_group, group) for group in groups]
            for fut in as_completed(futs):
                candidates.extend(fut.result())
    else:
        candidates = []
        for group in groups:
            candidates.extend(_summarize_group(group))
    candidates.sort(key=lambda item: (float(item["score"]), int(item["support"])), reverse=True)
    focus_metrics = set(_parse_tokens(cfg.focus_metric))
    if focus_metrics:
        candidates = [row for row in candidates if str(row.get("metric", "")) in focus_metrics]
    if cfg.focus_only and focus_dmag:
        wanted = _range_label("dM", *focus_dmag)
        candidates = [
            row for row in candidates
            if row.get("scope") == "by_focus_mag_delta_range" and row.get("group_value") == wanted
        ]
    candidates.sort(key=lambda item: (float(item["score"]), int(item["support"])), reverse=True)
    return candidates


def annotate_shuffle_controls(events: list[dict[str, Any]], cfg: ExplorerConfig,
                              candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    n_controls = max(0, int(cfg.shuffle_controls))
    if n_controls <= 0 or not candidates:
        return []
    observed_keys = {
        (row["scope"], row["group_key"], row["group_value"], row["metric"])
        for row in candidates
    }
    control_scores: dict[tuple[Any, ...], list[float]] = {key: [] for key in observed_keys}
    control_rows: list[dict[str, Any]] = []
    control_cfg = ExplorerConfig(**asdict(cfg))
    control_cfg.jobs = 1
    control_cfg.shuffle_controls = 0
    for idx in range(n_controls):
        shuffled = interval_shuffled_events(events, int(cfg.random_seed) + idx)
        pairs = build_pairs(shuffled, control_cfg)
        add_group_median_residuals(pairs, control_cfg)
        rows = discover_candidates(pairs, control_cfg)
        for row in rows:
            key = (row["scope"], row["group_key"], row["group_value"], row["metric"])
            if key in control_scores:
                control_scores[key].append(float(row["score"]))
        if rows:
            best = rows[0]
            control_rows.append({
                "control_no": idx + 1,
                "best_score": best["score"],
                "best_scope": best["scope"],
                "best_group_value": best["group_value"],
                "best_metric": best["metric"],
                "best_median": best["median"],
                "best_support": best["support"],
            })
    for row in candidates:
        key = (row["scope"], row["group_key"], row["group_value"], row["metric"])
        scores = control_scores.get(key, [])
        if not scores:
            row["shuffle_control_p_score"] = ""
            row["shuffle_control_max_score"] = ""
            row["shuffle_control_mean_score"] = ""
            continue
        obs = float(row["score"])
        row["shuffle_control_p_score"] = (1.0 + sum(1 for score in scores if score >= obs)) / (1.0 + len(scores))
        row["shuffle_control_max_score"] = max(scores)
        row["shuffle_control_mean_score"] = sum(scores) / len(scores)
    return control_rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        seen: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.append(key)
        fieldnames = seen
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=2, sort_keys=True, default=str)


def write_report(path: Path, cfg: ExplorerConfig, meta: dict[str, Any],
                 candidates: list[dict[str, Any]], pairs: list[dict[str, Any]],
                 output_legend: dict[str, Any]) -> None:
    top = candidates[: max(1, int(cfg.top_k))]
    command_line = cfg.command_line or " ".join(shlex.quote(x) for x in sys.argv)
    sibling_lines = []
    for sibling in meta.get("sibling_event_csvs") or []:
        sibling_lines.append(f"- related event/source CSV: `{sibling}`")
    if not sibling_lines:
        sibling_lines.append("- related event/source CSV: none detected next to source")
    codes = output_legend.get("codes", {}) if isinstance(output_legend, dict) else {}
    code_legend = output_legend.get("code_legend", {}) if isinstance(output_legend, dict) else {}
    lines = [
        "# Seismic Constant Explorer",
        "",
        "This is an exploratory scan, not a discovery claim. A candidate is useful",
        "when it is stable under held-out catalogs, shuffled controls and future",
        "train/backtest windows.",
        "",
        "## Invocation",
        "",
        f"- command: `{command_line}`",
        f"- output stem: `{output_legend.get('output_stem', '')}`",
        f"- timestamp: `{output_legend.get('timestamp', '')}`",
        "",
        "## Filename Code Legend",
        "",
        f"- source code: `{codes.get('source', '')}` - {code_legend.get(codes.get('source', ''), '')}",
        f"- metric code: `{codes.get('metrics', '')}` - {code_legend.get(codes.get('metrics', ''), '')}",
        f"- lag code: `{codes.get('lags', '')}` - {code_legend.get(codes.get('lags', ''), 'explicit lag set from --lags')}",
        f"- support code: `{codes.get('support', '')}` - minimum support per candidate group",
        f"- time-cluster code: `{codes.get('time_clusters', '')}` - quantile-based time clusters",
        f"- shuffle code: `{codes.get('shuffle', '')}` - interval-shuffled control catalogs",
        "",
        "## Dataset",
        "",
        f"- CSV: `{meta['csv_path']}`",
        f"- CSV name: `{meta.get('csv_name', '')}`",
        f"- CSV directory: `{meta.get('csv_dir', '')}`",
        f"- source mode: `{meta.get('event_source', '')}`",
        f"- master-like astro columns detected: {meta.get('astro_like_column_count', 0)}",
        f"- master event threshold: mag > {meta.get('master_min_mag', 0.0)}",
        f"- usable events: {meta['usable_events']} / input rows: {meta['input_rows']}",
        f"- generated event pairs: {len(pairs)}",
        f"- columns: date=`{meta['date_col']}`, mag=`{meta['mag_col']}`, "
        f"lat=`{meta.get('lat_col')}`, lon=`{meta.get('lon_col')}`, depth=`{meta.get('depth_col')}`",
        f"- lags: `{cfg.lags}`",
        f"- magnitude bin width: {cfg.mag_bin_width:g}",
        f"- time clusters: {cfg.time_clusters}",
        f"- residual mode: `{cfg.residual_mode}`",
        f"- residual group: `{cfg.residual_group}`",
        f"- residual metrics only: {bool(cfg.residual_metrics_only)}",
        f"- residual base metrics: `{cfg.residual_metrics}`",
        f"- focus only: {bool(cfg.focus_only)}",
        f"- focus metric: `{cfg.focus_metric or 'none'}`",
        f"- focus mag delta range: `{cfg.focus_mag_delta_range or 'none'}`",
        "",
        "## Source Files Nearby",
        "",
        *sibling_lines,
        "",
        "## Best Candidates",
        "",
        "| rank | score | scope | group | metric | support | median | robust spread | closest known | rel.err |",
        "|---:|---:|---|---|---|---:|---:|---:|---|---:|",
    ]
    for idx, row in enumerate(top, start=1):
        rel_error = row.get("known_rel_error")
        rel_text = f"{float(rel_error):.4g}" if rel_error not in ("", None) else ""
        lines.append(
            f"| {idx} | {float(row['score']):.2f} | {row['scope']} | "
            f"{row['group_value']} | {row['metric']} | {row['support']} | "
            f"{float(row['median']):.6g} | {float(row['mad_rel']):.4g} | "
            f"{row['known_name']} | {rel_text} |"
        )
    lines.extend([
        "",
        "## Metric Notes",
        "",
        "- `fibonacci_dt_ratio`: ratio between consecutive inter-event times at the same lag.",
        "- `bp_eta_log10_df1p6_b1`: log10 heuristic of the Baiesi-Paczuski style proximity metric "
        "`dt * r^1.6 * 10^-Mprev`.",
        "- `energy_*`: uses the standard radiated-energy approximation `log10(E_J)=1.5*M+4.8`.",
        "- `energy_distance_balance`: log energy divided by `1 + log10(r3d_km)`.",
        "- `*_resid`: value minus the median expected value inside the configured residual group.",
        "- `by_focus_mag_delta_range`: pre-registered `abs(delta magnitude)` range from `--focus-mag-delta-range`.",
        "",
        "## Next Falsification Steps",
        "",
        "1. Re-run on disjoint regions or historical windows.",
        "2. Compare against time-shuffled and magnitude-shuffled catalogs.",
        "3. Promote only stable candidates into `cli.py train` as engineered CSV features.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def write_png(path: Path, candidates: list[dict[str, Any]]) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[warn] matplotlib unavailable, PNG skipped: {exc}")
        return False
    top = candidates[:20]
    if not top:
        return False
    labels = [f"{r['metric']}\n{r['group_value']}"[:52] for r in top]
    scores = [float(r["score"]) for r in top]
    fig, ax = plt.subplots(figsize=(12, max(6, 0.36 * len(top))))
    y = np.arange(len(top))
    ax.barh(y, scores, color="#2563eb")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("exploration score")
    ax.set_title("Top candidate seismic constants")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return True


def run(cfg: ExplorerConfig) -> dict[str, Any]:
    events, meta = read_events(cfg)
    if len(events) < 3:
        raise ValueError("Servono almeno 3 eventi utilizzabili per calcolare relazioni evento-evento")
    pairs = build_pairs(events, cfg)
    if not pairs:
        raise ValueError("Nessuna coppia evento-evento generata; controlla date, lags e filtri")
    residual_meta = add_group_median_residuals(pairs, cfg)
    candidates = discover_candidates(pairs, cfg)
    control_rows = annotate_shuffle_controls(events, cfg, candidates)
    out_dir = Path(cfg.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix, output_legend = _resolve_output_stem(cfg, meta, out_dir)

    candidate_csv = out_dir / f"{prefix}_candidates.csv"
    candidate_json = out_dir / f"{prefix}_summary.json"
    report_md = out_dir / f"{prefix}_report.md"
    png_path = out_dir / f"{prefix}_top_candidates.png"
    pair_csv = out_dir / f"{prefix}_event_pairs.csv"
    control_csv = out_dir / f"{prefix}_shuffle_controls.csv"

    write_csv(candidate_csv, candidates)
    if control_rows:
        write_csv(control_csv, control_rows)
    summary = {
        "config": asdict(cfg),
        "meta": meta,
        "pair_count": len(pairs),
        "candidate_count": len(candidates),
        "shuffle_control_count": len(control_rows),
        "residual": residual_meta,
        "output": output_legend,
        "command_line": cfg.command_line or " ".join(shlex.quote(x) for x in sys.argv),
        "top_candidates": candidates[: max(1, int(cfg.top_k))],
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    write_json(candidate_json, summary)
    write_report(report_md, cfg, meta, candidates, pairs, output_legend)
    png_written = False
    if cfg.make_png:
        png_written = write_png(png_path, candidates)
    if cfg.write_pairs:
        rows = pairs[: max(0, int(cfg.max_pairs_csv))]
        write_csv(pair_csv, rows)
    return {
        "candidate_csv": str(candidate_csv),
        "summary_json": str(candidate_json),
        "report_md": str(report_md),
        "png": str(png_path) if png_written else "",
        "pair_csv": str(pair_csv) if cfg.write_pairs else "",
        "control_csv": str(control_csv) if control_rows else "",
        "top_candidates": candidates[: max(1, int(cfg.top_k))],
    }


def add_arguments(ap: argparse.ArgumentParser) -> argparse.ArgumentParser:
    ap.add_argument("--task", "--csv", dest="csv_path", required=True,
                    help="CSV catalog path, e.g. USGS export")
    ap.add_argument("--output-dir", default=ExplorerConfig.output_dir)
    ap.add_argument("--output-prefix", default=ExplorerConfig.output_prefix,
                    help=("optional human prefix; when omitted, a source/metric prefix is generated. "
                          "A timestamped suffix is always added."))
    ap.add_argument("--output-suffix", default=ExplorerConfig.output_suffix,
                    help=("optional human suffix; when omitted, source/metric/lag/support/shuffle "
                          "codes are generated. A timestamp is always added."))
    ap.add_argument("--date-col", default=ExplorerConfig.date_col)
    ap.add_argument("--mag-col", default=ExplorerConfig.mag_col)
    ap.add_argument("--lat-col", default=ExplorerConfig.lat_col)
    ap.add_argument("--lon-col", default=ExplorerConfig.lon_col)
    ap.add_argument("--depth-col", default=ExplorerConfig.depth_col)
    ap.add_argument("--start-date", default="")
    ap.add_argument("--end-date", default="")
    ap.add_argument("--min-mag", type=float, default=None)
    ap.add_argument("--max-mag", type=float, default=None)
    ap.add_argument("--lags", default=ExplorerConfig.lags,
                    help="comma-separated backward lags; Fibonacci-like default: 1,2,3,5,8")
    ap.add_argument("--mag-bin-width", type=float, default=ExplorerConfig.mag_bin_width)
    ap.add_argument("--time-clusters", type=int, default=ExplorerConfig.time_clusters)
    ap.add_argument("--min-support", type=int, default=ExplorerConfig.min_support)
    ap.add_argument("--top-k", type=int, default=ExplorerConfig.top_k)
    ap.add_argument("--jobs", type=int, default=ExplorerConfig.jobs,
                    help="parallel workers for independent group scans")
    ap.add_argument("--dimensionless-only", action="store_true",
                    help="rank only unit-free ratios/log-ratios for stricter known-constant search")
    ap.add_argument("--residual-mode", default=ExplorerConfig.residual_mode,
                    choices=["none", "group-median"],
                    help="subtract an expected group median before candidate discovery")
    ap.add_argument("--residual-metrics-only", action="store_true",
                    help="when residual-mode is active, rank only *_resid metrics")
    ap.add_argument("--residual-group", default=ExplorerConfig.residual_group,
                    help="comma-separated pair fields used to estimate residual baseline")
    ap.add_argument("--residual-metrics", default=ExplorerConfig.residual_metrics,
                    help="comma-separated base metrics to residualize")
    ap.add_argument("--focus-metric", default=ExplorerConfig.focus_metric,
                    help="comma-separated metric names to keep, e.g. energy_distance_balance_resid")
    ap.add_argument("--focus-mag-delta-range", default=ExplorerConfig.focus_mag_delta_range,
                    help="pre-registered abs(delta magnitude) range LO,HI, e.g. 0.5,1.5")
    ap.add_argument("--focus-only", action="store_true",
                    help="rank only the configured focus metric/range hypothesis")
    ap.add_argument("--event-source", default=ExplorerConfig.event_source,
                    choices=["auto", "csv", "master"],
                    help=("auto filters master-like astro/USGS files to rows with mag > --master-min-mag; "
                          "csv keeps all parseable rows"))
    ap.add_argument("--master-min-mag", type=float, default=ExplorerConfig.master_min_mag,
                    help="for event-source auto/master, rows with mag <= this are non-events")
    ap.add_argument("--shuffle-controls", type=int, default=ExplorerConfig.shuffle_controls,
                    help="run N interval-shuffled null catalogs and add empirical score p-values")
    ap.add_argument("--random-seed", type=int, default=ExplorerConfig.random_seed)
    ap.add_argument("--write-pairs", action="store_true",
                    help="also export event-to-event feature rows")
    ap.add_argument("--max-pairs-csv", type=int, default=ExplorerConfig.max_pairs_csv)
    ap.add_argument("--no-png", dest="make_png", action="store_false", default=True)
    return ap


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    return add_arguments(ap)


def config_from_namespace(args: argparse.Namespace) -> ExplorerConfig:
    return ExplorerConfig(
        csv_path=args.csv_path,
        output_dir=args.output_dir,
        output_prefix=args.output_prefix,
        output_suffix=args.output_suffix,
        date_col=args.date_col,
        mag_col=args.mag_col,
        lat_col=args.lat_col,
        lon_col=args.lon_col,
        depth_col=args.depth_col,
        start_date=args.start_date,
        end_date=args.end_date,
        min_mag=args.min_mag,
        max_mag=args.max_mag,
        lags=args.lags,
        mag_bin_width=args.mag_bin_width,
        time_clusters=args.time_clusters,
        min_support=args.min_support,
        top_k=args.top_k,
        jobs=args.jobs,
        dimensionless_only=args.dimensionless_only,
        residual_mode=args.residual_mode,
        residual_metrics_only=args.residual_metrics_only,
        residual_group=args.residual_group,
        residual_metrics=args.residual_metrics,
        focus_metric=args.focus_metric,
        focus_mag_delta_range=args.focus_mag_delta_range,
        focus_only=args.focus_only,
        event_source=args.event_source,
        master_min_mag=args.master_min_mag,
        shuffle_controls=args.shuffle_controls,
        random_seed=args.random_seed,
        write_pairs=args.write_pairs,
        max_pairs_csv=args.max_pairs_csv,
        make_png=args.make_png,
        command_line=getattr(args, "command_line", "") or " ".join(shlex.quote(x) for x in sys.argv),
    )


def run_from_namespace(args: argparse.Namespace) -> dict[str, Any]:
    return run(config_from_namespace(args))


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = run_from_namespace(args)
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise SystemExit(f"ERRORE seismic_constant_explorer: {exc}") from exc
    print(f"Candidate CSV: {result['candidate_csv']}")
    print(f"Summary JSON : {result['summary_json']}")
    print(f"Report MD    : {result['report_md']}")
    if result.get("png"):
        print(f"PNG          : {result['png']}")
    if result.get("pair_csv"):
        print(f"Event pairs  : {result['pair_csv']}")
    if result.get("control_csv"):
        print(f"Controls CSV : {result['control_csv']}")
    top = result.get("top_candidates") or []
    if top:
        best = top[0]
        rel_error = best.get("known_rel_error")
        rel_text = f"{float(rel_error):.4g}" if rel_error not in ("", None) else "n/a"
        print(
            "Best candidate: "
            f"{best['metric']} median={float(best['median']):.6g} "
            f"scope={best['scope']} group={best['group_value']} "
            f"known={best.get('known_name') or 'n/a'} rel_err={rel_text}"
        )


if __name__ == "__main__":
    main()
