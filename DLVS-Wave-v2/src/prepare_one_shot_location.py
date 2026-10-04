#!/usr/bin/env python3
"""Build audited one-shot inputs: train-only zones and raw known ephemerides.

This builder reuses catalog events, never old predicted zone labels. It excludes
seismic lag columns from both training and inference for the exogenous one-shot
protocol. All numeric scaling is fitted inside each model's training window.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from production_location import save_json,save_csv,sha


def build(config):
    source=Path(config['source_spatial_root']);output=Path(config['output_spatial_root'])
    if output.exists() and any(output.iterdir()):raise ValueError('Fresh input output directory required')
    output.mkdir(parents=True,exist_ok=True);data=output/'01_data';data.mkdir()
    old=json.loads((source/'event_only_master_manifest.json').read_text())
    frames={s:pd.read_csv(source/'01_data'/f'{s}_events.csv') for s in ['training','validation']}
    cutoff=pd.Timestamp(old['validation_start'])
    assert pd.to_datetime(frames['training'].time,utc=True,format='mixed').max()<cutoff
    assert pd.to_datetime(frames['validation'].time,utc=True,format='mixed').min()>=cutoff
    assert set(frames['training'].id).isdisjoint(frames['validation'].id)
    k=int(config.get('zone_count',5));coords=frames['training'][['latitude','longitude']].to_numpy()
    fit=KMeans(n_clusters=k,random_state=config.get('seed',42),n_init=20).fit(coords)
    centers=fit.cluster_centers_[np.argsort(-fit.cluster_centers_[:,0])]
    def assign(frame):
        a=np.radians(frame[['latitude','longitude']].to_numpy());b=np.radians(centers)
        h=np.sin((a[:,None,0]-b[None,:,0])/2)**2+np.cos(a[:,None,0])*np.cos(b[None,:,0])*np.sin((a[:,None,1]-b[None,:,1])/2)**2
        return h.argmin(1)
    changes={};labels={};geometry=[];zones=[]
    for s,f in frames.items():
        predicted=assign(f);changed=f.zone_id.to_numpy()!=predicted
        changes[s]=f.loc[changed,['id','time','zone_id']].assign(training_only_zone=predicted[changed]).to_dict('records')
        f['zone_id']=predicted;f['zone_name']=[f'Zone {z}' for z in predicted]
        assert set(predicted)==set(range(k)),'Missing validation/training zone; adapt threshold within fixed window before fitting'
        save_csv(data/f'{s}_events.csv',f)
        rows=[]
        for date,g in f.groupby('date',sort=True):
            row={'date':date,'event_count':len(g),'event_ids':';'.join(g.id.astype(str)),
                 'target_zone_ids':';'.join(str(z) for z in sorted(g.zone_id.unique())),
                 'event_magnitude_max':float(g.mag.max())}
            row.update({f'target_Zone_{z}':int(g.zone_id.eq(z).any()) for z in range(k)});rows.append(row)
        labels[s]=pd.DataFrame(rows)
    colors=['#DC2626','#2563EB','#7C3AED','#EA580C','#0891B2','#16A34A','#CA8A04','#DB2777']
    # Ellipses are training-only descriptive dispersion, not predictive coverage.
    for z,c in enumerate(centers):
        subset=frames['training'].loc[frames['training'].zone_id.eq(z)]
        vals,vecs=np.linalg.eigh(np.cov(subset.longitude,subset.latitude));order=np.argsort(-vals);vals,vecs=vals[order],vecs[:,order]
        geometry.append({'zone_id':z,'center_lat':float(c[0]),'center_lon':float(c[1]),
                         'width_deg':float(max(2*2.45*np.sqrt(max(vals[0],.04)),2)),
                         'height_deg':float(max(2*2.45*np.sqrt(max(vals[1],.04)),1.8)),
                         'angle_deg':float(np.degrees(np.arctan2(vecs[1,0],vecs[0,0]))),'color':colors[z%len(colors)]})
        zones.append({'zone_id':z,'name':f'Zone {z}','centroid_lat':float(c[0]),'centroid_lon':float(c[1]),
                      'training_event_count':len(subset),'max_magnitude':float(subset.mag.max()),'color':colors[z%len(colors)]})
    save_json(data/'spatial_zones_metadata.json',{'zones':zones,'zone_fit_scope':'training events only','zone_fit_end_exclusive':str(cutoff),'seed':config.get('seed',42)})
    save_json(output/'report_metadata/original_zone_geometry.json',{'audit':{'method':'Training-only KMeans and covariance ellipses; preserves original map technique, not hindsight-fitted boundaries'},'ellipses':geometry})
    input_hashes={str(source/'01_data'/f'{s}_events.csv'):sha(source/'01_data'/f'{s}_events.csv') for s in frames}
    feature_contracts={}
    for branch,raw_file in config['raw_astronomy_masters'].items():
        # Preserve the reference body/field selection; reconstruct temporal offsets
        # from raw unscaled ephemerides, with calendar offsets explicitly verified.
        names=pd.read_csv(source/branch/'01_data/training_master.csv',nrows=0).columns
        astro=[c for c in names if c.startswith('astro_')];base_cols=[c for c in astro if '_shift_' not in c]
        raw=pd.read_csv(raw_file,usecols=['date']+base_cols);raw['date']=pd.to_datetime(raw.date)
        raw=raw.set_index('date').sort_index();assert raw.index.is_unique
        feature=raw.copy();lineage={}
        for col in astro:
            if '_shift_' not in col:
                lineage[col]={'raw_field':col,'offset_days':0,'known_in_advance':True};continue
            base,mode,weeks=col.rsplit('_shift_',1)[0],col.rsplit('_shift_',1)[1].split('_')[0],int(col.rsplit('_',1)[1].replace('w',''))
            days=7*weeks*(1 if mode=='lead' else -1)
            feature[col]=raw[base].reindex(raw.index+pd.Timedelta(days=days)).to_numpy()
            lineage[col]={'raw_field':base,'offset_days':days,'known_in_advance':True}
        feature=feature[astro];feature.index=feature.index.strftime('%Y-%m-%d');feature.index.name='date';feature=feature.reset_index()
        base=output/branch/'01_data';base.mkdir(parents=True,exist_ok=True)
        for split in ['training','validation']:
            merged=labels[split].merge(feature,on='date',how='left',validate='one_to_one')
            if merged[astro].isna().any().any():raise ValueError('Ephemeris coverage missing; download missing dates, do not fill')
            assert np.isfinite(merged[astro]).all().all();save_csv(base/f'{split}_master.csv',merged)
        old_dates=pd.read_csv(source/branch/'01_data/prospective_master.csv',usecols=['date'])
        future=old_dates.merge(feature,on='date',how='left',validate='one_to_one')
        assert np.isfinite(future[astro]).all().all();save_csv(base/'prospective_master.csv',future)
        feature_contracts[branch]={'raw_master':str(Path(raw_file).resolve()),'raw_master_sha256':sha(raw_file),
                                   'feature_count':len(astro),'features':lineage,'excluded_fields':[c for c in names if c.startswith('seis_')],
                                   'scaling':'none in builder; fit only selected model training rows'}
        input_hashes[str(Path(raw_file).resolve())]=sha(raw_file)
    manifest={**old,'status':'one_shot_masters_complete','zone_count':k,'training_events':len(frames['training']),'training_weeks':len(labels['training']),
              'validation_events':len(frames['validation']),'validation_weeks':len(labels['validation']),
              'validation_event_counts':{str(z):int(frames['validation'].zone_id.eq(z).sum()) for z in range(k)},
              'input_hashes':input_hashes,'forecast_mode':'one_shot_exogenous_features_fixed_model',
              'zone_fit_scope':'training events before validation_start only','all_features_known_in_advance':True,
              'feature_contracts':feature_contracts,'zone_assignment_changes_from_reference':changes,
              'validation_used_for':'hyperparameter/feature/ensemble/calibration selection; not an untouched test',
              'builder_sha256':sha(__file__)}
    save_json(output/'event_only_master_manifest.json',manifest)
    save_json(output/'one_shot_leakage_audit.json',{'training_validation_ids_disjoint':True,'training_before_validation':True,
              'zones_fitted_on_training_only':True,'validation_coordinates_not_used_to_fit_zones':True,
              'features_only_raw_known_astronomy':True,'no_seismic_lags_or_event_fields_in_features':True,
              'no_global_fitted_normalization_or_imputation':True,'fixed_validation_window':True,
              'no_online_weight_update_during_validation_or_forecast':True,'selection_set_is_not_independent_test':True,
              'zone_assignment_changes':changes,'source_manifest_sha256':sha(output/'event_only_master_manifest.json')})
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True)
    args=p.parse_args();print(json.dumps(build(json.loads(args.config.read_text())),indent=2))
