#!/usr/bin/env python3
"""Test Modulo 10: Master Sanitization, Alphanumeric Flag Encoding & Zero-Variance Pruning."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

from cleaning import MasterSanitizer, sanitize_master
from compression import BitPackingConfig, QuantizedBitPacker


def test_alphanumeric_encoding_and_pruning():
    print("[TEST 10.1] Testing Alphanumeric Flag Encoding and Constant Column Pruning...")
    n_rows = 20
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n_rows, freq="D").strftime("%Y-%m-%d"),
        # Alphanumeric flags
        "astro_sun_presence": ["/L" if i % 2 == 0 else "/T" for i in range(n_rows)],
        "astro_moon_flag": ["m", "r", "t", "*", ""] * 4,
        # Real variable numeric
        "astro_moon_dist": np.linspace(380000, 400000, n_rows),
        "seis_core_magnitude": np.random.uniform(4.0, 7.0, n_rows),
        # Constant zero-variance columns (must be pruned!)
        "astro_sun_helio_dist": [0.0] * n_rows,
        "astro_sun_phase_angle": [0.0] * n_rows,
        "astro_sun_eclipse_flag": ["-"] * n_rows,
    })

    sanitizer = MasterSanitizer()
    df_clean, report = sanitizer.sanitize_and_prune(df)

    # 1. Alphanumeric columns must be converted to float
    assert pd.api.types.is_numeric_dtype(df_clean["astro_sun_presence"]), "Failed to encode /L and /T flags to numeric!"
    assert pd.api.types.is_numeric_dtype(df_clean["astro_moon_flag"]), "Failed to encode lunar flags to numeric!"
    assert set(df_clean["astro_sun_presence"].unique()) == {1.0, 2.0}

    # 2. Constant columns must be pruned
    assert "astro_sun_helio_dist" not in df_clean.columns, "Failed to prune constant 0.0 helio_dist!"
    assert "astro_sun_phase_angle" not in df_clean.columns, "Failed to prune constant phase_angle!"
    assert "astro_sun_eclipse_flag" not in df_clean.columns, "Failed to prune constant eclipse_flag!"
    assert report.total_pruned_count == 3, f"Expected 3 pruned cols, got {report.total_pruned_count}"

    print("  [✓] Alphanumeric Encoding & Pruning Passed Successfully!")


def test_packed_containers_contain_no_degenerate_65535():
    print("[TEST 10.2] Testing Bit-Packing Output Has No Degenerate 65535 Constant Containers...")
    n_rows = 50
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n_rows, freq="D").strftime("%Y-%m-%d"),
        "astro_var_1": np.random.uniform(10, 50, n_rows),
        "astro_var_2": np.random.uniform(100, 200, n_rows),
        "astro_var_3": np.random.uniform(0.1, 0.9, n_rows),
        "astro_var_4": np.sin(np.linspace(0, 10, n_rows)),
        # Flat columns
        "astro_flat_1": [0.0] * n_rows,
        "astro_flat_2": [5.0] * n_rows,
    })

    # Packing with zero-variance pruning enabled
    packer = QuantizedBitPacker(BitPackingConfig(bits_per_field=2, fields_per_container=8, prune_zero_variance=True))
    df_packed, codebook = packer.pack(df)

    # Verify that flat columns were pruned from codebook and packed containers
    assert "astro_flat_1" in codebook.pruned_constant_columns
    assert "astro_flat_2" in codebook.pruned_constant_columns

    # Verify that packed containers vary across rows and are not stuck on constant 65535
    for col in df_packed.columns:
        if col.startswith("packed_"):
            vals = df_packed[col].to_numpy()
            assert not (vals == 65535).all(), f"Container {col} is degenerate constant 65535!"
            assert len(np.unique(vals)) > 1, f"Container {col} has zero variation!"

    print("  [✓] Zero-Variance Pruning in Bit-Packing Passed (No 65535 constant containers)!")


if __name__ == "__main__":
    print("===========================================================================")
    print("STARTING MODULO 10 (SANITIZATION, ENCODING & PRUNING) TESTS")
    print("===========================================================================")
    test_alphanumeric_encoding_and_pruning()
    test_packed_containers_contain_no_degenerate_65535()
    print("===========================================================================")
    print("ALL MODULO 10 TESTS PASSED 100%!")
    print("===========================================================================")
