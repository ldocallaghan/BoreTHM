"""Model runs for the 56-32 shallow-assembly diagnosis, on the forecast's code.

usage: model_runs.py bound FORECAST_TREE [--workers N] [--film-mult X] [--only BHA,...]
       model_runs.py sensitivity FORECAST_TREE [--workers N]

FORECAST_TREE is a checkout of the commit the v1.8.0 predictions were made
at, with that checkout's package installed in the running interpreter. Its
predict_thermal.py builds every circulation as the forecast did; this script
changes only the settings named below and writes into this folder.

bound: for every scored window, the largest heat the rock could give the
fluid, by two routes.

  rock_model_W      the v1.8.0 circulation with every setting chosen to
                    raise heat gain: the hotter of the 16A transfer and the
                    native cement bond log at each depth; open hole of the
                    drilled diameter everywhere (no casing or cement); one
                    hour of exposure at every depth, the model's floor; the
                    annulus film coefficients times FILM_MULT; the top of
                    the FORGE core conductivity range and the highest core
                    density and heat capacity; friction and motor heat off,
                    so the return rise is rock heat alone.
  conduction_bound_W  the radial conduction from the same hottest profile
                    into a wall held at the inlet temperature, with no film,
                    casing or cement, the same rock properties, and each
                    depth's exposure the smaller of its recorded value and
                    one hour (at least 1 s).

  Measured heat is m_dot cp (return - inlet), and hydraulic heat is
  standpipe pressure times volumetric flow. Output: energy_balance.csv.

sensitivity: the declared v1.8.0 calculation for the scored windows of
assemblies 2 to 5 with one input changed at a time: the native profile in
place of the 16A transfer, the daily report "In" temperature as the inlet,
and the inlet implied by the measured return less the median measured
return minus inlet of assemblies 6 to 11. Output: sensitivity.csv.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from dataclasses import replace
from importlib import import_module
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
FT, INCH, PSI, GPM = 0.3048, 0.0254, 6894.757293168361, 3.785411784e-3/60
SHALLOW = ("2", "3", "4", "5")
DEEP = ("6", "7", "8", "9", "10", "11")
# FORGE granitoid cores (MetaRock 2021, tabulated by Xing et al. 2026), as
# carried in borethm.studies.validate_forge16b: K_ROCK_RANGE and the highest
# of the three densities and of the three heat capacities.
K_ROCK_MAX = 3.087
RHOCP_ROCK_MAX = 2680.0*1091.1
EXPOSURE_S = 3600.0
FILM_MULT = 100.0
# Drilled diameters, in. The 0 to 129 ft interval takes the conductor's
# 20 in outside diameter, the smallest hole it could sit in.
HOLE_SECTIONS = ((129., 20.), (382., 17.5), (3494., 12.25), (math.inf, 8.75))
STATE = {}


def load(tree):
    """Import the forecast's prediction module from TREE."""
    sys.path.insert(0, str(Path(tree).resolve()))
    pt = import_module("validation.forge56-32.predict_thermal")
    import borethm
    package = Path(borethm.__file__).resolve()
    if not package.is_relative_to(Path(tree).resolve()):
        raise RuntimeError(f"borethm is imported from {package}, outside the forecast tree")
    return pt


def read(path):
    with open(path, encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def native_profile():
    """CBL MTEM by TVD [m] -> C, with its end values held beyond the log."""
    rows = [r for r in read(HERE/"native_temperature_logs.csv") if r["log"] == "cbl_mtem"]
    tvd = np.array([float(r["tvd_ft"]) for r in rows])*FT
    temp = np.array([float(r["temperature_C"]) for r in rows])
    order = np.argsort(tvd)
    tvd, temp = tvd[order], temp[order]
    return lambda z: np.interp(np.asarray(z, float), tvd, temp)


def initialize(tree):
    pt = load(tree)
    pt.initialize()
    transfer = pt.STATE[2]
    native = native_profile()
    STATE.update(pt=pt, transfer=transfer, native=native,
                 hottest=lambda z: np.maximum(transfer(z), native(z)))


def open_hole(depth):
    import borethm.well_geometry as wg
    intervals, top = [], 0.
    for bottom_ft, diameter in HOLE_SECTIONS:
        bottom = min(bottom_ft*FT, depth+1e-6)
        if top < bottom:
            intervals.append(wg.open_hole(top, bottom, diameter*INCH))
        top = bottom
    return intervals


def heat_capacity(fluid, t_in, t_out):
    """Mean cp over the inlet-to-return interval at atmospheric pressure."""
    import borethm.model1_coupled as m1
    temps = np.linspace(t_in, t_out, 9)
    return float(np.mean(m1.fluid_props(temps, np.full(9, m1.P_SURF), fluid)[1]))


def raw_exposure(stamp, md_bit):
    """Recorded circulation time since the bit first reached each depth, unfloored."""
    import borethm.model1_coupled as m1
    clock = STATE["pt"].STATE[0]
    seconds = (np.datetime64(stamp)-clock.t0).astype("timedelta64[s]").astype(float)
    now = float(np.interp(seconds, clock.seconds, clock.circ))
    return m1.exposure_from_history(clock.circ, clock.depth, now)


def conduction_bound(md_bit, t_in, stamp):
    from borethm import rock_response as rr
    pt = STATE["pt"]
    survey = pt.STATE[1]
    z = np.linspace(0., md_bit, 4001)
    radius = np.select([z <= b*FT for b, _ in HOLE_SECTIONS], [d*INCH/2 for _, d in HOLE_SECTIONS])
    t = np.clip(raw_exposure(stamp, md_bit)(z), 1., EXPOSURE_S)
    resistance = rr.resistance(t, K_ROCK_MAX/RHOCP_ROCK_MAX, radius, K_ROCK_MAX, "cylinder")
    drive = np.maximum(STATE["hottest"](survey.tvd(z))-t_in, 0.)
    return float(np.trapezoid(drive/resistance, z))


def bound_row(window, film_mult):
    import borethm.model1_coupled as m1
    pt = STATE["pt"]
    survey = pt.STATE[1]
    sample = dict(window["conditions"])
    sample["motor_differential_psi"] = "0"
    row = dict(sample_id=window["sample_id"], bha=window["bha"], time=window["time"])
    try:
        _, kw, _ = pt.circulation(sample)
    except (ValueError, KeyError, IndexError) as error:
        return row | dict(bound_status=f"input: {error}")
    g = kw["geometry"]
    depth = g.md_bit
    tvd_bit = float(survey.tvd(depth))
    t_in, t_out = float(window["inlet_C"]), float(window["measured_return_C"])
    fluid = kw["fluid"]
    rho = float(m1.fluid_props(np.array([t_in]), np.array([m1.P_SURF]), fluid)[0][0])
    q = float(window["flow_gpm"])*GPM
    cp = heat_capacity(fluid, t_in, t_out)
    section = pt.number(pt.STATE[4][window["bha"]]["hole_size_in"])
    shoe_ft = {17.5: 129., 12.25: 382., 8.75: 3494.}[section]
    path = np.linspace(shoe_ft*FT, depth, 400)
    row.update(bit_ft=depth/FT, tvd_bit_ft=tvd_bit/FT, open_hole_top_ft=shoe_ft,
               flow_gpm=window["flow_gpm"], inlet_C=t_in, measured_return_C=t_out,
               density_ppg=window["conditions"]["density_ppg"], rho_kg_m3=rho, cp_J_kgK=cp,
               measured_Q_W=rho*q*cp*(t_out-t_in),
               hydraulic_W=float(window["spp_psi"])*PSI*q,
               formation_bit_transfer_C=float(STATE["transfer"](tvd_bit)),
               formation_bit_hottest_C=float(STATE["hottest"](tvd_bit)),
               formation_open_max_transfer_C=float(np.max(STATE["transfer"](survey.tvd(path)))),
               formation_open_max_hottest_C=float(np.max(STATE["hottest"](survey.tvd(path)))),
               conduction_bound_W=conduction_bound(depth, t_in, window["time"]))
    settings = kw | dict(geotherm=STATE["hottest"], target_rock_T=float(STATE["hottest"](tvd_bit)),
                         geometry=type(g)(g.string, open_hole(depth), g.survey),
                         k_rock=K_ROCK_MAX, rhocp_rock=RHOCP_ROCK_MAX, friction_heat=False,
                         Q_face=0., film_mult=film_mult)
    exposure = lambda s: np.full_like(np.asarray(s, float), EXPOSURE_S)
    try:
        result = m1.solve_seeded(exposure, (), **settings, physics="v1.8.0")
    except (ValueError, RuntimeError, ArithmeticError) as error:
        return row | dict(bound_status=f"solver: {error}")
    if not result["success"]:
        return row | dict(bound_status="solver failed")
    rise = result["T_return_surface"]-t_in
    row.update(bound_status="converged", rock_model_return_C=result["T_return_surface"],
               rock_model_W=rho*q*cp*rise)
    return row


def sensitivity_row(job):
    import borethm.model1_coupled as m1
    pt = STATE["pt"]
    window, case, inlet = job
    sample = dict(window["conditions"])
    if inlet is not None:
        sample["inlet_C"] = repr(inlet)
    row = dict(sample_id=window["sample_id"], bha=window["bha"], case=case,
               inlet_C=sample["inlet_C"], measured_return_C=window["measured_return_C"])
    try:
        exposure, kw, _ = pt.circulation(sample)
    except (ValueError, KeyError, IndexError) as error:
        return row | dict(status=f"input: {error}")
    if case == "native profile":
        tvd_bit = float(pt.STATE[1].tvd(kw["geometry"].md_bit))
        kw = kw | dict(geotherm=STATE["native"], target_rock_T=float(STATE["native"](tvd_bit)))
    breaks = m1.exposure_breaks(exposure, kw["geometry"].md_bit)
    try:
        result = m1.solve_seeded(exposure, breaks, **kw, physics="v1.8.0")
    except (ValueError, RuntimeError, ArithmeticError) as error:
        return row | dict(status=f"solver: {error}")
    if not result["success"]:
        return row | dict(status="solver failed")
    return row | dict(status="converged", v180_return_C=result["T_return_surface"],
                      error_C=result["T_return_surface"]-float(window["measured_return_C"]))


def windows(tree, assemblies=None):
    conditions = {r["sample_id"]: r for r in read(Path(tree)/"validation/forge56-32/predictions-v1.8.0/conditions.csv")}
    out = []
    for r in read(HERE/"window_surface.csv"):
        if assemblies and r["bha"] not in assemblies:
            continue
        out.append(r | dict(conditions=conditions[r["sample_id"]]))
    return out


def report_inlets():
    """Daily report 'In' (F) by sample date; a window takes the nearest earlier-or-same report sample."""
    rows = [r for r in read(HERE/"report_temperatures.csv")
            if r["source"] == "daily drilling report" and r["in_F"] and r["sample_time"]]
    stamps = [(np.datetime64(f"{r['report_date']}T{r['sample_time']}"), (float(r["in_F"])-32)/1.8) for r in rows]
    return sorted(stamps)


def nearest_report_inlet(stamps, when):
    t = np.datetime64(when.replace(" ", "T"))
    return min(stamps, key=lambda s: (abs((s[0]-t).astype("timedelta64[s]").astype(float)), s[0]))[1]


def tree_commit(tree):
    return subprocess.run(["git", "-C", str(tree), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("bound", "sensitivity"))
    parser.add_argument("tree", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--film-mult", type=float, default=FILM_MULT)
    parser.add_argument("--only", help="comma-separated assemblies")
    parser.add_argument("--output", type=Path, default=HERE)
    args = parser.parse_args()
    if args.workers > 4:
        raise SystemExit("at most 4 worker processes")
    commit = tree_commit(args.tree)
    only = tuple(args.only.split(",")) if args.only else None
    with ProcessPoolExecutor(max_workers=args.workers, initializer=initialize, initargs=(str(args.tree),)) as pool:
        if args.action == "bound":
            ws = windows(args.tree, only)
            rows = list(pool.map(bound_row, ws, [args.film_mult]*len(ws), chunksize=1))
            name = "energy_balance.csv" if args.film_mult == FILM_MULT and not only else \
                f"energy_balance_film{args.film_mult:g}{'_'+'-'.join(only) if only else ''}.csv"
        else:
            ws = windows(args.tree, SHALLOW)
            deep = [float(r["measured_return_C"])-float(r["inlet_C"]) for r in windows(args.tree, DEEP)]
            offset = float(np.median(deep))
            stamps = report_inlets()
            jobs = []
            for w in ws:
                jobs += [(w, "declared", None), (w, "native profile", None),
                         (w, "daily report inlet", nearest_report_inlet(stamps, w["time"])),
                         (w, "implied inlet", float(w["measured_return_C"])-offset)]
            rows = list(pool.map(sensitivity_row, jobs, chunksize=1))
            name = "sensitivity.csv"
    write(args.output/name, rows)
    meta = dict(forecast_commit=commit, action=args.action)
    if args.action == "bound":
        meta.update(film_mult=args.film_mult, k_rock_W_mK=K_ROCK_MAX, rhocp_rock_J_m3K=RHOCP_ROCK_MAX,
                    exposure_s=EXPOSURE_S, physics="v1.8.0", friction_heat=False, motor_heat=False,
                    profile="larger of the 16A transfer and the CBL MTEM log at each TVD",
                    hole_sections=[dict(bottom_ft=b if math.isfinite(b) else "bit", diameter_in=d)
                                   for b, d in HOLE_SECTIONS],
                    assemblies=list(only) if only else "all scored")
    else:
        meta.update(assemblies=list(SHALLOW), physics="v1.8.0", other_settings="as declared",
                    deep_median_return_minus_inlet_C=offset,
                    native_profile="CBL MTEM by TVD, end values held",
                    report_inlet="nearest daily report 'In' sample in time")
    (args.output/(Path(name).stem+"-source.json")).write_text(json.dumps(meta, indent=2)+"\n",
                                                             encoding="utf-8", newline="\n")
    print(name, len(rows), "rows;", sum(r.get("bound_status", r.get("status")) == "converged" for r in rows), "converged")


if __name__ == "__main__":
    main()
