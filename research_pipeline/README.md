# Canonical research pipeline

This tracked source tree is the reusable implementation for new earthquake
timing and localization studies. Generated study artifacts remain under
`DB/<study>/`, but no executable source in this directory imports Python from
an earlier `DB` study.

## Layout

- `scientific/`: catalog construction, aligned JPL master preparation,
  hard-negative injection, compact-history search, feature ablation,
  LCS/KAN/deep/logistic/tree and hybrid training, metric-specialist fusion,
  fold-contextual reliability fusion, localization, controls, and artifact
  checks.
- `reporting/`: the parameter-driven professional report generator, renderer,
  peak-mode selector, narrative builder, workflow manifest, and time-scale
  utilities.
- `recipes/`: frozen study recipes or thin launch examples. Scientific and
  reporting logic must stay in the two canonical directories above.

## Running a study

The canonical orchestrator accepts the output project as a parameter; all
scientific and presentation settings are read from JSON. V15 has a dedicated
entry point but shares the implementation with the backward-compatible runner:

```bash
./.venv/bin/python research_pipeline/scientific/run_v15.py \
  --project-dir DB/japan-m83plus-180d-2026-2028-contextual-v15
```

When `contextual_fusion` is present in `pipeline_request.json`, every outer
fold independently selects a sparse model combination and a label-free shape
rule. Its fold-origin and all-history-refit forecasts are combined by audited
context reliability. An order-preserving record-shuffle series may contribute
only the configured bounded anchor share; target-label randomization remains a
zero-weight control. Search budgets, weak-peak rescue, smoothing, constraints,
projection shares and anchor candidates all come from the referenced JSON.

USGS downloads are reused by default. Add `--refresh-downloads` only when an
intentional data-snapshot refresh is required.

## Reuse rules

1. Put study-specific thresholds, cadence, holdouts, k-factor grids, hard
   negatives, model profiles, fusion gates, and report choices in JSON.
2. Do not embed an event, location, forecast date, or winner in report code.
3. Preserve chronological outer holdouts while screening master density and
   model capacity.
4. Keep non-target regional/world events auditable and outside astronomical
   feature columns; they may be down-weighted or sampled, but never silently
   relabeled as positive Japan events.
5. A report can describe a failed gate, but cannot promote it to a qualified
   forecast.

Run `verify_source_tree.py` to ensure the canonical sources compile and contain
no executable dependency on a historical `DB` pipeline.
