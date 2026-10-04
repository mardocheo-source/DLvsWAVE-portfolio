#!/usr/bin/env python3
"""
Fixes uncompressed master normalization: scales ALL 3,095 features strictly to [0.0, 1.0].
"""

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

REPO_ROOT = Path("/mnt/git0/git/repository/DLvsWAVE")
PROJECT_DIR = REPO_ROOT / "DLVS-Wave-v2"
DEMO_DIR = PROJECT_DIR / "studies_output/japan_megathrust_m77_uncompressed_sample_demo"

raw_master_path = PROJECT_DIR / "tests_env/multi_country_century_tests/loc1_japan_tohoku_1900_2030/master_7d_summarized.csv"
print("Loading raw master:", raw_master_path)
df = pd.read_csv(raw_master_path)
df["date"] = pd.to_datetime(df["date"]).dt.normalize()

# Identify all numeric feature columns (astro + seismic lag)
exclude_cols = {"date", "seis_core_latitude", "seis_core_longitude", "seis_core_magnitude", "seis_core_depth"}
feature_cols = [c for c in df.columns if c not in exclude_cols]

print(f"Total feature columns to normalize: {len(feature_cols)}")

# Fit MinMaxScaler on pre-cutoff historical data (<= 2026-07-31)
cutoff_date = pd.Timestamp("2026-07-31")
hist_mask = df["date"] <= cutoff_date

scaler = MinMaxScaler(feature_range=(0.0, 1.0))
scaler.fit(df.loc[hist_mask, feature_cols].fillna(0.0))

# Transform all rows (train + val + prospective forecast)
df[feature_cols] = np.clip(scaler.transform(df[feature_cols].fillna(0.0)), 0.0, 1.0)

# Add target and hard negatives
japan_catalog_path = REPO_ROOT / "DB/japan-m79plus-7d-aug-sep2026-cutoff-jul31-recency-globalneg-v21/01_inputs/usgs_japan_m55_1900_cutoff_20260731T1500Z_fresh.csv"
world_catalog_path = REPO_ROOT / "DB/japan-m75plus-180d-shift90-operators-quantile4-v17/01_inputs/usgs_world_m75_1900_20260801.csv"

japan_cat = pd.read_csv(japan_catalog_path)
japan_cat["time"] = pd.to_datetime(japan_cat["time"], utc=True).dt.tz_localize(None)
japan_m77 = japan_cat[japan_cat["mag"] >= 7.7].copy()
japan_m77["week_start"] = japan_m77["time"].dt.to_period("W-SUN").dt.start_time

world_cat = pd.read_csv(world_catalog_path)
world_cat["time"] = pd.to_datetime(world_cat["time"], utc=True).dt.tz_localize(None)
foreign_m77 = world_cat[
    (world_cat["mag"] >= 7.7) &
    ~((world_cat["latitude"].between(22.0, 50.5)) & (world_cat["longitude"].between(122.0, 156.0)))
].copy()
foreign_m77["week_start"] = foreign_m77["time"].dt.to_period("W-SUN").dt.start_time

japan_weeks = set(japan_m77["week_start"].dt.normalize())
foreign_weeks = set(foreign_m77["week_start"].dt.normalize())

df["japan_m77_event"] = 0
df["is_world_hard_negative"] = 0
df["sample_role"] = "quiet_negative"

for idx in df.index:
    dt = df.at[idx, "date"]
    if dt <= cutoff_date:
        if dt in japan_weeks:
            df.at[idx, "japan_m77_event"] = 1
            df.at[idx, "sample_role"] = "japan_positive"
        elif dt in foreign_weeks:
            df.at[idx, "japan_m77_event"] = 0
            df.at[idx, "is_world_hard_negative"] = 1
            df.at[idx, "sample_role"] = "foreign_hard_negative"
    else:
        df.at[idx, "sample_role"] = "prospective_unlabelled"

out_master = DEMO_DIR / "01_uncompressed_master/master_7d_uncompressed_normalized.csv"
df.to_csv(out_master, index=False)
print("Saved 100% normalized uncompressed master:", out_master)

# Verify min and max across all feature columns
feat_min = df[feature_cols].min().min()
feat_max = df[feature_cols].max().max()
print(f"VERIFICATION: Min across all {len(feature_cols)} features: {feat_min:.6f} | Max: {feat_max:.6f}")
