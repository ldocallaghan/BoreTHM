"""Rebuild the amended event archive with the rebuilt bit depths.

The event rules are unchanged from the 7 November amendment. Only the bit
depth differs: depth_reference.rebuilt_depth removes rig depth-tally
resets, which otherwise appear as bit movement inside a pause.
"""
import numpy as np

from validation.forge16b.sanvean import build_extracts as build, trip_history
from validation.forge16b.sanvean.depth_reference import rebuilt_depth

OUT = build.HERE / "events-2026-11-07-depth"


def main():
    counts = []
    for run in range(11, 18):
        rows = trip_history.rows(build.HERE / f"bha-{run}-inputs.csv.gz")

        def field(key):
            return np.array([build.number(row[key]) for row in rows])

        time = np.array([build.timestamp(row["time"]) for row in rows])
        bit = np.array([rebuilt_depth(t, b, clock="sanvean", assembly=run)
                        for t, b in zip(time, field("bit_depth_ft"))])
        history = build.History(time, bit, field("hole_depth_ft"),
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
