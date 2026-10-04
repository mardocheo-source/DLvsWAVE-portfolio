#!/usr/bin/env bash
# ==============================================================================
# DLVS-WAVE v2.0 - Complete Step-by-Step Sequence Runner for: Run_1_Japan_Tohoku
# Runs scripts 01 -> 02 -> 03 -> 04 -> 05 -> 06 in chronological order
# ==============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "================================================================================"
echo " LAUNCHING FULL STEP-BY-STEP SEQUENCE FOR: Run_1_Japan_Tohoku"
echo "================================================================================"

t0=$(date +%s)

bash "$SCRIPT_DIR/01_extract_seismic.sh"
bash "$SCRIPT_DIR/02_render_map.sh"
bash "$SCRIPT_DIR/03_fetch_horizons.sh"
bash "$SCRIPT_DIR/04_fuse_and_compress_master.sh"
bash "$SCRIPT_DIR/05_resample_30d_and_compress.sh"
bash "$SCRIPT_DIR/06_run_optuna_optimizer.sh"

t1=$(date +%s)
elapsed=$((t1 - t0))

echo ""
echo "================================================================================"
echo " ALL 6 STEPS EXECUTED SUCCESSFULLY IN ${elapsed}s!"
echo " Directory Artifacts:"
ls -lh "$SCRIPT_DIR"
echo "================================================================================"
