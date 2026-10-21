"""C2: whole-hole prescriptions change the fluid used in each solve."""
import numpy as np
import pytest

from borethm import fluids
from borethm import site_evaluation as se


@pytest.fixture
def trial(monkeypatch):
    monkeypatch.setattr(fluids, '_water', lambda T, P: tuple(np.full(np.broadcast(np.asarray(T), np.asarray(P)).shape, value)
                                                           for value in (1000., 4000., 0.001, 0.6)))
    seen = []
    def evaluation(site, thermal, budget, fluid, **kwargs):
        density = 1000. if fluid is None else fluid.rho_surface
        seen.append(density)
        return dict(z=1000., fluid=fluid, circ={'rop': 3. / 3600.}, drill={'ROP': 3. / 3600.},
                    m1={'success': True, 'hyd': {'dp_annulus': 1e6}}, rop_passes=[])
    monkeypatch.setattr(se, '_evaluate_v12', evaluation)
    monkeypatch.setattr(se, 'site_cycle', lambda *args, **kwargs: dict(drill_SG=1.0))
    return seen


def test_shallow_requirement_changes_simulated_drilling_and_trip_fluids(trial, monkeypatch):
    monkeypatch.setattr(se, 'common_windows', lambda *args, **kwargs:
                        dict(drilling_fluid={'lo': 1100.}, trip_fluid={'lo': 1200.}))
    trip_seen = []
    def tools(site, output):
        material = output['trip_fluid']
        trip_seen.append(1000. if material is None else material.rho_surface)
        return {'tool': 'PASS'}
    monkeypatch.setattr(se, 'tool_gates', tools)
    fluid, passes, converged, _ = se.drilling_fluid(se.SOULTZ, corrected=True)
    assert converged
    assert trial == [1000., 1100.]
    assert trip_seen == [1000., 1200.]
    assert fluid.rho_surface == 1100.
    assert passes[-1]['density_residual_SG'] == 0.
    assert passes[-1]['trip_residual_SG'] == 0.


def test_revisited_density_is_unconverged_and_keeps_the_simulated_state(trial, monkeypatch):
    def windows(site, output):
        requirement = 1100. if trial[-1] < 1050. else 1000.
        return dict(drilling_fluid={'lo': requirement}, trip_fluid={'lo': requirement})
    monkeypatch.setattr(se, 'common_windows', windows)
    monkeypatch.setattr(se, 'tool_gates', lambda *args: {'tool': 'PASS'})
    fluid, passes, converged, _ = se.drilling_fluid(se.SOULTZ, corrected=True)
    assert not converged and passes[-1]['stop'] == 'cycling'
    assert fluid.rho_surface == passes[-1]['simulated_rho_surface'] == 1100.
