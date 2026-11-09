"""Operations on Model 1 solves and full evaluations.

With no operations and with Operations(), the evaluation reproduces the
v1.8.0 release result exactly (tests/make_golden_reproduction.py records it).
The result additions agree with the existing keys, and stated values change
what they state on real circulations.
"""
from dataclasses import replace
import json

import pytest

from borethm import model1_coupled as m1
from borethm import physics
from borethm import site_evaluation as se
from borethm import well_geometry as wg
from borethm.operations import Operations
from borethm.programme import HydraulicProgramme
from make_golden_reproduction import ADDED_KEYS, PHYSICS, SITES, path, recorded

pytestmark = [pytest.mark.slow, pytest.mark.default_physics]
CASES = [(key, p) for key in SITES for p in PHYSICS]


@pytest.fixture(scope='module')
def results():
    """result_dict for a site and physics, with no operations or Operations(),
    evaluated once per module."""
    cache = {}

    def get(key, physics_name, mode='none'):
        if (key, physics_name, mode) not in cache:
            operations = None if mode == 'none' else Operations()
            cache[key, physics_name, mode] = se.result_dict(
                se.evaluate(se.find_site(key), physics=physics_name, operations=operations))
        return cache[key, physics_name, mode]

    return get


def canonical(data):
    return json.dumps(data, sort_keys=True)


@pytest.mark.parametrize('mode', ['none', 'empty'])
@pytest.mark.parametrize('key,physics_name', CASES)
def test_results_reproduce_the_release_exactly(results, key, physics_name, mode):
    golden = json.loads(path(key, physics_name).read_text(encoding='utf-8'))
    assert canonical(recorded(results(key, physics_name, mode))) == canonical(golden)


@pytest.mark.parametrize('key,physics_name', CASES)
def test_empty_operations_give_the_same_additions(results, key, physics_name):
    none, empty = results(key, physics_name), results(key, physics_name, 'empty')
    for name in ADDED_KEYS:
        assert canonical(none[name]) == canonical(empty[name])
    assert not any(entry['stated'] for entry in none['operations'].values())


@pytest.mark.parametrize('key,physics_name', CASES)
def test_additions_agree_with_the_existing_keys(results, key, physics_name):
    data = results(key, physics_name)
    windows, profile, water = data['windows'], data['window_profile'], data['programme']['drilling_simulated_rho_surface']
    assert set(profile['depths_m']) >= set(windows['depths'])
    for name in ('drilling_fluid', 'trip_fluid'):
        w, p = windows[name], profile[name]
        lows = [v for v in p['lo_kg_m3'] if v is not None]
        highs = [v for v in p['hi_kg_m3'] if v is not None]
        assert max([water] + lows) == w['lo']
        assert min(highs) == (float('inf') if w['hi'] == 'inf' else w['hi'])
        for side in ('lo', 'hi'):
            by = w[side + '_by']
            if by['md'] is not None:
                i = profile['depths_m'].index(by['md'])
                assert p[side + '_kg_m3'][i] == w[side]
                assert (p[side + '_by'][i]['state'], p[side + '_by'][i]['case']) == (by['state'], by['case'])
        width = data['window_width'][name]
        assert (width['lo_kg_m3'], width['hi_kg_m3'], width['open']) == (w['lo'], w['hi'], w['open'])
        if w['hi'] != 'inf':
            assert width['width_kg_m3'] == w['hi'] - w['lo']
    for state, cases in profile['states'].items():
        for case in cases.values():
            assert set(case['lo_mechanism']) <= {None, *se.LOWER_MECHANISMS}
            assert set(case['hi_mechanism']) <= {None, se.UPPER_MECHANISM}

    pumps, c = data['pump_check'], data['components']['pumps']
    assert pumps['limit_Pa'] == m1.PUMP_LIMIT and pumps['pumps'] == se.RIG_PUMPS
    assert pumps['drilling']['spp_Pa'] == data['programme']['spp_Pa'] == c['spp']
    assert pumps['drilling']['margin_Pa'] == m1.PUMP_LIMIT - c['spp']
    assert c['ok'] == (pumps['drilling']['ok'] and pumps['trip']['ok'])
    assert c['within_rig'] == (pumps['drilling']['within_rig'] and pumps['trip']['within_rig'])
    if pumps['trip']['separate_circulation']:
        assert pumps['trip']['spp_Pa'] == c['trip_spp']

    tools, check = data['tools'], data['tool_check']
    assert check['limit_C'] == tools['limit'] == data['operations']['tool_limit_C']['value']
    assert (check['drilling']['peak_C'], check['drilling']['ok']) == (tools['drilling']['T'], tools['drilling']['ok'])
    assert (check['connection']['peak_C'], check['connection']['ok']) == (tools['connection']['peak'], tools['connection']['ok'])
    assert (check['run_in_staged']['peak_C'], check['run_in_staged']['ok']) == (
        tools['trip_in']['staged']['peak'], tools['trip_in']['ok'])
    assert check['run_in_unstaged']['peak_C'] == tools['trip_in']['unstaged']['peak']
    assert check['run_in_unstaged']['ok'] == (tools['trip_in']['unstaged']['peak'] < tools['limit'])

    coating, co = data['coating_check'], tools['coating']
    assert coating['rating_C'] == co['rating']
    assert [coating[s]['max_C'] for s in ('circulating', 'connection', 'run_in')] == [
        co['circulating_max'], co['connection']['max'], co['trip_in']['max']]
    over = not all(coating[s]['ok'] for s in ('circulating', 'connection', 'run_in'))
    assert (co['status'] == 'INDETERMINATE') == over

    ops, programme = data['operations'], data['programme']
    assert ops['mass_flow_kg_s']['value'] == programme['mass_flow_kg_s']
    if programme['flow_unit'] == 'L/s':
        assert ops['volume_flow_L_s']['value'] == programme['flow']
    else:
        assert ops['mass_flow_kg_s']['value'] == programme['flow']
        assert ops['volume_flow_L_s']['value'] == programme['mass_flow_kg_s'] * 1000.0 / water
    assert not ops['mass_flow_kg_s']['stated'] and not ops['volume_flow_L_s']['stated']
    for state in ('drilling', 'trip'):
        p = data['pump_check'][state]
        assert p['flow_L_s'] == p['flow_gpm'] * 3.785411784 / 60.0
        assert p['rig_capacity_L_s'] == p['rig_capacity_gpm'] * 3.785411784 / 60.0
    tool_sets = {k: v['sets_status'] for k, v in data['tool_check'].items() if isinstance(v, dict)}
    assert tool_sets == {k: k != 'run_in_unstaged' for k in tool_sets}
    assert all(data['coating_check'][k]['sets_status'] for k in ('circulating', 'connection', 'run_in'))
    assert ops['trip_hours']['value'] == data['cycle']['trip_h']
    assert ops['rop_m_h']['value'] == programme['rop_m_h']
    assert ops['drilling_fluid_kg_m3']['value'] == programme['drilling_simulated_rho_surface']
    assert ops['trip_fluid_kg_m3']['value'] == programme['trip_simulated_rho_surface']
    assert ops['pipes']['value'][0] == programme['pipe'] or programme['pipe'] in ops['pipes']['value']


# ------------------------------------------------------------ stated values on a real circulation
@pytest.fixture(scope='module')
def circulation():
    """Newberry's reference well circulated with water at 30 kg/s, its rock
    exposed at 10 m/h, under physics v1.7.0."""
    site = replace(se.find_site('newberry'), programme=HydraulicProgramme.reference_programme())
    z, geotherm = site.target(), site.temperature()
    with physics.using('v1.7.0'):
        run = se.circulate(site, z, geotherm, wg.TK_DRAKON, 30.0, m1.exposure_from_rop(z, 10.0, 0.0),
                           P_surface=m1.P_SURF)
    out = dict(z=z, T_rock=float(geotherm(z)), m1=run, drill={'ROP': 10.0 / 3600.0},
               circ=dict(pipe=wg.TK_DRAKON, m_dot=30, rop=10.0 / 3600.0))
    return site, out


def gates(circulation, **fields):
    site, out = circulation
    site = replace(site, operations=Operations(**fields))
    out = dict(out, m1=dict(out['m1']), site=site)
    out['m1'].pop('trip_columns', None)
    out['m1'].pop('pause_columns', None)
    return se.tool_gates(site, out)


def test_a_tool_limit_below_the_bit_temperature_fails_the_tool(circulation):
    default = gates(circulation)
    assert default['tool'] == 'PASS' and default['limit'] == 200.0
    limit = default['drilling']['T'] - 1.0
    stated = gates(circulation, tool_limit_C=limit)
    assert stated['limit'] == limit and not stated['drilling']['ok']
    assert stated['tool'] == f"FAIL: {default['drilling']['T']:.0f} C at the bit while drilling"


def test_a_stated_connection_is_checked_without_a_search(circulation):
    long = gates(circulation, precirculation_min=0.5, connection_p90_min=60.0)
    assert long['connection']['practice'] == dict(precirc_min=0.5, off_min=60.0)
    peak = long['connection']['peak']
    drilling = long['drilling']['T']
    assert peak > drilling + 2.0
    limit = 0.5 * (peak + drilling)
    failed = gates(circulation, precirculation_min=0.5, connection_p90_min=60.0, tool_limit_C=limit)
    assert failed['connection']['schedule'] is None and failed['connection']['peak'] == peak
    assert failed['tool'] == f'FAIL: {peak:.0f} C through the stated connection'
    searched = gates(circulation, connection_median_min=60.0, tool_limit_C=limit)
    assert searched['connection']['practice']['off_min'] == pytest.approx(6.33)


def test_a_stated_staging_is_the_schedule_reported(circulation):
    stated = gates(circulation, stage_spacing_m=300.0, stage_minutes=10.0)
    staged = stated['trip_in']['staged']
    assert (staged['spacing_m'], staged['minutes']) == (300.0, 10.0)
    assert (stated['trip_in']['schedule']['spacing_m'], stated['trip_in']['schedule']['minutes']) == (300.0, 10.0)
    limit = 0.5 * (staged['peak'] + max(stated['drilling']['T'], stated['connection']['peak']))
    failed = gates(circulation, stage_spacing_m=300.0, stage_minutes=10.0, tool_limit_C=limit)
    assert failed['trip_in']['schedule'] is None
    assert failed['tool'] == f"FAIL: {staged['peak']:.0f} C running in with the stated staging"


def test_a_longer_trip_heats_the_tool_running_in(circulation):
    assert (gates(circulation, trip_hours=60.0)['trip_in']['unstaged']['peak']
            > gates(circulation)['trip_in']['unstaged']['peak'] + 1.0)
    assert (gates(circulation, trip_scale=3.0)['trip_in']['unstaged']['peak']
            > gates(circulation)['trip_in']['unstaged']['peak'] + 1.0)


def test_stated_coating_ratings_replace_the_table(circulation):
    default = gates(circulation)['coating']
    assert (default['rating'], default['status']) == (204.0, 'within rating')
    low = gates(circulation, coating_ratings_C={'TK-Drakon coated': default['trip_in']['max'] - 1.0})['coating']
    assert low['status'] == 'INDETERMINATE'
    assert gates(circulation, coating_ratings_C={})['coating']['status'] == 'no rating'


def test_stated_pump_limit_and_cleaning_velocity_set_the_flags(circulation):
    site, out = circulation
    hyd = out['m1']['hyd']
    assert not hyd['over_pump_limit'] and hyd['cleans_hole']
    stated = replace(site, operations=Operations(pump_pressure_limit_Pa=0.9 * hyd['spp'],
                                                 min_annular_velocity_m_s=1.1 * hyd['v_ann_min']))
    with physics.using('v1.7.0'):
        run = se.circulate(stated, out['z'], site.temperature(), wg.TK_DRAKON, 30.0,
                           m1.exposure_from_rop(out['z'], 10.0, 0.0), P_surface=m1.P_SURF)
    assert run['hyd']['spp'] == hyd['spp']
    assert run['hyd']['over_pump_limit'] and not run['hyd']['cleans_hole']


# ------------------------------------------------------------ stated values on full evaluations
def evaluate(operations):
    return se.result_dict(se.evaluate(se.find_site('newberry'), physics='v1.7.0', operations=operations))


def test_a_stated_flow_over_the_pump_limit_is_reported_and_kept():
    data = evaluate(Operations(mass_flow_kg_s=20.0, pump_pressure_limit_Pa=1.5e6,
                               sources={'pump_pressure_limit_Pa': ('assumed', 'test rig')}))
    assert data['programme']['flow'] == 20.0
    assert data['status']['label'] == 'NO-GO'
    assert 'the standpipe pressure exceeds the pump limit' in data['status']['reasons']
    assert data['pump_check']['limit_Pa'] == 1.5e6 and not data['pump_check']['drilling']['ok']
    assert data['programme']['conflict'].startswith('at the stated flow of 20 kg/s')
    assert data['operations']['mass_flow_kg_s']['stated'] and not data['operations']['volume_flow_L_s']['stated']
    assert data['operations']['pump_pressure_limit_Pa']['stated']
    assert data['operations']['pump_pressure_limit_Pa']['basis'] == 'assumed'
    assert 'operations.mass_flow_kg_s: no source is given' in data['input_warnings']
    if data['status']['reasons'][0] == 'the standpipe pressure exceeds the pump limit':
        assert data['reading']['controlling_constraint'].endswith(
            'Stated operations used in this check: pump pressure limit 1.5 MPa; mass flow 20 kg/s.')


def test_stated_operations_are_the_ones_evaluated():
    data = evaluate(Operations(volume_flow_L_s=25.0, rop_m_h=8.0, trip_hours=24.0, stage_spacing_m=300.0,
                               stage_minutes=10.0, rig_pumps=1, tool_limit_C=180.0,
                               drilling_fluid_kg_m3=1050.0))
    programme = data['programme']
    assert (programme['flow'], programme['flow_unit']) == (25.0, 'L/s')
    assert programme['rop_m_h'] == pytest.approx(8.0)
    assert programme['drilling_simulated_rho_surface'] == 1050.0
    assert data['cycle']['trip_h'] == 24.0
    staged = data['tool_check']['run_in_staged']
    assert (staged['spacing_m'], staged['minutes']) == (300.0, 10.0)
    assert data['tool_check']['limit_C'] == 180.0 and data['tools']['limit'] == 180.0
    assert data['pump_check']['pumps'] == 1
    assert all(data['operations'][name]['stated'] for name in
               ('volume_flow_L_s', 'rop_m_h', 'trip_hours', 'stage_spacing_m', 'stage_minutes', 'rig_pumps',
                'tool_limit_C', 'drilling_fluid_kg_m3'))
    assert not data['operations']['pipes']['stated']
    window = data['windows']['drilling_fluid']
    inside = window['open'] and window['lo'] <= 1050.0 <= window['hi']
    reasons = data['status']['reasons']
    if inside:
        assert not any('outside its common window' in r for r in reasons)
    else:
        assert data['status']['label'] in ('NO-GO', 'INDETERMINATE')


# ------------------------------------------------------------ stating the chosen flow
@pytest.mark.parametrize('unit', ['mass_flow_kg_s', 'volume_flow_L_s'])
def test_stating_the_chosen_water_flow_reproduces_the_result(results, unit):
    """Newberry circulates water. The chosen flow stated in either unit
    gives the default result, apart from the operations record."""
    default = results('newberry', 'v1.7.0')
    value = default['operations'][unit]['value']
    stated = se.result_dict(se.evaluate(se.find_site('newberry'), physics='v1.7.0', operations=Operations(
        **{unit: value}, sources={unit: ('assumed', 'the flow the evaluator chose')})))
    assert stated['operations'][unit]['stated']
    for key in default:
        if key not in ('operations', 'versions'):
            assert canonical(stated[key]) == canonical(default[key]), key


@pytest.mark.parametrize('unit', ['mass_flow_kg_s', 'volume_flow_L_s'])
def test_stating_the_chosen_mud_flow_reproduces_the_circulation(unit):
    """With a weighted fluid, the flow the search chooses, stated in either
    unit, is solved with the same mass flow to the last bit."""
    from borethm import fluids
    site = replace(se.find_site('newberry'), programme=HydraulicProgramme.reference_programme())
    z, geotherm = site.target(), site.temperature()
    mud = fluids.Mud(1150.0, conserve_mass=True)
    exposure = m1.exposure_from_rop(z, 10.0, 0.0)
    with physics.using('v1.7.0'):
        chosen = se.choose_circulation(site, z, geotherm, exposure, P_surface=m1.P_SURF, fluid=mud, retry=False)
        value = chosen['run']['m_dot'] if unit == 'mass_flow_kg_s' else chosen['m_dot']
        stated = se.choose_circulation(replace(site, operations=Operations(**{unit: value})), z, geotherm, exposure,
                                       P_surface=m1.P_SURF, fluid=mud, retry=False)
    assert stated['pipe'] == chosen['pipe']
    assert stated['run']['m_dot'] == chosen['run']['m_dot']
    for key in ('Td', 'Tu', 'z'):
        assert (stated['run'][key] == chosen['run'][key]).all(), key
    assert stated['run']['hyd']['spp'] == chosen['run']['hyd']['spp']

