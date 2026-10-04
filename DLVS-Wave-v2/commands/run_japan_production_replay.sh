#!/usr/bin/env bash
set -euo pipefail
COMMAND_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${COMMAND_DIR}/.." && pwd)"
REPOSITORY_DIR="$(cd -- "${PROJECT_DIR}/.." && pwd)"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/dlvs-japan-replay}"
exec "${DLVS_PYTHON:-${REPOSITORY_DIR}/.venv/bin/python}" "${PROJECT_DIR}/src/run_japan_production_replay.py" --config "${DLVS_JAPAN_CONFIG:-${PROJECT_DIR}/configs/japan_replay_production.json}" "$@"
