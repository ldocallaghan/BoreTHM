"""Independent arithmetic and provenance audit of the motorless pressure tables."""
import csv
import hashlib
import json
import math
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from borethm import fluids, model1_coupled as m1
from borethm.studies import forge16_energy as energy
from borethm.studies import validate_forge16b_wholewell as whole

ROOT = Path(__file__).resolve().parents[2]/'geothermal-thermo-hydraulic-model'
OUT = Path(__file__).resolve().parent/'s2b'
DATA = ROOT/'validation/forge16b'
read = lambda name: list(csv.DictReader((OUT/name).open(newline='',encoding='utf-8')))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
plan = json.loads((OUT/'plan.json').read_text())
assert sha(OUT/'plan.json') == (OUT/'plan.sha256').read_text().strip()
assert sha(ROOT/'src/borethm/studies/forge16b_hydraulics.py') == plan['script_sha256']
assert sha(DATA/'comparison_protocol_s2b.md') == plan['protocol_sha256']
for name, value in plan['calculation_hashes'].items():
    assert sha(Path(m1.__file__).parent/name) == value, name
for name, value in plan['source_hashes'].items():
    assert sha(DATA/name) == value, name
for name, value in plan['preserved_archives'].items():
    assert sha(DATA/name) == value, name

samples = read('pressure-samples.csv')
assert len(samples) == 90
assert Counter((r['run'], r['rheology_case']) for r in samples) == Counter({
    (str(run), mode): count for run, count in ((12,12),(13,14),(15,4),(16,15))
    for mode in ('s1_original','s2_revised')})
ss = {r['case_id']:r for r in samples}
input_samples = {r['id']:r for r in plan['samples']}
pieces = read('model-pieces.csv')
components = read('bha-components.csv')
transitions = read('bha-transitions.csv')
joints = read('tool-joints.csv')
budgets = read('scenario-budgets.csv')
assert len(budgets) == 6480
assert set(Counter(r['case_id'] for r in budgets).values()) == {72}
for r in samples:
    case = r['case_id']
    expected = plan['expected'][case]
    included = sum(float(r[k]) for k in ('pipe_body_psi','bha_hwdp_psi',
        'bha_lower_aggregate_psi','bit_nozzles_psi','annulus_psi','density_column_psi'))
    assert abs(included-float(r['model_spp_psi'])) < 1e-9
    assert abs(float(r['model_spp_psi'])-expected['spp']/whole.PSI) < 1e-9
    assert float(r['motor_allowance_psi']) == 0.
    assert r['unknown_tool_loss_psi'] == ''
    own = [p for p in pieces if p['case_id'] == case]
    assert abs(sum(float(p['dp_bore']) for p in own)/whole.PSI-sum(float(r[k])
        for k in ('pipe_body_psi','bha_hwdp_psi','bha_lower_aggregate_psi'))) < 1e-9

# Independently reconstruct each component's Darcy/Bingham calculation from
# saved temperature profiles and recorded length/diameters.
for case, row in ss.items():
    inp = input_samples[row['sample']]
    fluid, _, _ = energy.fluid_for(inp,row['rheology_case'])
    profile = np.load(OUT/'profiles'/f'{case}.npz')
    g = whole.geometry(inp,plan['components'],plan['k_idp'])
    mdot = float(plan['expected'][case]['mass_rate_kg_s'])
    own = [c for c in components if c['case_id']==case]
    for c in own:
        z=(float(c['md_top_ft'])+float(c['md_bottom_ft']))*.5*whole.FT
        length=float(c['length_ft'])*whole.FT
        pressure=float(m1.P_of_z(g.survey.tvd(z)))
        hole=float(2*g.at(np.array([z]))['r_wall'][0])
        for annulus in (False,True):
            temp=float(np.interp(z,profile['z'],profile['Tu' if annulus else 'Td']))
            rho,_,mu,_=(float(x[0]) for x in m1.fluid_props(np.array([temp]),np.array([pressure]),fluid))
            d=float(c['id_in'])*whole.INCH
            od=float(c['annulus_od_used_in'])*whole.INCH
            area=math.pi*(hole**2-od**2)/4 if annulus else math.pi*d*d/4
            diameter=hole-od if annulus else d
            v=mdot/(rho*area)
            ty=fluid.yield_point
            apparent=mu+ty*diameter/((8 if annulus else 6)*v)
            re=rho*v*diameter/apparent
            lam=(48 if annulus else 32)*mu*v/diameter**2+(6 if annulus else 16/3)*ty/diameter
            turb=.316*(rho*v*diameter/mu)**-.25*rho*v*v/(2*diameter)
            expected=(turb if re>2100 else lam)*length/whole.PSI
            key='annulus_friction_psi' if annulus else 'bore_friction_psi'
            assert abs(expected-float(c[key]))<1e-8,(case,c['component'],key)

joint_sums=defaultdict(lambda: [0.,0.,0.])
for r in joints:
    key=(r['case_id'],r['geometry'])
    joint_sums[key][0 if r['conduit']=='bore' else 1]+=float(r['increment_psi_per_inch'])
    joint_sums[key][2]+=float(r['sudden_local_psi'])
transition_sums=defaultdict(float)
for r in transitions:
    transition_sums[r['case_id']]+=float(r['loss_psi'])
for r in budgets:
    sample=ss[r['case_id']]
    jb,ja,jl=joint_sums[(r['case_id'],r['joint_geometry'])]
    length=float(r['joint_length_in'])
    assert abs(float(r['joint_internal_increment_psi'])-jb*length)<1e-9
    assert abs(float(r['joint_annulus_increment_psi'])-ja*length)<1e-9
    shape=r['local_shape']=='sudden'
    assert abs(float(r['joint_local_increment_psi'])-(jl if shape else 0))<1e-9
    assert abs(float(r['bha_local_increment_psi'])-(transition_sums[r['case_id']] if shape else 0))<1e-9
    surface=float(r['surface_coefficient'])*float(sample['density_ppg'])*(float(sample['flow_gpm'])/100)**1.86
    assert abs(surface-float(r['surface_lines_estimate_psi']))<1e-9
    added=sum(float(r[k]) for k in ('bha_bore_increment_psi','bha_annulus_increment_psi',
        'joint_internal_increment_psi','joint_annulus_increment_psi','joint_local_increment_psi',
        'bha_local_increment_psi','surface_lines_estimate_psi'))
    assert abs(float(r['estimated_increment_psi'])-added)<1e-9
    total=float(sample['model_spp_psi'])+added
    measured=float(sample['measured_spp_psi'])
    assert abs(float(r['accounted_psi'])-total)<1e-9
    assert abs(float(r['remaining_residual_psi'])-(measured-total))<1e-9
    assert abs(float(r['accounted_fraction'])-total/measured)<1e-12
    assert r['unknown_tool_loss_psi']==''

replays=read('replays.csv')
assert len(replays)==90 and all(r['success']=='True' for r in replays)
assert max(float(r['max_temperature_difference_C']) for r in replays)==0
report=dict(samples=45,replays=90,scenario_budgets=6480,
    max_replay_temperature_difference_C=0,
    max_replay_pressure_difference_psi=max(abs(float(r['pressure_difference_psi'])) for r in replays),
    duration_s=sum(float(r['duration_s']) for r in replays),
    existing_calculation_files_unchanged=len(plan['calculation_hashes']),
    preserved_S1_S2_archive_files=len(plan['preserved_archives']),
    source_files_unchanged=len(plan['source_hashes']),
    independent_component_rows_checked=len(components),
    revised_joint_Re_domain_failures=sum(r['newtonian_Re_domain']=='False' for r in joints if r['rheology_case']=='s2_revised'),
    original_joint_Re_domain_failures=sum(r['newtonian_Re_domain']=='False' for r in joints if r['rheology_case']=='s1_original'),
    all_checks_passed=True)
(OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
