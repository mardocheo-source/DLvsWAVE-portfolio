#!/usr/bin/env python3
"""Experimental walk-forward forecast from a focused seismic constant signal.

This module is deliberately conservative: it forecasts the next event belonging
to a pre-registered residual-signal family, not earthquakes in general.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import shlex
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from seismic_constant_explorer import (
    ExplorerConfig,
    _cluster_label,
    _haversine_km,
    _mag_bin,
    _parse_float_range,
    _parse_lags,
    _parse_tokens,
    _range_label,
    _safe_log10,
    _time_cluster_edges,
    read_events,
)
from tasks import parse_datetime_like


@dataclass
class ForecastConfig:
    csv_path: str
    output_dir: str = "constant_forecast"
    date_col: str = "auto"
    mag_col: str = "auto"
    lat_col: str = "auto"
    lon_col: str = "auto"
    depth_col: str = "auto"
    start_date: str = ""
    end_date: str = ""
    min_mag: float | None = None
    max_mag: float | None = None
    event_source: str = "auto"
    master_min_mag: float = 0.0
    lags: str = "1,2,3,5,8"
    mag_bin_width: float = 0.5
    time_clusters: int = 4
    residual_group: str = "mag_bin,time_cluster,lag"
    focus_metric: str = "energy_distance_balance_resid"
    focus_mag_delta_range: str = "0.5,1.5"
    target_constant: str = "auto"
    match_quantile: float = 0.25
    forecast_coverage: float = 0.80
    validation_windows: int = 24
    validation_step_events: int = 20
    recent_validation_events: int = 0
    daily_forecast_start: str = ""
    daily_forecast_end: str = ""
    daily_forecast_resolution_days: float = 1.0
    holdout_days: float = 0.0
    holdout_start_date: str = ""
    holdout_end_date: str = ""
    observed_through_date: str = ""
    min_train_events: int = 300
    min_signal_events: int = 12
    command_line: str = ""


def _base_metric(metric: str) -> str:
    return metric[:-6] if metric.endswith("_resid") else metric


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    return float(np.quantile(np.asarray(values, dtype=float), min(1.0, max(0.0, q))))


def _event_pair_features(events: list[dict[str, Any]], cur_idx: int, lag: int,
                         edges: list[float], cfg: ForecastConfig) -> dict[str, Any] | None:
    prev_idx = cur_idx - lag
    if prev_idx < 0:
        return None
    prev = events[prev_idx]
    cur = events[cur_idx]
    dt_days = (cur["date"] - prev["date"]).total_seconds() / 86400.0
    if dt_days <= 0:
        return None

    r2d_km = None
    r3d_km = None
    if prev["lat"] is not None and prev["lon"] is not None and cur["lat"] is not None and cur["lon"] is not None:
        r2d_km = _haversine_km(float(prev["lat"]), float(prev["lon"]), float(cur["lat"]), float(cur["lon"]))
        dz = float(cur["depth_km"] or 0.0) - float(prev["depth_km"] or 0.0)
        r3d_km = math.sqrt(r2d_km ** 2 + dz ** 2)

    loge_prev = 1.5 * float(prev["mag"]) + 4.8
    loge_cur = 1.5 * float(cur["mag"]) + 4.8
    mag_abs_delta = abs(float(cur["mag"]) - float(prev["mag"]))
    focus_range = _parse_float_range(cfg.focus_mag_delta_range)
    focus_label = ""
    if focus_range:
        lo, hi = focus_range
        if lo <= mag_abs_delta < hi:
            focus_label = _range_label("dM", lo, hi)

    r_eff = None
    r = r3d_km if r3d_km is not None else r2d_km
    if r is not None:
        r_eff = max(float(r), 1e-6)

    row: dict[str, Any] = {
        "event_idx": int(cur_idx),
        "lag": int(lag),
        "from_date": prev["date"].isoformat(sep=" "),
        "to_date": cur["date"].isoformat(sep=" "),
        "dt_days": dt_days,
        "mag_prev": float(prev["mag"]),
        "mag_cur": float(cur["mag"]),
        "mag_mid": (float(prev["mag"]) + float(cur["mag"])) / 2.0,
        "mag_abs_delta": mag_abs_delta,
        "time_cluster": _cluster_label(dt_days, edges),
        "mag_bin": _mag_bin((float(prev["mag"]) + float(cur["mag"])) / 2.0, cfg.mag_bin_width),
        "parity_mag_range": _mag_bin(mag_abs_delta, cfg.mag_bin_width),
        "focus_mag_delta_range": focus_label,
        "log10_energy_cur_j": loge_cur,
        "log10_energy_ratio": loge_cur - loge_prev,
        "r2d_km": r2d_km,
        "r3d_km": r3d_km,
        "energy_per_day_log10": loge_cur - _safe_log10(dt_days),
        "energy_ratio_per_day_log10": (loge_cur - loge_prev) - _safe_log10(dt_days),
        "energy_distance_balance": None,
        "bp_eta_log10_df1p6_b1": None,
    }
    if r_eff is not None:
        row["energy_distance_balance"] = loge_cur / (1.0 + _safe_log10(r_eff))
        row["bp_eta_log10_df1p6_b1"] = _safe_log10(dt_days) + 1.6 * _safe_log10(r_eff) - float(prev["mag"])
    return row


def _build_training_pairs(events: list[dict[str, Any]], cfg: ForecastConfig) -> tuple[list[dict[str, Any]], list[float]]:
    lags = _parse_lags(cfg.lags)
    dts: list[float] = []
    for lag in lags:
        for idx in range(lag, len(events)):
            dt = (events[idx]["date"] - events[idx - lag]["date"]).total_seconds() / 86400.0
            if dt > 0:
                dts.append(dt)
    edges = _time_cluster_edges(dts, cfg.time_clusters)
    pairs: list[dict[str, Any]] = []
    for lag in lags:
        for idx in range(lag, len(events)):
            row = _event_pair_features(events, idx, lag, edges, cfg)
            if row is not None:
                pairs.append(row)
    return pairs, edges


def _group_key(row: dict[str, Any], group_cols: list[str]) -> tuple[Any, ...]:
    return tuple(row.get(col, "") for col in group_cols)


def _fit_baselines(pairs: list[dict[str, Any]], cfg: ForecastConfig) -> dict[tuple[Any, ...], float]:
    group_cols = _parse_tokens(cfg.residual_group)
    base = _base_metric(cfg.focus_metric)
    buckets: dict[tuple[Any, ...], list[float]] = {}
    for row in pairs:
        value = row.get(base)
        if _finite(value):
            buckets.setdefault(_group_key(row, group_cols), []).append(float(value))
    return {key: float(np.median(vals)) for key, vals in buckets.items() if vals}


def _residual_value(row: dict[str, Any], cfg: ForecastConfig,
                    baselines: dict[tuple[Any, ...], float]) -> float | None:
    group_cols = _parse_tokens(cfg.residual_group)
    base = _base_metric(cfg.focus_metric)
    value = row.get(base)
    expected = baselines.get(_group_key(row, group_cols))
    if expected is None or not _finite(value):
        return None
    return float(value) - float(expected)


def fit_signal_model(events: list[dict[str, Any]], cfg: ForecastConfig) -> dict[str, Any]:
    if len(events) < max(3, int(cfg.min_train_events)):
        raise ValueError(f"Servono almeno {cfg.min_train_events} eventi di train per il forecast")
    pairs, edges = _build_training_pairs(events, cfg)
    baselines = _fit_baselines(pairs, cfg)
    focus_rows: list[dict[str, Any]] = []
    residuals: list[float] = []
    for row in pairs:
        if not row.get("focus_mag_delta_range"):
            continue
        resid = _residual_value(row, cfg, baselines)
        if resid is None:
            continue
        clone = dict(row)
        clone["residual"] = resid
        focus_rows.append(clone)
        residuals.append(resid)
    if len(residuals) < int(cfg.min_signal_events):
        raise ValueError("Pochi eventi focus nel train: aumenta finestra o abbassa min_signal_events")

    if str(cfg.target_constant).lower() == "auto":
        constant = float(np.median(np.asarray(residuals, dtype=float)))
    else:
        constant = float(cfg.target_constant)
    distances = [abs(v - constant) for v in residuals]
    threshold = max(_quantile(distances, cfg.match_quantile), 1e-12)

    compatible_by_idx: dict[int, dict[str, Any]] = {}
    for row in focus_rows:
        dist = abs(float(row["residual"]) - constant)
        if dist > threshold:
            continue
        idx = int(row["event_idx"])
        prev = compatible_by_idx.get(idx)
        if prev is None or dist < float(prev["distance_to_constant"]):
            compatible_by_idx[idx] = {
                "event_idx": idx,
                "date": events[idx]["date"],
                "residual": float(row["residual"]),
                "distance_to_constant": dist,
                "lag": int(row["lag"]),
                "mag": float(events[idx]["mag"]),
            }
    compatible = [compatible_by_idx[idx] for idx in sorted(compatible_by_idx)]
    if len(compatible) < int(cfg.min_signal_events):
        raise ValueError("Pochi eventi compatibili nel train: aumenta match_quantile o abbassa min_signal_events")
    gaps = [
        (compatible[i]["date"] - compatible[i - 1]["date"]).total_seconds() / 86400.0
        for i in range(1, len(compatible))
    ]
    if not gaps:
        raise ValueError("Intervalli compatibili insufficienti per stimare una finestra")

    alpha = max(0.0, min(0.98, 1.0 - float(cfg.forecast_coverage))) / 2.0
    q_low = _quantile(gaps, alpha)
    q_med = _quantile(gaps, 0.5)
    q_high = _quantile(gaps, 1.0 - alpha)
    return {
        "edges": edges,
        "baselines": baselines,
        "constant": constant,
        "threshold": threshold,
        "compatible": compatible,
        "gaps": gaps,
        "q_low_days": q_low,
        "q_median_days": q_med,
        "q_high_days": q_high,
        "focus_pair_count": len(focus_rows),
        "compatible_event_count": len(compatible),
    }


def _compatible_event_score(events: list[dict[str, Any]], idx: int, cfg: ForecastConfig,
                            model: dict[str, Any]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for lag in _parse_lags(cfg.lags):
        row = _event_pair_features(events, idx, lag, model["edges"], cfg)
        if row is None or not row.get("focus_mag_delta_range"):
            continue
        resid = _residual_value(row, cfg, model["baselines"])
        if resid is None:
            continue
        dist = abs(float(resid) - float(model["constant"]))
        if dist <= float(model["threshold"]) and (best is None or dist < float(best["distance_to_constant"])):
            best = {
                "event_idx": idx,
                "date": events[idx]["date"],
                "mag": float(events[idx]["mag"]),
                "lat": events[idx]["lat"],
                "lon": events[idx]["lon"],
                "depth_km": events[idx]["depth_km"],
                "lag": lag,
                "residual": float(resid),
                "distance_to_constant": dist,
            }
    return best


def _next_compatible_event(events: list[dict[str, Any]], start_idx: int, cfg: ForecastConfig,
                           model: dict[str, Any]) -> dict[str, Any] | None:
    for idx in range(max(0, int(start_idx)), len(events)):
        hit = _compatible_event_score(events, idx, cfg, model)
        if hit is not None:
            return hit
    return None


def _forecast_from_model(anchor_date: Any, model: dict[str, Any]) -> dict[str, Any]:
    last = model["compatible"][-1]["date"]
    raw_start = last + timedelta(days=float(model["q_low_days"]))
    median = last + timedelta(days=float(model["q_median_days"]))
    raw_end = last + timedelta(days=float(model["q_high_days"]))
    window_already_open = raw_start <= anchor_date <= raw_end
    window_expired = raw_end < anchor_date
    practical_start = anchor_date if window_already_open else raw_start
    return {
        "last_compatible_date": last,
        "raw_start": raw_start,
        "start": practical_start,
        "median": median,
        "end": raw_end,
        "window_already_open": bool(window_already_open),
        "window_expired": bool(window_expired),
    }


def _daily_forecast_rows(model: dict[str, Any], cfg: ForecastConfig) -> list[dict[str, Any]]:
    if not cfg.daily_forecast_start or not cfg.daily_forecast_end:
        return []
    start = parse_datetime_like(cfg.daily_forecast_start)
    end = parse_datetime_like(cfg.daily_forecast_end)
    if start is None or end is None:
        raise ValueError("--daily-forecast-start/end non parseabili")
    if end < start:
        raise ValueError("--daily-forecast-end deve essere >= --daily-forecast-start")
    step = max(1e-6, float(cfg.daily_forecast_resolution_days))
    last = model["compatible"][-1]["date"]
    gaps = [float(v) for v in model.get("gaps", []) if _finite(v) and float(v) > 0]
    if not gaps:
        return []
    arr = np.asarray(gaps, dtype=float)
    observed_through = parse_datetime_like(cfg.observed_through_date) if cfg.observed_through_date else None
    rows: list[dict[str, Any]] = []
    cursor = start
    while cursor <= end:
        next_cursor = cursor + timedelta(days=step)
        age_start = (cursor - last).total_seconds() / 86400.0
        age_end = (next_cursor - last).total_seconds() / 86400.0
        if age_end <= 0:
            cdf_start = cdf_end = mass = hazard = 0.0
        else:
            a0 = max(0.0, age_start)
            a1 = max(0.0, age_end)
            cdf_start = float(np.mean(arr < a0))
            cdf_end = float(np.mean(arr < a1))
            mass = max(0.0, cdf_end - cdf_start)
            survivor = max(1e-12, 1.0 - cdf_start)
            hazard = mass / survivor
        rows.append({
            "date": cursor.date().isoformat(),
            "window_start": cursor.isoformat(sep=" "),
            "window_end": next_cursor.isoformat(sep=" "),
            "observed_status": "observed" if observed_through is None or cursor <= observed_through else "future",
            "days_since_last_signal": age_start,
            "empirical_cdf_start": cdf_start,
            "empirical_cdf_end": cdf_end,
            "unconditional_daily_mass": mass,
            "conditional_daily_probability": hazard,
            "inside_coverage_window": int(
                float(model["q_low_days"]) <= max(0.0, age_start) <= float(model["q_high_days"])
            ),
            "near_median_score": 1.0 / (1.0 + abs(max(0.0, age_start) - float(model["q_median_days"]))),
        })
        cursor = next_cursor
    max_hazard = max((float(r["conditional_daily_probability"]) for r in rows), default=0.0)
    max_median_score = max((float(r["near_median_score"]) for r in rows), default=0.0)
    for row in rows:
        row["daily_risk_score"] = (
            0.7 * (float(row["conditional_daily_probability"]) / max(max_hazard, 1e-12))
            + 0.3 * (float(row["near_median_score"]) / max(max_median_score, 1e-12))
        )
    return rows


def _annotate_daily_actuals(rows: list[dict[str, Any]], events: list[dict[str, Any]],
                            start_idx: int, cfg: ForecastConfig,
                            model: dict[str, Any]) -> list[dict[str, Any]]:
    for row in rows:
        row["actual_signal_event_count"] = 0
        row["actual_signal_event_dates"] = ""
        row["actual_signal_event_mags"] = ""
        row["actual_signal_event_lags"] = ""
    if not rows:
        return rows
    windows = [
        (
            parse_datetime_like(str(row["window_start"])),
            parse_datetime_like(str(row["window_end"])),
            row,
        )
        for row in rows
    ]
    hits_by_row: dict[int, list[dict[str, Any]]] = {id(row): [] for _, _, row in windows}
    for idx in range(max(0, int(start_idx)), len(events)):
        hit = _compatible_event_score(events, idx, cfg, model)
        if hit is None:
            continue
        event_dt = hit["date"]
        for start, end, row in windows:
            if start is not None and end is not None and start <= event_dt < end:
                hits_by_row[id(row)].append(hit)
                break
    for _, _, row in windows:
        hits = hits_by_row[id(row)]
        row["actual_signal_event_count"] = len(hits)
        row["actual_signal_event_dates"] = ";".join(hit["date"].isoformat(sep=" ") for hit in hits)
        row["actual_signal_event_mags"] = ";".join(f"{float(hit['mag']):.3g}" for hit in hits)
        row["actual_signal_event_lags"] = ";".join(str(hit["lag"]) for hit in hits)
    return rows


def _regular_validation_cuts(n_events: int, cfg: ForecastConfig) -> list[tuple[int, str]]:
    min_train = max(3, int(cfg.min_train_events))
    step = max(1, int(cfg.validation_step_events))
    cuts = list(range(min_train, max(min_train, n_events - 1), step))
    cuts = [cut for cut in cuts if cut < n_events]
    if cfg.validation_windows > 0:
        cuts = cuts[-int(cfg.validation_windows):]
    return [(cut, "rolling") for cut in cuts]


def _recent_signal_validation_cuts(events: list[dict[str, Any]], cfg: ForecastConfig) -> list[tuple[int, str]]:
    n = max(0, int(cfg.recent_validation_events))
    if n <= 0:
        return []
    model = fit_signal_model(events, cfg)
    min_train = max(3, int(cfg.min_train_events))
    cuts = [
        int(row["event_idx"]) for row in model["compatible"]
        if int(row["event_idx"]) >= min_train and int(row["event_idx"]) < len(events)
    ]
    cuts = cuts[-n:]
    return [(cut, "recent_signal") for cut in cuts]


def _validation_cuts(events: list[dict[str, Any]], cfg: ForecastConfig) -> list[tuple[int, str]]:
    recent = _recent_signal_validation_cuts(events, cfg)
    if recent:
        return recent
    return _regular_validation_cuts(len(events), cfg)


def _resolve_holdout(events: list[dict[str, Any]], cfg: ForecastConfig) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not events:
        raise ValueError("Catalogo vuoto")
    holdout_start = parse_datetime_like(cfg.holdout_start_date) if cfg.holdout_start_date else None
    holdout_end = parse_datetime_like(cfg.holdout_end_date) if cfg.holdout_end_date else None
    if holdout_start is None and float(cfg.holdout_days or 0.0) > 0.0:
        holdout_start = events[-1]["date"] - timedelta(days=float(cfg.holdout_days))
    if holdout_end is None and holdout_start is not None:
        holdout_end = events[-1]["date"]
    if holdout_start is None:
        return events, {
            "enabled": False,
            "train_event_count": len(events),
            "holdout_event_count": 0,
            "holdout_start": "",
            "holdout_end": "",
            "first_holdout_index": len(events),
        }
    if holdout_end is None or holdout_end < holdout_start:
        raise ValueError("Holdout non valido: end deve essere >= start")
    train = [event for event in events if event["date"] < holdout_start]
    first_holdout_index = len(train)
    holdout = [event for event in events if holdout_start <= event["date"] <= holdout_end]
    if len(train) < int(cfg.min_train_events):
        raise ValueError("Holdout troppo largo: restano pochi eventi di train")
    if not holdout:
        raise ValueError("Holdout senza eventi reali nel catalogo")
    if not cfg.daily_forecast_start:
        cfg.daily_forecast_start = holdout_start.date().isoformat()
    if not cfg.daily_forecast_end:
        cfg.daily_forecast_end = holdout_end.date().isoformat()
    return train, {
        "enabled": True,
        "train_event_count": len(train),
        "holdout_event_count": len(holdout),
        "holdout_start": holdout_start.isoformat(sep=" "),
        "holdout_end": holdout_end.isoformat(sep=" "),
        "first_holdout_index": first_holdout_index,
    }


def run(cfg: ForecastConfig) -> dict[str, Any]:
    explorer_cfg = ExplorerConfig(
        csv_path=cfg.csv_path,
        output_dir=cfg.output_dir,
        date_col=cfg.date_col,
        mag_col=cfg.mag_col,
        lat_col=cfg.lat_col,
        lon_col=cfg.lon_col,
        depth_col=cfg.depth_col,
        start_date=cfg.start_date,
        end_date=cfg.end_date,
        min_mag=cfg.min_mag,
        max_mag=cfg.max_mag,
        event_source=cfg.event_source,
        master_min_mag=cfg.master_min_mag,
        lags=cfg.lags,
        mag_bin_width=cfg.mag_bin_width,
        time_clusters=cfg.time_clusters,
        residual_group=cfg.residual_group,
        residual_metrics=_base_metric(cfg.focus_metric),
        focus_metric=cfg.focus_metric,
        focus_mag_delta_range=cfg.focus_mag_delta_range,
        focus_only=True,
        command_line=cfg.command_line,
    )
    events, meta = read_events(explorer_cfg)
    if len(events) < int(cfg.min_train_events) + 2:
        raise ValueError("Catalogo troppo corto per train + validation")
    forecast_train_events, holdout_info = _resolve_holdout(events, cfg)

    rows: list[dict[str, Any]] = []
    for no, (cut, validation_kind) in enumerate(_validation_cuts(forecast_train_events, cfg), start=1):
        train = forecast_train_events[:cut]
        anchor_date = train[-1]["date"]
        try:
            model = fit_signal_model(train, cfg)
            forecast = _forecast_from_model(anchor_date, model)
            actual = _next_compatible_event(forecast_train_events, cut, cfg, model)
        except ValueError as exc:
            rows.append({
                "window_no": no,
                "validation_kind": validation_kind,
                "train_events": cut,
                "anchor_date": anchor_date.isoformat(sep=" "),
                "status": f"skipped: {exc}",
            })
            continue
        hit = False
        lead_days = ""
        actual_date = ""
        actual_mag = ""
        actual_lag = ""
        if actual is not None:
            actual_date_obj = actual["date"]
            hit = forecast["start"] <= actual_date_obj <= forecast["end"]
            lead_days = (actual_date_obj - anchor_date).total_seconds() / 86400.0
            actual_date = actual_date_obj.isoformat(sep=" ")
            actual_mag = actual["mag"]
            actual_lag = actual["lag"]
        rows.append({
            "window_no": no,
            "validation_kind": validation_kind,
            "train_events": cut,
            "anchor_date": anchor_date.isoformat(sep=" "),
            "constant": model["constant"],
            "threshold": model["threshold"],
            "compatible_train_events": model["compatible_event_count"],
            "focus_pair_count": model["focus_pair_count"],
            "forecast_start": forecast["start"].isoformat(sep=" "),
            "forecast_median": forecast["median"].isoformat(sep=" "),
            "forecast_end": forecast["end"].isoformat(sep=" "),
            "window_already_open": forecast["window_already_open"],
            "window_expired": forecast["window_expired"],
            "actual_next_compatible_date": actual_date,
            "actual_next_compatible_mag": actual_mag,
            "actual_next_compatible_lag": actual_lag,
            "actual_lead_days": lead_days,
            "hit": int(hit),
            "status": "ok",
        })

    final_model = fit_signal_model(forecast_train_events, cfg)
    final_forecast = _forecast_from_model(forecast_train_events[-1]["date"], final_model)
    daily_rows = _daily_forecast_rows(final_model, cfg)
    if daily_rows:
        _annotate_daily_actuals(
            daily_rows,
            events,
            int(holdout_info.get("first_holdout_index", len(forecast_train_events))),
            cfg,
            final_model,
        )
    final_row = {
        "catalog_last_event_date": events[-1]["date"].isoformat(sep=" "),
        "catalog_last_event_mag": float(events[-1]["mag"]),
        "catalog_last_event_lat": events[-1]["lat"],
        "catalog_last_event_lon": events[-1]["lon"],
        "training_last_event_date": forecast_train_events[-1]["date"].isoformat(sep=" "),
        "training_last_event_mag": float(forecast_train_events[-1]["mag"]),
        "forecast_uses_holdout": bool(holdout_info.get("enabled")),
        "holdout_start": holdout_info.get("holdout_start", ""),
        "holdout_end": holdout_info.get("holdout_end", ""),
        "signal": cfg.focus_metric,
        "focus_mag_delta_range": cfg.focus_mag_delta_range,
        "constant": final_model["constant"],
        "threshold": final_model["threshold"],
        "compatible_train_events": final_model["compatible_event_count"],
        "q_low_days": final_model["q_low_days"],
        "q_median_days": final_model["q_median_days"],
        "q_high_days": final_model["q_high_days"],
        "forecast_start": final_forecast["start"].isoformat(sep=" "),
        "forecast_median": final_forecast["median"].isoformat(sep=" "),
        "forecast_end": final_forecast["end"].isoformat(sep=" "),
        "window_already_open": final_forecast["window_already_open"],
        "window_expired": final_forecast["window_expired"],
    }

    ok_rows = [r for r in rows if r.get("status") == "ok" and r.get("actual_next_compatible_date")]
    hit_count = sum(int(r.get("hit", 0)) for r in ok_rows)
    hit_rate = hit_count / len(ok_rows) if ok_rows else None
    widths = []
    for r in ok_rows:
        start = datetime.fromisoformat(str(r["forecast_start"]))
        end = datetime.fromisoformat(str(r["forecast_end"]))
        widths.append((end - start).total_seconds() / 86400.0)

    out_dir = Path(cfg.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"constant_forecast_{Path(cfg.csv_path).stem}_{stamp}"
    validation_csv = out_dir / f"{stem}_validation.csv"
    forecast_csv = out_dir / f"{stem}_forecast.csv"
    daily_csv = out_dir / f"{stem}_daily_forecast.csv"
    daily_png = out_dir / f"{stem}_daily_forecast.png"
    summary_json = out_dir / f"{stem}_summary.json"
    report_md = out_dir / f"{stem}_report.md"

    _write_csv(validation_csv, rows)
    _write_csv(forecast_csv, [final_row])
    daily_png_written = False
    if daily_rows:
        _write_csv(daily_csv, daily_rows)
        daily_png_written = _write_daily_png(daily_png, daily_rows)
    summary = {
        "config": asdict(cfg),
        "meta": meta,
        "holdout": holdout_info,
        "event_count": len(events),
        "forecast_train_event_count": len(forecast_train_events),
        "validation_windows": len(rows),
        "validation_evaluated": len(ok_rows),
        "hit_count": hit_count,
        "hit_rate": hit_rate,
        "median_window_width_days": _quantile(widths, 0.5) if widths else None,
        "forecast": final_row,
        "daily_forecast": {
            "csv": str(daily_csv) if daily_rows else "",
            "png": str(daily_png) if daily_png_written else "",
            "row_count": len(daily_rows),
            "start": cfg.daily_forecast_start,
            "end": cfg.daily_forecast_end,
            "resolution_days": cfg.daily_forecast_resolution_days,
            "top_days": sorted(
                daily_rows,
                key=lambda row: float(row.get("daily_risk_score", 0.0)),
                reverse=True,
            )[:10],
        },
        "command_line": cfg.command_line or " ".join(shlex.quote(x) for x in sys.argv),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    _write_json(summary_json, summary)
    _write_report(report_md, summary, rows)
    return {
        "validation_csv": str(validation_csv),
        "forecast_csv": str(forecast_csv),
        "daily_csv": str(daily_csv) if daily_rows else "",
        "daily_png": str(daily_png) if daily_png_written else "",
        "summary_json": str(summary_json),
        "report_md": str(report_md),
        "summary": summary,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=2, sort_keys=True, default=str)


def _write_daily_png(path: Path, rows: list[dict[str, Any]]) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[warn] matplotlib unavailable, daily PNG skipped: {exc}")
        return False
    if not rows:
        return False
    dates = [datetime.fromisoformat(str(row["window_start"])) for row in rows]
    scores = [float(row.get("daily_risk_score", 0.0)) for row in rows]
    probs = [float(row.get("conditional_daily_probability", 0.0)) for row in rows]
    inside = [int(row.get("inside_coverage_window", 0) or 0) for row in rows]
    actual = [min(1.0, float(row.get("actual_signal_event_count", 0) or 0)) for row in rows]
    future_dates = [date for date, row in zip(dates, rows) if row.get("observed_status") == "future"]

    fig, ax1 = plt.subplots(figsize=(12, 6.2))
    ax1.plot(dates, scores, color="#1d4ed8", linewidth=2.0, marker="o", markersize=3, label="daily risk score")
    if any(v > 0 for v in actual):
        ax1.step(dates, actual, where="post", color="#16a34a", linewidth=2.0, label="actual signal event")
        ax1.scatter(
            [date for date, value in zip(dates, actual) if value > 0],
            [1.0 for value in actual if value > 0],
            color="#16a34a",
            s=38,
            zorder=5,
        )
    ax1.set_ylabel("daily risk score", color="#1d4ed8")
    ax1.tick_params(axis="y", labelcolor="#1d4ed8")
    ax1.set_ylim(bottom=0)
    ax1.grid(True, axis="both", alpha=0.25)
    for date, flag in zip(dates, inside):
        if flag:
            ax1.axvspan(date, date + timedelta(days=1), color="#bfdbfe", alpha=0.25, linewidth=0)
    if future_dates:
        ax1.axvspan(min(future_dates), dates[-1] + timedelta(days=1), color="#e5e7eb", alpha=0.28,
                    linewidth=0, label="future / unobserved")

    ax2 = ax1.twinx()
    ax2.bar(dates, probs, width=0.75, color="#f97316", alpha=0.35, label="conditional daily probability")
    ax2.set_ylabel("conditional daily probability", color="#c2410c")
    ax2.tick_params(axis="y", labelcolor="#c2410c")
    ax2.set_ylim(bottom=0)

    max_labels = 22
    tick_step = max(2, int(math.ceil(len(dates) / max_labels)))
    tick_dates = dates[::tick_step]
    if dates[-1] not in tick_dates:
        tick_dates.append(dates[-1])
    ax1.set_xticks(tick_dates)
    ax1.set_xticklabels([date.strftime("%Y-%m-%d") for date in tick_dates], rotation=90, ha="center")
    ax1.tick_params(axis="x", labelsize=8)
    ax1.set_title("Experimental daily signal forecast")
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, loc="upper right")
    fig.subplots_adjust(bottom=0.24, top=0.90, left=0.08, right=0.92)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return True


def _write_report(path: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    fc = summary["forecast"]
    daily = summary.get("daily_forecast") or {}
    hit_rate = summary["hit_rate"]
    hit_text = "n/a" if hit_rate is None else f"{100.0 * hit_rate:.1f}%"
    lines = [
        "# Experimental Seismic Constant Forecast",
        "",
        "This is not an operational earthquake prediction. It forecasts the next",
        "event matching the focused residual signal family and validates that rule",
        "with walk-forward splits.",
        "",
        "## Forecast",
        "",
        f"- signal: `{fc['signal']}`",
        f"- focus magnitude delta range: `{fc['focus_mag_delta_range']}`",
        f"- last catalog event: `{fc['catalog_last_event_date']}` mag={fc['catalog_last_event_mag']:.3g}",
        f"- training last event: `{fc.get('training_last_event_date', fc['catalog_last_event_date'])}`",
        f"- holdout: {fc.get('forecast_uses_holdout', False)} "
        f"{fc.get('holdout_start', '')} -> {fc.get('holdout_end', '')}",
        f"- constant estimate: {float(fc['constant']):.6g}",
        f"- match threshold: {float(fc['threshold']):.6g}",
        f"- next signal-window start: `{fc['forecast_start']}`",
        f"- next signal-window median: `{fc['forecast_median']}`",
        f"- next signal-window end: `{fc['forecast_end']}`",
        f"- window already open: {fc['window_already_open']}",
        f"- window expired: {fc['window_expired']}",
        "",
        "## Daily Forecast",
        "",
        f"- CSV: `{daily.get('csv', '') or 'not requested'}`",
        f"- PNG: `{daily.get('png', '') or 'not generated'}`",
        f"- rows: {daily.get('row_count', 0)}",
        "",
        "| date | daily risk score | conditional probability | actual signal events | inside window |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in daily.get("top_days", [])[:10]:
        lines.append(
            f"| {row.get('date', '')} | {float(row.get('daily_risk_score', 0.0)):.4g} | "
            f"{float(row.get('conditional_daily_probability', 0.0)):.4g} | "
            f"{row.get('actual_signal_event_count', '')} | "
            f"{row.get('inside_coverage_window', '')} |"
        )
    lines.extend([
        "",
        "## Validation",
        "",
        f"- windows requested/evaluated: {summary['validation_windows']} / {summary['validation_evaluated']}",
        f"- hit count: {summary['hit_count']}",
        f"- hit rate: {hit_text}",
        f"- median window width days: {summary['median_window_width_days']}",
        "",
        "## Recent Validation Rows",
        "",
        "| window | kind | anchor | forecast start | forecast end | actual next signal event | hit |",
        "|---:|---|---|---|---|---|---:|",
    ])
    for row in rows[-10:]:
        lines.append(
            f"| {row.get('window_no', '')} | {row.get('validation_kind', '')} | "
            f"{row.get('anchor_date', '')} | "
            f"{row.get('forecast_start', '')} | {row.get('forecast_end', '')} | "
            f"{row.get('actual_next_compatible_date', '')} | {row.get('hit', '')} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def add_arguments(ap: argparse.ArgumentParser) -> argparse.ArgumentParser:
    ap.add_argument("--task", "--csv", dest="csv_path", required=True)
    ap.add_argument("--output-dir", default=ForecastConfig.output_dir)
    ap.add_argument("--date-col", default=ForecastConfig.date_col)
    ap.add_argument("--mag-col", default=ForecastConfig.mag_col)
    ap.add_argument("--lat-col", default=ForecastConfig.lat_col)
    ap.add_argument("--lon-col", default=ForecastConfig.lon_col)
    ap.add_argument("--depth-col", default=ForecastConfig.depth_col)
    ap.add_argument("--start-date", default="")
    ap.add_argument("--end-date", default="")
    ap.add_argument("--min-mag", type=float, default=None)
    ap.add_argument("--max-mag", type=float, default=None)
    ap.add_argument("--event-source", default=ForecastConfig.event_source, choices=["auto", "csv", "master"])
    ap.add_argument("--master-min-mag", type=float, default=ForecastConfig.master_min_mag)
    ap.add_argument("--lags", default=ForecastConfig.lags)
    ap.add_argument("--mag-bin-width", type=float, default=ForecastConfig.mag_bin_width)
    ap.add_argument("--time-clusters", type=int, default=ForecastConfig.time_clusters)
    ap.add_argument("--residual-group", default=ForecastConfig.residual_group)
    ap.add_argument("--focus-metric", default=ForecastConfig.focus_metric)
    ap.add_argument("--focus-mag-delta-range", default=ForecastConfig.focus_mag_delta_range)
    ap.add_argument("--target-constant", default=ForecastConfig.target_constant,
                    help="auto oppure valore numerico, esempio 0.025")
    ap.add_argument("--match-quantile", type=float, default=ForecastConfig.match_quantile,
                    help="quota dei residui focus piu' vicini alla costante considerata compatibile")
    ap.add_argument("--forecast-coverage", type=float, default=ForecastConfig.forecast_coverage)
    ap.add_argument("--validation-windows", type=int, default=ForecastConfig.validation_windows)
    ap.add_argument("--validation-step-events", type=int, default=ForecastConfig.validation_step_events)
    ap.add_argument("--recent-validation-events", type=int, default=ForecastConfig.recent_validation_events,
                    help="validate on the last N compatible signal events instead of rolling cuts")
    ap.add_argument("--daily-forecast-start", default=ForecastConfig.daily_forecast_start)
    ap.add_argument("--daily-forecast-end", default=ForecastConfig.daily_forecast_end)
    ap.add_argument("--daily-forecast-resolution-days", type=float,
                    default=ForecastConfig.daily_forecast_resolution_days)
    ap.add_argument("--holdout-days", type=float, default=ForecastConfig.holdout_days,
                    help="pure backtest: fit before the last N days, forecast/overlay the held-out period")
    ap.add_argument("--holdout-start-date", default=ForecastConfig.holdout_start_date,
                    help="pure backtest: explicit holdout start date")
    ap.add_argument("--holdout-end-date", default=ForecastConfig.holdout_end_date,
                    help="pure backtest: explicit holdout end date; default last catalog event")
    ap.add_argument("--observed-through-date", default=ForecastConfig.observed_through_date,
                    help="daily forecast: mark rows after this date as future/unobserved")
    ap.add_argument("--min-train-events", type=int, default=ForecastConfig.min_train_events)
    ap.add_argument("--min-signal-events", type=int, default=ForecastConfig.min_signal_events)
    return ap


def config_from_namespace(args: argparse.Namespace) -> ForecastConfig:
    return ForecastConfig(
        csv_path=args.csv_path,
        output_dir=args.output_dir,
        date_col=args.date_col,
        mag_col=args.mag_col,
        lat_col=args.lat_col,
        lon_col=args.lon_col,
        depth_col=args.depth_col,
        start_date=args.start_date,
        end_date=args.end_date,
        min_mag=args.min_mag,
        max_mag=args.max_mag,
        event_source=args.event_source,
        master_min_mag=args.master_min_mag,
        lags=args.lags,
        mag_bin_width=args.mag_bin_width,
        time_clusters=args.time_clusters,
        residual_group=args.residual_group,
        focus_metric=args.focus_metric,
        focus_mag_delta_range=args.focus_mag_delta_range,
        target_constant=args.target_constant,
        match_quantile=args.match_quantile,
        forecast_coverage=args.forecast_coverage,
        validation_windows=args.validation_windows,
        validation_step_events=args.validation_step_events,
        recent_validation_events=args.recent_validation_events,
        daily_forecast_start=args.daily_forecast_start,
        daily_forecast_end=args.daily_forecast_end,
        daily_forecast_resolution_days=args.daily_forecast_resolution_days,
        holdout_days=args.holdout_days,
        holdout_start_date=args.holdout_start_date,
        holdout_end_date=args.holdout_end_date,
        observed_through_date=args.observed_through_date,
        min_train_events=args.min_train_events,
        min_signal_events=args.min_signal_events,
        command_line=getattr(args, "command_line", "") or " ".join(shlex.quote(x) for x in sys.argv),
    )


def run_from_namespace(args: argparse.Namespace) -> dict[str, Any]:
    return run(config_from_namespace(args))


def main() -> None:
    ap = add_arguments(argparse.ArgumentParser(description=__doc__))
    result = run_from_namespace(ap.parse_args())
    print(f"Validation CSV: {result['validation_csv']}")
    print(f"Forecast CSV  : {result['forecast_csv']}")
    if result.get("daily_csv"):
        print(f"Daily CSV     : {result['daily_csv']}")
    if result.get("daily_png"):
        print(f"Daily PNG     : {result['daily_png']}")
    print(f"Summary JSON  : {result['summary_json']}")
    print(f"Report MD     : {result['report_md']}")


if __name__ == "__main__":
    main()
