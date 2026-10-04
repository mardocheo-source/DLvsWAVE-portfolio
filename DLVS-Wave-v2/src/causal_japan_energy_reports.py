"""Automatic report lineage for refitted energy and unchanged location models."""
from pathlib import Path
import importlib.util,json,shutil,sys,textwrap
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from production_location import save_json,save_csv,sha
from production_report_navigation import compose,infer_entry
from production_location_reports import savefig,text_page,build as location_report
from production_energy_reports import build as energy_report


def parameter_label(c):
    p=c.get('params',{});family=c.get('family','')
    keys={'kan':['grid_size','spline_order','learning_rate','logit_temperature','logit_bias'],
          'deep_learning':['hidden_dim','num_layers','dropout','learning_rate','logit_temperature','logit_bias'],
          'lcs':['population_size','crossover_rate','mutation_rate','rule_center','rule_temperature']}.get(family,[])
    short={'grid_size':'G','spline_order':'k','learning_rate':'lr','logit_temperature':'temp','logit_bias':'bias','hidden_dim':'h','num_layers':'L','dropout':'drop','population_size':'pop','crossover_rate':'cross','mutation_rate':'mut','rule_center':'center','rule_temperature':'temp'}
    return ', '.join(f'{short[k]}={p[k]}' for k in keys if k in p)


def table_page(title,headers,rows,path,method='KAN / Deep / LCS'):
    fig,ax=plt.subplots(figsize=(19,11.7));ax.axis('off');fig.suptitle(title,fontsize=15,weight='bold',y=.97)
    fig.text(.5,.92,method,color='#DC2626',style='italic',ha='center',fontsize=11)
    width=26 if len(headers)>=8 else 35
    wrapped=[['\n'.join(textwrap.fill(line,width=width,break_long_words=True) for line in str(value).splitlines()) for value in row] for row in rows]
    table=ax.table(cellText=wrapped,colLabels=headers,bbox=[0,.08,1,.76],cellLoc='center')
    table.auto_set_font_size(False);table.set_fontsize(9)
    heights=[2]+[max(value.count('\n')+1 for value in row)+1 for row in wrapped]
    for (i,j),cell in table.get_celld().items():
        cell.set_height(heights[i]/sum(heights))
        cell.set_facecolor('#1E293B' if i==0 else '#FFF4C2' if i==len(rows) else '#EFF6FF' if i%2 else '#FFF1F2')
        if i==0:cell.set_text_props(color='white',weight='bold')
    fig.text(.08,.035,'Values come from committed trial and fusion metadata. Full feature masks, parameters and origin-specific fit records are saved beside the report.',fontsize=9)
    return savefig(fig,path)


def build_energy(config,root):
    energy=root/'01_energy_forecast_m77';events=pd.read_csv(energy/'events.csv');epdf,q=energy_report(energy,events,config)
    text_page('Energy Training and Selection Protocol',[
        ('Separate training origins','Validation 1 is trained before June 23, 2003; validation 2 before December 6, 2010. The forecast is refitted with observations before July 31, 2026 at 15:00 UTC. The training timeline displays the available final-refit pool, with the earlier validation origins marked. Actual candidate windows and retained rows are saved per trial.'),
        ('Validation then forecast','Validation selects features, hyperparameters and peak/calm calibration. There is no additional test split. The later forecast refit does not change the earlier validation calculations.'),
        ('Causal inputs and infill',('Both branches use pi-pair gap sampling and observed terminal weeks. All seismic predictor inputs are excluded, including past lags. The catalog supplies targets and calm intervals only. Bitwise astronomy is used only by LCS; KAN and Deep use uncompressed astronomy.' if not config.get('seismic_lag_weeks') else 'Both branches use pi-pair gap sampling and all observed terminal weeks. Past seismic lags are rebuilt with issue-time availability checks. Every origin has a new training-only bitwise codebook. The final July 27 target interval is only observed through the stated July 31 cutoff.')),
        ('Output interpretation','Scores are validation-selected, not independently calibrated earthquake probabilities. The original spectrum transfer function is retained as a heuristic potential class, not a deterministic physical magnitude estimate.')],energy/'fusion_main_minor/energy_audit.pdf')
    base=json.loads((energy/'fusion_main_minor/report_manifest.json').read_text());entries=[infer_entry(p) for p in base['page_sources']]
    for branch in config['branches']:
        b=energy/branch
        for stage in ['03_level1_fusion','04_level2_deep_meta_optimizer/level2_fusion','05_level3_final_fusion']:
            p=b/stage/'fusion_manifest.json'
            if not p.exists():continue
            m=json.loads(p.read_text());rows=[]
            for r,pw,cw in zip(m['selected_trials'],m['peak_weights'],m['calm_weights']):
                c=r['configuration'];scores=r['metrics'].get('validation_event_probabilities',[])
                rows.append([c['trial_id'],c['family'],f'{pw:.1%}',f'{cw:.1%}',', '.join(f'{v:.3f}' for v in scores),str(c.get('training_start','stage curve')),str(c.get('infill_seed_mode','inherited')),parameter_label(c)])
            fm=m['validation_metrics'];rows.append(['FUSION','asymmetric','100%','100%',', '.join(f'{v:.3f}' for v in fm.get('validation_event_probabilities',[])),'origin-specific','pi pairs','loss '+str(round(fm['calibration_objective_on_final_clipped_curve'],5))])
            p=table_page(branch.replace('_',' ')+' | '+stage,['Trial','Model','Peak weight','Calm weight','Validation peaks','Training start','Infill','Hyperparameters'],rows,b/stage/'fusion_trials_composition_table.pdf');entries.append(infer_entry(p))
        manifest=json.loads((b/'01_data/causal_master_manifest.json').read_text());flat=pd.read_csv(b/'all_trials.csv');selected=[]
        for family in ['kan','deep_learning','lcs']:
            part=flat.loc[flat.family.eq(family)].sort_values('composite_needle_loss')
            if not len(part):continue
            picks=pd.concat([part.head(3),part.tail(3)]).drop_duplicates('trial_id')
            rows=[]
            for _,r in picks.iterrows():
                f=json.loads(r.features);rows.append([int(r.trial_id),f"{r.composite_needle_loss:.4f}",r.training_start,len(f),'\n'.join(', '.join(f[i:i+3]) for i in range(0,min(len(f),9),3)),parameter_label({'family':family,'params':json.loads(r.hyperparameters)})])
            p=table_page(branch.replace('_',' ')+' | Feature and parameter inventory',['Trial','Selection loss','Training start','Fields','Selected fields (excerpt)','Parameters (excerpt)'],rows,b/f'appendix_{family}.pdf',family.upper()+((' / rebuilt bitwise astronomy'+(' + causal seismic' if config.get('seismic_lag_weeks') else ' only')) if family=='lcs' else ' / uncompressed inputs'))
            entries.append(infer_entry(p))
        rows=[[n,d['issue_time'],d['training_last_week'],d['training_event_weeks'],d['quantization_fit_end'],str(d['partial_terminal_target_intervals'])[:100]] for n,d in manifest['contexts'].items()]
        p=table_page(branch.replace('_',' ')+' | Actual origin-specific training',['Origin','Issue time','Last training week','Positive weeks','Codebook fit end','Partial final-week coverage'],rows,b/'training_origin_audit.pdf','Training, pi infill and bitwise audit');entries.append(infer_entry(p))
    # Keep the original two-panel spectrum renderer, with explicit new curve inputs.
    from src.uncompressed_pipeline.energy_report_spectrum import compute_and_plot_intensity_magnitude_spectrum
    fusion=energy/'fusion_main_minor';sources={}
    for key,stage in [('l1','03_level1_fusion'),('l2','04_level2_deep_meta_optimizer/level2_fusion'),('l3','05_level3_final_fusion')]:
        frames=[pd.read_csv(energy/b/stage/'prospective_forecast.csv') for b in config['branches']]
        assert frames[0].date.equals(frames[1].date)
        fc=frames[0].copy();fc['predicted_prob']=config['main_fusion_weight']*frames[0].predicted_prob+(1-config['main_fusion_weight'])*frames[1].predicted_prob
        p=fusion/f'{key}_prospective_forecast.csv';save_csv(p,fc);sources[key]=p
    compute_and_plot_intensity_magnitude_spectrum(fusion,fusion,raw_master_path=fusion/'disabled_legacy_analog_input',usgs_catalog_path=fusion/'disabled_legacy_catalog_input',forecast_inputs=sources)
    entries.append(infer_entry(fusion/'prospective_energy_magnitude_spectrum.pdf'))
    p=text_page('Energy Availability, Validation and Final Refit',[
        ('Validation then forecast','There is no added independent test split. Candidate configurations and the peak/calm fusion calibration are selected using two historical validation corridors. Each corridor has its own prior-only training. Selected configurations have a separate fit using observations available before the forecast issue. No later observations feed back into an earlier validation fit.'),
        ('Astronomical and seismic features',('Only astronomical inputs are searchable in this energy experiment. Both past and future seismic predictors are excluded from every family. LCS receives freshly packed astronomical fields; KAN and Deep use uncompressed fields. Quantile edges are fitted before each issue. The reused neural and historical location models were not retrained by this experiment and retain their separately documented inputs.' if not config.get('seismic_lag_weeks') else 'Known astronomical leads and lags remain searchable. Supplied seismic offset columns are discarded; magnitude, depth and count lags are rebuilt from completed past weeks with source end at or before each issue. Inputs are frozen for the entire prediction horizon. Output backshifts are disabled. LCS receives newly packed astronomical containers plus these causal seismic fields; quantile edges are fit before each issue.')),
        ('Pi infill and the terminal calm interval','Both branches sample each historical calm gap using recorded sequential two-digit pi pairs. All observed terminal weeks after the last event are retained. The final July 27 row covers only July 27 through the catalog cutoff July 31 at 15:00 UTC; unobserved days after that cutoff are not declared calm. Every trial saves an exact training-row bitmask against its immutable dated context table, sampling seeds and origin-specific scalers.'),
        ('Limits and checks','Structural audits perturb unavailable future seismic observations and prediction labels. Selected model predictions are replayed before publication. Validation is used for selection and is not an independent accuracy estimate. Historical catalog revisions remain a limitation. The magnitude spectrum retains the original heuristic transfer function and is not a calibrated physical magnitude forecast.')],fusion/'causal_protocol_audit.pdf');entries.append(infer_entry(p))
    nav=compose(entries,epdf,'Energy Forecast - Contents');save_json(fusion/'report_manifest.json',{'report':str(epdf),'sha256':sha(epdf),'pages':nav['pages'],'page_sources':[e['path'] for e in entries],'metrics':q,'navigation':nav})
    return epdf,entries


def publish(config,root):
    root=Path(root);epdf,entries=build_energy(config,root)
    original=Path(config['location_reference_root']);source=original/'02a_spatial_zones_forecast_multitarget';spatial=root/source.name
    if not spatial.exists():
        shutil.copytree(source,spatial,symlinks=True)
        # Relocate numerical file references; retain other historical source provenance.
        for p in spatial.rglob('*'):
            if not p.is_symlink() and p.suffix in ['.json','.csv','.md']:
                s=p.read_text()
                if str(source) in s:p.write_text(s.replace(str(source),str(spatial)))
    c=json.loads((original/'location_configuration.json').read_text());c.update(study_root=str(root),spatial_root=str(spatial),search_output_root=str(spatial/'extended_search'),energy_forecast_csv=str(root/'01_energy_forecast_m77/fusion_main_minor/final_prospective_forecast.csv'))
    save_json(root/'location_configuration.json',c)
    save_json(root/'00_reproduction_audit/location_reuse.json',{'source_study':str(original),'location_refitted':False,'saved_models_reused':True,'energy_windows_recomputed':True})
    from production_leakage_audit import audit
    from audit_location_publication import audit as numeric_audit
    from production_publish_location import publish as visible
    import torch
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    audit(c);report=location_report(c);numeric_audit(c);visible(c)
    # Original cover layout, now containing the recalculated A+B map.
    from src.uncompressed_pipeline.compile_structured_master_dossier import generate_executive_title_cover_page
    cover=root/'executive_cover.pdf'
    generate_executive_title_cover_page(title='DLVS-WAVE v2.0: JOINT SEISMIC FORECAST DOSSIER',subtitle='Refitted Energy | Neural location | Historical location',
        metadata={'Geographic Target':'Japan','Forecast':'August 2026 through January 2027','Energy Training':'Origin-specific validation fits + separate pre-forecast refit','Quiescence':'Pi-pair infill in both branches; observed terminal weeks retained','Seismic Predictors':('None for ENERGY: no past or future seismic inputs' if not config.get('seismic_lag_weeks') else 'Rebuilt causal lags; issue-time frozen horizon'),'Bitwise':'Rebuilt per origin, training-only quantile edges','Location':'Reused neural and historical models; separate maps','Evaluation':'Validation selects configurations; no independent test claimed'},output_pdf=cover,spatial_callout='TWO LOCATION METHODS',mini_map_png=(spatial/'dual_method_reports/fused_methods/zone_map.png' if config.get('cover_location_map',False) else None))
    allentries=[{'path':str(cover),'section':'OVERVIEW','branch':'Japan','method':'Energy / Location A / B / A+B','title':'Refitted energy and two location methods'},*entries]
    for item in report['page_sources']:
        e={k:item[k] for k in ['path','section','branch','title','method']}
        if e['section']=='OVERVIEW':e['section']='LOCATION FORECAST'
        allentries.append(e)
    joint=root/'JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf';nav=compose(allentries,joint,'Energy Forecast / Location Forecast - Contents')
    save_json(root/'publication_manifest.json',{'energy':str(epdf),'location':report['report'],'joint':str(joint),'joint_pages':nav['pages'],'joint_sha256':sha(joint),'status':'generated_pending_visual_review'})
    return joint
