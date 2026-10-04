#!/usr/bin/env bash
# Japan-zone M7.9+ profile: CPU, 6 workers, MI top-50 shortlist, direct full train.
set -euo pipefail

cd "$(dirname "$0")/.."

RUN_STAMP="${RUN_STAMP:-$(date +%Y%m%d-%H%M%S)}"
DB_ROOT="${DB_ROOT:-/mnt/git0/git/repository/astro-USGS2/DB}"

export RUN_STAMP
export DB_ROOT
export MACRO_ROOT="${MACRO_ROOT:-$DB_ROOT/japan-zone-mag79plus-cpu6-top50-full-$RUN_STAMP}"

export RUN_PROFILE_NAME="${RUN_PROFILE_NAME:-cpu6_top50_full}"
export RUN_COMMAND_HINT="${RUN_COMMAND_HINT:-commands/run_japan_zone_mag79_cpu6_top50_full.sh}"
export RUN_COMMAND_REASON="${RUN_COMMAND_REASON:-Use MI as a fast one-shot broad shortlist, keep the top 50 features so KAN/Deep can still exploit useful feature combinations, then skip metric pretests and run the small-trial workload on CPU with six workers. This is often faster than XPU when each trial is dominated by Python orchestration and small kernels.}"

export KAN_DEVICE="${KAN_DEVICE:-cpu}"
export DEEP_DEVICE="${DEEP_DEVICE:-cpu}"
export JOBS="${JOBS:-6}"
export ACCELERATOR_JOBS="${ACCELERATOR_JOBS:-6}"

export METRIC_TEST="${METRIC_TEST:-0}"
export METRIC_TEST_CPU_COMPARE="${METRIC_TEST_CPU_COMPARE:-0}"
export AUTO_DEVICE_SELECT="${AUTO_DEVICE_SELECT:-0}"

export FEATURE_PRESELECT="${FEATURE_PRESELECT:-1}"
export FEATURE_PRESELECT_REBUILD="${FEATURE_PRESELECT_REBUILD:-1}"
export FEATURE_SELECTION_K_BEST="${FEATURE_SELECTION_K_BEST:-50}"
export FEATURE_SELECTION_THRESHOLD="${FEATURE_SELECTION_THRESHOLD-}"
export FEATURE_SELECTION_PERCENTILE="${FEATURE_SELECTION_PERCENTILE-}"
export FEATURE_SELECTION_MIN_FEATURES="${FEATURE_SELECTION_MIN_FEATURES:-10}"
export FEATURE_SELECTION_MAX_FEATURES="${FEATURE_SELECTION_MAX_FEATURES:-50}"

export RUN_30D="${RUN_30D:-1}"
export RUN_7D="${RUN_7D:-1}"
export RUN_3D="${RUN_3D:-1}"

echo "======================================================================"
echo " Japan-zone M7.9+ CPU6 top-50 full wrapper"
echo " Macro root:       $MACRO_ROOT"
echo " Device:           KAN=$KAN_DEVICE Deep=$DEEP_DEVICE jobs=$JOBS"
echo " Feature policy:   k_best=$FEATURE_SELECTION_K_BEST min/max=$FEATURE_SELECTION_MIN_FEATURES/$FEATURE_SELECTION_MAX_FEATURES"
echo " Metric pretest:   $METRIC_TEST"
echo " Auto device:      $AUTO_DEVICE_SELECT"
echo "======================================================================"

commands/run_japan_zone_mag79_30d_7d_3d_proximity_xpu_24h.sh "$@"
