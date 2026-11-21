"""Select the 58-32 forecast samples from input channels only.

Part A: half-hour drilling windows. Part B: the PT-log schedule from the
whitelisted header fields, on the rig clock. No temperature target is read.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from importlib import import_module

c = import_module("validation.forge58-32.thermal.common")

LOGGER_TO_RIG = timedelta(hours=2)   # see the protocol, part B timing
TIME_PAIRS = {"RUN1": "TIME1", "RUN2": "TIME2", "RUN3": "TIME3", "RUN4": "TIME4"}
TDL_FT = 6798.0
DEPTH_STEP_FT = 10.0
TIME_STEP_S = 10.0


def iso(t):
    return str(np.datetime64(t, "s")).replace("T", " ")


def mean(values):
    values = values[np.isfinite(values)]
    return float(values.mean()) if len(values) else np.nan


def write(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def windows(h, run_id, assigned, scale, samples, srv):
    t = h["time"]
    seconds = t.astype("datetime64[s]").astype(np.int64)
    bit, hole, flow, rop = h["bit_depth_ft"], h["hole_depth_ft"], h["flow_gpm"], h["rop_ft_h"]
    valid = (flow > 300) & (np.abs(bit-hole) <= 5) & (rop > 1)
    centre = (seconds+900)//1800
    for key in np.unique(centre[valid]):
        take = np.flatnonzero(valid & (centre == key))
        if len(take) < 90 or np.ptp(hole[take]) < .5:
            continue
        mid = int(key)*1800
        runs = {int(run_id[i]) for i in take}
        run = assigned.get(next(iter(runs))) if len(runs) == 1 and 0 not in runs else None
        bha = run["bha"] if run else ""
        hole_ft, bit_ft = mean(hole[take]), mean(bit[take])
        when = iso(np.datetime64(mid, "s"))
        row = dict(kind="drilling", time=when, sample_start=iso(np.datetime64(mid-900, "s")),
                   sample_end=iso(np.datetime64(mid+900, "s")), qualified_bins=len(take),
                   bit_ft=bit_ft, tvd_ft=float(srv.tvd(bit_ft*c.FT))/c.FT, hole_ft=hole_ft,
                   run_id=";".join(map(str, sorted(runs))), bha=bha,
                   assembly_status=(run["status"] if run else
                                    "window spans more than one run" if len(runs) > 1 else "bit at surface"),
                   jets=run["jets"] if run else "", tfa_in2=run["tfa_in2"] if run else np.nan,
                   flow_pason_gpm=mean(flow[take]), flow_primary_gpm=mean(flow[take])*scale,
                   inlet_C=mean(h["inlet_C"][take]), inlet_bins=int(np.isfinite(h["inlet_C"][take]).sum()),
                   spp_psi=mean(h["spp_psi"][take]), spp_bins=int(np.isfinite(h["spp_psi"][take]).sum()),
                   rop_ft_h=mean(rop[take]), history_through_report_clock=when >= c.GAP[1])
        try:
            row.update(c.mud_for(when, hole_ft, samples))
        except ValueError as error:
            row["mud_status"] = str(error)
        reasons = []
        if not bha:
            reasons.append("no uniquely assigned assembly")
        elif not np.isfinite(row["tfa_in2"]):
            reasons.append("no single recorded nozzle set")
        if not np.isfinite(row["inlet_C"]):
            reasons.append("no inlet temperature")
        if not np.isfinite(row.get("density_ppg", np.nan)):
            reasons.append("no mud density")
        row["input_status"] = "complete" if not reasons else "; ".join(reasons)
        yield row


def headers():
    out = {}
    for r in c.read(c.HERE/"pt-headers.csv"):
        name = r["source"].split("_")[1] if "MU-ESW1_" in r["source"] else r["source"]
        out.setdefault(name, {})[r["key"]] = r["value"]
    return out


def logger_time(text):
    return datetime.strptime(text, "%a %b %d %H-%M-%S %Y")


def preceding_circulation(h, before):
    """The last spell of bins with flow above 100 US gal/min and the bit within 100 ft of bottom."""
    t, flow, bit, hole = h["time"], h["flow_gpm"], h["bit_depth_ft"], h["hole_depth_ft"]
    on = (flow > 100) & (np.abs(hole-bit) <= 100) & (t < np.datetime64(before))
    idx = np.flatnonzero(on)
    if not len(idx):
        raise ValueError("no circulation before the log")
    end = idx[-1]
    start = end
    while start > 0 and on[start-1] and (t[start]-t[start-1]) <= np.timedelta64(10, "s"):
        start -= 1
    sl = slice(start, end+1)
    later = (t > t[end]) & (t < np.datetime64(before)) & (flow > 100)
    return dict(circ_start=iso(t[start]), circ_end=iso(t[end]+np.timedelta64(10, "s")),
                circ_flow_pason_gpm=mean(flow[sl]), circ_inlet_C=mean(h["inlet_C"][sl]),
                circ_bit_ft=mean(bit[sl]), circ_hole_ft=float(np.nanmax(hole[sl])),
                pumped_bins_after_circulation=int(later.sum()),
                pumped_volume_after_circulation_gal=float(np.nansum(flow[later])*10/60),
                pumped_bins_after_max_bit_ft=float(np.nanmax(bit[later])) if later.any() else np.nan)


def log_schedule(h, run_id, assigned, scale, samples, srv):
    head = headers()
    plan, points = [], []
    for run, timed in TIME_PAIRS.items():
        for name, kind in ((run, "depth"), (timed, "time")):
            fields = head[name]
            start = logger_time(fields["DATE"])+LOGGER_TO_RIG
            bottom = logger_time(head[timed]["DATE"])+LOGGER_TO_RIG
            first = start if kind == "depth" else bottom
            row = dict(log=name, kind=kind, logger_date=fields["DATE"], rig_start=start.isoformat(sep=" "),
                       rig_bottom=bottom.isoformat(sep=" "), strt=float(fields["STRT"]), stop=float(fields["STOP"]),
                       step=float(fields["STEP"]), tdl_ft=TDL_FT, tlob1=fields.get("TLOB1", ""))
            circ = preceding_circulation(h, first)
            row |= circ
            i = np.searchsorted(h["time"], np.datetime64(circ["circ_end"]))-1
            info = assigned.get(int(run_id[i]))
            # The circulation's assembly: the single assembly named by the
            # reports dated on its first and last days, with that last day's nozzles.
            days = sorted({circ["circ_start"][:10], circ["circ_end"][:10]})
            named = {c.report_bha().get(d, "") for d in days}
            nozzles = c.report_jets().get(days[-1], set())
            row |= dict(run_bha=info["bha"] if info else "", run_status=info["status"] if info else "",
                        circulation_report_days=";".join(days),
                        assembly_for_circulation=next(iter(named)) if len(named) == 1 and "" not in named else "",
                        jets=";".join("-".join(map(str, j)) for j in sorted(nozzles)),
                        tfa_in2=c.tfa_in2(next(iter(nozzles))) if len(nozzles) == 1 else np.nan,
                        circ_flow_primary_gpm=circ["circ_flow_pason_gpm"]*scale)
            row |= c.mud_for(circ["circ_end"], circ["circ_hole_ft"], samples)
            plan.append(row)
            if kind == "depth":
                top, base = max(0., row["strt"]), min(row["stop"], circ["circ_hole_ft"])
                for depth in np.arange(np.ceil(top/DEPTH_STEP_FT)*DEPTH_STEP_FT, base+1e-9, DEPTH_STEP_FT):
                    frac = (depth-row["strt"])/(TDL_FT-row["strt"])
                    when = start+(bottom-start)*min(frac, 1.)
                    points.append(dict(log=name, md_ft=float(depth), rig_time=when.isoformat(sep=" ", timespec="seconds"),
                                       elapsed_s=""))
            else:
                for elapsed in np.arange(row["strt"], row["stop"]+1e-9, TIME_STEP_S):
                    when = bottom+timedelta(seconds=float(elapsed))
                    points.append(dict(log=name, md_ft=TDL_FT, rig_time=when.isoformat(sep=" ", timespec="seconds"),
                                       elapsed_s=float(elapsed)))
    return plan, points


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    h = c.rig()
    run_id = c.runs(h)
    assigned = c.assign_runs(h, run_id)
    scale = c.flow_scale()
    samples = c.mud_samples(h)
    srv = c.survey()
    rows = sorted(windows(h, run_id, assigned, scale, samples, srv), key=lambda r: r["time"])
    for i, row in enumerate(rows, 1):
        row["sample_id"] = f"58t-{i:04}"
    write(args.output/"conditions.csv", rows)
    write(args.output/"runs.csv", [dict(run_id=k) | v for k, v in sorted(assigned.items())])
    plan, points = log_schedule(h, run_id, assigned, scale, samples, srv)
    write(args.output/"log-plan.csv", plan)
    write(args.output/"log-points.csv", points)
    print(len(rows), Counter(r["input_status"] for r in rows), Counter(r["bha"] for r in rows))
    print(len(points), Counter(p["log"] for p in points))


if __name__ == "__main__":
    main()
