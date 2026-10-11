"""C6 controller and minimum-intervention checks against independent oracles."""
import numpy as np
import pytest

import levers as lv
import pressure as pr


def constant_fluid(rho):
    return dict(rho=rho, cp=4000., mu=1.e-3, k=0.6)


def test_mpd_replaces_friction_and_thermal_density_loss():
    depths = np.linspace(0., 10000., 101)
    temperatures = (depths, np.full_like(depths, 20.))
    target = 120.e6
    drilling = lv.controlled_column(target, temperatures, constant_fluid(1100.), 5.e6)
    connection = lv.controlled_column(target, temperatures, constant_fluid(1100.))
    hot_trip = lv.controlled_column(target, temperatures, constant_fluid(1000.))
    assert drilling['backpressure'] == pytest.approx(target - 1100. * pr.G * 10000. - 5.e6)
    assert connection['backpressure'] - drilling['backpressure'] == pytest.approx(5.e6)
    assert hot_trip['backpressure'] - connection['backpressure'] == pytest.approx(100. * pr.G * 10000.)
    for result in (drilling, connection, hot_trip):
        assert abs(result['error_Pa']) < 1.


def test_mpd_cannot_remove_pressure_from_an_already_heavy_column():
    depth = np.array([0., 10000.])
    result = lv.controlled_column(100.e6, (depth, np.array([20., 20.])), constant_fluid(1200.))
    assert result['backpressure'] == 0.
    assert not result['controllable']
    assert result['error_Pa'] > 0.


def test_density_constraints_keep_both_branches_before_hardware_intersection():
    grid = [1000., 1100., 1200., 1300., 1400.]
    assert lv.feasible_intervals(grid, [1., -1., -2., -1., 1.]) == [(1000., 1050.), (1350., 1400.)]
    assert lv.feasible_intervals(grid, [-1., 1., 2., 1., -1.]) == [(1050., 1350.)]


def test_mpd_trip_fracture_check_covers_hot_shallow_pressure():
    depths = np.array([0., 1000., 10000.])
    cold = lv.controlled_column(120.e6, (depths, depths * 0. + 20.), constant_fluid(1100.))
    hot = lv.controlled_column(120.e6, (depths, depths * 0. + 300.), constant_fluid(1000.))
    maximum = lv.trip_upper_pressure(hot['pressure'], cold['pressure'])
    assert maximum[1] == pytest.approx(120.e6 - 1000. * pr.G * 9000.)
    assert maximum[1] > cold['pressure'][1]
    assert maximum[-1] == pytest.approx(120.e6)


def test_bisection_retains_a_failure_and_pass_and_refines_the_tolerance():
    def oracle(value):
        return dict(assessment={'reopened': value >= 0.37, 'failures': []}, evidence=str(value))
    first = lv.bisect_minimum(oracle, (0., oracle(0.)), (1., oracle(1.)), 0.01)
    assert first['failing']['intervention'] < 0.37 <= first['passing']['intervention']
    assert first['passing']['intervention'] - first['failing']['intervention'] <= 0.01
    lower, upper = first['failing']['intervention'], first['passing']['intervention']
    second = lv.bisect_minimum(oracle, (lower, oracle(lower)), (upper, oracle(upper)), 0.005)
    assert second['failing']['intervention'] < 0.37 <= second['passing']['intervention']
    assert abs(second['passing']['intervention'] - first['passing']['intervention']) <= 0.01


def test_numerical_failure_keeps_the_last_confirmed_bracket_unresolved():
    def oracle(value):
        return dict(assessment={'reopened': False, 'failures': ['solver']}, evidence=str(value))
    failed = dict(assessment={'reopened': False, 'failures': ['wall stability']}, evidence='base')
    passed = dict(assessment={'reopened': True, 'failures': []}, evidence='upper')
    bracket = lv.bisect_minimum(oracle, (0., failed), (1., passed), 0.01)
    assert bracket['unresolved']
    assert bracket['failing']['evidence'] == 'base'
    assert bracket['passing']['evidence'] == 'upper'


def test_coating_unknown_is_explicit_and_a_failed_rig_gate_cannot_reopen():
    components = dict(solver={'ok': True}, tool={'ok': True},
        pumps={'ok': True, 'within_rig': True}, hole_cleaning={'ok': True},
        window_refinement={'converged': True}, stability={'verdict': 'GO'},
        admissibility={'inadmissible': []}, coating={'status': 'INDETERMINATE'})
    out = dict(components=components, windows={n: {'open': True} for n in ('drilling_fluid', 'trip_fluid')},
               status={'label': 'INDETERMINATE', 'reasons': ['coating qualification']}, fluid=None, trip_fluid=None)
    import fluids
    for window in out['windows'].values():
        window.update(lo=fluids.water().rho_surface, hi=1500.)
    result = lv.gates(out)
    assert result['reopened'] and result['verdict'] == 'CONDITIONAL'
    assert result['qualification_indeterminate'] == ['coating qualification']
    components['pumps']['within_rig'] = False
    assert not lv.gates(out)['reopened']


def test_water_viscosity_endpoint_keeps_the_yield_point_separate():
    import fluids
    mud = fluids.Mud(1300., fluids.PV_REF * lv.water_pv_fraction(), fluids.YP_REF)
    T, P = np.array([80.]), np.array([10.e6])
    assert mud.props(T, P)[2] == pytest.approx(fluids._water(T, P)[2])
    assert mud.yield_point == fluids.YP_REF


def test_mpd_skin_reference_uses_connection_backpressure(monkeypatch):
    depths = np.array([0., 10000.])
    temperatures = (depths, np.array([20., 20.]))
    monkeypatch.setattr(pr, 'circulating_temperatures', lambda run: temperatures)
    run = dict(fluid=constant_fluid(1100.), backpressure=0., P_surface=100000.)
    reference = lv.MPD(120.e6).reference_run(run)
    assert reference['backpressure'] == pytest.approx(120.e6 - 1100. * pr.G * 10000.)
    assert run['backpressure'] == 0.
    assert reference['P_surface'] == run['P_surface']


def test_pair_selection_ranks_applied_margins_and_stops_after_single_success():
    from dataclasses import asdict, replace
    import lever_pairs as lp
    base = lv.base_settings('soultz')
    def record(settings, width, mpd=None):
        return dict(settings=asdict(settings), metrics=dict(solver_ok=True,
            pressure_margin_SG=dict(drilling_fluid=width, trip_fluid=width + 0.01)),
            result=dict(components=dict(window_refinement=dict(converged=True))),
            mpd=mpd, assessment=dict(reopened=False))
    baseline = record(base, -0.08)
    summaries = [dict(lever='L2', trials=[baseline, record(replace(base, shoe_m=9000.), -0.03)]),
                 dict(lever='L3', trials=[record(replace(base, pv_fraction=0.1), -0.05)]),
                 dict(lever='L1', trials=[record(replace(base, bhp_Pa=140.e6), 0.02, dict(ok=False))])]
    assert [r['lever'] for r in lp.select_pair('soultz', summaries)] == ['L2', 'L3']
    summaries[1]['trials'][0]['assessment']['reopened'] = True
    assert lp.select_pair('soultz', summaries) == []
