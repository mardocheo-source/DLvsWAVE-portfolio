# Forecast rules and reproducibility audit

Audit date: 2026-09-07. Maintained source: `DLVS-Wave-v2/src`.
Scope: source inspection, configuration checks, offline contract tests and
standalone startup/resume. Existing production studies and Japan PDFs are not
modified by this audit. This is an implementation audit, not a new forecast.

## Findings

The nested pipeline can be launched without an assistant. The new opt-in
`origin_refit_astro_only` energy protocol shares Japan fitting and sampling, but
excludes all seismic predictors. Legacy configurations retain their old path.
The matrix distinguishes implemented behavior from remaining limitations.

| Requested behavior | Implementation / evidence | Status |
|---|---|---|
| Unique output per execution under studies_output | `forecast_cli.main`: UTC + label + ID; existing output refused | Implemented |
| Single-region and nested operation | `initial_membership_rules`, `initial_geo_level`, `max_geo_level`; three portable JSON examples | Implemented, maximum L4 in launcher |
| Save an area map before training | `run_global_recursive_forecast.run` -> `world_node_map.build` | Implemented |
| Separate model stages from geographic levels | Five branch stage folders; geographic L0-L4 in navigation | Implemented |
| Report before descent / explicit stop | `node_report`, `study_status.pdf`, `summary`; stopped-node PDF smoke test | Implemented |
| Main and minor energy and location | `production_energy`, `production_location`; KAN, Deep ResNet, LCS; independent historical analog search | Implemented |
| Main/minor final 85/15 ordinates | `world_weighted_energy_fusion.choose`; tests on validation/forecast and 0/100, 85/15, 100/0 | Implemented |
| Recover suppressed peaks with huntanyway | Recover existing stage curves when validation-best stage is flat; preserve source CSVs and hashes | Implemented, not a peak guarantee |
| Compare parent time window | Recovery stage prioritization with configured tolerance | Implemented for recovery, not a general posterior update |
| Prefer higher confidence when branches disagree | Validation ranks candidate stages; fixed main weight dominates | Partial: no separately calibrated confidence arbitration |
| First event rather than highest peak | `production_geography.select_peak` with `first_event` | Implemented; interior local maxima only |
| Temporal child zoom | `world_zoom.temporal_zoom`; November 2 gives October 19-November 22 | Implemented |
| Recent-event geographic rectangle | `world_zoom.event_rectangle`; cutoff exclusion, recency weighting, date-line and margin tests | Implemented |
| Adjacent zones on consecutive dates | `world_zone_reconciliation.decide`; gap, adjacency, score margin; one reconciliation | Implemented |
| Fresh fits after domain union | `apply` archives prior node and clears fitted state, preserving charged node budget | Implemented |
| Several simultaneous geographic siblings | Current driver selects one child, optionally a combined domain | Not implemented |
| Energy 2-3 recent validation events without sacrificing too much training | `energy_contract`; magnitude decrement, recency and retained-event checks | Implemented as event-week count; actual earthquake count can exceed it |
| More location validation events / no empty training rows | `prepare_location`; occupied weeks and multi-target zone labels | Implemented |
| Strict upper bound on location validation events | `maximum_location_validation_events`; optional shortest covered suffix and zone refit | Implemented; new example maximum 30, minimum 12 |
| Automatic smaller magnitude | Energy target and location validation threshold adapt within configured floor | Implemented; no automatic below-floor catalog download |
| No unknown future seismic inputs, World | Astronomical-only masters; labels remain separate | Implemented for this input path |
| Known future astronomy / feature search | `load_astronomy`; training-only normalization and randomized feature subsets | Implemented; configurable astronomical offset list, head/tail coverage receipts |
| Future seismic removal before bitwise fusion | `world_origin_energy.prepare`, independent astronomy-only codebooks | Implemented in new World; legacy remains uncompressed |
| Pi-derived per-gap infill for both energy branches | `causal_japan_energy.sample_training` | Implemented in new World using the shared sampler |
| All terminal observed quiescence retained | Shared sampler and World origin tables | Implemented in new World; legacy unchanged |
| Separate forecast refit through recent cutoff | `world_origin_energy` using `causal_japan_energy.fit` | Implemented in new World; cutoff remains fixed during nested zoom |
| One-shot location | Fixed training/validation split and fixed model across forecast horizon | Implemented |
| Leakage and selected-model replay checks | `production_leakage_audit`, `audit_world_location_publication`, bounded BLAS replay | Implemented; does not make validation an untouched test |
| Magnitude training graph with connected grouped periods | `world_energy_reports.validation_plot` | Implemented; separate Japan accepted renderer preserved in its snapshot |
| Energy-derived location map intervals | `world_location_reports` consumes final fused energy CSV | Implemented |
| Neural, historical and combined location reports | `dual_method_reports/{learned,historical_analogs,fused_methods}` | Implemented; literal a/b views are in Japan publisher |
| English help and operator examples | `forecast_cli`, `commands/forecast.sh`, operator guide | Added and checked |
| Frozen code, immutable config, runtime record | `forecast_cli.execute`, source manifest, `runtime_environment.json` | Added/verified for new standalone studies |
| Resume without charging pause as node compute | `node_elapsed_seconds` checkpoint, preserved across union | Corrected in maintained driver; existing studies retain frozen behavior |
| Source available in mother project | Missing spectrum renderer recovered into src; dependency closure checked before commit | Corrected |

## Reproducibility boundaries

1. A fresh run with the same configuration executes the same documented
   algorithm. Identical final results also depend on raw catalog revision,
   ephemerides, numeric libraries, threading, hardware and committed trial count.
2. Exact old-study resume uses its frozen source and original paths. The launcher
   rejects tampered source. It does not automatically migrate absolute cache
   references or alter a stopped study's magnitude settings.
3. The causal Japan launcher needs private/local input files and an existing
   location reference; excluding them from Git is intentional. It is not a
   data-free clone-and-run reproduction of the old report.
4. The offline synthetic smoke tests verify execution mechanics and generated
   stop reports. Live network acquisition and a fresh multi-hour full search
   are not rerun as part of this packaging audit.
5. No completed Japan run, fitted artifact or published PDF was changed. New
   source is for subsequent runs. Historical source snapshots are excluded from
   the commit along with all other study outputs.

## Corrections made during this audit

- Added the standalone `forecast.sh` / `forecast_cli.py` command suite.
- Replaced private cache paths in the World default with portable fresh-download
  behavior and made the recent selection/union/hunt policies explicit.
- Added regional single-node and regional recursive example configurations.
- Added pinned runtime requirements and source/runtime freezing at launch.
- Fixed union membership for a `zones` list without a redundant single `zone`.
- Preserved accumulated node time across reconciliation and excluded paused time
  in subsequent executions of the maintained driver.
- Restored the missing energy spectrum renderer from the completed Japan source
  snapshot into the maintained source tree.
- Added executable offline tests and generated-output Git exclusions.

Do not replace a “Partial” or “Not implemented” row with “Implemented” until its
actual code path and an appropriate test exist. In particular, adding a JSON
parameter that a fitter never reads is not implementation.

## Previous release verification (7e4e937)

Thirteen offline tests passed both in the working project and in an isolated
export containing only the release's selected source/configuration files. The
suite includes actual tiny KAN, Deep ResNet and LCS fits, strict numerical replay,
stage fusion, source tampering detection and an end-to-end cached-input run that
generates an explicit stopped-node PDF. The Bash preflight and help commands
also passed from outside the repository directory. No full production forecast
or live-data download was launched for this release check.

The release contains 44 Python dependency files listed with checksums in
`FORECAST_SOURCE_MANIFEST.json`. Test fixtures and rendered PDFs are temporary;
only test source is included. The Git change list was checked against an explicit
source/documentation allowlist before publication.

## Astronomy-only refit upgrade

The new protocol is wired into the maintained input builder, worker dispatch,
trial search, replay and report composer. Tests exercise actual KAN/Deep/LCS
fits with prediction-label perturbation, future-observation exclusion,
training-only quantile edges, terminal-row retention and separate forecast
training. A separate tiny integration run executes both branches, all fusion
stages, strict selected-model replay and report rendering from synthetic data.
It is not a production accuracy result. Source publication excludes its outputs.

The new example has a hard 30-event location maximum and seeks a smaller
whole-week window with every zone covered and at least 12 events. The split
and geographic clustering are recomputed; this is not plot subsampling.
All adjustments are automatic Python decisions recorded in metadata.

## Independent magnitude arguments upgrade

`forecast_magnitudes.py` resolves and validates separate training/validation
thresholds for energy and location, plus two independent validation floors.
The Python CLI and Bash wrapper expose explicit arguments and save the resolved
overrides before freezing a new run. Builders use the values in event selection
and training/refit target construction; maps and energy history plots display
the corresponding thresholds. Legacy aliases still work. Tests verify CLI
persistence, invalid catalog coverage rejection, energy validation events excluded
from higher-threshold refit labels, and lower-magnitude location validation
without admitting those events to location training. Existing frozen World and
Japan studies are unchanged by this maintained-source upgrade.
