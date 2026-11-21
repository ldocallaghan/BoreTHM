"""Draw the diagnosis figures from the CSVs in this folder.

usage: figures.py

Writes PNG files beside this script:

  temperature_time.png             Pason inlet and return while pumping,
                                   the daily report "In" and "Out", the
                                   assembly starts, casing points, the
                                   mud cooler note and the inlet step
  return_minus_inlet_depth.png     return minus inlet against bit depth,
                                   coloured by assembly
  energy_balance.png               measured heat gain against the rock
                                   bound plus hydraulic heat
  formation_profiles.png           the 16A transfer and the native logs
  sensitivity_errors.png           v1.8.0 error of assemblies 2 to 5 for
                                   each sensitivity case
"""
import csv
from datetime import datetime
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
INK, RULE, GRID = "#2b2b2b", "#9a9a9a", "#e3e3e3"
INLET, RETURN, THIRD = "#2a78d6", "#eb6834", "#1baf7a"
ASSEMBLIES = [str(n) for n in range(2, 12)]
SHADES = {b: plt.get_cmap("Blues")(0.45+0.55*i/(len(ASSEMBLIES)-1)) for i, b in enumerate(ASSEMBLIES)}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
STEP = datetime(2021, 2, 15, 18, 13)
COOLER = datetime(2021, 2, 10)


def read(path):
    with open(path, encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def num(text):
    return float(text) if text not in ("", None) else np.nan


def style():
    plt.rcParams.update({"font.size": 8, "axes.edgecolor": RULE, "axes.labelcolor": INK,
                         "xtick.color": INK, "ytick.color": INK, "axes.grid": True,
                         "grid.color": GRID, "grid.linewidth": .6, "legend.frameon": False})


def casing_points():
    first = {}
    for r in read(STUDY/"casing_records.csv"):
        first.setdefault((r["OD_in"], r["shoe_MD_ft"]), r["report_date"])
    return [(datetime.fromisoformat(d), f"{float(od):g} in shoe {shoe} ft")
            for (od, shoe), d in first.items() if "2021-02-08" <= d <= "2021-02-28"]


def temperature_time(record):
    t = np.array([datetime.fromisoformat(r["time"]) for r in record])
    pumping = np.array([num(r["flow_gpm"]) > 300 for r in record])
    fig, ax = plt.subplots(figsize=(10, 5.2))
    for key, colour, label in (("inlet_C", INLET, "Pason inlet"), ("return_C", RETURN, "Pason return")):
        y = np.array([num(r[key]) for r in record])
        y[~pumping] = np.nan
        ax.plot(t, y, color=colour, linewidth=1.2, label=f"{label} (10 min mean, flow > 300 US gal/min)")
    reports = [r for r in read(HERE/"report_temperatures.csv") if r["source"] == "daily drilling report"]
    for key, colour, label in (("in_F", INLET, 'daily report "In"'), ("out_F", RETURN, 'daily report "Out"')):
        pts = []
        for r in reports:
            m = re.match(r"(\d{2})-([A-Za-z]{3})-(\d{2})\s+(\d{2}):(\d{2})", r["sample"])
            if m and r[key]:
                when = datetime(2000+int(m[3]), MONTHS.index(m[2].title())+1, int(m[1]), int(m[4]), int(m[5]))
                pts.append((when, (float(r[key])-32)/1.8))
        pts = [p for p in pts if t[0] <= p[0] <= t[-1]]
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=36, facecolors="white", edgecolors=colour,
                   linewidths=1.6, zorder=3, label=label)
    starts = {}
    for r, when in zip(record, t):
        if r["bha"] and r["bha"] not in starts and num(r["flow_gpm"]) > 300:
            starts[r["bha"]] = when
    top = ax.get_ylim()[1]
    for bha, when in starts.items():
        ax.axvline(when, color=RULE, linewidth=.6, linestyle=":")
        ax.text(when, top, f" {bha}", color=INK, fontsize=7, va="top")
    events = [(when, INK, "--", label) for when, label in casing_points()]
    events += [(COOLER, THIRD, "-", "mud cooler turned on, 10 Feb (no time given)"),
               (STEP, THIRD, "-", "Pason inlet signal lost, 18:13 on 15 Feb")]
    for letter, (when, colour, dash, label) in zip("abcde", sorted(events)):
        ax.axvline(when, color=colour, linewidth=.9, linestyle=dash, label=f"{letter}: {label}")
        ax.text(when, 1.005, letter, transform=ax.get_xaxis_transform(), color=INK, fontsize=7,
                ha="center", va="bottom", fontweight="bold")
    ax.set_ylabel("temperature, °C")
    ax.set_title("56-32 surface mud temperatures; dotted lines and numbers mark the first pumping of each assembly",
                 color=INK, pad=14)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.07), fontsize=7, ncol=3)
    fig.tight_layout()
    fig.savefig(HERE/"temperature_time.png", dpi=150)
    plt.close(fig)


def by_assembly_scatter(ax, rows, x, y, size=8):
    for bha in ASSEMBLIES:
        sel = [r for r in rows if r["bha"] == bha]
        if sel:
            ax.scatter([x(r) for r in sel], [y(r) for r in sel], s=size, color=SHADES[bha],
                       marker="o" if int(bha) >= 6 else "^", linewidths=0, label=f"assembly {bha}")


def return_minus_inlet(record):
    rows = [r for r in record if r["bha"] and num(r["flow_gpm"]) > 300 and r["return_minus_inlet_C"]
            and abs(num(r["bit_ft"])-num(r["hole_ft"])) <= 5]
    fig, ax = plt.subplots(figsize=(7, 4))
    by_assembly_scatter(ax, rows, lambda r: num(r["bit_ft"]), lambda r: num(r["return_minus_inlet_C"]))
    ax.axhline(0, color=RULE, linewidth=1)
    ax.set_xlabel("bit depth, ft MD")
    ax.set_ylabel("Pason return minus inlet, °C")
    ax.set_title("10-minute means on bottom with flow > 300 US gal/min (triangles: assemblies 2 to 5)", color=INK)
    ax.legend(fontsize=7, ncol=2, markerscale=1.5)
    fig.tight_layout()
    fig.savefig(HERE/"return_minus_inlet_depth.png", dpi=150)
    plt.close(fig)


def energy_balance(classes):
    fig, ax = plt.subplots(figsize=(6, 5))
    limit = lambda r: (num(r["rock_bound_W"])+num(r["hydraulic_W"]))/1e6
    by_assembly_scatter(ax, classes, limit, lambda r: num(r["measured_Q_W"])/1e6, size=12)
    hi = max(max(limit(r) for r in classes), max(num(r["measured_Q_W"]) for r in classes)/1e6)*1.05
    ax.plot([0, hi], [0, hi], color=RULE, linewidth=1)
    ax.plot([0, hi/1.25], [0, hi], color=INK, linewidth=1, linestyle="--")
    ax.text(hi/1.25*.97, hi*.97, "1.25 × bound ", color=INK, fontsize=7, ha="right", va="top")
    ax.text(hi*.99, hi*.95, "bound", color=INK, fontsize=7, ha="right", va="top")
    ax.set_xlabel("largest rock heat plus hydraulic heat, MW (calculated)")
    ax.set_ylabel("measured heat gain, MW")
    ax.set_title("Each scored window (triangles: assemblies 2 to 5)", color=INK)
    ax.legend(fontsize=7, ncol=2, markerscale=1.3, loc="center right")
    fig.tight_layout()
    fig.savefig(HERE/"energy_balance.png", dpi=150)
    plt.close(fig)


def formation_profiles(logs, windows):
    fig, ax = plt.subplots(figsize=(5, 6))
    cbl = sorted((num(r["tvd_ft"]), num(r["temperature_C"]), num(r["transfer_16a_C"]))
                 for r in logs if r["log"] == "cbl_mtem")
    thru = sorted((num(r["tvd_ft"]), num(r["temperature_C"])) for r in logs if r["log"] == "thrubit_wtep")
    ax.plot([c[2] for c in cbl], [c[0] for c in cbl], color=INK, linewidth=1.6, label="16A transfer (declared)")
    ax.plot([c[1] for c in cbl], [c[0] for c in cbl], color=INLET, linewidth=1.2,
            label="56-32 cement bond log MTEM, 17 Aug 2021")
    ax.plot([c[1] for c in thru], [c[0] for c in thru], color=RETURN, linewidth=1.2,
            label="56-32 ThruBit WTEP_TMG, 27 Feb 2021")
    shallow = [num(w["tvd_ft"]) for w in windows if w["bha"] in ("2", "3", "4", "5")]
    ax.axhspan(min(shallow), max(shallow), color=GRID, zorder=0, label="bit depths, assemblies 2 to 5")
    ax.set_ylim(5500, 0)
    visible = [c[1] for c in cbl if c[0] <= 5500]+[c[2] for c in cbl if c[0] <= 5500]
    ax.set_xlim(min(visible)-5, max(visible)+5)
    ax.set_xlabel("temperature, °C")
    ax.set_ylabel("true vertical depth, ft")
    ax.legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    fig.savefig(HERE/"formation_profiles.png", dpi=150)
    plt.close(fig)


def sensitivity_errors(rows, windows):
    depth = {w["sample_id"]: num(w["bit_ft"]) for w in windows}
    cases = list(dict.fromkeys(r["case"] for r in rows))
    fig, axes = plt.subplots(1, len(cases), figsize=(2.6*len(cases), 3), sharex=True, sharey=True)
    for ax, case in zip(np.atleast_1d(axes), cases):
        sel = [r for r in rows if r["case"] == case and r["status"] == "converged"]
        ax.scatter([depth[r["sample_id"]] for r in sel], [num(r["error_C"]) for r in sel], s=8,
                   color=INLET, linewidths=0)
        ax.axhline(0, color=RULE, linewidth=1)
        ax.set_title(f"{case} (n = {len(sel)})", color=INK)
        ax.set_xlabel("bit depth, ft MD")
    np.atleast_1d(axes)[0].set_ylabel("v1.8.0 minus measured return, °C")
    fig.tight_layout()
    fig.savefig(HERE/"sensitivity_errors.png", dpi=150)
    plt.close(fig)


def main():
    style()
    record = read(HERE/"surface_record_10min.csv")
    temperature_time(record)
    return_minus_inlet(record)
    energy_balance(read(HERE/"classification.csv"))
    windows = read(HERE/"window_surface.csv")
    formation_profiles(read(HERE/"native_temperature_logs.csv"), windows)
    if (HERE/"sensitivity.csv").exists():
        sensitivity_errors(read(HERE/"sensitivity.csv"), windows)


if __name__ == "__main__":
    main()
