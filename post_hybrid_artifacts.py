#!/usr/bin/env python3
"""
Post-hybrid di artifact gia' esportati.

Combina due trial senza rifare training: legge i CSV validation/forecast prodotti
da export_best_trial, normalizza opzionalmente le predizioni, applica logica
AND/OR/weighted e scrive nuovi CSV/PNG piu' un JSON descrittivo delle regole LCS
coinvolte.

Documentazione estesa: POST_HYBRID_ARTIFACTS.md
"""
import argparse
import csv
import glob
import itertools
import json
import math
import os
import shutil
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

from artifacts import safe_slug, write_combined_panels_png


def _load_json(path):
    with open(path) as f:
        return json.load(f)


def _to_float(value, default=float("nan")):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _read_rows(path, *, has_segment):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out = dict(row)
            out["_row_index"] = int(float(row.get("row_index", len(rows))))
            out["_segment"] = row.get("segment", "") if has_segment else ""
            out["_actual"] = _to_float(row.get("actual"))
            out["_predicted"] = _to_float(row.get("predicted"))
            out["_pred_recalibrated"] = _to_float(row.get("pred_recalibrated"))
            rows.append(out)
    return rows


def _key(row, *, has_segment):
    date_key = row.get("date") or row.get("context") or ""
    if date_key:
        return (row.get("_segment", "") if has_segment else "", date_key[:10])
    if has_segment:
        return (row.get("_segment", ""), row.get("_row_index"))
    return (row.get("_row_index"),)


def _align_rows(rows_a, rows_b, *, has_segment):
    by_b = {_key(r, has_segment=has_segment): r for r in rows_b}
    aligned = []
    for a in rows_a:
        b = by_b.get(_key(a, has_segment=has_segment))
        if b is not None:
            aligned.append((a, b))
    return aligned


def _finite(values):
    return [v for v in values if math.isfinite(v)]


def _is_binary(values):
    vals = _finite(values)
    if not vals:
        return True
    return all(abs(v - 0.0) < 1e-9 or abs(v - 1.0) < 1e-9 for v in vals)


def _fit_normalizer(values, mode):
    vals = _finite(values)
    if mode == "auto":
        mode = "binary" if _is_binary(vals) else "minmax"
    if mode == "none":
        return {"mode": "none"}
    if mode == "binary":
        return {"mode": "binary"}
    if mode == "minmax":
        if not vals:
            return {"mode": "minmax", "lo": 0.0, "hi": 1.0}
        lo, hi = min(vals), max(vals)
        return {"mode": "minmax", "lo": float(lo), "hi": float(hi)}
    raise ValueError(f"normalizzazione non supportata: {mode}")


def _apply_normalizer(value, norm, *, raw_threshold, normalized_threshold):
    if not math.isfinite(value):
        return 0.0
    mode = norm.get("mode")
    if mode == "none":
        return float(value)
    if mode == "binary":
        return 1.0 if float(value) >= float(raw_threshold) else 0.0
    if mode == "minmax":
        lo, hi = float(norm.get("lo", 0.0)), float(norm.get("hi", 1.0))
        if abs(hi - lo) < 1e-12:
            return 1.0 if float(value) >= float(raw_threshold) else 0.0
        return max(0.0, min(1.0, (float(value) - lo) / (hi - lo)))
    return 1.0 if float(value) >= float(normalized_threshold) else 0.0


def _artifact_threshold(meta, fallback=0.1):
    model_cfg = meta.get("model_config", {}) or {}
    hybrid_cfg = model_cfg.get("hybrid_cfg", {}) or {}
    if "event_threshold" in hybrid_cfg:
        return float(hybrid_cfg["event_threshold"])
    lcs_cfg = model_cfg.get("lcs_cfg", {}) or {}
    if "binary_threshold" in lcs_cfg:
        return float(lcs_cfg["binary_threshold"])
    split = meta.get("split_info", {}) or {}
    if "threshold" in split:
        return float(split["threshold"])
    return float(fallback)


def _artifact_prediction_threshold(meta, fallback=0.5):
    params = meta.get("params", {}) or {}
    if isinstance(params, dict) and params.get("metric_prediction_threshold") is not None:
        return float(params["metric_prediction_threshold"])
    model_cfg = meta.get("model_config", {}) or {}
    hybrid_cfg = model_cfg.get("hybrid_cfg", {}) or {}
    if "hybrid_threshold" in hybrid_cfg:
        return float(hybrid_cfg["hybrid_threshold"])
    if meta.get("bank") in ("__lcs__", "__hybrid__"):
        return 0.5
    return float(fallback)


def _score_value(row, column):
    if column == "pred_recalibrated":
        return row["_pred_recalibrated"]
    return row["_predicted"]


def _combine(score_a, score_b, logic, alpha, threshold, threshold_a=None, threshold_b=None):
    logic = logic.lower()
    threshold_a = threshold if threshold_a is None else threshold_a
    threshold_b = threshold if threshold_b is None else threshold_b
    a_evt = score_a >= threshold_a
    b_evt = score_b >= threshold_b
    if logic in ("and", "sure"):
        return 1.0 if (a_evt and b_evt) else 0.0
    if logic in ("or", "conservative"):
        return 1.0 if (a_evt or b_evt) else 0.0
    if logic == "weighted":
        score = float(alpha) * score_a + (1.0 - float(alpha)) * score_b
        return 1.0 if score >= threshold else 0.0
    raise ValueError(f"logica non supportata: {logic}")


def _event_metrics(actual, pred):
    tp = fp = tn = fn = 0
    for y, p in zip(actual, pred):
        yy = int(y)
        pp = int(p)
        if yy == 1 and pp == 1:
            tp += 1
        elif yy == 0 and pp == 1:
            fp += 1
        elif yy == 0 and pp == 0:
            tn += 1
        elif yy == 1 and pp == 0:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    bal_acc = 0.5 * (recall + specificity)
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": precision, "recall": recall,
        "specificity": specificity, "f1": f1, "bal_acc": bal_acc,
    }


def _metric_value(metrics, name):
    name = str(name or "f1").lower()
    if name == "f05":
        p, r = metrics["precision"], metrics["recall"]
        beta2 = 0.25
        return (1.0 + beta2) * p * r / (beta2 * p + r) if (p + r) else 0.0
    return float(metrics.get(name, metrics["f1"]))


def _threshold_candidates(scores):
    vals = sorted(set(round(v, 12) for v in _finite(scores)))
    if not vals:
        return [0.5]
    candidates = {0.0, 0.5, 1.0, min(vals) - 1e-9, max(vals) + 1e-9}
    candidates.update(vals)
    for a, b in zip(vals, vals[1:]):
        candidates.add((a + b) * 0.5)
    return sorted(candidates)


def _calibrate_thresholds(actual, scores_a, scores_b, *, logic, alpha,
                          threshold, mode, metric_name, min_recall):
    if str(mode or "none").lower() in ("", "none"):
        return {
            "enabled": False,
            "threshold": float(threshold),
            "threshold_a": float(threshold),
            "threshold_b": float(threshold),
            "metric": metric_name,
        }
    logic = logic.lower()
    candidates_a = _threshold_candidates(scores_a)
    candidates_b = _threshold_candidates(scores_b)
    candidates_final = _threshold_candidates(
        [float(alpha) * a + (1.0 - float(alpha)) * b for a, b in zip(scores_a, scores_b)]
    )
    best = None
    if logic == "weighted":
        for th in candidates_final:
            pred = [_combine(a, b, logic, alpha, th) for a, b in zip(scores_a, scores_b)]
            metrics = _event_metrics(actual, pred)
            if metrics["recall"] + 1e-12 < min_recall:
                continue
            key = (
                _metric_value(metrics, metric_name),
                -metrics["fp"],
                metrics["recall"],
                -sum(pred),
            )
            if best is None or key > best["key"]:
                best = {"key": key, "threshold": th, "threshold_a": th,
                        "threshold_b": th, "metrics": metrics}
    else:
        for th_a in candidates_a:
            for th_b in candidates_b:
                pred = [
                    _combine(a, b, logic, alpha, threshold, threshold_a=th_a, threshold_b=th_b)
                    for a, b in zip(scores_a, scores_b)
                ]
                metrics = _event_metrics(actual, pred)
                if metrics["recall"] + 1e-12 < min_recall:
                    continue
                key = (
                    _metric_value(metrics, metric_name),
                    -metrics["fp"],
                    metrics["recall"],
                    -sum(pred),
                )
                if best is None or key > best["key"]:
                    best = {"key": key, "threshold": threshold, "threshold_a": th_a,
                            "threshold_b": th_b, "metrics": metrics}
    if best is None:
        return {
            "enabled": False,
            "reason": "no_candidate_satisfied_min_recall",
            "threshold": float(threshold),
            "threshold_a": float(threshold),
            "threshold_b": float(threshold),
            "metric": metric_name,
            "min_recall": float(min_recall),
        }
    return {
        "enabled": True,
        "mode": mode,
        "metric": metric_name,
        "min_recall": float(min_recall),
        "threshold": float(best["threshold"]),
        "threshold_a": float(best["threshold_a"]),
        "threshold_b": float(best["threshold_b"]),
        "validation_metrics_at_calibration": best["metrics"],
    }


def _artifact_label(meta):
    display_label = meta.get("display_label")
    if display_label:
        return str(display_label)
    return f"{meta.get('bank')} / {meta.get('readout')} / seed{meta.get('seed')}"


def _artifact_source_dir_name(meta, fallback):
    return safe_slug(
        f"{fallback}__{meta.get('bank')}__{meta.get('readout')}__seed{meta.get('seed')}"
    )


def _copy_if_exists(path, dest_dir, copied):
    if not path or not isinstance(path, str):
        return None
    if not os.path.exists(path) or not os.path.isfile(path):
        return None
    src = os.path.abspath(path)
    if src in copied:
        return copied[src]
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(path))
    base, ext = os.path.splitext(dest)
    n = 2
    while os.path.exists(dest) and os.path.abspath(dest) != src:
        dest = f"{base}__copy{n}{ext}"
        n += 1
    shutil.copy2(src, dest)
    copied[src] = dest
    return dest


def _copy_related_sidecars(json_path, dest_dir, copied):
    stem = os.path.splitext(json_path)[0]
    related = []
    for ext in (".csv", ".png"):
        related.extend(glob.glob(stem + "*" + ext))
    for path in sorted(set(related)):
        _copy_if_exists(path, dest_dir, copied)


def _collect_artifact_sources(meta, json_path, dest_dir):
    copied = {}
    manifest = {
        "label": _artifact_label(meta),
        "source_json": json_path,
        "copied_files": [],
    }
    _copy_if_exists(json_path, dest_dir, copied)
    for key in (
        "test_csv", "test_png", "validation_combined_csv",
        "forecast_csv", "forecast_png", "best_rules_json",
        "signature_json",
    ):
        _copy_if_exists(meta.get(key), dest_dir, copied)
    _copy_related_sidecars(json_path, dest_dir, copied)
    manifest["copied_files"] = sorted(copied.values())
    manifest_path = os.path.join(dest_dir, "source_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    return manifest_path


def _json_path_from_index_row(row):
    for key in ("signature_json", "json", "test_json"):
        path = row.get(key)
        if path and os.path.exists(path):
            return path
    test_csv = row.get("test_csv")
    if test_csv:
        guess = os.path.splitext(test_csv)[0] + ".json"
        if os.path.exists(guess):
            return guess
    return None


def _candidate_json_paths(scan_dir=None, index_csv=None):
    paths = []
    if index_csv:
        with open(index_csv, newline="") as f:
            for row in csv.DictReader(f):
                path = _json_path_from_index_row(row)
                if path:
                    paths.append(path)
    if scan_dir:
        paths.extend(glob.glob(os.path.join(scan_dir, "**", "*__test.json"), recursive=True))
    seen = set()
    out = []
    for path in paths:
        abspath = os.path.abspath(path)
        if abspath in seen:
            continue
        seen.add(abspath)
        out.append(abspath)
    return out


def _component(meta, key, default=0.0):
    comps = meta.get("score_components", {}) or {}
    trial = meta.get("trial_metrics", {}) or {}
    winner = meta.get("winner_summary", {}) or {}
    for source in (comps, trial, winner):
        value = source.get(key)
        if value is not None:
            return _to_float(value, default)
    return default


def _trial_metric(meta, key, default=0.0):
    trial = meta.get("trial_metrics", {}) or {}
    value = trial.get(key)
    if value is not None:
        return _to_float(value, default)
    comps = meta.get("score_components", {}) or {}
    alias = {
        "overall": "overall",
        "event_f1": "f1",
        "event_recall": "recall",
        "event_precision": "precision",
        "event_bal_acc": "bal_acc",
    }.get(key)
    if alias and alias in comps:
        return _to_float(comps.get(alias), default)
    return default


def _forecast_stats(meta, score_column):
    path = meta.get("forecast_csv")
    if not path or not os.path.exists(path):
        return {"rows": 0, "std": 0.0, "range": 0.0, "active_raw": 0}
    rows = _read_rows(path, has_segment=False)
    values = [_score_value(r, score_column) for r in rows]
    vals = _finite(values)
    if not vals:
        return {"rows": len(rows), "std": 0.0, "range": 0.0, "active_raw": 0}
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    threshold = _artifact_threshold(meta)
    return {
        "rows": len(rows),
        "std": math.sqrt(var),
        "range": max(vals) - min(vals),
        "active_raw": sum(1 for v in vals if v >= threshold),
        "active_ratio_raw": (
            sum(1 for v in vals if v >= threshold) / len(vals) if vals else 0.0
        ),
    }


def _forecast_guard_from_stats(stats, *, mode, flat_eps, high_ratio):
    mode = str(mode or "auto").lower()
    if mode == "off":
        return {"mode": mode, "penalty": 0.0, "bonus": 0.0, "flags": []}
    rows = int(stats.get("rows", 0) or 0)
    frange = float(stats.get("range", 0.0) or 0.0)
    active_ratio = float(stats.get("active_ratio_raw", 0.0) or 0.0)
    flags = []
    penalty = 0.0
    bonus = 0.0
    if rows <= 0:
        flags.append("missing_forecast")
        return {"mode": mode, "penalty": 0.02, "bonus": 0.0, "flags": flags}
    short = rows <= 2
    if frange <= flat_eps and active_ratio >= high_ratio:
        flags.append("flat_high_forecast")
        penalty += 0.10 if short else 0.20
    elif frange <= flat_eps:
        flags.append("flat_low_or_constant_forecast")
        penalty += 0.00 if not short else 0.01
    else:
        flags.append("variable_forecast")
        bonus += 0.02 if not short else 0.0
    if active_ratio >= 0.90 and not short:
        flags.append("mostly_high_forecast")
        penalty += 0.10
    return {"mode": mode, "penalty": penalty, "bonus": bonus, "flags": flags}


def _candidate_score(meta, score_column, forecast_guard, forecast_flat_eps, forecast_high_ratio):
    overall = _trial_metric(meta, "overall")
    f1 = _trial_metric(meta, "event_f1")
    recall = _trial_metric(meta, "event_recall")
    bal = _trial_metric(meta, "event_bal_acc")
    shape = _component(meta, "shape_overall")
    peak = _component(meta, "peak_score")
    depression = _component(meta, "depression_score")
    forecast = _forecast_stats(meta, score_column)
    guard = _forecast_guard_from_stats(
        forecast, mode=forecast_guard,
        flat_eps=forecast_flat_eps, high_ratio=forecast_high_ratio,
    )
    shape_floor = min(peak, depression)
    score = (
        0.22 * overall
        + 0.22 * f1
        + 0.16 * recall
        + 0.12 * bal
        + 0.18 * shape
        + 0.07 * shape_floor
        + guard["bonus"]
        - guard["penalty"]
    )
    return {
        "candidate_score": max(0.0, float(score)),
        "overall": overall,
        "event_f1": f1,
        "event_recall": recall,
        "event_bal_acc": bal,
        "shape_overall": shape,
        "peak_score": peak,
        "depression_score": depression,
        "shape_floor": shape_floor,
        "forecast_std": forecast["std"],
        "forecast_range": forecast["range"],
        "forecast_active_raw": forecast["active_raw"],
        "forecast_active_ratio_raw": forecast["active_ratio_raw"],
        "forecast_guard_flags": "|".join(guard["flags"]),
        "forecast_guard_penalty": guard["penalty"],
        "forecast_guard_bonus": guard["bonus"],
    }


def _load_candidate(path, score_column, forecast_guard, forecast_flat_eps, forecast_high_ratio):
    try:
        meta = _load_json(path)
    except Exception:
        return None
    if not meta.get("validation_combined_csv") or not os.path.exists(meta.get("validation_combined_csv")):
        return None
    if not meta.get("forecast_csv") or not os.path.exists(meta.get("forecast_csv")):
        return None
    info = _candidate_score(
        meta, score_column, forecast_guard, forecast_flat_eps, forecast_high_ratio,
    )
    info.update({
        "json_path": path,
        "label": _artifact_label(meta),
        "bank": meta.get("bank", ""),
        "readout": meta.get("readout", ""),
        "seed": meta.get("seed", ""),
    })
    return {"path": path, "meta": meta, "info": info}


def _load_scan_candidates(scan_dir, index_csv, score_column, top_candidates,
                          forecast_guard, forecast_flat_eps, forecast_high_ratio):
    candidates = []
    for path in _candidate_json_paths(scan_dir=scan_dir, index_csv=index_csv):
        item = _load_candidate(
            path, score_column, forecast_guard, forecast_flat_eps, forecast_high_ratio,
        )
        if item is not None:
            candidates.append(item)
    candidates.sort(key=lambda c: c["info"]["candidate_score"], reverse=True)
    if top_candidates and top_candidates > 0:
        candidates = candidates[:top_candidates]
    return candidates


def _pair_kind_bonus(a, b):
    ba, bb = str(a.get("bank", "")), str(b.get("bank", ""))
    if ba == bb and str(a.get("readout", "")) == str(b.get("readout", "")):
        return -0.10
    if "__hybrid__" in (ba, bb) and ba != bb:
        return 0.05
    if "__lcs__" in (ba, bb) and ba != bb:
        return 0.03
    return 0.0


def _simulate_pair(meta_a, meta_b, *, logic, normalize, score_column,
                   alpha, threshold, calibrate_mode, calibrate_metric, min_recall,
                   actual_threshold, forecast_guard, forecast_flat_eps, forecast_high_ratio):
    val_a = meta_a.get("validation_combined_csv")
    val_b = meta_b.get("validation_combined_csv")
    rows_val_a = _read_rows(val_a, has_segment=True)
    rows_val_b = _read_rows(val_b, has_segment=True)
    aligned_val = _align_rows(rows_val_a, rows_val_b, has_segment=True)
    if not aligned_val:
        return None
    raw_thr_a = _artifact_threshold(meta_a)
    raw_thr_b = _artifact_threshold(meta_b)
    if actual_threshold is None:
        actual_threshold = min(raw_thr_a, raw_thr_b)
    norm_a = _fit_normalizer([_score_value(a, score_column) for a, _ in aligned_val], normalize)
    norm_b = _fit_normalizer([_score_value(b, score_column) for _, b in aligned_val], normalize)
    val_scores_a = [
        _apply_normalizer(_score_value(a, score_column), norm_a,
                          raw_threshold=raw_thr_a, normalized_threshold=threshold)
        for a, _ in aligned_val
    ]
    val_scores_b = [
        _apply_normalizer(_score_value(b, score_column), norm_b,
                          raw_threshold=raw_thr_b, normalized_threshold=threshold)
        for _, b in aligned_val
    ]
    val_actual = []
    for a, b in aligned_val:
        actual_raw = a["_actual"] if math.isfinite(a["_actual"]) else b["_actual"]
        val_actual.append(1.0 if math.isfinite(actual_raw) and actual_raw >= actual_threshold else 0.0)
    calibration = _calibrate_thresholds(
        val_actual, val_scores_a, val_scores_b,
        logic=logic, alpha=alpha, threshold=threshold,
        mode=calibrate_mode, metric_name=calibrate_metric,
        min_recall=max(0.0, min(1.0, min_recall)),
    )
    threshold_eff = float(calibration.get("threshold", threshold))
    threshold_a = float(calibration.get("threshold_a", threshold_eff))
    threshold_b = float(calibration.get("threshold_b", threshold_eff))
    pred = [
        _combine(sa, sb, logic, alpha, threshold_eff,
                 threshold_a=threshold_a, threshold_b=threshold_b)
        for sa, sb in zip(val_scores_a, val_scores_b)
    ]
    metrics = _event_metrics(val_actual, pred)
    forecast_eval = {
        "rows": 0,
        "active_ratio": 0.0,
        "range": 0.0,
        "guard": {"mode": forecast_guard, "penalty": 0.0, "bonus": 0.0, "flags": []},
    }
    fc_a = meta_a.get("forecast_csv")
    fc_b = meta_b.get("forecast_csv")
    if fc_a and fc_b and os.path.exists(fc_a) and os.path.exists(fc_b):
        rows_fc_a = _read_rows(fc_a, has_segment=False)
        rows_fc_b = _read_rows(fc_b, has_segment=False)
        aligned_fc = _align_rows(rows_fc_a, rows_fc_b, has_segment=False)
        pred_fc = []
        for a, b in aligned_fc:
            raw_a = _score_value(a, score_column)
            raw_b = _score_value(b, score_column)
            score_a = _apply_normalizer(
                raw_a, norm_a, raw_threshold=raw_thr_a,
                normalized_threshold=threshold_eff,
            )
            score_b = _apply_normalizer(
                raw_b, norm_b, raw_threshold=raw_thr_b,
                normalized_threshold=threshold_eff,
            )
            pred_fc.append(_combine(
                score_a, score_b, logic, alpha, threshold_eff,
                threshold_a=threshold_a, threshold_b=threshold_b,
            ))
        if pred_fc:
            frange = max(pred_fc) - min(pred_fc)
            active_ratio = sum(1 for v in pred_fc if v >= 0.5) / len(pred_fc)
            stats = {
                "rows": len(pred_fc),
                "range": frange,
                "active_ratio_raw": active_ratio,
                "active_raw": sum(1 for v in pred_fc if v >= 0.5),
            }
            forecast_eval = {
                "rows": len(pred_fc),
                "active_ratio": active_ratio,
                "range": frange,
                "guard": _forecast_guard_from_stats(
                    stats, mode=forecast_guard,
                    flat_eps=forecast_flat_eps, high_ratio=forecast_high_ratio,
                ),
            }
    disagreement = sum(
        1 for sa, sb in zip(val_scores_a, val_scores_b)
        if (sa >= threshold_a) != (sb >= threshold_b)
    ) / max(len(val_scores_a), 1)
    return {
        "metrics": metrics,
        "calibration": calibration,
        "threshold": threshold_eff,
        "threshold_a": threshold_a,
        "threshold_b": threshold_b,
        "normalizer_a": norm_a,
        "normalizer_b": norm_b,
        "validation_rows": len(aligned_val),
        "disagreement": disagreement,
        "forecast_eval": forecast_eval,
    }


def _propose_pairs(candidates, *, logic, normalize, score_column, alpha, threshold,
                   calibrate_mode, calibrate_metric, min_recall, actual_threshold,
                   top_pairs, forecast_guard, forecast_flat_eps, forecast_high_ratio):
    proposals = []
    for ca, cb in itertools.combinations(candidates, 2):
        sim = _simulate_pair(
            ca["meta"], cb["meta"], logic=logic, normalize=normalize,
            score_column=score_column, alpha=alpha, threshold=threshold,
            calibrate_mode=calibrate_mode, calibrate_metric=calibrate_metric,
            min_recall=min_recall, actual_threshold=actual_threshold,
            forecast_guard=forecast_guard, forecast_flat_eps=forecast_flat_eps,
            forecast_high_ratio=forecast_high_ratio,
        )
        if sim is None:
            continue
        ia, ib = ca["info"], cb["info"]
        metrics = sim["metrics"]
        avg_shape = 0.5 * (ia["shape_overall"] + ib["shape_overall"])
        min_depression = min(ia["depression_score"], ib["depression_score"])
        pair_guard = sim["forecast_eval"]["guard"]
        score = (
            0.36 * metrics["f1"]
            + 0.22 * metrics["bal_acc"]
            + 0.14 * metrics["recall"]
            + 0.10 * metrics["precision"]
            + 0.10 * avg_shape
            + 0.05 * min_depression
            + pair_guard["bonus"]
            - pair_guard["penalty"]
            + _pair_kind_bonus(ia, ib)
        )
        proposals.append({
            "pair_score": score,
            "a": ca,
            "b": cb,
            "simulation": sim,
            "avg_shape": avg_shape,
            "min_depression": min_depression,
        })
    proposals.sort(key=lambda p: p["pair_score"], reverse=True)
    return proposals[:max(1, int(top_pairs or 20))]


def _write_proposals(path, proposals):
    fields = [
        "rank", "pair_score", "a_label", "b_label", "a_json", "b_json",
        "f1", "recall", "precision", "bal_acc", "tp", "fp", "tn", "fn",
        "threshold_a", "threshold_b", "avg_shape", "min_depression",
        "forecast_guard_flags", "forecast_guard_penalty", "forecast_active_ratio",
        "a_overall", "a_shape", "a_peak", "a_depression", "a_forecast_range",
        "a_forecast_guard", "b_overall", "b_shape", "b_peak", "b_depression",
        "b_forecast_range", "b_forecast_guard",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for i, prop in enumerate(proposals, 1):
            ia, ib = prop["a"]["info"], prop["b"]["info"]
            m = prop["simulation"]["metrics"]
            writer.writerow({
                "rank": i,
                "pair_score": prop["pair_score"],
                "a_label": ia["label"],
                "b_label": ib["label"],
                "a_json": ia["json_path"],
                "b_json": ib["json_path"],
                "f1": m["f1"],
                "recall": m["recall"],
                "precision": m["precision"],
                "bal_acc": m["bal_acc"],
                "tp": m["tp"],
                "fp": m["fp"],
                "tn": m["tn"],
                "fn": m["fn"],
                "threshold_a": prop["simulation"]["threshold_a"],
                "threshold_b": prop["simulation"]["threshold_b"],
                "avg_shape": prop["avg_shape"],
                "min_depression": prop["min_depression"],
                "forecast_guard_flags": "|".join(prop["simulation"]["forecast_eval"]["guard"]["flags"]),
                "forecast_guard_penalty": prop["simulation"]["forecast_eval"]["guard"]["penalty"],
                "forecast_active_ratio": prop["simulation"]["forecast_eval"]["active_ratio"],
                "a_overall": ia["overall"],
                "a_shape": ia["shape_overall"],
                "a_peak": ia["peak_score"],
                "a_depression": ia["depression_score"],
                "a_forecast_range": ia["forecast_range"],
                "a_forecast_guard": ia["forecast_guard_flags"],
                "b_overall": ib["overall"],
                "b_shape": ib["shape_overall"],
                "b_peak": ib["peak_score"],
                "b_depression": ib["depression_score"],
                "b_forecast_range": ib["forecast_range"],
                "b_forecast_guard": ib["forecast_guard_flags"],
            })


def _load_rules(meta):
    path = meta.get("best_rules_json")
    if not path:
        return []
    if not os.path.exists(path):
        return []
    try:
        rules = _load_json(path)
    except Exception:
        return []
    if isinstance(rules, list):
        return rules
    if isinstance(rules, dict):
        for key in ("rules", "best_rules"):
            if isinstance(rules.get(key), list):
                return rules[key]
    return []


def _positive_rules(rules, max_rules):
    pos = [r for r in rules if int(r.get("action", 0) or 0) == 1]
    return pos[:max_rules]


def _derive_rules(meta_a, meta_b, rules_a, rules_b, *, logic, max_rules):
    pos_a = _positive_rules(rules_a, max_rules)
    pos_b = _positive_rules(rules_b, max_rules)
    derived = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "logic": logic,
        "note": (
            "Regole derivate senza retraining: i JSON export contengono le best_rules, "
            "ma non il firing per singola regola. In AND le regole positive LCS sono "
            "quindi annotate come gated/congiunte dal secondo artifact."
        ),
        "source_a": _artifact_label(meta_a),
        "source_b": _artifact_label(meta_b),
        "source_a_positive_rules": len(pos_a),
        "source_b_positive_rules": len(pos_b),
        "rules": [],
    }
    logic_l = logic.lower()
    if logic_l in ("and", "sure"):
        if pos_a and pos_b:
            for ra in pos_a:
                for rb in pos_b:
                    derived["rules"].append({
                        "type": "and_conjunction",
                        "source_a_rank": ra.get("rank"),
                        "source_b_rank": rb.get("rank"),
                        "conditions_human": (
                            [f"A: {c}" for c in ra.get("active_conditions_human", ra.get("conditions_human", []))]
                            + [f"B: {c}" for c in rb.get("active_conditions_human", rb.get("conditions_human", []))]
                        ),
                        "source_a_rule": ra,
                        "source_b_rule": rb,
                    })
        elif pos_a:
            for ra in pos_a:
                derived["rules"].append({
                    "type": "lcs_rule_gated_by_artifact_b",
                    "gate": _artifact_label(meta_b),
                    "source_rank": ra.get("rank"),
                    "conditions_human": ra.get("active_conditions_human", ra.get("conditions_human", [])),
                    "source_rule": ra,
                })
        elif pos_b:
            for rb in pos_b:
                derived["rules"].append({
                    "type": "lcs_rule_gated_by_artifact_a",
                    "gate": _artifact_label(meta_a),
                    "source_rank": rb.get("rank"),
                    "conditions_human": rb.get("active_conditions_human", rb.get("conditions_human", [])),
                    "source_rule": rb,
                })
    else:
        for side, meta, rules in (("a", meta_a, pos_a), ("b", meta_b, pos_b)):
            for rule in rules:
                derived["rules"].append({
                    "type": f"{logic_l}_source_rule",
                    "source": side,
                    "artifact": _artifact_label(meta),
                    "source_rank": rule.get("rank"),
                    "conditions_human": rule.get("active_conditions_human", rule.get("conditions_human", [])),
                    "source_rule": rule,
                })
    return derived


def _build_output_rows(aligned, *, score_col, norm_a, norm_b, raw_thr_a, raw_thr_b,
                       actual_threshold, logic, alpha, threshold, threshold_a,
                       threshold_b, has_segment):
    out = []
    for a, b in aligned:
        raw_a = _score_value(a, score_col)
        raw_b = _score_value(b, score_col)
        score_a = _apply_normalizer(raw_a, norm_a, raw_threshold=raw_thr_a, normalized_threshold=threshold)
        score_b = _apply_normalizer(raw_b, norm_b, raw_threshold=raw_thr_b, normalized_threshold=threshold)
        pred = _combine(
            score_a, score_b, logic, alpha, threshold,
            threshold_a=threshold_a, threshold_b=threshold_b,
        )
        actual_raw = a["_actual"] if math.isfinite(a["_actual"]) else b["_actual"]
        actual_event = 1.0 if math.isfinite(actual_raw) and actual_raw >= actual_threshold else 0.0
        row = {
            "segment": a.get("_segment", ""),
            "date": a.get("date") or a.get("context") or b.get("date") or b.get("context") or "",
            "row_index": a["_row_index"],
            "actual": actual_raw if math.isfinite(actual_raw) else "",
            "actual_event": actual_event,
            "a_raw": raw_a,
            "b_raw": raw_b,
            "a_score": score_a,
            "b_score": score_b,
            "predicted": pred,
            "error": pred - actual_event,
        }
        if not has_segment:
            row.pop("segment", None)
        out.append(row)
    return out


def _write_csv(path, rows, *, has_segment):
    fields = []
    if has_segment:
        fields.append("segment")
    fields.extend(["date", "row_index", "actual", "actual_event",
                   "a_raw", "b_raw", "a_score", "b_score", "predicted", "error"])
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def _panel_segments(rows, *, has_segment):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.get("segment", "") if has_segment else "forecast"].append(row)
    segments = []
    for label, items in grouped.items():
        segments.append({
            "label": label,
            "y_true": [r["actual_event"] for r in items],
            "y_pred": [r["predicted"] for r in items],
            "context": [r.get("date") or r.get("context") or "" for r in items],
        })
    return segments


def _source_panel_from_csv(path, *, title, subtitle, has_segment, score_column):
    rows = _read_rows(path, has_segment=has_segment)
    grouped = defaultdict(list)
    for row in rows:
        label = row.get("_segment", "") if has_segment else "forecast"
        grouped[label].append(row)
    segments = []
    for label, items in grouped.items():
        segments.append({
            "label": label,
            "y_true": [
                r["_actual"] if math.isfinite(r["_actual"]) else 0.0
                for r in items
            ],
            "y_pred": [_score_value(r, score_column) for r in items],
            "context": [r.get("date") or r.get("context") or "" for r in items],
        })
    return {"title": title, "subtitle": subtitle, "segments": segments}


def _font(size, bold=False, italic=False):
    if bold and italic:
        names = [
            "DejaVuSans-BoldOblique.ttf",
            "DejaVuSans-BoldItalic.ttf",
            "NotoSans-BoldItalic.ttf",
            "LiberationSans-BoldItalic.ttf",
            "DejaVuSansMono-BoldOblique.ttf",
            "DejaVuSans-Bold.ttf",
        ]
    elif bold:
        names = ["DejaVuSans-Bold.ttf", "NotoSans-Bold.ttf", "LiberationSans-Bold.ttf"]
    elif italic:
        names = [
            "DejaVuSans-Oblique.ttf",
            "DejaVuSans-Italic.ttf",
            "NotoSans-Italic.ttf",
            "LiberationSans-Italic.ttf",
            "DejaVuSans.ttf",
        ]
    else:
        names = ["DejaVuSans.ttf", "NotoSans-Regular.ttf", "LiberationSans-Regular.ttf"]
    candidates = []
    for name in names:
        candidates.extend([
            f"/usr/share/fonts/truetype/dejavu/{name}",
            f"/usr/share/fonts/dejavu/{name}",
            f"/usr/share/fonts/truetype/noto/{name}",
            f"/usr/share/fonts/truetype/liberation/{name}",
        ])
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _wrap_text(draw, text, font, width):
    words = str(text).split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_box(draw, box, title, lines, *, fill, outline, title_font, body_font):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=10, fill=fill, outline=outline, width=2)
    draw.text((x0 + 16, y0 + 12), title, fill=(25, 30, 38), font=title_font)
    y = y0 + 46
    max_w = x1 - x0 - 32
    for line in lines:
        for wrapped in _wrap_text(draw, line, body_font, max_w):
            if y + 18 > y1 - 10:
                return
            draw.text((x0 + 16, y), wrapped, fill=(55, 62, 74), font=body_font)
            y += 20


def _arrow(draw, start, end, fill=(60, 70, 85)):
    draw.line((start, end), fill=fill, width=3)
    ex, ey = end
    sx, sy = start
    if ex >= sx:
        pts = [(ex, ey), (ex - 12, ey - 7), (ex - 12, ey + 7)]
    else:
        pts = [(ex, ey), (ex + 12, ey - 7), (ex + 12, ey + 7)]
    draw.polygon(pts, fill=fill)


def _orthogonal_arrow(draw, points, fill=(60, 70, 85)):
    for a, b in zip(points, points[1:]):
        draw.line((a, b), fill=fill, width=3)
    if len(points) >= 2:
        sx, sy = points[-2]
        ex, ey = points[-1]
        if abs(ey - sy) >= abs(ex - sx):
            if ey >= sy:
                pts = [(ex, ey), (ex - 7, ey - 12), (ex + 7, ey - 12)]
            else:
                pts = [(ex, ey), (ex - 7, ey + 12), (ex + 7, ey + 12)]
        elif ex >= sx:
            pts = [(ex, ey), (ex - 12, ey - 7), (ex - 12, ey + 7)]
        else:
            pts = [(ex, ey), (ex + 12, ey - 7), (ex + 12, ey + 7)]
        draw.polygon(pts, fill=fill)


def _fmt_metric(value):
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_pct(value):
    try:
        return f"{100.0 * float(value):.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_delta(value, baseline):
    try:
        delta = float(value) - float(baseline)
    except (TypeError, ValueError):
        return ""
    sign = "+" if delta >= 0 else ""
    return f" ({sign}{delta:.3f})"


def _fmt_delta_pct(value, baseline):
    try:
        delta = 100.0 * (float(value) - float(baseline))
    except (TypeError, ValueError):
        return ""
    sign = "+" if delta >= 0 else ""
    return f"({sign}{delta:.1f}%)"


def _metric_lines(metrics, prefix=""):
    return [
        f"{prefix}F1: {_fmt_metric(metrics.get('f1'))}",
        f"{prefix}Recall: {_fmt_metric(metrics.get('recall'))}",
        f"{prefix}Precision: {_fmt_metric(metrics.get('precision'))}",
        f"{prefix}BalAcc: {_fmt_metric(metrics.get('bal_acc'))}",
    ]


def _premerge_metrics(aligned, *, side, meta, score_column, actual_threshold):
    pred_threshold = _artifact_prediction_threshold(meta)
    actual = []
    pred = []
    for a, b in aligned:
        row = a if side == "a" else b
        actual_raw = a["_actual"] if math.isfinite(a["_actual"]) else b["_actual"]
        actual.append(1.0 if math.isfinite(actual_raw) and actual_raw >= actual_threshold else 0.0)
        pred.append(1.0 if _score_value(row, score_column) >= pred_threshold else 0.0)
    metrics = _event_metrics(actual, pred)
    metrics["prediction_threshold"] = pred_threshold
    return metrics


def _artifact_original_metrics(meta):
    trial = meta.get("trial_metrics", {}) or {}
    return {
        "overall": _to_float(trial.get("overall"), 0.0),
        "f1": _to_float(trial.get("event_f1"), 0.0),
        "recall": _to_float(trial.get("event_recall"), 0.0),
        "precision": _to_float(trial.get("event_precision"), 0.0),
        "bal_acc": _to_float(trial.get("event_bal_acc"), 0.0),
    }


def _compact_metric_line(label, metrics, include_overall=False):
    parts = []
    if include_overall:
        parts.append(f"Ov={_fmt_metric(metrics.get('overall'))}")
    parts.extend([
        f"F1={_fmt_metric(metrics.get('f1'))}",
        f"R={_fmt_metric(metrics.get('recall'))}",
        f"P={_fmt_metric(metrics.get('precision'))}",
        f"Bal={_fmt_metric(metrics.get('bal_acc'))}",
    ])
    return f"{label}: " + " ".join(parts)


def _metric_color(value, other):
    try:
        v, o = float(value), float(other)
    except (TypeError, ValueError):
        return (55, 62, 74)
    if abs(v - o) < 1e-12:
        return (28, 130, 60)
    return (28, 130, 60) if v > o else (190, 45, 45)


def _draw_candidate_box(draw, box, title, meta, metrics, other_metrics, *,
                        fill, outline, title_font, body_font, metric_font):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=10, fill=fill, outline=outline, width=2)
    draw.text((x0 + 14, y0 + 10), title, fill=(25, 30, 38), font=title_font)
    y = y0 + 42
    detail_lines = _artifact_flow_lines(meta)
    max_detail = 7
    printed = 0
    for line in detail_lines:
        if printed >= max_detail:
            break
        for part in _wrap_text(draw, str(line), body_font, x1 - x0 - 28):
            if printed >= max_detail:
                break
            draw.text((x0 + 14, y), part, fill=(55, 62, 74), font=body_font)
            y += 18
            printed += 1
    y += 4
    metric_names = [
        ("F1", "f1"),
        ("Recall", "recall"),
        ("Precision", "precision"),
        ("BalAcc", "bal_acc"),
    ]
    for label, key in metric_names:
        color = _metric_color(metrics.get(key), other_metrics.get(key))
        draw.text(
            (x0 + 14, y),
            f"Pre-merge {label}: {_fmt_pct(metrics.get(key))}",
            fill=color, font=metric_font,
        )
        y += 19
    draw.text(
        (x0 + 14, y),
        f"Pre-merge threshold: {_fmt_metric(metrics.get('prediction_threshold'))}",
        fill=(55, 62, 74), font=body_font,
    )


def _premerge_metric_lines(metrics):
    return [
        f"Pre-merge validation F1: {_fmt_metric(metrics.get('f1'))}",
        f"Pre-merge Recall: {_fmt_metric(metrics.get('recall'))}",
        f"Pre-merge Precision: {_fmt_metric(metrics.get('precision'))}",
        f"Pre-merge BalAcc: {_fmt_metric(metrics.get('bal_acc'))}",
        f"Pre-merge threshold: {_fmt_metric(metrics.get('prediction_threshold'))}",
    ]


def _best_source_metrics(summary):
    sources = summary.get("source_validation_metrics", {}) or {}
    a = sources.get("a", {}) or {}
    b = sources.get("b", {}) or {}
    return {
        key: max(float(a.get(key, 0.0) or 0.0), float(b.get(key, 0.0) or 0.0))
        for key in ("f1", "recall", "precision", "bal_acc")
    }


def _automatic_judgment(summary):
    result = summary.get("validation_metrics", {}) or {}
    best = _best_source_metrics(summary)
    improved = []
    worsened = []
    for key in ("f1", "recall", "precision", "bal_acc"):
        delta = float(result.get(key, 0.0) or 0.0) - float(best.get(key, 0.0) or 0.0)
        if delta > 1e-9:
            improved.append(key)
        elif delta < -1e-9:
            worsened.append(key)
    if not worsened and improved:
        return "Fusion improves at least one metric and does not worsen the others."
    if "f1" in improved or "bal_acc" in improved:
        return "Fusion improves the main selection metric, with trade-offs."
    if not improved and not worsened:
        return "Fusion matches the best pre-merge candidate."
    return "Fusion is selective, but not a strict metric improvement."


def _judgment_color(summary):
    result = summary.get("validation_metrics", {}) or {}
    best = _best_source_metrics(summary)
    deltas = [
        float(result.get(key, 0.0) or 0.0) - float(best.get(key, 0.0) or 0.0)
        for key in ("f1", "recall", "precision", "bal_acc")
    ]
    if any(delta > 1e-9 for delta in deltas):
        return (28, 130, 60)
    if all(delta < -1e-9 for delta in deltas):
        return (190, 45, 45)
    return (55, 62, 74)


def _draw_metric_with_delta(draw, x, y, label, value, baseline, font, bold_font):
    text = f"{label}={_fmt_pct(value)}"
    draw.text((x, y), text, fill=(55, 62, 74), font=font)
    bbox = draw.textbbox((x, y), text, font=font)
    try:
        delta = float(value) - float(baseline)
    except (TypeError, ValueError):
        return bbox[2] + 8
    color = (28, 130, 60) if delta >= 0 else (190, 45, 45)
    delta_text = _fmt_delta_pct(value, baseline)
    draw.text((bbox[2] + 8, y), delta_text, fill=color, font=bold_font)
    delta_box = draw.textbbox((bbox[2] + 8, y), delta_text, font=bold_font)
    return delta_box[2] + 14


def _draw_result_box(draw, box, summary, *, title_font, body_font, bold_font,
                     verdict_font, small_font):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=10, fill=(250, 250, 252), outline=(135, 142, 155), width=2)
    sep_x = x0 + int((x1 - x0) * 0.48)
    dash_y = y0 + 14
    while dash_y < y1 - 14:
        draw.line((sep_x, dash_y, sep_x, min(dash_y + 9, y1 - 14)), fill=(185, 190, 200), width=1)
        dash_y += 16
    section_font = _font(20, bold=True, italic=True)
    draw.text((x0 + 16, y0 + 12), "Result", fill=(25, 30, 38), font=section_font)
    m = summary.get("validation_metrics", {}) or {}
    y = y0 + 42
    draw.text((x0 + 16, y), "Automatic verdict", fill=(25, 30, 38), font=section_font)
    y += 28
    verdict = _automatic_judgment(summary)
    for line in _wrap_text(draw, verdict, verdict_font, sep_x - x0 - 32):
        draw.text((x0 + 16, y), line, fill=_judgment_color(summary), font=verdict_font)
        y += 20
    y += 4
    if summary.get("bar_chart_mode") == "dual_source":
        # Confronto vs sorgenti originali vere A e B
        src_a = summary.get("bar_chart_source_a_metrics") or {}
        src_b = summary.get("bar_chart_source_b_metrics") or {}
        lbl_a = (summary.get("bar_chart_source_a_label") or "Source A")[:28]
        lbl_b = (summary.get("bar_chart_source_b_label") or "Source B")[:28]
        draw.text((x0 + 16, y), f"Δ vs original A ({lbl_a}):", fill=(55, 62, 74), font=body_font)
        y += 20
        x = x0 + 16
        x = _draw_metric_with_delta(draw, x, y, "F1", m.get("f1"), src_a.get("f1"), body_font, bold_font)
        _draw_metric_with_delta(draw, x, y, "Recall", m.get("recall"), src_a.get("recall"), body_font, bold_font)
        y += 20
        x = x0 + 16
        x = _draw_metric_with_delta(draw, x, y, "Prec", m.get("precision"), src_a.get("precision"), body_font, bold_font)
        _draw_metric_with_delta(draw, x, y, "BalAcc", m.get("bal_acc"), src_a.get("bal_acc"), body_font, bold_font)
        y += 22
        draw.text((x0 + 16, y), f"Δ vs original B ({lbl_b}):", fill=(55, 62, 74), font=body_font)
        y += 20
        x = x0 + 16
        x = _draw_metric_with_delta(draw, x, y, "F1", m.get("f1"), src_b.get("f1"), body_font, bold_font)
        _draw_metric_with_delta(draw, x, y, "Recall", m.get("recall"), src_b.get("recall"), body_font, bold_font)
        y += 20
        x = x0 + 16
        x = _draw_metric_with_delta(draw, x, y, "Prec", m.get("precision"), src_b.get("precision"), body_font, bold_font)
        _draw_metric_with_delta(draw, x, y, "BalAcc", m.get("bal_acc"), src_b.get("bal_acc"), body_font, bold_font)
        y += 22
    else:
        best = summary.get("bar_chart_baseline_metrics") or _best_source_metrics(summary)
        winner = summary.get("bar_chart_winner_metrics")
        if winner:
            draw.text((x0 + 16, y), "Δ vs best winner (shape/peak):",
                      fill=(55, 62, 74), font=body_font)
            y += 20
            x = x0 + 16
            x = _draw_metric_with_delta(draw, x, y, "F1", m.get("f1"), winner.get("f1"), body_font, bold_font)
            _draw_metric_with_delta(draw, x, y, "Recall", m.get("recall"), winner.get("recall"), body_font, bold_font)
            y += 20
            x = x0 + 16
            x = _draw_metric_with_delta(draw, x, y, "Precision", m.get("precision"), winner.get("precision"), body_font, bold_font)
            _draw_metric_with_delta(draw, x, y, "BalAcc", m.get("bal_acc"), winner.get("bal_acc"), body_font, bold_font)
            y += 22
        draw.text(
            (x0 + 16, y),
            summary.get("result_delta_label", "Validation vs best pre-merge candidate:"),
            fill=(55, 62, 74), font=body_font,
        )
        y += 20
        x = x0 + 16
        x = _draw_metric_with_delta(draw, x, y, "F1", m.get("f1"), best.get("f1"), body_font, bold_font)
        _draw_metric_with_delta(draw, x, y, "Recall", m.get("recall"), best.get("recall"), body_font, bold_font)
        y += 20
        x = x0 + 16
        x = _draw_metric_with_delta(draw, x, y, "Precision", m.get("precision"), best.get("precision"), body_font, bold_font)
        _draw_metric_with_delta(draw, x, y, "BalAcc", m.get("bal_acc"), best.get("bal_acc"), body_font, bold_font)
        y += 22
    draw.text(
        (x0 + 16, y),
        f"Confusion: tp={m.get('tp')} fp={m.get('fp')} tn={m.get('tn')} fn={m.get('fn')}",
        fill=(55, 62, 74), font=body_font,
    )
    y += 20
    draw.text(
        (x0 + 16, y),
        summary.get(
            "forecast_note",
            "Forecast is recalculated with the same calibrated thresholds and merge logic.",
        ),
        fill=(55, 62, 74), font=body_font,
    )
    _draw_bar_chart(
        draw, (sep_x + 24, y0 + 14, x1 - 22, y1 - 18),
        summary, font=bold_font, small_font=small_font,
    )


def _draw_dashed_line(draw, start, end, *, fill, width=1, dash=8, gap=5):
    x0, y0 = start
    x1, y1 = end
    if abs(y1 - y0) <= abs(x1 - x0):
        step = dash + gap
        x = x0
        direction = 1 if x1 >= x0 else -1
        while (x - x1) * direction < 0:
            x_next = x + direction * min(dash, abs(x1 - x))
            draw.line((x, y0, x_next, y1), fill=fill, width=width)
            x += direction * step
    else:
        step = dash + gap
        y = y0
        direction = 1 if y1 >= y0 else -1
        while (y - y1) * direction < 0:
            y_next = y + direction * min(dash, abs(y1 - y))
            draw.line((x0, y, x1, y_next), fill=fill, width=width)
            y += direction * step


def _draw_patterned_bar(draw, rect, *, fill, outline, pattern):
    x0, y0, x1, y1 = rect
    draw.rectangle(rect, fill=fill, outline=outline, width=1)
    if y1 - y0 < 4:
        return
    if pattern == "solid":
        return
    if pattern == "diag":
        y = y0 + 3
        while y < y1:
            draw.line((x0 + 2, min(y + 5, y1 - 1), x1 - 2, y), fill=outline, width=1)
            y += 11
    elif pattern == "outline":
        return
    elif pattern == "horizontal":
        y = y0 + 5
        while y < y1:
            draw.line((x0 + 1, y, x1 - 1, y), fill=outline, width=1)
            y += 7
    elif pattern == "cross":
        y = y0 + 5
        while y < y1:
            draw.line((x0 + 1, y, x1 - 1, y), fill=outline, width=1)
            y += 8
        x = x0 + 4
        while x < x1:
            draw.line((x, y0 + 1, x, y1 - 1), fill=outline, width=1)
            x += 8


def _draw_bar_chart(draw, box, summary, *, font, small_font):
    x0, y0, x1, y1 = box
    if summary.get("bar_chart_mode") == "cumulative":
        current = summary.get("bar_chart_current_metrics") or summary.get("validation_metrics", {}) or {}
        baseline = summary.get("bar_chart_baseline_metrics") or _best_source_metrics(summary)
        metrics = [("F1", "f1"), ("Recall", "recall"), ("Precision", "precision"), ("BalAcc", "bal_acc")]
        title = summary.get("bar_chart_title", "Cumulative gain vs best original source")
        draw.text((x0, y0), title, fill=(25, 30, 38), font=font)
        chart_left = x0 + 34
        chart_right = x1 - 8
        chart_top = y0 + 44
        value_top = chart_top + 18
        chart_bottom = y1 - 58
        for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
            ty = chart_bottom - (chart_bottom - value_top) * tick
            fill = (178, 184, 194) if tick in (0.0, 1.0) else (225, 229, 235)
            draw.line((chart_left, ty, chart_right, ty), fill=fill, width=1)
            label = f"{int(tick * 100)}%"
            tb = draw.textbbox((0, 0), label, font=small_font)
            draw.text((chart_left - (tb[2] - tb[0]) - 6, ty - 7), label, fill=(95, 102, 114), font=small_font)
        draw.line((chart_left, value_top, chart_left, chart_bottom), fill=(180, 186, 196), width=1)
        group_w = (chart_right - chart_left) / len(metrics)
        bar_w = min(22, max(12, int(group_w / 5)))
        winner_bc = summary.get("bar_chart_winner_metrics")
        styles = {
            "baseline": {
                "fill": (210, 217, 228),
                "outline": (88, 98, 118),
                "pattern": "horizontal",
                "text_fill": (78, 88, 108),
            },
            "winner": {
                "fill": (252, 210, 150),
                "outline": (160, 100, 30),
                "pattern": "cross",
                "text_fill": (120, 70, 20),
            },
            "current": {
                "fill": (88, 160, 98),
                "outline": (33, 80, 45),
                "pattern": "solid",
                "text_fill": (20, 60, 32),
            },
        }
        bar_w = min(18, max(10, int(group_w / (6 if winner_bc else 5))))
        for i, (label, key) in enumerate(metrics):
            gx = chart_left + i * group_w + group_w * 0.5
            vals = [("baseline", float(baseline.get(key, 0.0) or 0.0))]
            if winner_bc:
                vals.append(("winner", float(winner_bc.get(key, 0.0) or 0.0)))
            vals.append(("current", float(current.get(key, 0.0) or 0.0)))
            n = len(vals)
            for j, (name, value) in enumerate(vals):
                offset = (j - (n - 1) / 2.0) * (bar_w + 6)
                bx0 = gx + offset - bar_w / 2
                bh = max(1, (chart_bottom - value_top) * max(0.0, min(1.0, value)))
                by0 = chart_bottom - bh
                style = styles[name]
                _draw_patterned_bar(
                    draw, (bx0, by0, bx0 + bar_w, chart_bottom),
                    fill=style["fill"], outline=style["outline"], pattern=style["pattern"],
                )
                pct = f"{int(round(value * 100))}"
                pb = draw.textbbox((0, 0), pct, font=small_font)
                draw.text(
                    (bx0 + (bar_w - (pb[2] - pb[0])) / 2, max(chart_top - 2, by0 - 18)),
                    pct, fill=style["text_fill"], font=small_font,
                )
            tb = draw.textbbox((0, 0), label, font=small_font)
            draw.text((gx - (tb[2] - tb[0]) / 2, chart_bottom + 8), label, fill=(75, 82, 94), font=small_font)
        legend_items = [("baseline", summary.get("bar_chart_baseline_label", "Best original"))]
        if winner_bc:
            legend_items.append(("winner", summary.get("bar_chart_winner_label", "Best winner")))
        legend_items.append(("current", summary.get("bar_chart_current_label", "Current")))
        lx, ly = chart_left, y1 - 22
        for name, label in legend_items:
            style = styles[name]
            _draw_patterned_bar(
                draw, (lx, ly + 4, lx + 12, ly + 16),
                fill=style["fill"], outline=style["outline"], pattern=style["pattern"],
            )
            draw.text((lx + 16, ly), label, fill=(75, 82, 94), font=small_font)
            tw = draw.textbbox((0, 0), label, font=small_font)
            lx += 20 + (tw[2] - tw[0]) + 8
        return
    if summary.get("bar_chart_mode") == "dual_source":
        current = summary.get("bar_chart_current_metrics") or summary.get("validation_metrics", {}) or {}
        src_a = summary.get("bar_chart_source_a_metrics") or {}
        src_b = summary.get("bar_chart_source_b_metrics") or {}
        metrics = [("F1", "f1"), ("Recall", "recall"), ("Precision", "precision"), ("BalAcc", "bal_acc")]
        title = summary.get("bar_chart_title", "Smart merge vs original sources")
        draw.text((x0, y0), title, fill=(25, 30, 38), font=font)
        chart_left = x0 + 34
        chart_right = x1 - 8
        chart_top = y0 + 44
        value_top = chart_top + 18
        chart_bottom = y1 - 58
        for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
            ty = chart_bottom - (chart_bottom - value_top) * tick
            fill = (178, 184, 194) if tick in (0.0, 1.0) else (225, 229, 235)
            draw.line((chart_left, ty, chart_right, ty), fill=fill, width=1)
            lbl = f"{int(tick * 100)}%"
            tb = draw.textbbox((0, 0), lbl, font=small_font)
            draw.text((chart_left - (tb[2] - tb[0]) - 6, ty - 7), lbl, fill=(95, 102, 114), font=small_font)
        draw.line((chart_left, value_top, chart_left, chart_bottom), fill=(180, 186, 196), width=1)
        group_w = (chart_right - chart_left) / len(metrics)
        bar_w = min(18, max(10, int(group_w / 6)))
        styles_ds = {
            "source_a": {
                "fill": (210, 217, 228), "outline": (88, 98, 118),
                "pattern": "horizontal", "text_fill": (78, 88, 108),
            },
            "source_b": {
                "fill": (178, 205, 240), "outline": (35, 75, 125),
                "pattern": "diag", "text_fill": (35, 75, 125),
            },
            "current": {
                "fill": (88, 160, 98), "outline": (33, 80, 45),
                "pattern": "solid", "text_fill": (20, 60, 32),
            },
        }
        for i, (label, key) in enumerate(metrics):
            gx = chart_left + i * group_w + group_w * 0.5
            vals = [
                ("source_a", float(src_a.get(key, 0.0) or 0.0)),
                ("source_b", float(src_b.get(key, 0.0) or 0.0)),
                ("current", float(current.get(key, 0.0) or 0.0)),
            ]
            n = len(vals)
            for j, (name, value) in enumerate(vals):
                offset = (j - (n - 1) / 2.0) * (bar_w + 6)
                bx0 = gx + offset - bar_w / 2
                bh = max(1, (chart_bottom - value_top) * max(0.0, min(1.0, value)))
                by0 = chart_bottom - bh
                style = styles_ds[name]
                _draw_patterned_bar(
                    draw, (bx0, by0, bx0 + bar_w, chart_bottom),
                    fill=style["fill"], outline=style["outline"], pattern=style["pattern"],
                )
                pct = f"{int(round(value * 100))}"
                pb = draw.textbbox((0, 0), pct, font=small_font)
                draw.text(
                    (bx0 + (bar_w - (pb[2] - pb[0])) / 2, max(chart_top - 2, by0 - 18)),
                    pct, fill=style["text_fill"], font=small_font,
                )
            tb = draw.textbbox((0, 0), label, font=small_font)
            draw.text((gx - (tb[2] - tb[0]) / 2, chart_bottom + 8), label, fill=(75, 82, 94), font=small_font)
        legend_items_ds = [
            ("source_a", (summary.get("bar_chart_source_a_label") or "Source A")[:20]),
            ("source_b", (summary.get("bar_chart_source_b_label") or "Source B")[:20]),
            ("current", summary.get("bar_chart_current_label", "Smart merge")),
        ]
        lx, ly = chart_left, y1 - 22
        for name, label in legend_items_ds:
            style = styles_ds[name]
            _draw_patterned_bar(
                draw, (lx, ly + 4, lx + 12, ly + 16),
                fill=style["fill"], outline=style["outline"], pattern=style["pattern"],
            )
            draw.text((lx + 16, ly), label, fill=(75, 82, 94), font=small_font)
            tw = draw.textbbox((0, 0), label, font=small_font)
            lx += 20 + (tw[2] - tw[0]) + 8
        return
    result = summary.get("validation_metrics", {}) or {}
    sources = summary.get("source_validation_metrics", {}) or {}
    a = sources.get("a", {}) or {}
    b = sources.get("b", {}) or {}
    metrics = [("F1", "f1"), ("Recall", "recall"), ("Precision", "precision"), ("BalAcc", "bal_acc")]
    draw.text((x0, y0), "Metric comparison", fill=(25, 30, 38), font=font)
    chart_left = x0 + 34
    chart_right = x1 - 8
    chart_top = y0 + 44
    value_top = chart_top + 18
    chart_bottom = y1 - 58
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        ty = chart_bottom - (chart_bottom - value_top) * tick
        fill = (178, 184, 194) if tick in (0.0, 1.0) else (225, 229, 235)
        draw.line((chart_left, ty, chart_right, ty), fill=fill, width=1)
        label = f"{int(tick * 100)}%"
        tb = draw.textbbox((0, 0), label, font=small_font)
        draw.text((chart_left - (tb[2] - tb[0]) - 6, ty - 7), label, fill=(95, 102, 114), font=small_font)
    draw.line((chart_left, value_top, chart_left, chart_bottom), fill=(180, 186, 196), width=1)
    group_w = (chart_right - chart_left) / len(metrics)
    bar_w = min(17, max(10, int(group_w / 6)))
    styles = {
        "fusion": {
            "fill": (88, 160, 98),
            "outline": (33, 80, 45),
            "pattern": "solid",
            "text_fill": (20, 60, 32),
        },
        "a": {
            "fill": (178, 205, 240),
            "outline": (35, 75, 125),
            "pattern": "diag",
            "text_fill": (35, 75, 125),
        },
        "b": {
            "fill": (252, 235, 224),
            "outline": (145, 70, 35),
            "pattern": "outline",
            "text_fill": (145, 70, 35),
        },
    }
    for i, (label, key) in enumerate(metrics):
        gx = chart_left + i * group_w + group_w * 0.5
        fusion_value = float(result.get(key, 0.0) or 0.0)
        ref_y = chart_bottom - (chart_bottom - value_top) * max(0.0, min(1.0, fusion_value))
        _draw_dashed_line(
            draw,
            (gx - group_w * 0.34, ref_y),
            (gx + group_w * 0.34, ref_y),
            fill=(35, 65, 40), width=2, dash=10, gap=4,
        )
        vals = [
            ("fusion", fusion_value),
            ("a", float(a.get(key, 0.0) or 0.0)),
            ("b", float(b.get(key, 0.0) or 0.0)),
        ]
        for j, (name, value) in enumerate(vals):
            bx0 = gx + (j - 1) * (bar_w + 5) - bar_w / 2
            bh = max(1, (chart_bottom - value_top) * max(0.0, min(1.0, value)))
            by0 = chart_bottom - bh
            style = styles[name]
            _draw_patterned_bar(
                draw, (bx0, by0, bx0 + bar_w, chart_bottom),
                fill=style["fill"], outline=style["outline"], pattern=style["pattern"],
            )
            pct = f"{int(round(value * 100))}"
            pb = draw.textbbox((0, 0), pct, font=small_font)
            text_x = bx0 + (bar_w - (pb[2] - pb[0])) / 2
            text_y = ref_y - 19
            text_y = max(chart_top - 2, text_y)
            draw.text(
                (text_x, text_y),
                pct, fill=style["text_fill"], font=small_font,
            )
        tb = draw.textbbox((0, 0), label, font=small_font)
        draw.text((gx - (tb[2] - tb[0]) / 2, chart_bottom + 8), label, fill=(75, 82, 94), font=small_font)
    lx, ly = chart_left, y1 - 22
    for name, label in (("fusion", "Fusion"), ("a", "A"), ("b", "B")):
        style = styles[name]
        _draw_patterned_bar(
            draw, (lx, ly + 4, lx + 12, ly + 16),
            fill=style["fill"], outline=style["outline"], pattern=style["pattern"],
        )
        draw.text((lx + 16, ly), label, fill=(75, 82, 94), font=small_font)
        lx += 72
    _draw_dashed_line(draw, (lx + 4, ly + 10), (lx + 34, ly + 10), fill=(35, 65, 40), width=1, dash=6, gap=3)
    draw.text((lx + 40, ly), "Fusion ref", fill=(75, 82, 94), font=small_font)


def _artifact_flow_lines(meta):
    bank = str(meta.get("bank", ""))
    readout = str(meta.get("readout", ""))
    seed = meta.get("seed", "")
    component_lineage = meta.get("component_lineage") or []
    if component_lineage:
        return [f"Source: {bank} / {readout} / seed{seed}"] + [
            str(line) for line in component_lineage[:6]
        ]
    lines = [f"Bank: {bank}", f"Readout: {readout}", f"Seed: {seed}"]
    cfg = (meta.get("model_config", {}) or {}).get("hybrid_cfg")
    if cfg:
        partner = cfg.get("partner", {}) or {}
        if partner.get("kind") == "deep":
            partner_label = f"DeepNet preset: {partner.get('preset')}"
        else:
            partner_label = f"Partner: {partner.get('bank')} + {partner.get('readout')}"
        lines.extend([
            f"Hybrid source: LCS={cfg.get('lcs_label')}",
            partner_label,
            f"Internal merge: {cfg.get('mode')} alpha={cfg.get('alpha')} thr={cfg.get('hybrid_threshold')}",
        ])
    elif bank == "__lcs__":
        lines.append("Rule source: LCS best_rules")
    elif bank == "__kan__":
        lines.append("Rule source: KAN spline backend")
    elif bank == "__kan_hybrid__":
        lines.append("Rule source: KAN hybrid backend")
    else:
        prep = (meta.get("model_config", {}) or {}).get("preprocessing", {}) or {}
        if prep:
            lines.append(f"Preprocess: {prep.get('bank_transform_scaling', prep.get('kind', 'n/a'))}")
    return lines


def _write_lineage_diagram(path, meta_a, meta_b, summary):
    width, height = 1500, 1110
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    title_font = _font(28, bold=True)
    subtitle_font = _font(15)
    box_title = _font(19, bold=True)
    body = _font(14)
    body_bold = _font(14, bold=True)
    verdict_font = _font(14, bold=True, italic=True)
    small = _font(12)
    footer_font = _font(12, italic=True)

    title = "Post-Hybrid Selection Lineage"
    tb = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((width - (tb[2] - tb[0])) / 2, 32), title, fill=(25, 30, 38), font=title_font)
    subtitle = "How candidate artifacts were fused, calibrated on validation, and applied to forecast."
    sb = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    draw.text(
        ((width - (sb[2] - sb[0])) / 2, 70),
        subtitle,
        fill=(90, 98, 110), font=subtitle_font,
    )

    a_box = (60, 135, 590, 405)
    b_box = (910, 135, 1440, 405)
    legend_box = (60, 445, 430, 720)
    merge_box = (470, 445, 1440, 720)
    result_box = (150, 790, 1350, 1072)
    source_metrics = summary.get("source_validation_metrics", {}) or {}
    _draw_candidate_box(
        draw, a_box, "Candidate A", meta_a,
        source_metrics.get("a", {}), source_metrics.get("b", {}),
        fill=(246, 250, 255), outline=(70, 130, 210),
        title_font=box_title, body_font=body, metric_font=body_bold,
    )
    _draw_candidate_box(
        draw, b_box, "Candidate B", meta_b,
        source_metrics.get("b", {}), source_metrics.get("a", {}),
        fill=(255, 248, 244), outline=(215, 115, 65),
        title_font=box_title, body_font=body, metric_font=body_bold,
    )

    m = summary.get("validation_metrics", {})
    calibration = summary.get("calibration", {}) or {}
    selection = summary.get("selection", {}) or {}
    draw.rounded_rectangle(merge_box, radius=10, fill=(248, 250, 247), outline=(85, 155, 95), width=2)
    mx0, my0, mx1, my1 = merge_box
    draw.text((mx0 + 16, my0 + 12), "Final Post-Hybrid Gate", fill=(25, 30, 38), font=box_title)
    merge_lines = [
        f"Merge logic: {summary.get('logic')}  normalize={summary.get('normalization_requested')}",
        f"Calibration: {summary.get('calibration_effective')} / metric={calibration.get('metric', 'f1')}",
        f"Threshold A: {summary.get('threshold_a'):.6g}",
        f"Threshold B: {summary.get('threshold_b'):.6g}",
        f"Selection score: {selection.get('pair_score', 'manual')}",
    ]
    y = my0 + 48
    for line in merge_lines:
        draw.text((mx0 + 16, y), line, fill=(55, 62, 74), font=body)
        y += 20
    note_x = mx0 + 690
    draw.text((note_x, my0 + 48), "Fusion output", fill=(25, 30, 38), font=body_bold)
    note = "The Result box below contains final deltas, the grouped bar chart, and the automatic verdict."
    if summary.get("bar_chart_mode") == "cumulative":
        note = "The Result box below contains cumulative deltas vs the best original baselines, the cumulative bar chart, and the automatic verdict."
    elif summary.get("bar_chart_mode") == "dual_source":
        note = "Two-stage internal merge. The Result box compares the final output against the original source lineage, not only the two visible gate boxes."
    ny = my0 + 78
    for line in _wrap_text(draw, note, body, mx1 - note_x - 18):
        draw.text((note_x, ny), line, fill=(55, 62, 74), font=body)
        ny += 20
    _orthogonal_arrow(draw, [(325, 405), (325, 425), (650, 425), (650, 445)])
    _orthogonal_arrow(draw, [(1175, 405), (1175, 425), (970, 425), (970, 445)])
    _orthogonal_arrow(draw, [(955, 720), (955, 765), (750, 765), (750, 790)])

    _draw_result_box(
        draw, result_box, summary, title_font=box_title, body_font=body,
        bold_font=body_bold, verdict_font=verdict_font, small_font=small,
    )
    legend = [
        "Blue candidate: source A",
        "Orange candidate: source B",
        "Green gate: post-hybrid merge",
        "Candidate metrics are reassessed before merge on the aligned validation set.",
        "Green/red candidate metrics compare A vs B.",
        (
            "Result deltas compare final validation against the original source lineage (A and B)."
            if summary.get("bar_chart_mode") == "dual_source"
            else "Result deltas compare final validation against the best original baseline per metric."
            if summary.get("bar_chart_mode") == "cumulative"
            else "Result deltas compare final validation against the best pre-merge candidate."
        ),
        "Selection score is post-hybrid, not original KPI.",
    ]
    _draw_box(
        draw, legend_box, "Legend", legend,
        fill=(255, 255, 255), outline=(190, 196, 206),
        title_font=box_title, body_font=small,
    )
    try:
        now = datetime.now(ZoneInfo("Asia/Tokyo"))
        stamp = now.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S local")
    footer = f"Generated by post_hybrid_artifacts.py | local timestamp: {stamp}"
    fb = draw.textbbox((0, 0), footer, font=footer_font)
    draw.text(((width - (fb[2] - fb[0])) / 2, height - 34), footer,
              fill=(100, 108, 120), font=footer_font)

    image.save(path)


def _write_lineage_comparison_png(path, meta_a, meta_b, out_val, out_forecast,
                                  *, score_column, summary):
    panels = []
    if meta_a.get("validation_combined_csv"):
        panels.append(_source_panel_from_csv(
            meta_a["validation_combined_csv"],
            title="CANDIDATE A VALIDATION",
            subtitle=_artifact_label(meta_a),
            has_segment=True,
            score_column=score_column,
        ))
    if meta_b.get("validation_combined_csv"):
        panels.append(_source_panel_from_csv(
            meta_b["validation_combined_csv"],
            title="CANDIDATE B VALIDATION",
            subtitle=_artifact_label(meta_b),
            has_segment=True,
            score_column=score_column,
        ))
    panels.append({
        "title": "FINAL POST-HYBRID VALIDATION",
        "subtitle": (
            f"{summary.get('logic')} | normalize={summary.get('normalization_requested')} "
            f"| thrA={summary.get('threshold_a'):.3g} thrB={summary.get('threshold_b'):.3g}"
        ),
        "segments": _panel_segments(out_val, has_segment=True),
    })
    if meta_a.get("forecast_csv"):
        panels.append(_source_panel_from_csv(
            meta_a["forecast_csv"],
            title="CANDIDATE A FORECAST",
            subtitle=_artifact_label(meta_a),
            has_segment=False,
            score_column=score_column,
        ))
    if meta_b.get("forecast_csv"):
        panels.append(_source_panel_from_csv(
            meta_b["forecast_csv"],
            title="CANDIDATE B FORECAST",
            subtitle=_artifact_label(meta_b),
            has_segment=False,
            score_column=score_column,
        ))
    if out_forecast:
        panels.append({
            "title": "FINAL POST-HYBRID FORECAST",
            "subtitle": (
                f"{summary.get('logic')} | forecast recalculated from A and B "
                f"using validation-calibrated thresholds"
            ),
            "segments": _panel_segments(out_forecast, has_segment=False),
        })
    write_combined_panels_png(path, panels, autoscale=True)


def main():
    parser = argparse.ArgumentParser(description="Post-hybrid tra due artifact DLvsWAVE esportati.")
    parser.add_argument("--a", default="", help="test.json del primo artifact")
    parser.add_argument("--b", default="", help="test.json del secondo artifact")
    parser.add_argument("--scan-dir", default="",
                        help="cartella da scandagliare per trovare artifact *__test.json candidati")
    parser.add_argument("--index-csv", default="",
                        help="best_trials_index.csv da usare come sorgente candidati")
    parser.add_argument("--proposal-only", action="store_true",
                        help="scrive solo la shortlist delle coppie candidate, senza fondere")
    parser.add_argument("--top-candidates", type=int, default=30,
                        help="numero massimo di artifact candidati da simulare")
    parser.add_argument("--top-pairs", type=int, default=20,
                        help="numero di coppie candidate da salvare nella shortlist")
    parser.add_argument("--forecast-guard", default="auto", choices=["auto", "off"],
                        help=("controllo anti-degenerazione forecast per proposal: "
                              "auto penalizza forecast piatto alto o quasi tutto positivo; "
                              "non richiede picchi"))
    parser.add_argument("--forecast-flat-eps", type=float, default=1e-9,
                        help="range massimo per considerare il forecast piatto nel guard")
    parser.add_argument("--forecast-high-ratio", type=float, default=0.8,
                        help="quota di punti positivi oltre cui un forecast piatto/quasi alto e' sospetto")
    parser.add_argument("--out-dir", default="", help="directory output; default: ./post_hybrid vicino ad A")
    parser.add_argument("--name", default="", help="nome/stem output")
    parser.add_argument("--logic", default="and", choices=["and", "or", "weighted", "sure", "conservative"])
    parser.add_argument("--normalize", default="auto", choices=["auto", "none", "binary", "minmax"])
    parser.add_argument("--score-column", default="predicted", choices=["predicted", "pred_recalibrated"])
    parser.add_argument("--alpha", type=float, default=0.5, help="peso del primo artifact per logic=weighted")
    parser.add_argument("--threshold", type=float, default=0.5, help="soglia su score normalizzato/finale")
    parser.add_argument("--threshold-a", type=float, default=None,
                        help="soglia sullo score A; default uguale a --threshold o calibrata")
    parser.add_argument("--threshold-b", type=float, default=None,
                        help="soglia sullo score B; default uguale a --threshold o calibrata")
    parser.add_argument("--calibrate", default="validation", choices=["none", "validation"],
                        help="calibra le soglie usando la validation allineata; usa none per disattivare")
    parser.add_argument("--calibrate-metric", default="f1",
                        choices=["f1", "f05", "bal_acc", "precision", "recall"],
                        help="metrica da massimizzare in calibrazione")
    parser.add_argument("--min-recall", type=float, default=0.0,
                        help="recall minima richiesta durante la calibrazione")
    parser.add_argument("--actual-threshold", type=float, default=None,
                        help="soglia evento per actual; default letta dagli artifact o 0.1")
    parser.add_argument("--max-rules", type=int, default=20)
    args = parser.parse_args()
    calibrate_mode = args.calibrate
    selected_proposal = None

    scan_source = args.scan_dir or args.index_csv
    if (not args.a or not args.b) and not scan_source:
        raise SystemExit("Specifica --a e --b, oppure usa --scan-dir/--index-csv per scegliere automaticamente.")

    if scan_source:
        scan_base = args.scan_dir or os.path.dirname(os.path.abspath(args.index_csv))
        scan_out_dir = args.out_dir or os.path.join(scan_base, "post_hybrid_checks")
        os.makedirs(scan_out_dir, exist_ok=True)
        candidates = _load_scan_candidates(
            args.scan_dir or None, args.index_csv or None,
            args.score_column, args.top_candidates,
            args.forecast_guard, args.forecast_flat_eps, args.forecast_high_ratio,
        )
        if len(candidates) < 2:
            raise SystemExit("Servono almeno due artifact candidati con validation/forecast per proporre fusioni.")
        proposals = _propose_pairs(
            candidates, logic=args.logic, normalize=args.normalize,
            score_column=args.score_column, alpha=args.alpha, threshold=args.threshold,
            calibrate_mode=calibrate_mode, calibrate_metric=args.calibrate_metric,
            min_recall=args.min_recall, actual_threshold=args.actual_threshold,
            top_pairs=args.top_pairs, forecast_guard=args.forecast_guard,
            forecast_flat_eps=args.forecast_flat_eps,
            forecast_high_ratio=args.forecast_high_ratio,
        )
        proposal_path = os.path.join(scan_out_dir, "post_hybrid_pair_proposals.csv")
        _write_proposals(proposal_path, proposals)
        print(f"Candidate artifacts: {len(candidates)}")
        print(f"Pair proposals:      {proposal_path}")
        for i, prop in enumerate(proposals[:5], 1):
            m = prop["simulation"]["metrics"]
            print(
                f"[{i}] score={prop['pair_score']:.3f} "
                f"f1={m['f1']:.3f} rec={m['recall']:.3f} "
                f"prec={m['precision']:.3f} bal={m['bal_acc']:.3f} "
                f"A={prop['a']['info']['label']}  B={prop['b']['info']['label']}"
            )
        if args.proposal_only:
            return
        if not proposals:
            raise SystemExit("Nessuna coppia proponibile trovata.")
        if not args.a or not args.b:
            selected_proposal = proposals[0]
            args.a = proposals[0]["a"]["path"]
            args.b = proposals[0]["b"]["path"]
            if not args.name:
                args.name = (
                    f"auto_{safe_slug(proposals[0]['a']['info']['readout'])}"
                    f"_X_{safe_slug(proposals[0]['b']['info']['readout'])}"
                    f"__{safe_slug(args.logic)}__{safe_slug(args.normalize)}"
                )
            if not args.out_dir:
                args.out_dir = scan_out_dir

    meta_a = _load_json(args.a)
    meta_b = _load_json(args.b)
    out_dir = args.out_dir or os.path.join(os.path.dirname(os.path.abspath(args.a)), "post_hybrid")
    os.makedirs(out_dir, exist_ok=True)

    stem = args.name or (
        f"posthyb_{safe_slug(meta_a.get('readout'))}_X_{safe_slug(meta_b.get('readout'))}"
        f"__{safe_slug(args.logic)}__{safe_slug(args.normalize)}"
    )
    val_a = meta_a.get("validation_combined_csv")
    val_b = meta_b.get("validation_combined_csv")
    fc_a = meta_a.get("forecast_csv")
    fc_b = meta_b.get("forecast_csv")
    if not val_a or not val_b:
        raise SystemExit("Entrambi gli artifact devono avere validation_combined_csv nel JSON.")

    rows_val_a = _read_rows(val_a, has_segment=True)
    rows_val_b = _read_rows(val_b, has_segment=True)
    aligned_val = _align_rows(rows_val_a, rows_val_b, has_segment=True)
    if not aligned_val:
        raise SystemExit("Nessuna riga validation allineabile tra i due artifact.")

    raw_thr_a = _artifact_threshold(meta_a)
    raw_thr_b = _artifact_threshold(meta_b)
    actual_threshold = args.actual_threshold
    if actual_threshold is None:
        actual_threshold = min(raw_thr_a, raw_thr_b)

    norm_a = _fit_normalizer([_score_value(a, args.score_column) for a, _ in aligned_val], args.normalize)
    norm_b = _fit_normalizer([_score_value(b, args.score_column) for _, b in aligned_val], args.normalize)
    val_scores_a = [
        _apply_normalizer(
            _score_value(a, args.score_column), norm_a,
            raw_threshold=raw_thr_a, normalized_threshold=args.threshold,
        )
        for a, _ in aligned_val
    ]
    val_scores_b = [
        _apply_normalizer(
            _score_value(b, args.score_column), norm_b,
            raw_threshold=raw_thr_b, normalized_threshold=args.threshold,
        )
        for _, b in aligned_val
    ]
    val_actual = []
    for a, b in aligned_val:
        actual_raw = a["_actual"] if math.isfinite(a["_actual"]) else b["_actual"]
        val_actual.append(1.0 if math.isfinite(actual_raw) and actual_raw >= actual_threshold else 0.0)
    calibration = _calibrate_thresholds(
        val_actual, val_scores_a, val_scores_b,
        logic=args.logic, alpha=args.alpha, threshold=args.threshold,
        mode=calibrate_mode, metric_name=args.calibrate_metric,
        min_recall=max(0.0, min(1.0, args.min_recall)),
    )
    threshold = float(calibration.get("threshold", args.threshold))
    threshold_a = args.threshold_a
    if threshold_a is None:
        threshold_a = float(calibration.get("threshold_a", threshold))
    threshold_b = args.threshold_b
    if threshold_b is None:
        threshold_b = float(calibration.get("threshold_b", threshold))
    out_val = _build_output_rows(
        aligned_val, score_col=args.score_column, norm_a=norm_a, norm_b=norm_b,
        raw_thr_a=raw_thr_a, raw_thr_b=raw_thr_b, actual_threshold=actual_threshold,
        logic=args.logic, alpha=args.alpha, threshold=threshold,
        threshold_a=threshold_a, threshold_b=threshold_b, has_segment=True,
    )

    out_forecast = []
    if fc_a and fc_b and os.path.exists(fc_a) and os.path.exists(fc_b):
        rows_fc_a = _read_rows(fc_a, has_segment=False)
        rows_fc_b = _read_rows(fc_b, has_segment=False)
        aligned_fc = _align_rows(rows_fc_a, rows_fc_b, has_segment=False)
        out_forecast = _build_output_rows(
            aligned_fc, score_col=args.score_column, norm_a=norm_a, norm_b=norm_b,
            raw_thr_a=raw_thr_a, raw_thr_b=raw_thr_b, actual_threshold=actual_threshold,
            logic=args.logic, alpha=args.alpha, threshold=threshold,
            threshold_a=threshold_a, threshold_b=threshold_b, has_segment=False,
        )

    val_csv = os.path.join(out_dir, stem + "__validation_combined.csv")
    forecast_csv = os.path.join(out_dir, stem + "__forecast.csv")
    png_path = os.path.join(out_dir, stem + "__combined.png")
    lineage_png_path = os.path.join(out_dir, stem + "__lineage_diagram.png")
    comparison_png_path = os.path.join(out_dir, stem + "__lineage_comparison.png")
    rules_path = os.path.join(out_dir, stem + "__derived_rules.json")
    summary_path = os.path.join(out_dir, stem + "__summary.json")
    bundle_dir = os.path.join(out_dir, stem + "__sources")
    source_a_dir = os.path.join(bundle_dir, _artifact_source_dir_name(meta_a, "source_a"))
    source_b_dir = os.path.join(bundle_dir, _artifact_source_dir_name(meta_b, "source_b"))
    source_a_manifest = _collect_artifact_sources(meta_a, args.a, source_a_dir)
    source_b_manifest = _collect_artifact_sources(meta_b, args.b, source_b_dir)
    _write_csv(val_csv, out_val, has_segment=True)
    if out_forecast:
        _write_csv(forecast_csv, out_forecast, has_segment=False)

    panels = [{
        "title": "POST-HYBRID VALIDATION",
        "subtitle": (
            f"{args.logic} | normalize={args.normalize}({norm_a.get('mode')},{norm_b.get('mode')}) "
            f"| thrA={threshold_a:.3g} thrB={threshold_b:.3g} "
            f"| A={_artifact_label(meta_a)} | B={_artifact_label(meta_b)}"
        ),
        "segments": _panel_segments(out_val, has_segment=True),
    }]
    if out_forecast:
        panels.append({
            "title": "POST-HYBRID FORECAST",
            "subtitle": (
                f"{args.logic} | threshold={threshold:.3g} "
                f"| thrA={threshold_a:.3g} thrB={threshold_b:.3g} "
                "| point dates = period start"
            ),
            "segments": _panel_segments(out_forecast, has_segment=False),
        })
    write_combined_panels_png(png_path, panels, autoscale=True)

    rules = _derive_rules(
        meta_a, meta_b, _load_rules(meta_a), _load_rules(meta_b),
        logic=args.logic, max_rules=max(1, args.max_rules),
    )
    with open(rules_path, "w") as f:
        json.dump(rules, f, indent=2, sort_keys=True)

    summary = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "artifact_a": args.a,
        "artifact_b": args.b,
        "label_a": _artifact_label(meta_a),
        "label_b": _artifact_label(meta_b),
        "logic": args.logic,
        "alpha": args.alpha,
        "threshold": threshold,
        "threshold_a": threshold_a,
        "threshold_b": threshold_b,
        "actual_threshold": actual_threshold,
        "score_column": args.score_column,
        "normalization_requested": args.normalize,
        "calibration_requested": args.calibrate,
        "calibration_effective": calibrate_mode,
        "normalizer_a": norm_a,
        "normalizer_b": norm_b,
        "calibration": calibration,
        "validation_rows": len(out_val),
        "forecast_rows": len(out_forecast),
        "validation_metrics": _event_metrics(
            [r["actual_event"] for r in out_val],
            [r["predicted"] for r in out_val],
        ),
        "source_validation_metrics": {
            "a": _premerge_metrics(
                aligned_val, side="a", meta=meta_a,
                score_column=args.score_column, actual_threshold=actual_threshold,
            ),
            "b": _premerge_metrics(
                aligned_val, side="b", meta=meta_b,
                score_column=args.score_column, actual_threshold=actual_threshold,
            ),
        },
        "source_merge_threshold_metrics": {
            "a": _event_metrics(
                val_actual,
                [1.0 if s >= threshold_a else 0.0 for s in val_scores_a],
            ),
            "b": _event_metrics(
                val_actual,
                [1.0 if s >= threshold_b else 0.0 for s in val_scores_b],
            ),
        },
        "source_original_metrics": {
            "a": _artifact_original_metrics(meta_a),
            "b": _artifact_original_metrics(meta_b),
        },
        "selection": {
            "mode": "auto_pair_scan" if selected_proposal is not None else "manual_or_explicit",
            "pair_score": (
                selected_proposal["pair_score"] if selected_proposal is not None else None
            ),
            "pair_rank": 1 if selected_proposal is not None else None,
            "note": (
                "Pair score combines simulated post-hybrid validation metrics, shape, "
                "depression, forecast guard, and family complementarity; it is not the "
                "original single-artifact KPI."
            ),
        },
        "paths": {
            "validation_csv": val_csv,
            "forecast_csv": forecast_csv if out_forecast else None,
            "combined_png": png_path,
            "lineage_diagram_png": lineage_png_path,
            "lineage_comparison_png": comparison_png_path,
            "derived_rules_json": rules_path,
            "sources_dir": bundle_dir,
            "source_a_dir": source_a_dir,
            "source_b_dir": source_b_dir,
            "source_a_manifest": source_a_manifest,
            "source_b_manifest": source_b_manifest,
        },
    }
    _write_lineage_diagram(lineage_png_path, meta_a, meta_b, summary)
    _write_lineage_comparison_png(
        comparison_png_path, meta_a, meta_b, out_val, out_forecast,
        score_column=args.score_column, summary=summary,
    )
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    print(f"Validation CSV: {val_csv}")
    if out_forecast:
        print(f"Forecast CSV:   {forecast_csv}")
    print(f"Combined PNG:    {png_path}")
    print(f"Lineage PNG:     {lineage_png_path}")
    print(f"Comparison PNG:  {comparison_png_path}")
    print(f"Derived rules:   {rules_path}")
    print(f"Sources dir:     {bundle_dir}")
    print(f"Summary JSON:    {summary_path}")
    m = summary["validation_metrics"]
    print(
        "Metrics: "
        f"f1={m['f1']:.3f} recall={m['recall']:.3f} "
        f"precision={m['precision']:.3f} bal_acc={m['bal_acc']:.3f} "
        f"tp={m['tp']} fp={m['fp']} tn={m['tn']} fn={m['fn']}"
    )


if __name__ == "__main__":
    main()
