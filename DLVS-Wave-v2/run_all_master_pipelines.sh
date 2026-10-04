#!/usr/bin/env bash
# ==============================================================================
# DLVS-WAVE v2.0 - MASTER ALL-IN-ONE PIPELINE EXECUTION SCRIPT
# Runs all tests, production runs, and multi-country century pipelines
# Automatically detects and handles Python virtual environment
# ==============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Virtual Environment Resolution
if [ -f "/mnt/git0/git/repository/DLvsWAVE/.venv/bin/python3" ]; then
    PYTHON_EXEC="/mnt/git0/git/repository/DLvsWAVE/.venv/bin/python3"
elif [ -n "$VIRTUAL_ENV" ]; then
    PYTHON_EXEC="python3"
else
    PYTHON_EXEC="python3"
fi

export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

echo "================================================================================"
echo " DLVS-WAVE v2.0 - COMPLETE MASTER SYSTEM RUNNER"
echo " Project Directory: $PROJECT_ROOT"
echo " Python Executable: $PYTHON_EXEC"
echo " Date: $(date -u)"
echo "================================================================================"
echo ""

# 1. UNIT & MODULE TESTS (7/7 modules)
echo ">>> STEP 1: Running Complete 7-Module Validation Suite <<<"
$PYTHON_EXEC "$PROJECT_ROOT/tests_env/run_all_tests.py"
echo ""

# 2. PRODUCTION RUNS (Japan & Italy)
echo ">>> STEP 2: Running Full Production Pipelines (Japan Tohoku & Central Italy) <<<"
$PYTHON_EXEC "$PROJECT_ROOT/production_runs/execute_production_runs.py"
echo ""

# 3. CENTURY-SCALE 131-YEAR MULTI-COUNTRY SUITE (1900-2030)
echo ">>> STEP 3: Running Century-Scale (1900-2030) Suite Across 4 Global Locations <<<"
$PYTHON_EXEC "$PROJECT_ROOT/tests_env/multi_country_century_tests/run_all_century_tests.py"
echo ""

echo "================================================================================"
echo " ALL PIPELINES, TESTS, AND PRODUCTION DATASETS GENERATED SUCCESSFULLY!"
echo "================================================================================"
