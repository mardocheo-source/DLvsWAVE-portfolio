"""Leakage-safe weekly dataset construction for the Japan megathrust study.

The source master supplies only compacted astronomical predictors.  Binary
labels are rebuilt from frozen event catalogues, and prospective rows retain a
missing target instead of being silently treated as negative observations.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from src.pretreatment import MasterPretreatmentEngine, PretreatmentConfig


TARGET_COLUMN = "japan_m77_event"
DATE_COLUMN = "date"
PI_DIGITS = (
    "31415926535897932384626433832795028841971693993751058209749445923078164062862089986280"
    "34825342117067982148086513282306647093844609550582231725359408128481117450284102701938"
)
PI_DIGIT_PAIRS = tuple(int(PI_DIGITS[index:index + 2]) for index in range(0, len(PI_DIGITS) - 1, 2))


@dataclass(frozen=True)
class BinaryDataConfig:
    magnitude_threshold: float = 7.7
    cutoff_utc: str = "2026-07-31T23:59:59Z"
    forecast_start: str = "2026-08-01"
    forecast_end: str = "2027-01-31"
    validation_event_count: int = 2
    validation_weeks_before: int = 13
    validation_weeks_after: int = 13
    japan_lat_min: float = 22.0
    japan_lat_max: float = 50.5
    japan_lon_min: float = 122.0
    japan_lon_max: float = 156.0


@dataclass
class TrialSplit:
    train: pd.DataFrame
    validation: pd.DataFrame
    validation_event_weeks: list[pd.Timestamp]
    validation_start: pd.Timestamp
    validation_corridor_index: pd.DataFrame
    training_background_chunks: pd.DataFrame


def week_start_utc(values: pd.Series | Iterable[object]) -> pd.Series:
    """Return timezone-naive Monday starts after parsing source times as UTC."""
    parsed = pd.to_datetime(pd.Series(values), utc=True, errors="coerce")
    normalized = parsed.dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()
    return normalized - pd.to_timedelta(normalized.dt.weekday, unit="D")


def _load_catalog(path: str | Path, threshold: float, cutoff: pd.Timestamp) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False)
    required = {"time", "mag", "latitude", "longitude"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Catalogue {path} lacks columns: {', '.join(missing)}")
    frame = frame.copy()
    frame["time"] = pd.to_datetime(frame["time"], utc=True, errors="coerce")
    frame["mag"] = pd.to_numeric(frame["mag"], errors="coerce")
    frame["latitude"] = pd.to_numeric(frame["latitude"], errors="coerce")
    frame["longitude"] = pd.to_numeric(frame["longitude"], errors="coerce")
    frame = frame.loc[
        frame["time"].notna()
        & frame["mag"].ge(float(threshold))
        & frame["time"].le(cutoff)
    ].copy()
    frame["week_start"] = week_start_utc(frame["time"])
    return frame.sort_values("time").reset_index(drop=True)


def _weekly_catalog_summary(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=[
                DATE_COLUMN,
                f"{prefix}_event_count",
                f"{prefix}_max_magnitude",
                f"{prefix}_event_ids",
            ]
        )
    id_column = "id" if "id" in frame.columns else None

    def identifiers(group: pd.DataFrame) -> str:
        if id_column:
            return "|".join(group[id_column].dropna().astype(str).unique())
        return ""

    grouped = frame.groupby("week_start", sort=True)
    output = grouped["mag"].agg(["size", "max"]).reset_index()
    output.columns = [DATE_COLUMN, f"{prefix}_event_count", f"{prefix}_max_magnitude"]
    ids = grouped.apply(identifiers, include_groups=False).rename(f"{prefix}_event_ids").reset_index(drop=True)
    output[f"{prefix}_event_ids"] = ids
    return output


def build_clean_binary_master(
    compacted_master_path: str | Path,
    japan_catalog_path: str | Path,
    world_catalog_path: str | Path,
    config: BinaryDataConfig,
) -> tuple[pd.DataFrame, list[str], dict[str, object]]:
    """Create an all-Japan 0/1 weekly master with foreign hard negatives.

    Only columns named ``packed_astro_container_*`` are admitted as model
    predictors.  This deliberately rejects contemporaneous seismic fields and
    their shifts from the source master.
    """
    master = pd.read_csv(compacted_master_path, low_memory=False)
    if DATE_COLUMN not in master.columns:
        raise ValueError("Compacted master lacks a date column")
    feature_columns = sorted(c for c in master.columns if c.startswith("packed_astro_container_"))
    if not feature_columns:
        raise ValueError("Compacted master has no packed_astro_container_* predictors")

    master = master[[DATE_COLUMN, *feature_columns]].copy()
    master[DATE_COLUMN] = pd.to_datetime(master[DATE_COLUMN], errors="coerce").dt.normalize()
    if master[DATE_COLUMN].isna().any():
        raise ValueError("Compacted master contains invalid dates")
    if master[DATE_COLUMN].duplicated().any():
        raise ValueError("Compacted master contains duplicate weekly dates")
    master = master.sort_values(DATE_COLUMN).reset_index(drop=True)

    cutoff = pd.Timestamp(config.cutoff_utc)
    if cutoff.tzinfo is None:
        cutoff = cutoff.tz_localize("UTC")
    else:
        cutoff = cutoff.tz_convert("UTC")
    cutoff_naive = cutoff.tz_localize(None)

    japan = _load_catalog(japan_catalog_path, config.magnitude_threshold, cutoff)
    world = _load_catalog(world_catalog_path, config.magnitude_threshold, cutoff)
    inside_extended_japan = (
        world["latitude"].between(config.japan_lat_min, config.japan_lat_max)
        & world["longitude"].between(config.japan_lon_min, config.japan_lon_max)
    )
    foreign = world.loc[~inside_extended_japan].copy()

    japan_weekly = _weekly_catalog_summary(japan, "japan")
    foreign_weekly = _weekly_catalog_summary(foreign, "foreign")
    clean = master.merge(japan_weekly, how="left", on=DATE_COLUMN)
    clean = clean.merge(foreign_weekly, how="left", on=DATE_COLUMN)

    for prefix in ("japan", "foreign"):
        clean[f"{prefix}_event_count"] = clean[f"{prefix}_event_count"].fillna(0).astype(int)
        clean[f"{prefix}_max_magnitude"] = pd.to_numeric(
            clean[f"{prefix}_max_magnitude"], errors="coerce"
        )
        clean[f"{prefix}_event_ids"] = clean[f"{prefix}_event_ids"].fillna("").astype(str)

    historical = clean[DATE_COLUMN].le(cutoff_naive)
    positive = historical & clean["japan_event_count"].gt(0)
    hard_negative = historical & ~positive & clean["foreign_event_count"].gt(0)
    clean[TARGET_COLUMN] = np.where(historical, positive.astype(float), np.nan)
    clean["is_japan_positive"] = positive.astype(np.int8)
    clean["is_world_hard_negative"] = hard_negative.astype(np.int8)
    clean["is_forecast"] = (~historical).astype(np.int8)
    clean["sample_role"] = np.select(
        [positive, hard_negative, ~historical],
        ["japan_positive", "foreign_hard_negative", "prospective_unlabelled"],
        default="quiet_negative",
    )

    forecast_start = pd.Timestamp(config.forecast_start)
    forecast_end = pd.Timestamp(config.forecast_end)
    forecast_rows = clean[DATE_COLUMN].between(forecast_start, forecast_end)
    if not forecast_rows.any():
        raise ValueError("The compacted master does not cover the requested forecast interval")

    summary: dict[str, object] = {
        "rows": int(len(clean)),
        "feature_count": int(len(feature_columns)),
        "historical_rows": int(historical.sum()),
        "prospective_rows": int((~historical).sum()),
        "forecast_rows": int(forecast_rows.sum()),
        "japan_catalog_events_at_or_above_threshold": int(len(japan)),
        "japan_positive_weeks": int(clean["is_japan_positive"].sum()),
        "world_catalog_events_at_or_above_threshold": int(len(world)),
        "foreign_hard_negative_events": int(len(foreign)),
        "foreign_hard_negative_weeks": int(clean["is_world_hard_negative"].sum()),
        "cutoff_utc": cutoff.isoformat(),
        "forecast_start": str(forecast_start.date()),
        "forecast_end": str(forecast_end.date()),
        "magnitude_threshold": float(config.magnitude_threshold),
        "validation_event_count": int(config.validation_event_count),
        "validation_weeks_before": int(config.validation_weeks_before),
        "validation_weeks_after": int(config.validation_weeks_after),
        "japan_extended_bbox": {
            "latitude": [config.japan_lat_min, config.japan_lat_max],
            "longitude": [config.japan_lon_min, config.japan_lon_max],
        },
    }
    return clean, feature_columns, summary


def _corridor_mask(dates: pd.Series, event_dates: Iterable[pd.Timestamp], before: int, after: int) -> np.ndarray:
    values = dates.to_numpy(dtype="datetime64[D]")
    mask = np.zeros(len(dates), dtype=bool)
    for event_date in event_dates:
        start = np.datetime64((pd.Timestamp(event_date) - pd.Timedelta(weeks=before)).date())
        end = np.datetime64((pd.Timestamp(event_date) + pd.Timedelta(weeks=after)).date())
        mask |= (values >= start) & (values <= end)
    return mask


def _pi_background_chunks(
    pool: pd.DataFrame,
    candidate_mask: np.ndarray,
    *,
    desired_count: int,
    chunk_weeks: int,
    seed: int,
) -> tuple[np.ndarray, pd.DataFrame]:
    """Select deterministic quiet chunks using successive two-digit pairs of pi.

    Candidates are split into contiguous weekly gaps between mandatory seismic
    corridors.  Each pi pair is mixed with the trial seed and iteration number
    to choose a gap and a contiguous start position.  The same inputs always
    return exactly the same rows and audit table.
    """
    desired_count = max(0, min(int(desired_count), int(np.sum(candidate_mask))))
    selected = np.zeros(len(pool), dtype=bool)
    columns = [
        "chunk_id", "pi_pair", "derived_seed", "gap_start", "gap_end",
        "chunk_start", "chunk_end", "row_count",
    ]
    if desired_count == 0:
        return selected, pd.DataFrame(columns=columns)

    positions = np.flatnonzero(candidate_mask)
    dates = pd.to_datetime(pool[DATE_COLUMN]).reset_index(drop=True)
    split_points = np.flatnonzero(
        (np.diff(positions) != 1)
        | (dates.iloc[positions[1:]].to_numpy() - dates.iloc[positions[:-1]].to_numpy() != np.timedelta64(7, "D"))
    ) + 1
    gaps = [values for values in np.split(positions, split_points) if len(values)]
    records: list[dict[str, object]] = []
    max_attempts = max(200, desired_count * 12)
    attempt = 0
    while int(selected.sum()) < desired_count and attempt < max_attempts:
        pair = PI_DIGIT_PAIRS[attempt % len(PI_DIGIT_PAIRS)]
        derived_seed = int((int(seed) * 1009 + pair * 9176 + attempt * 37) % (2**32 - 1))
        rng = np.random.default_rng(derived_seed)
        gap_index = int((pair + int(rng.integers(0, len(gaps)))) % len(gaps))
        gap = gaps[gap_index]
        available = gap[~selected[gap]]
        if len(available):
            # Re-split after earlier chunks so every new selection is contiguous.
            available_splits = np.flatnonzero(np.diff(available) != 1) + 1
            runs = [values for values in np.split(available, available_splits) if len(values)]
            run = runs[int(rng.integers(0, len(runs)))]
            remaining = desired_count - int(selected.sum())
            length = min(max(1, int(chunk_weeks)), len(run), remaining)
            start_max = len(run) - length
            start = int(rng.integers(0, start_max + 1)) if start_max else 0
            chosen = run[start:start + length]
            selected[chosen] = True
            records.append(
                {
                    "chunk_id": len(records),
                    "pi_pair": pair,
                    "derived_seed": derived_seed,
                    "gap_start": dates.iloc[gap[0]],
                    "gap_end": dates.iloc[gap[-1]],
                    "chunk_start": dates.iloc[chosen[0]],
                    "chunk_end": dates.iloc[chosen[-1]],
                    "row_count": len(chosen),
                }
            )
        attempt += 1
    if int(selected.sum()) != desired_count:
        raise RuntimeError(
            f"Pi-pair chunk sampler selected {int(selected.sum())}/{desired_count} requested rows"
        )
    return selected, pd.DataFrame(records, columns=columns)


def build_validation_corridor_index(
    historical: pd.DataFrame,
    validation_events: Iterable[pd.Timestamp],
    *,
    weeks_before: int,
    weeks_after: int,
) -> pd.DataFrame:
    """Index equal-size weekly master slices around every held-out event."""
    if int(weeks_before) < 1 or int(weeks_after) < 1:
        raise ValueError("Validation weekly index margins must be positive")
    records: list[pd.DataFrame] = []
    for event_number, event_value in enumerate(validation_events, start=1):
        event_date = pd.Timestamp(event_value)
        start = event_date - pd.Timedelta(weeks=int(weeks_before))
        end = event_date + pd.Timedelta(weeks=int(weeks_after))
        event_rows = historical.loc[historical[DATE_COLUMN].eq(event_date)]
        event_id = event_rows["japan_event_ids"].iloc[0] if len(event_rows) else ""
        magnitude = event_rows["japan_max_magnitude"].iloc[0] if len(event_rows) else np.nan
        corridor = historical.loc[
            historical[DATE_COLUMN].between(start, end), [DATE_COLUMN]
        ].copy()
        corridor.rename(columns={DATE_COLUMN: "row_date"}, inplace=True)
        corridor.insert(0, "event_number", event_number)
        corridor.insert(1, "event_id", event_id)
        corridor.insert(2, "event_date", event_date)
        corridor.insert(3, "event_magnitude", magnitude)
        corridor["relative_week"] = (
            (corridor["row_date"] - event_date).dt.days / 7.0
        ).round().astype(int)
        corridor["window_start"] = start
        corridor["window_end"] = end
        records.append(corridor)
    return pd.concat(records, ignore_index=True) if records else pd.DataFrame()


def build_trial_split(
    clean: pd.DataFrame,
    *,
    window_before: int,
    window_after: int,
    background_ratio: float,
    train_start_year: int,
    validation_event_count: int,
    seed: int,
    background_chunk_weeks: int = 4,
    validation_weeks_before: int = 13,
    validation_weeks_after: int = 13,
) -> TrialSplit:
    if not 2 <= int(window_before) <= 7 or not 2 <= int(window_after) <= 7:
        raise ValueError("window_before and window_after must be in [2, 7]")
    historical = clean.loc[clean[TARGET_COLUMN].notna()].copy()
    positive_weeks = historical.loc[historical[TARGET_COLUMN].eq(1), DATE_COLUMN].drop_duplicates().sort_values()
    if len(positive_weeks) <= validation_event_count:
        raise ValueError("Not enough distinct positive weeks for the requested temporal validation")
    validation_events = [pd.Timestamp(value) for value in positive_weeks.tail(validation_event_count)]
    validation_corridor_index = build_validation_corridor_index(
        historical,
        validation_events,
        weeks_before=validation_weeks_before,
        weeks_after=validation_weeks_after,
    )
    validation_start = pd.Timestamp(validation_corridor_index["window_start"].min())

    validation_end = pd.Timestamp(validation_corridor_index["window_end"].max())
    training_end = validation_start - pd.Timedelta(weeks=1)
    excluded = (
        "seis_core_magnitude", "seis_core_hard_negative", "is_japan_positive",
        "is_world_hard_negative", "is_forecast", "japan_event_count",
        "japan_max_magnitude", "foreign_event_count", "foreign_max_magnitude",
    )
    config = PretreatmentConfig(
        mode="energetic",
        target_col=TARGET_COLUMN,
        train_start_date=f"{int(train_start_year)}-01-01",
        train_end_date=training_end.date().isoformat(),
        eval_start_date=validation_start.date().isoformat(),
        eval_end_date=validation_end.date().isoformat(),
        min_magnitude_threshold=0.5,
        window_before=int(window_before),
        window_after=int(window_after),
        background_sample_ratio=float(background_ratio),
        background_chunk_size=int(background_chunk_weeks),
        seed=int(seed),
        eval_min_events=int(validation_event_count),
        eval_max_events=int(validation_event_count),
        auto_balance_dates=False,
        eval_window_mode="corridors",
        eval_corridor_span=max(int(validation_weeks_before), int(validation_weeks_after)),
        eval_event_dates=tuple(value.date().isoformat() for value in validation_events),
        mandatory_negative_col="is_world_hard_negative",
        excluded_feature_cols=excluded,
    )
    result = MasterPretreatmentEngine(config).process(
        historical, study_name=f"binary_m77_split_seed{int(seed)}"
    )
    train = result.train_df.copy()
    validation = result.eval_df.copy()
    train[DATE_COLUMN] = pd.to_datetime(train[DATE_COLUMN], errors="raise")
    validation[DATE_COLUMN] = pd.to_datetime(validation[DATE_COLUMN], errors="raise")
    audit_rows = result.metadata.get("pi_zipper_audit", [])
    background_chunks = pd.DataFrame(audit_rows)
    if not background_chunks.empty:
        background_chunks["background_chunk_weeks"] = int(background_chunk_weeks)
        background_chunks["seed"] = int(seed)
    expected_rows = sum(
        1 + int(validation_weeks_before) + int(validation_weeks_after)
        for _ in validation_events
    )
    if len(validation) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} validation rows from symmetric event corridors; got {len(validation)}"
        )
    if train[TARGET_COLUMN].nunique() < 2 or validation[TARGET_COLUMN].nunique() < 2:
        raise ValueError("Temporal split does not contain both binary classes")
    if pd.to_datetime(train[DATE_COLUMN]).max() >= validation_start:
        raise ValueError("Zero-leakage violation: training reaches the validation corridor")
    return TrialSplit(
        train,
        validation,
        validation_events,
        validation_start,
        validation_corridor_index,
        background_chunks,
    )


def build_full_training_sample(
    clean: pd.DataFrame,
    *,
    window_before: int,
    window_after: int,
    background_ratio: float,
    train_start_year: int,
    seed: int,
    background_chunk_weeks: int = 4,
    return_audit: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame]:
    historical = clean.loc[
        clean[TARGET_COLUMN].notna()
        & clean[DATE_COLUMN].ge(pd.Timestamp(f"{int(train_start_year)}-01-01"))
    ].copy()
    events = historical.loc[historical[TARGET_COLUMN].eq(1), DATE_COLUMN].drop_duplicates()
    corridor = _corridor_mask(historical[DATE_COLUMN], events, window_before, window_after)
    mandatory = corridor | historical["is_world_hard_negative"].eq(1).to_numpy()
    candidates = historical.index[(~mandatory) & historical[TARGET_COLUMN].eq(0)].to_numpy()
    count = min(len(candidates), max(int(round(len(candidates) * background_ratio)), len(events) * 2))
    candidate_mask = historical.index.isin(candidates)
    chosen_mask, chunks = _pi_background_chunks(
        historical.reset_index(drop=True),
        np.asarray(candidate_mask, dtype=bool),
        desired_count=count,
        chunk_weeks=background_chunk_weeks,
        seed=seed,
    )
    selected = mandatory | chosen_mask
    sample = historical.loc[selected].sort_values(DATE_COLUMN).reset_index(drop=True)
    return (sample, chunks) if return_audit else sample


def select_features(train: pd.DataFrame, candidates: list[str], feature_count: int) -> list[str]:
    """Select predictors using training-only standardized class separation."""
    usable = train[candidates].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    usable = usable.fillna(usable.median()).fillna(0.0)
    y = train[TARGET_COLUMN].to_numpy(dtype=float)
    positive = usable.loc[y == 1]
    negative = usable.loc[y == 0]
    if positive.empty or negative.empty:
        raise ValueError("Feature selection requires both classes")
    scale = usable.std(axis=0).replace(0.0, np.nan)
    score = ((positive.mean(axis=0) - negative.mean(axis=0)).abs() / scale).replace([np.inf, -np.inf], np.nan)
    score = score.fillna(-1.0).sort_values(ascending=False)
    return score.head(min(int(feature_count), int((score >= 0).sum()))).index.tolist()
