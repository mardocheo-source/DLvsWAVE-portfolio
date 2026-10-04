# V25 deep-history weekly pipeline — Sanriku, Hokkaido and southern Kurils

## Scope and interpretation

This is an experimental pattern-validation pipeline for one regional M7.9+ weekly score. It is not an operational earthquake-prediction system, and the score is not a probability. A 2026 peak may be reported only together with the frozen timing and location gate results.

The prospective seismic cutoff is `2026-08-01 00:00 JST` (exclusive). No August 2026 earthquake observation is allowed into data preparation, model selection, validation or fitting.

## Earthquake data

- Instrumental catalog: fresh USGS FDSN download, 1900 through `2026-07-31 15:00 UTC` (exclusive), regional M5.5+ for catalog construction and worldwide M7.9+ for non-regional hard negatives.
- Region: 38.8–46.0 N, 140.0–150.5 E.
- Historical timing attachments: 1611 Keicho Sanriku, 1843 Kushiro–Nemuro, 1894 Nemuro-oki and 1896 Meiji Sanriku.
- Historical rows preserve the official day but do not fabricate an event time or epicentral coordinates. They are timing-only (`location_eligible=0`).
- The combined target catalog has 15 independent seven-day slots: four historical timing-only and eleven location-eligible instrumental events.
- 1454 and 1611 are not counted as two independent megathrust examples because the long-term evaluation discusses their possible equivalence.

## Astronomical data and exact epoch contract

Each row label is Saturday `00:00 JST`. Horizons is queried at that exact instant by applying `epoch_offset_hours=-9` before conversion to UTC Julian Day. The manifest records the requested and returned epochs; the maximum verified alignment error is zero days.

Primary bodies must pass endpoint probes at both 1611 and 2026. The primary set is Sun, Mercury, Venus, Moon, Mars, Jupiter, Uranus, Io, Europa, Ganymede and Callisto. Saturn, Neptune, Pluto, Titan and Bennu fail full-span availability and are excluded. Eris, Sedna, Apophis, 2012 VP113 and 2015 TG387 are technically queryable but are excluded from the primary run because a centuries-long small-body retro-propagation is treated only as a sensitivity input.

No astronomical value is forward-filled or imputed. A JPL field with any non-finite value is dropped as a whole and audited; the current master retains all 176 JPL fields, 16 for each primary body.

## Calculated eclipse columns

Swiss Ephemeris in Moshier mode calculates, independently of earthquake labels:

- global solar and lunar eclipse presence, count and maximum type code in `[Saturday 00:00 JST, next Saturday 00:00 JST)`;
- the same properties for eclipses visible from 42.5 N, 145.0 E;
- any-global presence and count;
- signed and absolute days from the week midpoint to the nearest global eclipse, plus its solar/lunar family.

This produces 17 numeric columns. A deterministic screen includes `all`, `no_eclipse` and `eclipse_only` controls. Only one of the 15 target weeks (1894-03-17) contains a global eclipse, so eclipse-only results must be interpreted as a sparse ablation, not evidence of physical causation.

## Model and validation contract

- Three outer reporting events: 1994, 1995 and 2003.
- The same three events are used for the timing and location panels.
- Each outer fold performs configuration, feature and ensemble-weight selection using earlier events only; its final fit contains 12, 13 and 14 positive events respectively.
- The prospective fit contains all 15 timing events. Location uses only the 11 rows with observed coordinates.
- Recent development folds receive greater objective weight, while every fit must retain a non-zero training-quality gate.
- Search space: deterministic body/field ablations plus random vertical/horizontal sampling combinations; logistic regression, Extra Trees, histogram boosting, five PyTorch MLPs, two spline KANs and two UCS/LCS variants.
- Deep nets and KANs run on CPU: these are small, irregular tabular folds, where device-transfer and compilation overhead make XPU unattractive.
- Worldwide non-regional M7.9+ events are negative controls, with the most recent high-magnitude subset frozen for a hard-negative audit.

Timing passes only if all three outer peaks are exact, all are within one slot, mean event percentile is at least 0.85, mean quality is at least 0.70, training quality is at least 0.55 and both hard-negative thresholds pass. Location has independent median, q80, zone-hit and recency-baseline improvement gates. A failed gate is written as a failure; it is never converted into a validated forecast.

The reporting events have appeared in the prior research lineage. Nested selection is leakage-safe within V25, but the result is not a historically untouched discovery test.

## Reproduction

Run `research_pipeline/scientific/run_v25_historical_eclipse.sh`. It performs the USGS downloads, catalog construction, Horizons build, strict sanitization, eclipse calculation, nested model search, composite rendering and final consistency verification.
