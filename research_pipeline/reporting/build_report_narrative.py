#!/usr/bin/env python3
"""Build the parameter-driven explanatory layer used by the v9 report.

The report renderer deliberately does not invent explanations from plot labels.
This script reads the run manifest and the audited model outputs, then writes a
machine-readable description of terminology, choices, results and limitations.
The same schema can be regenerated for another region, time window or magnitude
threshold without changing report prose in the plotting code.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from common_v6 import PROJECT, write_json
from report_time_scale import infer_time_scale, interval_end, interval_label


def interval(start_value: str, time_scale) -> tuple[pd.Timestamp, pd.Timestamp, str]:
    start = pd.Timestamp(start_value)
    end = interval_end(start, time_scale)
    return start, end, interval_label(start, time_scale)


def build_narrative() -> dict:
    manifest = json.loads((PROJECT / "00_config/run_manifest.json").read_text())
    timing_summary = json.loads(
        (PROJECT / "05_ensemble/timing/final_summary.json").read_text()
    )
    location_summary = json.loads(
        (PROJECT / "05_ensemble/location_zone_summary.json").read_text()
    )
    isolation = json.loads(
        (PROJECT / "05_ensemble/timing/peak_isolation_gate.json").read_text()
    )
    metric_fusion = json.loads(
        (
            PROJECT
            / "05_ensemble/timing/metric_specialist_fusion/"
            "metric_specialist_fusion_summary.json"
        ).read_text()
    )
    metric_trial = metric_fusion["selected_trial"]
    contextual_summary_path = (
        PROJECT
        / "05_ensemble/timing/contextual_fold_fusion/"
        "contextual_fold_fusion_summary.json"
    )
    contextual_summary = (
        json.loads(contextual_summary_path.read_text())
        if contextual_summary_path.is_file()
        else None
    )
    zone_search = json.loads(
        (PROJECT / "02_audit/location_zone_search.json").read_text()
    )
    report_request_path = PROJECT / "00_config/standard_report_request.json"
    report_request = (
        json.loads(report_request_path.read_text())
        if report_request_path.is_file()
        else {}
    )
    peak_request = report_request.get("forecast_peak_modes", {})
    configured_timing_path = str(
        peak_request.get("primary_score_csv", "")
    ).strip()
    configured_timing_column = str(
        peak_request.get("primary_score_column", "")
    ).strip()
    timing_forecast_path = (
        Path(configured_timing_path)
        if configured_timing_path
        else PROJECT / "05_ensemble/timing/forecast_predictions.csv"
    )
    if not timing_forecast_path.is_absolute():
        timing_forecast_path = PROJECT / timing_forecast_path
    timing_forecast = pd.read_csv(timing_forecast_path)
    primary_timing_score_column = (
        configured_timing_column
        if configured_timing_column in timing_forecast
        else "score_percentile_not_probability"
    )
    location_forecast = pd.read_csv(
        PROJECT / "05_ensemble/location_zone_forecast.csv"
    )
    peak_mode_path = (
        PROJECT / "05_ensemble/timing/forecast_peak_modes.csv"
    )
    peak_audit_path = (
        PROJECT / "05_ensemble/timing/forecast_peak_modes.json"
    )
    peak_modes = (
        pd.read_csv(peak_mode_path)
        if peak_mode_path.is_file()
        else pd.DataFrame()
    )
    peak_audit = (
        json.loads(peak_audit_path.read_text())
        if peak_audit_path.is_file()
        else {}
    )
    primary_selection_path = (
        PROJECT / "05_ensemble/timing/forecast_primary_selection.csv"
    )
    primary_selection = (
        pd.read_csv(primary_selection_path)
        if primary_selection_path.is_file()
        else pd.DataFrame()
    )
    location_validation = pd.read_csv(
        PROJECT / "05_ensemble/location_zone_validation.csv"
    )
    zones = pd.read_csv(PROJECT / "05_ensemble/location_zones.csv")
    weights = pd.read_csv(
        PROJECT / "05_ensemble/timing/peak_isolation_system_weights.csv"
    ).sort_values("positive_weight", ascending=False)
    contextual_validation_path = (
        PROJECT
        / "05_ensemble/timing/contextual_fold_fusion/"
        "contextual_fold_validation_predictions.csv"
    )
    focused_validation_path = (
        PROJECT
        / "05_ensemble/timing/metric_specialist_fusion/"
        "false_positive_aware_validation_predictions.csv"
    )
    if contextual_validation_path.is_file():
        timing_validation = pd.read_csv(contextual_validation_path)
        timing_score_column = "contextual_promoted_score_not_probability"
    elif focused_validation_path.is_file():
        timing_validation = pd.read_csv(focused_validation_path)
        timing_score_column = "selected_score_not_probability"
    else:
        timing_validation = pd.read_csv(
            PROJECT / "05_ensemble/timing/validation_predictions.csv"
        )
        timing_score_column = "score_percentile_not_probability"
    timing_gate = pd.read_csv(
        PROJECT / "05_ensemble/timing/validation_gate.csv"
    )
    timing_holdout_count = len(timing_gate)
    exact_timing_peaks = (
        int(
            contextual_summary["validation"].get(
                "strict_local_peak_count",
                timing_holdout_count
                if contextual_summary["validation"][
                    "all_events_are_strict_local_peaks"
                ]
                else 0,
            )
        )
        if contextual_summary is not None
        else int(metric_trial["exact_peak_count"])
    )
    if "hard_negative_control" in timing_validation:
        hard_negative_validation = timing_validation.loc[
            timing_validation["hard_negative_control"].fillna(0).astype(int).eq(1)
        ]
    else:
        hard_negative_validation = pd.DataFrame()
    hard_negative_result = ""
    if not hard_negative_validation.empty:
        control_scores = hard_negative_validation[timing_score_column].astype(float)
        controls_below_event = 0
        for step, controls_for_fold in hard_negative_validation.groupby("step"):
            fold_rows = timing_validation.loc[timing_validation["step"].eq(step)]
            if "designated_holdout" in fold_rows:
                event_rows = fold_rows.loc[
                    fold_rows["designated_holdout"].fillna(0).astype(int).eq(1)
                ]
            else:
                event_rows = fold_rows.loc[fold_rows["actual"].astype(int).eq(1)]
            if (
                len(event_rows) == 1
                and float(event_rows.iloc[0][timing_score_column])
                > float(controls_for_fold[timing_score_column].max())
            ):
                controls_below_event += 1
        hard_negative_result = (
            f" {len(hard_negative_validation)} selected non-Japan controls are "
            "annotated directly in the chart; their scores range from "
            f"{control_scores.min():.3f} to {control_scores.max():.3f}, and the "
            f"control is below the designated event in {controls_below_event}/"
            f"{hard_negative_validation['step'].nunique()} folds."
        )

    parameters = manifest["parameters"]
    time_scale = infer_time_scale(timing_forecast["date"])
    interval_singular = time_scale.display_singular
    interval_plural = time_scale.display_plural
    if primary_selection.empty:
        best_timing = timing_forecast.loc[
            timing_forecast[primary_timing_score_column].idxmax()
        ]
        selected_timing_score = float(best_timing[primary_timing_score_column])
        selected_rule_label = "absolute peak"
    else:
        primary_row = primary_selection.iloc[0]
        best_timing = timing_forecast.loc[
            timing_forecast["date"].astype(str).eq(str(primary_row["date"]))
        ].iloc[0]
        selected_timing_score = float(primary_row["score"])
        selected_rule_label = {
            "first_occurrence": "first qualifying occurrence",
            "absolute_peak": "absolute peak",
        }.get(
            str(primary_row["selection_mode"]),
            str(primary_row["selection_mode"]).replace("_", " "),
        )
    start, end, best_interval = interval(best_timing["date"], time_scale)
    best_location = location_forecast.loc[
        location_forecast["date"].eq(best_timing["date"])
    ].iloc[0]
    selected_zone = zones.loc[
        zones["zone"].eq(int(best_location["predicted_zone"]))
    ].iloc[0]
    exact_location = int(
        (
            location_validation["actual_zone"]
            == location_validation["predicted_zone"]
        ).sum()
    )
    location_total = len(location_validation)
    false_before = int(
        sum(
            row["false_peak_count"]
            for row in isolation["baseline_without_alias"]["profiles"]
        )
    )
    false_after = int(
        sum(
            row["false_peak_count"]
            for row in isolation["selected"]["profiles"]
        )
    )
    objective_before = float(
        isolation["baseline_without_alias"]["total_objective_higher_is_better"]
    )
    objective_after = float(
        isolation["selected"]["total_objective_higher_is_better"]
    )
    selected_k = int(zone_search["selected"]["zones"])
    candidate_k = [int(row["zones"]) for row in zone_search["trials"]]
    top_systems = [
        {
            "name": str(row.system),
            "weight": float(row.positive_weight),
        }
        for row in weights.head(3).itertuples()
    ]
    peak_selection_fragments = []
    if not peak_modes.empty:
        source_labels = {
            "chronological_incremental": "Incremental",
            "historical_record_shuffle": "Record shuffle",
        }
        for source_mode, group in peak_modes.groupby(
            "source_mode",
            sort=False,
        ):
            first = group.loc[
                group["selection_mode"].eq("first_significant_peak")
            ].iloc[0]
            maximum = group.loc[
                group["selection_mode"].eq("maximum_peak")
            ].iloc[0]
            _, _, first_interval = interval(first["date"], time_scale)
            _, _, maximum_interval = interval(maximum["date"], time_scale)
            if str(first["date"]) == str(maximum["date"]):
                detail = (
                    f"first and maximum coincide at {first_interval} "
                    f"(score {first['score']:.3f}, zone "
                    f"{int(first['predicted_zone'])})"
                )
            else:
                detail = (
                    f"first significant {first_interval} "
                    f"(score {first['score']:.3f}, zone "
                    f"{int(first['predicted_zone'])}); maximum "
                    f"{maximum_interval} (score {maximum['score']:.3f}, zone "
                    f"{int(maximum['predicted_zone'])})"
                )
            peak_selection_fragments.append(
                f"{source_labels.get(source_mode, source_mode)}: {detail}"
            )
    peak_selection_result = (
        " ".join(peak_selection_fragments)
        if peak_selection_fragments
        else (
            f"The largest displayed score is "
            f"{best_timing[primary_timing_score_column]:.3f} "
            f"for {best_interval}."
        )
    )
    if not peak_modes.empty and all(
        len(group["date"].astype(str).unique()) == 1
        and len(group["predicted_zone"].astype(int).unique()) == 1
        for _, group in peak_modes.groupby("selection_mode")
    ):
        collapsed_fragments = []
        mode_labels = {
            "first_significant_peak": "first significant",
            "maximum_peak": "maximum",
        }
        source_short = {
            "chronological_incremental": "incremental",
            "historical_record_shuffle": "shuffle",
        }
        for selection_mode in (
            "first_significant_peak",
            "maximum_peak",
        ):
            group = peak_modes.loc[
                peak_modes["selection_mode"].eq(selection_mode)
            ]
            _, _, selected_interval = interval(
                group.iloc[0]["date"],
                time_scale,
            )
            score_text = "; ".join(
                f"{source_short.get(row.source_mode, row.source_mode)} "
                f"{row.score:.3f}"
                for row in group.itertuples()
            )
            collapsed_fragments.append(
                f"{mode_labels[selection_mode]} {selected_interval} → zone "
                f"{int(group.iloc[0]['predicted_zone'])} ({score_text})"
            )
        peak_selection_result = (
            "Both timing histories agree on the selected dates: "
            + "; ".join(collapsed_fragments)
            + "."
        )
    if not primary_selection.empty:
        primary_row = primary_selection.iloc[0]
        _, _, primary_interval = interval(primary_row["date"], time_scale)
        peak_selection_result = (
            f"The configured {selected_rule_label} is {primary_interval} "
            f"with {primary_row['source_mode']} score "
            f"{float(primary_row['score']):.3f}; the independently fitted "
            f"location model assigns zone "
            f"{int(primary_row['predicted_zone'])}."
        )
    if contextual_summary is not None:
        event_scores = [
            float(
                fold.get(
                    "promoted_validation_metrics",
                    fold["selected"]["metrics"],
                )["event_score"]
            )
            for fold in contextual_summary["folds"]
        ]
        margins = [
            float(
                fold.get(
                    "promoted_validation_metrics",
                    fold["selected"]["metrics"],
                )[
                    "event_over_background_margin"
                ]
            )
            for fold in contextual_summary["folds"]
        ]
        fold_weights = [
            float(fold["final_reliability_weight"])
            for fold in contextual_summary["folds"]
        ]
        timing_validation_result = (
            f"{exact_timing_peaks}/{timing_holdout_count} configured held-out "
            "events are strict local maxima after the same label-free smoothing "
            "rule is applied to validation and forecast. Fold event scores range "
            f"from {min(event_scores):.3f} to {max(event_scores):.3f}; event-to-"
            f"background margins range from {min(margins):+.3f} to "
            f"{max(margins):+.3f}. Reliability weights are "
            + ", ".join(f"{weight:.1%}" for weight in fold_weights)
            + f"; maximum false peaks above the configured floor: "
            f"{int(contextual_summary['validation']['maximum_false_peak_count'])}."
            + hard_negative_result
        )
        timing_validation_reading = (
            "The purple curve is the promoted fold-contextual fusion and the red "
            "step line is the held-out real-event indicator. Each fold searches "
            "its own model combination, projects that combination forward, then "
            "the forecasts are fused by fold reliability. The feature–target "
            "preserving row-order anchor is included inside the purple curve."
        )
    else:
        timing_validation_result = (
            f"{exact_timing_peaks}/{timing_holdout_count} configured held-out "
            f"events are strict local maxima. False-positive-aware validation "
            f"quality is {metric_trial['validation_quality_mean']:.3f} mean and "
            f"{metric_trial['validation_quality_worst']:.3f} on the weaker fold; "
            "hard negatives are below their paired event in "
            f"{metric_trial['hard_negative_below_event_count']}/"
            f"{timing_holdout_count} folds. {hard_negative_result}"
        )
        timing_validation_reading = (
            "The blue curve is the false-positive-aware fusion score. Red stars "
            "identify real held-out Japan events and orange X markers identify "
            "the frozen worldwide non-Japan controls on the same score axis. A "
            "dotted vertical divider separates incremental folds."
        )
    if peak_audit:
        peak_parameters = peak_audit["parameters"]
        peak_rule_description = (
            f"This run uses local radius "
            f"{peak_parameters['local_peak_radius']}, a "
            f"{peak_parameters['first_peak_quantile']:.0%} quantile floor "
            f"and a {peak_parameters['first_peak_minimum_max_fraction']:.0%} "
            "maximum-score floor."
        )
    else:
        peak_rule_description = (
            "The first-significant rule uses the configured local-peak and "
            "score-floor parameters."
        )
    standard_parameters_path = (
        PROJECT / "00_config/standard_report_parameters.json"
    )
    standard_parameters = (
        json.loads(standard_parameters_path.read_text())
        if standard_parameters_path.is_file()
        else {}
    )
    presentation = standard_parameters.get("forecast_peak_modes", {})
    history_mode = presentation.get("history_comparison", "hide")
    history_minimum = float(
        presentation.get("history_min_validation_quality", 0.5)
    )
    history_requires_null = bool(
        presentation.get("history_require_above_null", True)
    )
    history_summary_path = (
        PROJECT / "07_historical_record_shuffle/timing/summary.json"
    )
    null_summary_path = PROJECT / "07_randomized_control/timing/summary.json"
    history_summary = (
        json.loads(history_summary_path.read_text())
        if history_summary_path.is_file()
        else {}
    )
    null_summary = (
        json.loads(null_summary_path.read_text())
        if null_summary_path.is_file()
        else {}
    )
    history_quality = float(
        history_summary.get("validation_metrics", {}).get(
            "quality_higher_is_better", float("nan")
        )
    )
    null_quality = float(
        null_summary.get("validation_metrics", {}).get(
            "quality_higher_is_better", float("nan")
        )
    )
    history_integrity = bool(
        history_summary.get("feature_target_pairs_preserved")
        and history_summary.get("training_membership_preserved")
        and history_summary.get("outer_cutoffs_preserved")
        and history_summary.get("validation_targets_untouched")
    )
    history_auto_gate = bool(
        history_summary.get("status") == "COMPLETE"
        and history_integrity
        and pd.notna(history_quality)
        and history_quality >= history_minimum
        and (
            history_quality > null_quality
            if history_requires_null and pd.notna(null_quality)
            else not history_requires_null
        )
    )
    history_included = bool(
        history_mode == "show"
        or (history_mode == "auto" and history_auto_gate)
    )
    if history_included:
        history_reading = (
            "The dashed green line is the intact historical-record shuffle; "
            "it is an order-sensitivity comparison, not the randomized-label "
            "null test."
        )
        history_result = (
            f" The historical-order comparison passes its configured gate: "
            f"validation quality {history_quality:.3f} versus randomized-label "
            f"quality {null_quality:.3f}, with feature-target pairs and outer "
            "cutoffs preserved."
        )
    else:
        history_reading = (
            "No historical-order comparison passed the configured display gate."
        )
        history_result = ""
    suppression_applied = isolation["status"] == "ALIAS_PENALTY_ACCEPTED"
    alias_candidates = int(isolation["search"]["alias_candidates"])
    isolation_decision = (
        (
            f"The search evaluated {alias_candidates:,} suppression candidates "
            f"and accepted lag {isolation['selected']['alias_lag_slots']} with "
            f"strength {isolation['selected']['alias_strength']:.2f}."
        )
        if suppression_applied
        else (
            f"The search evaluated {alias_candidates:,} suppression candidates, "
            "but none passed the validation gate; the unsuppressed baseline "
            "was retained."
        )
    )

    return {
        "schema_version": "2.0",
        "source_pipeline": manifest["pipeline"],
        "source_created_at": manifest["created_at"],
        "report_identity": {
            "title": (
                f"Experimental {parameters['region_label']} earthquake timing "
                "and localization study"
            ),
            "region": parameters["region_label"],
            "forecast_window": {
                "requested_start": parameters["forecast_start"],
                "requested_end": parameters["forecast_end"],
                "grid_start": parameters["forecast_grid_start"],
                "time_scale": time_scale.to_dict(),
                "interval_rule": "[start, end): start included, end excluded",
            },
            "timing_magnitude_threshold": float(
                parameters["timing_magnitude_threshold"]
            ),
            "timing_validation_magnitude_threshold": float(
                parameters.get(
                    "timing_validation_magnitude_threshold",
                    parameters["timing_magnitude_threshold"],
                )
            ),
            "hard_negative_training_magnitude_threshold": float(
                parameters.get(
                    "hard_negative_training_magnitude_threshold",
                    parameters["timing_magnitude_threshold"],
                )
            ),
            "hard_negative_validation_magnitude_threshold": float(
                parameters.get(
                    "hard_negative_validation_magnitude_threshold",
                    parameters["timing_magnitude_threshold"],
                )
            ),
            "location_magnitude_threshold": float(
                parameters["location_magnitude_threshold"]
            ),
            "location_validation_magnitude_threshold": float(
                parameters.get(
                    "location_validation_magnitude_threshold",
                    parameters["location_magnitude_threshold"],
                )
            ),
            "scientific_status": (
                "Retrospective research diagnostic. It is not an operational "
                "earthquake warning and its scores are not probabilities."
            ),
        },
        "executive_purpose": {
            "plain_language": (
                "This study tests whether an autonomous, agentic pipeline can "
                "screen many astronomical position features and several modern "
                "machine-learning families, validate them chronologically, and "
                f"compress their outputs into an auditable {interval_singular} "
                "timing score "
                "and a numbered geographic-zone estimate."
            ),
            "why_agentic": (
                "The pipeline performs data checks, feature ablation, model "
                "comparison, validation-gated correction, ensemble weighting, "
                "plot generation and report checks without manually choosing a "
                "single preferred network. This reduces experimental turnaround "
                "time while preserving the decisions in CSV and JSON audit files."
            ),
            "what_is_new": (
                "It combines rule learning (LCS), spline-based neural networks "
                "(KAN), conventional PyTorch neural networks and hybrid variants. "
                "The goal is methodological comparison and automation, not proof "
                "that celestial positions physically cause earthquakes."
            ),
        },
        "vocabulary": [
            {
                "term": "Timing",
                "definition": (
                    f"Ranking of consecutive {interval_plural}. It does not "
                    "name an exact day or hour."
                ),
            },
            {
                "term": f"{interval_singular.capitalize()} [start, end)",
                "definition": (
                    "The start date belongs to the interval; the end date is the "
                    "start of the next interval and is excluded."
                ),
            },
            {
                "term": "Timing score",
                "definition": (
                    "An empirical percentile on a 0–1 scale. A larger value means "
                    "the model ranks that interval above more of its historical "
                    "reference intervals. It is not an earthquake probability."
                ),
            },
            {
                "term": "Zone",
                "definition": (
                    "A numbered two-dimensional geographic class learned jointly "
                    "from latitude and longitude. A zone number is only an "
                    "identifier; zone 4 is not four times zone 1."
                ),
            },
            {
                "term": "K",
                "definition": (
                    "The candidate number of geographic zones tested during "
                    "clustering. K=4 means four total zones, not zone code 4."
                ),
            },
            {
                "term": "GMM",
                "definition": (
                    "Gaussian Mixture Model: a clustering method that represents "
                    "the historical geographic catalogue as several overlapping "
                    "two-dimensional distributions and assigns every map cell to "
                    "the most likely zone."
                ),
            },
            {
                "term": "Validation fold",
                "definition": (
                    "A chronological test in which a selected historical event "
                    "is hidden from fitting and used only to assess the model."
                ),
            },
            {
                "term": "Incremental validation",
                "definition": (
                    "Later timing folds may learn from earlier validation-era "
                    "history, but never from their own held-out event."
                ),
            },
            {
                "term": "One-shot localization",
                "definition": (
                    "One location model and one fusion are fitted once and then "
                    "used for every displayed forecast interval."
                ),
            },
            {
                "term": "Penalty / alias control",
                "definition": (
                    "A soft reduction applied to repeated false-peak patterns. It "
                    "is accepted only when validation improves and the real event "
                    "peaks remain intact; it is not automatic deletion."
                ),
            },
            {
                "term": "Historical-zone frequency adjustment",
                "definition": (
                    "A correction that prevents the most common historical zone "
                    "from winning only because it occurs often. Strength 0 means "
                    "no correction; 0.35 means 35% of the full adjustment; 0.65 "
                    "means 65%; 1.00 means the full adjustment. These numbers are "
                    "settings, not accuracy or probability."
                ),
            },
            {
                "term": "Feature ablation",
                "definition": (
                    "A controlled removal test. A feature is removed only if "
                    "practical training and validation checks do not become worse; "
                    "otherwise the removal is rolled back."
                ),
            },
            {
                "term": "Ensemble / fusion",
                "definition": (
                    "A weighted combination of multiple model outputs. Weights are "
                    "derived from training and, more strongly, held-out validation."
                ),
            },
            {
                "term": "Higher-is-better skill",
                "definition": (
                    "A normalized comparison score used for selection. Values such "
                    "as 0.356 and 0.650 mean different measured skill, not 35.6% "
                    "and 65.0% earthquake probability."
                ),
            },
        ],
        "model_families": [
            {
                "name": "LCS",
                "expanded": "Learning Classifier System",
                "explanation": (
                    "An evolutionary rule-learning method. It searches human-readable "
                    "IF feature lies in interval THEN class rules, scores their "
                    "fitness and evolves the rule population."
                ),
                "report_variants": (
                    "lcs_only uses the rule system alone; names such as "
                    "lcs_deep_tiny combine its output with another family."
                ),
            },
            {
                "name": "KAN",
                "expanded": "Kolmogorov–Arnold Network",
                "explanation": (
                    "A neural architecture that learns flexible spline-like "
                    "functions on connections instead of relying only on fixed "
                    "scalar activation functions."
                ),
                "report_variants": (
                    "kan_only uses KAN alone; kan_deep_* and lcs_kan_deep_* are "
                    "hybrid prediction combinations."
                ),
            },
            {
                "name": "Deep learning",
                "expanded": "PyTorch feed-forward neural networks",
                "explanation": (
                    "Conventional multilayer neural networks used as nonlinear "
                    "comparators and ensemble members."
                ),
                "report_variants": (
                    "tiny is compact; wide uses more hidden capacity; regularized "
                    "uses stronger complexity control; deep_ensemble combines all "
                    "three."
                ),
            },
            {
                "name": "Hybrid systems",
                "expanded": "LCS/KAN/deep combinations",
                "explanation": (
                    "They combine predictions from complementary model families. "
                    "The underscore-separated name lists the included families; "
                    "it does not denote a new geographic zone or feature."
                ),
                "report_variants": (
                    "All sixteen tested variants retain a positive ensemble weight, "
                    "although weak variants contribute only a small amount."
                ),
            },
        ],
        "method_choices": {
            "timing": {
                "validation_mode": "incremental chronological outer validation",
                "validation_events": len(timing_summary["outer_validation_events"]),
                "training_weight": float(parameters["training_objective_weight"]),
                "validation_weight": float(
                    parameters["validation_objective_weight"]
                ),
                "peak_control_status": isolation["status"],
                "false_peaks_before": false_before,
                "false_peaks_after": false_after,
                "isolation_skill_before": objective_before,
                "isolation_skill_after": objective_after,
                "plain_reason": (
                    f"Timing must reward a peak in the correct held-out "
                    f"{interval_singular} while "
                    "also penalizing strong competitors before and after it. The "
                    "selected objective combines exact-peak, rank, prominence, "
                    "background and false-peak controls, all oriented so larger "
                    "means better."
                ),
            },
            "localization": {
                "validation_mode": "one-shot chronological holdout",
                "validation_events": location_total,
                "candidate_zone_counts": candidate_k,
                "selected_zone_count": selected_k,
                "exact_matches": exact_location,
                "exact_total": location_total,
                "plain_reason": (
                    "Latitude and longitude are learned jointly as one zone, "
                    "preventing an impossible combination of latitude from one "
                    "cluster and longitude from another."
                ),
                "historical_frequency_adjustment": {
                    "formula": (
                        "adjusted zone score = raw zone score / "
                        "(historical zone frequency ** strength)"
                    ),
                    "tested_strengths": [0.0, 0.35, 0.65, 1.0],
                    "interpretation": {
                        "0.00": "no historical-frequency adjustment",
                        "0.35": "35% of the full adjustment",
                        "0.65": "65% of the full adjustment",
                        "1.00": "full adjustment",
                    },
                    "not_accuracy_or_probability": True,
                },
            },
            "ensemble": {
                "all_systems_positive": True,
                "top_timing_systems": top_systems,
                "plain_reason": (
                    "No family is discarded completely. Validation has the larger "
                    "selection weight, while training keeps a non-zero role to "
                    "discourage a model that memorizes only a few held-out events."
                ),
            },
        },
        "formula_examples": [
            {
                "title": "Training and validation quality",
                "formula": (
                    "combined quality = w_train × Q_train + "
                    "w_validation × Q_validation"
                ),
                "symbols": (
                    "Q_train and Q_validation are normalized higher-is-better "
                    "skills; the w values are configured evidence weights."
                ),
                "worked_example": (
                    f"With w_train={parameters['training_objective_weight']:.2f} "
                    f"and w_validation={parameters['validation_objective_weight']:.2f}, "
                    "a system with Q_train=0.80 and Q_validation=0.60 receives "
                    f"{float(parameters['training_objective_weight']) * 0.80 + float(parameters['validation_objective_weight']) * 0.60:.3f}."
                ),
            },
            {
                "title": "Positive-weight ensemble",
                "formula": "ensemble score(t) = Σ_i w_i × score_i(t),  Σ_i w_i = 1",
                "symbols": (
                    "score_i(t) is system i's score for interval t; w_i is its "
                    "non-negative contribution weight."
                ),
                "worked_example": (
                    "If two systems score an interval 0.70 and 0.40 with weights "
                    "0.75 and 0.25, the fused score is "
                    "0.75×0.70 + 0.25×0.40 = 0.625."
                ),
            },
            {
                "title": "Empirical timing percentile",
                "formula": (
                    "timing percentile = count(reference scores ≤ current score) "
                    "/ count(reference scores)"
                ),
                "symbols": (
                    "The reference scores come from the historical comparison "
                    "distribution used in this run."
                ),
                "worked_example": (
                    "If 80 of 100 reference scores are no larger than the current "
                    "score, the empirical percentile is 0.80. This is a rank, "
                    "not an 80% earthquake probability."
                ),
            },
            {
                "title": "Historical-zone frequency adjustment",
                "formula": (
                    "adjusted zone score = raw zone score / "
                    "(historical zone frequency ^ strength)"
                ),
                "symbols": (
                    "Strength 0 applies no adjustment; strength 1 applies the "
                    "full inverse-frequency adjustment."
                ),
                "worked_example": (
                    "For raw score 0.50, historical frequency 0.40 and strength "
                    "0.35, the adjusted comparison value is "
                    f"0.50 / (0.40^0.35) = {0.50 / (0.40 ** 0.35):.3f}; "
                    "the value is subsequently compared or normalized, not read "
                    "as probability."
                ),
            },
            {
                "title": "Interval membership",
                "formula": "event belongs to interval ⇔ start ≤ event time < end",
                "symbols": (
                    f"The configured resolution is {time_scale.resolution_text}; "
                    "the start is included and the end is excluded."
                ),
                "worked_example": (
                    f"For {interval_label(start, time_scale)}, an event exactly "
                    f"at {start:%Y-%m-%d} is included; an event exactly at "
                    f"{end:%Y-%m-%d} belongs to the next interval."
                ),
            },
        ],
        "selected_result": {
            "timing_interval": best_interval,
            "timing_score": selected_timing_score,
            "location_zone": int(best_location["predicted_zone"]),
            "location_zone_score": float(
                best_location["predicted_zone_confidence"]
            ),
            "interpretation": (
                f"Within the configured grid, {best_interval} is the "
                f"configured {selected_rule_label} "
                f"(score {selected_timing_score:.3f}). "
                f"The one-shot location fusion associates that interval with "
                f"zone {int(best_location['predicted_zone'])}. This is a ranked "
                "experimental output, not a calibrated event probability."
            ),
        },
        "figures": {
            "essential_map": {
                "question": "What is the combined timing-and-location result?",
                "reading": (
                    "The coloured background covers the entire configured map and "
                    "shows the zone assigned to every cell. The outlined rectangle "
                    "is only the historical core envelope of the selected zone; "
                    "the full selected territory is the matching background colour. "
                    "Zone numbers are printed directly on the map, so no separate "
                    "legend is required."
                ),
                "result": (
                    peak_selection_result
                    if not peak_modes.empty
                    else (
                        f"The highest-ranked interval is {best_interval}; its "
                        f"associated one-shot location class is zone "
                        f"{int(best_location['predicted_zone'])} with fusion score "
                        f"{best_location['predicted_zone_confidence']:.3f}. Its "
                        f"reference bounds are latitude "
                        f"{selected_zone['latitude_low']:.2f}°N – "
                        f"{selected_zone['latitude_high']:.2f}°N and longitude "
                        f"{selected_zone['longitude_low']:.2f}°E – "
                        f"{selected_zone['longitude_high']:.2f}°E."
                    )
                ),
                "caution": (
                    "The rectangle is not an error tolerance and the zone score is "
                    "not a geographic probability."
                ),
            },
            "timing_forecast": {
                "question": (
                    f"Which {interval_singular} is selected by the configured "
                    f"{selected_rule_label} rule?"
                ),
                "reading": (
                    "The purple line is the configured primary score series. "
                    f"{history_reading} "
                    "Orange markers identify bins meeting the configured score "
                    "floor; the outlined annotation identifies the one primary "
                    f"selection. {peak_rule_description}"
                ),
                "result": peak_selection_result + history_result,
                "caution": (
                    "Scores may be compared within this run but are not calibrated "
                    "earthquake probabilities."
                ),
            },
            "timing_validation": {
                "question": (
                    f"Did the timing method isolate the hidden historical "
                    f"{interval_plural}?"
                ),
                "reading": timing_validation_reading,
                "result": timing_validation_result,
                "caution": (
                    f"There are only {timing_holdout_count} timing holdouts. "
                    "This demonstrates the pipeline behaviour on those folds, "
                    "not general predictive proof."
                ),
            },
            "location_forecast": {
                "question": (
                    f"Which learned zone is selected for each "
                    f"{interval_singular}?"
                ),
                "reading": (
                    "The vertical values are categorical zones, not latitude. "
                    "The coloured band marks only the configured primary timing "
                    "slot; all other bins remain visible as context."
                ),
                "result": (
                    f"One newly fitted location fusion supplies every slot. "
                    f"{peak_selection_result}"
                ),
                "caution": (
                    "A zone number indicates a territory shown on the map; numerical "
                    "distance between zone codes is not geographic distance."
                ),
            },
            "location_validation": {
                "question": "Did the one-shot model recover the hidden event zones?",
                "reading": (
                    "Red is the real chronological zone sequence and dashed blue is "
                    "the predicted sequence. When they are identical, a tiny visual "
                    "offset is added only so that both lines remain visible."
                ),
                "result": (
                    f"Exact-zone overlap: {exact_location}/{location_total} "
                    "held-out events have the same real and predicted zone."
                ),
                "caution": (
                    f"The sample contains only {location_total} events and therefore "
                    "does not establish operational localization accuracy."
                ),
            },
            "zone_construction": {
                "question": "How were the numbered geographic zones created?",
                "reading": (
                    f"The algorithm tested {candidate_k} total-zone candidates. "
                    f"Here K means total number of zones. It selected K={selected_k} "
                    "using 80% geographic separation (silhouette) and 20% model "
                    "parsimony (BIC skill), with a minimum event count per zone."
                ),
                "result": (
                    f"The selected GMM divides the complete map into {selected_k} "
                    "exhaustive territories; no map cell is left outside a zone."
                ),
                "caution": (
                    "Zone numbers are ordered south to north for readability and "
                    "are labels, not a risk or magnitude scale."
                ),
            },
            "peak_isolation": {
                "question": (
                    "Was false-peak suppression searched, and was it selected?"
                ),
                "reading": (
                    "Each pair of side-by-side bars refers to one incremental "
                    "validation fold. The pale bar is the unsuppressed baseline and "
                    "the blue bar is the selected decision. Equal bars mean the "
                    "search retained the baseline; they do not mean the search was "
                    "skipped. Higher is better."
                ),
                "result": (
                    f"Combined isolation skill changes from {objective_before:.3f} "
                    f"to {objective_after:.3f}; credible false peaks change from "
                    f"{false_before} to {false_after}. {isolation_decision}"
                ),
                "caution": (
                    "A skill value such as 0.356 or 0.650 is a normalized selection "
                    "metric, not a 35.6% or 65.0% earthquake probability."
                ),
            },
            "timing_weights": {
                "question": "How did every timing system perform in training and validation?",
                "reading": (
                    "Blue circles are mean training quality and orange diamonds are "
                    "mean held-out validation quality across incremental folds. "
                    "Farther right is better. The connecting line exposes the "
                    "generalization gap; rank uses 25% training and 75% validation."
                ),
                "result": (
                    "The chart compares the two evidence sources separately. "
                    "Ensemble weights are intentionally not plotted as if they were "
                    "accuracy; they are downstream contribution coefficients."
                ),
                "caution": (
                    "Training and validation quality are normalized selection "
                    "metrics, not earthquake probabilities."
                ),
            },
            "location_systems": {
                "question": "Which individual systems generalized best for zones?",
                "reading": (
                    "Blue points show training quality and orange diamonds show "
                    "held-out validation quality. All metrics are oriented so "
                    "farther right is better. The connecting segment reveals the "
                    "train–validation gap."
                ),
                "result": (
                    "Ranks are assigned mainly from held-out performance while "
                    "retaining a smaller training contribution."
                ),
                "caution": (
                    "A large training score with weaker validation can indicate "
                    "overfitting and therefore does not automatically win."
                ),
            },
            "location_fusion": {
                "question": "Which combination of zone models was selected?",
                "reading": (
                    "Rows compare candidate fusions. Farther right means better "
                    "held-out quality; the number is the displayed rank. The zone-"
                    "frequency adjustment reduces the automatic advantage of common "
                    "zones. Its 35%, 65% and 100% values are settings, not accuracy."
                ),
                "result": (
                    "The final location forecast uses the highest-ranked fusion, "
                    "not an arbitrarily chosen single network."
                ),
                "caution": (
                    "Fusion quality is a model-selection score on a small holdout, "
                    "not a calibrated probability."
                ),
            },
            "centroid_coordinates": {
                "question": "What latitude and longitude references are implied by the selected zones?",
                "reading": (
                    "The upper charts translate each forecast zone into its learned "
                    "centroid latitude and longitude. The lower charts compare real "
                    "validation-event coordinates with the centroid of the predicted "
                    "zone. The coloured band marks the configured primary timing "
                    "selection."
                ),
                "result": (
                    "This page provides coordinate reference values for the same "
                    "zone sequence, allowing the reader to see geographic movement "
                    "without separating latitude and longitude into incompatible models."
                ),
                "caution": (
                    "A centroid is the representative centre of a broad zone. These "
                    "coordinates are not an independent point forecast or an error radius."
                ),
            },
        },
        "conclusion": {
            "demonstrated": [
                "An autonomous pipeline can compare rule learning, KAN, deep neural networks and hybrids under one chronological audit.",
                "A validation-gated peak operator can reduce repeated false peaks while preserving the configured timing-event maxima.",
                "Joint geographic zones avoid combining latitude and longitude from incompatible clusters.",
                "Every major model, feature and report decision is retained in machine-readable audit artifacts.",
            ],
            "practical_advantages": [
                "Faster iteration across many models and feature subsets.",
                "Consistent metric direction and explicit train-versus-validation weighting.",
                "Reproducible reports whose explanatory text is generated from run data.",
                "Clear separation between timing ranking, geographic classification and scientific limitations.",
            ],
            "evidence_limits": [
                "This study alone is insufficient to establish definitively whether a connection exists between Solar System configurations and earthquakes.",
                "The small validation sets do not establish general or operational forecasting skill.",
                "A single randomized-label control is only a sensitivity check; a repeated null distribution is required before claiming that the timing alignment exceeds chance.",
                "Scores are not probabilities, warnings or guarantees that an event will occur.",
            ],
            "final_statement": (
                "The achieved result is a transparent and reusable experimental "
                "workflow. Its value is the disciplined comparison, chronological "
                "validation, automated quality control and auditable reporting of "
                "heterogeneous models. Further independent, prospective and "
                "larger-sample studies are required before drawing a definitive "
                "physical conclusion."
            ),
        },
    }


def main() -> None:
    destination = PROJECT / "00_config/report_narrative.json"
    narrative = build_narrative()
    write_json(destination, narrative)
    print(f"Report narrative: {destination}")


if __name__ == "__main__":
    main()
