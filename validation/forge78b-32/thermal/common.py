"""Shared inputs for the 78B-32 thermal forecast: history, assemblies, geometry, mud and formation.

Imports the released BoreTHM package. Reads only the committed input extracts
in `inputs/`. No temperature target is read.
"""
import csv
from dataclasses import replace
from datetime import datetime, timedelta
import gzip
import hashlib
from pathlib import Path

import numpy as np

from borethm import fluids, hydraulic_losses as hl, model1_coupled as m1, well_geometry as wg
from borethm.studies import validate_forge16b as b

HERE = Path(__file__).resolve().parent
WELL = HERE.parent
INPUTS = HERE/"inputs"
FT, INCH, GPM = 0.3048, 0.0254, 3.785411784e-3/60
PPG = 119.82642731689663
YP_PA = 0.4788025898033584
K_ROCK, RHOCP_ROCK = b.K_ROCK, b.RHOCP_ROCK
PV_REF_T = 48.9

# Casing from the end-of-well casing table: outside diameter, bore, shoe and
# the drilled hole it was cemented in (in, ft). The conductor's hole is not
# recorded; rock starts at its outside diameter.
CASINGS = (
    dict(name="conductor", od_in=24.0, id_in=23.0, shoe_ft=128.5, hole_in=None),
    dict(name="surface", od_in=16.0, id_in=15.25, shoe_ft=416.0, hole_in=22.0),
    dict(name="intermediate", od_in=11.75, id_in=10.88, shoe_ft=2990.0, hole_in=14.75),
    dict(name="production", od_in=7.0, id_in=5.82, shoe_ft=8509.0, hole_in=10.625),
)
# Drilled diameter by depth, from the section depths of the bit records and
# BHA sheets: 22 in to 421 ft, 14-3/4 in to 3,009 ft, 10-5/8 in to 8,545 ft
# (the cored intervals were reamed to 10-5/8 in), 5-3/4 in below.
SECTIONS = ((0.0, 421.0, 22.0), (421.0, 3009.0, 14.75), (3009.0, 8545.0, 10.625), (8545.0, np.inf, 5.75))

# Drill pipe by bit diameter (protocol, "Drill pipe").
PIPE_5 = dict(name="5 in 19.5 lb/ft", od_in=5.0, id_in=4.276,
              joint=dict(od_in=6.625, id_in=3.25, length_in=29.0, pitch_ft=31.5,
                         source="56-32 pressure protocol connection scenario"))
PIPE_55 = dict(name="5.5 in 24.7 lb/ft", od_in=5.5, id_in=4.670, joint=None)
PIPE_35 = dict(name="3.5 in 13.30 lb/ft (unchecked)", od_in=3.5, id_in=2.764, joint=None)

SLB_MWD = ("1", "3", "4", "6", "7", "8", "9", "10")
SDI = ("14", "15", "22")
# Sanvean sensor positions above the bit (ft): lower and upper sub. BHA 3 and 4
# from the sheet spans of CSS-008 and CSS-007; BHA 15 as stated in the
# 15 July report.
SANVEAN_FT = {"3": (63.74, 120.76), "4": (63.74, 120.76), "15": (50.96, 132.86)}
BHA22_DEPTH_OUT_FT = 9500.0   # the sheet prints 10; the bit record gives 9,500
SHEET_DEPTH_TOL_FT = 1.0
SHEET_TIME_TOL = timedelta(hours=12)


def sha(path):
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
        out = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return np.nan
    return out if np.isfinite(out) else np.nan


# ---------- history ----------

def rig():
    """Pason ten-second inputs. TEMP IN is read as Fahrenheit."""
    with gzip.open(INPUTS/"rig_inputs_10s.csv.gz", "rt", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    out = dict(time=np.array([np.datetime64(r["time"]) for r in rows]))
    for key in ("bit_depth_ft", "hole_depth_ft", "flow_gpm", "rop_ft_h", "inlet_temperature_source_degrees"):
        out[key] = np.array([number(r[key]) for r in rows])
    out["inlet_C"] = (out["inlet_temperature_source_degrees"]-32)/1.8
    return out


class Clock:
    """Cumulative circulation: ten seconds for each Pason bin whose flow exceeds 100 US gal/min."""
    def __init__(self, history):
        t, q, h = history["time"], history["flow_gpm"], history["hole_depth_ft"]
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


# ---------- survey and formation ----------

def survey():
    rows = list(csv.reader(open(INPUTS/"survey-source.csv", encoding="utf-8", newline="")))
    head = [h.replace("\n", " ") for h in rows[0]]
    i_md, i_tvd = head.index("Measured Depth (ft)"), head.index("True Vertical Depth (ft)")
    md, tvd = [], []
    for r in rows[1:]:
        x, y = number(r[i_md]), number(r[i_tvd])
        if np.isfinite(x) and np.isfinite(y):
            md.append(x)
            tvd.append(y)
    md, tvd = np.array(md)*FT, np.array(tvd)*FT
    if md[0] > 0:
        md, tvd = np.r_[0., md], np.r_[0., tvd]
    return wg.Survey(md, tvd)


FORMATION_FILE = WELL.parent/"forge16a"/"formation_temperature_216day.csv"


def formation():
    """The 16A 216-day survey against TVD (m), held at its end values beyond the log.

    The same interpolation as `validate_forge16a.formation("216", ...)`, read
    from the repository copy because the released package does not ship the
    16A data.
    """
    rows = read(FORMATION_FILE)
    tvd = np.array([number(r["tvd_ft"]) for r in rows])*FT
    temp = np.array([number(r["temp_C"]) for r in rows])
    return lambda z: np.interp(np.asarray(z, float), tvd, temp)


# ---------- assemblies ----------

def sheet_time(text):
    return datetime.strptime(text.replace(" ", ""), "%d-%b-%y%H:%M")


def sheets():
    out = {}
    for r in read(INPUTS/"bha_sheets.csv"):
        depth_out = BHA22_DEPTH_OUT_FT if r["bha"] == "22" else number(r["depth_out_ft"])
        out[r["bha"]] = dict(bha=r["bha"], depth_in_ft=number(r["depth_in_ft"]), depth_out_ft=depth_out,
                             time_in=sheet_time(r["date_in_source"]), time_out=sheet_time(r["date_out_source"]))
    return out


def assign(sheet_rows, centre, hole_min_ft, hole_max_ft):
    """The single assembly whose widened sheet depth interval and times contain the window."""
    found = [s["bha"] for s in sheet_rows.values()
             if s["depth_in_ft"]-SHEET_DEPTH_TOL_FT <= hole_min_ft and hole_max_ft <= s["depth_out_ft"]+SHEET_DEPTH_TOL_FT
             and s["time_in"]-SHEET_TIME_TOL <= centre <= s["time_out"]+SHEET_TIME_TOL]
    return (found[0], "assigned") if len(found) == 1 else ("", "no sheet" if not found else "more than one sheet")


def components(bha):
    """Sheet components from the bit upward: dicts with item, length, OD and bore."""
    rows = [r for r in read(INPUTS/"bha_components.csv") if r["bha"] == bha]
    return [dict(item=r["item"], comment=r["comment"], length_ft=number(r["length_ft"]),
                 od_in=number(r["od_in"]), id_in=number(r["id_in"])) for r in sorted(rows, key=lambda r: int(r["row"]))]


def spans(bha):
    """(item, comment, bottom ft, top ft) above the bit face for each component."""
    out, base = [], 0.
    for c in components(bha):
        out.append((c["item"], c["comment"], base, base+c["length_ft"]))
        base += c["length_ft"]
    return out


def sensor_offset_ft(bha):
    """Midpoint of the MWD item (SLB) or of the lower monel below the pulser sub (Scientific Drilling)."""
    s = spans(bha)
    if bha in SLB_MWD:
        bottom, top = next((lo, hi) for item, _, lo, hi in s if item == "MWD")
    elif bha in SDI:
        pulser = next(i for i, (item, comment, _, _) in enumerate(s) if "PULSER" in comment.upper())
        bottom, top = next((lo, hi) for item, _, lo, hi in reversed(s[:pulser]) if item == "MONEL")
    else:
        return np.nan
    return 0.5*(bottom+top)


def bit_diameter(bha):
    first = components(bha)[0]
    return first["od_in"] if first["item"] in ("BIT", "CORBT", "CORBIT") else np.nan


def nozzles(bha):
    """Nozzle sets of the bit records whose diameter equals the sheet bit and whose depth in is within 1 ft."""
    sheet = sheets()[bha]
    d = bit_diameter(bha)
    sets = set()
    for r in read(INPUTS/"bit_reports.csv"):
        if (abs(number(r["diameter_in"])-d) < 1e-3 and abs(number(r["depth_in_ft"])-sheet["depth_in_ft"]) <= 1.0
                and r["jets_32nds"].strip()):
            sets.add(tuple(sorted(int(j) for j in r["jets_32nds"].split())))
    return sets


def tfa_in2(jets):
    return float(sum(np.pi/4*(j/32)**2 for j in jets))


# ---------- mud ----------

def section(hole_ft):
    return next(i for i, (top, bottom, _) in enumerate(SECTIONS) if hole_ft <= bottom or i == len(SECTIONS)-1)


def mud_samples(history):
    """Mud checks with the Pason hole depth at their time, which sets their hole section."""
    rows = read(INPUTS/"mud_reports.csv")
    t = history["time"]
    hole = np.fmax.accumulate(np.where(np.isfinite(history["hole_depth_ft"]), history["hole_depth_ft"], 0.))
    for r in rows:
        when = np.datetime64(f"{r['sample_date']}T{r['sample_time']}")
        r["hole_ft"] = float(hole[max(0, min(np.searchsorted(t, when), len(t)-1))])
        r["when"] = when
    return rows


def mud_for(when, hole_ft, samples):
    """Nearest density and nearest paired PV/YP in the same hole section; ties to the earlier sample."""
    pool = [s for s in samples if section(s["hole_ft"]) == section(hole_ft)]
    key = lambda s: (abs((s["when"]-np.datetime64(when)).astype("timedelta64[s]").astype(float)), s["when"])
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


def water_reference():
    """Water's density (kg/m3) at the package reference state and viscosity (cP) at PV_REF_T."""
    w = fluids.water()
    viscosity = float(np.ravel(m1.fluid_props(np.array([PV_REF_T]), np.array([m1.P_SURF]), w)[2])[0])*1e3
    return w.rho_surface, viscosity


def fluid_for(density_ppg, pv_cP, yp):
    """The water rule: a density at or below water's takes the package's water.

    A reported plastic viscosity below water's own at the reference
    temperature (the fresh-water checks report 0 to 2 cP) takes water's
    viscosity.
    """
    rho_w, mu_w = water_reference()
    if density_ppg*PPG <= rho_w:
        return fluids.water(), "water"
    pv = pv_cP if np.isfinite(pv_cP) and pv_cP >= mu_w else None
    return (fluids.Mud(density_ppg*PPG, pv_ref=pv*1e-3 if pv is not None else None,
                       yield_point=yp*YP_PA if np.isfinite(yp) else 0., pv_ref_T=PV_REF_T),
            "mud" if pv is not None else "mud, water viscosity")


# ---------- geometry ----------

def pipe_type(name, od, inside, joint=None):
    p = wg.PipeType(name, (wg.Layer(inside*INCH/2, od*INCH/2, wg.K_STEEL),))
    return replace(p, hydraulic_joint=joint) if joint is not None else p


def drill_pipe(bit_in):
    spec = PIPE_5 if bit_in > 11 else PIPE_55 if bit_in > 6 else PIPE_35
    j = spec["joint"]
    joint = None if j is None else hl.HydraulicJoint(j["od_in"]*INCH, j["id_in"]*INCH, j["length_in"]*INCH,
                                                     j["pitch_ft"]*FT, source=j["source"])
    return pipe_type(spec["name"], spec["od_in"], spec["id_in"], joint), spec["name"]


def drilled_diameter(depth_ft, bit_in, depth_in_ft):
    """The section diameter above the assembly's depth in; its bit diameter below."""
    if depth_ft >= depth_in_ft:
        return bit_in
    return next(d for top, bottom, d in SECTIONS if depth_ft < bottom)


def hole(bha, md_bit):
    """Casing in place (bore larger than the bit), cemented to the next casing or its hole; open hole below."""
    r = lambda d: d*INCH/2
    steel = lambda p, q: wg.Layer(p, q, wg.K_STEEL)
    cement = lambda p, q: wg.Layer(p, q, wg.K_CEMENT)
    bit_in = bit_diameter(bha)
    depth_in_ft = sheets()[bha]["depth_in_ft"]
    in_place = sorted((c for c in CASINGS if c["id_in"] > bit_in), key=lambda c: c["id_in"])
    out, top = [], 0.
    for shoe in sorted(c["shoe_ft"] for c in in_place):
        covering = [c for c in in_place if c["shoe_ft"] >= shoe]
        layers, prev = [steel(r(covering[0]["id_in"]), r(covering[0]["od_in"]))], covering[0]
        for outer in covering[1:]:
            layers += [cement(r(prev["od_in"]), r(outer["id_in"])), steel(r(outer["id_in"]), r(outer["od_in"]))]
            prev = outer
        if prev["hole_in"] is not None:
            layers.append(cement(r(prev["od_in"]), r(prev["hole_in"])))
        if top*FT < md_bit:
            out.append(wg.HoleInterval(top*FT, min(shoe*FT, md_bit+1e-6), r(covering[0]["id_in"]), tuple(layers)))
        top = shoe
    # Open hole below the deepest shoe, split where the drilled diameter changes.
    edges = sorted({top, *(e for _, e, _ in SECTIONS[:-1] if top < e), *([depth_in_ft] if depth_in_ft > top else [])})
    edges = [e for e in edges if e*FT < md_bit]+[md_bit/FT+1e-6/FT]
    for lo, hi in zip(edges[:-1], edges[1:]):
        out.append(wg.open_hole(lo*FT, min(hi*FT, md_bit+1e-6), drilled_diameter(lo, bit_in, depth_in_ft)*INCH))
    return out


def geometry(bha, md_bit, srv):
    """String from the sheet components; a component without OD or bore is drill pipe (flagged).

    A mud motor's internal thermal geometry takes the bore of the component above it.
    A roller reamer or stabiliser listed at or above the bit diameter (its
    cutter or blade gauge) takes the OD of the drill collar above it (flagged).
    """
    bit_in = bit_diameter(bha)
    pipe, pipe_name = drill_pipe(bit_in)
    rows = components(bha)
    bottom, remaining, flags = [], md_bit, []
    for i, row in enumerate(rows):
        if row["item"] in ("BIT", "CORBT", "CORBIT"):
            continue
        if remaining <= 1e-6:
            break
        od, bore, length = row["od_in"], row["id_in"], row["length_ft"]
        if row["item"] in ("RR", "STAB") and od >= bit_in:
            od = next((r["od_in"] for r in rows[i+1:] if r["item"] == "DC"), np.nan)
            flags.append(f"{row['item']} at gauge, collar OD")
        tools = ()
        if row["item"] == "MMTR":
            bore = rows[i+1]["id_in"] if i+1 < len(rows) else np.nan
            tools = (wg.DownholeTool("mud_motor", od, differential=0., source=row["comment"]),)
        if not np.isfinite(length):
            flags.append(f"{row['item']} (no length)")
            break
        if np.isfinite(od) and np.isfinite(bore):
            shape = pipe_type(row["item"], od, bore)
        else:
            shape = pipe
            flags.append(row["item"])
        take = min(remaining, length*FT)
        bottom.append(wg.StringSegment(take, shape, tools=tools))
        remaining -= take
    if remaining > 1e-6:
        bottom.append(wg.StringSegment(remaining, pipe))
    return wg.WellGeometry(list(reversed(bottom)), hole(bha, md_bit), srv), flags, pipe_name
