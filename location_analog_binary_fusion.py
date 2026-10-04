#!/usr/bin/env python3
"""Fuse analog and binary localization reports into one final view."""
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
        if math.isfinite(out):
            return out
    except Exception:
        return None
    return None


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def metric_float(metrics: dict[str, object], key: str) -> float | None:
    try:
        value = metrics.get(key)
        if value is None:
            return None
        out = float(value)
        return out if math.isfinite(out) else None
    except Exception:
        return None


def merge_validation_metrics(analog_meta: dict[str, object],
                             binary_meta: dict[str, object]) -> dict[str, object]:
    am = analog_meta.get("validation_metrics") if isinstance(analog_meta, dict) else None
    bm = binary_meta.get("validation_metrics") if isinstance(binary_meta, dict) else None
    am = am if isinstance(am, dict) else {}
    bm = bm if isinstance(bm, dict) else {}
    out: dict[str, object] = {
        "analog": am,
        "binary": bm,
        "method_note": (
            "Combined from analog regression and binary threshold validation. "
            "Binary event metrics are preferred when a classification metric exists."
        ),
    }
    for key in ("overall", "event_f1", "event_recall", "event_precision", "event_bal_acc", "event_specificity"):
        bv = metric_float(bm, key)
        av = metric_float(am, key)
        vals = [v for v in (av, bv) if v is not None]
        if key.startswith("event_") and bv is not None:
            out[key] = bv
        elif vals:
            out[key] = sum(vals) / len(vals)
        else:
            out[key] = None
    out["bank"] = f"analog:{am.get('bank', '')}|binary:{bm.get('bank', '')}"
    out["readout"] = f"analog:{am.get('readout', '')}|binary:{bm.get('readout', '')}"
    return out


def sigmoid(x: float) -> float:
    if x >= 40:
        return 1.0
    if x <= -40:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def side_label(value: float, threshold: float, direction: str) -> str:
    if direction == "below":
        return "below" if value <= threshold else "above"
    return "above" if value >= threshold else "below"


def positive_label(direction: str) -> str:
    return "below" if direction == "below" else "above"


def analog_support(value: float, threshold: float, direction: str, scale: float) -> float:
    signed = (threshold - value) if direction == "below" else (value - threshold)
    return sigmoid(signed / max(scale, 1e-9))


def infer_scale(values: list[float], threshold: float) -> float:
    if not values:
        return 1.0
    lo, hi = min(values), max(values)
    span = max(hi - lo, 1e-9)
    avg_abs = mean([abs(v - threshold) for v in values]) or 0.0
    return max(span * 0.18, avg_abs * 0.65, 1e-6)


def agreement_label(analog_decision: str, binary_decision: str) -> str:
    if not analog_decision or not binary_decision:
        return "unknown"
    return "agree" if analog_decision == binary_decision else "conflict"


def final_decision(fused_probability: float, direction: str) -> str:
    pos = positive_label(direction)
    neg = "above" if pos == "below" else "below"
    return pos if fused_probability >= 0.5 else neg


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
    analog = [float(r["analog_estimated_value"]) for r in rows]
    binary = [float(r["binary_probability"]) for r in rows]
    fused = [float(r["fused_probability"]) for r in rows]
    focus_dates = [
        parse_dt(str(r["date"])) for r in rows if int(r.get("focus_window", 0) or 0) == 1
    ]
    threshold = optional_float(summary.get("decision_threshold"))
    focus_start = summary.get("focus_start_date")
    focus_end = summary.get("focus_end_date")
    focus_start_dt = parse_dt(str(focus_start)) if focus_start else None
    focus_end_dt = parse_dt(str(focus_end)) if focus_end else None

    def label_hline(ax, y: float, text: str) -> None:
        ax.text(
            0.012, y, text,
            transform=ax.get_yaxis_transform(),
            ha="left", va="bottom",
            fontsize=8.5, color="#111827",
            bbox={"boxstyle": "round,pad=0.18", "facecolor": "white",
                  "edgecolor": "none", "alpha": 0.82},
        )

    fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True)
    ax = axes[0]
    ax.plot(dates, analog, color="#dc2626", marker="o", linewidth=1.8,
            label=f"analog {summary.get('target_source')}")
    if threshold is not None:
        ax.axhline(threshold, color="#111827", linestyle="--", linewidth=1.1,
                   label=f"threshold {threshold:g}")
        label_hline(ax, threshold, f"threshold {threshold:.3f}")
    if focus_start_dt and focus_end_dt:
        ax.axvspan(focus_start_dt, focus_end_dt, color="#fee2e2", alpha=0.55)
    ax.set_ylabel(str(summary.get("target_source")))
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")

    ax = axes[1]
    ax.plot(dates, binary, color="#2563eb", marker="o", linewidth=1.8,
            label="binary probability")
    ax.axhline(0.5, color="#111827", linestyle="--", linewidth=1.1,
               label="binary decision line")
    label_hline(ax, 0.5, "decision 0.500")
    if focus_start_dt and focus_end_dt:
        ax.axvspan(focus_start_dt, focus_end_dt, color="#dbeafe", alpha=0.55)
    ax.set_ylabel("probability")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")

    ax = axes[2]
    ax.plot(dates, fused, color="#15803d", marker="o", linewidth=2.0,
            label="fused localization support")
    ax.axhline(0.5, color="#111827", linestyle="--", linewidth=1.1,
               label="fused decision line")
    label_hline(ax, 0.5, "decision 0.500")
    if focus_start_dt and focus_end_dt:
        ax.axvspan(focus_start_dt, focus_end_dt, color="#dcfce7", alpha=0.55)
    if focus_dates:
        focus_y = [
            float(r["fused_probability"])
            for r in rows if int(r.get("focus_window", 0) or 0) == 1
        ]
        ax.scatter(focus_dates, focus_y, s=90, facecolors="none",
                   edgecolors="black", linewidths=1.7, label="focus points")
    ax.set_ylabel("fused support")
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("point date = START of forecast window")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")

    fig.suptitle(title, fontsize=14, fontweight="bold")
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analog-csv", required=True, type=Path)
    ap.add_argument("--analog-json", required=True, type=Path)
    ap.add_argument("--binary-csv", required=True, type=Path)
    ap.add_argument("--binary-json", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--output-prefix", default="location_analog_binary_fusion")
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    analog_meta = json.loads(args.analog_json.read_text())
    binary_meta = json.loads(args.binary_json.read_text())
    analog_rows = {r["date"]: r for r in read_csv(args.analog_csv)}
    binary_rows = {r["date"]: r for r in read_csv(args.binary_csv)}
    common_dates = sorted(set(analog_rows) & set(binary_rows), key=parse_dt)
    if not common_dates:
        raise SystemExit("No common forecast dates between analog and binary reports")

    target = analog_meta.get("target_source") or binary_meta.get("target_source")
    direction = str(binary_meta.get("binary_direction") or analog_meta.get("binary_direction") or "above")
    threshold = optional_float(binary_meta.get("decision_threshold"))
    if threshold is None:
        threshold = optional_float(analog_meta.get("decision_threshold"))
    if threshold is None:
        raise SystemExit("Resolved numeric decision_threshold not found in analog/binary metadata")
    analog_values = [
        float(analog_rows[d]["estimated_value"]) for d in common_dates
    ]
    scale = infer_scale(analog_values, threshold)

    rows: list[dict[str, object]] = []
    for date in common_dates:
        a = analog_rows[date]
        b = binary_rows[date]
        analog_value = float(a["estimated_value"])
        binary_prob = float(b["estimated_value"])
        a_support = analog_support(analog_value, threshold, direction, scale)
        fused_prob = 0.55 * a_support + 0.45 * binary_prob
        a_decision = side_label(analog_value, threshold, direction)
        b_decision = str(b.get("decision_vs_threshold") or final_decision(binary_prob, direction))
        rows.append({
            "date": date,
            "analog_estimated_value": analog_value,
            "analog_support": a_support,
            "binary_probability": binary_prob,
            "fused_probability": fused_prob,
            "analog_decision": a_decision,
            "binary_decision": b_decision,
            "fused_decision": final_decision(fused_prob, direction),
            "agreement": agreement_label(a_decision, b_decision),
            "focus_window": int(a.get("focus_window", "0") or 0) or int(b.get("focus_window", "0") or 0),
        })

    focus_rows = [r for r in rows if int(r["focus_window"]) == 1]
    selected = focus_rows or rows
    agreement_fraction = (
        sum(1 for r in selected if r["agreement"] == "agree") / len(selected)
        if selected else 0.0
    )
    fused_mean = mean([float(r["fused_probability"]) for r in selected])
    analog_mean = mean([float(r["analog_estimated_value"]) for r in selected])
    binary_mean = mean([float(r["binary_probability"]) for r in selected])
    final = final_decision(float(fused_mean or 0.0), direction)
    confidence = "high" if agreement_fraction >= 0.75 and abs(float(fused_mean or 0.5) - 0.5) >= 0.15 else (
        "medium" if agreement_fraction >= 0.5 else "low"
    )
    summary = {
        "target_source": target,
        "direction": direction,
        "positive_label": positive_label(direction),
        "decision_threshold": threshold,
        "focus_start_date": analog_meta.get("focus_start_date") or binary_meta.get("focus_start_date"),
        "focus_end_date": analog_meta.get("focus_end_date") or binary_meta.get("focus_end_date"),
        "focus_rows": len(focus_rows),
        "analog_mean": analog_mean,
        "binary_probability_mean": binary_mean,
        "fused_probability_mean": fused_mean,
        "agreement_fraction": agreement_fraction,
        "source_mode": "analog_binary",
        "method_label": "KAN-only analog+binary",
        "validation_metrics": merge_validation_metrics(analog_meta, binary_meta),
        "final_decision": final,
        "confidence": confidence,
        "analog_json": str(args.analog_json),
        "binary_json": str(args.binary_json),
        "fusion_formula": (
            "fused_probability = 0.55 * analog_threshold_support + "
            "0.45 * binary_probability"
        ),
        "note": (
            "This is a second-stage experimental localization fusion. Analog estimates "
            "the physical value; binary tests the threshold condition. The fused result "
            "is strongest when both agree inside the focus window."
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
                "binary_probability", "fused_probability", "analog_decision",
                "binary_decision", "fused_decision", "agreement", "focus_window",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    title = args.title or f"{target} analog + binary localization fusion"
    write_png(out_png, rows, summary, title)
    sign = "<=" if direction == "below" else ">="
    out_md.write_text(
        f"# {title}\n\n"
        "Experimental second-stage localization fusion.\n\n"
        f"- target: `{target}`\n"
        f"- condition: `{target} {sign} {threshold}`\n"
        f"- focus window: `{summary['focus_start_date']}` -> `{summary['focus_end_date']}`\n"
        f"- analog mean in focus: `{analog_mean}`\n"
        f"- binary probability mean in focus: `{binary_mean}`\n"
        f"- fused probability mean in focus: `{fused_mean}`\n"
        f"- analog/binary agreement in focus: `{agreement_fraction:.3f}`\n"
        f"- final fused decision: **{final}**\n"
        f"- confidence: **{confidence}**\n\n"
        f"Formula: `{summary['fusion_formula']}`.\n\n"
        "Point semantics: every forecast date is the START of its forecast window.\n",
    )
    print(f"CSV:  {out_csv}")
    print(f"JSON: {out_json}")
    print(f"PNG:  {out_png}")
    print(f"MD:   {out_md}")


if __name__ == "__main__":
    main()
