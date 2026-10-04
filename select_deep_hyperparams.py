#!/usr/bin/env python3
"""Lightweight DeepNet hyperparameter pretest for CSV event forecasts."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from benchmark import resolve_target_window_indices
from deep_nets import DeepConfig, DeepNet
from tasks import load_csv_dataset


def parse_seeds(text: str) -> list[int]:
    text = str(text or "").strip()
    if not text:
        return [0]
    out = []
    for part in text.split(","):
        part = part.strip()
        if part:
            out.append(int(part))
    return out or [0]


def event_metrics(y_true, y_pred, threshold: float) -> dict:
    y_true = np.asarray(y_true, dtype=float).reshape(-1)
    y_pred = np.asarray(y_pred, dtype=float).reshape(-1)
    yt = y_true >= threshold
    yp = y_pred >= threshold
    tp = float(np.sum(yt & yp))
    tn = float(np.sum((~yt) & (~yp)))
    fp = float(np.sum((~yt) & yp))
    fn = float(np.sum(yt & (~yp)))
    precision = tp / max(tp + fp, 1e-12)
    recall = tp / max(tp + fn, 1e-12)
    specificity = tn / max(tn + fp, 1e-12)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-12)
    bal = 0.5 * (recall + specificity)
    score = f1 * bal if np.any(yt) else bal
    return {
        "score": float(score),
        "f1": float(f1),
        "precision": float(precision),
        "recall": float(recall),
        "specificity": float(specificity),
        "bal_acc": float(bal),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def candidate_configs(pretest_epochs: int, full_epochs: int) -> list[dict]:
    raw = [
        ("hp_tiny_relu", [16], "relu", 0.0, False, 64, 1e-3, 1e-4),
        ("hp_small_relu", [32, 16], "relu", 0.0, False, 64, 1e-3, 1e-4),
        ("hp_small_gelu", [32, 16], "gelu", 0.0, False, 64, 7e-4, 1e-4),
        ("hp_medium_gelu", [64, 32], "gelu", 0.05, False, 64, 7e-4, 1e-4),
        ("hp_medium_silu", [64, 32], "silu", 0.05, False, 64, 7e-4, 1e-4),
        ("hp_wide_gelu", [128, 64], "gelu", 0.10, False, 64, 5e-4, 2e-4),
        ("hp_wide_bn", [128, 64], "gelu", 0.05, True, 64, 5e-4, 2e-4),
        ("hp_deep_gelu", [128, 128, 64, 32], "gelu", 0.10, False, 64, 5e-4, 2e-4),
        ("hp_tanh_small", [32, 16], "tanh", 0.0, False, 64, 7e-4, 1e-4),
        ("hp_auto_gelu", None, "gelu", 0.05, False, 64, 7e-4, 1e-4),
    ]
    out = []
    for name, hidden, activation, dropout, batch_norm, batch_size, lr, wd in raw:
        out.append(
            {
                "name": name,
                "hidden_sizes": hidden,
                "activation": activation,
                "dropout": dropout,
                "batch_norm": batch_norm,
                "batch_size": batch_size,
                "lr": lr,
                "weight_decay": wd,
                "pretest_epochs": pretest_epochs,
                "full_epochs": full_epochs,
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-csv", required=True)
    ap.add_argument("--output-csv", required=True)
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--preset-json", required=True)
    ap.add_argument("--target-col", default="target")
    ap.add_argument("--skip-cols-list", default="date,mag,depth,latitude,longitude")
    ap.add_argument("--target-threshold", type=float, default=0.5)
    ap.add_argument("--target-event-count", type=int, default=2)
    ap.add_argument("--target-pre-records", type=int, default=6)
    ap.add_argument("--target-post-records", type=int, default=6)
    ap.add_argument("--isolated-event-windows", action="store_true")
    ap.add_argument("--seeds", default="3")
    ap.add_argument("--top-n", type=int, default=5)
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda", "xpu", "auto"])
    ap.add_argument("--pretest-epochs", type=int, default=80)
    ap.add_argument("--full-epochs", type=int, default=240)
    args = ap.parse_args()

    meta = load_csv_dataset(args.input_csv, target_cols_list=args.target_col, skip_cols_list=args.skip_cols_list)
    X = np.asarray(meta["X"], dtype=float)
    y = np.asarray(meta["y"], dtype=float).reshape(-1)
    split = resolve_target_window_indices(
        y,
        {
            "threshold": args.target_threshold,
            "event_count": args.target_event_count,
            "event_start": None,
            "pre_records": args.target_pre_records,
            "post_records": args.target_post_records,
            "isolated_windows": args.isolated_event_windows,
            "allow_train_after_test": False,
            "time_series": "auto",
        },
        context_datetimes=meta.get("context_datetimes"),
    )
    if split is None:
        raise SystemExit("target window could not be resolved")
    train_idx = np.asarray(split["train_idx"], dtype=int)
    test_idx = np.asarray(split["test_idx"], dtype=int)
    X_train, y_train = X[train_idx], y[train_idx]
    X_test, y_test = X[test_idx], y[test_idx]

    rows = []
    seeds = parse_seeds(args.seeds)
    for cand in candidate_configs(args.pretest_epochs, args.full_epochs):
        seed_scores = []
        for seed in seeds:
            cfg = DeepConfig(
                hidden_sizes=cand["hidden_sizes"],
                activation=cand["activation"],
                dropout=float(cand["dropout"]),
                batch_norm=bool(cand["batch_norm"]),
                epochs=int(cand["pretest_epochs"]),
                batch_size=int(cand["batch_size"]),
                lr=float(cand["lr"]),
                weight_decay=float(cand["weight_decay"]),
                early_stop_patience=15,
                final_retrain_full_train=False,
                scale_features=True,
                validation_metric="event_composite",
                validation_threshold=args.target_threshold,
                target_window_threshold=args.target_threshold,
                target_window_event_count=args.target_event_count,
                target_window_pre_records=args.target_pre_records,
                target_window_post_records=args.target_post_records,
                target_window_isolated_windows=args.isolated_event_windows,
                device=args.device,
                seed=int(seed),
            )
            model = DeepNet(cfg=cfg)
            model.fit(X_train, y_train)
            pred = model.predict(X_test)
            m = event_metrics(y_test, pred, args.target_threshold)
            seed_scores.append(m)
        score = float(np.mean([m["score"] for m in seed_scores]))
        row = {
            **cand,
            "score": score,
            "f1": float(np.mean([m["f1"] for m in seed_scores])),
            "bal_acc": float(np.mean([m["bal_acc"] for m in seed_scores])),
            "precision": float(np.mean([m["precision"] for m in seed_scores])),
            "recall": float(np.mean([m["recall"] for m in seed_scores])),
            "seed_count": len(seeds),
        }
        rows.append(row)

    rows.sort(key=lambda r: (r["score"], r["f1"], r["bal_acc"]), reverse=True)
    for i, row in enumerate(rows, 1):
        row["rank"] = i
        row["selected"] = 1 if i <= args.top_n else 0

    out_csv = Path(args.output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "rank", "selected", "name", "score", "f1", "bal_acc", "precision", "recall",
        "hidden_sizes", "activation", "dropout", "batch_norm", "batch_size", "lr",
        "weight_decay", "pretest_epochs", "full_epochs", "seed_count",
    ]
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            item = dict(row)
            item["hidden_sizes"] = "" if item["hidden_sizes"] is None else ",".join(map(str, item["hidden_sizes"]))
            w.writerow({k: item.get(k, "") for k in fields})

    selected = rows[: args.top_n]
    presets = []
    for i, row in enumerate(selected, 1):
        cfg = DeepConfig(
            hidden_sizes=row["hidden_sizes"],
            activation=row["activation"],
            dropout=float(row["dropout"]),
            batch_norm=bool(row["batch_norm"]),
            epochs=int(row["full_epochs"]),
            batch_size=int(row["batch_size"]),
            lr=float(row["lr"]),
            weight_decay=float(row["weight_decay"]),
            early_stop_patience=25,
            final_retrain_full_train=True,
        )
        preset = asdict(cfg)
        preset["name"] = f"hpt{i}_{row['name']}"
        preset["source_score"] = row["score"]
        presets.append(preset)

    payload = {
        "input_csv": args.input_csv,
        "target_col": args.target_col,
        "split_info": split.get("info", {}),
        "candidate_count": len(rows),
        "selected_count": len(presets),
        "ranking_csv": str(out_csv),
        "preset_json": args.preset_json,
        "rows": rows,
    }
    Path(args.output_json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    Path(args.preset_json).write_text(json.dumps({"presets": presets}, indent=2), encoding="utf-8")
    print(f"[hyper-pretest] selected={len(presets)}/{len(rows)} presets={args.preset_json}")
    print(f"[hyper-pretest] ranking={out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
