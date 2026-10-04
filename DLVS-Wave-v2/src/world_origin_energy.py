"""Japan-style origin-specific energy fits, restricted to astronomical inputs.

Opt in with energy_protocol="origin_refit_astro_only". The legacy World fitter
remains available when the option is absent. Reuse the Japan fitting/sampling
functions, not its regional data, dates or existing trained models. Every
validation corridor has a prior-only training context. A separate forecast
context ends at the catalog cutoff, even when a child zoom starts months later.
Targets describe earthquake occurrence; they are never selectable predictors.
No past/future seismic fields or foreign-earthquake hard negatives are supplied.
"""
from dataclasses import asdict
from pathlib import Path
import argparse
import copy
import json
import logging

import numpy as np
import pandas as pd
import torch

import production_energy as engine
import causal_japan_energy as origin_model
from production_location import save_json, save_csv, sha
from src.compression import BitPackingConfig, QuantizedBitPacker

PROTOCOL = 'origin_refit_astro_only'


def prepare(events, astronomy, node_dir, config):
    """Build independent quantizers and dated training/prediction contexts.

    The forecast codebook can use later pre-issue history than the validation
    codebooks. It cannot change the earlier validation predictions. A partial
    terminal week is retained with its exact observed fraction, never completed
    with assumed future calm. All context metadata and field lineage are saved.
    """
    from production_geography import energy_contract
    out=Path(node_dir)/'01_energy_forecast';out.mkdir(parents=True,exist_ok=True)
    cutoff=pd.Timestamp(config['catalog_cutoff']).tz_localize(None)
    events=events.loc[pd.to_datetime(events.time)<=cutoff].copy()
    contract,val=energy_contract(events,config)
    contexts=[]
    for number,g in val.groupby('event_number',sort=True):
        contexts.append((f'validation_{number}',pd.Timestamp(g.date.min()),g.reset_index(drop=True)))
    first=next(iter(astronomy.values()))
    future_dates=pd.to_datetime(first.date)
    future_dates=future_dates[future_dates.between(config['forecast_start'],config['forecast_end'])]
    if not len(future_dates):raise ValueError('empty_origin_forecast_horizon')
    if cutoff>=future_dates.min():raise ValueError('catalog_cutoff_must_precede_forecast')
    contexts.append(('forecast',cutoff,pd.DataFrame({'date':future_dates.to_numpy()})))
    contract.update(energy_protocol=PROTOCOL,forecast_issue=str(cutoff),
        protocol='Separate prior-only validation origins; separate pre-forecast refit; fixed one-shot within each horizon',
        seismic_input_policy='No seismic predictors or hard-negative event indices; astronomical predictors only',
        target_tail_policy='Observed terminal weeks retained; partial issue week is not filled beyond cutoff',
        infill_seed_mode=config.get('infill_seed_mode','pi_pairs'),pi_pair_offset=config.get('pi_pair_offset',0),
        terminal_infill='all_observed',bitwise='Training-only astronomical codebook rebuilt independently per origin')
    save_json(out/'data_contract.json',contract);save_csv(out/'events.csv',events)
    for branch,astro in astronomy.items():
        base=astro.copy();base['date']=pd.to_datetime(base.date)
        if base.date.duplicated().any():raise ValueError('duplicate_astronomy_dates')
        features=[c for c in base if c.startswith('astro_')]
        if not features:raise ValueError('missing_astronomical_energy_features')
        base=base[['date']+features].set_index('date').sort_index()
        if not np.isfinite(base.to_numpy()).all():raise ValueError('nonfinite_astronomical_energy_features')
        data=out/branch/'01_data';data.mkdir(parents=True,exist_ok=True);metadata={}
        for name,issue,pred in contexts:
            train_dates=base.index[(base.index>=pd.Timestamp(config['training_start']))&(base.index<issue)]
            dates=train_dates.append(pd.DatetimeIndex(pred.date));frame=base.reindex(dates).reset_index(names='date')
            if frame[features].isna().any().any():raise ValueError('missing_origin_astronomy_coverage')
            visible=events.loc[(pd.to_datetime(events.time)<issue)&events.mag.ge(contract['training_magnitude'])]
            positive=set(pd.to_datetime(visible.date))
            n=len(train_dates);frame['event_target']=[int(d in positive) if d<issue else np.nan for d in dates]
            if name!='forecast':
                frame.loc[n:,'event_target']=pred.event_target.to_numpy()
                frame.loc[n:,'event_number']=pred.event_number.to_numpy()
                frame.loc[n:,'relative_week']=pred.relative_week.to_numpy()
            # Required by the shared Japan sampler, always false and never a feature.
            frame['is_world_hard_negative']=0
            frame['observed_target_days']=[min(7.,max(0.,(issue-d).total_seconds()/86400)) for d in dates]
            packer=QuantizedBitPacker(BitPackingConfig(prune_zero_variance=False))
            packed,codebook=packer.pack(frame[['date']+features],feature_cols=features,fit_mask=np.arange(len(frame))<n)
            packed_fields=[c for c in packed if c.startswith('packed_')]
            frame=pd.concat([frame,packed[packed_fields].reset_index(drop=True)],axis=1)
            context=data/name;context.mkdir(exist_ok=True)
            training=frame.iloc[:n].drop(columns=['event_number','relative_week'],errors='ignore').copy()
            prediction=frame.iloc[n:].copy()
            save_csv(context/'training.csv',training);save_csv(context/'prediction.csv',prediction)
            save_json(context/'bitwise_codebook.json',asdict(codebook))
            metadata[name]={'issue_time':str(issue),'training_last_week':str(training.date.max()),'training_rows':len(training),
                'training_event_weeks':int(training.event_target.sum()),'predict_rows':len(prediction),
                'quantization_fit_end':codebook.quantile_fit_end_date,
                'partial_terminal_target_intervals':training.loc[training.observed_target_days.lt(7),['date','observed_target_days','event_target']].astype(str).to_dict('records'),
                'training_sha256':sha(context/'training.csv'),'prediction_sha256':sha(context/'prediction.csv'),
                'codebook_sha256':sha(context/'bitwise_codebook.json')}
        save_json(data/'causal_master_manifest.json',{'energy_protocol':PROTOCOL,'contexts':metadata,'lean_features':features,
            'bitwise_features':packed_fields,'bitwise_source_fields':features,'seismic_predictors':[],
            'data_builder_sha256':sha(__file__),'shared_fitter_sha256':sha(origin_model.__file__)})
        save_csv(data/'training_master.csv',pd.read_csv(data/'validation_1/training.csv'))
        save_csv(data/'validation_master.csv',pd.concat([pd.read_csv(data/name/'prediction.csv') for name,_,_ in contexts if name!='forecast'],ignore_index=True))
        save_csv(data/'prospective_master.csv',pd.read_csv(data/'forecast/prediction.csv'))
    return out,contract


def proposal(tid,family,frames,features,config,parent=None):
    """Use the shared search space, pi sampler and model families without seismic fields."""
    c=origin_model.proposal(tid,family,frames,features,config,parent)
    expected='packed_' if family=='lcs' else 'astro_'
    if not all(f.startswith(expected) for f in c['features']):raise ValueError('non_astronomical_feature_selected')
    c.update(feature_representation='bitwise_astronomy_only' if family=='lcs' else 'uncompressed_astronomy_only',energy_protocol=PROTOCOL)
    return c


def install(config,root):
    origin_model.install(config,root)
    if origin_model.MANIFEST.get('energy_protocol')!=PROTOCOL:raise ValueError('wrong_energy_data_protocol')
    engine.propose=proposal


def audit(config,energy,output,exercise_models=True):
    """Check both branches/origins and optionally exercise all three actual fitters.

    Prediction-label perturbations must not alter fitted predictions. Every
    codebook fits before its issue, contains astronomy only, and the terminal
    training row survives pi-infill. No accuracy claim is made by this audit.
    """
    checks=[];torch.set_num_threads(config.get('threads',1));torch.use_deterministic_algorithms(True)
    previous=(engine.propose,engine.fit)
    try:
        for branch in config['branches']:
            root=Path(energy)/branch;install(config,root)
            for name,m in origin_model.MANIFEST['contexts'].items():
                tr=origin_model.CONTEXTS[name]['training'];pr=origin_model.CONTEXTS[name]['prediction'];issue=pd.Timestamp(m['issue_time'])
                assert pd.Timestamp(tr.date.max())<issue<=pd.Timestamp(pr.date.min())
                assert m['training_sha256']==sha(root/'01_data'/name/'training.csv')
                assert m['prediction_sha256']==sha(root/'01_data'/name/'prediction.csv')
                cb=json.loads((root/'01_data'/name/'bitwise_codebook.json').read_text())
                assert pd.Timestamp(cb['quantile_fit_end_date'])<issue
                assert all(f.startswith('astro_') for fs in cb['containers'].values() for f in fs)
                assert not any(f.startswith('seis_') for f in tr)
                assert not tr.is_world_hard_negative.any()
                if name=='forecast':assert pr.event_target.isna().all()
                checks.append({'branch':branch,'origin':name,'issue':str(issue),'training_last_week':m['training_last_week'],
                    'astronomy_only':True,'training_only_codebook':True,'codebook_sha256':m['codebook_sha256']})
            frames={s:pd.read_csv(root/'01_data'/f'{s}_master.csv') for s in ['training','validation','prospective']}
            for family in ['kan','deep_learning','lcs']:
                c=proposal(1,family,frames,[],config);c['epochs']=2;c['params']['population_size']=24
                c['features']=c['features'][:4]
                for name,context in origin_model.CONTEXTS.items():
                    selected,gaps=origin_model.sample_training(c,context['training'])
                    assert selected.date.max()==context['training'].date.max()
                    if gaps:
                        from src.uncompressed_pipeline.l1_engine import get_pi_infill_seed
                        if config.get('infill_seed_mode','pi_pairs')=='pi_pairs':
                            assert gaps[0]['seed']==get_pi_infill_seed(gaps[0]['pi_pair_index'])
                if exercise_models:
                    fitted=copy.deepcopy(c);a,_,_=origin_model.fit(fitted,frames)
                    saved={n:d['prediction'].event_target.copy() for n,d in origin_model.CONTEXTS.items()}
                    try:
                        for d in origin_model.CONTEXTS.values():d['prediction']['event_target']=12345
                        b,_,_=origin_model.fit(copy.deepcopy(c),frames)
                    finally:
                        for n,d in origin_model.CONTEXTS.items():d['prediction']['event_target']=saved[n]
                    assert all(np.array_equal(a[s],b[s]) for s in a)
                    for n,m in fitted['fit_contexts'].items():
                        mask=np.unpackbits(np.frombuffer(bytes.fromhex(m['training_row_mask_hex']),dtype=np.uint8),bitorder='little')[:m['training_context_rows']]
                        assert mask[-1] and mask.sum()==m['training_rows']
                checks.append({'branch':branch,'family':family,'terminal_rows_retained':True,'prediction_label_perturbation_checked':exercise_models})
    finally:
        engine.propose,engine.fit=previous
    result={'status':'passed','energy_protocol':PROTOCOL,'checks':checks,'source_sha256':sha(__file__),'scope':'Input availability and fitting isolation, not independent predictive accuracy'}
    save_json(output,result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--branch',required=True)
    a=p.parse_args();c=json.loads(a.config.read_text());torch.set_num_threads(c.get('threads',1));torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s');install(c,a.root)
    return engine.run(c,a.branch,a.root)


if __name__=='__main__':raise SystemExit(main())
