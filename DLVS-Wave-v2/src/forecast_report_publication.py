"""Publish reviewed report editions beside their study, preserving prior PDFs.

Only report files are copied. Training data, trials, models and active study
directories are never moved. Publication is idempotent for identical files.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import uuid


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def publish_edition(study, edition):
    study,edition=Path(study).resolve(),Path(edition).resolve()
    record=json.loads((edition/'publication_manifest.json').read_text())
    if record.get('source_study')!=str(study) or edition==study:
        raise ValueError('Report edition must belong to this study and use a separate staging folder')
    names=['JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf',
           'ENERGY_FORECAST_MASTER_REPORT.pdf','SPATIAL_ZONES_MASTER_REPORT.pdf']
    for name in names:
        if not (edition/name).is_file():raise FileNotFoundError(edition/name)
    copies={study/name:edition/name for name in names}
    energy=study/'01_energy_forecast_m77';location=study/'02a_spatial_zones_forecast_multitarget'
    for folder,name in [(energy,names[1]),(location,names[2])]:
        if folder.is_dir():copies[folder/name]=edition/name
    if (edition/'pages/executive_cover.pdf').exists():
        copies[study/'executive_cover.pdf']=edition/'pages/executive_cover.pdf'
    for dest,source in list(copies.items()):
        nav=source.with_suffix('.navigation.json')
        if nav.exists():copies[dest.with_suffix('.navigation.json')]=nav
    changed={d:s for d,s in copies.items() if not d.exists() or sha(d)!=sha(s)}
    archive=None;saved={}
    if changed:
        archive=study/'report_editions'/('previous_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6])
        archive.mkdir(parents=True)
        for dest in changed:
            if dest.exists():
                backup=archive/dest.relative_to(study);backup.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(dest,backup)
                if sha(dest)!=sha(backup):raise IOError('Report archive verification failed')
                saved[str(dest)]={'archive':str(backup),'sha256':sha(backup)}
        old_manifest=study/'publication_manifest.json'
        if old_manifest.exists():shutil.copy2(old_manifest,archive/'publication_manifest.json')
        (archive/'archive_manifest.json').write_text(json.dumps(saved,indent=2)+'\n')
        for dest,source in changed.items():
            temporary=dest.with_name(dest.name+'.publish.tmp')
            shutil.copy2(source,temporary)
            if sha(temporary)!=sha(source):raise IOError('Report publication verification failed')
            temporary.replace(dest)
    previous=json.loads((study/'publication_manifest.json').read_text()) if (study/'publication_manifest.json').exists() else {}
    previous.update(joint=str(study/names[0]),energy=str(study/names[1]),location=str(study/names[2]),
        joint_sha256=sha(study/names[0]),joint_pages=record.get('joint_navigation',{}).get('pages'),
        report_edition=str(edition),publication_layout='reports_in_study_root',
        status=record.get('status','generated_pending_visual_review'))
    if archive:previous['previous_reports_archive']=str(archive)
    (study/'publication_manifest.json').write_text(json.dumps(previous,indent=2)+'\n')
    (study/'REPORTS.md').write_text('# Study reports\n\n'
        'Open JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf in this folder.\n\n'
        'ENERGY_FORECAST_MASTER_REPORT.pdf and SPATIAL_ZONES_MASTER_REPORT.pdf are the separate reports. '
        'The same editions are also available in the corresponding energy and location folders.\n\n'
        'Previous PDFs are preserved under report_editions/previous_*. Trial data and models are unchanged.\n')
    return study/names[0]
