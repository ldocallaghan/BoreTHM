"""Use frozen FORGE samples for the formation-profile and sensor comparisons."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import csv
import json
from pathlib import Path
import sys

import numpy as np

from validation.forge16b.sanvean.build_extracts import number, records, timestamp

HERE = Path(__file__).resolve().parent
ENTRY14 = HERE.parent/"entry-14"
FORGE16A = HERE.parents[1]/"forge16a"
STATE = None
CHANNELS = ("bit_box_C", "top_sub_C", "lower_mandrel_C")


def initialize():
    global STATE
    sys.path.insert(0, str(ENTRY14))
    import forge_tools

    calc = forge_tools.entry13.diagnosis.Calculation()
    a, b = calc.score.a, calc.score.b
    _, tb, cb, db = calc.whole.clock(HERE.parents[1]/"forge16b")
    ta, ca, da, _ = calc.adapter.energy.clock_a(FORGE16A)
    form = a.formation("216", a.survey())[0]
    sensor_data = {}
    for run in a.read("run_inputs.csv"):
        rows = a.read(f"sanvean_BHA{run['run']}_10s.csv")
        time = np.array([timestamp(row["time"]) for row in rows])
        data = {key: np.array([number(row[key]) for row in rows]) for key in
                ("flow_gpm", "on_bottom_flag", "invalid_flow_count",
                 *(f"drilling_{k}" for k in CHANNELS), *(f"drilling_{k}_count" for k in CHANNELS))}
        sensor_data[run["run"]] = (time, data)
    STATE = calc, forge_tools, b.T_FORM, form, {"16A": (ta, ca, da), "16B": (tb, cb, db)}, sensor_data


def solve(sample):
    calc, tools, legacy_form, tvd_form, clocks, sensors = STATE
    m1, b, whole = calc.m1, calc.score.b, calc.whole
    well, run = sample["well"], sample["run"]
    g = tools.with_tools(tools.entry13.geometry(calc, sample, "tapered_primary"))
    time, clock, depth = clocks[well]
    exposure = m1.smooth_exposure(m1.exposure_from_history(
        clock, depth, float(np.interp(sample["time_s"], time, clock))), g.md_bit)
    breaks = m1.exposure_breaks(exposure, g.md_bit)
    fluid, pv, yp = calc.fluid(sample)
    inlet = sample["T_in_C"]
    rho = float(m1.fluid_props(np.array([inlet]), np.array([m1.P_SURF]), fluid)[0][0])
    q = sample["flow_gpm"]*whole.GPM
    rotary, _ = calc.rotary.heat(sample)
    kw = dict(m_dot=rho*q, T_inj=inlet, geometry=g,
              Q_face=sample["motor_heat_psi"]*whole.PSI*q+rotary.bit_W, k_rock=b.K_ROCK,
              rhocp_rock=b.RHOCP_ROCK, friction_heat=True, tfa=sample["tfa_m2"], fluid=fluid,
              verbose=False, surface=calc.surface, annulus_heat=rotary.annulus)
    offset = 84 if run in ("17", "18", "19", "20", "27", "38") else 22
    base = {"sample_id": sample["id"], "well": well, "run": run, "bit_ft": sample["bit_ft"],
            "flow_gpm": sample["flow_gpm"], "inlet_C": inlet, "density_ppg": sample["density_ppg"],
            "pv_cP": pv, "yp_lbf_100ft2": yp, "tvd_m": float(g.survey.tvd(g.md_bit)),
            "cumulative_exposure_bit_s": float(exposure(g.md_bit))}
    scenarios = (("published", legacy_form), ("tvd", tvd_form)) if well == "16B" else (("published", tvd_form),)
    for tag, profile in scenarios:
        t_rock = float(profile(g.survey.tvd(g.md_bit)))
        result = m1.solve_seeded(exposure, breaks, **kw, geotherm=profile, target_rock_T=t_rock, physics="v1.8.0")
        base.update({f"{tag}_success": result["success"], f"{tag}_formation_C": t_rock})
        if result["success"]:
            base |= {f"{tag}_bit_C": float(result["T_bottom_delivered"]),
                     f"{tag}_return_C": float(result["T_return_surface"]),
                     f"{tag}_sensor_C": float(result["sol"].sol(g.md_bit-offset*whole.FT)[0])}
            if well == "16A":
                time, data = sensors[run]
                i, j = np.searchsorted(time, [sample["time_s"]-900, sample["time_s"]+901])
                for channel, proxy_ft in zip(CHANNELS, (0., 40., None)):
                    col = f"drilling_{channel}"
                    valid = np.isfinite(data[col][i:j]) & (data[col+"_count"][i:j] > 0)
                    if valid.sum() >= 90 and proxy_ft is not None:
                        measured = np.average(data[col][i:j][valid], weights=data[col+"_count"][i:j][valid])
                        model = float(result["sol"].sol(g.md_bit-proxy_ft*whole.FT)[0])
                        base |= {f"{channel}_measured": measured, f"{channel}_model": model,
                                 f"{channel}_residual": model-measured}
        if tag == "tvd" and base["published_success"] and base["tvd_success"]:
            for field in ("formation_C", "bit_C", "sensor_C", "return_C"):
                base[f"change_{field}"] = base[f"tvd_{field}"]-base[f"published_{field}"]
    if well == "16B":
        base["measured_sensor_C"] = sample["measured_MWD_C"]
    base["measured_return_C"] = sample["measured_return_C"]
    return base


def guarded(sample):
    try:
        return solve(sample)
    except (ValueError, KeyError, IndexError, RuntimeError) as error:
        return {"sample_id": sample["id"], "well": sample["well"], "run": sample["run"],
                "error": str(error)}


def summarise_sensors(samples):
    frozen = json.loads((HERE.parents[1]/"forge16b/s2/plan.json").read_text(encoding="utf-8"))
    primary = {row["id"] for row in frozen["samples"] if row.get("source") == "Sanvean on-bottom"}
    samples = [row for row in samples if row["sample_id"] in primary]
    with (FORGE16A/"run_inputs.csv").open(encoding="utf-8", newline="") as stream:
        runs = list(csv.DictReader(stream))
    for run in runs:
        for channel in CHANNELS:
            if run[channel.replace("_C", "_available")] != "True":
                continue
            group = [row for row in samples if row["run"] == run["run"] and row.get(f"{channel}_residual", "") != ""]
            residual = [row[f"{channel}_residual"] for row in group]
            yield dict(run=run["run"], channel=channel, compared=len(group),
                       bias_C=np.mean(np.asarray(residual, float)) if residual else "",
                       rms_C=np.sqrt(np.mean(np.square(np.asarray(residual, float)))) if residual else "",
                       status="paired" if residual else "no frozen sample with model proxy and required coverage")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    plan = json.loads((HERE.parents[1]/"forge16b/s2/plan.json").read_text(encoding="utf-8"))
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers, initializer=initialize) as pool:
        for i, row in enumerate(pool.map(guarded, plan["samples"]), 1):
            rows.append(row)
            if i % 25 == 0:
                print(i, len(plan["samples"]), flush=True)
    records(HERE/"formation-and-sensor-samples.csv", rows)
    records(HERE/"16a-sensor-residuals.csv", summarise_sensors([r for r in rows if r["well"] == "16A"]))


if __name__ == "__main__":
    main()
