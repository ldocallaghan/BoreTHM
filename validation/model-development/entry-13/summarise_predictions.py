"""Reduce target-free predictions, audit the geometry and state joint fractions."""
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics as st

import numpy as np

from borethm import hydraulic_losses as hl
from predict import OPTIONS,VARIANTS,diagnosis,geometry,selection,write
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
INCH=.0254


def read(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))


def coefficients(well,angle):
    """Bore K on the tool-joint velocity, tapered and abrupt, for one joint."""
    v=OPTIONS['installed'][well];body=math.pi*(v['body_ID_in']*INCH)**2/4;bore=math.pi*(v['joint_ID_in']*INCH)**2/4
    tapered=(float(hl.conical_change(body,bore,1000.,1.,angle)[1]),float(hl.conical_change(bore,body,1000.,1.,angle)[1]))
    abrupt=(float(hl.local_change(body,bore,1000.,1.,1e-3,v['joint_ID_in']*INCH)[1]),float(hl.local_change(bore,body,1000.,1.,1e-3,v['joint_ID_in']*INCH)[1]))
    return tapered,abrupt


def cone(calc,sample,well,angle):
    """Neglected wall friction for one joint's two cones, at the window's inlet state."""
    v=OPTIONS['installed'][well];d0,d1=v['body_ID_in']*INCH,v['joint_ID_in']*INCH
    length=(d0-d1)/2/math.tan(math.radians(angle)/2)
    fluid,_,_=calc.fluid(sample);q=sample['flow_gpm']*calc.whole.GPM
    rho,_,mu,_=calc.m1.fluid_props(np.array([sample['T_in_C']]),np.array([hl.PROPERTY_FLOOR]),fluid)
    rho,mu=float(rho[0]),float(mu[0]);mass=rho*q;yp=getattr(fluid,'yield_point',0.)
    def gradient(d):return float(hl.passage_gradient(rho,mu,yp,mass,math.pi*d**2/4,d,False,'colebrook')[0])
    x,w=np.polynomial.legendre.leggauss(16);z=(x+1)/2
    wall=2*length*sum(wi/2*gradient(d0+(d1-d0)*zi) for zi,wi in zip(z,w))
    body=2*length*gradient(d0)
    ktaper,kabrupt=coefficients(well,angle)
    velocity=mass/(rho*math.pi*d1**2/4);dyn=.5*rho*velocity**2
    return dict(cone_length_each_in=length/INCH,cone_wall_friction_psi=wall/hl.PSI,body_friction_same_length_psi=body/hl.PSI,
        neglected_excess_psi=(wall-body)/hl.PSI,tapered_local_psi=sum(ktaper)*dyn/hl.PSI,abrupt_local_psi=sum(kabrupt)*dyn/hl.PSI,
        joint_reynolds=rho*velocity*d1/mu,body_reynolds=rho*(mass/(rho*math.pi*d0**2/4))*d0/mu)


def main():
    p=HERE/'predictions';m=json.loads((p/'manifest.json').read_text(encoding='utf-8'))
    assert m['windows']==22 and not m['targets_compared'] and not m['solver_failures']
    rows=read(p/'model-only.csv');assert len(rows)==22*len(VARIANTS)
    grouped=defaultdict(list)
    for r in rows:grouped[r['variant'],r['well']].append(r)
    summary=[]
    fields=('spp_psi_change','model_hydraulic_kW_change','bit_C_change','sensor_bore_C_change','return_C_change',
            'spp_psi_vs_working','model_hydraulic_kW_vs_working','bit_C_vs_working','sensor_bore_C_vs_working','return_C_vs_working',
            'bore_joint_local_psi','annulus_joint_local_psi')
    for (variant,well),group in sorted(grouped.items()):
        r=dict(variant=variant,well=well,windows=len(group))
        for name in fields:
            values=[float(x[name]) for x in group]
            r.update({name+'_min':min(values),name+'_max':max(values),name+'_mean':st.mean(values)})
        summary.append(r)
    write(p/'rough-effects.csv',summary)
    old={(r['sample_id'],r['variant']):r for r in read(HERE.parent/'entry-12/predictions/model-only.csv')}
    checks=[]
    for r in rows:
        if r['variant'] not in ('working','installed_primary','installed_no_local'):continue
        for name in ('spp_psi','model_hydraulic_kW','bit_C','return_C'):
            a,b=float(old[r['sample_id'],r['variant']][name]),float(r[name])
            tolerance=1. if name=='spp_psi' else .001*max(abs(a),1) if name=='model_hydraulic_kW' else .1
            checks.append(dict(sample_id=r['sample_id'],variant=r['variant'],field=name,entry12=a,replayed=b,
                               difference=b-a,tolerance=tolerance,passed=abs(b-a)<=tolerance))
    assert all(r['passed'] for r in checks)
    write(p/'entry12-replay-check.csv',checks)
    calc=diagnosis.Calculation();samples=[s for s in calc.plan['samples'] if not(s['well']=='16A' and s.get('source')!='Sanvean on-bottom')]
    windows=selection.select(samples);audit=[]
    for s in windows:
        for variant in VARIANTS:
            g=geometry(calc,s,variant)
            for n,segment in enumerate(g.string):
                joint=segment.pipe.hydraulic_joint
                if joint is None:continue
                audit.append(dict(sample_id=s['id'],well=s['well'],assembly=s['run'],variant=variant,segment=n,
                    name=segment.pipe.name,length_ft=segment.length/.3048,body_ID_in=2*segment.pipe.r_bore/.0254,
                    joint_ID_in=joint.bore_diameter/.0254,restriction_in=joint.restriction_length/.0254,
                    spacing_ft=joint.spacing/.3048,transition=joint.transition,taper_angle_deg=joint.taper_angle_deg))
    write(p/'geometry-audit.csv',audit)
    # A tapered joint must carry the installed bore on non-insulated, non-HWDP pipe.
    for r in audit:
        if r['transition']=='tapered':
            assert not r['name'].startswith('IDP,') and 'HWDP' not in r['name'].upper()
            assert math.isclose(r['joint_ID_in'],OPTIONS['installed'][r['well']]['joint_ID_in'])
        elif r['name'].startswith('IDP,'):
            assert r['transition'] in ('abrupt','gradual')
    assert any(r['transition']=='tapered' for r in audit)
    fractions=[]
    for well in ('16A','16B'):
        chosen=sorted((s for s in windows if s['well']==well),key=lambda s:s['flow_gpm'])
        sample=chosen[len(chosen)//2]
        for angle in sorted({v['taper_angle_deg'] for v in OPTIONS['variants'].values() if 'taper_angle_deg' in v}):
            t,a=coefficients(well,angle)
            fractions.append(dict(well=well,angle_deg=angle,K_contraction=t[0],K_expansion=t[1],K_total=sum(t),
                abrupt_K_contraction=a[0],abrupt_K_expansion=a[1],abrupt_K_total=sum(a),bore_local_fraction_of_abrupt=sum(t)/sum(a),
                representative_sample=sample['id'],representative_flow_gpm=sample['flow_gpm'],**cone(calc,sample,well,angle)))
    write(p/'joint-fractions.csv',fractions)
    reynolds=[]
    for s in windows:
        if s['well'] not in OPTIONS['installed']:continue
        values=cone(calc,s,s['well'],11.5)
        reynolds.append(dict(sample_id=s['id'],well=s['well'],assembly=s['run'],flow_gpm=s['flow_gpm'],
            inlet_C=s['T_in_C'],body_reynolds=values['body_reynolds'],joint_reynolds=values['joint_reynolds']))
    write(p/'joint-reynolds.csv',reynolds)
    m['source_sha256_summaries']={Path(__file__).relative_to(ROOT).as_posix():hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    m['derived_sha256']={name:hashlib.sha256((p/name).read_bytes()).hexdigest() for name in ('rough-effects.csv','entry12-replay-check.csv','geometry-audit.csv','joint-fractions.csv','joint-reynolds.csv')}
    (p/'manifest.json').write_bytes((json.dumps(m,indent=2)+'\n').encode('utf-8'))
    print('Predictions reduced; entry 12 replay checks passed:',len(checks))


if __name__=='__main__':main()
