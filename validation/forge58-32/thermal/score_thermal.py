"""Score the 58-32 thermal forecast as declared in thermal_protocol.md.

usage: python -m validation.forge58-32.thermal.score_thermal OUTPUT

Reads the committed predictions and targets, refuses files whose hashes
differ from their manifests, and writes the part A, B and D scores and
figures to OUTPUT.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime
from importlib import import_module
import json
import math
from pathlib import Path

import numpy as np

from borethm import fluids, model1_coupled as m1

c = import_module("validation.forge58-32.thermal.common")
pt = import_module("validation.forge58-32.thermal.predict_thermal")
PRED = c.WELL/"predictions-v1.9.0"
TARGETS = c.WELL/"targets"
FLOWS = ("primary", "secondary")
MODELS = ("v1.9.0", "v1.7.0", "analytical")
PRIMARY = "v1.9.0"
PERSISTENCE = "persistence"
MIN_FINITE_FRACTION = .8
UNIT_MARGIN_C = 5.
GROUPS = {"depth": "bit_ft", "flow": "flow_primary_gpm", "inlet": "inlet_C"}
ORIGIN = datetime(2017, 7, 31)
SHOE_FT = c.INTERMEDIATE["shoe_ft"]


def f(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return math.nan
    return out


def check_hashes():
    manifest = json.loads((PRED/"manifest.json").read_text())
    for name, sha in manifest["predictions_sha256"].items():
        if c.sha(PRED/name) != sha:
            raise SystemExit(f"{name} differs from the prediction manifest")
    for name in ("return_temperature.csv", "log_temperature.csv"):
        sha = (TARGETS/f"{name}.sha256").read_text().split()[0]
        if c.sha(TARGETS/name) != sha:
            raise SystemExit(f"{name} differs from its recorded hash")


def metrics(errors):
    e = np.asarray([x for x in errors if math.isfinite(x)], dtype=float)
    if not len(e):
        return dict(n=0, bias_C="", mae_C="", rmse_C="", within_2C="", within_5C="")
    return dict(n=len(e), bias_C=float(e.mean()), mae_C=float(np.abs(e).mean()),
                rmse_C=float(np.sqrt((e**2).mean())), within_2C=float((np.abs(e) <= 2).mean()),
                within_5C=float((np.abs(e) <= 5).mean()))


def table(rows, names, measured, set_name, part, flow, group_kind="all", group="all"):
    """One summary row per predictor on the same samples, with skill of v1.9.0."""
    out = []
    primary = metrics([r[f"{flow}_{PRIMARY}"]-r[measured] for r in rows])
    for name in names:
        key = name if name in (PERSISTENCE, "formation") else f"{flow}_{name}"
        row = dict(part=part, set=set_name, flow=flow, predictor=name, group_kind=group_kind, group=group)
        row |= metrics([r[key]-r[measured] for r in rows])
        row["skill_of_v1.9.0"] = ""
        if name != PRIMARY and row["n"] and row["rmse_C"] > 0:
            row["skill_of_v1.9.0"] = 1-primary["rmse_C"]/row["rmse_C"]
        out.append(row)
    return out


def quartiles(values):
    return [float(v) for v in np.percentile(values, [0, 25, 50, 75, 100])]


def label(value, edges):
    k = int(np.searchsorted(edges[1:4], value, side="left"))
    return f"Q{k+1} {edges[k]:.2f} to {edges[k+1]:.2f}"


# ---------- part A ----------

def part_a():
    conditions = c.read(c.HERE/"samples/conditions.csv")
    predictions = {r["sample_id"]: r for r in c.read(PRED/"predictions.csv")}
    targets = {r["sample_id"]: r for r in c.read(TARGETS/"return_temperature.csv")}
    windows = []
    for cond in conditions:
        p = predictions[cond["sample_id"]]
        w = dict(sample_id=cond["sample_id"], time=cond["time"], bha=cond["bha"], bit_ft=f(cond["bit_ft"]),
                 flow_primary_gpm=f(cond["flow_primary_gpm"]), flow_pason_gpm=f(cond["flow_pason_gpm"]),
                 inlet_C=f(cond["inlet_C"]), spp_psi=f(cond["spp_psi"]),
                 history_through_report_clock=cond["history_through_report_clock"], cond=cond)
        for flow in FLOWS:
            for name in MODELS:
                w[f"{flow}_{name}"] = f(p.get(f"{flow}_{name}_return_C"))
            for key in ("mass_flow_kg_s", "energy_limit_W", "rock_bound_W", "hydraulic_power_W"):
                w[f"{flow}_{key}"] = f(p.get(f"{flow}_{key}"))
        w["predicted"] = all(math.isfinite(w[f"{fl}_{n}"]) for fl in FLOWS for n in MODELS)
        t = targets.get(cond["sample_id"])
        if not w["predicted"]:
            w |= dict(status="not predicted", reasons=cond["input_status"], measured_C=math.nan)
        elif t is None:
            raise SystemExit(f"missing target for {cond['sample_id']}")
        else:
            if int(t["qualified_bins"]) != int(cond["qualified_bins"]) or t["unit_conversion"] != "(F-32)/1.8":
                raise SystemExit(f"target inconsistent with the declaration: {cond['sample_id']}")
            q, n = int(t["qualified_seconds"]), int(t["finite_seconds"])
            reasons = []
            if q == 0 or n < MIN_FINITE_FRACTION*q:
                reasons.append("R1")
            if n and t["min_C"] == t["max_C"]:
                reasons.append("R3")
            w |= dict(qualified_seconds=q, finite_seconds=n, finite_fraction=n/q if q else math.nan,
                      measured_C=f(t["mean_C"]) if n else math.nan,
                      status="excluded" if reasons else "scored", reasons="; ".join(reasons))
        windows.append(w)
    if set(targets) - {w["sample_id"] for w in windows if w["predicted"]}:
        raise SystemExit("target file has windows outside the forecast")
    # Persistence: the preceding scored window, in time order, with the same assembly.
    last = {}
    for w in sorted(windows, key=lambda w: w["time"]):
        w[PERSISTENCE] = last.get(w["bha"], math.nan) if w["status"] == "scored" else math.nan
        if w["status"] == "scored":
            last[w["bha"]] = w["measured_C"]
    # Part D on the scored windows.
    for w in windows:
        if w["status"] != "scored":
            continue
        fluid = pt.fluid_for(w["cond"])
        mean_T = .5*(w["inlet_C"]+w["measured_C"])
        cp = float(m1.fluid_props(np.array([mean_T]), np.array([m1.P_SURF]), fluids.with_default_rheology(fluid))[1][0])
        w["cp_J_kgK"] = cp
        for flow in FLOWS:
            q = w[f"{flow}_mass_flow_kg_s"]*cp*(w["measured_C"]-w["inlet_C"])
            w[f"{flow}_measured_heat_W"] = q
            limit = w[f"{flow}_energy_limit_W"]
            w[f"{flow}_energy_class"] = ("unclassified" if not math.isfinite(limit) else
                                         "inconsistent" if q > limit else "consistent")
        w["unit_check"] = w["measured_C"] < w["inlet_C"]-UNIT_MARGIN_C
    return windows


def summarise_a(windows):
    scored = [w for w in windows if w["status"] == "scored"]
    predicted = [w for w in windows if w["predicted"]]
    for kind, key in GROUPS.items():
        edges = quartiles([w[key] for w in predicted])
        for w in windows:
            w[f"{kind}_quartile"] = label(w[key], edges) if w["predicted"] else ""
    rows = []
    sets = {"all scored": scored,
            "energy-consistent": [w for w in scored if w["primary_energy_class"] == "consistent"]}
    for flow in FLOWS:
        for set_name, subset in sets.items():
            for w in subset:
                w["m"] = w["measured_C"]
            rows += table(subset, MODELS, "m", set_name, "A", flow)
            withp = [w for w in subset if math.isfinite(w[PERSISTENCE])]
            rows += table(withp, (*MODELS, PERSISTENCE), "m", f"{set_name}, with persistence", "A", flow)
            for bha in sorted({w["bha"] for w in subset}, key=lambda b: (len(b), b)):
                rows += table([w for w in subset if w["bha"] == bha], MODELS, "m", set_name, "A", flow, "assembly", bha)
            for kind in GROUPS:
                for lab in sorted({w[f"{kind}_quartile"] for w in predicted}):
                    rows += table([w for w in subset if w[f"{kind}_quartile"] == lab], MODELS, "m", set_name,
                                  "A", flow, kind, lab)
    return rows


def counts_a(windows):
    tally = Counter()
    tally["drilling windows"] = len(windows)
    tally["with converged predictions"] = sum(w["predicted"] for w in windows)
    tally["scored"] = sum(w["status"] == "scored" for w in windows)
    tally["excluded"] = sum(w["status"] == "excluded" for w in windows)
    for w in windows:
        if w["status"] == "excluded":
            for rule in w["reasons"].split("; "):
                tally[f"excluded by {rule}"] += 1
        if w["status"] == "not predicted":
            tally[f"not predicted: {w['reasons']}"] += 1
    scored = [w for w in windows if w["status"] == "scored"]
    tally["scored with persistence"] = sum(math.isfinite(w[PERSISTENCE]) for w in scored)
    tally["unit check, scored with return more than 5 °C below inlet (excludes nothing)"] = sum(w["unit_check"] for w in scored)
    for flow in FLOWS:
        for cls in ("consistent", "inconsistent", "unclassified"):
            tally[f"part D, {flow} flow: {cls}"] = sum(w[f"{flow}_energy_class"] == cls for w in scored)
    tally["scored with history through the 27-31 August report clock"] = sum(
        w["history_through_report_clock"] == "True" for w in scored)
    return [dict(count=k, windows=v) for k, v in tally.items()]


# ---------- part B ----------

def part_b():
    pred = {(r["log"], r["md_ft"], r["rig_time"]): r for r in c.read(PRED/"log-predictions.csv")}
    points = []
    for t in c.read(TARGETS/"log_temperature.csv"):
        p = pred[(t["log"], t["md_ft"], t["rig_time"])]
        row = dict(log=t["log"], kind="timed" if t["log"].startswith("TIME") else "depth", md_ft=f(t["md_ft"]),
                   elapsed_s=f(t["elapsed_s"]), rig_time=t["rig_time"], static_s=f(p["static_s"]),
                   cased=p["cased"] == "True", finite_readings=int(t["finite_readings"]),
                   measured_C=f(t["mean_C"]), formation=f(p["formation_C"]))
        for flow in FLOWS:
            for name in ("v1.9.0", "v1.7.0"):
                row[f"{flow}_{name}"] = f(p[f"{flow}_{name}_C"])
                row[f"{flow}_{name}_cased_reheated"] = f(p[f"{flow}_{name}_cased_reheated_C"])
            row[f"{flow}_analytical"] = f(p[f"{flow}_analytical_annulus_C"])
        row["status"] = "scored" if math.isfinite(row["measured_C"]) else "no valid reading"
        points.append(row)
    return points


def summarise_b(points):
    scored = [p for p in points if p["status"] == "scored"]
    groups = [("all depth logs", [p for p in scored if p["kind"] == "depth"]),
              ("all timed logs", [p for p in scored if p["kind"] == "timed"]),
              ("depth logs, cased", [p for p in scored if p["kind"] == "depth" and p["cased"]]),
              ("depth logs, open hole", [p for p in scored if p["kind"] == "depth" and not p["cased"]])]
    groups += [(log, [p for p in scored if p["log"] == log]) for log in sorted({p["log"] for p in scored})]
    rows = []
    for flow in FLOWS:
        for group, subset in groups:
            for p in subset:
                p["m"] = p["measured_C"]
            rows += table(subset, (*MODELS, "formation"), "m", "all scored", "B", flow, "log group", group)
            sens = [dict(p, **{f"{flow}_{PRIMARY}": p[f"{flow}_{PRIMARY}_cased_reheated"]}) for p in subset]
            row = table(sens, (PRIMARY,), "m", "cased sensitivity", "B", flow, "log group", group)[0]
            row["predictor"] = "v1.9.0 cased reheated"
            rows.append(row)
    return rows


# ---------- figures ----------

def figures(windows, points, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ink, mark, rule, second, third = "#2b2b2b", "#2a6fdb", "#9a9a9a", "#d9822b", "#3a9d5d"
    plt.rcParams.update({"font.size": 8, "axes.edgecolor": rule, "axes.labelcolor": ink, "xtick.color": ink,
                         "ytick.color": ink, "axes.grid": True, "grid.color": "#e3e3e3", "grid.linewidth": .6})
    written = []
    scored = [w for w in windows if w["status"] == "scored"]
    measured = np.array([w["measured_C"] for w in scored])
    lo, hi = float(measured.min())-2, float(measured.max())+2
    for flow in FLOWS:
        names = [*MODELS, PERSISTENCE]
        fig, axes = plt.subplots(1, len(names), figsize=(3*len(names), 3.2), sharex=True, sharey=True)
        for ax, name in zip(axes, names):
            key = name if name == PERSISTENCE else f"{flow}_{name}"
            pairs = [(w["measured_C"], w[key]) for w in scored if math.isfinite(w[key])]
            x, y = np.array(pairs).T
            ax.scatter(x, y, s=8, color=mark, alpha=.6, linewidths=0)
            ax.plot([lo, hi], [lo, hi], color=rule, linewidth=1)
            ax.set_title(f"{name} (n = {len(pairs)})", color=ink)
            ax.set_xlabel("Measured return, °C")
        axes[0].set_ylabel(f"Predicted return, °C ({flow} flow)")
        fig.tight_layout()
        name = "measured_vs_predicted.png" if flow == "primary" else "measured_vs_predicted_secondary_flow.png"
        fig.savefig(output/name, dpi=150)
        plt.close(fig)
        written.append(name)
    bhas = sorted({w["bha"] for w in scored}, key=lambda b: (len(b), b))
    for name, key, xlabel in (("depth", "bit_ft", "Bit depth, ft MD"),
                              ("time", "time", "Days from 31 July 2017, rig time"),
                              ("flow", "flow_primary_gpm", "Primary flow, US gal/min")):
        columns = 5
        nrows = max(1, math.ceil(len(bhas)/columns))
        fig, axes = plt.subplots(nrows, columns, figsize=(3*columns, 2.4*nrows), sharey=True, squeeze=False)
        for ax in axes.flat[len(bhas):]:
            ax.set_visible(False)
        for ax, bha in zip(axes.flat, bhas):
            subset = [w for w in scored if w["bha"] == bha]
            x = [(datetime.fromisoformat(w["time"])-ORIGIN).total_seconds()/86400 if key == "time" else w[key]
                 for w in subset]
            ax.axhline(0, color=rule, linewidth=1)
            ax.scatter(x, [w[f"primary_{PRIMARY}"]-w["measured_C"] for w in subset], s=8, color=mark, linewidths=0)
            ax.set_title(f"Assembly {bha} (n = {len(subset)})", color=ink)
            ax.set_xlabel(xlabel)
        for ax in axes[:, 0]:
            ax.set_ylabel("v1.9.0 minus measured, °C")
        fig.tight_layout()
        fig.savefig(output/f"residual_vs_{name}.png", dpi=150)
        plt.close(fig)
        written.append(f"residual_vs_{name}.png")
    # Part D: measured heat gain against the declared limit.
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    for cls, colour in (("consistent", mark), ("inconsistent", second)):
        sub = [w for w in scored if w["primary_energy_class"] == cls]
        ax.scatter([w["primary_energy_limit_W"]/1e6 for w in sub], [w["primary_measured_heat_W"]/1e6 for w in sub],
                   s=8, color=colour, linewidths=0, label=f"{cls} (n = {len(sub)})")
    top = max(max(w["primary_energy_limit_W"] for w in scored), max(w["primary_measured_heat_W"] for w in scored))/1e6
    ax.plot([0, top], [0, top], color=rule, linewidth=1)
    ax.set_xlabel("Declared limit, MW (primary flow)")
    ax.set_ylabel("Measured heat gain, MW")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output/"energy_consistency.png", dpi=150)
    plt.close(fig)
    written.append("energy_consistency.png")
    # Part B: forecast and measured profiles for each log.
    for kind, logs, xkey, xlabel in (("depth", ("RUN1", "RUN2", "RUN3", "RUN4"), "md_ft", "Measured depth, ft"),
                                     ("timed", ("TIME1", "TIME2", "TIME3", "TIME4"), "elapsed_s", "Seconds at 6,798 ft")):
        fig, axes = plt.subplots(1, 4, figsize=(12, 4.2 if kind == "depth" else 3.2), sharey=kind == "depth", squeeze=False)
        for ax, log in zip(axes.flat, logs):
            sub = sorted([p for p in points if p["log"] == log], key=lambda p: p[xkey])
            x = [p[xkey] for p in sub]
            series = (("measured", "measured_C", ink, "-"), ("v1.9.0", "primary_v1.9.0", mark, "-"),
                      ("v1.7.0", "primary_v1.7.0", second, "--"), ("analytical, circulating", "primary_analytical", third, ":"),
                      ("PT118 formation", "formation", rule, "-"))
            for lab, key, colour, style in series:
                y = [p[key] for p in sub]
                if kind == "depth":
                    ax.plot(y, x, color=colour, linestyle=style, linewidth=1, label=lab)
                else:
                    ax.plot(x, y, color=colour, linestyle=style, linewidth=1, label=lab)
            ax.set_title(f"{log} (n = {sum(p['status'] == 'scored' for p in sub)})", color=ink)
            if kind == "depth":
                ax.set_xlabel("Temperature, °C")
                ax.axhline(SHOE_FT, color=rule, linewidth=.6, linestyle=":")
            else:
                ax.set_xlabel(xlabel)
        if kind == "depth":
            axes[0, 0].invert_yaxis()
            axes[0, 0].set_ylabel(xlabel)
        else:
            axes[0, 0].set_ylabel("Temperature, °C")
        axes[0, -1].legend(frameon=False, fontsize=7)
        fig.tight_layout()
        fig.savefig(output/f"log_profiles_{kind}.png", dpi=150)
        plt.close(fig)
        written.append(f"log_profiles_{kind}.png")
    return written


def write(path, rows, fields=None):
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    check_hashes()
    args.output.mkdir(parents=True, exist_ok=True)
    windows = part_a()
    summary = summarise_a(windows)
    points = part_b()
    summary += summarise_b(points)
    write(args.output/"summary.csv", summary, ["part", "set", "flow", "predictor", "group_kind", "group", "n", "bias_C",
                                               "mae_C", "rmse_C", "within_2C", "within_5C", "skill_of_v1.9.0"])
    wfields = ["sample_id", "time", "bha", "bit_ft", "flow_primary_gpm", "flow_pason_gpm", "inlet_C", "spp_psi",
               "qualified_seconds", "finite_seconds", "finite_fraction", "status", "reasons", "measured_C",
               *[f"{fl}_{n}" for fl in FLOWS for n in MODELS], PERSISTENCE, "unit_check", "cp_J_kgK",
               *[f"{fl}_{k}" for fl in FLOWS for k in ("mass_flow_kg_s", "measured_heat_W", "rock_bound_W",
                                                        "hydraulic_power_W", "energy_limit_W", "energy_class")],
               "depth_quartile", "flow_quartile", "inlet_quartile", "history_through_report_clock"]
    write(args.output/"windows.csv", windows, wfields)
    write(args.output/"log_points.csv", points, [k for k in points[0] if k != "m"])
    tally = counts_a(windows)
    tally += [dict(count=f"part B {k}", windows=v) for k, v in
              Counter(p["status"] for p in points).items()]
    write(args.output/"counts.csv", tally)
    written = figures(windows, points, args.output)
    sources = dict(predictions=json.loads((PRED/"manifest.json").read_text())["predictions_sha256"],
                   targets={n: c.sha(TARGETS/n) for n in ("return_temperature.csv", "log_temperature.csv")},
                   scorer_sha256=c.sha(Path(__file__)), figures=written)
    (args.output/"sources.json").write_text(json.dumps(sources, indent=2)+"\n", encoding="utf-8", newline="\n")
    for row in tally:
        print(row["count"], row["windows"])


if __name__ == "__main__":
    main()
