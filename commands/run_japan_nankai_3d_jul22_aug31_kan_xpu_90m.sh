#!/usr/bin/env bash
# Night run: Japan/Nankai 3d KAN forecast through end of August on Intel XPU.
#
# Budget target: about 1.5h on the verified Intel Arc/XPU setup.
# Important: keep JOBS=1 on XPU; parallel jobs compete for the same GPU.
set -euo pipefail

cd "$(dirname "$0")/.."

export ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
export OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-3d-jul22-aug31-kan-xpu-90m}"
export PYTHON_BIN="${PYTHON_BIN:-${HOME}/venvs/dlvswave-xpu/bin/python}"

export MIN_HISTORICAL_DATE="${MIN_HISTORICAL_DATE:-1903-01-01}"
export FORECAST_START="${FORECAST_START:-2026-07-22}"
export FORECAST_END="${FORECAST_END:-2026-08-31}"
export REBUILD_MASTER="${REBUILD_MASTER:-1}"
export CLEAN_BODIES_ON_REBUILD="${CLEAN_BODIES_ON_REBUILD:-1}"

export KAN_DEVICE="${KAN_DEVICE:-xpu}"
export KAN_QUIET="${KAN_QUIET:-1}"
export JOBS="${JOBS:-1}"
export SEEDS_SPEC="${SEEDS_SPEC:-4:120}"
export MAX_ITER="${MAX_ITER:-900}"
export BEST_N="${BEST_N:-48}"
export KEEP_BEST="${KEEP_BEST:-12}"

export TARGET_EVENT_COUNT="${TARGET_EVENT_COUNT:-2}"
export VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-2}"
export TARGET_PRE_RECORDS="${TARGET_PRE_RECORDS:-6}"
export TARGET_POST_RECORDS="${TARGET_POST_RECORDS:-6}"
export VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-6}"
export VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-6}"

export LOG_FILE="${LOG_FILE:-$OUT_DIR/kan_3d_jul22_aug31_xpu_90m.log}"
export DB_FILE="${DB_FILE:-$OUT_DIR/japan_nankai_3d_jul22_aug31_kan_xpu_90m.db}"

echo "======================================================================"
echo " Japan/Nankai 3d Jul22-Aug31 KAN XPU night run"
echo " Output dir:      $OUT_DIR"
echo " Forecast:        $FORECAST_START -> $FORECAST_END"
echo " Historical clip: >= $MIN_HISTORICAL_DATE"
echo " Rebuild master:  $REBUILD_MASTER"
echo " Python:          $PYTHON_BIN"
echo " KAN:             device=$KAN_DEVICE quiet=$KAN_QUIET jobs=$JOBS"
echo " Trials:          presets=tiny,small,wide seeds=$SEEDS_SPEC max_iter=$MAX_ITER"
echo " Expected budget: about 1.5h on Intel Arc/XPU"
echo "======================================================================"

exec ./commands/run_japan_nankai_3d_jul22_aug12_kan_micro4h.sh
