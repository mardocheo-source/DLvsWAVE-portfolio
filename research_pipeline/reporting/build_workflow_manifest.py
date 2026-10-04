#!/usr/bin/env python3
"""Build a machine-readable workflow account from completed run artifacts."""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re

import pandas as pd

from common_v6 import (
    PROJECT,
    SYSTEMS,
    model_configuration,
    write_json,
)
from report_time_scale import infer_time_scale


SYSTEM_DISPLAY_NAMES = {
    "lcs_only": "LCS only",
    "kan_only": "KAN only",
    "deep_tiny": "Deep learning — tiny",
    "deep_wide": "Deep learning — wide",
    "deep_regularized": "Deep learning — regularized",
    "lcs_kan": "LCS + KAN",
    "kan_deep_tiny": "KAN + Deep learning — tiny",
    "deep_ensemble": "Deep-learning ensemble",
}


def system_display_name(system: str) -> str:
    if system in SYSTEM_DISPLAY_NAMES:
        return SYSTEM_DISPLAY_NAMES[system]
    members = SYSTEMS.get(system)
    if not members:
        return system.replace("_", " ").title()
    labels = {
        "lcs": "LCS",
        "kan": "KAN",
        "deep_tiny": "Deep tiny",
        "deep_wide": "Deep wide",
        "deep_regularized": "Deep regularized",
    }
    return " + ".join(labels.get(member, member) for member in members)


def load_or_build_timing_quality(
    training_weight: float,
    validation_weight: float,
) -> pd.DataFrame:
    """Derive the timing ranking from fold summaries when no cached CSV exists."""
    destination = (
        PROJECT / "05_ensemble/timing/timing_system_quality_report.csv"
    )
    if destination.is_file():
        return pd.read_csv(destination)
    fold_directories = sorted(
        path
        for path in (PROJECT / "04_models/timing").iterdir()
        if path.is_dir()
    )
    rows = []
    for system in SYSTEMS:
        summaries = []
        for fold in fold_directories:
            path = fold / system / "summary.json"
            if path.is_file():
                summaries.append(json.loads(path.read_text()))
        if not summaries:
            continue
        training_quality = sum(
            float(item["training_metrics"]["quality_higher_is_better"])
            for item in summaries
        ) / len(summaries)
        validation_quality = sum(
            float(item["validation_metrics"]["quality_higher_is_better"])
            for item in summaries
        ) / len(summaries)
        rows.append(
            {
                "system": system,
                "display_name": system_display_name(system),
                "training_quality": training_quality,
                "validation_quality": validation_quality,
                "combined_quality": (
                    float(training_weight) * training_quality
                    + float(validation_weight) * validation_quality
                ),
                "folds": len(summaries),
            }
        )
    if not rows:
        raise FileNotFoundError(
            "No timing system summaries are available to build the ranking"
        )
    frame = pd.DataFrame(rows).sort_values(
        "combined_quality", ascending=False
    ).reset_index(drop=True)
    frame["rank"] = frame.index + 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)
    return frame


def celestial_catalogue() -> tuple[dict, str]:
    """Load a configurable body catalogue, falling back to the bundled JPL map."""
    configured = os.environ.get("DLVSWAVE_CELESTIAL_BODY_CATALOG")
    candidates = [
        Path(configured).expanduser() if configured else None,
        PROJECT / "00_config/celestial_body_catalog.json",
        Path(__file__).with_name("celestial_body_catalog.json"),
    ]
    for candidate in candidates:
        if candidate is not None and candidate.exists():
            catalogue = json.loads(candidate.read_text())
            audit_path = PROJECT / "00_config/astro_source_audit.json"
            if audit_path.is_file():
                audit = json.loads(audit_path.read_text())
                contract = audit.get("required_contract", {})
                groups = {
                    "core_bodies": "planet, dwarf planet or star",
                    "major_moons": "natural satellite",
                    "minor_bodies": "minor Solar System body",
                }
                for group, category in groups.items():
                    for target_id, name in contract.get(group, {}).items():
                        catalogue.setdefault("entries", {}).setdefault(
                            str(target_id),
                            {
                                "name": str(name),
                                "category": category,
                            },
                        )
                catalogue["audit_extension"] = str(audit_path)
            return catalogue, str(candidate)
    raise FileNotFoundError("No celestial-body catalogue is available")


def parse_feature_name(feature: str, catalogue: dict) -> dict:
    """Decode body identifier and measurement from an ephemeris field name."""
    def humanize(value: str) -> str:
        """Keep the source token intact semantically while removing separators."""
        return re.sub(r"\s+", " ", str(value).replace("_", " ")).strip()

    named_body = re.match(
        (
            r"^body:(?P<target>[^|]+)"
            r"\|center:(?P<center>[^|]+)"
            r"\|frame:(?P<frame>[^|]+)"
            r"\|eph:(?P<measurement>[^|]+)"
            r"\|op:(?P<operator>[^|]+)$"
        ),
        str(feature),
    )
    if named_body:
        target_name = named_body.group("target")
        base_name = re.sub(
            r"_(?:system_)?barycenter$", "", target_name
        ).replace("_", " ")
        catalogue_match = next(
            (
                body
                for body in catalogue.get("entries", {}).values()
                if str(body.get("name", "")).casefold()
                == base_name.casefold()
            ),
            {},
        )
        display_name = str(
            catalogue_match.get("name")
            or humanize(target_name).title()
        )
        return {
            "feature": str(feature),
            "measurement": (
                f"{humanize(named_body.group('measurement'))} · "
                f"{humanize(named_body.group('operator'))} · "
                f"{humanize(named_body.group('frame'))}"
            ),
            "observer": named_body.group("center"),
            "target_id": target_name,
            "body_name": display_name,
            "body_category": catalogue_match.get(
                "category", "configured Solar System body"
            ),
        }
    structured = re.match(
        (
            r"^body:(?P<target>[^|]+)"
            r"\|obs:(?P<observer>[^|]+)"
            r"\|eph:(?P<measurement>[^|]+)"
            r"\|op:(?P<operator>[^|]+)$"
        ),
        str(feature),
    )
    if structured:
        target_id = structured.group("target")
        fallback = catalogue.get("fallback", {})
        body = catalogue.get("entries", {}).get(
            target_id,
            {
                "name": fallback.get(
                    "name_template", "JPL target {target_id}"
                ).format(target_id=target_id),
                "category": fallback.get(
                    "category", "configured Solar System body"
                ),
            },
        )
        return {
            "feature": str(feature),
            "measurement": (
                f"{humanize(structured.group('measurement'))} · "
                f"{humanize(structured.group('operator'))}"
            ),
            "observer": structured.group("observer"),
            "target_id": target_id,
            "body_name": body["name"],
            "body_category": body["category"],
        }
    match = re.match(
        r"^(?P<target>[^_]+)_geo_[^_]+_[^_]+_[^_]+_(?P<measurement>.+)$",
        str(feature),
    )
    if match:
        target_id = match.group("target")
        fallback = catalogue.get("fallback", {})
        body = catalogue.get("entries", {}).get(
            target_id,
            {
                "name": fallback.get(
                    "name_template", "JPL target {target_id}"
                ).format(target_id=target_id),
                "category": fallback.get(
                    "category", "configured Solar System body"
                ),
            },
        )
        return {
            "feature": str(feature),
            "measurement": humanize(match.group("measurement")),
            "observer": "encoded in legacy field name",
            "target_id": target_id,
            "body_name": body["name"],
            "body_category": body["category"],
        }
    return {
        "feature": str(feature),
        "measurement": humanize(str(feature)),
        "observer": "not applicable",
        "target_id": "—",
        "body_name": "Calendar or derived field",
        "body_category": "non-body feature",
    }


def top_feature_evidence(
    paths: list[Path], limit: int | None = 20
) -> list[dict]:
    """Build a higher-is-better consensus from one or more ranking audits."""
    catalogue, _ = celestial_catalogue()
    by_feature: dict[str, list[dict]] = {}
    for path in paths:
        payload = json.loads(path.read_text())
        ranking = payload.get("ranking", [])
        denominator = max(1, len(ranking) - 1)
        for row in ranking:
            item = dict(row)
            item["rank_skill"] = 1.0 - (float(row["rank"]) - 1.0) / denominator
            by_feature.setdefault(str(row["feature"]), []).append(item)
    evidence = []
    for feature, rows in by_feature.items():
        decoded = parse_feature_name(feature, catalogue)
        evidence.append(
            {
                **decoded,
                "ranking_score_higher_is_better": float(
                    sum(row["rank_skill"] for row in rows) / len(rows)
                ),
                "mean_rank_across_audits": float(
                    sum(float(row["mean_rank"]) for row in rows) / len(rows)
                ),
                "mutual_information": float(
                    sum(float(row["mutual_information"]) for row in rows)
                    / len(rows)
                ),
                "random_forest_importance": float(
                    sum(float(row["random_forest"]) for row in rows) / len(rows)
                ),
                "extra_trees_importance": float(
                    sum(float(row["extra_trees"]) for row in rows) / len(rows)
                ),
                "audits_present": len(rows),
            }
        )
    evidence.sort(
        key=lambda row: (
            -row["ranking_score_higher_is_better"],
            row["mean_rank_across_audits"],
            row["feature"],
        )
    )
    for rank, row in enumerate(evidence, 1):
        row["display_rank"] = rank
    return evidence if limit is None else evidence[:limit]


def celestial_body_summary(evidence: list[dict], displayed_limit: int = 20) -> list[dict]:
    """Collapse repeated measurements to one auditable row per JPL target."""
    represented = {
        row["target_id"]
        for row in evidence[:displayed_limit]
        if row["target_id"] != "—"
    }
    grouped: dict[str, dict] = {}
    for row in evidence:
        target_id = row["target_id"]
        if target_id == "—":
            continue
        item = grouped.setdefault(
            target_id,
            {
                "target_id": target_id,
                "body_name": row["body_name"],
                "body_category": row["body_category"],
                "ranked_measurement_count": 0,
                "best_feature_rank": int(row["display_rank"]),
                "best_feature": row["feature"],
                "represented_in_top_features": target_id in represented,
            },
        )
        item["ranked_measurement_count"] += 1
        if int(row["display_rank"]) < int(item["best_feature_rank"]):
            item["best_feature_rank"] = int(row["display_rank"])
            item["best_feature"] = row["feature"]
    return sorted(
        grouped.values(),
        key=lambda row: (row["best_feature_rank"], row["target_id"]),
    )


def _range_text(values: list[int]) -> str:
    clean = sorted(set(int(value) for value in values))
    if not clean:
        return "not recorded"
    return str(clean[0]) if len(clean) == 1 else f"{clean[0]}–{clean[-1]}"


def top_timing_models(
    timing_quality: pd.DataFrame,
    epochs_scale: float,
    recorded_configurations: dict | None = None,
    limit: int = 3,
) -> list[dict]:
    recorded_configurations = recorded_configurations or {}
    compact_path = (
        PROJECT / "02_master_search/compact_k_factor_selection.json"
    )
    compact_selection = (
        json.loads(compact_path.read_text()).get("selected", {})
        if compact_path.is_file()
        else {}
    )
    timing_master_path = PROJECT / "01_inputs/timing_master.csv"
    compact_start_year = None
    if timing_master_path.is_file():
        timing_years = (
            pd.read_csv(timing_master_path, usecols=["date"])["date"]
            .astype(str)
            .str.slice(0, 4)
            .astype(int)
        )
        if len(timing_years):
            compact_start_year = int(timing_years.min())
    results = []
    for row in timing_quality.sort_values("rank").head(limit).itertuples():
        summaries = []
        fold_details = []
        for path in sorted(
            (PROJECT / "04_models/timing").glob(
                f"*/{row.system}/summary.json"
            )
        ):
            summary = json.loads(path.read_text())
            summaries.append(summary)
            history = summary.get("history", {})
            event_radius = history.get(
                "event_radius", compact_selection.get("k_event")
            )
            history_start_year = history.get(
                "start_year", compact_start_year
            )
            step_path = path.parent.parent / "step_summary.json"
            step = json.loads(step_path.read_text()) if step_path.exists() else {}
            event = step.get("event", {})
            fold_details.append(
                {
                    "fold": len(fold_details) + 1,
                    "held_out_event_slot": event.get("date", "not recorded"),
                    "held_out_event_magnitude": event.get(
                        "magnitude", "not recorded"
                    ),
                    "feature_count": int(summary["feature_count"]),
                    "training_events": int(summary["training_events"]),
                    "training_rows": int(summary["training_rows"]),
                    "event_radius": (
                        int(event_radius)
                        if event_radius is not None
                        else "not recorded"
                    ),
                    "history_start_year": (
                        int(history_start_year)
                        if history_start_year is not None
                        else "not recorded"
                    ),
                }
            )
        feature_counts = [item["feature_count"] for item in summaries]
        members = list(
            summaries[0]["members"]
            if summaries
            else SYSTEMS.get(str(row.system), ())
        )
        results.append(
            {
                "rank": int(row.rank),
                "system": str(row.system),
                "display_name": str(row.display_name),
                "training_quality": float(row.training_quality),
                "validation_quality": float(row.validation_quality),
                "combined_quality": float(row.combined_quality),
                "folds": int(row.folds),
                "components": members,
                "training_context": {
                    "features_across_folds": _range_text(feature_counts),
                    "training_events_across_folds": _range_text(
                        [item["training_events"] for item in summaries]
                    ),
                    "training_rows_across_folds": _range_text(
                        [item["training_rows"] for item in summaries]
                    ),
                    "event_radius_across_folds": _range_text(
                        [
                            item.get("history", {}).get(
                                "event_radius",
                                compact_selection.get("k_event"),
                            )
                            for item in summaries
                            if item.get("history", {}).get(
                                "event_radius",
                                compact_selection.get("k_event"),
                            )
                            is not None
                        ]
                    ),
                    "history_start_years": _range_text(
                        [
                            item.get("history", {}).get(
                                "start_year", compact_start_year
                            )
                            for item in summaries
                            if item.get("history", {}).get(
                                "start_year", compact_start_year
                            )
                            is not None
                        ]
                    ),
                },
                "fold_details": fold_details,
                "component_configurations": {
                    member: recorded_configurations.get(
                        member,
                        model_configuration(
                            member,
                            epochs_scale,
                            max(feature_counts) if feature_counts else None,
                        ),
                    )
                    for member in members
                },
            }
        )
    return results


def top_location_models(
    location_quality: pd.DataFrame,
    location_summary: dict,
    epochs_scale: float,
    limit: int = 3,
) -> list[dict]:
    selected_feature_count = int(
        location_summary["selected_features"]["count"]
    )
    recorded = location_summary.get("base_model_configurations", {})
    results = []
    for row in location_quality.sort_values("rank").head(limit).itertuples():
        system = str(row.system)
        members = list(SYSTEMS.get(system, (system,)))
        results.append(
            {
                "rank": int(row.rank),
                "system": system,
                "display_name": system_display_name(system),
                "training_quality": float(row.training_quality),
                "validation_quality": float(row.validation_quality),
                "combined_quality": float(
                    row.origin_quality_25train_75validation
                ),
                "validation_exact_zone": float(row.validation_exact_zone),
                "validation_top_two_zone": float(row.validation_top_two_zone),
                "components": members,
                "training_context": {
                    "features": selected_feature_count,
                    "training_events": int(location_summary["training_events"]),
                    "holdout_events": len(location_summary["validation_events"]),
                    "validation_design": location_summary["validation_design"][
                        "mode"
                    ],
                },
                "component_configurations": {
                    member: recorded.get(
                        member,
                        model_configuration(
                            member,
                            epochs_scale,
                            selected_feature_count,
                        ),
                    )
                    for member in members
                },
            }
        )
    return results


def fusion_display_name(raw_name: str) -> str:
    value = str(raw_name)
    strengths = ("_prior_correct_1.00", "_prior_correct_0.65", "_prior_correct_0.35")
    strength = None
    for suffix in strengths:
        if value.endswith(suffix):
            value = value[: -len(suffix)]
            strength = float(suffix.rsplit("_", 1)[-1])
            break
    labels = {
        "best_single": "Best individual zone model",
        "top3_hard_vote": "Top three models — majority vote",
        "top3_soft_probability": "Top three models — weighted scores",
        "diverse3_soft_probability": "Three diverse models — weighted scores",
        "five_bases_soft_probability": "Five base models — weighted scores",
        "all16_quality_soft_probability": (
            "All sixteen systems — quality-weighted scores"
        ),
    }
    label = labels.get(value, value.replace("_", " ").title())
    if strength is None:
        return label + "; no historical-frequency adjustment"
    return (
        label
        + f"; historical-zone frequency adjustment strength {strength:.0%}"
    )


def read_json(relative: str) -> dict:
    return json.loads((PROJECT / relative).read_text())


def relative(path: Path) -> str:
    return str(path.relative_to(PROJECT))


def build_workflow() -> dict:
    manifest = read_json("00_config/run_manifest.json")
    request_path = PROJECT / "00_config/pipeline_request.json"
    pipeline_request = (
        json.loads(request_path.read_text()) if request_path.is_file() else {}
    )
    interval_audit_path = PROJECT / "02_audit/interval_feature_operators.json"
    interval_audit = (
        json.loads(interval_audit_path.read_text())
        if interval_audit_path.is_file()
        else None
    )
    model_screen_path = PROJECT / "03_feature_research/model_runtime_quality_audit.json"
    model_screen = (
        json.loads(model_screen_path.read_text())
        if model_screen_path.is_file()
        else None
    )
    timing_summary = read_json("05_ensemble/timing/final_summary.json")
    location_summary = read_json("05_ensemble/location_zone_summary.json")
    isolation = read_json("05_ensemble/timing/peak_isolation_gate.json")
    zone_search = read_json("02_audit/location_zone_search.json")
    timing_features = read_json(
        "03_feature_research/timing/final_conservative_features.json"
    )
    location_features = read_json(
        "03_feature_research/location_zones/feature_ranking.json"
    )
    timing_forecast = pd.read_csv(
        PROJECT / "05_ensemble/timing/forecast_predictions.csv"
    )
    time_scale = infer_time_scale(timing_forecast["date"]).to_dict()
    extended_audit_path = PROJECT / "02_audit/extended_astro_master.json"
    extended_audit = (
        json.loads(extended_audit_path.read_text())
        if extended_audit_path.exists()
        else None
    )
    astro_audit_path = PROJECT / "00_config/astro_source_audit.json"
    astro_audit = (
        json.loads(astro_audit_path.read_text())
        if astro_audit_path.exists()
        else None
    )
    observer = (
        astro_audit.get("required_contract", {}).get("observer", {})
        if astro_audit
        else {}
    )

    timing_ablation_files = sorted(
        (PROJECT / "03_feature_research/timing").glob("*/ablation_trials.csv")
    )
    timing_ablation = (
        pd.concat(
            [pd.read_csv(path) for path in timing_ablation_files],
            ignore_index=True,
        )
        if timing_ablation_files
        else pd.DataFrame()
    )
    location_ablation_path = (
        PROJECT / "03_feature_research/location_zones/ablation_trials.csv"
    )
    location_ablation = pd.read_csv(location_ablation_path)
    timing_quality = load_or_build_timing_quality(
        manifest["parameters"]["training_objective_weight"],
        manifest["parameters"]["validation_objective_weight"],
    )
    location_quality = pd.read_csv(
        PROJECT / "05_ensemble/location_zone_system_ranking.csv"
    )
    fusion_trials = pd.read_csv(
        PROJECT / "05_ensemble/location_zone_fusion_trials.csv"
    )
    best_timing_system = timing_quality.sort_values("rank").iloc[0]
    best_location_system = location_quality.sort_values("rank").iloc[0]
    best_fusion = fusion_trials.sort_values(
        "quality_higher_is_better", ascending=False
    ).iloc[0]
    timing_input = manifest["input"]
    parameters = manifest["parameters"]
    body_catalogue, body_catalogue_source = celestial_catalogue()
    timing_ranking_paths = sorted(
        (PROJECT / "03_feature_research/timing").glob(
            "*/statistical_ranking.json"
        )
    )
    location_ranking_paths = [
        PROJECT / "03_feature_research/location_zones/feature_ranking.json"
    ]
    location_parameters = location_summary.get("run_parameters", {})
    if "epochs_scale" not in location_parameters:
        raise KeyError(
            "location_zone_summary.json does not persist run_parameters.epochs_scale"
        )
    location_epochs_scale = float(location_parameters["epochs_scale"])
    timing_models = top_timing_models(
        timing_quality,
        float(parameters["epochs_scale"]),
        manifest.get("base_model_configurations", {}),
    )
    location_models = top_location_models(
        location_quality,
        location_summary,
        location_epochs_scale,
    )

    stages = [
        {
            "order": 1,
            "id": "data_master",
            "title": "Data acquisition, contracts and master construction",
            "inputs": [
                "Solar System body-position feature master",
                "Regional earthquake catalogue and event coordinates",
                "Region, magnitude thresholds, forecast dates and interval grid",
                (
                    "Observer location supplied through the astronomical "
                    "source contract"
                ),
            ],
            "operations": [
                "Verify required columns, date ordering, finite values and checksums.",
                "Align every row to the configured start-based interval grid.",
                *(
                    [
                        "Sample each target interval on a finer Horizons grid and derive configured minimum, median and maximum ephemeris features."
                    ]
                    if interval_audit
                    else []
                ),
                "Create separate timing and localization masters and prevent forecast rows from entering training.",
            ],
            "decision_rule": (
                "Stop on a failed schema, checksum, time-grid or data-leakage "
                "contract; do not silently continue with incomplete downloads."
            ),
            "outputs": [
                "01_inputs/timing_master.csv",
                "01_inputs/location_master.csv",
                "00_config/run_manifest.json",
            ],
            "audit_files": [
                "00_config/run_manifest.json",
                "00_config/report_artifact_discovery.json",
                *(
                    ["00_config/astro_source_audit.json"]
                    if astro_audit
                    else []
                ),
            ],
            "evidence": {
                "timing_master_rows": int(timing_input["rows"]),
                "master_first_interval": timing_input.get(
                    "first_date", "read from timing_master.csv"
                ),
                "candidate_predictive_features": int(
                    timing_input["native_safe_start_features"]
                ),
                "interval_operator_features": (
                    int(interval_audit["generated_operator_feature_count"])
                    if interval_audit
                    else 0
                ),
                "fine_samples_per_interval": (
                    int(interval_audit["samples_per_interval"])
                    if interval_audit
                    else "not applicable"
                ),
                "timing_master_sha256": timing_input["sha256"],
                "interval_resolution": time_scale["resolution_text"],
                "observer_label": observer.get(
                    "label", "not recorded for this run"
                ),
                "observer_latitude": observer.get(
                    "latitude", "not recorded for this run"
                ),
                "observer_longitude": observer.get(
                    "longitude", "not recorded for this run"
                ),
                "observer_elevation_km": observer.get(
                    "elevation_km", "not recorded for this run"
                ),
                "historical_extension_mode": (
                    extended_audit["mode"]
                    if extended_audit
                    else "not recorded for this run"
                ),
                "1923_source_rows_in_audited_window": (
                    extended_audit["source_gap_audit"][
                        "kanto_window_source_rows"
                    ]
                    if extended_audit
                    else "not applicable"
                ),
            },
            "value_added": (
                "Creates one reproducible, leakage-controlled table shared by "
                "all model families instead of allowing each model to use a "
                "different interpretation of dates or events."
            ),
        },
        {
            "order": 2,
            "id": "feature_search",
            "title": "Feature ranking and guarded backward ablation",
            "inputs": [
                "Native-safe astronomical feature set",
                "Chronological timing folds",
                "One-shot localization holdout",
            ],
            "operations": [
                *(
                    [
                        "Fit empirical quantile cut points on training rows only and transform validation/forecast rows to the configured ordinal levels."
                    ]
                    if int(parameters.get("quantile_bins", 0)) >= 2
                    else []
                ),
                "Rank features with statistical and tree-based relevance signals.",
                "Probe low-ranked feature blocks, then individual features.",
                "Accept a removal only when practical model quality stays within configured damage tolerances; otherwise roll it back.",
                "Repeat conservatively down to, but never below, the configured minimum feature count.",
            ],
            "decision_rule": (
                "Ranking proposes removals; chronological training and held-out "
                "validation decide whether each removal is retained."
            ),
            "outputs": [
                "03_feature_research/timing/final_conservative_features.json",
                "03_feature_research/location_zones/feature_ranking.json",
                "03_feature_research/**/ablation_trials.csv",
            ],
            "audit_files": [
                "03_feature_research/timing/final_conservative_features.json",
                "03_feature_research/location_zones/ablation_trials.csv",
            ],
            "evidence": {
                "timing_features_retained": int(
                    timing_features["feature_count"]
                ),
                "timing_ablation_probes": int(len(timing_ablation)),
                "timing_accepted_removals": int(
                    timing_ablation.get("accepted", pd.Series(dtype=bool))
                    .astype(bool)
                    .sum()
                ),
                "location_ranked_features": int(
                    len(location_features["ranking"])
                ),
                "location_ablation_probes": int(len(location_ablation)),
                "location_accepted_probes": int(
                    location_ablation["accepted"].astype(bool).sum()
                ),
                "minimum_feature_floor": int(parameters["feature_min"]),
                "quantile_bins": int(parameters.get("quantile_bins", 0)),
                "quantile_fit_scope": (
                    pipeline_request.get("preprocessing", {}).get(
                        "fit_scope", "disabled"
                    )
                ),
            },
            "value_added": (
                "Tests feature simplification against real model behaviour. "
                "This is safer than selecting a fixed top-N list solely from a "
                "theoretical importance rank."
            ),
        },
        {
            "order": 3,
            "id": "timing_models",
            "title": "Timing-system search and incremental validation",
            "inputs": [
                "Retained timing features",
                (
                    f"Japan training event slots at M≥"
                    f"{parameters['timing_magnitude_threshold']:g}"
                ),
                (
                    "Configured chronological validation events at M≥"
                    f"{parameters.get('timing_validation_magnitude_threshold', parameters['timing_magnitude_threshold']):g}"
                ),
                "Non-Japan controls with independently configured training and validation floors",
            ],
            "operations": [
                *(
                    [
                        "Fast-screen architecture, optimizer, loss, regularization and family-specific capacity candidates; promote one configuration per family using a quality-speed KPI."
                    ]
                    if model_screen
                    else []
                ),
                "Fit LCS, KAN, PyTorch tiny/wide/regularized and hybrid variants.",
                "Repeat feature/model selection for each incremental outer fold.",
                "Score event rank, local prominence, competitors, background and false peaks in one higher-is-better objective.",
                "Search positive ensemble weights and validation-gated alias penalties.",
            ],
            "decision_rule": (
                "All variants retain positive weight. Selection uses "
                f"{parameters['training_objective_weight']:.0%} training and "
                f"{parameters['validation_objective_weight']:.0%} held-out "
                "validation, and a penalty is accepted only if every real "
                "validation peak is preserved."
            ),
            "outputs": [
                "04_models/timing/**/summary.json",
                "05_ensemble/timing/validation_predictions.csv",
                "05_ensemble/timing/forecast_predictions.csv",
            ],
            "audit_files": [
                "05_ensemble/timing/timing_system_quality_report.csv",
                "05_ensemble/timing/peak_isolation_gate.json",
                "05_ensemble/timing/final_summary.json",
            ],
            "evidence": {
                "systems_compared": int(len(timing_quality)),
                "outer_validation_events": int(
                    len(timing_summary["outer_validation_events"])
                ),
                "best_ranked_system": str(best_timing_system["display_name"]),
                "best_combined_quality": float(
                    best_timing_system["combined_quality"]
                ),
                "ensemble_weight_trials": int(
                    isolation["search"]["weight_candidates"]
                ),
                "isolation_before": float(
                    isolation["baseline_without_alias"][
                        "total_objective_higher_is_better"
                    ]
                ),
                "isolation_after": float(
                    isolation["selected"][
                        "total_objective_higher_is_better"
                    ]
                ),
                "hyperparameter_screened_families": (
                    int(len(model_screen["selected"])) if model_screen else 0
                ),
            },
            "value_added": (
                "Compares new and conventional neural approaches under the same "
                "chronological evidence and explicitly rewards isolated event "
                "peaks instead of minimizing only a generic average error."
            ),
        },
        {
            "order": 4,
            "id": "location_models",
            "title": "Joint geographic-zone and localization-system search",
            "inputs": [
                (
                    "Japan location-training coordinates at M≥"
                    f"{parameters['location_magnitude_threshold']:g}"
                ),
                (
                    "Chronological location holdouts at M≥"
                    f"{parameters.get('location_validation_magnitude_threshold', parameters['location_magnitude_threshold']):g}"
                ),
                "Retained localization features",
                "Configured geographic rectangle",
            ],
            "operations": [
                "Test candidate two-dimensional GMM zone counts with minimum-size constraints.",
                "Assign every map cell to one learned joint latitude–longitude zone.",
                "Fit the same LCS, KAN, deep and hybrid families for zone classification.",
                "Compare single systems and soft fusions, including validated historical-frequency adjustment strengths.",
            ],
            "decision_rule": (
                "Choose zone count with 80% geographic separation and 20% BIC "
                "parsimony; choose model fusion by held-out higher-is-better "
                "quality, not by training fit alone."
            ),
            "outputs": [
                "05_ensemble/location_zones.csv",
                "05_ensemble/location_zone_decision_grid.csv",
                "05_ensemble/location_zone_forecast.csv",
            ],
            "audit_files": [
                "02_audit/location_zone_search.json",
                "05_ensemble/location_zone_system_ranking.csv",
                "05_ensemble/location_zone_fusion_trials.csv",
            ],
            "evidence": {
                "zone_construction_events": int(
                    location_summary["zone_construction_events"]
                ),
                "candidate_zone_counts": [
                    int(row["zones"]) for row in zone_search["trials"]
                ],
                "selected_zone_count": int(zone_search["selected"]["zones"]),
                "systems_compared": int(len(location_quality)),
                "best_ranked_system": SYSTEM_DISPLAY_NAMES.get(
                    str(best_location_system["system"]),
                    str(best_location_system["system"]).replace("_", " ").title(),
                ),
                "fusion_candidates": int(len(fusion_trials)),
                "selected_fusion": fusion_display_name(
                    str(best_fusion["fusion"])
                ),
            },
            "value_added": (
                "Predicts latitude and longitude jointly, preventing an "
                "incompatible latitude from one seismic cluster from being "
                "combined with longitude from another."
            ),
        },
        {
            "order": 5,
            "id": "fusion_report_qc",
            "title": "Forecast fusion, report generation and quality control",
            "inputs": [
                "Timing ensemble and selected location fusion",
                "Machine-readable run, validation and zone audits",
                "Reader-facing narrative rules",
            ],
            "operations": [
                "Select the highest empirical timing rank within the requested window.",
                "Associate every interval with the one-shot predicted geographic zone and centroid.",
                "Generate explanations, formulas, figures, linked contents and bookmarks from CSV/JSON.",
                "Run artifact, interval, leakage, visual-content and PDF structure checks.",
            ],
            "decision_rule": (
                "Publish the report only when required artifacts exist and every "
                "self-check passes; scores remain explicitly uncalibrated."
            ),
            "outputs": [
                "00_config/report_narrative.json",
                "00_config/report_workflow.json",
                "06_report/V10_REPORT.md",
                "06_report/V10_REPORT.pdf",
                "06_report/self_check_v10.json",
            ],
            "audit_files": [
                "00_config/report_artifact_discovery.json",
                "06_report/self_check_v10.json",
            ],
            "evidence": {
                "timing_forecast_intervals": int(len(timing_forecast)),
                "location_holdouts": int(
                    len(location_summary["validation_events"])
                ),
                "location_exact_matches": int(
                    round(
                        location_summary["validation_metrics"][
                            "exact_zone_accuracy"
                        ]
                        * len(location_summary["validation_events"])
                    )
                ),
                "report_language": "English",
            },
            "value_added": (
                "Turns a large experimental search into a reproducible decision "
                "trail that another reader can audit without relying on the "
                "original conversation or manual report assembly."
            ),
        },
    ]
    timing_feature_rows = top_feature_evidence(timing_ranking_paths, limit=None)
    location_feature_rows = top_feature_evidence(
        location_ranking_paths, limit=None
    )
    randomized = {}
    for domain in ("timing", "location"):
        path = PROJECT / f"07_randomized_control/{domain}/summary.json"
        if path.exists():
            randomized[domain] = json.loads(path.read_text())
    return {
        "schema_version": "1.1",
        "generated_at": datetime.now().astimezone().isoformat(),
        "source_pipeline": manifest["pipeline"],
        "project_directory": str(PROJECT),
        "time_scale": time_scale,
        "stage_count": len(stages),
        "execution_order": [stage["id"] for stage in stages],
        "stages": stages,
        "feature_evidence": {
            "catalogue": body_catalogue.get(
                "catalogue", "configured celestial-body catalogue"
            ),
            "catalogue_source": body_catalogue_source,
            "score_semantics": (
                "consensus ranking score normalized to 0–1; higher means a "
                "feature ranked nearer the top across the available audits"
            ),
            "timing": {
                "audit_count": len(timing_ranking_paths),
                "top_features": timing_feature_rows[:20],
                "display_limit": 20,
                "total_ranked_features": len(timing_feature_rows),
                "celestial_bodies": celestial_body_summary(
                    timing_feature_rows, 20
                ),
            },
            "localization": {
                "audit_count": len(location_ranking_paths),
                "top_features": location_feature_rows[:20],
                "display_limit": 20,
                "total_ranked_features": len(location_feature_rows),
                "celestial_bodies": celestial_body_summary(
                    location_feature_rows, 20
                ),
            },
        },
        "model_evidence": {
            "quality_formula": (
                f"{parameters['training_objective_weight']:.0%} training + "
                f"{parameters['validation_objective_weight']:.0%} validation"
            ),
            "timing": {
                "epochs_scale": float(parameters["epochs_scale"]),
                "top_systems": timing_models,
            },
            "localization": {
                "epochs_scale": location_epochs_scale,
                "top_systems": location_models,
            },
        },
        "reproducibility_contract": (
            "The workflow description is generated from the same manifest, "
            "CSV and JSON artifacts used by the report; no stage values are "
            "manually transcribed into the PDF."
        ),
        "randomized_control": {
            "available": set(randomized) == {"timing", "location"},
            "controls": randomized,
            "scope": (
                "one-shot null experiments with training labels permuted and "
                "chronological holdouts preserved; outputs never affect the "
                "primary sequential forecast"
            ),
        },
    }


def main() -> None:
    destination = PROJECT / "00_config/report_workflow.json"
    write_json(destination, build_workflow())
    print(f"Report workflow: {destination}")


if __name__ == "__main__":
    main()
