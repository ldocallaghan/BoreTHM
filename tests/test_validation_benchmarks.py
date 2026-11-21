"""Checks of the independent analytical circulation comparator."""
import numpy as np
import pytest

from validation.benchmarks.kabir1996 import Case, hasan_kabir_td, ramey_td


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("length, A, B", [(4572., 4300., 145.), (2657., 6700., 275.)])
def test_closed_form_solves_energy_balances(length, A, B, reverse):
    case = Case(length, 35., 15., .045, A, B)
    depth = np.linspace(0, length, 511)
    closed = case.closed_form(depth, reverse)
    np.testing.assert_allclose(case.boundary(closed[:, 0], closed[:, -1], reverse),
                               0, atol=1e-10)
    np.testing.assert_allclose(case.closed_form(depth, reverse, derivative=True),
                               case.ode(depth, closed, reverse), atol=1e-12)
    numerical = case.numerical(reverse)
    assert numerical.success
    np.testing.assert_allclose(closed, numerical.sol(depth), atol=1e-6, rtol=0)


def test_closed_form_at_large_length_is_finite():
    case = Case(1e5, 30, 15, .001, 100, 10)
    assert np.isfinite(case.closed_form(np.linspace(0, case.length))).all()
    assert np.isfinite(case.closed_form(np.linspace(0, case.length), reverse=True)).all()


def test_formation_temperature_functions():
    assert hasan_kabir_td(1.) == pytest.approx(.78967)
    assert hasan_kabir_td(10.) == pytest.approx(1.6510480993)
    assert ramey_td(100.) == pytest.approx(2.7057322736)
    with pytest.raises(ValueError):
        hasan_kabir_td(0)
