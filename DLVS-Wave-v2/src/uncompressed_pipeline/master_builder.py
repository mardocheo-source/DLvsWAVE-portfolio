"""
DLVS-Wave v2.0: Dual-Mode Master Dataset Builder
Builds:
1. Lean Uncompressed Master: Primary astro bodies + strictly 3 astro index shifts (Lead 13w, Lag 13w, Lead 4w)
   + historical seismic pre-event shifts, all normalized [0.0, 1.0] (approx 40-55 features, not 3000!).
2. Bitwise Compacted Master: Quantized 2-bit integer packed containers from raw astro data,
   subsequently normalized [0.0, 1.0] for ultra-fast training.
"""

from __future__ import annotations

import json
import logging
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from src.compression import BitPackingConfig, QuantizedBitPacker

logger = logging.getLogger("uncompressed_pipeline.master_builder")


def build_dual_mode_masters(
    raw_master_csv: Path | str,
    japan_catalog_csv: Path | str,
    world_catalog_csv: Path | str,
    output_dir: Path | str,
    magnitude_threshold: float = 7.7,
    cutoff_utc: str = "2026-07-31T23:59:59Z",
) -> dict[str, Any]:
    """Builds both the Lean Uncompressed (3-Index) Master and the Bitwise Compacted Master."""
    raw_master_csv = Path(raw_master_csv)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading raw master: {raw_master_csv}")
    raw_df = pd.read_csv(raw_master_csv, low_memory=False)
    raw_df["date"] = pd.to_datetime(raw_df["date"]).dt.normalize()
    raw_df = raw_df.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    cadence = raw_df["date"].diff().dropna().dt.days
    if cadence.empty or int(cadence.mode().iloc[0]) != 7 or not cadence.eq(7).all():
        raise ValueError("The dual-mode builder requires one strictly regular 7-day row per sample.")

    cutoff_dt = pd.Timestamp(cutoff_utc).tz_localize(None) if pd.Timestamp(cutoff_utc).tzinfo is None else pd.Timestamp(cutoff_utc).tz_convert("UTC").tz_localize(None)
    hist_mask = raw_df["date"] <= cutoff_dt
    validation_start = pd.Timestamp("2003-09-22") - pd.Timedelta(weeks=13)
    fit_mask = raw_df["date"] < validation_start

    # 1. Target Construction & Foreign Hard Negatives
    japan_cat = pd.read_csv(japan_catalog_csv)
    japan_cat["time"] = pd.to_datetime(japan_cat["time"], utc=True).dt.tz_localize(None)
    japan_pos = japan_cat[(japan_cat["mag"] >= magnitude_threshold) & (japan_cat["time"] <= cutoff_dt)].copy()
    japan_pos["week_start"] = japan_pos["time"].dt.to_period("W-SUN").dt.start_time

    world_cat = pd.read_csv(world_catalog_csv)
    world_cat["time"] = pd.to_datetime(world_cat["time"], utc=True).dt.tz_localize(None)
    foreign_pos = world_cat[
        (world_cat["mag"] >= magnitude_threshold) &
        (world_cat["time"] <= cutoff_dt) &
        ~((world_cat["latitude"].between(22.0, 50.5)) & (world_cat["longitude"].between(122.0, 156.0)))
    ].copy()
    foreign_pos["week_start"] = foreign_pos["time"].dt.to_period("W-SUN").dt.start_time

    japan_weeks = set(japan_pos["week_start"].dt.normalize())
    foreign_weeks = set(foreign_pos["week_start"].dt.normalize())

    targets_df = pd.DataFrame(index=raw_df.index)
    targets_df["date"] = raw_df["date"]
    targets_df["japan_m77_event"] = 0.0
    targets_df["is_world_hard_negative"] = 0
    targets_df["sample_role"] = "quiet_negative"

    for idx in raw_df.index:
        dt = raw_df.at[idx, "date"]
        if dt <= cutoff_dt:
            if dt in japan_weeks:
                targets_df.at[idx, "japan_m77_event"] = 1
                targets_df.at[idx, "sample_role"] = "japan_positive"
            elif dt in foreign_weeks:
                targets_df.at[idx, "japan_m77_event"] = 0
                targets_df.at[idx, "is_world_hard_negative"] = 1
                targets_df.at[idx, "sample_role"] = "foreign_hard_negative"
        else:
            targets_df.at[idx, "japan_m77_event"] = np.nan
            targets_df.at[idx, "sample_role"] = "prospective_unlabelled"

    # 2. Select Lean In-Chiaro Features (Key Bodies + 3 Astro Shifts + Seismic Shifts)
    seis_shift_cols = [c for c in raw_df.columns if c.startswith("seis_core_magnitude_shift_") or c.startswith("seis_core_depth_shift_")]
    
    # Primary bodies (defaults to key_bodies, or all astro bodies present in raw_df if none match)
    default_key_bodies = ["sun", "moon", "jupiter", "saturn", "mars", "venus", "mercury"]
    present_astro = [c for c in raw_df.columns if c.startswith("astro_")]
    available_bodies = sorted(list(set([c.split("_")[1] for c in present_astro if len(c.split("_")) > 1])))
    
    key_bodies = [b for b in default_key_bodies if b in available_bodies]
    if not key_bodies:
        # Fallback to whatever astro bodies are present in raw_df (e.g. minor bodies)
        key_bodies = available_bodies

    core_astro_cols = []
    for body in key_bodies:
        # Longitude/RA, Latitude/DEC, Distance, Elevation
        for metric in ["ra_app_min", "dec_app_min", "dist_min", "elev_min"]:
            col = f"astro_{body}_{metric}"
            if col in raw_df.columns:
                core_astro_cols.append(col)

    logger.info(f"Selected {len(core_astro_cols)} core astronomical invariants for bodies {key_bodies} and {len(seis_shift_cols)} seismic shifts.")

    # Strictly 3 Astro Shifts for the core astro predictors:
    # 1. Lead +13w (+3 months)
    # 2. Lag -13w (-3 months)
    # 3. Lead +4w (+1 month pre-activation)
    lean_shifts_dict = {}
    shift_cols_names = []
    for col in core_astro_cols[:12]:
        c_lead13 = f"{col}_shift_lead_13w"
        c_lag13 = f"{col}_shift_lag_13w"
        c_lead4 = f"{col}_shift_lead_4w"
        lean_shifts_dict[c_lead13] = raw_df[col].shift(-13).bfill()
        lean_shifts_dict[c_lag13] = raw_df[col].shift(13).ffill()
        lean_shifts_dict[c_lead4] = raw_df[col].shift(-4).bfill()
        shift_cols_names.extend([c_lead13, c_lag13, c_lead4])

    lean_shift_df = pd.DataFrame(lean_shifts_dict, index=raw_df.index)
    lean_feature_cols = core_astro_cols + seis_shift_cols + shift_cols_names
    logger.info(f"Total LEAN feature set size: {len(lean_feature_cols)} features (strictly selected).")

    # Build Lean Uncompressed Normalized Master
    lean_master_df = pd.concat([targets_df, raw_df[core_astro_cols + seis_shift_cols], lean_shift_df], axis=1)
    
    scaler_lean = MinMaxScaler(feature_range=(0.0, 1.0))
    scaler_lean.fit(lean_master_df.loc[fit_mask, lean_feature_cols].fillna(0.0))
    lean_master_df[lean_feature_cols] = np.clip(scaler_lean.transform(lean_master_df[lean_feature_cols].fillna(0.0)), 0.0, 1.0)

    lean_master_path = output_dir / "master_7d_lean_uncompressed_normalized.csv"
    lean_master_df.to_csv(lean_master_path, index=False)
    logger.info(f"Saved Lean Uncompressed Master -> {lean_master_path} ({len(lean_master_df)} rows, {len(lean_master_df.columns)} cols)")

    # 3. Build Bitwise Compacted Master (from Raw un-normalized Astro, then normalized)
    all_raw_astro = [c for c in raw_df.columns if c.startswith("astro_")]
    packer = QuantizedBitPacker(BitPackingConfig(bits_per_field=2, fields_per_container=8, container_dtype="uint16"))
    
    # Pack continuous astro fields on historical split
    packed_astro_df, codebook = packer.pack(
        raw_df[["date"] + all_raw_astro],
        feature_cols=all_raw_astro,
        fit_mask=fit_mask,
    )
    packed_container_cols = [c for c in packed_astro_df.columns if c.startswith("packed_astro_container_")]
    logger.info(f"Generated {len(packed_container_cols)} bitwise integer containers from {len(all_raw_astro)} raw astro fields.")

    # Merge packed containers with targets and normalized seismic shifts
    bitwise_master_df = pd.concat([targets_df, raw_df[seis_shift_cols], packed_astro_df[packed_container_cols]], axis=1)
    
    # Normalize integer containers and seismic shifts to [0.0, 1.0]
    bitwise_feat_cols = seis_shift_cols + packed_container_cols
    scaler_bitwise = MinMaxScaler(feature_range=(0.0, 1.0))
    scaler_bitwise.fit(bitwise_master_df.loc[fit_mask, bitwise_feat_cols].fillna(0.0))
    bitwise_master_df[bitwise_feat_cols] = np.clip(scaler_bitwise.transform(bitwise_master_df[bitwise_feat_cols].fillna(0.0)), 0.0, 1.0)

    bitwise_master_path = output_dir / "master_7d_bitwise_compacted_normalized.csv"
    bitwise_master_df.to_csv(bitwise_master_path, index=False)
    logger.info(f"Saved Bitwise Compacted Master -> {bitwise_master_path} ({len(bitwise_master_df)} rows, {len(bitwise_master_df.columns)} cols)")

    codebook_path = output_dir / "master_7d_bitwise_codebook.json"
    with open(codebook_path, "w", encoding="utf-8") as f:
        json.dump(codebook, f, indent=2, default=str)

    available_bodies = sorted({c.split("_")[1] for c in core_astro_cols})
    missing_bodies = [body for body in key_bodies if body not in available_bodies]

    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    manifest = {
        "lean_uncompressed_master_path": str(lean_master_path),
        "lean_features_count": len(lean_feature_cols),
        "lean_features": lean_feature_cols,
        "lean_base_astro_features": core_astro_cols,
        "lean_shift_source_features": core_astro_cols[:12],
        "lean_shift_contract": ["shift_lead_13w", "shift_lag_13w", "shift_lead_4w"],
        "available_primary_bodies": available_bodies,
        "missing_primary_bodies_in_source": missing_bodies,
        "bitwise_compacted_master_path": str(bitwise_master_path),
        "bitwise_containers_count": len(packed_container_cols),
        "bitwise_features_count": len(bitwise_feat_cols),
        "bitwise_features": bitwise_feat_cols,
        "bitwise_codebook_path": str(codebook_path),
        "weekly_rows": int(len(raw_df)),
        "weekly_cadence_days": 7,
        "training_fit_end": str((validation_start - pd.Timedelta(weeks=1)).date()),
        "validation_window_start": str(validation_start.date()),
        "validation_event_weeks": ["2003-09-22", "2011-03-07"],
        "japan_positive_weeks": int(len(japan_weeks)),
        "foreign_hard_negative_weeks": int(len(foreign_weeks - japan_weeks)),
        "forecast_rows": int(raw_df["date"].between("2026-08-01", "2027-01-31").sum()),
        "forecast_first_week": str(raw_df.loc[raw_df["date"].between("2026-08-01", "2027-01-31"), "date"].min().date()),
        "forecast_last_week": str(raw_df.loc[raw_df["date"].between("2026-08-01", "2027-01-31"), "date"].max().date()),
        "normalization_fit_scope": "strictly pre-validation rows only",
        "historical_cutoff": str(cutoff_dt.date()),
        "magnitude_threshold": magnitude_threshold,
        "input_sha256": {
            "weekly_master": sha256(raw_master_csv),
            "japan_catalog": sha256(Path(japan_catalog_csv)),
            "world_catalog": sha256(Path(world_catalog_csv)),
        },
    }

    manifest_path = output_dir / "dual_master_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest
