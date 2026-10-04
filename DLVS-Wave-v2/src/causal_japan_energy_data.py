"""Issue-time Japan energy inputs; rebuild raw seismic lags and packed astronomy."""
from pathlib import Path
from dataclasses import asdict
import json
import numpy as np
import pandas as pd
from production_location import save_json,save_csv,sha
from src.compression import BitPackingConfig,QuantizedBitPacker


def seismic_features(dates,events,issue,lags):
    """Closed historical weeks only, frozen at issue time for the entire horizon."""
    dates=pd.DatetimeIndex(dates);issue=pd.Timestamp(issue)
    visible=events.loc[events.time<issue].copy()
    visible['week']=visible.time.dt.to_period('W-SUN').dt.start_time
    grouped=visible.groupby('week').agg(magnitude=('mag','max'),depth=('depth','mean'),count=('mag','size'))
    latest_closed=issue.to_period('W-SUN').start_time-pd.Timedelta(weeks=1)
    values={};lineage=[]
    for lag in lags:
        assert lag>=1
        target=dates-pd.Timedelta(weeks=lag)
        anchors=pd.DatetimeIndex(np.minimum(target.to_numpy(),np.datetime64(latest_closed)))
        assert ((anchors+pd.Timedelta(weeks=1))<=issue).all()
        sampled=grouped.reindex(anchors).fillna(0)
        for metric in ['magnitude','depth','count']:
            name=f'seis_past_{metric}_lag_{lag}w'
            values[name]=sampled[metric].to_numpy(float)
        lineage.extend({'target_week':str(d),'lag_weeks':lag,'source_week':str(a),'source_end_exclusive':str(a+pd.Timedelta(weeks=1)),'issue_time':str(issue)} for d,a in zip(dates,anchors))
    return pd.DataFrame(values),lineage


def prepare(config,energy):
    energy=Path(energy);events=pd.read_csv(config['japan_catalog'])
    events['time']=pd.to_datetime(events.time,utc=True).dt.tz_localize(None)
    cutoff=pd.Timestamp(config['catalog_cutoff']);events=events.loc[events.time<cutoff].copy()
    events['date']=events.time.dt.to_period('W-SUN').dt.start_time
    world=pd.read_csv(config['world_catalog']);world['time']=pd.to_datetime(world.time,utc=True).dt.tz_localize(None)
    world=world.loc[~(world.latitude.between(22,50.5)&world.longitude.between(122,156))]
    magnitude=float(config['magnitude']);width=config['validation_half_width_weeks']
    specs=[]
    for i,event in enumerate(config['validation_event_weeks'],1):
        center=pd.Timestamp(event);dates=pd.date_range(center-pd.Timedelta(weeks=width),center+pd.Timedelta(weeks=width),freq='7D')
        specs.append((f'validation_{i}',dates[0],dates,i,center))
    forecast_dates=pd.date_range(config['forecast_first_week'],config['forecast_last_week'],freq='7D')
    specs.append(('forecast',pd.Timestamp(config['forecast_issue']),forecast_dates,0,None))
    assert pd.Timestamp(config['forecast_issue'])<=cutoff
    contract={'effective_magnitude':magnitude,'requested_magnitude':magnitude,'validation_event_weeks':config['validation_event_weeks'],
        'validation_earthquakes':len(config['validation_event_weeks']),'half_width_weeks':width,'training_end_exclusive':str(specs[0][1]),
        'forecast_issue':config['forecast_issue'],'protocol':'rolling-origin validation, fixed one-shot within each corridor; separate pre-forecast refit',
        'target_tail_policy':'Last training week is observed only until issue time; partial tail coverage is explicitly saved. No unobserved tail days are labelled calm.',
        'seismic_policy':'Past completed weeks only; per-row source ends never exceed the issue time. No output backshift.',
        'input_hashes':{k:sha(config[k]) for k in ['japan_catalog','world_catalog']}}
    energy.mkdir(parents=True,exist_ok=True);save_json(energy/'data_contract.json',contract);save_csv(energy/'events.csv',events)
    for branch,source in config['raw_astronomy'].items():
        data=energy/branch/'01_data';data.mkdir(parents=True,exist_ok=True)
        raw=pd.read_csv(source,low_memory=False);raw['date']=pd.to_datetime(raw.date).dt.normalize();raw=raw.sort_values('date').drop_duplicates('date')
        # Drop every supplied offset. Reconstruct the known astronomy offsets in actual weeks.
        astro=[c for c in raw if c.startswith('astro_') and '_shift_' not in c]
        base=raw[['date']+astro].copy().set_index('date')
        core=[c for c in astro if any(c.endswith('_'+x) for x in ['ra_app_min','dec_app_min','dist_min','elev_min'])]
        shifted={}
        for c in core[:int(config.get('astronomy_shift_max_base_fields',12))]:
            for lag in config['astro_offset_weeks']:
                shifted[f'{c}_offset_{lag:+d}w']=base[c].reindex(base.index+pd.Timedelta(weeks=lag)).to_numpy()
        base=pd.concat([base,pd.DataFrame(shifted,index=base.index)],axis=1)
        if config.get('compact_astronomy',False):base=base[core+list(shifted)]
        lean=core+list(shifted);allastro=list(base.columns);seis_names=None;context_meta={}
        for name,issue,predict_dates,event_number,center in specs:
            start=pd.Timestamp(config['training_start']);training_dates=base.index[(base.index>=start)&(base.index<issue)]
            dates=training_dates.append(predict_dates);frame=base.reindex(dates).reset_index(names='date')
            # Missing early astronomy is declared, fixed zero; no future-dependent fill.
            frame[allastro]=frame[allastro].fillna(0)
            visible=events.loc[(events.time<issue)&events.mag.ge(magnitude)]
            train_weeks=set(visible.date);frame['event_target']=[int(d in train_weeks) if d<issue else 0 for d in dates]
            if name!='forecast':frame.loc[len(training_dates):,'event_target']=[int(d in set(events.loc[events.mag.ge(magnitude)].date)) for d in predict_dates]
            else:frame.loc[len(training_dates):,'event_target']=np.nan
            foreign=set(world.loc[(world.time<issue)&world.mag.ge(magnitude),'time'].dt.to_period('W-SUN').dt.start_time)
            frame['is_world_hard_negative']=[int(d in foreign and d not in train_weeks) for d in dates]
            frame['observed_target_days']=[min(7.,max(0.,(issue-d).total_seconds()/86400)) for d in dates]
            seis,lineage=seismic_features(dates,events,issue,config['seismic_lag_weeks']);seis_names=list(seis)
            frame=pd.concat([frame.reset_index(drop=True),seis],axis=1)
            fit_mask=np.arange(len(frame))<len(training_dates)
            packer=QuantizedBitPacker(BitPackingConfig(prune_zero_variance=False))
            packed,codebook=packer.pack(frame[['date']+allastro],feature_cols=allastro,fit_mask=fit_mask)
            packed_names=[c for c in packed if c.startswith('packed_')]
            assert not any('seis' in c for fields in codebook.containers.values() for c in fields)
            frame=pd.concat([frame,packed[packed_names].reset_index(drop=True)],axis=1)
            context=data/name;context.mkdir(exist_ok=True)
            training=frame.iloc[:len(training_dates)].copy();prediction=frame.iloc[len(training_dates):].copy()
            if event_number:
                prediction['event_number']=event_number;prediction['relative_week']=((prediction.date-center).dt.days/7).astype(int)
            save_csv(context/'training.csv',training);save_csv(context/'prediction.csv',prediction)
            save_json(context/'bitwise_codebook.json',asdict(codebook));save_csv(context/'seismic_source_times.csv',pd.DataFrame(lineage,columns=['target_week','lag_weeks','source_week','source_end_exclusive','issue_time']))
            partial=training.loc[training.observed_target_days.lt(7),['date','observed_target_days','event_target']].astype(str).to_dict('records')
            context_meta[name]={'issue_time':str(issue),'training_last_week':str(training.date.max()),'training_rows':len(training),'training_event_weeks':int(training.event_target.sum()),
                'partial_terminal_target_intervals':partial,'quantization_fit_end':str(codebook.quantile_fit_end_date),'predict_rows':len(prediction),
                'training_sha256':sha(context/'training.csv'),'prediction_sha256':sha(context/'prediction.csv'),'codebook_sha256':sha(context/'bitwise_codebook.json')}
        manifest={'contexts':context_meta,'lean_features':lean+seis_names,'bitwise_features':packed_names+seis_names,
            'bitwise_source_fields':allastro,'excluded_supplied_seismic_columns':[c for c in raw if c.startswith('seis_')],
            'raw_astronomy_sha256':sha(source),'seismic_fields_rebuilt_from_issue_limited_catalog':True,'supplied_offset_columns_reconstructed':True}
        save_json(data/'causal_master_manifest.json',manifest)
        # Compatibility tables for the unchanged hierarchy and reporting interface.
        save_csv(data/'training_master.csv',pd.read_csv(data/'validation_1/training.csv'))
        save_csv(data/'validation_master.csv',pd.concat([pd.read_csv(data/f'validation_{i}/prediction.csv') for i in range(1,len(specs))],ignore_index=True))
        save_csv(data/'prospective_master.csv',pd.read_csv(data/'forecast/prediction.csv'))
    return energy
