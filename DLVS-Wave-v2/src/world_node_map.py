"""Create a readable geographic scope sheet before a world's node starts fitting."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mpl_toolkits.basemap import Basemap
from production_geography import geometry,membership

def build(node,state,config):
    node=Path(node);node.mkdir(parents=True,exist_ok=True)
    rules=state.get('membership_rules',config.get('parent_region_rules',[]));g=geometry(rules)
    south,north,west,east=g['bounds'];center=g['centroid'][1]
    regional=bool(rules and rules[-1].get('type')=='rectangle')
    padx=max(5,(east-west)*.15);pady=max(5,(north-south)*.15)
    left,right=(west-padx,east+padx) if regional else (center-180,center+180)
    bottom,top=(max(-89,south-pady),min(89,north+pady)) if regional else (-90,90)
    fig=plt.figure(figsize=(11.693,8.268));ax=fig.add_axes([.07,.31,.86,.55])
    m=Basemap(projection='cyl',llcrnrlon=left,urcrnrlon=right,llcrnrlat=bottom,urcrnrlat=top,resolution='c',ax=ax)
    m.drawmapboundary(fill_color='#EFF6FF');m.fillcontinents(color='#E2E8F0',lake_color='#EFF6FF');m.drawcoastlines(linewidth=.5)
    lon,lat=np.meshgrid(np.linspace(left,right,361),np.linspace(bottom,top,181));grid=pd.DataFrame({'longitude':lon.ravel(),'latitude':lat.ravel()});mask=membership(grid,rules).reshape(lon.shape)
    ax.contourf(lon,lat,mask,levels=[.5,1.5],colors=['#38BDF8'],alpha=.35)
    if mask.any() and not mask.all():ax.contour(lon,lat,mask.astype(float),levels=[.5],colors=['#0284C7'],linewidths=1.4)
    ax.add_patch(Rectangle((west,south),east-west,north-south,fill=False,edgecolor='#DC2626',linewidth=2,linestyle='--'))
    m.drawparallels([-60,-30,0,30,60],labels=[1,0,0,0],linewidth=.3,fontsize=8)
    m.drawmeridians(np.arange(round(left/20)*20,right+1,20),labels=[0,0,0,1],linewidth=.3,fontsize=8)
    level=state.get('level',0);label=(' - Combined parent zones '+ ' + '.join(map(str,config['combined_parent_zones']))) if config.get('combined_parent_zones') else ' - Area being analysed';fig.suptitle(f'Geographic level {level}{label}',fontsize=18,weight='bold',y=.96)
    peak=config.get('parent_event',{})
    fig.text(.07,.9,f"Selected event window: {peak.get('start','not selected')} to {peak.get('end','not selected')}  |  Selection: {config.get('selection_mode','first_peak')}",fontsize=10)
    if state.get('reconciliation') and not state.get('energy_quality'):
        fig.text(.07,.865,'Combined-domain recalculation pending | Previous single-zone forecasts are archived',fontsize=9,color='#B45309')
    ec=state.get('energy_contract',{});lc=state.get('location_contract',{})
    from forecast_magnitudes import policy
    magnitudes=policy(config)
    obs_raw=state.get('observer',config.get('astronomy_observer','500@399'))
    obs_desc='Geocentric (500@399)' if obs_raw=='500@399' else f'Topocentric ({obs_raw})'
    lines=[f"Blue area: actual selection. Red rectangle: geographic bounds. Centre: {g['centroid'][0]:.2f}, {center:.2f} | Observer: {obs_desc}.",f"Bounds: latitude {south:.1f} to {north:.1f}; longitude {west:.1f} to {east:.1f} (unwrapped across the dateline).",f"Forecast: {config.get('forecast_start')} to {config.get('forecast_end')} | Input cutoff: {config.get('catalog_cutoff')}",f"Magnitude: download >= {config.get('download_floor')} | Energy training >= {ec.get('training_magnitude',magnitudes['energy_training_magnitude'])}; validation requested >= {magnitudes['energy_validation_magnitude']}, used >= {ec.get('effective_magnitude','pending')}",f"Location: training >= {lc.get('training_magnitude',magnitudes['location_training_magnitude'])}, validation >= {lc.get('validation_magnitude','pending')} | Validation events: {lc.get('validation_events','pending')}",f"Location validation: {lc.get('validation_start','pending')} to {lc.get('validation_end','pending')} | Training events: {lc.get('training_events','pending')}"]
    for i,line in enumerate(lines):fig.text(.07,.235-i*.029,line,fontsize=8.8,color='#334155')
    for ext in ['png','pdf']:fig.savefig(node/f'AREA_AND_PARAMETERS.{ext}',dpi=150)
    plt.close(fig);(node/'AREA_AND_PARAMETERS.json').write_text(json.dumps({'geometry':g,'parent_event':peak,'configuration':config,'energy_contract':ec,'location_contract':lc},indent=2,default=str))
    return node/'AREA_AND_PARAMETERS.pdf'
