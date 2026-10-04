"""Recalculate published location curves from saved trials, weights and calibration."""
from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd

from production_location import load_inputs, metrics, quality_rank, save_json, sha


def audit(config):
    spatial=Path(config['spatial_root']);search=Path(config['search_output_root'])
    report_root=spatial/'dual_method_reports'
    report=json.loads((report_root/'report_manifest.json').read_text())
    frames,targets,features,events,rows,truth=load_inputs(config,'main_bodies_branch')
    columns=[f'prob_Zone_{i}' for i in range(len(targets))]
    results=[];total_trials=0;total_models=0
    for method in ['learned','historical_analogs']:
        root=search if method=='learned' else search/method
        selection=json.loads((report_root/method/'stage_pair_selection.json').read_text())
        assert len(selection['candidates'])==4 and selection['prospective_scores_not_used_for_selection']
        assert selection['selected_stages']==report['methods'][method]['selected_branch_stages']
        assert quality_rank(selection['selected_metrics'])==max(quality_rank(c['metrics']) for c in selection['candidates'])
        arrays=[];branches=[]
        for branch in ['main_bodies_branch','minor_bodies_branch']:
            branch_root=root/branch;stage=selection['selected_stages'][branch]
            completed=json.loads((branch_root/'completed_manifest.json').read_text())
            assert len(pd.read_csv(branch_root/'all_trials.csv'))==completed['completed_trials']
            total_trials+=completed['completed_trials']
            for split,digest in completed['identity']['input_hashes'].items():
                assert sha(spatial/branch/'01_data'/f'{split}_master.csv')==digest
            folder=branch_root/stage;manifest=json.loads((folder/'fusion_manifest.json').read_text())
            replay=json.loads((folder/'selected_stage_replay_manifest.json').read_text())
            assert replay['stage_manifest_sha256']==sha(folder/'fusion_manifest.json')
            assert replay['fit_source_sha256']==completed['identity']['source_sha256']
            assert {m['trial_id'] for m in replay['models']}=={m['trial_id'] for m in manifest['selected_trials']}
            for model in replay['models']:
                assert sha(model['model_path'])==model['model_sha256']
                proof=json.loads(Path(model['replay_proof']).read_text())
                assert proof['max_errors'].get('training',0.) <= min(proof.get('training_absolute_tolerance',1e-10),2*np.finfo(np.float32).eps) and all(v<1e-10 for k,v in proof['max_errors'].items() if k!='training')
            total_models+=len(replay['models'])
            raw={s:np.zeros((len(frames[s]),len(targets))) for s in ['validation','prospective']}
            for item in manifest['selected_trials']:
                with np.load(item['trial_record']['predictions_file']) as candidate:
                    for split in raw:raw[split]+=candidate[split]*np.asarray(item['weights_by_zone'])
            bias=np.asarray(manifest['calibration']['logit_bias_by_zone']);temperature=manifest['calibration']['temperature']
            transformed={};errors={}
            for split,filename in [('validation','validation_predictions'),('prospective','prospective_forecast')]:
                uncalibrated=pd.read_csv(folder/f'uncalibrated_{filename}.csv')[columns].to_numpy()
                assert np.max(np.abs(raw[split]-uncalibrated))<1e-10
                logit=np.log(np.clip(raw[split],1e-6,1-1e-6)/np.clip(1-raw[split],1e-6,1))
                predicted=1/(1+np.exp(-np.clip((logit+bias)/temperature,-30,30)))
                saved=pd.read_csv(folder/f'{filename}.csv')[columns].to_numpy()
                errors[split]=float(np.max(np.abs(predicted-saved)));assert errors[split]<1e-8
                transformed[split]=saved
            arrays.append(transformed)
            branches.append({'branch':branch,'selected_stage':stage,'trials':completed['completed_trials'],
                             'selected_models':len(replay['models']),'calibration_reconstruction_max_errors':errors})
        weight=selection['main_weight'];errors={}
        for split,filename in [('validation','validation_predictions'),('prospective','prospective_forecast')]:
            expected=weight*arrays[0][split]+(1-weight)*arrays[1][split]
            saved=pd.read_csv(report_root/method/f'{filename}.csv')
            assert saved.date.equals(frames[split].date)
            errors[split]=float(np.max(np.abs(expected-saved[columns].to_numpy())));assert errors[split]<1e-12
            assert np.array_equal(saved.predicted_zone_id,expected.argmax(1))
            if split=='validation':
                q=metrics(frames[split][targets].to_numpy(),expected,rows,truth)
                assert abs(q['quality_index']-report['methods'][method]['metrics']['quality_index'])<1e-12
                event_csv=pd.read_csv(report_root/method/'individual_event_validation.csv')
                assert event_csv.id.tolist()==events.id.tolist()
                assert np.array_equal(event_csv.predicted_zone_id,expected.argmax(1)[rows])
        results.append({'method':method,'metrics':q,'branches':branches,'fusion_max_errors':errors})
    cross_method=None
    if 'fused_methods' in report['methods']:
        meta=json.loads((report_root/'fused_methods/metrics_and_corridors.json').read_text());weight=meta['weights']['A_learned']
        assert 0<weight<1 and not meta['future_labels_used'];errors={}
        use_consensus=meta.get('consensus_gating',False)
        for split in ['validation_predictions','prospective_forecast']:
            a=pd.read_csv(report_root/'learned'/f'{split}.csv');b=pd.read_csv(report_root/'historical_analogs'/f'{split}.csv')
            c=pd.read_csv(report_root/'fused_methods'/f'{split}.csv')
            if use_consensus:
                from spatial_consensus_fusion import compute_consensus_fusion
                expected=compute_consensus_fusion(a,b,columns,a_weight=weight)[columns].to_numpy()
            else:
                expected=weight*a[columns].to_numpy()+(1-weight)*b[columns].to_numpy()
            assert a.date.equals(b.date) and a.date.equals(c.date)
            errors[split]=float(np.max(np.abs(c[columns].to_numpy()-expected)));assert errors[split]<1e-12
            assert np.array_equal(c.predicted_zone_id,expected.argmax(1))
            if split=='validation_predictions':
                q=metrics(frames['validation'][targets].to_numpy(),expected,rows,truth)
                assert abs(q['quality_index']-meta['metrics']['quality_index'])<1e-12
        cross_method={'weights':meta['weights'],'max_errors':errors,'metrics':q,'consensus_gating':use_consensus}
    proof={'status':'passed','completed_location_trials':total_trials,'selected_stage_model_artifacts':total_models,'cross_method_fusion':cross_method,
           'same_saved_transforms_reconstructed_for_validation_and_forecast':True,'all_four_stage_pairs_compared':True,
           'validation_is_selection_set_not_independent_test':True,'methods':results,
           'report_manifest_sha256':sha(report_root/'report_manifest.json'),'audit_source_sha256':sha(__file__)}
    save_json(spatial/'location_publication_numeric_verification.json',proof)
    return proof


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(audit(json.loads(args.config.read_text())),indent=2))
