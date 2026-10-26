"""Unfitted FORGE 16A circulation comparison, using the existing 16B method.

Prepare freezes the sample list and inputs before any solve. Run evaluates
that list without changing it, checkpointing every result outside the source
tree. No parameter is fitted. See validation/forge16a/comparison_protocol.md
in the source checkout. Installed studies require that external archive.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import platform
import re
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from borethm import model1_coupled as m1, well_geometry as wg
from borethm.fluids import Mud
from borethm._paths import repository_path, repository_root, require_path

DATA = repository_path('validation/forge16a')
FT, INCH, GPM, PSI = .3048, .0254, 6.30902e-5, 6894.757
K_ROCK = (2.149 + 2.341 + 3.002) / 3
K_RANGE = (2.041, 3.087)
RHOCP_ROCK = (2680 + 2600 + 2650) / 3 * (864.8 + 862.3 + 1091.1) / 3
RUNS = ("18", "23", "30", "34", "35r1", "35r2", "38", "39", "42")
DATES = dict(zip(RUNS, ("11/24/2020", "11/29/2020", "12/04/2020",
                       "12/08/2020", "12/09/2020", "12/09/2020",
                       "12/13/2020", "12/14/2020", "12/18/2020")))
BRANCHES = ("bore_bit_C", "bore_40ft_C", "annulus_bit_C", "annulus_40ft_C")


def read(name):
    with (require_path(DATA, 'FORGE 16A archive; use --data') / name).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def number(s, default=float("nan")):
    try:
        return float(str(s).replace(",", ""))
    except (ValueError, TypeError):
        return default


def epoch(s):
    # UTC attaches a deterministic numeric coordinate; source time zone unknown.
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def csv_out(path, rows):
    rows = list(rows)
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(rows)


def survey():
    rr = read("survey_16a.csv")
    md = [number(r["md_ft"]) for r in rr]
    tvd = [number(r["tvd_ft"]) for r in rr]
    # Explicit final-inclination continuation, not the last station interval slope.
    md.append(12000.)
    tvd.append(tvd[-1] + (12000 - md[-2]) * math.cos(math.radians(number(rr[-1]["inc_deg"]))))
    return wg.Survey(np.array(md) * FT, np.array(tvd) * FT)


def formation(which, path):
    rr = read(f"formation_temperature_{which}day.csv")
    md = np.array([number(r["md_ft"]) for r in rr])
    tvd = np.array([number(r["tvd_ft"]) for r in rr]) * FT
    temp = np.array([number(r["temp_C"]) for r in rr])
    # Endpoint-to-endpoint mean gradient over exactly the final 500 ft MD.
    dtvd = tvd[-1] - float(path.tvd((md[-1] - 500) * FT))
    gradient = (temp[-1] - float(np.interp(md[-1] - 500, md, temp))) / dtvd
    def geotherm(z):
        z = np.asarray(z, float)
        out = np.interp(z, tvd, temp)
        return out
    return geotherm, float(md[-1]), gradient, float(tvd[-1]), float(temp[-1])


def component_inputs():
    all_rows = read("bha_components.csv")
    out = {}
    for run in RUNS:
        n = run[:2]
        rr = [r for r in all_rows if r["BHA"] == n and r["report_date"] == DATES[run]]
        # Duplicate PDFs are alternatives, not extra components. Choose the
        # report with the most explicitly populated dimensions; retain its hash.
        members = sorted(set(r["member"] for r in rr))
        member = max(members, key=lambda m: (sum(bool(r["OD_in"]) + bool(r["ID_in"])
                     for r in rr if r["member"] == m), m))
        rr = sorted([r for r in rr if r["member"] == member], key=lambda r: int(r["item"]))
        comp = []
        for r in rr:
            label, item = r["component"], int(r["item"])
            od, inside = number(r["OD_in"]), number(r["ID_in"])
            notes = []
            if not np.isfinite(od):
                if item == 1:
                    od = 8.75
                elif "Motor" in label or "PUK" in label:
                    od = 6.5
                elif "6 3/4" in label:
                    od = 6.75
                else:
                    raise ValueError(f"Unresolved OD: {run} {label}")
                notes.append("OD from nominal size in component description")
            if not np.isfinite(inside):
                if item == 1 or "Motor" in label:
                    inside = 1.25
                    notes.append("bore represented by matching motor bore, 1.25 in; bit jets treated separately")
                elif "MWD" in label or "PUK" in label:
                    inside = 3.25
                    notes.append("bore from matching 16A MWD/sensor components, 3.25 in")
                else:
                    raise ValueError(f"Unresolved ID: {run} {label}")
            kind = "assembly"
            if "Drill Pipe" in label:
                kind = "HWDP" if any(x in label.upper() for x in ("HWDP", "HVY", "HV WT", "HW WT")) else "ordinary pipe"
                if kind == "ordinary pipe":
                    notes.append(f"reported ID {inside:g} in unresolved; primary ordinary-pipe ID 4.276 in")
            comp.append(dict(run=run, item=item, component=label, kind=kind, od_in=od,
                             reported_id_in=inside, primary_id_in=4.276 if kind == "ordinary pipe" else inside,
                             length_ft=number(r["length_ft"]), report_date=r["report_date"],
                             member=member, sha256=r["sha256"], input_note="; ".join(notes)))
        out[run] = comp
    return out


def hole(bit_ft):
    r = lambda x: x * INCH / 2
    steel = lambda a, b: wg.Layer(a, b, wg.K_STEEL)
    cement = lambda a, b: wg.Layer(a, b, wg.K_CEMENT)
    cid = math.sqrt((20 * INCH)**2 - 4 / math.pi * (54 * .45359237 / FT / 7850))
    # No unrecorded conductor borehole diameter: conductor OD is the shallow
    # rock-interface radius; external cement thickness is unresolved.
    a, b = r(8.835), r(9.625)
    c, d = r(12.415), r(13.375)
    e, f = cid / 2, r(20)
    return [wg.HoleInterval(0, 130 * FT, a, (steel(a,b), cement(b,c), steel(c,d), cement(d,e), steel(e,f))),
            wg.HoleInterval(130 * FT, 1629 * FT, a, (steel(a,b), cement(b,c), steel(c,d), cement(d,r(17.5)))),
            wg.HoleInterval(1629 * FT, 5110 * FT, a, (steel(a,b), cement(b,r(12.25)))),
            wg.open_hole(5110 * FT, bit_ft * FT + 1e-6, 8.75 * INCH)]


def geometry(run, bit_ft, components, pipe_sensitivity=False):
    comp = components[run]
    def pipe(name, od, inside):
        return wg.PipeType(name, (wg.Layer(inside * INCH / 2, od * INCH / 2, wg.K_STEEL),))
    # The 16B representation: length-weighted OD/ID for the compact BHA.
    # Keep HWDP and the long ordinary-pipe sections separate and in order.
    bottom_up, core = [], []
    def flush():
        if core:
            length = sum(c["length_ft"] for c in core)
            od = sum(c["od_in"] * c["length_ft"] for c in core) / length
            inside = sum(c["primary_id_in"] * c["length_ft"] for c in core) / length
            bottom_up.append((length, pipe("length-weighted BHA", od, inside)))
            core.clear()
    for c in comp:
        if c["kind"] == "assembly":
            core.append(c)
        else:
            flush()
            inside = c["reported_id_in"] if pipe_sensitivity else c["primary_id_in"]
            bottom_up.append((c["length_ft"], pipe(c["component"], c["od_in"], inside)))
    flush()
    dp = bit_ft - sum(x[0] for x in bottom_up)
    if dp <= 0:
        raise ValueError("assembly longer than drilled depth")
    string = [wg.StringSegment(dp * FT, pipe("5 in 19.5 lb/ft drill pipe", 5, 4.276))]
    string.extend(wg.StringSegment(length * FT, p) for length, p in reversed(bottom_up))
    return wg.WellGeometry(string, hole(bit_ft), survey())


def mudlog():
    rr = read("mud_log_by_depth.csv")
    out = {}
    for field in ("temp_in_F", "temp_out_F"):
        good = [(number(r["md_ft"]), number(r[field])) for r in rr if 32 < number(r[field]) < 300]
        x, y = np.array(good).T
        out[field] = (x, y)
    return out


def sample_input(row, run, mud, daily):
    depth = number(row["bit_depth_ft"])
    r = next(d for d in daily if d["run"] == run)
    return dict(run=run, time=row["time"], time_s=epoch(row["time"]), bit_ft=depth,
                flow_gpm=number(row["flow_gpm"]), motor_dp_psi=max(0., number(row.get("motor_differential_psi"), 0.)),
                T_in_C=(float(np.interp(depth, *mud["temp_in_F"])) - 32) / 1.8,
                measured_return_C=(float(np.interp(depth, *mud["temp_out_F"])) - 32) / 1.8,
                mud_weight_ppg=r["mud_weight_ppg"], pv_cP=r["pv_cP"], yp_lbf_100ft2=r["yp_lbf_100ft2"],
                tfa_m2=r["tfa_m2"], washout=run in ("35r1", "35r2"),
                formation_tail=depth > 10740, survey_tail=depth > 10955)


def prepare(output):
    output.mkdir(parents=True, exist_ok=True)
    if (output / "plan.json").exists():
        raise FileExistsError("A frozen plan already exists; use another output directory for a new method")
    components = component_inputs()
    daily, details = [], read("daily_well_inputs.csv")
    for run in RUNS:
        rr = [r for r in details if r["BHA"] == run[:2] and r["report_date"] in
              next(r for r in read("run_inputs.csv") if r["run"] == run)["report_dates"].split("; ")]
        # Run-level report means, fixed without temperature-error selection.
        avg = lambda col: float(np.mean([number(r[col]) for r in rr if np.isfinite(number(r[col]))]))
        jets = [(3,13),(4,12)] if run == "34" else [(3,14),(3,13)]
        daily.append(dict(run=run, mud_weight_ppg=avg("mud_weight_ppg"), pv_cP=avg("plastic_viscosity_cP"),
                          yp_lbf_100ft2=avg("yield_point_lbf_100ft2"),
                          tfa_m2=sum(n * math.pi/4*(size/32*INCH)**2 for n,size in jets),
                          mud_report_dates="; ".join(sorted(set(r["report_date"] for r in rr))),
                          mud_members="; ".join(sorted(set(r["member"] for r in rr))),
                          jets_32nds=str(jets)))
    mud = mudlog()
    samples, exclusions, bounds = [], Counter(), {}
    for run in RUNS:
        rr = read(f"sanvean_BHA{run}_10s.csv")
        ts = np.array([epoch(r["time"]) for r in rr])
        last = -1e30
        bounds[run] = (ts[0], ts[-1])
        for i, row in enumerate(rr):
            q, bit, depth = (number(row[k]) for k in ("flow_gpm", "bit_depth_ft", "hole_depth_ft"))
            qualifies = (number(row["invalid_flow_count"]) == 0 and number(row["flow_gpm_count"]) == number(row["raw_count"])
                         and 300 < q <= 2000 and abs(bit-depth) <= 5 and number(row["on_bottom_flag"]) > .5
                         and number(row["rop_ft_h"]) > 1)
            if not qualifies or ts[i] - last < 1800:
                continue
            last = ts[i]
            s = sample_input(row, run, mud, daily)
            s["source"] = "Sanvean on-bottom"
            window = rr[np.searchsorted(ts, ts[i]-900):np.searchsorted(ts, ts[i]+900, side="right")]
            for ch in ("bit_box_C", "top_sub_C"):
                count = sum(number(r[f"drilling_{ch}_count"], 0) for r in window)
                seconds = sum(10 * number(r[f"drilling_{ch}_count"], 0) / max(1, number(r["raw_count"], 0)) for r in window)
                s[ch + "_coverage_s"] = seconds
                s[ch + "_count"] = count
                if count and seconds >= 900:
                    s["measured_" + ch] = sum(number(r[f"drilling_{ch}"],0) * number(r[f"drilling_{ch}_count"],0) for r in window) / count
            if "measured_bit_box_C" not in s and "measured_top_sub_C" not in s:
                exclusions[run + ": under 15 min sensor coverage"] += 1
                continue
            samples.append(s)
    # Broader return-only comparison: all rig drilling intervals for which a
    # reviewed assembly has a dated, depth-overlapping active bit record.
    # Retain inference explicitly; do not borrow unreviewed assembly dimensions.
    br = read("bit_records.csv")
    active = {}
    for run in RUNS:
        records = [r for r in br if r["BHA"] == run[:2]
                   and np.isfinite(number(r["depth_in_ft"]))]
        # BHA and bit numbers diverge after BHA 23. The latest depth-in entry
        # identifies the drilling bit, including records with no depth-out yet.
        lo = max(number(r["depth_in_ft"]) for r in records)
        records = [r for r in records if number(r["depth_in_ft"]) == lo]
        hi = max([number(r["depth_out_ft"]) for r in records if np.isfinite(number(r["depth_out_ft"]))]
                 + [number(next(r for r in read("run_inputs.csv") if r["run"] == run)["drilling_MD_max_ft"])])
        active[run] = (lo, hi)
    clock_rows = read("rig_history_1min.csv")
    last = -1e30
    for row in clock_rows:
        q, depth, t = number(row["flow_gpm"]), number(row["hole_depth_ft"]), epoch(row["time"])
        if not (300 < q <= 2000 and number(row["on_bottom_flag"]) > .5 and number(row["rop_ft_h"]) > 1):
            continue
        candidates = [run for run,(lo,hi) in active.items() if lo <= depth <= hi
                      and bounds[run][0] - 86400 <= t <= bounds[run][1] + 86400]
        if len(candidates) > 1 and all(r in ("35r1","35r2") for r in candidates):
            candidates = [min(candidates, key=lambda r: min(abs(t-bounds[r][0]), abs(t-bounds[r][1])))]
        if len(candidates) != 1:
            exclusions["rig drilling minutes: no unique reviewed assembly"] += 1
            continue
        if t-last < 1800:
            continue
        last = t
        run = candidates[0]
        s = sample_input({**row, "bit_depth_ft": row["hole_depth_ft"]}, run, mud, daily)
        s["source"] = "rig inferred bit depth, return only"
        samples.append(s)
    for i,s in enumerate(samples):
        s["sample_id"] = f"s{i+1:04d}"
        geometry(s["run"], s["bit_ft"], components)  # input-only geometry check
    cases = []
    for s in samples:
        variants = [(1.,K_ROCK,"216-constant",False)]
        if s["source"] == "Sanvean on-bottom":
            variants = [(film,k,form,False) for film in (1.,.75) for k in (K_ROCK,*K_RANGE)
                        for form in (("216-constant","57") if s["bit_ft"] <= 8728 else ("216-constant",))]
            if s["formation_tail"]:
                variants.append((1.,K_ROCK,"216-gradient",False))
            if s["run"] == "42":
                variants.append((1.,K_ROCK,"216-constant",True))
        for film,k,form,pipe in variants:
            cases.append(dict(case_id=f"c{len(cases)+1:05d}", sample_id=s["sample_id"], film_mult=film,
                              k_rock=k, formation=form, pipe_id_sensitivity=pipe))
    manifest = {p.name: digest(p) for p in sorted(DATA.glob("*")) if p.is_file()}
    model_dir = Path(m1.__file__).parent
    model_hashes = {p.name: digest(p) for p in sorted(model_dir.glob("*.py"))}
    checkout = repository_root()
    commit = subprocess.check_output(["git","rev-parse","HEAD"],cwd=checkout,text=True).strip() if checkout else None
    description = (subprocess.check_output(["git","describe","--tags","--always","--dirty"],cwd=checkout,text=True).strip()
                   if checkout else 'installed borethm ' + importlib.metadata.version('borethm'))
    plan = dict(baseline=commit, describe=description,
                prepared_utc=datetime.now(timezone.utc).isoformat(), source_hashes=manifest,
                calculation_hashes=model_hashes, study_sha256=digest(__file__), components=components,
                mud_and_nozzles=daily, samples=samples, cases=cases,
                exclusions=dict(exclusions), active_bit_depth_ranges_ft=active,
                clock_missing_fraction_minutes=sum(not r["circulating_fraction"] for r in clock_rows),
                clock_missing_depth_minutes=sum(not r["hole_depth_ft"] for r in clock_rows),
                clock_note="Missing circulation fraction contributes zero observed circulation; missing depth forward-filled. No rock recovery during stops, following 16B.",
                versions={"Python":platform.python_version(), **{n:importlib.metadata.version(n) for n in ("numpy","scipy","iapws","matplotlib")}})
    dump(output/"plan.json",plan)
    (output/"plan.sha256").write_text(digest(output/"plan.json")+"\n")
    csv_out(output/"samples.csv",samples)
    csv_out(output/"case-plan.csv",cases)
    csv_out(output/"string-inputs.csv",[c for cc in components.values() for c in cc])
    csv_out(output/"mud-and-nozzles.csv",daily)
    print(json.dumps(dict(samples=len(samples), sources=Counter(s["source"] for s in samples),
                          runs=Counter(s["run"] for s in samples if s["source"]=="Sanvean on-bottom"),
                          cases=len(cases), exclusions=dict(exclusions)),indent=2))


def run(output, limit=None):
    plan = json.loads((output/"plan.json").read_text())
    if digest(output/"plan.json") != (output/"plan.sha256").read_text().strip():
        raise ValueError("Frozen plan changed")
    for name, sha in plan["calculation_hashes"].items():
        if digest(Path(m1.__file__).parent/name) != sha:
            raise ValueError(f"Calculation changed: {name}")
    for name, sha in plan["source_hashes"].items():
        if digest(DATA/name) != sha:
            raise ValueError(f"Input changed: {name}")
    done = set()
    dest = output/"results.jsonl"
    if dest.exists():
        done = {r["case_id"] for r in map(json.loads,dest.read_text().splitlines())}
    samples = {s["sample_id"]:s for s in plan["samples"]}
    cr = read("rig_history_1min.csv")
    times = np.array([epoch(r["time"]) for r in cr])
    circ = np.cumsum([number(r["circulating_fraction"],0.) * 60 for r in cr])
    depths, last_depth = [], 0.
    for row in cr:
        last_depth = max(last_depth,number(row["hole_depth_ft"],last_depth))
        depths.append(last_depth * FT)
    depths = np.array(depths)
    path = survey()
    forms = {n:formation(n,path) for n in ("216","57")}
    processed = 0
    for case in plan["cases"]:
        if case["case_id"] in done:
            continue
        if limit is not None and processed >= limit:
            break
        s = samples[case["sample_id"]]
        start = time.perf_counter()
        row = {**case, "success":False}
        try:
            g = geometry(s["run"],s["bit_ft"],plan["components"],case["pipe_id_sensitivity"])
            form,end,gradient,tvd_end,temp_end = forms["57" if case["formation"]=="57" else "216"]
            if case["formation"] == "216-gradient":
                base = form
                form = lambda z: base(z) + np.maximum(np.asarray(z)-tvd_end,0.) * gradient
            fluid = Mud(s["mud_weight_ppg"] * 119.8264273, pv_ref=s["pv_cP"]*.001,
                        yield_point=s["yp_lbf_100ft2"]*.4788025898)
            rho = float(m1.fluid_props(np.array([s["T_in_C"]]),np.array([m1.P_SURF]),fluid)[0][0])
            q = s["flow_gpm"] * GPM
            ex = m1.smooth_exposure(m1.exposure_from_history(circ,depths,float(np.interp(s["time_s"],times,circ))),g.md_bit)
            r = m1.solve_seeded(ex,m1.exposure_breaks(ex,g.md_bit),m_dot=q*rho,T_inj=s["T_in_C"],
                                geotherm=form,geometry=g,target_rock_T=float(form(path.tvd(g.md_bit))),
                                Q_face=s["motor_dp_psi"]*PSI*q,k_rock=case["k_rock"],rhocp_rock=RHOCP_ROCK,
                                friction_heat=True,tfa=s["tfa_m2"],film_mult=case["film_mult"],fluid=fluid,verbose=False)
            row.update(success=bool(r["success"]),solver_status=int(r["sol"].status),
                       solver_message=str(r["sol"].message),nodes=int(len(r["sol"].x)),
                       seed_success=bool(r["seed"]["success"]) if r["seed"] else None,
                       bore_bit_C=float(r["Td"][-1]),annulus_bit_C=float(r["Tu"][-1]),
                       bore_40ft_C=float(np.interp(g.md_bit-40*FT,r["z"],r["Td"])),
                       annulus_40ft_C=float(np.interp(g.md_bit-40*FT,r["z"],r["Tu"])),
                       return_C=float(r["Tu"][0]),formation_gradient_C_per_km=gradient*1000)
            vals=[row[b] for b in BRANCHES]
            row.update(sensor_range_min_C=min(vals),sensor_range_max_C=max(vals),
                       position_spread_bore_C=abs(vals[0]-vals[1]),position_spread_annulus_C=abs(vals[2]-vals[3]),
                       medium_spread_bit_C=abs(vals[0]-vals[2]),medium_spread_40ft_C=abs(vals[1]-vals[3]))
        except Exception as err:
            row["exception"] = f"{type(err).__name__}: {err}"
        row["duration_s"] = time.perf_counter()-start
        with dest.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,allow_nan=False)+"\n")
            f.flush()
        processed += 1
        print(f'{case["case_id"]} {s["run"]} {s["bit_ft"]:.1f} ft {case["formation"]} film={case["film_mult"]} k={case["k_rock"]:.4f} ok={row["success"]} {row["duration_s"]:.2f}s',flush=True)


def main():
    global DATA
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","run"))
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--limit",type=int)
    p.add_argument("--data",type=Path,default=DATA,help="External validation/forge16a archive (required outside a checkout)")
    args=p.parse_args()
    DATA=require_path(args.data, 'FORGE 16A archive; use --data').resolve()
    if args.action == "prepare":
        prepare(args.output)
    else:
        run(args.output,args.limit)


if __name__ == "__main__":
    main()
