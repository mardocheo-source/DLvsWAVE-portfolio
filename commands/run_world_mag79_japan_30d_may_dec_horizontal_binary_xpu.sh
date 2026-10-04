#!/usr/bin/env bash
# Japan/Asia regional target, worldwide M7.9+ May-Dec 2026, 30d nasaDb horizontal-history KAN/XPU.
set -euo pipefail

cd "$(dirname "$0")/.."

export RUN_LABEL="${RUN_LABEL:-japan-zone-mag79plus-30d-may-dec-horizontal-binary-kan-xpu}"
export OUT_DIR="${OUT_DIR:-/mnt/git0/git/repository/astro-USGS2/DB/$RUN_LABEL}"
export PYTHON_BIN="${PYTHON_BIN:-${HOME}/venvs/dlvswave-xpu/bin/python}"
export KAN_DEVICE="${KAN_DEVICE:-xpu}"
export KAN_QUIET="${KAN_QUIET:-1}"
export JOBS="${JOBS:-1}"

export STEP_INTERVAL="${STEP_INTERVAL:-30d}"
export FORECAST_START="${FORECAST_START:-2026-04-30}"
export FORECAST_END="${FORECAST_END:-2026-12-31}"
export EVENTS_END_DATE="${EVENTS_END_DATE:-2026-04-29}"
export FORECAST_LABEL="${FORECAST_LABEL:-May-Dec 2026, 30d regional Japan/Asia reduced astro}"
export REBUILD_MASTER="${REBUILD_MASTER:-1}"

export NASA_AUTO_OBSERVER_FROM_TARGET="${NASA_AUTO_OBSERVER_FROM_TARGET:-1}"
export NASA_OBSERVER_ALIAS="${NASA_OBSERVER_ALIAS:-target_centroid}"
export NASA_PLACE="${NASA_PLACE:-japan}"
export EPHEMERIDES_FIELDS="${EPHEMERIDES_FIELDS:-3,4,20,27}"
export BODY_PRIMARY_LEVELS="${BODY_PRIMARY_LEVELS:-1.0 2.11 2.12 2.21 2.14 2.22 2.32}"
export BODY_SECONDARY_LEVELS="${BODY_SECONDARY_LEVELS:-5.22 4.1 4.32 6.11 6.22}"

export MIN_MAG="${MIN_MAG:-7.9}"
export ENABLE_BINARY_TARGET=1
export ENABLE_HORIZONTAL_HISTORY="${ENABLE_HORIZONTAL_HISTORY:-1}"
export BINARY_TARGET_COL="${BINARY_TARGET_COL:-target}"
export TARGET_COL="${TARGET_COL:-$BINARY_TARGET_COL}"
export BINARY_SOURCE_COL="${BINARY_SOURCE_COL:-mag}"
export BINARY_THRESHOLD="${BINARY_THRESHOLD:-7.9}"
export BINARY_OPERATOR="${BINARY_OPERATOR:->=}"
# Magnitude detection needs the zero/negative context rows. The catalog is
# already filtered by MIN_MAG; row-filter must not drop near-event or sparse
# non-event records before the binary target is learned.
export ROW_FILTER="${ROW_FILTER:-none}"
export OUT_OF_REGION_MODE="${OUT_OF_REGION_MODE:-neutralize-seismic}"
export SKIP_COLS_LIST="${SKIP_COLS_LIST:-date,mag,depth,latitude,longitude}"
export METRIC_TARGET_THRESHOLD="${METRIC_TARGET_THRESHOLD:-0.5}"
export METRIC_PREDICTION_THRESHOLD="${METRIC_PREDICTION_THRESHOLD:-0.5}"
export TARGET_WINDOW_THRESHOLD="${TARGET_WINDOW_THRESHOLD:-0.5}"

export HISTORY_MODE="${HISTORY_MODE:-fibonacci-gold}"
export HISTORY_VALUE="${HISTORY_VALUE:-1280}"
export HISTORY_ENABLE_SEISMIC="${HISTORY_ENABLE_SEISMIC:-1}"
export HISTORY_ENABLE_ASTRO="${HISTORY_ENABLE_ASTRO:-1}"
export HISTORY_ASTRO_BODIES="${HISTORY_ASTRO_BODIES:-301,599,101955}"
export HISTORY_ASTRO_FIELDS="${HISTORY_ASTRO_FIELDS:-RA_rate,DEC_rate,AZ,EL,delta,delta_rate,sunTargetPA,velocityPA}"
export HISTORY_NEGATIVE_SAMPLING_MODE="${HISTORY_NEGATIVE_SAMPLING_MODE:-random-sparse}"
export HISTORY_RANDOM_NEGATIVES_PER_POSITIVE="${HISTORY_RANDOM_NEGATIVES_PER_POSITIVE:-8}"
export HISTORY_KEEP_NEIGHBOR_RECORDS="${HISTORY_KEEP_NEIGHBOR_RECORDS:-2}"
export HISTORY_KEEP_RECENT_NEGATIVES="${HISTORY_KEEP_RECENT_NEGATIVES:-6}"

export SEEDS_SPEC="${SEEDS_SPEC:-4:48}"
export MAX_ITER="${MAX_ITER:-600}"
export BEST_N="${BEST_N:-36}"
export KEEP_BEST="${KEEP_BEST:-10}"
export KEEP_WORST="${KEEP_WORST:-3}"
export TARGET_EVENT_COUNT="${TARGET_EVENT_COUNT:-3}"
export VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-3}"
export VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-2}"
export VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-2}"
export FUSION_TITLE="${FUSION_TITLE:-Japan-zone M7.9+ May-Dec 2026 30d reduced-astro proximity KAN/XPU forecast}"

echo "======================================================================"
echo " Japan-zone M7.9+ 30d May-Dec reduced-astro horizontal-history KAN XPU"
echo " Output dir:      $OUT_DIR"
echo " Forecast grid:   $FORECAST_START -> $FORECAST_END"
echo " Step interval:   $STEP_INTERVAL"
echo " Rebuild master:  $REBUILD_MASTER"
echo " NASA observer:   auto_from_target=$NASA_AUTO_OBSERVER_FROM_TARGET alias=$NASA_OBSERVER_ALIAS"
echo " NASA profile:    place=$NASA_PLACE fields=$EPHEMERIDES_FIELDS"
echo " Bodies reduced:  primary='$BODY_PRIMARY_LEVELS' secondary='$BODY_SECONDARY_LEVELS'"
echo " History bodies:  $HISTORY_ASTRO_BODIES"
echo " KAN:             device=$KAN_DEVICE seeds=$SEEDS_SPEC max_iter=$MAX_ITER jobs=$JOBS"
echo "======================================================================"

exec ./commands/run_world_mag85_30d_may_dec_horizontal_binary_xpu.sh "$@"
