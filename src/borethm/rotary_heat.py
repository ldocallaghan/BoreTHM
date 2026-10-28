"""Heat from rotating the drill string, placed by a soft-string torque balance.

Surface rotary power P = omega T (omega = 2 pi RPM / 60, T the top-drive
torque) becomes heat in the well. Part is friction where the string touches
the casing or rock; the rest turns the bit. The split follows the soft-string
torque model of Johancsik, Friesen and Dawson (1984). For a rotating string
with no axial motion, an element of length ds with tension F, buoyed weight w
per unit length, inclination theta and azimuth phi presses on the wall with
force per unit length

    w_n = sqrt( (F sin(theta) dphi/ds)^2 + (w sin(theta) - F dtheta/ds)^2 )

where s is measured depth, so dtheta/ds is positive where the hole builds
angle. In a build the tension pulls the string towards the inside of the bend,
the high side, while the weight presses it to the low side, so the two terms
oppose. Tension changes by w cos(theta) ds over each element, starting from
-WOB at the bit. Friction torque is mu w_n r per unit length, with r the
contact radius (tool-joint radius where the pipe has joints).

The friction factor mu is set for each sample from the measured off-bottom
rotating torque (no weight on bit). The same mu then gives the on-bottom
friction torque; the remainder of the measured on-bottom torque turns the
bit. Friction heat is released into the annulus fluid where it is generated,
in proportion to w_n r; bit heat is released at the bit. Viscous drag from
rotation is part of the measured torque and is placed with the friction.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

STEEL_DENSITY = 7850.0          # kg/m3
GRAVITY = 9.80665               # m/s2
FT_LBF = 1.3558179483314004     # N m
KLBF = 4448.2216152605          # N


def stations(md, inc_deg, azi_deg, grid):
    """Inclination and azimuth [rad] interpolated onto grid [m]."""
    azi = np.unwrap(np.radians(azi_deg))
    return np.interp(grid, md, np.radians(inc_deg)), np.interp(grid, md, azi)


def string_properties(geometry, grid):
    """Weight in air per unit length [N/m] and contact radius [m] along grid.

    All wall layers are taken as steel. Hydraulic connections add their
    extra steel over the connection length divided by the pitch, and set the
    contact radius to the connection's outside radius.
    """
    weight = np.zeros_like(grid)
    radius = np.zeros_like(grid)
    top = 0.0
    for segment in geometry.string:
        bottom = top + segment.length
        mask = (grid >= top) & (grid <= bottom)
        layers = segment.pipe.layers
        area = sum(np.pi*(l.r_out**2-l.r_in**2) for l in layers)
        outer = max(l.r_out for l in layers)
        joint = segment.pipe.hydraulic_joint
        if joint is not None:
            extra = np.pi/4*(joint.outer_diameter**2-joint.bore_diameter**2)-area
            area += max(extra, 0.0)*joint.restriction_length/joint.spacing
            outer = max(outer, joint.outer_diameter/2)
        weight[mask] = STEEL_DENSITY*GRAVITY*area
        radius[mask] = outer
        top = bottom
    return weight, radius


def contact_force(grid, inc, azi, buoyed_weight, wob):
    """Soft-string wall force per unit length [N/m] for a rotating string."""
    ds = np.diff(grid)
    theta = 0.5*(inc[1:]+inc[:-1])
    dtheta, dphi = np.diff(inc)/ds, np.diff(azi)/ds
    w = 0.5*(buoyed_weight[1:]+buoyed_weight[:-1])
    lower = np.empty_like(ds)
    tension = -float(wob)
    for i in range(len(ds)-1, -1, -1):
        lower[i] = tension
        tension += w[i]*np.cos(theta[i])*ds[i]
    mid = lower+0.5*w*np.cos(theta)*ds
    return np.sqrt((mid*np.sin(theta)*dphi)**2+(w*np.sin(theta)-mid*dtheta)**2)


@dataclass
class RotaryHeat:
    """Heat released by string rotation.

    bit_W is released at the bit. annulus(md) returns heat per unit length
    [W/m] released into the annulus fluid. friction_factor is the value
    implied by the off-bottom torque; capped is True when the calculated
    on-bottom friction exceeded the measured torque and was scaled down.
    """
    bit_W: float
    friction_W: float
    friction_factor: float
    capped: bool
    grid: np.ndarray
    density: np.ndarray

    def annulus(self, md):
        return np.interp(md, self.grid, self.density)


def partition(geometry, survey_md, inc_deg, azi_deg, mud_density, rpm, torque_on, torque_off,
              wob_on, friction_factor=None, step=2.0, smoothing=30.0):
    """Split measured surface rotary power into wall friction and bit work.

    survey stations are in m and degrees. rpm is the on-bottom surface speed,
    torque_on and torque_off are surface torques [N m], wob_on is the
    on-bottom weight on bit [N] and mud_density is kg/m3. If torque_off is
    None, friction_factor must be given. The friction heat is averaged over
    a running window of smoothing [m], about one survey-station spacing, so
    that changes of curvature at stations do not make the source jump; the
    total is unchanged.
    """
    L = geometry.md_bit
    grid = np.unique(np.r_[np.arange(0.0, L, step), L])
    inc, azi = stations(survey_md, inc_deg, azi_deg, grid)
    weight, radius = string_properties(geometry, grid)
    buoyed = weight*(1.0-mud_density/STEEL_DENSITY)
    r_mid = 0.5*(radius[1:]+radius[:-1])
    ds = np.diff(grid)
    lever_off = np.sum(contact_force(grid, inc, azi, buoyed, 0.0)*r_mid*ds)
    lever_on = contact_force(grid, inc, azi, buoyed, wob_on)*r_mid
    if torque_off is not None:
        if lever_off <= 0:
            raise ValueError('no wall contact force: the friction factor is undefined')
        friction_factor = float(torque_off)/lever_off
    elif friction_factor is None:
        raise ValueError('give an off-bottom torque or a friction factor')
    omega = 2*np.pi*float(rpm)/60.0
    friction_torque = friction_factor*np.sum(lever_on*ds)
    capped = friction_torque > torque_on
    scale = float(torque_on)/friction_torque if capped and friction_torque > 0 else 1.0
    per_length = omega*friction_factor*scale*lever_on
    friction_W = float(np.sum(per_length*ds))
    width = max(int(round(smoothing/step)), 1)
    if width > 1 and friction_W > 0:
        kernel = np.ones(width)
        spread = np.convolve(per_length*ds, kernel, 'same')/np.convolve(ds, kernel, 'same')
        per_length = spread*friction_W/np.sum(spread*ds)
    bit_W = max(omega*float(torque_on)-friction_W, 0.0)
    centres = 0.5*(grid[1:]+grid[:-1])
    return RotaryHeat(bit_W, friction_W, float(friction_factor), bool(capped), centres, per_length)
