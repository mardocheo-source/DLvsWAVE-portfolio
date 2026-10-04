#!/usr/bin/env python3
"""Build a reduced master CSV from a one-shot mutual-information feature pass."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.feature_selection import mutual_info_classif

from benchmark import resolve_target_window_indices
from tasks import load_csv_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select a stable feature list with mutual information and write a reduced master CSV."
    )
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--ranking-csv", required=True)
    parser.add_argument("--manifest-json", required=True)
    parser.add_argument("--report-md", required=True)
    parser.add_argument("--target-col", required=True)
    parser.add_argument("--skip-cols-list", default="")
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--k-best", type=int, default=None)
    parser.add_argument("--percentile", type=float, default=None)
    parser.add_argument("--min-features", type=int, default=0)
    parser.add_argument("--max-features", type=int, default=0)
    parser.add_argument("--target-threshold", type=float, default=None)
    parser.add_argument("--target-event-count", type=int, default=0)
    parser.add_argument("--target-pre-records", type=int, default=0)
    parser.add_argument("--target-post-records", type=int, default=0)
    parser.add_argument("--isolated-event-windows", action="store_true")
    return parser.parse_args()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV without header: {path}")
        return list(reader.fieldnames), list(reader)


def write_projected_csv(path: Path, header: list[str], rows: list[dict[str, str]], keep: set[str]) -> list[str]:
    projected_header = [col for col in header if col in keep]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=projected_header)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in projected_header})
    return projected_header


def select_features(args: argparse.Namespace) -> dict:
    input_csv = Path(args.input_csv)
    meta = load_csv_dataset(input_csv, target_cols_list=args.target_col, skip_cols_list=args.skip_cols_list)
    X = np.asarray(meta["X"], dtype=float)
    y = np.asarray(meta["y"], dtype=float)
    feature_cols = list(meta["feature_cols"])

    window_cfg = None
    if args.target_threshold is not None and args.target_event_count > 0:
        window_cfg = {
            "threshold": args.target_threshold,
            "event_count": args.target_event_count,
            "pre_records": args.target_pre_records,
            "post_records": args.target_post_records,
            "isolated_windows": bool(args.isolated_event_windows),
        }
    resolved_window = resolve_target_window_indices(
        y, window_cfg, context_datetimes=meta.get("context_datetimes")
    ) if window_cfg else None
    if resolved_window is not None:
        train_idx = np.asarray(resolved_window["train_idx"], dtype=int)
        split_info = resolved_window["info"]
        train_source = "target_window_train"
    else:
        train_idx = np.arange(len(y), dtype=int)
        split_info = None
        train_source = "all_rows"

    X_train = X[train_idx]
    y_train = y[train_idx]
    variances = np.var(X_train, axis=0)
    active_indices = np.flatnonzero(variances > 1e-6)
    constant_indices = np.flatnonzero(variances <= 1e-6)
    if active_indices.size == 0:
        active_indices = np.arange(X_train.shape[1], dtype=int)
        constant_indices = np.asarray([], dtype=int)

    scores = {int(i): 0.0 for i in range(len(feature_cols))}
    mi_scores = mutual_info_classif(
        X_train[:, active_indices],
        y_train,
        discrete_features=True,
        random_state=42,
    )
    for idx, score in zip(active_indices, mi_scores):
        scores[int(idx)] = float(score)
    for idx in constant_indices:
        scores[int(idx)] = 0.0

    sorted_active = sorted(active_indices.tolist(), key=lambda i: scores[int(i)], reverse=True)
    if args.k_best is not None and args.k_best > 0:
        selected = sorted_active[: args.k_best]
        selection_reason = "k_best"
    elif args.percentile is not None and args.percentile > 0.0:
        k = max(1, int(len(active_indices) * args.percentile))
        selected = sorted_active[:k]
        selection_reason = "percentile"
    elif args.threshold is not None:
        selected = [int(i) for i in active_indices if scores[int(i)] >= args.threshold]
        selection_reason = "threshold"
    else:
        selected = list(sorted_active)
        selection_reason = "all_active"

    if args.min_features and len(selected) < args.min_features:
        selected = sorted_active[: args.min_features]
        selection_reason += "+min_features"
    if args.max_features and len(selected) > args.max_features:
        selected = selected[: args.max_features]
        selection_reason += "+max_features"
    if not selected:
        selected = [int(sorted_active[0])]
        selection_reason += "+fallback_top1"

    selected_set = set(int(i) for i in selected)
    ranking_rows = []
    for rank, idx in enumerate(sorted(range(len(feature_cols)), key=lambda i: scores[i], reverse=True), start=1):
        ranking_rows.append(
            {
                "rank": rank,
                "selected": int(idx in selected_set),
                "mi": scores[idx],
                "variance": float(variances[idx]),
                "feature": feature_cols[idx],
            }
        )

    selected_features = [feature_cols[int(i)] for i in selected]
    return {
        "meta": meta,
        "train_source": train_source,
        "train_rows": int(train_idx.size),
        "split_info": split_info,
        "selection_reason": selection_reason,
        "feature_count_input": len(feature_cols),
        "selected_features": selected_features,
        "ranking_rows": ranking_rows,
        "mi_max": max(scores.values()) if scores else 0.0,
    }


def main() -> None:
    args = parse_args()
    input_csv = Path(args.input_csv)
    output_csv = Path(args.output_csv)
    ranking_csv = Path(args.ranking_csv)
    manifest_json = Path(args.manifest_json)
    report_md = Path(args.report_md)

    selected = select_features(args)
    header, rows = read_rows(input_csv)
    non_feature_keep = set(selected["meta"]["skip_cols"])
    non_feature_keep.add(selected["meta"]["target_col"])
    keep = non_feature_keep | set(selected["selected_features"])
    projected_header = write_projected_csv(output_csv, header, rows, keep)

    ranking_csv.parent.mkdir(parents=True, exist_ok=True)
    with ranking_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["rank", "selected", "mi", "variance", "feature"])
        writer.writeheader()
        writer.writerows(selected["ranking_rows"])

    manifest = {
        "input_csv": str(input_csv),
        "output_csv": str(output_csv),
        "ranking_csv": str(ranking_csv),
        "target_col": selected["meta"]["target_col"],
        "skip_cols": selected["meta"]["skip_cols"],
        "train_source": selected["train_source"],
        "train_rows": selected["train_rows"],
        "split_info": selected["split_info"],
        "selection": {
            "threshold": args.threshold,
            "k_best": args.k_best,
            "percentile": args.percentile,
            "min_features": args.min_features,
            "max_features": args.max_features,
            "reason": selected["selection_reason"],
            "input_feature_count": selected["feature_count_input"],
            "selected_feature_count": len(selected["selected_features"]),
            "mi_max": selected["mi_max"],
            "features": selected["selected_features"],
        },
        "projected_columns": projected_header,
    }
    manifest_json.parent.mkdir(parents=True, exist_ok=True)
    manifest_json.write_text(json.dumps(manifest, indent=2) + "\n")

    lines = [
        "# MI Feature Preselect",
        "",
        f"- Input: `{input_csv}`",
        f"- Output: `{output_csv}`",
        f"- Ranking: `{ranking_csv}`",
        f"- Target: `{selected['meta']['target_col']}`",
        f"- Train source: `{selected['train_source']}`",
        f"- Train rows: {selected['train_rows']}",
        f"- Input feature count: {selected['feature_count_input']}",
        f"- Selected feature count: {len(selected['selected_features'])}",
        f"- MI max: {selected['mi_max']:.6f}",
        f"- Selection reason: `{selected['selection_reason']}`",
        "",
        "## Selected Features",
        "",
        "| rank | MI | feature |",
        "|---:|---:|---|",
    ]
    selected_names = set(selected["selected_features"])
    selected_rank = 0
    for row in selected["ranking_rows"]:
        if row["feature"] not in selected_names:
            continue
        selected_rank += 1
        lines.append(f"| {selected_rank} | {float(row['mi']):.6f} | `{row['feature']}` |")
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text("\n".join(lines) + "\n")

    print(
        "[feature-preselect]"
        f" selected={len(selected['selected_features'])}/{selected['feature_count_input']}"
        f" mi_max={selected['mi_max']:.6f}"
        f" output={output_csv}"
    )
    print(f"[feature-preselect] ranking={ranking_csv}")
    print(f"[feature-preselect] manifest={manifest_json}")


if __name__ == "__main__":
    main()
