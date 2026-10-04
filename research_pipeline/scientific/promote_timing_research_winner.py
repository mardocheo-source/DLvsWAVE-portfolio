#!/usr/bin/env python3
"""Promote the audited timing-research winner into its parent study."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True, type=Path)
    args = parser.parse_args()
    project = args.project_dir.expanduser().resolve()
    summary_path = (
        project
        / "08_extended_search/timing_models/timing_model_research_summary.json"
    )
    research = read_json(summary_path)
    winner = research["winner"]
    source = Path(winner["experiment_dir"]).expanduser().resolve()
    expected_root = (
        project / "08_extended_search/timing_models"
    ).resolve()
    if source.parent != expected_root:
        raise ValueError(f"Winner is outside the timing-research root: {source}")

    file_targets = [
        "01_inputs/timing_master.csv",
        "01_inputs/v4_native_safe_features.json",
        "02_master_search/compact_k_factor_selection.json",
        "02_master_search/master_search_selection.json",
        "02_audit/world_non_japan_hard_negatives.csv",
        "00_config/run_manifest.json",
        "00_config/completion.json",
    ]
    directory_targets = [
        "03_feature_research/timing",
        "04_models/timing",
        "05_ensemble/timing",
    ]
    copied_files: list[dict] = []
    for relative in file_targets:
        origin = source / relative
        if not origin.is_file():
            raise FileNotFoundError(origin)
        destination = project / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, destination)
        copied_files.append(
            {
                "path": relative,
                "sha256": sha256(destination),
                "bytes": destination.stat().st_size,
            }
        )
    for relative in directory_targets:
        origin = source / relative
        if not origin.is_dir():
            raise FileNotFoundError(origin)
        destination = project / relative
        shutil.copytree(origin, destination, dirs_exist_ok=True)
        for path in sorted(destination.rglob("*")):
            if path.is_file():
                copied_files.append(
                    {
                        "path": str(path.relative_to(project)),
                        "sha256": sha256(path),
                        "bytes": path.stat().st_size,
                    }
                )

    audit = {
        "schema": "v14.timing_research_winner_promotion.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection_summary": str(summary_path),
        "winner_name": winner["name"],
        "winner_source": str(source),
        "selection_tie_tolerance": research.get("selection_tie_tolerance"),
        "tie_break_rule": research.get("tie_break_rule"),
        "winner_metrics": winner,
        "copied_file_count": len(copied_files),
        "copied_files": copied_files,
    }
    audit_path = project / "02_audit/timing_model_promotion.json"
    audit_path.write_text(
        json.dumps(audit, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "winner": winner["name"],
        "copied_file_count": len(copied_files),
        "audit": str(audit_path),
    }, indent=2))


if __name__ == "__main__":
    main()
