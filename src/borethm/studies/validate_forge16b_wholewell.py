"""FORGE 16B whole-well comparison using unchanged circulation functions.

Prepare freezes observed samples and period inputs before solving. Run writes
checkpointed predictions to an external directory. The external source archive
and protocol are in validation/forge16b. No parameter is fitted.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import importlib.metadata
import json
import math
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from borethm import fluids, model1_coupled as m1, well_geometry as wg
from borethm.studies import validate_forge16b as trial

FT, INCH, GPM, PSI = trial.FT, trial.INCH, trial.GPM, trial.PSI
PPG, YP_PA = 119.8264273, .4788025898
TRIAL_RUNS = {17:'BHA10',18:'BHA11',19:'BHA12',20:'BHA13'}


def read(path):
    with Path(path).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))


def number(s):
    try:return float(s)
    except (ValueError,TypeError):return float('nan')


def epoch(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def dump(path,obj):
    Path(path).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def csv_out(path,rows):
    rows=list(rows)
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)


def system(t):
    if t<epoch('2023-05-03 21:50:00'):return 'intermediate-hole mud'
    if t<epoch('2023-05-12 15:30:00'):return 'post-cement/particle-drilling fluid'
    return 'post-clean rotary fluid'


def period_mud(data,selected,definitions):
    bounds={n:[float('inf'),-float('inf')] for n in definitions}
    deepest=0.
    with selected.open(newline='',encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            q,h,b,rop=(number(r[k]) for k in ['flow_gpm','hole_depth_ft','bit_depth_ft','rop_ft_h'])
            if math.isfinite(h):deepest=max(deepest,h)
            if not (300<q<=2000 and abs(h-b)<=5 and rop>1):continue
            for n,d in definitions.items():
                if number(d['depth_in_ft'])+5<h<number(d['depth_out_ft'])-5 and deepest<=number(d['depth_out_ft'])+.5:
                    t=epoch(r['time']);bounds[n][0]=min(t,bounds[n][0]);bounds[n][1]=max(t,bounds[n][1]);break
    observations=[]
    for filename in ['mud_samples.csv','mud_supplement_s1.csv']:
        for i,r in enumerate(read(data/filename),1):
            stamp=datetime.strptime(r['sample'][:15],'%d-%b-%y %H:%M').replace(tzinfo=timezone.utc).timestamp()
            observations.append({**r,'time_s':stamp,'fluid_system':system(stamp),'source_id':f'{filename}:{i}'})
    observations.sort(key=lambda r:(r['time_s'],r['source_id']))
    inputs={};ledger=[]
    defaults={'PV_cP':fluids.PV_REF*1000,'YP_lbf_100ft2':fluids.YP_REF/YP_PA}
    for n,(start,end) in bounds.items():
        if not math.isfinite(start):continue
        chosen=[r for r in observations if start<=r['time_s']<=end and r['fluid_system']==system(start)]
        period_fallback=False
        if not chosen:
            earlier=[r for r in observations if r['time_s']<start and r['fluid_system']==system(start)]
            if not earlier:raise ValueError(f'No recorded mud density for EOW {n}')
            chosen=[earlier[-1]];period_fallback=True
        values=[]
        for r in chosen:
            filled={}
            for field in ['density_ppg','PV_cP','YP_lbf_100ft2']:
                value=number(r.get(field));donor=r;method='reported'
                if not math.isfinite(value):
                    earlier=[x for x in observations if x['time_s']<r['time_s'] and
                             x['fluid_system']==r['fluid_system'] and math.isfinite(number(x.get(field)))]
                    if earlier:
                        donor=earlier[-1];value=number(donor[field]);method='nearest earlier within fluid system'
                    elif field in defaults:
                        value=defaults[field];donor=None;method='BoreTHM reference rheology'
                    else:raise ValueError(f'Missing density: {r["source_id"]}')
                filled[field]=value
                ledger.append(dict(eow_bha=n,source_id=r['source_id'],sample=r['sample'],report_page=r['page'],
                    fluid_system=r['fluid_system'],field=field,value=value,method=method,
                    donor_source_id=donor['source_id'] if donor else '',donor_sample=donor['sample'] if donor else '',
                    donor_page=donor['page'] if donor else '',period_sample_carried=period_fallback))
            values.append(filled)
        inputs[n]={k:float(np.mean([r[k] for r in values])) for k in ['density_ppg','PV_cP','YP_lbf_100ft2']}
        inputs[n].update(eow_bha=n,mud_samples=len(values),fluid_system=system(start),
            drilling_start=datetime.fromtimestamp(start,timezone.utc).isoformat(),
            drilling_end=datetime.fromtimestamp(end,timezone.utc).isoformat(),
            source_ids=';'.join(r['source_id'] for r in chosen),period_sample_carried=period_fallback,
            carried_fields=sum(r['method']=='nearest earlier within fluid system' for r in ledger if r['eow_bha']==n),
            reference_fields=sum(r['method']=='BoreTHM reference rheology' for r in ledger if r['eow_bha']==n))
    return inputs,ledger


def steel(name,od,inside):
    return wg.PipeType(name,(wg.Layer(inside*INCH/2,od*INCH/2,wg.K_STEEL),))


def geometry(s,components,k_idp):
    n=s['eow_bha'];bit=s['bit_ft']
    if n in TRIAL_RUNS:return trial.geometry(TRIAL_RUNS[n],bit,k_idp)
    bottom_up=[];compact=[]
    def flush():
        if not compact:return
        length=sum(c['length_ft'] for c in compact)
        od=sum(c['length_ft']*c['od_in'] for c in compact)/length
        inside=sum(c['length_ft']*c['id_in'] for c in compact)/length
        bottom_up.append((length,steel('length-weighted BHA',od,inside)));compact.clear()
    for c in components[str(n)]:
        if c['kind'] in ('assembly','collar'):compact.append(c)
        else:
            flush();bottom_up.append((c['length_ft'],steel(c['component'],c['od_in'],c['id_in'])))
    flush()
    regular=bit-sum(length for length,_ in bottom_up)
    if regular<=0:raise ValueError('Assembly longer than well')
    string=[wg.StringSegment(regular*FT,trial.DRILL_PIPE)]
    string.extend(wg.StringSegment(length*FT,pipe) for length,pipe in reversed(bottom_up))
    if n in (3,4):
        r=lambda d:d*INCH/2
        layers=(wg.Layer(r(15),r(16),wg.K_STEEL),wg.Layer(r(16),r(22),wg.K_CEMENT))
        hole=[wg.HoleInterval(0,1136*FT,r(15),layers),wg.open_hole(1136*FT,bit*FT+1e-6,14.75*INCH)]
    else:hole=trial.hole(bit*FT)
    return wg.WellGeometry(string,hole,trial.SURVEY)


def clock(data):
    rows=read(data/'circulation_history_10min.csv')
    times=np.array([epoch(r['time']) for r in rows])
    circ=np.cumsum([number(r['circulating_count'])*10 for r in rows])
    depths=[];last=0.
    for r in rows:
        d=number(r['max_hole_depth_ft'])
        if math.isfinite(d):last=max(last,d)
        depths.append(last*FT)
    return rows,times,circ,np.array(depths)


def prepare(data,selected,output,trial_check):
    output.mkdir(parents=True,exist_ok=True)
    if (output/'plan.json').exists():raise FileExistsError('Frozen plan exists; choose a new directory')
    check=json.loads(trial_check.read_text())
    if not check['passed']:raise ValueError('Trial reproduction has not passed')
    definitions={int(r['eow_bha']):r for r in read(data/'run_definitions.csv')}
    mud,ledger=period_mud(data,selected,definitions)
    comp={}
    for r in read(data/'component_inputs_s1.csv'):
        c={**r,**{k:number(r[k]) for k in ['length_ft','od_in','id_in']}}
        comp.setdefault(r['eow_bha'],[]).append(c)
    samples=[]
    for r in read(data/'candidate_samples.csv'):
        n=int(r['eow_bha']);definition=definitions[n]
        positions=[22,69,84] if n==3 else [22,84] if n in (4,27,38) else [int(number(r['sensor_offset_ft']))]
        s={**r,'eow_bha':n,'time_s':epoch(r['time']),'bit_ft':number(r['bit_depth_ft']),
           'flow_gpm':number(r['flow_gpm']),'T_in_C':(number(r['temp_in_F'])-32)/1.8,
           'measured_MWD_C':number(r['measured_MWD_C']),'requested_positions_ft':positions,
           'nominal_position_ft':None if n in (3,4) else 84 if n in (27,38) else positions[0],
           'reported_differential_psi':number(r['reported_differential_psi']),
           'motor_heat_psi':max(0,number(r['reported_differential_psi'])) if definition['motor']=='yes' else 0.,
           'documented_motor':definition['motor']=='yes','tfa_m2':sum(math.pi/4*(int(x)/32*INCH)**2 for x in definition['jets_32nds'].split(';')),
           'mud':mud[n]}
        geometry(s,comp,check['checks'][0].get('k_idp',4.9237482416889895))
        samples.append(s)
    history,times,circ,depths=clock(data)
    events=[]
    for r in read(data/'observed_off_spells.csv'):
        if r['long_reset']!='True':continue
        end=epoch(r['end'])
        events.append({**r,'event_id':f'off{len(events)+1:04d}','reset_time_s':end,
                       'reset_circulation_s':float(np.interp(end,times,circ))})
    cases=[]
    for s in samples:
        for fluid in ['recorded_mud','water']:
            for film in [1.,.75]:
                for exposure in ['cumulative','full_recovery']:
                    cases.append(dict(case_id=f'16b-c{len(cases)+1:04d}',sample_id=s['sample_id'],
                                      fluid=fluid,film_mult=film,exposure=exposure))
    package=Path(m1.__file__).parent
    sources={p.name:digest(p) for p in data.iterdir() if p.is_file()}
    package_inputs={str(p):digest(p) for p in Path(str(trial.DATA)).glob('*.csv')}
    model={str(p):digest(p) for p in package.glob('*.py')}
    model[str(Path(trial.__file__))]=digest(trial.__file__)
    plan=dict(baseline=subprocess.check_output(['git','rev-parse','HEAD'],cwd=data.parents[1],text=True).strip(),
        prepared_utc=datetime.now(timezone.utc).isoformat(),study_sha256=digest(__file__),
        protocol_sha256=digest(data/'comparison_protocol_s1.md'),source_hashes=sources,
        selected_source_sha256=digest(selected),calculation_hashes=model,package_input_hashes=package_inputs,
        trial_reproduction=check,k_idp=4.9237482416889895,samples=samples,components=comp,mud=list(mud.values()),
        cases=cases,events=events,exposure_floor_s=m1.T_EXPOSURE_FLOOR,
        clock_summary=dict(missing_flow_rows=sum(int(r['missing_flow_count']) for r in history),
                           incomplete_bins=sum(int(r['raw_count'])!=60 for r in history),
                           gaps_over_600s=int(np.count_nonzero(np.diff(times)>600))),
        versions={'Python':platform.python_version(),**{x:importlib.metadata.version(x) for x in ['borethm','numpy','scipy','iapws','matplotlib']}})
    dump(output/'plan.json',plan);(output/'plan.sha256').write_text(digest(output/'plan.json')+'\n')
    csv_out(output/'mud-inputs.csv',mud.values());csv_out(output/'mud-assignment-ledger.csv',ledger)
    csv_out(output/'case-plan.csv',cases);csv_out(output/'recovery-events.csv',events)
    print(json.dumps(dict(samples=len(samples),cases=len(cases),mud=list(mud.values()),clock=plan['clock_summary']),indent=2))


def run(data,output,limit=None):
    plan=json.loads((output/'plan.json').read_text())
    assert digest(output/'plan.json')==(output/'plan.sha256').read_text().strip(),'Plan changed'
    assert digest(__file__)==plan['study_sha256'],'Study changed'
    for name,h in plan['source_hashes'].items():assert digest(data/name)==h,name
    for name,h in {**plan['calculation_hashes'],**plan['package_input_hashes']}.items():assert digest(name)==h,name
    _,times,circ,depths=clock(data)
    reset_times=[e['reset_time_s'] for e in plan['events']]
    dest=output/'results.jsonl';done=set()
    if dest.exists():done={json.loads(line)['case_id'] for line in dest.read_text().splitlines()}
    samples={s['sample_id']:s for s in plan['samples']};processed=0
    for case in plan['cases']:
        if case['case_id'] in done:continue
        if limit is not None and processed>=limit:break
        s=samples[case['sample_id']];start=time.perf_counter()
        row={**case,'eow_bha':s['eow_bha'],'success':False}
        try:
            g=geometry(s,plan['components'],plan['k_idp'])
            fluid=None
            if case['fluid']=='recorded_mud':
                mud=s['mud'];fluid=fluids.Mud(mud['density_ppg']*PPG,pv_ref=mud['PV_cP']*.001,
                                              yield_point=mud['YP_lbf_100ft2']*YP_PA)
            rho=float(m1.fluid_props(np.array([s['T_in_C']]),np.array([m1.P_SURF]),fluid)[0][0])
            q=s['flow_gpm']*GPM
            now=float(np.interp(s['time_s'],times,circ))
            original=m1.exposure_from_history(circ,depths,now);ex=original
            reset=bisect.bisect_right(reset_times,s['time_s'])-1
            if case['exposure']=='full_recovery' and reset>=0:
                event=plan['events'][reset];cap=max(0,now-event['reset_circulation_s'])
                ex=lambda z:np.minimum(original(z),cap)
                row.update(reset_event=event['event_id'],circulation_since_reset_h=cap/3600)
            else:row.update(reset_event='none',circulation_since_reset_h=None)
            smooth=m1.smooth_exposure(ex,g.md_bit)
            result=m1.solve_seeded(smooth,m1.exposure_breaks(smooth,g.md_bit),m_dot=q*rho,T_inj=s['T_in_C'],
                geotherm=trial.T_FORM,geometry=g,target_rock_T=float(trial.T_FORM(trial.SURVEY.tvd(g.md_bit))),
                Q_face=s['motor_heat_psi']*PSI*q,k_rock=trial.K_ROCK,rhocp_rock=trial.RHOCP_ROCK,
                friction_heat=True,tfa=s['tfa_m2'],film_mult=case['film_mult'],fluid=fluid,verbose=False)
            row.update(success=bool(result['success']),solver_status=int(result['sol'].status),
                solver_message=str(result['sol'].message),seed_success=bool(result['seed']['success']) if result['seed'] else None,
                nodes=len(result['sol'].x),return_C=float(result['Tu'][0]),inlet_density_kg_m3=rho,mass_rate_kg_s=q*rho,
                motor_face_power_W=s['motor_heat_psi']*PSI*q)
            for position in [22,69,84,85]:
                for name,key in [('bore','Td'),('annulus','Tu')]:
                    row[f'{name}_{position}ft_C']=float(np.interp(g.md_bit-position*FT,result['z'],result[key]))
            values=[row[f'bore_{p}ft_C'] for p in s['requested_positions_ft']]
            row['requested_position_spread_C']=max(values)-min(values)
        except Exception as error:row['exception']=f'{type(error).__name__}: {error}'
        row['duration_s']=time.perf_counter()-start
        with dest.open('a',encoding='utf-8') as f:f.write(json.dumps(row,allow_nan=False)+'\n');f.flush()
        processed+=1
        print(case['case_id'],s['eow_bha'],case['fluid'],case['film_mult'],case['exposure'],row['success'],round(row['duration_s'],2),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','run'])
    p.add_argument('--data',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--selected',type=Path)
    p.add_argument('--trial-check',type=Path)
    p.add_argument('--limit',type=int)
    a=p.parse_args()
    if a.action=='prepare':
        if a.selected is None or a.trial_check is None:p.error('prepare requires --selected and --trial-check')
        prepare(a.data.resolve(),a.selected.resolve(),a.output.resolve(),a.trial_check.resolve())
    else:run(a.data.resolve(),a.output.resolve(),a.limit)


if __name__=='__main__':main()
