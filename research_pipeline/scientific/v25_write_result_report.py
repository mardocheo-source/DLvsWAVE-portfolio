#!/usr/bin/env python3
"""Write the compact, gate-first V25 result report from audited artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def yn(value: bool) -> str:
    return "sì" if bool(value) else "no"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", required=True)
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    results = project / "05_results"
    summary = json.loads((results / "summary.json").read_text())
    verification = json.loads((project / "02_audit/final_verification.json").read_text())
    timing = pd.read_csv(results / "timing_ensemble_fold_metrics.csv")
    location_rows = pd.read_csv(results / "location_frozen_audit_ensemble.csv")
    ablations = pd.read_csv(results / "final_body_field_ablation_summary.csv")
    eclipse_audit = json.loads((project / "02_audit/eclipse_feature_audit.json").read_text())

    timing_summary = summary["timing"]
    location = summary["location_conditional_on_timing_peak"]
    selected = summary["search"]["final_selected_features"]
    selected_eclipse = [name for name in selected if name.startswith("eclipse:")]

    timing_lines = [
        f"| {row.event_slot} | {int(row.argmax_offset_slots):+d} | {yn(row.exact_peak)} | {row.event_percentile:.3f} | {row.quality:.3f} |"
        for row in timing.itertuples(index=False)
    ]
    location_lines = [
        f"| {row.event_slot} | {row.error_km:.0f} | {yn(row.zone_hit)} | {row.recency_baseline_error_km:.0f} |"
        for row in location_rows.itertuples(index=False)
    ]

    def ablation_table(dimension: str) -> str:
        frame = ablations.loc[ablations.dimension.eq(dimension)].sort_values("best_screen_objective", ascending=False)
        return "\n".join(
            f"| {row.value} | {int(row.trial_count)} | {row.best_screen_objective:.3f} | {row.median_screen_objective:.3f} |"
            for row in frame.itertuples(index=False)
        )

    report = f"""# V25 deep-history + eclipse — risultato finale

## Esito

**Non validato.** Gate temporale `{timing_summary['gate_status']}`; gate location `{location['gate_status']}`. Il `PASS` del verifier indica soltanto coerenza di dati, epoche, split e artefatti, non accuratezza predittiva.

Output grezzo da non promuovere a previsione operativa:

- settimana con score massimo: **{timing_summary['peak_slot_start_jst']} – {timing_summary['peak_slot_end_jst']} JST**, score empirico {timing_summary['peak_ensemble_score']:.3f} (non probabilità);
- zona condizionata a quel massimo: **{location['most_likely_zone']}**, {location['estimated_latitude']:.3f} N, {location['estimated_longitude']:.3f} E;
- raggio CV80 stimato: {location['uncertainty_radius_km']:.0f} km.

## Validazione temporale frozen

| evento | offset massimo (settimane) | esatto | percentile evento | qualità |
|---|---:|---:|---:|---:|
{chr(10).join(timing_lines)}

Exact rate: **{timing_summary['validation_exact_rate']:.0%}**; within-one: **{timing_summary['validation_within_one_rate']:.0%}**; percentile medio {timing_summary['validation_mean_event_percentile']:.3f}; qualità media {timing_summary['validation_mean_quality']:.3f}. Il training non è stato azzerato (quality {timing_summary['training_metrics']['quality']:.3f}), ma non generalizza ai picchi frozen. Il gate p90 sui hard-negative mondiali {'è passato' if timing_summary['gate_checks']['hard_negative_p90_below_0_85'] else 'è fallito'}.

## Validazione location sugli stessi eventi

| evento | errore km | zona corretta | baseline recency km |
|---|---:|---:|---:|
{chr(10).join(location_lines)}

Mediana {location['audit_median_error_km']:.0f} km; q80 {location['audit_q80_error_km']:.0f} km; zone-hit {location['audit_zone_hit_rate']:.0%}; peggioramento rispetto alla baseline recency {abs(location['audit_median_error_improvement_vs_recency_baseline']):.1%}.

## Dati ed epoche

- 15 eventi indipendenti di timing: 4 storici timing-only e 11 con coordinate osservate.
- Fit outer con 12, 13 e 14 positivi; fit prospettico con 15 positivi e {timing_summary['final_fit_counts']['train_negative_row_count']} righe negative.
- 1.339 settimane sparse dal 1611 al 2026; cutoff esclusivo `2026-08-01 00:00 JST`; zero osservazioni sismiche di agosto usate.
- 11 corpi JPL primari, 176 campi, errore massimo di allineamento epoch zero giorni.
- {len(eclipse_audit['feature_columns'])} colonne eclissi Swiss Ephemeris; una sola settimana-evento su 15 contiene un’eclissi globale.
- Verifier di pipeline: `{verification['status']}`.

## Ablation corpi

| gruppo | trial | best objective | median objective |
|---|---:|---:|---:|
{ablation_table('body_group')}

## Ablation campi/eclissi

| gruppo | trial | best objective | median objective |
|---|---:|---:|---:|
{ablation_table('field_group')}

`eclipse_only` è il gruppo peggiore per best objective. Il modello finale ha selezionato {len(selected_eclipse)} feature eclissi su {len(selected)} feature totali: {', '.join(f'`{name}`' for name in selected_eclipse) if selected_eclipse else 'nessuna'}. Questo non dimostra una relazione fisica, soprattutto perché il segnale positivo same-week riguarda un solo evento storico.

## Limite di leakage

Ogni fold seleziona configurazione, feature e pesi soltanto da eventi precedenti. I tre eventi di reporting appartengono però alla linea di ricerca precedente: il test è nested e earlier-only all’interno di V25, ma non è un discovery holdout storicamente vergine.
"""
    (results / "V25_RESULT.md").write_text(report)
    print(results / "V25_RESULT.md")


if __name__ == "__main__":
    main()
