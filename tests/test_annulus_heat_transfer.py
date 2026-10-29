"""The annulus_model 'bingham' candidate: the Wilson-Thomas criterion, the
annulus film correlations and their use in the circulation solve."""
import numpy as np
import pytest

from borethm import fluids
from borethm import model1_coupled as m1
from borethm import well_geometry as wg


def test_wilson_thomas_branches():
    rho, D = 1000.0, 0.1
    # He > 1e5: transition velocity 25 (tau_y / rho)^0.5, independent of PV
    tau, mu = 10.0, 0.005
    assert rho * tau * D ** 2 / mu ** 2 > 1e5
    vt = 25 * np.sqrt(tau / rho)
    assert not fluids.wilson_thomas_turbulent(rho, mu, tau, vt * 0.999, D)
    assert fluids.wilson_thomas_turbulent(rho, mu, tau, vt * 1.001, D)
    # 1700 <= He <= 1e5: rho V_T D / mu = 80 He^0.4
    tau, mu = 0.5, 0.01
    he = rho * tau * D ** 2 / mu ** 2
    assert 1700 <= he <= 1e5
    vt = 80 * he ** 0.4 * mu / (rho * D)
    assert not fluids.wilson_thomas_turbulent(rho, mu, tau, vt * 0.999, D)
    assert fluids.wilson_thomas_turbulent(rho, mu, tau, vt * 1.001, D)
    # He < 1700 tends to Re 2100, which also covers no yield stress
    mu = 0.001
    for tau in (0.0, 1e-6):
        vt = 2100 * mu / (rho * D)
        assert not fluids.wilson_thomas_turbulent(rho, mu, tau, vt * 0.999, D)
        assert fluids.wilson_thomas_turbulent(rho, mu, tau, vt * 1.001, D)


def test_bingham_gradient_criteria():
    v = np.array([1.0, 1.5, 2.0, 2.5])
    args = (1080.0, 0.005, 7.18, v, 0.0952, True)
    default = fluids.bingham_gradient(*args)
    assert np.array_equal(default[0], fluids.bingham_gradient(*args, 'apparent-viscosity')[0])
    wt_grad = fluids.bingham_gradient(*args, 'wilson-thomas')[0]
    laminar = 48 * 0.005 * v / 0.0952 ** 2 + 6 * 7.18 / 0.0952
    turbulent = ~fluids.wilson_thomas_turbulent(1080.0, 0.005, 7.18, v, 0.0952)
    assert np.allclose(wt_grad[turbulent], laminar[turbulent])
    with pytest.raises(ValueError, match='regime'):
        fluids.bingham_gradient(*args, 'unknown')


def test_gnielinski_annulus_by_hand():
    Re, Pr, a = 5e4, 5.0, 0.5
    re_star = Re * ((1 + a * a) * np.log(a) + (1 - a * a)) / ((1 - a) ** 2 * np.log(a))
    f = (1.8 * np.log10(re_star) - 1.5) ** -2
    k1 = 1.07 + 900 / Re - 0.63 / (1 + 10 * Pr)
    nu = f / 8 * Re * Pr / (k1 + 12.7 * np.sqrt(f / 8) * (Pr ** (2 / 3) - 1))
    assert m1.gnielinski_annulus(Re, Pr, a, 'inner') == pytest.approx(nu * 0.75 * a ** -0.17)
    assert m1.gnielinski_annulus(Re, Pr, a, 'outer') == pytest.approx(nu * (0.9 - 0.15 * a ** 0.6))
    with pytest.raises(ValueError):
        m1.gnielinski_annulus(Re, Pr, a, 'both')


def annulus(r_out, r_wall):
    return dict(A_ann=np.array([np.pi * (r_wall ** 2 - r_out ** 2)]), Dh_ann=np.array([2 * (r_wall - r_out)]),
                r_out=np.array([r_out]), r_wall=np.array([r_wall]))


def test_laminar_and_turbulent_films():
    g = annulus(0.05555, 0.1111)             # r* = 0.5
    T, P = np.array([80.0]), np.array([2e7])
    mud = fluids.Mud(1080.0, pv_ref=0.012, yield_point=7.18, pv_ref_T=48.9)
    rho, cp, mu, k = m1.fluid_props(T, P, mud)
    # slow enough to be laminar: the tabulated values at r* = 0.5
    v = 0.5
    hi, ho = m1.annulus_films(float(v * rho[0] * g['A_ann'][0]), g, T, P, mud)
    assert hi[0] * g['Dh_ann'][0] / k[0] == pytest.approx(6.18102)
    assert ho[0] * g['Dh_ann'][0] / k[0] == pytest.approx(5.03655)
    # water at a high Reynolds number: Gnielinski on the plastic (water) viscosity
    rho, cp, mu, k = m1.fluid_props(T, P, None)
    m_dot = float(2.0 * rho[0] * g['A_ann'][0])
    hi, ho = m1.annulus_films(m_dot, g, T, P, None)
    re = m_dot * g['Dh_ann'][0] / (g['A_ann'][0] * mu[0])
    pr = cp[0] * mu[0] / k[0]
    assert re > 1e4
    assert hi[0] == pytest.approx(m1.gnielinski_annulus(re, pr, 0.5, 'inner') * k[0] / g['Dh_ann'][0])
    assert ho[0] == pytest.approx(m1.gnielinski_annulus(re, pr, 0.5, 'outer') * k[0] / g['Dh_ann'][0])


def test_solve_selects_and_records_the_candidate():
    mud = fluids.Mud(1080.0, pv_ref=0.012, yield_point=7.18, pv_ref_T=48.9)
    # 40 kg/s: about 1.5 m/s in the annulus, laminar by Wilson-Thomas and
    # turbulent by the apparent-viscosity Reynolds number
    base = dict(m_dot=40.0, pipe=wg.LEGACY_VACUUM, verbose=False, fluid=mud, friction_heat=True)
    current = m1.solve(**base)
    candidate = m1.solve(**base, annulus_model='bingham')
    assert current['annulus_model'] == 'v1.6.0' and candidate['annulus_model'] == 'bingham'
    assert current['success'] and candidate['success']
    assert candidate['T_bottom_delivered'] != pytest.approx(current['T_bottom_delivered'], abs=1e-3)
    # the pressure budget follows the circulation's criterion unless told otherwise
    inherited = m1.hydraulics(40.0, current['geometry'], result=candidate, fluid=mud)
    explicit = m1.hydraulics(40.0, current['geometry'], result=candidate, fluid=mud, annulus_model='bingham')
    assert inherited['spp'] == explicit['spp']
    other = m1.hydraulics(40.0, current['geometry'], result=candidate, fluid=mud, annulus_model='v1.6.0')
    assert [p['annulus_regime'] for p in inherited['pieces']] == ['laminar']
    assert [p['annulus_regime'] for p in other['pieces']] != ['laminar']
    assert inherited['spp'] > other['spp']
    with pytest.raises(ValueError, match='annulus_model'):
        m1.solve(**base, annulus_model='bingham', hydraulics_model='v1.5.0')
    with pytest.raises(ValueError, match='annulus_model'):
        m1.solve(**base, annulus_model='other')
