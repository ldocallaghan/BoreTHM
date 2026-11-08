"""Model-only run 17 connection replay with a lumped conditioning history."""
import argparse
import importlib
from pathlib import Path

import numpy as np

from borethm.column_replay import ColumnStep, ToolContact, replay
from borethm.layered_tool import LayeredTool
from borethm.moving_column import MovingColumn
from borethm.run_in_column import RadialColumn
from borethm.wall_thermal import NU_LAMINAR
from borethm.studies.pressure_comparison import assembly_audit
from validation.benchmarks.run_circulation import write_csv

audit = importlib.import_module(f"{__package__}.run17_rayleigh")
inputs = importlib.import_module(f"{__package__}.run17_boundaries")
model = audit.model
b = audit.forge16b


def run(event, operating, *, cells, radial, step_s, well_mixed, recorded_contact=True):
    plan = audit.read_json(audit.PLAN)
    form = audit.forge16a.formation("216", audit.forge16a.survey())[0]
    _, *clocks = audit.whole.clock(audit.FORGE)
    defs = {int(r["eow_bha"]): r for r in audit.rows(audit.FORGE/"run_definitions.csv")}
    g, solved, m_dot, exposure, stamp, _ = audit.conditioning(event, plan, form, clocks, defs)
    carrier = next(r for r in audit.rows(inputs.HERE/"sanvean_sensor_geometry.csv")
                   if r["eow_bha"] == "17")
    bit = next(r for r in assembly_audit()
               if r["well"] == "16B" and r["bha"] == "17" and r["bit"])
    bit_span = (0., bit["length_ft"])
    box_span = (float(carrier["black_box_bottom_ft"]), float(carrier["black_box_top_ft"]))
    contacts = (("bit", bit_span, bit["reported_od_in"], bit["reported_id_in"]),
                ("black_box", box_span, float(carrier["black_box_od_in"]),
                 float(carrier["black_box_bore_in"])))
    faces = np.r_[np.linspace(0., g.md_bit, cells+1),
                  np.cumsum([seg.length for seg in g.string])[:-1],
                  [h.md_top for h in g.hole if 0. < h.md_top < g.md_bit]]
    for _, (lower, upper), _, _ in contacts:
        start, end = g.md_bit-upper*b.FT, g.md_bit-lower*b.FT
        faces = np.r_[faces[(faces < start) | (faces > end)], start, end]
    faces = np.unique(faces)
    lengths = np.diff(faces)
    md = (faces[1:]+faces[:-1])/2
    dim = g.at(md)
    pressure = model.P_of_z(dim["tvd"])
    td, tu = solved["sol"].sol(md)
    _, h = model.annulus_films(m_dot, dim, tu, pressure, band="erge", viscosity="plastic")
    _, _, _, k = model.fluid_props(tu, pressure)
    static = NU_LAMINAR*k/dim["Dh_ann"]
    horizon = np.maximum(exposure(md), float(event["duration_s"]))
    capacity = 4.18e6
    rock = []
    for i, duration in enumerate(horizon):
        node = RadialColumn(dim["r_rock"][i], float(form(dim["tvd"][i])), b.K_ROCK,
                            b.RHOCP_ROCK, duration+3600., radial_nodes=radial,
                            casing_resistance=dim["R_hole"][i])
        node.circulate(duration, tu[i], h[i])
        node.max_radial_step_s = 1.
        rock.append(node)
    column = MovingColumn(rock, lengths, dim["A_ann"]*lengths, capacity,
                          dim["A_bore"]*lengths, td.copy())
    sensors = []
    for label, (lower, upper), od, bore in contacts:
        midpoint = g.md_bit-(lower+upper)/2*b.FT
        index = np.searchsorted(faces, midpoint)-1
        tool = LayeredTool(bore*b.INCH/2, od*b.INCH/2, capacity, td[index])
        length = lengths[index] if recorded_contact else min(0.25, lengths[index])
        sensors.append((label, index, tool, length))

    def steps():
        for time, end, flow, inlet in operating:
            wall = tuple(h if flow else (np.full(len(md), np.inf) if well_mixed else static))
            contacts = tuple(ToolContact(tool, length, i, i, 3.66*k[i]/(2*tool.bore_radius),
                                         float(h[i] if flow else wall[i]))
                             for _, i, tool, length in sensors)
            pieces = int(np.ceil((end-time)/step_s))
            for _ in range(pieces):
                yield ColumnStep((end-time)/pieces, wall, contacts, flow=flow, inlet_C=inlet)

    series = list(replay(column, steps()))
    for label, j in (("bit", 0), ("black_box", 1)):
        readings = [row.sensors_C[j][0 if j == 0 else 2] for row in series]
        restart = inputs.timestamp(event["end_pason"])-stamp
        after = [v for row, v in zip(series, readings, strict=True) if row.elapsed > restart]
        yield dict(event=event["event"], cells=len(md), radial_nodes=radial,
                   max_step_s=step_s, contact="recorded" if recorded_contact else "0.25 m",
                   coupling="mixed" if well_mixed else "slow",
                   sensor=label, peak_restart_C=max(after),
                   max_step_energy_error_J=max(abs(row.energy_residual_J) for row in series),
                   total_abs_rock_heat_J=sum(abs(row.into_rock_J) for row in series))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--time-fine", action="store_true")
    parser.add_argument("--pilot", action="store_true",
                        help="the two-configuration pilot with a 0.25 m contact")
    args = parser.parse_args()
    event = next(r for r in audit.rows(audit.HERE/"run17-boundaries.csv")
                 if r["event"] == "pause-02")
    start = inputs.timestamp(event["circulation_end"])
    restart = inputs.timestamp(event["end_pason"])
    stop = restart+300
    operating = [(start, restart, 0., None)]
    # Use the raw pumping records in the observed restart, preserving gaps.
    history = list(inputs.rig_inputs(args.archive, restart-10, stop))
    for time, _, _, flow, inlet in history:
        left, right = max(time, restart), min(time+10, stop)
        if right > left and np.isfinite(flow) and np.isfinite(inlet):
            operating.append((left, right, max(flow, 0.)*b.GPM, (inlet-32)*5/9))
    if sum(end-begin for begin, end, *_ in operating) != stop-start:
        raise ValueError("recorded operating history does not cover the replay")
    settings = {
        "axial": ((40, 80, 5.), (80, 80, 5.), (160, 80, 5.)),
        "radial": ((80, 40, 5.), (80, 80, 5.), (80, 160, 5.)),
        "time": ((80, 80, 10.), (80, 80, 5.), (80, 80, 2.5)),
    }
    if args.time_fine:
        settings = {"time": ((80, 80, 2.5), (80, 80, 1.25), (80, 80, .625))}
    if args.pilot:
        settings = {"pilot": ((40, 40, 10.), (80, 80, 5.))}
    results = {}
    for axis, variants in settings.items():
        for cells, radial, step in variants:
            for mixed in (False, True):
                key = (cells, radial, step, mixed)
                if key not in results:
                    results[key] = list(run(event, operating, cells=cells, radial=radial,
                                            step_s=step, well_mixed=mixed,
                                            recorded_contact=not args.pilot))
    rows = [dict(axis=axis, level=level) | row
            for axis, variants in settings.items()
            for level, (cells, radial, step) in enumerate(variants, 1)
            for mixed in (False, True)
            for row in results[cells, radial, step, mixed]]
    if not (args.time_fine or args.pilot):
        rows.extend(dict(axis="contact", level=1) | row
                for mixed in (False, True)
                for row in run(event, operating, cells=80, radial=80, step_s=5.,
                               well_mixed=mixed, recorded_contact=False))
    write_csv(args.output, rows)


if __name__ == "__main__":
    main()
