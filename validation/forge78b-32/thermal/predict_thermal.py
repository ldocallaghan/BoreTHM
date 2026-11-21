"""Calculate the declared 78B-32 thermal forecasts with the released package.

usage: python -m validation.forge78b-32.thermal.predict_thermal SAMPLES OUTPUT [--workers N] [--limit N]

For each window with complete inputs: the drill-string fluid temperature at
the downhole sensor and at the Sanvean sensor positions, and the surface
return temperature, from the v1.9.0 defaults, physics='v1.7.0' and the
analytical comparator. Reads only the committed samples and inputs.
"""
import os

# One BLAS thread per model process.
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_name] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

import borethm
from borethm import model1_coupled as m1

c = import_module("validation.forge78b-32.thermal.common")
thermal = import_module("validation.comparators.thermal")
PHYSICS = {"v1.9.0": None, "v1.7.0": "v1.7.0"}
MAX_WORKERS = 3
STATE = None


def initialize():
    global STATE
    STATE = dict(clock=c.Clock(c.rig()), survey=c.survey(), form=c.formation())


def setup(row):
    srv, form, clock = STATE["survey"], STATE["form"], STATE["clock"]
    depth = c.number(row["bit_ft"])*c.FT
    flow, inlet, tfa = (c.number(row[k]) for k in ("flow_gpm", "inlet_C", "tfa_in2"))
    if not (depth > 0 and flow > 100 and np.isfinite(inlet) and np.isfinite(tfa)):
        raise ValueError("missing depth, pumped flow, inlet or nozzle area")
    fluid, _ = c.fluid_for(c.number(row["density_ppg"]), c.number(row["pv_cP"]), c.number(row["yp"]))
    geometry, flags, pipe = c.geometry(row["bha"], depth, srv)
    rho = float(m1.fluid_props(np.array([inlet]), np.array([m1.P_SURF]), fluid)[0][0])
    exposure = clock.exposure(row["centre"], geometry.md_bit)
    kw = dict(m_dot=rho*flow*c.GPM, T_inj=inlet, geotherm=form, geometry=geometry,
              target_rock_T=float(form(srv.tvd(depth))), Q_face=0., k_rock=c.K_ROCK,
              rhocp_rock=c.RHOCP_ROCK, friction_heat=True, tfa=tfa*c.INCH**2, fluid=fluid, verbose=False)
    return exposure, kw, flags, pipe


def positions(row):
    """Measured depths (m) of the forecast points: name -> depth, or NaN above surface."""
    bit = c.number(row["bit_ft"])
    out = {}
    for name, key in (("sensor", "sensor_offset_ft"), ("sanvean_lower", "sanvean_lower_offset_ft"),
                      ("sanvean_upper", "sanvean_upper_offset_ft")):
        offset = c.number(row.get(key))
        md = bit-offset
        out[name] = md*c.FT if np.isfinite(md) and md > 0 else np.nan
    return out


def predict_window(row):
    out = {k: row[k] for k in ("sample_id", "centre", "bha", "input_status")}
    if row["input_status"] != "complete":
        return out
    try:
        exposure, kw, flags, pipe = setup(row)
    except (ValueError, KeyError, IndexError, StopIteration) as error:
        out["input_status"] = f"setup: {error}"
        return out
    out |= dict(component_flags=";".join(flags), drill_pipe=pipe, mass_flow_kg_s=kw["m_dot"])
    points = {k: v for k, v in positions(row).items() if np.isfinite(v)}
    for name, physics in PHYSICS.items():
        try:
            breaks = m1.exposure_breaks(exposure, kw["geometry"].md_bit)
            result = m1.solve_seeded(exposure, breaks, **(kw | {"physics": physics}))
            out[f"{name}_status"] = "converged" if result["success"] else "solver failed"
            if result["success"]:
                out[f"{name}_return_C"] = float(result["T_return_surface"])
                out[f"{name}_bit_C"] = float(result["T_bottom_delivered"])
                for point, z in points.items():
                    out[f"{name}_{point}_C"] = float(np.interp(z, result["z"], result["Td"]))
        except (ValueError, KeyError, IndexError, RuntimeError, ArithmeticError) as error:
            out[f"{name}_status"] = f"exception: {error}"
    try:
        case = thermal.analytical(kw["geometry"], kw["fluid"], kw["m_dot"], kw["T_inj"], kw["geotherm"],
                                  exposure, kw["k_rock"], kw["rhocp_rock"])
        out["analytical_return_C"] = float(case.closed_form(0.)[1])
        for point, z in points.items():
            out[f"analytical_{point}_C"] = float(case.closed_form(z)[0])
        out["analytical_status"] = "calculated"
    except (ValueError, ArithmeticError, np.linalg.LinAlgError) as error:
        out["analytical_status"] = f"exception: {error}"
    return out


def write(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def manifest(samples, output, windows):
    """Package identity, input and code hashes, the code commit and prediction counts."""
    root = c.WELL.parent.parent
    git = lambda *a: subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True).stdout.strip()
    rel = lambda p: p.resolve().relative_to(root).as_posix()
    inputs = sorted([samples/"windows.csv", samples/"qualified-bins.csv.gz", c.FORMATION_FILE,
                     *(p for p in c.INPUTS.iterdir() if p.is_file())])
    code = [Path(__file__), c.HERE/"common.py", c.HERE/"prepare_thermal.py", root/"validation/comparators/thermal.py"]
    rows = c.read(output/"predictions.csv")
    by_id = {w["sample_id"]: w for w in windows}
    counts = dict(windows=len(rows), windows_complete_input=sum(r["input_status"] == "complete" for r in rows))
    for part, quantity in (("part_a", "sensor"), ("part_b_eye", "sensor"), ("part_b_return", "return"),
                           ("part_b_sanvean", "sanvean_lower"), ("part_b_sanvean", "sanvean_upper")):
        sub = [r for r in rows if by_id[r["sample_id"]][part] == "True"]
        key = f"{part}_{quantity}" if part == "part_b_sanvean" else part
        counts[f"{key}_windows"] = len(sub)
        for name in (*PHYSICS, "analytical"):
            counts[f"{key}_{name}"] = sum(bool(r.get(f"{name}_{quantity}_C")) for r in sub)
        counts[f"{key}_all_three"] = sum(all(r.get(f"{n}_{quantity}_C") for n in (*PHYSICS, "analytical")) for r in sub)
    package = Path(borethm.__file__).resolve().parent
    installed = Path(borethm.__file__).as_posix()
    installed = installed[installed.index("site-packages/"):]
    out = dict(package_version=borethm.__version__, package_file=installed, python=sys.version.split()[0],
               code_commit=git("rev-parse", "HEAD"),
               uncommitted_thermal_changes=bool(git("status", "--porcelain", "--", "validation/forge78b-32/thermal")),
               input_sha256={rel(p): c.sha(p) for p in inputs},
               code_sha256={rel(p): c.sha(p) for p in code},
               package_sha256={n: c.sha(package/n) for n in ("model1_coupled.py", "physics.py", "well_geometry.py",
                                                              "fluids.py", "rock_response.py")},
               predictions_sha256={"predictions.csv": c.sha(output/"predictions.csv")},
               counts=counts)
    (output/"manifest.json").write_text(json.dumps(out, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps(counts, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("samples", type=Path, help="directory written by prepare_thermal.py")
    parser.add_argument("output", type=Path)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--limit", type=str, default="", help="comma-separated sample ids, for timing")
    args = parser.parse_args()
    if args.workers > MAX_WORKERS:
        raise SystemExit(f"at most {MAX_WORKERS} model processes")
    if "site-packages" not in borethm.__file__:
        raise SystemExit(f"borethm must be the installed release; found {borethm.__file__}")
    args.output.mkdir(parents=True, exist_ok=True)
    windows = c.read(args.samples/"windows.csv")
    todo = [w for w in windows if w["sample_id"] in args.limit.split(",")] if args.limit else windows
    results = []
    with ProcessPoolExecutor(max_workers=args.workers, initializer=initialize) as pool:
        for i, row in enumerate(pool.map(predict_window, todo, chunksize=1), 1):
            results.append(row)
            if i % 20 == 0:
                print(f"{i}/{len(todo)} windows", flush=True)
    write(args.output/("predictions.csv" if not args.limit else "predictions-trial.csv"), results)
    if not args.limit:
        manifest(args.samples, args.output, windows)


if __name__ == "__main__":
    main()
