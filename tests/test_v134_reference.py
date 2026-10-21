"""C2 reference integration; uses the documented uniform trip-fluid bound."""
import pytest

from borethm import site_evaluation as se
from borethm.comparative_sites import LARDERELLO


@pytest.mark.slow
def test_larderello_simulates_the_all_depth_prescription():
    output = se.evaluate(LARDERELLO, circulation='v1.3.4')
    assert output['fluid_converged']
    data = se.result_dict(output)
    programme = data['programme']
    assert abs(programme['drilling_prescribed_rho_surface'] - programme['drilling_simulated_rho_surface']) < 2.
    assert abs(programme['trip_prescribed_rho_surface'] - programme['trip_simulated_rho_surface']) < 2.
    assert programme['drilling_simulated_rho_surface'] > 1000.
    assert output['tools']['trip_fluid_SG'] == pytest.approx(programme['trip_simulated_rho_surface'] / 1000.)
    assert programme['bit_C'] > 0 and programme['ecd_SG'] > 0
