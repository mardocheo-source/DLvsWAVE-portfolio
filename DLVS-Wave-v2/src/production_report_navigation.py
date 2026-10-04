"""Data-driven PDF contents and navigation, including intermediate documents."""
from pathlib import Path
import io
import json
import math
import re
import shutil
import textwrap
import matplotlib.pyplot as plt
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import NameObject, TextStringObject

RED='#DC2626'


def location_method_note(entry):
    """Explain the method on each relevant page; never infer an observed success."""
    if 'LOCATION FORECAST' not in entry.get('section',''):return ''
    s=(entry.get('method','')+' '+entry.get('branch','')).lower()
    if 'combined' in s or 'a+b' in s:
        return 'Combined scores from both location methods; this is a synthesis, not a third independent forecast.'
    if 'neural' in s and ('historical' in s or 'analog' in s):
        return 'Two separate location methods: compare their own validation and maps for the same energy window.'
    if 'historical' in s or 'analog' in s:
        return 'Historical analogs: similar past inputs vote for zones. Results can differ from the neural method.'
    if 'kan' in s or 'neural' in s:
        return 'Neural location: KAN, Deep ResNet and LCS learn zone associations. Results can differ from historical analogs.'
    return ''


def readable_entry(entry):
    entry=dict(entry)
    replacements={'A+B':'Combined neural and historical methods','A / B / A+B':'Neural models / Historical analogs / Combined methods','A - ':'Neural models: ','B - ':'Historical method: '}
    for field in ['branch','method','title']:
        value=entry.get(field,'')
        for old,new in sorted(replacements.items(),key=lambda item:-len(item[0])):value=value.replace(old,new)
        entry[field]=value
    match=re.search(r'/L(\d+)/([^/]+)/',entry.get('path',''))
    if match and not entry.get('section','').startswith('Geographic level'):
        level=int(match.group(1));region='World' if level==0 and match.group(2)=='n000_world' else match.group(2)
        entry['section']=f"Geographic level {level} - {region} | "+entry.get('section','')
    return entry



def content_path(path):
    path=Path(path);raw=path.parent/'.page_content'/path.name
    return raw if raw.exists() else path


def navigated_page(page, entry, number, total):
    entry=readable_entry(entry) if 'Geographic level' not in entry.get('section','') else entry
    width,height=float(page.mediabox.width),float(page.mediabox.height)
    result=PdfWriter().add_blank_page(width=width,height=height)
    # Every page, including covers and dividers, reserves real navigation space.
    note=entry.get('note',location_method_note(entry))
    result.merge_transformed_page(page,Transformation().scale(.85).translate(width*.075,height*(.065 if note else .045)))
    buffer=io.BytesIO();fig=plt.figure(figsize=(width/72,height/72))
    fig.patch.set_alpha(0)
    breadcrumb=' > '.join(filter(None,[entry.get('section'),entry.get('branch'),entry.get('title')]))
    fig.text(.04,.978,textwrap.shorten(breadcrumb,width=125,placeholder='...'),fontsize=8,color='#0369A1',weight='bold',va='top')
    fig.text(.5,.942,entry.get('method','Protocol and provenance'),fontsize=10,color=RED,fontstyle='italic',ha='center',va='top')
    fig.text(.04,.015,'DLVS-Wave | '+entry.get('section','Study'),fontsize=7,color='#475569')
    fig.text(.96,.015,f'{number} / {total}',fontsize=8,ha='right',color='#334155')
    if note:fig.text(.04,.042,note,fontsize=7.5,color='#475569',va='bottom')
    fig.savefig(buffer,format='pdf',transparent=True);plt.close(fig);buffer.seek(0)
    result.merge_page(PdfReader(buffer).pages[0]);return result


def decorate(path,entry):
    """Idempotently frame an intermediate PDF while retaining unframed content."""
    path=Path(path);reader=PdfReader(path);raw=path.parent/'.page_content'/path.name
    if not reader.metadata or reader.metadata.get('/DLVSNavigation')!='v2':
        raw.parent.mkdir(exist_ok=True);shutil.copy2(path,raw)
    reader=PdfReader(raw);writer=PdfWriter()
    for i,page in enumerate(reader.pages,1):writer.add_page(navigated_page(page,entry,i,len(reader.pages)))
    writer.add_metadata({'/DLVSNavigation':'v2'})
    temp=path.with_suffix('.navigation.tmp.pdf');writer.write(temp);temp.replace(path)


def infer_entry(path,title=''):
    path=Path(path);s=str(path).lower()
    section='ENERGY FORECAST' if any(part.startswith('01_energy_forecast') for part in path.parts) or path.stem in {'energy_reference_scope','energy_training_protocol','energy_audit'} else 'LOCATION FORECAST'
    if 'historical_analogs' in s or 'b_historical' in s:method='B - Historical weighted analogs'
    elif 'fused_methods' in s:method='A+B - Fusion of learned and historical scores'
    elif section=='LOCATION FORECAST':method='A - KAN + Deep ResNet + LCS'
    else:method='KAN / Deep / LCS - energy ensemble'
    if section=='ENERGY FORECAST' and 'appendix' in path.stem:
        if 'lcs' in path.stem:method='LCS / rebuilt bitwise inputs'
        elif 'deep' in path.stem:method='Deep ResNet / uncompressed inputs'
        elif 'kan' in path.stem:method='KAN / uncompressed inputs'
    if not title:
        phase=next((label for part,label in [('level2_fusion','Refinement'),('03_level1_fusion','Initial'),('05_level3_final_fusion','Final')] if part in path.parts),'')
        title=(phase+' / ' if phase else '')+path.stem.replace('_',' ')
    branch='Main bodies' if 'main_bodies_branch' in s else 'Minor bodies' if 'minor_bodies_branch' in s else 'Main + Minor fusion'
    return {'section':section,'branch':branch,'method':method,'title':title or path.stem.replace('_',' '),'path':str(path)}


def compose(entries,output,title='Study contents'):
    """Generate actual page references; Energy and Location have separate columns."""
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    entries=[readable_entry(e) for e in entries]
    for i,e in enumerate(entries):
        if i and e.get('section','').endswith('OVERVIEW'):e['section']=e['section'][:-len('OVERVIEW')]+'LOCATION FORECAST'
    has_cover=bool(entries and entries[0].get('section')=='OVERVIEW')
    body=entries[1:] if has_cover else entries
    groups={}
    for e in body:groups.setdefault(e['section'],[]).append(e)
    columns=[]
    for section,items in groups.items():
        for start in range(0,len(items),26):columns.append((section,items[start:start+26]))
    toc_count=max(1,math.ceil(len(columns)/2));cursor=(1 if has_cover else 0)+toc_count+1
    for e in body:
        e['page_start']=cursor;e['page_count']=len(PdfReader(content_path(e['path'])).pages);cursor+=e['page_count']
    total=cursor-1;toc_pages=[]
    for idx in range(toc_count):
        fig=plt.figure(figsize=(11.693,8.268));fig.text(.06,.94,title,fontsize=20,weight='bold',color='#0F172A')
        for col,(section,items) in enumerate(columns[idx*2:idx*2+2]):
            x=.06+col*.48;fig.text(x,.88,section.replace(' | ','\n'),fontsize=10,weight='bold',color='#0369A1');y=.817
            for e in items:
                label=f"{e['page_start']:02d}  {e.get('branch','')} / {e['title']}"
                fig.text(x,y,textwrap.shorten(label,width=63,placeholder='...'),fontsize=8,color='#334155')
                fig.text(x+.024,y-.015,textwrap.shorten(e.get('method','Protocol and provenance'),width=68,placeholder='...'),fontsize=7,color=RED,fontstyle='italic')
                y-=.0305
        buffer=io.BytesIO();fig.savefig(buffer,format='pdf');plt.close(fig);buffer.seek(0)
        toc_pages.append(PdfReader(buffer).pages[0])
    writer=PdfWriter();number=0
    if has_cover:
        number+=1;writer.add_page(navigated_page(PdfReader(content_path(entries[0]['path'])).pages[0],entries[0],number,total))
    for page in toc_pages:
        number+=1;writer.add_page(navigated_page(page,{'section':'CONTENTS','title':'Energy / Location','method':'Methods are shown in red italics'},number,total))
    for e in body:
        for page in PdfReader(content_path(e['path'])).pages:
            number+=1;writer.add_page(navigated_page(page,e,number,total))
    assert number==total
    writer.add_metadata({'/DLVSNavigation':'v2'})
    for page in writer.pages:page.compress_content_streams()
    temporary=output.with_suffix('.tmp.pdf');writer.write(temporary);temporary.replace(output)
    navigation={'pages':total,'contents_pages':toc_count,'entries':entries,'every_page_has_navigation':True}
    output.with_suffix('.navigation.json').write_text(json.dumps(navigation,indent=2)+'\n')
    return navigation
