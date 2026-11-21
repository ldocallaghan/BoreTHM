"""Describe 56-32 coverage and infer ranges from the development samples."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from borethm.studies import validate_forge16a as a
from validation.forge16b.sanvean.build_extracts import number, records, timestamp

HERE = Path(__file__).resolve().parent
VALIDATION = HERE.parents[1]
FORECAST = VALIDATION/"forge56-32/predictions-v1.8.0"


def read(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def numeric(rows, key):
    return np.array([number(row.get(key)) for row in rows])


def stats(values):
    values = values[np.isfinite(values)]
    if not len(values):
        return dict(count=0)
    low, median, high = np.quantile(values, [0, .5, 1])
    return dict(count=len(values), minimum=low, median=median, maximum=high)


def circulation_timing(well):
    source = VALIDATION/("forge16a/rig_history_1min.csv" if well == "16A"
                         else "forge16b/pason_selected_1min.csv")
    rows = read(source)
    time = np.array([timestamp(r["time"]) for r in rows])
    pumping = numeric(rows, "flow_gpm") > 100.
    prev = np.maximum.accumulate(np.where(pumping, np.arange(len(rows)), -1))
    pump_start = pumping & np.r_[True, (~pumping[:-1]) | (np.diff(time) != 60)]
    started = np.maximum.accumulate(np.where(pump_start, np.arange(len(rows)), -1))
    def timing(now):
        i = np.searchsorted(time, now, side="right")-1
        if i < 0 or now-time[i] > 60 or prev[i] < 0:
            return np.nan, np.nan
        latest = prev[i]
        age = 0 if pumping[i] else max(0, now-time[latest]-60)
        left = started[latest]
        earlier = prev[left-1] if left else -1
        pause = max(0, time[left]-time[earlier]-60) if earlier >= 0 else np.nan
        return age, pause
    return timing


def development():
    definitions = {row["eow_bha"]: row for row in read(VALIDATION/"forge16b/run_definitions.csv")}
    plan = json.loads((VALIDATION/"forge16b/s2/plan.json").read_text(encoding="utf-8"))
    primary = {r["id"] for r in plan["samples"] if r.get("source") == "Sanvean on-bottom"}
    sample_times = {r["id"]: r["time_s"] for r in plan["samples"]}
    timing = {well: circulation_timing(well) for well in ("16A", "16B")}
    for row in read(HERE/"formation-and-sensor-samples.csv"):
        well, run = row["well"], row["run"]
        sensor = (number(row.get("bit_box_C_residual")) if row["sample_id"] in primary else np.nan) if well == "16A" else (
            number(row.get("published_sensor_C"))-number(row.get("measured_sensor_C")))
        return_error = number(row.get("published_return_C"))-number(row.get("measured_return_C"))
        motor = definitions[run]["motor"] if well == "16B" else "yes"
        age, pause = timing[well](sample_times[row["sample_id"]])
        yield dict(well=well, run=run, bit_ft=number(row["bit_ft"]), tvd_ft=number(row.get("tvd_m"))/.3048,
                   flow_gpm=number(row["flow_gpm"]), inlet_C=number(row["inlet_C"]),
                   density_ppg=number(row["density_ppg"]), pv_cP=number(row["pv_cP"]),
                   yp=number(row["yp_lbf_100ft2"]), motor=motor, formation_C=number(row.get("published_formation_C")),
                   return_residual_C=return_error, sensor_residual_C=sensor,
                   pipe=definitions[run]["pipe_type"] if well == "16B" else "regular",
                   seconds_since_circulation=age, preceding_pause_s=pause, sample_id=row["sample_id"])


def coverage(forecast, source):
    form = a.formation("216", a.survey())[0]
    for r in forecast:
        r["formation_C"] = float(form(number(r["tvd_ft"])*.3048))
    cols = ("bit_ft", "tvd_ft", "flow_gpm", "inlet_C", "density_ppg", "pv_cP",
            "yp", "formation_C", "seconds_since_circulation", "preceding_pause_s")
    groups = {name: [r for r in source if r["well"] == name] for name in ("16A", "16B")}
    groups["56-32 drilling"] = [r for r in forecast if r["kind"] == "drilling"]
    groups["56-32 trip stages"] = [r for r in forecast if r["kind"] == "trip_stage"]
    groups["56-32 drilling pauses"] = [r for r in forecast if r["kind"] not in ("trip_stage", "drilling")]
    for group, rows in groups.items():
        for col in cols:
            yield dict(group=group, quantity=col, records=len(rows)) | stats(numeric(rows, col))


def matched_ranges(forecast, source):
    """Use fixed engineering bands and report coverage with each interval."""
    # Fixed matching widths: 500 m TVD, 100 US gal/min, 10 K inlet and
    # 0.7 lbm/gal density. All limits operate on inputs only.
    widths = {"tvd_ft": 500/.3048, "flow_gpm": 100., "inlet_C": 10., "density_ppg": .7}
    for row in forecast:
        if row["kind"] != "drilling":
            continue
        candidates = [r for r in source if r["motor"] == row["motor"] and
                      all(abs(r[k]-number(row[k])) <= width for k, width in widths.items())]
        for measure in ("return", "sensor"):
            pool = numeric(candidates, f"{measure}_residual_C")
            pool = pool[np.isfinite(pool)]
            out = dict(sample_id=row["sample_id"], measure=measure, matched=len(pool),
                       comparison="development residuals, model minus observation")
            if len(pool) >= 3:
                lo, hi = np.quantile(pool, [.10,.90])
                out |= dict(inferred_p10_C=lo, inferred_p90_C=hi)
            yield out


def trip_ranges(forecast):
    previous = VALIDATION/"model-development/entry-14/results/entry14-amended/entry14/run-in.csv"
    details = {r["event_id"]: r for r in read(VALIDATION/"forge16a/transient-events.csv")}
    scores = [(number(details[r["event_id"]]["depth_end_ft"]), number(r["peak_error_C"]))
              for r in read(previous) if r["success"] == "True"]
    for row in forecast:
        if row["kind"] == "trip_stage":
            end = number(row["bit_ft"])
            match = [error for depth, error in scores if abs(depth-end)*.3048 <= 500]
            out = dict(sample_id=row["sample_id"], matched=len(match), end_md_ft=end,
                       measure="run-in peak", basis="500 m MD end-depth band, 16A partial legs")
            if len(match) >= 3:
                lo, hi = np.quantile(match, [.10,.90])
                out |= dict(inferred_p10_C=lo, inferred_p90_C=hi)
            yield out


def main():
    forecast, source = read(FORECAST/"conditions.csv"), list(development())
    records(HERE/"56-32-condition-coverage.csv", coverage(forecast, source))
    records(HERE/"56-32-conditional-residual-ranges.csv", matched_ranges(forecast, source))
    records(HERE/"56-32-trip-analogues.csv", trip_ranges(forecast))
    counts = Counter((r["well"], r["motor"], r["pipe"]) for r in source)
    records(HERE/"development-assembly-mix.csv",
            (dict(well=well, motor=motor, pipe=pipe, count=count)
             for (well, motor, pipe), count in sorted(counts.items())))


if __name__ == "__main__":
    main()
