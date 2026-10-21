"""C1: unit-mass parcels, component volumes and the reference states."""
import numpy as np
import pytest

from borethm import fluids


def unit_parcel(rho_surface, rho_water_surface, temperatures, water_densities):
    # Two independent balances for one kg at the reference state:
    # component masses sum to one; component volumes sum to 1/rho_surface.
    masses = np.linalg.solve([[1., 1.], [1. / rho_water_surface, 1. / 4200.]],
                             [1., 1. / rho_surface])
    water_mass, barite_mass = masses
    water_volume = water_mass / water_densities
    barite_volume = barite_mass / 4200. * (1. + 5e-5 * (temperatures - 20.))
    recovered_water = water_volume * water_densities
    recovered_barite = barite_volume * 4200. / (1. + 5e-5 * (temperatures - 20.))
    return masses, water_volume, barite_volume, recovered_water, recovered_barite


def test_component_masses_are_conserved_using_independent_parcel_volumes(monkeypatch):
    def water(T, P):
        T, P = np.broadcast_arrays(np.asarray(T, float), np.asarray(P, float))
        rho = 1000. - (T - 20.) + (P - 1e5) / 1e7
        return rho, np.full_like(T, 4000.), np.full_like(T, 0.001), np.full_like(T, 0.6)
    monkeypatch.setattr(fluids, '_water', water)
    T, P = np.array([20., 200., 300., 400.]), np.array([1e5, 100e6, 100e6, 100e6])
    masses, Vw, Vb, recovered_w, recovered_b = unit_parcel(1360., 1000., T, water(T, P)[0])
    assert recovered_w == pytest.approx(masses[0], abs=1e-12)
    assert recovered_b == pytest.approx(masses[1], abs=1e-12)
    mud = fluids.Mud(1360.)
    rho, cp, _, conductivity = mud.props(T, P)
    assert mud.x == pytest.approx(masses[1], abs=1e-12)
    assert rho * (Vw + Vb) * (1 - mud.x) == pytest.approx(masses[0], abs=1e-12)
    assert rho * (Vw + Vb) * mud.x == pytest.approx(masses[1], abs=1e-12)
    assert cp == pytest.approx(masses[0] * 4000. + masses[1] * 436., abs=1e-12)
    fraction = Vb / (Vw + Vb)
    contrast = (1.5 - 0.6) / (1.5 + 2 * 0.6)
    assert conductivity == pytest.approx(0.6 * (1 + 2 * contrast * fraction) / (1 - contrast * fraction))


@pytest.mark.slow
def test_four_reference_states_and_exact_water_limit():
    from borethm import water_table as wt
    T, P = np.array([20., 200., 300., 400.]), np.array([1e5, 100e6, 100e6, 100e6])
    mud = fluids.Mud(1360.)
    assert mud.props(T, P)[0] == pytest.approx([1360., 1268.0, 1142.7, 976.4], abs=0.5)
    legacy = fluids.Mud(1360., conserve_mass=False)
    assert legacy.props(T, P)[0] == pytest.approx([1360., 1289.7, 1198.2, 1080.4], abs=0.5)
    for actual, reference in zip(fluids.water().props(T, P), wt.props(T, P)):
        np.testing.assert_array_equal(actual, reference)


@pytest.mark.parametrize('density', [900., 4200., 4500., np.nan, np.inf, -1.])
def test_impossible_surface_density_is_rejected(monkeypatch, density):
    monkeypatch.setattr(fluids, '_rho_water_ref', lambda: 1000.)
    with pytest.raises(ValueError):
        fluids.Mud(density)
