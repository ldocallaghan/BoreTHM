"""Heat conduction into the rock around a circulating well.

A cylindrical hole of radius a in an infinite, initially uniform rock has its
wall temperature changed by a step at t = 0 and held. The heat flow per unit
length is q = 2 pi k dT G(t_D), with t_D = alpha t / a^2. In the Laplace
domain (variable s, conjugate to t_D) the dimensionless flux is

    G(s) = K1(sqrt(s)) / (sqrt(s) K0(sqrt(s)))

(Carslaw and Jaeger, Conduction of Heat in Solids, 2nd edition, 1959). The
step resistance per unit length is 1 / (2 pi k G(t_D)).

The legacy treatment uses ln(1 + 2 sqrt(t_D)) in place of 1/G(t_D), the
quasi-steady logarithm with a conduction radius a + 2 sqrt(alpha t). It is
retained as 'logarithmic' for reproducing earlier calculations.

G(t_D) is evaluated once, on a grid, by the fixed Talbot inversion (Abate and
Valko, International Journal for Numerical Methods in Engineering 60, 2004,
979-993), and interpolated in log-log coordinates.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy import special

RESPONSES = ('logarithmic', 'cylinder')
LOG10_TD_MIN = -6.0
LOG10_TD_MAX = 12.0
_STEP = 0.02
_TALBOT_M = 32


def _laplace_flux(s):
    root = np.sqrt(s)
    return special.kve(1, root) / (root * special.kve(0, root))


def talbot_flux(t_d, terms=_TALBOT_M):
    """Dimensionless wall flux G(t_D) by fixed Talbot inversion (array input)."""
    t_d = np.atleast_1d(np.asarray(t_d, float))
    r = 2.0 * terms / (5.0 * t_d)
    theta = np.arange(1, terms) * np.pi / terms
    cot = 1.0 / np.tan(theta)
    s = r[:, None] * theta * (cot + 1j)
    sigma = theta + (theta * cot - 1.0) * cot
    body = np.exp(t_d[:, None] * s) * _laplace_flux(s) * (1.0 + 1j * sigma)
    first = 0.5 * np.exp(r * t_d) * _laplace_flux(r + 0j).real
    return (r / terms) * (first + body.real.sum(axis=1))


@lru_cache(maxsize=1)
def _table():
    x = np.arange(LOG10_TD_MIN, LOG10_TD_MAX + 0.5 * _STEP, _STEP)
    return x, np.log(talbot_flux(10.0 ** x))


def cylinder_flux(t_d):
    """Dimensionless wall flux G(t_D) for a constant wall-temperature step."""
    t_d = np.asarray(t_d, float)
    x = np.log10(t_d)
    if np.any(~np.isfinite(x)) or np.any(x < LOG10_TD_MIN) or np.any(x > LOG10_TD_MAX):
        raise ValueError(f'dimensionless time outside 1e{LOG10_TD_MIN:g} to 1e{LOG10_TD_MAX:g}')
    grid, values = _table()
    return np.exp(np.interp(x, grid, values))


def resistance(t, alpha, radius, k_rock, response='cylinder'):
    """Rock thermal resistance per unit length [m K/W] after exposure t [s]."""
    t_d = alpha * np.asarray(t, float) / radius ** 2
    if response == 'logarithmic':
        return np.log(1.0 + 2.0 * np.sqrt(t_d)) / (2 * np.pi * k_rock)
    if response == 'cylinder':
        return 1.0 / (2 * np.pi * k_rock * cylinder_flux(t_d))
    raise ValueError(f'rock response must be one of {RESPONSES}')
