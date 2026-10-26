"""Inventory observed pumps-off spells before transient model comparison."""
import json
import statistics as st
from pathlib import Path
import numpy as np
from borethm.studies import validate_forge16a as v

def write_inventory(output):
    ROOT=Path(output)
    ROOT.mkdir(parents=True,exist_ok=True)
    all_spells=[]

    for run in v.RUNS:
        rr=v.read(f'sanvean_BHA{run}_10s.csv')
        for r in rr:r['epoch']=v.epoch(r['time'])
        spells=[];start=None
        for i in range(len(rr)+1):
            r=rr[i] if i<len(rr) else {}
            off=(i<len(rr) and v.number(r.get('flow_gpm_count'))==v.number(r.get('raw_count'))
                 and v.number(r.get('raw_count'),0)>0 and 0<=v.number(r.get('minimum_flow_gpm'))
                 and v.number(r.get('maximum_flow_gpm'))<=100)
            contiguous=i==0 or i==len(rr) or rr[i]['epoch']-rr[i-1]['epoch']<=20
            if start is not None and (not off or not contiguous):
                rows=rr[start:i]
                duration=rows[-1]['epoch']+10-rows[0]['epoch']
                if duration>=60:
                    vals=[r for r in rows if np.isfinite(v.number(r['bit_depth_ft'])) and np.isfinite(v.number(r['hole_depth_ft']))]
                    sensed=[r for r in rows if v.number(r['bit_box_C_count'],0)>0]
                    if vals:
                        depths=[v.number(r['bit_depth_ft']) for r in vals]
                        delta=depths[-1]-depths[0]
                        near=sum(abs(v.number(r['bit_depth_ft'])-v.number(r['hole_depth_ft']))<=100 for r in vals)/len(vals)
                        dr=[b-a for a,b in zip(depths,depths[1:])]
                        positive=sum(max(x,0) for x in dr);negative=-sum(min(x,0) for x in dr)
                        row=dict(run=run,spell_id=f'{run}-off{len(spells)+1:03d}',start=rows[0]['time'],end_last_bin=rows[-1]['time'],
                            start_i=start,end_i=i-1,duration_s=duration,depth_start_ft=depths[0],depth_end_ft=depths[-1],
                            depth_min_ft=min(depths),depth_max_ft=max(depths),hole_ft=st.median(v.number(r['hole_depth_ft']) for r in vals),
                            net_down_ft=delta,upward_motion_ft=negative,downward_motion_ft=positive,
                            near_bottom_fraction=near,temperature_bins=len(sensed),total_bins=len(rows),
                            temperature_coverage_fraction=len(sensed)/len(rows),
                            before_flow_gpm=v.number(rr[start-1]['flow_gpm'],0) if start else 0,
                            first_temperature_time=sensed[0]['time'] if sensed else '',
                            last_temperature_time=sensed[-1]['time'] if sensed else '',
                            first_temperature_depth_ft=v.number(sensed[0]['bit_depth_ft'],0) if sensed else 0,
                            first_temperature_C=v.number(sensed[0]['bit_box_C'],0) if sensed else 0,
                            last_temperature_C=v.number(sensed[-1]['bit_box_C'],0) if sensed else 0)
                        spells.append(row)
                start=None
            if off and start is None:start=i
        all_spells.extend(spells)
        first=next((r for r in rr if v.number(r['bit_box_C_count'],0)>0),None)
        pauses=[s for s in spells if s['near_bottom_fraction']>=.9 and s['depth_max_ft']-s['depth_min_ft']<=100 and s['temperature_coverage_fraction']>=.8]
        trips=[s for s in spells if s['net_down_ft']>=500 and s['upward_motion_ft']<=.1*s['downward_motion_ft']]
        print(run,'first bit/temp depth',rr[0]['bit_depth_ft'],first['bit_depth_ft'] if first else None,
              'off spells',len(spells),'pauses',len(pauses),'RIH spells',[(s['spell_id'],round(s['duration_s']/60,1),round(s['depth_start_ft']),round(s['depth_end_ft']),round(s['temperature_coverage_fraction'],2)) for s in trips])
    v.csv_out(ROOT/'observed-off-spells.csv',all_spells)
