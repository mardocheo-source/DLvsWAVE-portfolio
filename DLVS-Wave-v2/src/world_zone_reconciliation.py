"""Bounded parent/child reconciliation before fitting a child's location models.

A neighboring-zone union requires consecutive parent/child energy weeks, a
changed winning parent location zone, spatial adjacency, and small score gaps
at both dates. A recent-event rectangle is derived from their combined support.
The driver allows one reconciliation per node, archives earlier single-domain
fits, preserves consumed time and starts fresh energy/location fits. It must not
reuse a single-zone model as a model fitted on the larger domain. The generated
lineage page and JSON explain each decision. See docs/FORECAST_RULES_AUDIT.md.
"""
from pathlib import Path
import json
import shutil
import numpy as np
import pandas as pd
from production_geography import vectors,select_peak,geometry
from production_location import sha,save_json
from world_zoom import event_rectangle


def adjacent(centers,a,b,step=1.):
    lon,lat=np.meshgrid(np.arange(-180,180,step),np.arange(-89.5,90,step))
    labels=(vectors(lat.ravel(),lon.ravel())@np.asarray(centers).T).argmax(1).reshape(lat.shape)
    for other in [np.roll(labels,1,axis=1),np.vstack([labels[:1],labels[:-1]])]:
        if np.any(((labels==a)&(other==b))|((labels==b)&(other==a))):return True
    return False


def decide(parent,node,events,config):
    parent,node=Path(parent),Path(node)
    result={'triggered':False,'reason':'no_reconciliation_required','parent_node':str(parent),'child_node':str(node)}
    if not config.get('zone_reconciliation_enabled',True):return {**result,'reason':'disabled'}
    forecast=parent/'02_location_forecast/dual_method_reports/fused_methods/prospective_forecast.csv'
    zonesfile=parent/'02_location_forecast/01_data/spatial_zones_metadata.json'
    energy=node/'01_energy_forecast/fusion_main_minor/final_prospective_forecast.csv'
    if not all(p.exists() for p in [forecast,zonesfile,energy]):return {**result,'reason':'parent_or_child_output_missing'}
    peak=select_peak(pd.read_csv(energy),config)['selected'];origin=config.get('parent_event',{})
    if not peak or not origin:return {**result,'reason':'peak_missing'}
    old,new=pd.Timestamp(origin['apex']),pd.Timestamp(peak['apex']);gap=abs((old-new).days)
    if not 0<gap<=config.get('zone_reconciliation_max_gap_days',7):return {**result,'reason':'dates_not_consecutive','gap_days':gap}
    f=pd.read_csv(forecast);dates=pd.to_datetime(f.date);rows=[]
    for date in [old,new]:
        match=f.loc[dates.eq(date)]
        if len(match)!=1:return {**result,'reason':'parent_week_missing'}
        rows.append(match.iloc[0])
    zones=json.loads(zonesfile.read_text());cols=[f'prob_Zone_{i}' for i in range(len(zones['centers']))]
    oldscores,newscores=[r[cols].to_numpy(float) for r in rows];a,b=int(oldscores.argmax()),int(newscores.argmax())
    if a==b:return {**result,'reason':'same_zone'}
    if not adjacent(zones['centers'],a,b):return {**result,'reason':'zones_not_adjacent','zone_ids':[a,b]}
    margin=max(abs(oldscores[a]-oldscores[b]),abs(newscores[a]-newscores[b]))
    if margin>config.get('zone_reconciliation_max_score_gap',.05):return {**result,'reason':'score_gap_exceeds_joint_policy','score_gap':float(margin)}
    parentstate=json.loads((parent/'node_state.json').read_text());ancestors=parentstate['membership_rules']
    union=ancestors+[{'centers':zones['centers'],'zone':a,'zones':sorted([a,b]),'buffer_km':config.get('minimum_child_buffer_km',25)}]
    rules,support=event_rectangle(events,union,config)
    return {**result,'triggered':True,'reason':'consecutive_weeks_adjacent_zones_and_close_parent_scores','zone_ids':sorted([a,b]),'parent_peak':origin,'child_peak':peak,'gap_days':gap,'parent_scores':{str(old.date()):oldscores.tolist(),str(new.date()):newscores.tolist()},'maximum_score_gap':float(margin),'policy':{'max_gap_days':config.get('zone_reconciliation_max_gap_days',7),'max_score_gap':config.get('zone_reconciliation_max_score_gap',.05),'adjacency':'shared nearest-centroid boundary on 1-degree spherical grid','maximum_reconciliations_per_node':1},'membership_rules':rules,'geometry':geometry(rules),'rectangle_support':support,'source_sha256':{str(p):sha(p) for p in [forecast,zonesfile,energy]},'numerical_status':'unified_domain_requires_fresh_energy_and_location_fits'}


def apply(root,node,entry,decision):
    root,node=Path(root),Path(node)
    archive=root/'test'/f"{node.name}_before_zone_union"
    if archive.exists():raise FileExistsError(archive)
    archive.parent.mkdir(exist_ok=True);shutil.move(str(node),str(archive));node.mkdir(parents=True)
    keep={k:entry[k] for k in ['level','node_id','node_budget_started_epoch','node_elapsed_seconds'] if k in entry}
    entry.clear();entry.update(keep,status='not_executed',domain_override=decision['membership_rules'],membership_rules=decision['membership_rules'],geometry=decision['geometry'],reconciliation_count=1,reconciliation=decision)
    decision['archived_source_node']=str(archive)
    save_json(node/'zone_reconciliation.json',decision);save_json(node/'node_state.json',entry)


def lineage_page(node,decision):
    from world_location_reports import text_page
    ids=' + '.join(str(z) for z in decision['zone_ids'])
    return text_page('Why these neighbouring zones are analysed together',[
        ('One combined study area',f'Parent zones {ids} are treated as one geographic study domain. Internal location subzones will be fitted again inside this combined area.'),
        ('Why the domain changed',f"Parent energy selected {decision['parent_peak']['apex']}; the narrower child energy study selected {decision['child_peak']['apex']}. The parent location winner changes between neighbouring zones over these consecutive weeks. Their scores are close (maximum gap {decision['maximum_score_gap']:.4f})."),
        ('Geographic construction',f"The combined recent catalogue supplies {decision['rectangle_support']['support_events']} events. Recency-weighted coordinate limits and a {decision['rectangle_support']['margin_km']} km margin define one rectangle, handling the date line explicitly."),
        ('Lineage and recalculation', 'Parent fused location CSV -> child energy CSV -> consecutive-week and adjacency checks -> union of parent zones -> recent-event rectangle -> fresh energy and location fits. Previous single-zone models are archived and are not presented as forecasts for the union.'),
        ('Reproducibility', 'zone_reconciliation.json records dates, zone IDs, scores, bounds, source SHA-256 hashes and the archived calculation. One reconciliation per node prevents repeated expansion. Validation remains a model-selection set.')
    ],Path(node)/'ZONE_UNION_LINEAGE.pdf')
