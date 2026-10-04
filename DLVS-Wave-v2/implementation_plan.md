# DLVS-Wave Phase 2 Deep Meta-Optimizer

## Goal

Refine the completed Phase 1 Optuna trials for KAN, Deep Learning, and LCS with a shared neural surrogate, while retaining the exact Phase 1 parameter domains and evaluation objective.

## Implemented pipeline

1. Read and validate successful Phase 1 trials (`objective_loss < 500` and finite multi-objective metrics).
2. Project model and pretreatment parameters into a normalized latent space with exact typed decoding.
3. Standardize the four learned targets: objective loss, validation MSE, validation F1, and validation depression MAE.
4. Train a residual multi-head surrogate with MC Dropout and an inverse conditional generator.
5. Propose unseen candidates from conditional generation, differentiable Expected Improvement, local perturbation, and random fallback.
6. Evaluate each candidate through `MasterPretreatmentEngine` and the selected real forecasting model.
7. Persist every success or failure atomically to `meta_trials_<model>.csv`; resume without reevaluating known configurations.
8. Write the Phase 2 best parameters/metrics/validation series plus machine-readable and Markdown Phase 1-versus-Phase 2 reports.
9. Render a comparison chart covering convergence, distributions, MSE/F1 trade-off, and winner deltas.
10. Refit the selected winner and create a nested, self-contained validation/forecast/report subset. `--selection-policy phase2` deliberately finalizes the best second-level candidate even when Phase 1 scored better; `overall` retains the lower objective.
11. Optionally merge the three finalized subsets with `--make-ensemble`, emitting classic and stage-dependent temporal ensembles.
12. Use vertical ISO date ticks and label forecast local maxima at their vertices with dedicated Y-axis headroom.

## Validation contract

The Phase 2 objective intentionally matches Phase 1:

`0.5 × validation MSE + 4 × (1 − validation F1) + 0.5 × validation depression MAE`

This comparison reuses the Phase 1 selection-validation protocol. It can rank search methods but is not an unbiased estimate of future generalization. The chosen configuration must subsequently be confirmed on a later, untouched temporal holdout before it is presented as validated forecasting performance.

## Reproducibility and compute

- Seeded NumPy and PyTorch proposal/evaluation paths.
- Explicit requested and actual compute devices in every trial record and report.
- CPU is the default and can be forced with `--device cpu`.
- `--max-meta-trials`, surrogate/model epoch controls, and timeout make smoke tests and production runs independently configurable.
- The local study launchers default to 2,400 seconds each, including reserved finalization time; three sequential runs therefore have a combined 7,200-second budget.
- The finalized launcher accepts only `--device cpu`, so it cannot accidentally acquire the occupied XPU.

## Example

```bash
python src/run_deep_meta_optimizer.py \
  --input-trials-csv studies_output/optuna_study_japan_7d_m69_2h/study_lcs/optuna_trials_lcs.csv \
  --input-master tests_env/multi_country_century_tests/loc1_japan_tohoku_1900_2030/master_7d_summarized_packed_16bit.csv \
  --model-type lcs \
  --device cpu \
  --timeout-seconds 600 \
  --output-dir studies_output/optuna_study_japan_7d_m69_2h/study_lcs/phase2_deep_meta_opt
```

For a complete selected subset, use the local `run_phase2_<model>.sh` scripts. After all three complete, use `ensemble/run_phase2_ensemble.sh` with explicit KAN, deep-learning, LCS and output directories. Each study directory contains its own `PHASE2_README.md`.
