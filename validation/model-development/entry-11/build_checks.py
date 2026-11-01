"""Declared pressure-channel checks and density-equivalent bounds.

Requires pandas for the source reader. Pressure values do not select an
interval. No BoreTHM import, new hydraulic solve or skill score is made.
"""
import argparse
from collections import defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import statistics as st

import numpy as np
import pandas as pd

from build_flow import chunks58, packed, write
from diagnostic_rules import epoch_seconds, retained_off_indices, spells

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def source_range(d):
    return dict(first_time=str(d.time.iloc[0]),last_time=str(d.time.iloc[-1]),
        source_members=';'.join(dict.fromkeys(d.source_member)),
        source_row_ranges=json.dumps([dict(member=name,first_row=int(g.source_row.min()),
            last_row=int(g.source_row.max()),selected_rows=len(g)) for name,g in d.groupby('source_member',sort=False)]),
        first_source_row=int(d.source_row.iloc[0]),last_source_row=int(d.source_row.iloc[-1]))


def med(s):
    s=s[np.isfinite(s)]
    return float(s.median()) if len(s) else None


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raw58',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    intervals=pd.read_csv(HERE/'sources/tables/drilling-parameter-intervals.csv',keep_default_na=False).to_dict('records')
    for i,r in enumerate(intervals):
        r['interval_id']='report-'+str(r['report_no'])+'-'+str(i+1)
        r['day']=datetime.strptime(r['report_date'],'%d-%b-%y').strftime('%Y-%m-%d') if r['report_date'] else ''
    observations=defaultdict(list);bounded=[];sources=[];header=True
    with packed(a.output/'A2-native-comparisons.csv.gz') as native:
        for d in chunks58(a.raw58,sources):
            if d.time.notna().sum()==0:continue
            days=d.time.dt.strftime('%Y-%m-%d')
            recent=d[(d.time>='2017-08-02')&(d.time<'2017-08-07')]
            if len(recent):bounded.append(recent[['time','source_member','source_row','spp','flow','p1','p2']].copy())
            for r in intervals:
                if not r['day'] or r['day'] not in set(days.dropna()):continue
                mask=(days==r['day'])&d.bit.between(float(r['depth_start_ft']),float(r['depth_end_ft']))
                mask &= (d.bit-d.hole).abs().le(5)&d.rop.gt(1)&d.p1.ge(0)&d.p2.ge(0)&(d.p1+d.p2).gt(0)
                group=d.loc[mask,['time','source_member','source_row','spp','flow','p1','p2','bit','hole','rop']].copy()
                if group.empty:continue
                observations[r['interval_id']].append(group)
                group.insert(0,'interval_id',r['interval_id'])
                group.to_csv(native,index=False,header=header,lineterminator='\n');header=False
    comparisons=[]
    for r in intervals:
        row=dict(r,native_rows=0,pressure_rows=0,median_pressure_psi=None,median_flow_gpm=None,median_bit_depth_ft=None,
                 difference_from_report_psi=None,status='no eligible native observations')
        groups=observations[r['interval_id']]
        if groups:
            d=pd.concat(groups,ignore_index=True)
            pressure=med(d.spp)
            row.update(native_rows=len(d),pressure_rows=int(np.isfinite(d.spp).sum()),
                median_pressure_psi=pressure,median_flow_gpm=med(d.flow),median_bit_depth_ft=med(d.bit),
                difference_from_report_psi=pressure-float(r['reported_pressure_psi']) if pressure is not None else None,
                status='available' if pressure is not None else 'no finite pressure',**source_range(d))
        comparisons.append(row)
    write(a.output/'A2-report-comparison.csv',comparisons)
    d=pd.concat(bounded,ignore_index=True).sort_values(['time','source_member','source_row']).reset_index(drop=True)
    seconds=np.asarray(epoch_seconds(d.time))
    off=list(retained_off_indices(seconds,d.p1.to_numpy(),d.p2.to_numpy()))
    scope=[]
    for day in ('2017-08-03','2017-08-04','2017-08-05','2017-08-06'):
        scope.append((day,pd.Timestamp(day),pd.Timestamp(day)+pd.Timedelta(days=1)))
    windows=pd.read_csv(ROOT/'validation/forge58-32/pressure-test/inputs/windows.csv')
    for event,g in windows.groupby('event_id',sort=False):
        scope.append((event,pd.to_datetime(g.window_start).min()-pd.Timedelta(hours=2),pd.to_datetime(g.window_end).max()+pd.Timedelta(hours=2)))
    off_rows=[];summaries=[]
    for name,start,end in scope:
        pooled=[];spells_count=0
        for n,indices in enumerate(off,1):
            chosen=[i for i in indices if start<=d.time.iloc[i]<end]
            if not chosen:continue
            g=d.iloc[chosen]
            duration=(g.time.iloc[-1]-g.time.iloc[0]).total_seconds()+1
            if duration<60:continue
            pooled.append(g);spells_count+=1
            off_rows.append(dict(scope=name,period=n,duration_s=duration,native_rows=len(g),
                pressure_rows=int(np.isfinite(g.spp).sum()),median_pressure_psi=med(g.spp),**source_range(g)))
        g=pd.concat(pooled,ignore_index=True) if pooled else None
        summaries.append(dict(scope=name,periods=spells_count,native_rows=len(g) if g is not None else 0,
            median_pressure_psi=med(g.spp) if g is not None else None,status='available' if g is not None else 'no qualifying period'))
    write(a.output/'A1-off-periods.csv',off_rows);write(a.output/'A1-offset-summary.csv',summaries)
    selected=(d.time>='2017-08-05')&(d.time<'2017-08-06')&d.p1.between(50,53)&d.p2.eq(0)
    slow=[]
    for n,(begin,end) in enumerate(spells(seconds,selected.to_numpy()),1):
        g=d.iloc[begin:end]
        slow.append(dict(period=n,duration_s=(g.time.iloc[-1]-g.time.iloc[0]).total_seconds()+1,
            native_rows=len(g),median_pressure_psi=med(g.spp),median_flow_gpm=med(g.flow),
            median_pump1_spm=med(g.p1),difference_from_95_psi=med(g.spp)-95 if med(g.spp) is not None else None,
            difference_from_104_psi=med(g.spp)-104 if med(g.spp) is not None else None,**source_range(g)))
    if not slow:slow=[dict(status='no native period with pump1=50-53 and pump2=0 on 5 August')]
    write(a.output/'A3-slow-periods.csv',slow)
    rates=[]
    for rate,g in d.loc[selected].groupby('p1',sort=True):
        rates.append(dict(pump1_spm=float(rate),native_rows=len(g),median_pressure_psi=med(g.spp),median_flow_gpm=med(g.flow),**source_range(g)))
    write(a.output/'A3-slow-by-rate.csv',rates)
    event_rows=pd.read_csv(ROOT/'validation/forge58-32/pressure-test/results/events.csv')
    bounds=[]
    for r in event_rows[(event_rows.scenario=='primary')&(event_rows.cohort=='scenario')].to_dict('records'):
        rho=float(windows[windows.event_id==r['event_id']].density_ppg.median())
        factor=r['target_psi']/r['predicted_psi']
        bounds.append(dict(classification='calculated bound',event_id=r['event_id'],variant=r['variant'],
            target_psi=r['target_psi'],predicted_psi=r['predicted_psi'],scale_factor=factor,
            median_input_density_ppg=rho,density_equivalent_ppg=rho*factor,
            qualification='Uniform pressure scaling at fixed velocities and friction factors; not a new mud input or solve'))
    write(a.output/'E-density-bounds.csv',bounds)
    manifest=dict(method='Declared source-state selections and fixed-pressure-scale density bounds; no model solves',
        sources=sources,code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(a.output.glob('[AE]*'))})
    (a.output/'pressure-check-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
