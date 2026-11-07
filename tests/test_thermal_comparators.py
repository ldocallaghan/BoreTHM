"""The comparison choices are independent of the held-out observations."""
import numpy as np
import pytest

from borethm import model1_coupled, well_geometry as wg
from validation.comparators.thermal import analytical, persistence, previous_physics, undisturbed_formation


def test_previous_physics_is_explicit(monkeypatch):
    monkeypatch.setattr(model1_coupled, "solve", lambda **settings: settings)
    assert previous_physics(m_dot=24, physics="v1.8.0") == {"m_dot": 24, "physics": "v1.7.0"}


def test_analytical_uses_measured_length_and_formation_endpoints():
    survey = wg.Survey([0., 1000.], [0., 800.])
    g = wg.WellGeometry.single(1000., wg.uniform_wall(45., .05, .06), .11, survey)
    fluid = dict(rho=1000., cp=4200., mu=.001, k=.65)
    profile = analytical(g, fluid, 20., 30., lambda z: 10.+.06*z,
                         lambda z: np.full_like(z, 7200.), 2.5, 2.5e6)
    assert profile.length == 1000.
    assert profile.gradient == pytest.approx(.048)
    assert profile.closed_form(0.)[0] == pytest.approx(30.)
    np.testing.assert_allclose(undisturbed_formation([0., 1000.], survey, lambda z: 10.+.06*z),
                               [10., 58.])


def test_persistence_never_uses_a_reading_at_or_after_the_leg_start():
    np.testing.assert_equal(persistence(3, [3, 1, 2, 0], [80, 25, np.nan, 20], [3, 4]),
                            [25., 25.])
    assert np.isnan(persistence(1, [1, 2], [40, 50], [1])[0])
