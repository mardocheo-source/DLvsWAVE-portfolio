#!/usr/bin/env bash
# Step 4: Chronological Fusion, Shift Indexing, Anti-Leakage Audit & 1D Bit-Packing (Modulo 5, 8, 9, 10)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DLVS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)/DLVS-Wave-v2"
PYTHON_BIN="${PYTHON_BIN:-$(which python3)}"

echo "=== [Step 4/6] Chronological Master Fusion, Shift Generation & Astro Bit-Packing ==="
"$PYTHON_BIN" "$DLVS_ROOT/src/master_fusion.py" \
    --astro-csv "$SCRIPT_DIR/ephemerides_daily.csv" \
    --seis-csv "$SCRIPT_DIR/seismic_events.csv" \
    --output-dir "$SCRIPT_DIR" \
    --base-filename master_1d \
    --bits-per-field 2 \
    --fields-per-container 8 \
    --container-dtype uint16 \
    --astro-min-step -5 --astro-max-step 5 --astro-step-days 7 \
    --seis-min-step -5 --seis-max-step 0 --seis-step-days 7

echo ">>> Step 4 Complete: 1D Uncompressed & Bit-Packed Masters + Audit Report generated in $SCRIPT_DIR"
