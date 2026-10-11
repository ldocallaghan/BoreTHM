"""A diverged candidate cannot become a physical wellhead-pressure request."""
import numpy as np
import pytest

import model1_coupled as m1
import pressure as pr
import site_evaluation as se


@pytest.mark.parametrize('temperature', [1000., np.nan, np.inf])
def test_invalid_return_temperature_is_a_failed_candidate(monkeypatch, temperature):
    monkeypatch.setattr(m1, 'solve', lambda **kwargs: dict(success=False, T_return_surface=temperature))
    monkeypatch.setattr(m1, 'hydraulics', lambda *args, **kwargs: {})
    monkeypatch.setattr(pr, 'backpressure', lambda *args: pytest.fail('invalid return reached the saturation law'))
    result = se.circulate(se.SOULTZ, se.SOULTZ.target(), se.SOULTZ.temperature(), se.SITE_PIPES[0],
                          5., retry=False)
    assert not result['success']
    assert result['backpressure'] == 0.
    assert 'saturation-pressure domain' in result['failure']


def test_a_forced_pressure_does_not_request_the_open_annulus_saturation_policy(monkeypatch):
    monkeypatch.setattr(m1, 'solve', lambda **kwargs: dict(success=True, T_return_surface=400.))
    monkeypatch.setattr(m1, 'hydraulics', lambda *args, **kwargs: {})
    monkeypatch.setattr(pr, 'backpressure', lambda *args: pytest.fail('forced pressure reached the open-annulus policy'))
    result = se.circulate(se.SOULTZ, se.SOULTZ.target(), se.SOULTZ.temperature(), se.SITE_PIPES[0],
                          5., P_surface=m1.P_OP, retry=False)
    assert result['success']
    assert result['backpressure'] == 0.
