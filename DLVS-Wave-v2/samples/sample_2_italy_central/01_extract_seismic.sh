#!/usr/bin/env bash
# Step 1: Seismic Catalog Extraction from USGS (Modulo 1)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DLVS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)/DLVS-Wave-v2"
PYTHON_BIN="${PYTHON_BIN:-$(which python3)}"

echo "=== [Step 1/6] Extracting Seismic Events from USGS ==="
"$PYTHON_BIN" "$DLVS_ROOT/src/seismic.py" \
    --min-lat 41.0 --max-lat 44.5 \
    --min-lon 11.5 --max-lon 15.0 \
    --start-date 2024-01-01 --end-date 2024-05-01 \
    --min-mag 4.0 \
    --output-csv "$SCRIPT_DIR/seismic_events.csv"

echo ">>> Step 1 Complete: Saved to $SCRIPT_DIR/seismic_events.csv"
