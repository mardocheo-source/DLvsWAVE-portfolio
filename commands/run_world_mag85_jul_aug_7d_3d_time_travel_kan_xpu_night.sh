#!/usr/bin/env bash
# Night macro-run: worldwide M8.5+ July-August 2026 ribbon forecasts.
# Runs 7d precision first, then 3d precision, both on Intel XPU.
set -euo pipefail

cd "$(dirname "$0")/.."

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
MACRO_OUT_DIR="${MACRO_OUT_DIR:-$ASTRO_ROOT/DB/world-mag85plus-jul-aug-time-travel-ribbon-kan-xpu-night}"
PYTHON_BIN="${PYTHON_BIN:-${HOME}/venvs/dlvswave-xpu/bin/python}"

TIME_TRAVEL_MODE="${TIME_TRAVEL_MODE:-fibonacci-gold}"
TIME_TRAVEL_VALUE="${TIME_TRAVEL_VALUE:-1280}"
REUSE_EXISTING_MASTER="${REUSE_EXISTING_MASTER:-0}"
FORECAST_START="${FORECAST_START:-2026-07-01}"
FORECAST_END="${FORECAST_END:-2026-08-31}"

mkdir -p "$MACRO_OUT_DIR"
MACRO_LOG="$MACRO_OUT_DIR/world_mag85plus_jul_aug_7d_3d_time_travel_kan_xpu_night.log"

cat > "$MACRO_OUT_DIR/RUN_THIS_NIGHT_MACRO.sh" <<EOF
#!/usr/bin/env bash
cd "$(pwd)"
TIME_TRAVEL_MODE="$TIME_TRAVEL_MODE" TIME_TRAVEL_VALUE="$TIME_TRAVEL_VALUE" \\
REUSE_EXISTING_MASTER="$REUSE_EXISTING_MASTER" \\
FORECAST_START="$FORECAST_START" FORECAST_END="$FORECAST_END" \\
PYTHON_BIN="$PYTHON_BIN" \\
./commands/run_world_mag85_jul_aug_7d_3d_time_travel_kan_xpu_night.sh
EOF
chmod +x "$MACRO_OUT_DIR/RUN_THIS_NIGHT_MACRO.sh"

cat > "$MACRO_OUT_DIR/pipeline_notes.md" <<EOF
# Worldwide M8.5+ July-August 2026 Night Macro

Runs two independent KAN/XPU forecasts:

1. 7-day precision: \`run_world_mag85_7d_jul_aug_time_travel_kan_xpu_1h.sh\`
2. 3-day precision: \`run_world_mag85_3d_jul_aug_time_travel_kan_xpu_1h.sh\`

Shared settings:

- Target: worldwide M8.5+.
- Forecast real timeline: ${FORECAST_START} -> ${FORECAST_END}.
- Historical ephemerides start after 1903.
- Time-travel ribbon: \`${TIME_TRAVEL_MODE}\` value \`${TIME_TRAVEL_VALUE}\`.
- Validation: 3 events, with 6 records before and 6 records after each event.
- KAN device: Intel XPU, jobs=1.
- Approximate target budget: about 1 hour per child script on the current XPU setup.

Re-run command: \`RUN_THIS_NIGHT_MACRO.sh\`.
EOF

echo "======================================================================"
echo " Worldwide M8.5+ Jul-Aug 2026 7d + 3d Time-Travel KAN/XPU night macro"
echo " Macro output: $MACRO_OUT_DIR"
echo " Forecast:     $FORECAST_START -> $FORECAST_END"
echo " Ribbon:       $TIME_TRAVEL_MODE value=$TIME_TRAVEL_VALUE"
echo " Rebuild:      REUSE_EXISTING_MASTER=$REUSE_EXISTING_MASTER"
echo " Python:       $PYTHON_BIN"
echo " Log:          $MACRO_LOG"
echo "======================================================================"

{
  echo "[macro] started $(date -Is)"
  echo "[macro] 1/2: 7d forecast"
  TIME_TRAVEL_MODE="$TIME_TRAVEL_MODE" \
  TIME_TRAVEL_VALUE="$TIME_TRAVEL_VALUE" \
  REUSE_EXISTING_MASTER="$REUSE_EXISTING_MASTER" \
  FORECAST_START="$FORECAST_START" \
  FORECAST_END="$FORECAST_END" \
  PYTHON_BIN="$PYTHON_BIN" \
  ./commands/run_world_mag85_7d_jul_aug_time_travel_kan_xpu_1h.sh

  echo "[macro] 2/2: 3d forecast"
  TIME_TRAVEL_MODE="$TIME_TRAVEL_MODE" \
  TIME_TRAVEL_VALUE="$TIME_TRAVEL_VALUE" \
  REUSE_EXISTING_MASTER="$REUSE_EXISTING_MASTER" \
  FORECAST_START="$FORECAST_START" \
  FORECAST_END="$FORECAST_END" \
  PYTHON_BIN="$PYTHON_BIN" \
  ./commands/run_world_mag85_3d_jul_aug_time_travel_kan_xpu_1h.sh

  echo "[macro] finished $(date -Is)"
} 2>&1 | tee "$MACRO_LOG"

echo ""
echo "======================================================================"
echo " Night macro complete"
echo " Macro dir: $MACRO_OUT_DIR"
echo " Log:       $MACRO_LOG"
echo "======================================================================"
