#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/DB/hokkaido-sanriku-south-kurils-m79plus-7d-v25-deep-history-eclipse"
INPUT_DIR="${PROJECT_DIR}/01_inputs"
CONFIG_DIR="${PROJECT_DIR}/00_config"
AUDIT_DIR="${PROJECT_DIR}/02_audit"
RESULTS_DIR="${PROJECT_DIR}/05_results"
WORLD_CSV="${ROOT_DIR}/DB/japan-m79plus-7d-aug-sep2026-cutoff-jul31-recency-globalneg-v21/01_inputs/usgs_world_m79_1900_cutoff_20260731T1500Z_fresh.csv"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
JPL_BUILDER="${ROOT_DIR}/DB/OK-japan-m79plus-7d-jul17-aug2026-fresh-weekly-peak-v12/pipeline/build_jpl_observer_master.py"

mkdir -p "${INPUT_DIR}" "${CONFIG_DIR}" "${AUDIT_DIR}" "${RESULTS_DIR}"

curl -fsSLG "https://earthquake.usgs.gov/fdsnws/event/1/query" \
  --data-urlencode "format=csv" \
  --data-urlencode "starttime=1900-01-01T00:00:00Z" \
  --data-urlencode "endtime=2026-07-31T15:00:00Z" \
  --data-urlencode "minmagnitude=5.5" \
  --data-urlencode "minlatitude=38.8" \
  --data-urlencode "maxlatitude=46.0" \
  --data-urlencode "minlongitude=140.0" \
  --data-urlencode "maxlongitude=150.5" \
  --output "${INPUT_DIR}/usgs_corridor_m55_1900_cutoff_20260731T1500Z.csv"

curl -fsSLG "https://earthquake.usgs.gov/fdsnws/event/1/query" \
  --data-urlencode "format=csv" \
  --data-urlencode "starttime=1900-01-01T00:00:00Z" \
  --data-urlencode "endtime=2026-07-31T15:00:00Z" \
  --data-urlencode "minmagnitude=7.9" \
  --data-urlencode "orderby=time-asc" \
  --output "${WORLD_CSV}"

"${PYTHON_BIN}" "${ROOT_DIR}/research_pipeline/scientific/v25_prepare_historical_corridor.py" \
  --regional-usgs "${INPUT_DIR}/usgs_corridor_m55_1900_cutoff_20260731T1500Z.csv" \
  --world-usgs "${WORLD_CSV}" \
  --historical-csv "${INPUT_DIR}/historical_corridor_m79.csv" \
  --output-target-catalog "${INPUT_DIR}/corridor_targets_m79_deep_history.csv" \
  --output-periods "${CONFIG_DIR}/period_starts.csv" \
  --output-audit "${AUDIT_DIR}/catalog_period_audit.json"

"${PYTHON_BIN}" "${JPL_BUILDER}" \
  --safe-ephemerides-csv "${CONFIG_DIR}/jpl_bodies_primary_1611_2026.csv" \
  --events-csv "${INPUT_DIR}/corridor_targets_m79_deep_history.csv" \
  --output-float-csv "${INPUT_DIR}/deep_history_weekly_astro_float.csv" \
  --manifest-json "${CONFIG_DIR}/jpl_manifest.json" \
  --start-date 1611-11-26 \
  --end-date 2026-09-26 \
  --step-days 7 \
  --period-starts-csv "${CONFIG_DIR}/period_starts.csv" \
  --epoch-offset-hours -9 \
  --observer-lat 42.5 \
  --observer-lon 145.0 \
  --observer-elevation 0 \
  --observer-alias hokkaido_corridor_center \
  --ephemerides-fields 1,2,3,4,13,19,31,43 \
  --auto-clip none

"${PYTHON_BIN}" "${ROOT_DIR}/research_pipeline/scientific/v25_sanitize_jpl_master.py" \
  --input-csv "${INPUT_DIR}/deep_history_weekly_astro_float.csv" \
  --output-csv "${INPUT_DIR}/deep_history_weekly_astro_sanitized.csv" \
  --report-json "${AUDIT_DIR}/sanitization.json"

"${PYTHON_BIN}" "${ROOT_DIR}/research_pipeline/scientific/v25_add_eclipse_features.py" \
  --input-master "${INPUT_DIR}/deep_history_weekly_astro_sanitized.csv" \
  --output-master "${INPUT_DIR}/deep_history_weekly_astro_eclipses.csv" \
  --output-eclipse-catalog "${INPUT_DIR}/calculated_eclipse_catalog.csv" \
  --output-audit "${AUDIT_DIR}/eclipse_feature_audit.json" \
  --observer-lat 42.5 \
  --observer-lon 145.0

MPLCONFIGDIR=/tmp/dlvswave-v25-final "${PYTHON_BIN}" "${ROOT_DIR}/research_pipeline/scientific/v25_historical_nested.py" \
  --astro-master "${INPUT_DIR}/deep_history_weekly_astro_eclipses.csv" \
  --japan-catalog "${INPUT_DIR}/corridor_targets_m79_deep_history.csv" \
  --world-catalog "${WORLD_CSV}" \
  --output-dir "${RESULTS_DIR}" \
  --config-trials 32 \
  --top-configs 4 \
  --validation-event-count 3 \
  --force-start-year 1611 \
  --run-name hokkaido-sanriku-south-kurils-m79plus-7d-v25-deep-history-eclipse \
  --seed 625411

MPLCONFIGDIR=/tmp/dlvswave-v25-composite "${PYTHON_BIN}" "${ROOT_DIR}/research_pipeline/scientific/v22_hokkaido_validation_composite.py" \
  --results-dir "${RESULTS_DIR}" \
  --output-png "${RESULTS_DIR}/historical_eclipse_validation_location_forecast_composite.png"

"${PYTHON_BIN}" "${ROOT_DIR}/research_pipeline/scientific/v25_verify_historical_eclipse.py" \
  --project-dir "${PROJECT_DIR}"

"${PYTHON_BIN}" "${ROOT_DIR}/research_pipeline/scientific/v25_write_result_report.py" \
  --project-dir "${PROJECT_DIR}"
