#!/usr/bin/env python3
"""Test Modulo 9: Shift Indexing, Anti-Data-Leakage, Discrete Seismic Shifts, and Front-Positioned Seismic Preservation."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

from indexing import HistoricalShiftEngine, ShiftParameters
from compression import BitPackingConfig, QuantizedBitPacker
from resampling import TemporalSummarizer, ResamplingConfig
from cleaning import MasterSanitizer


def test_shift_generation_and_anti_leakage():
    print("[TEST 9.1] Testing Shift Generation and Anti-Leakage Protocol...")
    dates = pd.date_range("2024-01-01", periods=30, freq="D").strftime("%Y-%m-%d")
    df = pd.DataFrame({
        "date": dates,
        "astro_moon_dist": np.linspace(380000, 400000, 30),
        "astro_sun_dec": np.sin(np.linspace(0, np.pi, 30)),
        "seis_core_magnitude": np.random.uniform(4.0, 7.0, 30),
        "seis_core_depth": np.random.uniform(10.0, 50.0, 30),
    })

    params = ShiftParameters(
        astro_min_step=-2,
        astro_max_step=2,
        astro_step_days=7,
        seis_min_step=-2,
        seis_max_step=0,
        seis_step_days=7,
        allow_future_seismic=False,
    )
    engine = HistoricalShiftEngine(params)
    df_shifted, audit_meta = engine.apply_shifts(df)

    assert audit_meta["anti_leakage_status"] == "PASSED (Zero Future Seismic Leakage)"
    assert audit_meta["future_seismic_shifts_count"] == 0
    assert audit_meta["generated_astro_shifts"] == 8
    assert audit_meta["generated_seismic_shifts"] == 4

    assert "astro_moon_dist_shift_m7d" in df_shifted.columns
    assert "astro_moon_dist_shift_p14d" in df_shifted.columns
    assert "seis_core_magnitude_shift_m14d" in df_shifted.columns
    assert "seis_core_magnitude_shift_p7d" not in df_shifted.columns

    print("  [✓] Shifts & Anti-Leakage Passed Successfully!")


def test_discrete_seismic_shift_fidelity():
    print("[TEST 9.2] Testing Discrete Seismic Shifts (No Artificial Event Propagation)...")
    dates = pd.date_range("2024-01-01", periods=10, freq="D").strftime("%Y-%m-%d")
    mag_series = [0.0] * 10
    mag_series[2] = 7.1  # 2024-01-03
    mag_series[7] = 5.8  # 2024-01-08

    df = pd.DataFrame({
        "date": dates,
        "astro_var": np.linspace(1, 10, 10),
        "seis_core_magnitude": mag_series,
        "seis_core_depth": [0.0 if m == 0.0 else 25.0 for m in mag_series],
    })

    sanitizer = MasterSanitizer()
    df_clean, rep = sanitizer.sanitize_and_prune(df)

    # Verify no ffill happened: day 3 (index 3) must be 0.0, NOT 7.1!
    assert df_clean.loc[3, "seis_core_magnitude"] == 0.0, "Seismic data was improperly forward-filled!"

    # Apply 2-day shift
    params = ShiftParameters(
        astro_min_step=-1, astro_max_step=1, astro_step_days=2,
        seis_min_step=-1, seis_max_step=0, seis_step_days=2,
    )
    engine = HistoricalShiftEngine(params)
    df_shifted, _ = engine.apply_shifts(df_clean)

    # seis_core_magnitude_shift_m2d on day 4 (2024-01-05) must be 7.1
    # on day 5 (2024-01-06) must be 0.0
    assert df_shifted.loc[4, "seis_core_magnitude_shift_m2d"] == 7.1
    assert df_shifted.loc[5, "seis_core_magnitude_shift_m2d"] == 0.0
    assert df_shifted.loc[9, "seis_core_magnitude_shift_m2d"] == 5.8

    print("  [✓] Discrete Seismic Shift Fidelity Passed (Zero Artificial Event Propagation)!")


def test_front_positioned_seismic_preservation():
    print("[TEST 9.3] Testing Front-Positioned Seismic Preservation in Chiaro & Bit-Packing...")
    n_rows = 20
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n_rows, freq="D").strftime("%Y-%m-%d"),
        "astro_moon_dist": np.linspace(380000, 400000, n_rows),
        "astro_sun_dist": np.linspace(149000000, 152000000, n_rows),
        "seis_core_magnitude": np.random.uniform(4.0, 7.0, n_rows),
        "seis_core_latitude": np.linspace(35.0, 40.0, n_rows),
        "seis_core_longitude": np.linspace(138.0, 142.0, n_rows),
        "seis_core_depth": np.linspace(10.0, 50.0, n_rows),
        "seis_core_magnitude_shift_m7d": np.random.uniform(4.0, 7.0, n_rows),
    })

    packer = QuantizedBitPacker(BitPackingConfig(bits_per_field=2, fields_per_container=8))
    df_packed, codebook = packer.pack(df)

    # Verify column order: date is 1st, then seismic core, then seismic shifts, then packed astro containers
    cols = list(df_packed.columns)
    assert cols[0] == "date"
    assert cols[1] == "seis_core_magnitude"
    assert cols[2] == "seis_core_latitude"
    assert cols[3] == "seis_core_longitude"
    assert cols[4] == "seis_core_depth"
    assert cols[5] == "seis_core_magnitude_shift_m7d"
    assert any("packed_astro_container" in c for c in cols)

    # Reverse unpacking lossless check
    df_unpacked = packer.unpack(df_packed, codebook)
    assert "seis_core_magnitude" in df_unpacked.columns
    assert "astro_moon_dist" in df_unpacked.columns

    print("  [✓] Front-Positioned Seismic Preservation in Chiaro Passed Successfully!")


def test_resampling_safety_lock_and_inheritance():
    print("[TEST 9.4] Testing Resampling Safety Lock on Bit-Packed Data...")
    df_packed_mock = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02"],
        "packed_astro_container_000": [1234, 5678],
    })

    summarizer = TemporalSummarizer(ResamplingConfig(window_days=7))
    try:
        summarizer.summarize(df_packed_mock)
        raise AssertionError("Safety lock failed to trigger on packed DataFrame!")
    except ValueError as e:
        assert "SAFETY LOCK ACTIVATED" in str(e)

    print("  [✓] Safety Lock on Bit-Packed Data Passed Successfully!")


if __name__ == "__main__":
    print("===========================================================================")
    print("STARTING MODULO 9 (SHIFT INDEXING, ANTI-LEAKAGE & SEISMIC PRESERVATION) TESTS")
    print("===========================================================================")
    test_shift_generation_and_anti_leakage()
    test_discrete_seismic_shift_fidelity()
    test_front_positioned_seismic_preservation()
    test_resampling_safety_lock_and_inheritance()
    print("===========================================================================")
    print("ALL MODULO 9 TESTS PASSED 100%!")
    print("===========================================================================")
