"""Origin-refit World report pages using the same Japan table/spectrum renderers.

All labels, training dates, source curves and feature inventories are read from
this node's metadata. No Japan report, regional date or fitted curve is reused.
"""
from pathlib import Path
import json
import pandas as pd
from causal_japan_energy_reports import table_page, parameter_label
from production_location import save_json, save_csv
from production_location_reports import text_page


def pages(root,config):
    root=Path(root);result=[];fusion=root/'fusion_main_minor'
    stages=['03_level1_fusion','04_level2_deep_meta_optimizer/level2_fusion','05_level3_final_fusion']
    for branch in config['branches']:
        b=root/branch
        for stage in stages:
            path=b/stage/'fusion_manifest.json'
            if not path.exists():continue
            m=json.loads(path.read_text());rows=[]
            for r,pw,cw in zip(m['selected_trials'],m['peak_weights'],m['calm_weights']):
                c=r['configuration'];scores=r['metrics'].get('validation_event_probabilities',[])
                rows.append([c['trial_id'],c['family'],f'{pw:.1%}',f'{cw:.1%}',', '.join(f'{v:.3f}' for v in scores),c.get('training_start','stage curve'),c.get('infill_seed_mode','inherited'),parameter_label(c)])
            if rows:
                result.append(table_page(branch.replace('_',' ')+' | '+stage,['Trial','Model','Peak weight','Calm weight','Validation peaks','Training start','Infill','Parameters'],rows,b/stage/'fusion_trials_composition_table.pdf'))
        manifest=json.loads((b/'01_data/causal_master_manifest.json').read_text())
        rows=[[n,d['issue_time'],d['training_last_week'],d['training_event_weeks'],d['quantization_fit_end']] for n,d in manifest['contexts'].items()]
        result.append(table_page(branch.replace('_',' ')+' | Actual training origins',['Origin','Issue time','Last training week','Event weeks','Bitwise training end'],rows,b/'training_origin_audit.pdf','Astronomy only | Pi infill | Separate forecast refit'))
        flat=pd.read_csv(b/'all_trials.csv');rows=[]
        for family in ['kan','deep_learning','lcs']:
            part=flat.loc[flat.family.eq(family)].sort_values('composite_needle_loss')
            for _,r in part.head(2).iterrows():
                fields=json.loads(r.features)
                rows.append([int(r.trial_id),family,f'{r.composite_needle_loss:.4f}',len(fields),', '.join(fields[:6]),parameter_label({'family':family,'params':json.loads(r.hyperparameters)})])
        if rows:
            result.append(table_page(branch.replace('_',' ')+' | Feature search inventory',['Trial','Family','Selection loss','Fields','Field excerpt','Parameter excerpt'],rows,b/'feature_search_inventory.pdf','KAN / Deep: astronomy | LCS: rebuilt bitwise astronomy'))
    sources={};lineage={};w=config.get('main_fusion_weight',.85)
    for key,stage in zip(['l1','l2','l3'],stages):
        if key=='l3':
            sources[key]=fusion/'final_prospective_forecast.csv';lineage[key]={'source':'final selected pointwise main/minor fusion'};continue
        frames=[];used=[]
        for b in config['branches']:
            p=root/b/stage/'prospective_forecast.csv'
            if not p.exists():p=root/b/stages[0]/'prospective_forecast.csv'
            frames.append(pd.read_csv(p));used.append(str(p))
        if not frames[0].date.equals(frames[1].date):raise ValueError('spectrum_stage_dates_mismatch')
        f=frames[0].copy();f['predicted_prob']=w*frames[0].predicted_prob+(1-w)*frames[1].predicted_prob
        sources[key]=fusion/f'{key}_prospective_forecast.csv';save_csv(sources[key],f);lineage[key]={'sources':used,'weights':[w,1-w]}
    from src.uncompressed_pipeline.energy_report_spectrum import compute_and_plot_intensity_magnitude_spectrum
    compute_and_plot_intensity_magnitude_spectrum(fusion,fusion,raw_master_path=fusion/'disabled_legacy_analog_input',usgs_catalog_path=fusion/'disabled_legacy_catalog_input',forecast_inputs=sources)
    save_json(fusion/'spectrum_lineage.json',lineage)
    result.append(fusion/'prospective_energy_magnitude_spectrum.pdf')
    result.append(text_page('Training, Validation and Forecast - Actual Protocol',[
        ('Same fitting mechanism as Japan','KAN, Deep ResNet and LCS use the shared Japan fitting and pi-infill implementation. Every validation corridor has a separate training origin. Each prospective curve comes from a separate refit ending at the catalog cutoff. Parameters and fusion calibration are selected using validation; no independent test split is added.'),
        ('Astronomy only','Past and future astronomical offsets are searchable because ephemerides are computable in advance. No seismic predictor is supplied, including previous-event indices. Earthquakes are targets only. LCS receives astronomical bitfields rebuilt with quantile edges fitted before each origin; its selected containers can be traced to original fields through the JSON codebook.'),
        ('Observed terminal quiescence',f"Both main and minor branches retain all observed terminal weeks through {config['catalog_cutoff']}. Pi-derived seeds sample earlier calm gaps. The partial final week has its observed duration recorded. A later nested zoom does not invent calm observations between this cutoff and its forecast start."),
        ('Reproduction and interpretation','Origin tables, row masks, gap seeds, scaler values, codebooks and selected-model replay checks are saved beside the trial files. The spectrum uses the same two-panel renderer as Japan; its magnitude transfer is a heuristic potential class. Neither its class nor the validation-selected score is an independently calibrated earthquake probability.')],fusion/'origin_refit_protocol.pdf'))
    return result
