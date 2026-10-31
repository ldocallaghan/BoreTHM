"""Pipe friction choices checked against independent pressure and heat balances."""
import math

import numpy as np
import pytest

from borethm import fluids, hydraulic_losses as hl, model1_coupled as m1
from borethm import well_geometry as wg


@pytest.mark.parametrize('roughness_ratio', [0., .001])
def test_colebrook_against_tabulated_hand_values(roughness_ratio):
    # Re = 100000; roots of Majumdar (2020), p13, equation 13a.
    expected = .0179897731 if roughness_ratio == 0 else .0221745359
    assert fluids.colebrook(100000., roughness_ratio) == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize('annulus', [False, True])
def test_bingham_option_changes_only_turbulent_factor(annulus):
    rho, mu, tau, diameter = 1000., .001, .01, .1
    velocity = np.array([.0001, 1.])
    gradient, re = fluids.bingham_gradient(rho, mu, tau, velocity, diameter, annulus,
                                          'colebrook', .0001)
    original, original_re = fluids.bingham_gradient(rho, mu, tau, velocity, diameter, annulus)
    assert np.array_equal(re, original_re)
    assert re[0] < 2100 < re[1]
    assert gradient[0] == original[0]
    # Turbulent Reynolds number on PV is 100000, epsilon/D is .001.
    assert gradient[1] == pytest.approx(.0221745359*rho/(2*diameter), abs=1e-5)


@pytest.mark.parametrize('yield_point', [0., .01])
def test_joint_replacement_uses_selected_friction_at_both_bores(yield_point):
    rho, mu, q = 1000., .001, .01
    body, joint = .1, .08
    area = math.pi*body**2/4
    small = math.pi*joint**2/4
    # Independent bisection of the implicit Colebrook equation for this hand case.
    def gradient(d):
        v = q/(math.pi*d*d/4)
        re = rho*v*d/mu
        lo, hi = .005, .1
        for _ in range(60):
            f = (lo+hi)/2
            residual = 1/math.sqrt(f)+2*math.log10(.0001/(3.7*d)+2.51/(re*math.sqrt(f)))
            if residual > 0:
                lo = f
            else:
                hi = f
        return (lo+hi)/2*rho*v*v/(2*d)
    replacement, local = hl.joint_increment(rho, mu, yield_point, q*rho, area, body,
        small, joint, .7, friction='colebrook', roughness=.0001)
    ratio = small/area
    expected_local = ((1-ratio)**2+.5*(1-ratio)**.75)*rho*(q/small)**2/2
    assert replacement == pytest.approx(.7*(gradient(joint)-gradient(body)), abs=.01)
    assert local == pytest.approx(expected_local, abs=.01)


def test_pressure_inherits_friction_and_matches_dissipated_power():
    fluid = dict(rho=1000., cp=4000., mu=.001, k=.6)
    pipe = wg.uniform_wall(45., .04, .05)
    g = wg.WellGeometry.single(800., pipe, r_hole=.11)
    r = m1.solve(m_dot=20., geometry=g, fluid=fluid, friction_heat=True,
                 friction='colebrook', roughness=45.72e-6, verbose=False)
    assert r['success']
    inherited = m1.hydraulics(20., g, result=r, fluid=fluid)
    explicit = m1.hydraulics(20., g, result=r, fluid=fluid,
                             friction='colebrook', roughness=45.72e-6)
    assert inherited['spp'] == explicit['spp']
    power = sum(sum(side.values()) for side in r['energy_check']['assigned_terms_W'].values())
    assert power == pytest.approx((inherited['dp_string']+inherited['dp_annulus'])*.02, abs=.001*power)
    assert r['energy_check']['passed']
    blasius = m1.hydraulics(20., g, result=r, fluid=fluid, friction='blasius', roughness=0.)
    assert inherited['dp_string'] > blasius['dp_string']


def test_herschel_bulkley_annulus_is_unaffected_by_pipe_friction_choice():
    args = (1000., .001, 1., 20., .02, .1)
    a = hl.passage_gradient(*args, annulus=True, regime='herschel-bulkley')
    b = hl.passage_gradient(*args, annulus=True, regime='herschel-bulkley',
                             friction='colebrook', roughness=45.72e-6)
    assert a == b


@pytest.mark.parametrize('options', [dict(friction='unknown'), dict(roughness=-1.),
                                    dict(roughness=float('nan')), dict(roughness=.001)])
def test_invalid_friction_inputs_are_rejected(options):
    with pytest.raises(ValueError):
        m1.hydraulics(20., wg.WellGeometry.single(100., wg.CONVENTIONAL), **options)


def test_legacy_heat_rejects_new_friction_option():
    with pytest.raises(ValueError, match='v1.5.0 heat'):
        m1.solve(geometry=wg.WellGeometry.single(100., wg.CONVENTIONAL),
                 hydraulics_model='v1.5.0', friction='colebrook', verbose=False)
