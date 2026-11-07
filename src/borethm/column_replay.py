"""Replay prescribed motion, recovery and circulation on the same column."""
from dataclasses import dataclass, replace

import numpy as np

from .layered_tool import LayeredTool
from .moving_column import MovingColumn


@dataclass(frozen=True)
class ToolContact:
    tool: LayeredTool
    length: float
    annulus_index: int
    bore_index: int
    inside_film: float
    outside_film: float
    footprint: tuple[tuple[float, float], tuple[float, float]] | None = None


@dataclass(frozen=True)
class ColumnStep:
    duration: float
    wall_films: tuple[float, ...]
    contacts: tuple[ToolContact, ...] = ()
    annulus_volume: np.ndarray | None = None
    added_bore_volume: float = 0.
    float_valve: bool = False
    fill_C: float | None = None
    flow: float = 0.
    inlet_C: float | None = None
    active_cells: int | None = None
    bore_volume: np.ndarray | None = None


@dataclass(frozen=True)
class StepResult:
    elapsed: float
    sensors_C: tuple
    supplied_J: float
    returned_J: float
    into_rock_J: float
    energy_residual_J: float


def stored_energy(column, contacts):
    liquid = column.fluid_heat_capacity*(
        np.dot(column.annulus_volume, column.annulus_temperature)
        + np.dot(column.bore_volume, column.bore_temperature))
    steel = sum(contact.length*np.dot(contact.tool.capacity[1:],
                                      contact.tool.temperature_C[1:])
                for contact in contacts)
    return liquid + steel


def replay(column: MovingColumn, steps):
    """Yield sensor readings and heat inventories as each step completes.

    The caller supplies time steps, geometry, contact positions and films.
    The radial steel travels with each tool. Its liquid temperature is
    shared with the bore volume used for advection.
    """
    elapsed = 0.
    for step in steps:
        if not np.isfinite(step.duration) or step.duration <= 0:
            raise ValueError("step duration must be finite and positive")
        if (not np.isfinite(step.flow) or step.flow < 0
                or step.flow and (step.inlet_C is None or not np.isfinite(step.inlet_C))):
            raise ValueError("flow must be finite and pump-on requires a finite inlet temperature")
        if step.added_bore_volume and step.annulus_volume is None:
            raise ValueError("bore extension requires new annulus geometry")
        if len(step.wall_films) != len(column.rock):
            raise ValueError("each radial cell needs a wall film")

        initial = stored_energy(column, step.contacts)
        supplied = returned = 0.
        if step.annulus_volume is not None:
            _, returned = column.descend(step.annulus_volume, step.added_bore_volume,
                                         float_valve=step.float_valve,
                                         fill_temperature=step.fill_C)
            if step.float_valve and step.added_bore_volume:
                supplied += step.added_bore_volume*step.fill_C*column.fluid_heat_capacity
        if step.bore_volume is not None:
            column.regrid_bore(step.bore_volume)
        if step.flow:
            outlet, rock = column.restart_step(
                step.duration, step.flow, step.inlet_C, step.wall_films,
                active_cells=step.active_cells)
            supplied += step.duration*step.flow*step.inlet_C*column.fluid_heat_capacity
            returned += outlet
        else:
            rock = column.recover(step.duration, step.wall_films)
        for contact in step.contacts:
            if contact.footprint is None:
                column.exchange_string_tool_heat(
                    contact.annulus_index, contact.bore_index, contact.tool,
                    step.duration, contact.inside_film, contact.outside_film,
                    tool_length=contact.length)
            else:
                annulus, bore = contact.footprint
                column.exchange_tool_footprint(
                    contact.tool, step.duration, contact.inside_film, contact.outside_film,
                    tool_length=contact.length, annulus_interval=annulus, bore_interval=bore)
        elapsed += step.duration
        residual = stored_energy(column, step.contacts)-initial-supplied+returned+rock
        yield StepResult(elapsed, tuple(c.tool.sensor_temperatures() for c in step.contacts),
                         supplied, returned, rock, residual)


def circulation_phases(steps, flush_volume):
    """Split recorded pump steps at the exact restart throughput.

    The throughput is one bore volume plus the annulus volume alongside
    the BHA. The caller supplies that volume from the current geometry.
    Each row is tagged with the calculation to use for its duration.
    """
    if not np.isfinite(flush_volume) or flush_volume <= 0:
        raise ValueError("flush volume must be finite and positive")
    remaining = flush_volume
    for step in steps:
        if step.flow <= 0.:
            remaining = flush_volume
            yield "static", step
            continue
        if remaining <= 0.:
            yield "steady", step
            continue
        pumped = step.flow*step.duration
        if pumped <= remaining:
            remaining -= pumped
            yield "restart", step
            continue
        transient_time = remaining/step.flow
        yield "restart", replace(step, duration=transient_time)
        yield "steady", replace(step, duration=step.duration-transient_time,
                                annulus_volume=None, added_bore_volume=0., bore_volume=None)
        remaining = 0.
