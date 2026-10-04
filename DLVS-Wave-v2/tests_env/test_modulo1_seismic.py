"""Test Modulo 1: Seismic extraction, bounding box check, and format validation."""
import sys
from pathlib import Path

# Add src to python path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from seismic import extract_seismic_events, SeismicQueryConfig, SeismicExtractor
from naming import SEISMIC_CORE_FIELDS, validate_column_names
import pandas as pd


def test_seismic_extractor():
    test_dir = Path(__file__).resolve().parent
    out_csv = test_dir / "test_seismic_output.csv"

    # Define small bounding box (Japan Noto / Central Japan area Jan 2024)
    min_lat, max_lat = 36.0, 38.5
    min_lon, max_lon = 136.0, 138.5
    min_mag = 4.0
    start_time = "2024-01-01"
    end_time = "2024-01-05"

    print(f"[TEST 1] Querying seismic events for box ({min_lat}-{max_lat}, {min_lon}-{max_lon}) mag >= {min_mag}...")
    df, saved_path = extract_seismic_events(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        min_magnitude=min_mag,
        start_time=start_time,
        end_time=end_time,
        output_path=out_csv,
    )

    print(f"[TEST 1] Extracted {len(df)} records. Saved to: {saved_path}")

    # Assertions
    assert saved_path is not None and saved_path.exists(), "Output CSV was not created!"
    assert len(df) > 0, "Expected at least 1 seismic event in test window (Noto Jan 2024)!"

    # Check canonical columns
    for f in SEISMIC_CORE_FIELDS:
        assert f in df.columns, f"Required core column '{f}' missing from output!"

    is_valid, invalid_cols = validate_column_names(df.columns)
    assert is_valid, f"Invalid column names found: {invalid_cols}"

    # Check bounding box
    assert (df["seis_core_latitude"] >= min_lat).all(), "Found record below min_lat!"
    assert (df["seis_core_latitude"] <= max_lat).all(), "Found record above max_lat!"
    assert (df["seis_core_longitude"] >= min_lon).all(), "Found record below min_lon!"
    assert (df["seis_core_longitude"] <= max_lon).all(), "Found record above max_lon!"
    assert (df["seis_core_magnitude"] >= min_mag).all(), "Found record below min_magnitude!"

    print("[TEST 1] SUCCESS: Seismic Extractor test passed!")


if __name__ == "__main__":
    test_seismic_extractor()
