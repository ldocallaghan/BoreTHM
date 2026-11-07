"""Calculate recorded restart throughput and handover times for run 17."""
import argparse
import importlib
from pathlib import Path

import numpy as np

from borethm.column_replay import ColumnStep, circulation_phases
from validation.benchmarks.run_circulation import write_csv
from validation.scoreboard.scoreboard import PLAN, geometry, read_json

rig = importlib.import_module(f"{__package__}.run17_boundaries")


def geometry_volume(bit_ft, plan):
    assembly = geometry(dict(well="16B", run="17", eow_bha=17,
                             bit_ft=bit_ft), plan, "current")
    string = np.r_[0., np.cumsum([segment.length for segment in assembly.string])]
    hole = [section.md_top for section in assembly.hole if 0 < section.md_top < string[-1]]
    faces = np.unique(np.r_[string, hole])
    lengths = np.diff(faces)
    stations = (faces[:-1]+faces[1:])/2
    dimensions = assembly.at(stations)
    bore = np.dot(lengths, dimensions["A_bore"])
    bha = stations >= string[1]
    annulus = np.dot(lengths[bha], dimensions["A_ann"][bha])
    return bore, annulus


def pumping(history, start, end):
    for stamp, _, _, gpm, inlet in history:
        duration = min(stamp+10, end)-max(stamp, start)
        if duration > 0 and np.isfinite(gpm) and np.isfinite(inlet):
            yield ColumnStep(duration, (), flow=max(gpm, 0.)*6.30902e-5,
                             inlet_C=(inlet-32)*5/9)


def report(history, events, offset, plan):
    for row in events:
        stage = row["kind"] == "trip_stage"
        start_raw = row["circ_start"] if stage else row["pump_on"]
        if not start_raw:
            continue
        start = rig.timestamp(start_raw)+offset
        end = rig.timestamp(row["circ_end"])+offset if stage else start+300
        bore, annulus = geometry_volume(float(row["bit_end_ft"]), plan)
        steps = list(pumping(history, start, end))
        base = dict(event=row["id"], start_pason=rig.iso(start), end_pason=rig.iso(end),
                    bore_m3=bore, bha_annulus_m3=annulus, flush_m3=bore+annulus)
        if sum(step.duration for step in steps) != end-start:
            yield base | {"status": "incomplete recorded inputs"}
            continue
        elapsed = 0.
        handover = None
        for mode, step in circulation_phases(steps, bore+annulus):
            if mode == "steady" and handover is None:
                handover = elapsed
            elapsed += step.duration
        yield base | dict(status="reached" if handover is not None else "unreached",
                          handover_elapsed_s=handover,
                          pumped_m3=sum(step.duration*step.flow for step in steps))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    events = rig.rows(rig.HERE/"events-2026-11-07-depth/bha-17-events.csv")
    alignment = next(row for row in rig.rows(rig.HERE/"clock-alignment.csv")
                     if row["eow_bha"] == "17")
    offset = int(alignment["pason_minus_sanvean_s"])
    first = min(rig.timestamp(row["start"]) for row in events)+offset-10
    last = max(rig.timestamp(row["end"]) for row in events)+offset+600
    history = np.array(list(rig.rig_inputs(args.archive, first, last)))
    write_csv(args.output, report(history, events, offset, read_json(PLAN)))


if __name__ == "__main__":
    main()
