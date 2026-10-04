"""Render node energy reports from committed, recomputed hierarchical curves."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from production_location import save_json,save_csv,sha
from production_location_reports import savefig,text_page,merge
from production_energy import calibration_score


def validation_plot(frame,training,events,contract,title,path):
    fig,(ax,hist)=plt.subplots(2,1,figsize=(16,10),gridspec_kw={'height_ratios':[1.5,1]})
    fig.suptitle('DLVS-Wave v2.0 Validation Report\n'+title,fontsize=16,weight='bold',y=.97)
    x=np.arange(len(frame));truth=frame.event_target.to_numpy();pred=frame.predicted_prob.to_numpy()
    ax.plot(x,truth,color='#008ACA',lw=2,label='Observed event (binary target)')
    ax.plot(x,pred,'--',color='#EF2B2D',lw=2,label='Model prediction (score)')
    for num in frame.event_number.unique():
        indices=np.flatnonzero(frame.event_number.eq(num));center=indices[np.flatnonzero(frame.iloc[indices].relative_week.eq(0))[0]]
        if num!=frame.event_number.iloc[0]:ax.axvline(indices[0]-.5,color='#475569',linestyle='--')
        date=str(frame.iloc[center].date)[:10];eq=events.loc[events.date.astype(str).str[:10].eq(date)&events.mag.ge(contract['effective_magnitude'])]
        mag=f'M{eq.mag.max():.1f}' if len(eq) else ''
        ax.plot(center,pred[center],'o',ms=8,color='#EF4444',mec='black')
        ax.annotate(f'{date} {mag}\nPred: {pred[center]:.3f}',(center,pred[center]),xytext=(0,12),textcoords='offset points',ha='center',va='bottom',fontsize=8,
                    bbox={'boxstyle':'round,pad=.25','fc':'white','ec':'#94A3B8'})
    stride=max(1,len(frame)//26);ticks=x[::stride];ax.set_xticks(ticks);ax.set_xticklabels(frame.iloc[ticks].date.astype(str).str[:10],rotation=90,fontsize=8)
    ax.set_ylim(-.04,1.45);ax.set_ylabel('Binary target / model score [0,1]',weight='bold');ax.legend(loc='upper right',fontsize=8);ax.grid(alpha=.35,linestyle='--')
    ax.set_title(f"Validation event corridors: {frame.date.min()[:10]} to {frame.date.max()[:10]} | {contract['validation_earthquakes']} actual earthquakes | +/- {contract['half_width_weeks']} weeks",fontsize=11,weight='bold')
    dates=pd.to_datetime(training.date)
    positive=np.flatnonzero(training.event_target.to_numpy()>0)
    # Merge the closest neighboring groups until displayed centers are separated.
    fraction=float(contract.get('training_plot_min_separation_fraction',.035))
    if not 0<fraction<1:raise ValueError('training_plot_min_separation_fraction must be between 0 and 1')
    separation=max(1.,(len(training)-1)*fraction)
    clusters=[[int(i)] for i in positive]
    while len(clusters)>1:
        centers=np.array([np.mean(group) for group in clusters])
        closest=int(np.argmin(np.diff(centers)))
        if centers[closest+1]-centers[closest]>=separation:break
        clusters[closest:closest+2]=[clusters[closest]+clusters[closest+1]]
    centers=np.array([np.mean(group) for group in clusters])
    training_threshold=contract.get('training_magnitude',contract['effective_magnitude'])
    selected=events.loc[events.date.astype(str).str[:10].isin(dates.dt.strftime('%Y-%m-%d'))&events.mag.ge(training_threshold)]
    mag_min=float(selected.mag.min()) if len(selected) else float(contract['effective_magnitude'])
    mag_max=float(selected.mag.max()) if len(selected) else mag_min
    baseline=max(0.,mag_min-.5)
    group_magnitudes=[]
    for group in clusters:
        magnitudes=selected.loc[selected.date.astype(str).str[:10].isin(dates.iloc[group].dt.strftime('%Y-%m-%d')),'mag']
        if magnitudes.empty:raise ValueError('Missing catalog magnitudes for training group')
        group_magnitudes.append(float(magnitudes.max()))
    center_dates=[dates.iloc[0]+pd.Timedelta(days=float(center)*7) for center in centers]
    weekly_magnitudes=selected.assign(week=selected.date.astype(str).str[:10]).groupby('week').mag.max()
    connected_groups=[]
    for group in clusters:
        event_dates=dates.iloc[group]
        magnitudes=[float(weekly_magnitudes[d.strftime('%Y-%m-%d')]) for d in event_dates]
        # Preserve the full time span: connect actual event magnitudes within a group.
        # Return to the display baseline only outside that grouped interval.
        xs=[event_dates.iloc[0]-pd.Timedelta(days=3.5),*event_dates,event_dates.iloc[-1]+pd.Timedelta(days=3.5)]
        ys=[baseline,*magnitudes,baseline]
        hist.plot(xs,ys,color='#0284C7',lw=1.9)
        hist.fill_between(xs,baseline,ys,color='#0284C7',alpha=.25)
        connected_groups.append({'dates':[str(d.date()) for d in event_dates],'magnitudes':magnitudes})
    groups=len(clusters)
    group_metadata={'connected_event_series':connected_groups,'minimum_separation_fraction':fraction,'minimum_separation_weeks':separation,'total_training_events':len(selected),'displayed_groups':groups,'magnitude_min':mag_min,'magnitude_max':mag_max,'groups':[{'start':str(dates.iloc[g[0]].date()),'end':str(dates.iloc[g[-1]].date()),'center':str(d),'event_weeks':len(g),'maximum_magnitude':mag} for g,d,mag in zip(clusters,center_dates,group_magnitudes)]}
    Path(path).with_suffix('.training_groups.json').write_text(json.dumps(group_metadata,indent=2)+'\n')
    hist.set_title(f'Historical training timeline: {training.date.min()[:10]} to {training.date.max()[:10]}',fontsize=11,weight='bold')
    if contract.get('forecast_issue'):
        hist.set_title(f'Available history for final forecast refit: {training.date.min()[:10]} to {training.date.max()[:10]}\nValidation fits use only their own pre-issue prefixes; final tail has declared observed coverage',fontsize=11,weight='bold')
        for i,event in enumerate(contract['validation_event_weeks'],1):
            cutoff=pd.Timestamp(event)-pd.Timedelta(weeks=contract['half_width_weeks'])
            hist.axvline(cutoff,color=['#7C3AED','#EA580C'][(i-1)%2],linestyle='--',label=f'Validation {i} issue {cutoff:%Y-%m-%d}')
        hist.legend(loc='upper left',fontsize=7)
    hist.set_ylabel('Magnitude',weight='bold');hist.set_ylim(baseline,mag_max+max(.15,(mag_max-baseline)*.12));hist.grid(alpha=.35,linestyle='--')
    fig.subplots_adjust(left=.065,right=.97,top=.86,bottom=.12,hspace=.55)
    fig.text(.065,.045,f'Training: {len(selected)} total earthquakes  |  {groups} displayed groups  |  Magnitude: {mag_min:.1f} to {mag_max:.1f}',fontsize=12,weight='bold',color='#334155')
    return savefig(fig,path)


def forecast_plot(frame,title,path,config=None):
    from scipy.signal import find_peaks
    fig,ax=plt.subplots(figsize=(16,8.6));dates=pd.to_datetime(frame.date);prob=frame.predicted_prob.to_numpy(float)
    ax.plot(dates,prob,'o--',color='#EF2B2D',lw=2,ms=4,label='Prospective model score')
    p_range=float(prob.max()-prob.min()) if len(prob) else 0.
    min_prom=float((config or {}).get('minimum_peak_prominence',max(1e-4,0.10*p_range)))
    indices,props=find_peaks(prob,plateau_size=1,prominence=min_prom)
    lefts=props.get('left_edges',indices)
    rights=props.get('right_edges',indices)
    for k,i in enumerate(indices):
        l=int(lefts[k]);r=int(rights[k])
        if l==r:
            lbl=f'{dates.iloc[i]:%Y-%m-%d}\n{prob[i]:.3f}'
            ax.annotate(lbl,(dates.iloc[i],prob[i]),xytext=(0,14+20*(k%2)),textcoords='offset points',ha='center',fontsize=8,
                        bbox={'fc':'white','ec':'#94A3B8','boxstyle':'round,pad=.2'})
        else:
            d_start=dates.iloc[l];d_end=dates.iloc[r]
            lbl=f'{d_start:%Y-%m-%d} to {d_end:%Y-%m-%d}\nPlateau: {prob[i]:.3f}'
            mid_date=d_start+(d_end-d_start)/2
            ax.annotate(lbl,(mid_date,prob[i]),xytext=(0,14+20*(k%2)),textcoords='offset points',ha='center',fontsize=8,weight='bold',
                        bbox={'fc':'#FEF3C7','ec':'#D97706','boxstyle':'round,pad=.3'})
            ax.plot(dates.iloc[l:r+1],prob[l:r+1],'o-',color='#DC2626',lw=3.5,ms=6)
    scale=max(float(prob.max()),1e-6)
    ax.set_ylim(-.04*scale,1.35*scale);ax.set_xticks(dates);ax.set_xticklabels(dates.dt.strftime('%Y-%m-%d'),rotation=90,fontsize=9)
    ax.set_ylabel('Energy-event score - automatic axis range',weight='bold');ax.grid(alpha=.35,linestyle='--');ax.legend(loc='upper left')
    fig.suptitle('DLVS-Wave v2.0 Prospective Forecast\n'+title,fontsize=16,weight='bold',y=.96)
    fig.subplots_adjust(left=.07,right=.97,top=.84,bottom=.23)
    fig.text(.07,.045,'Fixed one-shot parameters; no future earthquake labels. A score peak does not supply a physical magnitude estimate.',fontsize=9,color='#475569')
    return savefig(fig,path)


def build(root,events,config):
    root=Path(root);out=root/'fusion_main_minor';out.mkdir(parents=True,exist_ok=True)
    contract=json.loads((root/'data_contract.json').read_text());contract['training_plot_min_separation_fraction']=config.get('training_plot_min_separation_fraction',.035);w=float(config.get('main_fusion_weight',.85))
    branches=['main_bodies_branch','minor_bodies_branch'];curves={};records=[]
    for b in branches:
        for stage in ['03_level1_fusion','04_level2_deep_meta_optimizer/level2_fusion','05_level3_final_fusion']:
            p=root/b/stage
            if not (p/'fusion_manifest.json').exists():continue
            m=json.loads((p/'fusion_manifest.json').read_text());records.append({'branch':b,'stage':stage,**m['validation_metrics']})
        curves[b]={s:pd.read_csv(root/b/'05_level3_final_fusion'/f'{s}.csv') for s in ['validation_predictions','prospective_forecast']}
    for s in curves[branches[0]]:
        a,b=[curves[branch][s] for branch in branches];assert a.date.equals(b.date)
        a=a.copy();a['predicted_prob']=np.clip(w*a.predicted_prob+(1-w)*b.predicted_prob,.001,.999)
        save_csv(out/f'final_{s}.csv',a)
    val=pd.read_csv(out/'final_validation_predictions.csv');fc=pd.read_csv(out/'final_prospective_forecast.csv')
    loss,hits,sparsity,calm,timing,fp=calibration_score(val.predicted_prob.to_numpy()[None,:],val)
    q={'calibration_loss':float(loss[0]),'centered_peak_count':int(hits[0]),'event_count':val.event_number.nunique(),'sparsity':float(sparsity[0]),'calm_mean':float(calm[0]),'timing_error_weeks':float(timing[0]),'false_positives':int(fp[0]),'strict_gate_passed':bool(hits[0]==val.event_number.nunique() and sparsity[0]>=.9)}
    save_json(out/'final_fusion_manifest.json',{'weights':[w,1-w],'metrics':q,'validation_evaluated_after_fusion':True,'forecast_mode':'one_shot','validation_is_selection_set':True,'energy_contract':contract})
    save_csv(out/'all_stage_metrics.csv',pd.DataFrame(records))
    def training_for_plot(branch):
        path=root/branch/'01_data'
        return pd.read_csv(path/('forecast/training.csv' if contract.get('forecast_issue') else 'training_master.csv'))
    pages=[]
    for b in branches:
        tr=training_for_plot(b)
        for name,label in [('03_level1_fusion','Initial asymmetric compound'),('05_level3_final_fusion','Final hierarchical fusion')]:
            p=root/b/name;v=pd.read_csv(p/'validation_predictions.csv')
            pages.append(validation_plot(v,tr,events,contract,b.replace('_',' ')+' — '+label,p/'compound_validation_report.pdf'))
        pages.append(forecast_plot(curves[b]['prospective_forecast'],b.replace('_',' '),root/b/'05_level3_final_fusion/prospective_forecast_report.pdf'))
    pages += [validation_plot(val,training_for_plot(branches[0]),events,contract,'Final main / minor energy fusion',out/'compound_validation_report.pdf'),
              forecast_plot(fc,'Final main / minor energy fusion',out/'prospective_forecast_report.pdf')]
    pages.append(text_page('Energy Pipeline and Audit',[
        ('Five committed stages','01_data: raw exogenous masters and explicit binary event targets. 02_level1: KAN, Deep ResNet and LCS screening. 03_level1_fusion: peak/calm asymmetric fusion. 04_level2_deep_meta_optimizer: refinement and its own fusion. 05_level3_final_fusion: fusion of the two stage trajectories. Finally, main/minor curves combine with fixed weights.'),
        ('Real inputs and date adaptation',f"Requested M{contract['requested_magnitude']:.1f}; effective M{contract['effective_magnitude']:.1f}. Validation weeks: {', '.join(contract['validation_event_weeks'])}. Training ends before {contract['training_end_exclusive']}. Every threshold and training-retention attempt is saved in data_contract.json."),
        ('Selection and inference','The 0-1 peak/calm calibration is chosen on the validation event corridors. It is applied unchanged to the prospective grid. Base model training, scaling and prototype construction use training only; raw astronomical features are known in advance. This is a fixed one-shot reconstruction, not incremental retraining or independent testing.'),
        ('Actual final fusion quality',json.dumps(q))],out/'energy_audit.pdf'))
    from production_report_navigation import compose,infer_entry
    report=root/'ENERGY_FORECAST_MASTER_REPORT.pdf';navigation=compose([infer_entry(p) for p in pages],report,'Energy Forecast - Contents')
    save_json(out/'report_manifest.json',{'report':str(report),'pages':navigation['pages'],'sha256':sha(report),'page_sources':[str(p) for p in pages],'metrics':q,'status':'generated_pending_visual_review'})
    return report,q
