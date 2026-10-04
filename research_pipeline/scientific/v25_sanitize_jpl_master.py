#!/usr/bin/env python3
"""Drop only non-finite JPL feature columns and audit retained body coverage."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


BODY = re.compile(r"^body:([^|]+)\|")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--report-json", required=True, type=Path)
    args = parser.parse_args()

    frame = pd.read_csv(args.input_csv, low_memory=False)
    feature_columns = [name for name in frame.columns if name.startswith("body:")]
    numeric = frame[feature_columns].apply(pd.to_numeric, errors="coerce")
    finite = np.isfinite(numeric.to_numpy(float))
    valid = finite.all(axis=0)
    dropped = [name for name, keep in zip(feature_columns, valid) if not keep]
    output = frame.drop(columns=dropped)
    retained = [name for name in feature_columns if name not in set(dropped)]
    input_bodies = {match.group(1) for name in feature_columns if (match := BODY.match(name))}

    counts: dict[str, int] = {}
    for name in retained:
        match = BODY.match(name)
        if match:
            counts[match.group(1)] = counts.get(match.group(1), 0) + 1

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output_csv, index=False)
    payload = {
        "status": "PASS" if retained and set(counts) == input_bodies and all(value > 0 for value in counts.values()) else "FAIL",
        "policy": "Only JPL columns containing at least one non-finite value are removed; bodies are retained and downstream feature ablation continues to treat their remaining fields equally.",
        "input": {"path": str(args.input_csv.resolve()), "sha256": sha256(args.input_csv), "rows": len(frame), "feature_columns": len(feature_columns)},
        "output": {"path": str(args.output_csv.resolve()), "sha256": sha256(args.output_csv), "rows": len(output), "feature_columns": len(retained)},
        "dropped_columns": dropped,
        "required_body_retained_feature_counts": counts,
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
