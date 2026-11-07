"""Build FORGE 16B staged-trip temperature comparison keys from rig inputs."""
import argparse
import importlib
from pathlib import Path

import numpy as np

from validation.benchmarks.run_circulation import write_csv
from validation.forge16b.sanvean.events import History

rig = importlib.import_module(f"{__package__}.run17_boundaries")
HERE = Path(__file__).parent
FORGE = rig.HERE.parent


def trip_indices(history, definition, frozen, incoming):
    run = definition["eow_bha"]
    if run in frozen:
        record = frozen[run]
        return tuple(np.searchsorted(history.time, rig.timestamp(record[key]))
                     for key in ("trip_in_start", "first_within_5ft_bottom"))
    top, bottom = (float(definition[key]) for key in ("depth_in_ft", "depth_out_ft"))
    on_bottom = (np.abs(history.hole-history.bit) <= 5.)
    first_drilling = np.flatnonzero(on_bottom & (history.hole > top+5.)
                                    & (history.hole < bottom-5.) & (history.flow > 100.))
    if run in incoming:
        makeup_end = rig.timestamp(incoming[run]["end"])
        first_drilling = first_drilling[history.time[first_drilling] >= makeup_end]
    if not len(first_drilling):
        return None
    first = first_drilling[0]
    surface = np.flatnonzero((history.bit[:first] >= 0.) & (history.bit[:first] <= 100.)
                             & (np.abs(history.hole[:first]-top) <= 10.))
    if run in incoming:
        start = int(np.searchsorted(history.time, makeup_end))
        if start >= first:
            return None
    elif len(surface):
        start = int(surface[-1])+1
    else:
        return None
    reached = np.flatnonzero(on_bottom[start:first+1] & (history.hole[start:first+1] >= top-5.))
    if not len(reached):
        return None
    return start, start+int(reached[0])


def index(history, definitions, frozen, incoming):
    for definition in definitions:
        run = definition["eow_bha"]
        if run == "17":
            continue
        base = dict(assembly=run, run_start_depth_ft=definition["depth_in_ft"])
        if run == "26":
            yield base | dict(status="no documented MWD")
            continue
        bounds = trip_indices(history, definition, frozen, incoming)
        if bounds is None or bounds[0] >= bounds[1]:
            yield base | dict(status="trip start unresolved")
            continue
        candidates = [r for r in history.trip_stages(*bounds) if r[2] is not None]
        if not candidates:
            yield base | dict(status="no qualifying circulation stage")
        for number, (start, end, pump_on, pump_stop) in enumerate(candidates, 1):
            offset = definition["sensor_offset_ft"]
            offsets = offset or ("22,69,84" if run == "3" else "22,84" if run == "4" else "")
            yield base | dict(measure="H3", stage=number,
                              start=rig.iso(history.time[start]), end=rig.iso(history.time[end]),
                              pump_on=rig.iso(history.time[pump_on]),
                              circulation_end=rig.iso(history.time[pump_stop-1]+history.step),
                              bit_at_pump_on_ft=history.bit[pump_on],
                              mwd_offsets_ft=offsets,
                              status="candidate" if offsets else "no documented MWD",
                              timing_basis=("archived trip" if run in frozen else
                                            "reported assembly makeup" if run in incoming else
                                            "Pason depth and flow"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    records = np.array(list(rig.rig_inputs(args.archive, 0, np.inf)))
    time, bit, hole, flow, _ = records.T
    history = History(time, bit, hole, flow, np.zeros_like(flow), 10)
    frozen = {r["eow_bha"]: r for r in rig.rows(rig.HERE/"trip-history.csv")
              if r["trip_in_start"] and r["first_within_5ft_bottom"]}
    source = HERE.parent/"entry-9/16b-assembly-intervals.csv"
    incoming = {r["assembly"]: r for r in rig.rows(source)
                if r["status"] == "reported incoming assembly"}
    stages = list(index(history, rig.rows(FORGE/"run_definitions.csv"), frozen, incoming))
    write_csv(args.output, stages)


if __name__ == "__main__":
    main()
