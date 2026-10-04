#!/usr/bin/env bash
# ==============================================================================
# DLVS-WAVE v2.0 - Self-Contained Reproduction Script
# Run: Run_1_Japan_Tohoku
# Timespan: 2024-01-01 to 2024-05-01
# Bounding Box: Lat [36.0, 41.5], Lon [139.0, 145.0], Min Mag: 4.5
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2"

# Automatic Virtual Environment Detection & Activation
if [ -f "/mnt/git0/git/repository/DLvsWAVE/.venv/bin/python3" ]; then
    PYTHON_EXEC="/mnt/git0/git/repository/DLvsWAVE/.venv/bin/python3"
elif [ -n "$VIRTUAL_ENV" ]; then
    PYTHON_EXEC="python3"
else
    PYTHON_EXEC="python3"
fi

export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

echo "================================================================================"
echo " REPRODUCING PIPELINE RUN: Run_1_Japan_Tohoku"
echo " Python Executable: $PYTHON_EXEC"
echo " Output Directory:  $SCRIPT_DIR"
echo "================================================================================"

# --- STEP 1: PARAMETRIC SEISMIC EXTRACTION (USGS FDSN) ---
echo "[1/4] Extracting seismic events..."
$PYTHON_EXEC "$PROJECT_ROOT/src/seismic.py"     --min-lat 36.0     --max-lat 41.5     --min-lon 139.0     --max-lon 145.0     --min-magnitude 4.5     --start-time "2024-01-01"     --end-time "2024-05-01"     --output-csv "$SCRIPT_DIR/seismic_events.csv"

# --- STEP 2: PARAMETRIC MAP GENERATION ---
echo "[2/4] Rendering parametric geographic seismic map..."
$PYTHON_EXEC "$PROJECT_ROOT/src/visualization.py"     --input-csv "$SCRIPT_DIR/seismic_events.csv"     --output-png "$SCRIPT_DIR/seismic_events_map.png"     --min-lat 36.0     --max-lat 41.5     --min-lon 139.0     --max-lon 145.0     --observer-lat 38.75     --observer-lon 142.0     --size-by magnitude     --color-by auto     --min-alpha 0.30     --max-alpha 0.95     --title "Run_1_Japan_Tohoku - Seismic Activity & Observer Map"

# --- STEP 3 & 4: COMPLETE MASTER FUSION, BIT-PACKING & MANIFEST GENERATION ---
echo "[3/4] Running Master Ephemerides Fetch, 16-Bit Bit-Packing & 30-Day Resampling..."
$PYTHON_EXEC "$PROJECT_ROOT/src/pipeline.py"     --run-name "Run_1_Japan_Tohoku"     --output-dir "$SCRIPT_DIR"     --min-lat 36.0     --max-lat 41.5     --min-lon 139.0     --max-lon 145.0     --min-magnitude 4.5     --start-time "2024-01-01"     --stop-time "2024-05-01"     --window-days-summary 30     --bits-per-field 2     --fields-per-container 8     --run-optuna     --optuna-trials 5

echo ""
echo "================================================================================"
echo " REPRODUCTION COMPLETED SUCCESSFULLY FOR: Run_1_Japan_Tohoku"
ls -lh "$SCRIPT_DIR"
echo "================================================================================"
