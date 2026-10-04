"""Publish current location products in the visible study folders without data loss."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,shutil
from production_location import save_json,sha


def publish(config):
    study=Path(config['study_root']);source=Path(config['spatial_root']);search=Path(config['search_output_root'])
    canonical=source if source.name=='02_location_forecast' else study/'02a_spatial_zones_forecast_multitarget';canonical.mkdir(parents=True,exist_ok=True)
    report=source/'SPATIAL_ZONES_MASTER_REPORT.pdf';assert report.is_file()
    audit=study/'00_reproduction_audit'/('location_before_strict_publication_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    moves=[]
    def archive(path):
        if path.exists() or path.is_symlink():
            target=audit/path.relative_to(canonical);target.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(path),target)
            moves.append({'original':str(path),'archived':str(target)})
    def link(path,target):
        if path.is_symlink() and path.resolve()==target.resolve():return
        if path.exists() or path.is_symlink():archive(path)
        path.parent.mkdir(parents=True,exist_ok=True);path.symlink_to(os.path.relpath(target,path.parent),target_is_directory=target.is_dir())
    if canonical!=source:
        link(canonical/'01_data',source/'01_data')
        for name in ['event_only_master_manifest.json','one_shot_leakage_audit.json']:
            archive(canonical/name);shutil.copy2(source/name,canonical/name)
    for branch in ['main_bodies_branch','minor_bodies_branch']:
        visible=canonical/branch;visible.mkdir(exist_ok=True)
        if canonical!=source:link(visible/'01_data',source/branch/'01_data')
        for stage in ['02_level1','03_level1_fusion','04_level2_deep_meta_optimizer','05_level3_final_fusion']:
            target=search/branch/stage
            assert target.exists(),target;link(visible/stage,target)
        link(search/branch/'01_data',source/branch/'01_data')
        (visible/'README.md').write_text('# Current strict one-shot location branch\n\nThe five visible stages point to the committed extended search. Training contains earthquake weeks only. Refer to ../SPATIAL_ZONES_MASTER_REPORT.pdf for both learned and historical methods.\n')
    for branch in ['main_bodies_branch','minor_bodies_branch']:
        link(search/'historical_analogs'/branch/'01_data',source/branch/'01_data')
    link(canonical/'historical_analogs',search/'historical_analogs')
    fusion=canonical/'fusion_main_minor'
    if fusion.exists() and not (fusion/'CURRENT_TWO_METHODS.json').exists():archive(fusion)
    fusion.mkdir(exist_ok=True)
    for method in ['learned','historical_analogs','fused_methods']:link(fusion/method,source/'dual_method_reports'/method)
    for letter,method in [('a','learned'),('b','historical_analogs')]:
        folder=canonical/letter;folder.mkdir(exist_ok=True)
        method_root=search if method=='learned' else search/'historical_analogs'
        for branch in ['main_bodies_branch','minor_bodies_branch']:
            link(folder/branch,method_root/branch)
            branch_report=source/'dual_method_reports'/method/branch/'BRANCH_LOCATION_REPORT.pdf'
            if branch_report.exists():link(method_root/branch/'BRANCH_LOCATION_REPORT.pdf',branch_report)
        link(folder/'fusion_main_minor',source/'dual_method_reports'/method)
        (folder/'README.md').write_text(f'# Location {letter.upper()}: {method}\n\nMain and minor bodies are fitted separately within this method. Their fusion, validation and forecast are in fusion_main_minor. Branch reports sit next to the five internal model stages.\n')
    link(canonical/'fusion_a_b',source/'dual_method_reports/fused_methods')
    save_json(fusion/'CURRENT_TWO_METHODS.json',{'source':str(source/'dual_method_reports'),'methods':['learned','historical_analogs'],'fusion':'main/minor separately within each method','cross_method_fusion':'../fusion_a_b','a_weight':config.get('location_method_fusion_a_weight',0.5)})
    if canonical!=source:
        archive(canonical/'SPATIAL_ZONES_MASTER_REPORT.pdf');shutil.copy2(report,canonical/'SPATIAL_ZONES_MASTER_REPORT.pdf')
    manifest=json.loads((source/'dual_method_reports/report_manifest.json').read_text())
    save_json(canonical/'CURRENT_REPORT.json',{'canonical_report':str(canonical/'SPATIAL_ZONES_MASTER_REPORT.pdf'),'report_sha256':sha(report),'source_spatial_root':str(source),'source_search':str(search),'methods':manifest['methods'],'archive_moves':moves})
    if moves:save_json(audit/'archive_mapping.json',{'moves':moves,'note':'Historical metadata records original paths; this mapping resolves the archived physical artifacts. No old numerical result is promoted as current.'})
    (canonical/'README.md').write_text('# Current location reports\n\nOpen SPATIAL_ZONES_MASTER_REPORT.pdf: A: learned KAN/Deep/LCS, B: historical weighted analogs, and A+B score fusion appear, with one observed/predicted zone graph per method, maps, future curves and the one-shot/leakage audit.\n\nThe main_bodies_branch and minor_bodies_branch folders expose the five current stages. a/ and b/ each contain main/minor branches and their fusion. fusion_a_b contains cross-method scores, validation and the cover map. All probabilities, feature masks, trial configurations and selected models are preserved. Prior outputs are archived under the study audit directory; CURRENT_REPORT.json identifies the active calculation.\n')
    return canonical/'SPATIAL_ZONES_MASTER_REPORT.pdf'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);a=p.parse_args();print(publish(json.loads(a.config.read_text())))
