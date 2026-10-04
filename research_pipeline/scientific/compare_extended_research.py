#!/usr/bin/env python3
"""Write a machine-readable baseline-versus-revised timing comparison."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True, type=Path)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    project = args.project_dir.expanduser().resolve()
    baseline_root = project / "08_extended_search/baseline_archive"
    before = load(
        baseline_root / "metric_specialist_fusion_before_extended_search.json"
    )
    after = load(
        project
        / "05_ensemble/timing/metric_specialist_fusion/metric_specialist_fusion_summary.json"
    )
    before_trial = before["selected_trial"]
    after_trial = after["selected_trial"]
    gate_pass = after["status"] == "PASS"
    master = load(
        project
        / "08_extended_search/master_screen/extended_master_search_summary.json"
    )
    models = load(
        project
        / "08_extended_search/timing_models/timing_model_research_summary.json"
    )
    payload = {
        "status": "COMPLETE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result_interpretation": (
            "timing validation improved materially and the configured internal "
            "quality/control gate passes; the output remains experimental and "
            "uncalibrated"
            if gate_pass
            else "timing validation improved materially, but the configured "
            "quality/control gate still fails; the output remains experimental "
            "and uncalibrated"
        ),
        "baseline": {
            "fusion_status": before["status"],
            "validation_mean": before_trial["validation_quality_mean"],
            "validation_worst": before_trial["validation_quality_worst"],
            "exact_peak_count": before_trial["exact_peak_count"],
        },
        "revised": {
            "fusion_status": after["status"],
            "validation_mean": after_trial["validation_quality_mean"],
            "validation_worst": after_trial["validation_quality_worst"],
            "exact_peak_count": after_trial["exact_peak_count"],
            "false_positive_quality_mean": after_trial.get(
                "false_positive_quality_mean"
            ),
            "false_positive_quality_worst": after_trial.get(
                "false_positive_quality_worst"
            ),
            "hard_negative_below_event_count": after_trial.get(
                "hard_negative_below_event_count"
            ),
        },
        "delta": {
            "validation_mean": (
                after_trial["validation_quality_mean"]
                - before_trial["validation_quality_mean"]
            ),
            "validation_worst": (
                after_trial["validation_quality_worst"]
                - before_trial["validation_quality_worst"]
            ),
            "exact_peak_count": (
                after_trial["exact_peak_count"] - before_trial["exact_peak_count"]
            ),
        },
        "master_screen": {
            "candidate_count": master["candidate_count"],
            "winner": master["winner"],
            "non_japan_negatives_removed": False,
            "frozen_validation_controls": master["frozen_validation_controls"],
        },
        "model_search": {
            "experiment_count": models["experiment_count"],
            "winner": models["winner"],
        },
    }
    output = args.output_json or project / "08_extended_search/final_research_comparison.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(payload["delta"], indent=2))


if __name__ == "__main__":
    main()
