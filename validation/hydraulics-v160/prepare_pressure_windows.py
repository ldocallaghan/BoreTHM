"""Apply preregistered short-window rules using only flow/depth inputs.

No BoreTHM imports and no targets. Preserve the original 56-32 ten-minute
list. Outputs distinguish events, windows, assignment and motor exclusions.
"""
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def read(root,name):
    with (root/name).open(encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))


def num(s):
    try:
        x=float(s)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):
        return None


def write(root,name,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with (root/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fields,lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def assign56(root):
    cross=read(root,'bha_crosswalk.csv')
    def owner(time,depth):
        day=time.date().isoformat()
        match=[r['bha_sheet_id'] for r in cross if r['date_in'] and r['date_in']<=day
               and (not r['date_out'] or day<=r['date_out']) and num(r['depth_in_ft']) is not None
               and num(r['depth_out_ft']) is not None and num(r['depth_in_ft'])-2<=depth<=num(r['depth_out_ft'])+2]
        return match[0] if len(match)==1 else ''
    motors={r['bha_sheet_id']:r for r in read(root,'motor_mapping.csv')}
    return owner,motors


def assign58(root):
    reports=read(root,'bha_reports.csv')
    days=defaultdict(set)
    for r in reports:
        days[r['report_date']].add(r['bha_id'])
    def owner(time,depth):
        matches=days[time.date().isoformat()]
        prior=days[(time.date()-timedelta(days=1)).isoformat()]
        following=days[(time.date()+timedelta(days=1)).isoformat()]
        # End-state DDRs cannot locate an assembly change within a source day.
        # Only assign an interior day with the same single BHA on either side.
        return next(iter(matches)) if len(matches)==1 and matches==prior==following else ''
    motors={}
    for r in reports:
        item=motors.setdefault(r['bha_id'],dict(bha_sheet_id=r['bha_id'],motor_interval_status='motorless_reported_BHA',
                    recorded_maker='',sheet_id='',rated_min_gpm='',rated_max_gpm='',no_load_psi='',input_evidence=''))
        if r['motor']=='documented':
            item['motor_interval_status']='excluded_unknown_maker'
        elif ('BIT' not in r['components'].split(';') or len(r['components'].split(';'))<4) and item['motor_interval_status']=='motorless_reported_BHA':
            item['motor_interval_status']='excluded_motor_status_unresolved'
        item['input_evidence']+=r['source_member']+' page'+r['page']+';'
    write(root,'motor_mapping.csv',list(motors.values()))
    return owner,motors


def exclusion(bha, motor, qmin, qmax):
    if not bha:
        return 'excluded_BHA_unresolved'
    if motor is None:
        return 'excluded_motor_status_unresolved'
    state=motor['motor_interval_status']
    if state=='motorless_reported_BHA':
        return 'motorless_primary'
    if state!='eligible_with_flag':
        return state
    if qmin<num(motor['rated_min_gpm']) or qmax>num(motor['rated_max_gpm']):
        return 'excluded_outside_motor_rated_flow'
    return 'motor_interval'


def main(root,well):
    owner,motors=assign56(root) if well=='56-32' else assign58(root)
    rows=read(root,'rig_inputs_10s.csv')
    stop=datetime(2021,2,28) if well=='56-32' else datetime(2017,9,14)
    events=[]
    current=None
    last_t=None
    epoch=[]
    epoch_q=None
    previous=None
    candidates=[]
    event_index=0
    # An event is uninterrupted off-bottom occupancy, including pump stops and
    # bit movement. Stationarity is a window cut, not a way to multiply events.
    for r in rows:
        t=datetime.fromisoformat(r['time'])
        if t>=stop:
            break
        bmin,bmax,hmin,q,qmin,qmax=[num(r.get(k)) for k in ('bit_depth_ft_min','bit_depth_ft_max','hole_depth_ft_min','flow_gpm','flow_gpm_min','flow_gpm_max')]
        good=all(x is not None for x in (bmin,bmax,hmin)) and bmin>=100 and hmin-bmax>=10
        if good and current is not None:
            good=last_t is not None and (t-last_t).total_seconds()<=60
            if not good:
                current=None
                good=all(x is not None for x in (bmin,bmax,hmin)) and bmin>=100 and hmin-bmax>=10
        if not good:
            current=None
        elif current is None:
            event_index+=1
            current=dict(event_id=well+'-off'+str(event_index).zfill(4),start=t,end=t,bmin=bmin,bmax=bmax)
            events.append(current)
        if current is not None:
            current.update(end=t,bmin=min(current['bmin'],bmin),bmax=max(current['bmax'],bmax))
        r['_event']=current['event_id'] if current else ''
        r['_time']=t
        # A new flow epoch starts at pumps-on, a missing bin, or a >5% departure
        # from its first stable flow. Settling is 60 s, then non-overlapping 60 s windows.
        covered=all((num(r.get(k+'_count')) or 0)>=8 for k in ('flow_gpm','bit_depth_ft','hole_depth_ft'))
        stable=covered and q is not None and q>100 and qmin is not None and qmin>100 and qmax is not None and qmax-qmin<=.1*q
        same=stable and previous is not None and (t-previous).total_seconds()==10 and epoch_q is not None and abs(q/epoch_q-1)<=.05
        if not same:
            epoch=[]
            epoch_q=q if stable else None
        if stable:
            epoch.append(r)
            if len(epoch)>=12 and (len(epoch)-12)%6==0:
                window=epoch[-6:]
                ev={x['_event'] for x in window}
                bv=[num(x['bit_depth_ft_min']) for x in window]
                bx=[num(x['bit_depth_ft_max']) for x in window]
                flows=sorted(num(x['flow_gpm']) for x in window)
                med=(flows[2]+flows[3])/2
                if len(ev)==1 and '' not in ev and max(bx)-min(bv)<=2 and (flows[-1]-flows[0])/med<=.05:
                    time=window[0]['_time']+timedelta(seconds=30)
                    depth=math.fsum(num(x['hole_depth_ft']) for x in window)/6
                    bha=owner(time,depth)
                    qlo=min(num(x['flow_gpm_min']) for x in window)
                    qhi=max(num(x['flow_gpm_max']) for x in window)
                    candidates.append(dict(window_id=well+'-'+time.strftime('%Y%m%dT%H%M%S'),event_id=next(iter(ev)),time=time.isoformat(sep=' '),
                        window_start=window[0]['_time'].isoformat(sep=' '),window_end=(window[-1]['_time']+timedelta(seconds=10)).isoformat(sep=' '),
                        bha_id=bha,flow_gpm=math.fsum(flows)/6,flow_min_gpm=qlo,flow_max_gpm=qhi,
                        bit_depth_ft=math.fsum(num(x['bit_depth_ft']) for x in window)/6,hole_depth_ft=depth,
                        selection=exclusion(bha,motors.get(bha),qlo,qhi),rule='short_60s_settle_60s_window',targets_read=False))
        previous=t if stable else None
        last_t=t
    # Old windows are retained verbatim as candidates, with the same source
    # motor exclusions applied. Events use midpoint membership in occupancy.
    old=[]
    if well=='56-32':
        for r in read(root,'candidate_windows.csv'):
            if r['role']!='primary_off_bottom':
                continue
            t=datetime.fromisoformat(r['time'])
            ev=[e for e in events if e['start']<=t<=e['end']+timedelta(seconds=10)]
            bha=r['bha_sheet_id']
            q=num(r['flow_gpm'])
            raw_window=[x for x in rows if '_time' in x and t-timedelta(minutes=5)<=x['_time']<t+timedelta(minutes=5)]
            minima=[num(x['flow_gpm_min']) for x in raw_window if num(x.get('flow_gpm_min')) is not None]
            maxima=[num(x['flow_gpm_max']) for x in raw_window if num(x.get('flow_gpm_max')) is not None]
            qlo,qhi=(min(minima),max(maxima)) if minima and maxima else (q,q)
            old.append(dict(window_id=r['window_id'],time=r['time'],event_id=ev[0]['event_id'] if len(ev)==1 else 'legacy-'+r['window_id'],
                bha_id=bha,flow_gpm=q,flow_min_gpm=qlo,flow_max_gpm=qhi,selection=exclusion(bha,motors.get(bha),qlo,qhi),rule='old_10minute'))
    if well=='58-32':
        buckets=defaultdict(list)
        for r in rows:
            if '_time' in r:
                t=r['_time']
                buckets[t.replace(minute=t.minute//10*10,second=0)].append(r)
        for start,ws in sorted(buckets.items()):
            core=[r for r in ws if all(num(r[k]) is not None for k in ('flow_gpm','bit_depth_ft','hole_depth_ft'))]
            if len(core)<54:
                continue
            if any((b['_time']-a['_time']).total_seconds()>60 for a,b in zip(ws,ws[1:])):
                continue
            q=sorted(num(r['flow_gpm']) for r in core)
            median=q[len(q)//2]
            if median<=100 or (q[int(.9*(len(q)-1))]-q[int(.1*(len(q)-1))])/median>.10:
                continue
            if any(num(r['flow_gpm_min']) is None or num(r['flow_gpm_min'])<=100 for r in ws):
                continue
            off=sum(num(r['hole_depth_ft_min'])-num(r['bit_depth_ft_max'])>=50 for r in core)
            if off/len(core)<.9 or max(num(r['bit_depth_ft_max']) for r in core)-min(num(r['bit_depth_ft_min']) for r in core)>5 or min(num(r['bit_depth_ft_min']) for r in core)<100:
                continue
            t=start+timedelta(minutes=5)
            bha=owner(t,math.fsum(num(r['hole_depth_ft']) for r in core)/len(core))
            event=next((r['_event'] for r in core if r['_time']>=t and r['_event']), '')
            q=math.fsum(q)/len(q)
            qlo=min(num(r['flow_gpm_min']) for r in ws)
            qhi=max(num(r['flow_gpm_max']) for r in ws)
            old.append(dict(window_id=well+'-'+t.strftime('%Y%m%dT%H%M%S'),time=t.isoformat(sep=' '),event_id=event or 'legacy-'+t.isoformat(),
                bha_id=bha,flow_gpm=q,flow_min_gpm=qlo,flow_max_gpm=qhi,selection=exclusion(bha,motors.get(bha),qlo,qhi),rule='old_10minute'))
    event_bhas=defaultdict(set)
    for r in candidates:
        if r['bha_id']:
            event_bhas[r['event_id']].add(r['bha_id'])
    for data in (old,candidates):
        for r in data:
            motor=motors.get(r['bha_id'])
            low=num(motor.get('rated_min_gpm')) if motor else None
            high=num(motor.get('rated_max_gpm')) if motor else None
            r['outside_rated_flow']=bool(low is not None and high is not None and (r['flow_min_gpm']<low or r['flow_max_gpm']>high))
            if len(event_bhas[r['event_id']])>1:
                r['selection']='excluded_event_BHA_conflict'
    by=defaultdict(lambda:dict(windows=0,events=set(),outside_rated=0))
    for label,data in [('old',old),('new',candidates)]:
        for r in data:
            key=(label,r['bha_id'] or 'unresolved',r['selection'])
            by[key]['windows']+=1
            by[key]['events'].add(r['event_id'])
            by[key]['outside_rated']+=int(r['outside_rated_flow'])
    counts=[dict(rule=k[0],bha_id=k[1],selection=k[2],windows=v['windows'],events=len(v['events']),outside_rated_windows=v['outside_rated']) for k,v in sorted(by.items())]
    write(root,'off_bottom_windows.csv',candidates)
    if old:
        write(root,'old_off_bottom_qualification.csv',old)
    write(root,'off_bottom_counts.csv',counts)
    selected_events=defaultdict(list)
    for r in candidates:
        selected_events[r['event_id']].append(r)
    report=[]
    for eid,ws in selected_events.items():
        bhas={r['bha_id'] for r in ws}
        report.append(dict(event_id=eid,start=ws[0]['window_start'],end=ws[-1]['window_end'],windows=len(ws),
                           bha_id=next(iter(bhas)) if len(bhas)==1 else 'mixed_unresolved',
                           eligible_motor_windows=sum(r['selection']=='motor_interval' for r in ws),
                           motorless_primary_windows=sum(r['selection']=='motorless_primary' for r in ws)))
    write(root,'off_bottom_events.csv',report)
    summary=dict(well=well,old_windows=len(old),new_windows=len(candidates),new_events=len(report),
                 new_selection_counts=dict(Counter(r['selection'] for r in candidates)),targets_read=False)
    (root/'off_bottom_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',required=True,type=Path)
    parser.add_argument('--well',required=True,choices=('56-32','58-32'))
    args=parser.parse_args()
    main(args.data,args.well)
