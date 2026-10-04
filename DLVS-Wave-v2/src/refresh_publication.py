"""Regenerate Japan or node reports, navigation and A/B score fusion from saved fits."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,shutil,subprocess,sys
from pypdf import PdfReader,PdfWriter
from production_location import save_json,sha
from production_report_navigation import decorate,infer_entry,compose,content_path
from production_location_reports import build as location_report,text_page
from production_leakage_audit import audit as leakage_audit
from audit_location_publication import audit as numeric_audit


def energy_navigation(root):
    energy=root/'01_energy_forecast_m77'
    if not energy.exists():return
    final=energy/'ENERGY_FORECAST_MASTER_REPORT.pdf'
    original=energy/'.page_content/ENERGY_FORECAST_MASTER_REPORT.pdf'
    original.parent.mkdir(exist_ok=True)
    if not original.exists():shutil.copy2(final,original)
    changed=[]
    for path in sorted(energy.rglob('*.pdf')):
        if '.page_content' in path.parts or path==final or '.navigation.tmp' in path.name:continue
        entry=infer_entry(path)
        entry['method']='LCS / bitwise-packed inputs' if 'lcs' in str(path).lower() else 'KAN / Deep uncompressed + LCS bitwise energy ensemble'
        decorate(path,entry);changed.append(str(path))
    # Reassemble native figures to avoid carrying obsolete compiled page numbers.
    main=energy/'main_bodies_branch';minor=energy/'minor_bodies_branch';fusion=energy/'fusion_main_minor'
    sources=[
        (fusion/'compound_prospective_forecast.pdf','Prospective forecast','Main + Minor fusion'),
        (fusion/'energy_report_spectrum/prospective_energy_magnitude_spectrum.pdf','Energy magnitude spectrum','Main + Minor fusion'),
        (main/'05_level3_final_fusion/multilevel_fusion_benchmark_comparison.pdf','Benchmark comparison','Main bodies'),
        (minor/'03_level1_fusion/fusion_trials_composition_table.pdf','Initial fusion composition','Minor bodies'),
        (minor/'04_level2_deep_meta_optimizer/level2_fusion/fusion_trials_composition_table.pdf','Refinement fusion composition','Minor bodies'),
        (main/'05_level3_final_fusion/fusion_trials_composition_table.pdf','Final stage composition','Main bodies'),
        (minor/'05_level3_final_fusion/fusion_trials_composition_table.pdf','Final stage composition','Minor bodies'),
        (fusion/'ablation_best_worst_composition_table.pdf','Best/worst trials','Main + Minor fusion'),
        (fusion/'compound_validation_report.pdf','Validation and quiescence','Main + Minor fusion'),
        (fusion/'appendix_audit_features_kan.pdf','KAN feature inventory','Main + Minor fusion'),
        (fusion/'appendix_audit_features_deep_learning.pdf','Deep feature inventory','Main + Minor fusion'),
        (fusion/'appendix_audit_features_lcs.pdf','LCS bitwise feature inventory','Main + Minor fusion')]
    entries=[]
    for path,title,branch in sources:
        assert path.exists(),path
        entries.append({'path':str(path),'section':'ENERGY FORECAST','branch':branch,'title':title,
            'method':'LCS / bitwise-packed inputs' if 'lcs.pdf' in path.name else 'KAN / Deep uncompressed + LCS bitwise ensemble'})
    protocol=text_page('Energy Training, Quiescence and Representation',[
        ('Actual reproduction training cutoff','Initial and refined energy fits use weekly training records through June 16, 2003. Validation uses two 27-week corridors centered on September 22, 2003 and March 7, 2011. The same fitted models predict August 2026 through January 2027; no second fit through July 2026 was performed.'),
        ('Quiescence and pi seeds','Training includes event-context weeks, hard negatives and a sampled calm pool before the cutoff. Minor screening and the legacy minor refinement use sequential two-digit pi seeds for calm sampling. Main screening uses trial_seed; main refinement uses seed + trial_id. A pi_infill_seed field alone does not prove that seed was applied.'),
        ('Later source variant, absent from this reproduction','The later source sets the training cutoff to July 31, 2026. The saved historical_contract_restoration.patch changes that cutoff back to pre-validation 2003 to reproduce the numerical reference. Thus the added terminal training through 2026 is absent here. Applying post-validation observations would change the meaning of historical validation.'),
        ('Actual feature representations and input availability','Energy KAN/Deep use lean uncompressed masters; energy LCS uses bitwise-compacted astronomical containers plus seismic fields. These masters were rebuilt. Astronomical leads are knowable in advance; four selected original candidates also use unavailable future seismic observations after output shifting. This energy replica is not certified as causal.')],energy/'energy_training_protocol.pdf')
    entries.append({'path':str(protocol),'section':'ENERGY FORECAST','branch':'Protocol audit','title':'Cutoff, terminal quiescence and bitwise inputs','method':'Actual training and representation audit'})
    nav=compose(entries,final,'Energy Forecast - Contents')
    save_json(energy/'report_navigation_manifest.json',{'intermediate_pdfs':changed,'navigation':nav,'original_content_sha256':sha(original),'report_sha256':sha(final)})
    return protocol


def refresh(config):
    root=Path(config['study_root']);spatial=Path(config['spatial_root'])
    archive=root/'00_reproduction_audit'/('before_ab_navigation_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    archive.mkdir(parents=True,exist_ok=True)
    for path in [root/'JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf',spatial/'SPATIAL_ZONES_MASTER_REPORT.pdf',root/'01_energy_forecast_m77/ENERGY_FORECAST_MASTER_REPORT.pdf',spatial/'dual_method_reports/report_manifest.json']:
        if path.exists():dest=archive/path.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    import torch
    torch.set_num_threads(config.get('threads',2));torch.use_deterministic_algorithms(True)
    leakage_audit(config);report=location_report(config);numeric=numeric_audit(config)
    protocol=energy_navigation(root)
    if protocol:
        from production_japan_joint_report import build
        from production_publish_location import publish
        joint=build(config);publish(config)
        exporter=root/'commands/report_metadata.py'
        if exporter.exists():subprocess.run([sys.executable,str(exporter),str(root)],check=True)
    else:
        # Global node: assemble native page sources with the same explicit hierarchy.
        energy=root/'01_energy_forecast';manifest=json.loads((energy/'fusion_main_minor/report_manifest.json').read_text())
        entries=[infer_entry(path) for path in manifest['page_sources']]
        compose(entries,energy/'ENERGY_FORECAST_MASTER_REPORT.pdf','Energy Forecast - Contents')
        from production_publish_location import publish
        publish(config)
        entries += [{k:e[k] for k in ['path','section','branch','title','method']} for e in report['page_sources']]
        joint=root/'JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf';compose(entries,joint,'Energy Forecast / Location Forecast - Contents')
    result={'status':'generated_pending_visual_review','location_report':report['report'],'joint_report':str(joint),
        'archive':str(archive),'location_numeric_audit':numeric,'source_sha256':sha(__file__)}
    save_json(root/'publication_refresh_manifest.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(refresh(json.loads(args.config.read_text())),indent=2))
