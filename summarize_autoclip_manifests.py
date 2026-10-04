#!/usr/bin/env python3
"""Write a compact Markdown explanation for vertical/horizontal auto-clip runs."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return json.load(f)


def table(rows: list[list[object]]) -> str:
    if not rows:
        return ""
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]
    out = []
    for idx, row in enumerate(rows):
        out.append("| " + " | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)) + " |")
        if idx == 0:
            out.append("| " + " | ".join("-" * widths[i] for i in range(len(row))) + " |")
    return "\n".join(out)


def grouped_clip_rows(items: list[dict[str, Any]]) -> list[list[object]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(lambda: {"bodies": [], "commands": [], "sample": ""})
    for item in items:
        key = (
            str(item.get("error_type") or item.get("reason") or "unknown"),
            str(item.get("kind") or ""),
            str(item.get("clip_date") or ""),
        )
        grouped[key]["bodies"].append(str(item.get("body_name") or "?"))
        grouped[key]["commands"].append(str(item.get("horizons_command") or "?"))
        grouped[key]["sample"] = grouped[key]["sample"] or str(item.get("error") or "")
    rows = [["error_type/reason", "kind", "clip_date", "bodies", "commands", "sample_error"]]
    for (etype, kind, clip_date), payload in sorted(grouped.items()):
        rows.append([
            etype,
            kind or "-",
            clip_date or "-",
            ", ".join(sorted(set(payload["bodies"]))),
            ", ".join(sorted(set(payload["commands"]))),
            payload["sample"][:160],
        ])
    return rows


def selected_bodies(manifest: dict[str, Any]) -> str:
    body_meta = manifest.get("body_specs") or manifest.get("body_ephemerides") or manifest.get("body_meta") or []
    names = []
    for item in body_meta:
        if isinstance(item, dict):
            names.append(str(item.get("body_name") or item.get("name") or item.get("horizons_command") or "?"))
    return ", ".join(names) if names else "(not listed)"


def best_common_window(path: Path | None) -> dict[str, str] | None:
    if not path or not path.exists():
        return None
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    def key(row: dict[str, str]) -> tuple[float, float, float]:
        return (
            float(row.get("consensus_count") or 0),
            float(row.get("risk_mean") or 0),
            float(row.get("risk_max") or 0),
        )
    return max(rows, key=key)


def section(label: str, manifest: dict[str, Any]) -> str:
    ac = manifest.get("auto_clip") or {}
    global_clip = ac.get("global_date_clip") or {
        "requested_start_date": ac.get("requested_start_date"),
        "requested_end_date": ac.get("requested_end_date"),
        "effective_start_date": ac.get("effective_start_date"),
        "effective_end_date": ac.get("effective_end_date"),
    }
    parts = [f"## {label}"]
    parts.append("")
    parts.append(f"- mode: `{ac.get('mode', 'unknown')}`")
    parts.append(f"- requested range: `{global_clip.get('requested_start_date')}` -> `{global_clip.get('requested_end_date')}`")
    parts.append(f"- effective range: `{global_clip.get('effective_start_date')}` -> `{global_clip.get('effective_end_date')}`")
    parts.append(f"- policy: {ac.get('horizontal_policy', 'vertical removes failing bodies; horizontal clips temporal bounds')}")
    parts.append(f"- selected bodies after clipping: {selected_bodies(manifest)}")
    parts.append("")

    date_clips = ac.get("date_clips") or []
    body_clips = ac.get("body_clips") or []
    if date_clips:
        parts.append("### Date Clips")
        parts.append(table(grouped_clip_rows(date_clips)))
        parts.append("")
    else:
        parts.append("### Date Clips")
        parts.append("None.")
        parts.append("")

    if body_clips:
        parts.append("### Body Clips")
        parts.append(table(grouped_clip_rows(body_clips)))
        parts.append("")
    else:
        parts.append("### Body Clips")
        parts.append("None.")
        parts.append("")

    error_groups = ac.get("error_groups") or []
    if error_groups:
        rows = [["error_type", "kind", "clip_date", "body_count", "bodies"]]
        for group in error_groups:
            rows.append([
                group.get("error_type") or "-",
                group.get("kind") or "-",
                group.get("clip_date") or "-",
                group.get("body_count") or len(group.get("body_names") or []),
                ", ".join(str(x) for x in (group.get("body_names") or [])),
            ])
        parts.append("### Error Groups")
        parts.append(table(rows))
        parts.append("")
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vertical-manifest", required=True, type=Path)
    ap.add_argument("--horizontal-manifest", required=True, type=Path)
    ap.add_argument("--common-csv", type=Path)
    ap.add_argument("--output-md", required=True, type=Path)
    ap.add_argument("--title", default="Japan/Nankai Auto-Clip Comparison")
    args = ap.parse_args()

    vertical = load_json(args.vertical_manifest)
    horizontal = load_json(args.horizontal_manifest)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"# {args.title}", ""]
    lines.append("This report summarizes why each master was clipped before KAN-only short training.")
    lines.append("")
    lines.append(section("Vertical Auto-Clip Master", vertical))
    lines.append(section("Horizontal Auto-Clip Master", horizontal))

    best = best_common_window(args.common_csv)
    lines.append("## Forecast Comparison")
    lines.append("")
    if best:
        lines.append(
            "Best common detected window: "
            f"`{best.get('window_start')}` -> `{best.get('window_end')}` "
            f"(risk_mean={best.get('risk_mean')}, risk_max={best.get('risk_max')}, "
            f"consensus={best.get('consensus_count')}/{best.get('source_count')})."
        )
    else:
        lines.append("Common forecast CSV not available or empty.")
    lines.append("")
    lines.append("Point semantics: every forecast date is the START of its forecast window.")
    args.output_md.write_text("\n".join(lines) + "\n")
    print(f"Markdown report: {args.output_md}")


if __name__ == "__main__":
    main()
