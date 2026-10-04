#!/usr/bin/env bash
# Read-only source study; new report edition required. Extra options: --help.
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/dlvs-report-edition}"
exec "${DLVS_PYTHON:-${PROJECT_DIR}/../.venv/bin/python}" "${PROJECT_DIR}/src/reissue_forecast_report.py" "$@"
