"""Audit trip depth-reference changes using rig inputs only."""
import argparse
import csv
import gzip
import io
from pathlib import Path
import zipfile

import numpy as np

from validation.benchmarks.run_circulation import write_csv
from validation.forge16b.sanvean.build_extracts import HERE, iso, number, timestamp
from validation.forge16b.sanvean.depth_reference import corrected_depth, corrections
from validation.forge16b.sanvean.events import History
from validation.forge16b.sanvean.trip_history import rows

FIELDS = ("Bit Depth (feet)", "Hole Depth (feet)", "Total Pump Output (gal_per_min)",
          "Hook Load (klbs)", "Block Height (feet)", "Hookload Threshold (klbs)")


def inputs(path):
    with zipfile.ZipFile(path) as archive, archive.open("10 Second Data.csv") as raw:
        reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
        header = next(reader)
        positions = [header.index(field) for field in FIELDS]
        return np.array([(timestamp(row[0]+" "+row[1]),
                          *(number(row[i]) if row[i] != "-999.25" else np.nan for i in positions))
                         for row in reader])


def trip_windows(stage_index):
    windows = {r["eow_bha"]: (timestamp(r["trip_in_start"]),
                             timestamp(r["first_within_5ft_bottom"]))
               for r in rows(HERE/"trip-history.csv")}
    index = rows(stage_index)
    for row in index:
        if row["status"] != "candidate" or row["assembly"] in windows:
            continue
        stages = [s for s in index
                  if s["assembly"] == row["assembly"] and s["status"] == "candidate"]
        windows[row["assembly"]] = (min(timestamp(s["start"]) for s in stages),
                                    max(timestamp(s["circulation_end"]) for s in stages))
    return windows


def resets(rig, windows, *, clock="pason", step=10):
    time, bit, _, flow, hook, block, threshold = rig.T
    slips = (hook <= threshold) & (flow < 50.) & np.isfinite(bit)
    offsets = {r["assembly"]: r for r in corrections()}
    history = History(time, bit, bit, flow, hook, step)
    for run, (start, end) in sorted(windows.items(), key=lambda item: int(item[0])):
        first, last = np.searchsorted(time, (start, end), side="left")
        found = False
        for a, b in history.spells(slips, first, last):
            candidates = [(i, j) for j in range(a+1, b)
                          for i in range(max(a, j-30//step), j) if bit[i]-bit[j] > 50.]
            # Overlapping 10–30 second windows around one drop are one reset.
            while candidates:
                i, j = min(candidates, key=lambda pair: (pair[1], -pair[0]))
                found = True
                applied = offsets.get(run)
                yield dict(assembly=run, status="candidate", reset_time=iso(time[j]),
                           drop_ft=round(bit[i]-bit[j], 2), before_ft=bit[i], after_ft=bit[j],
                           flow_before_gpm=flow[i], flow_after_gpm=flow[j],
                           hook_before_klbs=hook[i], hook_after_klbs=hook[j],
                           slips_threshold_klbs=threshold[j],
                           block_before_ft=block[i], block_after_ft=block[j],
                           correction_ft=(applied["subtract_ft"] if applied and
                                          applied[f"{clock}_reset"] == iso(time[j]) else ""))
                candidates = [(x, y) for x, y in candidates if x >= j]
        if not found:
            yield dict(assembly=run, status="no candidate")


def sanvean_screen(pason):
    alignment = {r["eow_bha"]: int(r["pason_minus_sanvean_s"])
                 for r in rows(HERE/"clock-alignment.csv")}
    for trip in rows(HERE/"trip-history.csv"):
        run = trip["eow_bha"]
        offset = alignment[run]
        start, end = (timestamp(trip[k])-offset for k in
                      ("trip_in_start", "first_within_5ft_bottom"))
        with gzip.open(HERE/f"bha-{run}-inputs.csv.gz", "rt", encoding="utf-8") as stream:
            source = csv.DictReader(stream)
            data = np.array([(timestamp(r["time"]), *(number(r[k]) for k in
                              ("bit_depth_ft", "hole_depth_ft", "flow_gpm",
                               "hook_load_klbs", "block_height_ft"))) for r in source])
        nearest = np.searchsorted(pason[:, 0], data[:, 0]+offset, side="right")-1
        threshold = pason[nearest, 6]
        yield from resets(np.column_stack([data, threshold]), {run: (start, end)},
                          clock="sanvean", step=1)


def cycle_travel(time, hook, block, threshold, step, *, loaded):
    valid = (hook > threshold if loaded else hook <= threshold) & np.isfinite(block)
    history = History(time, block, block, hook, threshold, step)
    travel = [(-1 if loaded else 1)*(block[b-1]-block[a])
              for a, b in history.spells(valid)]
    return [value for value in travel if 50. < value <= 120.]


def stands(rig):
    with gzip.open(HERE/"bha-17-inputs.csv.gz", "rt", encoding="utf-8") as stream:
        selected = [row for row in csv.DictReader(stream)
                    if row["time"] <= "2023-05-21 10:43:23"]
    data = np.array([(timestamp(r["time"]), *(number(r[k]) for k in
                      ("bit_depth_ft", "hook_load_klbs", "block_height_ft"))) for r in selected])
    first = np.flatnonzero(np.all(np.isfinite(data[:, 1:]), axis=1))[0]
    time, bit, hook, block = data[first:].T
    pason_start = timestamp("2023-05-21 05:33:40")
    early = rig[(rig[:, 0] >= pason_start) & (rig[:, 0] < time[0]+7)]
    early_cycles = cycle_travel(early[:, 0], early[:, 4], early[:, 5], early[:, 6], 10,
                                loaded=False)
    loaded = cycle_travel(time, hook, block, 52., 1, loaded=True)
    in_slips = cycle_travel(time, hook, block, 52., 1, loaded=False)
    mean = np.mean(loaded)
    for clock, stamp, raw, extra in (("sanvean", time[0], bit[0], 0),
                                      ("pason", early[0, 0], early[0, 1], len(early_cycles))):
        count = len(in_slips)+extra
        yield dict(clock=clock, start=iso(stamp), recorded_bit_ft=raw,
                   corrected_bit_ft=corrected_depth(stamp, raw, clock=clock, assembly=17),
                   complete_stand_cycles=count, mean_loaded_stand_ft=mean,
                   bottom_bit_ft=bit[-1], implied_start_ft=bit[-1]-count*mean)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pason_zip", type=Path)
    parser.add_argument("h3_index", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rig = inputs(args.pason_zip)
    write_csv(args.output/"depth-reference-screen.csv", resets(rig, trip_windows(args.h3_index)))
    write_csv(args.output/"depth-reference-screen-sanvean.csv", sanvean_screen(rig))
    write_csv(args.output/"run17-stand-check.csv", stands(rig))


if __name__ == "__main__":
    main()
