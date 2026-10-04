#!/usr/bin/env python3
"""Check completed Japan energy replay outputs against their declared reference.

Comparisons happen after fitting. The reference is never supplied to a model.
Optional PDF rendering prepares images for a separate visual review.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import subprocess

import numpy as np
import pandas as pd
from pypdf import PdfReader


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def audit(study, reference, render=False):
    study, reference = Path(study).resolve(), Path(reference).resolve()
    config = json.loads((study/'run_config.json').read_text())
    folders = [Path('01_energy_forecast_m77')/branch/stage
               for branch in ['main_bodies_branch', 'minor_bodies_branch']
               for stage in ['03_level1_fusion', '04_level2_deep_meta_optimizer/level2_fusion', '05_level3_final_fusion']]
    folders.append(Path('01_energy_forecast_m77/fusion_main_minor'))
    curves = []
    for folder in folders:
        for name in ['compound_validation_predictions.csv', 'compound_prospective_forecast.csv',
                     'final_validation_predictions.csv', 'final_prospective_forecast.csv']:
            actual_path, reference_path = study/folder/name, reference/folder/name
            if not actual_path.exists():
                assert not reference_path.exists(), f'Missing expected curve: {actual_path}'
                continue
            actual, expected = pd.read_csv(actual_path), pd.read_csv(reference_path)
            pd.testing.assert_frame_equal(actual, expected, check_exact=False, rtol=1e-8, atol=1e-8, check_dtype=False)
            numeric = actual.select_dtypes('number').columns
            maximum = float(np.nanmax(np.abs(actual[numeric].to_numpy()-expected[numeric].to_numpy())))
            curves.append({'file': str(folder/name), 'rows': len(actual), 'maximum_numeric_difference': maximum,
                           'actual_sha256': digest(actual_path), 'reference_sha256': digest(reference_path)})

    refinements = []
    for branch, expected_count in [('main_bodies_branch', 3000), ('minor_bodies_branch', 240)]:
        relative = Path('01_energy_forecast_m77')/branch/'04_level2_deep_meta_optimizer/meta_trials_level2.csv'
        actual, expected = pd.read_csv(study/relative, low_memory=False), pd.read_csv(reference/relative, low_memory=False)
        assert len(actual) == len(expected) == expected_count
        numeric = [name for name in actual.select_dtypes('number')
                   if not any(term in name.lower() for term in ['elapsed', 'execution', 'quality_time'])]
        assert set(numeric).issubset(expected.columns)
        assert np.allclose(actual[numeric], expected[numeric], rtol=1e-12, atol=1e-12, equal_nan=True)
        # The original minor engine stores its mask as feat__ indicators; main
        # also records a serialized feature_mask. Compare each actual schema.
        text_fields = [name for name in ['feature_mask', 'network_type', 'train_start_date',
                                        'hyper_param1_name', 'hyper_param2_name', 'hyper_param3_name']
                       if name in actual and name in expected]
        for name in text_fields:
            assert actual[name].equals(expected[name]), (branch, name)
        refinements.append({'branch': branch, 'trials': len(actual), 'numeric_columns_checked': len(numeric),
                            'feature_indicator_columns_checked': sum(name.startswith('feat__') for name in numeric),
                            'text_fields_checked': text_fields, 'numeric_and_feature_fields_match': True,
                            'actual_sha256': digest(study/relative), 'reference_sha256': digest(reference/relative)})

    screening = []
    for proof_path in sorted((study/'00_reproduction_audit/energy_screening_resume').glob('*/*/complete_comparison.json')):
        proof = json.loads(proof_path.read_text())
        assert proof['all_numeric_nontime_columns_match_reference_1e_12']
        assert proof['all_feature_masks_match'] and len(proof['package_replays']) == 6
        branch = proof_path.parent.parent.name
        count_key = 'main_l1_counts' if branch == 'main_bodies_branch' else 'minor_l1_counts'
        assert proof['completed_trials'] == config[count_key][proof['family']]
        screening.append({'branch': branch, 'family': proof['family'], 'trials': proof['completed_trials'],
                          'verified_model_package_replays': 6, 'proof_sha256': digest(proof_path)})
    assert len(screening) == 6
    availability = json.loads((study/'00_reproduction_audit/energy_temporal_availability_audit.json').read_text())
    proof = {'status': 'passed', 'checked_utc': datetime.now(timezone.utc).isoformat(),
             'audit_source_sha256': digest(Path(__file__)), 'unique_energy_trials': sum(x['trials'] for x in screening+refinements),
             'curve_checks': curves, 'screening': screening, 'refinements': refinements,
             'energy_reference_future_seismic_dependency_candidates': availability['candidates_with_future_seismic_week_dependencies'],
             'numerical_replication_is_not_a_causal_forecast_certification': True}
    assert proof['unique_energy_trials'] == 19403
    save(study/'00_reproduction_audit/complete_energy_numeric_verification.json', proof)
    if render:
        from PIL import Image, ImageDraw
        pdf = study/'01_energy_forecast_m77/ENERGY_FORECAST_MASTER_REPORT.pdf'
        pages = len(PdfReader(pdf).pages)
        navigation=pdf.with_suffix('.navigation.json')
        assert pages == (json.loads(navigation.read_text())['pages'] if navigation.exists() else 12)
        raw=pdf.parent/'.page_content'/pdf.name
        if raw.exists():assert len(PdfReader(raw).pages)==12
        output = study/'00_reproduction_audit/fresh_energy_visual_review'
        output.mkdir(exist_ok=True)
        subprocess.run(['pdftoppm', '-scale-to', '1600', '-png', str(pdf), str(output/'page')],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for start in range(0, pages, 6):
            canvas = Image.new('RGB', (1500, 1120), '#dddddd')
            draw = ImageDraw.Draw(canvas)
            for slot, index in enumerate(range(start, min(start+6, pages))):
                im = Image.open(output/f'page-{index+1:02d}.png')
                im.thumbnail((735, 340))
                x, y = slot % 2 * 750, slot // 2 * 373
                draw.text((x+8, y+5), f'Page {index+1}', fill='black')
                canvas.paste(im, (x, y+25))
            canvas.save(output/f'contact-{start+1:02d}.png')
        save(output/'render_manifest.json', {'pdf': str(pdf), 'sha256': digest(pdf), 'pages': pages,
                                            'status': 'rendered_pending_visual_review'})
    return {'status': proof['status'], 'energy_trials': proof['unique_energy_trials'], 'curves_verified': len(curves)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--render', action='store_true')
    args = parser.parse_args()
    print(json.dumps(audit(args.study, args.reference, args.render), indent=2))
