#!/usr/bin/env bash
# Compatibility wrapper. Use run_japan_nankai_august_observer_autoclip_both_compare_kan.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/run_japan_nankai_august_observer_autoclip_both_compare_kan.sh" "$@"
