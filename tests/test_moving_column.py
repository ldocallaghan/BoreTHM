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


def test_partial_pump_steps_preserve_front_through_turnaround():
    small_steps = make_column()
    single_step = make_column()
    repeated_return = sum(small_steps.restart_step(1., .5, 15., [0., 0., 0.])[0]
                          for _ in range(5))
    direct_return, _ = single_step.restart_step(5., .5, 15., [0., 0., 0.])
    np.testing.assert_allclose(small_steps.bore_temperature, single_step.bore_temperature)
    np.testing.assert_allclose(small_steps.annulus_temperature, single_step.annulus_temperature)
    assert repeated_return == pytest.approx(direct_return)
    assert single_step.annulus_temperature[-1] == pytest.approx(18.75)


def test_repeated_displacement_preserves_temperature_front():
    small_steps = make_column()
    single_step = make_column()
    repeat_heat = 0.
    for change in (.25, .5, .75, 1.):
        _, heat = small_steps.descend([2., 2.-change, 2.], 0., float_valve=True)
        repeat_heat += heat
    _, direct_heat = single_step.descend([2., 1., 2.], 0., float_valve=True)
    np.testing.assert_allclose(small_steps.annulus_temperature, [50., 60., 80.])
    np.testing.assert_allclose(small_steps.annulus_temperature, single_step.annulus_temperature)
    assert repeat_heat == pytest.approx(direct_heat)


def test_explicit_radial_step_matches_original_static_equations():
    from borethm.wall_thermal import State, run

    duration = 100.
    states = [State("static", duration, C=1e5, h=50., T_node0=35.)]
    original = run(states, 120., .1, 2.5, 2.5e6, n=32)
    eliminated = run(states, 120., .1, 2.5, 2.5e6, n=32, dt_max=duration/50)
    np.testing.assert_allclose(eliminated.T_wall, original.T_wall, atol=1e-9, rtol=0.)
    np.testing.assert_allclose(eliminated.T_node, original.T_node, atol=1e-9, rtol=0.)


def test_bore_regrid_moves_no_heat_and_retains_original_front():
    column = make_column()
    column.restart_step(1., .3, 15., [0., 0., 0.])
    before = inventory(column)
    column.regrid_bore([.6, .4])
    np.testing.assert_allclose(column.bore_temperature, [22.5, 30.])
    column.regrid_bore([.3, .7])
    np.testing.assert_allclose(column.bore_temperature, [15., 30.])
    assert inventory(column) == pytest.approx(before)
