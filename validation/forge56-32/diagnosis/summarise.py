"""Apply the post-hoc classification rule and summarise the diagnosis by assembly.

usage: summarise.py

Reads energy_balance.csv, sensitivity.csv (when present) and the declared
scores in ../scores/windows.csv. Writes:

  classification.csv       each scored window with its heat terms, ratio
                           and class under the README's rule
  energy_by_assembly.csv   medians and ranges of the heat terms by assembly
  secondary_scores.csv     v1.8.0 bias and RMSE on all scored windows and on
                           the energy-consistent windows, overall and by
                           assembly
  sensitivity_summary.csv  v1.8.0 bias and RMSE of assemblies 2 to 5 for
                           each sensitivity case
"""
import csv
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MARGIN = 1.25
SHALLOW = ("2", "3", "4", "5")


def read(path):
    with open(path, encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def order(bhas):
    return sorted(set(bhas), key=int)


def metrics(errors):
    e = np.asarray(errors, float)
    if not len(e):
        return dict(n=0, bias_C="", rmse_C="")
    return dict(n=len(e), bias_C=float(e.mean()), rmse_C=float(np.sqrt((e**2).mean())))


def classify(balance, scores):
    rows = []
    for r in balance:
        s = scores[r["sample_id"]]
        rock = max(float(r["rock_model_W"]), float(r["conduction_bound_W"]))
        limit = rock+float(r["hydraulic_W"])
        measured = float(r["measured_Q_W"])
        rows.append(dict(sample_id=r["sample_id"], time=r["time"], bha=r["bha"], bit_ft=r["bit_ft"],
                         inlet_C=r["inlet_C"], measured_return_C=r["measured_return_C"],
                         v180_return_C=s["v1.8.0"], v180_error_C=s["v1.8.0_minus_measured_C"],
                         measured_Q_W=measured, hydraulic_W=r["hydraulic_W"], rock_bound_W=rock,
                         ratio=measured/limit,
                         energy_class="energy-inconsistent" if measured > MARGIN*limit else "energy-consistent"))
    return rows


def by_assembly(balance):
    out = []
    for bha in order(r["bha"] for r in balance):
        sel = [r for r in balance if r["bha"] == bha]
        row = dict(bha=bha, windows=len(sel))
        for key in ("measured_Q_W", "hydraulic_W", "rock_model_W", "conduction_bound_W"):
            vals = np.array([float(r[key]) for r in sel])/1e6
            row[key.replace("_W", "_MW_median")] = float(np.median(vals))
            row[key.replace("_W", "_MW_min")] = float(vals.min())
            row[key.replace("_W", "_MW_max")] = float(vals.max())
        rock = np.array([max(float(r["rock_model_W"]), float(r["conduction_bound_W"])) for r in sel])/1e6
        row.update(rock_bound_MW_median=float(np.median(rock)), rock_bound_MW_min=float(rock.min()),
                   rock_bound_MW_max=float(rock.max()))
        ratio = [float(r["measured_Q_W"]) /
                 (max(float(r["rock_model_W"]), float(r["conduction_bound_W"]))+float(r["hydraulic_W"])) for r in sel]
        row.update(ratio_median=float(np.median(ratio)), ratio_min=float(min(ratio)), ratio_max=float(max(ratio)),
                   energy_inconsistent=sum(m > MARGIN for m in ratio))
        for key in ("measured_return_C", "inlet_C", "formation_bit_transfer_C", "formation_bit_hottest_C",
                    "formation_open_max_hottest_C"):
            row[key+"_median"] = float(np.median([float(r[key]) for r in sel]))
        out.append(row)
    return out


def secondary(classes):
    rows = []
    for subset_name, keep in (("all scored (declared)", lambda r: True),
                              ("energy-consistent", lambda r: r["energy_class"] == "energy-consistent"),
                              ("energy-inconsistent", lambda r: r["energy_class"] == "energy-inconsistent")):
        sel = [r for r in classes if keep(r)]
        rows.append(dict(set=subset_name, group="all", **metrics([float(r["v180_error_C"]) for r in sel])))
        for bha in order(r["bha"] for r in classes):
            part = [r for r in sel if r["bha"] == bha]
            rows.append(dict(set=subset_name, group=f"assembly {bha}",
                             **metrics([float(r["v180_error_C"]) for r in part])))
        part = [r for r in sel if r["bha"] in SHALLOW]
        rows.append(dict(set=subset_name, group="assemblies 2 to 5", **metrics([float(r["v180_error_C"]) for r in part])))
        part = [r for r in sel if r["bha"] not in SHALLOW]
        rows.append(dict(set=subset_name, group="assemblies 6 to 11", **metrics([float(r["v180_error_C"]) for r in part])))
    return rows


def sensitivity(rows):
    out = []
    cases = list(dict.fromkeys(r["case"] for r in rows))
    for case in cases:
        for bha in (*SHALLOW, "2 to 5"):
            sel = [r for r in rows if r["case"] == case and (bha == "2 to 5" or r["bha"] == bha)]
            ok = [r for r in sel if r["status"] == "converged"]
            inlets = [float(r["inlet_C"]) for r in ok]
            out.append(dict(case=case, bha=bha, windows=len(sel), converged=len(ok),
                            inlet_C_median=float(np.median(inlets)) if inlets else "",
                            **metrics([float(r["error_C"]) for r in ok])))
    return out


def main():
    balance = read(HERE/"energy_balance.csv")
    scores = {r["sample_id"]: r for r in read(HERE.parent/"scores/windows.csv")}
    classes = classify(balance, scores)
    write(HERE/"classification.csv", classes)
    write(HERE/"energy_by_assembly.csv", by_assembly(balance))
    write(HERE/"secondary_scores.csv", secondary(classes))
    if (HERE/"sensitivity.csv").exists():
        write(HERE/"sensitivity_summary.csv", sensitivity(read(HERE/"sensitivity.csv")))
    for bha in order(r["bha"] for r in classes):
        sel = [r for r in classes if r["bha"] == bha]
        print(bha, len(sel), sum(r["energy_class"] == "energy-inconsistent" for r in sel), "inconsistent")


if __name__ == "__main__":
    main()
