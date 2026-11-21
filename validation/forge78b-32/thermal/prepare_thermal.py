"""Select the 78B-32 forecast windows from input channels only.

usage: python -m validation.forge78b-32.thermal.prepare_thermal OUTPUT_DIR

Builds the half-hour drilling windows by the 56-32 rule, assigns each to an
assembly by its BHA sheet, and records the window inputs, the sensor
positions and the parts each window belongs to. Writes `windows.csv` and
`qualified-bins.csv.gz`. No temperature target is read.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime
import gzip
from importlib import import_module
from pathlib import Path

import numpy as np

c = import_module("validation.forge78b-32.thermal.common")

PASON_INLET_FROM = "2021-07-09"


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
        writer.writerows({k: ("" if isinstance(v, float) and not np.isfinite(v) else v) for k, v in r.items()}
                         for r in rows)


def report_inlets(samples):
    """The "In" temperature (F) of each mud check, by date."""
    return [(s["when"], c.number(s["report_inlet_F"])) for s in samples if np.isfinite(c.number(s["report_inlet_F"]))]


def report_inlet_for(centre, inlets):
    """That day's mud check; a day without one takes the nearest check in time, ties to the earlier."""
    day = [(w, x) for w, x in inlets if str(w)[:10] == str(centre)[:10]]
    pool = day or inlets
    when, value = min(pool, key=lambda p: (abs((p[0]-centre).astype("timedelta64[s]").astype(float)), p[0]))
    return (value-32)/1.8, str(when).replace("T", " "), "same day" if day else "nearest day"


def flagged_days():
    """Days on which the report inlet differs from the Pason inlet by more than 5 K."""
    return {r["sample_date"] for r in c.read(c.INPUTS/"inlet-check.csv") if r["flag_over_5K"] == "True"}


def windows(h):
    t = h["time"]
    seconds = t.astype("datetime64[s]").astype(np.int64)
    bit, hole, flow, rop = h["bit_depth_ft"], h["hole_depth_ft"], h["flow_gpm"], h["rop_ft_h"]
    with np.errstate(invalid="ignore"):
        valid = (flow > 300) & (np.abs(bit-hole) <= 5) & (rop > 1)
    centre = (seconds+900)//1800
    for key in np.unique(centre[valid]):
        take = np.flatnonzero(valid & (centre == key))
        if len(take) < 90 or np.ptp(hole[take]) < .5:
            continue
        yield int(key)*1800, take


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    h = c.rig()
    srv, form = c.survey(), c.formation()
    sheets = c.sheets()
    samples = c.mud_samples(h)
    inlets = report_inlets(samples)
    flagged = flagged_days()
    offsets = {bha: c.sensor_offset_ft(bha) for bha in (*c.SLB_MWD, *c.SDI)}
    tfa = {}
    for bha in sheets:
        sets = c.nozzles(bha)
        tfa[bha] = (c.tfa_in2(next(iter(sets))), " ".join(map(str, next(iter(sets))))) if len(sets) == 1 else \
            (np.nan, "none recorded" if not sets else "more than one nozzle set")
    rows, bins = [], []
    for mid, take in windows(h):
        centre = np.datetime64(mid, "s")
        when = iso(centre)
        hole = h["hole_depth_ft"][take]
        bha, status = c.assign(sheets, datetime.fromisoformat(when), float(np.min(hole)), float(np.max(hole)))
        bit_ft = mean(h["bit_depth_ft"][take])
        hole_ft = mean(hole)
        row = dict(centre=when, window_start=iso(centre-np.timedelta64(900, "s")),
                   window_end=iso(centre+np.timedelta64(900, "s")), qualified_bins=len(take),
                   hole_min_ft=float(np.min(hole)), hole_max_ft=float(np.max(hole)), hole_ft=hole_ft, bit_ft=bit_ft,
                   bha=bha, assembly_status=status, flow_gpm=mean(h["flow_gpm"][take]),
                   rop_ft_h=mean(h["rop_ft_h"][take]))
        pason = h["inlet_C"][take]
        if when[:10] >= PASON_INLET_FROM and np.isfinite(pason).any():
            row |= dict(inlet_C=mean(pason), inlet_source="pason", inlet_bins=int(np.isfinite(pason).sum()),
                        inlet_report_check="")
        else:
            value, check, basis = report_inlet_for(centre, inlets)
            row |= dict(inlet_C=value, inlet_source="report", inlet_bins=0, inlet_report_check=f"{check} ({basis})")
        row["inlet_flag"] = str(when[:10] in flagged)
        if bha:
            row["bit_diameter_in"] = c.bit_diameter(bha)
            row["tfa_in2"], row["nozzles_32nds"] = tfa[bha]
            row["tool"] = "SLB MWD" if bha in c.SLB_MWD else "SDI" if bha in c.SDI else "none"
        offset = offsets.get(bha, np.nan)
        sensor_md_ft = bit_ft-offset
        row |= dict(sensor_offset_ft=offset, sensor_md_ft=sensor_md_ft)
        if np.isfinite(sensor_md_ft) and sensor_md_ft > 0:
            tvd = float(srv.tvd(sensor_md_ft*c.FT))
            row |= dict(sensor_tvd_ft=tvd/c.FT, formation_at_sensor_C=float(form(tvd)))
        lower, upper = c.SANVEAN_FT.get(bha, (np.nan, np.nan))
        row |= dict(sanvean_lower_offset_ft=lower, sanvean_upper_offset_ft=upper)
        try:
            row |= c.mud_for(when, hole_ft, samples)
            row["fluid"] = c.fluid_for(row["density_ppg"], row["pv_cP"], row["yp"])[1]
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
        row |= dict(part_a=str(bha in c.SLB_MWD), part_b_eye=str(bha in c.SDI),
                    part_b_return=str(bool(bha) and row["inlet_source"] == "pason"),
                    part_b_sanvean=str(bha in c.SANVEAN_FT))
        rows.append(row)
        bins.append([iso(x) for x in h["time"][take]])
    rows = [dict(sample_id=f"78t-{i:04}", **r) for i, r in enumerate(rows, 1)]
    write(args.output/"windows.csv", rows)
    with gzip.open(args.output/"qualified-bins.csv.gz", "wt", encoding="utf-8", newline="") as stream:
        w = csv.writer(stream, lineterminator="\n")
        w.writerow(["sample_id", "bin_time"])
        for row, b in zip(rows, bins):
            for x in b:
                w.writerow([row["sample_id"], x])
    print("windows", len(rows), "bins", sum(map(len, bins)))
    print("assembly", sorted(Counter(r["bha"] or r["assembly_status"] for r in rows).items(),
                             key=lambda kv: (len(kv[0]), kv[0])))
    print("input", Counter(r["input_status"] for r in rows))
    for part in ("part_a", "part_b_eye", "part_b_return", "part_b_sanvean"):
        sub = [r for r in rows if r[part] == "True"]
        print(part, len(sub), "complete", sum(r["input_status"] == "complete" for r in sub))
    print("inlet", Counter((r["inlet_source"], r["inlet_flag"]) for r in rows))
    print("nearest-day report inlet", sum("nearest day" in r["inlet_report_check"] for r in rows))
    print("fluid", Counter(r.get("fluid", "") for r in rows))
    print("offsets", {k: round(v, 2) for k, v in offsets.items()})
    print("nozzles", {k: v[1] for k, v in tfa.items()})


if __name__ == "__main__":
    main()
