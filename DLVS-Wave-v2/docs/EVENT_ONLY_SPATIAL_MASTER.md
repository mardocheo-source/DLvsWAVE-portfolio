# Automatic event-only spatial master preparation

Entry point: `src/prepare_event_only_spatial_master.py`.

The builder prepares new data files in a new output directory. It does not modify the energy pipeline, an active production study, or previously trained models. A new output directory is mandatory: an existing directory is rejected to prevent overwriting another run.

## Parameters and time semantics

- `--min-time DAYS`: validation window duration in **days**, not a calendar date. Example: `1095` is approximately three years. The final UTC calendar day counts as one day. The first usable weekly bin is the first Monday on or after the resulting start; it never moves backward outside the requested window.
- `--end-time`: final catalog cutoff, including its timezone.
- `--validation-mag`: initial spatial validation magnitude; default 6.8.
- `--min-download-mag`: hard lower bound for automatic validation magnitude reduction. It is not the starting download magnitude.
- `--mag-step`: decrement; default 0.1.
- `--train-mag`: fixed training magnitude; default 6.8. Validation threshold changes never change this parameter.
- `--min-events-per-zone`: required number of validation earthquakes in each existing zone; default 1. Set a larger value when more than presence of each class is required.

The current correction uses 2028 days, preserving validation from 2021-01-11 through 2026-07-31. It does not extend validation backward to older events. Training uses only event weeks before validation starts; training and validation cannot share a week or an event ID.

## Automatic source order

1. Read every supplied `--event-source`. These may be CSV catalogs stored in the repository database directories or event-rich master CSVs. Supported fields include origin time, magnitude, latitude, longitude and an optional catalog ID. A feature-only master or a master containing only old binary targets cannot recreate previously omitted low-magnitude events; it is rejected as an event source with a recorded reason.
2. Combine sources, remove duplicate event IDs and apply the requested area, cutoff and magnitude. The Japan arc exclusion and existing nearest-centroid zone assignment are retained. Zone boundaries are not refitted to force coverage.
3. If all zones already meet the requested count, use those real cached events. A completeness manifest, when supplied, checks source SHA-256, geographic bounds, time range and magnitude coverage. A complete local catalog can establish that a zone is absent at a threshold, avoiding a redundant network request.
4. When coverage is missing and cache completeness is not established, first call USGS **count** at the current threshold, area and time interval. Download only the bounded result. Requests exceeding the configured event limit are divided into smaller time intervals, counted again and deduplicated after download. The magnitude is not lowered merely to solve a download-size problem.
5. If a zone still has too few events, decrement validation magnitude and repeat. Stop successfully at the first sufficient threshold. Stop with `failure.json` if the magnitude floor, request limit or time limit is reached. An incomplete validation set is never labelled valid.
6. If usable historical training events are absent, the same bounded USGS mechanism can retrieve them at the **unchanged training magnitude**, within the existing feature-grid dates.

An event database in this implementation means an event CSV available locally, including files in `DB/`. Direct SQLite/PostgreSQL connections are not implemented; export the relevant event fields to CSV and pass that file as an event source.

USGS documents a maximum of 20,000 events per query. The default batch ceiling here is 19,000, with at most 40 requests, a 30-second request timeout and a 300-second overall preparation budget. These are exposed as CLI parameters. [USGS Event API documentation](https://earthquake.usgs.gov/fdsnws/event/1/).

## Targets and effemerides

Training and validation masters contain only weeks with catalog earthquakes. There is no Calm class, `prob_Calm`, quiescence target or filler row. Five `target_Zone_*` columns encode the actual zones as multi-hot labels. If earthquakes in two zones occur in the same week, both labels are retained instead of discarding one. Separate event tables preserve all origin times, magnitudes, coordinates and IDs; event counts and weekly row counts are reported separately.

Prospective rows remain unlabelled. Existing main/minor feature matrices supply the same weekly astronomical and seismic feature values, with exact date joins and finite-value checks. For the current data, their 1900–2030 coverage is sufficient: no JPL request is needed. This reuses their existing feature/scaling contract; it does not reconstruct or redefine seismic feature engineering when the validation label threshold changes.

The previous six-class spatial engine is **not compatible unchanged** with these five-zone event-only targets. The new masters are preparation output, not evidence that the old forecasts have been corrected. Subsequent training, fusion, validation metrics and report generation must use an event-only target head and loss, and must read the new split files explicitly.

## Current result

Output study: `studies_output/AUTORUN_japan_joint_energy_and_spatial_production_20260906/02a_spatial_zones_forecast_multitarget`.

The automatic search tried M6.8, 6.7, 6.6, 6.5, 6.4 and 6.3. M6.3 is the first threshold satisfying all-zone coverage in the fixed window.

| Zone | Validation earthquakes |
|---|---:|
| 0 | 1 |
| 1 | 8 |
| 2 | 6 |
| 3 | 2 |
| 4 | 5 |

There are 22 validation earthquakes in 19 weekly rows. Each branch has 225 training earthquakes in 199 weekly rows at M6.8. Feature counts remain 66 for main bodies and 82 for minor bodies. All validation labels are derived from the existing M5.5 regional catalog; this build downloaded neither events nor JPL ephemerides. Two preliminary live USGS count checks returned 12 events at M6.8 and 22 at M6.3 for the same regional query.

Output evidence: `run_config.json`, `selection_audit.json`, `master_manifest.json`, `01_data/training_events.csv`, `01_data/validation_events.csv`, and the separate training/validation/prospective masters under each branch's `01_data/`. Coverage source, input hashes, executable source snapshot and verification results are retained with the new study.

## Integration into the active study

The prepared masters now live in the existing spatial branch of AUTORUN_japan_joint_energy_and_spatial_production_20260906. The main task owns subsequent training and joint-report regeneration after energy completion. Preparation provenance is archived under the same study in 00_reproduction_audit/event_only_master_preparation. There is no independent study or scheduled duplicate training. Event-only metadata in the spatial root uses the event_only_ filename prefix. The standalone builder requires a new staging destination and must not overwrite this active folder.
