#!/usr/bin/env python3
"""Fuse vertical and horizontal localization fusion reports."""
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


def metric_float(metrics: dict[str, object] | None, key: str) -> float | None:
    if not isinstance(metrics, dict):
        return None
    try:
        value = metrics.get(key)
        if value is None:
            return None
        out = float(value)
        return out if math.isfinite(out) else None
    except Exception:
        return None


def validation_quality(summary: dict[str, object]) -> float:
    metrics = summary.get("validation_metrics")
    if not isinstance(metrics, dict):
        return 0.5
    vals = []
    for key, weight in (
        ("overall", 0.35),
        ("event_f1", 0.25),
        ("event_bal_acc", 0.20),
        ("event_precision", 0.10),
        ("event_recall", 0.10),
    ):
        value = metric_float(metrics, key)
        if value is not None:
            vals.append((max(0.0, min(1.0, value)), weight))
    if not vals:
        return 0.5
    return sum(v * w for v, w in vals) / max(sum(w for _, w in vals), 1e-9)


def aggregate_validation_metrics(*summaries: dict[str, object]) -> dict[str, object]:
    items = []
    for summary in summaries:
        metrics = summary.get("validation_metrics")
        if isinstance(metrics, dict):
            items.append(metrics)
    out: dict[str, object] = {}
    for key in ("overall", "event_f1", "event_recall", "event_precision", "event_bal_acc", "event_specificity"):
        vals = [metric_float(m, key) for m in items]
        vals = [v for v in vals if v is not None]
        out[key] = (sum(vals) / len(vals)) if vals else None
    out["quality_score"] = sum(validation_quality(s) for s in summaries) / max(len(summaries), 1)
    out["sources"] = [s.get("method_label") or s.get("source_mode") for s in summaries]
    return out


def positive_label(direction: str) -> str:
    return "below" if direction == "below" else "above"


def final_decision(probability: float, direction: str) -> str:
    pos = positive_label(direction)
    neg = "above" if pos == "below" else "below"
    return pos if probability >= 0.5 else neg


def agreement(a: str, b: str) -> str:
    if not a or not b:
        return "unknown"
    return "agree" if a == b else "conflict"


def internal_agreement_value(value: object) -> float:
    text = str(value or "")
    if text in {"agree", "binary_only", "unary"}:
        return 1.0
    return 0.0


def value_weight(probability: float) -> float:
    return 0.25 + abs(float(probability) - 0.5)


def confidence_label(fused_mean: float, vh_agreement: float,
                     source_agreement: float) -> str:
    margin = abs(float(fused_mean) - 0.5)
    score = 0.45 * vh_agreement + 0.35 * source_agreement + 0.20 * min(1.0, margin / 0.25)
    if score >= 0.72:
        return "high"
    if score >= 0.48:
        return "medium"
    return "low"


def candidate_metrics(rows: list[dict[str, object]], prefix: str,
                      source_summary: dict[str, object]) -> dict[str, float]:
    selected = [r for r in rows if int(r.get("focus_window", 0) or 0) == 1] or rows
    probs = [float(r[f"{prefix}_fused_probability"]) for r in selected]
    agreements = [internal_agreement_value(r.get(f"{prefix}_agreement", "")) for r in selected]
    return {
        "support": float(mean(probs) or 0.0),
        "margin": abs(float(mean(probs) or 0.0) - 0.5),
        "internal_agreement": float(source_summary.get("agreement_fraction") or mean(agreements) or 0.0),
    }


def final_metrics(rows: list[dict[str, object]]) -> dict[str, float]:
    selected = [r for r in rows if int(r.get("focus_window", 0) or 0) == 1] or rows
    probs = [float(r["final_probability"]) for r in selected]
    vh_agree = [1.0 if str(r["vertical_horizontal_agreement"]) == "agree" else 0.0 for r in selected]
    source_agree = [float(r["combined_internal_agreement"]) for r in selected]
    support = float(mean(probs) or 0.0)
    return {
        "support": support,
        "margin": abs(support - 0.5),
        "internal_agreement": float(mean(source_agree) or 0.0),
        "vertical_horizontal_agreement": float(mean(vh_agree) or 0.0),
    }


def contradiction_resolution(v_dec: str, h_dec: str, vq: float, hq: float) -> str:
    if v_dec == h_dec:
        return "agreement"
    diff = abs(vq - hq)
    if diff < 0.03:
        return "conflict_near_tie"
    return "vertical_preferred_by_validation" if vq > hq else "horizontal_preferred_by_validation"


def write_main_png(path: Path, rows: list[dict[str, object]], summary: dict[str, object],
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
    vertical_value = [float(r["vertical_estimated_value"]) for r in rows]
    horizontal_value = [float(r["horizontal_estimated_value"]) for r in rows]
    final_value = [float(r["final_estimated_value"]) for r in rows]
    vertical_prob = [float(r["vertical_fused_probability"]) for r in rows]
    horizontal_prob = [float(r["horizontal_fused_probability"]) for r in rows]
    final_prob = [float(r["final_probability"]) for r in rows]
    threshold = optional_float(summary.get("decision_threshold"))
    focus_start = summary.get("focus_start_date")
    focus_end = summary.get("focus_end_date")
    fs = parse_dt(str(focus_start)) if focus_start else None
    fe = parse_dt(str(focus_end)) if focus_end else None

    def label_hline(ax, y: float, text: str) -> None:
        ax.text(
            0.012, y, text,
            transform=ax.get_yaxis_transform(),
            ha="left", va="bottom",
            fontsize=8.5, color="#111827",
            bbox={"boxstyle": "round,pad=0.18", "facecolor": "white",
                  "edgecolor": "none", "alpha": 0.82},
        )

    # Do not share the x-axis with the bar-chart panel: the first two panels
    # use dates while the third uses categorical labels.
    fig, axes = plt.subplots(3, 1, figsize=(13, 9.4), sharex=False)
    ax = axes[0]
    ax.plot(dates, vertical_value, marker="o", linewidth=1.7, color="#2563eb", label="vertical estimate")
    ax.plot(dates, horizontal_value, marker="o", linewidth=1.7, color="#dc2626", label="horizontal estimate")
    ax.plot(dates, final_value, marker="o", linewidth=2.2, color="#15803d", label="final fused estimate")
    if threshold is not None:
        ax.axhline(threshold, color="#111827", linestyle="--", linewidth=1.1, label=f"threshold {threshold:g}")
        label_hline(ax, threshold, f"threshold {threshold:.3f}")
    if fs and fe:
        ax.axvspan(fs, fe, color="#fef3c7", alpha=0.55)
    ax.set_ylabel(str(summary.get("target_source")))
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")

    ax = axes[1]
    ax.plot(dates, vertical_prob, marker="o", linewidth=1.5, color="#2563eb", label="vertical support")
    ax.plot(dates, horizontal_prob, marker="o", linewidth=1.5, color="#dc2626", label="horizontal support")
    ax.plot(dates, final_prob, marker="o", linewidth=2.2, color="#15803d", label="final support")
    ax.axhline(0.5, color="#111827", linestyle="--", linewidth=1.1, label="decision line")
    label_hline(ax, 0.5, "decision 0.500")
    if fs and fe:
        ax.axvspan(fs, fe, color="#dcfce7", alpha=0.45)
    ax.set_ylabel("probability/support")
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("point date = START of forecast window")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")

    ax = axes[2]
    names = ["vertical", "horizontal", "final"]
    support = [
        float(summary["vertical_metrics"]["support"]),
        float(summary["horizontal_metrics"]["support"]),
        float(summary["final_metrics"]["support"]),
    ]
    agree = [
        float(summary["vertical_metrics"]["internal_agreement"]),
        float(summary["horizontal_metrics"]["internal_agreement"]),
        float(summary["final_metrics"]["vertical_horizontal_agreement"]),
    ]
    validation = [
        float(summary.get("vertical_validation_quality", 0.5)),
        float(summary.get("horizontal_validation_quality", 0.5)),
        float(summary.get("final_validation_metrics", {}).get("quality_score", 0.5) or 0.5),
    ]
    x = range(len(names))
    ax.bar([i - 0.24 for i in x], support, width=0.24, color="#60a5fa", label="focus support")
    ax.bar([i for i in x], agree, width=0.24, color="#86efac", label="agreement")
    ax.bar([i + 0.24 for i in x], validation, width=0.24, color="#fbbf24", label="validation quality")
    ax.set_xticks(list(x), names)
    ax.set_ylim(0, 1.05)
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(loc="best")
    ax.set_ylabel("metric")

    fig.suptitle(title, fontsize=14, fontweight="bold")
    for ax in axes[:2]:
        for label in ax.get_xticklabels():
            label.set_rotation(45)
            label.set_ha("right")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_lineage_png(path: Path, summary: dict[str, object], title: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    except Exception as exc:
        print(f"[warn] matplotlib unavailable, lineage PNG skipped: {exc}")
        return

    fig, ax = plt.subplots(figsize=(13, 7.2))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.5, 0.95, title, ha="center", va="top", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.91, "Vertical and horizontal localization fusions are compared on the same focus window.",
            ha="center", va="top", fontsize=10, color="#6b7280")

    def box(x, y, w, h, title_text, lines, color):
        patch = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.01",
            linewidth=1.6, edgecolor=color, facecolor="#ffffff"
        )
        ax.add_patch(patch)
        ax.text(x + 0.02, y + h - 0.045, title_text, fontsize=12, fontweight="bold", color="#111827")
        yy = y + h - 0.085
        for line in lines:
            ax.text(x + 0.02, yy, line, fontsize=9.2, color="#374151")
            yy -= 0.04

    vm = summary["vertical_metrics"]
    hm = summary["horizontal_metrics"]
    fm = summary["final_metrics"]
    direction = summary.get("direction")
    sign = "<=" if direction == "below" else ">="
    threshold = summary.get("decision_threshold")
    vertical_mode = str(summary.get("vertical_source_mode") or "analog_binary")
    horizontal_mode = str(summary.get("horizontal_source_mode") or "analog_binary")
    vertical_agreement_label = (
        "unary metric: LCS binary-only"
        if vertical_mode == "binary_only" else
        "internal analog/binary agreement"
    )
    vertical_quality = float(summary.get("vertical_validation_quality", 0.5))
    horizontal_quality = float(summary.get("horizontal_validation_quality", 0.5))
    horizontal_agreement_label = (
        "unary metric: LCS binary-only"
        if horizontal_mode == "binary_only" else
        "internal analog/binary agreement"
    )
    box(
        0.07, 0.56, 0.36, 0.26,
        "Candidate A - vertical fusion",
        [
            f"support={vm['support']:.3f} margin={vm['margin']:.3f}",
            f"{vertical_agreement_label}={vm['internal_agreement']:.3f}",
            f"validation quality={vertical_quality:.3f}",
            f"decision={summary.get('vertical_decision')}",
            f"condition: {summary.get('target_source')} {sign} {threshold}",
        ],
        "#2563eb",
    )
    box(
        0.57, 0.56, 0.36, 0.26,
        "Candidate B - horizontal fusion",
        [
            f"support={hm['support']:.3f} margin={hm['margin']:.3f}",
            f"{horizontal_agreement_label}={hm['internal_agreement']:.3f}",
            f"validation quality={horizontal_quality:.3f}",
            f"decision={summary.get('horizontal_decision')}",
            f"condition: {summary.get('target_source')} {sign} {threshold}",
        ],
        "#dc2626",
    )
    box(
        0.25, 0.16, 0.50, 0.26,
        "Final vertical/horizontal localization fusion",
        [
            f"support={fm['support']:.3f} margin={fm['margin']:.3f}",
            f"vertical/horizontal agreement={fm['vertical_horizontal_agreement']:.3f}",
            f"combined internal agreement={fm['internal_agreement']:.3f}",
            f"conflict policy={summary.get('conflict_policy')}",
            f"final decision={summary.get('final_decision')} confidence={summary.get('confidence')}",
            f"focus: {summary.get('focus_start_date')} -> {summary.get('focus_end_date')}",
        ],
        "#15803d",
    )
    ax.add_patch(FancyArrowPatch((0.25, 0.56), (0.42, 0.42), arrowstyle="-|>",
                                 mutation_scale=16, linewidth=1.6, color="#374151"))
    ax.add_patch(FancyArrowPatch((0.75, 0.56), (0.58, 0.42), arrowstyle="-|>",
                                 mutation_scale=16, linewidth=1.6, color="#374151"))
    ax.text(
        0.5, 0.08,
        "Generated by location_vertical_horizontal_fusion.py. Values are experimental model signals, not deterministic predictions.",
        ha="center", fontsize=8.5, color="#6b7280",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vertical-csv", required=True, type=Path)
    ap.add_argument("--vertical-json", required=True, type=Path)
    ap.add_argument("--horizontal-csv", required=True, type=Path)
    ap.add_argument("--horizontal-json", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--output-prefix", default="final_vertical_horizontal_localization_fusion")
    ap.add_argument("--title", default="Vertical vs horizontal localization fusion")
    args = ap.parse_args()

    v_summary = json.loads(args.vertical_json.read_text())
    h_summary = json.loads(args.horizontal_json.read_text())
    v_rows = {r["date"]: r for r in read_csv(args.vertical_csv)}
    h_rows = {r["date"]: r for r in read_csv(args.horizontal_csv)}
    common_dates = sorted(set(v_rows) & set(h_rows), key=parse_dt)
    if not common_dates:
        raise SystemExit("No common dates between vertical and horizontal localization fusions")

    threshold = optional_float(v_summary.get("decision_threshold"))
    if threshold is None:
        threshold = optional_float(h_summary.get("decision_threshold"))
    if threshold is None:
        raise SystemExit("No numeric decision_threshold found in vertical/horizontal summaries")
    target = v_summary.get("target_source") or h_summary.get("target_source")
    direction = str(v_summary.get("direction") or h_summary.get("direction") or "above")
    v_quality = validation_quality(v_summary)
    h_quality = validation_quality(h_summary)
    rows: list[dict[str, object]] = []
    for date in common_dates:
        v = v_rows[date]
        h = h_rows[date]
        vp = float(v["fused_probability"])
        hp = float(h["fused_probability"])
        vv = float(v["analog_estimated_value"])
        hv = float(h["analog_estimated_value"])
        vw = value_weight(vp)
        hw = value_weight(hp)
        v_dec = str(v.get("fused_decision") or final_decision(vp, direction))
        h_dec = str(h.get("fused_decision") or final_decision(hp, direction))
        resolution = contradiction_resolution(v_dec, h_dec, v_quality, h_quality)
        if v_dec != h_dec and resolution not in {"conflict_near_tie"}:
            # When the two master policies contradict each other, use validation
            # quality as the arbiter instead of averaging blindly.
            if resolution.startswith("vertical"):
                vw *= 1.0 + 2.5 * max(0.0, v_quality - h_quality)
                hw *= max(0.20, 1.0 - 1.5 * max(0.0, v_quality - h_quality))
            else:
                hw *= 1.0 + 2.5 * max(0.0, h_quality - v_quality)
                vw *= max(0.20, 1.0 - 1.5 * max(0.0, h_quality - v_quality))
        final_value = (vv * vw + hv * hw) / max(vw + hw, 1e-9)
        if v_dec != h_dec and resolution not in {"conflict_near_tie"}:
            final_prob = (vp * vw + hp * hw) / max(vw + hw, 1e-9)
        else:
            final_prob = 0.50 * ((vp + hp) / 2.0) + 0.25 * min(vp, hp) + 0.25 * (1.0 - abs(vp - hp))
        final_prob = max(0.0, min(1.0, final_prob))
        internal = (
            internal_agreement_value(v.get("agreement"))
            + internal_agreement_value(h.get("agreement"))
        ) / 2.0
        rows.append({
            "date": date,
            "vertical_estimated_value": vv,
            "horizontal_estimated_value": hv,
            "final_estimated_value": final_value,
            "vertical_fused_probability": vp,
            "horizontal_fused_probability": hp,
            "final_probability": final_prob,
            "vertical_decision": v_dec,
            "horizontal_decision": h_dec,
            "final_decision": final_decision(final_prob, direction),
            "vertical_horizontal_agreement": agreement(v_dec, h_dec),
            "conflict_resolution": resolution,
            "combined_internal_agreement": internal,
            "focus_window": int(v.get("focus_window", "0") or 0) or int(h.get("focus_window", "0") or 0),
        })

    selected = [r for r in rows if int(r["focus_window"]) == 1] or rows
    v_metrics = candidate_metrics(rows, "vertical", v_summary)
    h_metrics = candidate_metrics(rows, "horizontal", h_summary)
    f_metrics = final_metrics(rows)
    fused_mean = float(f_metrics["support"])
    vh_agreement = float(f_metrics["vertical_horizontal_agreement"])
    source_agreement = float(f_metrics["internal_agreement"])
    final_dec = final_decision(fused_mean, direction)
    summary = {
        "target_source": target,
        "direction": direction,
        "decision_threshold": threshold,
        "focus_start_date": v_summary.get("focus_start_date") or h_summary.get("focus_start_date"),
        "focus_end_date": v_summary.get("focus_end_date") or h_summary.get("focus_end_date"),
        "focus_rows": len([r for r in rows if int(r["focus_window"]) == 1]),
        "vertical_metrics": v_metrics,
        "horizontal_metrics": h_metrics,
        "final_metrics": f_metrics,
        "vertical_source_mode": v_summary.get("source_mode", "analog_binary"),
        "horizontal_source_mode": h_summary.get("source_mode", "analog_binary"),
        "vertical_method_label": v_summary.get("method_label", "analog+binary"),
        "horizontal_method_label": h_summary.get("method_label", "analog+binary"),
        "vertical_validation_quality": v_quality,
        "horizontal_validation_quality": h_quality,
        "final_validation_metrics": aggregate_validation_metrics(v_summary, h_summary),
        "conflict_policy": (
            "If vertical and horizontal decisions conflict, the side with better "
            "validation quality is weighted more strongly; near ties keep the "
            "agreement/penalty fusion."
        ),
        "vertical_decision": final_decision(float(v_metrics["support"]), direction),
        "horizontal_decision": final_decision(float(h_metrics["support"]), direction),
        "final_decision": final_dec,
        "final_estimated_value_mean": mean([float(r["final_estimated_value"]) for r in selected]),
        "final_probability_mean": fused_mean,
        "confidence": confidence_label(fused_mean, vh_agreement, source_agreement),
        "vertical_json": str(args.vertical_json),
        "horizontal_json": str(args.horizontal_json),
        "fusion_formula": (
            "final_probability = 0.50*mean(vertical,horizontal) + "
            "0.25*min(vertical,horizontal) + 0.25*(1-abs(vertical-horizontal))"
        ),
        "note": (
            "This fuses the already-fused analog/binary localization signals from vertical "
            "and horizontal auto-clip masters. It rewards agreement between the two master "
            "construction policies."
        ),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_csv = args.output_dir / f"{args.output_prefix}.csv"
    out_json = args.output_dir / f"{args.output_prefix}.json"
    out_png = args.output_dir / f"{args.output_prefix}.png"
    out_lineage = args.output_dir / f"{args.output_prefix}__lineage.png"
    out_md = args.output_dir / f"{args.output_prefix}.md"
    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "date", "vertical_estimated_value", "horizontal_estimated_value",
                "final_estimated_value", "vertical_fused_probability",
                "horizontal_fused_probability", "final_probability",
                "vertical_decision", "horizontal_decision", "final_decision",
                "vertical_horizontal_agreement", "conflict_resolution",
                "combined_internal_agreement",
                "focus_window",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_main_png(out_png, rows, summary, args.title)
    write_lineage_png(out_lineage, summary, args.title + " lineage")
    sign = "<=" if direction == "below" else ">="
    out_md.write_text(
        f"# {args.title}\n\n"
        "Experimental final localization fusion across vertical and horizontal auto-clip masters.\n\n"
        f"- target: `{target}`\n"
        f"- condition: `{target} {sign} {threshold}`\n"
        f"- focus window: `{summary['focus_start_date']}` -> `{summary['focus_end_date']}`\n"
        f"- vertical support: `{v_metrics['support']}`\n"
        f"- horizontal support: `{h_metrics['support']}`\n"
        f"- final support: `{summary['final_probability_mean']}`\n"
        f"- final estimated value mean: `{summary['final_estimated_value_mean']}`\n"
        f"- vertical/horizontal agreement: `{f_metrics['vertical_horizontal_agreement']}`\n"
        f"- vertical validation quality: `{v_quality}`\n"
        f"- horizontal validation quality: `{h_quality}`\n"
        f"- conflict policy: `{summary['conflict_policy']}`\n"
        f"- final decision: **{final_dec}**\n"
        f"- confidence: **{summary['confidence']}**\n\n"
        f"Formula: `{summary['fusion_formula']}`.\n\n"
        "Point semantics: every forecast date is the START of its forecast window.\n",
    )
    print(f"CSV:     {out_csv}")
    print(f"JSON:    {out_json}")
    print(f"PNG:     {out_png}")
    print(f"LINEAGE: {out_lineage}")
    print(f"MD:      {out_md}")


if __name__ == "__main__":
    main()
