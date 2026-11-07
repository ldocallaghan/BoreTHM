"""Optional radial column history and conservative fluid displacement.

Zhang et al. (2026), Geothermics 136, 103598, Eqs. 4–25 track fluid by
occupied volume. This implementation works in volume coordinates, so
it uses the current string geometry when the string moves. The radial
heat calculation is delegated to wall_thermal.run.
"""
from dataclasses import dataclass, field

import numpy as np

from . import wall_thermal


@dataclass
class RadialColumn:
    """A depth node with its own exposure clock and rock temperature field.

    Geometry and material properties are in SI. The wall radius is
    the fluid-side radius. A casing resistance, if supplied, is per metre
    of well in series with the film. This approximation has no casing
    heat capacity. The fluid capacity is per metre of well.
    """
    radius: float
    formation_C: float
    conductivity: float
    rock_heat_capacity: float
    history_horizon_s: float
    radial_nodes: int = 200
    casing_resistance: float = 0.
    temperature_C: float | None = None
    rock: np.ndarray | None = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if (min(self.radius, self.conductivity, self.rock_heat_capacity,
                self.history_horizon_s) <= 0 or self.radial_nodes < 2
                or self.casing_resistance < 0):
            raise ValueError("invalid radial column geometry or material properties")
        if self.temperature_C is None:
            self.temperature_C = self.formation_C

    def _film(self, film):
        if np.isnan(film) or film < 0:
            raise ValueError("film coefficient must be non-negative")
        if film == 0 or self.casing_resistance == 0:
            return film
        return 1/(1/film + 2*np.pi*self.radius*self.casing_resistance)

    def _advance(self, duration, state):
        if duration <= 0 or not np.isfinite(duration):
            raise ValueError("duration must be positive and finite")
        radius = wall_thermal.r_max_for(
            self.radius, self.conductivity/self.rock_heat_capacity, self.history_horizon_s)
        result = wall_thermal.run([state], self.formation_C, self.radius,
                                  self.conductivity, self.rock_heat_capacity,
                                  n=self.radial_nodes, r_max=radius, T0=self.rock)
        self.rock = result.fields[-1]
        return result

    def circulate(self, duration, fluid_C, film):
        """Advance a prescribed circulating interval at the node."""
        h = self._film(film)
        if np.isinf(h):
            state = wall_thermal.State("fixed", duration, T_wall=fluid_C)
        else:
            state = wall_thermal.State("circulating", duration, T_fluid=fluid_C, h=h)
        result = self._advance(duration, state)
        self.temperature_C = fluid_C
        return result

    def shut_in(self, duration, capacity, film):
        """Advance recovery and carry the liquid and rock states forward."""
        h = self._film(film)
        if capacity <= 0 or not np.isfinite(capacity) or not np.isfinite(h):
            raise ValueError("static capacity must be positive and the film finite")
        state = wall_thermal.State("static", duration, h=h, C=capacity,
                                   T_node0=self.temperature_C)
        result = self._advance(duration, state)
        self.temperature_C = float(result.T_node[-1])
        return result


def gap_rayleigh(gap, delta_C, density, cp, viscosity, conductivity, expansion):
    """Rayleigh number based on the radial gap and local fluid properties."""
    return 9.80665 * expansion * abs(delta_C) * gap**3 * density**2 * cp / (viscosity*conductivity)


def static_annulus_films(r_inner, r_wall, height, delta_C, density, cp,
                         viscosity, conductivity, expansion):
    """Return laminar floor, convection sensitivity and applicability.

    The floor uses BoreTHM's Nu=4.36 on the hydraulic diameter. The
    convective case uses Thomas and de Vahl Davis (1970), Eqs. 2–4 as
    reproduced by Keyhani, Kulacki and Christensen (1983),
    doi:10.1115/1.3245606. The correlations use the gap, with published
    bounds 1–10 on radius ratio, 1–33 on aspect ratio, 0.5–10000 on Pr
    and Ra up to 2e5. The regime boundaries quoted in that source use
    Pr=1 and do not cover all heights. The code flags intermediate regimes
    and extrapolation beyond the reported ranges.
    """
    gap = r_wall-r_inner
    if not 0 < r_inner < r_wall or min(height, density, cp, viscosity, conductivity) <= 0:
        raise ValueError("invalid annulus geometry or fluid properties")
    pr = cp*viscosity/conductivity
    ra = gap_rayleigh(gap, delta_C, density, cp, viscosity, conductivity, expansion)
    ratio, aspect = r_wall/r_inner, height/gap
    floor = wall_thermal.NU_LAMINAR*conductivity/(2*gap)
    if ra == 0:
        return floor, floor, ra, False
    if aspect > 5 and ra/aspect <= 400:
        nu = .595*ra**.101*pr**.024*aspect**(-.052)*ratio**.505
        regime_supported = True
    elif aspect <= 5 and ra/aspect >= 3000:
        nu = .286*ra**.258*pr**.006*aspect**(-.238)*ratio**.442
        regime_supported = True
    else:
        nu = .202*ra**.294*pr**.097*aspect**(-.264)*ratio**.423
        regime_supported = False
    supported = (regime_supported and 1 <= ratio <= 10 and 1 <= aspect <= 33
                 and .5 <= pr <= 1e4 and ra <= 2e5)
    return floor, max(floor, nu*conductivity/gap), ra, supported


def volume_remap(source_volumes, source_values, target_volumes, *, start=0.):
    """Volume-average a conserved scalar over a contiguous slice of parcels."""
    source_volumes, source_values, target_volumes = (
        np.asarray(x, dtype=float) for x in (source_volumes, source_values, target_volumes))
    if (source_volumes.ndim != 1 or target_volumes.ndim != 1
            or source_values.shape != source_volumes.shape
            or not len(source_volumes) or np.any(source_volumes <= 0)
            or np.any(target_volumes <= 0)
            or any(not np.all(np.isfinite(x)) for x in
                   (source_volumes, source_values, target_volumes))):
        raise ValueError("parcel volumes must be positive and values finite")
    edges = np.r_[0., np.cumsum(source_volumes)]
    requested = start + np.r_[0., np.cumsum(target_volumes)]
    if not np.isfinite(start) or start < 0 or requested[-1] > edges[-1]*(1+1e-12):
        raise ValueError("requested parcels lie outside the source volume")
    inventory = np.r_[0., np.cumsum(source_volumes*source_values)]
    return np.diff(np.interp(requested, edges, inventory))/target_volumes


def displace_annulus(old_volume, old_temperature, new_volume, *, bore_intake=0.):
    """Move old liquid towards surface as the external string volume grows.

    Arrays are in deepest-to-shallowest order. Call on the part of the
    column affected by the advance. Intake, if present, is withdrawn
    first from the deepest end of this slice, at the entering bore.
    The unretained remainder exits at surface. Return its volume and
    temperature inventory as well as the intake inventory.
    """
    old_volume, old_temperature, new_volume = (
        np.asarray(x, dtype=float) for x in (old_volume, old_temperature, new_volume))
    updated = volume_remap(old_volume, old_temperature, new_volume, start=bore_intake)
    intake = (bore_intake*volume_remap(old_volume, old_temperature, [bore_intake])[0]
              if bore_intake else 0.)
    exit_volume = max(0., np.sum(old_volume)-np.sum(new_volume)-bore_intake)
    exit_inventory = np.dot(old_volume, old_temperature)-np.dot(new_volume, updated)-intake
    return updated, intake, exit_volume, exit_inventory


def pump_on_step(volumes, temperatures, pumped_volume, inlet_C):
    """Advance plug flow down the bore and back up the annulus by volume.

    The sequence starts at the inlet, turns at the bit, and ends at the
    surface return. The returned inventory is volume times temperature.
    It gives sensible heat when multiplied by constant volumetric heat
    capacity. Wall exchange can advance separately between flow steps.
    """
    if not np.isfinite(pumped_volume) or pumped_volume < 0:
        raise ValueError("pumped volume must be finite and non-negative")
    if not pumped_volume:
        return np.array(temperatures, dtype=float, copy=True), 0.
    source = np.r_[pumped_volume, volumes]
    values = np.r_[inlet_C, temperatures]
    updated = volume_remap(source, values, volumes)
    returned = pumped_volume*volume_remap(source, values, [pumped_volume],
                                         start=np.sum(volumes))[0]
    return updated, returned
