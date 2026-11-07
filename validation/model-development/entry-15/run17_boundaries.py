"""Recover run 17 circulation boundary inputs from GDR 1516.

The source reader selects only time, depth, pump output and inlet
temperature. Event times are converted to the Pason clock before lookup.
"""
import argparse
import csv
import io
import zipfile
from pathlib import Path

import numpy as np

from validation.forge16b.sanvean.build_extracts import HERE, iso, number, records, timestamp
from validation.forge16b.sanvean.depth_reference import corrected_depth
from validation.forge16b.sanvean.events import History
from validation.forge16b.sanvean.trip_history import rows

CHANNELS = ("Bit Depth (feet)", "Hole Depth (feet)",
            "Total Pump Output (gal_per_min)", "TEMP IN MANIFOLD (DEGREES)")


def rig_inputs(archive, first, last, *, correct_depth=True):
    with zipfile.ZipFile(archive) as source, source.open("10 Second Data.csv") as raw:
        data = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
        header = next(data)
        indices = [header.index(channel) for channel in CHANNELS]
        for row in data:
            stamp = timestamp(row[0] + " " + row[1])
            if stamp >= last:
                break
            if stamp >= first:
                bit, hole, flow, inlet = (
                    number(row[i]) if row[i] != "-999.25" else np.nan for i in indices)
                if correct_depth:
                    bit = corrected_depth(stamp, bit)
                yield stamp, bit, hole, flow, inlet


def boundary_rows(events, rig, offset):
    time, bit, hole, flow, inlet = rig.T
    history = History(time, bit, hole, flow, np.zeros_like(flow), 10)
    for event in events:
        start = timestamp(event["start"]) + offset
        end = timestamp(event["end"]) + offset
        depth = number(event["bit_end_ft"])
        if not np.isfinite(depth):
            depths = bit[(time >= start) & (time < end) & np.isfinite(bit)]
            depth = depths[-1] if len(depths) else np.nan
        base = dict(event=event["id"], event_kind=event["kind"],
                    start_pason=iso(start), end_pason=iso(end), depth_ft=depth)
        # A shallower circulation cannot set the boundary at this depth.
        windows = list(history.spells((time < start) & (bit >= depth) & (flow > 100)
                                      & np.isfinite(inlet)))
        if not windows:
            yield base | dict(status="no observed conditioning window")
            continue
        left, right = windows[-1]
        first, last = history.bounds(left, right)
        last = min(last, start)
        sl = slice(left, right)
        weights = np.minimum(history.step, last-time[sl])
        yield base | dict(status="observed", circulation_start=iso(first),
                          circulation_end=iso(last), duration_s=last-first,
                          time_to_event_s=start-last, mean_bit_ft=np.average(bit[sl], weights=weights),
                          mean_flow_gpm=np.average(flow[sl], weights=weights),
                          mean_inlet_C=(np.average(inlet[sl], weights=weights)-32)*5/9)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    event = rows(HERE/"events-2026-11-07/bha-17-events.csv")
    alignment = next(r for r in rows(HERE/"clock-alignment.csv") if r["eow_bha"] == "17")
    offset = int(alignment["pason_minus_sanvean_s"])
    first = min(timestamp(r["start"]) for r in event) + offset - 172800
    last = max(timestamp(r["end"]) for r in event) + offset
    rig = np.array(list(rig_inputs(args.archive, first, last)))
    records(args.output, list(boundary_rows(event, rig, offset)))


if __name__ == "__main__":
    main()
