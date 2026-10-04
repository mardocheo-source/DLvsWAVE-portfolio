"""Executable preflight for issue-time features, quantization and training isolation."""
from pathlib import Path
import copy,json
import numpy as np
import pandas as pd
import torch
from production_location import save_json,sha
from causal_japan_energy_data import seismic_features
import causal_japan_energy as model


def preflight(config,energy,output):
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    energy=Path(energy);checks=[]
    events=pd.read_csv(config['japan_catalog']);events['time']=pd.to_datetime(events.time,utc=True).dt.tz_localize(None)
    for branch in config['branches']:
        root=energy/branch;model.install(config,root)
        for name,meta in model.MANIFEST['contexts'].items():
            p=root/'01_data'/name;lineage=pd.read_csv(p/'seismic_source_times.csv')
            assert (pd.to_datetime(lineage.source_end_exclusive)<=pd.to_datetime(lineage.issue_time)).all()
            tr=model.CONTEXTS[name]['training'];pr=model.CONTEXTS[name]['prediction'];issue=pd.Timestamp(meta['issue_time'])
            assert pd.to_datetime(tr.date).max()<issue<=pd.to_datetime(pr.date).min()
            codebook=json.loads((p/'bitwise_codebook.json').read_text());assert pd.Timestamp(codebook['quantile_fit_end_date'])<issue
            assert all(f.startswith('astro_') for fields in codebook['containers'].values() for f in fields)
            dirty=events.copy();after=dirty.time>=issue;dirty.loc[after,'mag']=99;dirty.loc[after,'depth']=999
            a,_=seismic_features(pd.to_datetime(pr.date),events,issue,config['seismic_lag_weeks'])
            b,_=seismic_features(pd.to_datetime(pr.date),dirty,issue,config['seismic_lag_weeks']);pd.testing.assert_frame_equal(a,b)
            assert set(a)<=set(model.MANIFEST['bitwise_features'])
            checks.append({'branch':branch,'context':name,'seismic_future_perturbation_invariant':True,'quantizer_fit_end':codebook['quantile_fit_end_date'],'issue':str(issue),'training_last_week':str(tr.date.max()),'partial_tail':meta['partial_terminal_target_intervals']})
        frames={s:pd.read_csv(root/'01_data'/f'{s}_master.csv') for s in ['training','validation','prospective']}
        assert int(frames['validation'].event_target.sum())==len(config['validation_event_weeks'])
        for family in ['kan','deep_learning','lcs']:
            c=model.proposal(1,family,frames,[],config);c['epochs']=3;c['params']['population_size']=24
            # Include a historical seismic predictor in every structural test.
            c['features']=c['features'][:4]
            if config['seismic_lag_weeks']:
                c['features'] += [f"seis_past_magnitude_lag_{config['seismic_lag_weeks'][0]}w"]
            else:
                assert not any('seis' in f for f in model.MANIFEST['lean_features']+model.MANIFEST['bitwise_features'])
                assert not any('seis' in f for f in c['features'])
            fitted=copy.deepcopy(c);a,_,_=model.fit(fitted,frames)
            for meta in fitted['fit_contexts'].values():
                mask=np.unpackbits(np.frombuffer(bytes.fromhex(meta['training_row_mask_hex']),dtype=np.uint8),bitorder='little')[:meta['training_context_rows']]
                assert mask.sum()==meta['training_rows'] and mask[-1]==1
            saved={n:d['prediction'].event_target.copy() for n,d in model.CONTEXTS.items()}
            for d in model.CONTEXTS.values():d['prediction']['event_target']=98765
            b,_,_=model.fit(copy.deepcopy(c),frames)
            for n,d in model.CONTEXTS.items():d['prediction']['event_target']=saved[n]
            assert all(np.array_equal(a[s],b[s]) for s in a)
            selected,infill=model.sample_training(c,model.CONTEXTS['forecast']['training'])
            assert infill and infill[0]['seed']==14
            assert selected.date.max()==model.CONTEXTS['forecast']['training'].date.max()
            checks.append({'branch':branch,'family':family,'prediction_label_perturbation_invariant':True,'terminal_infill_last_week':selected.date.max(),'first_infill_pi_seed':infill[0]['seed']})
    result={'status':'passed','checks':checks,'scope':'Structural tests; not independent forecast accuracy or historical catalog-vintage certification.','source_sha256':sha(__file__)}
    save_json(output,result);return result
