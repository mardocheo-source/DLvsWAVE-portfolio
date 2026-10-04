#!/usr/bin/env bash
# ==============================================================================
# DLVS-Wave v2.0: Optuna Multi-Microstudy Orchestrator Runner
#
# Target: Japan Region (M >= 6.9+ Energetic Magnitude Forecast)
# Dataset: 7-Day Compacted Master (1900-01-01 to 2030-12-30, 400 astro containers)
# Validation Scope: Last 3 Major Earthquakes (2025-12 M7.6, 2026-04 M7.4, 2026-06 M6.9)
# Microstudies: KAN (Splines) + Deep Learning (Tabular ResNet) + LCS (Evolutionary Rules)
# Constraints: 2.0 Hours Global Budget (40 mins per microstudy) | CPU Mode
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_PYTHON="${REPO_ROOT}/.venv/bin/python3"

MASTER_CSV="${REPO_ROOT}/DLVS-Wave-v2/tests_env/multi_country_century_tests/loc1_japan_tohoku_1900_2030/master_7d_summarized_packed_16bit.csv"
OUTPUT_DIR="${REPO_ROOT}/DLVS-Wave-v2/studies_output/optuna_study_japan_7d_m69_2h"

TOTAL_TIMEOUT_SECONDS="${1:-7200}"  # 2.0 hours default
DEVICE="${2:-cpu}"                  # cpu default, or xpu / cuda
N_TRIALS_PER_STUDY="${3:-120}"

echo "=============================================================================="
echo "LAUNCHING DLVS-WAVE V2.0 OPTUNA MULTI-MICROSTUDY ORCHESTRATOR"
echo "=============================================================================="
echo "  Master CSV:       ${MASTER_CSV}"
echo "  Target Field:     seis_core_magnitude"
echo "  Magnitude Thresh: M >= 6.9+"
echo "  Validation Scope: Last 3 Events"
echo "  Total Budget:     ${TOTAL_TIMEOUT_SECONDS}s ($((TOTAL_TIMEOUT_SECONDS / 3600))h)"
echo "  Compute Device:   ${DEVICE}"
echo "  Output Directory: ${OUTPUT_DIR}"
echo "=============================================================================="

"${VENV_PYTHON}" "${REPO_ROOT}/DLVS-Wave-v2/src/orchestrator.py" \
    --input-master "${MASTER_CSV}" \
    --target-col "seis_core_magnitude" \
    --min-mag-threshold 6.9 \
    --eval-events 3 \
    --total-timeout-seconds "${TOTAL_TIMEOUT_SECONDS}" \
    --output-dir "${OUTPUT_DIR}" \
    --device "${DEVICE}" \
    --n-trials-per-study "${N_TRIALS_PER_STUDY}" \
    --roi-name "Japan Area (7D Compacted Astro)" \
    --forecast-steps 150

echo "=============================================================================="
echo "ORCHESTRATION FINISHED SUCCESSFULLY -> Results saved in: ${OUTPUT_DIR}"
echo "=============================================================================="
