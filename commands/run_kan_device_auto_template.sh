#!/usr/bin/env bash
# Generic KAN device-autoselect launcher template.
#
# Copy this pattern for new pipelines:
#   DEVICE_MODE=auto  -> benchmark accelerator vs CPU, then train with winner.
#   DEVICE_MODE=cpu   -> force CPU.
#   DEVICE_MODE=xpu   -> force Intel XPU.
#   DEVICE_MODE=cuda  -> force NVIDIA CUDA.
set -euo pipefail

cd "$(dirname "$0")/.."

: "${PIPELINE_MACRO:?Set PIPELINE_MACRO=/path/to/RUN_GEOGRAPHIC_COUNTERCHECK.sh}"

DEVICE_MODE="${DEVICE_MODE:-auto}"
CPU_JOBS="${CPU_JOBS:-6}"
ACCELERATOR_JOBS="${ACCELERATOR_JOBS:-1}"
AUTO_DEVICE_PRIMARY="${AUTO_DEVICE_PRIMARY:-xpu}"
PROGRESS_FILTER="${PROGRESS_FILTER:-1}"
VARIANTS_PER_PHASE="${VARIANTS_PER_PHASE:-5}"
TRIALS_PER_VARIANT="${TRIALS_PER_VARIANT:-144}"

case "$DEVICE_MODE" in
  auto)
    export KAN_DEVICE="$AUTO_DEVICE_PRIMARY"
    export JOBS="$ACCELERATOR_JOBS"
    export METRIC_TEST_CPU_COMPARE=1
    export METRIC_TEST_CPU_COMPARE_ONCE=0
    export METRIC_TEST_CPU_JOBS="$CPU_JOBS"
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

echo "======================================================================"
echo " KAN device-autoselect template runner"
echo " Macro:             $PIPELINE_MACRO"
echo " Device mode:       $DEVICE_MODE"
echo " Initial KAN:       device=$KAN_DEVICE jobs=$JOBS"
echo " CPU compare jobs:  $CPU_JOBS"
echo " Progress filter:   $PROGRESS_FILTER"
echo "======================================================================"

if [[ "$PROGRESS_FILTER" == "1" ]]; then
  stdbuf -oL -eL "$PIPELINE_MACRO" 2>&1 | python3 -u countercheck_progress_filter.py \
    --phase-no 1 \
    --phase-name run \
    --variants "$VARIANTS_PER_PHASE" \
    --trials-per-variant "$TRIALS_PER_VARIANT"
else
  "$PIPELINE_MACRO"
fi
