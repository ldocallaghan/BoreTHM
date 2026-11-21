"""Score the 78B-32 thermal forecast as declared in ../thermal_protocol.md.

usage: python score_thermal.py [--root WELL_DIR] OUTPUT

Reads the committed samples, predictions and targets. Refuses any
prediction or target file whose SHA-256 differs from its manifest or
recorded hash. Applies R1 to R3 and part E as declared and writes the
scores, counts and figures to OUTPUT.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MODELS = ("v1.9.0", "v1.7.0", "analytical")
PRIMARY = "v1.9.0"
PERSISTENCE = "persistence"
MIN_VALID_SHARE = 0.8
RANGE_DOWNHOLE_C = (0.0, 250.0)
RANGE_RETURN_C = (0.0, 120.0)
RANGE_SANVEAN_C = (0.0, 250.0)
BOUND_BELOW_INLET_C = 3.0
BOUND_ABOVE_FORMATION_C = 10.0
ALIGN_MIN_PUMP_AGREEMENT = 0.95
ALIGN_MAX_HOLE_DIFF_FT = 5.0
GROUPS = {"depth": "bit_ft", "flow": "flow_gpm", "inlet": "inlet_C"}


def f(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write(path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fields, lineterminator="\n")
        w.writeheader()
        w.writerows({k: ("" if isinstance(v, float) and not math.isfinite(v) else v) for k, v in r.items()}
                    for r in rows)


def check_hashes(root):
    pred = root/"predictions-v1.9.0"
    manifest = json.loads((pred/"manifest.json").read_text())
    for name, digest in manifest["predictions_sha256"].items():
        if sha(pred/name) != digest:
            raise SystemExit(f"{name} differs from the prediction manifest")
    for name in ("downhole.csv", "sanvean.csv", "sanvean-alignment.json"):
        digest = (root/"targets"/f"{name}.sha256").read_text().split()[0]
        if sha(root/"targets"/name) != digest:
            raise SystemExit(f"{name} differs from its recorded hash")


def to_c(recorded, fahrenheit):
    x = f(recorded)
    if not math.isfinite(x) or x == -999.25:
        return math.nan
    return (x - 32.0) / 1.8 if fahrenheit else x


def valid(x, bounds):
    return math.isfinite(x) and bounds[0] < x <= bounds[1]


def metrics(errors):
    e = np.asarray([x for x in errors if math.isfinite(x)], dtype=float)
    if not len(e):
        return dict(n=0, bias_C="", mae_C="", rmse_C="", within_2C="", within_5C="")
    return dict(n=len(e), bias_C=float(e.mean()), mae_C=float(np.abs(e).mean()),
                rmse_C=float(np.sqrt((e**2).mean())), within_2C=float((np.abs(e) <= 2).mean()),
                within_5C=float((np.abs(e) <= 5).mean()))


def table(rows, part, set_name, names=MODELS, key="pred", group_kind="all", group="all"):
    """One row per predictor on the same samples, with the skill of the primary predictor."""
    out = []
    prim = metrics([r[f"{key}_{PRIMARY}"] - r["measured_C"] for r in rows])
    for name in names:
        col = name if name == PERSISTENCE else f"{key}_{name}"
        row = dict(part=part, set=set_name, predictor=name, group_kind=group_kind, group=group)
        row |= metrics([r[col] - r["measured_C"] for r in rows])
        row["skill_of_v1.9.0"] = ""
        if name != PRIMARY and row["n"] and row["rmse_C"] > 0:
            row["skill_of_v1.9.0"] = 1 - prim["rmse_C"] / row["rmse_C"]
        out.append(row)
    return out


def quartile_labels(rows, key, predicted):
    edges = [float(v) for v in np.percentile([r[key] for r in predicted], [0, 25, 50, 75, 100])]
    for r in rows:
        k = int(np.searchsorted(edges[1:4], r[key], side="left"))
        r[f"{key}_quartile"] = f"Q{k+1} {edges[k]:.2f} to {edges[k+1]:.2f}"


# ---------- per-window measurement ----------

def readings(targets):
    by = {}
    for r in targets:
        by.setdefault((r["sample_id"], r["channel"]), []).append(r)
    return by


def measure_fresh(rows, qualified, bounds):
    """Primary rule: mean of the fresh valid readings; R1 on valid bins; R3 needs a fresh reading."""
    vals = [(to_c(r["recorded"], True), r["fresh"] == "1") for r in rows]
    n_valid = sum(valid(x, bounds) for x, _ in vals)
    fresh = [x for x, fr in vals if fr and valid(x, bounds)]
    reasons = []
    if qualified == 0 or n_valid < MIN_VALID_SHARE * qualified:
        reasons.append("R1")
    if not fresh:
        reasons.append("R3")
    return dict(valid_bins=n_valid, fresh_readings=len(fresh),
                measured_C=float(np.mean(fresh)) if fresh else math.nan, reasons=reasons)


def measure_mean(rows, qualified, bounds, fahrenheit=True):
    """56-32 rule: mean over the valid readings of the qualified bins; R1; R3 on a constant record."""
    vals = [to_c(r["recorded"], fahrenheit) for r in rows]
    good = [x for x in vals if valid(x, bounds)]
    reasons = []
    if qualified == 0 or len(good) < MIN_VALID_SHARE * qualified:
        reasons.append("R1")
    if good and min(good) == max(good):
        reasons.append("R3")
    return dict(valid_bins=len(good), measured_C=float(np.mean(good)) if good else math.nan, reasons=reasons)


def base_rows(windows, predictions, flag, pred_key):
    rows = []
    for w in windows:
        if w.get(flag) != "True":
            continue
        p = predictions.get(w["sample_id"], {})
        r = dict(sample_id=w["sample_id"], centre=w["centre"], bha=w["bha"], bit_ft=f(w["bit_ft"]),
                 flow_gpm=f(w["flow_gpm"]), inlet_C=f(w["inlet_C"]), inlet_source=w["inlet_source"],
                 inlet_flag=w["inlet_flag"], formation_at_sensor_C=f(w.get("formation_at_sensor_C")),
                 sensor_tvd_ft=f(w.get("sensor_tvd_ft")), qualified_bins=int(w["qualified_bins"]))
        for m in MODELS:
            r[f"pred_{m}"] = f(p.get(f"{m}_{pred_key}"))
        r["predicted"] = all(math.isfinite(r[f"pred_{m}"]) for m in MODELS)
        rows.append(r)
    return rows


def score_downhole(rows, by, channel, rule):
    for r in rows:
        if not r["predicted"]:
            r |= dict(status="not predicted", reasons="", measured_C=math.nan)
            continue
        got = by.get((r["sample_id"], channel), [])
        m = (measure_fresh(got, r["qualified_bins"], RANGE_DOWNHOLE_C) if rule == "fresh"
             else measure_mean(got, r["qualified_bins"], RANGE_DOWNHOLE_C))
        r |= dict(valid_bins=m["valid_bins"], fresh_readings=m.get("fresh_readings", ""),
                  measured_C=m["measured_C"], status="excluded" if m["reasons"] else "scored",
                  reasons="; ".join(m["reasons"]))
    return rows


def persistence(rows):
    last = {}
    for r in sorted(rows, key=lambda r: r["centre"]):
        r[PERSISTENCE] = last.get(r["bha"], math.nan) if r["status"] == "scored" else math.nan
        if r["status"] == "scored":
            last[r["bha"]] = r["measured_C"]


def bounds_check(rows):
    """Part E: flag a scored window more than 3 C below its inlet or 10 C above the formation at the sensor."""
    for r in rows:
        if r["status"] != "scored":
            r["part_e_flag"] = ""
            continue
        low = r["measured_C"] < r["inlet_C"] - BOUND_BELOW_INLET_C
        high = r["measured_C"] > r["formation_at_sensor_C"] + BOUND_ABOVE_FORMATION_C
        r["part_e_flag"] = "below inlet" if low else "above formation" if high else "none"


def summarise(rows, part, grouped=True, extra_sets=None):
    scored = [r for r in rows if r["status"] == "scored"]
    predicted = [r for r in rows if r["predicted"]]
    out = []
    sets = {"all scored": scored, "excluding inlet-flagged days": [r for r in scored if r["inlet_flag"] != "True"],
            "Pason inlet only": [r for r in scored if r["inlet_source"] == "pason"]}
    sets |= extra_sets or {}
    if grouped and predicted:
        for key in GROUPS.values():
            quartile_labels(rows, key, predicted)
    for set_name, subset in sets.items():
        out += table(subset, part, set_name)
        withp = [r for r in subset if math.isfinite(r.get(PERSISTENCE, math.nan))]
        if withp:
            out += table(withp, part, f"{set_name}, with persistence", (*MODELS, PERSISTENCE))
        for bha in sorted({r["bha"] for r in subset}, key=lambda b: (len(b), b)):
            out += table([r for r in subset if r["bha"] == bha], part, set_name, group_kind="assembly", group=bha)
        if grouped:
            for kind, key in GROUPS.items():
                for lab in sorted({r[f"{key}_quartile"] for r in predicted}):
                    out += table([r for r in subset if r[f"{key}_quartile"] == lab], part, set_name,
                                 group_kind=kind, group=lab)
    return out


def count(rows, part):
    t = Counter()
    t["windows"] = len(rows)
    t["with converged predictions"] = sum(r["predicted"] for r in rows)
    for r in rows:
        t[r["status"]] += 1
        if r["status"] == "excluded":
            for rule in r["reasons"].split("; "):
                t[f"excluded by {rule}"] += 1
        if r.get("part_e_flag") not in (None, "", "none"):
            t[f"part E flag: {r['part_e_flag']}"] += 1
    t["scored on inlet-flagged days"] = sum(r["status"] == "scored" and r["inlet_flag"] == "True" for r in rows)
    t["scored with report inlet"] = sum(r["status"] == "scored" and r["inlet_source"] == "report" for r in rows)
    return [dict(part=part, count=k, windows=v) for k, v in t.items()]


# ---------- Sanvean ----------

def score_sanvean(windows, predictions, sanvean, alignment):
    ok_files = {}
    for name, a in alignment.items():
        accept = (a.get("offset_s") is not None and (a.get("pump_agreement") or 0) >= ALIGN_MIN_PUMP_AGREEMENT
                  and a.get("hole_depth_median_abs_diff_ft") is not None
                  and a["hole_depth_median_abs_diff_ft"] <= ALIGN_MAX_HOLE_DIFF_FT)
        ok_files[a["assembly"]] = accept
    by = {}
    for r in sanvean:
        by.setdefault((r["sample_id"], r["position"]), []).append(r)
    rows = []
    for position in ("lower", "upper"):
        for r in base_rows(windows, predictions, "part_b_sanvean", f"sanvean_{position}_C"):
            r["position"] = position
            got = by.get((r["sample_id"], position), [])
            if not r["predicted"]:
                r |= dict(status="not predicted", reasons="", measured_C=math.nan)
            elif not ok_files.get(r["bha"], False):
                r |= dict(status="excluded", reasons="clock alignment not accepted", measured_C=math.nan)
            elif not got:
                r |= dict(status="outside Sanvean record", reasons="", measured_C=math.nan)
            else:
                bins = {}
                for g in got:
                    x = to_c(g["recorded_C"], False)
                    bins.setdefault(g["aligned_time"][:18], []).append(x)
                good = [x for xs in bins.values() for x in xs if valid(x, RANGE_SANVEAN_C)]
                bins_with_valid = sum(any(valid(x, RANGE_SANVEAN_C) for x in xs) for xs in bins.values())
                reasons = []
                if bins_with_valid < MIN_VALID_SHARE * r["qualified_bins"]:
                    reasons.append("R1")
                if good and min(good) == max(good):
                    reasons.append("R3")
                r |= dict(valid_bins=bins_with_valid, measured_C=float(np.mean(good)) if good else math.nan,
                          status="excluded" if reasons else "scored", reasons="; ".join(reasons))
            rows.append(r)
    return rows, ok_files


# ---------- figures ----------

def figure(rows, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    scored = [r for r in rows if r["status"] == "scored"]
    if not scored:
        return
    fig, ax = plt.subplots(figsize=(6, 7))
    for bha in sorted({r["bha"] for r in scored}, key=lambda b: (len(b), b)):
        sub = [r for r in scored if r["bha"] == bha]
        ax.scatter([r["measured_C"] for r in sub], [r["bit_ft"] for r in sub], s=14, label=f"BHA {bha} measured")
        ax.scatter([r[f"pred_{PRIMARY}"] for r in sub], [r["bit_ft"] for r in sub], s=14, marker="x",
                   label=f"BHA {bha} v1.9.0")
    ax.invert_yaxis()
    ax.set_xlabel("Temperature (°C)")
    ax.set_ylabel("Bit depth (ft)")
    ax.set_title(title)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output", type=Path)
    ap.add_argument("--root", type=Path, default=HERE.parent)
    args = ap.parse_args()
    root = args.root
    check_hashes(root)
    args.output.mkdir(parents=True, exist_ok=True)
    windows = read(root/"thermal"/"samples"/"windows.csv")
    predictions = {r["sample_id"]: r for r in read(root/"predictions-v1.9.0"/"predictions.csv")}
    by = readings(read(root/"targets"/"downhole.csv"))
    alignment = json.loads((root/"targets"/"sanvean-alignment.json").read_text())

    summary, counts = [], []
    # Part A, primary (fresh readings) and the declared 56-32 secondary.
    a = score_downhole(base_rows(windows, predictions, "part_a", "sensor_C"), by, "mwd_temp", "fresh")
    persistence(a)
    bounds_check(a)
    summary += summarise(a, "A", extra_sets={"part E unflagged": [r for r in a if r["status"] == "scored"
                                                                  and r["part_e_flag"] == "none"]})
    counts += count(a, "A")
    write(args.output/"part-a-windows.csv", a)
    a2 = score_downhole(base_rows(windows, predictions, "part_a", "sensor_C"), by, "mwd_temp", "mean")
    summary += summarise(a2, "A, 56-32 mean")
    counts += count(a2, "A, 56-32 mean")
    write(args.output/"part-a-mean-windows.csv", a2)
    # Part B: the other downhole channel, the return temperature and the Sanvean sensors.
    b1 = score_downhole(base_rows(windows, predictions, "part_b_eye", "sensor_C"), by, "eye_temp", "fresh")
    summary += summarise(b1, "B, EYE TEMP", grouped=False)
    counts += count(b1, "B, EYE TEMP")
    write(args.output/"part-b-eye-windows.csv", b1)
    b2 = base_rows(windows, predictions, "part_b_return", "return_C")
    for r in b2:
        if not r["predicted"]:
            r |= dict(status="not predicted", reasons="", measured_C=math.nan)
            continue
        m = measure_mean(by.get((r["sample_id"], "temp_out"), []), r["qualified_bins"], RANGE_RETURN_C)
        r |= dict(valid_bins=m["valid_bins"], measured_C=m["measured_C"],
                  status="excluded" if m["reasons"] else "scored", reasons="; ".join(m["reasons"]))
    summary += summarise(b2, "B, TEMP OUT", grouped=False)
    counts += count(b2, "B, TEMP OUT")
    write(args.output/"part-b-return-windows.csv", b2)
    b3, accepted = score_sanvean(windows, predictions, read(root/"targets"/"sanvean.csv"), alignment)
    for position in ("lower", "upper"):
        sub = [r for r in b3 if r["position"] == position]
        summary += summarise(sub, f"B, Sanvean {position}", grouped=False)
        counts += count(sub, f"B, Sanvean {position}")
    counts += [dict(part="B, Sanvean", count=f"clock alignment accepted, BHA {k}", windows=v) for k, v in accepted.items()]
    write(args.output/"part-b-sanvean-windows.csv", b3)

    write(args.output/"summary.csv", summary)
    write(args.output/"counts.csv", counts)
    figure(a, args.output/"part-a-depth.png", "78B-32 MWD temperature, part A")
    figure(b1, args.output/"part-b-eye-depth.png", "78B-32 EYE temperature, part B")
    figure(b2, args.output/"part-b-return-depth.png", "78B-32 return temperature, part B")
    head = [r for r in summary if r["part"] == "A" and r["set"] == "all scored" and r["group_kind"] == "all"]
    print(json.dumps(dict(counts=[c for c in counts if c["part"] == "A"], headline=head), indent=1, default=str))


if __name__ == "__main__":
    main()
