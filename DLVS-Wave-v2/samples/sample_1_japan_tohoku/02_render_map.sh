#!/usr/bin/env bash
# Step 2: Advanced Parametric Mapping (Aging Fading, Sub-ROI Box & Leader Lines) (Modulo 7)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DLVS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)/DLVS-Wave-v2"
PYTHON_BIN="${PYTHON_BIN:-$(which python3)}"

echo "=== [Step 2/6] Rendering High-Definition Parametric Seismic Map ==="
"$PYTHON_BIN" "$DLVS_ROOT/src/visualization.py" \
    --input-csv "$SCRIPT_DIR/seismic_events.csv" \
    --output-map "$SCRIPT_DIR/seismic_events_map.png" \
    --map-title "Seismic Activity Map (Sample 1 Japan Tohoku)" \
    --min-lat 36.0 --max-lat 41.5 \
    --min-lon 139.0 --max-lon 145.0 \
    --enable-time-aging \
    --sub-min-lat 37.5 --sub-max-lat 39.5 \
    --sub-min-lon 140.5 --sub-max-lon 143.0 \
    --sub-box-label "Sub-ROI Target" \
    --max-annotated-peaks 2

echo ">>> Step 2 Complete: High-res map generated at $SCRIPT_DIR/seismic_events_map.png"
