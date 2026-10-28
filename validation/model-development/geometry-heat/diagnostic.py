"""Separate thermal geometry and heat-source geometry without changing a model.

The study composes existing conductance and dissipation functions. Its matched
controls must reproduce the archived whole-model calculations at 0.1 C.
"""
import argparse
from collections import defaultdict
import importlib.util
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import solve_bvp

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('frozen_scoreboard',ROOT/'validation/scoreboard/scoreboard.py')
score=importlib.util.module_from_spec(spec);spec.loader.exec_module(score)
m1,hl,a,b,whole,energy=score.m1,score.hl,score.a,score.b,score.whole,score.energy


def solve(thermal,source,new_thermal,new_heat,exposure,breaks,mass,fluid,inlet,form,face,tfa,
          seed_years=1.,init=None):
    """The original equations with independently selected existing inputs."""
    length=thermal.md_bit
    top,bottom=m1._pieces(thermal,breaks)
    changes=top[1:]
    heat_changes=m1._pieces(source,breaks)[0][1:]
    loss=hl.LossModel(source) if new_heat else None
    ttop,tbottom=m1._pieces(thermal)
    overlapping=new_thermal and len(changes)>1 and np.any(np.diff(changes)<m1.BLEND)
    bit_p=float(m1.P_of_z(thermal.survey.tvd(length)))

    def thermal_rhs(z,td,tu,at=None):
        ui,uo,p=m1.conductances(z,td,tu,mass,seed_years,b.K_ROCK,thermal,exposure,
            fluid,b.RHOCP_ROCK,at,1.,m1.P_SURF)
        rock=form(thermal.survey.tvd(z))
        return ui*(tu-td)/(mass*m1._cp(td,p,fluid)),(-uo*(rock-tu)+ui*(tu-td))/(mass*m1._cp(tu,p,fluid))

    def old_sources(z,td,tu,at=None):
        g=source.at(z if at is None else at)
        p=m1.P_of_z(source.survey.tvd(z))
        return (m1._friction_gradient(mass,td,p,g['A_bore'],g['Dh_bore'],fluid)/m1._cp(td,p,fluid),
                -m1._friction_gradient(mass,tu,p,g['A_ann'],g['Dh_ann'],fluid)/m1._cp(tu,p,fluid))

    def blend_two(z,td,tu,function,edges):
        hd,hu=function(z,td,tu)
        for edge in edges:
            mask=abs(z-edge)<.5*m1.BLEND
            if not mask.any():continue
            zz=z[mask];left=function(zz,td[mask],tu[mask],np.full_like(zz,edge-m1.BLEND))
            right=function(zz,td[mask],tu[mask],np.full_like(zz,edge+m1.BLEND))
            w=(zz-edge)/m1.BLEND+.5
            hd[mask]=(1-w)*left[0]+w*right[0];hu[mask]=(1-w)*left[1]+w*right[1]
        return hd,hu

    def odes(z,y):
        td,tu=y
        if not overlapping:
            dd,du=blend_two(z,td,tu,thermal_rhs,changes)
        else:
            dd,du=thermal_rhs(z,td,tu)
            width=min(m1.BLEND,length)
            near=np.zeros(z.shape,bool)
            for edge in ttop[1:]:near|=abs(z-edge)<width/2
            dd[near]=0.;du[near]=0.
            for lower,upper in zip(ttop,tbottom):
                weight=np.zeros_like(z)
                for lo,hi in ((lower,upper),(-upper,-lower),(2*length-upper,2*length-lower)):
                    weight+=np.maximum(0.,np.minimum(z+width/2,hi)-np.maximum(z-width/2,lo))/width
                mask=near&(weight>0)
                if mask.any():
                    value=thermal_rhs(z[mask],td[mask],tu[mask],np.full(mask.sum(),(lower+upper)/2))
                    dd[mask]+=weight[mask]*value[0];du[mask]+=weight[mask]*value[1]
        hd,hu=(hl.heat_gradients(loss,z,td,tu,mass,fluid) if new_heat else
               blend_two(z,td,tu,old_sources,heat_changes))
        return np.vstack([dd+hd,du+hu])

    def bc(ya,yb):
        cp=float(m1._cp(np.array([yb[0]]),np.array([bit_p]),fluid)[0])
        rho=float(m1.fluid_props(np.array([yb[0]]),np.array([max(bit_p,m1.P_LIQUID) if new_heat else bit_p]),fluid)[0][0])
        jump=face/(mass*cp)+m1.nozzle_dp(mass,rho,tfa)/(rho*cp)
        return np.array([ya[0]-inlet,yb[1]-yb[0]-jump])

    z=np.unique(np.r_[np.linspace(0,length,160),changes-.5*m1.BLEND,changes+.5*m1.BLEND,
                      heat_changes-.5*m1.BLEND,heat_changes+.5*m1.BLEND])
    if new_thermal or new_heat:z=z[(z>=0)&(z<=length)]
    target=float(form(thermal.survey.tvd(length)))
    y=(np.vstack([np.interp(z,[0,length],[inlet,inlet+30]),np.interp(z,[0,length],[inlet+30,target*.7])])
       if init is None else np.vstack([np.interp(z,init['z'],init['Td']),np.interp(z,init['z'],init['Tu'])]))
    sol=solve_bvp(odes,bc,z,y,max_nodes=20000,tol=1e-4)
    zz=np.linspace(0,length,400);td,tu=sol.sol(zz)
    return dict(z=zz,Td=td,Tu=tu,sol=sol,m_dot=mass,geometry=thermal,
                success=bool(sol.success and max(td.max(),tu.max())<480.),solver_status=int(sol.status))


def seeded(**kw):
    result=None
    for years in m1.SEED_YEARS:
        seed=solve(**{**kw,'exposure':None,'breaks':()},seed_years=years)
        if not seed['success']:continue
        result=solve(**kw,seed_years=years,init=seed)
        if result['success']:return result
    return result if result is not None else solve(**kw)


def setup(sample,plan,clocks):
    legacy=score.geometry(sample,plan,'legacy');current=score.geometry(sample,plan,'current')
    _,pv,yp=energy.fluid_for(sample,'s1_original' if sample['well']=='16B' else 'blind_original')
    fluid=score.Mud(sample['density_ppg']*whole.PPG,pv_ref=None if pv is None else pv*.001,
                    yield_point=yp*whole.YP_PA,pv_ref_T=26.7)
    flow=sample['flow_gpm']*whole.GPM
    rho=float(m1.fluid_props(np.array([sample['T_in_C']]),np.array([m1.P_SURF]),fluid)[0][0])
    times,clock,depth=clocks[sample['well']]
    exposure=m1.smooth_exposure(m1.exposure_from_history(clock,depth,float(np.interp(sample['time_s'],times,clock))),legacy.md_bit)
    form=b.T_FORM if sample['well']=='16B' else a.formation('216',legacy.survey)[0]
    return legacy,current,dict(exposure=exposure,breaks=m1.exposure_breaks(exposure,legacy.md_bit),
        mass=flow*rho,fluid=fluid,inlet=sample['T_in_C'],form=form,face=sample['motor_heat_psi']*whole.PSI*flow,tfa=sample['tfa_m2'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--controls-only',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    plan=score.read_json(score.PLAN)
    samples=[s for s in plan['samples'] if (s.get('measured_bit_box_C') if s['well']=='16A' else s.get('measured_MWD_C')) is not None]
    assert len(samples)==244
    before={r['sample_id']:r for r in score.read_csv(ROOT/'validation/scoreboard/baseline/circulation.csv')}
    after={r['sample_id']:r for r in score.read_csv(ROOT/'validation/model-development/entry-1/circulation.csv')}
    ta,ca,da,_=energy.clock_a(ROOT/'validation/forge16a');_,tb,cb,db=whole.clock(ROOT/'validation/forge16b')
    clocks={'16A':(ta,ca,da),'16B':(tb,cb,db)}
    ids={r['sample_id'] for r in score.read_csv(ROOT/'validation/model-development/entry-2/selected-windows.csv')}
    controls=[];started=time.perf_counter()
    for sample in samples:
        if sample['id'] not in ids:continue
        legacy,current,kw=setup(sample,plan,clocks)
        for name,geom,new,reference in [('legacy',legacy,False,before),('entry1',current,True,after)]:
            result=seeded(thermal=geom,source=geom,new_thermal=new,new_heat=new,**kw)
            saved=reference[sample['id']]
            row=dict(sample_id=sample['id'],well=sample['well'],bha=sample['run'],control=name,
                success=result['success'],bit_difference_C=float(result['Td'][-1])-float(saved['bit_C']),
                return_difference_C=float(result['Tu'][0])-float(saved['return_C']))
            row['passed']=row['success'] and max(abs(row['bit_difference_C']),abs(row['return_difference_C']))<=.1
            controls.append(row);score.write_csv(args.output/'controls.csv',controls)
    if not all(r['passed'] for r in controls):raise RuntimeError('Matched controls differ from their archives')
    if args.controls_only:return
    rows=[]
    for sample in samples:
        legacy,current,kw=setup(sample,plan,clocks)
        old,new=before[sample['id']],after[sample['id']]
        cp=float(m1._cp(np.array([float(old['bit_C'])]),np.array([m1.P_of_z(legacy.survey.tvd(legacy.md_bit))]),kw['fluid'])[0])
        added=float(new['model_hydraulic_W'])-float(old['model_hydraulic_W'])
        bound=added/(kw['mass']*cp)
        for case,thermal,source,nt,nh in [('A',legacy,current,False,True),('B',current,legacy,True,False)]:
            row=dict(sample_id=sample['id'],well=sample['well'],bha=sample['run'],case=case,success=False,
                archived_bit_rise_C=float(new['bit_C'])-float(old['bit_C']),
                archived_return_rise_C=float(new['return_C'])-float(old['return_C']),
                added_in_hole_W=added,mass_rate_kg_s=kw['mass'],cp_legacy_bit_J_kgK=cp,bulk_heating_scale_C=bound)
            try:
                result=seeded(thermal=thermal,source=source,new_thermal=nt,new_heat=nh,**kw)
                bit=float(result['Td'][-1]);ret=float(result['Tu'][0])
                row.update(success=result['success'],solver_status=result['solver_status'],bit_C=bit,return_C=ret,
                    bit_change_C=bit-float(old['bit_C']),return_change_C=ret-float(old['return_C']),
                    bit_exceeds_bulk_scale=bit-float(old['bit_C'])>bound+.1)
            except Exception as error:row['error']=f'{type(error).__name__}: {error}'
            rows.append(row);score.write_csv(args.output/'samples.csv',rows)
        print(json.dumps(dict(sample=sample['id'],completed=len(rows))),flush=True)
    groups=defaultdict(list)
    for row in rows:groups[row['well'],row['bha'],row['case']].append(row)
    summaries=[]
    for (well,bha,case),group in sorted(groups.items()):
        good=[r for r in group if r['success']]
        summary=dict(well=well,bha=bha,case=case,planned=len(group),compared=len(good),failures=len(group)-len(good))
        for field in ('bit_change_C','return_change_C','archived_bit_rise_C','archived_return_rise_C',
                      'added_in_hole_W','mass_rate_kg_s','cp_legacy_bit_J_kgK','bulk_heating_scale_C'):
            if good:summary[field]=float(np.mean([r[field] for r in good]))
        summary['bit_scale_exceedances']=sum(r['bit_exceeds_bulk_scale'] for r in good)
        summaries.append(summary)
    score.write_csv(args.output/'assemblies.csv',summaries)
    score.write_json(args.output/'manifest.json',dict(declaration='71b2c10',sample_count=len(samples),cases=len(rows),
        failures=sum(not r['success'] for r in rows),runtime_s=time.perf_counter()-started,
        settings=dict(PV_reference_C=26.7,film_multiplier=1.,exposure='cumulative',controls_resolution_C=.1),
        meaning='Bulk heating scale is not a pointwise counterflow temperature bound',
        results_sha256={p.name:score.sha(p) for p in args.output.glob('*.csv')}))


if __name__=='__main__':main()
