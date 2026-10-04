#!/usr/bin/env python3
"""Adapt a binary localization report to the local-fusion interface.

This is used for symbolic-only experiments such as LCS/LCS-hybrid, where an
analog latitude/longitude/depth estimate does not exist.  The output keeps the
same CSV/JSON shape consumed by location_vertical_horizontal_fusion.py, but it
marks the report as binary-only so downstream lineage can label the metric as
unary instead of analog/binary agreement.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path


def parse_dt(value: str) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.strptime(text[:10], "%Y-%m-%d")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except Exception:
        return None


def final_decision(probability: float, direction: str) -> str:
    positive = "below" if direction == "below" else "above"
    negative = "above" if direction == "below" else "below"
    return positive if probability >= 0.5 else negative


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def write_png(path: Path, rows: list[dict[str, object]], summary: dict[str, object],
              title: str) -> None:
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
    probs = [float(r["fused_probability"]) for r in rows]
    focus_dates = [
        parse_dt(str(r["date"])) for r in rows
        if int(r.get("focus_window", 0) or 0) == 1
    ]
    focus_probs = [
        float(r["fused_probability"]) for r in rows
        if int(r.get("focus_window", 0) or 0) == 1
    ]
    fig, ax = plt.subplots(figsize=(12, 5.4))
    ax.plot(dates, probs, marker="o", linewidth=2.0, color="#7c3aed",
            label="binary-only support")
    ax.axhline(0.5, color="#111827", linestyle="--", linewidth=1.1,
               label="decision 0.500")
    if focus_dates:
        ax.scatter(focus_dates, focus_probs, s=95, facecolors="none",
                   edgecolors="black", linewidths=1.7, label="focus points")
    ax.set_ylim(-0.05, 1.05)
    ax.set_ylabel("binary probability/support")
    ax.set_xlabel("point date = START of forecast window")
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binary-csv", required=True, type=Path)
    ap.add_argument("--binary-json", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--output-prefix", default="binary_only_localization_fusion")
    ap.add_argument("--title", default="Binary-only localization fusion")
    ap.add_argument("--method-label", default="LCS/LCS-hybrid")
    args = ap.parse_args()

    meta = json.loads(args.binary_json.read_text())
    rows_in = sorted(read_csv(args.binary_csv), key=lambda r: parse_dt(r["date"]))
    direction = str(meta.get("binary_direction") or "above")
    threshold = optional_float(meta.get("decision_threshold"))
    target = meta.get("target_source") or "location"
    threshold_proxy = float(threshold) if threshold is not None else 0.0

    rows: list[dict[str, object]] = []
    for row in rows_in:
        prob = optional_float(row.get("estimated_value"))
        if prob is None:
            prob = optional_float(row.get("predicted_raw"))
        prob = max(0.0, min(1.0, float(prob if prob is not None else 0.0)))
        rows.append({
            "date": row["date"],
            "analog_estimated_value": threshold_proxy,
            "analog_support": prob,
            "binary_probability": prob,
            "fused_probability": prob,
            "analog_decision": "not_applicable_binary_only",
            "binary_decision": row.get("decision_vs_threshold") or final_decision(prob, direction),
            "fused_decision": row.get("decision_vs_threshold") or final_decision(prob, direction),
            "agreement": "binary_only",
            "focus_window": int(row.get("focus_window", "0") or 0),
        })

    selected = [r for r in rows if int(r["focus_window"]) == 1] or rows
    probs = [float(r["fused_probability"]) for r in selected]
    fused_mean = mean(probs)
    summary = {
        "target_source": target,
        "direction": direction,
        "positive_label": "below" if direction == "below" else "above",
        "decision_threshold": threshold,
        "focus_start_date": meta.get("focus_start_date"),
        "focus_end_date": meta.get("focus_end_date"),
        "focus_rows": len([r for r in rows if int(r["focus_window"]) == 1]),
        "analog_mean": None,
        "binary_probability_mean": fused_mean,
        "fused_probability_mean": fused_mean,
        "agreement_fraction": 1.0,
        "source_mode": "binary_only",
        "method_label": args.method_label,
        "validation_metrics": meta.get("validation_metrics", {}),
        "final_decision": final_decision(float(fused_mean or 0.0), direction),
        "confidence": "binary-only",
        "binary_json": str(args.binary_json),
        "fusion_formula": "fused_probability = binary_probability",
        "note": (
            f"{args.method_label} is a binary/unary localization check. "
            "No analog physical value is estimated; the value column is a "
            "threshold placeholder used only for compatibility with the "
            "vertical/horizontal comparison."
        ),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_csv = args.output_dir / f"{args.output_prefix}.csv"
    out_json = args.output_dir / f"{args.output_prefix}.json"
    out_png = args.output_dir / f"{args.output_prefix}.png"
    out_md = args.output_dir / f"{args.output_prefix}.md"
    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "date", "analog_estimated_value", "analog_support",
                "binary_probability", "fused_probability",
                "analog_decision", "binary_decision", "fused_decision",
                "agreement", "focus_window",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_png(out_png, rows, summary, args.title)
    out_md.write_text(
        f"# {args.title}\n\n"
        f"- target: `{target}`\n"
        f"- binary condition threshold: `{threshold}`\n"
        f"- focus window: `{summary['focus_start_date']}` -> `{summary['focus_end_date']}`\n"
        f"- mean support: `{summary['fused_probability_mean']}`\n"
        f"- decision: **{summary['final_decision']}**\n\n"
        "This is a binary-only/unary localization report. LCS/LCS-hybrid does "
        "not produce an analog latitude/longitude/depth estimate here.\n",
    )
    print(f"CSV:  {out_csv}")
    print(f"JSON: {out_json}")
    print(f"PNG:  {out_png}")
    print(f"MD:   {out_md}")


if __name__ == "__main__":
    main()
