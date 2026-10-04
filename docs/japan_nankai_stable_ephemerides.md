# Japan/Nankai Stable Ephemerides Variant

This note documents the stable 30d Japan/Nankai ephemerides variant.

## Why This Variant Exists

Older Japan pipelines used `nasaDb.py` with `earthFull` or `fullAstroJapan`, plus observer geometry near Japan. That produced rich fields such as RA, DEC, AZ, EL, range/range-rate, apparent coordinates, and ecliptic coordinates for many bodies. Those fields can be expressive, but they are less defensible for very old historical dates because topocentric apparent quantities, satellites, asteroids, and trans-Neptunian objects may have limited or less stable Horizons coverage.

The stable variant keeps the forecast shape closer to Earth-referenced astronomy while using a simpler, more historically robust coordinate system:

- JPL geometric vectors instead of observer apparent ephemerides.
- Earth-center `@399` as the reference center.
- ICRF/J2000 Cartesian state vectors: `x`, `y`, `z`, `vx`, `vy`, `vz`, `lighttime`, `range`, `range_rate`.
- Barycenters for planets and outer systems where possible.

## Body Choices

The stable CSV is `resources/japan_nankai_stable_geocentric_ephemerides.csv`.

Included:

- Sun center `10` from Earth center.
- Mercury/Venus barycenters `1`, `2`.
- Moon center `301` from Earth center.
- Mars barycenter `4`, not Mars center `499`.
- Jupiter/Saturn/Uranus/Neptune system barycenters `5`, `6`, `7`, `8`.
- Pluto system barycenter `9` as a coarse distant proxy.

Excluded intentionally:

- Earth target from Earth center.
- Galilean moons, Titan, asteroids, Bennu/Apophis, Eris/Sedna/TNOs.

Those excluded bodies were useful in old `earthFull/fullAstroJapan` experiments, but they are more fragile for a 1498+ historical model. Jupiter and Saturn barycenters are used as stable proxies for their moon systems.

## Auto-Clip Policy

The wrapper tries vertical auto-clip first, preserving the full 1498+ history and removing unavailable bodies only if necessary.

If Mars is removed by vertical auto-clip, the wrapper rebuilds the master with horizontal auto-clip instead. This follows the experimental preference: keep Mars if the only cost is moving the start date forward. Mars is represented as barycenter `4`, so it should usually survive vertical clipping.

## Validation Leakage Guard

The normal/reverse/random validation wrapper uses `make_validation_variant_master.py`.

Reverse and random variants permute only rows with `date < FORECAST_START`. Rows in the forecast area are not shuffled. The wrapper also checks each variant mapping CSV and fails if any forecast row maps to a different source row.

Recent validation random negatives are sampled inside the validation event span, not inside the forecast area. Causal train/test separation remains based on output serial slot order.

## 30d Future Forecast Window

The current stable-geocentric 30d wrapper defaults to a future-oriented forecast window:

- `FORECAST_START=2026-02-01`
- `FORECAST_END=2026-12-31`

Recent past rows are kept for validation only. This avoids presenting early-2025 windows as future forecast signal after those periods have already passed.

## Negative Anchor Events

To reduce false positives, the stable-geocentric 30d master can augment the Japan/Nankai positive event list with large global earthquakes that are outside the Japan box:

- Japan box: latitude `28..44`, longitude `128..147`.
- Source: local global catalog `WORLD-MAG7.7-1900-2025-10-01-MERGED/earthquakes.RAW.csv`.
- Filter: global `mag >= 8.0`, outside the Japan box.
- Default cap: strongest `48` selected anchors after a 30-day dedupe.

These rows are written with `mag=0` and blank `latitude`, `longitude`, and `depth`. The master therefore builds the astronomical row at the real global-event date, but the final seismic target remains a negative Japan/Nankai example. This is intentional: the model sees "major earthquake elsewhere" as a non-event for the Japan M8+ target.

## FullAstroJapan 7d Zoom Variant

The 7d diagnostic wrapper uses the legacy `astro-USGS2/nasaDb.py` preset:

- `--place fullAstroJapan`
- ephemerides fields `1,2,3,4,13,19,31,43`
- full primary/secondary/extra body levels from `nasaDb.py` and `config.py`
- observer override `34.5,137.5,0,japan_center` by default, so the rich fullAstroJapan body set is evaluated from central Japan

It intentionally starts at `1904-01-01`. This is the horizontal/full tradeoff: keep the richer body set, including secondary bodies, and drop the much older historical events whose dates and ephemerides are less reliable for this zoom. The default forecast context is `2026-07-01 -> 2026-09-30`, so the 7d run acts as a microscope over the broad August signal rather than a standalone long-horizon detector.

The same negative-anchor builder is used with the date filter enabled. In the local catalog check it kept 8 Japan/Nankai positive events from 1933, 1941, 1944, 1946, 1952, 1968, 2003, and 2011, plus 48 global non-Japan M8+ negative anchors.
