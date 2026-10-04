#!/usr/bin/env python3
"""Build a parameter-driven event-time astronomical master for V20.

The source V19 master and catalogue are never modified.  Only Japan-region
events with a trusted, parseable timestamp are retained.  Historical records
whose midnight value is merely conventional are excluded.  Every event epoch
is deliberately reduced to the centre of its observed local six-hour band so
that the experiment does not claim minute-level timing precision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from build_jpl_safe_360d_master import (  # noqa: E402
    VECTOR_COLUMNS,
    build_astro_epochs_jd,
    fetch_vectors_for_body,
    read_body_specs,
)


META_COLUMNS = {
    "sample_time_utc",
    "sample_time_local",
    "feature_epoch_utc",
    "sample_kind",
    "event_id",
    "event_name",
    "place",
    "source",
    "mag",
    "latitude",
    "longitude",
    "depth",
    "target_band",
    "target_band_label",
    "candidate_band",
    "candidate_band_label",
    "forecast_slot_start",
    "forecast_slot_end",
}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--project-dir", type=Path, required=True)
    value.add_argument("--config", type=Path, default=None)
    value.add_argument("--reuse-download", action="store_true")
    return value


def resolve(project: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (project / path).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def time_band_label(labels: list[str], index: int) -> str:
    if not 0 <= index < len(labels):
        raise ValueError(f"Invalid time-band index: {index}")
    return str(labels[index])


def band_center(local_time: pd.Timestamp, band_hours: int) -> pd.Timestamp:
    band = int(local_time.hour // band_hours)
    center_hour = band * band_hours + band_hours / 2.0
    base = local_time.normalize()
    return base + pd.Timedelta(hours=center_hour)


def audit_catalog(frame: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    target = config["time_target"]
    bounds = config["japan_bounds"]
    trusted = {str(item) for item in config["trusted_sources"]}
    minimum_magnitude = float(config["minimum_magnitude"])
    timezone = str(target["timezone"])
    band_hours = int(target["band_hours"])
    labels = list(target["band_labels"])
    if 24 % band_hours or len(labels) != 24 // band_hours:
        raise ValueError("band_hours must divide 24 and match band_labels")

    work = frame.copy()
    work["parsed_time_utc"] = pd.to_datetime(work["time"], utc=True, errors="coerce")
    numeric = {}
    for column in ("mag", "latitude", "longitude", "depth"):
        numeric[column] = pd.to_numeric(work.get(column), errors="coerce")
    work["mag_numeric"] = numeric["mag"]
    work["latitude_numeric"] = numeric["latitude"]
    work["longitude_numeric"] = numeric["longitude"]
    source_ok = work["source"].astype(str).isin(trusted)
    timestamp_ok = work["parsed_time_utc"].notna()
    magnitude_ok = work["mag_numeric"].ge(minimum_magnitude)
    bounds_ok = (
        work["latitude_numeric"].between(
            float(bounds["latitude_min"]), float(bounds["latitude_max"])
        )
        & work["longitude_numeric"].between(
            float(bounds["longitude_min"]), float(bounds["longitude_max"])
        )
    )
    year_ok = work["parsed_time_utc"].dt.year.ge(
        int(target.get("minimum_timestamp_year", 1900))
    )
    conventional_historical = (
        work["source"].astype(str).str.contains("historical", case=False, na=False)
        | work["event_id"].astype(str).str.contains(
            "historical_attachment", case=False, na=False
        )
    )
    selected = source_ok & timestamp_ok & magnitude_ok & bounds_ok & year_ok
    if bool(target.get("exclude_conventional_midnight_historical_records", True)):
        selected &= ~conventional_historical

    reasons = np.full(len(work), "selected", dtype=object)
    reasons[~source_ok.to_numpy()] = "untrusted_or_historical_source"
    reasons[~timestamp_ok.to_numpy()] = "missing_or_unparseable_timestamp"
    reasons[~magnitude_ok.to_numpy()] = "below_magnitude_threshold"
    reasons[~bounds_ok.to_numpy()] = "outside_configured_japan_region"
    reasons[~year_ok.fillna(False).to_numpy()] = "before_minimum_timestamp_year"
    reasons[conventional_historical.to_numpy()] = "conventional_historical_time"
    reasons[selected.to_numpy()] = "selected"
    work["v20_selection_reason"] = reasons

    events = work[selected].copy()
    events = events.sort_values("parsed_time_utc", kind="mergesort")
    events = events.drop_duplicates("event_id", keep="last").reset_index(drop=True)
    local = events["parsed_time_utc"].dt.tz_convert(timezone)
    events["sample_time_local"] = local
    events["target_band"] = (local.dt.hour // band_hours).astype(int)
    events["target_band_label"] = events["target_band"].map(
        lambda item: time_band_label(labels, int(item))
    )
    centers_local = pd.Series(
        [band_center(value, band_hours) for value in local], index=events.index
    )
    events["feature_epoch_utc"] = centers_local.dt.tz_convert("UTC")
    events["time_approximation_minutes"] = (
        (events["feature_epoch_utc"] - events["parsed_time_utc"])
        .dt.total_seconds()
        .div(60.0)
    )
    return events, work


def forecast_candidates(config: dict) -> pd.DataFrame:
    target = config["time_target"]
    forecast = config["forecast"]
    timezone = str(target["timezone"])
    band_hours = int(target["band_hours"])
    labels = list(target["band_labels"])
    stride = int(forecast["sample_stride_days"])
    rows = []
    for slot in forecast["slots"]:
        start = pd.Timestamp(slot["start"])
        end = pd.Timestamp(slot["end"])
        if end < start:
            raise ValueError(f"Forecast slot ends before it starts: {slot}")
        days = list(pd.date_range(start, end, freq=f"{stride}D"))
        if days[-1] != end:
            days.append(end)
        for day in days:
            for band in range(24 // band_hours):
                center_hour = band * band_hours + band_hours / 2.0
                local = day.tz_localize(timezone) + pd.Timedelta(hours=center_hour)
                rows.append(
                    {
                        "sample_time_utc": "",
                        "sample_time_local": local.isoformat(),
                        "feature_epoch_utc": local.tz_convert("UTC"),
                        "sample_kind": "forecast_candidate",
                        "event_id": "",
                        "event_name": "",
                        "place": "",
                        "source": "",
                        "mag": 0.0,
                        "latitude": np.nan,
                        "longitude": np.nan,
                        "depth": np.nan,
                        "target_band": -1,
                        "target_band_label": "",
                        "candidate_band": band,
                        "candidate_band_label": time_band_label(labels, band),
                        "forecast_slot_start": start.strftime("%Y-%m-%d"),
                        "forecast_slot_end": end.strftime("%Y-%m-%d"),
                    }
                )
    return pd.DataFrame(rows)


def event_rows(events: pd.DataFrame) -> pd.DataFrame:
    rows = pd.DataFrame(
        {
            "sample_time_utc": events["parsed_time_utc"].map(lambda x: x.isoformat()),
            "sample_time_local": events["sample_time_local"].map(lambda x: x.isoformat()),
            "feature_epoch_utc": events["feature_epoch_utc"],
            "sample_kind": "event",
            "event_id": events["event_id"].astype(str),
            "event_name": events.get("event_name", "").astype(str),
            "place": events.get("place", "").astype(str),
            "source": events["source"].astype(str),
            "mag": events["mag_numeric"].astype(float),
            "latitude": events["latitude_numeric"].astype(float),
            "longitude": events["longitude_numeric"].astype(float),
            "depth": pd.to_numeric(events.get("depth"), errors="coerce"),
            "target_band": events["target_band"].astype(int),
            "target_band_label": events["target_band_label"].astype(str),
            "candidate_band": -1,
            "candidate_band_label": "",
            "forecast_slot_start": "",
            "forecast_slot_end": "",
        }
    )
    return rows


def vector_column(body: str, field: str) -> str:
    return (
        f"body:{body}|center:at399|frame:ICRF_J2000|"
        f"eph:{field}|op:val"
    )


def add_calendar_features(frame: pd.DataFrame, requested: list[str]) -> list[str]:
    timestamps = pd.to_datetime(frame["feature_epoch_utc"], utc=True)
    month = timestamps.dt.month.to_numpy(float)
    day = timestamps.dt.dayofyear.to_numpy(float)
    added = []
    if "month" in requested:
        frame["calendar_month"] = month
        added.append("calendar_month")
    if "month_sin" in requested:
        frame["calendar_month_sin"] = np.sin(2.0 * np.pi * (month - 1.0) / 12.0)
        added.append("calendar_month_sin")
    if "month_cos" in requested:
        frame["calendar_month_cos"] = np.cos(2.0 * np.pi * (month - 1.0) / 12.0)
        added.append("calendar_month_cos")
    if "doy_sin" in requested:
        frame["calendar_doy_sin"] = np.sin(2.0 * np.pi * day / 365.2425)
        added.append("calendar_doy_sin")
    if "doy_cos" in requested:
        frame["calendar_doy_cos"] = np.cos(2.0 * np.pi * day / 365.2425)
        added.append("calendar_doy_cos")

    phase_requested = bool(
        {"moon_phase_fraction", "moon_elongation_cos"}.intersection(requested)
    )
    if phase_requested:
        sun = frame[[vector_column("sun", field) for field in ("x", "y", "z")]].to_numpy(float)
        moon = frame[[vector_column("moon", field) for field in ("x", "y", "z")]].to_numpy(float)
        denominator = np.linalg.norm(sun, axis=1) * np.linalg.norm(moon, axis=1)
        elongation = np.divide(
            np.sum(sun * moon, axis=1),
            denominator,
            out=np.zeros(len(frame), dtype=float),
            where=denominator > 0,
        )
        elongation = np.clip(elongation, -1.0, 1.0)
        if "moon_elongation_cos" in requested:
            frame["moon_elongation_cos_at_band_center"] = elongation
            added.append("moon_elongation_cos_at_band_center")
        if "moon_phase_fraction" in requested:
            frame["moon_phase_fraction_at_band_center"] = (1.0 - elongation) / 2.0
            added.append("moon_phase_fraction_at_band_center")
    return added


def main() -> None:
    args = parser().parse_args()
    project = args.project_dir.resolve()
    config_path = args.config or project / "00_config/pipeline_request.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    catalog_path = resolve(project, config["catalog_csv"])
    body_path = resolve(project, config["body_csv"])
    output_path = project / "01_inputs/event_time_master.csv"
    audit_path = project / "02_audit/event_time_master_manifest.json"
    event_audit_path = project / "02_audit/event_timestamp_selection.csv"

    catalog = pd.read_csv(catalog_path, low_memory=False)
    events, catalog_audit = audit_catalog(catalog, config)
    catalog_audit.to_csv(event_audit_path, index=False)
    event_frame = event_rows(events)
    candidates = forecast_candidates(config)
    combined = pd.concat([event_frame, candidates], ignore_index=True)
    combined["feature_epoch_utc"] = pd.to_datetime(
        combined["feature_epoch_utc"], utc=True
    )

    expected_classes = 24 // int(config["time_target"]["band_hours"])
    class_counts = (
        event_frame["target_band"].value_counts().sort_index().to_dict()
    )
    if len(events) < int(config["time_target"]["required_outer_validation_events"]) + 8:
        raise ValueError("Too few trusted events for chronological V20 validation")
    if len(class_counts) != expected_classes:
        raise ValueError(f"Trusted event set does not represent every time band: {class_counts}")

    epochs = sorted(
        {
            float(value)
            for value in build_astro_epochs_jd(
                [item.to_pydatetime().replace(tzinfo=None) for item in combined["feature_epoch_utc"]],
                "none",
                0.0,
            )
        }
    )
    if args.reuse_download and output_path.is_file() and audit_path.is_file():
        print(f"Reusing event-time JPL master: {output_path}")
        return

    jpl = config["jpl_master"]
    specs = read_body_specs(body_path, str(jpl.get("moon_center", "earth")))
    vectors_by_body: dict[str, dict[float, dict]] = {}
    body_audit = []
    for index, spec in enumerate(specs, start=1):
        print(f"[{index}/{len(specs)}] JPL event-time vectors: {spec.name}", flush=True)
        vectors, meta = fetch_vectors_for_body(
            spec,
            epochs,
            str(jpl.get("refplane", "earth")),
            int(jpl.get("chunk_size", 70)),
            float(jpl.get("sleep_seconds", 0.2)),
            int(jpl.get("max_retries", 6)),
        )
        vectors_by_body[spec.name] = {
            round(epoch, 9): row for epoch, row in zip(epochs, vectors)
        }
        body_audit.append(meta)

    row_epochs = build_astro_epochs_jd(
        [item.to_pydatetime().replace(tzinfo=None) for item in combined["feature_epoch_utc"]],
        "none",
        0.0,
    )
    vector_features = []
    for spec in specs:
        available = set(vectors_by_body[spec.name][round(epochs[0], 9)])
        fields = [field for field in VECTOR_COLUMNS if field in available]
        for field in fields:
            column = vector_column(spec.name, field)
            combined[column] = [
                vectors_by_body[spec.name][round(epoch, 9)][field]
                for epoch in row_epochs
            ]
            vector_features.append(column)
    calendar_features = add_calendar_features(
        combined, list(config["feature_controls"].get("calendar_features", []))
    )
    feature_names = vector_features + calendar_features
    if not np.isfinite(combined[feature_names].to_numpy(float)).all():
        raise ValueError("Non-finite value in V20 astronomical features")
    forbidden = [
        name for name in feature_names
        if any(token in name.lower() for token in ("hour", "minute", "second", "target_band", "candidate_band"))
    ]
    if forbidden:
        raise ValueError(f"Direct time-target leakage in feature columns: {forbidden}")
    combined["feature_epoch_utc"] = combined["feature_epoch_utc"].map(
        lambda item: item.isoformat()
    )
    combined.to_csv(output_path, index=False)

    holdouts = int(config["time_target"]["required_outer_validation_events"])
    outer = event_frame.tail(holdouts)
    manifest = {
        "schema": "v20.event_time_master.v1",
        "status": "COMPLETE",
        "experimental": True,
        "catalog": str(catalog_path),
        "catalog_sha256": sha256(catalog_path),
        "body_csv": str(body_path),
        "body_csv_sha256": sha256(body_path),
        "trusted_event_rows": int(len(event_frame)),
        "excluded_catalog_rows": int(len(catalog_audit) - len(event_frame)),
        "event_class_counts": {str(k): int(v) for k, v in class_counts.items()},
        "outer_validation_events": int(holdouts),
        "outer_validation_distinct_bands": int(outer["target_band"].nunique()),
        "outer_validation_class_counts": {
            str(k): int(v)
            for k, v in outer["target_band"].value_counts().sort_index().to_dict().items()
        },
        "non_japan_hard_negative_rows": 0,
        "timestamp_policy": {
            "trusted_sources": config["trusted_sources"],
            "timezone": config["time_target"]["timezone"],
            "band_hours": config["time_target"]["band_hours"],
            "feature_epoch_policy": config["time_target"]["feature_epoch_policy"],
            "historical_conventional_midnight_excluded": True,
        },
        "forecast_candidate_rows": int(len(candidates)),
        "unique_jpl_epochs": int(len(epochs)),
        "available_body_count": int(len(specs)),
        "bodies": body_audit,
        "feature_count": int(len(feature_names)),
        "vector_feature_count": int(len(vector_features)),
        "calendar_feature_count": int(len(calendar_features)),
        "feature_names": feature_names,
        "forbidden_direct_time_features_present": False,
        "source_master_untouched": True,
        "output_csv": str(output_path),
        "output_sha256": sha256(output_path),
    }
    write_json(audit_path, manifest)
    print(json.dumps(manifest, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
