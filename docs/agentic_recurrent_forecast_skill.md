# Skill: Agentic Recurrent Forecast Planning

Use this abstract skill in a future branch when asked to build or extend an
agentic forecast loop for DLvsWAVE.

## Purpose

Guide sequential forecast refinement using a small local decision model
(Gemma/Phi-class) plus deterministic safety checks.

The goal is not to let the language model predict earthquakes. The goal is to
let it choose the next experiment: split by longitude, split by latitude, lower
context magnitude, change resolution, rerun, or stop.

## Inputs

Required:

- root region bounds,
- target magnitude and target geographic rule,
- forecast window,
- available event catalog path or downloader command,
- available ephemeris/master builder,
- runtime budget,
- maximum recursion depth.

Optional:

- prior forecast common-window CSV/JSON,
- vertical/horizontal auto-clip reports,
- validation lineage metrics,
- false-positive summary,
- user-provided trusted forecast windows.

## Workflow

1. Define the root node.
2. Build or reuse a master for the node.
3. Run vertical and horizontal auto-clip forecasts.
4. Generate common-window and lineage validation artifacts.
5. Summarize the node into a compact decision packet.
6. Ask the decision agent for the next action.
7. Validate the agent proposal with deterministic rules.
8. Create child nodes if accepted.
9. Run children sequentially or in bounded parallel.
10. Fuse child outputs only after validation quality checks.
11. Stop when confidence, budget, or data sufficiency rules say so.

## Decision Packet

The packet given to the decision model should be concise JSON:

```json
{
  "node": {
    "id": "root",
    "lat_min": 28.0,
    "lat_max": 44.0,
    "lon_min": 128.0,
    "lon_max": 147.0,
    "resolution_days": 30,
    "target_magnitude": 8.0,
    "context_magnitude": null
  },
  "validation": {
    "f1": 0.66,
    "recall": 1.0,
    "precision": 0.5,
    "balanced_accuracy": 0.875,
    "false_positive_count": 1,
    "false_negative_count": 0
  },
  "forecast": {
    "highest_window_start": "2026-08-07",
    "highest_window_end": "2026-08-10",
    "risk_mean": 0.77,
    "risk_max": 0.88,
    "consensus": "2/2",
    "is_flat": false
  },
  "disagreement": {
    "vertical_horizontal": "moderate",
    "axis_hint": "unknown"
  },
  "budget": {
    "max_depth": 2,
    "current_depth": 0,
    "remaining_hours": 6
  }
}
```

## Expected Agent Output

Require strict JSON:

```json
{
  "action": "split_lon",
  "confidence": 0.72,
  "reason": "East/west ambiguity is more plausible than north/south ambiguity.",
  "children": [
    {
      "id": "west",
      "lat_min": 28.0,
      "lat_max": 44.0,
      "lon_min": 128.0,
      "lon_max": 137.5
    },
    {
      "id": "east",
      "lat_min": 28.0,
      "lat_max": 44.0,
      "lon_min": 137.5,
      "lon_max": 147.0
    }
  ],
  "context_magnitude": 7.0,
  "resolution_days": 7,
  "safeguards": [
    "target remains M8+ Japan-region only",
    "forecast rows are not shuffled",
    "validation is before forecast"
  ]
}
```

## Deterministic Acceptance Rules

Reject the proposal if:

- child bounds do not cover the parent region,
- child bounds overlap too much without reason,
- child event count is too low,
- target definition changes,
- forecast window changes without explicit user approval,
- validation would include forecast rows,
- proposed context magnitude creates too many rows for the runtime budget,
- proposed recursion depth exceeds limit.

Prefer lowering context magnitude only when:

- target positives are too sparse,
- false positives are high,
- validation windows have too few negatives,
- the catalog can be filtered without leakage.

Prefer stopping when:

- vertical/horizontal overlap is narrow and high strength,
- children do not improve validation,
- forecast is flat/high everywhere,
- historical records are insufficient.

## Implementation Notes

Do not start by adding a complex autonomous agent. Start with a deterministic
orchestrator and a mocked decision JSON.

Recommended files for a future branch:

```text
agentic_forecast/
  orchestrator.py
  node.py
  decision_agent.py
  decision_policy.py
  catalog_context.py
  spatial_split.py
  run_registry.py
  prompts/
    gemma_phi_decision_prompt.md
  schemas/
    decision_packet.schema.json
    decision_response.schema.json
commands/
  run_agentic_japan_nankai_forecast.sh
```

## Prompt Template

```text
You are not forecasting earthquakes directly.
You choose the next experiment for a DLvsWAVE forecasting pipeline.

Given the node summary JSON, choose one action:
- split_lon
- split_lat
- lower_mag_context
- increase_resolution
- decrease_resolution
- rerun_same
- stop

Return strict JSON only.
Do not change the target definition.
Do not move the forecast window.
Do not use future labels.
Explain the reason in one short sentence.
```

## First Milestone

Build a non-agentic dry run:

1. Root node: Japan/Nankai.
2. Run vertical/horizontal auto-clip.
3. Produce comparison and validation quality report.
4. Hard-code one longitude split.
5. Run both children.
6. Compare parent vs children.
7. Only then add Gemma/Phi decision proposals.

