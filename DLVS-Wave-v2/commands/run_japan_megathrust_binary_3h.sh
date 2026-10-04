#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPOSITORY_DIR="$(cd "${PROJECT_DIR}/.." && pwd)"
PYTHON="${REPOSITORY_DIR}/.venv/bin/python"

MASTER="${PROJECT_DIR}/tests_env/multi_country_century_tests/loc1_japan_tohoku_1900_2030/master_7d_summarized_packed_16bit.csv"
JAPAN_CATALOG="${REPOSITORY_DIR}/DB/japan-m79plus-7d-aug-sep2026-cutoff-jul31-recency-globalneg-v21/01_inputs/usgs_japan_m55_1900_cutoff_20260731T1500Z_fresh.csv"
WORLD_CATALOG="${REPOSITORY_DIR}/DB/japan-m75plus-180d-shift90-operators-quantile4-v17/01_inputs/usgs_world_m75_1900_20260801.csv"
OUTPUT_DIR="${PROJECT_DIR}/studies_output/japan_megathrust_m77_binary_7d_pi_chunks_validation_3m_3h"

TOTAL_SECONDS="${1:-10800}"
CPU_THREADS="${2:-6}"
TRIALS_PER_MODEL="${3:-180}"

export CUDA_VISIBLE_DEVICES=""
export ONEAPI_DEVICE_SELECTOR="opencl:cpu"
export OMP_NUM_THREADS="${CPU_THREADS}"
export MKL_NUM_THREADS="${CPU_THREADS}"
export OPENBLAS_NUM_THREADS="${CPU_THREADS}"
export NUMEXPR_NUM_THREADS="${CPU_THREADS}"
export MPLCONFIGDIR="${PROJECT_DIR}/tmp/matplotlib_binary_megathrust"

"${PYTHON}" "${PROJECT_DIR}/src/run_binary_megathrust_pipeline.py" \
  --input-master "${MASTER}" \
  --japan-catalog "${JAPAN_CATALOG}" \
  --world-catalog "${WORLD_CATALOG}" \
  --output-dir "${OUTPUT_DIR}" \
  --magnitude-threshold 7.7 \
  --cutoff-utc "2026-07-31T23:59:59Z" \
  --forecast-start "2026-08-01" \
  --forecast-end "2027-01-31" \
  --validation-event-count 2 \
  --validation-weeks-before 13 \
  --validation-weeks-after 13 \
  --window-before-min 2 \
  --window-before-max 7 \
  --window-after-min 2 \
  --window-after-max 7 \
  --decision-threshold 0.70 \
  --quality-gate-policy advisory \
  --total-timeout-seconds "${TOTAL_SECONDS}" \
  --n-trials-per-model "${TRIALS_PER_MODEL}" \
  --cpu-threads "${CPU_THREADS}" \
  --device cpu

bash "${SCRIPT_DIR}/continue_japan_megathrust_through_level3.sh" "${CPU_THREADS}"
