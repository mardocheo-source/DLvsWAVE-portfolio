#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${DLVS_PYTHON_BIN:-${PROJECT_ROOT}/../.venv/bin/python}"
OUTPUT_ROOT="${2:-${PROJECT_ROOT}/studies_output/japan_zone_m69plus_7d_aug24_2026_2h}"
TOTAL_TIMEOUT_SECONDS="${1:-7200}"
CATALOG="${PROJECT_ROOT}/../constant_explorer/japan_usgs_m6_1900_20260517.csv"
UNPACKED_MASTER="${PROJECT_ROOT}/tests_env/multi_country_century_tests/loc1_japan_tohoku_1900_2030/master_7d_summarized.csv"
PACKED_MASTER="${PROJECT_ROOT}/tests_env/multi_country_century_tests/loc1_japan_tohoku_1900_2030/master_7d_summarized_packed_16bit.csv"
CLUSTER_DIR="${OUTPUT_ROOT}/01_clusters"
ZONE_MASTER="${OUTPUT_ROOT}/02_master/zone_target_master.csv"

export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/dlvs_zone_matplotlib}"
export CUDA_VISIBLE_DEVICES=""
export ONEAPI_DEVICE_SELECTOR="opencl:cpu"
mkdir -p -- "${MPLCONFIGDIR}" "${OUTPUT_ROOT}"

"${PYTHON_BIN}" "${PROJECT_ROOT}/src/cluster_seismic_zones.py" \
  --event-catalog "${CATALOG}" \
  --recent-master-events "${UNPACKED_MASTER}" \
  --feature-master "${PACKED_MASTER}" \
  --output-dir "${CLUSTER_DIR}" \
  --time-min 1900-01-01 \
  --time-max 2026-07-31 \
  --latitude-min 24 \
  --latitude-max 46.5 \
  --longitude-min 122 \
  --longitude-max 150.5 \
  --magnitude-min 6.9 \
  --minimum-zones 2 \
  --maximum-zones 5 \
  --minimum-zone-events 12 \
  --validation-events 24 \
  --forecast-start 2026-08-03 \
  --forecast-end 2026-10-26

exec "${PYTHON_BIN}" "${PROJECT_ROOT}/src/run_zone_forecast_study.py" \
  --input-master "${ZONE_MASTER}" \
  --cluster-dir "${CLUSTER_DIR}" \
  --output-dir "${OUTPUT_ROOT}" \
  --total-timeout-seconds "${TOTAL_TIMEOUT_SECONDS}" \
  --n-trials-per-study 10000 \
  --recent-validation-weight 3.0 \
  --target-date 2026-08-24 \
  --device cpu

