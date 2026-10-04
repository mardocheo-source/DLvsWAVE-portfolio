#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_DIR="$(cd -- "${PROJECT_DIR}/.." && pwd)"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/dlvs-causal-energy}"
export PYTHONPATH="${PROJECT_DIR}:${PROJECT_DIR}/src"
exec "${DLVS_PYTHON:-${REPOSITORY_DIR}/.venv/bin/python}" "${PROJECT_DIR}/src/run_causal_japan_energy.py" "$@"
