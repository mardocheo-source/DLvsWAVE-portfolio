"""Select the best saved initial/final stage pair on fused validation scores.

Neither branch forecasts nor old fits are changed. All four 85/15 combinations
remain auditable, and newly selected initial-stage models are replayed exactly.
"""
from pathlib import Path
import copy
import itertools
import json
import time

import numpy as np
import pandas as pd
import torch

from production_location import fit, metrics, quality_rank, save_json, sha

BRANCHES = ['main_bodies_branch', 'minor_bodies_branch']
STAGES = ['03_level1_fusion', '05_level3_final_fusion']


def select_stage_pair(method_root, frames, targets, rows, truth, main_weight, output):
    method_root, output = Path(method_root), Path(output)
    columns = [f'prob_Zone_{i}' for i in range(len(targets))]
    stages, candidates = {}, []
    for branch in BRANCHES:
        assert (method_root/branch/'completed_manifest.json').is_file()
        for stage in STAGES:
            folder = method_root/branch/stage
            data = {split: pd.read_csv(folder/f'{split}.csv')
                    for split in ['validation_predictions', 'prospective_forecast']}
            for split, original in [('validation_predictions', 'validation'), ('prospective_forecast', 'prospective')]:
                assert data[split].date.equals(frames[original].date)
                assert np.isfinite(data[split][columns]).all().all()
                assert np.array_equal(data[split].predicted_zone_id, data[split][columns].to_numpy().argmax(1))
            stages[branch, stage] = data
    for main_stage, minor_stage in itertools.product(STAGES, repeat=2):
        main, minor = stages[BRANCHES[0], main_stage], stages[BRANCHES[1], minor_stage]
        prediction = main_weight*main['validation_predictions'][columns].to_numpy() + (1-main_weight)*minor['validation_predictions'][columns].to_numpy()
        q = metrics(frames['validation'][targets].to_numpy(), prediction, rows, truth)
        candidates.append({'main_stage': main_stage, 'minor_stage': minor_stage, 'metrics': q})
    winner = max(candidates, key=lambda item: (quality_rank(item['metrics']),
                 item['main_stage'] == STAGES[1] and item['minor_stage'] == STAGES[1]))
    original = next(item for item in candidates if item['main_stage'] == item['minor_stage'] == STAGES[1])
    assert quality_rank(winner['metrics']) >= quality_rank(original['metrics'])
    selection = {
        'selection_rule': 'Highest fused validation quality rank across all four initial/final stage pairs; unchanged final/final wins an exact tie.',
        'selection_source_sha256': sha(Path(__file__)),
        'main_weight': main_weight, 'minor_weight': 1-main_weight,
        'selected_stages': dict(zip(BRANCHES, [winner['main_stage'], winner['minor_stage']])),
        'candidates': candidates, 'selected_metrics': winner['metrics'],
        'original_final_pair_metrics': original['metrics'],
        'initial_and_final_candidate_outputs_preserved': True,
        'prospective_scores_not_used_for_selection': True,
        'validation_is_selection_set_not_independent_test': True,
        'input_sha256': {str(method_root/branch/stage/f'{split}.csv'): sha(method_root/branch/stage/f'{split}.csv')
                        for branch in BRANCHES for stage in STAGES
                        for split in ['validation_predictions', 'prospective_forecast']},
    }
    save_json(output/'stage_pair_selection.json', selection)
    return [stages[branch, selection['selected_stages'][branch]] for branch in BRANCHES], selection


def materialize_selected_stage(branch_root, stage, frames, targets, deadline):
    """Replay newly selected models with the same frozen fitting implementation."""
    branch_root = Path(branch_root)
    completed = json.loads((branch_root/'completed_manifest.json').read_text())
    fit_source = Path(fit.__code__.co_filename)
    expected_sha = completed['identity']['source_sha256']
    if sha(fit_source) != expected_sha:
        for ancestor in list(branch_root.parents) + list(branch_root.resolve().parents):
            candidate = ancestor/'automation_source/src/production_location.py'
            if candidate.exists() and sha(candidate) == expected_sha:
                fit_source = candidate
                break
    assert sha(fit_source) == expected_sha, 'Selected model fitter source changed'
    folder = branch_root/stage
    manifest = json.loads((folder/'fusion_manifest.json').read_text())
    replays = []
    torch.set_num_threads(int(completed['identity']['config'].get('threads', 2)))
    torch.use_deterministic_algorithms(True)
    for selected in manifest['selected_trials']:
        trial = int(selected['trial_id'])
        record = selected['trial_record']
        assert Path(record['predictions_file']).resolve().is_relative_to(branch_root.resolve())
        model_dir = folder/'selected_models'/f'trial_{trial:06d}'
        proof_path, model_path = model_dir/'replay_verification.json', model_dir/'model.pt'
        if not proof_path.exists() or not model_path.exists():
            if time.monotonic() >= deadline:
                raise TimeoutError('selected_stage_model_replay_budget; completed artifacts preserved')
            prediction, artifact = fit(copy.deepcopy(record['configuration']), frames, targets)
            with np.load(record['predictions_file']) as saved:
                errors = {split: float(np.max(np.abs(prediction[split]-saved[split]))) for split in prediction}
            assert max(errors.values()) < 1e-10, errors
            model_dir.mkdir(parents=True, exist_ok=True)
            temporary = model_path.with_suffix('.pt.tmp')
            torch.save({'configuration': record['configuration'], 'artifact': artifact}, temporary)
            temporary.replace(model_path)
            save_json(proof_path, {'max_errors': errors, 'exact_replay': True})
        proof = json.loads(proof_path.read_text())
        assert proof['exact_replay'] and max(proof['max_errors'].values()) < 1e-10
        replays.append({'trial_id': trial, 'model_path': str(model_path), 'model_sha256': sha(model_path),
                        'replay_proof': str(proof_path), 'weights_by_zone': selected['weights_by_zone']})
    value = {'stage': stage, 'model_count': len(replays), 'fit_source_sha256': sha(fit_source),
             'stage_manifest_sha256': sha(folder/'fusion_manifest.json'), 'models': replays}
    save_json(folder/'selected_stage_replay_manifest.json', value)
    return value
