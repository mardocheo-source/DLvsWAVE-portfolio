#!/usr/bin/env python3
"""Standalone entry point for the maintained World / single-region pipeline.

Run ``commands/forecast.sh --help`` for commands and see
``docs/FORECAST_PIPELINE_GUIDE.md`` for protocols, examples and limitations.
New studies freeze Python source before execution. Resume verifies that frozen
source and configuration; it never imports a newer fitter into an old study.
Preflight is read-only and does not download data or train models.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import uuid

PROJECT = Path(__file__).resolve().parent.parent
PACKAGES = {'numpy': 'numpy', 'pandas': 'pandas', 'scipy': 'scipy',
            'sklearn': 'scikit-learn', 'torch': 'torch', 'matplotlib': 'matplotlib',
            'pypdf': 'pypdf', 'astroquery': 'astroquery', 'mpmath': 'mpmath',
            'threadpoolctl': 'threadpoolctl', 'mpl_toolkits.basemap': 'basemap'}


def read_json(path):
    return json.loads(Path(path).read_text())


def source_hashes(directory):
    """Hash only Python source; trial arrays, PDFs and bytecode are excluded."""
    directory = Path(directory)
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob('*.py'))}


def validate(config):
    """Reject incompatible contracts before creating a study or spending compute."""
    errors = []
    required = ['training_start', 'catalog_cutoff', 'forecast_start', 'forecast_end',
                'download_floor', 'branches', 'maximum_study_seconds', 'maximum_node_seconds']
    errors.extend(f'Missing setting: {key}' for key in required if key not in config)
    if errors:
        raise ValueError('\n'.join(errors))
    from forecast_magnitudes import validate as validate_magnitudes
    validate_magnitudes(config)
    from forecast_search_policy import validate as validate_search_policy
    validate_search_policy(config)
    def date(key):
        return datetime.fromisoformat(config[key].replace('Z', '+00:00')).replace(tzinfo=None)
    if not date('training_start') < date('catalog_cutoff') < date('forecast_start') <= date('forecast_end'):
        errors.append('Require training_start < catalog_cutoff < forecast_start <= forecast_end.')
    if not 0 <= config.get('initial_geo_level', 0) <= config.get('max_geo_level', 3) <= 4:
        errors.append('Geographic levels must satisfy 0 <= initial <= maximum <= 4.')
    if set(config['branches']) != {'main_bodies_branch', 'minor_bodies_branch'}:
        errors.append('Both main_bodies_branch and minor_bodies_branch are required.')
    for branch, settings in config['branches'].items():
        if settings.get('trials_per_family', 0) < 1 or settings.get('refinement_trials', 0) < 0:
            errors.append(f'Invalid trial limits for {branch}.')
    for key in ['maximum_study_seconds', 'maximum_node_seconds', 'magnitude_step']:
        value = config.get(key, .1)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            errors.append(f'{key} must be finite and positive.')
    if not 0 <= config.get('main_fusion_weight', .85) <= 1:
        errors.append('main_fusion_weight must be in [0, 1].')
    if config.get('forecast_mode', 'one_shot') != 'one_shot':
        errors.append('This runner supports fixed one-shot inference only.')
    if config.get('selection_mode', 'first_peak') not in ['first_event', 'first_peak', 'largest_peak', 'largest_observed_peak']:
        errors.append('Unsupported selection_mode.')
    if config.get('energy_validation_events', 2) not in [2, 3]:
        errors.append('Energy validation supports 2 or 3 event weeks; location uses its own larger set.')
    if config.get('location_feature_prefixes', ['astro_']) != ['astro_']:
        errors.append('World location currently supports astronomical features only.')
    if config.get('maximum_location_validation_events') is not None:
        cap=config['maximum_location_validation_events']
        if not isinstance(cap,int) or cap<config.get('minimum_location_validation_events',12):
            errors.append('maximum_location_validation_events must be an integer at least the minimum event count.')
    if not isinstance(config.get('location_window_refinement_max_steps',3),int) or not 0<=config.get('location_window_refinement_max_steps',3)<=10:
        errors.append('location_window_refinement_max_steps must be an integer from 0 to 10.')
    origin_refit=config.get('energy_protocol','legacy_astro')=='origin_refit_astro_only'
    if config.get('energy_protocol','legacy_astro') not in ['legacy_astro','origin_refit_astro_only']:
        errors.append('Unknown energy_protocol.')
    if origin_refit:
        if config.get('infill_seed_mode','pi_pairs') not in ['pi_pairs','trial_seed']:
            errors.append('infill_seed_mode must be pi_pairs or trial_seed.')
        if config.get('terminal_infill','all_observed')!='all_observed':
            errors.append('The new protocol must retain all observed terminal weeks.')
        if not isinstance(config.get('pi_pair_offset',0),int) or config.get('pi_pair_offset',0)<0:
            errors.append('pi_pair_offset must be a nonnegative integer.')
        if config.get('bitwise_energy',True) is not True:
            errors.append('The new protocol uses training-only bitwise astronomy for LCS.')
    for key in (['seismic_lag_weeks'] if origin_refit else ['infill_seed_mode', 'terminal_infill', 'seismic_lag_weeks', 'bitwise_energy']):
        if key in config:
            errors.append(f'{key} is incompatible with the selected World energy protocol. See the guide.')
    offsets=config.get('astronomy_offset_weeks',[-13,4,13])
    if not isinstance(offsets,list) or not offsets or not all(isinstance(x,int) and abs(x)<=104 for x in offsets):
        errors.append('astronomy_offset_weeks must be a nonempty list of integer offsets within 104 weeks.')
    for rule in config.get('initial_membership_rules', []):
        if rule.get('type') != 'rectangle':
            continue  # Legacy spherical rules are checked by membership().
        bounds = rule.get('bounds', [])
        if len(bounds) != 4 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in bounds):
            errors.append('Rectangle bounds must contain four finite numbers.'); continue
        south, north, west, east = bounds
        if not -90 <= south < north <= 90 or not 0 < east-west <= 360:
            errors.append('Rectangle: south < north, west < east, longitude width <= 360; unwrap dateline crossings.')
    for key in ['input_cache_dir', 'astronomy_raw_cache']:
        if config.get(key) and not Path(config[key]).is_dir():
            errors.append(f'{key} does not exist: {config[key]}')
    if errors:
        raise ValueError('\n'.join(errors))


def environment():
    """Record the numeric runtime; wall-time-limited searches can differ by host."""
    packages = {}
    for module, distribution in PACKAGES.items():
        if importlib.util.find_spec(module) is None:
            raise ValueError(f'Missing {distribution}; install requirements-forecast.txt with this Python interpreter.')
        packages[distribution] = importlib.metadata.version(distribution)
    return {'python': sys.version, 'platform': platform.platform(), 'packages': packages,
            'threads': {key: os.environ.get(key) for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']}}


def execute(study, extra=()):
    """Use only the study snapshot; inherited PYTHONPATH cannot select live code."""
    study = Path(study).resolve()
    frozen = study/'source_snapshot/src'
    expected = read_json(study/'source_manifest.json')
    if expected != source_hashes(frozen):
        raise ValueError('Frozen source differs from source_manifest.json; refusing resume.')
    config = study/'run_configuration.json'
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join([str(frozen.parent), str(frozen)])
    argv = [sys.executable, str(frozen/'run_global_recursive_forecast.py'),
            '--config', str(config), '--output', str(study), '--resume', *extra]
    return subprocess.call(argv, env=env, cwd=study)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ['check', 'run']:
        p = commands.add_parser(command, help='Read-only preflight' if command == 'check' else 'Create a new frozen study and execute it')
        p.add_argument('--config', type=Path, required=True, help='JSON configuration; cache paths are relative to this file')
        from forecast_magnitudes import OPTIONS
        for option,help_text in OPTIONS.items():
            p.add_argument('--'+option.replace('_','-'),type=float,default=None,help=help_text+'; overrides JSON')
        if command == 'run':
            p.add_argument('--output', type=Path, help='New directory; default: studies_output/<UTC>_<label>_<ID>')
            p.add_argument('--label', default='world', help='Short study name, e.g. japan_region or world')
            p.add_argument('--inputs-only', action='store_true', help='Download/verify inputs, then stop before fitting')
            p.add_argument('--initialize-only', action='store_true', help='Freeze source/configuration and create run.sh; do not download or fit')
    p = commands.add_parser('resume', help='Continue a study using its verified frozen Python and saved configuration')
    p.add_argument('--study', type=Path, required=True)
    p = commands.add_parser('status', help='Print node status and stop reasons without starting work')
    p.add_argument('--study', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == 'status':
        state = read_json(args.study/'study_state.json')
        print(json.dumps({k: state[k] for k in ['status', 'elapsed_seconds']}, indent=2))
        for node in state['nodes']:
            print(f"L{node['level']} {node['node_id']}: {node['status']} | {node.get('stop_reason', '')}")
        return 0
    if args.command == 'resume':
        environment()
        return execute(args.study)
    config = read_json(args.config)
    for option in OPTIONS:
        value=getattr(args,option,None)
        if value is not None:config[option]=value
    for key in ['input_cache_dir', 'astronomy_raw_cache']:
        if config.get(key):
            config[key] = str((args.config.resolve().parent/config[key]).resolve())
    validate(config)
    runtime = environment()
    if args.command == 'check':
        print(json.dumps({'status': 'preflight_passed', 'configuration': config, 'runtime': runtime,
                          'note': 'No downloads or fitting performed. Cached source coverage and live network services are verified at run time.'}, indent=2))
        return 0
    label = ''.join(c for c in args.label if c.isalnum() or c in '_-') or 'study'
    study = (args.output or PROJECT/'studies_output'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+label+'_'+uuid.uuid4().hex[:8])).resolve()
    study.mkdir(parents=True, exist_ok=False)
    frozen = study/'source_snapshot/src'
    hashes=source_hashes(PROJECT/'src')
    manifest=PROJECT/'docs/FORECAST_SOURCE_MANIFEST.json'
    if config.get('energy_protocol')=='origin_refit_astro_only':
        selected=read_json(manifest)['files']
        if any(hashes.get(name)!=value for name,value in selected.items()):
            study.rmdir()
            raise ValueError('Maintained source manifest is stale; check forecast_source_manifest.py before release.')
        hashes=selected
    for name in hashes:
        target = frozen/name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT/'src'/name, target)
    for filename, content in [('run_configuration.json', config), ('source_manifest.json', source_hashes(frozen)), ('runtime_environment.json', runtime)]:
        (study/filename).write_text(json.dumps(content, indent=2)+'\n')
    import shlex
    (study/'run.sh').write_text('#!/usr/bin/env bash\nset -euo pipefail\nSTUDY_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"\nDEFAULT_PYTHON='+shlex.quote(sys.executable)+'\nexec "${DLVS_PYTHON:-$DEFAULT_PYTHON}" "$STUDY_DIR/source_snapshot/src/forecast_cli.py" resume --study "$STUDY_DIR"\n')
    (study/'run.sh').chmod(0o755)
    print(study, flush=True)
    if args.initialize_only:return 0
    return execute(study, ['--inputs-only'] if args.inputs_only else [])


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print(f'Forecast: {error}', file=sys.stderr)
        raise SystemExit(2)
