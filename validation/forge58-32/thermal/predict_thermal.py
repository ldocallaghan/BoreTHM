"""Calculate the declared 58-32 thermal forecasts with the released package.

Part A: return temperature for each drilling window, for the primary (scaled)
and secondary (Pason) flow, with the v1.9.0 defaults, physics='v1.7.0' and the
analytical comparator. Part D: the heat bounds of the consistency rule.
Part B: the static fluid-column temperature at each scheduled log point.
"""
import os

# One BLAS thread per model process, so four processes use four cores.
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_name] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from datetime import datetime
from importlib import import_module
import json
from pathlib import Path
import sys

import numpy as np

import borethm
from borethm import fluids, model1_coupled as m1, physics as ph, rock_response, wall_thermal as wt
from borethm import site_evaluation as se
from borethm.fluids import Mud

c = import_module("validation.forge58-32.thermal.common")
thermal = import_module("validation.comparators.thermal")
PHYSICS = {"v1.9.0": None, "v1.7.0": "v1.7.0"}
FLOWS = {"primary": "flow_primary_gpm", "secondary": "flow_pason_gpm"}
BOUND_FILM_MULT = 1.0e3      # part D: film resistance removed
BOUND_EXPOSURE_S = m1.T_EXPOSURE_FLOOR   # part D: the shortest exposure the model allows
WALL = dict(n=120, growth=1.2)          # as the v1.9.0 trip and pause columns
STATE = None


def initialize():
    global STATE
    history = c.rig()
    STATE = dict(clock=c.Clock(history), survey=c.survey(), form=c.formation())


def fluid_for(row):
    pv, yp = c.number(row["pv_cP"]), c.number(row["yp"])
    return Mud(c.number(row["density_ppg"])*c.PPG, pv_ref=pv*1e-3 if np.isfinite(pv) else None,
               yield_point=yp*c.YP_PA if np.isfinite(yp) else 0., pv_ref_T=c.PV_REF_T)


def setup(bha, bit_ft, hole_ft, when, flow_gpm, inlet_C, tfa, fluid, casing=True, exposure=None):
    srv, form, clock = STATE["survey"], STATE["form"], STATE["clock"]
    depth = bit_ft*c.FT
    if not (depth > 0 and flow_gpm > 100 and np.isfinite(inlet_C) and np.isfinite(tfa)):
        raise ValueError("missing depth, pumped flow, inlet or nozzle area")
    geometry, flags = c.geometry(bha, depth, hole_ft, srv, casing)
    rho = float(m1.fluid_props(np.array([inlet_C]), np.array([m1.P_SURF]), fluid)[0][0])
    exposure = exposure or clock.exposure(when, geometry.md_bit)
    kw = dict(m_dot=rho*flow_gpm*c.GPM, T_inj=inlet_C, geotherm=form, geometry=geometry,
              target_rock_T=float(form(srv.tvd(depth))), Q_face=0., k_rock=c.K_ROCK,
              rhocp_rock=c.RHOCP_ROCK, friction_heat=True, tfa=tfa*c.INCH**2, fluid=fluid, verbose=False)
    return exposure, kw, flags


def solve(exposure, kw, physics):
    breaks = m1.exposure_breaks(exposure, kw["geometry"].md_bit)
    return m1.solve_seeded(exposure, breaks, **(kw | {"physics": physics}))


def analytical(exposure, kw):
    return thermal.analytical(kw["geometry"], kw["fluid"], kw["m_dot"], kw["T_inj"], kw["geotherm"],
                              exposure, kw["k_rock"], kw["rhocp_rock"])


def heat_bounds(row, flow_gpm, fluid):
    """Part D: the larger of the model rock-heat bound and the radial conduction bound, in W."""
    srv, form = STATE["survey"], STATE["form"]
    floor = lambda z: np.full(np.shape(z), BOUND_EXPOSURE_S, float)
    exposure, kw, _ = setup(row["bha"], c.number(row["bit_ft"]), c.number(row["hole_ft"]), row["time"], flow_gpm,
                            c.number(row["inlet_C"]), c.number(row["tfa_in2"]), fluid, casing=False, exposure=floor)
    out = {}
    result = m1.solve_seeded(floor, (), **(kw | dict(friction_heat=False, film_mult=BOUND_FILM_MULT)))
    if result["success"]:
        mean_T = 0.5*(result["T_return_surface"]+kw["T_inj"])
        cp = float(m1.fluid_props(np.array([mean_T]), np.array([m1.P_SURF]), fluids.with_default_rheology(fluid))[1][0])
        out["rock_bound_model_W"] = kw["m_dot"]*cp*(result["T_return_surface"]-kw["T_inj"])
    else:
        out["rock_bound_model_status"] = "solver failed"
    # Radial conduction from the profile into a wall held at the inlet temperature.
    alpha = c.K_ROCK/c.RHOCP_ROCK
    z = np.arange(0.5, kw["geometry"].md_bit/c.FT, 1.0)*c.FT
    radius = np.array([float(kw["geometry"].at(np.array([zi]))["r_rock"][0]) for zi in z])
    flux = rock_response.cylinder_flux(alpha*BOUND_EXPOSURE_S/radius**2)
    excess = np.maximum(form(srv.tvd(z))-kw["T_inj"], 0.)
    out["rock_bound_conduction_W"] = float(np.sum(2*np.pi*c.K_ROCK*excess*flux)*c.FT)
    out["rock_bound_W"] = max(out.get("rock_bound_model_W", -np.inf), out["rock_bound_conduction_W"])
    out["hydraulic_power_W"] = c.number(row["spp_psi"])*c.PSI*flow_gpm*c.GPM
    out["energy_limit_W"] = 1.25*(out["rock_bound_W"]+out["hydraulic_power_W"])
    return out


def predict_window(row):
    out = {k: row[k] for k in ("sample_id", "time", "bha", "input_status")}
    if row["input_status"] != "complete":
        return out
    fluid = fluid_for(row)
    for flow_name, key in FLOWS.items():
        q = c.number(row[key])
        try:
            exposure, kw, flags = setup(row["bha"], c.number(row["bit_ft"]), c.number(row["hole_ft"]), row["time"],
                                        q, c.number(row["inlet_C"]), c.number(row["tfa_in2"]), fluid)
        except (ValueError, KeyError, IndexError) as error:
            out[f"{flow_name}_input_status"] = str(error)
            continue
        out["components_as_drill_pipe"] = ";".join(flags)
        out[f"{flow_name}_mass_flow_kg_s"] = kw["m_dot"]
        for name, physics in PHYSICS.items():
            try:
                result = solve(exposure, kw, physics)
                out[f"{flow_name}_{name}_status"] = "converged" if result["success"] else "solver failed"
                if result["success"]:
                    out[f"{flow_name}_{name}_return_C"] = result["T_return_surface"]
                    out[f"{flow_name}_{name}_bit_C"] = result["T_bottom_delivered"]
            except (ValueError, KeyError, IndexError, RuntimeError, ArithmeticError) as error:
                out[f"{flow_name}_{name}_status"] = f"exception: {error}"
        try:
            comparison = analytical(exposure, kw)
            out[f"{flow_name}_analytical_return_C"] = float(comparison.closed_form(0.)[1])
        except (ValueError, ArithmeticError, np.linalg.LinAlgError) as error:
            out[f"{flow_name}_analytical_status"] = f"exception: {error}"
        try:
            out |= {f"{flow_name}_{k}": v for k, v in heat_bounds(row, q, fluid).items()}
        except (ValueError, KeyError, IndexError, RuntimeError, ArithmeticError) as error:
            out[f"{flow_name}_bound_status"] = f"exception: {error}"
    return out


# ---------- part B ----------

def wall_films(result, kw, physics, z):
    """Annulus temperature and hole-wall film coefficient at the end of circulation."""
    g = kw["geometry"]
    setting = ph.resolve(physics or "v1.8.0")
    Tu = np.interp(z, result["z"], result["Tu"])
    h = np.empty_like(z)
    fluid = fluids.with_default_rheology(kw["fluid"]) if setting["rheology_from_pv_yp"] else kw["fluid"]
    for i, zi in enumerate(z):
        props = g.at(np.array([zi]))
        props["tvd"] = g.survey.tvd(np.array([zi]))
        P = m1.P_of_z(props["tvd"])
        if setting["annulus_model"] in m1._ANNULUS_SETTINGS:
            band, viscosity = m1._ANNULUS_SETTINGS[setting["annulus_model"]]
            h[i] = float(m1.annulus_films(kw["m_dot"], props, np.array([Tu[i]]), P, fluid, band, viscosity)[1][0])
        else:
            h[i] = float(m1.h_dittus(kw["m_dot"], props["A_ann"], props["Dh_ann"], np.array([Tu[i]]), P, fluid=fluid)[0])
    return Tu, h


def predict_logs(plan, points, flow_name, physics_name):
    """One wall calculation per scheduled depth, read at every log time there."""
    srv, form = STATE["survey"], STATE["form"]
    row = plan[0]
    fluid = fluid_for(row)
    q = c.number(row["circ_flow_primary_gpm" if flow_name == "primary" else "circ_flow_pason_gpm"])
    end = row["circ_end"]
    exposure, kw, flags = setup(row["assembly_for_circulation"], c.number(row["circ_bit_ft"]), c.number(row["circ_hole_ft"]),
                                end, q, c.number(row["circ_inlet_C"]), c.number(row["tfa_in2"]), fluid)
    physics = PHYSICS[physics_name]
    result = solve(exposure, kw, physics)
    if not result["success"]:
        return [dict(p, **{f"{flow_name}_{physics_name}_status": "solver failed"}) for p in points]
    comparison = analytical(exposure, kw)
    depths = sorted({c.number(p["md_ft"]) for p in points})
    z = np.minimum(np.array(depths)*c.FT, kw["geometry"].md_bit)
    Tu, h = wall_films(result, kw, physics, z)
    t_end = datetime.fromisoformat(end)
    latest = max(datetime.fromisoformat(p["rig_time"]) for p in points)
    static_s = (latest-t_end).total_seconds()
    shoe = c.INTERMEDIATE["shoe_ft"]*c.FT
    series = {}
    for d, zi, Tu_i, h_i in zip(depths, z, Tu, h):
        tvd = float(srv.tvd(zi))
        T_rock = float(form(tvd))
        cased = zi < shoe
        a = c.INTERMEDIATE["id_in"]*c.INCH/2 if cased else c.PRODUCTION_HOLE_IN*c.INCH/2
        cap, hs = se._static_node(T_rock, tvd, a, 0.0, fluid)
        t_c = float(np.atleast_1d(exposure(np.array([zi])))[0])
        states = [wt.State("circulating", t_c, T_fluid=Tu_i, h=h_i),
                  wt.State("static", static_s, h=hs, C=cap, T_node0=Tu_i)]
        res = wt.run(states, T_rock, a, c.K_ROCK, c.RHOCP_ROCK, **WALL)
        after = res.t >= t_c
        series[d] = (np.r_[0., res.t[after]-t_c], np.r_[Tu_i, res.T_node[after]], Tu_i, cased, T_rock,
                     float(comparison.closed_form(zi)[1]))
    out = []
    for p in points:
        t_s, T_s, Tu_i, cased, T_rock, ana = series[c.number(p["md_ft"])]
        elapsed = (datetime.fromisoformat(p["rig_time"])-t_end).total_seconds()
        reheated = float(np.interp(elapsed, t_s, T_s))
        key = f"{flow_name}_{physics_name}"
        out.append(dict(log=p["log"], md_ft=p["md_ft"], rig_time=p["rig_time"], static_s=elapsed,
                        **{f"{key}_C": Tu_i if cased else reheated,
                           f"{key}_cased_reheated_C": reheated,
                           f"{key}_circulating_annulus_C": Tu_i,
                           f"{flow_name}_analytical_annulus_C": ana,
                           "formation_C": T_rock, "cased": cased}))
    return out


def run_logs(task):
    plan, points, flow_name, physics_name = task
    return predict_logs(plan, points, flow_name, physics_name)


def write(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def manifest(samples, output):
    """Package identity, input and code hashes, the code commit and prediction counts."""
    import subprocess
    root = c.WELL.parent.parent
    commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", "validation/forge58-32/thermal"],
                           capture_output=True, text=True).stdout.strip()
    rel = lambda p: p.resolve().relative_to(root).as_posix()
    inputs = sorted([*(samples/n for n in ("conditions.csv", "runs.csv", "log-plan.csv", "log-points.csv")),
                     *(c.INPUTS.iterdir()), c.HERE/"pt-headers.csv",
                     *(c.WELL/n for n in ("rig_inputs_10s.csv.gz", "bha_reports.csv", "bha_components.csv",
                                          "bit_inputs.csv", "mud_reports.csv", "survey.csv",
                                          "pressure-test/inputs/components.csv"))])
    code = [Path(__file__), c.HERE/"common.py", c.HERE/"prepare_thermal.py", c.HERE/"build_thermal_inputs.py",
            c.HERE/"read_pt_headers.py", root/"validation/comparators/thermal.py"]
    windows = c.read(output/"predictions.csv")
    logs = c.read(output/"log-predictions.csv")
    counts = dict(windows=len(windows), windows_complete_input=sum(r["input_status"] == "complete" for r in windows))
    for flow in FLOWS:
        for name in (*PHYSICS, "analytical"):
            key = f"{flow}_{name}_return_C"
            counts[key] = sum(bool(r.get(key)) for r in windows)
        counts[f"{flow}_all_three_returns"] = sum(all(r.get(f"{flow}_{n}_return_C") for n in (*PHYSICS, "analytical"))
                                                  for r in windows)
        counts[f"{flow}_energy_limit"] = sum(bool(r.get(f"{flow}_energy_limit_W")) for r in windows)
    counts["log_points"] = len(logs)
    for name in sorted({r["log"] for r in logs}):
        counts[f"log_points_{name}"] = sum(r["log"] == name for r in logs)
    package = Path(borethm.__file__).resolve().parent
    # The installed path below site-packages; the machine-specific prefix is not recorded.
    installed = Path(borethm.__file__).as_posix()
    installed = installed[installed.index("site-packages/"):]
    out = dict(package_version=borethm.__version__, package_file=installed,
               python=sys.version.split()[0], code_commit=commit, uncommitted_thermal_changes=bool(dirty),
               input_sha256={rel(p): c.sha(p) for p in inputs if p.is_file() and p.name != "manifest.json"},
               input_manifest_sha256=c.sha(c.INPUTS/"manifest.json"),
               code_sha256={rel(p): c.sha(p) for p in code},
               package_sha256={n: c.sha(package/n) for n in ("model1_coupled.py", "physics.py", "well_geometry.py",
                                                              "wall_thermal.py", "site_evaluation.py", "rock_response.py")},
               predictions_sha256={n: c.sha(output/n) for n in ("predictions.csv", "log-predictions.csv")},
               counts=counts)
    (output/"manifest.json").write_text(json.dumps(out, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps(counts, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("samples", type=Path, help="directory written by prepare_thermal.py")
    parser.add_argument("output", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0, help="first N windows only, for timing")
    parser.add_argument("--part", choices=("A", "B", "AB"), default="AB")
    args = parser.parse_args()
    if args.workers > 4:
        raise SystemExit("at most four model processes")
    if "site-packages" not in borethm.__file__:
        raise SystemExit(f"borethm is not the installed release: {borethm.__file__}")
    args.output.mkdir(parents=True, exist_ok=True)
    windows = c.read(args.samples/"conditions.csv")
    if args.limit:
        windows = windows[:args.limit]
    plan = c.read(args.samples/"log-plan.csv")
    points = c.read(args.samples/"log-points.csv")
    with ProcessPoolExecutor(max_workers=args.workers, initializer=initialize) as pool:
        if "B" in args.part:
            tasks = [(plan, points, f, p) for f in FLOWS for p in PHYSICS]
            merged = {}
            for rows in pool.map(run_logs, tasks):
                for r in rows:
                    merged.setdefault((r["log"], r["md_ft"], r["rig_time"]), {}).update(r)
            write(args.output/"log-predictions.csv", list(merged.values()))
            print("part B done", flush=True)
        if "A" in args.part:
            results = []
            for i, row in enumerate(pool.map(predict_window, windows, chunksize=1), 1):
                results.append(row)
                if i % 25 == 0:
                    print(f"{i}/{len(windows)} windows", flush=True)
            write(args.output/("predictions.csv" if not args.limit else "predictions-trial.csv"), results)
    if args.part == "AB" and not args.limit:
        manifest(args.samples, args.output)


if __name__ == "__main__":
    main()
