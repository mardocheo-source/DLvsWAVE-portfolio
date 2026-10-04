#!/usr/bin/env bash
# Fresh astronomy-only World with Japan-style origin refits. Extra forecast run options follow.
# Example: bash commands/run_world_astro_refit.sh --output /absolute/new/study
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "${PROJECT_DIR}/commands/forecast.sh" run \
  --config "${PROJECT_DIR}/configs/world_nested_astro_refit.json" --label world_astro_refit "$@"
