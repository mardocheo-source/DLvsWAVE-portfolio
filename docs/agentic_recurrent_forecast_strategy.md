# Agentic Recurrent Forecast Strategy

Concept note for a future DLvsWAVE branch that performs sequential, agent-guided
forecast refinement across geography, magnitude thresholds, and temporal
resolution.

## Goal

Build a recurrent forecast loop where a small local decision model, for example
Gemma or Microsoft Phi, helps decide whether the next forecast iteration should:

- split the geographic area by longitude,
- split the geographic area by latitude,
- lower the earthquake magnitude threshold to add contextual non-mega events,
- increase/decrease temporal resolution,
- stop because the forecast is already sufficiently localized and stable.

The model is not the forecaster. It is a decision assistant that proposes the
next experiment. DLvsWAVE remains responsible for master generation, validation,
forecasting, scoring, and anti-leakage constraints.

## Core Idea

Start from a broad region, such as Japan/Nankai, then run a forecast at a coarse
or medium resolution. If the result is broad, unstable, or conflicting, create
child experiments that partition the problem.

Example sequence:

1. Run whole-region forecast.
2. Compare vertical vs horizontal auto-clip.
3. Compare validation variants or KAN/LCS/hybrid families.
4. Ask the decision agent whether uncertainty is more spatial, temporal, or data
   density related.
5. If spatial, split the region by longitude or latitude.
6. If data density is too low, download lower-magnitude earthquake context but
   preserve the target definition for megaquake positives.
7. Run child forecasts.
8. Fuse child results only after validation quality checks.
9. Recurse until a stopping condition is reached.

## Decision Agent Role

The agent receives compact, structured summaries, not raw giant CSVs.

Inputs:

- region bounds: latitude min/max, longitude min/max,
- target threshold, e.g. M8+,
- context threshold, e.g. M7+ or M6.5+ if available,
- master manifest,
- validation metrics,
- false positive/false negative summary,
- forecast window candidates,
- vertical/horizontal clip report,
- source forecast disagreement,
- runtime and memory budget.

Outputs:

- `action`: `split_lon`, `split_lat`, `lower_mag_context`, `increase_resolution`,
  `decrease_resolution`, `rerun_same`, or `stop`,
- `reason`,
- proposed child regions,
- proposed magnitude threshold for context records,
- confidence,
- required safeguards.

Important: the agent output is advisory. A deterministic policy layer validates
and can reject it.

## Sequential Splitting

The system should maintain a tree of experiments.

Each node contains:

- region bounds,
- time resolution,
- target magnitude threshold,
- context magnitude threshold,
- parent experiment id,
- forecast window,
- validation strategy,
- master path,
- train run paths,
- final consensus artifacts,
- decision summary.

A child node is created only when:

- parent validation is not degenerate,
- forecast confidence is non-flat,
- forecast disagreement suggests localization is useful,
- there is enough historical/context data to train meaningfully,
- runtime budget allows it.

## Split Axis Heuristics

Prefer longitude split when:

- forecast peaks differ east/west,
- candidate source regions span the Pacific trench vs inland Japan,
- false positives cluster in different longitude bands,
- Nankai vs Tohoku-like signatures appear mixed.

Prefer latitude split when:

- forecast peaks differ north/south,
- recent false positives are northern Japan while target is Nankai-like,
- event density is elongated along Honshu,
- validation successes/failures separate by latitude.

Prefer magnitude-context expansion when:

- M8+ positives are too few,
- validation has too many false positives,
- the model cannot learn quiet/non-target years,
- lower magnitude events can act as negative or weak-context anchors without
  becoming target positives.

## Lower-Magnitude Context Strategy

The master may include additional earthquakes below target magnitude, but target
labels must remain strict.

Example:

- target positive: Japan-region M8+ only,
- context records: Japan-region M7.0+ or M7.5+,
- optional negative anchors: global M8+ outside Japan inserted with `mag=0`
  or `target=0`, depending on master schema,
- forecast target remains M8+ Japan/Nankai-like.

The pipeline should avoid silently changing the target meaning. Context
earthquakes improve feature coverage; they do not redefine success.

## Anti-Leakage Rules

The agent must never see future labels for the forecast window.

Required safeguards:

- freeze forecast start/end before any split decision,
- keep forecast rows unshuffled,
- train data must end before forecast fit boundary,
- validation windows must be before forecast window,
- random/reverse variants must preserve forecast row order,
- any lower-magnitude download must use catalog dates available before the
  simulated forecast cutoff when running historical validation,
- decision agent receives only summaries produced after valid splits.

## Scoring and Stop Conditions

Stop when at least one of these is true:

- vertical/horizontal consensus agrees on a narrow high-risk window,
- child splits do not improve validation quality,
- forecast becomes flat or all-positive,
- too few historical/context records remain,
- max depth reached,
- runtime budget exhausted,
- spatial split produces unstable contradictory child forecasts.

Suggested metrics:

- validation F1,
- recall,
- precision,
- balanced accuracy,
- false positive count,
- forecast peak sharpness,
- forecast consensus fraction,
- vertical/horizontal agreement,
- parent-child forecast consistency,
- runtime cost.

## Suggested Directory Layout

```text
agentic_runs/
  japan_nankai_agentic_<timestamp>/
    plan.json
    root/
      master/
      train_vertical/
      train_horizontal/
      comparison/
      decision.json
    child_lon_west/
    child_lon_east/
    child_lat_south/
    child_lat_north/
    final_consensus/
```

## Decision JSON Schema

```json
{
  "node_id": "root",
  "action": "split_lon",
  "reason": "Forecast disagreement is stronger east/west than north/south.",
  "confidence": 0.72,
  "proposed_children": [
    {
      "id": "lon_west",
      "lat_min": 28.0,
      "lat_max": 44.0,
      "lon_min": 128.0,
      "lon_max": 137.5
    },
    {
      "id": "lon_east",
      "lat_min": 28.0,
      "lat_max": 44.0,
      "lon_min": 137.5,
      "lon_max": 147.0
    }
  ],
  "context_magnitude_threshold": 7.0,
  "safeguards": [
    "forecast rows remain unshuffled",
    "target remains M8+ in Japan/Nankai region",
    "validation ends before forecast fit boundary"
  ]
}
```

## Implementation Phases

Phase 1: deterministic orchestrator only.

- Run root vertical/horizontal experiments.
- Produce summaries.
- Use fixed heuristic split decisions.

Phase 2: decision-agent proposal.

- Add local Gemma/Phi call.
- Require JSON output.
- Validate output with deterministic policy.

Phase 3: recurrent tree.

- Permit depth 2 or 3.
- Compare children to parent.
- Generate final spatial-temporal consensus.

Phase 4: learning from runs.

- Store decisions, outcomes, and rejected proposals.
- Use them as examples for future decision prompts.

## Practical Starting Point

For the current Japan/Nankai work, the first useful branch should support:

- root region: lat `28..44`, lon `128..147`,
- target: M8+ in Japan region,
- optional context: M7+ in same region,
- optional negative anchors: M8+ outside Japan,
- resolution ladder: 360d -> 30d -> 7d -> 3d,
- split candidates: longitude split first, then latitude if needed,
- final comparison: vertical/horizontal auto-clip plus child-region consensus.

