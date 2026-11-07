import numpy as np
import pytest

from borethm.layered_tool import LayeredTool
from borethm.run_in_column import RadialColumn


def test_mixed_wall_energy():
    column = RadialColumn(.108, 150., 2.5, 2.5e6, 7200., radial_nodes=80)
    column.circulate(3600., 60., 100.)
    result = column.shut_in(3600., 1e5, np.inf)
    assert column.temperature_C == result.T_wall[-1]
    assert result.energy_in + 1e5*(column.temperature_C-60.) == pytest.approx(
        0., abs=1e-3)


@pytest.mark.parametrize("inside_film", [0., 50., np.inf])
def test_layered_tool_energy_and_surface_limit(inside_film):
    tool = LayeredTool(.03, .085, 4.18e6, 50.)
    initial = tool.temperature_C.copy()
    heat = tool.step(15., 100., inside_film, np.inf)
    assert np.dot(tool.capacity, tool.temperature_C-initial) == pytest.approx(heat)
    bore, inside, mid, outside = tool.sensor_temperatures()
    assert bore <= inside <= mid <= outside
    assert outside == 100.
    if inside_film == 0.:
        assert bore == 50.
