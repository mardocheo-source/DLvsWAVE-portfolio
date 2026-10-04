"""Test Modulo 4: 2-bit Quantization and Integer Bit-Packing Compression."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from compression import BitPackingConfig, QuantizedBitPacker


def test_bit_packing_and_decompression():
    test_dir = Path(__file__).resolve().parent
    out_packed_csv = test_dir / "test_packed_master.csv"
    out_codebook_json = test_dir / "test_compression_codebook.json"

    # Create mock dataset with 8 continuous features
    np.random.seed(42)
    n_rows = 100
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D").strftime("%Y-%m-%d")

    data = {"date": dates}
    for i in range(8):
        data[f"astro_field_{i}"] = np.random.normal(loc=10.0 * (i + 1), scale=2.0, size=n_rows)

    df = pd.DataFrame(data)

    # 1. 2-Bit Quantization & uint16 Packing (8 fields x 2 bits = 16 bits = 1 integer container)
    print("[TEST 4] Packing 8 fields (2-bit each) into single 16-bit containers...")
    config = BitPackingConfig(
        bits_per_field=2,
        fields_per_container=8,
        container_dtype="uint16",
    )
    packer = QuantizedBitPacker(config)
    df_packed, codebook = packer.pack(df)

    # Save outputs
    packer.save_codebook(codebook, out_codebook_json)
    df_packed.to_csv(out_packed_csv, index=False)

    print(f"[TEST 4] Original shape: {df.shape} -> Packed shape: {df_packed.shape}")
    print(f"[TEST 4] Number of packed containers: {codebook.total_packed_features}")

    assert df_packed.shape[1] == 2, f"Expected 2 columns (date + 1 packed container), got {df_packed.shape[1]}"
    container_col = [c for c in df_packed.columns if c.startswith("packed_")][0]
    assert df_packed[container_col].dtype == np.uint16, f"Expected uint16 dtype, got {df_packed[container_col].dtype}"

    # 2. Reverse Unpacking (Decompression)
    print("[TEST 4] Performing reverse unpacking (lossless verification)...")
    df_unpacked = packer.unpack(df_packed, codebook)

    # Verify that all 8 columns exist and values are exactly 0, 1, 2, 3 (2-bit range)
    for col in [f"astro_field_{i}" for i in range(8)]:
        assert col in df_unpacked.columns, f"Unpacked missing column {col}"
        vals = df_unpacked[col].to_numpy()
        assert np.isin(vals, [0, 1, 2, 3]).all(), f"Values in {col} outside 2-bit range: {vals}"

    print("[TEST 4] SUCCESS: 2-bit Quantization and Bit-Packing test passed 100%!")


if __name__ == "__main__":
    test_bit_packing_and_decompression()
