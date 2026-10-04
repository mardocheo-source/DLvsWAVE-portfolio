#!/usr/bin/env bash
# One-shot observer-frame pipeline: create Japan/Nankai 360d topocentric master
# from the center of Japan, then run the LONG training profile on it.
#
# Usage:
#   cd /mnt/git0/git/repository/DLvsWAVE
#   ./commands/run_japan_nankai_360d_observer_japan_long.sh
set -euo pipefail

cd "$(dirname "$0")/.."

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-360d-observer-japan-center}"
MASTER_PATH="${MASTER:-${MASTER_OUT:-$OUT_DIR/master_with_usgs_core_astrofmt.csv}}"
SKIP_MASTER="${SKIP_MASTER:-0}"

DB_FILE="${DB_FILE:-japan_nankai_360d_observer_japan_long.db}"
LOG_FILE="${LOG_FILE:-/tmp/dlvswave_japan_nankai_360d_observer_japan_long.log}"

echo "======================================================================"
echo " Japan/Nankai 360d observer-frame master + LONG train"
echo " Master target:  $MASTER_PATH"
echo " Observer:       ${OBSERVER_ALIAS:-japan_center} lat=${OBSERVER_LAT:-34.5} lon=${OBSERVER_LON:-137.5}"
echo " Output dir:     $OUT_DIR"
echo " SKIP_MASTER:    $SKIP_MASTER"
echo " DB:             $DB_FILE"
echo " Log:            $LOG_FILE"
echo "======================================================================"

if [[ "$SKIP_MASTER" != "1" ]]; then
    OUT_DIR="$OUT_DIR" MASTER_OUT="$MASTER_PATH" "$PWD/commands/create_master_japan_nankai_360d_observer_japan.sh"
else
    echo "[SKIP] Observer master creation skipped."
fi

MASTER="$MASTER_PATH" DB_FILE="$DB_FILE" LOG_FILE="$LOG_FILE" "$PWD/commands/train_japan_nankai_360d_long.sh"
