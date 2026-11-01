"""Ramp endpoints cannot move the inlet or turnaround beyond the well."""
import numpy as np
import pytest

from borethm import model1_coupled as m1, well_geometry as wg


@pytest.mark.parametrize('mode', ['v1.5.0', 'v1.6.0'])
@pytest.mark.parametrize('short_end', ['surface', 'bit'])
def test_short_end_segment_keeps_the_physical_boundaries(mode, short_end):
    segments = [wg.StringSegment(.25, wg.WU_COLLAR),
                wg.StringSegment(99.75, wg.CONVENTIONAL)]
    if short_end == 'bit':
        segments.reverse()
    geometry = wg.WellGeometry(segments, [wg.open_hole(0., 100., .25)])
    result = m1.solve(m_dot=20., T_inj=40., geometry=geometry,
        fluid=dict(rho=1000., cp=4200., mu=.02, k=.6),
        hydraulics_model=mode, friction_heat=True, verbose=False)
    assert result['success']
    assert result['sol'].x[0] == 0.
    assert result['sol'].x[-1] == geometry.md_bit
    assert result['Td'][0] == pytest.approx(40., abs=1e-10)
    assert np.isfinite(result['Td']).all() and np.isfinite(result['Tu']).all()
