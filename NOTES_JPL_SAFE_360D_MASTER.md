# JPL-Safe 360d Japan/Nankai Master

This note documents the 360-day Japan/Nankai master/training setup created on
2026-05-06.

## What Was Added

- `build_jpl_safe_360d_master.py`
- `build_jpl_observer_360d_master.py`
- `commands/create_master_japan_nankai_360d.sh`
- `commands/create_master_japan_nankai_360d_observer_japan.sh`
- `commands/train_japan_nankai_360d_fast.sh`
- `commands/train_japan_nankai_360d_long.sh`
- `commands/run_japan_nankai_360d_final.sh`
- `commands/run_japan_nankai_360d_observer_japan_long.sh`
- `commands/run_japan_nankai_360d_observer_autoclip_both_compare_long.sh`
- `make_validation_variant_master.py`
- `commands/run_japan_nankai_360d_validation_variants_long.sh`

The one-shot command is:

```bash
cd /mnt/git0/git/repository/DLvsWAVE
./commands/run_japan_nankai_360d_final.sh
```

After the first historical run, JPL Horizons reported that Mars vectors are not
available before A.D. 1600-01-02. Two explicit comparison wrappers were added:

```bash
# Full historical start, excludes Mars.
./commands/run_japan_nankai_360d_from1498_no_mars.sh

# Keeps Mars, starts after the Horizons Mars lower bound.
./commands/run_japan_nankai_360d_from1600_with_mars.sh
```

Two auto-clipping wrappers are also available:

```bash
# Vertical clipping: preserve requested dates, remove unavailable bodies.
./commands/run_japan_nankai_360d_autoclip_vertical.sh

# Horizontal clipping: preserve bodies, shorten date range when Horizons
# reports a parsable date bound.
./commands/run_japan_nankai_360d_autoclip_horizontal.sh
```

To run both variants and automatically compare their final smart-fusion
forecasts:

```bash
./commands/run_japan_nankai_360d_autoclip_both_compare.sh
```

Useful comparison-only mode, if both trainings already exist:

```bash
SKIP_RUNS=1 ./commands/run_japan_nankai_360d_autoclip_both_compare.sh
```

The comparison uses the latest `pulsar_train*_best_trials_*` directory from
each output folder and writes CSV/PNG/JSON under:

```text
/mnt/git0/git/repository/astro-USGS2/DB/japan-nankai-big-one-360d-autoclip-comparison
```

For a longer search with more BANK/readout/hybrid combinations but deliberately
compact LCS rules:

```bash
./commands/run_japan_nankai_360d_autoclip_both_compare_long.sh
```

That long profile defaults to one small LCS preset, 4 active LCS conditions,
5 exported LCS rules, smart post-hybrid up to 3 candidate peaks, and a final
vertical-vs-horizontal merge that accepts up to 2 peaks.

Observer-frame alternative, using topocentric Horizons ephemerides from the
approximate center of Japan (`lat=34.5`, `lon=137.5`, `elev=0km`):

```bash
./commands/create_master_japan_nankai_360d_observer_japan.sh
```

One-shot observer master plus long training:

```bash
./commands/run_japan_nankai_360d_observer_japan_long.sh
```

Observer vertical-vs-horizontal auto-clip comparison with the same final
overlap graph used by the vector runs:

```bash
./commands/run_japan_nankai_360d_observer_autoclip_both_compare_long.sh
```

The observer builder writes the same master filenames as the vector builder,
but its astro columns use `frame:topocentric` and `obs:japan_center`. `earth`
is excluded by default because Earth as a target from a terrestrial observer is
normally invalid/redundant. `AUTO_CLIP=vertical` is the default, so unavailable
historical targets are removed while preserving the 1498 start.

Smart post-hybrid best-effort internals are now persisted under the run folder:

```text
post_hybrid_checks_smart/shape_winner_merge/
post_hybrid_checks_smart/peak_winner_merge/
post_hybrid_checks_smart/smart_result/
```

Older logs may say `tmpdir`; new runs write those intermediate merges visibly.

Validation robustness variants:

```bash
./commands/run_japan_nankai_360d_validation_variants_long.sh
```

This creates three masters under
`japan-nankai-big-one-360d-validation-variants-long`: `normal`, `reverse`, and
`random`.  The anti-leak rule is strict: rows with `date >= FORECAST_START`
are never shuffled.  Only pre-forecast rows are reversed or randomly permuted
into serial date slots.  Each variant writes:

```text
validation_variant_manifest.json
validation_variant_mapping.csv
master_with_usgs_core_astrofmt.csv
```

Then each variant runs the long training/smart merge, and a final
`forecast_common_window.py` consensus compares the three
`smart_fusion_final__forecast.csv` files.

## Important Semantics

- One row is one 360-day period.
- The `date` column is the start of that period.
- Earthquake events are assigned with left-bin logic:
  `event_time in [row_date, next_row_date)`.
- Historical dates are handled with Python `datetime`/CSV logic, not pandas
  timestamp parsing, because this dataset starts in 1498.

## Why This Does Not Use nasaDb.py Yet

For this specific master, the attached safe ephemerides CSV is the source of
truth. It declares Horizons target ids and recommended centers, for example:

- Sun `10` at `@0`
- Earth `399` at `@0`
- Moon `301`, defaulted here to `@0` for common-frame SSB vectors
- Jupiter/Saturn/Uranus/Neptune system barycenters at `@0`

The existing `astro-USGS2/nasaDb.py` pipeline currently calls:

```python
Horizons(...).ephemerides(quantities=...)
```

That is the older standard flow for ephemerides/observer-style fields. This
360d historical master instead needs:

```python
Horizons(...).vectors(...)
```

using Cartesian state vectors from the body/center pairs in the safe CSV.

## Future Cleanup Tip

The clean next step is to add a vector mode to `nasaDb.py`, for example:

```bash
--safe-vectors-csv jpl_safe_ephemerides_for_japan_historical_model.csv
--vectors-mode
--moon-center ssb
```

Then `nasaDb.py` could own the standard download/cache/merge behavior while
still respecting the JPL-safe CSV contract. At that point
`build_jpl_safe_360d_master.py` could become a thin wrapper, a regression test,
or be retired.

## Outputs To Check After Run

Expected output directory:

```text
/mnt/git0/git/repository/astro-USGS2/DB/japan-nankai-big-one-360d
```

Key files:

- `master_with_usgs_core_astrofmt_float.csv`
- `master_with_usgs_core_astrofmt.csv`
- `master_with_usgs_core_astrofmt_manifest.json`

The manifest records the actual Horizons ids, centers, vector columns, event
assignment summary, and moon-center mode used for that run.

## Annual Validation Policy

For 360-day records, sparse historical events can make validation windows span
many decades. The training CLI now has:

```bash
--validation-max-lookback-records N
```

This limits backtest/recent-validation event windows to the last `N` records
before the forecast/target anchor and automatically reduces event-count down to
1 when the requested count is too wide for that limit.

The Japan/Nankai 360d training script defaults to:

- `FORECAST_START=2023-01-01`
- `VALIDATION_MAX_LOOKBACK_RECORDS=30`
- main target/test window with two events
- recent validation with two events, intended to cover the 2003 and 2011
  Japan M8+ bins
- `VALIDATION_PRE_RECORDS=5`
- `VALIDATION_POST_RECORDS=3`
- LCS internal validation uses the same two-event window via `--lcs-val-*`
- Deep/Torch internal validation uses the same two-event window via
  `--deep-val-*` and `--deep-validation-metric event_composite`
- no automatic backtest windows, because the annual sparse dataset made the
  combined validation chart reach too far into the past

For the vertical master this maps to event rows around:

- `2003-08-22`
- `2010-07-16` period start for the 2011 event

For the horizontal master this maps to:

- `2003-02-18`
- `2011-01-07`

## Body Availability Modes

The builder now supports three controls for JPL coverage issues:

```bash
--auto-clip vertical
--auto-clip horizontal
--exclude-bodies mars
--on-body-error skip
--probe-only
```

The equivalent environment variables in `create_master_japan_nankai_360d.sh`
are:

```bash
EXCLUDE_BODIES=mars
ON_BODY_ERROR=skip
AUTO_CLIP=vertical
```

Probe checks performed on 2026-05-06:

- `1498-01-01 -> 2035-12-31`, excluding Mars: Sun, Mercury, Venus, Earth, Moon,
  Jupiter barycenter, Saturn barycenter, Uranus barycenter, and Neptune
  barycenter all responded from Horizons.
- `1600-01-02 -> 2035-12-31`, including Mars: all 10 safe CSV bodies responded
  from Horizons.
