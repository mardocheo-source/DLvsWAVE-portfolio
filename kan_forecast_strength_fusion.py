#!/usr/bin/env python3
"""Fuse KAN-only forecast artifacts by consensus and peak strength.

This is intentionally simpler than post-hybrid fusion: it only reads forecast
CSV files from KAN trials, normalizes each forecast's signal strength over the
requested forecast window, and selects one strongest fused peak.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from datetime import datetime, timedelta
from pathlib import Path


def parse_dt(value: str) -> datetime:
    text = str(value).strip()
    if not text:
        raise ValueError("empty date")
    text = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.strptime(text[:10], "%Y-%m-%d")


def fmt_dt(dt: datetime) -> str:
    return dt.date().isoformat()


def auto_score_column(row: dict[str, str]) -> str:
    for key in ("predicted", "pred", "pred_recalibrated", "score", "risk"):
        if key in row:
            return key
    numeric = []
    for key, value in row.items():
        if key in {"date", "segment", "row_index", "actual"}:
            continue
        try:
            float(value)
            numeric.append(key)
        except Exception:
            pass
    if not numeric:
        raise ValueError("No numeric score column found")
    return numeric[-1]


def read_forecast(path: Path, score_column: str) -> list[tuple[datetime, float]]:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return []
    date_col = "date" if "date" in rows[0] else None
    if date_col is None:
        for candidate in ("time", "context", "period_start"):
            if candidate in rows[0]:
                date_col = candidate
                break
    if date_col is None:
        raise ValueError(f"{path}: date column not found")
    col = auto_score_column(rows[0]) if score_column == "auto" else score_column
    out = []
    for row in rows:
        try:
            out.append((parse_dt(row[date_col]), float(row[col])))
        except Exception:
            continue
    return out


def minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if not math.isfinite(lo) or not math.isfinite(hi) or abs(hi - lo) < 1e-12:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def infer_step(sorted_dates: list[datetime]) -> timedelta:
    if len(sorted_dates) < 2:
        return timedelta(days=3)
    deltas = []
    for a, b in zip(sorted_dates, sorted_dates[1:]):
        delta = b - a
        if delta.total_seconds() > 0:
            deltas.append(delta)
    if not deltas:
        return timedelta(days=3)
    deltas.sort(key=lambda d: d.total_seconds())
    return deltas[len(deltas) // 2]


def safe_float(value, default: float = 0.0) -> float:
    try:
        x = float(value)
    except Exception:
        return default
    return x if math.isfinite(x) else default


def validation_quality_score(row: dict[str, str]) -> float:
    """Forecast-source quality from validation/event behavior only.

    This intentionally ignores inference speed, parameter count, train time and
    KPI/velocity style summaries.  Forecast fusion should be driven by how well
    the source model behaved on validation, not by how cheap it was to run.
    """
    f1 = safe_float(row.get("event_f1"))
    recall = safe_float(row.get("event_recall"))
    bal = safe_float(row.get("event_bal_acc"))
    precision = safe_float(row.get("event_precision"))
    spec = safe_float(row.get("event_specificity"))
    if any(v > 0 for v in (f1, recall, bal, precision, spec)):
        return float(0.40 * f1 + 0.20 * recall + 0.20 * bal + 0.10 * precision + 0.10 * spec)
    # Regression/non-event fallback: use validation fit only, still no speed.
    mse = safe_float(row.get("mse_test"), default=safe_float(row.get("mse_mean"), default=1.0))
    return float(1.0 / (1.0 + max(0.0, mse)))


def source_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        str(row.get("forecast_csv") or ""),
        str(row.get("readout") or ""),
        str(row.get("seed") or ""),
    )


def load_kan_sources(index_csv: Path, rank_mode: str) -> list[dict[str, str]]:
    with index_csv.open(newline="") as f:
        rows = list(csv.DictReader(f))
    sources = []
    for row in rows:
        bank = str(row.get("bank", "") or "")
        if bank != "__kan__":
            continue
        if str(row.get("inverted_twin", "")).lower() in {"true", "1", "yes"}:
            continue
        fc = row.get("forecast_csv") or ""
        if not fc or not os.path.exists(fc):
            continue
        row = dict(row)
        overall = safe_float(row.get("overall") or row.get("overall_mean"))
        quality = validation_quality_score(row)
        row["_overall_float"] = overall
        row["_validation_quality_float"] = quality
        if rank_mode == "overall":
            row["_rank_float"] = overall
        else:
            row["_rank_float"] = quality
        sources.append(row)
    sources.sort(
        key=lambda r: (
            float(r.get("_rank_float", 0.0)),
            float(r.get("event_f1") or 0.0),
            float(r.get("event_recall") or 0.0),
            float(r.get("event_bal_acc") or 0.0),
            -safe_float(r.get("mse_test"), default=999999.0),
        ),
        reverse=True,
    )
    return sources


def write_png(path: Path, rows: list[dict[str, object]], title: str, point_label: str, fusion_note: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[warn] matplotlib unavailable, PNG skipped: {exc}")
        return
    if not rows:
        return
    dates = [parse_dt(str(r["date"])) for r in rows]
    fused = [float(r["fused_score"]) for r in rows]
    consensus = [float(r["consensus_fraction"]) for r in rows]
    selected = [r for r in rows if int(r.get("selected_peak", 0) or 0) == 1]

    fig, ax = plt.subplots(figsize=(12, 5.2))
    ax.plot(dates, fused, marker="o", color="#d62728", linewidth=2.0, label="fused strength")
    ax.plot(dates, consensus, marker="s", color="#4c78a8", linewidth=1.4, alpha=0.75, label="consensus fraction")
    if selected:
        sx = [parse_dt(str(r["date"])) for r in selected]
        sy = [float(r["fused_score"]) for r in selected]
        ax.scatter(sx, sy, s=180, facecolors="none", edgecolors="black", linewidths=2.0, label="selected peak")
        for r in selected:
            ax.annotate(
                str(r["date"]),
                (parse_dt(str(r["date"])), float(r["fused_score"])),
                xytext=(0, 14), textcoords="offset points",
                ha="center", fontsize=9, fontweight="bold",
            )
    ax.set_title(title)
    ax.set_ylabel("normalized risk / consensus")
    ax.set_xlabel(point_label)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.25)
    if fusion_note:
        ax.text(
            0.01, 0.985, fusion_note,
            transform=ax.transAxes,
            ha="left", va="top",
            fontsize=8.5,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#999999", "alpha": 0.82},
        )
    ax.legend(loc="upper right")
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index-csv", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--score-column", default="auto")
    ap.add_argument("--top-n", type=int, default=0, help="0 = use all KAN forecasts in index")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--max-peaks", type=int, default=1)
    ap.add_argument("--rank-mode", choices=["validation-quality", "overall"], default="validation-quality",
                    help="How to rank/select source forecasts before fusion. validation-quality ignores speed/params.")
    ap.add_argument("--inverse-worst-n", type=int, default=1,
                    help="Default 1. Invert this many worst ranked source forecasts as anti-signals; 0 disables.")
    ap.add_argument("--title", default="KAN-only August micro forecast fusion")
    ap.add_argument("--output-prefix", default="kan_august_micro_strength_fusion")
    ap.add_argument("--point-label", default="auto")
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    ranked_sources = load_kan_sources(args.index_csv, args.rank_mode)
    if not ranked_sources:
        raise SystemExit(f"No KAN forecast sources found in {args.index_csv}")
    inverse_n = max(0, int(args.inverse_worst_n))
    if len(ranked_sources) <= 1:
        inverse_n = 0
    else:
        inverse_n = min(inverse_n, len(ranked_sources) - 1)
    inverse_keys = {source_key(src) for src in ranked_sources[-inverse_n:]} if inverse_n else set()
    normal_pool = [src for src in ranked_sources if source_key(src) not in inverse_keys]
    normal_sources = normal_pool[:args.top_n] if args.top_n > 0 else normal_pool
    inverse_sources = [src for src in ranked_sources if source_key(src) in inverse_keys]
    sources = [(src, "normal") for src in normal_sources] + [(src, "inverse_worst") for src in inverse_sources]
    if not sources:
        raise SystemExit(f"No usable KAN forecast sources found in {args.index_csv}")

    source_payload = []
    by_date: dict[str, list[float]] = {}
    raw_by_date: dict[str, list[float]] = {}
    normal_source_count = 0
    inverse_source_count = 0
    for src, contribution in sources:
        path = Path(src["forecast_csv"])
        series = read_forecast(path, args.score_column)
        if not series:
            continue
        raw_values = [v for _dt, v in series]
        norm_values = minmax(raw_values)
        if contribution == "inverse_worst":
            norm_values = [1.0 - v for v in norm_values]
            inverse_source_count += 1
        else:
            normal_source_count += 1
        label = (
            f"{src.get('readout')} seed={src.get('seed')} "
            f"valq={src.get('_validation_quality_float'):.4f} overall={src.get('_overall_float'):.4f}"
        )
        source_payload.append({
            "label": label,
            "contribution": contribution,
            "inversion_formula": "1 - minmax(forecast_score)" if contribution == "inverse_worst" else None,
            "forecast_csv": str(path),
            "readout": src.get("readout"),
            "seed": src.get("seed"),
            "overall": src.get("_overall_float"),
            "validation_quality": src.get("_validation_quality_float"),
            "rank_score": src.get("_rank_float"),
            "rank_mode": args.rank_mode,
            "event_precision": src.get("event_precision"),
            "event_recall": src.get("event_recall"),
            "event_f1": src.get("event_f1"),
            "event_bal_acc": src.get("event_bal_acc"),
            "event_specificity": src.get("event_specificity"),
            "mse_test": src.get("mse_test"),
            "n_rows": len(series),
        })
        for (dt, raw), norm in zip(series, norm_values):
            key = fmt_dt(dt)
            by_date.setdefault(key, []).append(float(norm))
            raw_by_date.setdefault(key, []).append(float(raw))

    dates = sorted(parse_dt(k) for k in by_date)
    step = infer_step(dates)
    rows = []
    n_sources = max(1, len(source_payload))
    for dt in dates:
        key = fmt_dt(dt)
        vals = by_date.get(key, [])
        raw_vals = raw_by_date.get(key, [])
        consensus_count = sum(1 for v in vals if v >= args.threshold)
        consensus_fraction = consensus_count / n_sources
        mean_norm = sum(vals) / len(vals) if vals else 0.0
        max_norm = max(vals) if vals else 0.0
        raw_mean = sum(raw_vals) / len(raw_vals) if raw_vals else 0.0
        fused_score = 0.60 * mean_norm + 0.25 * max_norm + 0.15 * consensus_fraction
        rows.append({
            "date": key,
            "window_end": fmt_dt(dt + step),
            "source_count": len(vals),
            "total_sources": n_sources,
            "normal_source_count": normal_source_count,
            "inverse_source_count": inverse_source_count,
            "consensus_count": consensus_count,
            "consensus_fraction": round(consensus_fraction, 6),
            "risk_mean_norm": round(mean_norm, 6),
            "risk_max_norm": round(max_norm, 6),
            "raw_mean": round(raw_mean, 6),
            "fused_score": round(fused_score, 6),
            "selected_peak": 0,
        })
    ranked = sorted(range(len(rows)), key=lambda i: float(rows[i]["fused_score"]), reverse=True)
    for i in ranked[: max(0, args.max_peaks)]:
        rows[i]["selected_peak"] = 1

    csv_path = args.output_dir / f"{args.output_prefix}.csv"
    json_path = args.output_dir / f"{args.output_prefix}.json"
    png_path = args.output_dir / f"{args.output_prefix}.png"
    step_days = step.total_seconds() / 86400.0
    if args.point_label == "auto":
        point_label = f"point date = START of forecast window; inferred step ~{step_days:g} days"
    else:
        point_label = args.point_label
    with csv_path.open("w", newline="") as f:
        fieldnames = list(rows[0].keys()) if rows else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    best = sorted(
        [r for r in rows if r["selected_peak"]],
        key=lambda r: float(r["fused_score"]),
        reverse=True,
    )
    with json_path.open("w") as f:
        json.dump({
            "index_csv": str(args.index_csv),
            "score_column": args.score_column,
            "rank_mode": args.rank_mode,
            "inverse_worst_n": args.inverse_worst_n,
            "inverse_worst_applied": inverse_source_count,
            "inverse_worst_formula": "1 - minmax(forecast_score)",
            "normal_source_count": normal_source_count,
            "inverse_source_count": inverse_source_count,
            "threshold": args.threshold,
            "max_peaks": args.max_peaks,
            "fusion_formula": "0.60*mean_norm + 0.25*max_norm + 0.15*consensus_fraction; inverse-worst sources contribute as 1-minmax(score)",
            "point_semantics": point_label,
            "inferred_step_days": step_days,
            "sources": source_payload,
            "selected_peak": best[0] if best else None,
            "selected_peaks": best,
            "outputs": {"csv": str(csv_path), "json": str(json_path), "png": str(png_path)},
        }, f, indent=2, default=str)
    fusion_note = (
        f"Fusion args: rank-mode={args.rank_mode}; "
        f"inverse-worst-n={args.inverse_worst_n}; applied={inverse_source_count}; "
        "inverse formula=1-minmax(score)"
    )
    write_png(png_path, rows, args.title, point_label, fusion_note)
    if best:
        b = best[0]
        print(
            "KAN micro strongest selected peak: "
            f"{b['date']} -> {b['window_end']} fused={b['fused_score']} "
            f"consensus={b['consensus_count']}/{b['total_sources']}"
        )
        if len(best) > 1:
            print("Selected peaks:")
            for r in best:
                print(
                    f"  {r['date']} -> {r['window_end']} fused={r['fused_score']} "
                    f"consensus={r['consensus_count']}/{r['total_sources']}"
                )
    print(f"CSV:  {csv_path}")
    print(f"JSON: {json_path}")
    print(f"PNG:  {png_path}")


if __name__ == "__main__":
    main()
