"""Spherical membership and node-specific energy/location data contracts.

Energy validation selects recent isolated event corridors with training-retention
and magnitude-reduction limits. World energy features are astronomical only;
this adapter does not implement the separate causal Japan forecast refit or
pi-infill/bitwise protocol. Location fits zones using pre-validation events and
uses only occupied weeks as multi-target training rows. Its validation threshold
may decrease within the downloaded catalog floor to meet per-zone support.
See docs/FORECAST_PIPELINE_GUIDE.md for the full protocol comparison and limits.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from production_location import save_json,save_csv,sha

RADIUS_KM=6371.0088


def vectors(latitude,longitude):
    lat,lon=np.radians(latitude),np.radians(longitude)
    return np.column_stack([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)])


def membership(events,rules):
    xyz=vectors(events.latitude,events.longitude);mask=np.ones(len(events),bool)
    for rule in rules:
        if rule.get('type')=='rectangle':
            south,north,west,east=rule['bounds'];center=(west+east)/2
            lon=center+(events.longitude.to_numpy()-center+180)%360-180
            mask &= events.latitude.between(south,north).to_numpy() & (lon>=west) & (lon<=east)
            continue
        angles=np.arccos(np.clip(xyz@np.asarray(rule['centers']).T,-1,1))
        zone_ids=rule['zones'] if 'zones' in rule else [rule['zone']]
        mask &= angles[:,zone_ids].min(1) <= angles.min(1)+rule.get('buffer_km',0)/RADIUS_KM+1e-12
    return mask


def geometry(rules,step=1.):
    lon,lat=np.meshgrid(np.arange(-180+step/2,180,step),np.arange(-90+step/2,90,step))
    grid=pd.DataFrame({'latitude':lat.ravel(),'longitude':lon.ravel()});m=membership(grid,rules)
    area=float(np.cos(np.radians(grid.latitude[m])).sum()/np.cos(np.radians(grid.latitude)).sum())
    if not rules:return {'area_fraction':1.,'bounds':[-90.,90.,-180.,180.],'centroid':[0.,0.],'crosses_antimeridian':False}
    if not m.any():return {'area_fraction':0.,'bounds':None,'centroid':None}
    if rules[-1].get('type')=='rectangle':
        south,north,west,east=rules[-1]['bounds']
        return {'area_fraction':area,'bounds':[south,north,west,east],'centroid':[(south+north)/2,(west+east)/2],'crosses_antimeridian':west < -180 or east > 180,'membership':'rectangle intersected with ancestor regions'}
    c=np.asarray(rules[-1]['centers'])[rules[-1]['zone']]
    clat=float(np.degrees(np.arcsin(c[2])));clon=float(np.degrees(np.arctan2(c[1],c[0])))
    longitudes=clon+(grid.longitude[m].to_numpy()-clon+180)%360-180
    west,east=float(longitudes.min()-step/2),float(longitudes.max()+step/2)
    return {'area_fraction':area,'bounds':[max(-90.,float(grid.latitude[m].min()-step/2)),min(90.,float(grid.latitude[m].max()+step/2)),west,east],
            'centroid':[clat,clon],'crosses_antimeridian':west < -180 or east > 180,
            'grid_resolution_degrees':step,'membership':'exact spherical angular Voronoi margin; bounds/area approximated only for display'}


def cluster_zones(training,config,output):
    xyz=vectors(training.latitude,training.longitude);candidates=[]
    for k in config.get('zone_counts',[3,4,5,6,8]):
        if len(training)<k*config.get('minimum_zone_training_events',8):continue
        fit=KMeans(n_clusters=k,n_init=20,random_state=config.get('seed',42)).fit(xyz)
        centers=fit.cluster_centers_;centers/=np.linalg.norm(centers,axis=1,keepdims=True)
        labels=np.argmax(xyz@centers.T,axis=1);counts=np.bincount(labels,minlength=k)
        if counts.min()<config.get('minimum_zone_training_events',8):continue
        score=float(silhouette_score(xyz,labels,metric='euclidean',sample_size=min(2000,len(xyz)),random_state=42))
        candidates.append({'k':k,'silhouette_chord_distance':score,'min_support':int(counts.min()),'counts':counts.tolist(),'centers':centers.tolist()})
    if not candidates:raise ValueError('insufficient_training_support_for_zones')
    winner=max(candidates,key=lambda r:(r['silhouette_chord_distance'],-r['k']))
    centers=np.array(winner['centers']);order=np.lexsort((np.arctan2(centers[:,1],centers[:,0]),-centers[:,2]));centers=centers[order]
    labels=np.argmax(xyz@centers.T,axis=1);records=[]
    for z,c in enumerate(centers):
        sub=training.iloc[np.flatnonzero(labels==z)]
        angles=np.arccos(np.clip(xyz[labels==z]@c,-1,1))
        records.append({'zone_id':z,'name':f'Zone {z}','centroid_lat':float(np.degrees(np.arcsin(c[2]))),
                        'centroid_lon':float(np.degrees(np.arctan2(c[1],c[0]))),'training_event_count':len(sub),
                        'max_magnitude':float(sub.mag.max()),'median_radius_km':float(np.median(angles)*RADIUS_KM),
                        'p95_radius_km':float(np.quantile(angles,.95)*RADIUS_KM),'color':['#DC2626','#2563EB','#7C3AED','#EA580C','#0891B2','#16A34A','#CA8A04','#DB2777'][z%8]})
    result={'zones':records,'centers':centers.tolist(),'fit_scope':'training events before fixed validation window','selection':'maximum training silhouette, smaller k on tie',
            'candidates':candidates,'seed':config.get('seed',42),'geometry':'spherical nearest unit centroid; canonical north-to-south IDs'}
    save_json(output,result);return result


def prepare_location(events,astronomy,node_dir,config):
    from forecast_magnitudes import validate as magnitude_policy
    magnitudes=magnitude_policy(config)
    out=Path(node_dir)/'02_location_forecast';data=out/'01_data';data.mkdir(parents=True,exist_ok=True)
    end=pd.Timestamp(config['catalog_cutoff']);end=end.tz_localize(None) if end.tzinfo else end
    start=end.normalize()-pd.Timedelta(days=int(config.get('location_validation_days',2028)))
    # Use the next weekly boundary so no validation input slot precedes the window.
    start=start.to_period('W-SUN').start_time+pd.Timedelta(days=7)
    if config.get('_location_validation_start'):start=pd.Timestamp(config['_location_validation_start'])
    training=events.loc[(events.date<start)&(events.mag>=magnitudes['location_training_magnitude'])].copy()
    if len(training)<config.get('minimum_location_training_events',40):raise ValueError('insufficient_location_training_events')
    zones=cluster_zones(training,config,data/'spatial_zones_metadata.json');centers=np.array(zones['centers']);k=len(centers)
    training['zone_id']=np.argmax(vectors(training.latitude,training.longitude)@centers.T,axis=1)
    attempts=[];validation=None
    for mag in np.arange(magnitudes['location_validation_magnitude'],magnitudes['location_validation_min_magnitude']-.001,-config.get('magnitude_step',.1)):
        mag=round(float(mag),3);v=events.loc[(events.date>=start)&(events.time<=end)&(events.mag>=mag)].copy()
        maximum=config.get('maximum_location_validation_events')
        if maximum is not None and len(v)>maximum:
            # Move the actual split, then refit geographic zones on the expanded
            # training history. Never truncate just the chart or split one week.
            boundary=pd.Timestamp(v.sort_values('time').iloc[-int(maximum)].date)
            if len(v.loc[v.date>=boundary])>maximum:boundary+=pd.Timedelta(weeks=1)
            if boundary<=start:raise ValueError('location_event_limit_cannot_shrink_window')
            revised=dict(config);revised['_location_validation_start']=str(boundary)
            revised['_location_window_adjustments']=config.get('_location_window_adjustments',[])+[{'previous_start':str(start),'new_start':str(boundary),'magnitude':mag,'previous_events':len(v),'maximum_events':int(maximum)}]
            return prepare_location(events,astronomy,node_dir,revised)
        labels=np.argmax(vectors(v.latitude,v.longitude)@centers.T,axis=1) if len(v) else np.array([],int)
        counts=np.bincount(labels,minlength=k);okay=bool(counts.min()>=config.get('minimum_zone_validation_events',1) and len(v)>=config.get('minimum_location_validation_events',12))
        attempts.append({'magnitude':mag,'validation_events':len(v),'counts':counts.tolist(),'sufficient':okay})
        if okay:v['zone_id']=labels;validation=v;break
    save_json(out/'threshold_attempts.json',attempts)
    if validation is None:raise ValueError('location_validation_zone_coverage_failed_at_floor')
    if config.get('compact_location_validation',False):
        # Seek the shortest whole-week suffix covering every fitted zone. Refit
        # zones at that new split; retain this successful split if the candidate
        # loses geographic support. Bound retries because zone definitions change.
        budget=config.get('location_window_refinement_max_steps',3)
        step=config.get('_location_compact_step',0)
        for boundary in sorted(validation.date.unique(),reverse=True):
            tail=validation.loc[validation.date>=boundary]
            counts=tail.zone_id.value_counts().reindex(range(k),fill_value=0)
            if len(tail)>=config.get('minimum_location_validation_events',12) and counts.min()>=config.get('minimum_zone_validation_events',1):
                boundary=pd.Timestamp(boundary)
                if boundary>start and step<budget:
                    revised=dict(config);revised.update(_location_validation_start=str(boundary),_location_compact_step=step+1)
                    revised['_location_window_adjustments']=config.get('_location_window_adjustments',[])+[{'previous_start':str(start),'new_start':str(boundary),'previous_events':len(validation),'candidate_events':len(tail),'reason':'shortest whole-week suffix covering all zones; zones refitted at new split'}]
                    try:return prepare_location(events,astronomy,node_dir,revised)
                    except ValueError as error:
                        config=dict(config);config['_location_window_adjustments']=config.get('_location_window_adjustments',[])+[{'retained_start':str(start),'rejected_start':str(boundary),'reason':str(error)}]
                        # A rejected candidate may have written its metadata.
                        save_json(data/'spatial_zones_metadata.json',zones);save_json(out/'threshold_attempts.json',attempts)
                break
    for frame in [training,validation]:
        frame['date']=frame.date.dt.strftime('%Y-%m-%d');frame['zone_name']=[f'Zone {z}' for z in frame.zone_id]
    save_csv(data/'training_events.csv',training);save_csv(data/'validation_events.csv',validation)
    def labels(frame):
        rows=[]
        for date,g in frame.groupby('date',sort=True):
            row={'date':date,'event_count':len(g),'event_ids':';'.join(g.id.astype(str)),'event_magnitude_max':float(g.mag.max())}
            row.update({f'target_Zone_{z}':int(g.zone_id.eq(z).any()) for z in range(k)});rows.append(row)
        return pd.DataFrame(rows)
    train_labels,val_labels=labels(training),labels(validation)
    for branch,astro in astronomy.items():
        base=out/branch/'01_data';base.mkdir(parents=True,exist_ok=True);astro=astro.copy();astro['date']=pd.to_datetime(astro.date).dt.strftime('%Y-%m-%d')
        for name,target in [('training',train_labels),('validation',val_labels)]:
            merged=target.merge(astro,on='date',how='left',validate='one_to_one')
            if merged.isna().any().any():raise ValueError('missing_location_features')
            save_csv(base/f'{name}_master.csv',merged)
        future=astro.loc[(astro.date>=config['forecast_start'])&(astro.date<=config['forecast_end'])]
        if len(future)==0:raise ValueError('empty_forecast')
        save_csv(base/'prospective_master.csv',future)
    manifest={'status':'masters_complete','training_magnitude':magnitudes['location_training_magnitude'],'validation_magnitude':attempts[-1]['magnitude'],
              'requested_validation_magnitude':magnitudes['location_validation_magnitude'],'minimum_validation_magnitude':magnitudes['location_validation_min_magnitude'],
              'training_events':len(training),'training_weeks':len(train_labels),'validation_events':len(validation),'validation_weeks':len(val_labels),
              'validation_start':str(start),'validation_end':str(end),'zone_count':k,'validation_event_counts':validation.zone_id.value_counts().sort_index().to_dict(),
              'event_only':True,'normalization_fit_scope':'each trial training rows','training_retained_fraction':float(len(training)/(len(training)+len(validation))),
              'zone_fit_scope':zones['fit_scope'],'attempts':attempts,'window_adjustments':config.get('_location_window_adjustments',[])}
    save_json(out/'event_only_master_manifest.json',manifest);return out,manifest,zones


def energy_contract(events,config):
    from forecast_magnitudes import validate as magnitude_policy,energy_training
    magnitudes=magnitude_policy(config)
    cutoff=pd.Timestamp(config['catalog_cutoff']);cutoff=cutoff.tz_localize(None) if cutoff.tzinfo else cutoff
    minimum_date=cutoff-pd.DateOffset(years=int(config.get('max_energy_validation_age_years',5)))
    requested=magnitudes['energy_validation_magnitude'];floor=magnitudes['energy_validation_min_magnitude']
    attempts=[];count=int(config.get('energy_validation_events',2))
    for threshold in np.arange(requested,floor-.001,-config.get('magnitude_step',.1)):
        threshold=round(float(threshold),3);eligible=events.loc[events.mag>=threshold].sort_values('time')
        training_threshold=energy_training(config,threshold)
        training_eligible=events.loc[events.mag>=training_threshold]
        weeks=eligible.groupby('date',as_index=False).agg(mag=('mag','max'),event_count=('id','size'))
        recent=weeks.loc[(weeks.date>=minimum_date)&(weeks.date<cutoff-pd.Timedelta(days=14))]
        if len(recent)<count:
            attempts.append({'threshold':threshold,'recent_event_weeks':len(recent),'reason':'too_few_recent_events'});continue
        from itertools import combinations
        candidate_indices=list(combinations(range(max(0,len(recent)-100),len(recent)),count))
        candidate_indices.sort(key=lambda ids:tuple(reversed(ids)),reverse=True)
        for ids in candidate_indices:
            selected=recent.iloc[list(ids)];centers=selected.date.tolist()
            for width in config.get('energy_corridor_half_width_choices',[13,8,4,2,1]):
                start=min(centers)-pd.Timedelta(weeks=width);end=max(centers)+pd.Timedelta(weeks=width)
                if end>cutoff:continue
                if any((b-a).days<=14*width for a,b in zip(centers,centers[1:])):continue
                rows=[];valid=True
                for i,center in enumerate(centers,1):
                    dates=pd.date_range(center-pd.Timedelta(weeks=width),center+pd.Timedelta(weeks=width),freq='7D')
                    positives=weeks.loc[weeks.date.isin(dates)]
                    if len(positives)!=1:valid=False;break
                    rows.extend({'date':d,'event_number':i,'relative_week':j-width,'event_target':int(d==center)} for j,d in enumerate(dates))
                if not valid:continue
                train_events=training_eligible.loc[training_eligible.date<start];fraction=1-len(train_events)/max(len(training_eligible),1)
                enough=len(train_events)>=config.get('minimum_energy_training_events',12) and fraction<=config.get('max_training_event_removal_fraction',.25)
                attempts.append({'threshold':threshold,'half_width_weeks':width,'training_events':len(train_events),'removed_fraction':fraction,'sufficient':enough})
                if not enough:continue
                return {'requested_magnitude':requested,'effective_magnitude':threshold,'training_end_exclusive':str(start),'validation_event_weeks':[str(d.date()) for d in centers],
                        'training_magnitude':training_threshold,'forecast_refit_magnitude':training_threshold,'minimum_validation_magnitude':floor,
                        'thresholds_differ':training_threshold!=threshold,
                        'validation_earthquakes':int(selected.event_count.sum()),'half_width_weeks':width,'attempts':attempts},pd.DataFrame(rows)
    raise ValueError('insufficient_recent_energy_validation_with_training_retention: '+json.dumps(attempts))


def prepare_energy(events,astronomy,node_dir,config):
    if config.get('energy_protocol')=='origin_refit_astro_only':
        from world_origin_energy import prepare
        return prepare(events,astronomy,node_dir,config)
    out=Path(node_dir)/'01_energy_forecast';out.mkdir(parents=True,exist_ok=True)
    contract,val=energy_contract(events,config);save_json(out/'data_contract.json',contract)
    target_weeks=set(events.loc[events.mag>=contract['training_magnitude'],'date']);start=pd.Timestamp(contract['training_end_exclusive'])
    for branch,astro in astronomy.items():
        f=astro.copy();f['date']=pd.to_datetime(f.date);f['event_target']=f.date.isin(target_weeks).astype(int)
        base=out/branch/'01_data';base.mkdir(parents=True,exist_ok=True)
        training=f.loc[f.date<start];validation=val.merge(f.drop(columns='event_target'),on='date',how='left',validate='one_to_one')
        future=f.loc[f.date.between(config['forecast_start'],config['forecast_end'])].drop(columns='event_target')
        # Strict one-shot mode uses only known ephemerides, consistently with
        # location. Seismic-only occurrence labels remain separate from features.
        if config.get('forecast_mode','one_shot')!='one_shot':
            raise ValueError('Online seismic-feature inference requires its own explicit origin schedule')
        for split,a in [('training',training),('validation',validation),('prospective',future)]:
            if a.isna().any().any():raise ValueError('missing_energy_features')
            save_csv(base/f'{split}_master.csv',a)
    return out,contract


def select_peak(frame,config):
    p=frame.predicted_prob.to_numpy();threshold=config.get('energy_peak_threshold',.7)
    if config.get('selection_mode')=='first_event':
        from scipy.signal import find_peaks
        p_range=float(p.max()-p.min()) if len(p) else 0.
        min_prom=float(config.get('minimum_peak_prominence',max(1e-4,0.10*p_range)))
        indices,props=find_peaks(p,plateau_size=1,prominence=min_prom)
        candidates=[]
        lefts=props.get('left_edges',indices)
        rights=props.get('right_edges',indices)
        proms=props.get('prominences',np.zeros(len(indices)))
        sel_start=pd.Timestamp(config.get('selection_start',config['forecast_start']))
        for k,i in enumerate(indices):
            l=int(lefts[k]);r=int(rights[k])
            start_date=pd.Timestamp(frame.iloc[l].date)
            end_date=pd.Timestamp(frame.iloc[r].date)+pd.Timedelta(days=6)
            apex_date=pd.Timestamp(frame.iloc[i].date)
            reason='before_selection_start' if apex_date<sel_start else None
            candidates.append({'start':str(start_date.date()),'end':str(end_date.date()),
                               'apex':str(apex_date.date()),'height':float(p[i]),
                               'prominence':float(proms[k]),'rows':list(range(l,r+1)),
                               'rejection_reason':reason})
        eligible=[c for c in candidates if c['rejection_reason'] is None]
        return {'mode':'first_event','candidates':candidates,'selected':eligible[0] if eligible else None,'stop_reason':None if eligible else 'no_local_maximum'}
    if config.get('selection_mode')=='largest_observed_peak':
        eligible=np.flatnonzero(pd.to_datetime(frame.date)>=pd.Timestamp(config.get('selection_start',config['forecast_start'])))
        if not len(eligible):return {'mode':'largest_observed_peak','candidates':[],'selected':None,'stop_reason':'empty_selection_period'}
        apex=int(eligible[np.argmax(p[eligible])]);date=pd.Timestamp(frame.iloc[apex].date)
        selected={'start':str(date.date()),'end':str((date+pd.Timedelta(days=6)).date()),'apex':str(date.date()),'height':float(p[apex]),'rows':[apex],'rejection_reason':None}
        return {'mode':'largest_observed_peak','candidates':[selected],'selected':selected,'stop_reason':None}

    high=np.flatnonzero(p>=threshold);groups=np.split(high,np.flatnonzero(np.diff(high)>1)+1) if len(high) else []
    candidates=[]
    for indices in groups:
        apex=int(indices[np.argmax(p[indices])]);left=float(p[indices[0]-1]) if indices[0]>0 else 0.;right=float(p[indices[-1]+1]) if indices[-1]+1<len(p) else 0.
        prominence=float(p[apex]-max(left,right));date=pd.Timestamp(frame.iloc[apex].date)
        reason='before_selection_start' if date<pd.Timestamp(config.get('selection_start',config['forecast_start'])) else ('insufficient_prominence' if prominence<config.get('minimum_peak_prominence',.05) else None)
        candidates.append({'start':str(pd.Timestamp(frame.iloc[indices[0]].date).date()),'end':str((pd.Timestamp(frame.iloc[indices[-1]].date)+pd.Timedelta(days=6)).date()),
                           'apex':str(date.date()),'height':float(p[apex]),'prominence':prominence,'rows':indices.tolist(),'rejection_reason':reason})
    eligible=[c for c in candidates if c['rejection_reason'] is None]
    mode=config.get('selection_mode','first_peak')
    if mode not in ['first_peak','largest_peak']:raise ValueError('unsupported selection_mode')
    selected=min(eligible,key=lambda c:(-c['height'],c['apex']) if mode=='largest_peak' else (c['apex'],)) if eligible else None
    return {'mode':mode,'candidates':candidates,'selected':selected,'stop_reason':None if selected else 'no_significant_peak'}


def choose_child(parent_rules,zones,location_forecast,peak,config):
    k=len(zones['zones']);columns=[f'prob_Zone_{z}' for z in range(k)]
    scores=location_forecast.iloc[peak['rows']][columns].mean().to_numpy();zone=int(np.argmax(scores))
    radius=zones['zones'][zone]['median_radius_km']
    buffer=max(config.get('minimum_child_buffer_km',25),config.get('child_buffer_fraction',.1)*radius)
    rule={'centers':zones['centers'],'zone':zone,'buffer_km':float(buffer)};rules=parent_rules+[rule]
    before,after=geometry(parent_rules),geometry(rules)
    if after['area_fraction']>=before['area_fraction']*.995:raise ValueError('child_area_not_reduced')
    order=np.argsort(-scores,kind='stable');margin=float(scores[order[0]]-scores[order[1]])
    return rules,{'selected_zone':zone,'scores':scores.tolist(),'runner_up_zone':int(order[1]),'score_margin':margin,
                  'ambiguity_gate_passed':margin>=config.get('minimum_child_zone_margin',.05),
                  'margin_interpretation':'Declared score-separation heuristic, not calibrated confidence',
                  'peak':peak,'buffer_km':buffer,'buffer_fraction':config.get('child_buffer_fraction',.1),
                  'parent_geometry':before,'child_geometry':after,'membership_rules':rules,'selection':'largest mean location marginal on selected energy peak rows; lowest zone ID breaks exact ties'}
