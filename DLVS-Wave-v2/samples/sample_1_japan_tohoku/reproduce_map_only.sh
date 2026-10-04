#!/usr/bin/env bash
# ==============================================================================
# DLVS-WAVE v2.0 - Fast Map Reproduction Script (1-Second Execution)
# Run: Run_1_Japan_Tohoku
# Features: Summary Metrics Box, Mainshock Peak Leader Lines, Aging Fading, Sub-ROI Box
# ==============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2"
PYTHON_EXEC="/mnt/git0/git/repository/DLvsWAVE/.venv/bin/python3"

echo "Rendering parametric map for: Run_1_Japan_Tohoku with Summary Box & Peak Leader Lines..."
$PYTHON_EXEC "$PROJECT_ROOT/src/visualization.py" \
    --input-csv "$SCRIPT_DIR/seismic_events.csv" \
    --output-png "$SCRIPT_DIR/seismic_events_map.png" \
    --min-lat 36.0 \
    --max-lat 41.5 \
    --min-lon 139.0 \
    --max-lon 145.0 \
    --margin-deg 1.5 \
    --size-by magnitude \
    --color-by auto \
    --min-alpha 0.30 \
    --max-alpha 0.95 \
    --max-peaks 2 \
    --sub-min-lat 37.5 \
    --sub-max-lat 39.5 \
    --sub-min-lon 140.5 \
    --sub-max-lon 143.0 \
    --observer-lat 38.75 \
    --observer-lon 142.0 \
    --title "Run_1_Japan_Tohoku - Seismic Activity & Peak Map"

echo "Map successfully updated: $SCRIPT_DIR/seismic_events_map.png"
