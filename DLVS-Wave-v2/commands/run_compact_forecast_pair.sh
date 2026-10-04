#!/usr/bin/env bash
# Start two initialized studies sequentially inside one bounded Linux cgroup.
# Usage: bash commands/run_compact_forecast_pair.sh JAPAN_STUDY WORLD_STUDY [UNIT]
# Initialize Japan with run_causal_japan_energy.py --initialize-only and World
# with forecast_cli.py run --initialize-only before calling this launcher.
set -euo pipefail
if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo 'Usage: run_compact_forecast_pair.sh JAPAN_STUDY WORLD_STUDY [UNIT]' >&2
  exit 2
fi
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
JAPAN_STUDY="$(realpath -- "$1")"
WORLD_STUDY="$(realpath -- "$2")"
UNIT="${3:-dlvs-compact-forecast-pair}"
PYTHON_BIN="${DLVS_PYTHON:-${PROJECT_DIR}/../.venv/bin/python}"
test -f "${JAPAN_STUDY}/configuration.json"
test -f "${WORLD_STUDY}/run_configuration.json"
# No silent fallback to an unbounded background process.
exec systemd-run --user --unit="${UNIT}" \
  --property=MemoryHigh=2500M --property=MemoryMax=3G \
  --property=MemorySwapMax=512M --property=TasksMax=64 \
  --property=OOMPolicy=stop --property=RuntimeMaxSec=32h \
  --property=Nice=10 --property=WorkingDirectory="${PROJECT_DIR}" \
  --setenv=OPENBLAS_NUM_THREADS=1 --setenv=OMP_NUM_THREADS=1 \
  --setenv=MKL_NUM_THREADS=1 --setenv=DLVS_MAX_PARALLEL_WORKERS=1 \
  --setenv=MPLCONFIGDIR=/tmp/dlvs-compact-pair \
  /bin/bash -c '
    set -euo pipefail
    "$1" "$2/source_snapshot/src/run_causal_japan_energy.py" --config "$2/configuration.json" --output "$2" --resume
    "$1" "$3/source_snapshot/src/forecast_cli.py" resume --study "$3"
  ' dlvs-compact-pair "${PYTHON_BIN}" "${JAPAN_STUDY}" "${WORLD_STUDY}"
