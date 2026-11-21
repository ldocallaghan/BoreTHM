"""Figures of the scored 78B-32 windows in the 58-32 form.

usage: python plot_scores.py [SCORES]

Reads the window files written by score_thermal.py and draws, for part A,
the EYE TEMP part and the return temperature, the measured against the
predicted temperature for each predictor, the measured and v1.9.0
temperature against bit depth with one panel per assembly, and the v1.9.0
error against bit depth, time and flow by assembly. It calculates no score.
"""
import argparse
import csv
from datetime import datetime
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MODELS = ("v1.9.0", "v1.7.0", "analytical")
ORIGIN = datetime(2021, 6, 28)
PARTS = (("part-a", "part-a-windows.csv", "MWD temperature", True),
         ("part-b-eye", "part-b-eye-windows.csv", "EYE temperature", False),
         ("part-b-return", "part-b-return-windows.csv", "return temperature", False))


def f(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def scored(path):
    with open(path, encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["status"] == "scored"]
    for r in rows:
        for k in ("measured_C", "bit_ft", "flow_gpm", "persistence", *(f"pred_{m}" for m in MODELS)):
            r[k] = f(r.get(k))
        r["days"] = (datetime.fromisoformat(r["centre"]) - ORIGIN).total_seconds()/86400
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scores", type=Path, nargs="?", default=HERE.parent/"scores")
    args = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ink, mark, rule = "#2b2b2b", "#2a6fdb", "#9a9a9a"
    plt.rcParams.update({"font.size": 8, "axes.edgecolor": rule, "axes.labelcolor": ink, "xtick.color": ink,
                         "ytick.color": ink, "axes.grid": True, "grid.color": "#e3e3e3", "grid.linewidth": .6})
    for prefix, name, quantity, with_persistence in PARTS:
        rows = scored(args.scores/name)
        if not rows:
            continue
        names = [*MODELS, "persistence"] if with_persistence else list(MODELS)
        measured = np.array([r["measured_C"] for r in rows])
        lo, hi = float(measured.min())-2, float(measured.max())+2
        fig, axes = plt.subplots(1, len(names), figsize=(3*len(names), 3.2), sharex=True, sharey=True)
        for ax, model in zip(axes, names):
            key = model if model == "persistence" else f"pred_{model}"
            pairs = [(r["measured_C"], r[key]) for r in rows if math.isfinite(r[key])]
            x, y = np.array(pairs).T
            ax.scatter(x, y, s=8, color=mark, alpha=.6, linewidths=0)
            ax.plot([lo, hi], [lo, hi], color=rule, linewidth=1)
            ax.set_title(f"{model} (n = {len(pairs)})", color=ink)
            ax.set_xlabel(f"Measured {quantity}, °C")
        axes[0].set_ylabel(f"Predicted {quantity}, °C")
        fig.tight_layout()
        fig.savefig(args.scores/f"{prefix}-measured-vs-predicted.png", dpi=150)
        plt.close(fig)
        bhas = sorted({r["bha"] for r in rows}, key=lambda b: (len(b), b))
        columns = min(5, len(bhas))
        nrows = max(1, math.ceil(len(bhas)/columns))
        fig, axes = plt.subplots(nrows, columns, figsize=(3*columns, 3.4*nrows), squeeze=False)
        for ax in axes.flat[len(bhas):]:
            ax.set_visible(False)
        for ax, bha in zip(axes.flat, bhas):
            subset = [r for r in rows if r["bha"] == bha]
            ax.scatter([r["measured_C"] for r in subset], [r["bit_ft"] for r in subset], s=10, color=mark,
                       linewidths=0, label="measured")
            ax.scatter([r["pred_v1.9.0"] for r in subset], [r["bit_ft"] for r in subset], s=12, color=ink,
                       marker="x", linewidths=.8, label="v1.9.0")
            ax.invert_yaxis()
            ax.set_title(f"Assembly {bha} (n = {len(subset)})", color=ink)
            ax.set_xlabel(f"{quantity[0].upper()}{quantity[1:]}, °C")
        for ax in axes[:, 0]:
            ax.set_ylabel("Bit depth, ft MD")
        axes[0, 0].legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(args.scores/f"{prefix}-depth-by-assembly.png", dpi=150)
        plt.close(fig)
        for kind, key, xlabel in (("depth", "bit_ft", "Bit depth, ft MD"),
                                  ("time", "days", "Days from 28 June 2021, rig time"),
                                  ("flow", "flow_gpm", "Flow, US gal/min")):
            columns = min(5, len(bhas))
            nrows = max(1, math.ceil(len(bhas)/columns))
            fig, axes = plt.subplots(nrows, columns, figsize=(3*columns, 2.4*nrows), sharey=True, squeeze=False)
            for ax in axes.flat[len(bhas):]:
                ax.set_visible(False)
            for ax, bha in zip(axes.flat, bhas):
                subset = [r for r in rows if r["bha"] == bha]
                ax.axhline(0, color=rule, linewidth=1)
                ax.scatter([r[key] for r in subset], [r["pred_v1.9.0"] - r["measured_C"] for r in subset],
                           s=8, color=mark, linewidths=0)
                ax.set_title(f"Assembly {bha} (n = {len(subset)})", color=ink)
                ax.set_xlabel(xlabel)
            for ax in axes[:, 0]:
                ax.set_ylabel("v1.9.0 minus measured, °C")
            fig.tight_layout()
            fig.savefig(args.scores/f"{prefix}-residual-vs-{kind}.png", dpi=150)
            plt.close(fig)


if __name__ == "__main__":
    main()
