#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPOSITORY_DIR="$(cd "${PROJECT_DIR}/.." && pwd)"
PYTHON="${REPOSITORY_DIR}/.venv/bin/python"
RUN_DIR="${PROJECT_DIR}/studies_output/japan_megathrust_m77_binary_7d_pi_chunks_validation_3m_3h"

CPU_THREADS="${1:-6}"
export CUDA_VISIBLE_DEVICES=""
export ONEAPI_DEVICE_SELECTOR="opencl:cpu"
export OMP_NUM_THREADS="${CPU_THREADS}"
export MKL_NUM_THREADS="${CPU_THREADS}"
export OPENBLAS_NUM_THREADS="${CPU_THREADS}"
export NUMEXPR_NUM_THREADS="${CPU_THREADS}"
export MPLCONFIGDIR="${PROJECT_DIR}/tmp/matplotlib_binary_megathrust"

until test -f "${RUN_DIR}/run_manifest.json" \
  && test -f "${RUN_DIR}/03_level2/study_kan/meta_best_params_kan.json" \
  && test -f "${RUN_DIR}/03_level2/study_deep_learning/meta_best_params_deep_learning.json" \
  && test -f "${RUN_DIR}/03_level2/study_lcs/meta_best_params_lcs.json"; do
  sleep 20
done

"${PYTHON}" -m src.binary_megathrust_timestamp_audit \
  --run-dir "${RUN_DIR}" 2>&1 | tee "${RUN_DIR}/05_report/timestamp_assignment_audit.log"

"${PYTHON}" -m src.binary_megathrust_peak_specialists \
  --run-dir "${RUN_DIR}" 2>&1 | tee "${RUN_DIR}/05_report/peak_timing_specialists.log"

if ! test -f "${RUN_DIR}/06_level3_episodic_hazard/level3_manifest.json"; then
  "${PYTHON}" -m src.run_echn_level3 \
    --run-dir "${RUN_DIR}" \
    --cutoff-date "2026-07-31" \
    --forecast-start "2026-08-01" \
    --forecast-end "2027-01-31" \
    --sequence-radius 7 \
    --feature-count 96 \
    --hidden-dim 48 \
    --batch-size 96 \
    --epochs 12 \
    --pretrain-epochs 4 \
    --full-cycles 2 \
    --decision-threshold 0.70 \
    --quiet-ratio 4.0 \
    --seeds 2 \
    --cpu-threads "${CPU_THREADS}" \
    --device cpu 2>&1 | tee "${RUN_DIR}/06_level3_episodic_hazard.log"
fi

"${PYTHON}" -m src.binary_megathrust_quality_audit \
  --run-dir "${RUN_DIR}" \
  --decision-threshold 0.70 2>&1 | tee "${RUN_DIR}/05_report/quality_audit.log"
