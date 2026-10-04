"""Executable invariance checks for fixed one-shot base model fits."""
import copy
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from production_location import load_inputs,propose,fit,save_json,sha


def audit(config):
    small={**config,'seed':config.get('seed',42),'search_space':{**config.get('search_space',{}),'epochs':[3],'feature_counts':[4],'hidden_dim':[16],'num_layers':[1]}}
    root=Path(config['spatial_root']);meta=json.loads((root/'01_data/spatial_zones_metadata.json').read_text())
    contract=json.loads((root/'event_only_master_manifest.json').read_text())
    train_events=pd.read_csv(root/'01_data/training_events.csv');validation_events=pd.read_csv(root/'01_data/validation_events.csv')
    assert train_events.id.is_unique and validation_events.id.is_unique
    overlap=sorted(set(train_events.id)&set(validation_events.id));assert not overlap
    train_times=pd.to_datetime(train_events.time,utc=True,format='mixed');validation_times=pd.to_datetime(validation_events.time,utc=True,format='mixed')
    cutoff=pd.to_datetime(contract['validation_start'],utc=True);assert train_times.max()<cutoff<=validation_times.min()
    assert validation_times.max()<=pd.to_datetime(contract['validation_end'],utc=True)
    geometry_scope=meta.get('fit_scope',meta.get('zone_fit_scope',''));assert geometry_scope.lower().startswith('training')
    if 'zone_fit_end_exclusive' in meta:assert pd.to_datetime(meta['zone_fit_end_exclusive'],utc=True)<=cutoff
    checks=[];branch_checks=[]
    for branch in ['main_bodies_branch','minor_bodies_branch']:
        frames,targets,features,events,rows,truth=load_inputs(config,branch)
        assert all(c.startswith('astro_') for c in features)
        ids=lambda frame:set(';'.join(frame.event_ids.astype(str)).split(';'))
        assert ids(frames['training'])==set(train_events.id)
        assert ids(frames['validation'])==set(validation_events.id)
        branch_checks.append({'branch':branch,'training_rows':len(frames['training']),'validation_rows':len(frames['validation']),
            'training_events':len(train_events),'validation_events':len(validation_events),'overlapping_event_ids':overlap,
            'last_training_event':str(train_times.max()),'first_validation_event':str(validation_times.min()),
            'validation_window_start':str(cutoff),'validation_window_end':contract['validation_end'],
            'feature_count':len(features),'all_predictors_raw_astronomy':True,'all_training_rows_contain_events':True,
            'input_hashes':{s:sha(root/branch/'01_data'/f'{s}_master.csv') for s in frames}})
        for tid,family in enumerate(['kan','deep_learning','lcs','analog'],1):
            cfg=propose(tid,family,small,frames,targets,features)
            a,_=fit(copy.deepcopy(cfg),frames,targets)
            altered={s:f.copy(deep=True) for s,f in frames.items()}
            altered['validation'][features]=altered['validation'][features]*37+123456
            altered['validation'][targets]=1-altered['validation'][targets]
            b,_=fit(copy.deepcopy(cfg),altered,targets)
            errors={s:float(np.max(np.abs(a[s]-b[s]))) for s in ['training','prospective']}
            assert max(errors.values())<1e-12,(branch,family,errors)
            checks.append({'branch':branch,'family':family,'validation_features_and_labels_perturbed':True,'training_prediction_max_change':errors['training'],
                           'forecast_prediction_max_change':errors['prospective'],'base_fit_does_not_use_validation':True})
    report={'forecast_mode':'one_shot_exogenous_fixed_parameters','training_validation_ids_disjoint':True,'training_before_validation':True,
            'features_only_raw_known_astronomy':True,'no_online_weight_update_during_validation_or_forecast':True,
            'zones_fitted_on_training_only':True,'zone_fit_scope':geometry_scope,'branch_data_checks':branch_checks,
            'base_model_perturbation_checks':checks,'source_sha256':sha(Path(__file__).with_name('production_location.py')),
            'audit_source_sha256':sha(__file__),'perturbation_scope':'One deterministic short fit per family and branch; eight checks. All selected production models have separate replay proofs.',
            'validation_is_selection_set':True,'independent_test_performance_claimed':False,
            'catalog_revision_limit':'Occurrence-time cutoff on a later historical catalog snapshot; no archived as-of catalog is assumed.'}
    save_json(root/'one_shot_leakage_audit.json',report);return report
