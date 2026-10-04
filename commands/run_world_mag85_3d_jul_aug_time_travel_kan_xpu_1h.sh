#!/usr/bin/env bash
# Worldwide M8.5+ July-August 2026, 3-day precision, KAN/XPU ribbon run.
set -euo pipefail

cd "$(dirname "$0")/.."

export ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
export RUN_LABEL="${RUN_LABEL:-world-mag85plus-3d-jul-aug-time-travel-ribbon-kan-xpu-1h}"
export OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/$RUN_LABEL}"
export PYTHON_BIN="${PYTHON_BIN:-${HOME}/venvs/dlvswave-xpu/bin/python}"

export STEP_DAYS=3
export START_DATE="${START_DATE:-1908-09-03}"
export EVENTS_END_DATE="${EVENTS_END_DATE:-2026-06-30}"
export END_DATE="${END_DATE:-2026-08-31}"
export FORECAST_START="${FORECAST_START:-2026-07-01}"
export FORECAST_END="${FORECAST_END:-2026-08-31}"

export TIME_TRAVEL_MODE="${TIME_TRAVEL_MODE:-fibonacci-gold}"
export TIME_TRAVEL_VALUE="${TIME_TRAVEL_VALUE:-1280}"
export REUSE_EXISTING_MASTER="${REUSE_EXISTING_MASTER:-0}"

export KAN_DEVICE="${KAN_DEVICE:-xpu}"
export KAN_QUIET="${KAN_QUIET:-1}"
export JOBS="${JOBS:-1}"
export KAN_PRESETS_RUN="${KAN_PRESETS_RUN:-tiny,small,wide}"
export SEEDS_SPEC="${SEEDS_SPEC:-4:72}"
export MAX_ITER="${MAX_ITER:-850}"
export BEST_N="${BEST_N:-48}"
export KEEP_BEST="${KEEP_BEST:-12}"

export TARGET_EVENT_COUNT="${TARGET_EVENT_COUNT:-3}"
export VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-3}"
export VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-6}"
export VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-6}"

export LOG_FILE="${LOG_FILE:-$OUT_DIR/world_mag85plus_3d_jul_aug_time_travel_kan_xpu_1h.log}"
export DB_FILE="${DB_FILE:-$OUT_DIR/world_mag85plus_3d_jul_aug_time_travel_kan_xpu_1h.db}"

echo "======================================================================"
echo " Worldwide M8.5+ 3d Jul-Aug 2026 Time-Travel Ribbon KAN/XPU"
echo " Output dir:  $OUT_DIR"
echo " Forecast:    $FORECAST_START -> $FORECAST_END"
echo " Master:      $START_DATE -> $END_DATE"
echo " Ribbon:      $TIME_TRAVEL_MODE value=$TIME_TRAVEL_VALUE"
echo " KAN budget:  seeds=$SEEDS_SPEC max_iter=$MAX_ITER jobs=$JOBS device=$KAN_DEVICE"
echo " Target time: about 1h on current Intel Arc/XPU setup"
echo "======================================================================"

exec ./commands/run_world_mag85_jul_aug_time_travel_kan_xpu_base.sh
