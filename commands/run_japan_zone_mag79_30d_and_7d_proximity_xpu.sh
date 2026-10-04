#!/usr/bin/env bash
# Sequential launcher for both prepared Japan/proximity XPU counterchecks.
set -euo pipefail

cd "$(dirname "$0")/.."

RUN_30D="${RUN_30D:-1}"
RUN_7D="${RUN_7D:-1}"
PROGRESS_FILTER="${PROGRESS_FILTER:-1}"
DEVICE_MODE="${DEVICE_MODE:-auto}"
CPU_MODE="${CPU_MODE:-0}"
CPU_JOBS="${CPU_JOBS:-6}"
ACCELERATOR_JOBS="${ACCELERATOR_JOBS:-1}"
AUTO_DEVICE_PRIMARY="${AUTO_DEVICE_PRIMARY:-xpu}"
CPU_SPEED_TEST="${CPU_SPEED_TEST:-0}"
METRIC_TEST_CPU_COMPARE="${METRIC_TEST_CPU_COMPARE:-$CPU_SPEED_TEST}"
METRIC_TEST_CPU_JOBS="${METRIC_TEST_CPU_JOBS:-$CPU_JOBS}"
METRIC_TEST_CPU_COMPARE_ONCE="${METRIC_TEST_CPU_COMPARE_ONCE:-1}"
METRIC_TEST_CPU_COMPARE_MARKER="${METRIC_TEST_CPU_COMPARE_MARKER:-/tmp/dlvswave_metric_tests/japan_zone_mag79_cpu_compare_$$.done}"
export METRIC_TEST_CPU_COMPARE METRIC_TEST_CPU_JOBS
export METRIC_TEST_CPU_COMPARE_ONCE METRIC_TEST_CPU_COMPARE_MARKER

MACRO_30D="/mnt/git0/git/repository/astro-USGS2/DB/japan-zone-mag79plus-proximity-check/RUN_GEOGRAPHIC_COUNTERCHECK.sh"
MACRO_7D="/mnt/git0/git/repository/astro-USGS2/DB/japan-zone-mag79plus-7d-aug-sep-proximity-check/RUN_GEOGRAPHIC_COUNTERCHECK.sh"
VARIANTS_PER_PHASE="${VARIANTS_PER_PHASE:-5}"
TRIALS_PER_VARIANT="${TRIALS_PER_VARIANT:-144}"
HISTORY_NEGATIVE_SAMPLING_MODE="${HISTORY_NEGATIVE_SAMPLING_MODE:-none}"
export HISTORY_NEGATIVE_SAMPLING_MODE
NASA_DAILY_MASTER_MODE="${NASA_DAILY_MASTER_MODE:-1}"
NASA_SLOT_ADVANCED_STATS="${NASA_SLOT_ADVANCED_STATS:-1}"
export NASA_DAILY_MASTER_MODE NASA_SLOT_ADVANCED_STATS

if [[ "$CPU_MODE" == "1" || "$CPU_MODE" == "true" || "$CPU_MODE" == "yes" ]]; then
  DEVICE_MODE=cpu
fi

case "$DEVICE_MODE" in
  auto)
    export KAN_DEVICE="$AUTO_DEVICE_PRIMARY"
    export JOBS="$ACCELERATOR_JOBS"
    export METRIC_TEST_CPU_COMPARE=1
    export METRIC_TEST_CPU_COMPARE_ONCE=0
    export AUTO_DEVICE_SELECT=1
    ;;
  cpu)
  export KAN_DEVICE=cpu
  export JOBS="$CPU_JOBS"
    export AUTO_DEVICE_SELECT=0
    ;;
  xpu)
    export KAN_DEVICE=xpu
    export JOBS="$ACCELERATOR_JOBS"
    export AUTO_DEVICE_SELECT=0
    ;;
  cuda|nvidia)
    export KAN_DEVICE=cuda
    export JOBS="$ACCELERATOR_JOBS"
    export AUTO_DEVICE_SELECT=0
    ;;
  *)
    echo "[ERROR] DEVICE_MODE must be auto, cpu, xpu, cuda, or nvidia; got '$DEVICE_MODE'" >&2
    exit 2
    ;;
esac

run_macro_with_progress() {
  local phase_no="$1"
  local phase_name="$2"
  local macro="$3"

  if [[ "$PROGRESS_FILTER" != "1" ]]; then
    "$macro"
    return $?
  fi

  set +e
  stdbuf -oL -eL "$macro" 2>&1 | python3 -u countercheck_progress_filter.py \
    --phase-no "$phase_no" \
    --phase-name "$phase_name" \
    --variants "$VARIANTS_PER_PHASE" \
    --trials-per-variant "$TRIALS_PER_VARIANT"
  local macro_status=${PIPESTATUS[0]}
  set -e
  return "$macro_status"
}

echo "======================================================================"
echo " Japan-zone M7.9+ proximity countercheck batch XPU"
echo " Mode: 30d then 7d, sequential, terminal-visible"
echo " 30d macro: $MACRO_30D"
echo " 7d macro:  $MACRO_7D"
echo " Reduced regional astro profile: enabled in both macros"
echo " Auto JPL observer from zone seismic centroid: enabled in both macros"
echo " Compact budget: 144 main-trial/variant, 720 main-trial/phase"
echo " Device mode: $DEVICE_MODE -> initial device=${KAN_DEVICE:-xpu} jobs=${JOBS:-1}"
echo " CPU speed test: $METRIC_TEST_CPU_COMPARE (CPU jobs=$METRIC_TEST_CPU_JOBS; auto mode enables it)"
echo " CPU speed test once per batch: $METRIC_TEST_CPU_COMPARE_ONCE"
echo " Progress filter: $PROGRESS_FILTER (set PROGRESS_FILTER=0 for raw logs)"
echo "======================================================================"

if [[ "$RUN_30D" == "1" ]]; then
  echo
  echo "======================================================================"
  echo "[1/2] Starting 30d Japan/proximity run"
  echo "======================================================================"
  run_macro_with_progress "1" "30d" "$MACRO_30D"
else
  echo
  echo "======================================================================"
  echo "[1/2] Skipping 30d Japan/proximity run because RUN_30D=$RUN_30D"
  echo "======================================================================"
fi

if [[ "$RUN_7D" == "1" ]]; then
  echo
  echo "======================================================================"
  echo "[2/2] Starting 7d Japan/proximity run"
  echo "======================================================================"
  run_macro_with_progress "2" "7d" "$MACRO_7D"
else
  echo
  echo "======================================================================"
  echo "[2/2] Skipping 7d Japan/proximity run because RUN_7D=$RUN_7D"
  echo "======================================================================"
fi

echo
echo "======================================================================"
echo " Japan-zone M7.9+ 30d + 7d proximity batch complete"
echo " 30d output: /mnt/git0/git/repository/astro-USGS2/DB/japan-zone-mag79plus-proximity-check"
echo " 7d output:  /mnt/git0/git/repository/astro-USGS2/DB/japan-zone-mag79plus-7d-aug-sep-proximity-check"
echo "======================================================================"
