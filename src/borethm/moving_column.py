"""Conservative volume transport and radial recovery for a well column."""
from dataclasses import dataclass

import numpy as np

from .liquid_parcels import Parcels
from .run_in_column import RadialColumn


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

        self._annulus = Parcels(self.annulus_volume.copy(), self.annulus_temperature)
        self._bore = Parcels(self.bore_volume.copy(), self.bore_temperature.copy())

    def _sync_parcels(self):
        self._annulus = self._annulus.with_cell_heat(self.annulus_volume, self.annulus_temperature)
        self._bore = self._bore.with_cell_heat(self.bore_volume, self.bore_temperature)

    def _read_parcels(self):
        self._set_annulus_temperature(self._annulus.averages(self.annulus_volume))
        self.bore_temperature = self._bore.averages(self.bore_volume)

    @property
    def annulus_temperature(self):
        return np.array([node.temperature_C for node in self.rock])

    def _set_annulus_temperature(self, values):
        for node, value in zip(self.rock, values, strict=True):
            node.temperature_C = value

    def descend(self, new_annulus_volume, added_bore_volume, *, float_valve,
                fill_temperature=None):
        """Displace fluid above the entering bit and extend the bore column.

        With a float valve, new pipe and its fill enter from the surface.
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
        intake_volume = 0. if float_valve else added_bore_volume
        if float_valve and added_bore_volume and not np.isfinite(
                fill_temperature if fill_temperature is not None else np.nan):
            raise ValueError("float-valve bore extension requires a finite fill temperature")
        old_end = float(np.sum(self.annulus_volume[:stop]))
        new_end = float(np.sum(new_volume[:stop]))
        exit_volume = old_end-new_end-intake_volume
        if not np.all(np.isfinite(new_volume)) or np.any(new_volume <= 0) or exit_volume < -1e-12:
            raise ValueError("invalid displacement inventory")
        self._sync_parcels()
        affected = self._annulus.slice(0., old_end).reversed()
        unchanged = self._annulus.slice(old_end, self._annulus.size)
        retained = affected.slice(intake_volume, intake_volume+new_end)
        returned = affected.slice(intake_volume+new_end, affected.size)
        self._annulus = retained.reversed().join(unchanged)
        self.annulus_volume = new_volume.copy()
        if added_bore_volume:
            if float_valve:
                entered = Parcels(np.array([added_bore_volume]), np.array([fill_temperature]))
                self._bore = entered.join(self._bore)
                self.bore_volume = np.r_[added_bore_volume, self.bore_volume]
            else:
                self._bore = self._bore.join(affected.slice(0., intake_volume))
                self.bore_volume = np.r_[self.bore_volume, added_bore_volume]
        self._read_parcels()
        return max(0., exit_volume), self.fluid_heat_capacity*returned.inventory

    def regrid_bore(self, volumes):
        """Change bore cell boundaries without mixing the retained parcels."""
        volumes = np.asarray(volumes, dtype=float)
        if (volumes.ndim != 1 or not len(volumes) or not np.all(np.isfinite(volumes))
                or np.any(volumes <= 0.)
                or not np.isclose(np.sum(volumes), np.sum(self.bore_volume), rtol=1e-12, atol=1e-12)):
            raise ValueError("new bore grid must preserve volume")
        self._sync_parcels()
        temperature = self._bore.averages(volumes)
        self.bore_volume = volumes.copy()
        self.bore_temperature = temperature

    def recover(self, duration, films):
        """Advance each wall and liquid state and return heat into the rock."""
        capacity = self.fluid_heat_capacity*self.annulus_volume/self.cell_length
        return sum(length*node.shut_in(duration, cap, film).energy_in
                   for length, node, cap, film in zip(
                       self.cell_length, self.rock, capacity, films, strict=True))

    def restart_step(self, duration, flow, inlet_C, films, *, active_cells=None):
        """Advect the connected bore and annulus, then advance wall exchange.

        Cells below the bit recover without through-flow. Return the surface
        exit inventory and the wall heat in joules.
        """
        active = len(self.rock) if active_cells is None else active_cells
        if not 0 < active <= len(self.rock) or not len(self.bore_volume):
            raise ValueError("circulation needs a bore and a connected annulus")
        pumped = duration*flow
        if not np.isfinite(pumped) or pumped < 0 or not np.isfinite(inlet_C):
            raise ValueError("invalid pumped volume or inlet temperature")
        if not pumped:
            return 0., self.recover(duration, films)
        self._sync_parcels()
        bore_end = float(np.sum(self.bore_volume))
        annulus_end = float(np.sum(self.annulus_volume[:active]))
        total = bore_end+annulus_end
        stagnant = self._annulus.slice(annulus_end, self._annulus.size)
        inlet = Parcels(np.array([pumped]), np.array([inlet_C]))
        circuit = inlet.join(self._bore).join(self._annulus.slice(0., annulus_end).reversed())
        self._bore = circuit.slice(0., bore_end)
        self._annulus = circuit.slice(bore_end, total).reversed().join(stagnant)
        self._read_parcels()
        returned = circuit.slice(total, circuit.size).inventory*self.fluid_heat_capacity
        return returned, self.recover(duration, films)

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

    def exchange_string_tool_heat(self, annulus_index, bore_index, tool, duration,
                                  inside_film, outside_film, *, tool_length):
        """Use the advected bore cell as the layered tool's liquid node."""
        if not 0 < tool_length <= self.cell_length[annulus_index]:
            raise ValueError("tool length must fit within the selected cell")
        node = self.rock[annulus_index]
        outside_capacity = self.fluid_heat_capacity*self.annulus_volume[annulus_index]/tool_length
        bore_capacity = self.fluid_heat_capacity*self.bore_volume[bore_index]/tool_length
        tool.temperature_C[0] = self.bore_temperature[bore_index]
        heat = tool.step(duration, node.temperature_C, inside_film, outside_film,
                         outside_capacity=outside_capacity, bore_capacity=bore_capacity)
        node.temperature_C -= heat/outside_capacity
        self.bore_temperature[bore_index] = tool.temperature_C[0]
        return heat*tool_length

    def exchange_tool_footprint(self, tool, duration, inside_film, outside_film, *,
                                tool_length, annulus_interval, bore_interval):
        """Exchange heat with the liquid over the carrier span in both conduits."""
        self._sync_parcels()
        annulus = self._annulus.slice(*annulus_interval)
        bore = self._bore.slice(*bore_interval)
        if min(annulus.size, bore.size, tool_length) <= 0:
            raise ValueError("tool footprint requires positive volume in both conduits")
        outside = annulus.inventory/annulus.size
        inside = bore.inventory/bore.size
        outside_capacity = self.fluid_heat_capacity*annulus.size/tool_length
        bore_capacity = self.fluid_heat_capacity*bore.size/tool_length
        tool.temperature_C[0] = inside
        heat = tool.step(duration, outside, inside_film, outside_film,
                         outside_capacity=outside_capacity, bore_capacity=bore_capacity)
        self._annulus = self._annulus.heat_interval(
            *annulus_interval, -heat/outside_capacity)
        self._bore = self._bore.heat_interval(*bore_interval, tool.temperature_C[0]-inside)
        self._read_parcels()
        return heat*tool_length
