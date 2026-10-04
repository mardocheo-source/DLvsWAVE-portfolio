#!/usr/bin/env python3
"""Build a post-hybrid-style lineage report for vertical vs horizontal KAN runs.

This is intentionally a thin adapter around post_hybrid_artifacts.py: the
existing post-hybrid visualizer already knows how to plot candidate A
validation, candidate B validation, the fused validation, and the lineage
metric diagram. Here candidate A is the best vertical-auto-clip KAN artifact
and candidate B is the best horizontal-auto-clip KAN artifact.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _float_value(value: Any, default: float = float("-inf")) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _index_csv_from_run(path: str) -> Path:
    p = Path(path)
    if p.is_file():
        return p
    direct = p / "best_trials_index.csv"
    if direct.exists():
        return direct
    matches = sorted(p.glob("pulsar_train*_best_trials_*/best_trials_index.csv"))
    if matches:
        return matches[-1]
    raise FileNotFoundError(f"best_trials_index.csv not found under {path}")


def _json_from_row(row: dict[str, str]) -> str | None:
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


def _candidate_rows(index_csv: Path, *, require_kan: bool) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with index_csv.open(newline="") as f:
        for row in csv.DictReader(f):
            json_path = _json_from_row(row)
            if not json_path:
                continue
            if _truthy(row.get("inverted_twin")):
                continue
            bank = str(row.get("bank") or "")
            readout = str(row.get("readout") or "")
            if "__INV" in bank or "__INV" in readout:
                continue
            if require_kan and "kan" not in (bank + " " + readout).lower():
                continue
            if not row.get("validation_combined_csv") or not os.path.exists(row["validation_combined_csv"]):
                continue
            if not row.get("forecast_csv") or not os.path.exists(row["forecast_csv"]):
                continue
            rows.append(row)
    rows.sort(
        key=lambda r: (
            _float_value(r.get("overall")),
            _float_value(r.get("event_f1")),
            _float_value(r.get("event_bal_acc")),
            _float_value(r.get("event_recall")),
        ),
        reverse=True,
    )
    return rows


def _select_candidate(index_or_run: str, *, rank: int, require_kan: bool) -> tuple[Path, dict[str, str]]:
    index_csv = _index_csv_from_run(index_or_run)
    rows = _candidate_rows(index_csv, require_kan=require_kan)
    if not rows:
        kind = "KAN " if require_kan else ""
        raise RuntimeError(f"No usable {kind}artifact found in {index_csv}")
    idx = max(0, int(rank) - 1)
    if idx >= len(rows):
        raise RuntimeError(f"Requested rank {rank}, but only {len(rows)} candidates found in {index_csv}")
    return index_csv, rows[idx]


def _final_evaluation_json_from_run(path: str) -> Path | None:
    p = Path(path)
    if p.is_file() and p.name.endswith("__final_evaluation.json"):
        return p
    if p.is_file():
        p = p.parent
    direct = list(p.glob("*/**/*__final_evaluation.json"))
    if not direct:
        direct = list(p.glob("**/*__final_evaluation.json"))
    direct = sorted({x.resolve() for x in direct})
    return direct[-1] if direct else None


def _load_manifest_summary(path: str) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    try:
        with p.open() as f:
            manifest = json.load(f)
    except Exception:
        return {}
    body_names = []
    for item in manifest.get("body_specs") or []:
        name = item.get("body_name")
        if name:
            body_names.append(str(name))
    skipped = []
    for item in manifest.get("skipped_body_specs") or []:
        name = item.get("body_name")
        reason = item.get("error_type") or item.get("reason")
        if name:
            skipped.append(f"{name}:{reason}" if reason else str(name))
    auto_clip = manifest.get("auto_clip") or {}
    return {
        "auto_clip_mode": auto_clip.get("mode") or manifest.get("auto_clip_mode"),
        "effective_start": auto_clip.get("effective_start_date") or manifest.get("start_date"),
        "first_period_start": manifest.get("first_period_start") or manifest.get("start_date"),
        "last_period_start": manifest.get("last_period_start") or manifest.get("end_date"),
        "step_days": manifest.get("step_days"),
        "period_count": manifest.get("period_count"),
        "body_names": body_names,
        "skipped": skipped,
    }


def _compact_body_line(body_names: list[str]) -> str:
    if not body_names:
        return "Bodies: n/a"
    aliases = {
        "jupiter_system_barycenter": "jupiter_bary",
        "saturn_system_barycenter": "saturn_bary",
        "uranus_system_barycenter": "uranus_bary",
        "neptune_system_barycenter": "neptune_bary",
        "pluto_system_barycenter": "pluto_bary",
    }
    compact = [aliases.get(name, name) for name in body_names]
    return f"Bodies ({len(compact)}): " + ", ".join(compact)


def _manifest_lineage_lines(variant: str, manifest_info: dict[str, Any]) -> list[str]:
    lines = []
    clip_mode = manifest_info.get("auto_clip_mode") or variant
    lines.append(f"Variant: {variant} autoclip | clip mode={clip_mode}")
    first = manifest_info.get("first_period_start") or "n/a"
    last = manifest_info.get("last_period_start") or "n/a"
    effective = manifest_info.get("effective_start")
    step = manifest_info.get("step_days")
    rows = manifest_info.get("period_count")
    date_line = f"Master rows: {first} -> {last}"
    extras = []
    if step:
        extras.append(f"step={step}d")
    if rows:
        extras.append(f"rows={rows}")
    if extras:
        date_line += " | " + " ".join(extras)
    lines.append(date_line)
    lines.append(_compact_body_line(list(manifest_info.get("body_names") or [])))
    if effective and effective != first:
        lines.append(f"Effective Horizons start: {effective}")
    skipped = list(manifest_info.get("skipped") or [])
    if skipped:
        lines.append("Skipped: " + "; ".join(skipped[:3]))
    return lines


def _decorate_final_json(
    path: Path, *, variant: str, run_label: str, out_dir: Path,
    validation_only: bool, manifest_info: dict[str, Any] | None = None,
) -> Path:
    with path.open() as f:
        final = json.load(f)
    outputs = final.get("outputs") or {}
    val = (outputs.get("validation") or {}).get("csv")
    fc = (outputs.get("forecast") or {}).get("csv")
    val_png = (outputs.get("validation") or {}).get("png")
    fc_png = (outputs.get("forecast") or {}).get("png")
    if not val or not os.path.exists(val):
        raise RuntimeError(f"{path}: final evaluation validation CSV not found")
    if not fc or not os.path.exists(fc):
        raise RuntimeError(f"{path}: final evaluation forecast CSV not found")

    source_trials = final.get("source_trials")
    rows = final.get("rows")
    manifest_lines = _manifest_lineage_lines(variant, manifest_info or {})
    meta = {
        "bank": f"{variant}_final_eval",
        "readout": "rank_weighted_kan_ensemble",
        "seed": "ensemble",
        "display_label": (
            f"{variant.upper()} autoclip | final rank-weighted KAN ensemble "
            f"| sources={source_trials}"
        ),
        "validation_combined_csv": val,
        "forecast_csv": "" if validation_only else fc,
        "test_png": val_png,
        "forecast_png": "" if validation_only else fc_png,
        "model_config": {
            "preprocessing": {"kind": "final_evaluation"},
            "metric_profile": final.get("metric_profile"),
            "shape_filter": final.get("shape_filter"),
            "negative_inertia": final.get("negative_inertia"),
        },
        "split_info": {
            "threshold": (final.get("metric_profile") or {}).get("threshold", 0.1),
            "prediction_threshold": (final.get("metric_profile") or {}).get("prediction_threshold", 0.5),
        },
        "component_lineage": [
            *manifest_lines,
            f"Final eval rows={rows} sources={source_trials}",
            f"Run: {run_label}",
        ],
        "vertical_horizontal_source": {
            "variant": variant,
            "run_label": run_label,
            "source_final_evaluation_json": str(path),
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{variant}_final_evaluation_candidate.json"
    with out_path.open("w") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
    return out_path


def _decorate_json(
    row: dict[str, str], *, variant: str, run_label: str, out_dir: Path,
    validation_only: bool, manifest_info: dict[str, Any] | None = None,
) -> Path:
    src = _json_from_row(row)
    if not src:
        raise RuntimeError(f"Missing artifact JSON for {variant}")
    with open(src) as f:
        meta = json.load(f)

    original_bank = str(meta.get("bank", row.get("bank", "")))
    original_readout = str(meta.get("readout", row.get("readout", "")))
    original_seed = str(meta.get("seed", row.get("seed", "")))
    score = row.get("overall") or meta.get("overall")
    label = (
        f"{variant.upper()} autoclip | "
        f"{original_bank} / {original_readout} / seed{original_seed}"
    )
    if score not in (None, ""):
        label += f" | overall={_float_value(score, 0.0):.3f}"

    lineage = [
        f"Original candidate: {original_bank} / {original_readout} / seed{original_seed}",
        *_manifest_lineage_lines(variant, manifest_info or {}),
        f"Run: {run_label}",
    ]
    previous = meta.get("component_lineage") or []
    meta["display_label"] = label
    meta["component_lineage"] = lineage + [str(x) for x in previous[:2]]
    if validation_only:
        meta["forecast_csv"] = ""
        meta["forecast_png"] = ""
    meta["vertical_horizontal_source"] = {
        "variant": variant,
        "run_label": run_label,
        "source_json": src,
        "source_index_row": row,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{variant}_selected_candidate.json"
    with out_path.open("w") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
    return out_path


def _metric_row(name: str, metrics: dict[str, Any]) -> dict[str, Any]:
    keys = ("f1", "recall", "precision", "bal_acc", "tp", "fp", "tn", "fn")
    row = {"source": name}
    for key in keys:
        row[key] = metrics.get(key)
    return row


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
        return out
    except Exception:
        return default


def _write_soft_validation_comparison_png(path: Path, validation_csv: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[warn] matplotlib unavailable, soft validation PNG skipped: {exc}")
        return

    with validation_csv.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return

    x = list(range(len(rows)))
    labels = [
        (r.get("date") or r.get("context") or str(r.get("row_index") or i))
        for i, r in enumerate(rows)
    ]
    actual = [_safe_float(r.get("actual_event")) for r in rows]
    a_score = [_safe_float(r.get("a_score")) for r in rows]
    b_score = [_safe_float(r.get("b_score")) for r in rows]
    soft = [0.5 * (a + b) for a, b in zip(a_score, b_score)]

    panels = [
        ("CANDIDATE A VALIDATION SIGNAL", "vertical normalized validation signal", a_score),
        ("CANDIDATE B VALIDATION SIGNAL", "horizontal normalized validation signal", b_score),
        (
            "VERTICAL/HORIZONTAL SOFT VALIDATION FUSION",
            "0.5 * vertical + 0.5 * horizontal; binary gate metrics are kept in summary JSON/quality CSV",
            soft,
        ),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(13.5, 10.5), sharex=True)
    if len(panels) == 1:
        axes = [axes]
    for ax, (title, subtitle, pred) in zip(axes, panels):
        ax.plot(x, actual, color="#2563eb", marker="o", linewidth=1.8, label="actual event")
        ax.plot(x, pred, color="#dc2626", marker="o", linewidth=1.5, label="normalized signal")
        ax.axhline(0.5, color="#6b7280", linestyle="--", linewidth=0.9, alpha=0.6)
        ax.set_title(title, loc="left", fontsize=12, pad=8)
        ax.text(0.0, 0.92, subtitle, transform=ax.transAxes, fontsize=8, color="#6b7280")
        ax.set_ylim(-0.08, 1.08)
        ax.grid(True, axis="y", alpha=0.22)
        ax.legend(loc="upper right", fontsize=8)
    step = max(1, len(labels) // 12)
    axes[-1].set_xticks(x[::step])
    axes[-1].set_xticklabels(labels[::step], rotation=90, fontsize=7)
    axes[-1].set_xlabel("validation row/date")
    fig.suptitle("Vertical vs Horizontal Validation Signal Lineage", fontsize=16, fontweight="bold", y=0.992)
    fig.tight_layout(rect=(0, 0, 1, 0.975))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _write_quality_reports(
    *,
    out_dir: Path,
    name: str,
    manifest: dict[str, Any],
    summary: dict[str, Any],
    comparison_report_dir: Path | None,
) -> dict[str, str]:
    paths = manifest["outputs"]
    fusion_metrics = summary.get("validation_metrics") or {}
    source_metrics = summary.get("source_validation_metrics") or {}
    rows = [
        _metric_row("fusion_vertical_horizontal", fusion_metrics),
        _metric_row("vertical_candidate", source_metrics.get("a") or {}),
        _metric_row("horizontal_candidate", source_metrics.get("b") or {}),
    ]
    payload = {
        "source_mode": manifest.get("source_mode_effective"),
        "validation_only": manifest.get("validation_only"),
        "forecast_authority": manifest.get("forecast_authority"),
        "fusion_validation_metrics": fusion_metrics,
        "vertical_validation_metrics": source_metrics.get("a") or {},
        "horizontal_validation_metrics": source_metrics.get("b") or {},
        "selected_sources": {
            "vertical": manifest.get("vertical_source_json"),
            "horizontal": manifest.get("horizontal_source_json"),
        },
        "paths": paths,
        "note": (
            "Validation quality metrics use the calibrated binary gate. "
            "The lineage comparison PNG shows soft normalized signal shape so it is not confused with the gate."
        ),
    }

    targets = [(out_dir, f"{name}__validation_quality")]
    if comparison_report_dir:
        targets.append((comparison_report_dir, "vertical_horizontal_validation_fusion_quality"))

    written: dict[str, str] = {}
    for target_dir, stem in targets:
        target_dir.mkdir(parents=True, exist_ok=True)
        json_path = target_dir / f"{stem}.json"
        csv_path = target_dir / f"{stem}.csv"
        md_path = target_dir / f"{stem}.md"
        txt_path = target_dir / f"{stem}_paths.txt"
        with json_path.open("w") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        with csv_path.open("w", newline="") as f:
            fieldnames = ["source", "f1", "recall", "precision", "bal_acc", "tp", "fp", "tn", "fn"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        with md_path.open("w") as f:
            f.write("# Vertical vs Horizontal Validation Fusion\n\n")
            f.write("Candidate A is the vertical auto-clip final validation candidate. ")
            f.write("Candidate B is the horizontal auto-clip final validation candidate.\n\n")
            f.write("Forecast authority: ")
            f.write(str(payload["forecast_authority"]))
            f.write("\n\n")
            f.write(
                "Note: validation metrics below use the calibrated binary gate; "
                "the lineage comparison PNG shows the soft normalized signal shape.\n\n"
            )
            f.write("## Validation Metrics\n\n")
            f.write("| source | f1 | recall | precision | bal_acc | tp | fp | tn | fn |\n")
            f.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")
            for row in rows:
                f.write(
                    f"| {row['source']} | {row.get('f1')} | {row.get('recall')} | "
                    f"{row.get('precision')} | {row.get('bal_acc')} | {row.get('tp')} | "
                    f"{row.get('fp')} | {row.get('tn')} | {row.get('fn')} |\n"
                )
            f.write("\n## Key Paths\n\n")
            for key, value in paths.items():
                if value in (None, ""):
                    continue
                f.write(f"- `{key}`: `{value}`\n")
        with txt_path.open("w") as f:
            for key, value in paths.items():
                if value in (None, ""):
                    continue
                f.write(f"{key}={value}\n")
        written[str(target_dir)] = str(json_path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create lineage PNGs comparing vertical vs horizontal KAN final candidates."
    )
    parser.add_argument("--vertical-run", required=True, help="Vertical run dir or best_trials_index.csv")
    parser.add_argument("--horizontal-run", required=True, help="Horizontal run dir or best_trials_index.csv")
    parser.add_argument("--vertical-manifest", default="", help="Vertical master manifest JSON")
    parser.add_argument("--horizontal-manifest", default="", help="Horizontal master manifest JSON")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--name", default="vertical_horizontal_kan_lineage")
    parser.add_argument("--candidate-rank", type=int, default=1, help="1=best by overall")
    parser.add_argument(
        "--source",
        default="final",
        choices=["final", "best"],
        help="final=use final_evaluation ensemble when available; best=use best single artifact",
    )
    parser.add_argument("--allow-non-kan", action="store_true")
    parser.add_argument("--logic", default="weighted", choices=["and", "or", "weighted", "sure", "conservative"])
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--normalize", default="auto", choices=["auto", "none", "binary", "minmax"])
    parser.add_argument("--score-column", default="predicted", choices=["predicted", "pred_recalibrated"])
    parser.add_argument("--calibrate", default="validation", choices=["none", "validation"])
    parser.add_argument("--calibrate-metric", default="f1", choices=["f1", "f05", "bal_acc", "precision", "recall"])
    parser.add_argument(
        "--include-posthybrid-forecast",
        action="store_true",
        help=(
            "Also draw the post_hybrid_artifacts forecast merge. By default this adapter is "
            "validation-only because vertical/horizontal forecast authority comes from "
            "forecast_common_window.py using fused signal strength."
        ),
    )
    parser.add_argument(
        "--comparison-report-dir",
        default="",
        help="Optional parent comparison dir where compact validation quality reports are also written.",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    selected_dir = out_dir / "selected_sources"
    require_kan = not args.allow_non_kan
    validation_only = not args.include_posthybrid_forecast
    vertical_manifest_info = _load_manifest_summary(args.vertical_manifest)
    horizontal_manifest_info = _load_manifest_summary(args.horizontal_manifest)

    v_index = h_index = None
    v_row = h_row = None
    v_final = _final_evaluation_json_from_run(args.vertical_run) if args.source == "final" else None
    h_final = _final_evaluation_json_from_run(args.horizontal_run) if args.source == "final" else None
    if v_final and h_final:
        vertical_json = _decorate_final_json(
            v_final, variant="vertical", run_label=str(v_final.parent.parent),
            out_dir=selected_dir, validation_only=validation_only,
            manifest_info=vertical_manifest_info,
        )
        horizontal_json = _decorate_final_json(
            h_final, variant="horizontal", run_label=str(h_final.parent.parent),
            out_dir=selected_dir, validation_only=validation_only,
            manifest_info=horizontal_manifest_info,
        )
    else:
        v_index, v_row = _select_candidate(args.vertical_run, rank=args.candidate_rank, require_kan=require_kan)
        h_index, h_row = _select_candidate(args.horizontal_run, rank=args.candidate_rank, require_kan=require_kan)
        vertical_json = _decorate_json(
            v_row, variant="vertical", run_label=str(v_index.parent),
            out_dir=selected_dir, validation_only=validation_only,
            manifest_info=vertical_manifest_info,
        )
        horizontal_json = _decorate_json(
            h_row, variant="horizontal", run_label=str(h_index.parent),
            out_dir=selected_dir, validation_only=validation_only,
            manifest_info=horizontal_manifest_info,
        )

    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent / "post_hybrid_artifacts.py"),
        "--a",
        str(vertical_json),
        "--b",
        str(horizontal_json),
        "--out-dir",
        str(out_dir),
        "--name",
        args.name,
        "--logic",
        args.logic,
        "--normalize",
        args.normalize,
        "--score-column",
        args.score_column,
        "--alpha",
        str(args.alpha),
        "--threshold",
        str(args.threshold),
        "--calibrate",
        args.calibrate,
        "--calibrate-metric",
        args.calibrate_metric,
    ]
    if validation_only:
        stale_forecast = out_dir / f"{args.name}__forecast.csv"
        if stale_forecast.exists():
            stale_forecast.unlink()
    subprocess.run(cmd, check=True)

    summary_path = out_dir / f"{args.name}__summary.json"
    validation_csv = out_dir / f"{args.name}__validation_combined.csv"
    lineage_comparison_png = out_dir / f"{args.name}__lineage_comparison.png"
    lineage_gate_comparison_png = out_dir / f"{args.name}__lineage_gate_comparison.png"
    if validation_only and lineage_comparison_png.exists():
        shutil.copy2(lineage_comparison_png, lineage_gate_comparison_png)
        _write_soft_validation_comparison_png(lineage_comparison_png, validation_csv)
    manifest = {
        "source_mode_requested": args.source,
        "source_mode_effective": "final" if v_final and h_final else "best",
        "validation_only": validation_only,
        "forecast_authority": (
            "forecast_common_window.py over vertical/horizontal fused signal strength"
            if validation_only else "post_hybrid_artifacts.py forecast merge"
        ),
        "vertical_index_csv": str(v_index) if v_index else None,
        "horizontal_index_csv": str(h_index) if h_index else None,
        "vertical_final_evaluation_json": str(v_final) if v_final else None,
        "horizontal_final_evaluation_json": str(h_final) if h_final else None,
        "vertical_manifest": args.vertical_manifest or None,
        "horizontal_manifest": args.horizontal_manifest or None,
        "vertical_manifest_summary": vertical_manifest_info,
        "horizontal_manifest_summary": horizontal_manifest_info,
        "vertical_selected_json": str(vertical_json),
        "horizontal_selected_json": str(horizontal_json),
        "vertical_source_json": _json_from_row(v_row) if v_row else str(v_final),
        "horizontal_source_json": _json_from_row(h_row) if h_row else str(h_final),
        "post_hybrid_command": cmd,
        "outputs": {
            "validation_csv": str(validation_csv),
            "forecast_csv": None if validation_only else str(out_dir / f"{args.name}__forecast.csv"),
            "combined_png": str(out_dir / f"{args.name}__combined.png"),
            "lineage_diagram_png": str(out_dir / f"{args.name}__lineage_diagram.png"),
            "lineage_comparison_png": str(lineage_comparison_png),
            "lineage_gate_comparison_png": str(lineage_gate_comparison_png) if validation_only else None,
            "summary_json": str(summary_path),
        },
    }
    summary = {}
    if summary_path.exists():
        with summary_path.open() as f:
            summary = json.load(f)
    quality_reports = _write_quality_reports(
        out_dir=out_dir,
        name=args.name,
        manifest=manifest,
        summary=summary,
        comparison_report_dir=Path(args.comparison_report_dir) if args.comparison_report_dir else None,
    )
    manifest["quality_reports"] = quality_reports
    manifest_path = out_dir / f"{args.name}__vertical_horizontal_manifest.json"
    with manifest_path.open("w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print(f"Source mode:          {manifest['source_mode_effective']}")
    print(f"Vertical candidate:   {manifest['vertical_source_json']}")
    print(f"Horizontal candidate: {manifest['horizontal_source_json']}")
    print(f"Validation quality:   {quality_reports.get(str(out_dir))}")
    if args.comparison_report_dir:
        print(f"Comparison quality:   {quality_reports.get(str(Path(args.comparison_report_dir)))}")
    print(f"Lineage manifest:     {manifest_path}")


if __name__ == "__main__":
    main()
