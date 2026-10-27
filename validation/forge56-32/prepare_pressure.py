"""Prepare 56-32 candidate pressure windows from inputs only.

No model or measured target is read. Unresolved source/motor inputs remain
explicit flags; this candidate list does not certify complete primary cases.
"""
import argparse
import bisect
import csv
import gzip
import json
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

HERE=Path(__file__).resolve().parent


def num(s):
    try:
        x=float(s)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):
        return None


def read(root,name):
    with (gzip.open(root/name,'rt',encoding='utf-8',newline='') if name.endswith('.gz') else (root/name).open(encoding='utf-8',newline='')) as f:
        return list(csv.DictReader(f))


def write(root,name,rows,fields=None):
    fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    with (root/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(rows)


def section(depth):
    return 'surface_17.5' if depth<=382 else ('intermediate_12.25' if depth<=3506 else 'production_8.75')


def main(root):
    history=read(root,'rig_inputs_10s.csv.gz')
    times=[datetime.fromisoformat(r['time']) for r in history]
    bits=read(root,'bit_records.csv');bhas=read(root,'bha_runs.csv');mud=read(root,'mud_reports.csv')
    crosswalk=[]
    for bha in bhas:
        lo=num(bha['depth_in_ft']);hi=num(bha['depth_out_ft'])
        if hi is None:hi=num(bha.get('depth_out_derived_candidate_ft'))
        matches=[b for b in bits if lo is not None and hi is not None and abs(num(b['depth_in_ft'])-lo)<=10 and abs(num(b['depth_out_ft'])-hi)<=2]
        crosswalk.append(dict(bha_sheet_id=bha['bha_sheet_id'],bit_run_sequence=matches[0]['run_sequence'] if len(matches)==1 else '',
                              depth_in_ft=lo,depth_out_ft=hi,date_in=bha['date_in'],date_out=bha['date_out'],
                              match_status='start_within_10ft_end_within_2ft' if len(matches)==1 else 'unresolved',
                              depth_out_basis=bha['depth_out_status'],source_member=bha['source_member']))
    write(root,'bha_crosswalk.csv',crosswalk)
    for row in mud:
        stamp=(row['sample_date']+' '+row['sample_time']) if row['sample_date'] and row['sample_time'] else None
        row['_time']=datetime.fromisoformat(stamp) if stamp else None
    def candidates(a,b):
        lo=bisect.bisect_left(times,a);hi=bisect.bisect_left(times,b)
        return history[lo:hi],times[lo:hi]
    counts=Counter();out=[]
    stop=datetime(2021,2,28)
    cadence=timedelta(minutes=10)
    end=times[0].replace(minute=times[0].minute//10*10,second=0)+cadence
    while end<min(times[-1],stop):
        rows,tt=candidates(end-timedelta(minutes=10),end)
        counts['grid_windows']+=1
        core=[r for r in rows if all(num(r[k]) is not None for k in ('flow_gpm','bit_depth_ft','hole_depth_ft'))]
        if len(core)<54 or any((b-a).total_seconds()>60 for a,b in zip(tt,tt[1:])):
            counts['insufficient_input_coverage']+=1;end+=cadence;continue
        q=sorted(num(r['flow_gpm']) for r in core)
        median=q[len(q)//2]
        if median<=100 or (q[int(.9*(len(q)-1))]-q[int(.1*(len(q)-1))])/median>.10:
            counts['non_circulating_or_unsteady_flow']+=1;end+=cadence;continue
        earlier,et=candidates(end-timedelta(minutes=10),end)
        if len(earlier)<54 or any(num(r['flow_gpm_min']) is None or num(r['flow_gpm_min'])<=100 for r in earlier) or any((b-a).total_seconds()>60 for a,b in zip(et,et[1:])):
            counts['insufficient_continuous_circulation']+=1;end+=cadence;continue
        off=sum(num(r['hole_depth_ft_min'])-num(r['bit_depth_ft_max'])>=50 for r in core)
        on=sum(abs(num(r['hole_depth_ft'])-num(r['bit_depth_ft']))<=5 and num(r['flow_gpm'])>300 and (num(r['rop_ft_h']) or 0)>1 for r in core)
        bmin=min(num(r['bit_depth_ft_min']) for r in core);bmax=max(num(r['bit_depth_ft_max']) for r in core)
        primary=off/len(core)>=.9 and bmax-bmin<=5 and bmin>=100
        secondary=on/len(core)>=.9
        if not primary and not secondary:
            counts['not_off_bottom_stationary_or_on_bottom_drilling']+=1;end+=cadence;continue
        role='primary_off_bottom' if primary else 'secondary_on_bottom'
        depth=math.fsum(num(r['hole_depth_ft']) for r in core)/len(core)
        bit_depth=math.fsum(num(r['bit_depth_ft']) for r in core)/len(core)
        time=end-timedelta(minutes=5);day=time.date().isoformat();flags=[]
        matching=[]
        for item in crosswalk:
            if item['depth_in_ft'] is None or item['depth_out_ft'] is None or not item['date_in']:continue
            # Calendar-day source boundaries are inclusive and unresolved overlaps stay visible.
            if day<item['date_in'] or (item['date_out'] and day>item['date_out']):continue
            if item['depth_in_ft']-2<=depth<=item['depth_out_ft']+2:matching.append(item)
        owner=matching[0] if len(matching)==1 else None
        if owner is None:flags.append('BHA_assignment_unresolved')
        sec=section(depth)
        mu=[r for r in mud if r['_time'] and r['_time']<stop and num(r['sample_depth_ft']) is not None and section(num(r['sample_depth_ft']))==sec and num(r['mud_weight_ppg']) is not None]
        chosen=min(mu,key=lambda r:(abs((r['_time']-time).total_seconds()),r['_time'])) if mu else None
        if chosen is None:flags.append('mud_density_missing')
        pv=[r for r in mu if num(r['plastic_viscosity_cP']) is not None and num(r['yield_point_lbf_100ft2']) is not None]
        rheology=min(pv,key=lambda r:(abs((r['_time']-time).total_seconds()),r['_time'])) if pv else None
        if rheology is None:flags.append('water_rheology_at_recorded_density')
        flags.append('rheology_continuity_assumed_within_hole_section')
        flags.append('Pason_inlet_Degrees_treated_as_F_from_report_convention')
        inlet=[num(r['inlet_temperature_source_degrees']) for r in core if num(r['inlet_temperature_source_degrees']) is not None]
        if len(inlet)<54:flags.append('inlet_coverage_incomplete')
        flags.append('motor_no_load_reference_and_match_unresolved')
        row=dict(window_id='56-'+time.strftime('%Y%m%dT%H%M%S')+'-'+role,
                 role=role,time=time.isoformat(sep=' '),window_start=(end-timedelta(minutes=10)).isoformat(sep=' '),window_end=end.isoformat(sep=' '),
                 input_bins=len(core),flow_gpm=math.fsum(q)/len(q),bit_depth_ft=bit_depth,hole_depth_ft=depth,
                 bit_range_ft=bmax-bmin,inlet_F=math.fsum(inlet)/len(inlet) if inlet else '',
                 bha_sheet_id=owner['bha_sheet_id'] if owner else '',bit_run_sequence=owner['bit_run_sequence'] if owner else '',
                 hole_section=sec,mud_weight_ppg=chosen['mud_weight_ppg'] if chosen else '',
                 mud_source=chosen['source_member'] if chosen else '',mud_sample_time=chosen['_time'].isoformat(sep=' ') if chosen else '',
                 PV_cP=rheology['plastic_viscosity_cP'] if rheology else '',YP_lbf_100ft2=rheology['yield_point_lbf_100ft2'] if rheology else '',
                 rheology_source=rheology['source_member'] if rheology else '',rheology_sample_time=rheology['_time'].isoformat(sep=' ') if rheology else '',
                 pv_ref_T_primary_C=48.9 if rheology else '',pv_ref_T_sensitivity_C=26.7 if rheology else '',
                 readiness='pending_V0_source_rulings',flags=';'.join(flags))
        out.append(row);counts[role]+=1;counts['unique_BHA_assigned']+=int(owner is not None)
        end+=cadence
    write(root,'candidate_windows.csv',out)
    (root/'window-preparation.json').write_text(json.dumps(dict(counts=counts,model_runs=0,target_files_read=0,
        status='input-only candidates; not certified complete primary cases'),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(counts,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,default=HERE);main(p.parse_args().data)
