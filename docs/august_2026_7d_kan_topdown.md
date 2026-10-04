# August 2026 7-day KAN top-down pipeline

This pipeline answers two separate experimental questions in order:

1. **When?** A small KAN reads a complete 7-day solar-system feature grid and
   ranks the August 2026 slots.
2. **Where?** Two small KAN regressors estimate latitude and longitude inside
   the strongest timing slot.

The default source master is reused from the existing worldwide M8.5+ run. It
contains 90 Earth-centered JPL vector features for the Sun, Moon, Mercury,
Venus, Mars, Jupiter, Saturn, Uranus, Neptune, and Pluto system barycenters.
The source file is copied into the run directory and is never modified.

The weekly grid is Wednesday-aligned. Complete August coverage therefore uses
the five slot starts `2026-07-29`, `2026-08-05`, `2026-08-12`,
`2026-08-19`, and `2026-08-26`; the first slot covers August 1-4.

## Data contract

The timing stage needs all weekly rows, including historical non-events, to
learn the event/no-event target. The location stage has a different contract:

- historical training and validation rows are earthquakes only;
- the five future rows overlapping August are retained only to carry
  astronomical features;
- `date`, `mag`, `depth`, `latitude`, and `longitude` are excluded as location
  model inputs;
- positive event rows inside the forecast window fail the anti-leak guard.

The reusable intermediate file is named
`02_location/seismic_history_with_forecast_grid.csv`. Its JSON manifest records
the selected event dates, future projection dates, counts, and leakage check.

## Quick run

```bash
./commands/run_august_2026_7d_kan_topdown.sh
```

Useful overrides:

```bash
KAN_DEVICE=cpu \
TIMING_SEEDS=4,5 \
LOCATION_SEEDS=4,5 \
OUT_DIR="$PWD/DB/my-august-topdown" \
./commands/run_august_2026_7d_kan_topdown.sh
```

To reuse an existing timing forecast and run only focus selection plus
localization:

```bash
RUN_TIMING=0 \
TIMING_FORECAST_CSV=/path/to/TASK__final_evaluation__forecast.csv \
./commands/run_august_2026_7d_kan_topdown.sh
```

Set `RUN_LOCATION=0` for timing and seismic-master preparation only.

## Outputs

- `01_timing/timing_focus_window.json`: ranking and selected 7-day slot.
- `02_location/seismic_history_with_forecast_grid.csv`: reusable location input.
- `02_location/latitude/location_report/`: latitude validation and forecast.
- `02_location/longitude/location_report/`: longitude validation and forecast.
- `02_location/august_2026_location_coordinates.csv`: combined coordinates.
- `03_dashboard/topdown_forecast_validation_dashboard.png`: timing and location
  forecast/validation panels with quality metrics.
- `run_manifest.md`: lineage for the complete run.

These outputs are experimental research artifacts, not an operational
earthquake warning.
