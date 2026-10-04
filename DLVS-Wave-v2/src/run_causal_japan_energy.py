"""Bounded fresh energy retraining; preserve the existing location models."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,shutil,subprocess,sys,time,uuid
# Both historical src.* and current direct module imports need stable roots.
SRC=Path(__file__).resolve().parent
sys.path[:0]=[str(SRC.parent),str(SRC)]
from production_location import save_json,sha


def initialize(config,root):
    from forecast_search_policy import validate
    validate(config)
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=False)
    (root/'commands').mkdir();(root/'logs').mkdir();(root/'00_reproduction_audit').mkdir()
    from forecast_source_manifest import build as source_manifest
    closure=source_manifest(SRC.parent)['files']
    declared=json.loads((SRC.parent/'docs/FORECAST_SOURCE_MANIFEST.json').read_text())['files']
    if closure!=declared:raise ValueError('Refresh the maintained source manifest before initializing Japan')
    for name in closure:
        target=root/'source_snapshot/src'/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(SRC/name,target)
    save_json(root/'configuration.json',config)
    save_json(root/'source_snapshot/manifest.json',{str(p.relative_to(root)):sha(p) for p in (root/'source_snapshot').rglob('*.py')})
    (root/'README.md').write_text('# Causal-input Japan energy retraining\n\nFresh energy trials; fixed existing location A/B models will be reused explicitly after energy completes. Each historical validation origin has its own training pool and bitwise codebook. The forecast has a separate pre-issue refit. Pi-pair calm sampling is applied to both main and minor branches. Full observed terminal quiescence is retained; partial issue-week coverage is disclosed. No future seismic inputs or output backshifts. Validation still selects models and calibrations.\n\nSee PROGRESS.md, study_state.json, configuration.json and logs/. Resume with commands/run_causal_energy.sh.\n')
    (root/'commands/run_causal_energy.sh').write_text('''#!/usr/bin/env bash
set -euo pipefail
STUDY_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/dlvs-causal-energy}"
export PYTHONPATH="${STUDY_DIR}/source_snapshot:${STUDY_DIR}/source_snapshot/src"
exec "${DLVS_PYTHON:-@PYTHON@}" "${STUDY_DIR}/source_snapshot/src/run_causal_japan_energy.py" --config "${STUDY_DIR}/configuration.json" --output "${STUDY_DIR}" --resume
'''.replace('@PYTHON@',sys.executable));(root/'commands/run_causal_energy.sh').chmod(0o755)
    return root


def run(config,root,prepare_only=False):
    from causal_japan_energy_data import prepare
    from run_global_recursive_forecast import workers
    root=Path(root).resolve();state_path=root/'study_state.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {'started_epoch':time.time(),'completed_steps':[]}
    deadline=state['started_epoch']+config.get('maximum_seconds',18000)
    def checkpoint(stage,status='running',error=None):
        state.update(stage=stage,status=status,error=error,updated_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.time()-state['started_epoch'])
        save_json(state_path,state);(root/'PROGRESS.md').write_text(f"# Japan causal energy retraining\n\n{state['updated_utc']}\n\nStatus: {status}\nStage: {stage}\nElapsed: {state['elapsed_seconds']:.0f} seconds\nCompleted: {', '.join(state['completed_steps'])}\n\nPer-branch real trial counts: 01_energy_forecast_m77/*/search_state.json\n")
    os.environ['PYTHONPATH']=str(root/'source_snapshot')+os.pathsep+str(root/'source_snapshot/src')
    energy=root/'01_energy_forecast_m77'
    try:
        if 'data' not in state['completed_steps']:
            checkpoint('rebuild_raw_lags_and_issue_specific_bitwise');prepare(config,energy);state['completed_steps'].append('data');checkpoint('causal_inputs_saved')
        if prepare_only:return
        if 'preflight' not in state['completed_steps']:
            from audit_causal_japan_energy import preflight
            checkpoint('causal_preflight');preflight(config,energy,root/'00_reproduction_audit/causal_preflight.json');state['completed_steps'].append('preflight')
        jobs=[]
        for branch in ['main_bodies_branch','minor_bodies_branch']:
            if not (energy/branch/'completed_manifest.json').exists():jobs.append(([root/'source_snapshot/src/causal_japan_energy.py','--config',root/'configuration.json','--branch',branch,'--root',energy/branch],root/'logs'/f'{branch}.log'))
        checkpoint('energy_main_minor_search_and_forecast_refits');workers(jobs,deadline-900,config)
        if 'energy' not in state['completed_steps']:state['completed_steps'].append('energy')
        checkpoint('energy_reports_and_reused_location_maps')
        from causal_japan_energy_reports import publish
        publish(config,root)
        state['completed_steps'].append('reports');checkpoint('all_reports_generated','complete_pending_visual_review')
    except BaseException as e:checkpoint(state.get('stage','initialization'),'interrupted',repr(e));raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path);p.add_argument('--resume',action='store_true');p.add_argument('--initialize-only',action='store_true');p.add_argument('--prepare-only',action='store_true');p.add_argument('--infill-seed-mode',choices=['pi_pairs','trial_seed']);p.add_argument('--pi-pair-offset',type=int)
    p.add_argument('--policy',type=Path,help='Optional JSON policy overlay; merged configuration is frozen before any fitting')
    p.add_argument('--no-seismic-inputs',action='store_true',help='Exclude ALL seismic predictor lags for energy; catalog remains available for targets and calm labels.')
    a=p.parse_args();c=json.loads(a.config.read_text())
    if a.policy:c.update(json.loads(a.policy.read_text()))
    if a.no_seismic_inputs:c['seismic_lag_weeks']=[]
    root=a.output or SRC.parent/'studies_output'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_japan_causal_energy_'+uuid.uuid4().hex[:8])
    if a.infill_seed_mode:c['infill_seed_mode']=a.infill_seed_mode
    if a.pi_pair_offset is not None:c['pi_pair_offset']=a.pi_pair_offset
    if not a.resume:
        initialize(c,root)
        if not a.initialize_only:
            argv=[sys.executable,str(Path(root)/'source_snapshot/src/run_causal_japan_energy.py'),'--config',str(Path(root)/'configuration.json'),'--output',str(root),'--resume']
            if a.prepare_only:argv.append('--prepare-only')
            os.execv(sys.executable,argv)
    else:assert json.loads((root/'configuration.json').read_text())==c
    print(root,flush=True)
    if not a.initialize_only:run(c,root,a.prepare_only)
if __name__=='__main__':main()
