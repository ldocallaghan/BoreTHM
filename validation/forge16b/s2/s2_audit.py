"""Independent arithmetic and provenance checks of the S2 evidence; no solves."""
import csv
import hashlib
import json
import math
import statistics as st
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from borethm import fluids,model1_coupled as m1
from borethm.studies import validate_forge16a as a,validate_forge16b_wholewell as b

ROOT=Path(__file__).resolve().parents[2]/'geothermal-thermo-hydraulic-model'
OUT=Path(__file__).resolve().parent/'s2';DA=ROOT/'validation/forge16a';DB=ROOT/'validation/forge16b'
def read(p):
    with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'plan.json').read_text());ss={s['id']:s for s in plan['samples']}
rows=[json.loads(x) for x in (OUT/'results.jsonl').read_text().splitlines()]
assert len(rows)==934 and {r['case_id'] for r in rows}=={r['case_id'] for r in plan['cases']}
assert sha(OUT/'plan.json')==(OUT/'plan.sha256').read_text().strip()
assert sha(ROOT/'src/borethm/studies/forge16_energy.py')==plan['script_sha256']
for root,mapping in [(DA,plan['source_a']),(DB,plan['source_b'])]:
    for name,digest in mapping.items():assert sha(root/name)==digest,name
package=Path(m1.__file__).parent
for name,digest in plan['calculation_hashes'].items():assert sha(package/name)==digest,name
replays=[r for r in rows if 'max_saved_temperature_difference_C' in r]
assert len(replays)==467 and max(r['max_saved_temperature_difference_C'] for r in replays)<.01
assert sum(s['well']=='16A' and s['spp_psi'] is not None for s in ss.values())==135
assert sum(s['well']=='16B' and s['spp_psi'] is not None for s in ss.values())==109
assert sum(s['well']=='16A' and s['spp_psi'] is None for s in ss.values())==223
obs={}
def stamp(s):return datetime.strptime(s[:15],'%d-%b-%y %H:%M').replace(tzinfo=timezone.utc).timestamp()
def system(t):
    if t>=datetime(2023,6,17,14,tzinfo=timezone.utc).timestamp():return 3
    if t<datetime(2023,5,3,21,50,tzinfo=timezone.utc).timestamp():return 0
    if t<datetime(2023,5,12,15,30,tzinfo=timezone.utc).timestamp():return 1
    return 2
for filename in ['mud_samples.csv','mud_supplement_s1.csv']:
    for i,r in enumerate(read(DB/filename),1):obs[f'{filename}:{i}']=r
ledger=read(OUT/'mud-revision-ledger.csv')
for r in ledger:
    source=obs[r['source_id']];t=stamp(source['sample']);key=r['field']
    if r['method']=='reported':assert float(r['value'])==float(source[key]);continue
    eligible=[]
    for sid,o in obs.items():
        try:v=float(o.get(key,''))
        except ValueError:continue
        ot=stamp(o['sample'])
        if system(t)==system(ot):eligible.append((abs(ot-t),ot,sid,v))
    if eligible:
        chosen=min(eligible)
        assert r['donor_source_id']==chosen[2] and float(r['value'])==chosen[3]
        assert math.isclose(float(r['donor_offset_days']),(chosen[1]-t)/86400,abs_tol=1e-12)
    else:assert 'water' in r['method']
geometries={};profiles=0
for r in rows:
    assert r['success'],r
    s=ss[r['sample']]
    if s['id'] not in geometries:
        geometries[s['id']]=a.geometry(s['run'],s['bit_ft'],plan['components_a']) if s['well']=='16A' else b.geometry(s,plan['components_b'],plan['k_idp'])
    g=geometries[s['id']]
    if s['well']=='16A':
        pv=None if r['rheology_case']=='water_rheology_sensitivity' else s['pv_cP']
        yp=0 if r['rheology_case']=='water_rheology_sensitivity' else s['yp_lbf_100ft2']
    else:
        mud=s['original_mud'] if r['rheology_case']=='s1_original' else s['revised_mud']
        pv=mud['PV_cP'];yp=mud['YP_lbf_100ft2']
    fluid=fluids.Mud(s['density_ppg']*119.8264273,pv_ref=pv*.001 if pv is not None else None,yield_point=yp*.4788025898)
    with np.load(OUT/'profiles'/(r['case_id']+'.npz')) as p:
        geom=g.at(p['z']);P=m1.P_of_z(geom['tvd'])
        rho,cp,mu,k=m1.fluid_props(p['annulus_T_C'],P,fluid)
        re=r['mass_rate_kg_s']*geom['Dh_ann']/(geom['A_ann']*mu)
        pr=cp*mu/k
        h=np.where(re<2300,4.36,.023*re**.8*pr**.4)*k/geom['Dh_ann']
        assert np.allclose(re,p['Re_thermal'],rtol=1e-12,atol=1e-8)
        assert np.allclose(h,p['h_annulus_W_m2K'],rtol=1e-12,atol=1e-8)
        assert np.array_equal(re<2300,p['thermal_laminar'])
        velocity=r['mass_rate_kg_s']/(rho*geom['A_ann'])
        apparent=rho*velocity*geom['Dh_ann']/(mu+fluid.yield_point*geom['Dh_ann']/(8*np.maximum(abs(velocity),1e-9)))
        assert np.allclose(apparent,p['Re_hydraulic_apparent'],rtol=1e-12,atol=1e-8)
        assert math.isclose(float(p['length_m'].sum()),g.md_bit,abs_tol=1e-9)
        fraction=float(np.sum(p['length_m']*(re<2300))/g.md_bit)
        assert math.isclose(fraction,r['thermal_laminar_length_fraction'],abs_tol=1e-12)
        profiles+=1
    assert math.isclose(r['spp'],r['dp_string']+r['dp_annulus']+r['dp_bit']+r['dp_buoyancy'],abs_tol=1e-6)
    q=s['flow_gpm']*b.GPM
    assert math.isclose(r['motor_face_power_W'],s['motor_heat_psi']*b.PSI*q,abs_tol=1e-7)
    assert math.isclose(r['model_spp_at_inlet_flow_W'],r['spp']*q,abs_tol=1e-6)
    if s['spp_psi'] is not None:
        assert math.isclose(r['measured_hydraulic_power_W'],s['spp_psi']*b.PSI*q,abs_tol=1e-6)
        assert math.isclose(r['adjusted_spp_residual_psi'],r['spp']/b.PSI-(s['spp_psi']-s['raw_differential_psi']),abs_tol=1e-8)
    summed=sum(r[k] for k in ['rise_distributed_friction_C','rise_rock_C','rise_internal_cp_C','rise_nozzle_C','rise_motor_C'])
    assert math.isclose(r['rise_closure_error_C'],r['model_rise_C']-summed,abs_tol=1e-12)
    assert math.isclose(r['rise_error_C'],r['return_C']-s['measured_return_C'],abs_tol=1e-10)
for s in ss.values():
    if s['well']=='16A':
        x=next(r for r in rows if r['sample']==s['id'] and r['rheology_case']=='blind_original')
        y=next(r for r in rows if r['sample']==s['id'] and r['rheology_case']=='water_rheology_sensitivity')
        assert x['density_ppg']==y['density_ppg']==s['density_ppg']
        assert math.isclose(x['mass_rate_kg_s'],y['mass_rate_kg_s'],abs_tol=1e-12)
        assert y['pv_ref_cP'] is None and y['yp_lbf_100ft2']==0
q4=read(OUT/'matched-primary-comparison.csv')
shared=[r for r in q4 if r['shared']=='True']
assert shared and all(r['A_ordinary_pipe_OD_in'] and r['B_ordinary_pipe_OD_in'] for r in shared)
assert sum(int(r['n_16A']) for r in q4)==135 and sum(int(r['n_16B']) for r in q4)==109
old=json.loads((ROOT.parent/'experiments/forge16b-wholewell/s0/model-and-existing-input-hashes.json').read_text())
for name,h in old.items():assert sha(ROOT/name)==h,name
report=dict(cases=len(rows),solver_failures=sum(not r['solver_success'] for r in rows),diagnostic_failures=sum(not r['success'] for r in rows),
    original_primary_replays_verified=len(replays),profiles_independently_verified=profiles,mud_field_assignments_verified=len(ledger),
    unchanged_baseline_files=len(old),unchanged_16a_source_files=len(plan['source_a']),unchanged_16b_source_files=len(plan['source_b']),
    pressure_samples_16A=135,pressure_samples_16B=109,missing_pressure_16A_return_only=223,
    matched_bins=len(shared),unmatched_bins=len(q4)-len(shared),
    max_abs_temperature_balance_closure_C=max(abs(r['rise_closure_error_C']) for r in rows))
(OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
