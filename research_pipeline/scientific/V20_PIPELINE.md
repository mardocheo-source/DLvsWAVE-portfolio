# V20 time connection finder

V20 is a special, parameter-driven experiment that classifies the Japan
Standard Time band of a trusted Japan-region M≥7.9 event from same-day NASA/JPL
Horizons fields.  It never replaces an event timestamp with the start of a
90-day interval.

The four target bands are 00:00–05:59, 06:00–11:59, 12:00–17:59 and
18:00–23:59 JST.  Historical conventional-midnight records and worldwide
non-Japan hard-negative rows are excluded.  Event feature epochs are the
centres of the observed bands.  Future compatibility is sampled at all four
band centres on every day; 90-day windows only group the output.

The optional `report.historical_forecast_comparison` object can reproduce a
previous timing forecast from its CSV and annotate its highest-ranked interval
with the V20 band belonging to the configured containing forecast slot. The
source label, source report page, temporal resolution, column names, matching
policy, input CSVs and output artifacts are configuration values; the renderer
does not hard-code the comparison study. Multiple time-band forecast sources
can be listed; the current V20 comparison reports both the sequential-weighted
and independent one-shot estimates with their validation metrics.

Reproduce an existing downloaded master and model run with:

```bash
./.venv/bin/python research_pipeline/scientific/run_v20.py \
  --project-dir DB/japan-m79plus-eventtime-6h-connection-v20 \
  --reuse-master --reuse-model
```

Every render records its issue datetime in the configured report timezone on
the cover, page footers, Markdown companion and JSON manifest. Pass
`--issued-at 2026-08-03T08:00:00+09:00` to reproduce a specific report edition;
otherwise the renderer uses the current time in `report.issue_timezone`.

Omit `--reuse-master` to retrieve JPL Horizons vectors again.  Omit
`--reuse-model` to repeat feature selection, the 21-candidate hyperparameter
screen, nested sequential validation, one-shot validation, randomized-label
null control, and both conditional forecasts.

This is an association experiment, not an earthquake-occurrence model.
