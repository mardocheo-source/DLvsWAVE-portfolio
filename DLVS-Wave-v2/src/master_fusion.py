"""Modulo 5: Master Fusion Engine for DLVS-Wave v2.0.

Chronologically aligns and fuses seismic event catalogs (Modulo 1)
with astronomical ephemeris time series (Modulo 2 / Modulo 3).
Integrates:
  - Configurable Seismic Core Field Selection (default: magnitude, latitude, longitude, depth).
  - Strict exclusion of non-physical metadata IDs (seis_core_id) by default.
  - Front-positioned Seismic Fields: date -> all seis_* features -> astro_* features for instant inspection.
  - Daily seismic event deduplication (strongest peak event per date).
  - Master Sanitization & Zero-Variance Pruning (Modulo 10).
  - Historical & Future Shift Indexing (Modulo 9).
  - Causal Anti-Data-Leakage Auditing & Reporting (master_anti_leakage_audit.md).
  - Schema Configuration Export (master_schema_config.json).
  - Astro Quantized Bit-Packing Compression preserving seismic in chiaro (Modulo 4).
  - Companion Markdown Decodification Manifest (Modulo 8).
"""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from cleaning import MasterSanitizer
from compression import BitPackingConfig, CompressionCodebook, QuantizedBitPacker
from indexing import HistoricalShiftEngine, ShiftParameters
from naming import DEFAULT_SEISMIC_CORE_FIELDS, reorder_master_dataframe, validate_column_names
from reporting import generate_master_manifest

logger = logging.getLogger("dlvs_wave.master_fusion")


def _read_clean_catalog(
    path: str | Path,
    magnitude_threshold: float,
    cutoff_utc: str,
) -> pd.DataFrame:
    """Load one frozen earthquake catalogue with UTC and numeric validation."""
    frame = pd.read_csv(path, low_memory=False)
    required = {"time", "mag", "latitude", "longitude"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Catalogue {path} lacks columns: {', '.join(missing)}")
    frame = frame.copy()
    frame["time"] = pd.to_datetime(frame["time"], utc=True, errors="coerce")
    for column in ("mag", "latitude", "longitude"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    cutoff = pd.Timestamp(cutoff_utc)
    cutoff = cutoff.tz_localize("UTC") if cutoff.tzinfo is None else cutoff.tz_convert("UTC")
    frame = frame.loc[
        frame["time"].notna()
        & frame["mag"].ge(float(magnitude_threshold))
        & frame["time"].le(cutoff)
    ].copy()
    frame["date"] = frame["time"].dt.tz_convert("UTC").dt.strftime("%Y-%m-%d")
    normalized = frame["time"].dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()
    frame["week_start"] = normalized - pd.to_timedelta(normalized.dt.weekday, unit="D")
    return frame.sort_values("time").reset_index(drop=True)


def _catalog_weekly_summary(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Create traceable event counts, peak magnitude, and IDs per Monday week."""
    columns = ["date", f"{prefix}_event_count", f"{prefix}_max_magnitude", f"{prefix}_event_ids"]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    id_column = "id" if "id" in frame.columns else None
    grouped = frame.groupby("week_start", sort=True)
    output = grouped["mag"].agg(["size", "max"]).reset_index()
    output.columns = columns[:3]
    if id_column:
        ids = grouped[id_column].agg(lambda values: "|".join(values.dropna().astype(str).unique()))
        output[columns[3]] = ids.reset_index(drop=True)
    else:
        output[columns[3]] = ""
    return output


def build_clean_binary_megathrust_master(
    daily_source_master_path: str | Path,
    japan_catalog_path: str | Path,
    world_catalog_path: str | Path,
    output_dir: str | Path,
    *,
    magnitude_threshold: float = 7.7,
    cutoff_utc: str = "2026-07-31T23:59:59Z",
    forecast_start: str = "2026-08-01",
    forecast_end: str = "2026-12-31",
    validation_weeks_before: int = 13,
    validation_weeks_after: int = 13,
    shift_weeks: int = 13,
    japan_lat_min: float = 22.0,
    japan_lat_max: float = 50.5,
    japan_lon_min: float = 122.0,
    japan_lon_max: float = 156.0,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    """Build a leakage-audited 7-day binary master through core DLVS modules.

    The function intentionally lives in ``master_fusion.py`` so event filtering,
    fusion, weekly resampling, calendar indexing, and compaction remain inside
    the repository's traceable master pipeline rather than in an ad-hoc runner.
    """
    from compression import BitPackingConfig
    from resampling import ResamplingConfig, TemporalSummarizer

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    daily_path = Path(daily_source_master_path)
    header = pd.read_csv(daily_path, nrows=0)
    astro_columns = [
        column for column in header.columns
        if column.startswith("astro_") and "_shift_" not in column
    ]
    if not astro_columns:
        raise ValueError("Daily source master has no base astronomical fields")
    astro = pd.read_csv(daily_path, usecols=["date", *astro_columns], low_memory=False)
    astro["date"] = pd.to_datetime(astro["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    if astro["date"].isna().any() or astro["date"].duplicated().any():
        raise ValueError("Daily astronomical source requires unique, valid dates")

    japan = _read_clean_catalog(japan_catalog_path, magnitude_threshold, cutoff_utc)
    world = _read_clean_catalog(world_catalog_path, magnitude_threshold, cutoff_utc)
    inside_extended_japan = (
        world["latitude"].between(japan_lat_min, japan_lat_max)
        & world["longitude"].between(japan_lon_min, japan_lon_max)
    )
    foreign = world.loc[~inside_extended_japan].copy()

    positive_daily = japan.groupby("date", sort=True)["mag"].max().rename("seis_core_magnitude")
    foreign_daily = foreign.groupby("date", sort=True)["mag"].max().rename("foreign_daily_max")
    event_daily = pd.concat([positive_daily, foreign_daily], axis=1).reset_index()
    event_daily["seis_core_magnitude"] = event_daily["seis_core_magnitude"].fillna(0.0)
    event_daily["seis_core_hard_negative"] = (
        event_daily["foreign_daily_max"].notna()
        & event_daily["seis_core_magnitude"].lt(float(magnitude_threshold))
    ).astype("int8")
    event_daily = event_daily[["date", "seis_core_magnitude", "seis_core_hard_negative"]]

    builder = MasterBuilder(
        packing_config=BitPackingConfig(bits_per_field=2, fields_per_container=8, container_dtype="uint16"),
        shift_params=ShiftParameters(astro_min_step=0, astro_max_step=0, seis_min_step=0, seis_max_step=0),
        enable_shifts=False,
        sanitize_and_prune=True,
        seismic_keep_fields=("seis_core_magnitude", "seis_core_hard_negative"),
    )
    fused_daily, _ = builder.fuse(astro, event_daily)
    weekly = TemporalSummarizer(
        ResamplingConfig(
            window_days=7,
            aggregations=("min", "max", "mean", "median"),
            recalculate_shifts=False,
        )
    ).summarize(fused_daily)
    weekly["date"] = pd.to_datetime(weekly["date"], errors="raise")
    weekly["seis_core_hard_negative"] = (
        weekly["seis_core_hard_negative"].fillna(0).gt(0)
        & weekly["seis_core_magnitude"].lt(float(magnitude_threshold))
    ).astype("int8")

    event_weeks = weekly.loc[
        weekly["seis_core_magnitude"].ge(float(magnitude_threshold)), "date"
    ].drop_duplicates().sort_values()
    if len(event_weeks) < 2:
        raise ValueError("Fewer than two Japan M-threshold event weeks are available")
    validation_events = [pd.Timestamp(value) for value in event_weeks.tail(2)]
    validation_years = [value.year for value in validation_events]
    if validation_years != [2003, 2011]:
        raise ValueError(
            "The requested frozen validation pair is not the last two event weeks: "
            f"found {validation_events}"
        )
    first_validation_row = validation_events[0] - pd.Timedelta(weeks=int(validation_weeks_before))
    train_end = first_validation_row - pd.Timedelta(weeks=1)

    shift_params = ShiftParameters(
        astro_min_step=-int(shift_weeks),
        astro_max_step=int(shift_weeks),
        astro_step_days=7,
        seis_min_step=0,
        seis_max_step=0,
        seis_step_days=7,
        allow_future_seismic=False,
        temporal_resolution="7d",
    )
    shift_engine = HistoricalShiftEngine(shift_params)
    shifted_weekly, shift_audit = shift_engine.apply_shifts(weekly)
    fit_mask = shifted_weekly["date"].le(train_end)
    packed, codebook = builder.packer.pack(shifted_weekly, fit_mask=fit_mask)
    builder.packer.save_codebook(codebook, destination / "clean_master_7d_shift13w_codebook.json")
    shift_engine.generate_anti_leakage_audit_report(
        shift_audit, destination / "clean_master_7d_shift13w_anti_leakage_audit.md"
    )
    shift_engine.save_schema_config(destination / "clean_master_7d_shift13w_schema_config.json")

    clean = packed.copy()
    clean["date"] = pd.to_datetime(clean["date"], errors="raise")
    japan_weekly = _catalog_weekly_summary(japan, "japan")
    foreign_weekly = _catalog_weekly_summary(foreign, "foreign")
    japan_weekly["date"] = pd.to_datetime(japan_weekly["date"], errors="raise")
    foreign_weekly["date"] = pd.to_datetime(foreign_weekly["date"], errors="raise")
    clean = clean.merge(japan_weekly, how="left", on="date").merge(foreign_weekly, how="left", on="date")
    for prefix in ("japan", "foreign"):
        clean[f"{prefix}_event_count"] = clean[f"{prefix}_event_count"].fillna(0).astype(int)
        clean[f"{prefix}_max_magnitude"] = pd.to_numeric(
            clean[f"{prefix}_max_magnitude"], errors="coerce"
        )
        clean[f"{prefix}_event_ids"] = clean[f"{prefix}_event_ids"].fillna("").astype(str)

    cutoff = pd.Timestamp(cutoff_utc)
    cutoff = cutoff.tz_localize("UTC") if cutoff.tzinfo is None else cutoff.tz_convert("UTC")
    cutoff_naive = cutoff.tz_localize(None)
    historical = clean["date"].le(cutoff_naive)
    positive = historical & clean["seis_core_magnitude"].ge(float(magnitude_threshold))
    hard_negative = historical & ~positive & clean["seis_core_hard_negative"].gt(0)
    clean["japan_m77_event"] = pd.Series(pd.NA, index=clean.index, dtype="Float64")
    clean.loc[historical, "japan_m77_event"] = positive.loc[historical].astype(float)
    clean["is_japan_positive"] = positive.astype("int8")
    clean["is_world_hard_negative"] = hard_negative.astype("int8")
    clean["is_forecast"] = (~historical).astype("int8")
    clean["sample_role"] = "quiet_negative"
    clean.loc[positive, "sample_role"] = "japan_positive"
    clean.loc[hard_negative, "sample_role"] = "foreign_hard_negative"
    clean.loc[~historical, "sample_role"] = "prospective_unlabelled"
    clean["date"] = clean["date"].dt.strftime("%Y-%m-%d")

    feature_columns = sorted(column for column in clean if column.startswith("packed_astro_container_"))
    forecast_mask = pd.to_datetime(clean["date"]).between(
        pd.Timestamp(forecast_start), pd.Timestamp(forecast_end)
    )
    if not forecast_mask.any():
        raise ValueError("The clean master does not cover the requested forecast range")

    clean.to_csv(destination / "clean_master_binary_7d.csv", index=False)
    event_index = clean.loc[
        clean["is_japan_positive"].eq(1) | clean["is_world_hard_negative"].eq(1),
        [
            "date", "japan_m77_event", "sample_role", "japan_max_magnitude",
            "foreign_max_magnitude", "japan_event_ids", "foreign_event_ids",
        ],
    ]
    event_index.to_csv(destination / "event_and_hard_negative_index.csv", index=False)
    summary: dict[str, Any] = {
        "construction_modules": ["master_fusion.py", "resampling.py", "indexing.py", "pretreatment.py"],
        "daily_source_master": str(daily_path.resolve()),
        "base_astronomical_fields": len(astro_columns),
        "weekly_rows": len(clean),
        "historical_rows": int(historical.sum()),
        "packed_feature_count": len(feature_columns),
        "feature_count": len(feature_columns),
        "magnitude_threshold": float(magnitude_threshold),
        "low_magnitude_events_included": 0,
        "japan_catalog_events_at_or_above_threshold": len(japan),
        "japan_positive_weeks": int(clean["is_japan_positive"].sum()),
        "foreign_hard_negative_events": len(foreign),
        "foreign_hard_negative_weeks": int(clean["is_world_hard_negative"].sum()),
        "validation_event_weeks": [value.date().isoformat() for value in validation_events],
        "validation_event_count": 2,
        "validation_window_start": first_validation_row.date().isoformat(),
        "training_hard_end": train_end.date().isoformat(),
        "validation_weeks_before": int(validation_weeks_before),
        "validation_weeks_after": int(validation_weeks_after),
        "shift_weeks": int(shift_weeks),
        "shift_audit": shift_audit,
        "quantile_fit": {
            "rows": codebook.quantile_fit_row_count,
            "start": codebook.quantile_fit_start_date,
            "end": codebook.quantile_fit_end_date,
        },
        "forecast_start": str(pd.Timestamp(forecast_start).date()),
        "forecast_end": str(pd.Timestamp(forecast_end).date()),
        "cutoff_utc": cutoff.isoformat(),
        "forecast_rows": int(forecast_mask.sum()),
        "japan_extended_bbox": {
            "latitude": [japan_lat_min, japan_lat_max],
            "longitude": [japan_lon_min, japan_lon_max],
        },
    }
    with (destination / "dataset_audit.json").open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, default=str)
    clean["date"] = pd.to_datetime(clean["date"], errors="raise")
    return clean, feature_columns, summary


@dataclass
class MasterFusionResult:
    master_uncompressed_path: Path | None
    master_packed_path: Path | None
    codebook_path: Path | None
    manifest_md_path: Path | None
    anti_leakage_audit_path: Path | None
    schema_config_path: Path | None
    uncompressed_shape: tuple[int, int]
    packed_shape: tuple[int, int]
    uncompressed_size_bytes: int
    packed_size_bytes: int
    size_reduction_pct: float
    feature_reduction_ratio: float


class MasterBuilder:
    """Fuses astronomical and seismic datasets with sanitization, shift indexing, and anti-leakage audit."""

    def __init__(
        self,
        packing_config: BitPackingConfig | None = None,
        shift_params: ShiftParameters | None = None,
        enable_shifts: bool = True,
        sanitize_and_prune: bool = True,
        seismic_keep_fields: Sequence[str] | None = None,
    ) -> None:
        self.packing_config = packing_config or BitPackingConfig()
        self.packer = QuantizedBitPacker(self.packing_config)
        self.shift_params = shift_params or ShiftParameters()
        self.enable_shifts = enable_shifts
        self.shift_engine = HistoricalShiftEngine(self.shift_params)
        self.sanitize_and_prune = sanitize_and_prune
        self.seismic_keep_fields = list(seismic_keep_fields or DEFAULT_SEISMIC_CORE_FIELDS)
        self.sanitizer = MasterSanitizer(protected_cols=("date", "time", *self.seismic_keep_fields))

    def fuse(self, df_astro: pd.DataFrame, df_seis: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Merges astronomical daily grid with seismic events chronologically, cleans, and applies shifts."""
        if df_astro.empty:
            raise ValueError("Astronomical DataFrame cannot be empty for master fusion.")

        df_a = df_astro.copy()
        df_a["date"] = df_a["date"].astype(str).str.strip()

        # Format seismic features and filter to requested core fields
        seis_cols_to_use = [c for c in self.seismic_keep_fields]

        if df_seis.empty:
            for col in seis_cols_to_use:
                df_a[col] = 0.0
            df_merged = df_a
        else:
            df_s = df_seis.copy()
            df_s["date"] = df_s["date"].astype(str).str.strip()

            # Ensure all requested core seismic fields exist
            for col in seis_cols_to_use:
                if col not in df_s.columns:
                    df_s[col] = 0.0

            # Daily deduplication: pick the strongest earthquake for each day
            sort_cols = ["date"]
            asc_order = [True]
            if "seis_core_magnitude" in df_s.columns:
                sort_cols.append("seis_core_magnitude")
                asc_order.append(False)

            df_s_daily = (
                df_s.sort_values(by=sort_cols, ascending=asc_order)
                .groupby("date", as_index=False)
                .first()
            )

            merge_cols = ["date", *[c for c in seis_cols_to_use if c in df_s_daily.columns]]
            df_merged = pd.merge(df_a, df_s_daily[merge_cols], on="date", how="left")

            # Days with no seismic activity are strictly 0.0
            for col in seis_cols_to_use:
                if col in df_merged.columns:
                    df_merged[col] = df_merged[col].fillna(0.0)

        df_merged.sort_values(by="date", inplace=True)
        df_merged.reset_index(drop=True, inplace=True)

        # 1. Master Sanitization & Zero-Variance Column Pruning
        if self.sanitize_and_prune:
            df_merged, clean_rep = self.sanitizer.sanitize_and_prune(df_merged)

        # 2. Historical & Future Shift Indexing
        audit_meta = {}
        if self.enable_shifts:
            df_merged, audit_meta = self.shift_engine.apply_shifts(df_merged)

        # 3. Canonical Front-Positioning for Date and Seismic Features
        df_merged = reorder_master_dataframe(df_merged)

        is_valid, invalid_cols = validate_column_names(df_merged.columns)
        if not is_valid:
            logger.warning(f"Columns not adhering to strict naming standard: {invalid_cols}")

        return df_merged, audit_meta

    def build_and_save(
        self,
        df_astro: pd.DataFrame,
        df_seis: pd.DataFrame,
        output_dir: str | Path,
        base_filename: str = "master",
    ) -> tuple[pd.DataFrame, pd.DataFrame, MasterFusionResult]:
        """Creates and exports uncompressed master, packed master, audit report, and manifest."""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # 1. Uncompressed Master with Front-Positioned Seismic Fields
        df_uncompressed, audit_meta = self.fuse(df_astro, df_seis)
        raw_csv_path = out_dir / f"{base_filename}_uncompressed.csv"
        df_uncompressed.to_csv(raw_csv_path, index=False)

        # 2. Anti-Leakage Audit Report & Schema Configuration
        audit_path = None
        config_path = None
        if audit_meta:
            audit_path = self.shift_engine.generate_anti_leakage_audit_report(
                audit_meta, out_dir / f"{base_filename}_anti_leakage_audit.md"
            )
            config_path = self.shift_engine.save_schema_config(
                out_dir / f"{base_filename}_schema_config.json"
            )

        # 3. Astro Bit-Packed Master (Seismic preserved in chiaro right after date)
        df_packed, codebook = self.packer.pack(df_uncompressed)
        packed_csv_path = out_dir / f"{base_filename}_packed_16bit.csv"
        codebook_path = out_dir / f"{base_filename}_codebook.json"
        df_packed.to_csv(packed_csv_path, index=False)
        self.packer.save_codebook(codebook, codebook_path)

        raw_size = raw_csv_path.stat().st_size
        packed_size = packed_csv_path.stat().st_size
        reduction = round((1.0 - (packed_size / max(1, raw_size))) * 100.0, 2)

        # 4. Companion Markdown Manifest Report
        manifest_md_path = out_dir / f"{base_filename}_manifest.md"
        generate_master_manifest(
            df_uncompressed=df_uncompressed,
            df_packed=df_packed,
            codebook=codebook,
            output_md_path=manifest_md_path,
            master_name=base_filename.replace("_", " ").title(),
            metadata={
                "raw_size_bytes": raw_size,
                "packed_size_bytes": packed_size,
                "size_reduction_pct": reduction,
            },
        )

        result = MasterFusionResult(
            master_uncompressed_path=raw_csv_path,
            master_packed_path=packed_csv_path,
            codebook_path=codebook_path,
            manifest_md_path=manifest_md_path,
            anti_leakage_audit_path=audit_path,
            schema_config_path=config_path,
            uncompressed_shape=df_uncompressed.shape,
            packed_shape=df_packed.shape,
            uncompressed_size_bytes=raw_size,
            packed_size_bytes=packed_size,
            size_reduction_pct=reduction,
            feature_reduction_ratio=codebook.compression_ratio_fields,
        )

        logger.info(
            f"Master built successfully: {df_uncompressed.shape[1]} raw cols -> {df_packed.shape[1]} packed cols. "
            f"Size reduction: {reduction}% ({raw_size}B -> {packed_size}B). Audit: {audit_path.name if audit_path else 'None'}"
        )
        return df_uncompressed, df_packed, result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Master Fusion & Anti-Leakage Shift Engine CLI for DLVS-Wave v2.0")
    p.add_argument("--astro-csv", required=True, help="Path to input astronomical ephemerides CSV")
    p.add_argument("--seis-csv", required=True, help="Path to input seismic events CSV")
    p.add_argument("--output-dir", required=True, help="Output directory to save master files")
    p.add_argument("--base-filename", default="master_1d", help="Base filename prefix (default: master_1d)")
    p.add_argument("--bits-per-field", type=int, default=2, help="Bits per field (default: 2)")
    p.add_argument("--fields-per-container", type=int, default=8, help="Fields per integer container (default: 8)")
    p.add_argument("--container-dtype", default="uint16", help="Container dtype (default: uint16)")
    p.add_argument("--seismic-fields", default="seis_core_magnitude,seis_core_latitude,seis_core_longitude,seis_core_depth", help="Comma-separated seismic core fields to retain (default: mag,lat,lon,depth)")
    p.add_argument("--no-shifts", action="store_true", help="Disable historical and future shift indexing")
    p.add_argument("--no-sanitize", action="store_true", help="Disable alphanumeric sanitization and zero-variance pruning")
    p.add_argument("--astro-min-step", type=int, default=-5, help="Astro min step multiplier (default: -5)")
    p.add_argument("--astro-max-step", type=int, default=5, help="Astro max step multiplier (default: 5)")
    p.add_argument("--astro-step-days", type=int, default=7, help="Astro step size in days (default: 7)")
    p.add_argument("--seis-min-step", type=int, default=-5, help="Seismic min step multiplier (default: -5)")
    p.add_argument("--seis-max-step", type=int, default=0, help="Seismic max step multiplier (default: 0)")
    p.add_argument("--seis-step-days", type=int, default=7, help="Seismic step size in days (default: 7)")
    p.add_argument("--allow-future-seismic", action="store_true", help="Allow future seismic shifts")
    return p


def main() -> None:
    args = build_parser().parse_args()
    df_astro = pd.read_csv(args.astro_csv)
    df_seis = pd.read_csv(args.seis_csv)

    # Parse requested seismic fields (accepting short names like mag, lat, lon, depth or full seis_core_*)
    raw_seis_fields = [f.strip() for f in args.seismic_fields.split(",") if f.strip()]
    seis_fields = []
    for f in raw_seis_fields:
        if f.startswith("seis_"):
            seis_fields.append(f)
        elif f in ("mag", "magnitude"):
            seis_fields.append("seis_core_magnitude")
        elif f in ("lat", "latitude"):
            seis_fields.append("seis_core_latitude")
        elif f in ("lon", "longitude"):
            seis_fields.append("seis_core_longitude")
        elif f in ("depth",):
            seis_fields.append("seis_core_depth")
        else:
            seis_fields.append(f"seis_core_{f}")

    shift_params = ShiftParameters(
        astro_min_step=args.astro_min_step,
        astro_max_step=args.astro_max_step,
        astro_step_days=args.astro_step_days,
        seis_min_step=args.seis_min_step,
        seis_max_step=args.seis_max_step,
        seis_step_days=args.seis_step_days,
        allow_future_seismic=args.allow_future_seismic,
    )

    packing_config = BitPackingConfig(
        bits_per_field=args.bits_per_field,
        fields_per_container=args.fields_per_container,
        container_dtype=args.container_dtype,
        isolated_families=True,
        prune_zero_variance=not args.no_sanitize,
    )

    builder = MasterBuilder(
        packing_config=packing_config,
        shift_params=shift_params,
        enable_shifts=not args.no_shifts,
        sanitize_and_prune=not args.no_sanitize,
        seismic_keep_fields=seis_fields,
    )

    df_raw, df_packed, res = builder.build_and_save(
        df_astro=df_astro,
        df_seis=df_seis,
        output_dir=args.output_dir,
        base_filename=args.base_filename,
    )
    print(f"Master Fusion Completed: {df_raw.shape[1]} raw cols -> {df_packed.shape[1]} packed cols ({res.size_reduction_pct}% reduction).")
    print(f"Raw Master CSV: {res.master_uncompressed_path}")
    print(f"Packed Master CSV: {res.master_packed_path}")
    print(f"Anti-Leakage Audit Report: {res.anti_leakage_audit_path}")
    print(f"Schema Configuration: {res.schema_config_path}")
    print(f"Manifest Report: {res.manifest_md_path}")


if __name__ == "__main__":
    main()
