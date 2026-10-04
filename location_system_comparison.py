#!/usr/bin/env python3
"""Compare final localization systems, e.g. KAN-only vs LCS binary-only."""
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


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except Exception:
        return None


def metric_float(metrics: dict[str, object] | None, key: str) -> float | None:
    if not isinstance(metrics, dict):
        return None
    return optional_float(metrics.get(key))


def validation_metrics(summary: dict[str, object]) -> dict[str, float | None]:
    raw = summary.get("final_validation_metrics")
    if not isinstance(raw, dict):
        raw = summary.get("validation_metrics")
    if not isinstance(raw, dict):
        raw = {}
    out: dict[str, float | None] = {}
    for key in ("quality_score", "overall", "event_f1", "event_recall", "event_precision", "event_bal_acc"):
        out[key] = metric_float(raw, key)
    return out


def final_decision(probability: float, direction: str) -> str:
    positive = "below" if direction == "below" else "above"
    negative = "above" if direction == "below" else "below"
    return positive if probability >= 0.5 else negative


def system_stats(rows: list[dict[str, object]], key: str) -> dict[str, float]:
    selected = [r for r in rows if int(r.get("focus_window", 0) or 0) == 1] or rows
    values = [float(r[key]) for r in selected]
    support = float(mean(values) or 0.0)
    return {
        "support": support,
        "margin": abs(support - 0.5),
        "active_fraction": sum(1 for v in values if v >= 0.5) / max(len(values), 1),
    }


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
    kan = [float(r["kan_probability"]) for r in rows]
    lcs = [float(r["lcs_probability"]) for r in rows]
    consensus = [float(r["consensus_probability"]) for r in rows]
    focus_start = summary.get("focus_start_date")
    focus_end = summary.get("focus_end_date")
    fs = parse_dt(str(focus_start)) if focus_start else None
    fe = parse_dt(str(focus_end)) if focus_end else None
    threshold = optional_float(summary.get("decision_threshold"))

    # Keep the bar summary on an independent categorical x-axis; otherwise it
    # collapses the temporal panels into one vertical stack of points.
    fig, axes = plt.subplots(4, 1, figsize=(13, 11.5), sharex=False)
    ax = axes[0]
    ax.plot(dates, kan, marker="o", linewidth=1.8, color="#2563eb",
            label="KAN-only analog+binary system")
    ax.plot(dates, lcs, marker="o", linewidth=1.8, color="#7c3aed",
            label="LCS/LCS-hybrid binary-only system")
    ax.axhline(0.5, color="#111827", linestyle="--", linewidth=1.0,
               label="decision 0.500")
    if fs and fe:
        ax.axvspan(fs, fe, color="#fef3c7", alpha=0.5)
    ax.set_ylabel("support")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")

    ax = axes[1]
    ax.plot(dates, consensus, marker="o", linewidth=2.2, color="#15803d",
            label="cross-system consensus")
    ax.axhline(0.5, color="#111827", linestyle="--", linewidth=1.0,
               label="decision 0.500")
    if fs and fe:
        ax.axvspan(fs, fe, color="#dcfce7", alpha=0.45)
    ax.set_ylabel("consensus support")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")

    ax = axes[2]
    labels = ["quality", "overall", "F1", "recall", "precision", "BalAcc"]
    keys = ["quality_score", "overall", "event_f1", "event_recall", "event_precision", "event_bal_acc"]
    kan_val = summary["kan_validation_metrics"]
    lcs_val = summary["lcs_validation_metrics"]
    x = range(len(labels))
    ax.bar([i - 0.18 for i in x], [float(kan_val.get(k) or 0.0) for k in keys],
           width=0.34, color="#2563eb", label="KAN validation")
    ax.bar([i + 0.18 for i in x], [float(lcs_val.get(k) or 0.0) for k in keys],
           width=0.34, color="#7c3aed", label="LCS validation")
    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, 1.05)
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(loc="best")
    ax.set_ylabel("validation")

    ax = axes[3]
    labels = ["KAN-only", "LCS binary-only", "consensus"]
    support = [
        float(summary["kan_metrics"]["support"]),
        float(summary["lcs_metrics"]["support"]),
        float(summary["consensus_metrics"]["support"]),
    ]
    active = [
        float(summary["kan_metrics"]["active_fraction"]),
        float(summary["lcs_metrics"]["active_fraction"]),
        float(summary["consensus_metrics"]["active_fraction"]),
    ]
    x = range(len(labels))
    ax.bar([i - 0.18 for i in x], support, width=0.34,
           color="#60a5fa", label="focus support")
    ax.bar([i + 0.18 for i in x], active, width=0.34,
           color="#c4b5fd", label="focus active fraction")
    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, 1.05)
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(loc="best")
    ax.set_ylabel("summary metric")
    note = (
        "LCS/LCS-hybrid is binary-only here: it validates the threshold side, "
        "not an analog coordinate estimate."
    )
    if threshold is not None:
        note = f"{note} Threshold={threshold:.3f}."
    ax.text(0.01, -0.36, note, transform=ax.transAxes, fontsize=8.8,
            color="#374151", va="top")

    fig.suptitle(title, fontsize=14, fontweight="bold")
    for ax in axes[:2]:
        for label in ax.get_xticklabels():
            label.set_rotation(45)
            label.set_ha("right")
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kan-csv", required=True, type=Path)
    ap.add_argument("--kan-json", required=True, type=Path)
    ap.add_argument("--lcs-csv", required=True, type=Path)
    ap.add_argument("--lcs-json", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--output-prefix", default="kan_vs_lcs_localization_system_comparison")
    ap.add_argument("--title", default="KAN-only vs LCS binary-only localization comparison")
    args = ap.parse_args()

    kan_summary = json.loads(args.kan_json.read_text())
    lcs_summary = json.loads(args.lcs_json.read_text())
    kan_rows = {r["date"]: r for r in read_csv(args.kan_csv)}
    lcs_rows = {r["date"]: r for r in read_csv(args.lcs_csv)}
    common_dates = sorted(set(kan_rows) & set(lcs_rows), key=parse_dt)
    if not common_dates:
        raise SystemExit("No common dates between KAN and LCS final reports")

    direction = str(kan_summary.get("direction") or lcs_summary.get("direction") or "above")
    threshold = optional_float(kan_summary.get("decision_threshold"))
    if threshold is None:
        threshold = optional_float(lcs_summary.get("decision_threshold"))
    rows: list[dict[str, object]] = []
    for date in common_dates:
        k = kan_rows[date]
        l = lcs_rows[date]
        kp = float(k["final_probability"])
        lp = float(l["final_probability"])
        consensus = 0.45 * ((kp + lp) / 2.0) + 0.35 * min(kp, lp) + 0.20 * (1.0 - abs(kp - lp))
        consensus = max(0.0, min(1.0, consensus))
        rows.append({
            "date": date,
            "kan_probability": kp,
            "lcs_probability": lp,
            "consensus_probability": consensus,
            "kan_decision": k.get("final_decision") or final_decision(kp, direction),
            "lcs_decision": l.get("final_decision") or final_decision(lp, direction),
            "consensus_decision": final_decision(consensus, direction),
            "systems_agreement": "agree" if (kp >= 0.5) == (lp >= 0.5) else "conflict",
            "focus_window": int(k.get("focus_window", "0") or 0) or int(l.get("focus_window", "0") or 0),
        })

    selected = [r for r in rows if int(r["focus_window"]) == 1] or rows
    agreement_fraction = sum(1 for r in selected if r["systems_agreement"] == "agree") / max(len(selected), 1)
    summary = {
        "target_source": kan_summary.get("target_source") or lcs_summary.get("target_source"),
        "direction": direction,
        "decision_threshold": threshold,
        "focus_start_date": kan_summary.get("focus_start_date") or lcs_summary.get("focus_start_date"),
        "focus_end_date": kan_summary.get("focus_end_date") or lcs_summary.get("focus_end_date"),
        "focus_rows": len([r for r in rows if int(r["focus_window"]) == 1]),
        "kan_metrics": system_stats(rows, "kan_probability"),
        "lcs_metrics": system_stats(rows, "lcs_probability"),
        "consensus_metrics": system_stats(rows, "consensus_probability"),
        "kan_validation_metrics": validation_metrics(kan_summary),
        "lcs_validation_metrics": validation_metrics(lcs_summary),
        "systems_agreement_fraction": agreement_fraction,
        "final_decision": final_decision(
            float(mean([float(r["consensus_probability"]) for r in selected]) or 0.0),
            direction,
        ),
        "kan_json": str(args.kan_json),
        "lcs_json": str(args.lcs_json),
        "fusion_formula": (
            "consensus = 0.45*mean(KAN,LCS) + 0.35*min(KAN,LCS) + "
            "0.20*(1-abs(KAN-LCS))"
        ),
        "method_note": (
            "KAN-only uses the analog+binary localization fusion. "
            "LCS/LCS-hybrid is binary-only/unary here because LCS does not "
            "estimate a continuous coordinate in this pipeline."
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
                "date", "kan_probability", "lcs_probability",
                "consensus_probability", "kan_decision", "lcs_decision",
                "consensus_decision", "systems_agreement", "focus_window",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_png(out_png, rows, summary, args.title)
    out_md.write_text(
        f"# {args.title}\n\n"
        f"- target: `{summary['target_source']}`\n"
        f"- threshold: `{summary['decision_threshold']}`\n"
        f"- focus window: `{summary['focus_start_date']}` -> `{summary['focus_end_date']}`\n"
        f"- KAN-only support: `{summary['kan_metrics']['support']}`\n"
        f"- LCS binary-only support: `{summary['lcs_metrics']['support']}`\n"
        f"- consensus support: `{summary['consensus_metrics']['support']}`\n"
        f"- KAN validation metrics: `{summary['kan_validation_metrics']}`\n"
        f"- LCS validation metrics: `{summary['lcs_validation_metrics']}`\n"
        f"- systems agreement: `{summary['systems_agreement_fraction']}`\n"
        f"- final decision: **{summary['final_decision']}**\n\n"
        f"Formula: `{summary['fusion_formula']}`.\n\n"
        f"{summary['method_note']}\n",
    )
    print(f"CSV:  {out_csv}")
    print(f"JSON: {out_json}")
    print(f"PNG:  {out_png}")
    print(f"MD:   {out_md}")


if __name__ == "__main__":
    main()
