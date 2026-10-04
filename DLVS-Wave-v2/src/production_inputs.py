"""Verified raw USGS/JPL inputs for parameterized production forecasts."""
from __future__ import annotations
import argparse
import io
import json
import logging
from pathlib import Path
import time
import urllib.parse
import urllib.request
import pandas as pd
import numpy as np
from production_location import save_json,save_csv,sha

LOG=logging.getLogger('production_inputs')


def request_bytes(url,timeout=45):
    request=urllib.request.Request(url,headers={'User-Agent':'DLVS-Wave-production-research/2.0'})
    with urllib.request.urlopen(request,timeout=timeout) as response:return response.read()


def load_catalog(config,output):
    output=Path(output)/'catalog';output.mkdir(parents=True,exist_ok=True)
    final=output/'events.csv';manifest=output/'manifest.json'
    contract={k:config[k] for k in ['training_start','catalog_cutoff','download_floor']}
    if final.exists() and manifest.exists():
        meta=json.loads(manifest.read_text());assert meta['contract']==contract and meta['sha256']==sha(final)
        return pd.read_csv(final,parse_dates=['time','date'])
    start=pd.Timestamp(config['training_start']);end=pd.Timestamp(config['catalog_cutoff']).tz_localize(None)
    parts=[];receipts=[];deadline=time.time()+config.get('download_max_seconds',900)
    while start<end:
        if time.time()>deadline:raise TimeoutError('catalog_download_budget')
        stop=min(start+pd.DateOffset(years=5),end);name=f'{start:%Y%m%d}_{stop:%Y%m%d}_m{config["download_floor"]:.1f}.csv';path=output/name
        params={'format':'csv','starttime':start.isoformat(),'endtime':stop.isoformat(),'minmagnitude':config['download_floor'],'orderby':'time-asc','limit':20000}
        url='https://earthquake.usgs.gov/fdsnws/event/1/query?'+urllib.parse.urlencode(params)
        receipt=path.with_suffix('.json')
        if path.exists() and receipt.exists():
            audit=json.loads(receipt.read_text());assert audit['url']==url and audit['sha256']==sha(path)
        else:
            LOG.info('USGS catalog %s to %s M>=%.1f',start.date(),stop.date(),config['download_floor'])
            raw=request_bytes(url,config.get('request_timeout_seconds',45))
            if not raw.strip():raw=b'id,time,latitude,longitude,depth,mag\n'
            parsed=pd.read_csv(io.BytesIO(raw))
            if len(parsed)>=20000:raise ValueError('USGS response reached cap; shorten configured query interval')
            path.write_bytes(raw);audit={'url':url,'sha256':sha(path),'rows':len(parsed),'downloaded_epoch':time.time()};save_json(receipt,audit)
        parts.append(pd.read_csv(path));receipts.append(audit);start=stop
    catalog=pd.concat(parts,ignore_index=True);catalog['time']=pd.to_datetime(catalog.time,utc=True,format='mixed').dt.tz_localize(None)
    for c in ['latitude','longitude','depth','mag']:catalog[c]=pd.to_numeric(catalog[c],errors='coerce')
    catalog=catalog.dropna(subset=['time','latitude','longitude','mag']);catalog['depth']=catalog.depth.fillna(0)
    catalog=catalog.loc[(catalog.time>=pd.Timestamp(config['training_start']))&(catalog.time<=end)].sort_values('time').drop_duplicates('id')
    catalog['longitude']=(catalog.longitude+180)%360-180;catalog['date']=catalog.time.dt.to_period('W-SUN').dt.start_time
    save_csv(final,catalog);save_json(manifest,{'contract':contract,'sha256':sha(final),'rows':len(catalog),'requests':receipts,
               'catalog_revision_scope':'Later retrieved historical catalog constrained by occurrence time, not an archived as-of publication snapshot'})
    return catalog.reset_index(drop=True)


def load_astronomy(config,output,observer=None):
    """Verify cached inputs and fetch missing head/tail epochs or topocentric coordinates.

    Astronomical time offsets are known in advance. Padding supports later
    nested forecast zooms; it never extends the earthquake catalog cutoff.
    """
    from astroquery.jplhorizons import Horizons,conf
    conf.timeout=config.get('request_timeout_seconds',45)
    output=Path(output)/'astronomy';output.mkdir(parents=True,exist_ok=True)
    policy=config.get('astronomy_observer_policy','geocentric_all_nodes')
    if observer is None:
        if policy not in ['geocentric_all_nodes','geocentric_root_topocentric_children']:
            raise ValueError('Unsupported observer policy; refusing implicit Japan observer')
        observer_loc='500@399'
        observer_label='500@399'
        observer_policy='geocentric_all_nodes'
    else:
        lat=float(observer['lat'])
        lon=float((observer['lon']+180)%360-180)
        elev=float(observer.get('elevation',0.0))
        observer_loc={'lat':round(lat,4),'lon':round(lon,4),'elevation':round(elev,3)}
        observer_label=f"topocentric@{lat:.4f},{lon:.4f}"
        observer_policy='topocentric_centroid'

    manifest_path=output/'manifest.json'
    if manifest_path.exists():
        try:
            meta=json.loads(manifest_path.read_text())
            if meta.get('observer')==observer_label or (observer is None and meta.get('observer') in ['500@399',None]):
                features={}
                valid=True
                for group in ['main','minor']:
                    csv_path=output/f'{group}_raw_features.csv'
                    if not csv_path.exists() or meta.get('feature_sha256',{}).get(group)!=sha(csv_path):
                        valid=False;break
                    features[f'{group}_bodies_branch']=pd.read_csv(csv_path,parse_dates=['date'])
                if valid:
                    LOG.info('Loaded verified astronomy features from %s (%s)',output,observer_label)
                    return features
        except Exception:
            pass

    root=Path(config['astronomy_raw_cache']) if (config.get('astronomy_raw_cache') and observer is None) else output/'raw_cache'
    offsets=config.get('astronomy_offset_weeks',[-13,4,13])
    padding=int(config.get('astronomy_horizon_padding_weeks',0))
    start=pd.Timestamp(config['training_start'])-pd.Timedelta(weeks=max(0,-min(offsets)))
    # Anchor all inputs on Monday, the exact seismic aggregation grid.
    start=start.to_period('W-SUN').start_time
    feature_stop=pd.Timestamp(config['forecast_end'])+pd.Timedelta(weeks=padding)
    stop=feature_stop+pd.Timedelta(weeks=max(0,max(offsets))+1)
    defaults={'main':[('sun','10',None),('moon','301',None),('mercury','199',None),('venus','299',None),('mars','499',None),('jupiter','599',None),('saturn','699',None)],
              'minor':[('ceres','1','smallbody'),('pallas','2','smallbody'),('vesta','4','smallbody'),('chiron','2060','smallbody'),('io','501',None),('europa','502',None),('ganymede','503',None),('callisto','504',None),('titan','606',None)]}
    deadline=time.time()+config.get('download_max_seconds',900)
    manifests={}
    for group in ['main','minor']:
        manifest_stem=f'world_{group}_manifest.json' if observer is None else f'topocentric_{group}_manifest.json'
        matches=sorted(root.glob(f'*{manifest_stem}'))
        if matches:
            manifests[group]=json.loads(matches[0].read_text());continue
        records=[];rawdir=output/'raw_cache';rawdir.mkdir(parents=True,exist_ok=True)
        wanted=config.get(f'{group}_bodies')
        for name,command,id_type in defaults[group]:
            if wanted is not None and name not in wanted:continue
            if time.time()>deadline:raise TimeoutError('astronomy_download_budget')
            body={'name':name,'command':command,'id_type':id_type}
            req={'body':body,'observer':observer_label,'start':str(start.date()),'stop':str((stop+pd.Timedelta(days=7)).date()),'step':'7d','quantities':'1,20'}
            p=rawdir/f'{name}.csv';receipt=p.with_suffix('.json')
            if p.exists() and receipt.exists():
                record=json.loads(receipt.read_text());assert record['request']==req and record['sha256']==sha(p)
            else:
                LOG.info('JPL %s raw history %s %s to %s',observer_policy,name,req['start'],req['stop'])
                h=Horizons(id=command,id_type=id_type,location=observer_loc,epochs={k:req[k] for k in ['start','stop','step']})
                raw=h.ephemerides(quantities='1,20',cache=False).to_pandas()
                f=pd.DataFrame({'date':pd.to_datetime(raw.datetime_jd,origin='julian',unit='D').dt.round('s')})
                for source,suffix in [('RA','ra_app_min'),('DEC','dec_app_min'),('delta','dist_min')]:f[f'astro_{name}_{suffix}']=pd.to_numeric(raw[source])
                save_csv(p,f);record={'request':req,'file':str(p.resolve()),'sha256':sha(p),'rows':len(f)};save_json(receipt,record)
            records.append(record)
        manifests[group]=records
        save_json(rawdir/manifest_stem,records)
    result={};provenance=[]
    for group,records in manifests.items():
        frames=[]
        wanted=config.get('main_bodies',['sun','moon','jupiter','saturn','mars']) if group=='main' else config.get('minor_bodies')
        for record in records:
            request=record['request'];body=request['body']
            if wanted is not None and body['name'] not in wanted:continue
            assert request['observer']==observer_label,'Wrong astronomical observer in cache'
            p=Path(record['file']);assert sha(p)==record['sha256']
            f=pd.read_csv(p,parse_dates=['date']);f=f.sort_values('date')
            if f.date.min()>start:
                head=output/f'{body["name"]}_head.csv';receipt=head.with_suffix('.json')
                req={'body':body,'observer':observer_label,'start':str(start.date()),'stop':str(f.date.min().date()),'step':'7d','quantities':'1,20'}
                if head.exists() and receipt.exists():
                    meta=json.loads(receipt.read_text());assert meta['request']==req and meta['sha256']==sha(head)
                    hframe=pd.read_csv(head,parse_dates=['date'])
                else:
                    if time.time()>deadline:raise TimeoutError('astronomy_download_budget')
                    LOG.info('JPL head %s %s to %s',body['name'],req['start'],req['stop'])
                    h=Horizons(id=body['command'],id_type=body['id_type'],location=observer_loc,epochs={k:req[k] for k in ['start','stop','step']})
                    raw=h.ephemerides(quantities='1,20',cache=False).to_pandas()
                    hframe=pd.DataFrame({'date':pd.to_datetime(raw.datetime_jd,origin='julian',unit='D').dt.round('s')})
                    for source,suffix in [('RA','ra_app_min'),('DEC','dec_app_min'),('delta','dist_min')]:hframe[f'astro_{body["name"]}_{suffix}']=pd.to_numeric(raw[source])
                    save_csv(head,hframe);save_json(receipt,{'request':req,'sha256':sha(head),'rows':len(hframe)})
                f=pd.concat([hframe,f],ignore_index=True).drop_duplicates('date').sort_values('date')
            tail_start=f.date.max()+pd.Timedelta(days=7);tail=output/f'{body["name"]}_tail.csv';tail_meta=tail.with_suffix('.json')
            if f.date.max()<stop:
                req={'body':body,'observer':observer_label,'start':str(tail_start.date()),'stop':str((stop+pd.Timedelta(days=7)).date()),'step':'7d','quantities':'1,20'}
                if tail.exists() and tail_meta.exists() and json.loads(tail_meta.read_text()).get('request')==req:
                    meta=json.loads(tail_meta.read_text());assert meta['request']==req and meta['sha256']==sha(tail)
                    t=pd.read_csv(tail,parse_dates=['date'])
                else:
                    if time.time()>deadline:raise TimeoutError('astronomy_download_budget')
                    LOG.info('JPL tail %s %s to %s',body['name'],req['start'],req['stop'])
                    h=Horizons(id=body['command'],id_type=body['id_type'],location=observer_loc,epochs={k:req[k] for k in ['start','stop','step']})
                    raw=h.ephemerides(quantities='1,20',cache=False).to_pandas()
                    t=pd.DataFrame({'date':pd.to_datetime(raw.datetime_jd,origin='julian',unit='D').dt.round('s')})
                    for source,suffix in [('RA','ra_app_min'),('DEC','dec_app_min'),('delta','dist_min')]:t[f'astro_{body["name"]}_{suffix}']=pd.to_numeric(raw[source])
                    save_csv(tail,t);save_json(tail_meta,{'request':req,'sha256':sha(tail),'rows':len(t)})
                f=pd.concat([f,t],ignore_index=True).drop_duplicates('date').sort_values('date')
            frames.append(f.set_index('date'));provenance.append({'cached_raw':str(p),'cached_sha256':sha(p),'body':body,'observer':observer_policy,'observer_label':observer_label,'tail':str(tail) if tail.exists() else None})
        f=pd.concat(frames,axis=1).sort_index();core=list(f)
        if f.isna().any().any():raise ValueError('Raw astronomy body date mismatch')
        shifts={}
        shift_core=core if 'astronomy_offset_weeks' in config else core[:12]
        if 'astronomy_shift_max_base_fields' in config:shift_core=core[:int(config['astronomy_shift_max_base_fields'])]
        for col in shift_core:
            for weeks in offsets:
                label=('lead_' if weeks>=0 else 'lag_')+str(abs(weeks))+'w'
                shifts[f'{col}_shift_{label}']=f[col].reindex(f.index+pd.Timedelta(weeks=weeks)).to_numpy()
        f=pd.concat([f,pd.DataFrame(shifts,index=f.index)],axis=1)
        f=f.loc[(f.index>=pd.Timestamp(config['training_start']))&(f.index<=feature_stop)]
        if not np.isfinite(f.to_numpy()).all():raise ValueError('Missing astronomy coverage; no imputation permitted')
        result[f'{group}_bodies_branch']=f.reset_index()
        save_csv(output/f'{group}_raw_features.csv',f.reset_index())
    save_json(output/'manifest.json',{'observer_policy':observer_policy,'observer':observer_label,'raw_sources':provenance,'normalization':'none; fit within model training','available_in_advance':True,
              'field_semantics':'Legacy ra_app_min/dec_app_min names contain Horizons quantity 1 astrometric RA/DEC in degrees; dist_min contains delta in AU. No min aggregation or apparent-coordinate transformation is implied.',
              'feature_sha256':{group:sha(output/f'{group}_raw_features.csv') for group in ['main','minor']}})
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();config=json.loads(args.config.read_text());logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    catalog=load_catalog(config,args.output);astro=load_astronomy(config,args.output)
    save_json(args.output/'inputs_complete.json',{'catalog_events':len(catalog),'astronomy_rows':{k:len(v) for k,v in astro.items()},'status':'complete'})
