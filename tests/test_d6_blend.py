"""Original and current thermal blending at short serial components."""
import numpy as np

from borethm import model1_coupled as m1, well_geometry as wg


FLUID = dict(rho=1000., cp=4200., mu=.001, k=.6)


def test_original_path_converges_on_submetre_components():
    geometry = wg.WellGeometry([
        wg.StringSegment(70., wg.CONVENTIONAL),
        wg.StringSegment(.3, wg.WU_COLLAR),
        wg.StringSegment(.3, wg.WU_HWDP),
        wg.StringSegment(29.4, wg.CONVENTIONAL)], [wg.open_hole(0., 100., .25)])
    result = m1.solve(m_dot=20., geometry=geometry, fluid=FLUID,
        hydraulics_model='v1.5.0', friction_heat=True, verbose=False)
    assert result['success']
    assert result['sol'].status == 0
    assert result['sol'].x[0] == 0.
    assert result['sol'].x[-1] == geometry.md_bit
    assert np.isfinite(result['Td']).all() and np.isfinite(result['Tu']).all()


def test_nonoverlap_paths_are_bit_exact_with_matching_equations():
    geometry = wg.WellGeometry([
        wg.StringSegment(70., wg.CONVENTIONAL),
        wg.StringSegment(5., wg.WU_COLLAR),
        wg.StringSegment(25., wg.CONVENTIONAL)], [wg.open_hole(0., 100., .25)])
    results = [m1.solve(m_dot=20., geometry=geometry, fluid=FLUID,
        hydraulics_model=mode, rock_response='logarithmic', friction_heat=False,
        verbose=False) for mode in ('v1.5.0', 'v1.6.0')]
    assert all(r['success'] for r in results)
    for key in ('z', 'Td', 'Tu'):
        np.testing.assert_array_equal(results[0][key], results[1][key])
