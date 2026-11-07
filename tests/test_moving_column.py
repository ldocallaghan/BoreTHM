import numpy as np
import pytest

from borethm.moving_column import MovingColumn
from borethm.run_in_column import RadialColumn


def make_column():
    rock = [RadialColumn(.1, formation, 2.5, 2.5e6, 7200., radial_nodes=40,
                         temperature_C=fluid)
            for formation, fluid in [(100., 40.), (140., 60.), (180., 80.)]]
    return MovingColumn(rock, [10., 10., 10.], [2., 2., 2.], 4.18e6, [1.], [30.])


def inventory(column):
    return column.fluid_heat_capacity*(
        np.dot(column.annulus_volume, column.annulus_temperature)
        + np.dot(column.bore_volume, column.bore_temperature))


@pytest.mark.parametrize("float_valve", [False, True])
def test_descent_and_recovery_energy(float_valve):
    column = make_column()
    initial = inventory(column)
    exit_volume, exit_heat = column.descend(
        [2., 1.5, 2.], .2, float_valve=float_valve, fill_temperature=25.)
    added_heat = .2*25.*column.fluid_heat_capacity if float_valve else 0.
    assert exit_volume == pytest.approx(.5 if float_valve else .3)
    assert inventory(column) + exit_heat == pytest.approx(initial + added_heat)
    assert column.annulus_temperature[-1] == 80.
    after_displacement = inventory(column)
    rock_heat = column.recover(60., [50., 0., np.inf])
    assert inventory(column) + rock_heat == pytest.approx(after_displacement)


def test_restart_energy_with_wall_exchange():
    column = make_column()
    initial = inventory(column)
    returned, rock_heat = column.restart_step(30., .01, 25., [50., 0., np.inf])
    assert inventory(column) + returned + rock_heat == pytest.approx(
        initial + 30.*.01*25.*column.fluid_heat_capacity)


def test_tool_exchange_conserves_fluid_and_tool_energy():
    from borethm.layered_tool import LayeredTool

    column = make_column()
    tool = LayeredTool(.025, .08, column.fluid_heat_capacity, 10.)
    initial_fluid = inventory(column)
    initial_tool = np.dot(tool.capacity, tool.temperature_C)
    heat = column.exchange_tool_heat(1, tool, 20., 50., 500., tool_length=2.)
    assert heat > 0.
    assert initial_fluid - inventory(column) == pytest.approx(heat)
    assert 2.*(np.dot(tool.capacity, tool.temperature_C)
                                  - initial_tool) == pytest.approx(heat)
