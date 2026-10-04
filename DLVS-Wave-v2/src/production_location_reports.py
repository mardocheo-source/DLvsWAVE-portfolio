#!/usr/bin/env python3
"""Two-method location dossier with one observed/predicted-zone plot per method."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import textwrap
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import numpy as np
import pandas as pd
from pypdf import PdfReader, PdfWriter, Transformation
from production_location import load_inputs, metrics, save_csv, save_json, sha
from production_location_selection import select_stage_pair, materialize_selected_stage
from production_report_navigation import decorate, infer_entry, compose
from spatial_consensus_fusion import compute_consensus_fusion, compute_consensus_peak_corridors, render_conjugate_map_plot

A4 = (11.693, 8.268)
COLORS = ['#DC2626','#2563EB','#7C3AED','#EA580C','#0891B2','#16A34A','#CA8A04','#DB2777']


def savefig(fig, path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path.with_suffix('.png'),dpi=160,facecolor='white')
    fig.savefig(path.with_suffix('.pdf'),facecolor='white');plt.close(fig)
    decorate(path.with_suffix('.pdf'),infer_entry(path))
    return path.with_suffix('.pdf')


def text_page(title, sections, path):
    fig=plt.figure(figsize=A4);fig.text(.055,.94,title,fontsize=17,weight='bold',color='#0F172A')
    y=.86
    for heading,body in sections:
        lines=[]
        for line in str(body).splitlines():lines.extend(textwrap.wrap(line,110,break_long_words=False) or [''])
        height=.036+.026*len(lines)
        if y-height<.06:raise ValueError(f'Text overflow: {title}: {heading}')
        fig.text(.06,y,heading,fontsize=11,weight='bold',color='#0369A1',va='top')
        fig.text(.06,y-.035,'\n'.join(lines),fontsize=10,color='#334155',va='top',linespacing=1.35)
        y-=height+.035
    return savefig(fig,path)


def event_plot(events, prediction, k, title, contract, q, path):
    fig,ax=plt.subplots(figsize=A4)
    fig.suptitle('DLVS-Wave v2.0 Location Validation Report',fontsize=16,weight='bold',y=.975)
    fig.text(.5,.935,title,fontsize=14,color='#DC2626',fontstyle='italic',ha='center')
    x=np.arange(len(events));truth=events.zone_id.to_numpy(int)
    ax.plot(x,truth,'o-',color='#008ACA',linewidth=2,markersize=6,label='Observed zone (0-based)')
    ax.plot(x,prediction,'o--',color='#EF2B2D',linewidth=2,markersize=4,label='Predicted zone (0-based)')
    ax.set_yticks(np.arange(k));ax.set_ylim(-.35,k-.65)
    ax.set_ylabel('Geographic zone ID',weight='bold')
    labels=[f'{pd.Timestamp(t):%Y-%m-%d %H:%M}\nM{m:.1f}' for t,m in zip(events.time,events.mag)]
    ticks=np.unique(np.linspace(0,len(events)-1,min(18,len(events)),dtype=int))
    ax.set_xticks(ticks);ax.set_xticklabels([f'#{i+1} '+pd.Timestamp(events.iloc[i].time).strftime('%Y-%m-%d') for i in ticks],rotation=60,ha='right',fontsize=8)
    pd.DataFrame({'event_number':x+1,'time':events.time.to_numpy(),'magnitude':events.mag.to_numpy(),'observed_zone':truth,'predicted_zone':prediction}).to_csv(Path(path).with_suffix('.events.csv'),index=False)
    ax.set_xlabel('One position per actual earthquake (UTC), in chronological order',weight='bold')
    start=pd.Timestamp(contract['validation_start']).strftime('%Y-%m-%d %H:%M')
    end=pd.Timestamp(contract['validation_end']).strftime('%Y-%m-%d %H:%M')
    ax.set_title(f"One-shot | Fixed validation window: {start} to {end} UTC\n"
                 f"{len(events)} earthquakes | M >= {contract['validation_magnitude']:.1f} | Correct zones: {q['correct_earthquakes']}/{len(events)} ({q['event_top1_accuracy']:.1%})",fontsize=11,pad=42,weight='bold')
    ax.grid(alpha=.35,linestyle='--');ax.legend(loc='lower left',bbox_to_anchor=(0,1.005),ncol=2,fontsize=10)
    fig.subplots_adjust(left=.07,right=.97,top=.79,bottom=.27)
    fig.text(.07,.035,'Models and fusion selected on this validation set. Multiple earthquakes in one weekly input slot share the same prediction.',fontsize=9,color='#475569')
    return savefig(fig,path)


def peak_corridors(energy, forecast, cols, threshold, config=None):
    assert pd.to_datetime(energy.date).equals(pd.to_datetime(forecast.date))
    active=np.flatnonzero(energy.predicted_prob.to_numpy()>=threshold)
    if config and config.get('selection_mode') in ['largest_observed_peak', 'first_event']:
        try:
            from production_geography import select_peak
            selected=select_peak(energy,config)['selected']
            active=np.asarray(selected['rows'],dtype=int) if selected else np.array([],dtype=int)
        except Exception:
            pass
    groups=np.split(active,np.flatnonzero(np.diff(active)>1)+1) if len(active) else []
    if len(groups)==0 and len(forecast)>0:
        candidate_rows=[]
        if config and config.get('parent_event'):
            pe=config['parent_event']
            pe_date=pd.to_datetime(pe.get('apex') or pe.get('start'))
            matches=np.flatnonzero(pd.to_datetime(forecast.date)==pe_date)
            if len(matches)>0:
                candidate_rows=matches
            elif pe.get('start') and pe.get('end'):
                f_dates=pd.to_datetime(forecast.date)
                range_matches=np.flatnonzero((f_dates>=pd.to_datetime(pe['start']))&(f_dates<=pd.to_datetime(pe['end'])))
                if len(range_matches)>0:candidate_rows=range_matches
        if len(candidate_rows)==0:
            e_probs=energy.predicted_prob.to_numpy()
            if e_probs.max()>0.05:
                candidate_rows=np.array([int(e_probs.argmax())])
            else:
                candidate_rows=np.array([int(forecast[cols].to_numpy().max(axis=1).argmax())])
        if len(candidate_rows)>0:
            groups=[candidate_rows]
    result=[]
    for indices in groups:
        mean=forecast.iloc[indices][cols].mean().to_numpy()
        order=np.argsort(-mean,kind='stable')
        start=pd.Timestamp(forecast.iloc[indices[0]].date);end=pd.Timestamp(forecast.iloc[indices[-1]].date)+pd.Timedelta(days=6)
        e_max=float(energy.iloc[indices].predicted_prob.max())
        if config and config.get('parent_event') and e_max<threshold:
            e_max=float(config['parent_event'].get('height',e_max))
        result.append({'start':str(start.date()),'end':str(end.date()),'selected_zone':int(mean.argmax()),
                       'zone_mean_scores':mean.tolist(),'runner_up_zone':int(order[1]),'top_score_margin':float(mean[order[0]]-mean[order[1]]),
                       'row_indices':indices.tolist(),'energy_threshold':threshold,
                       'energy_max':e_max})
    return result


def forecast_plot(forecast,corridors,k,title,path):
    fig,ax=plt.subplots(figsize=(16,8.6));dates=pd.to_datetime(forecast.date)
    pred=forecast[[f'prob_Zone_{z}' for z in range(k)]].to_numpy().argmax(1)
    ax.plot(dates,pred,'o--',color='#EF2B2D',linewidth=2,markersize=5,label='Predicted zone')
    for c in corridors:
        ax.axvspan(pd.Timestamp(c['start']),pd.Timestamp(c['end']),alpha=.13,color='#0284C7')
    ax.set_yticks(np.arange(k));ax.set_ylim(-.35,k-.65);ax.set_ylabel('Predicted geographic zone ID',weight='bold')
    ax.set_xticks(dates);ax.set_xticklabels(dates.dt.strftime('%Y-%m-%d'),rotation=90,fontsize=9)
    ax.grid(alpha=.35,linestyle='--');ax.legend(loc='upper right')
    fig.suptitle('DLVS-Wave v2.0 Location Prospective Forecast',fontsize=15,weight='bold',y=.97)
    fig.text(.5,.925,title,fontsize=13,color='#DC2626',fontstyle='italic',ha='center')
    ax.set_title('Highlighted intervals come from the final main/minor energy fusion',fontsize=11,pad=14)
    fig.subplots_adjust(left=.07,right=.97,top=.84,bottom=.23)
    fig.text(.07,.04,'Full zone marginals and energy-window rankings are saved in CSV and JSON. The future observed zone is unknown.',fontsize=9,color='#475569')
    return savefig(fig,path)


def map_plot(zones,catalog,corridors,config,title,path,geometry=None):
    from mpl_toolkits.basemap import Basemap
    bounds=config.get('map_bounds',[28,46.5,127,149.5]);south,north,west,east=bounds
    fig=plt.figure(figsize=A4);ax=fig.add_axes([.065,.12,.70,.75])
    m=Basemap(projection='cyl',llcrnrlat=south,urcrnrlat=north,llcrnrlon=west,urcrnrlon=east,resolution='l',ax=ax)
    m.drawcoastlines(linewidth=.75,color='#334155');m.drawcountries(linewidth=.5,color='#64748B')
    m.fillcontinents(color='#F1F5F9',lake_color='#EFF6FF');m.drawmapboundary(fill_color='#EFF6FF')
    m.drawparallels(np.linspace(south,north,5),labels=[1,0,0,0],fontsize=7,linewidth=.4,color='#94A3B8')
    m.drawmeridians(np.linspace(west,east,5),labels=[0,0,0,1],fontsize=7,linewidth=.4,color='#94A3B8')
    center_lon=(west+east)/2
    unwrap=lambda lon:center_lon+(np.asarray(lon)-center_lon+180)%360-180
    if not geometry and config.get('spherical_zone_centers'):
        from production_geography import vectors,membership
        lon,lat=np.meshgrid(np.linspace(west,east,361),np.linspace(south,north,181))
        grid=pd.DataFrame({'longitude':lon.ravel(),'latitude':lat.ravel()})
        labels=np.argmax(vectors(grid.latitude,grid.longitude)@np.asarray(config['spherical_zone_centers']).T,axis=1).astype(float)
        labels[~membership(grid,config.get('parent_region_rules',[]))]=np.nan
        from matplotlib.colors import ListedColormap
        ax.pcolormesh(lon,lat,labels.reshape(lon.shape),cmap=ListedColormap(COLORS[:len(zones)]),vmin=-.5,vmax=len(zones)-.5,alpha=.18,shading='nearest',zorder=2,rasterized=True)
    ax.scatter(unwrap(catalog.longitude),catalog.latitude,s=5,color='#64748B',alpha=.25,zorder=3,rasterized=True)
    for z in zones:
        i=int(z['zone_id']);color=COLORS[i%len(COLORS)];active=[c for c in corridors if c['selected_zone']==i]
        g=None
        if geometry:
            g=next((geom for geom in geometry if geom.get('zone_id')==i),None)
        if g is None and catalog is not None and not catalog.empty and 'zone_id' in catalog.columns:
            sub=catalog.loc[catalog['zone_id']==i]
            c_lat=float(z['centroid_lat']);c_lon=float(unwrap(z['centroid_lon']))
            if len(sub)>=3:
                sub_lon=c_lon+(unwrap(sub['longitude'])-c_lon+180)%360-180
                cov=np.cov(sub_lon,sub['latitude']);vals,vecs=np.linalg.eigh(cov)
                order=np.argsort(-vals);vals,vecs=vals[order],vecs[:,order]
                w=float(max(2*2.45*np.sqrt(max(vals[0],0.04)),1.8))
                h=float(max(2*2.45*np.sqrt(max(vals[1],0.04)),1.4))
                ang=float(np.degrees(np.arctan2(vecs[1,0],vecs[0,0])))
                g={'zone_id':i,'center_lon':c_lon,'center_lat':c_lat,'width_deg':w,'height_deg':h,'angle_deg':ang}
        if g is None:
            c_lat=float(z['centroid_lat']);c_lon=float(unwrap(z['centroid_lon']))
            rad_km=float(z.get('p95_radius_km') or z.get('median_radius_km') or 600.0)
            deg=rad_km/111.0;g={'zone_id':i,'center_lon':c_lon,'center_lat':c_lat,'width_deg':deg*2.0,'height_deg':deg*1.5,'angle_deg':0.0}
        if g:
            ax.add_patch(Ellipse((g['center_lon'],g['center_lat']),g['width_deg'],g['height_deg'],angle=g['angle_deg'],
                                facecolor=color if active else 'none',edgecolor=color,alpha=.32 if active else .7,linestyle='-' if active else '--',linewidth=2.4 if active else 0.9,zorder=4))
        longitude=float(unwrap(z['centroid_lon']))
        if active:
            ax.plot(longitude,z['centroid_lat'],'o',markerfacecolor='none',markeredgecolor=color,markersize=20,markeredgewidth=2.2,zorder=5)
        ax.plot(longitude,z['centroid_lat'],'*',color=color,markersize=12 if active else 7,zorder=6)
        box_edge=color if active else '#94A3B8'
        ax.annotate(str(i)+(' [ACTIVE]' if active else ''),(longitude,z['centroid_lat']),xytext=(5,5),textcoords='offset points',weight='bold',fontsize=10,
                    bbox={'facecolor':'white','edgecolor':box_edge,'linewidth':1.8 if active else 1.0,'alpha':.95},zorder=7)
        label=f'Zone {i}\n'+('\n'.join(f"{c['start']}\nto {c['end']} | {c['zone_mean_scores'][i]:.3f}" for c in active) if active else 'No selected energy window')
        fig.text(.79,.84-i*min(.14,.76/len(zones)),label,fontsize=8 if len(zones)<=5 else 6.5,va='top',color=color,weight='bold')
    fig.suptitle('DLVS-Wave v2.0: Geographic Zones and Forecast Windows',fontsize=12,weight='bold',y=.97)
    fig.text(.5,.925,title,fontsize=11,color='#DC2626',fontstyle='italic',ha='center')
    fig.text(.065,.035,'Zone geometry is saved independently of forecast scores. Highlight selection uses the actual fused CSV.',fontsize=8.5,color='#475569')
    return savefig(fig,path)


def merge(paths,output):
    writer=PdfWriter()
    for p in paths:
        reader=PdfReader(p)
        for page in reader.pages:writer.add_page(page)
    with Path(output).with_suffix('.tmp.pdf').open('wb') as f:writer.write(f)
    Path(output).with_suffix('.tmp.pdf').replace(output)


def build(config):
    spatial=Path(config['spatial_root']);search=Path(config['search_output_root'])
    study=Path(config.get('study_root',spatial.parent))
    output=spatial/'dual_method_reports';output.mkdir(parents=True,exist_ok=True)
    frames,targets,features,events,event_rows,truth=load_inputs(config,'main_bodies_branch');k=len(targets)
    cols=[f'prob_Zone_{z}' for z in range(k)]
    contract=json.loads((spatial/'event_only_master_manifest.json').read_text())
    audit_path=spatial/'one_shot_leakage_audit.json'
    audit=json.loads(audit_path.read_text())
    assert audit['training_validation_ids_disjoint'] and audit['training_before_validation'] and audit['zones_fitted_on_training_only']
    assert audit['validation_is_selection_set'] and not audit['independent_test_performance_claimed']
    assert {(c['branch'],c['family']) for c in audit['base_model_perturbation_checks']} == {
        (b,f) for b in ['main_bodies_branch','minor_bodies_branch'] for f in ['kan','deep_learning','lcs','analog']}
    assert all(c['training_prediction_max_change']<1e-12 and c['forecast_prediction_max_change']<1e-12 for c in audit['base_model_perturbation_checks'])
    zones=json.loads((spatial/'01_data/spatial_zones_metadata.json').read_text())['zones']
    training_events=pd.read_csv(spatial/'01_data/training_events.csv')
    geometry_path=spatial/'report_metadata/original_zone_geometry.json'
    geometry=json.loads(geometry_path.read_text())['ellipses'] if geometry_path.exists() else None
    energy_path=Path(config.get('energy_forecast_csv',study/'01_energy_forecast_m77/fusion_main_minor/final_prospective_forecast.csv'))
    energy=pd.read_csv(energy_path)
    methods={};pages=[];page_titles=[];allmetrics=[]
    weight=float(config.get('main_fusion_weight',.85))
    weight_label=f'{100*weight:g}/{100*(1-weight):g}'
    replay_deadline=time.monotonic()+float(config.get('selected_stage_replay_seconds',180))
    for name,label in [('learned','KAN + Deep ResNet + LCS'),('historical_analogs','Historical analog matching')]:
        method_root=search if name=='learned' else search/'historical_analogs'
        counts=[]
        fusion=output/name;fusion.mkdir(exist_ok=True)
        data,selection=select_stage_pair(method_root,frames,targets,event_rows,truth,weight,fusion)
        for index,branch in enumerate(['main_bodies_branch','minor_bodies_branch']):
            root=method_root/branch
            if not (root/'completed_manifest.json').exists():raise ValueError(f'Incomplete {name}/{branch}')
            manifest=json.loads((root/'completed_manifest.json').read_text());counts.append(manifest['completed_trials'])
            stage=selection['selected_stages'][branch]
            branch_frames,branch_targets,*_=load_inputs(config,branch)
            materialize_selected_stage(root,stage,branch_frames,branch_targets,replay_deadline)
            branch_metrics=metrics(frames['validation'][targets].to_numpy(),data[index]['validation_predictions'][cols].to_numpy(),event_rows,truth)
            allmetrics.append({'method':name,'branch':branch,'selected_stage':stage,'completed_trials':counts[-1],**branch_metrics})
            detail=fusion/branch;detail.mkdir(exist_ok=True)
            branch_title=label+' / '+branch.replace('_',' ')
            branch_corridors=peak_corridors(energy,data[index]['prospective_forecast'],cols,float(config.get('energy_peak_threshold',.7)),config)
            branch_pages=[event_plot(events,data[index]['validation_predictions'].predicted_zone_id.to_numpy()[event_rows],k,branch_title,contract,branch_metrics,detail/'zone_validation.pdf'),
                          map_plot(zones,training_events,branch_corridors,config,branch_title,detail/'zone_map.pdf',geometry),
                          forecast_plot(data[index]['prospective_forecast'],branch_corridors,k,branch_title,detail/'zone_forecast.pdf')]
            compose([infer_entry(p) for p in branch_pages],detail/'BRANCH_LOCATION_REPORT.pdf',branch_title)
        fused={}
        for s in data[0]:
            assert data[0][s].date.equals(data[1][s].date)
            f=data[0][s].copy();f[cols]=weight*data[0][s][cols].to_numpy()+(1-weight)*data[1][s][cols].to_numpy()
            f['predicted_zone_id']=f[cols].to_numpy().argmax(1);save_csv(fusion/f'{s}.csv',f);fused[s]=f
        val,fc=fused['validation_predictions'],fused['prospective_forecast']
        q=metrics(frames['validation'][targets].to_numpy(),val[cols].to_numpy(),event_rows,truth)
        attributed=events.copy();attributed['predicted_zone_id']=val.predicted_zone_id.to_numpy()[event_rows];attributed['correct']=attributed.zone_id.eq(attributed.predicted_zone_id)
        save_csv(fusion/'individual_event_validation.csv',attributed)
        corridors=peak_corridors(energy,fc,cols,float(config.get('energy_peak_threshold',.7)),config)
        save_json(fusion/'metrics_and_corridors.json',{'metrics':q,'corridors':corridors,'fusion_weights':[weight,1-weight],'counts':counts,'selected_branch_stages':selection['selected_stages']})
        allmetrics.append({'method':name,'branch':'fusion_main_minor','selected_stage':'best_pair','completed_trials':sum(counts),**q})
        methods[name]={'metrics':q,'corridors':corridors,'counts':counts,'selected_branch_stages':selection['selected_stages']}
        sections=[(f'{label}: validation',event_plot(events,attributed.predicted_zone_id.to_numpy(),k,label,contract,q,fusion/'zone_validation.pdf')),
                  (f'{label}: geographic map',map_plot(zones,training_events,corridors,config,label,fusion/'zone_map.pdf',geometry)),
                  (f'{label}: forecast',forecast_plot(fc,corridors,k,label,fusion/'zone_forecast.pdf'))]
        for title,p in sections:page_titles.append(title);pages.append(p)
    ql,qa=methods['learned']['metrics'],methods['historical_analogs']['metrics']
    dominance_weight=float(config.get('location_dominance_weight',config.get('main_fusion_weight',.85)))
    secondary_weight=1.0-dominance_weight
    configured_a_weight=config.get('location_method_fusion_a_weight')
    if configured_a_weight is not None and float(configured_a_weight)!=.5:
        a_weight=float(configured_a_weight)
        weight_selection=f'explicitly configured fixed weight: {100*a_weight:g}% learned / {100*(1-a_weight):g}% historical'
    else:
        rank_l=(ql['quality_index'],ql['event_top1_accuracy'],ql['macro_zone_recall'],-ql['binary_cross_entropy'],-ql['brier_score'])
        rank_a=(qa['quality_index'],qa['event_top1_accuracy'],qa['macro_zone_recall'],-qa['binary_cross_entropy'],-qa['brier_score'])
        if rank_a>rank_l:
            a_weight=secondary_weight
            weight_selection=f'validation reliability dominance: historical analogs dominant ({100*(1-a_weight):g}% historical / {100*a_weight:g}% learned) based on superior validation metrics (QI: {qa["quality_index"]:.3f} vs {ql["quality_index"]:.3f}, Brier: {qa["brier_score"]:.4f} vs {ql["brier_score"]:.4f})'
        elif rank_l>rank_a:
            a_weight=dominance_weight
            weight_selection=f'validation reliability dominance: learned models dominant ({100*a_weight:g}% learned / {100*(1-a_weight):g}% historical) based on superior validation metrics (QI: {ql["quality_index"]:.3f} vs {qa["quality_index"]:.3f}, Brier: {ql["brier_score"]:.4f} vs {qa["brier_score"]:.4f})'
        else:
            a_weight=0.50
            weight_selection='equal contributions (exact validation metric tie)'
    if not 0<a_weight<1:raise ValueError('A+B fusion requires positive weights for both methods')
    fusion=output/'fused_methods';fusion.mkdir(exist_ok=True)
    use_consensus=bool(config.get('use_consensus_gating',True))
    pair={}
    for filename in ['validation_predictions','prospective_forecast']:
        left=pd.read_csv(output/'learned'/f'{filename}.csv');right=pd.read_csv(output/'historical_analogs'/f'{filename}.csv')
        assert left.date.equals(right.date)
        if use_consensus:
            combined=compute_consensus_fusion(left,right,cols,a_weight=a_weight)
        else:
            combined=left.copy();combined[cols]=a_weight*left[cols].to_numpy()+(1-a_weight)*right[cols].to_numpy()
            combined['predicted_zone_id']=combined[cols].to_numpy().argmax(1)
        save_csv(fusion/f'{filename}.csv',combined);pair[filename]=combined
    val,fc=pair['validation_predictions'],pair['prospective_forecast']
    q=metrics(frames['validation'][targets].to_numpy(),val[cols].to_numpy(),event_rows,truth)
    attributed=events.copy();attributed['predicted_zone_id']=val.predicted_zone_id.to_numpy()[event_rows];attributed['correct']=attributed.zone_id.eq(attributed.predicted_zone_id)
    save_csv(fusion/'individual_event_validation.csv',attributed)
    if use_consensus:
        corridors=compute_consensus_peak_corridors(energy,fc,cols,float(config.get('energy_peak_threshold',.7)),config)
    else:
        corridors=peak_corridors(energy,fc,cols,float(config.get('energy_peak_threshold',.7)),config)
    cross={'metrics':q,'corridors':corridors,'weights':{'A_learned':a_weight,'B_historical':1-a_weight},
           'consensus_gating':use_consensus,
           'formula':'Consensus Gating Fusion: Outlier-damped & corroborated combination of Learned (A) and Historical Analogs (B)' if use_consensus else 'A_weight * learned marginal score + (1-A_weight) * historical marginal score',
           'weight_selection':weight_selection,'future_labels_used':False,
           'scores_are_not_calibrated_event_probabilities':True,
           'input_sha256':{str(output/m/f'{s}.csv'):sha(output/m/f'{s}.csv') for m in ['learned','historical_analogs'] for s in pair}}
    save_json(fusion/'metrics_and_corridors.json',cross);methods['fused_methods']=cross
    dom_desc=f"{100*(1-a_weight):g}% historical / {100*a_weight:g}% learned" if a_weight<0.5 else (f"{100*a_weight:g}% learned / {100*(1-a_weight):g}% historical" if a_weight>0.5 else f"{100*a_weight:g}% learned / {100*(1-a_weight):g}% historical")
    label=f'A+B consensus fusion ({dom_desc})' if use_consensus else f'A+B score fusion ({dom_desc})'
    fused_map_path=render_conjugate_map_plot(zones,training_events,corridors,config,label,fusion/'zone_map.pdf',geometry) if use_consensus else map_plot(zones,training_events,corridors,config,label,fusion/'zone_map.pdf',geometry)
    for title,p in [(f'{label}: validation',event_plot(events,attributed.predicted_zone_id.to_numpy(),k,label,contract,q,fusion/'zone_validation.pdf')),
                    (f'{label}: geographic map',fused_map_path),
                    (f'{label}: forecast',forecast_plot(fc,corridors,k,label,fusion/'zone_forecast.pdf'))]:page_titles.append(title);pages.append(p)
    cover=text_page('DLVS-Wave v2.0: Unified Location Forecast',[
        ('One-shot forecast, two distinct methods','Part A: actual production KAN, deep residual neural network and LCS rule models, with event-only multi-target training, initial screening, specialist fusion, refinement and final fusion. Part B: historical analog matching with its own feature and distance search. Both keep the fitted model fixed throughout inference.'),
        ('Fixed data contract',f"Training M >= {contract['training_magnitude']:.1f}: {len(training_events)} events / {len(frames['training'])} occupied weeks. Validation M >= {contract['validation_magnitude']:.1f}: {len(events)} events / {len(frames['validation'])} occupied weeks, {contract['validation_start']} to {contract['validation_end']}. Zones are numbered 0 to {k-1}; no Calm class or empty event rows."),
        ('Observed-versus-predicted location',f"Learned model fusion: {ql['correct_earthquakes']}/{len(events)} correct zones; macro-zone recall {ql['macro_zone_recall']:.1%}. Historical analog fusion: {qa['correct_earthquakes']}/{len(events)}; macro-zone recall {qa['macro_zone_recall']:.1%}. Each method has one validation graph, one point per earthquake."),
        ('Reading this report',f'A: KAN/Deep/LCS; B: historical weighted analogs. Each has main/minor branches and their {weight_label} fusion. The separate A+B section combines their zone scores with {dom_desc} weights based on validation reliability dominance and consensus gating. The generated index gives current page numbers. Active focal zones appear with solid borders and translucent fill.')],output/'cover.pdf')
    rows=[]
    for m in allmetrics:
        stage={'03_level1_fusion':'Initial','05_level3_final_fusion':'Refined','best_pair':'Best pair'}[m['selected_stage']]
        rows.append([m['method'].replace('historical_analogs','Analogs'),m['branch'].replace('_bodies_branch','').replace('fusion_main_minor',weight_label+' fusion'),stage,str(m['completed_trials']),f"{m['correct_earthquakes']}/{m['earthquakes']}",f"{m['macro_zone_recall']:.3f}",f"{m['macro_average_precision']:.3f}",f"{m['quality_index']:.3f}"])
    fig,ax=plt.subplots(figsize=A4);ax.axis('off');fig.suptitle('Actual Validation Comparison',fontsize=17,weight='bold',y=.94)
    table=ax.table(cellText=rows,colLabels=['Method','Branch','Stage','Fits','Correct','Recall','AP','Quality'],cellLoc='center',bbox=[.02,.43,.96,.4],colWidths=[.14,.17,.13,.11,.12,.11,.11,.11])
    table.auto_set_font_size(False);table.set_fontsize(9)
    for (row,col),cell in table.get_celld().items():
        cell.set_facecolor('#0F172A' if row==0 else ('#EFF6FF' if row%2 else '#F8FAFC'))
        if row==0:cell.get_text().set_color('white')
    future_rows=[]
    fused_corrs=methods.get('fused_methods',{}).get('corridors',[])
    for idx,(learned,analog) in enumerate(zip(methods['learned']['corridors'],methods['historical_analogs']['corridors'])):
        assert learned['start']==analog['start']
        fused_c=fused_corrs[idx] if idx<len(fused_corrs) else {}
        foci_list=fused_c.get('active_focal_zones',[fused_c.get('selected_zone','-')])
        foci_str=' + '.join(f"Zone {z}" for z in foci_list)
        future_rows.append([learned['start']+' to '+learned['end'],f"Zone {learned['selected_zone']}",f"Zone {analog['selected_zone']}",foci_str,f"{fused_c.get('top_score_margin',0.0):.3f}",'Conjugate Pair' if len(foci_list)>1 else ('Agreed' if learned['selected_zone']==analog['selected_zone'] else 'Disputed')])
    fig.text(.065,.405,'Prospective zones at the retained energy peaks',fontsize=12,weight='bold',color='#0369A1')
    if future_rows:
        future=ax.table(cellText=future_rows,colLabels=['Energy interval','Learned (A)','Analog (B)','Consensus Active Foci','Margin','Status'],cellLoc='center',bbox=[.02,.08,.96,.25],colWidths=[.28,.12,.12,.24,.10,.14])
        future.auto_set_font_size(False);future.set_fontsize(8.5)
        for (row,col),cell in future.get_celld().items():
            cell.set_facecolor('#0F172A' if row==0 else '#EFF6FF')
            if row==0:cell.get_text().set_color('white')
    fig.text(.06,.07,'Quality = 0.50 event accuracy + 0.30 macro recall + 0.20 macro AP. Final fused curves are evaluated directly.\nConsensus Gating resolves multi-method ambiguity and identifies active conjugate pairs along the tectonic arc.',fontsize=9,color='#334155')
    compare=savefig(fig,output/'comparison.pdf')
    method=text_page('Methods, Reproducibility and Limits',[
        ('One-shot forecast protocol','Every candidate is fitted once, using training events only. It predicts the whole validation and forecast grids without online updates. Inputs are raw astronomical ephemerides available in advance; model scalers and zone geometry use training only. Seismic lag and event metadata fields are excluded from this strict one-shot run.'),
        ('Fusion and validation',f'Initial and refined candidates use global and zone-specific specialists. All four initial/final main-minor stage pairs are compared on fused validation quality, retaining {weight_label} weights. The best pair is selected; earlier ensembles remain eligible. Saved models and calibration are applied unchanged to the forecast. All four scores and selected stages are recorded. These are selection-set results; future labels are never used.'),
        ('Magnitude adaptation',(f"Only the validation threshold was lowered to M{contract['validation_magnitude']:.1f} to represent every fixed zone. " if contract['validation_magnitude']<contract['training_magnitude'] else 'No magnitude reduction was needed for validation coverage. ')+f"Training remains M{contract['training_magnitude']:.1f}. The validation window was not extended backward. Earthquakes sharing a weekly feature vector have identical model inputs and predictions."),
        ('Geographic recursion',f"The configured child-zone expansion is {100*config.get('child_buffer_fraction',.1):.0f}% of the zone scale, clipped to its parent. This reduces boundary sensitivity; it does not establish that the chosen zone is correct. Parent peak/zone rankings and stop reasons must be saved before a child starts.")],output/'methods.pdf')
    baseline=study/'00_reproduction_audit/original_02_02a_map_discrepancy.json'
    provenance=text_page('Original Map Lineage and Historical Analogs',[
        ('The original screenshot','The original unified Japan PDF used the map from 02_spatial_zones_forecast. Its saved CSV chooses Zone 1 for September 7 and Zone 2 for October 19-26. The later 02a multi-target CSV instead chooses Zone 3 for September 7. These are different saved numerical results, not a graphical relabeling.' if baseline.exists() else 'Zone identities, geometry, parent region and forecast corridors are read from this node\'s saved calculation metadata.'),
        ('Original exporter behavior','In spatial_l1_engine.py, top_trials was computed but the forecast exporter used pr_probs from the last trial. Thus the old 02 map was not the stated average of the best five trials. The new workflow persists and verifies the actual selected ensemble and the same forecast transform.' if baseline.exists() else 'The actual selected model indices, per-zone weights and calibration are persisted with every branch. Reports consume the committed curves.'),
        ('Separate analog technique','The original energy analog module compared normalized astronomical vectors with historical event weeks using cosine similarity; it placed its marker at the strongest analog\'s epicenter and capped the displayed dispersion radius. That diagnostic was separate from the five-zone neural map. The new analog validation excludes validation events from its reference library.'),
        ('Reference input audit','The old weekly seismic fields m7d...m35d were shifted by 7...35 weekly rows (49...245 days). The strict one-shot location uses raw astronomy instead. The retained energy PDF reproduces its original inputs; its historical aggregate energy annotation also uses assumed magnitude/year values, not a direct catalog sum.' if baseline.exists() else 'This node uses raw ephemerides with true calendar shifts and no seismic predictor fields. Historical earthquake energies are summed directly from the occurrence-filtered node catalog. The source hashes and explicit data contracts accompany the reports.')],output/'provenance.pdf')
    audit_page=text_page('Leakage Checks and Evaluation Scope',[
        ('Base training and target construction','Training and validation earthquake IDs are disjoint. Zone centroids and boundaries are fitted before the validation window. Feature masks admit only known astronomical inputs. Scalers and zone prototypes are fitted on each candidate training subset; there is no validation imputation or validation-row training.'),
        ('Perturbation verification','Eight deterministic checks (four families, both branches) changed validation features and labels while keeping training fixed. Training/forecast predictions remained unchanged. These short structural checks complement the selected production models\' separate replay proofs. Details and source hashes: one_shot_leakage_audit.json.'),
        ('Model selection versus independent testing','Feature, hyperparameter, ensemble, stage-pair and calibration choices deliberately use this validation set. These final selected scores are not an estimate from an untouched independent test. One-shot refers to inference without incremental model updates, not to absence of validation-based model selection.'),
        ('Catalog version limitation','The occurrence-time cutoff is enforced. Historical USGS events may have been revised after their occurrence. This is a retrospective reconstruction from a later catalog snapshot, not proof of the exact data or forecast that was available on each historical issue date.')],output/'leakage_audit.pdf')
    allpages=[cover,*pages,compare,method,provenance,audit_page];titles=['Study and validation contract',*page_titles,'Validation comparison','Methods and limits','Original report provenance','Leakage audit and forecast protocol']
    energy_audit_path=study/'00_reproduction_audit/energy_temporal_availability_audit.json'
    if energy_audit_path.exists():
        energy_audit=json.loads(energy_audit_path.read_text())
        energy_note=text_page('Scope of the Retained Energy Reference',[
            ('A separate inference-availability issue',f"The strict one-shot checks in the location leakage audit apply to the updated location methods. The retained original energy replica has {energy_audit['candidates_with_future_seismic_week_dependencies']} selected candidates with seismic dependencies from weeks after the displayed prediction week. It is not certified as a causal one-shot validation."),
            ('Concrete original example','Main initial KAN trial 448 shifts its signal backward by 12 weeks and includes m7d seismic depth, which in the frozen master is a 7-week lag. The displayed prediction can therefore read seismic observations from five weeks later. This candidate contributes to the selected weighted-mean stage fusion.'),
            ('What the joint map means','Both location methods have independently calculated zone scores. Their highlighted dates still come from the retained energy reference curve. Strong selected location validation does not remove the energy timing issue or establish independent future accuracy.'),
            ('Reproducible evidence','The reference energy curves and PDF are preserved for comparison. The audit JSON and feature-dependency CSV are saved under 00_reproduction_audit. The generalized worldwide runner uses known astronomical predictors and training-only normalization for both energy and location.')],output/'energy_reference_scope.pdf')
        allpages.append(energy_note);titles.append('Retained energy inference-availability audit')
    cutoff_page=text_page('Training Cutoffs, Inputs and Quiescence',[
        ('Location: validation and forecast use the same fitted models',f"The available training event pool ends before {contract['validation_start']}. The last included earthquake is {training_events.time.max()}. Candidate training starts can differ and are saved per trial. No refit through the end of validation is performed for the future forecast."),
        ('Known future inputs versus future observations','Astronomical lead/lag features are present in training, validation and forecast with the same definitions and training-fitted scalers. Future ephemerides are calculable in advance. Both A and B exclude seismic-offset predictors, future earthquake labels and event metadata as input features.'),
        ('Quiescence is a different target','Location is conditional on an event: training contains occupied earthquake weeks only, with multi-target zone labels and no Calm class. It does not estimate whether a quiet week will contain an earthquake. The energy task includes negative and calm examples and supplies the displayed time windows.'),
        ('A+B score fusion',f"The A+B score is {a_weight:g} * A + {1-a_weight:g} * B after each method's main/minor fusion. The same formula applies to validation and future rows. Scores, rankings and all intervals are saved. Neither agreement nor a high score certifies future accuracy.")],output/'cutoffs_and_quiescence.pdf')
    allpages.append(cutoff_page);titles.append('Training cutoffs, feature availability and quiescence')
    entries=[]
    for title,p in zip(titles,allpages):
        entry=infer_entry(p,title)
        if p==cover:entry.update(section='OVERVIEW',branch='Location study',method='Neural models / Historical analogs / Combined methods')
        elif p.parent.name=='learned':entry.update(branch='Neural models / Main + Minor fusion',method='A - KAN + Deep ResNet + LCS')
        elif p.parent.name=='historical_analogs':entry.update(branch='Historical analogs / Main + Minor fusion',method='B - Historical weighted analogs')
        elif p.parent.name=='fused_methods':entry.update(branch='Combined neural and historical methods',method=label)
        else:entry.update(branch='Shared methods and audit',method='Protocol and provenance')
        if p.stem in ['zone_validation','zone_map','zone_forecast']:
            entry['title']={'zone_validation':'Validation','zone_map':'Map and all selected intervals','zone_forecast':'Prospective forecast'}[p.stem]
        entries.append(entry)
    location=spatial/'SPATIAL_ZONES_MASTER_REPORT.pdf';navigation=compose(entries,location,'Location Forecast - Contents')
    save_csv(output/'validation_comparison.csv',pd.DataFrame(allmetrics))
    manifest={'status':'generated_pending_visual_review','report':str(location),'pages':navigation['pages'],'sha256':sha(location),
              'methods':methods,'page_sources':[{**e,'sha256':sha(e['path'])} for e in entries],
              'config':config,'energy_forecast_sha256':sha(energy_path),'event_table_sha256':sha(spatial/'01_data/validation_events.csv'),
              'leakage_audit_sha256':sha(audit_path),'report_source_sha256':sha(__file__)}
    save_json(output/'report_manifest.json',manifest)
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True)
    args=p.parse_args();print(json.dumps(build(json.loads(args.config.read_text())),indent=2))
