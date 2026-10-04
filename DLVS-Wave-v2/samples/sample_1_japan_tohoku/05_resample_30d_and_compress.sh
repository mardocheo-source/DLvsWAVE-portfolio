#!/usr/bin/env bash
# Step 5: Multi-Scale Temporal Resampling (30-Day Window) & Scale Inheritance (Modulo 3 & 4)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DLVS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)/DLVS-Wave-v2"
PYTHON_BIN="${PYTHON_BIN:-$(which python3)}"

echo "=== [Step 5/6] Temporal Summarization (30d) & Scale-Inherited Shifts ==="
"$PYTHON_BIN" "$DLVS_ROOT/src/resampling.py" \
    --input-csv "$SCRIPT_DIR/master_1d_uncompressed.csv" \
    --output-csv "$SCRIPT_DIR/master_30d_summarized.csv" \
    --window-days 30 \
    --aggregations min max mean median \
    --recalculate-shifts \
    --shift-config-path "$SCRIPT_DIR/master_1d_schema_config.json"

echo "=== Compressing 30-Day Summarized Master into Astro Bit-Packed Containers ==="
"$PYTHON_BIN" "$DLVS_ROOT/src/compression.py" \
    --input-csv "$SCRIPT_DIR/master_30d_summarized.csv" \
    --output-csv "$SCRIPT_DIR/master_30d_summarized_packed_16bit.csv" \
    --output-codebook "$SCRIPT_DIR/master_30d_summarized_codebook.json" \
    --bits-per-field 2 \
    --fields-per-container 8 \
    --container-dtype uint16

echo ">>> Step 5 Complete: 30D Master & Codebook created in $SCRIPT_DIR"
