#!/usr/bin/env bash
# Compatibility wrapper. Use create_master_japan_nankai_august_observer_japan_sparse.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/create_master_japan_nankai_august_observer_japan_sparse.sh" "$@"
