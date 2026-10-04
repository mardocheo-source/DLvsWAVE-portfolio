#!/usr/bin/env bash
# One-shot pipeline: create the +21d shifted master, then run the matching train.
#
# Usage:
#   cd /mnt/git0/git/repository/DLvsWAVE
#   ./commands/run_japan_30d_shift21d_fast.sh
#
# Overrides are passed through to the two child scripts. Useful ones:
#   OUT_DIR, MASTER_OUT, MASTER, QUANT_BINS, DB_FILE, LOG_FILE, PYTHON_BIN
set -euo pipefail

cd "$(dirname "$0")/.."

DEFAULT_OUT_DIR="/mnt/git0/git/repository/astro-USGS2/DB/japan-mag80-1900plus-30d-shift21d"
MASTER_PATH="${MASTER:-${MASTER_OUT:-${OUT_DIR:-$DEFAULT_OUT_DIR}/master_with_usgs_core_astrofmt.csv}}"

echo "======================================================================"
echo " Japan 30d shift+21d - master + train pipeline"
echo " Master target: $MASTER_PATH"
echo "======================================================================"

"$PWD/commands/create_master_japan_mag80_30d_shift21d.sh"

MASTER="$MASTER_PATH" "$PWD/commands/train_japan_30d_shift21d_fast.sh"
