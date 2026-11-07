"""Conservative volume transport and radial recovery for a well column."""
from dataclasses import dataclass

import numpy as np

from .run_in_column import RadialColumn, displace_annulus, pump_on_step


@dataclass
class MovingColumn:
    """Annulus cells ordered surface to bottom with one radial state each.

    The drill string contains fluid in a separate top-to-bottom volume
    grid. A fixed volumetric heat capacity converts inventories to energy.
    """
    rock: list[RadialColumn]
    cell_length: np.ndarray
    annulus_volume: np.ndarray
    fluid_heat_capacity: float
    bore_volume: np.ndarray
    bore_temperature: np.ndarray

    def __post_init__(self):
        for name in ("cell_length", "annulus_volume", "bore_volume", "bore_temperature"):
            setattr(self, name, np.asarray(getattr(self, name), dtype=float))
        if (len(self.rock) != len(self.cell_length)
                or self.cell_length.shape != self.annulus_volume.shape
                or self.bore_volume.shape != self.bore_temperature.shape
                or min(self.fluid_heat_capacity, *self.cell_length, *self.annulus_volume,
                       *self.bore_volume) <= 0):
            raise ValueError("inconsistent column volumes or heat capacity")

    @property
    def annulus_temperature(self):
        return np.array([node.temperature_C for node in self.rock])

    def _set_annulus_temperature(self, values):
        for node, value in zip(self.rock, values, strict=True):
            node.temperature_C = value

    def descend(self, new_annulus_volume, added_bore_volume, *, float_valve,
                fill_temperature=None):
        """Displace fluid above the entering bit and extend the bore column.

        With a float valve the new bore inventory is supplied by the caller.
        Without it, new bore volume is taken at the deepest displaced cell.
        Return the surface exit volume and sensible-heat inventory (joules
        relative to 0 °C).
        """
        new_volume = np.asarray(new_annulus_volume, dtype=float)
        if new_volume.shape != self.annulus_volume.shape or added_bore_volume < 0:
            raise ValueError("invalid displacement geometry")
        changed = np.flatnonzero(new_volume != self.annulus_volume)
        if not len(changed):
            if added_bore_volume:
                raise ValueError("bore extension requires annulus displacement")
            return 0., 0.
        stop = changed[-1] + 1
        affected = slice(stop-1, None, -1)
        temperature = self.annulus_temperature
        intake_volume = 0. if float_valve else added_bore_volume
        if float_valve and added_bore_volume and fill_temperature is None:
            raise ValueError("float-valve bore extension requires a fill temperature")
        updated, intake, exit_volume, exit_inventory = displace_annulus(
            self.annulus_volume[affected], temperature[affected],
            new_volume[affected], bore_intake=intake_volume)
        temperature[affected] = updated
        self._set_annulus_temperature(temperature)
        self.annulus_volume = new_volume.copy()
        if added_bore_volume:
            entered = fill_temperature if float_valve else intake/added_bore_volume
            self.bore_volume = np.r_[self.bore_volume, added_bore_volume]
            self.bore_temperature = np.r_[self.bore_temperature, entered]
        return exit_volume, self.fluid_heat_capacity*exit_inventory

    def recover(self, duration, films):
        """Advance each wall and liquid state and return heat into the rock."""
        capacity = self.fluid_heat_capacity*self.annulus_volume/self.cell_length
        return sum(length*node.shut_in(duration, cap, film).energy_in
                   for length, node, cap, film in zip(
                       self.cell_length, self.rock, capacity, films, strict=True))

    def restart_step(self, duration, flow, inlet_C, films):
        """Advect the connected bore and annulus, then advance wall exchange.

        The grid must end at the bit during circulation. Return the surface
        exit inventory and the wall heat in joules.
        """
        count = len(self.bore_volume)
        volumes = np.r_[self.bore_volume, self.annulus_volume[::-1]]
        values = np.r_[self.bore_temperature, self.annulus_temperature[::-1]]
        advected, returned = pump_on_step(volumes, values, duration*flow, inlet_C)
        self.bore_temperature = advected[:count]
        self._set_annulus_temperature(advected[count:][::-1])
        return returned*self.fluid_heat_capacity, self.recover(duration, films)


    def exchange_tool_heat(self, index, tool, duration, inside_film, outside_film, *, tool_length):
        """Exchange heat with a tool at the chosen depth without losing energy."""
        node = self.rock[index]
        if not 0 < tool_length <= self.cell_length[index]:
            raise ValueError("tool length must fit within the selected cell")
        capacity = self.fluid_heat_capacity*self.annulus_volume[index]/tool_length
        heat = tool.step(duration, node.temperature_C, inside_film, outside_film,
                         outside_capacity=capacity)
        node.temperature_C -= heat/capacity
        return heat*tool_length
