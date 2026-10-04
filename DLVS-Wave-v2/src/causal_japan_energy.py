"""Original KAN/Deep/LCS and asymmetric hierarchy with issue-specific causal fits."""
from pathlib import Path
import argparse,copy,json,logging,time
import numpy as np
import pandas as pd
import torch
import production_energy as engine
from production_location import save_json
from src.uncompressed_pipeline.l1_engine import get_pi_infill_seed

_ORIGINAL_PROPOSE=engine.propose
CONTEXTS={};CONFIG={};MANIFEST={}


def proposal(tid,family,frames,features,config,parent=None):
    feature_pool=MANIFEST['bitwise_features' if family=='lcs' else 'lean_features']
    c=_ORIGINAL_PROPOSE(tid,family,frames,feature_pool,config,parent)
    c['infill_seed_mode']=config.get('infill_seed_mode','pi_pairs')
    c['pi_pair_offset']=int(config.get('pi_pair_offset',0))
    c['terminal_infill']=config.get('terminal_infill','all_observed')
    c['feature_representation']='bitwise_astro_with_causal_seismic' if family=='lcs' else 'uncompressed_causal'
    c['temporal_projection_shift_weeks']=0
    return c


def sample_training(c,frame):
    tr=frame.loc[frame.date>=c['training_start']].reset_index(drop=True)
    y=tr.event_target.to_numpy(int);positive=np.flatnonzero(y);assert len(positive)>0
    keep=np.zeros(len(tr),bool)
    for i in positive:keep[max(0,i-c['window_before_steps']):min(len(tr),i+c['window_after_steps']+1)]=True
    keep|=tr.is_world_hard_negative.to_numpy(bool)
    # Sample every calm gap, with explicit independently recorded pi-derived seeds.
    available=np.flatnonzero(~keep);gaps=np.split(available,np.flatnonzero(np.diff(available)>1)+1);audit=[]
    for number,gap in enumerate(gaps):
        if not len(gap):continue
        mode=c['infill_seed_mode'];idx=c['trial_id']-1+c['pi_pair_offset']+number
        seed=get_pi_infill_seed(idx) if mode=='pi_pairs' else c['seed']+number
        size=min(len(gap),max(1,int(np.ceil(len(gap)*min(1,c['background_infill_ratio'])))))
        selected=np.random.default_rng(seed).choice(gap,size,replace=False);keep[selected]=True
        audit.append({'gap_start':str(tr.date.iloc[gap[0]]),'gap_end':str(tr.date.iloc[gap[-1]]),'seed':int(seed),'pi_pair_index':int(idx) if mode=='pi_pairs' else None,'available_rows':len(gap),'sampled_rows':size})
    if c['terminal_infill']=='all_observed':keep[positive[-1]+1:]=True
    else:raise ValueError('terminal_infill must preserve all observed terminal weeks')
    assert keep[-1] and tr.date.iloc[-1]==frame.date.iloc[-1]
    return tr.loc[keep].copy(),audit


def fit(c,frames):
    start=time.time();predictions=[];yt=[];pt=[];artifacts={};audits={}
    for name,context in CONTEXTS.items():
        tr,infill=sample_training(c,context['training']);f=c['features'];x=tr[f].to_numpy(float)
        minimum=x.min(0);scale=np.ptp(x,axis=0);scale[scale<1e-9]=1
        norm=lambda a:np.clip((a[f].to_numpy(float)-minimum)/scale,0,1).astype(np.float32)
        xt=norm(tr);xp=norm(context['prediction']);y=tr.event_target.to_numpy(int)
        if c['family']=='lcs':train_prob,p,p2,artifact=engine.train_eval_trial_lcs(xt,y,xp,xp,c['params'],c['seed'])
        else:train_prob,p,p2,artifact=engine.train_eval_trial_torch(c['family'],xt,y,xp,np.zeros(len(xp)),xp,c['params'],c['epochs'],c['seed'])
        assert np.array_equal(p,p2)
        # The unchanged neural function computes its positive prototype on training.
        positive=xt[y==1];centroid=np.median(positive,axis=0)
        artifact['input_scaler']={'minimum':minimum.tolist(),'range':scale.tolist()}
        artifact['positive_prototype']={'centroid':centroid.tolist(),'mad':(np.median(abs(positive-centroid),axis=0)+1e-3).tolist()}
        artifacts[name]=artifact
        audits[name]={'issue_time':MANIFEST['contexts'][name]['issue_time'],'training_last_week':str(tr.date.max()),
            'training_rows':len(tr),'positive_weeks':int(y.sum()),'terminal_weeks_retained':int((tr.date>context['training'].loc[context['training'].event_target.eq(1),'date'].max()).sum()),
            'infill_gaps':infill,'training_row_mask_hex':np.packbits(context['training'].date.isin(tr.date).to_numpy(),bitorder='little').tobytes().hex(),
            'training_row_mask_bitorder':'little','training_context_rows':len(context['training']),'training_row_mask_source':'01_data/'+name+'/training.csv','scaler':artifact['input_scaler'],
            'quantization_codebook_sha256':MANIFEST['contexts'][name]['codebook_sha256']}
        if name=='forecast':future=p
        else:predictions.append(p);yt.extend(y);pt.extend(train_prob)
    pv=np.concatenate(predictions);q=engine.evaluate(frames['validation'].event_target.to_numpy(),pv,frames['validation'],np.array(yt),np.array(pt),time.time()-start)
    c['fit_contexts']=audits;c['training_rows']=sum(len(d['training']) for n,d in CONTEXTS.items() if n!='forecast')
    c['forecast_refit_completed']=True;c['inference_protocol']='fixed one-shot per origin; separate future refit'
    return {'training':np.array(pt),'validation':pv,'prospective':future},q,{'kind':'issue_specific_energy_models','contexts':artifacts}


def install(config,root):
    global CONTEXTS,CONFIG,MANIFEST
    CONFIG=config;data=Path(root)/'01_data';MANIFEST=json.loads((data/'causal_master_manifest.json').read_text())
    CONTEXTS={n:{s:pd.read_csv(data/n/(s+'.csv')) for s in ['training','prediction']} for n in MANIFEST['contexts']}
    engine.propose=proposal;engine.fit=fit


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--branch',required=True)
    a=p.parse_args();config=json.loads(a.config.read_text());torch.set_num_threads(config.get('threads',1));torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s');install(config,a.root)
    return engine.run(config,a.branch,a.root)
if __name__=='__main__':raise SystemExit(main())
