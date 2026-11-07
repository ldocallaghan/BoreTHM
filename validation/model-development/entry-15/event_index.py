"""Build event keys from archived timing and availability, without target values."""
from pathlib import Path

from validation.scoreboard.scoreboard import ROOT, read_csv, write_csv

HERE = Path(__file__).parent
EVENTS = ROOT/"validation/forge16b/sanvean/events-2026-11-07"


def rows():
    for row in read_csv(HERE.parent/"phase-0/16a-run-in-attribution.csv"):
        if row["channel"] != "bit_box_C":
            continue
        base = dict(well="16A", assembly=row["run"], event=row["event_id"],
                    start=row["start"], end=row["end"], pump_on=row["pump_on"],
                    sensor="bit box", float_record=row["float_record"])
        yield base | {"measure": "D1"}
        if row["pump_on"]:
            yield base | {"measure": "D2"}

    for run in range(11, 18):
        for row in read_csv(EVENTS/f"bha-{run}-events.csv"):
            stage = row["kind"] == "trip_stage"
            base = dict(well="16B", assembly=run, event=row["id"],
                        start=row["start"], end=row["end"],
                        pump_on=row["circ_start"] if stage else row["pump_on"],
                        circulation_end=row["circ_end"] if stage else "")
            for flag, sensor in (("sanvean_C_eligible", "bit box"),
                                 ("bb_mean_C_eligible", "Black Box")):
                if row[flag] != "True" or (stage and run != 17 and sensor == "bit box"):
                    continue
                measure = ("D3" if stage else "D4") if run == 17 else ("H1" if stage else "H2")
                yield base | {"sensor": sensor, "measure": measure}


if __name__ == "__main__":
    write_csv(HERE/"event-index.csv", list(rows()))
