# V18 reusable scientific pipeline

`run_v18.py` is the public entry point. Study choices live in the project's
`00_config/pipeline_request.json`; region projects do not require edits to the
Python sources.

```bash
./.venv/bin/python research_pipeline/scientific/run_v18.py \
  --project-dir DB/<project>
```

## Interval operators

`interval_features` controls the fine Horizons cadence and the fields that are
summarized inside each target interval:

- `source_step_days`: fine-grid cadence;
- `start_date`: first aligned historical interval;
- `operators`: any ordered subset of `min`, `median`, `max`, `mean`;
- `ephemerides`: selected ephemeris field names, or `*`;
- `bodies`: selected body identifiers, or `*`.

The original interval-start values remain `op:val`. Aggregate features have the
same structured name with their own operator, for example `op:median`. Every
window uses samples inside `[start, start + interval_days)` only.

## Raw and quantile preprocessing

`preprocessing.quantile_bins` enables empirical ordinal quantization. Four bins
emit exactly `0`, `1/3`, `2/3`, and `1`. Cut points are fitted independently on
the training rows of every chronological fold, then applied unchanged to that
fold's validation and forecast rows. The same rule is used during compact-master
search, feature ranking/ablation, model screening, final timing training,
historical controls, and localization.

Set `quantile_bins` to `0` to preserve continuous astronomical values. Models
may still fit their scaler exclusively on each training fold; no ordinal
quantization is applied to validation or forecast rows.

## Validation identity and controls

`timing.validation_slots` identifies the exact outer holdout bin for every
fold. If another genuine earthquake falls inside the same diagnostic
neighbourhood it remains visible, but is neither substituted for the designated
holdout nor counted as a false-positive competitor. The exported contextual
validation table records this identity in `designated_holdout`.

The catalogue discovery floor, timing-training floor, timing-validation floor
and location-validation floor are independent parameters. In this Japan run,
timing training and its two configured outer holdouts use M≥7.9, while the five
location holdouts may use M≥7.5. Likewise,
non-Japan hard negatives have separate training and validation magnitude floors.
This lets a lower-magnitude event test generalization without silently changing
the training target definition.

`compact_search.event_radius` controls the local validation context. V18 uses
two 90-day neighbours on either side, preserving the ±180-day context of the
earlier 180-day study while doubling temporal resolution.

## Offset grid

The project records both a reference anchor and a modulo offset. The V18 grid
uses 90-day bins anchored at 2025-09-18; relative to the V17 anchor 2025-10-03,
the phase difference is `75 mod 90` days. The offset is therefore independently
auditable and the resulting bins overlap the older 180-day windows.

Configured worldwide non-region events retain their catalogue identity only in
the audit columns. Their model-facing target, magnitude and coordinates are
neutral zero values. Target-label randomization is a separate null control and
always has zero promoted-forecast weight; intact-record order shuffling may be
used only as a bounded stability anchor.

## Safe continuation

Long stages can be retained while regenerating downstream diagnostics and the
report. The runner accepts `--reuse-compact-search`,
`--reuse-hyperparameter-screen`, `--reuse-timing-final`,
`--reuse-metric-fusion`, `--reuse-randomized-timing`,
`--reuse-historical-shuffle`, and `--reuse-contextual-fusion`. Each flag is
honoured only when every required non-empty artifact for that stage exists.
`--reuse-location` similarly retains the complete sequential, randomized and
finalized localization bundle.

## Reproducibility artifacts

The run persists:

- interval-operator provenance in `02_audit/interval_feature_operators.json`;
- all compact `k` trials in `02_master_search/compact_k_factor_trials.csv`;
- all family-parameter trials in
  `03_feature_research/model_parameter_screen_trials.csv`;
- promoted model overrides in
  `03_feature_research/selected_model_overrides.json`;
- measured family and hybrid runtimes in `03_feature_research/` and the final
  report;
- the full workflow and report data trace under `00_config/`.

Scores are experimental relative ranks, not calibrated earthquake
probabilities.
