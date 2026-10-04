#!/usr/bin/env bash
# One-shot final pipeline: create +7d shifted master, then run matching train.
#
# Usage:
#   cd /mnt/git0/git/repository/DLvsWAVE
#   ./commands/run_japan_30d_shift7d_final.sh
#
# Useful overrides:
#   SKIP_MASTER=1   reuse existing master
#   OUT_DIR=...     master output directory
#   MASTER=...      explicit master CSV for training
#   LOG_FILE=...    train log path
#   DB_FILE=...     train SQLite db name
set -euo pipefail

cd "$(dirname "$0")/.."

DEFAULT_OUT_DIR="/mnt/git0/git/repository/astro-USGS2/DB/japan-mag80-1900plus-30d-shift7d"
OUT_DIR="${OUT_DIR:-$DEFAULT_OUT_DIR}"
MASTER_PATH="${MASTER:-${MASTER_OUT:-$OUT_DIR/master_with_usgs_core_astrofmt.csv}}"
SKIP_MASTER="${SKIP_MASTER:-0}"

echo "======================================================================"
echo " Japan 30d shift+7d - final master + train pipeline"
echo " Master target: $MASTER_PATH"
echo " Forecast:      2026-06-01 -> 2026-09-30"
echo " Common window: previous 3 forecasts + this run smart forecast"
echo " SKIP_MASTER:   $SKIP_MASTER"
echo "======================================================================"

if [[ "$SKIP_MASTER" != "1" ]]; then
    OUT_DIR="$OUT_DIR" MASTER_OUT="$MASTER_PATH" "$PWD/commands/create_master_japan_mag80_30d_shift7d.sh"
else
    echo "[SKIP] Master creation skipped."
fi

MASTER="$MASTER_PATH" "$PWD/commands/train_japan_30d_shift7d_fast.sh"
