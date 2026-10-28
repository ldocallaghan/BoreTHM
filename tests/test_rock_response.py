"""The exact cylindrical rock response and the retained logarithmic term."""
import numpy as np
import pytest
from scipy.linalg import solve_banded

from borethm import rock_response as rr

GAMMA = np.euler_gamma


def radial_flux(times, outer=400.0, cells=600, steps=4000):
    """Dimensionless wall flux from a finite-volume radial conduction solve.

    Unit wall temperature from t_D = 0, zero initial temperature, insulated
    outer boundary far beyond the conduction front. Cell faces are spaced
    geometrically in r and the time steps geometrically in t_D; Crank-Nicolson
    after implicit start-up steps.
    """
    faces = np.geomspace(1.0, outer, cells + 1)
    centres = np.sqrt(faces[:-1] * faces[1:])
    volume = 0.5 * (faces[1:] ** 2 - faces[:-1] ** 2)
    conduct = faces[1:-1] / (centres[1:] - centres[:-1])
    wall = 1.0 / np.log(centres[0] / faces[0])          # steady-log link to the wall
    T = np.zeros(cells)
    edges = np.r_[0.0, np.geomspace(1e-8, max(times), steps)]
    out, now = [], 0.0
    pending = sorted(times)
    for i, t_next in enumerate(edges[1:]):
        dt = t_next - now
        theta = 1.0 if i < 20 else 0.5
        main = volume / dt
        lower = np.zeros(cells); upper = np.zeros(cells); diag = main.copy()
        diag[:-1] += theta * conduct; diag[1:] += theta * conduct
        diag[0] += theta * wall
        upper[1:] = -theta * conduct; lower[:-1] = -theta * conduct
        flux = np.zeros(cells)
        flux[:-1] += conduct * (T[1:] - T[:-1]); flux[1:] -= conduct * (T[1:] - T[:-1])
        flux[0] += wall * (1.0 - T[0])
        rhs = main * T + (1 - theta) * flux
        rhs[0] += theta * wall * 1.0
        T = solve_banded((1, 1), np.vstack([upper, diag, lower]), rhs)
        now = t_next
        while pending and now >= pending[0] * (1 - 1e-12):
            out.append(wall * (1.0 - T[0]))
            pending.pop(0)
    return np.array(out)


def test_short_time_series():
    for t_d in (1e-6, 1e-5, 1e-4):
        expected = 1 / np.sqrt(np.pi * t_d) + 0.5 - 0.25 * np.sqrt(t_d / np.pi) + t_d / 8
        assert rr.cylinder_flux(t_d) == pytest.approx(expected, rel=1e-6)


def test_long_time_series():
    """Two terms of the logarithmic series; their error falls as 1/L^3."""
    errors = []
    for t_d in (1e6, 1e9, 1e12):
        L = np.log(4 * t_d) - 2 * GAMMA
        errors.append(abs(rr.cylinder_flux(t_d) / (2 / L - 2 * GAMMA / L ** 2) - 1))
    assert errors[-1] < 3e-3 and errors[0] > errors[1] > errors[2]


def test_table_interpolation_matches_direct_inversion():
    t_d = 10 ** np.linspace(-5.9, 11.9, 113)
    assert np.allclose(rr.cylinder_flux(t_d), rr.talbot_flux(t_d), rtol=2e-5, atol=0)


def test_radial_conduction_solve_agrees():
    times = [0.03, 0.3, 3.0, 30.0]
    numerical = radial_flux(times)
    assert np.allclose(numerical, rr.cylinder_flux(np.array(times)), rtol=5e-3)


def test_logarithmic_term_is_the_original_expression():
    t, alpha, radius, k = np.array([3600., 86400., 3e7]), 1.0e-6, 0.111, 2.5
    original = np.log((radius + 2 * np.sqrt(alpha * t)) / radius) / (2 * np.pi * k)
    assert np.allclose(rr.resistance(t, alpha, radius, k, 'logarithmic'), original, rtol=1e-14)


def test_logarithmic_term_overstates_the_resistance_between_minutes_and_months():
    t_d = np.array([0.03, 0.29, 1.76, 7.0, 49.0, 211.0])
    ratio = np.log(1 + 2 * np.sqrt(t_d)) * rr.cylinder_flux(t_d)
    assert np.all((ratio > 1.04) & (ratio < 1.12))
    assert np.all(np.diff(ratio) < 0)


def test_outside_table_is_rejected():
    with pytest.raises(ValueError):
        rr.cylinder_flux(1e-7)
    with pytest.raises(ValueError):
        rr.resistance(1., 1e-6, .1, 2.5, 'line source')


def test_solver_selects_and_records_the_response():
    from borethm import model1_coupled as m1, well_geometry as wg
    current = m1.solve(verbose=False, pipe=wg.LEGACY_VACUUM)
    legacy = m1.solve(verbose=False, pipe=wg.LEGACY_VACUUM, hydraulics_model='v1.5.0')
    explicit = m1.solve(verbose=False, pipe=wg.LEGACY_VACUUM, rock_response='logarithmic')
    assert current['rock_response'] == 'cylinder' and legacy['rock_response'] == 'logarithmic'
    assert explicit['T_return_surface'] == legacy['T_return_surface']
    assert current['T_return_surface'] != legacy['T_return_surface']
    with pytest.raises(ValueError, match='logarithmic'):
        m1.solve(verbose=False, pipe=wg.LEGACY_VACUUM, hydraulics_model='v1.5.0', rock_response='cylinder')
