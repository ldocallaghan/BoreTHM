import numpy as np
import pytest

from borethm.run_in_column import RadialColumn, displace_annulus, pump_on_step


def test_zero_film_keeps_fluid_frozen():
    column = RadialColumn(.1, 150., 2.5, 2.5e6, 7200., radial_nodes=40)
    column.circulate(3600., 60., 100.)
    column.shut_in(3600., 1e5, 0.)
    assert column.temperature_C == pytest.approx(60.)


def test_displacement_accounts_for_intake_and_surface_exit():
    temperatures, intake, exit_volume, exit_inventory = displace_annulus(
        [2., 2.], [100., 60.], [1., 1.], bore_intake=1.)
    np.testing.assert_allclose(temperatures, [100., 60.])
    assert intake == pytest.approx(100.)
    assert exit_volume == pytest.approx(1.)
    assert exit_inventory == pytest.approx(60.)


@pytest.mark.parametrize("pumped", [1., 6.])
def test_pump_on_conserves_inventory(pumped):
    volumes = np.array([2., 2.])
    initial = np.array([100., 60.])
    result, returned = pump_on_step(volumes, initial, pumped, 20.)
    assert returned + np.dot(volumes, result) == pytest.approx(
        np.dot(volumes, initial) + 20. * pumped)
    np.testing.assert_allclose(result, [60., 80.] if pumped == 1. else [20., 20.])
