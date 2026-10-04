#!/usr/bin/env python3
"""Parameterized, checkpointed event-only location search using production models.

KAN and ResNet are the actual energy architectures with K sigmoid outputs. LCS
uses the production positive/negative radial rule engine independently per zone.
Analog matching is a separate model family and is never relabeled a neural fit.
All model/ensemble/calibration choices use the declared validation set; it is a
selection set, not an independent performance estimate. No forecast target exists.
"""
from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import logging
import os
import shutil
from pathlib import Path
import sys
import time


def storage_available(path,config):
    """Reserve disk space for final models and PDFs; absent option preserves legacy behavior."""
    return shutil.disk_usage(path).free>=float(config.get('minimum_disk_free_mb',0))*1024**2

os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
os.environ.setdefault('MKL_NUM_THREADS', '2')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import average_precision_score
from src.models.kan import KANNetwork
from src.models.deep_learning import DeepTabularResNet
from src.uncompressed_pipeline.l1_engine import train_eval_trial_lcs

LOG = logging.getLogger('production_location')
FAMILIES = ['kan', 'deep_learning', 'lcs']
DEFAULT_SPACE = {
    'feature_counts': [4, 8, 12, 16, 24, 32, 48, 64, 'all'],
    'feature_selection': ['random', 'zone_contrast', 'body_group'],
    'feature_scope': ['all', 'astro_only', 'unshifted_astro'],
    'train_start_years': [1900, 1920, 1940, 1960, 1980, 1990, 2000, 2010],
    'scaling': ['minmax', 'standard', 'robust'],
    'prototype_embedding': [False, True],
    'hidden_dim': [16, 32, 64, 96], 'num_layers': [1, 2, 3, 4],
    'grid_size': [3, 5, 7], 'spline_order': [2, 3],
    'dropout': [0.0, 0.05, 0.1, 0.2],
    'learning_rate': [0.0003, 0.001, 0.003, 0.008],
    'epochs': [40, 80, 120, 200], 'weight_decay': [0.00001, 0.0001, 0.001],
    'positive_weighting': ['none', 'sqrt', 'balanced'],
    'population_size': [40, 80, 120, 180, 240],
    'crossover_rate': [0.3, 0.6, 0.9], 'mutation_rate': [0.01, 0.05, 0.15],
    'rule_center': [0.35, 0.5, 0.62, 0.75], 'rule_temperature': [0.03, 0.08, 0.2],
    'analog_metric': ['cosine', 'euclidean', 'manhattan'],
    'analog_neighbors': [1, 3, 5, 9, 15, 25],
    'analog_weight_power': [0.0, 1.0, 2.0, 4.0],
}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False, default=lambda x: x.item() if isinstance(x, np.generic) else str(x)) + '\n')
    tmp.replace(path)


def save_csv(path, frame):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.csv.tmp')
    frame.to_csv(tmp, index=False)
    tmp.replace(path)


def load_inputs(config, branch):
    base = Path(config['spatial_root']) / branch / '01_data'
    frames = {s: pd.read_csv(base / f'{s}_master.csv') for s in ['training', 'validation', 'prospective']}
    targets = sorted([c for c in frames['training'] if c.startswith('target_Zone_')], key=lambda c: int(c.rsplit('_', 1)[1]))
    assert targets == [f'target_Zone_{z}' for z in range(len(targets))] and len(targets) >= 2
    features = [c for c in frames['training'] if c.startswith(tuple(config.get('feature_prefixes', ['astro_', 'seis_', 'packed_'])))]
    assert features and not any(c.startswith(('target_', 'event_')) for c in features)
    for split, f in frames.items():
        assert f.date.is_unique and pd.to_datetime(f.date).is_monotonic_increasing
        assert np.isfinite(f[features].to_numpy(float)).all()
        assert not any('calm' in c.lower() for c in f)
        if split != 'prospective':
            assert f.event_count.gt(0).all() and f[targets].sum(axis=1).gt(0).all()
            assert np.isin(f[targets], [0, 1]).all() and f[targets].sum().gt(0).all()
        else:
            assert not any(c.startswith('target_') for c in f)
    assert max(frames['training'].date) < min(frames['validation'].date)
    ids = lambda f: set(';'.join(f.event_ids.astype(str)).split(';'))
    assert ids(frames['training']).isdisjoint(ids(frames['validation']))
    events = pd.read_csv(Path(config['spatial_root']) / '01_data/validation_events.csv')
    events = events.sort_values(['time', 'id'], kind='stable').reset_index(drop=True)
    lookup = {d: i for i, d in enumerate(frames['validation'].date)}
    event_rows = np.array([lookup[d] for d in events.date], int)
    truth = events.zone_id.to_numpy(int)
    assert np.array_equal(frames['validation'][targets].to_numpy()[event_rows, truth], np.ones(len(events)))
    return frames, targets, features, events, event_rows, truth


def metrics(y, p, rows, truth):
    p = np.asarray(p, float)
    assert p.shape == y.shape and np.isfinite(p).all()
    p = np.clip(p, 1e-7, 1 - 1e-7)
    predicted = p.argmax(axis=1)[rows]
    correct = predicted == truth
    recall = [float(correct[truth == z].mean()) for z in range(y.shape[1])]
    ap = [float(average_precision_score(y[:, z], p[:, z])) for z in range(y.shape[1])]
    top1, balanced, macro_ap = float(correct.mean()), float(np.mean(recall)), float(np.mean(ap))
    return {'quality_index': .5 * top1 + .3 * balanced + .2 * macro_ap,
            'event_top1_accuracy': top1, 'correct_earthquakes': int(correct.sum()),
            'earthquakes': len(truth), 'macro_zone_recall': balanced,
            'macro_average_precision': macro_ap, 'recall_per_zone': recall,
            'average_precision_per_zone': ap,
            'binary_cross_entropy': float(-np.mean(y * np.log(p) + (1-y) * np.log(1-p))),
            'brier_score': float(np.mean((y-p)**2))}


def quality_rank(m):
    return (m['quality_index'], m['event_top1_accuracy'], m['macro_zone_recall'], -m['binary_cross_entropy'])


def propose(trial_id, family, config, frames, targets, features, parent=None):
    seed = config['seed'] + trial_id * 1009
    rng = np.random.default_rng(seed)
    space = {**DEFAULT_SPACE, **config.get('search_space', {})}
    starts = [f'{year}-01-01' for year in space['train_start_years']
              if len(frames['training'].loc[frames['training'].date >= f'{year}-01-01']) >= config.get('minimum_training_rows', 30)
              and frames['training'].loc[frames['training'].date >= f'{year}-01-01', targets].sum().gt(0).all()]
    if not starts:
        starts = [str(frames['training'].date.min())]
    start = str(rng.choice(starts))
    training = frames['training'].loc[frames['training'].date >= start]
    scope = str(rng.choice(space['feature_scope']))
    eligible = [c for c in features if scope == 'all' or (c.startswith('astro_') and (scope != 'unshifted_astro' or '_shift_' not in c))]
    if not eligible:
        eligible = features
    counts = sorted({x for x in space['feature_counts'] if isinstance(x, int) and x <= len(eligible)} | {len(eligible)})
    n = int(rng.choice(counts))
    method = str(rng.choice(space['feature_selection']))
    if method == 'zone_contrast':
        x, y = training[eligible].to_numpy(float), training[targets].to_numpy(float)
        score = np.zeros(len(eligible))
        for z in range(len(targets)):
            pos = y[:, z] > 0
            if pos.all() or not pos.any():
                continue
            score += abs(x[pos].mean(0) - x[~pos].mean(0)) / (x.std(0) + .01)
        score += rng.uniform(0, .1, len(score))
        selected = [eligible[i] for i in np.argsort(-score, kind='stable')[:n]]
    elif method == 'body_group':
        bodies = sorted({c.split('_')[1] for c in eligible if c.startswith('astro_')})
        chosen = set(rng.choice(bodies, max(1, int(rng.integers(1, len(bodies)+1))), replace=False)) if bodies else set()
        selected = [c for c in eligible if not c.startswith('astro_') or c.split('_')[1] in chosen]
    else:
        selected = [str(c) for c in rng.choice(eligible, n, replace=False)]
    hp = {}
    for key, choices in space.items():
        if key in ['feature_counts', 'feature_selection', 'feature_scope', 'train_start_years']:
            continue
        value = rng.choice(choices)
        hp[key] = value.item() if isinstance(value, np.generic) else value
    cfg = {'trial_id': trial_id, 'family': family, 'seed': seed, 'features': selected,
           'feature_selection': method, 'feature_scope': scope, 'training_start': start,
           'hyperparameters': hp, 'refinement_parent_id': None}
    if parent is not None:
        old = parent['configuration']
        cfg['family'] = old['family']
        cfg['refinement_parent_id'] = old['trial_id']
        if rng.random() < .7:
            selected = list(old['features'])
            remove_count = min(max(0, len(selected)-2), int(rng.integers(0, max(2, len(selected)//3))))
            if remove_count:
                selected = [s for s in selected if s not in set(rng.choice(selected, remove_count, replace=False))]
            pool = [c for c in features if c not in selected]
            if pool:
                selected += [str(c) for c in rng.choice(pool, min(len(pool), int(rng.integers(1, 6))), replace=False)]
            cfg['features'] = selected
        if rng.random() < .75:
            cfg['training_start'] = old['training_start']
        cfg['hyperparameters'] = copy.deepcopy(old['hyperparameters'])
        for key in rng.choice(list(hp), min(4, len(hp)), replace=False):
            cfg['hyperparameters'][key] = hp[key]
    return cfg


def fit(config, frames, targets):
    tr = frames['training'].loc[frames['training'].date >= config['training_start']]
    y = tr[targets].to_numpy(np.float32)
    columns, hp = config['features'], config['hyperparameters']
    raw = {s: f[columns].to_numpy(np.float32) for s, f in {**frames, 'training': tr}.items()}
    train = raw['training']
    if hp['scaling'] == 'standard':
        center, scale = train.mean(0), train.std(0)
    elif hp['scaling'] == 'robust':
        center = np.median(train, axis=0)
        scale = np.quantile(train, .75, axis=0) - np.quantile(train, .25, axis=0)
    else:
        center, scale = train.min(0), np.ptp(train, axis=0)
    scale = np.where(scale < 1e-6, 1., scale)
    x = {s: np.clip((a-center)/scale, -8, 8).astype(np.float32) for s, a in raw.items()}
    config['scaler'] = {'fit_scope': 'selected training rows only', 'center': center.tolist(), 'scale': scale.tolist()}
    config['training_rows'] = len(tr)
    config['training_events'] = int(tr.event_count.sum())
    config['actual_training_start'], config['actual_training_end'] = str(tr.date.min()), str(tr.date.max())
    family, seed = config['family'], int(config['seed'])
    if family == 'analog':
        preds, neighbor_indices = {}, {}
        for split, a in x.items():
            if hp['analog_metric'] == 'cosine':
                left = a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-8)
                right = x['training'] / np.maximum(np.linalg.norm(x['training'], axis=1, keepdims=True), 1e-8)
                distance = np.maximum(0, 1-left @ right.T)
            else:
                delta = a[:, None, :] - x['training'][None, :, :]
                distance = np.mean(abs(delta) if hp['analog_metric'] == 'manhattan' else delta**2, axis=2)
            k = min(int(hp['analog_neighbors']), len(tr))
            indices = np.argsort(distance, axis=1, kind='stable')[:, :k]
            chosen = np.take_along_axis(distance, indices, axis=1)
            weights = np.power(np.maximum(chosen, 1e-5), -float(hp['analog_weight_power']))
            weights /= weights.sum(axis=1, keepdims=True)
            preds[split] = np.clip(np.sum(y[indices] * weights[:, :, None], axis=1), .001, .999)
            neighbor_indices[split] = {'training_row_indices': indices.tolist(), 'weights': weights.tolist(), 'distances': chosen.tolist()}
        artifact = {'kind': 'historical_analog', 'training_dates': tr.date.tolist(), 'neighbor_matches': neighbor_indices}
    elif family == 'lcs':
        preds = {s: np.zeros((len(a), len(targets)), float) for s, a in x.items()}
        rules = []
        for z in range(len(targets)):
            a, b, c, artifact_z = train_eval_trial_lcs(x['training'], y[:, z], x['validation'], x['prospective'], hp, seed+z)
            preds['training'][:, z], preds['validation'][:, z], preds['prospective'][:, z] = a, b, c
            rules.append(artifact_z)
        artifact = {'kind': 'production_LCS_one_vs_rest', 'rules_by_zone': rules}
    else:
        if hp['prototype_embedding']:
            centers = np.stack([np.median(x['training'][y[:, z] > 0], axis=0) for z in range(len(targets))])
            for split in x:
                distance = np.mean((x[split][:, None, :] - centers[None, :, :])**2, axis=2)
                x[split] = np.hstack([x[split], np.minimum(distance, 25)]).astype(np.float32)
            config['training_zone_prototypes'] = centers.tolist()
        torch.manual_seed(seed)
        if family == 'kan':
            # B-spline domain mapping, with all transform parameters from training.
            x = {s: (np.tanh(a) * .9).astype(np.float32) for s, a in x.items()}
            net = KANNetwork(x['training'].shape[1], len(targets), (int(hp['hidden_dim']),), int(hp['grid_size']), int(hp['spline_order']))
        else:
            net = DeepTabularResNet(x['training'].shape[1], len(targets), int(hp['hidden_dim']), int(hp['num_layers']), float(hp['dropout']))
        counts = y.sum(0)
        pw = (len(y)-counts) / np.maximum(counts, 1)
        if hp['positive_weighting'] == 'sqrt':
            pw = np.sqrt(pw)
        elif hp['positive_weighting'] == 'none':
            pw = np.ones_like(pw)
        criterion = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(np.clip(pw, .1, 30), dtype=torch.float32))
        optimizer = torch.optim.AdamW(net.parameters(), lr=float(hp['learning_rate']), weight_decay=float(hp['weight_decay']))
        xt, yt = torch.tensor(x['training']), torch.tensor(y)
        net.train()
        for _ in range(int(hp['epochs'])):
            optimizer.zero_grad()
            loss = criterion(net(xt), yt)
            if not torch.isfinite(loss):
                raise FloatingPointError('nonfinite training loss')
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 5.)
            optimizer.step()
        net.eval()
        with torch.no_grad():
            preds = {s: torch.sigmoid(net(torch.tensor(a))).numpy().astype(float) for s, a in x.items()}
        artifact = {'kind': family, 'state_dict': {k: v.detach().cpu() for k, v in net.state_dict().items()}, 'positive_weights': pw.tolist()}
    return preds, artifact


def export_prediction(master, p, path):
    metadata = [c for c in master if not c.startswith(('astro_', 'seis_', 'packed_'))]
    f = master[metadata].copy()
    for z in range(p.shape[1]):
        f[f'prob_Zone_{z}'] = p[:, z]
    f['predicted_zone_id'] = p.argmax(1)
    save_csv(path, f)


def select_fusion(records, frames, targets, rows, truth, output, config, seed_offset=0):
    """Select shared or zone-specialist ensembles, then bounded logit calibration."""
    output.mkdir(parents=True, exist_ok=True)
    y = frames['validation'][targets].to_numpy(float)
    ordered = sorted(records, key=lambda r: quality_rank(r['metrics']), reverse=True)
    max_pool = int(config.get('ensemble_pool', 120))
    candidates_pool = ordered[:max_pool]
    # Include the best per-zone ranking candidates, even if global quality is weak.
    ids = {r['configuration']['trial_id'] for r in candidates_pool}
    for z in range(len(targets)):
        for r in sorted(records, key=lambda r: r['metrics']['average_precision_per_zone'][z], reverse=True)[:10]:
            if r['configuration']['trial_id'] not in ids:
                candidates_pool.append(r); ids.add(r['configuration']['trial_id'])
    arrays = [np.load(r['predictions_file']) for r in candidates_pool]
    val = np.stack([a['validation'] for a in arrays]); future = np.stack([a['prospective'] for a in arrays])
    candidates = []
    def evaluate(weights, label):
        pv = np.sum(val*weights[:, None, :], axis=0)
        pf = np.sum(future*weights[:, None, :], axis=0)
        q = metrics(y, pv, rows, truth)
        candidates.append({'id': len(candidates), 'method': label, **q})
        return q, pv, pf, weights.copy(), label
    best = None
    for n in [1, 2, 3, 5, 10, 20, 40, 80, len(candidates_pool)]:
        n = min(n, len(candidates_pool))
        weights = np.zeros((len(candidates_pool), len(targets))); weights[:n] = 1/n
        item = evaluate(weights, f'best_{n}_uniform')
        if best is None or quality_rank(item[0]) > quality_rank(best[0]): best = item
    for n in [1, 3, 5, 10, 20]:
        weights = np.zeros((len(candidates_pool), len(targets)))
        for z in range(len(targets)):
            ranked = sorted(range(len(candidates_pool)), key=lambda i: candidates_pool[i]['metrics']['average_precision_per_zone'][z], reverse=True)[:n]
            weights[ranked, z] = 1/len(ranked)
        item = evaluate(weights, f'zone_AP_specialists_top_{n}')
        if quality_rank(item[0]) > quality_rank(best[0]): best = item
    rng = np.random.default_rng(config['seed'] + seed_offset)
    for step in range(int(config.get('fusion_trials', 2000))):
        weights = best[3].copy()
        if rng.random() < .5:
            z = int(rng.integers(len(targets)))
            i = int(rng.integers(len(candidates_pool)))
            alpha = float(rng.choice([.1, .25, .5, 1.]))
            weights[:, z] *= 1-alpha; weights[i, z] += alpha
        else:
            i = int(rng.integers(min(max_pool, len(candidates_pool))))
            alpha = float(rng.choice([.05, .1, .25, .5]))
            weights *= 1-alpha; weights[i] += alpha
        item = evaluate(weights, 'validation_selected_specialist_weight_search')
        if quality_rank(item[0]) > quality_rank(best[0]): best = item
    q, pv, pf, weights, method = best
    selected = [{'trial_id': r['configuration']['trial_id'], 'weights_by_zone': weights[i].tolist(), 'trial_record': r}
                for i, r in enumerate(candidates_pool) if weights[i].sum() > 1e-12]
    raw_val, raw_future = pv.copy(), pf.copy()
    # Classwise calibration is selected on validation and then frozen identically
    # for forecast. It never receives future zone labels or requested map regions.
    lv = np.log(np.clip(pv, 1e-6, 1-1e-6) / np.clip(1-pv, 1e-6, 1))
    lf = np.log(np.clip(pf, 1e-6, 1-1e-6) / np.clip(1-pf, 1e-6, 1))
    bias, temperature = np.zeros(len(targets)), 1.
    sigmoid = lambda a: 1/(1+np.exp(-np.clip(a, -30, 30)))
    calibration_rows = []
    for step in range(int(config.get('calibration_trials', 3000))):
        b = bias.copy()
        b[int(rng.integers(len(targets)))] += float(rng.choice([-.5, -.2, -.1, -.05, .05, .1, .2, .5]))
        b = np.clip(b, -4, 4)
        t = float(rng.choice([.2, .35, .5, .7, 1., 1.5, 2.]))
        cv, cf = sigmoid((lv+b)/t), sigmoid((lf+b)/t)
        cq = metrics(y, cv, rows, truth)
        calibration_rows.append({'trial': step+1, 'bias': json.dumps(b.tolist()), 'temperature': t, **cq})
        if quality_rank(cq) > quality_rank(q):
            q, pv, pf, bias, temperature = cq, cv, cf, b, t
    export_prediction(frames['validation'], pv, output/'validation_predictions.csv')
    export_prediction(frames['prospective'], pf, output/'prospective_forecast.csv')
    export_prediction(frames['validation'], raw_val, output/'uncalibrated_validation_predictions.csv')
    export_prediction(frames['prospective'], raw_future, output/'uncalibrated_prospective_forecast.csv')
    save_csv(output/'fusion_candidates.csv', pd.DataFrame(candidates))
    save_csv(output/'calibration_candidates.csv', pd.DataFrame(calibration_rows))
    manifest = {'metrics': q, 'method': method, 'selected_trials': selected,
                'calibration': {'logit_bias_by_zone': bias.tolist(), 'temperature': temperature,
                                'fit_scope': 'validation selection', 'formula': 'sigmoid((logit(weighted_marginal)+bias)/temperature)'},
                'same_transform_on_validation_and_forecast': True,
                'candidate_count': len(candidates), 'calibration_trials': len(calibration_rows)}
    save_json(output/'fusion_manifest.json', manifest)
    return manifest


def run(config, branch, output, mode='learned'):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    lock = (output/'search.lock').open('w'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    frames, targets, features, events, event_rows, truth = load_inputs(config, branch)
    config = copy.deepcopy(config)
    branch_settings = config['branches'][branch]
    config.update(branch_settings)
    identity = {'config': config, 'branch': branch, 'mode': mode,
                'source_sha256': sha(__file__),
                'architecture_hashes': {n:sha(Path(__file__).parent / p) for n,p in {'KAN':'models/kan.py','DeepTabularResNet':'models/deep_learning.py','LCS':'uncompressed_pipeline/l1_engine.py'}.items()},
                'input_hashes': {s: sha(Path(config['spatial_root'])/branch/'01_data'/f'{s}_master.csv') for s in frames}}
    if (output/'search_identity.json').exists():
        assert json.loads((output/'search_identity.json').read_text()) == identity, 'Changed source/config/input; use a new output directory.'
    else: save_json(output/'search_identity.json', identity)
    started = time.time()
    old_state = json.loads((output/'search_state.json').read_text()) if (output/'search_state.json').exists() else {}
    elapsed_before = old_state.get('elapsed_seconds', 0.)
    deadline = started + max(0., float(config.get('max_seconds',3600)) - elapsed_before)
    screening_deadline = deadline - float(config.get('refinement_reserve_seconds',600)) - float(config.get('report_reserve_seconds',180))
    fit_deadline = deadline - float(config.get('report_reserve_seconds',180))
    records = []
    for stage in ['02_level1', '04_level2_deep_meta_optimizer']:
        for p in sorted((output/stage/'trial_cache').glob('trial_*/record.json')):
            record = json.loads(p.read_text())
            assert Path(record['predictions_file']).exists()
            records.append(record)
    records.sort(key=lambda r:r['configuration']['trial_id'])
    assert [r['configuration']['trial_id'] for r in records] == list(range(1,len(records)+1))
    y = frames['validation'][targets].to_numpy(float)
    stage_counts = lambda stage: sum(r['stage'] == stage for r in records)
    def progress(status, stage, reason=None):
        counts={f:sum(r['configuration']['family']==f for r in records) for f in (['analog'] if mode=='analog' else FAMILIES)}
        best=max(records,key=lambda r:quality_rank(r['metrics']))['metrics'] if records else None
        save_json(output/'search_state.json', {'status':status,'stage':stage,'completed_trials':len(records),'family_counts':counts,
                  'best_individual_metrics':best,'elapsed_seconds':elapsed_before+time.time()-started,
                  'max_seconds':config.get('max_seconds',3600),'stop_reason':reason,'updated_epoch':time.time()})
    def commit(family, stage, parent=None):
        tid=len(records)+1
        cfg=propose(tid,family,config,frames,targets,features,parent)
        start=time.time()
        pred,artifact=fit(cfg,frames,targets)
        q=metrics(y,pred['validation'],event_rows,truth)
        d=output/stage/'trial_cache'/f'trial_{tid:06d}';d.mkdir(parents=True,exist_ok=True)
        with (d/'predictions.npz.tmp').open('wb') as f:np.savez_compressed(f,**pred)
        (d/'predictions.npz.tmp').replace(d/'predictions.npz')
        record={'configuration':cfg,'metrics':q,'stage':stage,'elapsed_seconds':time.time()-start,'predictions_file':str((d/'predictions.npz').resolve())}
        # Commit configuration and every numerical curve; selected fits are replayed
        # and their model/rule artifacts saved with exact prediction checks below.
        save_json(d/'record.json',record);records.append(record)
        if tid%25==0 or tid==1:
            progress('running',stage)
            LOG.info('%s %s %s trials=%d Q=%.4f hit=%d/%d bestQ=%.4f',branch,mode,stage,tid,q['quality_index'],q['correct_earthquakes'],q['earthquakes'],max(r['metrics']['quality_index'] for r in records))
    progress('running','02_level1')
    cap=int(config.get('analog_trials',3000)) if mode=='analog' else int(config['trials_per_family'])*3
    while stage_counts('02_level1')<cap and time.time()<screening_deadline and storage_available(output,config):
        n=stage_counts('02_level1')
        commit('analog' if mode=='analog' else FAMILIES[n%3],'02_level1')
        if len(records)>=int(config.get('minimum_quality_trials',900)) and records[-1]['metrics']['quality_index']>=float(config.get('quality_target',.995)):
            break
    if not records:
        progress('stopped','02_level1','no_completed_trials_before_deadline');return 75
    initial=[r for r in records if r['stage']=='02_level1']
    if not (output/'03_level1_fusion/fusion_manifest.json').exists():
        select_fusion(initial,frames,targets,event_rows,truth,output/'03_level1_fusion',config,30001)
    parents=sorted(initial,key=lambda r:quality_rank(r['metrics']),reverse=True)[:32]
    refinement_cap=int(config.get('refinement_trials',3000)) if mode=='learned' else int(config.get('analog_refinement_trials',600))
    while stage_counts('04_level2_deep_meta_optimizer')<refinement_cap and time.time()<fit_deadline and storage_available(output,config):
        n=stage_counts('04_level2_deep_meta_optimizer');parent=parents[n%len(parents)]
        commit(parent['configuration']['family'],'04_level2_deep_meta_optimizer',parent)
    final=select_fusion(records,frames,targets,event_rows,truth,output/'05_level3_final_fusion',config,60001)
    unique={r['trial_id']:r['trial_record'] for r in final['selected_trials']}
    for tid,rec in unique.items():
        d=output/'05_level3_final_fusion/selected_models'/f'trial_{tid:06d}';d.mkdir(parents=True,exist_ok=True)
        if (d/'replay_verification.json').exists():continue
        pred,artifact=fit(copy.deepcopy(rec['configuration']),frames,targets)
        saved=np.load(rec['predictions_file'])
        errors={s:float(np.max(abs(pred[s]-saved[s]))) for s in pred}
        assert max(errors.values())<1e-10, errors
        torch.save({'configuration':rec['configuration'],'artifact':artifact},d/'model.pt')
        save_json(d/'replay_verification.json',{'max_errors':errors,'exact_replay':True})
    flat=[]
    for r in records:
        c=r['configuration'];flat.append({'trial_id':c['trial_id'],'stage':r['stage'],'family':c['family'],'seed':c['seed'],
                 'training_start':c['training_start'],'training_rows':c['training_rows'],'training_events':c['training_events'],
                 'features':json.dumps(c['features']),'hyperparameters':json.dumps(c['hyperparameters']),
                 **{k:v for k,v in r['metrics'].items() if not isinstance(v,list)},
                 **{f'feat__{f}':int(f in c['features']) for f in features}})
    save_csv(output/'all_trials.csv',pd.DataFrame(flat))
    save_json(output/'completed_manifest.json',{'identity':identity,'completed_trials':len(records),'initial_trials':len(initial),
                 'refinement_trials':len(records)-len(initial),'final_metrics':final['metrics'],'selected_model_count':len(unique),
                 'validation_rows':len(frames['validation']),'validation_events':len(events),'target_columns':targets,
                 'event_only':True,'validation_is_selection_set':True,'family_labels_share_architecture':False})
    progress('complete','05_level3_final_fusion','disk_reserve_reached' if not storage_available(output,config) else 'trial_caps_reached' if len(initial)==cap and len(records)-len(initial)==refinement_cap else 'time_or_quality_limit')
    LOG.info('%s %s FINISHED %d trials: %s',branch,mode,len(records),final['metrics'])
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--branch',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--mode',choices=['learned','analog'],default='learned')
    args=parser.parse_args()
    config=json.loads(args.config.read_text())
    torch.set_num_threads(int(config.get('threads',2)));torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    return run(config,args.branch,args.output,args.mode)


if __name__=='__main__':
    raise SystemExit(main())
