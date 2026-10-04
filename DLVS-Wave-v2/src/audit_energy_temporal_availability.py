"""Audit original energy projection and seismic-lag input availability."""
from pathlib import Path
import argparse,json,re
import pandas as pd
from production_location import save_json,save_csv,sha


def audit(root):
    root=Path(root);energy=root/'01_energy_forecast_m77';records=[];details=[]
    for branch in ['main_bodies_branch','minor_bodies_branch']:
        for stage,table in [('03_level1_fusion','02_level1/trials_all_models.csv'),('04_level2_deep_meta_optimizer/level2_fusion','04_level2_deep_meta_optimizer/meta_trials_level2.csv')]:
            manifest=json.loads((energy/branch/stage/'compound_fusion_manifest.json').read_text());trials=pd.read_csv(energy/branch/table,low_memory=False)
            for family,tid in zip(manifest['candidate_models'],manifest['candidate_trials']):
                selected=trials.loc[trials.network_type.eq(family)&trials.trial_id.eq(tid)];assert len(selected)==1;row=selected.iloc[0]
                shift=row.get('hp__temporal_projection_shift_weeks',0);shift=int(shift) if pd.notna(shift) else 0
                features=[c.removeprefix('feat__') for c in trials if c.startswith('feat__seis_') and pd.notna(row[c]) and float(row[c])==1]
                future=[]
                for field in features:
                    match=re.search(r'_shift_m(\d+)d$',field)
                    if not match:raise ValueError('Unknown old lag naming')
                    lag_rows=int(match[1]);offset=-shift-lag_rows
                    detail={'branch':branch,'stage':stage,'family':family,'trial_id':int(tid),'feature':field,
                            'projection_weeks':shift,'actual_seismic_lag_weeks':lag_rows,'source_week_relative_to_prediction':offset,
                            'source_week_after_prediction_week':offset>0}
                    details.append(detail)
                    if offset>0:future.append(detail)
                records.append({'branch':branch,'stage':stage,'family':family,'trial_id':int(tid),'projection_weeks':shift,'seismic_feature_count':len(features),
                                'future_seismic_week_dependencies':future,'affected':bool(future),'fusion_calibration':manifest['calibration']})
    out=root/'00_reproduction_audit';out.mkdir(parents=True,exist_ok=True)
    save_csv(out/'energy_temporal_feature_dependencies.csv',pd.DataFrame(details))
    result={'scope':'Selected initial/refined production energy candidates feeding final hierarchical fusion',
            'old_seismic_lag_semantics':'m7d...m35d are 7...35 weekly rows in the frozen raw master, verified separately against unshifted raw fields.',
            'projection_semantics':'For target week t and projection shift s, shifted output reads the model input at t-s. A seismic field with actual lag d weekly rows reads observations from t-s-d.',
            'selected_candidates':len(records),'candidates_with_future_seismic_week_dependencies':sum(r['affected'] for r in records),
            'no_lookahead_certification':False,'candidate_records':records,
            'training_normalization_scope':'The restored master builder fits min-max/bit quantiles before 2003-06-23; this check concerns inference availability, not direct validation-row fitting.',
            'one_shot_classification':'Original energy weights are fixed, but lagged seismic inputs vary across historical validation dates. Some negative projection shifts additionally read observations after the predicted week. It is not a certified strict one-shot or causal rolling-origin validation.',
            'forecast_cutoff_limit':'The old raw master zero-fills seismic observations after its cutoff. Absence of recorded future observations is not a forecast of those input values.',
            'strict_location_policy':'New location uses only exogenous astronomical inputs, true calendar shifts, training-only zones/scalers and no seismic feature fields.',
            'source_sha256':sha(__file__)}
    save_json(out/'energy_temporal_availability_audit.json',result)
    affected=[r for r in records if r['affected']]
    lines=['# Original energy inference-availability audit','',
           f"{len(affected)} of {len(records)} selected initial/refined candidates contain seismic dependencies from weeks after the predicted week.",'',
           'This is separate from deliberate validation-based model selection. The restored scaler and model training exclude validation rows, but that alone does not establish causal input availability at inference.','',
           'Example: a -12-week signal projection combined with the frozen m7d field (actually a 7-week lag) reads a seismic input from five weeks after the displayed prediction date. The selected main initial KAN trial 448 has this combination. Its stage uses nonzero weighted-mean peak/calm fusion, so it is not an unused diagnostic trial.','',
           'The exact historical energy replica remains intact for comparison. Its perfect selected corridor plot must not be presented as proof of a leakage-free prospective forecasting protocol. New one-shot location excludes seismic predictors. The worldwide generalized energy runner also uses raw astronomical predictors and fits normalization inside each training subset.','',
           'Evidence: energy_temporal_availability_audit.json; energy_temporal_feature_dependencies.csv; seismic_lag_calendar_audit.json.']
    (out/'ENERGY_TEMPORAL_AVAILABILITY_REVIEW.md').write_text('\n'.join(lines)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();r=audit(a.root);print({k:r[k] for k in ['selected_candidates','candidates_with_future_seismic_week_dependencies','no_lookahead_certification']})
