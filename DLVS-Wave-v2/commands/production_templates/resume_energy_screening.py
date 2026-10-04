#!/usr/bin/env python3
"""Resume actual production energy screening from persisted trials, in bounded chunks.

The original engine owns every random draw and fit. Chunk-local identifiers are
mapped back to family-local identifiers; global identifiers and seeds are kept.
Partially completed chunk CSVs are ingested on restart before any new fit starts.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import shutil
import sys
import time
from pathlib import Path

import recompute as run
import numpy as np
import pandas as pd
from src.uncompressed_pipeline import l1_engine, l1_engine_reference_main


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2))
    temporary.replace(path)


def equal_predictions(actual, expected):
    pd.testing.assert_frame_equal(actual.reset_index(drop=True), expected.reset_index(drop=True), check_exact=False,
                                  rtol=1e-12, atol=1e-12, check_dtype=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--branch', choices=['main_bodies_branch','minor_bodies_branch'], required=True)
    parser.add_argument('--family', choices=['kan', 'deep_learning', 'lcs'], required=True)
    parser.add_argument('--chunk-size', type=int, default=200)
    parser.add_argument('--max-seconds', type=float, default=540,
                        help='Shared fit/package budget; a completed fit is preserved.')
    args = parser.parse_args()
    if args.chunk_size < 1 or args.max_seconds <= 0:
        parser.error('Chunk size and time budget must be positive.')
    deadline = time.time() + args.max_seconds
    family = args.family
    main_branch = args.branch == 'main_bodies_branch'
    engine = l1_engine_reference_main if main_branch else l1_engine
    family_index = ['kan','deep_learning','lcs'].index(family)
    branch_seed = int(run.CONFIG['main_seed']) + family_index * 100000 if main_branch else int(run.CONFIG['minor_seed'])
    branch = run.ENERGY / args.branch
    study = branch / '02_level1' / f'study_{family}'
    study.mkdir(parents=True, exist_ok=True)
    canonical_csv = study / f'trials_{family}.csv'
    cache = study / 'trial_predictions'
    cache.mkdir(exist_ok=True)
    audit = run.ROOT / '00_reproduction_audit/energy_screening_resume' / args.branch / family
    chunks = audit / 'chunks'
    chunks.mkdir(parents=True, exist_ok=True)
    lock = (audit / 'driver.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    counts = run.CONFIG['main_l1_counts' if main_branch else 'minor_l1_counts']
    order = ['kan', 'deep_learning', 'lcs']
    target = int(counts[family])
    offset = sum(int(counts[name]) for name in order[:order.index(family)])
    records = pd.read_csv(canonical_csv, low_memory=False).to_dict('records') if canonical_csv.exists() else []
    original_count = len(records)
    assert [int(row['trial_id']) for row in records] == list(range(len(records)))
    assert [int(row['global_trial_id']) for row in records] == list(range(offset, offset + len(records)))
    assert len(records) <= target

    def save_records():
        temporary = canonical_csv.with_suffix('.csv.tmp')
        pd.DataFrame(records).fillna(0).to_csv(temporary, index=False)
        temporary.replace(canonical_csv)
        atomic_json(audit / 'progress.json', {
            'family': family, 'completed_trials': len(records), 'requested_trials': target,
            'chunk_size': args.chunk_size, 'max_seconds_this_invocation': args.max_seconds,
            'status': 'running', 'canonical_csv': str(canonical_csv),
            'recomputed_this_invocation_or_recovered_from_chunks': len(records) - original_count,
        })

    def ingest(csv_path):
        if not csv_path.is_file() or csv_path.stat().st_size == 0:
            return 0
        chunk = pd.read_csv(csv_path, low_memory=False)
        added = 0
        for raw in chunk.to_dict('records'):
            serial = int(raw['global_trial_id'])
            local = serial - offset
            assert raw['network_type'] == family and 0 <= local < target
            assert int(raw['seed']) == branch_seed + serial * 1009
            if local < len(records):
                old = records[local]
                assert int(old['global_trial_id']) == serial
                assert old['feature_mask'] == raw['feature_mask']
                assert np.isclose(old['composite_needle_loss'], raw['composite_needle_loss'], rtol=0, atol=1e-12)
                continue
            assert local == len(records), ('Non-contiguous recovered chunk', local, len(records), csv_path)
            copied = dict(raw)
            copied['trial_id'] = local
            for field, suffix, length in [('validation_prediction_csv', 'validation', 54),
                                           ('forecast_prediction_csv', 'forecast', 26)]:
                source = Path(raw[field])
                assert source.is_relative_to(run.ROOT) and source.is_file(), source
                frame = pd.read_csv(source)
                assert len(frame) == length and frame.predicted_prob.notna().all()
                destination = cache / f'trial_{local:06d}_{suffix}.csv'
                if destination.exists():
                    equal_predictions(pd.read_csv(destination), frame)
                else:
                    temporary = destination.with_suffix('.csv.tmp')
                    shutil.copy2(source, temporary)
                    temporary.replace(destination)
                copied[field] = str(destination)
            records.append(copied)
            added += 1
        if added:
            save_records()
            run.LOG.info('ENERGY RESUME %s: %d/%d canonical trials saved (%d recovered).', family, len(records), target, added)
        return added

    for csv_path in sorted(chunks.glob(f'chunk_*/trials_{family}.csv')):
        ingest(csv_path)
    manifest = json.loads((branch / '01_data/dual_master_manifest.json').read_text())
    is_bitwise = family == 'lcs'
    master = pd.read_csv(branch / '01_data' / ('master_7d_bitwise_compacted_normalized.csv' if is_bitwise else 'master_7d_lean_uncompressed_normalized.csv'), parse_dates=['date'])
    features = manifest['bitwise_features' if is_bitwise else 'lean_features']
    # Fitting chunks need no partial best/worst PDF packages. Original fits and
    # per-trial atomic CSV/cache writes remain unchanged.
    engine.package_best_worst_trials = lambda *unused: None
    while len(records) < target and time.time() < deadline:
        first = len(records)
        count = min(args.chunk_size, target - first)
        chunk_dir = chunks / f'chunk_{first:06d}'
        run.LOG.info('ENERGY RESUME %s: fitting original family trials %d..%d (global offset %d).', family, first, first + count - 1, offset + first)
        engine.run_microstudy(family, master, features, chunk_dir, count,
                             offset + first, deadline_epoch=deadline,
                             seed=branch_seed)
        added = ingest(chunk_dir / f'trials_{family}.csv')
        if added == 0:
            break
    if len(records) < target:
        run.LOG.info('ENERGY RESUME %s paused at its time budget: %d/%d. Restart the same command to continue.', family, len(records), target)
        return 75

    complete = pd.DataFrame(records)
    # Reference values are read only after all requested fresh trials exist.
    reference = pd.read_csv(run.REF / '01_energy_forecast_m77' / args.branch / '02_level1' / f'study_{family}' / f'trials_{family}.csv', low_memory=False)
    numeric = [name for name in complete.select_dtypes('number') if name in reference.select_dtypes('number')
               and not any(term in name for term in ['elapsed', 'execution', 'quality_time'])]
    assert len(reference) == target
    assert np.allclose(complete[numeric], reference[numeric], rtol=1e-12, atol=1e-12, equal_nan=True)
    assert complete.feature_mask.equals(reference.feature_mask)
    for row in records:
        for field, length in [('validation_prediction_csv', 54), ('forecast_prediction_csv', 26)]:
            prediction = Path(row[field])
            assert prediction.is_relative_to(run.ROOT) and prediction.is_file()
            assert len(pd.read_csv(prediction)) == length
    proof_path = audit / 'complete_comparison.json'
    proof = json.loads(proof_path.read_text()) if proof_path.exists() else {}
    proof.update(family=family, completed_trials=target,
                 all_numeric_nontime_columns_match_reference_1e_12=True,
                 all_feature_masks_match=True, all_prediction_csvs_complete=True)
    proof.setdefault('package_replays', [])
    atomic_json(proof_path, proof)
    ranked = complete.sort_values(['composite_needle_loss', 'train_loss'], kind='stable')
    for kind, selected in [('best', ranked.head(3)), ('worst', ranked.tail(3))]:
        for rank, (_, row) in enumerate(selected.iterrows(), 1):
            package = study / f'{kind}_{rank}'
            expected_files = ['trial_config.json', 'trial_metrics.json', 'validation_predictions.csv',
                              'prospective_forecast.csv', 'validation_report.pdf', 'prospective_forecast.pdf',
                              'rules.json' if is_bitwise else 'model_weights.pt']
            previous = [entry for entry in proof['package_replays'] if entry['package'] == str(package) and entry['trial_id'] == int(row.trial_id)]
            if previous and all((package / name).is_file() and (package / name).stat().st_size > 0 for name in expected_files):
                continue
            if time.time() >= deadline:
                run.LOG.info('ENERGY RESUME %s paused before packaging %s; all %d trials preserved.', family, package.name, target)
                return 75
            captured = []
            engine.package_best_worst_trials = lambda outputs, *unused: captured.extend(outputs)
            replay_dir = audit / 'package_replays' / f'trial_{int(row.trial_id):06d}'
            engine.run_microstudy(family, master, features, replay_dir, 1,
                                 int(row.global_trial_id), seed=branch_seed)
            assert len(captured) == 1
            trial = captured[0]
            for key, field in [('val_pred_df', 'validation_prediction_csv'), ('prospective_df', 'forecast_prediction_csv')]:
                equal_predictions(trial[key].assign(date=lambda x: x.date.astype(str)),
                                  pd.read_csv(row[field]).assign(date=lambda x: x.date.astype(str)))
            assert trial['row']['feature_mask'] == row.feature_mask
            assert np.isclose(trial['row']['composite_needle_loss'], row.composite_needle_loss, rtol=0, atol=1e-12)
            trial['trial_id'] = int(row.trial_id)
            trial['row'] = row.to_dict()
            engine._write_trial_package(package, trial, master, f'{kind.upper()} {rank} ({family.upper()} Trial #{int(row.trial_id)})')
            assert all((package / name).is_file() for name in expected_files)
            proof['package_replays'].append({'trial_id': int(row.trial_id), 'package': str(package),
                                             'replayed_predictions_equal_saved_new_trial_1e_12': True})
            atomic_json(proof_path, proof)
    # Reload the state immediately before merging our one completed checkpoint.
    with (run.ROOT / '00_reproduction_audit/energy_screening_resume/state.lock').open('w') as state_lock:
        fcntl.flock(state_lock, fcntl.LOCK_EX)
        run.STATE.clear()
        run.STATE.update(json.loads(run.STATE_PATH.read_text()))
        run.STATE['status'] = 'running'
        run.STATE.pop('error', None)
        run.checkpoint(f'{args.branch}_L1_{family}')
    atomic_json(audit / 'progress.json', {'family': family, 'completed_trials': target,
                                         'requested_trials': target, 'status': 'complete',
                                         'all_six_packages_verified': True, 'proof': str(proof_path)})
    run.LOG.info('ENERGY RESUME %s COMPLETE: %d original trials plus six verified replay packages.', family, target)
    return 0


if __name__ == '__main__':
    sys.exit(main())
