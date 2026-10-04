#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PY="/mnt/git0/git/repository/DLvsWAVE/.venv/bin/python3"

echo "================================================================================"
echo " DLVS-WAVE V2.0 - BASH TEST & EXTENDED VISUAL PIPELINE RUN"
echo "================================================================================"
echo "Base Directory: $BASE_DIR"
echo "Python Executable: $VENV_PY"
echo ""

# 1. Run Complete 7-Module Validation Suite
echo ">>> STEP 1: Running All 7 Unit & Integration Module Tests <<<"
$VENV_PY "$SCRIPT_DIR/run_all_tests.py"
echo ""

# 2. Execute End-to-End Visual Demo Run inside tests_env
DEMO_OUT_DIR="$SCRIPT_DIR/demo_visual_run"
mkdir -p "$DEMO_OUT_DIR"

echo ">>> STEP 2: Executing Full End-to-End Pipeline with Map & Manifest Generator <<<"
$VENV_PY - <<PY_EOF
import sys
from pathlib import Path
sys.path.insert(0, "$BASE_DIR/src")

from horizons import STANDARD_BASE_BODIES
from pipeline import PipelineRunConfig, execute_pipeline

config = PipelineRunConfig(
    run_name="Demo_Visual_Test_Noto_Japan",
    output_dir=Path("$DEMO_OUT_DIR"),
    min_lat=36.0,
    max_lat=38.5,
    min_lon=136.0,
    max_lon=138.5,
    min_magnitude=3.8,
    start_time="2024-01-01",
    stop_time="2024-03-01",  # 60 days
    bodies=STANDARD_BASE_BODIES,
    window_days_summary=30,
    bits_per_field=2,
    fields_per_container=8,  # 8 x 2-bit = 16-bit uint
    run_optuna=True,
    optuna_trials=5,
    generate_map=True,
    map_margin_deg=1.5,
)

summary = execute_pipeline(config)
print("\n=== DEMO PIPELINE FINISHED SUCCESSFULLY! ===")
print(f"Seismic Events Extracted : {summary.seismic_events_count}")
print(f"Map Image Generated      : {summary.seismic_map_path}")
print(f"Master Manifest Report   : {summary.master_manifest_path}")
print(f"Raw Master CSV           : {summary.raw_master_path} ({summary.raw_size_bytes:,} bytes)")
print(f"16-Bit Packed Master CSV : {summary.packed_16bit_master_path} ({summary.packed_size_bytes:,} bytes)")
print(f"Storage Reduction        : {summary.size_reduction_pct}%")
print(f"30-Day Summarized Master : {summary.summarized_30d_master_path}")
PY_EOF

echo ""
echo "================================================================================"
echo " DEMO OUTPUT ARTIFACTS GENERATED IN $DEMO_OUT_DIR:"
ls -lh "$DEMO_OUT_DIR"
echo "================================================================================"
