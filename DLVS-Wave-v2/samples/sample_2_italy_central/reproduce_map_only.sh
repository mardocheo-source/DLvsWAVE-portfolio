#!/usr/bin/env bash
# ==============================================================================
# DLVS-WAVE v2.0 - Fast Map Reproduction Script (1-Second Execution)
# Run: Run_2_Italy_Central
# Features: Summary Metrics Box, Mainshock Peak Leader Lines, Aging Fading, Sub-ROI Box
# ==============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2"
PYTHON_EXEC="/mnt/git0/git/repository/DLvsWAVE/.venv/bin/python3"

echo "Rendering parametric map for: Run_2_Italy_Central with Summary Box & Peak Leader Lines..."
$PYTHON_EXEC "$PROJECT_ROOT/src/visualization.py" \
    --input-csv "$SCRIPT_DIR/seismic_events.csv" \
    --output-png "$SCRIPT_DIR/seismic_events_map.png" \
    --min-lat 41.0 \
    --max-lat 44.5 \
    --min-lon 11.5 \
    --max-lon 15.0 \
    --margin-deg 1.5 \
    --size-by magnitude \
    --color-by auto \
    --min-alpha 0.30 \
    --max-alpha 0.95 \
    --max-peaks 1 \
    --sub-min-lat 42.0 \
    --sub-max-lat 43.5 \
    --sub-min-lon 12.5 \
    --sub-max-lon 14.0 \
    --observer-lat 42.75 \
    --observer-lon 13.25 \
    --title "Run_2_Italy_Central - Seismic Activity & Peak Map"

echo "Map successfully updated: $SCRIPT_DIR/seismic_events_map.png"
