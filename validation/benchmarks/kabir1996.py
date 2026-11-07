"""Closed-form circulation profiles from the Kabir et al. energy balances."""
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_bvp
from scipy.optimize import brentq


def hasan_kabir_td(t_d):
    """Appendix A dimensionless formation temperature for positive time."""
    t_d = np.asarray(t_d, dtype=float)
    if np.any(t_d < 1e-10):
        raise ValueError("dimensionless time must be at least 1e-10")
    root = np.sqrt(t_d)
    return np.where(t_d <= 1.5, 1.1281 * root * (1 - 0.3 * root),
                    (0.4063 + 0.5 * np.log(t_d)) * (1 + 0.6 / t_d))


def ramey_td(t_d):
    """Appendix A long-time approximation."""
    return np.log(2 * np.sqrt(t_d)) - 0.29


@dataclass(frozen=True)
class Case:
    length: float
    inlet: float
    surface: float
    gradient: float
    A: float
    B: float

    @classmethod
    def from_properties(cls, length, inlet, surface, gradient, mass_cp,
                        k_rock, radius, ua, rt, ut, t_d_temperature):
        return cls(length, inlet, surface, gradient,
                   mass_cp * (1 / (radius * ua) + t_d_temperature / k_rock) / (2 * np.pi),
                   mass_cp / (2 * np.pi * rt * ut))

    def ode(self, z, y, reverse=False):
        pipe, annulus = y
        coupling = (annulus - pipe) / self.B
        rock = (self.surface + self.gradient * z - annulus) / self.A
        return (-1 if reverse else 1) * np.array((coupling, coupling - rock))

    def boundary(self, top, bottom, reverse=False):
        return np.array((top[int(reverse)] - self.inlet, bottom[0] - bottom[1]))

    def closed_form(self, z, reverse=False, derivative=False):
        """Eliminate annulus temperature using the pipe energy equation.

        For s=+1 (forward) or -1 (reverse), Ta=Tt+s B Tt'.
        The resulting equation is AB Tt''-s B Tt'-Tt=-Tei+s B g.
        A linear particular solution is Tei-s B g. Anchor the positive
        exponential at the bottom and the negative one at the surface.
        """
        z = np.asarray(z)
        if np.any((z < 0) | (z > self.length)):
            raise ValueError("depth outside the well")
        sign = -1 if reverse else 1
        a, b, length = self.A, self.B, self.length
        delta = np.sqrt(1 + 4 * a / b)
        rates = np.array(((sign + delta) / (2 * a), (sign - delta) / (2 * a)))
        at_top = np.array((np.exp(-rates[0] * length), 1.))
        at_bottom = np.array((1., np.exp(rates[1] * length)))
        annulus_factors = 1 + sign * b * rates
        top_factors = annulus_factors if reverse else np.ones(2)
        top_particular = self.surface if reverse else self.surface - b * self.gradient
        amplitude = np.linalg.solve(
            np.array((at_top * top_factors, rates * at_bottom)),
            np.array((self.inlet - top_particular, -self.gradient)),
        )
        terms = np.stack((np.exp(rates[0] * (z - length)), np.exp(rates[1] * z)), axis=-1)
        if derivative:
            return np.array((terms @ (amplitude * rates) + self.gradient,
                             terms @ (amplitude * rates * annulus_factors) + self.gradient))
        formation = self.surface + self.gradient * z
        return np.array((terms @ amplitude + formation - sign * b * self.gradient,
                         terms @ (amplitude * annulus_factors) + formation))

    def numerical(self, reverse=False):
        z = np.linspace(0, self.length, 150)
        seed = np.full((2, len(z)), self.inlet)
        return solve_bvp(lambda x, y: self.ode(x, y, reverse),
                         lambda top, end: self.boundary(top, end, reverse),
                         z, seed, tol=1e-10, max_nodes=20000)

    def annulus_maximum(self):
        """Return depth and temperature of the forward annulus maximum."""
        grid = np.linspace(0, self.length, 1001)
        d = self.closed_form(grid, derivative=True)[1]
        brackets = zip(grid[:-1][d[:-1] * d[1:] < 0], grid[1:][d[:-1] * d[1:] < 0])
        candidates = [0., self.length, *(brentq(lambda z: self.closed_form(z, derivative=True)[1],
                                                lo, hi) for lo, hi in brackets)]
        depth = max(candidates, key=lambda z: self.closed_form(z)[1])
        return depth, float(self.closed_form(depth)[1])
