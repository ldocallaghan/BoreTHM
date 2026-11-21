"""Calculate the model-only forecast on the registered 56-32 input samples."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import csv
from dataclasses import replace
from importlib import import_module
import json
from pathlib import Path

import numpy as np

from borethm import hydraulic_losses as hl, model1_coupled as m1, tool_thermal as tt
from borethm import wall_thermal as wt, well_geometry as wg
from borethm.fluids import Mud
from validation.comparators import thermal
from validation.forge16b.sanvean.build_extracts import number, records, sha

prepare = import_module("validation.forge56-32.prepare_thermal")
p = prepare.pressure
HERE = Path(__file__).resolve().parent
MODES = ("v1.8.0", "v1.7.0")
STATE = None


def grouped(rows, key):
    out = defaultdict(list)
    for row in rows:
        out[row[key]].append(row)
    return out


def initialize():
    global STATE
    times, flow, hole, _ = p.rig_inputs()
    survey = p.survey()
    components = grouped(p.read("bha_components.csv"), "bha_sheet_id")
    bits = {r["run_sequence"]: r for r in p.read("bit_records.csv")}
    runs = {r["bha_sheet_id"]: r for r in p.read("bha_runs.csv")}
    areas = {r["bha_sheet_id"]: float(bits[r["bit_run_sequence"]]["TFA_in2"])
             for r in p.read("bha_crosswalk.csv") if bits[r["bit_run_sequence"]]["TFA_in2"]}
    STATE = p.Clock(times, flow, hole), survey, p.a.formation("216", p.a.survey())[0], components, runs, areas


def geometry(bha, depth, survey, components, runs, differential=0.):
    section = number(runs[bha]["hole_size_in"])
    if section == 8.75:
        hole = p.hole(depth)
    else:
        shoe, od, casing_id, drilled = (
            (129, 20., 19., 26.) if section == 17.5 else (382, 13.375, 12.615, 17.5))
        length = min(depth, shoe*p.FT)
        hole = [wg.cased(0., length, casing_id*p.INCH, od*p.INCH, drilled*p.INCH)]
        if length < depth:
            hole.append(wg.open_hole(length, depth, section*p.INCH))
    pipe = p.pipe("ordinary 5 in pipe", 5., 4.276,
                  hl.HydraulicJoint(6.625*p.INCH, 3.25*p.INCH, 29*p.INCH, 31.5*p.FT,
                                    source="56-32 pressure protocol connection scenario"))
    bottom, remaining = [], depth
    for row in sorted(components[bha], key=lambda r: int(r["item"])):
        if row["item"] == "1":
            continue
        name = " ".join(row["description"].split())
        od, bore, length = (number(row[k]) for k in ("OD_in", "ID_in", "length_ft"))
        cls = name.lower()
        if "motor" in cls:
            following = components[bha][int(row["item"])]
            bore = number(following["ID_in"])
            tools = (wg.DownholeTool("mud_motor", od, differential=differential, source=name),)
        elif "shock" in cls:
            bore = bore if np.isfinite(bore) else 2.875
            tools = ()
        else:
            tools = ()
        shape = p.pipe(name, od, bore) if np.isfinite(od+bore) else pipe
        if remaining <= 1e-6:
            break
        take = min(remaining, length*p.FT)
        bottom.append(wg.StringSegment(take, shape, tools=tools))
        remaining -= take
    if remaining > 1e-6:
        bottom.append(wg.StringSegment(remaining, pipe))
    else:
        bottom[-1] = replace(bottom[-1], length=bottom[-1].length+remaining)
    return wg.WellGeometry(list(reversed(bottom)), hole, survey)


def circulation(sample, previous=False):
    clock, survey, form, components, runs, areas = STATE
    prior = "preceding_" if previous else ""
    bha = sample[prior+"bha"]
    if bha not in runs:
        raise ValueError("no uniquely assigned circulation assembly")
    depth = number(sample[prior+"bit_ft"])*p.FT
    rate = number(sample[prior+"flow_gpm"])
    inlet = number(sample[prior+"inlet_C"])
    density = number(sample["density_ppg"])
    if not (depth > 0 and rate > 100 and np.isfinite(inlet+density)):
        raise ValueError("missing depth, pumped flow, inlet or mud density")
    dp = number(sample.get(prior+"motor_differential_psi"))
    dp = max(0., dp) if np.isfinite(dp) else 0.
    geometry_ = geometry(bha, depth, survey, components, runs, dp*p.PSI)
    pv, yp = number(sample["pv_cP"]), number(sample["yp"])
    fluid = Mud(density*p.PPG, pv_ref=pv*1e-3 if np.isfinite(pv) else None,
                yield_point=yp*p.YP_PA if np.isfinite(yp) else 0., pv_ref_T=48.9)
    rho = float(m1.fluid_props(np.array([inlet]), np.array([m1.P_SURF]), fluid)[0][0])
    stamp = sample["preceding_circ_end"] if previous else sample["time"]
    exposure = clock.exposure(stamp, geometry_.md_bit)
    kw = dict(m_dot=rho*rate*p.GPM, T_inj=inlet, geotherm=form, geometry=geometry_,
              target_rock_T=float(form(survey.tvd(depth))), Q_face=0., k_rock=p.b.K_ROCK,
              rhocp_rock=p.b.RHOCP_ROCK, friction_heat=True, tfa=areas[bha]*p.INCH**2,
              fluid=fluid, verbose=False)
    return exposure, kw, dp*p.PSI*rate*p.GPM


def static_tool(sample, prior, kw, depth):
    survey, form = STATE[1:3]
    md = max(0., depth-84*p.FT)
    g = kw["geometry"]
    props = g.at(np.array([min(md, g.md_bit)]))
    initial = float(prior["sol"].sol(min(md, g.md_bit))[0])
    rho, cp, _, k = (float(x[0]) for x in m1.fluid_props(
        np.array([initial]), m1.P_of_z(props["tvd"]), kw["fluid"]))
    r_bore, r_out, a = (float(props[key][0]) for key in ("r_bore", "r_out", "r_wall"))
    lump = tt.Lump.of_pipe(r_bore, r_out, rho*cp)
    hi, ho = wt.NU_LAMINAR*k/lump.D_in, wt.NU_LAMINAR*k/(2*(a-r_out))
    from datetime import datetime
    duration = (datetime.fromisoformat(sample["sample_end"])-datetime.fromisoformat(sample["sample_start"])).total_seconds()
    if sample["kind"] == "trip_stage":
        start = max(0., number(sample["bit_start_ft"])*p.FT-84*p.FT)
        if md <= start:
            raise ValueError("no downhole travel at the MWD proxy")
        def column(z):
            return float(prior["sol"].sol(z)[1]) if z <= g.md_bit else float(form(survey.tvd(z)))
        t0 = float(form(survey.tvd(0.))) if start == 0 else column(start)
        hist, _ = tt.trip_in(lump, lambda z: column(start+z), md-start, (md-start)/duration,
                             t0, ho, hi, dt=10.)
        return hist.peak()[0]
    if md > g.md_bit:
        raise ValueError("preceding circulation stops above the MWD proxy")
    outside = float(prior["sol"].sol(md)[1])
    hp = float(m1.h_dittus(kw["m_dot"], props["A_ann"], props["Dh_ann"],
                           np.array([outside]), m1.P_of_z(props["tvd"]), fluid=kw["fluid"])[0])
    circ = float(sample["preceding_duration_s"])
    states = [wt.State("circulating", circ, T_fluid=outside, h=hp),
              wt.State("static", duration, h=ho, C=rho*cp*np.pi*(a*a-r_out*r_out), T_node0=outside)]
    rock = float(form(survey.tvd(md)))
    wall = wt.run(states, rock, a, kw["k_rock"], kw["rhocp_rock"], n=120, growth=1.2)
    history = tt.run(lump, [tt.Segment(duration, lambda t: np.interp(t+circ, wall.t, wall.T_node),
                                       ho, hi)], tt.steady_steel(initial, outside, hi, hp, lump), initial)
    return history.peak()[0]


def predict(sample):
    row = {k: sample[k] for k in ("sample_id", "kind", "bha")}
    previous = sample["kind"] != "drilling"
    depth = number(sample["bit_ft"])*p.FT
    if sample["kind"] == "trip_stage":
        row["undisturbed_formation_C"] = float(thermal.undisturbed_formation(
            max(0., depth-84*p.FT), STATE[1], STATE[2]))
    try:
        exposure, kw, motor_face_W = circulation(sample, previous)
    except (ValueError, KeyError, IndexError) as error:
        return row | {"input_status": str(error)}
    row["input_status"] = "complete"
    breaks = m1.exposure_breaks(exposure, kw["geometry"].md_bit)
    z = max(0., kw["geometry"].md_bit-84*p.FT)
    for physics in MODES:
        try:
            face = motor_face_W if physics == "v1.7.0" else 0.
            result = m1.solve_seeded(exposure, breaks, **(kw | {"Q_face": face}), physics=physics)
            row[f"{physics}_circulation_status"] = "converged" if result["success"] else "solver failed"
            if result["success"]:
                row[f"{physics}_bit_bore_C"] = result["T_bottom_delivered"]
                row[f"{physics}_84ft_bore_C"] = float(result["sol"].sol(z)[0])
                row[f"{physics}_return_C"] = result["T_return_surface"]
                if previous:
                    row[f"{physics}_event_peak_C"] = static_tool(sample, result, kw, depth)
        except (ValueError, KeyError, IndexError, RuntimeError) as error:
            row[f"{physics}_exception"] = str(error)
    try:
        comparison = thermal.analytical(kw["geometry"], kw["fluid"], kw["m_dot"], kw["T_inj"],
                                       kw["geotherm"], exposure, kw["k_rock"], kw["rhocp_rock"])
        row["analytical_bit_bore_C"] = float(comparison.closed_form(comparison.length)[0])
        row["analytical_84ft_bore_C"] = float(comparison.closed_form(z)[0])
        row["analytical_return_C"] = float(comparison.closed_form(0.)[1])
    except (ValueError, ArithmeticError, np.linalg.LinAlgError) as error:
        row["analytical_exception"] = str(error)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    conditions = args.output/"conditions.csv"
    with conditions.open(encoding="utf-8", newline="") as stream:
        samples = list(csv.DictReader(stream))
    results = []
    with ProcessPoolExecutor(max_workers=args.workers, initializer=initialize) as pool:
        for i, row in enumerate(pool.map(predict, samples, chunksize=1), 1):
            results.append(row)
            if i % 25 == 0:
                print(f"{i}/{len(samples)} samples", flush=True)
    records(args.output/"predictions.csv", results)
    source = [conditions, args.output/"availability-by-pump.csv", args.output/"source-availability.json", Path(__file__),
              Path(prepare.__file__), *(HERE/name for name in
              ("thermal_protocol.md", "rig_inputs_10s.csv.gz", "mud_reports.csv", "bha_crosswalk.csv",
               "bha_components.csv", "bha_runs.csv", "bit_records.csv", "survey.csv")),
              HERE.parent/"forge16a/formation_temperature_216day.csv"]
    import borethm
    package_source = Path(borethm.__file__).resolve().parent
    manifest = dict(package_version=borethm.__version__,
                    input_sha256={f"validation/{f.relative_to(HERE.parent).as_posix()}": sha(f.resolve())
                                  for f in (path.resolve() for path in source)},
                    model_sha256={name: sha(package_source/name) for name in
                                  ("model1_coupled.py", "physics.py", "well_geometry.py", "tool_thermal.py", "wall_thermal.py")},
                    predictions_sha256=sha(args.output/"predictions.csv"))
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
