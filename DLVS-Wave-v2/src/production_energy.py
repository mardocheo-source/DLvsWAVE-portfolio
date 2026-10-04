"""Geography-independent adapter for the production energy model/fusion methods.

Uses the actual energy KAN/ResNet/LCS fitting functions and needle metrics. The
two Japan event dates and 54/26-row constants are replaced by data contracts.
Fusion keeps the original peak/calm strategies and 63,063 calibration settings.
"""
from __future__ import annotations
import argparse
import copy
import fcntl
import json
import logging
from pathlib import Path
import time
import numpy as np
import pandas as pd
import torch
from production_location import save_json,save_csv,sha,storage_available
from src.uncompressed_pipeline.l1_engine import train_eval_trial_torch,train_eval_trial_lcs
from src.uncompressed_pipeline.metrics import evaluate_needle_predictions

LOG=logging.getLogger('production_energy')
FAMILIES=['kan','deep_learning','lcs']


def evaluate(y,p,val,yt,pt,elapsed):
    result=evaluate_needle_predictions(y,p,val,yt,pt,elapsed).to_dict()
    result['validation_event_probabilities']=[float(p[np.flatnonzero((val.event_number.to_numpy()==number)&(val.relative_week.to_numpy()==0))[0]]) for number in sorted(val.event_number.unique())]
    # These legacy metric names refer to event positions, not geographic identity.
    result.pop('val_peak_tokachi_prob');result.pop('val_peak_tohoku_prob')
    return result


def propose(tid,family,frames,features,config,parent=None):
    seed=int(config.get('seed',42)+tid*1009);rng=np.random.default_rng(seed)
    tr=frames['training'];years=config.get('energy_train_start_years',[1900,1920,1940,1960,1980,2000])
    starts=[f'{y}-01-01' for y in years if tr.loc[tr.date>=f'{y}-01-01','event_target'].sum()>=8]
    if not starts:starts=[str(tr.date.iloc[0])]
    sizes=config.get('energy_feature_counts',{}).get(family,[4,8,12,16,24,32,48,64,len(features)])
    if not sizes or any(not isinstance(i,int) or i<1 for i in sizes):raise ValueError('energy_feature_counts must contain positive integer counts')
    n=int(rng.choice(sorted({min(i,len(features)) for i in sizes})))
    params={'learning_rate':float(rng.choice([.0003,.0007,.0015,.003])),
            'grid_size':int(rng.choice([3,5,7])),'spline_order':int(rng.choice([2,3])),
            'hidden_dim':int(rng.choice([32,64,128])),'num_layers':int(rng.choice([2,3,4])),
            'dropout':float(rng.choice([.05,.1,.2])),
            'logit_temperature':float(rng.choice([.12,.2,.35,.6,1.])),
            'logit_bias':float(rng.choice([0.,.4,.8,1.2,1.6])),
            'population_size':int(rng.choice([60,120,180,240])),
            'crossover_rate':float(rng.choice([.3,.6,.9])),'mutation_rate':float(rng.choice([.01,.05,.15])),
            'rule_center':float(rng.choice([.35,.5,.62,.75])),'rule_temperature':float(rng.choice([.03,.08,.2]))}
    c={'trial_id':tid,'family':family,'seed':seed,'features':[str(v) for v in rng.choice(features,n,replace=False)],
       'training_start':str(rng.choice(starts)),'window_before_steps':int(rng.choice([0,1,2,4,8])),
       'window_after_steps':int(rng.choice([0,1,2,4,8])),'background_infill_ratio':float(rng.choice([.1,.25,.5,1.,2.])),
       'epochs':int(rng.choice(config.get('energy_epochs',[40,80,120]))),'params':params,'refinement_parent':None}
    if parent:
        old=parent['configuration'];c['family']=old['family'];c['refinement_parent']=old['trial_id']
        if rng.random()<.7:
            selected=list(old['features']);rng.shuffle(selected);selected=selected[:max(2,len(selected)-int(rng.integers(0,max(2,len(selected)//3))))]
            available=[f for f in features if f not in selected]
            if available:selected += [str(v) for v in rng.choice(available,min(len(available),int(rng.integers(1,6))),replace=False)]
            c['features']=selected
        if rng.random()<.75:c['training_start']=old['training_start']
        c['params']=copy.deepcopy(old['params'])
        for key in rng.choice(list(params),3,replace=False):c['params'][key]=params[key]
    # Refinement must obey the same width limit as the initial search.
    limit=min(max(sizes),len(features))
    if len(c['features'])>limit:c['features']=[str(f) for f in rng.choice(c['features'],limit,replace=False)]
    c['feature_count_limit']=limit
    return c


def fit(c,frames):
    start=time.time();tr=frames['training'].loc[frames['training'].date>=c['training_start']].reset_index(drop=True)
    y=tr.event_target.to_numpy(int);positions=np.flatnonzero(y);keep=np.zeros(len(tr),bool)
    for i in positions:keep[max(0,i-c['window_before_steps']):min(len(tr),i+c['window_after_steps']+1)]=True
    candidates=np.flatnonzero(~keep);rng=np.random.default_rng(c['seed'])
    size=min(len(candidates),max(8,int(keep.sum()*c['background_infill_ratio'])))
    if size:keep[rng.choice(candidates,size,replace=False)]=True
    tr=tr.loc[keep].copy();y=tr.event_target.to_numpy(int);f=c['features']
    x=tr[f].to_numpy(float);minimum=x.min(0);scale=np.ptp(x,axis=0);scale[scale<1e-9]=1.
    norm=lambda a:np.clip((a[f].to_numpy(float)-minimum)/scale,0,1).astype(np.float32)
    xt,xv,xf=norm(tr),norm(frames['validation']),norm(frames['prospective'])
    if c['family']=='lcs':pt,pv,pf,artifact=train_eval_trial_lcs(xt,y,xv,xf,c['params'],c['seed'])
    else:pt,pv,pf,artifact=train_eval_trial_torch(c['family'],xt,y,xv,frames['validation'].event_target.to_numpy(),xf,c['params'],c['epochs'],c['seed'])
    c['scaler']={'minimum':minimum.tolist(),'range':scale.tolist(),'fit_scope':'selected training rows only'}
    c['actual_training_dates']=tr.date.astype(str).tolist();c['training_rows']=len(tr);c['training_positive_weeks']=int(y.sum())
    q=evaluate(frames['validation'].event_target.to_numpy(),pv,frames['validation'],y,pt,time.time()-start)
    return {'training':pt,'validation':pv,'prospective':pf},q,artifact


def calibration_score(probabilities,val):
    """Vectorized exact original fusion objective for any event corridor count."""
    y=val.event_target.to_numpy(int);calm=probabilities[:,y==0];events=probabilities[:,y==1]
    centered=np.zeros(len(probabilities),int);timing=np.zeros(len(probabilities))
    for number in sorted(val.event_number.unique()):
        idx=np.flatnonzero(val.event_number.to_numpy()==number);center=np.flatnonzero(val.iloc[idx].relative_week.to_numpy()==0)[0]
        peak=np.argmax(probabilities[:,idx],axis=1);error=abs(peak-center)
        centered+=(probabilities[:,idx[center]]>=.7)&(error==0);timing+=error
    count=val.event_number.nunique();timing/=count;sparsity=(calm<.05).mean(1);cm=calm.mean(1);fp=(calm>=.7).sum(1)
    loss=6*(1-centered/count)+5*(1-sparsity)+2*cm+2*np.mean((1-events)**2,axis=1)+.1*timing+.1*fp
    return loss,centered,sparsity,cm,timing,fp


def fuse(records,frames,output,config):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    ordered=sorted(records,key=lambda r:(r['metrics']['composite_needle_loss'],r['metrics'].get('train_loss',0.)))
    pool=ordered[:max(2,int(config.get('energy_fusion_candidates',10))-6)]
    pool += sorted(records,key=lambda r:(-r['metrics']['val_peak_hit_rate'],r['metrics']['val_peak_timing_error_weeks']))[:3]
    pool += sorted(records,key=lambda r:(-r['metrics']['val_quiescence_sparsity'],r['metrics']['val_calm_mean_prob']))[:3]
    pool=list({r['configuration']['trial_id']:r for r in pool}.values())
    arrays=[np.load(r['predictions_file']) for r in pool];v=np.stack([a['validation'] for a in arrays]);f=np.stack([a['prospective'] for a in arrays])
    peak=np.array([max(.1,.25+4*r['metrics']['val_peak_hit_rate']+min(r['metrics']['validation_event_probabilities'])-.1*r['metrics']['val_peak_timing_error_weeks']) for r in pool])
    calm=np.array([max(.1,.25+5*r['metrics']['val_quiescence_sparsity']-.15*r['metrics']['val_false_positives']-3*r['metrics']['val_calm_mean_prob']) for r in pool])
    peak/=peak.sum();calm/=calm.sum()
    po={'weighted_mean':(peak@v,peak@f),'specialist_envelope':(v.max(0),f.max(0)),'specialist_q90':(np.quantile(v,.9,axis=0),np.quantile(f,.9,axis=0))}
    co={'weighted_mean':(calm@v,calm@f),'depression_floor':(v.min(0),f.min(0)),'depression_q10':(np.quantile(v,.1,axis=0),np.quantile(f,.1,axis=0))}
    centers,temps=np.meshgrid(np.linspace(.05,.95,91),np.array([.015,.025,.04,.06,.09,.14,.22]),indexing='ij')
    centers=centers.ravel();temps=temps.ravel();best=None;candidates=[];number=0
    for pn,(pv,pf) in po.items():
        for cn,(cv,cf) in co.items():
            for alpha in np.linspace(0,1,11):
                raw=alpha*pv+(1-alpha)*cv
                probabilities=1/(1+np.exp(-np.clip((raw[None,:]-centers[:,None])/temps[:,None],-30,30)))
                loss,hits,sparse,mean,timing,fp=calibration_score(probabilities,frames['validation'])
                order=np.lexsort((mean,-sparse,-hits,loss));i=int(order[0]);number+=len(centers)
                key=(float(loss[i]),-int(hits[i]),-float(sparse[i]),float(mean[i]))
                meta={'peak_strategy':pn,'calm_strategy':cn,'alpha':float(alpha),'center':float(centers[i]),'temperature':float(temps[i]),
                      'calibration_loss':float(loss[i]),'centered_peak_count':int(hits[i]),'sparsity':float(sparse[i]),'calm_mean':float(mean[i]),'false_positives':int(fp[i])}
                candidates.append(meta)
                if best is None or key<best[0]:best=(key,meta,pv,cv,pf,cf)
    _,chosen,pv,cv,pf,cf=best
    transform=lambda peak,calm:np.clip(1/(1+np.exp(-np.clip((chosen['alpha']*peak+(1-chosen['alpha'])*calm-chosen['center'])/chosen['temperature'],-30,30))),.001,.999)
    valprob,fcprob=transform(pv,cv),transform(pf,cf)
    validation=frames['validation'][['date','event_target','event_number','relative_week']].copy();validation['predicted_prob']=valprob
    forecast=frames['prospective'][['date']].copy();forecast['predicted_prob']=fcprob
    save_csv(output/'validation_predictions.csv',validation);save_csv(output/'prospective_forecast.csv',forecast)
    losses,hits,sparse,mean,timing,fp=calibration_score(valprob[None,:],frames['validation'])
    truth=frames['validation'].event_target.to_numpy(int);positive=truth==1
    event_count=frames['validation'].event_number.nunique()
    quality={'calibration_objective_on_final_clipped_curve':float(losses[0]),'val_centered_peak_count':int(hits[0]),
             'val_peak_hit_rate':float(hits[0]/event_count),'val_quiescence_sparsity':float(sparse[0]),
             'val_calm_mean_prob':float(mean[0]),'val_peak_timing_error_weeks':float(timing[0]),
             'val_false_positives':int(fp[0]),'val_false_negatives':int(np.sum(valprob[positive]<.7)),
             'val_brier_score':float(np.mean((valprob-truth)**2)),
             'validation_event_probabilities':valprob[positive].tolist(),
             'strict_gate_passed':bool(hits[0]==event_count and sparse[0]>=.9),
             'training_metric_scope':'No common fused training score: candidates use different training windows.'}
    meta={'calibration':chosen,'calibration_settings_evaluated':number,'best_per_strategy_alpha':candidates,
          'selected_trials':pool,'peak_weights':peak.tolist(),'calm_weights':calm.tolist(),'validation_metrics':quality,
          'fusion_before_validation':True,'same_transform_on_forecast':True,'source_sha256':sha(__file__)}
    save_json(output/'fusion_manifest.json',meta);return meta


def run(config,branch,root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);lock=(root/'energy.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    frames={s:pd.read_csv(root/'01_data'/f'{s}_master.csv') for s in ['training','validation','prospective']}
    feats=[c for c in frames['training'] if c.startswith(('astro_','seis_','packed_'))]
    assert max(frames['training'].date)<min(frames['validation'].date)
    assert all(np.isfinite(f[feats]).all().all() for f in frames.values())
    identity={'input_hashes':{s:sha(root/'01_data'/f'{s}_master.csv') for s in frames},'config':config,'branch':branch,'source_sha256':sha(__file__)}
    if config.get('energy_protocol')=='origin_refit_astro_only':
        identity['origin_manifest_sha256']=sha(root/'01_data/causal_master_manifest.json')
    if (root/'search_identity.json').exists():assert json.loads((root/'search_identity.json').read_text())==identity
    else:save_json(root/'search_identity.json',identity)
    previous=json.loads((root/'search_state.json').read_text()) if (root/'search_state.json').exists() else {};before=previous.get('elapsed_seconds',0)
    start=time.time();budget=config.get('energy_branch_max_seconds',2400);deadline=start+max(0,budget-before)
    final_reserve=config.get('energy_final_reserve_seconds',180)
    initial_deadline=deadline-config.get('energy_refinement_reserve_seconds',500)-final_reserve
    records=[]
    for stage in ['02_level1','04_level2_deep_meta_optimizer']:
        records += [json.loads(p.read_text()) for p in sorted((root/stage/'trial_cache').glob('trial_*/record.json'))]
    records.sort(key=lambda r:r['configuration']['trial_id']);assert [r['configuration']['trial_id'] for r in records]==list(range(1,len(records)+1))
    def progress(status,stage,reason=None):
        save_json(root/'search_state.json',{'status':status,'stage':stage,'trials':len(records),'elapsed_seconds':before+time.time()-start,'max_seconds':budget,'stop_reason':reason,
                  'best_loss':min([r['metrics']['composite_needle_loss'] for r in records],default=None)})
    def commit(family,stage,parent=None):
        tid=len(records)+1;c=propose(tid,family,frames,feats,config,parent);pred,q,artifact=fit(c,frames)
        d=root/stage/'trial_cache'/f'trial_{tid:06d}';d.mkdir(parents=True,exist_ok=True)
        with (d/'predictions.npz.tmp').open('wb') as f:np.savez_compressed(f,**pred)
        (d/'predictions.npz.tmp').replace(d/'predictions.npz')
        r={'configuration':c,'metrics':q,'stage':stage,'predictions_file':str((d/'predictions.npz').resolve())};save_json(d/'record.json',r);records.append(r)
        if tid%25==0 or tid==1:
            progress('running',stage);LOG.info('%s energy %s %d: loss %.4f, best %.4f',branch,stage,tid,q['composite_needle_loss'],min(r['metrics']['composite_needle_loss'] for r in records))
    settings=config['branches'][branch];cap=settings['trials_per_family']*3;count=lambda stage:sum(r['stage']==stage for r in records)
    while count('02_level1')<cap and time.time()<initial_deadline and storage_available(root,config):commit(FAMILIES[count('02_level1')%3],'02_level1')
    if not records:raise TimeoutError('no_energy_trials_before_deadline')
    initial=[r for r in records if r['stage']=='02_level1'];first=fuse(initial,frames,root/'03_level1_fusion',config)
    parents=sorted(initial,key=lambda r:r['metrics']['composite_needle_loss'])[:32]
    while count('04_level2_deep_meta_optimizer')<settings['refinement_trials'] and time.time()<deadline-final_reserve and storage_available(root,config):
        n=count('04_level2_deep_meta_optimizer');parent=parents[n%len(parents)];commit(parent['configuration']['family'],'04_level2_deep_meta_optimizer',parent)
    refined=[r for r in records if r['stage']=='04_level2_deep_meta_optimizer']
    second=fuse(refined,frames,root/'04_level2_deep_meta_optimizer/level2_fusion',config) if refined else None
    # Preserve the original hierarchy: final fusion consumes the two already
    # calibrated stage curves, rather than silently pooling all raw trials again.
    sources=[];selected={}
    for index,(name,stage,manifest) in enumerate([
        ('level1_fusion',root/'03_level1_fusion',first),
        ('level2_fusion',root/'04_level2_deep_meta_optimizer/level2_fusion',second)]):
        if manifest is None:continue
        q=manifest['validation_metrics'];package=stage/'stage_predictions.npz'
        np.savez_compressed(package,validation=pd.read_csv(stage/'validation_predictions.csv').predicted_prob.to_numpy(),
                            prospective=pd.read_csv(stage/'prospective_forecast.csv').predicted_prob.to_numpy())
        sources.append({'configuration':{'trial_id':-index-1,'family':name},'predictions_file':str(package.resolve()),
                        'metrics':{**q,'composite_needle_loss':q['calibration_objective_on_final_clipped_curve']}})
        for trial in manifest['selected_trials']:selected[trial['configuration']['trial_id']]=trial
    final=fuse(sources,frames,root/'05_level3_final_fusion',config)
    final['stage_sources']=[r['configuration']['family'] for r in sources]
    final['underlying_selected_trial_ids']=sorted(selected)
    save_json(root/'05_level3_final_fusion/fusion_manifest.json',final)
    for r in selected.values():
        tid=r['configuration']['trial_id'];d=root/'05_level3_final_fusion/selected_models'/f'trial_{tid:06d}';d.mkdir(parents=True,exist_ok=True)
        pred,q,artifact=fit(copy.deepcopy(r['configuration']),frames);old=np.load(r['predictions_file']);errors={s:float(np.max(abs(old[s]-pred[s]))) for s in pred};assert max(errors.values())<1e-10
        torch.save({'configuration':r['configuration'],'artifact':artifact},d/'model.pt');save_json(d/'replay_verification.json',errors)
    flat=[]
    for r in records:
        c=r['configuration'];flat.append({'trial_id':c['trial_id'],'family':c['family'],'stage':r['stage'],'seed':c['seed'],'training_start':c['training_start'],
                 'features':json.dumps(c['features']),'hyperparameters':json.dumps(c['params']),**{k:v for k,v in r['metrics'].items() if not isinstance(v,list)},
                 **{f'feat__{f}':int(f in c['features']) for f in feats}})
    save_csv(root/'all_trials.csv',pd.DataFrame(flat));save_json(root/'completed_manifest.json',{'status':'complete','trials':len(records),'initial_trials':len(initial),'refinement_trials':len(refined),
                 'validation_metrics':final['validation_metrics'],'identity':identity,'forecast_mode':'one_shot','selected_models_replayed':True})
    progress('complete','05_level3_final_fusion','disk_reserve_reached' if not storage_available(root,config) else 'trial_caps_reached' if len(initial)==cap and len(refined)==settings['refinement_trials'] else 'time_budget');return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,required=True);parser.add_argument('--branch',required=True);parser.add_argument('--root',type=Path,required=True)
    a=parser.parse_args();config=json.loads(a.config.read_text());torch.set_num_threads(config.get('threads',2));torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s');raise SystemExit(run(config,a.branch,a.root))
