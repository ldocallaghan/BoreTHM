"""Build the amended event archive from inputs and availability flags."""
import numpy as np

from validation.forge16b.sanvean import build_extracts as build, trip_history

OUT = build.HERE / "events-2026-11-07"


def main():
    counts = []
    for run in range(11, 18):
        rows = trip_history.rows(build.HERE / f"bha-{run}-inputs.csv.gz")

        def field(key):
            return np.array([build.number(row[key]) for row in rows])

        history = build.History(np.array([build.timestamp(row["time"]) for row in rows]),
                                field("bit_depth_ft"), field("hole_depth_ft"),
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
