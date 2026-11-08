"""Rebuild the amended event archive with the rebuilt bit depths.

The event rules are unchanged from the 7 November amendment. Only the bit
depth differs: depth_reference.entry_depth takes the driller's tally
entries as the depth reference and scales the rig increments between
them. A typed entry otherwise appears as bit movement inside a pause.

The event rules find the bottom where the hole and bit depths agree within
5 ft. The rebuilt bit depth is compared with the hole depth shifted by the
same offset, so the rig's own hole-minus-bit geometry decides the bottom
and the scale between entries does not move it.
"""
import numpy as np

from validation.forge16b.sanvean import build_extracts as build, trip_history
from validation.forge16b.sanvean.depth_reference import entry_depth

OUT = build.HERE / "events-2026-11-08-entries"


def main():
    counts = []
    for run in range(11, 18):
        rows = trip_history.rows(build.HERE / f"bha-{run}-inputs.csv.gz")

        def field(key):
            return np.array([build.number(row[key]) for row in rows])

        time = np.array([build.timestamp(row["time"]) for row in rows])
        recorded = field("bit_depth_ft")
        bit = np.array([entry_depth(t, b, clock="sanvean", assembly=run)
                        for t, b in zip(time, recorded)])
        offset = bit - recorded
        hole = field("hole_depth_ft")
        hole = np.where(np.isfinite(offset), hole + offset, hole)
        history = build.History(time, bit, hole,
                                field("flow_gpm"), field("rotary_rpm"), 1)
        available = np.array([field(f"{k}_available") == 1 for k in build.TEMPS])
        events = list(build.event_records(history, available, field("data_loss_pct"), amended=True))
        build.records(OUT / f"bha-{run}-events.csv", events)
        for kind in ("trip_stage", "connection", "stop", "long_stop"):
            selected = [row for row in events if row["kind"] == kind]
            counts.append(dict(eow_bha=run, event_class=kind, candidates=len(selected)) |
                          {f"{k}_eligible": sum(row[f"{k}_eligible"] for row in selected)
                           for k in build.TEMPS})
    build.records(OUT / "event-counts.csv", counts)


if __name__ == "__main__":
    main()
