"""Model-only run 17 event histories on the tally-entry depths.

Every axial cell from surface to the deepest hole carries its own radial
rock field. Its history runs from the run 16 makeup through the 10 s Pason
record: circulating while the pumps run above PUMPS_ON_GPM with the bit
below the cell, at the annulus temperature and film of the circulation
solution for the state's mean bit depth and its pumping spell's median
flow and mean inlet, and static otherwise at the chosen coupling limit.
Circulation is taken as steady from pump-on, as in v1.8.0. Circulation before the window is one lumped spell, followed by a
static interval to the window start, as in the v1.8.0 pause study.

Each event then replays on the moving column from its own snapshot of
that history: the recorded descent with parcel displacement, the pause,
and the restart by volume advection until one string volume plus the BHA
annulus volume has passed. After that handover the circulation solution
for the restart flow and depth is prescribed until the end of the
following circulation (trip stages) or five minutes after pump-on
(connections).

The axial cells are uniform, joined by fixed faces at the deepest bit
position of every pumping spell around an event and at each event's
starting bit, so the boundary between circulated liquid above the bit
and static liquid below it does not move with the cell size. The tools
exchange heat with the liquid parcels along their own carrier span, the
descent intake and the restart circuit turn at the bit itself, and the
prescribed circulation is read at the sensor depth. The radial rock
nodes are concentrated at the wall (grid power 2).

The calculation reads time, bit and hole depth, pump output and inlet
temperature only. It reads no sensor temperature.
"""
import argparse
import copy
import csv
import hashlib
import importlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from borethm.column_replay import ColumnStep, Move, ToolContact, replay
from borethm.layered_tool import LayeredTool, displacement_film
from borethm.moving_column import MovingColumn
from borethm.run_in_column import RadialColumn
from borethm.wall_thermal import NU_LAMINAR
from borethm.studies.pressure_comparison import assembly_audit
from validation.benchmarks.run_circulation import write_csv
from validation.forge16b.sanvean.build_extracts import iso, timestamp

audit = importlib.import_module(f"{__package__}.run17_rayleigh")
rig = importlib.import_module(f"{__package__}.run17_boundaries")
descent = importlib.import_module(f"{__package__}.run17_descent")
flush_module = importlib.import_module(f"{__package__}.run17_flush")
model = audit.model
b = audit.forge16b
HERE = Path(__file__).parent

CAPACITY = 4.18e6                 # fixed water volumetric heat capacity, as the pilots
PUMPS_ON_GPM = 100.               # pumping threshold of the boundary ledger
WINDOW_START = timestamp("2023-05-20 00:38:30")   # run 16 makeup, Pason clock
SPLIT_S = 1800.                   # longest circulating state before a new profile
RESTART_S = 300.                  # the restart window of D3 and D4
BIT_OFFSET_FT = .625              # middle of the 1.25 ft bit contact
MERGE_FT = .01                    # bit depths closer than this share one fixed face
GRADE_LEVELS = 6                  # halvings of the cell length above each fixed face
SHALLOW_FT = 1500.                # longer than the run 16 and 17 assemblies


@dataclass
class Config:
    cells: int = 80
    radial: int = 40
    cap_s: float = 1.25
    mixed: bool = False           # False: laminar film (slow); True: well-mixed (fast)
    float_valve: bool = False
    grid_power: float = 2.        # radial nodes at a (r_max/a)^(xi^2), concentrated at the wall
    exchange_parts: int = 2       # tool exchanges per smallest footprint volume pumped past


def run_of(stamp):
    """Assembly in the hole at a Pason time: run 16 until its trip out ends."""
    return 16 if stamp < timestamp("2023-05-21 02:07:40") else 17


class Profiles:
    """Circulation solutions cached on run, bit depth, flow and inlet.

    This is also the well adapter of the event engine: the history and
    replay ask it for the assembly in the hole at a time, the event
    geometry, the sensor contacts and the restart flush volume.
    """

    clock_bin_s = 600.            # resolution of the circulation clock

    def __init__(self, cache=None):
        self.plan = audit.read_json(audit.PLAN)
        self.form = audit.forge16a.formation("216", audit.forge16a.survey())[0]
        _, self.time, self.clock, self.depth = audit.whole.clock(audit.FORGE)
        self.defs = {int(r["eow_bha"]): r for r in audit.rows(audit.FORGE/"run_definitions.csv")}
        self.cache = Path(cache) if cache else None
        self.memory = {}
        self.geometries = {}

    def key(self, stamp, bit_ft, flow_gpm, inlet_F):
        return (run_of(stamp), max(round(bit_ft/200.)*200., SHALLOW_FT),
                max(round(flow_gpm/25.)*25., PUMPS_ON_GPM), round(inlet_F/2.)*2.,
                round(stamp/3600.)*3600)

    def geometry(self, run, bit_ft):
        key = run, round(float(bit_ft))
        if key not in self.geometries:
            self.geometries[key] = audit.geometry(
                dict(well="16B", run=str(run), eow_bha=run, bit_ft=float(key[1])), self.plan, "current")
        return self.geometries[key]

    def run_of(self, stamp):
        return run_of(stamp)

    def event_geometry(self, bit_ft):
        """Geometry of the assembly whose events are replayed."""
        return self.geometry(17, bit_ft)

    def contacts(self):
        return contacts_for_run17()

    def flush_volume(self, bit_ft):
        """One string volume plus the BHA annulus volume."""
        bore, annulus = flush_module.geometry_volume(bit_ft, self.plan)
        return bore+annulus

    def outer_radius(self, run, bit_ft, md):
        """String outside radius at each depth, zero below the bit.

        With the bit shallower than the assembly, the components are read
        by their distance above the bit from a full-length string.
        """
        full = max(float(bit_ft), SHALLOW_FT)
        g = self.geometry(run, full)
        above = bit_ft*b.FT-np.asarray(md)
        station = np.clip(g.md_bit-above, 1e-3, g.md_bit-1e-3)
        return np.where(above >= 0, g.at(station)["r_out"], 0.)

    def __call__(self, stamp, bit_ft, flow_gpm, inlet_F):
        key = self.key(stamp, bit_ft, flow_gpm, inlet_F)
        if key in self.memory:
            return self.memory[key]
        name = hashlib.sha256(json.dumps(key).encode()).hexdigest()[:20]
        path = self.cache/f"{name}.json" if self.cache else None
        if path is not None and path.exists():
            saved = json.loads(path.read_text())
        else:
            run, bit, flow, inlet, hour = key
            g = self.geometry(run, bit)
            inlet_C = (inlet-32)/1.8
            rho = model.fluid_props(np.array([inlet_C]), np.array([model.P_SURF]))[0][0]
            m_dot = float(rho)*flow*b.GPM
            exposure = model.exposure_from_history(
                self.clock, self.depth, float(np.interp(hour, self.time, self.clock)))
            smooth = model.smooth_exposure(exposure, g.md_bit)
            tfa = sum(np.pi/4*(int(j)*b.INCH/32)**2 for j in self.defs[run]["jets_32nds"].split(";"))
            result = model.solve_seeded(
                smooth, model.exposure_breaks(smooth, g.md_bit), m_dot=m_dot, T_inj=inlet_C,
                geometry=g, geotherm=self.form, target_rock_T=float(self.form(g.survey.tvd(g.md_bit))),
                k_rock=b.K_ROCK, rhocp_rock=b.RHOCP_ROCK, friction_heat=True, Q_face=0., tfa=tfa,
                physics="v1.8.0", verbose=False)
            if not result["success"]:
                raise RuntimeError(f"circulation solve did not converge for {key}")
            z = np.linspace(0., g.md_bit, 400)
            td, tu = result["sol"].sol(z)
            dims = g.at(np.clip(z, 1e-3, g.md_bit-1e-3))
            pressure = model.P_of_z(dims["tvd"])
            _, h = model.annulus_films(m_dot, dims, tu, pressure, band="erge", viscosity="plastic")
            saved = dict(key=key, z=z.tolist(), td=td.tolist(), tu=tu.tolist(), h=h.tolist(),
                         m_dot=m_dot, md_bit=g.md_bit)
            if path is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(saved))
        profile = {k: np.asarray(v) if isinstance(v, list) else v for k, v in saved.items()}
        self.memory[key] = profile
        return profile


def sample(profile, z, field):
    """Profile value at depth z; below the bit, the value at the bit."""
    return np.interp(z, profile["z"], profile[field])


def rig_record(archive, first, last):
    """Time, tally-entry bit depth, hole depth, flow and inlet over a window."""
    rows = np.array(list(rig.rig_inputs(archive, first, last)))
    time, bit, hole, flow, inlet = rows.T
    hole = np.maximum.accumulate(np.where(np.isfinite(hole), hole, 0.))
    flow = np.where(np.isfinite(flow), flow, 0.)
    inlet = np.where(np.isfinite(inlet), inlet, np.nan)
    inlet = np.interp(time, time[np.isfinite(inlet)], inlet[np.isfinite(inlet)])
    return time, bit, hole, flow, inlet


def bit_faces(record, windows):
    """Bit depths (ft) that bound circulated rock, for fixed cell faces.

    A pumping spell circulates the hole above its deepest bit position and
    leaves the liquid below it static. A face at that depth, and at each
    event's starting bit depth, keeps the boundary between circulated and
    static liquid where the bit was, independent of the cell size. Only
    spells overlapping an event window, from the preceding spell on, are
    used.
    """
    time, bit, _, flow, _ = record
    on = flow > PUMPS_ON_GPM
    spell = np.cumsum(np.r_[True, on[1:] != on[:-1]])
    depths = set()
    for start, end in windows:
        first = np.searchsorted(time, start)
        depths.add(float(bit[min(first, len(bit)-1)]))
        before = spell[on & (time < start)]
        numbers = set(spell[on & (time >= start) & (time <= end)])
        if len(before):
            numbers.add(before[-1])
        for number in numbers:
            depths.add(float(np.nanmax(bit[spell == number])))
    return sorted(d for d in depths if np.isfinite(d) and d > 0)


class Grid:
    """Fixed axial cells from surface to the deepest hole in the window.

    The uniform faces are joined by any fixed faces (ft); a uniform face
    within a quarter cell of a fixed face is dropped, so refinement keeps
    the fixed faces and the uniform spacing.

    Above each fixed face the cells are graded, with faces at a half, a
    quarter and so on of the uniform spacing above it, down to 2**-grade of
    the spacing. The rock
    drilled last before an event has cooled least, and the grading resolves
    it at every level, with all lengths halving as the cell count doubles.
    A graded face within the finest graded length of a kept face is dropped.
    """

    def __init__(self, profiles, bottom_ft, cells, fixed_ft=(), grade=GRADE_LEVELS):
        uniform = np.linspace(0., bottom_ft, cells+1)
        # Bit depths closer than MERGE_FT are one face, at the deepest of them.
        fixed = []
        for f in sorted(f for f in fixed_ft if 0. < f < bottom_ft):
            if fixed and f-fixed[-1] < MERGE_FT:
                fixed[-1] = f
            else:
                fixed.append(f)
        fixed = np.array(fixed)
        if len(fixed):
            spacing = bottom_ft/cells
            keep = np.array([i in (0, cells) or np.min(np.abs(fixed-u)) > spacing/4
                             for i, u in enumerate(uniform)])
            kept = list(np.r_[uniform[keep], fixed])
            finest = spacing/2**(grade+1)
            # Finest graded faces first, so the cells next to the bit win.
            for level in range(grade, 0, -1):
                for f in fixed:
                    g = f-spacing/2**level
                    if g > 0. and np.min(np.abs(np.array(kept)-g)) > finest:
                        kept.append(g)
            uniform = np.unique(kept)
        self.faces_ft = uniform
        self.faces = uniform*b.FT
        self.lengths = np.diff(self.faces)
        self.md = (self.faces[:-1]+self.faces[1:])/2
        self.form = profiles.form
        g = profiles.event_geometry(bottom_ft)
        self.dims = g.at(np.clip(self.md, 1e-3, g.md_bit-1e-3))
        self.full_volume = np.pi*self.dims["r_wall"]**2*self.lengths
        self.pressure = model.P_of_z(self.dims["tvd"])
        self.formation = np.array([float(self.form(t)) for t in self.dims["tvd"]])
        _, _, _, self.k = model.fluid_props(self.formation, self.pressure)

    def subset(self, n):
        """The first n cells, for a column that ends at the hole bottom."""
        part = copy.copy(self)
        part.faces = self.faces[:n+1]
        part.faces_ft = self.faces_ft[:n+1]
        for name in ("lengths", "md", "full_volume", "pressure", "formation", "k"):
            setattr(part, name, getattr(self, name)[:n])
        part.dims = {key: value[:n] for key, value in self.dims.items()}
        return part

    def static_films(self, mixed, string_out_radius):
        if mixed:
            return np.full(len(self.md), np.inf)
        gap = np.maximum(self.dims["r_wall"]-string_out_radius, 1e-3)
        return NU_LAMINAR*self.k/(2*gap)

    def static_capacity(self, string_out_radius):
        return CAPACITY*np.pi*(self.dims["r_wall"]**2-string_out_radius**2)


def history(record, profiles, grid, config, stops):
    """Advance every cell's rock through the record; snapshot at each stop.

    Returns {stop: (rock list, bore temperature estimate per cell)}.
    """
    time, bit, hole, flow, inlet = record
    md_ft = grid.md/b.FT
    # A cell is drilled once the hole passes its upper face and is swept
    # once the bit passes it, matching the cell each tool contacts.
    top_ft = grid.faces_ft[:-1]
    horizon = time[-1]-time[0]+1e7
    rock = [RadialColumn(grid.dims["r_rock"][i], grid.formation[i], b.K_ROCK, b.RHOCP_ROCK,
                         horizon, radial_nodes=config.radial, grid_power=config.grid_power,
                         casing_resistance=grid.dims["R_hole"][i]) for i in range(len(md_ft))]
    # Circulation before the window: one lumped spell at the first window
    # profile that reaches the depth, then static to the window start.
    exposure = model.exposure_from_history(
        profiles.clock, profiles.depth, float(np.interp(time[0], profiles.time, profiles.clock)))
    pumping = profiles.clock
    last_on = profiles.time[np.flatnonzero(np.diff(pumping, prepend=pumping[0]) > 0)]
    gap = max(0., time[0]-(last_on[last_on < time[0]][-1]+profiles.clock_bin_s if (last_on < time[0]).any() else time[0]))
    first_on = np.flatnonzero(flow > PUMPS_ON_GPM)
    bore_C = grid.formation.copy()
    for i, z in enumerate(grid.md):
        pre = float(exposure(z))
        if pre <= 0 or not (hole[0] > top_ft[i]):
            continue
        reach = first_on[bit[first_on] > top_ft[i]]
        j = reach[0] if len(reach) else first_on[0]
        p = profiles(time[j], bit[j], flow[j], inlet[j])
        rock[i].circulate(pre, float(sample(p, z, "tu")), float(sample(p, z, "h")))
        if gap > 0:
            rock[i].shut_in(gap, float(grid.static_capacity(0.)[i]),
                            float(grid.static_films(config.mixed, 0.)[i]))
    snapshots = {}
    stops = sorted(stops)
    n = len(time)
    # Group consecutive samples with the same state everywhere: a change of
    # pumping, a bit depth that crosses a cell face, or SPLIT_S of circulation.
    face_index = np.searchsorted(grid.faces/b.FT, np.nan_to_num(bit), side="right")
    on = flow > PUMPS_ON_GPM
    # A circulating state takes the flow and inlet of its whole pumping
    # spell, so the ramps at pump-on and pump-off do not carry the steady
    # solution for a transient flow.
    spell = np.cumsum(np.r_[True, on[1:] != on[:-1]])
    spell_flow, spell_inlet = {}, {}
    for number in np.unique(spell[on]):
        members = spell == number
        spell_flow[number] = float(np.median(flow[members]))
        spell_inlet[number] = float(np.mean(inlet[members]))
    start = 0
    for k in range(1, n+1):
        boundary = (k == n or on[k] != on[start] or face_index[k] != face_index[start]
                    or (on[start] and time[k]-time[start] >= SPLIT_S)
                    or any(time[start] < s <= time[k] for s in stops))
        if not boundary:
            continue
        end_t = time[k] if k < n else time[-1]+10.
        for s in stops:
            if time[start] < s <= end_t:
                end_t = s
        duration = end_t-time[start]
        if duration > 0:
            rows = slice(start, k)
            bit_now = float(np.nanmax(bit[rows]))
            if on[start]:
                p = profiles(time[start], float(np.nanmean(bit[rows])), spell_flow[spell[start]],
                             spell_inlet[spell[start]])
            outer = profiles.outer_radius(profiles.run_of(time[start]), max(bit_now, 0.), grid.md)
            caps = grid.static_capacity(outer)
            films = grid.static_films(config.mixed, outer)
            for i, z in enumerate(grid.md):
                if hole[start] <= top_ft[i]:
                    continue
                if on[start] and bit_now > top_ft[i]:
                    rock[i].circulate(duration, float(sample(p, z, "tu")), float(sample(p, z, "h")))
                    bore_C[i] = float(sample(p, z, "td"))
                else:
                    rock[i].shut_in(duration, float(caps[i]), float(films[i]))
                    bore_C[i] = rock[i].temperature_C
        for s in stops:
            if time[start] < s <= end_t:
                snapshots[s] = (copy.deepcopy(rock), bore_C.copy())
        start = k
    return snapshots


def string_volumes(faces, full_volume, string, z):
    """Bore and annulus volume per cell with the bit at depth z.

    `string` is a fixed list of (length, outside radius, bore area) from
    the bit upwards. The top section extends to surface, so moving the bit
    slides the same assembly down and lengthens only the top pipe. Cells
    below the bit are full hole.
    """
    top = np.r_[0., np.cumsum([length for length, *_ in string])]
    lower = z-top[1:]
    upper = z-top[:-1]
    lower[-1] = 0.
    cell_lo, cell_hi = faces[:-1, None], faces[1:, None]
    overlap = np.clip(np.minimum(cell_hi, upper[None, :])-np.maximum(cell_lo, lower[None, :]), 0., None)
    radius = np.array([r for _, r, _ in string])
    area = np.array([a for *_, a in string])
    displaced = overlap @ (np.pi*radius**2)
    bore = overlap @ area
    return bore[bore > 0.], full_volume-displaced


def carrier_interval(edges, faces, full_volume, string, z):
    """Annulus and bore volume intervals from surface to the carrier edges.

    The intervals are in the parcel coordinates of the column, so the
    tool exchanges heat with the liquid over its own span whatever the
    cell size. Within a cell the hole volume is taken uniform, as the
    cell's annulus volume is.
    """
    top = np.r_[0., np.cumsum([length for length, *_ in string])]
    lower = z-top[1:]
    upper = z-top[:-1]
    lower[-1] = 0.
    radius = np.array([r for _, r, _ in string])
    area = np.array([a for *_, a in string])
    lengths = np.diff(faces)
    annulus, bore = [], []
    for depth in edges:
        overlap = np.clip(np.minimum(depth, upper)-np.maximum(0., lower), 0., None)
        i = int(np.clip(np.searchsorted(faces, depth, side="right")-1, 0, len(lengths)-1))
        hole = full_volume[:i].sum()+full_volume[i]*min(max(depth-faces[i], 0.), lengths[i])/lengths[i]
        annulus.append(hole-overlap @ (np.pi*radius**2))
        bore.append(overlap @ area)
    return (annulus[0], annulus[1]), (bore[0], bore[1])


def annulus_to(depth, faces, full_volume, string, z):
    """Annulus volume from surface to a depth with the bit at z."""
    (volume, _), _ = carrier_interval((depth, depth), faces, full_volume, string, z)
    return volume


def fixed_outer(string, z, md):
    """Outside radius of the fixed assembly at depths md, zero below the bit."""
    top = np.r_[0., np.cumsum([length for length, *_ in string])]
    above = z-np.asarray(md)
    index = np.clip(np.searchsorted(top, above, side="right")-1, 0, len(string)-1)
    return np.where(above >= 0, np.array([r for _, r, _ in string])[index], 0.)


def fixed_string(geometry):
    """(length, outside radius, bore area) from the bit upwards."""
    sections = []
    top = 0.
    for segment in geometry.string:
        middle = top+segment.length/2
        dims = geometry.at(np.array([min(max(middle, 1e-3), geometry.md_bit-1e-3)]))
        sections.append((segment.length, float(dims["r_out"][0]), float(dims["A_bore"][0])))
        top += segment.length
    return sections[::-1]


def contacts_for_run17():
    carrier = next(r for r in audit.rows(rig.HERE/"sanvean_sensor_geometry.csv") if r["eow_bha"] == "17")
    bit = next(r for r in assembly_audit() if r["well"] == "16B" and r["bha"] == "17" and r["bit"])
    lower, upper = float(carrier["black_box_bottom_ft"]), float(carrier["black_box_top_ft"])
    return (("bit", BIT_OFFSET_FT, bit["length_ft"], bit["reported_od_in"], bit["reported_id_in"]),
            ("black_box", (lower+upper)/2, upper-lower, float(carrier["black_box_od_in"]),
             float(carrier["black_box_bore_in"])))


def replay_event(event, record, profiles, grid, snapshot, config):
    """Replay one event and return the time series of both sensors."""
    time, bit, hole, flow, inlet = record
    start, stop = event["start_t"], event["replay_end_t"]
    rows = np.flatnonzero((time >= start) & (time <= stop))
    t, z_ft = time[rows], np.maximum.accumulate(bit[rows])
    # The column ends at the hole bottom: cells whose upper face is at or
    # below the hole depth at the event start are not yet drilled.
    n = int(np.count_nonzero(grid.faces[:-1] < hole[rows[0]]*b.FT))
    grid = grid.subset(n)
    rock, bore_guess = copy.deepcopy(snapshot[0][:n]), snapshot[1][:n]
    depth0 = float(z_ft[0])*b.FT

    # One assembly for the whole event, slid down with the bit, so the
    # displacement follows the motion exactly.
    final = profiles.event_geometry(event["final_bit_ft"])
    assembly = fixed_string(final)
    bottom = grid.faces[-1]

    bore, annulus = string_volumes(grid.faces, grid.full_volume, assembly, min(depth0, bottom))
    bore_C = np.interp(grid.md[:len(bore)], grid.md, bore_guess)
    column = MovingColumn(rock, grid.lengths, annulus, CAPACITY, bore, bore_C)
    # Each tool starts at the bore liquid of the cell it sits in. Values are
    # not interpolated across the bit, where circulated liquid above meets
    # static liquid below.
    def cell_of(depth):
        return int(np.clip(np.searchsorted(grid.faces, depth)-1, 0, len(grid.md)-1))
    tools = [(label, offset*b.FT, length*b.FT,
              LayeredTool(bore_in*b.INCH/2, od*b.INCH/2, CAPACITY,
                          float(bore_guess[cell_of(depth0-offset*b.FT)])))
             for label, offset, length, od, bore_in in profiles.contacts()]
    rho, cp, mu, k = model.fluid_props(grid.formation, grid.pressure)
    flush = profiles.flush_volume(event["final_bit_ft"])
    pumped_since_on, phase, out = 0., "static", []
    previous_depth, previous_total = depth0, float(np.sum(bore))
    # Depth of the bit in the column's current annulus geometry.
    geometry_depth = min(depth0, bottom)
    elapsed = 0.

    def q_on(j):
        return flow[rows[j]] > PUMPS_ON_GPM
    for j in range(len(rows)-1):
        duration = t[j+1]-t[j]
        # After the handover the circulation is prescribed, so the record
        # interval is the step; motion, pauses and restarts use the cap.
        count = 1 if phase == "steady" and q_on(j) else max(1, int(np.ceil(duration/config.cap_s)))
        q = flow[rows[j]]*b.GPM if flow[rows[j]] > PUMPS_ON_GPM else 0.
        if q:
            p = profiles(t[j], z_ft[j], flow[rows[j]], inlet[rows[j]])
            if phase == "static":
                phase, pumped_since_on = "restart", 0.
        else:
            phase = "static"
        ends = list(np.linspace(t[j], t[j+1], count+1)[1:])
        now = t[j]
        while ends:
            end = ends[0]
            # The restart step that completes the flush volume ends at the
            # handover, so the switch time does not depend on the step.
            if phase == "restart" and q and pumped_since_on+q*(end-now) > flush:
                end = now+(flush-pumped_since_on)/q
            else:
                ends.pop(0)
            dt = end-now
            if dt <= 0.:
                phase = "steady"
                continue
            z = min((z_ft[j]+(z_ft[j+1]-z_ft[j])*(end-t[j])/duration)*b.FT, bottom)
            moved = z > previous_depth+1e-9
            speed = (z-previous_depth)/dt if moved else 0.
            outer = fixed_outer(assembly, z, grid.md)
            static_films = grid.static_films(config.mixed, outer)
            if phase == "steady":
                films = sample(p, grid.md, "h")
                for i, node in enumerate(column.rock):
                    if grid.faces[i] < z:
                        node.circulate(dt, float(sample(p, grid.md[i], "tu")), float(films[i]))
                    else:
                        node.shut_in(dt, CAPACITY*column.annulus_volume[i]/grid.lengths[i],
                                     float(static_films[i]))
                column.bore_temperature = sample(p, np.cumsum(column.bore_volume)/
                                                 np.maximum(np.cumsum(column.bore_volume)[-1], 1e-9)*z, "td")
                elapsed += dt
                for label, offset, length, tool in tools:
                    # The prescribed circulation is read at the sensor depth.
                    i = min(int(np.searchsorted(grid.faces, z-offset)-1), len(grid.md)-1)
                    tool.step(dt, float(sample(p, z-offset, "tu")), 3.66*float(k[i])/(2*tool.bore_radius),
                              float(sample(p, z-offset, "h")), bore_capacity=None)
                    tool.temperature_C[0] = float(sample(p, z-offset, "td"))
                out.append((end, phase, *[tool.sensor_temperatures() for *_, tool in tools], 0., 0.))
                previous_depth, now = z, end
                continue
            films = sample(p, grid.md, "h") if q else static_films

            def contacts_at(depth):
                contacts = []
                for label, offset, length, tool in tools:
                    i = min(int(np.searchsorted(grid.faces, depth-offset)-1), len(grid.md)-1)
                    outside = (displacement_film(tool.outer_radius, grid.dims["r_wall"][i], speed,
                                                 rho[i], cp[i], mu[i], k[i])
                               if speed and tool.outer_radius < grid.dims["r_wall"][i] else float(films[i]))
                    # The tool exchanges with the parcels along its carrier, so
                    # its liquid is independent of the cell length.
                    footprint = carrier_interval((depth-offset-length/2, depth-offset+length/2),
                                                 grid.faces, grid.full_volume, assembly, depth)
                    contacts.append(ToolContact(tool, length, i, i, 3.66*float(k[i])/(2*tool.bore_radius),
                                                outside, footprint))
                return tuple(contacts)
            contacts = contacts_at(z)
            # Each tool exchanges at least exchange_parts times per footprint
            # volume passing it, so short slugs meet the tool.
            exchange_volume = min(b1-b0 for c in contacts for b0, b1 in c.footprint)/config.exchange_parts
            inlet_C = (inlet[rows[j]]-32)/1.8
            active = max(1, int(np.count_nonzero(grid.faces[:-1] < z))) if q else None
            if moved:
                # The liquid below the old bit is displaced past the tools as
                # the bit advances. The motion is split with the pumped flow
                # into parts no larger than the exchange volume, and each part
                # descends, pumps and exchanges in turn. The intake and the
                # restart circuit turn at the bit itself, so the liquid below
                # it stays in place whatever the cell size.
                swept = (annulus_to(z, grid.faces, grid.full_volume, assembly, geometry_depth)
                         - annulus_to(geometry_depth, grid.faces, grid.full_volume, assembly, geometry_depth))
                parts = max(1, int(np.ceil((q*dt+max(swept, 0.))/exchange_volume)))
                moves, depth_from, total_from = [], geometry_depth, previous_total
                for part in range(1, parts+1):
                    depth = depth_from+(z-geometry_depth)/parts if part < parts else z
                    bore_grid, annulus_grid = string_volumes(grid.faces, grid.full_volume, assembly, depth)
                    total = float(np.sum(bore_grid))
                    at_bit = annulus_to(depth, grid.faces, grid.full_volume, assembly, depth)
                    moves.append(Move(annulus_grid, contacts_at(depth) if part < parts else contacts,
                                      added_bore_volume=max(0., total-total_from), bore_volume=bore_grid,
                                      bit_volumes=(annulus_to(depth, grid.faces, grid.full_volume,
                                                              assembly, depth_from), at_bit),
                                      circuit_end=at_bit if q else None))
                    depth_from, total_from = depth, total
                new_total = total_from
                step = ColumnStep(dt, tuple(films), contacts, float_valve=config.float_valve,
                                  fill_C=inlet_C, flow=q, inlet_C=inlet_C if q else None,
                                  active_cells=active, moves=tuple(moves))
            else:
                at_bit = annulus_to(z, grid.faces, grid.full_volume, assembly, z)
                step = ColumnStep(dt, tuple(films), contacts, float_valve=config.float_valve,
                                  fill_C=inlet_C, flow=q, inlet_C=inlet_C if q else None,
                                  active_cells=active, circuit_end=at_bit if q else None,
                                  exchange_volume=exchange_volume if q else None)
            result = next(replay(column, [step]))
            elapsed += dt
            for into, sensors in result.samples[:-1]:
                out.append((now+into, phase, *sensors, 0., 0.))
            out.append((end, phase, *result.sensors_C, result.energy_residual_J,
                        result.into_rock_J))
            if moved:
                previous_total, geometry_depth = new_total, z
            previous_depth, now = z, end
            if phase == "restart":
                pumped_since_on += q*dt
                if pumped_since_on >= flush*(1-1e-12):
                    phase = "steady"
    return out


def events(offset):
    """Run 17 events on the Pason clock with their replay windows."""
    rows = audit.rows(rig.HERE/"events-2026-11-08-entries/bha-17-events.csv")
    for row in rows:
        stage = row["kind"] == "trip_stage"
        pump_on = row["circ_start"] if stage else row["pump_on"]
        if not pump_on:
            continue
        start = timestamp(row["start"])+offset
        on = timestamp(pump_on)+offset
        end = timestamp(row["circ_end"])+offset if stage and row["circ_end"] else on+RESTART_S
        yield dict(id=row["id"], kind=row["kind"], start_t=start, end_t=timestamp(row["end"])+offset,
                   pump_on_t=on, replay_end_t=max(end, on+RESTART_S),
                   final_bit_ft=float(row["bit_end_ft"]))


def model_pump_on(event, series, reach=60.):
    """The model's own pump-on: the static to pumping switch nearest the event's.

    The recorded flow can come on a few seconds either side of the event's
    pump-on. The windows split at the model's switch, where a sample always
    lies, so they do not depend on the step. Without a switch within reach
    the event's pump-on is kept.
    """
    t = np.array([row[0] for row in series])
    static = np.array([row[1] == "static" for row in series])
    switches = t[:-1][static[:-1] & ~static[1:]]
    if not len(switches) or np.min(np.abs(switches-event["pump_on_t"])) > reach:
        return event["pump_on_t"]
    return float(switches[np.argmin(np.abs(switches-event["pump_on_t"]))])


def quantities(event, series, config):
    """D3 and D4 quantities for both sensors over their bands."""
    t = np.array([row[0] for row in series])
    on = model_pump_on(event, series)
    out = []
    bands = {"bit": (0, 2), "black_box": (1, 3)}
    for index, label in enumerate(("bit", "black_box")):
        readings = np.array([row[2+index] for row in series])
        low, high = bands[label]
        # The bit band runs from bore fluid to steel mid-wall, centred
        # between them; the Black Box band spans the wall, centred mid-wall.
        centre = (readings[:, 0]+readings[:, 2])/2 if label == "bit" else readings[:, 2]
        values = dict(centre=centre, low=np.minimum(readings[:, low], readings[:, high]),
                      high=np.maximum(readings[:, low], readings[:, high]))
        for name, trace in values.items():
            during = (t > event["start_t"]) & (t <= on)
            restart = (t > on) & (t <= on+RESTART_S)
            row = dict(event=event["id"], kind=event["kind"], sensor=label, band=name,
                       coupling="fast" if config.mixed else "slow", float_valve=config.float_valve,
                       cells=config.cells, radial_nodes=config.radial, cap_s=config.cap_s)
            if event["kind"] == "trip_stage":
                row |= dict(stage_peak_C=float(trace[during].max()) if during.any() else np.nan,
                            restart_peak_C=float(trace[restart].max()) if restart.any() else np.nan,
                            circulation_end_C=float(trace[-1]))
            else:
                start = trace[np.argmin(np.abs(t-event["start_t"]))]
                end = trace[during][-1] if during.any() else np.nan
                row |= dict(rise_C=float(end-start),
                            restart_peak_C=float(trace[restart].max()) if restart.any() else np.nan)
            out.append(row)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cache", type=Path, default=None, help="folder for cached circulation solutions")
    parser.add_argument("--only", nargs="*", default=None, help="event ids")
    parser.add_argument("--cells", type=int, default=160)
    parser.add_argument("--radial", type=int, default=40)
    parser.add_argument("--cap", type=float, default=1.25)
    parser.add_argument("--coupling", choices=("slow", "fast", "both"), default="both")
    args = parser.parse_args()
    alignment = next(r for r in audit.rows(rig.HERE/"clock-alignment.csv") if r["eow_bha"] == "17")
    offset = int(alignment["pason_minus_sanvean_s"])
    selected = [e for e in events(offset) if args.only is None or e["id"] in args.only]
    # The record and grid always span the whole window, so the cells do
    # not depend on which events are selected.
    last = max(e["replay_end_t"] for e in events(offset))+60
    profiles = Profiles(args.cache)
    record = rig_record(args.archive, WINDOW_START, last)
    windows = [(e["start_t"], e["replay_end_t"]) for e in events(offset)]
    grid = Grid(profiles, float(np.nanmax(record[2])), args.cells, bit_faces(record, windows))
    couplings = {"slow": (False,), "fast": (True,), "both": (False, True)}[args.coupling]
    rows = []
    for mixed in couplings:
        base = Config(args.cells, args.radial, args.cap, mixed)
        snapshots = history(record, profiles, grid, base, [e["start_t"] for e in selected])
        for event in selected:
            floats = (False, True) if event["kind"] == "trip_stage" else (False,)
            for float_valve in floats:
                config = Config(args.cells, args.radial, args.cap, mixed, float_valve)
                series = replay_event(event, record, profiles, grid, snapshots[event["start_t"]], config)
                residual = max(abs(row[-2]) for row in series)
                # Summed residual over summed heat exchanged with the rock in
                # the column-tracked steps (the steady phase is prescribed).
                exchanged = sum(abs(row[-1]) for row in series)
                fraction = sum(abs(row[-2]) for row in series)/exchanged if exchanged else 0.
                for row in quantities(event, series, config):
                    rows.append(row | dict(max_step_energy_residual_J=residual,
                                            energy_residual_fraction=fraction))
                print(event["id"], "fast" if mixed else "slow", float_valve, flush=True)
    write_csv(args.output, rows)


if __name__ == "__main__":
    main()
