"""Post-run reproducibility and validation diagnostics for the binary M7.7 study.

This module never changes trained models or forecast values.  It audits a completed
run in place and writes machine-readable diagnostics plus a human-readable quality
certificate.  Scores from this audit remain retrospective diagnostics, not evidence
of operational earthquake-prediction skill.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


MODELS = ("kan", "deep_learning", "lcs")
STAGES = (("level1", "02_level1"), ("level2", "03_level2"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics(actual: pd.Series | np.ndarray, probability: pd.Series | np.ndarray, threshold: float) -> dict[str, Any]:
    y = np.asarray(actual, dtype=np.int8)
    p = np.clip(np.asarray(probability, dtype=float), 1e-7, 1.0 - 1e-7)
    predicted = p >= threshold
    tp = int(np.sum((y == 1) & predicted))
    fp = int(np.sum((y == 0) & predicted))
    fn = int(np.sum((y == 1) & ~predicted))
    tn = int(np.sum((y == 0) & ~predicted))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    brier = float(np.mean((p - y) ** 2))
    log_loss = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    prevalence = float(np.mean(y))
    climatology_brier = float(np.mean((prevalence - y) ** 2))

    # Average precision computed from the precision-recall staircase.
    order = np.argsort(-p, kind="stable")
    sorted_y = y[order]
    cumulative_tp = np.cumsum(sorted_y == 1)
    cumulative_fp = np.cumsum(sorted_y == 0)
    precision_curve = cumulative_tp / np.maximum(1, cumulative_tp + cumulative_fp)
    positive_count = max(1, int(np.sum(y == 1)))
    average_precision = float(np.sum(precision_curve[sorted_y == 1]) / positive_count)

    # Rank-based ROC AUC with tie-aware average ranks.
    ranks = pd.Series(p).rank(method="average").to_numpy()
    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))
    auc = 0.5
    if n_pos and n_neg:
        auc = float((np.sum(ranks[y == 1]) - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))

    ece = 0.0
    bin_ids = np.minimum((p * 10).astype(int), 9)
    for index in range(10):
        mask = bin_ids == index
        if np.any(mask):
            ece += float(np.mean(mask)) * abs(float(np.mean(p[mask])) - float(np.mean(y[mask])))
    return {
        "sample_count": len(y),
        "positives": n_pos,
        "negatives": n_neg,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": auc,
        "pr_auc": average_precision,
        "brier": brier,
        "climatology_brier": climatology_brier,
        "brier_improvement": climatology_brier - brier,
        "log_loss": log_loss,
        "ece_10bin": ece,
        "threshold": threshold,
    }


def _validation_path(root: Path, stage_dir: str, model: str) -> Path:
    return root / stage_dir / f"study_{model}" / "best_output" / f"selected_validation_{model}.csv"


def _index_path(root: Path, stage_dir: str, model: str) -> Path:
    return root / stage_dir / f"study_{model}" / "best_output" / f"selected_validation_corridor_index_{model}.csv"


def _model_diagnostics(root: Path, threshold: float) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    shift_rows: list[dict[str, Any]] = []
    global_index = root / "01_data" / "validation_corridor_index.csv"

    for stage, stage_dir in STAGES:
        for model in MODELS:
            validation_path = _validation_path(root, stage_dir, model)
            if not validation_path.exists():
                continue
            frame = pd.read_csv(validation_path)
            frame["date"] = pd.to_datetime(frame["date"])
            probability_column = f"probability_{model}"
            metrics = _metrics(frame["actual"], frame[probability_column], threshold)
            negative_dates = frame.loc[frame["actual"].eq(0), "date"]
            quiet_years = max(1 / 52, negative_dates.nunique() / 52.0)
            metrics.update({
                "stage": stage,
                "model": model,
                "validation_start": frame["date"].min().date().isoformat(),
                "validation_end": frame["date"].max().date().isoformat(),
                "false_alarms_per_quiet_year": metrics["fp"] / quiet_years,
            })
            summary_rows.append(metrics)

            positive_dates = pd.DatetimeIndex(frame.loc[frame["actual"].eq(1), "date"].unique())
            date_values = pd.DatetimeIndex(frame["date"])
            for shift_weeks in range(-6, 7):
                shifted = positive_dates + pd.to_timedelta(shift_weeks * 7, unit="D")
                shifted_actual = date_values.isin(shifted).astype(np.int8)
                shifted_metrics = _metrics(shifted_actual, frame[probability_column], threshold)
                shift_rows.append({
                    "stage": stage,
                    "model": model,
                    "shift_weeks": shift_weeks,
                    **shifted_metrics,
                })

            index_path = _index_path(root, stage_dir, model)
            if not index_path.exists():
                index_path = global_index
            if not index_path.exists():
                continue
            corridor = pd.read_csv(index_path)
            corridor["row_date"] = pd.to_datetime(corridor["row_date"])
            corridor["event_date"] = pd.to_datetime(corridor["event_date"])
            merged = corridor.merge(
                frame[["date", "actual", probability_column]],
                left_on="row_date",
                right_on="date",
                how="left",
            )
            for (event_number, event_id), episode in merged.groupby(["event_number", "event_id"], sort=True):
                episode = episode.dropna(subset=[probability_column]).copy()
                if episode.empty:
                    continue
                event_date = pd.Timestamp(episode["event_date"].iloc[0])
                event_row = episode.iloc[int(np.argmin(np.abs((episode["row_date"] - event_date).dt.days)))]
                peak_row = episode.loc[episode[probability_column].idxmax()]
                near = episode[episode["relative_week"].abs() <= 1]
                event_rows.append({
                    "stage": stage,
                    "model": model,
                    "event_number": int(event_number),
                    "event_id": str(event_id),
                    "event_date": event_date.date().isoformat(),
                    "event_magnitude": float(episode["event_magnitude"].iloc[0]),
                    "assigned_master_week": pd.Timestamp(event_row["row_date"]).date().isoformat(),
                    "probability_at_assigned_week": float(event_row[probability_column]),
                    "max_probability_plusminus_1week": float(near[probability_column].max()) if not near.empty else np.nan,
                    "max_probability_full_3month_corridor": float(episode[probability_column].max()),
                    "predicted_peak_date": pd.Timestamp(peak_row["row_date"]).date().isoformat(),
                    "predicted_peak_relative_week": int(peak_row["relative_week"]),
                    "gate_hit_assigned_week": int(float(event_row[probability_column]) >= threshold),
                    "gate_hit_plusminus_1week": int(bool((near[probability_column] >= threshold).any())),
                    "gate_hit_full_corridor": int(bool((episode[probability_column] >= threshold).any())),
                })

    return pd.DataFrame(summary_rows), pd.DataFrame(event_rows), pd.DataFrame(shift_rows)


def _data_checks(root: Path, configuration: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    clean_path = root / "01_data" / "clean_master_binary_7d.csv"
    clean = pd.read_csv(clean_path, low_memory=False)
    clean["date"] = pd.to_datetime(clean["date"])
    historical = clean.loc[~clean["is_forecast"].astype(bool)]
    forecast = clean.loc[clean["is_forecast"].astype(bool)]
    target = historical["japan_m77_event"].dropna()
    hard_negative = clean.loc[clean["is_world_hard_negative"].astype(bool)]
    deltas = clean["date"].sort_values().diff().dropna().dt.days
    expected_start = pd.Timestamp(configuration.get("forecast_start", "2026-08-01"))
    expected_end = pd.Timestamp(configuration.get("forecast_end", "2027-01-31"))
    checks = [
        ("unique_weekly_dates", bool(clean["date"].is_unique), f"unique={clean['date'].nunique()}, rows={len(clean)}"),
        ("monotonic_weekly_dates", bool(clean["date"].is_monotonic_increasing), "ascending master dates"),
        ("exact_seven_day_grid", bool((deltas == 7).all()), f"non_7d_deltas={int((deltas != 7).sum())}"),
        ("binary_historical_target", bool(set(target.unique()).issubset({0, 1, 0.0, 1.0})), f"values={sorted(target.unique().tolist())}"),
        ("foreign_hard_negatives_are_zero", bool(hard_negative["japan_m77_event"].fillna(-1).eq(0).all()), f"rows={len(hard_negative)}"),
        ("prospective_target_is_missing", bool(forecast["japan_m77_event"].isna().all()), f"rows={len(forecast)}"),
        ("forecast_interval_present", bool(forecast["date"].between(expected_start, expected_end).sum() >= 26), f"requested={expected_start.date()}..{expected_end.date()}"),
        ("predictor_namespace_is_packed_astro", bool(all(c.startswith("packed_astro_container_") for c in clean.columns if c.startswith("packed_astro"))), "packed astro predictor namespace"),
    ]
    check_frame = pd.DataFrame(checks, columns=["check", "passed", "detail"])

    input_rows: list[dict[str, Any]] = []
    for label, path_value in {
        "compacted_master": configuration.get("input_master"),
        "japan_catalog": configuration.get("japan_catalog"),
        "world_catalog": configuration.get("world_catalog"),
        "clean_master": str(clean_path),
    }.items():
        if not path_value:
            continue
        path = Path(path_value)
        input_rows.append({
            "name": label,
            "path": str(path.resolve()),
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
            "sha256": _sha256(path) if path.exists() else "",
        })
    return check_frame, pd.DataFrame(input_rows)


def _trial_inventory(root: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for stage, stage_dir in STAGES:
        for model in MODELS:
            name = f"optuna_trials_{model}.csv" if stage == "level1" else f"meta_trials_{model}.csv"
            path = root / stage_dir / f"study_{model}" / name
            if not path.exists():
                rows.append({"stage": stage, "model": model, "file": str(path), "trials": 0, "successful": 0})
                continue
            frame = pd.read_csv(path, low_memory=False)
            success = frame["status"].eq("success") if "status" in frame else pd.Series(False, index=frame.index)
            rows.append({
                "stage": stage,
                "model": model,
                "file": str(path),
                "trials": len(frame),
                "successful": int(success.sum()),
                "window_before_min": float(frame.loc[success, "window_before"].min()) if success.any() else np.nan,
                "window_before_max": float(frame.loc[success, "window_before"].max()) if success.any() else np.nan,
                "window_after_min": float(frame.loc[success, "window_after"].min()) if success.any() else np.nan,
                "window_after_max": float(frame.loc[success, "window_after"].max()) if success.any() else np.nan,
                "pi_chunk_parameter_present": "background_chunk_weeks" in frame.columns,
            })
    return pd.DataFrame(rows)


def _artifact_manifest(root: Path, excluded: set[Path]) -> pd.DataFrame:
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path in excluded or path.suffix == ".sqlite3":
            continue
        rows.append({
            "relative_path": str(path.relative_to(root)),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    return pd.DataFrame(rows)


def _git_state(project: Path) -> dict[str, Any]:
    def command(*args: str) -> str:
        result = subprocess.run(args, cwd=project, text=True, capture_output=True, check=False)
        return result.stdout.strip()

    return {
        "revision": command("git", "rev-parse", "HEAD"),
        "branch": command("git", "branch", "--show-current"),
        "porcelain": command("git", "status", "--short"),
    }


def run(run_dir: Path, threshold: float) -> dict[str, Any]:
    root = run_dir.resolve()
    manifest_path = root / "run_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Run is incomplete; missing {manifest_path}")
    run_manifest = _json(manifest_path)
    configuration = run_manifest.get("configuration", {})
    report_dir = root / "05_report"
    report_dir.mkdir(parents=True, exist_ok=True)

    check_frame, input_frame = _data_checks(root, configuration)
    diagnostics, event_frame, shift_frame = _model_diagnostics(root, threshold)
    trials = _trial_inventory(root)

    check_path = report_dir / "quality_data_checks.csv"
    input_path = report_dir / "quality_input_hashes.csv"
    diagnostics_path = report_dir / "quality_model_diagnostics.csv"
    events_path = report_dir / "quality_event_diagnostics.csv"
    shifts_path = report_dir / "quality_week_shift_sensitivity.csv"
    trials_path = report_dir / "quality_trial_inventory.csv"
    artifact_path = report_dir / "artifact_manifest.csv"
    certificate_path = report_dir / "QUALITY_CERTIFICATION.md"
    json_path = report_dir / "quality_certification.json"
    check_frame.to_csv(check_path, index=False)
    input_frame.to_csv(input_path, index=False)
    diagnostics.to_csv(diagnostics_path, index=False)
    event_frame.to_csv(events_path, index=False)
    shift_frame.to_csv(shifts_path, index=False)
    trials.to_csv(trials_path, index=False)

    project = Path(__file__).resolve().parents[1]
    git = _git_state(project)
    all_data_pass = bool(check_frame["passed"].all())
    all_models_present = len(diagnostics) == len(MODELS) * len(STAGES)
    quality_payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(root),
        "decision_threshold": threshold,
        "data_checks_passed": all_data_pass,
        "all_six_selected_models_present": all_models_present,
        "independent_certification": False,
        "selection_bias_warning": (
            "The two fixed held-out validation events were repeatedly consulted by L1/L2 model selection. "
            "These diagnostics are not an untouched outer certification."
        ),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "git": git,
        },
    }
    json_path.write_text(json.dumps(quality_payload, indent=2), encoding="utf-8")

    lines = [
        "# DLVS-Wave v2.0 quality certification",
        "",
        f"Generated UTC: `{quality_payload['created_utc']}`",
        f"Run directory: `{root}`",
        "",
        "## Verdict",
        "",
        f"- Data-integrity checks: `{'PASS' if all_data_pass else 'FAIL'}`.",
        f"- All six L1/L2 selected outputs present: `{'YES' if all_models_present else 'NO'}`.",
        "- Independent untouched outer certification: `NO`.",
        "",
        "> The two fixed held-out validation events were repeatedly consulted during L1/L2 selection. Their scores are useful",
        "> retrospective diagnostics but cannot be presented as an untouched certification of predictive skill.",
        "",
        "## Data integrity",
        "",
        "| Check | Result | Detail |",
        "|---|:---:|---|",
    ]
    for row in check_frame.itertuples(index=False):
        lines.append(f"| {row.check} | {'PASS' if row.passed else 'FAIL'} | {row.detail} |")
    lines.extend([
        "",
        "## Model diagnostics",
        "",
        "| Stage | Model | P | R | F1 | FP | FN | PR-AUC | Brier | Climatology Brier | Brier improvement | ECE |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in diagnostics.itertuples(index=False):
        lines.append(
            f"| {row.stage} | {row.model} | {row.precision:.3f} | {row.recall:.3f} | {row.f1:.3f} | "
            f"{row.fp} | {row.fn} | {row.pr_auc:.3f} | {row.brier:.4f} | {row.climatology_brier:.4f} | "
            f"{row.brier_improvement:.4f} | {row.ece_10bin:.4f} |"
        )
    lines.extend([
        "",
        "## Attached machine-readable evidence",
        "",
        "- `quality_input_hashes.csv`: immutable input lineage.",
        "- `quality_trial_inventory.csv`: L1/L2 trial counts and explored window bounds.",
        "- `quality_event_diagnostics.csv`: one row per stage/model/held-out event.",
        "- `quality_week_shift_sensitivity.csv`: the same validation predictions rescored at shifts from -6 to +6 weeks.",
        "- `artifact_manifest.csv`: SHA-256 inventory of run artifacts.",
        "",
        "## Scientific limitation",
        "",
        "This study tests retrospective associations in a very small set of rare events. The scores are experimental",
        "model outputs, not calibrated physical earthquake probabilities, and must not be used as an operational",
        "warning. A future claim of generalization requires event-grouped nested validation and an untouched outer set.",
        "",
    ])
    certificate_path.write_text("\n".join(lines), encoding="utf-8")
    artifact_frame = _artifact_manifest(root, {artifact_path, certificate_path, json_path})
    artifact_frame.to_csv(artifact_path, index=False)
    return quality_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--decision-threshold", type=float, default=0.70)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    print(json.dumps(run(arguments.run_dir, arguments.decision_threshold), indent=2))
