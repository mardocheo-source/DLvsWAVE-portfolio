#!/usr/bin/env bash
# One-shot pipeline: create Japan/Nankai 360d annual master, then train.
#
# Usage:
#   cd /mnt/git0/git/repository/DLvsWAVE
#   ./commands/run_japan_nankai_360d_final.sh
#
# Useful overrides:
#   SKIP_MASTER=1
#   START_DATE=1498-01-01 END_DATE=2035-12-31
#   FORECAST_START=2026-01-01 FORECAST_END=2035-12-31
#   OUT_DIR=...
#   MASTER=...
#   DB_FILE=...
#   LOG_FILE=...
set -euo pipefail

cd "$(dirname "$0")/.."

DEFAULT_OUT_DIR="/mnt/git0/git/repository/astro-USGS2/DB/japan-nankai-big-one-360d"
OUT_DIR="${OUT_DIR:-$DEFAULT_OUT_DIR}"
MASTER_PATH="${MASTER:-${MASTER_OUT:-$OUT_DIR/master_with_usgs_core_astrofmt.csv}}"
SKIP_MASTER="${SKIP_MASTER:-0}"

echo "======================================================================"
echo " Japan/Nankai 360d annual - final master + train pipeline"
echo " Master target:  $MASTER_PATH"
echo " Step:           360d"
echo " Record meaning: date is period START; one row = one 360d period"
echo " SKIP_MASTER:    $SKIP_MASTER"
echo "======================================================================"

if [[ "$SKIP_MASTER" != "1" ]]; then
    OUT_DIR="$OUT_DIR" MASTER_OUT="$MASTER_PATH" "$PWD/commands/create_master_japan_nankai_360d.sh"
else
    echo "[SKIP] Master creation skipped."
fi

MASTER="$MASTER_PATH" "$PWD/commands/train_japan_nankai_360d_fast.sh"
