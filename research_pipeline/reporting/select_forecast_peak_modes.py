#!/usr/bin/env python3
"""Select first-significant and global-maximum forecast slots.

The selection is data-driven and is evaluated independently for the
chronological incremental forecast and the intact historical-record shuffle.
Selected timing slots are then joined to the one-shot localization forecast.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


SOURCE_SPECS = (
    (
        "chronological_incremental",
        "05_ensemble/timing/forecast_predictions.csv",
        "score_percentile_not_probability",
    ),
    (
        "historical_record_shuffle",
        "07_historical_record_shuffle/timing/forecast.csv",
        "historical_record_shuffle_score",
    ),
)


def parser() -> argparse.ArgumentParser:
    script = Path(__file__).resolve()
    value = argparse.ArgumentParser(
        description=(
            "Select the earliest sufficiently strong local timing peak and "
            "the global maximum for each configured timing history."
        )
    )
    value.add_argument(
        "--project-dir",
        default=str(script.parents[1]),
    )
    value.add_argument(
        "--first-peak-quantile",
        type=float,
        default=0.75,
        help="Empirical-score quantile used as one significance floor.",
    )
    value.add_argument(
        "--first-peak-minimum-max-fraction",
        type=float,
        default=0.85,
        help="The first significant peak must also reach this fraction of max.",
    )
    value.add_argument(
        "--local-peak-radius",
        type=int,
        default=1,
    )
    value.add_argument(
        "--include-boundary-peaks",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    value.add_argument(
        "--first-peak-not-before",
        default=None,
        help=(
            "Optional inclusive bin-start floor for first-significant-peak "
            "selection; the global maximum remains defined on the full horizon."
        ),
    )
    value.add_argument(
        "--primary-selection",
        choices=("first_occurrence", "absolute_peak"),
        default="absolute_peak",
        help=(
            "Single selection used to focus the forecast and localization "
            "report. The two diagnostic peak modes remain audited separately."
        ),
    )
    value.add_argument(
        "--primary-score-csv",
        default=None,
        help=(
            "Optional score series used for the primary selection. Relative "
            "paths are resolved below the project directory."
        ),
    )
    value.add_argument("--primary-score-column", default=None)
    value.add_argument(
        "--primary-source-label",
        default=None,
        help="Reader-facing identifier for the primary score series.",
    )
    value.add_argument(
        "--first-occurrence-threshold",
        type=float,
        default=None,
        help=(
            "Inclusive score floor for first_occurrence. It is required when "
            "that primary-selection mode is requested."
        ),
    )
    value.add_argument(
        "--first-occurrence-fallback",
        choices=("absolute_peak", "error"),
        default="absolute_peak",
    )
    return value


def local_peak_indices(
    values: np.ndarray,
    radius: int,
    include_boundaries: bool,
) -> list[int]:
    peaks: list[int] = []
    for index, value in enumerate(values):
        left = max(0, index - radius)
        right = min(len(values), index + radius + 1)
        if not include_boundaries and (
            index - radius < 0 or index + radius >= len(values)
        ):
            continue
        neighbours = np.delete(values[left:right], index - left)
        if len(neighbours) and value >= neighbours.max() and np.any(
            value > neighbours
        ):
            peaks.append(index)
    return peaks


def selection_rows(
    source_mode: str,
    frame: pd.DataFrame,
    score_column: str,
    location: pd.DataFrame,
    args: argparse.Namespace,
) -> tuple[list[dict], dict]:
    scores = frame[score_column].to_numpy(float)
    maximum_index = int(np.nanargmax(scores))
    quantile_floor = float(np.nanquantile(scores, args.first_peak_quantile))
    maximum_fraction_floor = float(
        args.first_peak_minimum_max_fraction * scores[maximum_index]
    )
    threshold = max(quantile_floor, maximum_fraction_floor)
    local_peaks = local_peak_indices(
        scores,
        args.local_peak_radius,
        args.include_boundary_peaks,
    )
    first_peak_floor = (
        pd.Timestamp(args.first_peak_not_before)
        if args.first_peak_not_before
        else None
    )
    significant = []
    for index in local_peaks:
        if scores[index] < threshold:
            continue
        if (
            first_peak_floor is not None
            and pd.Timestamp(frame.iloc[index]["date"]) < first_peak_floor
        ):
            continue
        significant.append(index)
    if significant:
        first_index = significant[0]
    elif first_peak_floor is not None:
        eligible = [
            index
            for index in range(len(frame))
            if pd.Timestamp(frame.iloc[index]["date"]) >= first_peak_floor
        ]
        if not eligible:
            raise RuntimeError(
                "No forecast bin starts on or after --first-peak-not-before"
            )
        first_index = max(eligible, key=lambda index: scores[index])
    else:
        first_index = maximum_index
    fallback = not significant
    rows: list[dict] = []
    for selection_mode, index in (
        ("first_significant_peak", first_index),
        ("maximum_peak", maximum_index),
    ):
        timing_row = frame.iloc[index]
        matches = location.loc[
            location["date"].astype(str).eq(str(timing_row["date"]))
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"Localization join is not one-to-one for {timing_row['date']}"
            )
        location_row = matches.iloc[0]
        rows.append(
            {
                "source_mode": source_mode,
                "selection_mode": selection_mode,
                "date": str(timing_row["date"]),
                "slot_end_inclusive": str(timing_row["slot_end_inclusive"]),
                "score": float(scores[index]),
                "score_column": score_column,
                "significance_threshold": threshold,
                "quantile_floor": quantile_floor,
                "maximum_fraction_floor": maximum_fraction_floor,
                "is_local_peak": bool(index in local_peaks),
                "first_peak_fell_back_to_maximum": bool(
                    fallback and selection_mode == "first_significant_peak"
                ),
                "coincides_with_other_selection": bool(
                    first_index == maximum_index
                ),
                "predicted_zone": int(location_row["predicted_zone"]),
                "predicted_zone_confidence": float(
                    location_row["predicted_zone_confidence"]
                ),
                "zone_center_latitude": float(
                    location_row["zone_center_latitude"]
                ),
                "zone_center_longitude": float(
                    location_row["zone_center_longitude"]
                ),
            }
        )
    audit = {
        "source_mode": source_mode,
        "score_column": score_column,
        "score_count": len(scores),
        "local_peak_indices": local_peaks,
        "local_peak_dates": [
            str(frame.iloc[index]["date"]) for index in local_peaks
        ],
        "quantile_floor": quantile_floor,
        "maximum_fraction_floor": maximum_fraction_floor,
        "significance_threshold": threshold,
        "first_significant_index": first_index,
        "maximum_index": maximum_index,
        "coincident": first_index == maximum_index,
        "fallback_to_maximum": fallback,
        "first_peak_not_before": (
            first_peak_floor.date().isoformat()
            if first_peak_floor is not None
            else None
        ),
    }
    return rows, audit


def main() -> None:
    args = parser().parse_args()
    if not 0 <= args.first_peak_quantile <= 1:
        raise ValueError("first-peak-quantile must be within [0, 1]")
    if not 0 < args.first_peak_minimum_max_fraction <= 1:
        raise ValueError(
            "first-peak-minimum-max-fraction must be within (0, 1]"
        )
    if args.local_peak_radius < 1:
        raise ValueError("local-peak-radius must be positive")
    if args.first_occurrence_threshold is not None and not (
        0.0 <= args.first_occurrence_threshold <= 1.0
    ):
        raise ValueError("first-occurrence-threshold must be within [0, 1]")
    if (
        args.primary_selection == "first_occurrence"
        and args.first_occurrence_threshold is None
    ):
        raise ValueError(
            "first_occurrence requires --first-occurrence-threshold"
        )

    project = Path(args.project_dir).expanduser().resolve()
    location_path = project / "05_ensemble/location_zone_forecast.csv"
    location = pd.read_csv(location_path)
    rows: list[dict] = []
    source_audits: list[dict] = []
    for source_mode, relative_path, score_column in SOURCE_SPECS:
        path = project / relative_path
        frame = pd.read_csv(path)
        if frame["date"].astype(str).tolist() != location[
            "date"
        ].astype(str).tolist():
            raise RuntimeError(
                f"{source_mode} and localization do not share one forecast grid"
            )
        selected, audit = selection_rows(
            source_mode,
            frame,
            score_column,
            location,
            args,
        )
        rows.extend(selected)
        audit["path"] = str(path)
        source_audits.append(audit)

    output = pd.DataFrame(rows)
    destination = project / "05_ensemble/timing/forecast_peak_modes.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(destination, index=False)

    if args.primary_score_csv:
        primary_score_path = Path(args.primary_score_csv).expanduser()
        if not primary_score_path.is_absolute():
            primary_score_path = project / primary_score_path
    else:
        primary_score_path = project / SOURCE_SPECS[0][1]
    primary_score_path = primary_score_path.resolve()
    primary_score_column = (
        args.primary_score_column or SOURCE_SPECS[0][2]
    )
    primary_scores = pd.read_csv(primary_score_path)
    required_primary_columns = {"date", primary_score_column}
    missing_primary_columns = sorted(
        required_primary_columns.difference(primary_scores.columns)
    )
    if missing_primary_columns:
        raise ValueError(
            f"Primary score CSV is missing columns: {missing_primary_columns}"
        )
    if primary_scores["date"].astype(str).tolist() != location[
        "date"
    ].astype(str).tolist():
        raise RuntimeError(
            "Primary score series and localization do not share one forecast grid"
        )
    values = primary_scores[primary_score_column].to_numpy(float)
    primary_eligible = np.ones(len(primary_scores), dtype=bool)
    if args.first_peak_not_before:
        primary_dates = pd.to_datetime(primary_scores["date"], errors="raise")
        primary_eligible &= primary_dates.ge(
            pd.Timestamp(args.first_peak_not_before)
        ).to_numpy()
    if not primary_eligible.any():
        raise RuntimeError(
            "No primary forecast row remains at or after "
            f"--first-peak-not-before={args.first_peak_not_before}"
        )
    primary_fallback_used = False
    if args.primary_selection == "first_occurrence":
        candidates = np.flatnonzero(
            primary_eligible
            & (values >= float(args.first_occurrence_threshold))
        )
        if len(candidates):
            primary_index = int(candidates[0])
        elif args.first_occurrence_fallback == "absolute_peak":
            eligible_indices = np.flatnonzero(primary_eligible)
            primary_index = int(
                eligible_indices[np.nanargmax(values[eligible_indices])]
            )
            primary_fallback_used = True
        else:
            raise RuntimeError(
                "No score reaches the configured first-occurrence threshold"
            )
    else:
        eligible_indices = np.flatnonzero(primary_eligible)
        primary_index = int(
            eligible_indices[np.nanargmax(values[eligible_indices])]
        )
    timing_row = primary_scores.iloc[primary_index]
    location_match = location.loc[
        location["date"].astype(str).eq(str(timing_row["date"]))
    ]
    if len(location_match) != 1:
        raise RuntimeError(
            f"Primary localization join is not one-to-one for {timing_row['date']}"
        )
    location_row = location_match.iloc[0]
    primary_source_label = (
        args.primary_source_label
        or primary_score_path.stem.replace("_", " ")
    )
    primary_row = {
        "source_mode": primary_source_label,
        "selection_mode": args.primary_selection,
        "date": str(timing_row["date"]),
        "slot_end_inclusive": str(
            timing_row.get(
                "slot_end_inclusive",
                location_row.get("slot_end_inclusive", ""),
            )
        ),
        "score": float(values[primary_index]),
        "score_column": primary_score_column,
        "score_csv": str(primary_score_path),
        "first_occurrence_threshold": args.first_occurrence_threshold,
        "fallback_used": primary_fallback_used,
        "predicted_zone": int(location_row["predicted_zone"]),
        "predicted_zone_confidence": float(
            location_row["predicted_zone_confidence"]
        ),
        "zone_center_latitude": float(location_row["zone_center_latitude"]),
        "zone_center_longitude": float(location_row["zone_center_longitude"]),
    }
    primary_destination = (
        project / "05_ensemble/timing/forecast_primary_selection.csv"
    )
    pd.DataFrame([primary_row]).to_csv(primary_destination, index=False)
    unique_slots = []
    for date, group in output.groupby("date", sort=False):
        unique_slots.append(
            {
                "date": date,
                "slot_end_inclusive": str(
                    group.iloc[0]["slot_end_inclusive"]
                ),
                "source_modes": sorted(group["source_mode"].unique()),
                "selection_modes": sorted(group["selection_mode"].unique()),
                "predicted_zone": int(group.iloc[0]["predicted_zone"]),
                "predicted_zone_confidence": float(
                    group.iloc[0]["predicted_zone_confidence"]
                ),
                "zone_center_latitude": float(
                    group.iloc[0]["zone_center_latitude"]
                ),
                "zone_center_longitude": float(
                    group.iloc[0]["zone_center_longitude"]
                ),
            }
        )
    audit = {
        "schema_version": "1.0",
        "status": "COMPLETE",
        "purpose": (
            "parameterized first-significant and maximum timing selections "
            "joined to the independently fitted one-shot localization forecast"
        ),
        "parameters": {
            "first_peak_quantile": args.first_peak_quantile,
            "first_peak_minimum_max_fraction": (
                args.first_peak_minimum_max_fraction
            ),
            "local_peak_radius": args.local_peak_radius,
            "include_boundary_peaks": args.include_boundary_peaks,
            "first_peak_not_before": args.first_peak_not_before,
            "primary_selection": args.primary_selection,
            "primary_score_csv": str(primary_score_path),
            "primary_score_column": primary_score_column,
            "primary_source_label": primary_source_label,
            "first_occurrence_threshold": args.first_occurrence_threshold,
            "first_occurrence_fallback": args.first_occurrence_fallback,
        },
        "location_forecast": str(location_path),
        "sources": source_audits,
        "selections": rows,
        "unique_selected_slots": unique_slots,
        "selection_csv": str(destination),
        "primary_selection": primary_row,
        "primary_selection_csv": str(primary_destination),
    }
    json_path = project / "05_ensemble/timing/forecast_peak_modes.json"
    json_path.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
