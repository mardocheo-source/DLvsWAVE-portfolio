#!/usr/bin/env bash
# Standalone run/check/resume/status. Usage: bash commands/forecast.sh --help
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_DIR="$(cd -- "${PROJECT_DIR}/.." && pwd)"
PYTHON_BIN="${DLVS_PYTHON:-${REPOSITORY_DIR}/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then PYTHON_BIN="${DLVS_PYTHON:-python3}"; fi
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/dlvs-forecast-matplotlib}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
exec "$PYTHON_BIN" "${PROJECT_DIR}/src/forecast_cli.py" "$@"
