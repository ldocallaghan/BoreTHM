"""Exercise the moving-column replay on run 17 stage 03 inputs."""
import argparse
import importlib
from pathlib import Path

import numpy as np

from borethm.column_replay import ColumnStep, ToolContact, replay
from borethm.layered_tool import LayeredTool, displacement_film
from borethm.moving_column import MovingColumn
from borethm.run_in_column import RadialColumn
from borethm.wall_thermal import NU_LAMINAR
from validation.benchmarks.run_circulation import write_csv

audit = importlib.import_module(f"{__package__}.run17_rayleigh")
rig = importlib.import_module(f"{__package__}.run17_boundaries")
b = audit.forge16b
model = audit.model
CAPACITY = 4.18e6


def volumes(faces, full_annulus_volume, geometry):
    """Integrate bore and annulus sections on a common fixed depth grid."""
    pipe = np.r_[0., np.cumsum([s.length for s in geometry.string])]
    lower = np.maximum(faces[:-1, None], pipe[None, :-1])
    upper = np.minimum(faces[1:, None], pipe[None, 1:])
    overlap = np.maximum(upper-lower, 0.)
    radii = geometry.at((pipe[:-1]+pipe[1:])/2)
    bore = overlap @ radii["A_bore"]
    displaced = overlap @ (np.pi*radii["r_out"]**2)
    return bore[bore > 0.], full_annulus_volume-displaced


def prepare(event):
    plan = audit.read_json(audit.PLAN)
    form = audit.forge16a.formation("216", audit.forge16a.survey())[0]
    _, *clocks = audit.whole.clock(audit.FORGE)
    defs = {int(r["eow_bha"]): r for r in audit.rows(audit.FORGE/"run_definitions.csv")}
    previous, solved, mass_flow, exposure, stamp, _ = audit.conditioning(
        event, plan, form, clocks, defs)
    return plan, form, previous, solved, mass_flow, exposure, stamp


def calculate(event, data, *, cell_count, radial_nodes, cap, mixed, float_valve):
    plan, form, old, solved, mass_flow, exposure, stamp = prepare(event)
    times, bit_ft, _, _, inlet_F = data.T
    # The 1.08 ft of cumulative backtracking in this stage is omitted
    # from this model-only descent pilot.
    depth = np.maximum.accumulate(bit_ft)*b.FT
    faces = np.unique(np.r_[np.linspace(0., depth[-1], cell_count+1),
                            [h.md_top for h in old.hole if 0. < h.md_top < depth[-1]]])
    lengths = np.diff(faces)
    md = (faces[:-1]+faces[1:])/2
    dims = old.at(md)
    bore_C, annulus_C = solved["sol"].sol(md)
    pressure = model.P_of_z(dims["tvd"])
    rho, cp, mu, k = model.fluid_props(annulus_C, pressure)
    _, h = model.annulus_films(mass_flow, dims, annulus_C, pressure,
                               band="erge", viscosity="plastic")
    full_volume = np.pi*dims["r_wall"]**2*lengths
    radius = dims["r_rock"]
    off = times[0]-stamp
    rock = []
    for i, z in enumerate(md):
        duration = max(float(exposure(z)), float(event["duration_s"]))
        node = RadialColumn(radius[i], float(form(dims["tvd"][i])), b.K_ROCK,
                            b.RHOCP_ROCK, duration+off+3600., radial_nodes=radial_nodes,
                            casing_resistance=dims["R_hole"][i])
        node.circulate(duration, annulus_C[i], h[i])
        node.shut_in(off, CAPACITY*full_volume[i]/lengths[i],
                     np.inf if mixed else NU_LAMINAR*k[i]/(2*dims["r_wall"][i]))
        node.max_radial_step_s = 1.
        rock.append(node)

    def dimensions(z):
        return audit.geometry(dict(well="16B", run="17", eow_bha=17, bit_ft=z/b.FT),
                              plan, "current")

    bore, annulus = volumes(faces, full_volume, dimensions(depth[0]))
    column = MovingColumn(rock, lengths, annulus, CAPACITY, bore, bore_C[:len(bore)].copy())
    tools = [LayeredTool(bore_in*b.INCH/2, od*b.INCH/2, CAPACITY, bore_C[len(bore)-1])
             for od, bore_in in ((9.5, 2.75), (6.75, 2.25))]
    contact_lengths = (1.25*b.FT, 5.97*b.FT)
    offsets = (.625*b.FT, 110.955*b.FT)

    def steps():
        previous_depth = depth[0]
        previous_volume = np.sum(bore)
        for j, duration in enumerate(np.diff(times)):
            count = int(np.ceil(duration/cap))
            speed = (depth[j+1]-depth[j])/duration
            for sub in range(count):
                z = depth[j]+(depth[j+1]-depth[j])*(sub+1)/count
                moved = z > previous_depth+1e-9
                bore_grid, annulus_grid = volumes(faces, full_volume, dimensions(z))
                films = (np.full(len(md), np.inf) if mixed else
                         NU_LAMINAR*k/(2*(dims["r_wall"]-np.sqrt(
                             (full_volume-annulus_grid)/(np.pi*lengths)))))
                contacts = []
                for tool, offset, length in zip(tools, offsets, contact_lengths, strict=True):
                    i = min(int(np.searchsorted(faces, z-offset)-1), len(bore_grid)-1)
                    if i < 0 or lengths[i] < length:
                        raise ValueError("tool carrier must fit in the replay grid")
                    outer = (displacement_film(tool.outer_radius, dims["r_wall"][i],
                                               speed, rho[i], cp[i], mu[i], k[i])
                             if speed and tool.outer_radius < dims["r_wall"][i] else films[i])
                    contacts.append(ToolContact(tool, length, i, i,
                                                3.66*k[i]/(2*tool.bore_radius), outer))
                new_total = np.sum(bore_grid)
                yield ColumnStep(duration/count, tuple(films), tuple(contacts),
                                 annulus_volume=annulus_grid if moved else None,
                                 added_bore_volume=max(0., new_total-previous_volume),
                                 float_valve=float_valve, fill_C=(inlet_F[j]-32)*5/9,
                                 bore_volume=bore_grid if moved else None)
                previous_volume, previous_depth = new_total, z

    output = list(replay(column, steps()))
    return dict(event=event["event"], cells=len(md), radial_nodes=radial_nodes, cap_s=cap,
                coupling="mixed" if mixed else "slow", float_valve=float_valve,
                duration_s=output[-1].elapsed,
                bit_peak_C=max(row.sensors_C[0][0] for row in output),
                black_box_peak_C=max(row.sensors_C[1][2] for row in output),
                energy_residual_J=sum(abs(row.energy_residual_J) for row in output),
                rock_exchange_J=sum(abs(row.into_rock_J) for row in output))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    event = next(r for r in audit.rows(audit.HERE/"run17-boundaries.csv")
                 if r["event"] == "stage-03")
    first, last = (rig.timestamp(event[key]) for key in ("start_pason", "end_pason"))
    data = np.array(list(rig.rig_inputs(args.archive, first, last)))
    if not np.all(np.isfinite(data[:, [1, 4]])) or np.any(np.diff(data[:, 0]) != 10):
        raise ValueError("incomplete stage input")
    write_csv(args.output, (calculate(event, data, cell_count=40, radial_nodes=40, cap=1.25,
                                      mixed=mixed, float_valve=float_valve)
                            for mixed in (False, True) for float_valve in (False, True)))


if __name__ == "__main__":
    main()
