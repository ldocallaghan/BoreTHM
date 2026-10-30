"""The annulus_model 'herschel-bulkley' candidate: the mud's Herschel-Bulkley
rheology, the Founargiotakis slot model, the annulus film coefficients and
their use in the circulation solve."""
import numpy as np
import pytest

from borethm import fluids
from borethm import hydraulic_losses as hl
from borethm import model1_coupled as m1
from borethm import well_geometry as wg


def test_rheology_from_report_by_hand():
    pv, yp, gel = 14.0, 11.5, 4.5
    hb = fluids.HerschelBulkley.from_report(pv, yp, gel)
    r600, r300 = 2 * pv + yp, pv + yp
    n = np.log((r600 - gel) / (r300 - gel)) / np.log(1022 / 511)
    assert hb.n == pytest.approx(n)
    assert hb.K == pytest.approx((r300 - gel) * 1.0678 * 0.4788026 / 511 ** n)
    assert hb.tau0 == pytest.approx(gel * 1.0678 * 0.4788026)
    # with no yield stress and no yield point, a Newtonian fluid of viscosity PV
    newtonian = fluids.HerschelBulkley.from_report(10.0, 0.0, 0.0)
    assert newtonian.n == pytest.approx(1.0)
    assert newtonian.K == pytest.approx(10.0 * 1.0678 * 0.4788026 / 511)
    with pytest.raises(ValueError, match='300 rpm'):
        fluids.HerschelBulkley.from_report(pv, yp, r300)


def test_rheology_temperature_dependence():
    mud = fluids.Mud(1080.0, pv_ref=0.014, yield_point=5.5, pv_ref_T=26.7)
    T = np.array([20.0, 50.0, 80.0, 110.0])
    _, _, mu, _ = m1.fluid_props(T, np.full(4, 1e5), mud)
    constant = fluids.HerschelBulkley.from_report(14.0, 11.5, 4.5)
    tau0, K, n = constant.at(T, mu, mud)
    assert np.allclose(tau0, constant.tau0)
    assert np.allclose(K, constant.K * mu / 0.014)
    t_star, e_h = 330.0, 2900.0
    rising = fluids.HerschelBulkley.from_report(14.0, 11.5, 4.5, rise=(t_star, e_h))
    tau0 = rising.at(T, mu, mud)[0]
    expected = rising.tau0 * np.exp(e_h * np.maximum(1 / t_star - 1 / (T + 273.15), 0))
    assert np.allclose(tau0, expected)
    assert tau0[0] == tau0[1] == rising.tau0 and tau0[3] > tau0[2] > rising.tau0


def test_slot_model_newtonian_limit():
    rho, mu, gap = 1000.0, 0.01, 0.1
    v = np.array([0.1, 0.5, 2.0])
    state = fluids.hb_annulus(rho, 0.0, mu, 1.0, v, gap)
    assert np.allclose(state['re'], rho * v * gap / mu)
    assert np.allclose(state['n_prime'], 1.0)
    # laminar: the slot loss 48 mu V / gap^2, as bingham_gradient's annulus
    assert state['gradient'][0] == pytest.approx(48 * mu * v[0] / gap ** 2)
    assert state['gradient'][0] == pytest.approx(fluids.bingham_gradient(rho, mu, 0.0, v[0], gap, True)[0])
    # Re 1e3 laminar, 5e3 and 2e4 above Re2 = 3000: Dodge-Metzner at n' = 1
    assert np.allclose(state['re1'], 2100.0) and np.allclose(state['re2'], 3000.0)
    assert list(state['blend']) == [0.0, 1.0, 1.0]
    assert np.allclose(state['f'][1:], fluids.dodge_metzner(state['re'][1:], 1.0))
    assert np.allclose(state['gradient'], 2 * state['f'] * rho * v ** 2 / gap)


def test_dodge_metzner_satisfies_its_equation():
    re, n = np.array([3000.0, 1e4, 1e5]), np.array([0.4, 0.7, 1.0])
    f = fluids.dodge_metzner(re, n)
    lhs = f ** -0.5
    rhs = 4 / n ** 0.75 * np.log10(re * f ** (1 - n / 2)) - 0.395 / n ** 1.2
    assert np.allclose(lhs, rhs)


def test_slot_model_laminar_by_hand():
    rho, gap = 1080.0, 0.0953
    hb = fluids.HerschelBulkley.from_report(14.0, 11.5, 4.5)
    v = 0.5
    state = fluids.hb_annulus(rho, hb.tau0, hb.K, hb.n, v, gap)
    tau_w = float(state['tau_w'])
    assert state['re'] < state['re1']
    # Founargiotakis et al. (2008) eq. 5 at h = gap / 2 recovers the velocity
    h, m, xi = gap / 2, 1 / hb.n, hb.tau0 / tau_w
    mean = (tau_w / (h / 2) / hb.K) ** m * (h / 2) ** (m + 1) * (1 - xi) ** (m + 1) * (xi + m + 1) / ((m + 1) * (m + 2))
    assert mean == pytest.approx(v, rel=1e-9)
    # eq. 14 for n', and the Reynolds number 12 rho V^2 / tau_w in laminar flow
    n = hb.n
    assert state['n_prime'] == pytest.approx(n * (1 - xi) * (n * xi + n + 1) / (1 + n + 2 * n * xi + 2 * n * n * xi * xi))
    assert state['re'] == pytest.approx(12 * rho * v ** 2 / tau_w)
    assert state['gradient'] == pytest.approx(4 * tau_w / gap)


def test_slot_model_transition_and_bound():
    rho, gap = 1080.0, 0.0953
    hb = fluids.HerschelBulkley.from_report(14.0, 11.5, 4.5)
    v = np.linspace(0.2, 3.0, 400)
    for scale in (1.0, 0.5, 0.3):
        state = fluids.hb_annulus(rho, hb.tau0, hb.K * scale, hb.n, v, gap)
        # the wall stress closes tau_w = f rho V^2 / 2, never below the laminar line
        assert np.allclose(state['tau_w'], state['f'] * rho * v ** 2 / 2, rtol=1e-9)
        assert np.all(state['f'] >= 24 / state['re'] * (1 - 1e-12))
        assert np.all(np.diff(state['gradient']) > 0)
        band = (state['re'] > state['re1']) & (state['re'] < state['re2'])
        f_t2 = fluids.dodge_metzner(state['re2'], state['n_prime'])
        interpolated = 24 / state['re1'] + state['blend'] * (f_t2 - 24 / state['re1'])
        assert np.allclose(state['f'][band], np.maximum(interpolated, 24 / state['re'])[band])
        assert np.any(state['blend'] == 1.0) and np.any(state['blend'] == 0.0)


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


def test_wall_viscosity():
    hb = fluids.HerschelBulkley.from_report(14.0, 11.5, 4.5)
    state = fluids.hb_annulus(1080.0, hb.tau0, hb.K, hb.n, 2.0, 0.0953)
    gamma_w = ((state['tau_w'] - hb.tau0) / hb.K) ** (1 / hb.n)
    assert state['mu_w'] == pytest.approx(state['tau_w'] / gamma_w)
    assert state['mu_a'] == pytest.approx(1080.0 * 2.0 * 0.0953 / state['re'])
    newtonian = fluids.hb_annulus(1000.0, 0.0, 0.002, 1.0, np.array([0.1, 3.0]), 0.1)
    assert np.allclose(newtonian['mu_w'], 0.002) and np.allclose(newtonian['mu_a'], 0.002)


def test_film_coefficients():
    g = annulus(0.05555, 0.1111)             # r* = 0.5
    T, P = np.array([80.0]), np.array([2e7])
    mud = fluids.Mud(1080.0, pv_ref=0.014, yield_point=5.5, pv_ref_T=26.7)
    mud.rheology = fluids.HerschelBulkley.from_report(14.0, 11.5, 4.5)
    rho, cp, mu, k = m1.fluid_props(T, P, mud)
    dh = g['Dh_ann'][0]
    # slow enough to be laminar: the tabulated values at r* = 0.5
    hi, ho = m1.annulus_films(float(0.3 * rho[0] * g['A_ann'][0]), g, T, P, mud)
    assert hi[0] * dh / k[0] == pytest.approx(6.18102)
    assert ho[0] * dh / k[0] == pytest.approx(5.03655)
    # water fast enough to be turbulent: Gnielinski on Re = rho V d_h / mu (mu_w = mu)
    rho, cp, mu, k = m1.fluid_props(T, P, None)
    m_dot = float(2.0 * rho[0] * g['A_ann'][0])
    hi, ho = m1.annulus_films(m_dot, g, T, P, None)
    re, pr = 2.0 * rho[0] * dh / mu[0], cp[0] * mu[0] / k[0]
    assert hi[0] == pytest.approx(m1.gnielinski_annulus(re, pr, 0.5, 'inner') * k[0] / dh, rel=1e-6)
    assert ho[0] == pytest.approx(m1.gnielinski_annulus(re, pr, 0.5, 'outer') * k[0] / dh, rel=1e-6)
    # in the band, linear in Re between the laminar value and Gnielinski at Re2
    v = 2600 * mu[0] / (rho[0] * dh)
    hi, _ = m1.annulus_films(float(v * rho[0] * g['A_ann'][0]), g, T, P, None)
    blend = (2600 - 2100) / 900
    expected = (1 - blend) * 6.18102 + blend * m1.gnielinski_annulus(2600.0, pr, 0.5, 'inner')
    assert hi[0] * dh / k[0] == pytest.approx(expected, rel=1e-6)


def test_passage_gradient_herschel_bulkley():
    rho, mu = np.array([1000.0]), np.array([0.001])
    area, dh = np.array([0.02]), np.array([0.1])
    newtonian = hl.passage_gradient(rho, mu, 0.0, 40.0, area, dh, True, regime='herschel-bulkley')
    state = fluids.hb_annulus(rho, 0.0, mu, 1.0, 2.0, dh)
    assert newtonian[0] == pytest.approx(state['gradient']) and newtonian[1] == pytest.approx(state['re'])
    # the bore keeps the Bingham treatment
    bore = hl.passage_gradient(rho, mu, 2.0, 40.0, area, dh, False, regime='herschel-bulkley')
    assert bore[0] == pytest.approx(fluids.bingham_gradient(rho, mu, 2.0, 2.0, dh, False)[0])
    with pytest.raises(ValueError, match='regime'):
        hl.passage_gradient(rho, mu, 0.0, 40.0, area, dh, True, regime='other')


def test_solve_selects_and_records_the_candidate():
    mud = fluids.Mud(1080.0, pv_ref=0.014, yield_point=5.5, pv_ref_T=26.7)
    mud.rheology = fluids.HerschelBulkley.from_report(14.0, 11.5, 4.5)
    base = dict(m_dot=40.0, pipe=wg.LEGACY_VACUUM, verbose=False, fluid=mud, friction_heat=True)
    current = m1.solve(**base)
    candidate = m1.solve(**base, annulus_model='herschel-bulkley')
    assert current['annulus_model'] == 'v1.6.0' and candidate['annulus_model'] == 'herschel-bulkley'
    assert current['success'] and candidate['success']
    assert candidate['T_bottom_delivered'] != pytest.approx(current['T_bottom_delivered'], abs=1e-3)
    # the pressure budget follows the circulation's annulus model unless told otherwise
    inherited = m1.hydraulics(40.0, current['geometry'], result=candidate, fluid=mud)
    explicit = m1.hydraulics(40.0, current['geometry'], result=candidate, fluid=mud, annulus_model='herschel-bulkley')
    assert inherited['spp'] == explicit['spp']
    other = m1.hydraulics(40.0, current['geometry'], result=candidate, fluid=mud, annulus_model='v1.6.0')
    assert inherited['spp'] != pytest.approx(other['spp'], rel=1e-4)
    assert {p['annulus_regime'] for p in inherited['pieces']} <= {'laminar', 'mixed', 'turbulent'}
    with pytest.raises(ValueError, match='annulus_model'):
        m1.solve(**base, annulus_model='herschel-bulkley', hydraulics_model='v1.5.0')
    with pytest.raises(ValueError, match='annulus_model'):
        m1.solve(**base, annulus_model='other')


def test_erge_band_by_hand():
    n, kappa = np.array([0.1, 0.3, 0.6, 1.0]), 0.57
    re1, re2 = fluids.transition_band(n, 'erge', kappa)
    expected1 = 2100 * n ** 0.331 * (1 + 1.402 * kappa - 0.977 * kappa ** 2)
    assert np.allclose(re1, expected1)
    assert np.allclose(re2, 2900 * np.clip(n, 0.15, 0.4) ** (-0.039 * expected1 ** 0.307))
    assert np.all(re2 > re1)
    # a Newtonian fluid in a pipe (kappa 0) starts transition at 2100
    assert fluids.transition_band(1.0, 'erge', 0.0)[0] == pytest.approx(2100.0)
    # eccentricity lowers the onset
    assert fluids.transition_band(0.3, 'erge', kappa, eccentricity=1.0)[0] < re1[1]
    assert np.allclose(fluids.transition_band(n)[0], 3250 - 1150 * n)
    with pytest.raises(ValueError, match='kappa'):
        fluids.transition_band(n, 'erge')
    with pytest.raises(ValueError, match='band'):
        fluids.transition_band(n, 'other')


def test_slot_model_erge_band():
    rho, gap = 1080.0, 0.0953
    hb = fluids.HerschelBulkley.from_report(14.0, 11.5, 4.5)
    v = np.linspace(0.2, 3.0, 300)
    state = fluids.hb_annulus(rho, hb.tau0, hb.K * 0.5, hb.n, v, gap, band='erge', kappa=0.57)
    re1, re2 = fluids.transition_band(state['n_prime'], 'erge', 0.57)
    assert np.allclose(state['re1'], re1) and np.allclose(state['re2'], re2)
    assert np.allclose(state['tau_w'], state['f'] * rho * v ** 2 / 2, rtol=1e-9)
    # over the wide band the linearly interpolated friction factor can let the
    # gradient dip a little with velocity; it rises outside the band
    g = state['gradient']
    assert np.max(1 - g / np.maximum.accumulate(g)) < 0.06
    outside = (state['blend'] == 0) | (state['blend'] == 1)
    rising = np.diff(g) > 0
    assert np.all(rising[outside[:-1] & outside[1:]])
    # the laminar solution does not depend on the band
    slow = fluids.hb_annulus(rho, hb.tau0, hb.K, hb.n, 0.3, gap)
    assert fluids.hb_annulus(rho, hb.tau0, hb.K, hb.n, 0.3, gap, band='erge', kappa=0.57)['tau_w'] == pytest.approx(slow['tau_w'])


def test_film_coefficients_on_plastic_viscosity():
    g = annulus(0.05555, 0.1111)
    T, P = np.array([80.0]), np.array([2e7])
    mud = fluids.Mud(1080.0, pv_ref=0.014, yield_point=5.5, pv_ref_T=26.7)
    mud.rheology = fluids.HerschelBulkley.from_report(14.0, 11.5, 0.0)
    rho, cp, mu, k = m1.fluid_props(T, P, mud)
    dh = g['Dh_ann'][0]
    m_dot = float(3.0 * rho[0] * g['A_ann'][0])
    hi, ho = m1.annulus_films(m_dot, g, T, P, mud, 'erge', 'plastic')
    state = fluids.hb_annulus(rho, *mud.rheology.at(T, mu, mud), 3.0, dh, band='erge', kappa=0.5)
    assert state['blend'][0] == 1.0
    re, pr = 3.0 * rho[0] * dh / mu[0], cp[0] * mu[0] / k[0]
    assert hi[0] == pytest.approx(m1.gnielinski_annulus(re, pr, 0.5, 'inner') * k[0] / dh, rel=1e-6)
    assert ho[0] == pytest.approx(m1.gnielinski_annulus(re, pr, 0.5, 'outer') * k[0] / dh, rel=1e-6)
    wall = m1.annulus_films(m_dot, g, T, P, mud, 'erge', 'wall')[0]
    assert wall[0] != pytest.approx(hi[0], rel=1e-3)
    with pytest.raises(ValueError, match='viscosity'):
        m1.annulus_films(m_dot, g, T, P, mud, 'erge', 'other')


def test_solve_with_the_erge_candidate():
    mud = fluids.Mud(1080.0, pv_ref=0.014, yield_point=5.5, pv_ref_T=26.7)
    mud.rheology = fluids.HerschelBulkley.from_report(14.0, 11.5, 4.5)
    base = dict(m_dot=40.0, pipe=wg.LEGACY_VACUUM, verbose=False, fluid=mud, friction_heat=True)
    entry6 = m1.solve(**base, annulus_model='herschel-bulkley')
    entry7 = m1.solve(**base, annulus_model='herschel-bulkley-erge')
    assert entry7['success'] and entry7['annulus_model'] == 'herschel-bulkley-erge'
    assert entry7['T_bottom_delivered'] != pytest.approx(entry6['T_bottom_delivered'], abs=1e-3)
    inherited = m1.hydraulics(40.0, entry7['geometry'], result=entry7, fluid=mud)
    explicit = m1.hydraulics(40.0, entry7['geometry'], result=entry7, fluid=mud, annulus_model='herschel-bulkley-erge')
    assert inherited['spp'] == explicit['spp']


def test_power_law_path_matches_the_general_solver():
    hb = fluids.HerschelBulkley.from_report(14.0, 11.5, 0.0)
    v = np.linspace(0.05, 3.5, 300)
    for band, kappa in (('founargiotakis', None), ('erge', 0.57)):
        fast = fluids.hb_annulus(1080.0, 0.0, hb.K, hb.n, v, 0.0953, band=band, kappa=kappa)
        general = fluids.hb_annulus(1080.0, 1e-300, hb.K, hb.n, v, 0.0953, band=band, kappa=kappa)
        for key in ('tau_w', 're', 'f', 'mu_w', 'mu_a', 'gamma_nw'):
            assert np.allclose(fast[key], general[key], rtol=1e-8)
        assert np.allclose(fast['blend'], general['blend'], atol=1e-10)
        # laminar: the power-law slot stress K ((2n + 1) / 3n 12 V / gap)^n
        lam = fast['re'] <= fast['re1']
        expected = hb.K * ((2 * hb.n + 1) / (3 * hb.n) * 12 * v / 0.0953) ** hb.n
        assert np.allclose(fast['tau_w'][lam], expected[lam])
