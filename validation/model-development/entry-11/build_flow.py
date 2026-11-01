"""Native flow/stroke reductions for the declared pressure-input diagnosis.

Requires pandas. The 58-32 pressure projection is limited to 3-6 August.
No thermal channel, model function or scored measure is used.
"""
import argparse
from collections import defaultdict
import csv
from datetime import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import time
import zipfile

import numpy as np
import pandas as pd


def packed(path):
    raw = path.open('wb')
    return io.TextIOWrapper(gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0), encoding='utf-8', newline='')


def write(path, rows):
    rows = list(rows)
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, list(dict.fromkeys(k for r in rows for k in r)), lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def numeric(d, columns):
    for c in columns:
        d[c] = pd.to_numeric(d[c], errors='coerce').replace(-999.25, np.nan)
    return d


def chunks58(path, provenance):
    with zipfile.ZipFile(path) as top, zipfile.ZipFile(io.BytesIO(top.read('Pason_Logs.zip'))) as z:
        def order(name):
            m = re.search(r'(\d+)-(\d+)-(\d+)\.csv$', name)
            return datetime(2000+int(m[3]),int(m[1]),int(m[2])) if m else datetime.min
        for name in sorted((n for n in z.namelist() if n.endswith('.csv') and '__MACOSX' not in n), key=order):
            data = z.read(name); source = path.name+'!Pason_Logs.zip!'+name
            provenance.append(dict(source_member=source, sha256=hashlib.sha256(data).hexdigest()))
            offset = 4
            for d in pd.read_csv(io.BytesIO(data), skiprows=3, header=None, usecols=[0,1,2,4,5,8,11,12,14],
                                 dtype=str, keep_default_na=False, skip_blank_lines=False, chunksize=100000):
                d.columns = ['date','clock','hole','bit','rop','spp','p1','p2','flow']
                d['time'] = pd.to_datetime(d.date+' '+d.clock,format='%m/%d/%Y %H:%M:%S',errors='coerce')
                d['source_row'] = np.arange(offset,offset+len(d)); offset += len(d)
                d['source_member'] = source
                yield numeric(d,['hole','bit','rop','spp','p1','p2','flow'])
            print('58-32', name, offset-4, flush=True)


def chunks16a(path, provenance):
    name = '16A(78)-32_time_data_1s_intervals.csv'
    with zipfile.ZipFile(path) as z:
        with z.open(name) as f: digest = hashlib.file_digest(f,'sha256').hexdigest()
        provenance.append(dict(source_member=path.name+'!'+name,sha256=digest,
            qualification='2020 drilling export has SPM Total only; per-pump comparison unavailable'))
        offset = 2
        with z.open(name) as f:
            for d in pd.read_csv(f,usecols=['Time','Flow In','SPM Total'],dtype=str,keep_default_na=False,chunksize=100000):
                d.columns = ['time','flow','total']
                d['time'] = pd.to_datetime(d.time,format='mixed',errors='coerce')
                d['source_row'] = np.arange(offset,offset+len(d)); offset += len(d)
                d['source_member'] = path.name+'!'+name
                yield numeric(d,['flow','total'])
                print('16A rows',offset-2,flush=True)


def chunks16b(path, provenance):
    with zipfile.ZipFile(path) as top, zipfile.ZipFile(io.BytesIO(top.read('16B_Pason.zip'))) as z:
        name = '10 Second Data.csv'; source = path.name+'!16B_Pason.zip!'+name
        with z.open(name) as f: digest = hashlib.file_digest(f,'sha256').hexdigest()
        provenance.append(dict(source_member=source,sha256=digest,
            qualification='Pump 3 rate retained where recorded; combinations identify every active recorded pump'))
        columns = {'YYYY/MM/DD':'date','HH:MM:SS':'clock','Pump 1 strokes/min (SPM)':'p1',
                   'Pump 2 strokes/min (SPM)':'p2','Pump 3 strokes/min (SPM)':'p3',
                   'Total Pump Output (gal_per_min)':'flow'}
        offset = 2
        with z.open(name) as f:
            for d in pd.read_csv(f,usecols=list(columns),dtype=str,keep_default_na=False,chunksize=100000):
                d=d.rename(columns=columns)
                d['time']=pd.to_datetime(d.date+' '+d.clock,format='%Y/%m/%d %H:%M:%S',errors='coerce')
                d['source_row']=np.arange(offset,offset+len(d));offset+=len(d)
                d['source_member']=source
                yield numeric(d,['flow','p1','p2','p3'])
                print('16B rows',offset-2,flush=True)


def reduce(well, chunks, output):
    values=defaultdict(list); ranges={}; prior=None; rows=invalid=exact_count=step_count=0
    first=None;last=None;projection_header=True
    cols=['time','source_member','source_row','flow','p1','p2','spp','hole','bit','rop']
    changes=['time','source_member','source_row','combination','flow','strokes','ratio','rounded_ratio']
    with packed(output/(well+'-ratio-changes.csv.gz')) as exact, packed(output/(well+'-ratio-steps.csv.gz')) as steps, packed(output/(well+'-pressure-inputs.csv.gz')) as projection:
        exact_header=step_header=True
        for d in chunks:
            rows+=len(d);dt=d.time.dropna()
            if len(dt):
                first=min(first,dt.min()) if first is not None else dt.min()
                last=max(last,dt.max()) if last is not None else dt.max()
            if well=='58-32':
                selected=d[(d.time>='2017-08-03')&(d.time<'2017-08-07')]
                selected[cols].to_csv(projection,index=False,header=projection_header,lineterminator='\n');projection_header=False
            if 'total' in d:
                good=d.total.ge(0)&d.total.gt(0);d['strokes']=d.total;d['combination']='total_only'
            else:
                good=d.p1.ge(0)&d.p2.ge(0)
                d['strokes']=d.p1+d.p2
                d['combination']=np.where(d.p1.gt(0),'1','')+np.where(d.p2.gt(0),'+2','')
                if 'p3' in d:
                    # Missing third-pump telemetry is explicitly retained as
                    # an unknown third-pump state, not a recorded zero.
                    d['strokes']+=d.p3.fillna(0)
                    d['combination']+=np.where(d.p3.gt(0),'+3',np.where(d.p3.isna(),'+3_unknown',''))
                    good &= d.p3.ge(0)|d.p3.isna()
                d['combination']=d.combination.str.strip('+')
                good &= d.strokes.gt(0)
            good &= d.time.notna() & np.isfinite(d.flow) & np.isfinite(d.strokes)
            v=d.loc[good,['time','source_member','source_row','combination','flow','strokes']].copy()
            invalid+=len(d)-len(v)
            if v.empty:continue
            v['ratio']=v.flow/v.strokes;v['rounded_ratio']=v.ratio.round(2);v['day']=v.time.dt.strftime('%Y-%m-%d')
            for key,g in v.groupby(['day','combination'],sort=False):
                values[key].append(g.ratio.to_numpy(copy=True))
                if key not in ranges:ranges[key]=dict(first_time=str(g.time.iloc[0]),first_source_row=int(g.source_row.iloc[0]),last_time='',last_source_row=0,source_member=str(g.source_member.iloc[0]))
                ranges[key].update(last_time=str(g.time.iloc[-1]),last_source_row=int(g.source_row.iloc[-1]))
            joined=pd.concat([prior,v],ignore_index=True) if prior is not None else v.reset_index(drop=True)
            gap=joined.time.diff().dt.total_seconds()
            limit={'58-32':2,'16A':120,'16B':20}[well]
            fresh=(joined.combination.ne(joined.combination.shift())|joined.source_member.ne(joined.source_member.shift())|joined.day.ne(joined.day.shift())|gap.gt(limit)|gap.lt(0)|joined.source_row.diff().ne(1))
            changed=fresh|joined.ratio.ne(joined.ratio.shift())
            stepped=fresh|joined.rounded_ratio.ne(joined.rounded_ratio.shift())
            if prior is not None:changed.iloc[0]=False;stepped.iloc[0]=False
            c=joined.loc[changed,changes];s=joined.loc[stepped,changes]
            c.to_csv(exact,index=False,header=exact_header,lineterminator='\n');exact_header=False;exact_count+=len(c)
            s.to_csv(steps,index=False,header=step_header,lineterminator='\n');step_header=False;step_count+=len(s)
            prior=v.tail(1)
    summaries=[]
    for (day,combo),arr in sorted(values.items()):
        x=np.concatenate(arr)
        summaries.append(dict(well=well,day=day,combination=combo,native_rows=len(x),
            median_gal_stroke=float(np.median(x)),min_gal_stroke=float(x.min()),max_gal_stroke=float(x.max()),
            negative_flow_rows=int((x<0).sum()),**ranges[day,combo]))
    write(output/(well+'-ratios-by-day.csv'),summaries)
    return dict(well=well,native_rows=rows,ineligible_rows=invalid,exact_ratio_change_rows=exact_count,
        rounded_ratio_change_rows=step_count,first_time=str(first),last_time=str(last),daily_combinations=len(summaries))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--well',choices=('58-32','16A','16B'),required=True)
    p.add_argument('--raw',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);started=time.perf_counter();sources=[]
    iterator={'58-32':chunks58,'16A':chunks16a,'16B':chunks16b}[a.well](a.raw,sources)
    result=reduce(a.well,iterator,a.output)
    result.update(runtime_s=time.perf_counter()-started,sources=sources,pandas=pd.__version__,numpy=np.__version__,
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(a.output.glob(a.well+'-*'))})
    (a.output/(a.well+'-flow-manifest.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('sources','output_sha256')},indent=2),flush=True)


if __name__=='__main__':main()
