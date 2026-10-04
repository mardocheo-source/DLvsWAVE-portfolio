#!/usr/bin/env python3
"""Bounded single-region or nested energy + two-method location production.

Operator entry point: commands/forecast.sh (check/run/resume/status).
See docs/FORECAST_PIPELINE_GUIDE.md and FORECAST_RULES_AUDIT.md for the
implemented contracts and the separate causal Japan energy protocol.
Geographic L0-L4 are independent of the five internal model stages. A completed
node persists its report before descending. Source/configuration hashes protect
resume; changing a geographic domain requires fresh fits, not relabelled caches.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime,timezone
import fcntl
import json
import logging
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import uuid
import pandas as pd
import torch
from production_location import save_json,sha,storage_available
from production_inputs import load_catalog,load_astronomy
from world_node_map import build as node_scope_map
from world_zoom import temporal_zoom,event_rectangle
from world_zone_reconciliation import decide as reconcile_zones,apply as apply_reconciliation,lineage_page
from production_geography import membership,geometry,prepare_energy,prepare_location,select_peak,choose_child
from world_energy_reports import build as energy_report
from world_location_reports import build as location_report,text_page,merge
from production_leakage_audit import audit
from audit_world_location_publication import audit as audit_location_publication

LOG=logging.getLogger('global_production')
SRC=Path(__file__).resolve().parent


def workers(jobs,deadline,config=None):
    """Each model process has one log, its own cache and an explicit wall limit."""
    config=config or {};active=[];pending=list(jobs)
    limit=int(config.get('max_parallel_workers',os.environ.get('DLVS_MAX_PARALLEL_WORKERS',1)))
    if limit<1:raise ValueError('max_parallel_workers must be positive')
    reserve=int(config.get('minimum_available_memory_mb',4096))*1024
    def memory_available():
        p=Path('/proc/meminfo')
        if not p.exists():return True
        values={line.split(':')[0]:int(line.split()[1]) for line in p.read_text().splitlines()}
        return values.get('MemAvailable',0)>=reserve
    try:
        while pending or active:
            if time.time()>=deadline:raise TimeoutError('node_or_study_time_budget')
            while pending and len(active)<limit and memory_available():
                argv,log=pending.pop(0)
                log=Path(log);log.parent.mkdir(parents=True,exist_ok=True);stream=log.open('a')
                process=subprocess.Popen([sys.executable,*map(str,argv)],stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                active.append((process,stream,argv,log))
            for item in active[:]:
                process,stream,argv,log=item;code=process.poll()
                if code is not None:
                    stream.close();active.remove(item)
                    if code:raise RuntimeError(f'Worker exit {code}; inspect {log}')
                    LOG.info('Worker completed: %s',log)
            if active and time.time()>=deadline:raise TimeoutError('node_or_study_time_budget')
            if active or pending:time.sleep(5)
    finally:
        for process,stream,argv,log in active:
            if process.poll() is None:os.killpg(process.pid,signal.SIGINT)
        end=time.time()+45
        for process,stream,argv,log in active:
            try:process.wait(timeout=max(.1,end-time.time()))
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            stream.close()


def node_report(node,state,config,energy_pdf=None,location_pdf=None):
    sections=[('Geographic domain',json.dumps(state['geometry'])),
              ('Progress and limits',f"Status: {state['status']}. Stop reason: {state.get('stop_reason','none')}. Internal model stages are separate from geographic depth. Full effective configuration is saved in node_configuration.json."),
              ('Actual data and validation',json.dumps({'energy':state.get('energy_contract'),'location':state.get('location_contract')},default=str)),
              ('Next zone',json.dumps(state.get('child_selection',{}),default=str))]
    # Keep audit details in JSON and make the PDF readable even for a large node.
    compact=[]
    for title,body in sections:
        if len(body)>550:body=body[:500]+' ... See node_state.json for the complete recorded values.'
        compact.append((title,body))
    cover=node_scope_map(node,state,config)
    from production_report_navigation import compose,infer_entry
    entries=[{'path':str(cover),'section':'OVERVIEW','branch':state['node_id'],'title':'Node overview','method':'Energy / Location A / B / A+B'}]
    if state.get('stop_reason'):
        reason=str(state['stop_reason'])
        if 'insufficient_recent_energy_validation_with_training_retention' in reason:
            attempted=json.JSONDecoder().raw_decode(reason[reason.index('['):])[0]
            explanation='Too few recent earthquakes to construct the required energy validation window while retaining the training history.'
            detail='; '.join(f"M{a['threshold']:.1f}: {a['recent_event_weeks']} recent event weeks" for a in attempted)+'.'
        else:
            explanation=reason[:350]
            detail='See node_state.json for the complete stop reason and recorded parameters.'
        status_pdf=text_page(f"Geographic level {state['level']} - Study status",[
            ('Current state',f"{state['status'].replace('_',' ').capitalize()}. " + ('No energy or location models were trained for this node.' if not energy_pdf and not location_pdf else 'Completed results are preserved in this report.')),
            ('Why this level stopped',explanation),
            ('Thresholds and evidence',detail),
            ('What remains available','The input-area map and configuration are preserved. Completed parent-level forecasts remain in the World report. Later geographic levels have not been executed from this stopped node.'),
            ('Continuation','Resume only after addressing the recorded cause, preserving completed trials, source provenance and the remaining time budget.')
        ],node/'study_status.pdf')
        entries.append({'path':str(status_pdf),'section':'STATUS','branch':state['node_id'],'title':'Progress and reason for stopping','method':'Recorded execution state'})
    if energy_pdf and Path(energy_pdf).exists():
        manifest=json.loads((node/'01_energy_forecast/fusion_main_minor/report_manifest.json').read_text())
        entries.extend(infer_entry(p) for p in manifest['page_sources'])
    if location_pdf and Path(location_pdf).exists():
        manifest=json.loads((node/'02_location_forecast/dual_method_reports/report_manifest.json').read_text())
        for item in manifest['page_sources']:
            e={k:item[k] for k in ['path','section','branch','title','method']}
            if e['section']=='OVERVIEW':e['section']='LOCATION FORECAST'
            entries.append(e)
    if state.get('reconciliation'):
        lineage=lineage_page(node,state['reconciliation'])
        entries.append({'path':str(lineage),'section':'LINEAGE','branch':'Combined geographic area','title':'Why neighbouring zones were combined','method':'Consecutive weeks and adjacent zones'})
    path=node/'JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf';compose(entries,path,'Energy Forecast / Location Forecast - Contents')
    state['report']=str(path);state['report_sha256']=sha(path);save_json(node/'node_state.json',state)
    return path


def summary(root,state):
    save_json(root/'study_state.json',state)
    rows=[]
    for n in state['nodes']:
        rows.append({'level':n['level'],'node_id':n['node_id'],'status':n['status'],'observer':n.get('observer','500@399'),'report':n.get('report'),
                     'stop_reason':n.get('stop_reason'),'area_fraction':n.get('geometry',{}).get('area_fraction'),
                     'energy_gate':n.get('energy_quality',{}).get('strict_gate_passed'),
                     'selected_location_method':n.get('selected_location_method'),
                     'location_accuracy':n.get('location_quality',{}).get('event_top1_accuracy')})
    pd.DataFrame(rows).to_csv(root/'level_comparison.csv',index=False)
    lines=['# Worldwide nested forecast progress','',f"Updated: {datetime.now(timezone.utc).isoformat()}",f"Status: {state['status']}",'',
           '| Geographic level | Node | Observer | Status | Report / reason |','|---|---|---|---|---|']
    for r in rows:lines.append(f"| {r['level']} | {r['node_id']} | {r.get('observer','500@399')} | {r['status']} | {r.get('report') or r.get('stop_reason') or ''} |")
    (root/'PROGRESS.md').write_text('\n'.join(lines)+'\n')


def run(config,root,resume=False,inputs_only=False):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    lock=(root/'study.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    config_file=root/'run_configuration.json'
    if config_file.exists():assert json.loads(config_file.read_text())==config,'Resume configuration changed'
    else:save_json(config_file,config)
    source={str(p.relative_to(SRC)):sha(p) for p in SRC.rglob('*.py')}
    if (root/'source_manifest.json').exists():assert json.loads((root/'source_manifest.json').read_text())==source,'Source changed; use a new study'
    else:
        save_json(root/'source_manifest.json',source)
        snapshot=root/'source_snapshot/src';snapshot.mkdir(parents=True,exist_ok=True)
        for name in source:
            target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SRC/name,target)
    frozen_src=root/'source_snapshot/src'
    state=json.loads((root/'study_state.json').read_text()) if (root/'study_state.json').exists() else {
        'study_id':root.name,'created_utc':datetime.now(timezone.utc).isoformat(),'status':'preparing_inputs','elapsed_seconds':0,
        'nodes':[{'level':l,'node_id':f'n{l:03d}_'+(('region' if config.get('initial_membership_rules') else 'world') if l==0 else 'selected_region'),'status':'not_executed'} for l in range(config.get('initial_geo_level',0),config.get('max_geo_level',3)+1)]}
    previous=state.get('elapsed_seconds',0);start=time.time();deadline=start+max(0,config.get('maximum_study_seconds',28800)-previous)
    active_node=None;node_previous=0.;node_started=0.
    def checkpoint():
        state['elapsed_seconds']=previous+time.time()-start
        if active_node is not None:
            active_node['node_elapsed_seconds']=node_previous+time.time()-node_started
        summary(root,state)
    checkpoint()
    raw=root/'shared_raw_inputs'
    if config.get('input_cache_dir') and not (raw/'inputs_complete.json').exists():
        shutil.copytree(config['input_cache_dir'],raw,dirs_exist_ok=True)
    try:
        events=load_catalog(config,raw);astro=load_astronomy(config,raw)
        save_json(raw/'inputs_complete.json',{'catalog_events':len(events),'astronomy_rows':{k:len(v) for k,v in astro.items()},'status':'complete'})
        if inputs_only:state['status']='inputs_complete';checkpoint();return 0
        rules=config.get('initial_membership_rules',[]);state['status']='running'
        for entry in state['nodes']:
            level=entry['level']
            if entry['status']=='complete':
                if entry.get('child_selection'):rules=entry['child_selection']['membership_rules']
                if entry.get('stop_reason'):break
                continue
            node=root/f'L{level}'/entry['node_id'];node.mkdir(parents=True,exist_ok=True)
            if (node/'node_state.json').exists():entry.update(json.loads((node/'node_state.json').read_text()))
            rules=entry.get('domain_override',rules)
            # Charge active node execution, not the time spent paused between
            # invocations. Old studies continue with their own frozen runner.
            active_node=entry;node_previous=entry.get('node_elapsed_seconds',0.);node_started=time.time()
            entry['node_budget_started_epoch']=node_started-node_previous
            entry.update(status='running',geometry=geometry(rules),membership_rules=rules);entry.pop('stop_reason',None)
            node_config=copy.deepcopy(config);node_config.update(node_id=entry['node_id'],parent_region_rules=rules,map_bounds=entry['geometry']['bounds'])
            node_config['parent_event']=state['nodes'][state['nodes'].index(entry)-1].get('child_selection',{}).get('peak',{}) if state['nodes'].index(entry)>0 else config.get('parent_event',{})
            if level>0 and node_config.get('parent_event'):
                node_config.update(temporal_zoom(config,node_config['parent_event']))
            if entry.get('reconciliation'):node_config['combined_parent_zones']=entry['reconciliation']['zone_ids']
            if level==0 or not entry['geometry'].get('centroid'):
                entry['observer']='500@399'
                node_config['astronomy_observer']='500@399'
                node_astro=astro
            else:
                c_lat,c_lon=entry['geometry']['centroid']
                c_lon=float(((c_lon+180)%360)-180)
                c_lat=float(max(-90.,min(90.,c_lat)))
                topocentric_obs={'lat':c_lat,'lon':c_lon,'elevation':0.0}
                entry['observer']=f"topocentric@{c_lat:.4f},{c_lon:.4f}"
                node_config['astronomy_observer']=entry['observer']
                LOG.info('Node %s using topocentric observer at lat=%.4f, lon=%.4f',entry['node_id'],c_lat,c_lon)
                node_astro=load_astronomy(node_config,node,observer=topocentric_obs)
            save_json(node/'node_configuration.json',node_config);save_json(node/'node_state.json',entry);node_scope_map(node,entry,node_config);checkpoint()
            subset=events.loc[membership(events,rules)].copy();save_json(node/'catalog_selection.json',{'input_events':len(events),'node_events':len(subset),'rules':rules})
            node_deadline=min(deadline,entry['node_budget_started_epoch']+config.get('maximum_node_seconds',7200));epdf=lpdf=None
            try:
                if time.time()>=node_deadline:raise TimeoutError('node_or_study_budget_before_node')
                if not storage_available(node,node_config):raise ValueError('disk_reserve_reached_before_node')
                energy,ec=prepare_energy(subset,node_astro,node,node_config);entry['energy_contract']=ec
                location,lc,zones=prepare_location(subset,node_astro,node,node_config);entry['location_contract']=lc
                node_scope_map(node,entry,node_config)
                checkpoint()
                econfig={**node_config,'energy_branch_max_seconds':config.get('energy_branch_max_seconds',2400)}
                epath=node/'energy_configuration.json';save_json(epath,econfig)
                ejobs=[]
                energy_worker='production_energy.py'
                if config.get('energy_protocol')=='origin_refit_astro_only':
                    from world_origin_energy import audit as audit_energy_origins
                    audit_energy_origins(econfig,energy,energy/'origin_availability_audit.json',exercise_models=False)
                    energy_worker='world_origin_energy.py'
                for branch in config['branches']:
                    if not (energy/branch/'completed_manifest.json').exists():ejobs.append(([frozen_src/energy_worker,'--config',epath,'--branch',branch,'--root',energy/branch],node/'logs'/f'energy_{branch}.log'))
                workers(ejobs,node_deadline,config)
                epdf,eq=energy_report(energy,subset,node_config);entry['energy_quality']=eq
                node_report(node,entry,node_config,epdf);checkpoint()
                if level>0 and not entry.get('reconciliation_count'):
                    parents=sorted((root/f'L{level-1}').glob('*/node_state.json'))
                    if parents:
                        decision=reconcile_zones(parents[0].parent,node,events,node_config)
                        save_json(node/'zone_reconciliation_check.json',decision)
                        if decision['triggered']:
                            apply_reconciliation(root,node,entry,decision);checkpoint()
                            fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
                            return run(config,root,resume=True)
                # Fusion-only options do not alter the identity of cached location fits.
                fit_config={k:v for k,v in node_config.items() if k not in ['huntanyway','energy_fusion_policy']}
                lconfig={**fit_config,'spatial_root':str(location),'study_root':str(node),'search_output_root':str(location/'extended_search'),
                         'energy_forecast_csv':str(energy/'fusion_main_minor/final_prospective_forecast.csv'),
                         'max_seconds':config.get('location_branch_max_seconds',2400),'refinement_reserve_seconds':config.get('location_refinement_reserve_seconds',600),
                         'report_reserve_seconds':config.get('location_report_reserve_seconds',240),'threads':config.get('threads',2),'feature_prefixes':['astro_'],
                         'spherical_zone_centers':zones['centers'],'seed':config.get('seed',42)}
                audit(lconfig)
                lpath=node/'location_configuration.json';save_json(lpath,lconfig)
                aconfig={**lconfig,'max_seconds':config.get('analog_max_seconds',1200),'refinement_reserve_seconds':config.get('analog_refinement_reserve_seconds',250),
                         'analog_trials':config.get('analog_trials',3000),'analog_refinement_trials':config.get('analog_refinement_trials',600)}
                apath=node/'analog_configuration.json';save_json(apath,aconfig)
                jobs=[]
                for branch in config['branches']:
                    for mode,path,out in [('learned',lpath,location/'extended_search'/branch),('analog',apath,location/'extended_search/historical_analogs'/branch)]:
                        if not (out/'completed_manifest.json').exists():jobs.append(([frozen_src/'production_location.py','--config',path,'--branch',branch,'--mode',mode,'--output',out],node/'logs'/f'location_{mode}_{branch}.log'))
                workers(jobs,node_deadline,config)
                lm=location_report(lconfig);audit_location_publication(lconfig)
                lpdf=Path(lm['report']);entry['location_methods']={k:v['metrics'] for k,v in lm['methods'].items()}
                selected=max(entry['location_methods'],key=lambda k:(entry['location_methods'][k]['quality_index'],k=='fused_methods',k=='learned'))
                entry['selected_location_method']=selected;entry['location_quality']=entry['location_methods'][selected]
                curve=pd.read_csv(energy/'fusion_main_minor/final_prospective_forecast.csv');peaks=select_peak(curve,node_config);entry['peak_selection']=peaks
                q=entry['location_quality'];entry['status']='complete'
                if level==config.get('max_geo_level',3):entry['stop_reason']='configured_maximum_geographic_depth'
                elif not config.get('follow_peak_without_quality_gate',False) and not eq['strict_gate_passed']:entry['stop_reason']='energy_validation_quality_gate_not_met'
                elif not config.get('follow_peak_without_quality_gate',False) and (q['event_top1_accuracy']<config.get('minimum_child_location_accuracy',.75) or q['macro_zone_recall']<config.get('minimum_child_macro_recall',.6)):entry['stop_reason']='location_validation_quality_gate_not_met'
                elif peaks['selected'] is None:entry['stop_reason']=peaks['stop_reason']
                else:
                    forecast=pd.read_csv(location/'dual_method_reports'/selected/'prospective_forecast.csv')
                    candidate_rules,child=choose_child(rules,zones,forecast,peaks['selected'],node_config)
                    candidate_rules,rectangle_audit=event_rectangle(events,candidate_rules,node_config)
                    child.update(membership_rules=candidate_rules,child_geometry=geometry(candidate_rules),rectangle=rectangle_audit)
                    child['method']=selected;child['method_selection']='highest declared validation quality index; consensus fusion breaks an exact tie'
                    if child['ambiguity_gate_passed'] or config.get('follow_peak_without_quality_gate',False):rules=candidate_rules;entry['child_selection']=child
                    else:entry['candidate_child_selection']=child;entry['stop_reason']='ambiguous_prospective_zone_scores'
                node_report(node,entry,node_config,epdf,lpdf);checkpoint()
                LOG.info('Node %s complete; next: %s',entry['node_id'],entry.get('stop_reason','selected child'))
                if entry.get('stop_reason'):break
            except BaseException as exc:
                entry['status']='interrupted' if isinstance(exc,(TimeoutError,KeyboardInterrupt)) else 'stopped'
                entry['stop_reason']=repr(exc);node_report(node,entry,node_config,epdf,lpdf);checkpoint()
                if isinstance(exc,KeyboardInterrupt):raise
                LOG.exception('Node preserved before stopping');break
        finished=[n for n in state['nodes'] if n['status']!='not_executed']
        def resolve_report(p):
            if not p:return None
            path=Path(p)
            if not path.is_absolute():path=(root/path).resolve()
            return path if path.exists() else None
        reports=[resolve_report(n.get('report')) for n in finished]
        reports=[p for p in reports if p is not None]
        parent_reports=sorted((root/'L0').glob('*/JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf'))
        reports=parent_reports+[p for p in reports if p.resolve() not in {q.resolve() for q in parent_reports}]
        if reports:merge(reports,root/'WORLD_NESTED_JOINT_REPORT.pdf')
        checkpoint();return 0 if state['status']=='completed_with_recorded_stop' else 75
    except BaseException as exc:
        state['status']='interrupted';state['error']=repr(exc);checkpoint();raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path);p.add_argument('--resume',action='store_true');p.add_argument('--inputs-only',action='store_true')
    a=p.parse_args();config=json.loads(a.config.read_text());root=a.output or SRC.parent/'studies_output'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_world_nested_'+uuid.uuid4().hex[:8])
    if root.exists() and not a.resume:raise FileExistsError('Output already exists; use --resume with the unchanged configuration')
    torch.set_num_threads(config.get('threads',2));torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s');print(root,flush=True)
    return run(config,root,a.resume,a.inputs_only)
if __name__=='__main__':raise SystemExit(main())
