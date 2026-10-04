#!/usr/bin/env bash
set -euo pipefail
COMMAND_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${COMMAND_DIR}/.." && pwd)"
REPOSITORY_DIR="$(cd -- "${PROJECT_DIR}/.." && pwd)"
PYTHON_BIN="${DLVS_PYTHON:-${REPOSITORY_DIR}/.venv/bin/python}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/dlvs-global-matplotlib}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}"
exec "${PYTHON_BIN}" "${PROJECT_DIR}/src/run_global_recursive_forecast.py" --config "${DLVS_GLOBAL_CONFIG:-${PROJECT_DIR}/configs/world_nested_production.json}" "$@"
