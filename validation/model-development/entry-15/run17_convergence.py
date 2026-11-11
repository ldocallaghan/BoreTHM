"""Event-level convergence of the run 17 and 16A models, one discretisation at a time.

Each axis refines from the base grid (160 uniform axial cells joined by
the fixed bit faces, 40 radial nodes, 1.25 s maximum step) one level
down and one level up, holding the other two at base: axial 80, 160 and
320 uniform cells; radial 20, 40 and 80 nodes; maximum step 2.5, 1.25
and 0.625 s. Every event, sensor, band edge,
coupling limit and float assumption is compared. The criterion is a
change under 0.1 K between the two finest levels. The observed order is
log2 of the ratio of successive absolute changes when the signed changes
agree; reversals leave it unresolved.

Inputs are the outputs of `run17_events.py` (ev-<level>.csv) or, with
`--well 16A`, of `run16a_legs.py` (legs-<level>.csv) at each level.
"""
import argparse
import csv
import math
from pathlib import Path

from validation.benchmarks.run_circulation import write_csv

HERE = Path(__file__).parent
WELLS = {
    "16B": dict(prefix="ev", quantities=("stage_peak_C", "restart_peak_C", "circulation_end_C", "rise_C"),
                space="run17-parcel-refinement.csv", time="run17-parcel-time-fine.csv",
                summary="run17-event-convergence.csv"),
    "16A": dict(prefix="legs", quantities=("leg_peak_C", "restart_peak_C"),
                space="run16a-refinement.csv", time="run16a-time-refinement.csv",
                summary="run16a-event-convergence.csv"),
}
AXES = {"axial": ("ax80", "base", "ax320"), "radial": ("r20", "base", "r80"),
        "time": ("c250", "base", "c0625")}
KEY = ("event", "sensor", "band", "coupling", "float_valve")


def read(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def order(coarse, middle, fine):
    first, second = middle-coarse, fine-middle
    if first == 0 or second == 0 or (first > 0) != (second > 0):
        return None
    return math.log2(abs(first)/abs(second))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="folder holding the level outputs")
    parser.add_argument("--well", choices=tuple(WELLS), default="16B")
    args = parser.parse_args()
    well = WELLS[args.well]
    quantities = well["quantities"]
    levels = {name: {tuple(r[k] for k in KEY): r for r in read(args.folder/f"{well['prefix']}-{name}.csv")}
              for name in {n for names in AXES.values() for n in names}}
    rows, summary = {"axial": [], "radial": [], "time": []}, []
    for axis, names in AXES.items():
        for level, name in enumerate(names, 1):
            for key, row in levels[name].items():
                rows[axis].append(dict(axis=axis, level=level, kind=row.get("kind", "run_in_leg")) | {
                    k: row[k] for k in (*KEY, "cells", "radial_nodes", "cap_s", *quantities,
                                        "max_step_energy_residual_J", "energy_residual_fraction")})
        worst = {}
        for key, base in levels[names[1]].items():
            for quantity in quantities:
                values = [levels[n][key][quantity] for n in names]
                if any(v in ("", "nan") for v in values):
                    continue
                coarse, middle, fine = map(float, values)
                change = abs(fine-middle)
                label = (base.get("kind", "run_in_leg"), key[1], key[2], quantity)
                current = worst.get(label)
                if current is None or change > current[0]:
                    worst[label] = (change, order(coarse, middle, fine), key[0], key[3], key[4])
        for (kind, sensor, band, quantity), (change, observed, event, coupling, float_valve) in sorted(worst.items()):
            summary.append(dict(axis=axis, kind=kind, sensor=sensor, band=band, quantity=quantity,
                                largest_finest_change_K=change, event=event, coupling=coupling,
                                float_valve=float_valve,
                                observed_order="unresolved" if observed is None else f"{observed:.2f}",
                                within_0_1_K=change < .1))
    write_csv(HERE/well["space"], rows["axial"]+rows["radial"])
    write_csv(HERE/well["time"], rows["time"])
    write_csv(HERE/well["summary"], summary)
    failing = [s for s in summary if not s["within_0_1_K"]]
    print(len(summary), "axis-quantity groups;", len(failing), "above 0.1 K")
    for s in failing:
        print(s)


if __name__ == "__main__":
    main()
