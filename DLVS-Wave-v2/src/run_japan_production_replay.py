#!/usr/bin/env python3
"""Fresh-source replay of the original energy chain and audited dual location."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,shutil,subprocess,sys,time,uuid
from production_location import save_json,sha

SRC=Path(__file__).resolve().parent
PROJECT=SRC.parent
REPOSITORY=PROJECT.parent


def initialize(config,root):
    root=Path(root).resolve();template=Path(config['reference_reproduction_root']).resolve()
    if root.exists():raise FileExistsError('Fresh replay requires an empty, unique output path')
    if root.parent!=PROJECT/'studies_output':raise ValueError('Historical energy adapter requires a direct study folder inside project studies_output')
    root.mkdir();(root/'commands').mkdir();audit=root/'00_reproduction_audit';audit.mkdir()
    # Copy source code and declared experiment configuration only.
    shutil.copytree(template/'source_snapshot',root/'source_snapshot',ignore=shutil.ignore_patterns('__pycache__'))
    for name in ['recompute.py','finish_reproduction.py','report_metadata.py','location_reports.py']:
        shutil.copy2(template/'commands'/name,root/'commands'/name)
    shutil.copy2(PROJECT/'commands/production_templates/resume_energy_screening.py',root/'commands/resume_energy_screening.py')
    shutil.copytree(SRC,root/'automation_source/src',ignore=shutil.ignore_patterns('__pycache__'))
    energy_config=json.loads((template/'run_config.json').read_text());energy_config['execution_date']=datetime.now(timezone.utc).date().isoformat()
    energy_config['location_update']={'configuration':'location_configuration.json','mode':'strict_one_shot_event_only_two_methods'}
    save_json(root/'run_config.json',energy_config);save_json(root/'automation_configuration.json',config)
    save_json(audit/'event_only_location_pending.json',{'new_location_owns_spatial_finalization':True})
    # Freeze only raw event identities/coordinates, feature names and future dates.
    source=Path(config['location_data']['source_spatial_root']);raw=root/'raw_location_contract';(raw/'01_data').mkdir(parents=True)
    for name in ['training_events.csv','validation_events.csv']:shutil.copy2(source/'01_data'/name,raw/'01_data'/name)
    shutil.copy2(source/'event_only_master_manifest.json',raw/'event_only_master_manifest.json')
    import pandas as pd
    for b in ['main_bodies_branch','minor_bodies_branch']:
        d=raw/b/'01_data';d.mkdir(parents=True)
        pd.read_csv(source/b/'01_data/training_master.csv',nrows=0).to_csv(d/'training_master.csv',index=False)
        pd.read_csv(source/b/'01_data/prospective_master.csv',usecols=['date']).to_csv(d/'prospective_master.csv',index=False)
    spatial=root/'02a_spatial_zones_forecast_multitarget'
    data={**config['location_data'],'source_spatial_root':str(raw),'output_spatial_root':str(spatial)};save_json(root/'location_data_configuration.json',data)
    loc={**config['location_search'],'spatial_root':str(spatial),'study_root':str(root),'search_output_root':str(spatial/'extended_search'),
         'energy_forecast_csv':str(root/'01_energy_forecast_m77/fusion_main_minor/final_prospective_forecast.csv')}
    save_json(root/'location_configuration.json',loc)
    analog={**loc,**config.get('analog_overrides',{})};save_json(root/'analog_configuration.json',analog)
    # Reference-map provenance is evidence for the explanatory report, not a model input.
    for name in ['original_02_02a_map_discrepancy.json','original_map_numeric_lineage.json','seismic_lag_calendar_audit.json','original_principal_pdf_discrepancy.json']:
        p=template/'00_reproduction_audit'/name
        if p.exists():shutil.copy2(p,audit/name)
    source_files=[p for d in ['source_snapshot','automation_source','commands'] for p in (root/d).rglob('*') if p.is_file()]
    save_json(audit/'fresh_initialization_manifest.json',{'created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':{str(p.relative_to(root)):sha(p) for p in source_files},
         'copied_trained_models':False,'copied_prediction_curves':False,'copied_report_pages':False,'raw_contract_hashes':{str(p.relative_to(root)):sha(p) for p in raw.rglob('*') if p.is_file()},
         'reference_outputs_used_only_for_post_fit_comparison':True})
    (root/'README.md').write_text('# Fresh Japan production replay\n\nOriginal energy techniques and fixed trial counts are recomputed. Location uses two event-only, fixed one-shot methods. Source code, raw input contracts and configurations were copied at initialization; trained models, prediction curves and PDF pages were not copied.\n\nRun commands/run_full_replay.sh to resume with frozen sources. See PROGRESS.md and automation_state.json. The retained original energy inference-availability issue is reported separately; exact reproduction is not a leakage-free forecast certification.\n')
    shell='''#!/usr/bin/env bash
set -euo pipefail
STUDY_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_DIR="$(cd -- "${STUDY_DIR}/../../.." && pwd)"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/dlvs-japan-replay}"
exec "${DLVS_PYTHON:-${REPOSITORY_DIR}/.venv/bin/python}" "${STUDY_DIR}/automation_source/src/run_japan_production_replay.py" --config "${STUDY_DIR}/automation_configuration.json" --output "${STUDY_DIR}" --resume
'''
    (root/'commands/run_full_replay.sh').write_text(shell);(root/'commands/run_full_replay.sh').chmod(0o755)
    return root


def run(config,root):
    root=Path(root);state_file=root/'automation_state.json'
    state=json.loads(state_file.read_text()) if state_file.exists() else {'status':'running','completed_steps':[],'elapsed_seconds':0}
    previous=state.get('elapsed_seconds',0);start=time.time();deadline=start+max(0,config.get('maximum_seconds',21600)-previous)
    def checkpoint(stage,status='running'):
        state.update(stage=stage,status=status,elapsed_seconds=previous+time.time()-start,updated_utc=datetime.now(timezone.utc).isoformat())
        save_json(state_file,state);(root/'PROGRESS.md').write_text(f"# Fresh Japan replay\n\n{state['updated_utc']}\n\nStatus: {status}\n\nStage: {stage}\n\nCompleted: {', '.join(state['completed_steps'])}\n\nReal fit progress is in execution.log and logs/.\n")
    def step(name,args,accepted=(0,)):
        if name in state['completed_steps']:return
        checkpoint(name);remaining=deadline-time.time()
        if remaining<=0:raise TimeoutError('whole_replay_budget')
        logs=root/'logs';logs.mkdir(exist_ok=True)
        with (logs/f'{name}.log').open('a') as log:
            code=subprocess.call(['timeout','--signal=INT','--kill-after=90s',f'{max(1,int(remaining))}s',sys.executable,*map(str,args)],stdout=log,stderr=subprocess.STDOUT)
        if code not in accepted:raise RuntimeError(f'{name}: exit {code}; inspect logs/{name}.log')
        if code==0:state['completed_steps'].append(name)
        checkpoint(name);return code
    current=root/'automation_source/src';commands=root/'commands'
    try:
        step('energy_data',[commands/'recompute.py','--stage','data'])
        if not (root/'02a_spatial_zones_forecast_multitarget/event_only_master_manifest.json').exists():
            step('location_data',[current/'prepare_one_shot_location.py','--config',root/'location_data_configuration.json'])
        for branch in ['main_bodies_branch','minor_bodies_branch']:
            for family in ['kan','deep_learning','lcs']:
                name=f'{branch}_{family}_screening'
                while name not in state['completed_steps']:
                    step(name,[commands/'resume_energy_screening.py','--branch',branch,'--family',family,'--chunk-size',config.get('energy_chunk_size',128),'--max-seconds',config.get('energy_chunk_seconds',600)],accepted=(0,75))
            step(f'{branch}_refinement_and_fusion',[commands/'recompute.py','--stage','main' if branch.startswith('main') else 'minor'])
        step('energy_reports',[commands/'recompute.py','--stage','final'])
        step('energy_report_metadata',[commands/'report_metadata.py',root])
        step('energy_availability_audit',[current/'audit_energy_temporal_availability.py',root])
        # Independent model processes share immutable data but never model state.
        from run_global_recursive_forecast import workers
        jobs=[]
        for branch in ['main_bodies_branch','minor_bodies_branch']:
            for mode,path,out in [('learned',root/'location_configuration.json',root/'02a_spatial_zones_forecast_multitarget/extended_search'/branch),
                                  ('analog',root/'analog_configuration.json',root/'02a_spatial_zones_forecast_multitarget/extended_search/historical_analogs'/branch)]:
                if not (out/'completed_manifest.json').exists():jobs.append(([current/'production_location.py','--config',path,'--branch',branch,'--mode',mode,'--output',out],root/'logs'/f'location_{mode}_{branch}.log'))
        checkpoint('two_method_location_search');workers(jobs,deadline)
        from production_leakage_audit import audit
        import torch
        torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
        loc=json.loads((root/'location_configuration.json').read_text());audit(loc)
        step('location_report',[current/'production_location_reports.py','--config',root/'location_configuration.json'])
        step('location_numeric_audit',[current/'audit_location_publication.py','--config',root/'location_configuration.json'])
        step('joint_report',[current/'production_japan_joint_report.py','--config',root/'location_configuration.json'])
        step('final_report_metadata',[commands/'report_metadata.py',root])
        step('publish_location',[current/'production_publish_location.py','--config',root/'location_configuration.json'])
        step('refresh_publication',[current/'refresh_publication.py','--config',root/'location_configuration.json'])
        checkpoint('all_reports_generated','complete_pending_visual_review');return 0
    except BaseException as exc:
        state['error']=repr(exc);checkpoint(state.get('stage','initialization'),'interrupted');raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path);p.add_argument('--resume',action='store_true');p.add_argument('--initialize-only',action='store_true')
    a=p.parse_args();config=json.loads(a.config.read_text());root=a.output or PROJECT/'studies_output'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_japan_replay_'+uuid.uuid4().hex[:8])
    if not a.resume:initialize(config,root)
    else:assert json.loads((root/'automation_configuration.json').read_text())==config
    print(root,flush=True)
    if a.initialize_only:return 0
    return run(config,root)
if __name__=='__main__':raise SystemExit(main())
