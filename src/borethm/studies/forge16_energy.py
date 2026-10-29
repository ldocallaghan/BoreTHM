"""Frozen-input FORGE rheology sensitivities, heat transfer and energy checks.

This study calls existing model functions unchanged. Its S2 protocol is in
validation/forge16b/comparison_protocol_s2.md. Original blind evidence is read
only; all new plans, profiles and diagnostics go to an explicit output folder.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import importlib.metadata
import json
import math
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from borethm import fluids, model1_coupled as m1
from borethm.studies import validate_forge16a as a
from borethm.studies import validate_forge16b as b
from borethm.studies import validate_forge16b_wholewell as whole

FT, GPM, PSI = b.FT, b.GPM, b.PSI
PPG, YP_PA = whole.PPG, whole.YP_PA


def read(path):return whole.read(path)
def digest(path):return whole.digest(path)
def csv_out(path,rows):return whole.csv_out(path,rows)
def epoch(s):return whole.epoch(s)


def finite(s):
    n=whole.number(s)
    return n if math.isfinite(n) else None


def clean(obj):
    if isinstance(obj,dict):return {k:clean(v) for k,v in obj.items()}
    if isinstance(obj,(list,tuple)):return [clean(v) for v in obj]
    if isinstance(obj,(float,np.floating)):return float(obj) if math.isfinite(obj) else None
    if isinstance(obj,np.integer):return int(obj)
    return obj


def dump(path,obj):whole.dump(path,clean(obj))


def snapshot(root):
    return {p.relative_to(root).as_posix():digest(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def fluid_system(t):
    if t>=epoch('2023-06-17 14:00:00'):return 'post-TD sweep/logging fluid'
    return whole.system(t)


def revised_mud(data,old):
    observations={}
    for filename in ['mud_samples.csv','mud_supplement_s1.csv']:
        for i,r in enumerate(read(data/filename),1):
            t=datetime.strptime(r['sample'][:15],'%d-%b-%y %H:%M').replace(tzinfo=timezone.utc).timestamp()
            observations[f'{filename}:{i}']={**r,'time_s':t,'fluid_system':fluid_system(t),'source_id':f'{filename}:{i}'}
    result={};ledger=[]
    for run in old:
        fields=[]
        for sid in run['source_ids'].split(';'):
            r=observations[sid];filled={}
            for key in ['density_ppg','PV_cP','YP_lbf_100ft2']:
                value=finite(r.get(key));donor=r;method='reported'
                if value is None:
                    candidates=[x for x in observations.values() if x['fluid_system']==r['fluid_system'] and finite(x.get(key)) is not None]
                    if candidates:
                        donor=min(candidates,key=lambda x:(abs(x['time_s']-r['time_s']),x['time_s'],x['source_id']))
                        value=finite(donor[key]);method='nearest measurement either direction within fluid system'
                    elif key=='PV_cP':donor=None;method='water viscosity at recorded density'
                    elif key=='YP_lbf_100ft2':value=0.;donor=None;method='zero water yield point at recorded density'
                    else:raise ValueError('Missing density in selected source row')
                filled[key]=value
                ledger.append(dict(eow_bha=run['eow_bha'],source_id=sid,sample=r['sample'],source_page=r['page'],
                    fluid_system=r['fluid_system'],field=key,value=value,method=method,
                    donor_source_id=donor['source_id'] if donor else '',donor_sample=donor['sample'] if donor else '',
                    donor_page=donor['page'] if donor else '',donor_offset_days=(donor['time_s']-r['time_s'])/86400 if donor else None))
            fields.append(filled)
        values={}
        for key in ['density_ppg','PV_cP','YP_lbf_100ft2']:
            xs=[r[key] for r in fields]
            if all(x is None for x in xs):values[key]=None
            elif any(x is None for x in xs):raise ValueError('Mixed water and measured viscosity in one fluid system')
            else:values[key]=float(np.mean(xs))
        assert abs(values['density_ppg']-run['density_ppg'])<1e-12
        completed=[x for x in ledger if x['eow_bha']==run['eow_bha']]
        nearest=[x for x in completed if x['method'].startswith('nearest')]
        result[run['eow_bha']]={**run,**values,'rule':'S2 nearest either direction; water rheology if no measurement',
            'carried_fields':len(nearest),'reference_fields':0,
            'future_donor_fields':sum(x['donor_offset_days']>0 for x in nearest),
            'water_fallback_fields':sum(x['method'].startswith(('water','zero water')) for x in completed)}
    return result,ledger


def clock_a(data):
    rows=read(data/'rig_history_1min.csv')
    times=np.array([epoch(r['time']) for r in rows])
    circ=np.cumsum([(finite(r['circulating_fraction']) or 0.)*60 for r in rows])
    depths=[];last=0.;events=[];start=None
    for i,r in enumerate(rows):
        last=max(last,finite(r['hole_depth_ft']) or last);depths.append(last*FT)
        known=(finite(r['circulating_fraction'])==0 and
               finite(r['flow_valid_count'])==finite(r['source_count']) and (finite(r['flow_valid_count']) or 0)>0)
        contiguous=i==0 or times[i]-times[i-1]==60
        if start is not None and (not known or not contiguous):
            end=i-1;duration=times[end]+60-times[start]
            if duration>7200:events.append(dict(end_s=float(times[end]+60),duration_s=float(duration),near_surface=False))
            start=None
        if known and start is None:start=i
    if start is not None:
        duration=times[-1]+60-times[start]
        if duration>7200:events.append(dict(end_s=float(times[-1]+60),duration_s=float(duration),near_surface=False))
    return times,circ,np.array(depths),events


def trip_context(events,t):
    before=[x for x in events if x['end_s']<=t]
    near=[x for x in before if x['near_surface']]
    return dict(hours_since_last_observed_off_over2h=(t-before[-1]['end_s'])/3600 if before else None,
                hours_since_near_surface_trip_proxy=(t-near[-1]['end_s'])/3600 if near else None,
                confirmed_surface_trip_time_available=False)


def prepare(data_a,data_b,plan_a,output):
    output.mkdir(parents=True,exist_ok=True)
    if (output/'plan.json').exists():raise FileExistsError('Frozen S2 plan already exists')
    if Path(a.DATA).resolve()!=data_a:raise ValueError('16A helper archive must match explicit input archive')
    pa=json.loads(plan_a.read_text());pb=json.loads((data_b/'s1/frozen-inputs.json').read_text())
    revised,ledger=revised_mud(data_b,pb['mud'])
    olda={r['sample_id']:r for r in read(data_a/'circulation-primary.csv')}
    oldb={r['sample_id']:r for r in map(json.loads,(data_b/'s1/results.jsonl').read_text().splitlines())
          if r['fluid']=='recorded_mud' and r['film_mult']==1 and r['exposure']=='cumulative'}
    sources_a={run:{r['time']:r for r in read(data_a/f'sanvean_BHA{run}_10s.csv')} for run in a.RUNS}
    rig={r['time']:r for r in read(data_a/'rig_history_1min.csv')}
    _,_,_,events_a=clock_a(data_a)
    events_b=[dict(end_s=epoch(r['end']),duration_s=float(r['duration_s']),near_surface=r['trip_to_surface']=='True')
              for r in read(data_b/'observed_off_spells.csv') if r['long_reset']=='True']
    cooler_b={int(r['eow_bha']):r['cooler_context'] for r in read(data_b/'period_input_summary.csv')}
    samples=[]
    for s in pb['samples']:
        n=s['eow_bha']
        samples.append({**s,'well':'16B','id':'16B-'+s['sample_id'],'run':str(n),
            'density_ppg':s['mud']['density_ppg'],'original_mud':s['mud'],'revised_mud':revised[n],
            'measured_return_C':(float(s['temp_out_F'])-32)/1.8,'spp_psi':float(s['spp_psi']),
            'pressure_source':'Pason frozen EYE-qualified window mean','pressure_count':int(s['qualified_rows']),
            'raw_differential_psi':s['reported_differential_psi'],'rop_ft_h':float(s['rop_ft_h']),
            'cooler_context':cooler_b[n],**trip_context(events_b,s['time_s']),
            'saved_primary':oldb[s['sample_id']]})
    for s in pa['samples']:
        if s['source']=='Sanvean on-bottom':r=sources_a[s['run']][s['time']]
        else:r=rig.get(s['time'],{})
        pressure=finite(r.get('pump_pressure_psi')) if s['source']=='Sanvean on-bottom' else None
        rawdp=finite(r.get('motor_differential_psi'))
        samples.append({**s,'well':'16A','id':'16A-'+s['sample_id'],'density_ppg':s['mud_weight_ppg'],
            'requested_positions_ft':[0,40],'nominal_position_ft':None,'sensor_quantity':'Unresolved bore/annulus and bit/40 ft; both fixed channels',
            'spp_psi':pressure,'pressure_count':finite(r.get('pump_pressure_psi_count')) if pressure is not None else 0,
            'pressure_source':'Sanvean exact frozen input centre' if pressure is not None else 'Unavailable; return-only or missing Sanvean pressure',
            'raw_differential_psi':rawdp,'rop_ft_h':finite(r.get('rop_ft_h')),
            'motor_heat_psi':s['motor_dp_psi'],'cooler_context':'Coolers rigged up 24 Oct; operational count unverified; measured mud-log inlet used',
            **trip_context(events_a,s['time_s']),'saved_primary':olda[s['sample_id']]})
    cases=[]
    for s in samples:
        for mode in (['s1_original','s2_revised'] if s['well']=='16B' else ['blind_original','water_rheology_sensitivity']):
            cases.append(dict(case_id=f's2-{len(cases)+1:04d}',sample=s['id'],well=s['well'],rheology_case=mode))
    package=Path(m1.__file__).parent
    hashes={p.relative_to(package).as_posix():digest(p) for p in package.glob('*.py')}
    for module in [a,b,whole]:hashes[Path(module.__file__).relative_to(package).as_posix()]=digest(module.__file__)
    plan=dict(baseline=pb['baseline'],prepared_utc=datetime.now(timezone.utc).isoformat(),script_sha256=digest(__file__),
        protocol_sha256=digest(data_b/'comparison_protocol_s2.md'),source_a=snapshot(data_a),source_b=snapshot(data_b),
        original_plan_a_sha256=digest(plan_a),calculation_hashes=hashes,components_a=pa['components'],components_b=pb['components'],
        k_idp=pb['k_idp'],samples=samples,cases=cases,revised_mud=list(revised.values()),
        versions={'Python':platform.python_version(),**{n:importlib.metadata.version(n) for n in ['borethm','numpy','scipy','iapws','matplotlib']}})
    dump(output/'plan.json',plan);(output/'plan.sha256').write_text(digest(output/'plan.json')+'\n')
    csv_out(output/'mud-revision-ledger.csv',ledger);csv_out(output/'revised-mud.csv',revised.values());csv_out(output/'case-plan.csv',cases)
    print(json.dumps(dict(samples_16A=sum(s['well']=='16A' for s in samples),samples_16B=sum(s['well']=='16B' for s in samples),cases=len(cases),mud=list(revised.values())),indent=2))


def fluid_for(s,mode):
    if s['well']=='16B':
        mud=s['original_mud'] if mode=='s1_original' else s['revised_mud']
        pv=mud['PV_cP'];yp=mud['YP_lbf_100ft2']
    else:
        pv=None if mode=='water_rheology_sensitivity' else s['pv_cP']
        yp=0. if mode=='water_rheology_sensitivity' else s['yp_lbf_100ft2']
    return fluids.Mud(s['density_ppg']*PPG,pv_ref=pv*.001 if pv is not None else None,yield_point=yp*YP_PA),pv,yp


def annulus_values(g,mdot,fluid,result,z):
    z=np.asarray(z,float);geom=g.at(z);temp=result['sol'].sol(z)[1]
    pressure=m1.P_of_z(geom['tvd']);rho,cp,mu,k=m1.fluid_props(temp,pressure,fluid)
    vel=mdot/(rho*geom['A_ann']);re=mdot*geom['Dh_ann']/(geom['A_ann']*mu)
    h=m1.h_dittus(mdot,geom['A_ann'],geom['Dh_ann'],temp,pressure,fluid=fluid)
    if fluid.yield_point>0:
        _,apparent=fluids.bingham_gradient(rho,mu,fluid.yield_point,vel,geom['Dh_ann'],True)
        hyd_laminar=apparent<=fluids.RE_CRITICAL
    else:apparent=re;hyd_laminar=re<2300
    return dict(z=z,annulus_T_C=temp,Re_thermal=re,thermal_laminar=re<2300,h_annulus_W_m2K=h,
                Re_hydraulic_apparent=apparent,hydraulic_laminar=hyd_laminar,mu_Pas=mu,
                rho_kg_m3=rho,velocity_m_s=vel,Dh_annulus_m=geom['Dh_ann'])


def diagnostics(s,g,fluid,result,exposure,breaks,mdot):
    top,bot=m1._pieces(g);cuts=np.unique(np.r_[top,bot,np.linspace(0,g.md_bit,int(np.ceil(g.md_bit/25))+1)])
    mids=(cuts[:-1]+cuts[1:])/2;length=np.diff(cuts)
    profile=annulus_values(g,mdot,fluid,result,mids);profile['length_m']=length
    out={}
    for key in ['Re_thermal','h_annulus_W_m2K','Re_hydraulic_apparent']:
        vals=profile[key];out[key+'_min']=float(vals.min());out[key+'_max']=float(vals.max());out[key+'_length_mean']=float(np.sum(vals*length)/g.md_bit)
    out['thermal_laminar_length_fraction']=float(np.sum(length*profile['thermal_laminar'])/g.md_bit)
    out['hydraulic_laminar_length_fraction']=float(np.sum(length*profile['hydraulic_laminar'])/g.md_bit)
    for position in [0,22,40,69,84,85]:
        values=annulus_values(g,mdot,fluid,result,np.array([g.md_bit-position*FT]))
        for key in ['Re_thermal','h_annulus_W_m2K','Re_hydraulic_apparent','thermal_laminar','hydraulic_laminar']:
            val=values[key][0];out[f'{key}_{position}ft']=bool(val) if key.endswith('laminar') else float(val)
    hyd=m1.hydraulics(mdot,g,result=result,tfa=s['tfa_m2'],fluid=fluid)
    out.update({k:float(hyd[k]) for k in ['spp','dp_string','dp_annulus','dp_bit','dp_buoyancy','pump_power']})
    midpoint=(top+bot)/2;geom=g.at(midpoint);pressure=m1.P_of_z(geom['tvd'])
    tb=np.interp(midpoint,result['z'],result['Td']);ta=np.interp(midpoint,result['z'],result['Tu'])
    rb=m1.fluid_props(tb,pressure,fluid)[0];ra=m1.fluid_props(ta,pressure,fluid)[0]
    out['hydraulic_local_friction_power_W']=float(sum(p['dp_bore']*mdot/rb[i]+p['dp_ann']*mdot/ra[i] for i,p in enumerate(hyd['pieces'])))
    model_top,_=m1._pieces(g,breaks);changes=model_top[1:]
    z=np.unique(np.r_[np.linspace(0,g.md_bit,int(np.ceil(g.md_bit))+1),changes,changes-.5*m1.BLEND,changes+.5*m1.BLEND])
    z=z[(z>=0)&(z<=g.md_bit)];td,tu=result['sol'].sol(z)
    form=b.T_FORM if s['well']=='16B' else a.formation('216',g.survey)[0]
    # the rock term the diagnosed solve used; results without one are from the original logarithmic term
    response=result.get('rock_response') or 'logarithmic'
    def terms(geom_z=None):
        gm=g.at(z if geom_z is None else geom_z);P=m1.P_of_z(g.survey.tvd(z))
        ui,uo,_=m1.conductances(z,td,tu,mdot,1/365,b.K_ROCK,g,exposure,fluid,b.RHOCP_ROCK,geom_z,1.,
                                 rock_response=response)
        rock=uo*(form(g.survey.tvd(z))-tu);internal=ui*(tu-td)
        cb=m1._cp(td,P,fluid);ca=m1._cp(tu,P,fluid)
        gb=m1._friction_gradient(mdot,td,P,gm['A_bore'],gm['Dh_bore'],fluid)
        ga=m1._friction_gradient(mdot,tu,P,gm['A_ann'],gm['Dh_ann'],fluid)
        return np.array([gb/cb+ga/ca,rock/(mdot*ca),internal/mdot*(1/cb-1/ca),mdot*gb,mdot*ga,rock])
    rates=terms()
    for change in changes:
        mask=np.abs(z-change)<.5*m1.BLEND
        if not mask.any():continue
        left=terms(np.full_like(z,change-m1.BLEND));right=terms(np.full_like(z,change+m1.BLEND))
        weight=(z[mask]-change)/m1.BLEND+.5
        rates[:,mask]=(1-weight)*left[:,mask]+weight*right[:,mask]
    integrals=np.trapezoid(rates,z,axis=1)
    out.update(rise_distributed_friction_C=float(integrals[0]),rise_rock_C=float(integrals[1]),
               rise_internal_cp_C=float(integrals[2]),thermal_friction_bore_W=float(integrals[3]),
               thermal_friction_annulus_W=float(integrals[4]),rock_exchange_W=float(integrals[5]))
    q=s['flow_gpm']*GPM;Pbit=float(m1.P_of_z(g.survey.tvd(g.md_bit)))
    rho,cp,_,_=m1.fluid_props(np.array([result['Td'][-1]]),np.array([Pbit]),fluid)
    nozzle=m1.nozzle_dp(mdot,float(rho[0]),s['tfa_m2'])
    out.update(thermal_nozzle_power_W=nozzle*mdot/float(rho[0]),motor_face_power_W=s['motor_heat_psi']*PSI*q,
        rise_nozzle_C=nozzle/(float(rho[0])*float(cp[0])),rise_motor_C=s['motor_heat_psi']*PSI*q/(mdot*float(cp[0])),
        model_spp_at_inlet_flow_W=hyd['spp']*q,thermal_friction_power_W=float(integrals[3]+integrals[4]))
    out['model_rise_C']=float(result['Tu'][0]-s['T_in_C'])
    out['measured_rise_C']=s['measured_return_C']-s['T_in_C']
    out['rise_error_C']=out['model_rise_C']-out['measured_rise_C']
    out['rise_closure_error_C']=out['model_rise_C']-sum(out[k] for k in ['rise_distributed_friction_C','rise_rock_C','rise_internal_cp_C','rise_nozzle_C','rise_motor_C'])
    if s['spp_psi'] is not None:
        out.update(measured_hydraulic_power_W=s['spp_psi']*PSI*q,raw_spp_residual_psi=hyd['spp']/PSI-s['spp_psi'])
        if s['raw_differential_psi'] is not None:
            out['spp_minus_raw_differential_psi']=s['spp_psi']-s['raw_differential_psi']
            out['adjusted_spp_residual_psi']=hyd['spp']/PSI-out['spp_minus_raw_differential_psi']
    rhoin,cpin,_,_=m1.fluid_props(np.array([s['T_in_C']]),np.array([m1.P_SURF]),fluid)
    out['inlet_rho_kg_m3']=float(rhoin[0]);out['inlet_cp_J_kgK']=float(cpin[0])
    if s['spp_psi'] is not None:out['measured_hydraulic_rise_equiv_C']=out['measured_hydraulic_power_W']/(mdot*float(cpin[0]))
    return out,profile


def run(data_a,data_b,output,limit=None):
    plan=json.loads((output/'plan.json').read_text())
    assert digest(output/'plan.json')==(output/'plan.sha256').read_text().strip()
    assert digest(__file__)==plan['script_sha256']
    assert snapshot(data_a)==plan['source_a'],'16A archive changed'
    assert snapshot(data_b)==plan['source_b'],'16B archive changed'
    package=Path(m1.__file__).parent
    for name,h in plan['calculation_hashes'].items():assert digest(package/name)==h,name
    ta,ca,da,_=clock_a(data_a);_,tb,cb,db=whole.clock(data_b)
    samples={s['id']:s for s in plan['samples']};dest=output/'results.jsonl'
    done={json.loads(x)['case_id'] for x in dest.read_text().splitlines()} if dest.exists() else set()
    (output/'profiles').mkdir(exist_ok=True);processed=0
    for case in plan['cases']:
        if case['case_id'] in done:continue
        if limit is not None and processed>=limit:break
        s=samples[case['sample']];start=time.perf_counter();row={**case,'run':s['run'],'success':False,'solver_success':False}
        try:
            if s['well']=='16B':g=whole.geometry(s,plan['components_b'],plan['k_idp']);form=b.T_FORM;times,circ,depth=tb,cb,db
            else:g=a.geometry(s['run'],s['bit_ft'],plan['components_a']);form=a.formation('216',g.survey)[0];times,circ,depth=ta,ca,da
            fluid,pv,yp=fluid_for(s,case['rheology_case']);q=s['flow_gpm']*GPM
            rho=float(m1.fluid_props(np.array([s['T_in_C']]),np.array([m1.P_SURF]),fluid)[0][0]);mdot=q*rho
            ex=m1.smooth_exposure(m1.exposure_from_history(circ,depth,float(np.interp(s['time_s'],times,circ))),g.md_bit)
            breaks=m1.exposure_breaks(ex,g.md_bit)
            result=m1.solve_seeded(ex,breaks,m_dot=mdot,T_inj=s['T_in_C'],geotherm=form,geometry=g,
                target_rock_T=float(form(g.survey.tvd(g.md_bit))),Q_face=s['motor_heat_psi']*PSI*q,
                k_rock=b.K_ROCK,rhocp_rock=b.RHOCP_ROCK,friction_heat=True,tfa=s['tfa_m2'],film_mult=1.,fluid=fluid,verbose=False)
            row.update(solver_success=bool(result['success']),solver_status=int(result['sol'].status),solver_message=str(result['sol'].message),
                seed_success=bool(result['seed']['success']) if result['seed'] else None,nodes=len(result['sol'].x),
                return_C=float(result['Tu'][0]),pv_ref_cP=pv,yp_lbf_100ft2=yp,density_ppg=s['density_ppg'],
                water_viscosity=pv is None,mass_rate_kg_s=mdot,bit_tvd_ft=float(g.survey.tvd(g.md_bit)/FT),
                formation_at_bit_C=float(form(g.survey.tvd(g.md_bit))))
            for pos in [0,22,40,69,84,85]:
                for name,key in [('bore','Td'),('annulus','Tu')]:row[f'{name}_{pos}ft_C']=float(np.interp(g.md_bit-pos*FT,result['z'],result[key]))
            d,profile=diagnostics(s,g,fluid,result,ex,breaks,mdot);row.update(d)
            np.savez_compressed(output/'profiles'/(case['case_id']+'.npz'),**profile)
            row['success']=row['solver_success']
            if case['rheology_case'] in ['s1_original','blind_original']:
                saved=s['saved_primary'];keys=['return_C']
                if s['well']=='16B':keys += [f'{medium}_{pos}ft_C' for medium in ['bore','annulus'] for pos in [22,69,84,85]]
                else:
                    for medium in ['bore','annulus']:
                        row[medium+'_bit_C']=row[medium+'_0ft_C']
                    keys+=a.BRANCHES if isinstance(a.BRANCHES,list) else list(a.BRANCHES)
                row['max_saved_temperature_difference_C']=max(abs(row[k]-float(saved[k])) for k in keys)
        except Exception as err:row['exception']=f'{type(err).__name__}: {err}'
        row['duration_s']=time.perf_counter()-start
        with dest.open('a',encoding='utf-8') as f:f.write(json.dumps(clean(row),allow_nan=False)+'\n');f.flush()
        processed+=1
        print(case['case_id'],s['well'],s['run'],case['rheology_case'],'ok='+str(row['success']),f'{row["duration_s"]:.2f}s',flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','run']);p.add_argument('--data16a',type=Path,required=True)
    p.add_argument('--data16b',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--plan16a',type=Path);p.add_argument('--limit',type=int)
    q=p.parse_args()
    if q.action=='prepare':
        if q.plan16a is None:p.error('prepare requires --plan16a')
        prepare(q.data16a.resolve(),q.data16b.resolve(),q.plan16a.resolve(),q.output.resolve())
    else:run(q.data16a.resolve(),q.data16b.resolve(),q.output.resolve(),q.limit)


if __name__=='__main__':main()
