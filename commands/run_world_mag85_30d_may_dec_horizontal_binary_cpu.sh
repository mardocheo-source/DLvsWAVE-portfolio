#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export RUN_LABEL="${RUN_LABEL:-world-mag85plus-30d-may-dec-horizontal-binary-kan-cpu}"
export OUT_DIR="${OUT_DIR:-/mnt/git0/git/repository/astro-USGS2/DB/$RUN_LABEL}"
export PYTHON_BIN="${PYTHON_BIN:-$PWD/.venv/bin/python}"
export KAN_DEVICE="${KAN_DEVICE:-cpu}"
export KAN_QUIET="${KAN_QUIET:-0}"
export JOBS="${JOBS:-3}"

CLI_BINARY_TARGET_COL=""
CLI_TARGET_COL=""
CLI_BINARY_SOURCE_COL=""
CLI_BINARY_THRESHOLD=""
CLI_BINARY_OPERATOR=""
CLI_ROW_FILTER=""
CLI_FORECAST_FILTER=""
CLI_ZONES_CSV=""
CLI_TARGET_REGION=""
CLI_TARGET_ZONES=""
CLI_OUT_OF_REGION_MODE=""
ARGS_COPY=("$@")
idx=0
while [[ $idx -lt ${#ARGS_COPY[@]} ]]; do
  case "${ARGS_COPY[$idx]}" in
    --binary-target-col)
      if [[ $((idx + 1)) -lt ${#ARGS_COPY[@]} ]]; then
        CLI_BINARY_TARGET_COL="${ARGS_COPY[$((idx + 1))]}"
      fi
      idx=$((idx + 2))
      ;;
    --target-col)
      if [[ $((idx + 1)) -lt ${#ARGS_COPY[@]} ]]; then
        CLI_TARGET_COL="${ARGS_COPY[$((idx + 1))]}"
      fi
      idx=$((idx + 2))
      ;;
    --binary-source-col)
      if [[ $((idx + 1)) -lt ${#ARGS_COPY[@]} ]]; then
        CLI_BINARY_SOURCE_COL="${ARGS_COPY[$((idx + 1))]}"
      fi
      idx=$((idx + 2))
      ;;
    --binary-threshold)
      if [[ $((idx + 1)) -lt ${#ARGS_COPY[@]} ]]; then
        CLI_BINARY_THRESHOLD="${ARGS_COPY[$((idx + 1))]}"
      fi
      idx=$((idx + 2))
      ;;
    --binary-operator)
      if [[ $((idx + 1)) -lt ${#ARGS_COPY[@]} ]]; then
        CLI_BINARY_OPERATOR="${ARGS_COPY[$((idx + 1))]}"
      fi
      idx=$((idx + 2))
      ;;
    --row-filter)
      if [[ $((idx + 1)) -lt ${#ARGS_COPY[@]} ]]; then
        CLI_ROW_FILTER="${ARGS_COPY[$((idx + 1))]}"
      fi
      idx=$((idx + 2))
      ;;
    --forecast-filter)
      if [[ $((idx + 1)) -lt ${#ARGS_COPY[@]} ]]; then
        CLI_FORECAST_FILTER="${ARGS_COPY[$((idx + 1))]}"
      fi
      idx=$((idx + 2))
      ;;
    --zones-csv)
      if [[ $((idx + 1)) -lt ${#ARGS_COPY[@]} ]]; then
        CLI_ZONES_CSV="${ARGS_COPY[$((idx + 1))]}"
      fi
      idx=$((idx + 2))
      ;;
    --target-region)
      if [[ $((idx + 1)) -lt ${#ARGS_COPY[@]} ]]; then
        CLI_TARGET_REGION="${ARGS_COPY[$((idx + 1))]}"
      fi
      idx=$((idx + 2))
      ;;
    --target-zones)
      if [[ $((idx + 1)) -lt ${#ARGS_COPY[@]} ]]; then
        CLI_TARGET_ZONES="${ARGS_COPY[$((idx + 1))]}"
      fi
      idx=$((idx + 2))
      ;;
    --out-of-region-mode)
      if [[ $((idx + 1)) -lt ${#ARGS_COPY[@]} ]]; then
        CLI_OUT_OF_REGION_MODE="${ARGS_COPY[$((idx + 1))]}"
      fi
      idx=$((idx + 2))
      ;;
    *)
      idx=$((idx + 1))
      ;;
  esac
done

export ENABLE_BINARY_TARGET=1
export ENABLE_HORIZONTAL_HISTORY="${ENABLE_HORIZONTAL_HISTORY:-1}"
export BINARY_TARGET_COL="${CLI_BINARY_TARGET_COL:-${BINARY_TARGET_COL:-target}}"
export TARGET_COL="${CLI_TARGET_COL:-${TARGET_COL:-$BINARY_TARGET_COL}}"
export BINARY_SOURCE_COL="${CLI_BINARY_SOURCE_COL:-${BINARY_SOURCE_COL:-mag}}"
export BINARY_THRESHOLD="${CLI_BINARY_THRESHOLD:-${BINARY_THRESHOLD:-}}"
export BINARY_OPERATOR="${CLI_BINARY_OPERATOR:-${BINARY_OPERATOR:->=}}"
export ROW_FILTER="${CLI_ROW_FILTER:-${ROW_FILTER:-auto}}"
export FORECAST_FILTER="${CLI_FORECAST_FILTER:-${FORECAST_FILTER:-none}}"
export ZONES_CSV="${CLI_ZONES_CSV:-${ZONES_CSV:-$PWD/resources/seismic_zones.csv}}"
export TARGET_REGION="${CLI_TARGET_REGION:-${TARGET_REGION:-}}"
export TARGET_ZONES="${CLI_TARGET_ZONES:-${TARGET_ZONES:-}}"
export OUT_OF_REGION_MODE="${CLI_OUT_OF_REGION_MODE:-${OUT_OF_REGION_MODE:-keep}}"
if [[ -n "$CLI_TARGET_COL" && -z "$CLI_BINARY_SOURCE_COL" && "$CLI_TARGET_COL" != "$BINARY_TARGET_COL" ]]; then
  case "$CLI_TARGET_COL" in
    mag|latitude|longitude|depth)
      export BINARY_SOURCE_COL="$CLI_TARGET_COL"
      export TARGET_COL="$BINARY_TARGET_COL"
      ;;
  esac
fi
export SKIP_COLS_LIST="${SKIP_COLS_LIST:-date,mag,depth,latitude,longitude}"
export METRIC_TARGET_THRESHOLD="${METRIC_TARGET_THRESHOLD:-0.5}"
export METRIC_PREDICTION_THRESHOLD="${METRIC_PREDICTION_THRESHOLD:-0.5}"
export TARGET_WINDOW_THRESHOLD="${TARGET_WINDOW_THRESHOLD:-0.5}"

export HISTORY_MODE="${HISTORY_MODE:-fibonacci-gold}"
export HISTORY_VALUE="${HISTORY_VALUE:-1280}"
export HISTORY_SPACER_DAYS="${HISTORY_SPACER_DAYS:-0}"
export HISTORY_ENABLE_SEISMIC="${HISTORY_ENABLE_SEISMIC:-1}"
export HISTORY_ENABLE_ASTRO="${HISTORY_ENABLE_ASTRO:-1}"
export HISTORY_ASTRO_BODIES="${HISTORY_ASTRO_BODIES:-301,599,99942}"
export HISTORY_ASTRO_FIELDS="${HISTORY_ASTRO_FIELDS:-RA,DEC,r,r_rate,ObsEclLon,ObsEclLat}"
export HISTORY_NEGATIVE_SAMPLING_MODE="${HISTORY_NEGATIVE_SAMPLING_MODE:-random-sparse}"
export HISTORY_RANDOM_NEGATIVES_PER_POSITIVE="${HISTORY_RANDOM_NEGATIVES_PER_POSITIVE:-8}"
export HISTORY_RANDOM_NEGATIVE_SEED="${HISTORY_RANDOM_NEGATIVE_SEED:-20260608}"
export HISTORY_KEEP_NEIGHBOR_RECORDS="${HISTORY_KEEP_NEIGHBOR_RECORDS:-2}"
export HISTORY_KEEP_RECENT_NEGATIVES="${HISTORY_KEEP_RECENT_NEGATIVES:-6}"

export SEEDS_SPEC="${SEEDS_SPEC:-4:24}"
export MAX_ITER="${MAX_ITER:-1200}"
export BEST_N="${BEST_N:-36}"
export KEEP_BEST="${KEEP_BEST:-8}"
export KEEP_WORST="${KEEP_WORST:-3}"
export METRIC_TEST="${METRIC_TEST:-1}"
export REBUILD_MASTER="${REBUILD_MASTER:-1}"
export FUSION_TITLE="${FUSION_TITLE:-Worldwide M8.5+ May-Dec 2026 30d horizontal binary CPU KAN forecast}"

echo "======================================================================"
echo " Worldwide M8.5+ 30d horizontal-history binary KAN CPU"
echo " Output dir:      $OUT_DIR"
echo " Target:          $TARGET_COL"
echo " Binary source:   $BINARY_SOURCE_COL $BINARY_OPERATOR ${BINARY_THRESHOLD:-auto} -> $BINARY_TARGET_COL"
echo " Row filter:      $ROW_FILTER"
echo " Forecast filter: $FORECAST_FILTER"
echo " Target region:   ${TARGET_REGION:-none}"
echo " Target zones:    ${TARGET_ZONES:-none}"
echo " Out region mode: $OUT_OF_REGION_MODE"
echo " History:         mode=$HISTORY_MODE value=$HISTORY_VALUE seismic=$HISTORY_ENABLE_SEISMIC astro=$HISTORY_ENABLE_ASTRO"
echo " Astro bodies:    $HISTORY_ASTRO_BODIES"
echo " Sparse negatives: $HISTORY_NEGATIVE_SAMPLING_MODE per_pos=$HISTORY_RANDOM_NEGATIVES_PER_POSITIVE"
echo " KAN:             device=$KAN_DEVICE seeds=$SEEDS_SPEC max_iter=$MAX_ITER jobs=$JOBS"
echo "======================================================================"

exec ./commands/run_world_mag85_30d_may_dec_nasadb_kan_base.sh "$@"
