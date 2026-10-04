"""Test Modulo 5 & 6: Micro-master fusion, 2-bit packing, and Optuna hierarchical prefix search."""
import json
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

import numpy as np
import pandas as pd
from master_fusion import MasterBuilder
from optimizer import PrefixFeatureOptimizer, build_feature_hierarchy
from compression import BitPackingConfig


def test_micro_master_and_optuna():
    test_dir = Path(__file__).resolve().parent
    dates = pd.date_range("2024-01-01", periods=10, freq="D").strftime("%Y-%m-%d")

    # Mock Astronomical data
    df_astro = pd.DataFrame({
        "date": dates,
        "astro_sun_dist": np.linspace(0.983, 0.984, 10),
        "astro_sun_ra_icrf": np.linspace(280.0, 290.0, 10),
        "astro_moon_dist": np.linspace(0.0025, 0.0027, 10),
        "astro_moon_ra_icrf": np.linspace(150.0, 270.0, 10),
        "astro_moon_azim": np.linspace(10.0, 350.0, 10),
        "astro_jupiter_dist": np.linspace(4.5, 4.6, 10),
        "astro_jupiter_ra_icrf": np.linspace(45.0, 46.0, 10),
        "astro_jupiter_eclipse_flag": [0.0] * 10,
    })

    # Mock Seismic data
    df_seis = pd.DataFrame({
        "date": ["2024-01-02", "2024-01-05", "2024-01-08"],
        "time": ["2024-01-02T12:00:00.000Z", "2024-01-05T08:30:00.000Z", "2024-01-08T22:15:00.000Z"],
        "seis_core_id": ["eq_001", "eq_002", "eq_003"],
        "seis_core_latitude": [38.2, 38.5, 38.1],
        "seis_core_longitude": [141.0, 141.2, 140.9],
        "seis_core_depth": [25.0, 15.0, 30.0],
        "seis_core_magnitude": [5.2, 4.8, 6.1],
    })

    print("[TEST 5] Fusing micro-master and packing with 2-bit / 16-bit uint container...")
    builder = MasterBuilder(BitPackingConfig(bits_per_field=2, fields_per_container=4, container_dtype="uint16"))
    df_uncompressed, df_packed, fusion_res = builder.build_and_save(
        df_astro=df_astro,
        df_seis=df_seis,
        output_dir=test_dir,
        base_filename="test_micro_master",
    )

    print(f"[TEST 5] Uncompressed master shape: {df_uncompressed.shape}")
    print(f"[TEST 5] Packed master shape: {df_packed.shape}")
    print(f"[TEST 5] Size reduction: {fusion_res.size_reduction_pct}%")

    assert fusion_res.master_uncompressed_path.exists()
    assert fusion_res.master_packed_path.exists()
    assert fusion_res.codebook_path.exists()

    # 2. Test Optuna Hierarchical Prefix Search
    print("[TEST 5] Running Optuna hierarchical prefix search (n_trials=2)...")
    hierarchy = build_feature_hierarchy(df_uncompressed.columns, df=df_uncompressed)
    print(f"[TEST 5] Discovered prefix groups: {sorted(hierarchy.groups)}")
    assert "astro_sun" in hierarchy.groups
    assert "astro_moon" in hierarchy.groups
    assert "astro_jupiter" in hierarchy.groups

    optimizer = PrefixFeatureOptimizer(
        df=df_uncompressed,
        target_col="seis_core_magnitude",
        hierarchy=hierarchy,
    )
    summary, best_features, study = optimizer.optimize(n_trials=2)

    print(f"[TEST 5] Optuna run finished. Best score: {summary['best_score']}")
    print(f"[TEST 5] Selected features ({len(best_features)}): {best_features}")

    assert len(study.trials) == 2, f"Expected 2 trials, got {len(study.trials)}"
    assert summary["best_score"] is not None

    print("[TEST 5] SUCCESS: Micro-master fusion & Optuna Hierarchical Search test passed!")


if __name__ == "__main__":
    test_micro_master_and_optuna()
