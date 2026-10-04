#!/usr/bin/env bash
# Step 3: Parallel Ephemerides Extraction from JPL Horizons (Modulo 2)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DLVS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)/DLVS-Wave-v2"
PYTHON_BIN="${PYTHON_BIN:-$(which python3)}"

echo "=== [Step 3/6] Fetching Ephemerides from NASA JPL Horizons ==="
"$PYTHON_BIN" "$DLVS_ROOT/src/horizons.py" \
    --start-time 2024-01-01 --stop-time 2024-05-01 --step-size 1d \
    --observer-type geocentric \
    --observer-lat 0.0 --observer-lon 0.0 --observer-elevation-km 0.0 \
    --bodies sun,moon,mercury,venus,mars,jupiter,saturn \
    --output-csv "$SCRIPT_DIR/ephemerides_daily.csv" \
    --output-report "$SCRIPT_DIR/horizons_report.json"

echo ">>> Step 3 Complete: Ephemerides saved to $SCRIPT_DIR/ephemerides_daily.csv"
