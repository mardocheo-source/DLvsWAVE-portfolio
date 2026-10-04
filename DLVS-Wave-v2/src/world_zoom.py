"""Reproducible temporal and seismic-support zooms for geographic child nodes."""
import numpy as np
import pandas as pd
from production_geography import membership


def temporal_zoom(config, peak):
    start=pd.Timestamp(peak.get('start',peak['apex']))
    apex_dt=pd.Timestamp(peak['apex'])
    end=pd.Timestamp(peak.get('end',str((apex_dt+pd.Timedelta(days=6)).date())))
    return {'forecast_start':str((start-pd.Timedelta(weeks=config.get('child_weeks_before',2))).date()),
            'forecast_end':str((end+pd.Timedelta(weeks=config.get('child_weeks_after',2))).date()),
            'selection_start':str((start-pd.Timedelta(weeks=config.get('child_weeks_before',2))).date())}


def event_rectangle(events,rules,config):
    """Recent-event, recency-weighted central coverage with a geodesic margin.

    Only records available at the catalogue cutoff define the child domain.
    Longitudes are unwrapped about the parent centroid, avoiding a globe-wide
    bounding box for a compact cluster crossing the international date line.
    """
    from forecast_magnitudes import policy
    magnitudes=policy(config)
    cutoff=pd.Timestamp(config['catalog_cutoff']).tz_localize(None)
    date=pd.to_datetime(events['time'] if 'time' in events else events['date'],utc=True).dt.tz_localize(None)
    years=config.get('child_rectangle_recent_years',10)
    eligible=membership(events,rules)&(date<=cutoff)&(date>=cutoff-pd.DateOffset(years=years))&(events.mag>=magnitudes['location_training_magnitude'])
    sample=events.loc[eligible].copy();dates=date.loc[eligible]
    if len(sample)<config.get('child_rectangle_min_events',12):
        eligible=membership(events,rules)&(date<=cutoff)&(date>=cutoff-pd.DateOffset(years=years))&(events.mag>=config.get('download_floor',5.5))
        sample=events.loc[eligible].copy();dates=date.loc[eligible]
    if len(sample)<3:raise ValueError('insufficient_recent_events_for_child_rectangle')
    last=rules[-1]
    if last.get('type')=='rectangle':center=(last['bounds'][2]+last['bounds'][3])/2
    else:
        c=last['centers'][last['zone']];center=np.degrees(np.arctan2(c[1],c[0]))
    lon=center+(sample.longitude.to_numpy()-center+180)%360-180
    weights=np.exp2(-(cutoff-dates).dt.total_seconds().to_numpy()/(365.25*86400*config.get('child_rectangle_half_life_years',5)))
    coverage=config.get('child_rectangle_axis_coverage',.98)
    def limits(values):
        order=np.argsort(values);v=np.asarray(values)[order];w=weights[order];cdf=(np.cumsum(w)-.5*w)/w.sum()
        return np.interp([(1-coverage)/2,1-(1-coverage)/2],cdf,v)
    south,north=limits(sample.latitude.to_numpy());west,east=limits(lon)
    pad=config.get('child_rectangle_buffer_km',200)/111.195
    latmid=(south+north)/2;lonpad=pad/max(.2,np.cos(np.radians(latmid)))
    bounds=[max(-90,float(south-pad)),min(90,float(north+pad)),float(west-lonpad),float(east+lonpad)]
    rect={'type':'rectangle','bounds':bounds}
    contained=membership(sample,[rect])
    audit={'algorithm':'recency-weighted central coordinate quantiles plus km margin','recent_years':years,'half_life_years':config.get('child_rectangle_half_life_years',5),'axis_coverage':coverage,'margin_km':config.get('child_rectangle_buffer_km',200),'support_events':len(sample),'contained_events':int(contained.sum()),'cutoff':str(cutoff),'event_ids':sample.id.astype(str).tolist(),'bounds':bounds,'scope':'parent training and validation catalogue available at cutoff; child validation is selection-set evaluation'}
    return rules[:-1]+[rect],audit
