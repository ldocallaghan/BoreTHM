"""Compare pump-on bit depths across the FORGE 16B depth references.

For every H3 stage (Pason clock) and every run 17 trip stage (Sanvean
clock) the table gives the recorded depth, the first screen's constant
subtraction, the 25e27a5 offset rebuild and the tally-entry depth with
its uncertainty. It reads rig depth channels only.
"""
import argparse
from pathlib import Path

import numpy as np

from validation.benchmarks.run_circulation import write_csv
from validation.forge16b.sanvean import depth_entries as entries
from validation.forge16b.sanvean.build_extracts import HERE as SANVEAN, timestamp
from validation.forge16b.sanvean.depth_reference import corrected_depth, entry_depth, rebuilt_depth
from validation.forge16b.sanvean.trip_history import rows

HERE = Path(__file__).parent


def at(time, values, t):
    """Value at the last sample at or before t."""
    i = int(np.searchsorted(time, t, side="right")) - 1
    return values[i] if i >= 0 else np.nan


def interval_at(time, intervals, t):
    starts = np.array([time[iv["a"]] for iv in intervals])
    return intervals[int(np.searchsorted(starts, t, side="right")) - 1]


def row(clock, assembly, stage, pump_on, recorded, run, time, error, intervals):
    t = timestamp(pump_on)
    iv = interval_at(time, intervals, t)
    kwargs = dict(clock=clock) | (dict(assembly=run) if clock == "sanvean" else {})
    first = corrected_depth(t, recorded, clock=clock, assembly=run)
    return dict(assembly=assembly, stage=stage, clock=clock, pump_on=pump_on,
                recorded_ft=round(float(recorded), 2),
                first_screen_ft=round(float(first), 2),
                rebuild_25e27a5_ft=round(float(rebuilt_depth(t, recorded, **kwargs)), 2),
                entry_ft=round(float(entry_depth(t, recorded, **kwargs)), 2),
                uncertainty_ft=round(float(at(time, error, t)), 1),
                basis=iv["basis"], flag=iv["flag"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="16B_Pason.zip from GDR 1516")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    results = {(clock, run): (rec, result) for clock, run, rec, result in entries.records(args.archive)}
    pason, (_, p_error, p_intervals, _) = results[("pason", "")]
    p_time, p_bit = pason[0], pason[1]
    out = []
    for stage in rows(HERE/"h3-stage-index.csv"):
        if not stage["pump_on"]:
            continue
        recorded = at(p_time, p_bit, timestamp(stage["pump_on"]))
        out.append(row("pason", stage["assembly"], f"H3 {stage['stage']}", stage["pump_on"],
                       recorded, int(stage["assembly"]), p_time, p_error, p_intervals))
    sanvean, (_, s_error, s_intervals, _) = results[("sanvean", 17)]
    s_time, s_bit = sanvean[0], sanvean[1]
    for event in rows(SANVEAN/"events-2026-11-08-entries/bha-17-events.csv"):
        if event["kind"] != "trip_stage" or not event["circ_start"]:
            continue
        recorded = at(s_time, s_bit, timestamp(event["circ_start"]))
        out.append(row("sanvean", "17", event["id"], event["circ_start"], recorded, 17,
                       s_time, s_error, s_intervals))
    write_csv(args.output, out)


if __name__ == "__main__":
    main()
