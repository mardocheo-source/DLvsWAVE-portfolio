"""Test Modulo 3: Temporal Resampling, Naming Suffix Aggregations & Peak Seismic Coupling."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from naming import parse_field_name, validate_column_names
from resampling import resample_master, ResamplingConfig, TemporalSummarizer


def test_temporal_resampling():
    test_dir = Path(__file__).resolve().parent
    output_csv = test_dir / "test_resampled_3d_output.csv"

    dates = pd.date_range("2024-01-01", periods=7, freq="D").strftime("%Y-%m-%d")
    df_mock = pd.DataFrame({
        "date": dates,
        "astro_sun_dist": [0.983 + 0.0001 * i for i in range(7)],
        "astro_moon_dist": [0.0025 + 0.00005 * i for i in range(7)],
        "astro_moon_azim": [100.0 + 10.0 * i for i in range(7)],
    })

    print(f"[TEST 3.1] Running 3-day summarization on {len(df_mock)} rows...")
    df_res, saved_path = resample_master(
        df=df_mock,
        window_days=3,
        aggregations=("min", "max", "mean", "median"),
        output_path=output_csv,
    )

    print(f"[TEST 3.1] Resampled to {len(df_res)} window rows, {len(df_res.columns)} columns.")
    assert saved_path is not None and saved_path.exists(), "Resampled CSV was not saved!"
    assert len(df_res) >= 2, f"Expected at least 2 aggregated 3-day windows for 7 days, got {len(df_res)}"

    # Check aggregation suffix naming
    is_valid, invalid_cols = validate_column_names(df_res.columns)
    assert is_valid, f"Invalid column names in resampled data: {invalid_cols}"


def test_peak_seismic_coupling():
    print("[TEST 3.2] Testing Physical Peak Seismic Coupling (No Blending of Coordinates)...")
    # 10 days: Window 1 (day 0..4) has 2 earthquakes (M4.2 at 36.1,137.1,12km and M6.8 at 38.2,142.1,24km)
    # Window 2 (day 5..9) has 0 earthquakes
    dates = pd.date_range("2024-01-01", periods=10, freq="D").strftime("%Y-%m-%d")
    df = pd.DataFrame({
        "date": dates,
        "seis_core_magnitude": [0.0, 4.2, 6.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "seis_core_latitude": [0.0, 36.1, 38.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "seis_core_longitude": [0.0, 137.1, 142.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "seis_core_depth": [0.0, 12.0, 24.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "astro_sun_dist": np.linspace(1, 10, 10),
    })

    summarizer = TemporalSummarizer(ResamplingConfig(window_days=5))
    df_res = summarizer.summarize(df)

    # Window 1 (2024-01-01) must carry the exact peak M6.8 event coordinates!
    row0 = df_res.iloc[0]
    assert row0["seis_core_magnitude"] == 6.8, f"Expected 6.8, got {row0['seis_core_magnitude']}"
    assert row0["seis_core_latitude"] == 38.2, f"Latitude was blended! Expected 38.2, got {row0['seis_core_latitude']}"
    assert row0["seis_core_longitude"] == 142.1, f"Longitude was blended! Expected 142.1, got {row0['seis_core_longitude']}"
    assert row0["seis_core_depth"] == 24.0, f"Depth was blended! Expected 24.0, got {row0['seis_core_depth']}"

    # Window 2 (2024-01-06) had no earthquakes -> all 0.0
    row1 = df_res.iloc[1]
    assert row1["seis_core_magnitude"] == 0.0
    assert row1["seis_core_latitude"] == 0.0
    assert row1["seis_core_longitude"] == 0.0
    assert row1["seis_core_depth"] == 0.0

    print("  [✓] Physical Peak Seismic Coupling Verified 100% (Coordinates Preserved Pure & Unblended)!")


if __name__ == "__main__":
    test_temporal_resampling()
    test_peak_seismic_coupling()
