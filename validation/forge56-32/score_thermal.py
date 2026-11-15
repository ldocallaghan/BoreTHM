"""Score the 56-32 return temperature forecast against measured Temp OUT.

usage: score_thermal.py TARGETS OUTPUT

TARGETS is the measured return file described in the scoring protocol.
OUTPUT receives summary.csv, windows.csv, counts.csv, sources.json and,
when matplotlib is installed, the figures. The predictions are read from
predictions-v1.8.0 and must match the hash recorded in its manifest.
"""
import argparse
import csv
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PREDICTIONS = HERE/"predictions-v1.8.0"
PREDICTORS = {"v1.8.0": "v1.8.0_return_C", "v1.7.0": "v1.7.0_return_C",
              "analytical": "analytical_return_C"}
PRIMARY = "v1.8.0"
PERSISTENCE = "persistence"
MIN_FINITE_FRACTION = .8
RANGE_C = (0., 120.)
UNIT_CONVERSION = "(F-32)/1.8"
TARGET_FIELDS = ("sample_id", "qualified_bins", "qualified_seconds", "finite_seconds",
                 "mean_C", "min_C", "max_C", "unit_conversion")
GROUPS = {"depth": "bit_ft", "flow": "flow_gpm", "inlet": "inlet_C"}
ORIGIN = datetime(2021, 2, 8)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def drilling_windows(directory=PREDICTIONS):
    """Drilling rows of the committed forecast, joined to their inputs."""
    manifest = json.loads((directory/"manifest.json").read_text(encoding="utf-8"))
    if sha256(directory/"predictions.csv") != manifest["predictions_sha256"]:
        raise ValueError("predictions.csv does not match predictions_sha256 in the manifest")
    conditions = {r["sample_id"]: r for r in read_csv(directory/"conditions.csv")}
    windows = []
    for row in read_csv(directory/"predictions.csv"):
        if row["kind"] != "drilling":
            continue
        inputs = conditions[row["sample_id"]]
        window = dict(sample_id=row["sample_id"], time=inputs["time"], bha=row["bha"],
                      input_status=row["input_status"],
                      qualified_bins=int(inputs["qualified_bins"]),
                      return_available_rows=int(inputs["return_available_rows"]))
        for key in GROUPS.values():
            window[key] = float(inputs[key]) if finite(inputs[key]) else math.nan
        predicted = all(finite(row[column]) for column in PREDICTORS.values())
        window["predicted"] = row["input_status"] == "complete" and predicted and all(
            row[f"{name}_circulation_status"] == "converged" for name in ("v1.8.0", "v1.7.0"))
        for name, column in PREDICTORS.items():
            window[name] = float(row[column]) if finite(row[column]) else math.nan
        windows.append(window)
    return windows


def read_targets(path):
    rows = read_csv(path)
    if not rows or tuple(rows[0]) != TARGET_FIELDS:
        raise ValueError(f"target columns must be {TARGET_FIELDS}")
    targets = {}
    for row in rows:
        if row["sample_id"] in targets:
            raise ValueError(f"duplicate target row {row['sample_id']}")
        if row["unit_conversion"] != UNIT_CONVERSION:
            raise ValueError(f"unexpected unit conversion for {row['sample_id']}")
        targets[row["sample_id"]] = dict(
            qualified_bins=int(row["qualified_bins"]), qualified_seconds=int(row["qualified_seconds"]),
            finite_seconds=int(row["finite_seconds"]),
            **{k: float(row[k]) if finite(row[k]) else math.nan for k in ("mean_C", "min_C", "max_C")})
    return targets


def exclusion_rules(target):
    """Return every protocol rule that excludes a window with a target row."""
    rules = []
    seconds = target["qualified_seconds"]
    if seconds <= 0 or target["finite_seconds"]/seconds < MIN_FINITE_FRACTION:
        rules.append("R1 finite seconds below 80 % of qualified seconds")
    if target["finite_seconds"] > 0:
        if not (RANGE_C[0] <= target["min_C"] and target["max_C"] <= RANGE_C[1]):
            rules.append("R2 value outside 0 to 120 °C")
        if target["min_C"] == target["max_C"]:
            rules.append("R3 one constant value across the window")
    return rules


def classify(windows, targets):
    """Attach the measured value, status and reasons to each window."""
    predicted = {w["sample_id"] for w in windows if w["predicted"]}
    if set(targets) != predicted:
        missing, extra = sorted(predicted-set(targets)), sorted(set(targets)-predicted)
        raise ValueError(f"target rows must cover the predicted windows only; "
                         f"missing {missing[:5]}, extra {extra[:5]}")
    for w in windows:
        w.update(qualified_seconds="", finite_seconds="", finite_fraction="", measured_C=math.nan)
        if not w["predicted"]:
            w.update(status="not predicted", reasons=w["input_status"] or "no converged prediction")
            continue
        target = targets[w["sample_id"]]
        if target["qualified_bins"] != w["qualified_bins"]:
            raise ValueError(f"{w['sample_id']}: {target['qualified_bins']} qualified bins in the "
                             f"targets against {w['qualified_bins']} in the forecast inputs")
        seconds = target["qualified_seconds"]
        w.update(qualified_seconds=seconds, finite_seconds=target["finite_seconds"],
                 finite_fraction=target["finite_seconds"]/seconds if seconds else math.nan)
        rules = exclusion_rules(target)
        if rules:
            w.update(status="excluded", reasons="; ".join(rules))
        else:
            w.update(status="scored", reasons="", measured_C=target["mean_C"])
    previous = {}
    for w in sorted(windows, key=lambda w: w["time"]):
        w[PERSISTENCE] = math.nan
        if w["status"] != "scored":
            continue
        w[PERSISTENCE] = previous.get(w["bha"], math.nan)
        previous[w["bha"]] = w["measured_C"]
    return windows


def metrics(errors):
    e = np.asarray(errors, dtype=float)
    if not len(e):
        return dict(n=0, bias_C="", mae_C="", rmse_C="", within_2C="", within_5C="")
    return dict(n=len(e), bias_C=float(e.mean()), mae_C=float(np.abs(e).mean()),
                rmse_C=float(np.sqrt((e**2).mean())), within_2C=float((np.abs(e) <= 2).mean()),
                within_5C=float((np.abs(e) <= 5).mean()))


def quartile_edges(windows, key):
    values = np.array([w[key] for w in windows if w["predicted"] and math.isfinite(w[key])])
    return [float(v) for v in np.percentile(values, [0, 25, 50, 75, 100])]


def group_label(value, edges):
    """Quartile of an input value; each quartile includes its upper edge."""
    if not math.isfinite(value):
        return ""
    k = int(np.searchsorted(edges[1:4], value, side="left"))
    return f"Q{k+1} {edges[k]:.2f} to {edges[k+1]:.2f}"


def summarise(windows):
    scored = [w for w in windows if w["status"] == "scored"]
    rows = []

    def add(subset, set_name, names, group_kind="all", group="all"):
        primary = metrics([w[PRIMARY]-w["measured_C"] for w in subset])
        for name in names:
            row = dict(set=set_name, predictor=name, group_kind=group_kind, group=group)
            row |= metrics([w[name]-w["measured_C"] for w in subset])
            row["skill_of_v1.8.0"] = ""
            if name != PRIMARY and row["n"] and row["rmse_C"] > 0:
                row["skill_of_v1.8.0"] = 1-primary["rmse_C"]/row["rmse_C"]
            rows.append(row)

    add(scored, "all scored", list(PREDICTORS))
    with_persistence = [w for w in scored if math.isfinite(w[PERSISTENCE])]
    add(with_persistence, "with persistence", [*PREDICTORS, PERSISTENCE])
    for bha in sorted({w["bha"] for w in scored}, key=lambda b: (len(b), b)):
        add([w for w in scored if w["bha"] == bha], "all scored", [PRIMARY], "assembly", bha)
    for kind, key in GROUPS.items():
        edges = quartile_edges(windows, key)
        for w in windows:
            w[f"{kind}_quartile"] = group_label(w[key], edges) if w["predicted"] else ""
        for label in sorted({w[f"{kind}_quartile"] for w in windows if w["predicted"]}):
            add([w for w in scored if w[f"{kind}_quartile"] == label], "all scored", [PRIMARY], kind, label)
    return rows


def counts(windows):
    tally = Counter()
    tally["drilling windows"] = len(windows)
    tally["with converged predictions"] = sum(w["predicted"] for w in windows)
    tally["with return availability in the window"] = sum(w["return_available_rows"] > 0 for w in windows)
    tally["with finite qualified seconds"] = sum(
        bool(w["finite_seconds"]) for w in windows if w["predicted"])
    tally["scored"] = sum(w["status"] == "scored" for w in windows)
    tally["excluded"] = sum(w["status"] == "excluded" for w in windows)
    for w in windows:
        if w["status"] == "excluded":
            for rule in w["reasons"].split("; "):
                tally[f"excluded by {rule}"] += 1
        if w["status"] == "not predicted":
            tally[f"not predicted: {w['reasons']}"] += 1
    tally["scored with persistence"] = sum(
        w["status"] == "scored" and math.isfinite(w[PERSISTENCE]) for w in windows)
    return [dict(count=k, windows=v) for k, v in tally.items()]


def figures(windows, output):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    scored = [w for w in windows if w["status"] == "scored"]
    ink, mark, rule = "#2b2b2b", "#2a6fdb", "#9a9a9a"
    plt.rcParams.update({"font.size": 8, "axes.edgecolor": rule, "axes.labelcolor": ink,
                         "xtick.color": ink, "ytick.color": ink, "axes.grid": True,
                         "grid.color": "#e3e3e3", "grid.linewidth": .6})
    written = []

    names = [*PREDICTORS, PERSISTENCE]
    fig, axes = plt.subplots(1, len(names), figsize=(3*len(names), 3.2), sharex=True, sharey=True)
    measured = np.array([w["measured_C"] for w in scored])
    lo, hi = (float(np.nanmin(measured))-2, float(np.nanmax(measured))+2) if len(measured) else (0, 1)
    for ax, name in zip(axes, names):
        pairs = [(w["measured_C"], w[name]) for w in scored if math.isfinite(w[name])]
        if pairs:
            x, y = np.array(pairs).T
            ax.scatter(x, y, s=10, color=mark, alpha=.7, linewidths=0)
        ax.plot([lo, hi], [lo, hi], color=rule, linewidth=1)
        ax.set_title(f"{name} (n = {len(pairs)})", color=ink)
        ax.set_xlabel("Measured return, °C")
    axes[0].set_ylabel("Predicted return, °C")
    fig.tight_layout()
    fig.savefig(output/"measured_vs_predicted.png", dpi=150)
    plt.close(fig)
    written.append("measured_vs_predicted.png")

    bhas = sorted({w["bha"] for w in scored}, key=lambda b: (len(b), b))
    for name, key, label in (("depth", "bit_ft", "Bit depth, ft MD"),
                             ("time", "time", "Days from 8 February 2021, local rig time"),
                             ("flow", "flow_gpm", "Flow, US gal/min")):
        columns = 5
        rows = max(1, math.ceil(len(bhas)/columns))
        fig, axes = plt.subplots(rows, columns, figsize=(3*columns, 2.4*rows), sharey=True, squeeze=False)
        for ax in axes.flat[len(bhas):]:
            ax.set_visible(False)
        for ax, bha in zip(axes.flat, bhas):
            subset = [w for w in scored if w["bha"] == bha]
            x = [(datetime.fromisoformat(w["time"])-ORIGIN).total_seconds()/86400 if key == "time"
                 else w[key] for w in subset]
            ax.axhline(0, color=rule, linewidth=1)
            ax.scatter(x, [w[PRIMARY]-w["measured_C"] for w in subset], s=10, color=mark, linewidths=0)
            ax.set_title(f"Assembly {bha} (n = {len(subset)})", color=ink)
            ax.set_xlabel(label)
        for ax in axes[:, 0]:
            ax.set_ylabel("v1.8.0 minus measured, °C")
        fig.tight_layout()
        fig.savefig(output/f"residual_vs_{name}.png", dpi=150)
        plt.close(fig)
        written.append(f"residual_vs_{name}.png")
    return written


WINDOW_FIELDS = ["sample_id", "time", "bha", "bit_ft", "flow_gpm", "inlet_C", "qualified_bins",
                 "qualified_seconds", "finite_seconds", "finite_fraction", "status", "reasons",
                 "measured_C", *PREDICTORS, PERSISTENCE, *[f"{n}_minus_measured_C" for n in PREDICTORS],
                 f"{PERSISTENCE}_minus_measured_C", "depth_quartile", "flow_quartile", "inlet_quartile"]
SUMMARY_FIELDS = ["set", "predictor", "group_kind", "group", "n", "bias_C", "mae_C", "rmse_C",
                  "within_2C", "within_5C", "skill_of_v1.8.0"]


def score(targets_path, output, predictions=PREDICTIONS):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    windows = classify(drilling_windows(predictions), read_targets(targets_path))
    summary = summarise(windows)
    table = counts(windows)
    drawn = figures(windows, output)
    rows = []
    for w in sorted(windows, key=lambda w: w["sample_id"]):
        row = dict(w)
        for name in [*PREDICTORS, PERSISTENCE]:
            row[f"{name}_minus_measured_C"] = w[name]-w["measured_C"]
        rows.append({k: "" if isinstance(v, float) and not math.isfinite(v) else v
                     for k, v in row.items()})
    write_csv(output/"windows.csv", rows, WINDOW_FIELDS)
    write_csv(output/"summary.csv", summary, SUMMARY_FIELDS)
    write_csv(output/"counts.csv", table, ["count", "windows"])
    sources = dict(predictions_sha256=sha256(predictions/"predictions.csv"),
                   targets_sha256=sha256(targets_path), scorer_sha256=sha256(__file__),
                   figures=drawn)
    (output/"sources.json").write_text(json.dumps(sources, indent=2)+"\n", encoding="utf-8", newline="\n")
    return summary, table


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("targets", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    _, table = score(args.targets, args.output)
    for row in table:
        print(f"{row['windows']:5d}  {row['count']}")


if __name__ == "__main__":
    main()
