#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_DIR="$(cd -- "${PROJECT_DIR}/.." && pwd)"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/dlvs-publication-mpl}"
exec "${DLVS_PYTHON:-${REPOSITORY_DIR}/.venv/bin/python}" "${PROJECT_DIR}/src/refresh_publication.py" "$@"
