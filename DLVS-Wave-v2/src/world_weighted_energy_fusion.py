"""Auditable pointwise main/minor fusion; optional forecast-curve recovery.

Normal selection ranks committed stages on validation. With ``huntanyway``, a
flat selected stage may be replaced by an earlier stage having a distinct peak;
parent-window overlap has priority among recovery candidates. The final sum is
always ``main_weight * main[t] + (1-main_weight) * minor[t]``. No second sigmoid
or calm-floor operation is permitted after this sum. Both validation and future
ordinates use the same selected stages and weights. A constant pool stays flat.
The JSON proof records source hashes and explicitly marks forecast-shape-aware
selection; it is not additional validation evidence or calibrated confidence.
See docs/FORECAST_PIPELINE_GUIDE.md for flags and examples.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from production_location import sha,save_json,save_csv

STAGES=['03_level1_fusion','04_level2_deep_meta_optimizer/level2_fusion','05_level3_final_fusion']
BRANCHES=['main_bodies_branch','minor_bodies_branch']

def peak_rows(f):
    p=f.predicted_prob.to_numpy(float)
    return np.flatnonzero((p>np.r_[-np.inf,p[:-1]])&(p>=np.r_[p[1:],-np.inf])&(p>p.min()+1e-12)).tolist()

def rank(c):
    q=c['metrics']
    return (-q.get('val_centered_peak_count',0),q.get('val_false_positives',0),q.get('calibration_objective_on_final_clipped_curve',float('inf')))

def norm_peaks(series):
    p=series.to_numpy(float);base=float(p.min());rng=float(p.max()-base)
    return (p-base)/rng if rng>1e-6 else np.zeros_like(p)

def choose(root,config):
    root=Path(root);out=root/'fusion_main_minor';out.mkdir(exist_ok=True)
    w=float(config.get('main_fusion_weight',.85))
    if not 0<=w<=1:raise ValueError('main_fusion_weight must be in [0,1]')
    policy=config.get('energy_fusion_policy',{});hunt=bool(config.get('huntanyway',False))
    straighten=bool(config.get('straighten_peaks',False) or config.get('peak_normalization',False) or policy.get('straighten_peaks',False))
    parent=config.get('parent_event',{});tolerance=int(policy.get('parent_tolerance_weeks',1))
    selected={};audit={'weights':[w,1-w],'formula':'fused[t] = main_weight * norm(main[t]) + (1-main_weight) * norm(minor[t])' if straighten else 'fused[t] = main_weight * main[t] + (1-main_weight) * minor[t]','straighten_peaks':straighten,'huntanyway':hunt,'parent_window':parent,'parent_tolerance_weeks':tolerance,'branch_selection':{},'validation_is_selection_set':True,'recovery_uses_forecast_curve_shape':False,'no_refit':True}
    for branch in BRANCHES:
        pool=[]
        for stage in STAGES:
            path=root/branch/stage
            if not (path/'fusion_manifest.json').exists():continue
            m=json.loads((path/'fusion_manifest.json').read_text());frames={s:pd.read_csv(path/f'{s}.csv') for s in ['validation_predictions','prospective_forecast']}
            f=frames['prospective_forecast'];rows=peak_rows(f);near=[]
            if parent:
                lo=pd.Timestamp(parent['start'])-pd.Timedelta(weeks=tolerance);hi=pd.Timestamp(parent['end'])+pd.Timedelta(weeks=tolerance)
                near=[i for i in rows if pd.Timestamp(f.iloc[i].date)<=hi and pd.Timestamp(f.iloc[i].date)+pd.Timedelta(days=6)>=lo]
            pool.append({'stage':stage,'metrics':m['validation_metrics'],'frames':frames,'rows':rows,'near':near,'source_sha256':{s:sha(path/f'{s}.csv') for s in frames}})
        if not pool:raise ValueError('missing committed energy stages')
        base=min(pool,key=rank);pick=base;reason='best_validation_stage'
        if hunt and not base['rows']:
            candidates=[c for c in pool if c['rows']]
            if candidates:
                supported=[c for c in candidates if c['near']]
                pick=min(supported or candidates,key=rank);reason='huntanyway_recover_existing_stage_peak'
                audit['recovery_uses_forecast_curve_shape']=True
            else:
                pick=base;reason='best_validation_stage'
        selected[branch]=pick['frames']
        audit['branch_selection'][branch]={'stage':pick['stage'],'original_best_stage':base['stage'],'reason':reason,'validation_metrics':pick['metrics'],'source_sha256':pick['source_sha256'],'peak_dates':[str(pick['frames']['prospective_forecast'].iloc[i].date) for i in pick['rows']],'parent_supported_peak_dates':[str(pick['frames']['prospective_forecast'].iloc[i].date) for i in pick['near']], 'candidates':[{'stage':c['stage'],'metrics':c['metrics'],'peak_dates':[str(c['frames']['prospective_forecast'].iloc[i].date) for i in c['rows']]} for c in pool]}
    for split in ['validation_predictions','prospective_forecast']:
        main,minor=[selected[b][split] for b in BRANCHES]
        if not main.date.equals(minor.date):raise ValueError('unaligned main/minor dates')
        for col in ['event_target','event_number','relative_week']:
            if col in main and not main[col].equals(minor[col]):raise ValueError('unaligned validation targets')
        f=main.copy()
        if straighten:
            s_main=norm_peaks(main.predicted_prob);s_minor=norm_peaks(minor.predicted_prob)
            f['predicted_prob']=w*s_main+(1-w)*s_minor
        else:
            f['predicted_prob']=w*main.predicted_prob+(1-w)*minor.predicted_prob
        if not np.isfinite(f.predicted_prob).all():raise ValueError('nonfinite fusion')
        save_csv(out/f'final_{split}.csv',f)
        for b in BRANCHES:
            p=out/'selected_branch_curves'/b;p.mkdir(parents=True,exist_ok=True);save_csv(p/f'{split}.csv',selected[b][split])
    fc=pd.read_csv(out/'final_prospective_forecast.csv');audit['fused_peak_dates']=[str(fc.iloc[i].date) for i in peak_rows(fc)]
    audit['branch_contributions']={'main_weight':w,'minor_weight':1-w,'main_max_prospective':float(selected['main_bodies_branch']['prospective_forecast'].predicted_prob.max()),'minor_max_prospective':float(selected['minor_bodies_branch']['prospective_forecast'].predicted_prob.max()),'fused_max_prospective':float(fc.predicted_prob.max())}
    audit['routing_status']='peak_available' if audit['fused_peak_dates'] else 'no_distinct_peak_in_available_curves'
    audit['interpretation']='Fixed weights give main bodies priority. Validation rank selects stages; huntanyway explicitly uses existing forecast peaks and parent-window proximity to recover suppressed signals. This is an exploratory routing policy, not additional validation evidence.'
    save_json(out/'weighted_fusion_selection.json',audit)
    return selected,audit
