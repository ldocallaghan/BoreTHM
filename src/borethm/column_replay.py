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
class Move:
    """One part of a moving step: the geometry and contacts at its end."""
    annulus_volume: np.ndarray
    contacts: tuple[ToolContact, ...]
    added_bore_volume: float = 0.
    bore_volume: np.ndarray | None = None
    bit_volumes: tuple[float, float] | None = None
    circuit_end: float | None = None


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
    bit_volumes: tuple[float, float] | None = None
    circuit_end: float | None = None
    exchange_volume: float | None = None
    moves: tuple[Move, ...] = ()
    split: int = 0


@dataclass(frozen=True)
class StepResult:
    elapsed: float
    sensors_C: tuple
    supplied_J: float
    returned_J: float
    into_rock_J: float
    energy_residual_J: float
    samples: tuple = ()


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

    A pumped step with an exchange volume is split so that no more than
    that volume passes between tool exchanges, and liquid shorter than a
    step still meets each tool. The wall recovers once over the step.
    Readings after each part are returned as (time into the step, sensors).

    A moving step may instead give its motion as equal parts (moves). Each
    part descends to its own geometry, pumps its share of the flow and then
    exchanges with the tools at their new contacts, so the liquid displaced
    below the bit passes each tool as pumped liquid does, whatever the step.

    A static step with split = m is advanced in parts of 2**-m, 2**-m,
    2**-(m-1) and so on up to a half of the step, each with its own wall
    recovery and tool exchange. It resolves the fast response that follows
    a change of film, such as the bit stopping, independent of the step.
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

        if step.split and (step.flow or step.moves or step.annulus_volume is not None
                           or not isinstance(step.split, int) or step.split < 0):
            raise ValueError("only a static step can be split, into a whole number of halvings")
        initial = stored_energy(column, step.contacts)
        supplied = returned = 0.
        if step.split:
            samples, rock, into = [], 0., 0.
            for duration in split_durations(step.duration, step.split):
                rock += column.recover(duration, step.wall_films)
                exchange(column, step.contacts, duration)
                into += duration
                samples.append((into, tuple(c.tool.sensor_temperatures() for c in step.contacts)))
            elapsed += step.duration
            residual = stored_energy(column, step.contacts)-initial+rock
            yield StepResult(elapsed, samples[-1][1], 0., 0., rock, residual, tuple(samples))
            continue
        if step.moves:
            if step.annulus_volume is not None or step.bore_volume is not None:
                raise ValueError("a moving step gives its geometry in its parts")
            parts = len(step.moves)
            samples = []
            for number, move in enumerate(step.moves, 1):
                _, out = column.descend(move.annulus_volume, move.added_bore_volume,
                                        float_valve=step.float_valve, fill_temperature=step.fill_C,
                                        bit_volumes=move.bit_volumes)
                returned += out
                if step.float_valve and move.added_bore_volume:
                    supplied += move.added_bore_volume*step.fill_C*column.fluid_heat_capacity
                if move.bore_volume is not None:
                    column.regrid_bore(move.bore_volume)
                if step.flow:
                    pumped = step.duration*step.flow/parts
                    returned += column.advect(pumped, step.inlet_C, active_cells=step.active_cells,
                                              circuit_end=move.circuit_end)
                    supplied += pumped*step.inlet_C*column.fluid_heat_capacity
                exchange(column, move.contacts, step.duration/parts)
                samples.append((number*step.duration/parts,
                                tuple(c.tool.sensor_temperatures() for c in move.contacts)))
            rock = column.recover(step.duration, step.wall_films)
            elapsed += step.duration
            residual = stored_energy(column, step.contacts)-initial-supplied+returned+rock
            yield StepResult(elapsed, samples[-1][1], supplied, returned, rock, residual, tuple(samples))
            continue
        if step.annulus_volume is not None:
            _, returned = column.descend(step.annulus_volume, step.added_bore_volume,
                                         float_valve=step.float_valve,
                                         fill_temperature=step.fill_C,
                                         bit_volumes=step.bit_volumes)
            if step.float_valve and step.added_bore_volume:
                supplied += step.added_bore_volume*step.fill_C*column.fluid_heat_capacity
        if step.bore_volume is not None:
            column.regrid_bore(step.bore_volume)
        samples = []
        if step.flow and step.exchange_volume is not None:
            if not step.exchange_volume > 0:
                raise ValueError("exchange volume must be positive")
            pumped = step.duration*step.flow
            parts = max(1, int(np.ceil(pumped/step.exchange_volume)))
            for part in range(parts):
                returned += column.advect(pumped/parts, step.inlet_C, active_cells=step.active_cells,
                                          circuit_end=step.circuit_end)
                exchange(column, step.contacts, step.duration/parts)
                samples.append(((part+1)*step.duration/parts,
                                tuple(c.tool.sensor_temperatures() for c in step.contacts)))
            supplied += pumped*step.inlet_C*column.fluid_heat_capacity
            rock = column.recover(step.duration, step.wall_films)
        else:
            if step.flow:
                outlet, rock = column.restart_step(
                    step.duration, step.flow, step.inlet_C, step.wall_films,
                    active_cells=step.active_cells, circuit_end=step.circuit_end)
                supplied += step.duration*step.flow*step.inlet_C*column.fluid_heat_capacity
                returned += outlet
            else:
                rock = column.recover(step.duration, step.wall_films)
            exchange(column, step.contacts, step.duration)
        elapsed += step.duration
        residual = stored_energy(column, step.contacts)-initial-supplied+returned+rock
        yield StepResult(elapsed, tuple(c.tool.sensor_temperatures() for c in step.contacts),
                         supplied, returned, rock, residual, tuple(samples))


def split_durations(duration, halvings):
    """Parts of 2**-m, 2**-m, 2**-(m-1), ... 1/2 of a step; they sum to it."""
    return [duration/2**halvings]+[duration/2**k for k in range(halvings, 0, -1)]


def exchange(column, contacts, duration):
    """Exchange heat between each tool and the liquid at its contact."""
    for contact in contacts:
        if contact.footprint is None:
            column.exchange_string_tool_heat(
                contact.annulus_index, contact.bore_index, contact.tool,
                duration, contact.inside_film, contact.outside_film,
                tool_length=contact.length)
        else:
            annulus, bore = contact.footprint
            column.exchange_tool_footprint(
                contact.tool, duration, contact.inside_film, contact.outside_film,
                tool_length=contact.length, annulus_interval=annulus, bore_interval=bore)


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
