#!/usr/bin/env bash
# Worldwide M8.5+ 30d May-Dec 2026 traditional nasaDb KAN forecast on Intel XPU.
set -euo pipefail

cd "$(dirname "$0")/.."

export METRIC_TEST="${METRIC_TEST:-1}"
for arg in "$@"; do
  case "$arg" in
    --metric-test|-metric-test)
      export METRIC_TEST=1
      ;;
    --no-metric-test)
      export METRIC_TEST=0
      ;;
    *)
      echo "[ERROR] Unknown argument: $arg" >&2
      echo "        Supported: --metric-test, -metric-test, --no-metric-test" >&2
      echo "        Metric pretest runs by default; use --no-metric-test to skip it." >&2
      exit 1
      ;;
  esac
done

export ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
export RUN_LABEL="${RUN_LABEL:-world-mag85plus-30d-may-dec-nasadb-kan-xpu}"
export OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/$RUN_LABEL}"
export PYTHON_BIN="${PYTHON_BIN:-${HOME}/venvs/dlvswave-xpu/bin/python}"

export KAN_DEVICE="${KAN_DEVICE:-xpu}"
export KAN_QUIET="${KAN_QUIET:-1}"
export JOBS="${JOBS:-1}"
export SEEDS_SPEC="${SEEDS_SPEC:-4:96}"
export MAX_ITER="${MAX_ITER:-900}"
export BEST_N="${BEST_N:-48}"
export KEEP_BEST="${KEEP_BEST:-12}"
export KEEP_WORST="${KEEP_WORST:-3}"

export TARGET_EVENT_COUNT="${TARGET_EVENT_COUNT:-2}"
export VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-2}"
export VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-2}"
export VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-2}"
export REBUILD_MASTER="${REBUILD_MASTER:-1}"

export LOG_FILE="${LOG_FILE:-$OUT_DIR/world_mag85plus_30d_may_dec_nasadb_kan_xpu.log}"
export DB_FILE="${DB_FILE:-$OUT_DIR/world_mag85plus_30d_may_dec_nasadb_kan_xpu.db}"

echo "======================================================================"
echo " Worldwide M8.5+ 30d May-Dec traditional nasaDb KAN/XPU"
echo " Output dir: $OUT_DIR"
echo " Python:     $PYTHON_BIN"
echo " KAN:        device=$KAN_DEVICE jobs=$JOBS seeds=$SEEDS_SPEC max_iter=$MAX_ITER"
echo " Validation: 2 events"
echo " Metric test: $METRIC_TEST (default on; use --no-metric-test to skip)"
echo " Rebuild:    $REBUILD_MASTER"
echo "======================================================================"

exec ./commands/run_world_mag85_30d_may_dec_nasadb_kan_base.sh "$@"
