#!/usr/bin/env bash
# Step 6: Hierarchical Optuna Feature Selection (Modulo 6)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DLVS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)/DLVS-Wave-v2"
PYTHON_BIN="${PYTHON_BIN:-$(which python3)}"

echo "=== [Step 6/6] Running Hierarchical Prefix Optimization (Optuna) ==="
"$PYTHON_BIN" "$DLVS_ROOT/src/optimizer.py" \
    --input-csv "$SCRIPT_DIR/master_1d_uncompressed.csv" \
    --target-col seis_core_magnitude \
    --n-trials 50 \
    --output-summary "$SCRIPT_DIR/optuna_summary.json"

echo ">>> Step 6 Complete: Optimal feature subset saved in $SCRIPT_DIR/optuna_summary.json"
