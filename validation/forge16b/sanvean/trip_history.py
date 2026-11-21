"""Reconstruct trips and depth-dependent static intervals from rig inputs."""
import argparse
import csv
import gzip
from pathlib import Path

import numpy as np

from validation.forge16b.sanvean.build_extracts import HERE, iso, number, read_pason, records, timestamp
from validation.forge16b.sanvean.events import History


def rows(path):
    op = gzip.open if path.suffix == ".gz" else open
    with op(path, "rt", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def recover(run, rig, start, end, carrier_offset):
    t, bit, hole, flow = rig[:4]
    hist = History(t, bit, hole, flow, np.full_like(t, np.nan), 10)
    before = (t < start) & (t >= start-172800)
    near = before & (bit >= 0) & (np.abs(bit-hole) <= 5)
    last = np.flatnonzero(near)
    left_bottom = int(t[last[-1]])+10 if len(last) else None
    surface = before & (bit >= 0) & (bit <= 100)
    if left_bottom is not None:
        surface &= t >= left_bottom
    surface_spells = list(hist.spells(surface))
    reached = int(t[surface_spells[0][0]]) if surface_spells else None
    in_start = int(t[surface_spells[-1][1]-1])+10 if surface_spells else start
    bottom = np.flatnonzero((t >= in_start) & (t < end) & (hole > 0) &
                            (bit > 0) & (np.abs(bit-hole) <= 5))
    arrived = int(t[bottom[0]]) if len(bottom) else None
    summary = dict(eow_bha=run, previous_left_bottom=iso(left_bottom) if left_bottom else "",
                   surface_reached_within_100ft=iso(reached) if reached else "",
                   trip_in_start=iso(in_start), first_within_5ft_bottom=iso(arrived) if arrived else "",
                   note="source trip traced at 10 s" if all(x is not None for x in (left_bottom, reached, arrived))
                   else "partial input history")
    outgoing = []
    outbound = (t < in_start) & np.isfinite(bit)
    if left_bottom is not None:
        outbound &= t >= left_bottom
    else:
        outbound &= False
    outbound_ids = np.flatnonzero(outbound)
    if len(outbound_ids):
        minimum = outbound_ids[np.argmin(bit[outbound_ids])]
        summary.update(shallowest_outbound_depth_ft=bit[minimum],
                       shallowest_outbound_time=iso(t[minimum]))
        boundary = reached if reached is not None else t[minimum]
        for a, b in hist.spells((flow > 100) & outbound & (t < boundary)):
            outgoing.append(dict(eow_bha=run, start=iso(t[a]), end=iso(t[b-1]+10),
                                 duration_s=int(t[b-1]+10-t[a]), mean_gpm=float(flow[a:b].mean()),
                                 bit_start_ft=bit[a], bit_end_ft=bit[b-1],
                                 trip_out_coverage="through surface" if reached else "through shallowest observation"))

    profile = []
    if arrived is not None:
        incoming = np.flatnonzero((t >= in_start) & (t <= arrived) & np.isfinite(bit))
        for sensor, offset in (("bit", 0.), ("black_box_carrier_midpoint", carrier_offset)):
            for z in np.arange(0., bit[bottom[0]]-offset+1., 25.):
                passing = incoming[bit[incoming]-offset >= z]
                if not len(passing):
                    continue
                i = passing[0]
                # Use the last recorded flow above 100 gpm when the string reached
                # the given depth. A pipe positioned shallower than this depth
                # does not reset the static clock there.
                circulating = np.flatnonzero((t < t[i]) & (flow > 100) & (bit >= z))
                last_circ = t[circulating[-1]]+10 if len(circulating) else np.nan
                inside = (in_start <= last_circ <= t[i]) if np.isfinite(last_circ) else False
                profile.append(dict(eow_bha=run, sensor=sensor, depth_ft=z, pass_time=iso(t[i]),
                                    last_circulation=iso(last_circ) if np.isfinite(last_circ) else "",
                                    static_seconds=t[i]-last_circ, reconditioned_during_trip=inside))
    return summary, outgoing, profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pason_selected", type=Path)
    args = parser.parse_args()
    alignment = {r["eow_bha"]: int(r["pason_minus_sanvean_s"]) for r in rows(HERE/"clock-alignment.csv")}
    summary, outgoing, profile = [], [], []
    for geometry in rows(HERE/"sanvean_sensor_geometry.csv"):
        run = geometry["eow_bha"]
        source = rows(HERE/f"bha-{run}-inputs.csv.gz")
        time = np.array([timestamp(row["time"]) for row in source]) + alignment[run]
        midpoint = (number(geometry["black_box_bottom_ft"])+number(geometry["black_box_top_ft"]))/2
        rig = read_pason(args.pason_selected, time[0]-172800, time[-1])
        event = rows(HERE/f"bha-{run}-events.csv")
        trip_rows = [r for r in event if r["kind"] == "trip_stage"]
        last_stage = max((timestamp(r["end"]) for r in trip_rows), default=time[0])
        trip_end = max(last_stage+alignment[run]+900, time[0]+7200)
        result, circ, times = recover(run, rig, time[0], trip_end, midpoint)
        summary.append(result)
        outgoing.extend(circ)
        profile.extend(times)
    records(HERE/"trip-history.csv", summary)
    records(HERE/"trip-out-circulation.csv", outgoing)
    records(HERE/"static-time-by-depth.csv", profile)


if __name__ == "__main__":
    main()
