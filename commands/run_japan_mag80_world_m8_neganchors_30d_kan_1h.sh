#!/usr/bin/env bash
# 1-hour-ish Japan M8.0+ monthly KAN forecast with worldwide M8+ negative anchors.
#
# This wrapper keeps the full negative-anchor pipeline logic from
# run_japan_mag80_world_m8_neganchors_30d_kan_long.sh but reduces the compute
# budget and uses 2 workers. It writes to a separate folder so it can run
# without colliding with a long run already in progress.
set -euo pipefail

cd "$(dirname "$0")/.."

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/japan-mag80plus-world-m8-neganchors-30d-geocentric-kan-1h}"

export OUT_DIR
export JOBS="${JOBS:-2}"
export SEEDS_SPEC="${SEEDS_SPEC:-4:12}"
export MAX_ITER="${MAX_ITER:-1800}"
export BEST_N="${BEST_N:-24}"
export KEEP_BEST="${KEEP_BEST:-6}"
export KAN_PRESETS_RUN="${KAN_PRESETS_RUN:-tiny,small,wide}"
export KAN_QUIET="${KAN_QUIET:-1}"

echo "======================================================================"
echo " Japan M8.0+ 30d KAN negative anchors - 1h profile"
echo " OUT_DIR:   $OUT_DIR"
echo " JOBS:      $JOBS"
echo " SEEDS:     $SEEDS_SPEC"
echo " MAX_ITER:  $MAX_ITER"
echo " KAN:       $KAN_PRESETS_RUN"
echo " Quiet:     $KAN_QUIET"
echo "======================================================================"

./commands/run_japan_mag80_world_m8_neganchors_30d_kan_long.sh
