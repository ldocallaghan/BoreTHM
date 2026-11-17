"""Shared inputs for the 58-32 thermal forecast: history, geometry, mud and formation.

Imports the released BoreTHM package. Reads only the committed input extracts.
"""
import ast
import csv
from dataclasses import replace
import gzip
import json
from pathlib import Path

import numpy as np

from borethm import hydraulic_losses as hl, model1_coupled as m1, well_geometry as wg
from borethm.studies import validate_forge16b as b

HERE = Path(__file__).resolve().parent
WELL = HERE.parent
INPUTS = HERE/"inputs"
FT, INCH, PSI, GPM = 0.3048, 0.0254, 6894.757293168361, 3.785411784e-3/60
PPG = 119.82642731689663
YP_PA = 0.4788025898033584
K_ROCK, RHOCP_ROCK = b.K_ROCK, b.RHOCP_ROCK
PV_REF_T = 48.9
# Ordinary drill pipe: the 58-32 pressure test's primary catalogue scenario
# (TSC TSDS40, revision 9, PDF p1): 4.000 in, 14.00 lb/ft, 3.340 in bore,
# 5.250 x 2.563 in joint, 31.5 ft pitch, 29 in restriction length.
PIPE = dict(od_in=4.0, id_in=3.34, joint_od_in=5.25, joint_id_in=2.563, joint_in=29.0, pitch_ft=31.5)
# Casing bores: 13.375 in 54.5 lb/ft (EOWR p25) and 9.625 in 40 lb/ft (EOWR p31),
# nominal IDs 12.615 and 8.835 in (Cudd Well Control Technical Data Book, 2021,
# printed p48, Casing Capacity table). The conductor weight is unreported; the
# 56-32 transferred scenario of 106.5 lb/ft and 19.000 in ID is used.
CONDUCTOR = dict(shoe_ft=84.0, od_in=20.0, id_in=19.0)
SURFACE = dict(shoe_ft=338.0, od_in=13.375, id_in=12.615, hole_in=17.5, section_td_ft=342.0)
INTERMEDIATE = dict(shoe_ft=2172.0, od_in=9.625, id_in=8.835, hole_in=12.25, section_td_ft=2180.0)
PRODUCTION_HOLE_IN = 8.75
GAP = ("2017-08-27 00:00:00", "2017-09-01 00:00:00")


def sha(path):
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    with open(path, encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def number(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return np.nan
    return out if np.isfinite(out) else np.nan


def flow_scale():
    return json.loads((INPUTS/"manifest.json").read_text())["flow_scale"]["scale"]


# ---------- history ----------

def rig():
    """Pason ten-second inputs, with the matching pump-pressure bins."""
    with gzip.open(WELL/"rig_inputs_10s.csv.gz", "rt", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    with gzip.open(INPUTS/"pump_pressure_10s.csv.gz", "rt", encoding="utf-8", newline="") as stream:
        spp = {r["time"]: number(r["pump_pressure_psi"]) for r in csv.DictReader(stream)}
    out = dict(time=np.array([np.datetime64(r["time"]) for r in rows]))
    for key in ("bit_depth_ft", "hole_depth_ft", "flow_gpm", "rop_ft_h", "inlet_temperature_source_degrees"):
        out[key] = np.array([number(r[key]) for r in rows])
    out["spp_psi"] = np.array([spp.get(r["time"], np.nan) for r in rows])
    out["inlet_C"] = (out["inlet_temperature_source_degrees"]-32)/1.8
    return out


def report_clock():
    with gzip.open(INPUTS/"report_clock_10s.csv.gz", "rt", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    return (np.array([np.datetime64(r["time"]) for r in rows]),
            np.array([number(r["flow_gpm"]) for r in rows]),
            np.array([number(r["hole_depth_ft"]) for r in rows]))


class Clock:
    """Cumulative circulation: ten seconds for each bin whose flow exceeds 100 US gal/min.

    Pason bins, with the daily-report bins for 27 to 31 August inserted.
    """
    def __init__(self, history):
        t2, q2, h2 = report_clock()
        t = np.concatenate([history["time"], t2])
        q = np.concatenate([history["flow_gpm"], q2])
        h = np.concatenate([history["hole_depth_ft"], h2])
        order = np.argsort(t, kind="stable")
        t, q, h = t[order], q[order], h[order]
        self.t0 = t[0]
        self.seconds = (t-t[0]).astype("timedelta64[s]").astype(float)
        self.circ = np.cumsum(np.where(np.nan_to_num(q) > 100., 10., 0.))
        self.depth = np.fmax.accumulate(np.where(np.isfinite(h), h, 0.))*FT

    def circulated(self, when):
        return float(np.interp((np.datetime64(when)-self.t0).astype("timedelta64[s]").astype(float),
                               self.seconds, self.circ))

    def exposure(self, when, md_bit):
        now = self.circulated(when)
        return m1.smooth_exposure(m1.exposure_from_history(self.circ, self.depth, now), md_bit)

    def raw_exposure(self, when):
        """Circulating seconds since each depth was first reached, unsmoothed, floored at one hour."""
        f = m1.exposure_from_history(self.circ, self.depth, self.circulated(when))
        return lambda z: np.maximum(f(z), m1.T_EXPOSURE_FLOOR)


# ---------- formation ----------

def formation():
    """PT118 temperature against TVD (m), holding the end values beyond the log."""
    rows = read(INPUTS/"formation-pt118.csv")
    tvd = np.array([number(r["tvd_ft"]) for r in rows])*FT
    temp = np.array([number(r["temperature_C"]) for r in rows])
    return lambda z: np.interp(np.asarray(z, float), tvd, temp)


def survey():
    rows = read(WELL/"survey.csv")
    md = np.array([number(r["MD_ft"]) for r in rows])*FT
    tvd = np.array([number(r["TVD_ft"]) for r in rows])*FT
    if md[0] > 0:
        md, tvd = np.r_[0., md], np.r_[0., tvd]
    return wg.Survey(md, tvd)


# ---------- assemblies, bits and mud ----------

def report_bha():
    """Assembly named by each report date; a date naming two assemblies is ambiguous."""
    out = {}
    for r in read(WELL/"bha_reports.csv"):
        out.setdefault(r["report_date"], set()).add(r["bha_id"])
    return {d: next(iter(s)) if len(s) == 1 else "" for d, s in out.items()}


def report_jets():
    """Nozzle sizes (1/32 in) printed in each report date's bit table."""
    out = {}
    for r in read(WELL/"bit_inputs.csv"):
        cells = ast.literal_eval(r["input_cells"])
        # Cells are bit number, run, make, type and size (the size cell is
        # sometimes merged with neighbouring text), then up to four nozzle
        # cells in 1/32 in. Nozzles are the whole numbers that directly follow
        # the size cell, up to four, stopping at a blank. A number after a
        # blank is footage, so a bit with blank nozzle cells has no record.
        first = next((i for i in range(5, len(cells)) if cells[i].isdigit() and 7 <= int(cells[i]) <= 40
                      and cells[i-1] and not cells[i-1].isdigit()), None)
        if first is None:
            continue
        jets = []
        for c in cells[first:first+4]:
            if not c.isdigit():
                break
            jets.append(int(c))
        if jets:
            out.setdefault(r["report_date"], set()).add(tuple(jets))
    return out


def tfa_in2(jets):
    return float(sum(np.pi/4*(j/32)**2 for j in jets))


SURFACE_FT, SURFACE_FRACTION, SURFACE_BINS = 350., 0.2, 6


def runs(history):
    """Intervals between trips to surface, or input gaps over ten minutes.

    A trip to surface is at least SURFACE_BINS consecutive bins with the bit
    above SURFACE_FT and above SURFACE_FRACTION of the hole depth. Bit depths
    below -100 ft are recording faults and are not surface visits.
    """
    t, bit, hole = history["time"], history["bit_depth_ft"], history["hole_depth_ft"]
    shallow = np.isfinite(bit) & (bit > -100.) & (bit < SURFACE_FT) & (bit < SURFACE_FRACTION*np.nan_to_num(hole, nan=np.inf))
    edges = np.flatnonzero(np.diff(np.r_[0, shallow.astype(int), 0]))
    surface = np.zeros_like(shallow)
    for a, z in zip(edges[::2], edges[1::2]):
        if z-a >= SURFACE_BINS:
            surface[a:z] = True
    gap = np.r_[True, np.diff(t).astype("timedelta64[s]").astype(float) > 600.]
    run_id = np.cumsum(gap | np.r_[True, surface[1:] != surface[:-1]])
    run_id[surface] = 0
    return run_id


def assign_runs(history, run_id):
    """Assembly for each run: the single assembly named by every report whose end of day lies in the run."""
    named = report_bha()
    jets = report_jets()
    t = history["time"]
    out = {}
    for rid in np.unique(run_id[run_id > 0]):
        idx = np.flatnonzero(run_id == rid)
        start, end = t[idx[0]], t[idx[-1]]+np.timedelta64(10, "s")
        days = []
        day = (start-np.timedelta64(1, "D")).astype("datetime64[D]")
        while day <= end.astype("datetime64[D]"):
            midnight = (day+np.timedelta64(1, "D")).astype("datetime64[s]")
            if start <= midnight <= end:
                days.append(str(day))
            day += np.timedelta64(1, "D")
        ids = {named.get(d, "") for d in days}
        bha = next(iter(ids)) if len(ids) == 1 and "" not in ids else ""
        # The bit table of the day an assembly changes can still list the
        # previous bit, so the nozzles are those of the run's last report day.
        nozzle = jets.get(days[-1], set()) if days else set()
        listed = sorted({j for d in days for j in jets.get(d, set())})
        out[int(rid)] = dict(run_start=str(start), run_end=str(end), report_days=";".join(days),
                             bha=bha, status=("assigned" if bha else
                                              "no report end of day in run" if not days else
                                              "reports name different or missing assemblies"),
                             jets=";".join("-".join(map(str, j)) for j in sorted(nozzle)),
                             jets_listed_in_run=";".join("-".join(map(str, j)) for j in listed),
                             tfa_in2=tfa_in2(next(iter(nozzle))) if len(nozzle) == 1 else np.nan)
    return out


def mud_samples(history):
    rows = read(WELL/"mud_reports.csv")
    t, hole = history["time"], np.fmax.accumulate(np.where(np.isfinite(history["hole_depth_ft"]),
                                                            history["hole_depth_ft"], 0.))
    t2, _, h2 = report_clock()
    for r in rows:
        when = np.datetime64(f"{r['sample_date']}T{r['sample_time']}")
        if GAP[0] <= str(when).replace("T", " ") < GAP[1]:
            i = np.searchsorted(t2, when)
            r["hole_ft"] = float(h2[min(i, len(h2)-1)])
        else:
            i = np.searchsorted(t, when)
            r["hole_ft"] = float(hole[max(0, min(i, len(t)-1))])
    return rows


def section(hole_ft):
    return 0 if hole_ft <= SURFACE["section_td_ft"] else 1 if hole_ft <= INTERMEDIATE["section_td_ft"] else 2


def mud_for(when, hole_ft, samples):
    """Nearest density and nearest paired PV/YP in the same hole section; ties to the earlier sample."""
    pool = [s for s in samples if section(s["hole_ft"]) == section(hole_ft)]
    stamp = lambda s: np.datetime64(f"{s['sample_date']}T{s['sample_time']}")
    key = lambda s: (abs((stamp(s)-np.datetime64(when)).astype("timedelta64[s]").astype(float)), stamp(s))
    dense = [s for s in pool if np.isfinite(number(s["mud_weight_ppg"]))]
    if not dense:
        raise ValueError("no mud density in the section")
    density = min(dense, key=key)
    paired = [s for s in pool if np.isfinite(number(s["plastic_viscosity_cP"]))
              and np.isfinite(number(s["yield_point_lbf_100ft2"]))]
    rheology = min(paired, key=key) if paired else None
    return dict(density_ppg=number(density["mud_weight_ppg"]),
                mud_sample=f"{density['sample_date']} {density['sample_time']}",
                pv_cP=np.nan if rheology is None else number(rheology["plastic_viscosity_cP"]),
                yp=np.nan if rheology is None else number(rheology["yield_point_lbf_100ft2"]),
                rheology_sample="" if rheology is None else f"{rheology['sample_date']} {rheology['sample_time']}")


# ---------- geometry ----------

def pipe_type(name, od, inside, joint=None):
    p = wg.PipeType(name, (wg.Layer(inside*INCH/2, od*INCH/2, wg.K_STEEL),))
    return replace(p, hydraulic_joint=joint) if joint is not None else p


def drill_pipe():
    joint = hl.HydraulicJoint(PIPE["joint_od_in"]*INCH, PIPE["joint_id_in"]*INCH, PIPE["joint_in"]*INCH,
                              PIPE["pitch_ft"]*FT, source="58-32 pressure test primary catalogue scenario")
    return pipe_type("ordinary 4 in pipe", PIPE["od_in"], PIPE["id_in"], joint)


def hole(md_bit, hole_ft, casing=True):
    """Hole intervals for the section being drilled at hole_ft.

    casing=False removes every casing and cement layer and opens the hole at
    the drilled diameter: the heat-maximising geometry of the consistency bound.
    """
    r = lambda d: d*INCH/2
    steel = lambda p, q: wg.Layer(p, q, wg.K_STEEL)
    cement = lambda p, q: wg.Layer(p, q, wg.K_CEMENT)
    sec = section(hole_ft)
    c, s, m = CONDUCTOR, SURFACE, INTERMEDIATE
    if not casing:
        # Drilled diameters: 17.5 in to the surface shoe, 12.25 in to the
        # intermediate shoe, 8.75 in below, as far as the section has reached.
        bounds = [(0., s["shoe_ft"], s["hole_in"]), (s["shoe_ft"], m["shoe_ft"], m["hole_in"]),
                  (m["shoe_ft"], 1e9, PRODUCTION_HOLE_IN)]
        sizes = {0: [(0., 1e9, s["hole_in"])], 1: bounds[:1]+[(s["shoe_ft"], 1e9, m["hole_in"])], 2: bounds}[sec]
        return [wg.open_hole(top*FT, min(bot*FT, md_bit+1e-6), size*INCH)
                for top, bot, size in sizes if top*FT < md_bit]
    if sec == 0:
        intervals = [(0., c["shoe_ft"], r(c["id_in"]), (steel(r(c["id_in"]), r(c["od_in"])),))]
        open_from, open_size = c["shoe_ft"], s["hole_in"]
    elif sec == 1:
        intervals = [(0., c["shoe_ft"], r(s["id_in"]), (steel(r(s["id_in"]), r(s["od_in"])), cement(r(s["od_in"]), r(c["id_in"])),
                                                       steel(r(c["id_in"]), r(c["od_in"])))),
                     (c["shoe_ft"], s["shoe_ft"], r(s["id_in"]), (steel(r(s["id_in"]), r(s["od_in"])),
                                                                  cement(r(s["od_in"]), r(s["hole_in"]))))]
        open_from, open_size = s["shoe_ft"], m["hole_in"]
    else:
        inner = steel(r(m["id_in"]), r(m["od_in"]))
        intervals = [(0., c["shoe_ft"], r(m["id_in"]), (inner, cement(r(m["od_in"]), r(s["id_in"])), steel(r(s["id_in"]), r(s["od_in"])),
                                                       cement(r(s["od_in"]), r(c["id_in"])), steel(r(c["id_in"]), r(c["od_in"])))),
                     (c["shoe_ft"], s["shoe_ft"], r(m["id_in"]), (inner, cement(r(m["od_in"]), r(s["id_in"])),
                                                                  steel(r(s["id_in"]), r(s["od_in"])), cement(r(s["od_in"]), r(s["hole_in"])))),
                     (s["shoe_ft"], m["shoe_ft"], r(m["id_in"]), (inner, cement(r(m["od_in"]), r(m["hole_in"]))))]
        open_from, open_size = m["shoe_ft"], PRODUCTION_HOLE_IN
    out = []
    for top, bottom, a_, layers in intervals:
        if top*FT < md_bit:
            out.append(wg.HoleInterval(top*FT, min(bottom*FT, md_bit+1e-6), a_, layers))
    if md_bit > open_from*FT:
        out.append(wg.open_hole(open_from*FT, md_bit+1e-6, open_size*INCH))
    return out


def components(bha):
    """Assembly components from the bit upward: (name, OD in, bore in, length ft, flag)."""
    if bha == "2":
        rows = read(WELL/"pressure-test/inputs/components.csv")
        return [(r["component"], number(r["reported_OD_in"]), number(r["reported_ID_in"]),
                 number(r["total_length_ft"]), "Figure 14 bore" if np.isfinite(number(r["reported_ID_in"])) else "")
                for r in sorted(rows, key=lambda r: int(r["item"]))]
    rows = [r for r in read(WELL/"bha_components.csv") if r["bha_id"] == bha]
    if not rows:
        # Early reports state the assembly as one line without lengths. With no
        # recorded bore the string is ordinary pipe to the bit in either case.
        return [("no component table", np.nan, np.nan, np.nan, "")]
    last = max(r["report_date"] for r in rows)
    rows = [r for r in rows if r["report_date"] == last]
    # One report can repeat its table; keep the first page's rows.
    first = min((r["source_member"], int(r["page"])) for r in rows)
    rows = [r for r in rows if (r["source_member"], int(r["page"])) == first]
    return [(r["component"], number(r["OD_in"]), number(r["passage_ID_in"]), number(r["reported_length_ft"]),
             "") for r in sorted(rows, key=lambda r: int(r["table_row"]))]


def geometry(bha, md_bit, hole_ft, srv, casing=True):
    """String from the recorded components; a component without a recorded bore is ordinary pipe."""
    pipe = drill_pipe()
    bottom, remaining, flags = [], md_bit, []
    for name, od, bore, length, flag in components(bha):
        if name == "BIT":
            continue
        tools = (wg.DownholeTool("mud_motor", od, differential=0., source=name),) if name == "MMTR" else ()
        if not np.isfinite(length):
            flags.append(name)
            break
        if remaining <= 1e-6:
            break
        if np.isfinite(od+bore):
            shape = pipe_type(name, od, bore)
        else:
            shape = pipe
            flags.append(name)
        take = min(remaining, length*FT)
        bottom.append(wg.StringSegment(take, shape, tools=tools))
        remaining -= take
    if remaining > 1e-6:
        bottom.append(wg.StringSegment(remaining, pipe))
    return wg.WellGeometry(list(reversed(bottom)), hole(md_bit, hole_ft, casing), srv), flags
