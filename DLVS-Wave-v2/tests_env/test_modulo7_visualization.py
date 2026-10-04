"""Test Modulo 7: Parametric Seismic Mapping, Size-By, Auto Color-By, Aging Fading, and Sub-ROI Box."""
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

import numpy as np
import pandas as pd
from visualization import plot_seismic_map


def test_seismic_mapping():
    test_dir = Path(__file__).resolve().parent
    out_map1 = test_dir / "test_seismic_map_aging_subbox.png"
    out_map2 = test_dir / "test_seismic_map_dual_magnitude.png"

    # Create realistic mock earthquake cluster in Japan Tohoku over historical timeline
    np.random.seed(42)
    n_events = 40
    dates = pd.date_range("1900-01-01", periods=n_events, freq="3YS").strftime("%Y-%m-%dT%H:%M:%SZ")
    df_mock = pd.DataFrame({
        "seis_core_latitude": np.random.uniform(36.5, 41.0, n_events),
        "seis_core_longitude": np.random.uniform(139.5, 144.5, n_events),
        "seis_core_magnitude": np.random.uniform(4.5, 7.8, n_events),
        "seis_core_depth": np.random.uniform(10.0, 90.0, n_events),
        "time": list(dates),
    })

    # Test 1: Size by magnitude, Color auto (depth variance), Aging Fading ON, Nested Sub-ROI Box
    print("[TEST 7.1] Testing Map with Size=Magnitude, Color=Auto, Aging Fading=ON, and Nested Sub-ROI Box...")
    saved1 = plot_seismic_map(
        df_seis=df_mock,
        min_lat=35.0,
        max_lat=41.5,
        min_lon=138.0,
        max_lon=145.0,
        margin_deg=1.5,
        size_by="magnitude",
        color_by="auto",
        enable_aging_fading=True,
        min_alpha=0.30,
        max_alpha=0.95,
        sub_min_lat=37.5,
        sub_max_lat=39.5,
        sub_min_lon=140.5,
        sub_max_lon=143.0,
        observer_lat=38.25,
        observer_lon=141.5,
        title="Japan Century Quakes - Aging Fading & Nested Sub-ROI",
        output_path=out_map1,
    )
    assert saved1.exists() and saved1.stat().st_size > 5000

    # Test 2: Dual signal (Size=Magnitude, Color=Magnitude, Aging Fading=ON)
    print("[TEST 7.2] Testing Dual Signal Map (Size=Magnitude, Color=Magnitude)...")
    saved2 = plot_seismic_map(
        df_seis=df_mock,
        min_lat=35.0,
        max_lat=41.5,
        min_lon=138.0,
        max_lon=145.0,
        margin_deg=1.5,
        size_by="magnitude",
        color_by="magnitude",
        colormap="plasma",
        enable_aging_fading=True,
        title="Japan Century Quakes - Dual Magnitude Signal Map",
        output_path=out_map2,
    )
    assert saved2.exists() and saved2.stat().st_size > 5000

    print("[TEST 7] SUCCESS: Extended Parametric Seismic Mapping test passed 100%!")


if __name__ == "__main__":
    test_seismic_mapping()
