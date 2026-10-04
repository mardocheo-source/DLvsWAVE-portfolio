"""Write a progress snapshot INSIDE its own study, without importing forecasts.

Usage: python src/forecast_progress_report.py --study /path/to/study
Reads only this study's configuration and checkpoints. It never reuses another
study's PDFs, fits models, modifies checkpoints, or labels progress as results.
Safe to rerun while a worker is running; output replacement is atomic. Refresh
from the monitoring workflow, not from a model-fitting process.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import textwrap


def snapshot(study):
    study = Path(study).resolve()
    configuration = next((study / name for name in
                          ('configuration.json', 'run_configuration.json')
                          if (study / name).is_file()), None)
    if configuration is None:
        raise ValueError('Expected a study directory containing its configuration')
    json.loads(configuration.read_text())  # Reject malformed configuration.
    state_path = study / 'study_state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    branches = []
    for path in sorted(study.rglob('search_state.json')):
        record = json.loads(path.read_text())
        branches.append({'path': str(path.relative_to(study)),
                         'status': record.get('status', 'unknown'),
                         'stage': record.get('stage', 'unknown'),
                         'trials': record.get('trials'),
                         'elapsed_seconds': record.get('elapsed_seconds'),
                         'checkpoint_utc': datetime.fromtimestamp(
                             path.stat().st_mtime, timezone.utc).isoformat()})
    names = ('JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf',
             'WORLD_NESTED_JOINT_REPORT.pdf', 'ENERGY_FORECAST_MASTER_REPORT.pdf',
             'SPATIAL_ZONES_MASTER_REPORT.pdf')
    return {'study': str(study), 'study_name': study.name,
            'generated_utc': datetime.now(timezone.utc).isoformat(),
            'status': state.get('status', 'not_started_no_checkpoint'),
            'stage': state.get('stage', 'No calculation checkpoint yet'),
            'branches': branches,
            'root_result_reports': [n for n in names if (study / n).is_file()],
            'configuration': configuration.name,
            'kind': 'progress_snapshot_not_forecast_results'}


def write_report(study):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    data = snapshot(study)
    root = Path(data['study'])
    fig = plt.figure(figsize=(11.7, 8.3), facecolor='white')
    navy, blue = '#18283f', '#007db8'
    fig.text(.07, .91, 'STUDY PROGRESS', fontsize=23, weight='bold', color=navy)
    fig.text(.07, .86, data['study_name'], fontsize=12, weight='bold', color=blue)
    fig.text(.07, .82, 'Snapshot: ' + data['generated_utc'][:19] + ' UTC', fontsize=10)
    fig.text(.07, .74, 'Status: ' + data['status'].replace('_', ' '), fontsize=14, color=navy)
    fig.text(.07, .70, 'Stage: ' + data['stage'].replace('_', ' '), fontsize=11)
    lines = []
    for branch in data['branches']:
        lines += [branch['path'].removesuffix('/search_state.json'),
                  f"  {branch['trials']} trials at checkpoint | {branch['status']} | {branch['stage']}"]
    if not lines:
        lines = ['No branch calculation checkpoint has been written yet.']
    fig.text(.07, .63, '\n'.join(lines[:12]), va='top', fontsize=10, linespacing=1.6)
    reports = data['root_result_reports']
    explanation = ('Result reports available here: ' + ', '.join(reports)) if reports else (
        'The final result report has not been generated yet. This page reports '
        'checkpoint progress only; it contains no forecast results from earlier studies.')
    fig.text(.07, .25, textwrap.fill(explanation, 105), va='top', fontsize=11,
             color=navy, linespacing=1.5)
    fig.text(.07, .14, 'Source: this study only. Configuration: ' + data['configuration'], fontsize=10)
    fig.text(.07, .09, 'Progress PDF and JSON are stored beside the calculation.\n'
             'Counters refer to the latest saved checkpoint, not necessarily the currently fitting trial.',
             fontsize=9, color='#526277')
    output = root / 'STUDY_PROGRESS_REPORT.pdf'
    temporary = output.with_suffix('.pdf.tmp')
    try:
        fig.savefig(temporary, format='pdf')
    finally:
        plt.close(fig)
    temporary.replace(output)
    target = root / 'report_progress.json'
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(target)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True)
    print(write_report(parser.parse_args().study))
