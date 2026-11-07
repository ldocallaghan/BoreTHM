import numpy as np
import pytest

from borethm.column_replay import ColumnStep, ToolContact, replay
from borethm.layered_tool import LayeredTool
from borethm.moving_column import MovingColumn
from borethm.run_in_column import RadialColumn


@pytest.mark.parametrize("float_valve", [False, True])
def test_descent_pause_and_restart_share_bore_inventory(float_valve):
    rock = [RadialColumn(.1, 120., 2.5, 2.5e6, 3600., radial_nodes=40,
                         temperature_C=t) for t in (50., 70., 90.)]
    column = MovingColumn(rock, [10., 10., 10.], [2., 2., 2.], 4.18e6, [1.], [35.])
    tool = LayeredTool(.025, .08, column.fluid_heat_capacity, 20.)
    films = (50., 50., 0.)
    initial = ToolContact(tool, 2., 0, 0, 50., 400.)
    lowered = ToolContact(tool, 2., 1, 1, 50., 400.)
    steps = [
        ColumnStep(10., films, (initial,)),
        ColumnStep(10., films, (lowered,), np.array([2., 1.5, 2.]), .2,
                   float_valve, 25.),
        ColumnStep(30., films, (lowered,)),
        ColumnStep(30., films, (lowered,), flow=.01, inlet_C=25., active_cells=2),
    ]
    output = list(replay(column, steps))
    assert [step.elapsed for step in output] == [10., 20., 50., 80.]
    assert output[1].returned_J > 0.
    assert output[-1].returned_J > 0.
    assert column.annulus_temperature[-1] == pytest.approx(90.)
    assert output[-1].sensors_C[0][0] == column.bore_temperature[1]
    assert max(abs(step.energy_residual_J) for step in output) < 1e-4
    np.testing.assert_allclose(column.bore_volume, [.2, 1.] if float_valve else [1., .2])


def test_restart_throughput_splits_a_recorded_step_and_resets_after_pause():
    from borethm.column_replay import circulation_phases

    steps = [ColumnStep(10., (0.,), flow=2., inlet_C=20.),
             ColumnStep(20., (0.,), flow=3., inlet_C=21.),
             ColumnStep(10., (0.,)),
             ColumnStep(2., (0.,), flow=4., inlet_C=21.)]
    phases = list(circulation_phases(steps, flush_volume=35.))
    assert [(kind, step.duration) for kind, step in phases] == [
        ("restart", 10.), ("restart", 5.), ("steady", 15.),
        ("static", 10.), ("restart", 2.)]
