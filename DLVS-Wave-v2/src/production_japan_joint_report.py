"""Original energy figures with explicit Energy / Location navigation and A/B fusion."""
from pathlib import Path
import json
import sys
from production_location import sha,save_json
from production_report_navigation import compose


def build(config):
    root=Path(config['study_root']);spatial=Path(config['spatial_root']);metadata=spatial/'dual_method_reports'
    report=json.loads((metadata/'report_manifest.json').read_text())
    contract=json.loads((spatial/'event_only_master_manifest.json').read_text())
    compiler=root/'source_snapshot/src/uncompressed_pipeline/compile_structured_master_dossier.py'
    sys.path.insert(0,str(compiler.parents[1]));source=compiler.read_text()
    source=source.replace('spatial_dir = macro_dir / "02_spatial_zones_forecast"',f'spatial_dir = Path({json.dumps(str(spatial))})')
    start=source.index('        # --- SECTION 4: SPATIAL FAULT ZONES ---');end=source.index('    ]',start)
    source=source[:start]+source[end:]
    source=source.replace('    # Collect existing pages','    return pages_to_assemble\n\n    # Collect existing pages',1)
    for old,new in [('SECTION 1: MAIN BODIES','ENERGY: MAIN BODIES'),('SECTION 2: MINOR BODIES','ENERGY: MINOR BODIES'),('SECTION 3: SUPER-FUSION','ENERGY: MAIN + MINOR FUSION')]:source=source.replace(old,new)
    namespace={'__name__':'japan_energy_source_renderer','__file__':str(compiler)};exec(compile(source,str(compiler),'exec'),namespace)
    original_cover=namespace['generate_executive_title_cover_page']
    def cover(**kwargs):
        kwargs['subtitle']='Energy Forecast | Location A, B and A+B score fusion'
        kwargs['mini_map_png']=metadata/'fused_methods/zone_map.png'
        kwargs['spatial_callout']='ONE-SHOT LOCATION | A + B'
        kwargs['metadata']={
            'Geographic Target':'Japan | 28-46.5 N, 127-149.5 E',
            'Forecast Window':'2026-08-01 to 2027-01-31 | Weekly inputs',
            'Energy Reference':'Historical replica with future seismic dependencies; see Energy audit',
            'Location A':'KAN + Deep ResNet + LCS | Main + Minor bodies',
            'Location B':'Historical weighted analogs | Main + Minor bodies',
            'Location A+B':'Consensus Gating & Bipolar Conjugate Fusion of Methods A and B',
            'Location Validation':f"{contract['validation_events']} events | {contract['validation_start'][:10]} to {contract['validation_end'][:10]}",
            'Inference Protocol':'Fixed one-shot models | Validation is used for selection'}
        return original_cover(**kwargs)
    namespace['generate_executive_title_cover_page']=cover
    output=root/'JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf'
    sources=namespace['compile_complete_structured_dossier'](root,output)
    entries=[]
    for section,title,path in sources:
        branch='Main bodies' if 'MAIN BODIES' in section else 'Minor bodies' if 'MINOR BODIES' in section else 'Main + Minor fusion'
        entries.append({'path':str(path),'section':'OVERVIEW' if section=='COVER' else 'ENERGY FORECAST',
                        'branch':'Joint study' if section=='COVER' else branch,'title':title,
                        'method':'Energy / Location A / B / A+B' if section=='COVER' else 'KAN / Deep / LCS - energy ensemble'})
    location_entries=[]
    for entry in report['page_sources']:
        item={k:entry[k] for k in ['path','section','branch','title','method']}
        if Path(item['path']).stem=='energy_reference_scope':
            item.update(section='ENERGY FORECAST',branch='Temporal-availability audit',method='Original energy replica - known limitation');entries.append(item)
        else:
            if item['section']=='OVERVIEW':item.update(section='LOCATION FORECAST',branch='A / B / A+B overview')
            location_entries.append(item)
    protocol=root/'01_energy_forecast_m77/energy_training_protocol.pdf'
    if protocol.exists():entries.append({'path':str(protocol),'section':'ENERGY FORECAST','branch':'Protocol audit','title':'Cutoffs, terminal quiescence and bitwise inputs','method':'Actual training and representation audit'})
    entries+=location_entries
    navigation=compose(entries,output,'Energy Forecast / Location Forecast - Contents')
    runtime=metadata/'joint_assembler_runtime.py';runtime.write_text(source)
    save_json(metadata/'joint_report_manifest.json',{'report':str(output),'sha256':sha(output),'pages':navigation['pages'],
        'original_assembler':str(compiler),'original_assembler_sha256':sha(compiler),'runtime_assembler_sha256':sha(runtime),
        'location_report_sha256':report['sha256'],'navigation':navigation,'status':'generated_pending_visual_review'})
    return output


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);a=p.parse_args();print(build(json.loads(a.config.read_text())))
