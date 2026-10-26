"""Build small FORGE 16A source extracts without unpacking the GDR archives.

Usage: python validation/forge16a/build_extracts.py --raw PATH

Only the Python standard library is required. Read-only ZIP access preserves
the downloads. No BoreTHM calculation is imported or run. Sources and units
are described in README.md. Each Sanvean series uses 10-second mean bins;
valid counts and state fractions retain missing-data and transition information.
"""
from pathlib import Path
import argparse,bisect,csv,hashlib,io,json,math,re,statistics,time,zipfile
from datetime import datetime,timedelta
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
COLS={
 'bit_depth_ft':'Surface_Depth - Bit(ft)', 'hole_depth_ft':'Surface_Total Depth(ft)',
 'flow_gpm':'Surface_Flow In(GPM)', 'pump_pressure_psi':'Surface_Pump Pressure(psi)',
 'motor_differential_psi':'Surface_Differential Pressure(psi)',
 'bit_box_C':'Bit Box_Temperature(C)', 'top_sub_C':'Top Sub_Temperature(C)',
 'lower_mandrel_C':'Lower Mandrel_Temperature(C)', 'on_bottom_flag':'Surface_GC_OnBottom(bool)',
 'rop_ft_h':'Surface_ROP Depth/Hour(ft/hr)', 'block_position_ft':'Surface_Block Position(ft)'}
FLOW_MAX_GPM=2000.
DRILL_FLOW_GPM=300.
OFF_FLOW_GPM=100.

def number(x):
    try:
        value=float(x)
        return value if math.isfinite(value) and value!=-999.25 else None
    except (TypeError,ValueError):return None
def output(path,rows,fields=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields or list(rows[0]));writer.writeheader();writer.writerows(rows)
def sheet_rows(source,name):
    """Read cached XLSX values without interpreting numeric cells as dates."""
    with zipfile.ZipFile(source) as z:
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            shared=[''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        wb=ET.fromstring(z.read('xl/workbook.xml'))
        rels={n.get('Id'):n.get('Target') for n in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        s=next(n for n in wb.find('m:sheets',NS) if n.get('name')==name)
        target=rels[s.get('{'+NS['r']+'}id')]
        target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
        for row in ET.fromstring(z.read(target)).findall('.//m:sheetData/m:row',NS):
            cells=[]
            for c in row.findall('m:c',NS):
                col=0
                for ch in re.match('[A-Z]+',c.get('r')).group():col=26*col+ord(ch)-64
                while len(cells)<col:cells.append(None)
                v=c.find('m:v',NS)
                value=v.text if v is not None else None
                if c.get('t')=='s' and value is not None:value=shared[int(value)]
                if c.get('t')=='inlineStr':value=''.join(c.find('m:is',NS).itertext())
                cells[col-1]=value
            yield int(row.get('r')),cells
def interpolate(x,xs,ys):
    if not xs[0]<=x<=xs[-1]:return None
    i=min(max(bisect.bisect_right(xs,x)-1,0),len(xs)-2)
    return ys[i]+(ys[i+1]-ys[i])*(x-xs[i])/(xs[i+1]-xs[i])
def survey(raw,out):
    rows=[]
    with zipfile.ZipFile(raw/'1283.zip') as z:
        source=io.BytesIO(z.read('16A(78)-32 Survey.xlsx'))
        for index,cells in sheet_rows(source,'Sheet1'):
            if len(cells)<7:continue
            vals=[number(cells[i]) for i in [1,2,3,4,6]]
            if any(v is None for v in vals):continue
            seq,md,inc,az,tvd=vals
            if not 1<=seq<=1000 or not 0<=inc<=180 or not 0<=tvd<=md+.1:continue
            rows.append(dict(md_ft=md,inc_deg=inc,azi_deg=az,tvd_ft=tvd,source_row=index))
    assert len(rows)==422 and rows[0]['md_ft']==0
    assert all(a['md_ft']<b['md_ft'] for a,b in zip(rows,rows[1:]))
    output(out/'survey_16a.csv',rows)
    return rows
def formation(raw,out,survey_rows):
    xs=[x['md_ft'] for x in survey_rows];ys=[x['tvd_ft'] for x in survey_rows]
    result={}
    source=raw/'Utah FORGE Deep Well Temperature Profiles_Sept 2022.xlsx'
    for name,days in [('16A(78)-32',57),('16A(78)-32_2nd',216)]:
        rows=[];last=-math.inf;endpoint=None
        for i,cells in sheet_rows(source,name):
            if len(cells)<3:continue
            md,temp=number(cells[0]),number(cells[2])
            if md is None or temp is None:continue
            tvd=interpolate(md,xs,ys)
            if tvd is None:continue
            endpoint=dict(md_ft=md,tvd_ft=tvd,temp_F=temp,temp_C=(temp-32)/1.8,
                          workbook_tvd_ft=number(cells[1]),source_row=i)
            if md-last<10:continue
            rows.append(endpoint)
            last=md
        if endpoint is not None and rows[-1]['md_ft']!=endpoint['md_ft']:rows.append(endpoint)
        output(out/f'formation_temperature_{days}day.csv',rows)
        result[str(days)]=dict(rows=len(rows),maximum_MD_ft=rows[-1]['md_ft'],maximum_TVD_ft=rows[-1]['tvd_ft'],last_temperature_C=rows[-1]['temp_C'])
    return result
def mudlog(raw,out):
    fields=['md_ft','rop_ft_h','wob_klbf','CO2','temp_in_F','temp_out_F','pump_pressure_psi','spm1','spm2','spm3',
            'flow_gpm','return_flow_percent','gain_loss_bbl','rpm','torque_ft_lb','pit_volume_bbl']
    rows=[];active=False
    with zipfile.ZipFile(raw/'1283.zip') as z:
        with io.TextIOWrapper(z.open('16A(78)-32 Final mud log.las'),encoding='cp1252') as f:
            for line in f:
                if line.lstrip().startswith('~A'):active=True;continue
                if not active or not line.strip():continue
                values=[number(x) for x in line.split()]
                if len(values)!=len(fields):raise ValueError('Unexpected mud-log column count')
                rows.append(dict(zip(fields,values)))
    output(out/'mud_log_by_depth.csv',rows);return rows
def sanvean(raw,out):
    summaries=[];metadata=[]
    with zipfile.ZipFile(raw/'1292.zip') as outer:
        with outer.open('Forge 16A(78)-32 Sanvean Log.zip') as stream:
            with zipfile.ZipFile(stream) as logs:
                names=sorted([n for n in logs.namelist() if n.startswith('BHA ')],key=lambda n:(int(re.search(r'BHA (\d+)',n).group(1)),n))
                for package in names:
                    run=re.match(r'BHA (\w+)',package).group(1);rows=[];bins={};mins={};maxs={};counts={}
                    phase_seconds=dict(drilling=0.,pumps_off=0.,running_in_pumps_off=0.,unclassified=0.)
                    last=None;first=None;raw_rows=0;invalid_flow=0;high_flow=0;very_high_flow=0;raw_max_flow=None;nonincreasing=0;gaps=0
                    with zipfile.ZipFile(io.BytesIO(logs.read(package))) as z:
                        name=next(n for n in z.namelist() if n.lower().endswith('output data.csv'))
                        with io.TextIOWrapper(z.open(name),encoding='utf-8-sig',newline='') as f:
                            reader=csv.DictReader(line for line in f if line.strip() and not line.startswith('#'))
                            for row in reader:
                                t=datetime.strptime(row['DateTime'],'%Y/%m/%d %H:%M:%S.%f')
                                raw_rows+=1;first=first or t
                                vals={key:number(row.get(source)) for key,source in COLS.items()}
                                q=vals['flow_gpm'];bad=q is not None and not 0<=q<=FLOW_MAX_GPM
                                if q is not None:raw_max_flow=max(raw_max_flow if raw_max_flow is not None else q,q)
                                if q is not None and q>FLOW_MAX_GPM:high_flow+=1
                                if q is not None and q>100000:very_high_flow+=1
                                if bad:invalid_flow+=1;vals['flow_gpm']=None
                                # The source temperature null is blank. Preserve numerical
                                # zeros in the extract; the comparison protocol handles coverage.
                                for key,v in vals.items():
                                    if v is not None:
                                        mins[key]=min(mins.get(key,v),v);maxs[key]=max(maxs.get(key,v),v);counts[key]=counts.get(key,0)+1
                                tbin=t.replace(second=(t.second//10)*10,microsecond=0)
                                bucket=bins.setdefault(tbin,dict(total=0,bad_flow=0,values={k:[] for k in COLS},drilling_count=0,
                                                               drilling_temperature={k:[] for k in ['bit_box_C','top_sub_C','lower_mandrel_C']}))
                                bucket['total']+=1;bucket['bad_flow']+=bad
                                for key,v in vals.items():
                                    if v is not None:bucket['values'][key].append(v)
                                q,b,h,flag,rop=[vals[k] for k in ['flow_gpm','bit_depth_ft','hole_depth_ft','on_bottom_flag','rop_ft_h']]
                                if all(v is not None for v in [q,b,h,flag,rop]) and q>DRILL_FLOW_GPM and abs(b-h)<=5 and flag>.5 and rop>1:
                                    bucket['drilling_count']+=1
                                    for key in bucket['drilling_temperature']:
                                        if vals[key] is not None:bucket['drilling_temperature'][key].append(vals[key])
                                if last:
                                    oldtime,old=last;dt=(t-oldtime).total_seconds()
                                    if dt<=0:nonincreasing+=1
                                    elif dt>60:gaps+=1
                                    else:
                                        oq=old['flow_gpm'];b=old['bit_depth_ft'];h=old['hole_depth_ft'];flag=old['on_bottom_flag']
                                        if oq is not None and oq<=OFF_FLOW_GPM:
                                            phase_seconds['pumps_off']+=dt
                                            if b is not None and vals['bit_depth_ft'] is not None and (vals['bit_depth_ft']-b)/dt>.01:
                                                phase_seconds['running_in_pumps_off']+=dt
                                        elif (oq is not None and oq>DRILL_FLOW_GPM and b is not None and h is not None
                                              and abs(b-h)<=5 and flag is not None and flag>.5 and old['rop_ft_h'] is not None and old['rop_ft_h']>1):phase_seconds['drilling']+=dt
                                        else:phase_seconds['unclassified']+=dt
                                last=t,vals
                        columns=reader.fieldnames
                        for tbin,bucket in sorted(bins.items()):
                            x=dict(time=tbin.isoformat(sep=' '),raw_count=bucket['total'],invalid_flow_count=bucket['bad_flow'])
                            for key,values in bucket['values'].items():
                                x[key]=statistics.fmean(values) if values else '';x[key+'_count']=len(values)
                            for key in ['bit_box_C','top_sub_C','lower_mandrel_C']:
                                values=bucket['values'][key];x[key+'_max']=max(values) if values else ''
                            x['drilling_count']=bucket['drilling_count']
                            for key,values in bucket['drilling_temperature'].items():
                                x['drilling_'+key]=statistics.fmean(values) if values else ''
                                x['drilling_'+key+'_count']=len(values)
                            flow=bucket['values']['flow_gpm'];x['minimum_flow_gpm']=min(flow) if flow else '';x['maximum_flow_gpm']=max(flow) if flow else ''
                            rows.append(x)
                        output(out/f'sanvean_BHA{run}_10s.csv',rows)
                        summaries.append(dict(run=run,start=first.isoformat(sep=' '),end=last[0].isoformat(sep=' '),raw_rows=raw_rows,bins_10s=len(rows),
                                              bit_box_count=counts.get('bit_box_C',0),top_sub_count=counts.get('top_sub_C',0),lower_mandrel_count=counts.get('lower_mandrel_C',0),
                                              bit_depth_min_ft=mins.get('bit_depth_ft'),bit_depth_max_ft=maxs.get('bit_depth_ft'),hole_depth_max_ft=maxs.get('hole_depth_ft'),
                                              valid_flow_min_gpm=mins.get('flow_gpm'),valid_flow_max_gpm=maxs.get('flow_gpm'),
                                              invalid_flow_rows=invalid_flow,flow_above_2000_rows=high_flow,flow_above_100000_rows=very_high_flow,raw_maximum_flow_gpm=raw_max_flow,
                                              nonincreasing_timestamps=nonincreasing,gaps_above_60s=gaps,
                                              **{k+'_h':v/3600 for k,v in phase_seconds.items()}))
                        metadata.append(dict(run=run,archive=package,csv=name,columns=columns,
                                             minimum_values=mins,maximum_values=maxs,valid_counts=counts))
                        print(f'BHA {run}: {raw_rows} rows -> {len(rows)} bins',flush=True)
    output(out/'run_inventory.csv',summaries)
    (out/'sanvean_sources.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    return summaries
def rig(raw,out,mud):
    rows=[];bins={};source_count=0
    columns={'mud_temperature_F':'MUD TEMP','flow_gpm':'Flow In','return_flow_percent':'Return Flow',
             'hole_depth_ft':'Total Depth','block_position_ft':'Block Position','on_bottom_flag':'On Bottom','rop_ft_h':'ROP Depth/Hour','motor_differential_psi':'Differential Pressure'}
    with zipfile.ZipFile(raw/'1283.zip') as z:
        with io.TextIOWrapper(z.open('16A(78)-32_time_data_10s_intervals.csv'),encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                if not row.get('Time'):continue
                source_count+=1;t=datetime.strptime(row['Time'],'%m/%d/%y %H:%M')
                bucket=bins.setdefault(t,{**{k:[] for k in columns},'_source_count':0})
                bucket['_source_count']+=1
                for key,col in columns.items():
                    v=number(row.get(col))
                    if v is not None and not (key=='flow_gpm' and not 0<=v<=FLOW_MAX_GPM):bucket[key].append(v)
    xs=[x['md_ft'] for x in mud];tin=[x['temp_in_F'] for x in mud];tout=[x['temp_out_F'] for x in mud];matches=[]
    for t,bucket in sorted(bins.items()):
        row=dict(time=t.isoformat(sep=' '))
        row.update({k:statistics.fmean(bucket[k]) if bucket[k] else '' for k in columns})
        q=bucket['flow_gpm']
        row['source_count']=bucket['_source_count'];row['flow_valid_count']=len(q)
        row['circulating_fraction']=sum(v>OFF_FLOW_GPM for v in q)/len(q) if q else ''
        rows.append(row)
        h=row['hole_depth_ft'];temp=row['mud_temperature_F'];q=row['flow_gpm'];rop=row['rop_ft_h'];flag=row['on_bottom_flag']
        if all(x!='' for x in [h,temp,q,rop,flag]) and q>DRILL_FLOW_GPM and rop>1 and flag>.5 and temp>32:
            ti=interpolate(h,xs,tin);to=interpolate(h,xs,tout)
            if ti is not None and to is not None and ti>32 and to>32:
                matches.append(dict(time=row['time'],md_ft=h,rig_mud_F=temp,mudlog_in_F=ti,mudlog_out_F=to))
    output(out/'rig_history_1min.csv',rows);output(out/'rig_mud_channel_matches.csv',matches)
    result=dict(source_rows=source_count,minute_bins=len(rows),matched_drilling_minutes=len(matches),source_timestamp_resolution='minute; repeated entries per minute retained as means')
    for field in ['mudlog_in_F','mudlog_out_F']:
        err=[x['rig_mud_F']-x[field] for x in matches]
        result[field]=dict(mean_difference_F=statistics.fmean(err),MAE_F=statistics.fmean(abs(x) for x in err),RMSE_F=math.sqrt(statistics.fmean(x*x for x in err)))
    return result
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--raw',required=True,type=Path);parser.add_argument('--output',type=Path,default=HERE)
    parser.add_argument('--skip-sanvean',action='store_true');parser.add_argument('--reports',action='store_true',help='Also transcribe daily-report tables; requires pdfplumber')
    args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True);start=time.perf_counter()
    s=survey(args.raw,out);f=formation(args.raw,out,s);m=mudlog(args.raw,out)
    runs=sanvean(args.raw,out) if not args.skip_sanvean else list(csv.DictReader((out/'run_inventory.csv').open(encoding='utf-8')))
    rig_info=rig(args.raw,out,m)
    if args.reports:
        from build_report_tables import build
        build(args.raw,out)
    from audit_extracts import audit
    audit(out)
    result=dict(survey_stations=len(s),survey_last=s[-1],formation=f,mud_log_rows=len(m),runs=len(runs),rig=rig_info,elapsed_s=time.perf_counter()-start,
                flow_valid_range_gpm=[0,FLOW_MAX_GPM],drilling_flow_threshold_gpm=DRILL_FLOW_GPM,pumps_off_threshold_gpm=OFF_FLOW_GPM,
                method='Source extraction only; no thermal predictions or comparison errors computed.')
    (out/'extract-summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
