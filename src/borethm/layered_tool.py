"""Radial steel and bore-fluid heat storage for the optional run-in model.

Zhang et al. (2026), Geothermics 136, 103598, Eqs. 26–52.
"""
from dataclasses import dataclass, field

import numpy as np
from scipy.linalg import solve_banded

from .tool_thermal import STEEL_CP, STEEL_RHO
from .well_geometry import K_STEEL


def displacement_film(r_tool, r_hole, speed, density, cp, viscosity, conductivity):
    """Annulus film for flow displaced by a descending cylindrical tool."""
    gap = 2*(r_hole-r_tool)
    velocity = abs(speed)*r_tool**2/(r_hole**2-r_tool**2)
    reynolds = density*velocity*gap/viscosity
    prandtl = cp*viscosity/conductivity
    if reynolds <= 2300:
        nusselt = 4.9057*(r_tool/r_hole)**(-.313)
    else:
        friction = (.790*np.log(reynolds)-1.64)**-2
        nusselt = ((friction/8)*(reynolds-1000)*prandtl
                   / (1+12.7*np.sqrt(friction/8)*(prandtl**(2/3)-1)))
    return conductivity*nusselt/gap


@dataclass
class LayeredTool:
    """Fluid node and concentric steel cells, with capacities per metre."""

    bore_radius: float
    outer_radius: float
    fluid_heat_capacity: float
    initial_C: float
    layers: int = 8
    temperature_C: np.ndarray = field(init=False, repr=False)

    def __post_init__(self):
        if not 0 < self.bore_radius < self.outer_radius or self.layers < 2:
            raise ValueError("invalid tool geometry")
        if self.fluid_heat_capacity <= 0:
            raise ValueError("fluid heat capacity must be positive")
        self.faces = np.linspace(self.bore_radius, self.outer_radius, self.layers + 1)
        self.centres = np.sqrt((self.faces[:-1]**2+self.faces[1:]**2)/2)
        self.capacity = np.r_[np.pi*self.bore_radius**2*self.fluid_heat_capacity,
                              STEEL_RHO*STEEL_CP*np.pi*np.diff(self.faces**2)]
        self.temperature_C = np.full(self.layers + 1, self.initial_C, dtype=float)
        self.inside_surface_C = self.outside_surface_C = self.initial_C

    def step(self, duration, outside_C, inside_film, outside_film, *, outside_capacity=np.inf):
        """Return heat from the exterior per metre over an implicit step."""
        if duration <= 0 or min(inside_film, outside_film) < 0 or outside_capacity <= 0:
            raise ValueError("positive duration and non-negative films required")
        resistance = np.log(self.centres[0]/self.bore_radius)/(2*np.pi*K_STEEL)
        inner = (1/(resistance + 1/(2*np.pi*self.bore_radius*inside_film))
                 if inside_film else 0.)
        conductance = np.r_[inner, 2*np.pi*K_STEEL/np.log(
            self.centres[1:]/self.centres[:-1])]
        resistance = np.log(self.outer_radius/self.centres[-1])/(2*np.pi*K_STEEL)
        outer = (1/(resistance + 1/(2*np.pi*self.outer_radius*outside_film))
                 if outside_film else 0.)
        outer = outer/(1+outer*duration/outside_capacity)
        diagonal = self.capacity/duration
        rhs = diagonal*self.temperature_C
        diagonal[:-1] += conductance
        diagonal[1:] += conductance
        diagonal[-1] += outer
        rhs[-1] += outer*outside_C
        matrix = np.array([np.r_[0., -conductance], diagonal, np.r_[-conductance, 0.]])
        self.temperature_C = solve_banded((1, 1), matrix, rhs)
        heat = outer*(outside_C-self.temperature_C[-1])*duration
        outside_end = outside_C - heat/outside_capacity
        self.outside_surface_C = (
            outside_end - heat/duration/(2*np.pi*self.outer_radius*outside_film)
            if outside_film else self.temperature_C[-1])
        self.inside_surface_C = (self.temperature_C[0]
                                 + inner*(self.temperature_C[1]-self.temperature_C[0])
                                 /(2*np.pi*self.bore_radius*inside_film)
                                 if inside_film else self.temperature_C[1])
        return heat

    def sensor_temperatures(self):
        """Bore fluid, inside steel surface, mid-wall and outside steel surface."""
        mid = (self.bore_radius+self.outer_radius)/2
        steel = np.interp(mid, self.centres, self.temperature_C[1:])
        return self.temperature_C[0], self.inside_surface_C, steel, self.outside_surface_C
