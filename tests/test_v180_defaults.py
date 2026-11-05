"""The v1.8.0 default physics, its v1.7.0 preset and the tool allowances."""
import csv
from dataclasses import replace
import inspect
import math
from pathlib import Path

import numpy as np
import pytest

import borethm
from borethm import fluids, physics, tool_losses
from borethm import hydraulic_losses as hl
from borethm import model1_coupled as m1
from borethm import well_geometry as wg
from borethm.programme import HydraulicProgramme, programme_from_dict

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.default_physics
WATER = dict(rho=1000., cp=4180., mu=1e-3, k=.6)


def well(tools=(), joint=None, tool_loss=None):
    pipe = wg.PipeType('p', (wg.Layer(.05, .06, 45.),), hydraulic_joint=joint)
    collar = wg.PipeType('c', (wg.Layer(.03, .08, 45.),))
    return wg.WellGeometry([wg.StringSegment(900., pipe), wg.StringSegment(100., collar, tool_loss=tool_loss, tools=tuple(tools))],
                           [wg.open_hole(0., 1000., .22)])


@pytest.mark.parametrize('name,row', [(n, r) for n, r in physics.PRESETS.items()])
def test_each_preset_row_resolves(name, row):
    settings = physics.resolve(name)
    assert settings['physics'] == name
    assert all(settings[k] == v for k, v in row.items())


def test_table_of_defaults():
    new, old = physics.PRESETS['v1.8.0'], physics.PRESETS['v1.7.0']
    assert (new['annulus_model'], new['friction'], new['roughness']) == ('herschel-bulkley-erge', 'colebrook', 0.)
    assert (new['ordinary_joint_transition'], new['taper_angle_deg']) == ('tapered', 11.5)
    assert (old['annulus_model'], old['friction'], old['ordinary_joint_transition']) == ('v1.6.0', 'blasius', 'abrupt')
    assert physics.DEFAULT == 'v1.8.0'


def test_explicit_keyword_overrides_the_preset():
    settings = physics.resolve('v1.8.0', annulus_model='v1.6.0', friction='blasius')
    assert settings['annulus_model'] == 'v1.6.0' and settings['friction'] == 'blasius'
    assert physics.resolve('v1.7.0', friction='colebrook', roughness=1e-5)['roughness'] == 1e-5
    assert physics.resolve('v1.8.0', hydraulics_model='v1.5.0')['physics'] == 'v1.7.0'
    with pytest.raises(ValueError):
        physics.resolve('v1.6.0')


def test_result_records_physics_and_override():
    g = well()
    r = borethm.circulating_temperatures(m_dot=20., geometry=g, fluid=WATER, target_rock_T=100.)
    assert r['physics'] == 'v1.8.0' and r['annulus_model'] == 'herschel-bulkley-erge'
    assert r['friction'] == 'colebrook' and r['roughness'] == 0.
    assert r['physics_settings']['ordinary_joint_transition'] == 'tapered'
    old = borethm.circulating_temperatures(m_dot=20., geometry=g, fluid=WATER, target_rock_T=100., physics='v1.7.0')
    assert old['annulus_model'] == 'v1.6.0' and old['friction'] == 'blasius'
    mixed = borethm.circulating_temperatures(m_dot=20., geometry=g, fluid=WATER, target_rock_T=100., physics='v1.7.0', friction='colebrook')
    assert mixed['friction'] == 'colebrook' and mixed['annulus_model'] == 'v1.6.0'
    assert borethm.hydraulics(20., g, result=old, fluid=WATER)['spp'] == m1.hydraulics(20., g, result=old, fluid=WATER, physics='v1.7.0')['spp']


def test_joint_kinds_resolve_under_each_physics():
    base = hl.HydraulicJoint(.17, .08, .5, 9.)
    assert base.resolved('v1.8.0').transition == 'tapered' and base.resolved('v1.8.0').taper_angle_deg == 11.5
    assert base.resolved('v1.7.0').transition == 'abrupt'
    for kind in ('insulated', 'heavy-weight', 'bha'):
        for name in physics.PRESETS:
            assert replace(base, kind=kind).resolved(name).transition == 'abrupt'
    assert replace(base, transition='abrupt').resolved('v1.8.0').transition == 'abrupt'
    assert replace(base, taper_angle_deg=6.3).resolved('v1.8.0').taper_angle_deg == 6.3
    assert replace(base, kind='insulated', taper_angle_deg=6.3).resolved('v1.7.0').transition == 'tapered'
    with pytest.raises(ValueError):
        replace(base, kind='other')


def test_reference_programme_joint_kinds():
    for name, expected in (('v1.8.0', 'tapered'), ('v1.7.0', 'abrupt')):
        g = HydraulicProgramme.reference_programme(physics=name).geometry(5000., wg.CONVENTIONAL)
        joints = [s.pipe.hydraulic_joint for s in g.string if s.pipe.hydraulic_joint is not None]
        assert joints[0].kind == 'ordinary' and joints[0].resolved(name).transition == expected
        assert joints[1].kind == 'heavy-weight' and joints[1].resolved(name).transition == 'abrupt'
    insulated = HydraulicProgramme.reference_programme().geometry(5000., wg.DUAL_WALL).string[0].pipe.hydraulic_joint
    assert insulated.kind == 'insulated' and insulated.resolved('v1.8.0').transition == 'abrupt'


def test_reference_programme_tools_by_physics():
    new = HydraulicProgramme.reference_programme(physics='v1.8.0').geometry(5000., wg.CONVENTIONAL)
    pulser = next(s for s in new.string if s.tools)
    assert pulser.tool_loss is None and pulser.tools[0].tool_class == 'mwd_pulser' and pulser.tools[0].collar_in == 6.75
    assert pulser.tools[0].basis == 'total_internal' and pulser.tools[0].span_segments == 2
    old = HydraulicProgramme.reference_programme(physics='v1.7.0').geometry(5000., wg.CONVENTIONAL)
    assert not any(s.tools for s in old.string) and sum(s.tool_loss is not None for s in old.string) == 1


def test_no_yield_conversion_and_precedence():
    mud = fluids.Mud(1200., pv_ref=20e-3, yield_point=10*fluids.LBF_100FT2)
    converted = fluids.with_default_rheology(mud)
    assert mud.rheology is None and converted is not mud
    theta600, theta300 = 2*20+10, 20+10
    assert converted.rheology.tau0 == 0.
    assert converted.rheology.n == pytest.approx(math.log(theta600/theta300)/math.log(2))
    assert converted.rheology.K == pytest.approx(theta300*fluids.DIAL_PA/511.**converted.rheology.n)
    mud.rheology = fluids.HerschelBulkley(1., .7, .2)
    assert fluids.with_default_rheology(mud) is mud
    water = fluids.water()
    assert fluids.with_default_rheology(water) is water and fluids.with_default_rheology(WATER) is WATER
    assert fluids.with_default_rheology(None) is None


def harness():
    import importlib.util
    if not (ROOT/'validation/model-development/entry-13/predict.py').exists():
        pytest.skip('needs the source checkout')
    import sys
    entry = str(ROOT/'validation/model-development/entry-13')
    sys.path.insert(0, entry)
    try:
        spec = importlib.util.spec_from_file_location('entry13_predict_v180', Path(entry)/'predict.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(entry)
    return module


def test_conversion_reproduces_the_harness_values_for_every_sample():
    calc = harness().diagnosis.Calculation()
    wells = set()
    for sample in calc.plan['samples']:
        fluid, _, _ = calc.fluid(sample)
        expected = fluid.rheology
        fluid.rheology = None
        actual = fluids.with_default_rheology(fluid).rheology
        assert (actual.tau0, actual.rise) == (expected.tau0, expected.rise)
        # The harness converts YP to Pa with a rounded constant; the conversion back differs by 6e-6 of YP.
        assert actual.n == pytest.approx(expected.n, rel=1e-6) and actual.K == pytest.approx(expected.K, rel=1e-6)
        wells.add(sample['well'])
    assert wells == {'16A', '16B'}


def test_joints_resolve_as_entry_13_for_both_forge_wells():
    predict = harness()
    calc = predict.diagnosis.Calculation()
    checked = {}
    for sample in calc.plan['samples']:
        base = calc.score.geometry(sample, calc.plan, 'current')
        tapered = predict.apply_geometry(base, sample['well'], 'tapered_primary')
        installed = predict.apply_geometry(base, sample['well'], 'installed_primary')
        for chosen, source in zip(tapered.string, installed.string):
            joint, plain = chosen.pipe.hydraulic_joint, source.pipe.hydraulic_joint
            if joint is None:
                continue
            # The installed joints, with the transition left to the default, resolve to entry 13's.
            default = replace(plain, transition=None).resolved('v1.8.0')
            assert (default.transition, default.taper_angle_deg) == (joint.resolved('v1.8.0').transition, joint.resolved('v1.8.0').taper_angle_deg), (sample['id'], chosen.pipe.name)
            checked.setdefault((sample['well'], joint.kind), set()).add(joint.resolved('v1.8.0').transition)
    assert checked['16A', 'ordinary'] == {'tapered'} and checked['16B', 'ordinary'] == {'tapered'}
    assert checked['16A', 'heavy-weight'] == {'abrupt'} and checked['16B', 'heavy-weight'] == {'abrupt'}
    assert checked['16B', 'insulated'] == {'abrupt'}


def test_tool_table_is_complete_and_sourced():
    rows = tool_losses.source_rows()
    assert rows and all(r['document'] and r['url'] and r['printed'] for r in rows)
    assert {r['tool_class'] for r in rows if r['used'] == 'yes'} == {'mwd_pulser', 'rotary_steerable'}
    assert all(r['used'] == 'no' for r in rows if r['tool_class'] == 'mud_motor')
    assert set(tool_losses.defaults()) == {(c, b) for c in tool_losses.TOOL_CLASSES for b in tool_losses.BANDS}


def test_derived_table_is_current():
    spec_path = ROOT/'tools/build_tool_losses.py'
    if not spec_path.exists():
        pytest.skip('needs the source checkout')
    import importlib.util
    spec = importlib.util.spec_from_file_location('build_tool_losses', spec_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with open(module.OUTPUT, encoding='utf-8', newline='') as stream:
        saved = list(csv.DictReader(stream))
    assert saved == [{k: str(v) for k, v in row.items()} for row in module.rows()]


def test_rule_on_a_worked_class():
    d = tool_losses.defaults()['rotary_steerable', 6.75]
    orbit, aps = 8.34*600**2/56000, 130.
    assert d.flow_ref_gpm == 600. and d.dp_ref_psi == pytest.approx((orbit+aps)/2)
    assert (d.low_psi, d.high_psi) == (pytest.approx(orbit), 130.) and d.exponent == 2.
    telepacer = next(r for r in tool_losses.source_rows() if r['model'] == 'TelePacer 6 3/4')
    value, exponent = tool_losses._converted(telepacer, 600.)
    assert exponent == pytest.approx(math.log(125/45)/math.log(750/400))
    assert value == pytest.approx(45*(600/400)**exponent)


def test_size_bands_are_nearest():
    assert tool_losses.band_of(6.5) == 6.75 and tool_losses.band_of(9.) == 9.5
    assert tool_losses.band_of(8.25) == 8. and tool_losses.band_of(5.25) == 4.75
    with pytest.raises(ValueError):
        tool_losses.band_of(0.)


def test_tool_scaling_and_user_figure():
    tool = hl.DownholeTool('mwd_pulser', 6.75, 100*hl.PSI, 400*hl.GPM, 8.34*hl.PPG, 1.5).resolved('v1.8.0')
    assert tool.pressure(2*8.34*hl.PPG, 800*hl.GPM) == pytest.approx(100*hl.PSI*2*2**1.5)
    default = tool_losses.default_for('mwd_pulser', 6.75)
    named = hl.DownholeTool('mwd_pulser', 6.75).resolved('v1.8.0')
    assert named.pressure(8.34*hl.PPG, 600*hl.GPM) == pytest.approx(default.dp_ref_psi*hl.PSI)
    assert hl.DownholeTool('mwd_pulser', 6.75).resolved('v1.7.0') is None
    supplied = hl.DownholeTool('mwd_pulser', 6.75, 1e5, .02, 1000.)
    assert supplied.resolved('v1.7.0').dp_ref == 1e5
    with pytest.raises(ValueError):
        hl.DownholeTool('mwd_pulser', 6.75, 1e5)
    with pytest.raises(ValueError):
        hl.DownholeTool('bit', 6.75)


def test_tool_pressure_and_heat_enter_at_the_tools_depth():
    tool = hl.DownholeTool('mwd_pulser', 6.75)
    g, bare = well([tool]), well()
    a = m1.hydraulics(20., g, fluid=WATER)
    b = m1.hydraulics(20., bare, fluid=WATER)
    expected = tool.resolved('v1.8.0').pressure(1000., .02)
    assert a['spp']-b['spp'] == pytest.approx(float(expected))
    assert a['terms']['bore']['tool'] == pytest.approx(float(expected), rel=1e-6)
    assert 'tool_allowance_generic' in a['flags']
    model = hl.LossModel(g, friction='colebrook', physics='v1.8.0')
    grad = model.gradients(np.array([500., 950.]), np.array([40., 40.]), np.array([2e7, 2e7]), 20., WATER, blend=False)
    assert grad['tool'][0] == 0. and grad['tool'][1] > 0.


def test_missing_class_is_zero_with_a_warning():
    a = m1.hydraulics(20., well([hl.DownholeTool('filter_sub', 6.75)]), fluid=WATER)
    b = m1.hydraulics(20., well(), fluid=WATER)
    assert a['spp'] == b['spp']
    assert 'tool_default_zero_no_source:filter_sub:6.75' in a['flags']
    r = borethm.circulating_temperatures(m_dot=20., geometry=well([hl.DownholeTool('float_sub', 6.75)]), fluid=WATER, target_rock_T=100.)
    assert r['tool_warnings'] == ['tool_default_zero_no_source:float_sub:6.75']
    assert 'tool_default_single_source:mwd_pulser:9.5' in m1.hydraulics(20., well([hl.DownholeTool('mwd_pulser', 9.5)]), fluid=WATER)['flags']


def motor(differential=0.):
    return hl.DownholeTool('mud_motor', 6.75, 300*hl.PSI, 600*hl.GPM, 8.34*hl.PPG, differential=differential)


def test_motor_off_bottom_is_the_no_load_drop():
    a = m1.hydraulics(20., well([motor()]), fluid=WATER)
    b = m1.hydraulics(20., well(), fluid=WATER)
    assert a['spp']-b['spp'] == pytest.approx(float(motor().resolved('v1.8.0').pressure(1000., .02)))
    default = m1.hydraulics(20., well([hl.DownholeTool('mud_motor', 6.75)]), fluid=WATER)
    assert default['spp'] == b['spp'] and 'tool_default_zero_no_source:mud_motor:6.75' in default['flags']


def test_motor_on_bottom_heat_is_the_sum_times_flow():
    differential = 500*hl.PSI
    on = well([motor(differential)])
    a = m1.hydraulics(20., on, fluid=WATER)
    b = m1.hydraulics(20., well([motor()]), fluid=WATER)
    assert a['spp']-b['spp'] == pytest.approx(differential)
    r = m1.solve(m_dot=20., geometry=on, fluid=WATER, target_rock_T=100., friction_heat=True, Q_face=0., verbose=False)
    terms = r['energy_check']['assigned_terms_W']['bore']['tool']
    noload = float(motor().resolved('v1.8.0').pressure(1000., .02))
    assert terms == pytest.approx((noload+differential)*.02, rel=1e-6)
    assert r['energy_check']['passed']


def test_motor_under_v170_uses_only_the_previous_values():
    default = hl.DownholeTool('mud_motor', 6.75, differential=500*hl.PSI)
    assert default.resolved('v1.7.0') is None
    a = m1.hydraulics(20., well([default]), fluid=WATER, physics='v1.7.0')
    b = m1.hydraulics(20., well(), fluid=WATER, physics='v1.7.0')
    assert a['spp'] == b['spp']
    assert motor(500*hl.PSI).resolved('v1.7.0').differential == 0.


def test_site_file_programme_declares_physics_and_tools():
    programme = programme_from_dict(dict(physics='v1.7.0', friction='colebrook',
        bha_tools=[dict(tool_class='rotary_steerable', collar_in=6.75), dict(tool_class='mwd_pulser', collar_in=6.75,
                   dp_ref_psi=100., flow_ref_gpm=400., density_ref_ppg=8.34, exponent=1.8)]))
    assert programme.physics == 'v1.7.0' and programme.friction == 'colebrook'
    assert programme.bha_tools[1].dp_ref == pytest.approx(100*hl.PSI) and programme.bha_tools[1].exponent == 1.8
    custom = programme_from_dict(dict(surface=dict(enabled=False), segments=[dict(length=100., bore_diameter=.1, outer_diameter=.12,
        tools=[dict(tool_class='mud_motor', collar_in=6.75, differential_psi=300.)])]))
    assert custom.segments[0].tools[0].differential == pytest.approx(300*hl.PSI)
    with pytest.raises(ValueError):
        programme_from_dict(dict(physics='v1.0'))
    with pytest.raises(ValueError):
        programme_from_dict(dict(bha_tools=[dict(tool_class='mwd_pulser', collar_in=6.75, unknown=1)]))


def test_public_interface_additions():
    assert 'HerschelBulkley' in borethm.__all__ and 'DownholeTool' in borethm.__all__
    assert borethm.HerschelBulkley is fluids.HerschelBulkley
    for function in (borethm.circulating_temperatures, borethm.hydraulics, borethm.evaluate):
        assert 'physics' in inspect.signature(function).parameters
