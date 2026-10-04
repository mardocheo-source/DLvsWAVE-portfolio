"""Test Modulo 8: Markdown Decodification Manifest Generator."""
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

import numpy as np
import pandas as pd
from compression import BitPackingConfig, QuantizedBitPacker
from reporting import generate_master_manifest


def test_manifest_reporting():
    test_dir = Path(__file__).resolve().parent
    out_md = test_dir / "test_manifest_report.md"

    # Create mock dataset
    dates = pd.date_range("2024-01-01", periods=20, freq="D").strftime("%Y-%m-%d")
    df_raw = pd.DataFrame({
        "date": dates,
        "astro_sun_dist": np.linspace(0.983, 0.985, 20),
        "astro_sun_azim": np.linspace(100.0, 260.0, 20),
        "astro_moon_dist": np.linspace(0.0025, 0.0028, 20),
        "astro_moon_phase_angle": np.linspace(0.0, 180.0, 20),
        "astro_jupiter_dist": np.linspace(4.5, 4.6, 20),
        "astro_jupiter_ra_icrf": np.linspace(30.0, 35.0, 20),
        "astro_saturn_dist": np.linspace(9.5, 9.6, 20),
        "seis_core_magnitude": np.linspace(4.0, 6.5, 20),
    })

    packer = QuantizedBitPacker(BitPackingConfig(bits_per_field=2, fields_per_container=8))
    df_packed, codebook = packer.pack(df_raw)

    print("[TEST 8] Generating Markdown Decodification Manifest Report...")
    saved_path = generate_master_manifest(
        df_uncompressed=df_raw,
        df_packed=df_packed,
        codebook=codebook,
        output_md_path=out_md,
        master_name="Test Validation Master",
    )

    print(f"[TEST 8] Manifest report generated at: {saved_path}")
    assert saved_path.exists(), "Manifest Markdown file was not created!"
    
    with saved_path.open("r", encoding="utf-8") as f:
        text = f.read()
        assert "Decodification Matrix" in text
        assert "packed_" in text
        assert "Quantile 25%" in text
        assert "astro_sun_dist" in text

    print("[TEST 8] SUCCESS: Master Manifest and Decodification Reporting test passed!")


if __name__ == "__main__":
    test_manifest_reporting()
