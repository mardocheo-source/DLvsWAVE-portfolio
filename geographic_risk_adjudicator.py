#!/usr/bin/env python3
"""Adjudicate target-zone risk from geographic counter-check outputs.

This script is intentionally downstream-only: it does not train models and does
not mutate forecast artifacts.  It reads a geographic counter-check report,
compares the target zone against optional no-history and proximity-counter
runs, and writes a compact risk reassessment.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import date
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Reassess target-zone forecast risk using proximity counter-checks.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--countercheck-report", help="Path to countercheck_report.json.")
    src.add_argument("--plan-json", help="Countercheck plan JSON; report is inferred as countercheck_report.json beside it.")
    ap.add_argument("--output-dir", default="", help="Defaults to the countercheck report directory.")
    ap.add_argument("--output-prefix", default="target_risk_adjudication")
    ap.add_argument("--counter-penalty-weight", type=float, default=0.70)
    ap.add_argument("--global-counter-penalty-weight", type=float, default=0.18)
    ap.add_argument("--history-bonus-weight", type=float, default=0.15)
    ap.add_argument("--no-history-disagreement-weight", type=float, default=0.12)
    ap.add_argument("--high-threshold", type=float, default=0.70)
    ap.add_argument("--elevated-threshold", type=float, default=0.55)
    ap.add_argument("--counter-contested-threshold", type=float, default=0.30)
    return ap.parse_args()


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def num(value: Any, default: float = 0.0) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return default
    return x if math.isfinite(x) else default


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def parse_day(value: Any) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def row_date_key(row: dict[str, Any]) -> str:
    return str(row.get("date") or row.get("selected_date") or "").strip()


def read_fusion_rows(variant: dict[str, Any]) -> list[dict[str, Any]]:
    fusion = variant.get("fusion") or {}
    outputs = fusion.get("outputs") or {}
    csv_path = outputs.get("csv")
    if not csv_path:
        path = fusion.get("path")
        if path:
            csv_path = str(Path(path).with_suffix(".csv"))
    if csv_path and Path(csv_path).exists():
        with Path(csv_path).open(newline="") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            row["fused_score"] = num(row.get("fused_score"))
            row["consensus_fraction"] = num(row.get("consensus_fraction"))
        return rows
    peak = fusion.get("selected_peak") or {}
    if peak:
        return [peak]
    if fusion.get("selected_date"):
        return [{
            "date": fusion.get("selected_date"),
            "window_end": fusion.get("window_end"),
            "fused_score": num(fusion.get("fused_score")),
            "consensus_fraction": num(fusion.get("consensus_fraction")),
        }]
    return []


def quality(variant: dict[str, Any]) -> float:
    best = variant.get("best") or {}
    return clamp(num(best.get("best_overall"), 0.50))


def map_coverage(variant: dict[str, Any], main_events: float) -> float:
    event_count = num((variant.get("map") or {}).get("event_count"))
    if main_events <= 0:
        return 0.5
    return clamp(event_count / main_events)


def reliability(variant: dict[str, Any], main_events: float) -> float:
    # Validation quality carries most of the weight; event coverage prevents
    # sparse counter-zones from becoming overly dominant.
    return clamp(0.45 + 0.40 * quality(variant) + 0.15 * map_coverage(variant, main_events))


def score_strength(row: dict[str, Any], variant: dict[str, Any], main_events: float) -> float:
    fused = clamp(num(row.get("fused_score")))
    consensus = clamp(num(row.get("consensus_fraction"), 0.5))
    return clamp(fused * (0.55 + 0.45 * consensus) * reliability(variant, main_events))


def rows_by_date(variant: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row_date_key(row): row for row in read_fusion_rows(variant) if row_date_key(row)}


def infer_target_mode(report: dict[str, Any], main: dict[str, Any] | None) -> dict[str, Any]:
    plan = report.get("plan") or {}
    target = (main or {}).get("target_report") or {}
    source = str(target.get("binary_source_col") or target.get("target_col") or target.get("target_column") or "").lower()
    if source in {"latitude", "longitude", "depth"}:
        mode = "localization"
    elif source in {"lat", "lon"}:
        mode = "localization"
    elif "mag" in source:
        mode = "magnitude-detection"
    else:
        mode = "generic-target"
    return {
        "mode": mode,
        "target_column": target.get("target_col") or target.get("target_column"),
        "binary_source_column": target.get("binary_source_col"),
        "binary_operator": target.get("binary_operator"),
        "binary_threshold": target.get("binary_threshold") or plan.get("binary_threshold"),
        "target_zones": target.get("target_zones") or ",".join(plan.get("target_zones", [])),
        "row_filter": target.get("row_filter"),
        "out_of_region_mode": target.get("out_of_region_mode"),
    }


def verdict(score: float, pressure: float, args: argparse.Namespace) -> str:
    if score >= args.high_threshold and pressure < args.counter_contested_threshold:
        return "HIGH_TARGET_RISK"
    if score >= args.high_threshold:
        return "HIGH_BUT_GEOGRAPHICALLY_CONTESTED"
    if score >= args.elevated_threshold and pressure < args.counter_contested_threshold:
        return "ELEVATED_TARGET_RISK"
    if score >= args.elevated_threshold:
        return "ELEVATED_BUT_GEOGRAPHICALLY_CONTESTED"
    if pressure >= args.counter_contested_threshold:
        return "LOW_OR_COUNTER_DOMINATED"
    return "LOW_TARGET_RISK"


def selected_date(variant: dict[str, Any] | None) -> str:
    if not variant:
        return ""
    fusion = variant.get("fusion") or {}
    return str(fusion.get("selected_date") or "")


def make_adjudication(report: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    variants = report.get("variants") or report.get("summaries") or []
    main = next((v for v in variants if v.get("kind") == "main_history"), None)
    if main is None:
        main = next((v for v in variants if str(v.get("kind", "")).startswith("main")), None)
    nohist = next((v for v in variants if v.get("kind") == "main_no_history"), None)
    counters = [v for v in variants if str(v.get("kind", "")).startswith("counter")]
    if main is None:
        raise SystemExit("[risk] ERROR: no main target variant found in countercheck report.")

    main_events = num((main.get("map") or {}).get("event_count"), 1.0)
    main_rows = rows_by_date(main)
    nohist_rows = rows_by_date(nohist) if nohist else {}
    counter_rows = [(c, rows_by_date(c)) for c in counters]

    target_selected = selected_date(main)
    nohist_selected = selected_date(nohist)
    global_counter_peak = None
    global_counter_strength = 0.0
    for counter in counters:
        for row in read_fusion_rows(counter):
            s = score_strength(row, counter, main_events)
            if s > global_counter_strength:
                global_counter_strength = s
                global_counter_peak = {
                    "kind": counter.get("kind"),
                    "zones": counter.get("target_zones"),
                    "date": row_date_key(row),
                    "window_end": row.get("window_end"),
                    "fused_score": num(row.get("fused_score")),
                    "consensus_fraction": num(row.get("consensus_fraction")),
                    "strength": round(s, 6),
                }

    timeline: list[dict[str, Any]] = []
    for day_key in sorted(main_rows):
        row = main_rows[day_key]
        target_strength = score_strength(row, main, main_events)
        nohist_row = nohist_rows.get(day_key)
        nohist_strength = score_strength(nohist_row, nohist, main_events) if nohist_row and nohist else None

        max_counter = None
        max_counter_pressure = 0.0
        counter_details = []
        for counter, by_day in counter_rows:
            crow = by_day.get(day_key)
            if not crow:
                continue
            c_strength = score_strength(crow, counter, main_events)
            pressure = clamp(max(0.0, c_strength - 0.20))
            item = {
                "kind": counter.get("kind"),
                "zones": counter.get("target_zones"),
                "fused_score": round(num(crow.get("fused_score")), 6),
                "consensus_fraction": round(num(crow.get("consensus_fraction")), 6),
                "strength": round(c_strength, 6),
                "pressure": round(pressure, 6),
            }
            counter_details.append(item)
            if pressure > max_counter_pressure:
                max_counter_pressure = pressure
                max_counter = item

        history_bonus = 0.0
        nohist_disagreement = 0.0
        if nohist_strength is not None:
            history_bonus = clamp(target_strength - nohist_strength, -0.25, 0.25)
            if nohist_selected and nohist_selected != target_selected and nohist_strength > target_strength:
                nohist_disagreement = clamp(nohist_strength - target_strength)

        global_penalty = 0.0
        if global_counter_strength > target_strength:
            global_penalty = clamp(global_counter_strength - target_strength)

        adjusted = clamp(
            target_strength
            - args.counter_penalty_weight * max_counter_pressure
            - args.global_counter_penalty_weight * global_penalty
            - args.no_history_disagreement_weight * nohist_disagreement
            + args.history_bonus_weight * history_bonus
        )
        pressure_total = clamp(max_counter_pressure + 0.35 * global_penalty)
        timeline.append({
            "date": day_key,
            "window_end": row.get("window_end", ""),
            "target_fused_score": round(num(row.get("fused_score")), 6),
            "target_consensus": round(num(row.get("consensus_fraction")), 6),
            "target_strength": round(target_strength, 6),
            "no_history_strength": round(nohist_strength, 6) if nohist_strength is not None else "",
            "history_bonus": round(history_bonus, 6),
            "max_counter_pressure": round(max_counter_pressure, 6),
            "global_counter_penalty": round(global_penalty, 6),
            "adjusted_target_score": round(adjusted, 6),
            "verdict": verdict(adjusted, pressure_total, args),
            "strongest_same_date_counter": (max_counter or {}).get("kind", ""),
            "strongest_same_date_counter_zones": (max_counter or {}).get("zones", ""),
            "strongest_same_date_counter_strength": (max_counter or {}).get("strength", ""),
            "counter_details": counter_details,
        })

    best_row = max(timeline, key=lambda r: num(r.get("adjusted_target_score")), default={})
    selected_row = next((r for r in timeline if r.get("date") == target_selected), best_row)
    mode = infer_target_mode(report, main)
    result = {
        "source_report": report.get("path", ""),
        "target_mode": mode,
        "method": {
            "target_strength": "fused_score * consensus/reliability weighting",
            "same_date_counter_pressure": "strong proximity-counter rows on the same forecast date reduce target risk",
            "global_counter_penalty": "strongest proximity counter elsewhere reduces geographic specificity more lightly",
            "no_history_disagreement": "no-history dominance on a different selected peak reduces confidence",
        },
        "inputs": {
            "main_variant": main.get("kind"),
            "main_zones": main.get("target_zones"),
            "no_history_variant": nohist.get("kind") if nohist else None,
            "counter_count": len(counters),
            "available_variants": [v.get("kind") for v in variants],
        },
        "global_counter_peak": global_counter_peak,
        "target_selected_raw": {
            "date": target_selected,
            "window_end": (main.get("fusion") or {}).get("window_end"),
            "fused_score": (main.get("fusion") or {}).get("fused_score"),
            "consensus_fraction": (main.get("fusion") or {}).get("consensus_fraction"),
        },
        "target_selected_adjudicated": selected_row,
        "target_best_adjudicated": best_row,
        "timeline": timeline,
    }
    return result


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "date", "window_end", "target_fused_score", "target_consensus", "target_strength",
        "no_history_strength", "history_bonus", "max_counter_pressure", "global_counter_penalty",
        "adjusted_target_score", "verdict", "strongest_same_date_counter",
        "strongest_same_date_counter_zones", "strongest_same_date_counter_strength",
    ]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def write_md(path: Path, result: dict[str, Any], json_path: Path, csv_path: Path) -> None:
    mode = result["target_mode"]
    selected = result["target_selected_adjudicated"]
    best = result["target_best_adjudicated"]
    global_counter = result.get("global_counter_peak") or {}
    lines = [
        "# Target Risk Adjudication",
        "",
        "This is a downstream reassessment of the target-zone forecast after geographic counter-checks.",
        "",
        "## Final read",
        "",
        f"- Target mode: `{mode.get('mode')}`",
        f"- Target zones: `{mode.get('target_zones')}`",
        f"- Target source: `{mode.get('binary_source_column') or mode.get('target_column')}` `{mode.get('binary_operator') or ''}` `{mode.get('binary_threshold') or ''}`",
        f"- Raw selected target peak: `{result['target_selected_raw'].get('date')}` -> `{result['target_selected_raw'].get('window_end')}`, fused `{result['target_selected_raw'].get('fused_score')}`",
        f"- Adjudicated selected target score: `{selected.get('adjusted_target_score')}` / verdict `{selected.get('verdict')}`",
        f"- Best adjudicated target window: `{best.get('date')}` -> `{best.get('window_end')}`, score `{best.get('adjusted_target_score')}`, verdict `{best.get('verdict')}`",
        f"- Strongest global proximity counter: `{global_counter.get('kind', '')}` / `{global_counter.get('zones', '')}` at `{global_counter.get('date', '')}` -> `{global_counter.get('window_end', '')}`, strength `{global_counter.get('strength', '')}`",
        "",
        "## Timeline",
        "",
        "| date | window end | target fused | target strength | no-history strength | counter pressure | adjusted | verdict | strongest same-date counter |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result["timeline"]:
        lines.append(
            f"| {row.get('date')} | {row.get('window_end')} | {row.get('target_fused_score')} | "
            f"{row.get('target_strength')} | {row.get('no_history_strength')} | "
            f"{row.get('max_counter_pressure')} | {row.get('adjusted_target_score')} | "
            f"{row.get('verdict')} | {row.get('strongest_same_date_counter_zones')} |"
        )
    lines.extend([
        "",
        "## Interpretation rules",
        "",
        "- Same-date proximity pressure is treated as the strongest false-positive warning.",
        "- A stronger proximity counter at a different date still reduces geographic specificity, but with a lighter global penalty.",
        "- If no-history selects a different stronger peak, the history-based interpretation is marked less stable.",
        "- For magnitude targets this report reads as event-risk confidence. For latitude/longitude/depth targets it reads as localization confidence.",
        "",
        "## Files",
        "",
        f"- JSON: `{json_path}`",
        f"- CSV: `{csv_path}`",
        "",
    ])
    path.write_text("\n".join(lines))


def main() -> None:
    args = parse_args()
    report_path = Path(args.countercheck_report) if args.countercheck_report else Path(args.plan_json).with_name("countercheck_report.json")
    report = read_json(report_path)
    report["path"] = str(report_path)
    out_dir = Path(args.output_dir) if args.output_dir else report_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    result = make_adjudication(report, args)
    json_path = out_dir / f"{args.output_prefix}.json"
    csv_path = out_dir / f"{args.output_prefix}_timeline.csv"
    md_path = out_dir / f"{args.output_prefix}.md"
    result["outputs"] = {"json": str(json_path), "csv": str(csv_path), "md": str(md_path)}
    json_path.write_text(json.dumps(result, indent=2) + "\n")
    write_csv(csv_path, result["timeline"])
    write_md(md_path, result, json_path, csv_path)

    selected = result["target_selected_adjudicated"]
    best = result["target_best_adjudicated"]
    print(f"[risk] json: {json_path}")
    print(f"[risk] md:   {md_path}")
    print(f"[risk] csv:  {csv_path}")
    print(
        "[risk] selected target "
        f"{selected.get('date')}->{selected.get('window_end')} "
        f"adjusted={selected.get('adjusted_target_score')} verdict={selected.get('verdict')}"
    )
    print(
        "[risk] best target "
        f"{best.get('date')}->{best.get('window_end')} "
        f"adjusted={best.get('adjusted_target_score')} verdict={best.get('verdict')}"
    )


if __name__ == "__main__":
    main()
