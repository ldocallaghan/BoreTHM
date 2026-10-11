"""C3: exposure, shoe, final stand and local refinement checks."""
from dataclasses import replace
from types import SimpleNamespace
import numpy as np
import pytest

import fluids
import pressure as pr
import site_evaluation as se
import well_geometry as wg


@pytest.fixture
def synthetic(monkeypatch):
    geometry = wg.WellGeometry([wg.StringSegment(1100., wg.CONVENTIONAL)],
                               [wg.HoleInterval(0., 100., 0.15), wg.HoleInterval(100., 1100., 0.15)])
    site = replace(se.SOULTZ, target_depth=1100., geotherm=lambda z: np.asarray(z) * 0.04 + 20.)
    run = dict(geometry=geometry, fluid=None, z=np.linspace(0., 1100., 12), Tu=np.full(12, 20.))
    case = dict(label='scenario', window=dict(Pw_lo=1000. * pr.G * 1100., Pw_hi=2000. * pr.G * 1100.))
    cycle = dict(trip_h=10., cases=dict(drilling=[case], connection=[case]))
    output = dict(z=1100., drill={'ROP': 10. / 3600.}, m1=run, cycle=cycle, coverage_corrected=True)
    monkeypatch.setattr(fluids, '_water', lambda T, P: tuple(np.full(np.broadcast(np.asarray(T), np.asarray(P)).shape, value)
                                                           for value in (1000., 4000., 0.001, 0.6)))
    monkeypatch.setattr(pr, 'column', lambda tvd, T, fluid=None, P_surface=0.: P_surface + pr.G * np.asarray(tvd) * getattr(fluid, 'rho_surface', 1000.))
    monkeypatch.setattr(pr, 'annulus_friction', lambda *args: 0.)
    monkeypatch.setattr(se, 'trip_temperatures', lambda *args: (run['z'], run['Tu']))
    monkeypatch.setattr(se, '_ref_depth', lambda *args: 0.)
    monkeypatch.setattr(se, '_static_node', lambda *args: (1000., 10.))
    monkeypatch.setattr(se, '_bottom_conditions', lambda *args: dict(r_wall=0.15, r_string=0.05, Tu=20., h=100., bu_h=1.))
    monkeypatch.setattr(se.wall_thermal, 'run', lambda *args, **kwargs: SimpleNamespace(r=np.array([0.15, 0.25]), fields=[np.array([20., 20.])]))
    return site, output


@pytest.mark.parametrize('binding', [100., 300., 1100.])
def test_exposure_can_bind_at_the_shoe_shallow_depth_or_target(synthetic, monkeypatch, binding):
    site, output = synthetic
    def inputs(site, depth, rock, T_wall=None, **kwargs):
        required = 1500. if abs(depth - binding) < 1e-6 and T_wall == rock else 1000.
        cases = [dict(label='scenario', window=dict(Pw_lo=required * pr.G * depth, Pw_hi=2000. * pr.G * depth))]
        return cases[0], cases
    monkeypatch.setattr(se, 'stability_inputs', inputs)
    result = se.common_windows(site, output)
    assert result['drilling_fluid']['lo'] == pytest.approx(1500.)
    assert result['drilling_fluid']['lo_by']['md'] == binding
    assert result['refinement']['converged']
    assert [level['spacing_m'] for level in result['refinement']['levels']] == [50., 25.]


def test_youngest_rock_can_control_the_trip(synthetic, monkeypatch):
    site, output = synthetic
    def inputs(site, depth, rock, ecd_SG=0., **kwargs):
        required = 1400. if depth == 1100. and ecd_SG else 1000.
        cases = [dict(label='scenario', window=dict(Pw_lo=required * pr.G * depth, Pw_hi=2000. * pr.G * depth))]
        return cases[0], cases
    monkeypatch.setattr(se, 'stability_inputs', inputs)
    result = se.common_windows(site, output)
    assert result['trip_fluid']['lo_by']['md'] == 1100.
    assert result['trip_fluid']['lo'] == pytest.approx(1420.)
    assert result['refinement']['converged']


def test_an_unresolved_narrow_extremum_is_reported(synthetic, monkeypatch):
    site, output = synthetic
    def inputs(site, depth, rock, T_wall=None, **kwargs):
        required = max(1000., 1500. - 10. * abs(depth - 325.)) if T_wall == rock else 1000.
        cases = [dict(label='scenario', window=dict(Pw_lo=required * pr.G * depth, Pw_hi=2000. * pr.G * depth))]
        return cases[0], cases
    monkeypatch.setattr(se, 'stability_inputs', inputs)
    assert not se.common_windows(site, output)['refinement']['converged']


def test_failure_timing_lever_applies_at_a_shallow_exposure(synthetic, monkeypatch):
    site, output = synthetic
    def inputs(site, depth, rock, T_wall=None, **kwargs):
        required = 1500. if depth == 300. and T_wall == rock else 1000.
        cases = [dict(label='scenario', window=dict(Pw_lo=required * pr.G * depth,
                                                   Pw_hi=2000. * pr.G * depth))]
        return cases[0], cases
    monkeypatch.setattr(se, 'stability_inputs', inputs)
    assert se.common_windows(site, output)['drilling_fluid']['lo'] == pytest.approx(1500.)
    output['form_h'] = 1.
    assert se.common_windows(site, output)['drilling_fluid']['lo'] == pytest.approx(1000.)
