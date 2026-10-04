#!/usr/bin/env python3
"""Publish reports in their study folder from saved trial reports, without retraining.

Trial data and source graph pages remain read-only. Prior published PDFs are
archived before the new reports replace them in the study root. An optional
output path selects the internal edition folder, not the public report location.
Usage: python src/reissue_forecast_report.py --study STUDY
"""
from pathlib import Path
import argparse,hashlib,json,sys
from datetime import datetime,timezone
SRC=Path(__file__).resolve().parent
sys.path[:0]=[str(SRC),str(SRC.parent)]
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from production_report_navigation import compose,content_path,infer_entry
from src.uncompressed_pipeline.section_cover_generator import generate_executive_title_cover_page
from forecast_report_publication import publish_edition


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def explanation(path, title, paragraphs):
    import textwrap
    fig=plt.figure(figsize=(11.693,8.268));fig.text(.06,.94,title,fontsize=20,weight='bold',color='#0F172A')
    y=.85
    for heading,body in paragraphs:
        lines=textwrap.wrap(body,108)
        if y-.033*len(lines)<.1:raise ValueError('Explanatory page overflow')
        fig.text(.06,y,heading,fontsize=12,weight='bold',color='#0369A1')
        fig.text(.06,y-.035,'\n'.join(lines),fontsize=10,color='#334155',va='top',linespacing=1.4)
        y-=.08+.029*len(lines)
    fig.savefig(path);plt.close(fig);return path


def audit_stages(study):
    import csv
    results=[]
    for energy in sorted(study.glob('01_energy_forecast*')):
        for branch in ['main_bodies_branch','minor_bodies_branch']:
            for stage in ['03_level1_fusion','04_level2_deep_meta_optimizer/level2_fusion','05_level3_final_fusion']:
                p=energy/branch/stage/'fusion_manifest.json'
                if not p.exists():continue
                m=json.loads(p.read_text());item={'branch':branch,'stage':stage,'manifest_sha256':digest(p),'validation':m['validation_metrics'],'replay_errors':{}}
                arrays=[]
                try:
                    for trial in m['selected_trials']:arrays.append(np.load(trial['predictions_file']))
                    for split,filename in [('validation','validation_predictions.csv'),('prospective','prospective_forecast.csv')]:
                        a=np.stack([r[split] for r in arrays]);c=m['calibration']
                        peak={'weighted_mean':np.array(m['peak_weights'])@a,'specialist_envelope':a.max(0),'specialist_q90':np.quantile(a,.9,axis=0)}[c['peak_strategy']]
                        calm={'weighted_mean':np.array(m['calm_weights'])@a,'depression_floor':a.min(0),'depression_q10':np.quantile(a,.1,axis=0)}[c['calm_strategy']]
                        raw=c['alpha']*peak+(1-c['alpha'])*calm
                        expected=np.clip(1/(1+np.exp(-np.clip((raw-c['center'])/c['temperature'],-30,30))),.001,.999)
                        rows=list(csv.DictReader((p.parent/filename).open()));actual=np.array([float(r['predicted_prob']) for r in rows])
                        error=float(np.max(abs(actual-expected)));item['replay_errors'][split]=error
                        if error>1e-10:raise ValueError(f'Fusion replay mismatch: {p} / {split}')
                        if split=='prospective':item.update(forecast_weeks=len(actual),saturated_weeks=int((actual>=.99).sum()))
                finally:
                    for a in arrays:a.close()
                results.append(item)
    return results


def build(study,output,refresh=False):
    study=Path(study).resolve();output=Path(output).resolve()
    if output.exists():
        manifest=output/'publication_manifest.json'
        if not refresh or not manifest.exists() or json.loads(manifest.read_text()).get('source_study')!=str(study):
            raise FileExistsError('Choose a new edition, or explicitly refresh a matching report edition')
    navpath=study/'JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.navigation.json'
    nav=json.loads(navpath.read_text());cfg=json.loads((study/'configuration.json').read_text())
    audit=audit_stages(study)  # Fail before authoring if saved numeric curves disagree.
    source_entries=[e for e in nav['entries'] if e['section']!='OVERVIEW']
    protected={str(content_path(e['path'])):digest(content_path(e['path'])) for e in source_entries}
    protected.update({str(p):digest(p) for p in study.glob('*.pdf')})
    output.mkdir(parents=True,exist_ok=True);pages=output/'pages';pages.mkdir(exist_ok=True)
    energy=[];location=[]
    for entry in source_entries:
        e={k:v for k,v in entry.items() if k not in ['page_start','page_count']}
        if 'ENERGY FORECAST' in e['section']:
            phase=next((v for k,v in [('03_level1_fusion','Initial'),('level2_fusion','Refinement'),('05_level3_final_fusion','Final')] if k in Path(e['path']).parts),'')
            if phase:e['title']=infer_entry(e['path'])['title']
            energy.append(e);continue
        # Replace opaque branch letters with the method's actual name.
        path=str(e['path'])
        if '/historical_analogs/' in path:e.update(branch='Historical analogs / Main + Minor fusion',method='Historical weighted analogs')
        elif '/learned/' in path:e.update(branch='Neural models / Main + Minor fusion',method='KAN + Deep ResNet + LCS')
        elif '/fused_methods/' in path:e.update(branch='Supplementary combined scores',method='Combined neural and historical methods')
        if Path(e['path']).name not in ['cover.pdf','location_methods.pdf']:location.append(e)
    intro=explanation(pages/'location_methods.pdf','Two location methods, two separate maps',[
        ('Neural location - KAN + Deep ResNet + LCS','Models learn associations between input features and earthquake zones. Main and minor branches are fused within this method. Location training contains earthquake events, with no empty filler weeks.'),
        ('Historical location - weighted analogs','Similar historical input patterns vote for earthquake zones. This method has its own feature search and main/minor fusion. Its selected zone can differ from the neural prediction.'),
        ('How to read a disagreement','Compare both maps for the same energy window. At a boundary, inspect event coordinates and neighbouring zone scores. A match by one method does not make the other method a match.'),
        ('Timing and evaluation','Energy supplies the dates; fitted location models remain fixed. Validation selects models. The reported August Ibaraki example needs a dated catalog and saved pre-event forecast before it can be counted as a success.'),
        ('Supplementary synthesis','Combined scores appear as a supplementary synthesis of these two methods. Each method keeps its own map. The study cover contains no location map.')])
    location.insert(0,{'path':str(intro),'section':'LOCATION FORECAST','branch':'Reading guide','method':'Neural models and historical analogs','title':'Why the maps can disagree'})
    cover=pages/'executive_cover.pdf'
    generate_executive_title_cover_page('DLVS-WAVE v2.0: JAPAN FORECAST','Energy forecast | Neural location | Historical location',{
        'Study':'Japan - report edition from saved trials',
        'Forecast':f"{cfg['forecast_first_week']} to {cfg['forecast_last_week']}",
        'Energy':'Main bodies 85% / Minor bodies 15%',
        'Training':'Separate validation origins and forecast refit',
        'Quiescence':'Pi-pair infill; observed terminal weeks retained',
        'Location':'Two distinct methods, shown separately',
        'Publication':'Original study and numerical results preserved'},cover,energy_callout=f"M >= {cfg['magnitude']:.1f}",spatial_callout='TWO LOCATION METHODS',show_location_map=False)
    joint=output/'JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf'
    manifest={'source_study':str(study),'training_repeated':False,'fusion_replayed_from_saved_trials':True,'cover_location_map':False,'source_pages':protected,'energy_stage_audit':audit}
    manifest['energy_navigation']=compose(energy,output/'ENERGY_FORECAST_MASTER_REPORT.pdf','Energy Forecast - Contents')
    manifest['location_navigation']=compose(location,output/'SPATIAL_ZONES_MASTER_REPORT.pdf','Location Forecast - Contents')
    manifest['joint_navigation']=compose([{'path':str(cover),'section':'OVERVIEW','branch':'Japan','method':'Energy / Neural location / Historical location','title':'Study overview'},*energy,*location],joint,'Energy / Location - Contents')
    if any(digest(p)!=h for p,h in protected.items()):raise RuntimeError('A protected input changed during publication')
    manifest.update(original_reports_unchanged=True,joint_sha256=digest(joint),report=str(joint),status='generated_pending_visual_review')
    (output/'publication_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return publish_edition(study,output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',type=Path,required=True);p.add_argument('--output',type=Path,help='Optional internal edition folder; final reports always appear in the study root')
    p.add_argument('--refresh-edition',action='store_true',help='Refresh only an existing edition with matching publication provenance; never the source study')
    a=p.parse_args();output=a.output or a.study/'report_editions'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    print(build(a.study,output,a.refresh_edition))
