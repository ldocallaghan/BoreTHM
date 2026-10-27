"""Replay S2b frozen-point formulas and reconcile production differences.

No circulation solves and no held-out 56-32/58-32 target access. The frozen
S2b profiles and archived rheology convention are preserved. Uses package
formula kernels at the original component, transition and joint points.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
import time
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import numpy as np
from borethm import hydraulic_losses as hl, model1_coupled as m1, well_geometry as wg
from borethm.studies import forge16b_hydraulics as old, forge16_energy as energy
from borethm.studies import validate_forge16b_wholewell as whole

FT,INCH,PSI,GPM=old.FT,old.INCH,old.PSI,old.GPM
PROTOCOL_COMMIT='8bbfe2c44658dade8972a647970e3308047b6380'


def read(path):
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt',encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))


def write(path,rows):
    names=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,names,lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


class GuardedFluid:
    def __init__(self,fluid):
        self.original=fluid
        self.yield_point=getattr(fluid,'yield_point',0.)

    def props(self,t,p):
        return m1.fluid_props(t,np.maximum(p,5e6),self.original)


def props(g,result,fluid,depth,ann=False):
    t=float(np.interp(depth,result['z'],result['Tu' if ann else 'Td']))
    p=float(m1.P_of_z(g.survey.tvd(depth)))
    rho,cp,mu,k=(float(v[0]) for v in m1.fluid_props(np.array([t]),np.array([p]),fluid))
    return rho,mu


def run(data,out,limit=None):
    start=time.perf_counter()
    out.mkdir(parents=True,exist_ok=True)
    files=['plan.json','replayed-profiles.npz','pressure-samples.csv','bha-components.csv','bha-transitions.csv','tool-joints.csv.gz','scenario-budgets.csv']
    source_hashes={n:hashlib.sha256((data/n).read_bytes()).hexdigest() for n in files}
    plan=json.loads((data/'plan.json').read_text())
    profiles=np.load(data/'replayed-profiles.npz')
    samples={r['id']:r for r in plan['samples']}
    tables={}
    for name in ('pressure-samples','bha-components','bha-transitions','tool-joints','scenario-budgets'):
        grouped=defaultdict(list)
        for r in read(data/(name+('.csv.gz' if name=='tool-joints' else '.csv'))):
            grouped[r['case_id']].append(r)
        tables[name]=grouped
    checks,guard_rows,production_rows=[],[],[]
    maxima=defaultdict(float)
    cases=plan['cases'] if limit is None else plan['cases'][:limit]
    for case in cases:
        cid=case['case_id']
        s=samples[case['sample']]
        g=whole.geometry(s,plan['components'],plan['k_idp'])
        fluid=energy.fluid_for(s,case['rheology_case'])[0]
        rho_in=float(m1.fluid_props(np.array([s['T_in_C']]),np.array([m1.P_SURF]),fluid)[0][0])
        mass=s['flow_gpm']*GPM*rho_in
        result={k:profiles[cid+'_'+k] for k in ('z','Td','Tu')}
        legacy=m1.hydraulics(mass,g,result=result,fluid=fluid,tfa=s['tfa_m2'],hydraulics_model='v1.5.0')
        guarded=m1.hydraulics(mass,g,result=result,fluid=GuardedFluid(fluid),tfa=s['tfa_m2'],hydraulics_model='v1.5.0')
        oldrow=tables['pressure-samples'][cid][0]
        error=legacy['spp']/PSI-float(oldrow['model_spp_psi'])
        assert abs(error)<1e-8,(cid,'legacy',error)
        maxima['legacy_psi']=max(maxima['legacy_psi'],abs(error))
        guard_rows.append(dict(case_id=cid,run=s['run'],rheology_case=case['rheology_case'],
            legacy_psi=legacy['spp']/PSI,guarded_legacy_psi=guarded['spp']/PSI,
            guard_only_delta_psi=(guarded['spp']-legacy['spp'])/PSI,
            guard_only_delta_percent=100*(guarded['spp']/legacy['spp']-1),
            string_delta_psi=(guarded['dp_string']-legacy['dp_string'])/PSI,
            annulus_delta_psi=(guarded['dp_annulus']-legacy['dp_annulus'])/PSI,
            bit_delta_psi=(guarded['dp_bit']-legacy['dp_bit'])/PSI,
            buoyancy_delta_psi=(guarded['dp_buoyancy']-legacy['dp_buoyancy'])/PSI))
        component_values=[]
        for r in tables['bha-components'][cid]:
            depth=(float(r['md_top_ft'])+float(r['md_bottom_ft']))*FT/2
            hole=2*float(g.at(np.array([depth]))['r_wall'][0])
            inside=float(r['id_in'])*INCH
            outside=float(r['annulus_od_used_in'])*INCH
            values=[]
            for ann in (False,True):
                rho,mu=props(g,result,fluid,depth,ann)
                area=math.pi*(hole**2-outside**2)/4 if ann else math.pi*inside**2/4
                dh=hole-outside if ann else inside
                value=float(hl.passage_gradient(rho,mu,fluid.yield_point,mass,area,dh,ann)[0])*float(r['length_ft'])*FT/PSI
                expected=float(r['annulus_friction_psi' if ann else 'bore_friction_psi'])
                maxima['component_psi']=max(maxima['component_psi'],abs(value-expected))
                values.append(value)
            component_values.append(values)
        serial_bore=sum(v[0] for v in component_values)
        serial_ann=sum(v[1] for v in component_values)
        delta_bore=serial_bore-float(oldrow['bha_lower_aggregate_psi'])
        lower_ann=sum(p['dp_ann']/PSI for p in legacy['pieces'] if p['md_top']>=g._seg_ends[1]-1e-6)
        delta_ann=serial_ann-lower_ann
        lower=[dict(c) for c in reversed(plan['components'][str(s['eow_bha'])]) if c['kind']!='HWDP']
        for c in lower:
            c['annulus_od_used_in']=2*float(g.at(np.array([g.md_bit]))['r_out'][0])/INCH if 'bit' in c['component'].lower() else c['od_in']
        sequence=[dict(component='ordinary pipe',length_ft=g.string[0].length/FT,id_in=4.670,od_in=5.5),
                  dict(next(c for c in plan['components'][str(s['eow_bha'])] if c['kind']=='HWDP')),*lower]
        transition_values=[]
        depth=0.
        for upper,down in zip(sequence,sequence[1:]):
            depth+=upper['length_ft']*FT
            hole=2*float(g.at(np.array([depth]))['r_wall'][0])
            for ann in (False,True):
                rho,mu=props(g,result,fluid,depth,ann)
                if ann:
                    od1=down.get('annulus_od_used_in',down['od_in'])*INCH
                    od2=upper.get('annulus_od_used_in',upper['od_in'])*INCH
                    au,ad=math.pi*(hole**2-od1**2)/4,math.pi*(hole**2-od2**2)/4
                    dh=hole-max(od1,od2)
                else:
                    au,ad=(math.pi*(c['id_in']*INCH)**2/4 for c in (upper,down))
                    dh=min(upper['id_in'],down['id_in'])*INCH
                value=float(hl.local_change(au,ad,rho,mass,mu,dh)[0])/PSI
                expected=next(r for r in tables['bha-transitions'][cid] if r['upper']==upper['component'] and r['lower']==down['component']
                    and r['conduit']==('annulus' if ann else 'bore') and abs(float(r['md_ft'])-depth/FT)<1e-5)
                maxima['transition_psi']=max(maxima['transition_psi'],abs(value-float(expected['loss_psi'])))
                transition_values.append(value)
        joint_values=defaultdict(lambda:dict(internal=0.,annulus=0.,local=0.))
        for r in tables['tool-joints'][cid]:
            depth=float(r['md_ft'])*FT
            ann=r['conduit']=='annulus'
            rho,mu=props(g,result,fluid,depth,ann)
            hole=2*float(g.at(np.array([depth]))['r_wall'][0])
            bid=float(r['body_ID_in'])*INCH
            jid=float(r['joint_ID_in'])*INCH
            jod=float(r['joint_OD_in'])*INCH
            if ann:
                ab,aj=math.pi*(hole**2-(5.5*INCH)**2)/4,math.pi*(hole**2-jod**2)/4
                db,dj=hole-5.5*INCH,hole-jod
            else:
                ab,aj=math.pi*bid**2/4,math.pi*jid**2/4
                db,dj=bid,jid
            replacement,local=hl.joint_increment(rho,mu,fluid.yield_point,mass,ab,db,aj,dj,INCH,ann)
            weight=float(r['joint_count_weight'])
            replacement=float(replacement)*weight/PSI
            local=float(local)*weight/PSI
            maxima['joint_per_inch_psi']=max(maxima['joint_per_inch_psi'],abs(replacement-float(r['increment_psi_per_inch'])))
            maxima['joint_local_psi']=max(maxima['joint_local_psi'],abs(local-float(r['sudden_local_psi'])))
            joint_values[r['geometry']]['annulus' if ann else 'internal']+=replacement
            joint_values[r['geometry']]['local']+=local
        formula={}
        for r in tables['scenario-budgets'][cid]:
            name=r['joint_geometry']
            length=float(r['joint_length_in'])
            sudden=r['local_shape']=='sudden'
            surface_case=int(r['surface_case'])
            jj=joint_values[name]
            surface=0. if surface_case==0 else Surface(surface_case,s['density_ppg']*hl.PPG,s['flow_gpm']*GPM)/PSI
            frozen=dict(body=legacy['dp_string']/PSI+legacy['dp_annulus']/PSI+delta_bore+delta_ann,
                        joint_replacement=length*(jj['internal']+jj['annulus']),
                        joint_local=jj['local'] if sudden else 0.,geometric_local=sum(transition_values) if sudden else 0.,
                        bit=legacy['dp_bit']/PSI,buoyancy=legacy['dp_buoyancy']/PSI,surface=surface)
            total=sum(frozen.values())
            error=total-float(r['accounted_psi'])
            maxima['scenario_total_psi']=max(maxima['scenario_total_psi'],abs(error))
            formula[(name,length,sudden,surface_case)]=(frozen,total)
            checks.append(dict(case_id=cid,joint_geometry=name,joint_length_in=length,local_shape=r['local_shape'],surface_case=surface_case,
                               archived_psi=float(r['accounted_psi']),package_formula_replay_psi=total,difference_psi=error))
        for name,(od,jid) in old.JOINTS.items():
            for length in old.JOINT_LENGTHS_IN:
                for sudden in (False,True):
                    shape='abrupt' if sudden else 'gradual'
                    strings=[]
                    for i,c in enumerate(sequence):
                        pipe=whole.steel(c['component'],c.get('annulus_od_used_in',c['od_in']),c['id_in'])
                        if i<2:
                            pitch=old.JOINT_PITCH_FT*FT if i==0 else c['length_ft']*FT/30
                            joint=hl.HydraulicJoint(od*INCH,(jid if i==0 else c['id_in'])*INCH,length*INCH,pitch,shape,'frozen S2b scenario')
                            pipe=replace(pipe,hydraulic_joint=joint)
                        strings.append(wg.StringSegment(c['length_ft']*FT,pipe))
                    serial=wg.WellGeometry(strings,g.hole,g.survey)
                    raw=hl.hydraulics(mass,serial,result=result,fluid=fluid,tfa=s['tfa_m2'],transitions=shape,guard=False)
                    production=hl.hydraulics(mass,serial,result=result,fluid=fluid,tfa=s['tfa_m2'],transitions=shape,guard=True)
                    for surface_case in range(6):
                        frozen,total=formula[(name,float(length),sudden,surface_case)]
                        surface=0. if surface_case==0 else Surface(surface_case,rho_in,mass/rho_in)/PSI
                        pieces={key:sum(side[key] for side in raw['terms'].values())/PSI for key in ('body','joint_replacement','joint_local','geometric_local')}
                        deltas={key+'_delta_psi':pieces[key]-frozen[key] for key in pieces}
                        deltas.update(bit_sampling_delta_psi=raw['dp_bit']/PSI-frozen['bit'],
                                      buoyancy_integration_delta_psi=raw['dp_buoyancy']/PSI-frozen['buoyancy'],
                                      surface_density_delta_psi=surface-frozen['surface'],
                                      production_guard_delta_psi=(production['spp']-raw['spp'])/PSI)
                        prediction=production['spp']/PSI+surface
                        reconciliation=prediction-total-sum(deltas.values())
                        assert abs(reconciliation)<1e-7,(cid,'reconciliation',reconciliation)
                        production_rows.append(dict(case_id=cid,run=s['run'],rheology_case=case['rheology_case'],joint_geometry=name,
                            joint_length_in=length,local_shape=shape,surface_case=surface_case,frozen_point_psi=total,
                            production_psi=prediction,total_delta_psi=prediction-total,**deltas,reconciliation_error_psi=reconciliation))
        print(cid,'formula replay and production accounting verified',flush=True)
    assert all(v<1e-8 for v in maxima.values()),dict(maxima)
    for filename,rows in (('formula-replay.csv',checks),('legacy-guard.csv',guard_rows),('production-reconciliation.csv',production_rows)):
        write(out/filename,rows)
    assert all(hashlib.sha256((data/n).read_bytes()).hexdigest()==h for n,h in source_hashes.items())
    guard=[r['guard_only_delta_psi'] for r in guard_rows]
    percent=[r['guard_only_delta_percent'] for r in guard_rows]
    report=dict(protocol_commit=PROTOCOL_COMMIT,cases=len(cases),scenario_replays=len(checks),production_cases=len(production_rows),
        formula_max_errors=dict(maxima),legacy_guard_delta_psi_min=min(guard),legacy_guard_delta_psi_max=max(guard),
        legacy_guard_delta_percent_min=min(percent),legacy_guard_delta_percent_max=max(percent),
        duration_s=time.perf_counter()-start,source_hashes=source_hashes,preserved_archives=True,
        field_rheology_convention='archived 26.7 C retained for this formula replay',held_out_targets_read=False,
        production_difference_notes='integrated properties, conservative geometry/source blend, added casing transitions, bottom nozzle state, buoyancy integration and inlet surface density; guard isolated separately')
    (out/'replay-summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report,indent=2))


def Surface(case,rho,flow):
    return hl.SurfaceLoss.api_case(case).pressure(rho,flow)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,default=Path('validation/forge16b/s2b'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--limit',type=int)
    args=parser.parse_args()
    run(args.data,args.output,args.limit)
