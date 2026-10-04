#!/usr/bin/env bash
# ==============================================================================
# DLVS-Wave v2.0: Uncompressed Pipeline Runner (L1 + Fusion + L2 Meta-Optimizer)
# ==============================================================================
set -euo pipefail

STUDY_NAME="${1:-AUTORUN_japan_megathrust_m77_aug2026_jan2027_production}"
L1_TRIALS="${2:-600}"
L2_TRIALS="${3:-600}"
FUSION_MODE="${4:-auto}"
TOTAL_TIMEOUT_SECONDS="${5:-7200}"
CPU_THREADS="${6:-6}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

echo "================================================================================"
echo "Starting DLVS-Wave v2.0 Uncompressed Pipeline"
echo "Study Name:  ${STUDY_NAME}"
echo "L1 Trials:   ${L1_TRIALS} per model (KAN, Deep Learning, LCS)"
echo "L2 Trials:   ${L2_TRIALS} in Deep Meta-Optimizer"
echo "Fusion Mode: ${FUSION_MODE}"
echo "================================================================================"

.venv/bin/python DLVS-Wave-v2/src/run_uncompressed_l1_l2_pipeline.py \
    --study-name "${STUDY_NAME}" \
    --l1-trials-per-model "${L1_TRIALS}" \
    --l2-trials "${L2_TRIALS}" \
    --fusion-selection "${FUSION_MODE}" \
    --total-timeout-seconds "${TOTAL_TIMEOUT_SECONDS}" \
    --cpu-threads "${CPU_THREADS}" \
    --resume

echo "================================================================================"
echo "Pipeline finished successfully. Output in: DLVS-Wave-v2/studies_output/${STUDY_NAME}"
echo "================================================================================"
