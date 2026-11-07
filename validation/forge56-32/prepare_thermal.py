"""Select model-only forecast conditions and count temperature availability."""
import argparse
from collections import Counter
import csv
import gzip
from importlib import import_module
import io
import json
from pathlib import Path
import zipfile

import numpy as np

from validation.forge16b.sanvean.build_extracts import iso, number, records, sha, timestamp
from validation.forge16b.sanvean.events import History, pause_class

pressure = import_module("validation.forge56-32.compare_pressure")
HERE = Path(__file__).resolve().parent
CHANNELS = {"mwd": "MWD Temp (Fahrenheit)", "return": "Temp OUT (Degrees)"}


def read_rig():
    with gzip.open(HERE/"rig_inputs_10s.csv.gz", "rt", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    time = np.array([timestamp(r["time"]) for r in rows])
    cols = {key: np.array([number(row[key]) for row in rows]) for key in
            ("bit_depth_ft", "hole_depth_ft", "flow_gpm", "rpm", "rop_ft_h",
             "inlet_temperature_source_degrees", "invalid_flow_count")}
    cols["flow_gpm"][cols["invalid_flow_count"] != 0] = np.nan
    return History(time, cols["bit_depth_ft"], cols["hole_depth_ft"], cols["flow_gpm"],
                   cols["rpm"], 10), cols["rop_ft_h"], (cols["inlet_temperature_source_degrees"]-32)/1.8


def bha_for(date, hole, runs, trip=False):
    possible = []
    for run in runs:
        end = run["date_out"] or "2021-02-15"   # BHA 5 is the only blank end date.
        if (run["date_in"] <= date <= end
                and float(run["depth_in_ft"])-(5 if trip else 0) <= hole <= float(run["depth_out_ft"])):
            possible.append(run["bha_sheet_id"])
    return possible[0] if len(possible) == 1 else ""


def mean(values):
    valid = values[np.isfinite(values)]
    return float(valid.mean()) if len(valid) else np.nan


def forecast_conditions(history, rop, inlet):
    mud = pressure.read("mud_reports.csv")
    # The 6 March sample prints 33 ppg alongside 97.6% water.
    # Keep that source row in the archive and withhold it from assignment.
    mud = [r for r in mud if not (r["sample_date"] == "2021-03-06" and r["mud_weight_ppg"] == "33.00")]
    runs = pressure.read("bha_crosswalk.csv")
    survey = pressure.survey()
    bit, hole, flow, time = history.bit, history.hole, history.flow, history.time
    valid = (flow > 300) & (np.abs(bit-hole) <= 5) & (rop > 1)
    bins = (time+900)//1800
    runs_for_bin = [bha_for(iso(time[i])[:10], hole[i], runs) for i in np.flatnonzero(valid)]
    assignments = dict(zip(np.flatnonzero(valid), runs_for_bin))
    lead = list(history.spells(flow > 100))
    ends = np.array([time[j-1]+10 for _, j in lead])

    def row(kind, stamp, bit_ft, hole_ft, q, tin, first, end, bha, **extra):
        previous = np.searchsorted(ends, first, side="right")-1
        lead_start, lead_end = lead[previous] if previous >= 0 else (None, None)
        prev_pause = (time[lead_start]-ends[previous-1]) if previous >= 1 else np.nan
        base = dict(kind=kind, time=iso(stamp), sample_start=iso(first), sample_end=iso(end),
                    bit_ft=bit_ft, tvd_ft=float(survey.tvd(bit_ft*pressure.FT))/pressure.FT,
                    hole_ft=hole_ft, bha=bha, motor="yes" if bha else "", flow_gpm=q, inlet_C=tin,
                    seconds_since_circulation=(0 if q > 100 else first-ends[previous]) if previous >= 0 else np.nan,
                    preceding_pause_s=prev_pause)
        try:
            base.update(pressure.mud_for(iso(stamp), hole_ft, mud))
        except ValueError:
            pass
        if lead_start is not None:
            sl = slice(lead_start, lead_end)
            prior_bit, prior_hole = mean(bit[sl]), mean(hole[sl])
            base.update(preceding_flow_gpm=mean(flow[sl]), preceding_inlet_C=mean(inlet[sl]),
                        preceding_bit_ft=prior_bit, preceding_hole_ft=prior_hole,
                        preceding_bha=bha_for(iso(time[lead_end-1])[:10], prior_hole, runs, trip=True),
                        preceding_circ_start=iso(time[lead_start]), preceding_circ_end=iso(ends[previous]),
                        preceding_duration_s=ends[previous]-time[lead_start])
        return base | extra

    for bin_id in np.unique(bins[valid]):
        take = np.flatnonzero(valid & (bins == bin_id))
        if len(take) < 90 or np.ptp(hole[take]) < .5:
            continue
        bhas = {assignments[i] for i in take}
        centre = int(bin_id)*1800
        yield row("drilling", centre, mean(bit[take]), mean(hole[take]), mean(flow[take]),
                  mean(inlet[take]), centre-900, centre+900,
                  next(iter(bhas)) if len(bhas) == 1 else "", qualified_bins=len(take))
    for left, right, prior in history.drilling_pauses():
        start, end = history.bounds(left, right)
        depths = bit[left:right]
        movement = np.ptp(depths[np.isfinite(depths)]) if np.isfinite(depths).any() else np.nan
        if movement > 100:
            continue
        h = mean(hole[left:right])
        bha = bha_for(iso(time[left])[:10], h, runs)
        yield row(pause_class(end-start), start, mean(depths), h, mean(flow[left:right]),
                  mean(inlet[prior:left]), start, end, bha, bit_movement_ft=movement)
    reached = history._bottom_rows()
    for prev, bottom in zip(np.r_[-1, reached[:-1]], reached):
        if prev == bottom-1:
            continue
        stop = int(bottom)
        start = int(prev+1)
        # An input gap or a change of hole section can shorten an observed trip.
        start = max(start, np.searchsorted(time, time[stop]-86400))
        valid = np.flatnonzero(np.isfinite(bit[start:stop]) & (bit[start:stop] >= 0.) &
                               (np.abs(hole[start:stop]-hole[stop]) <= 20.)) + start
        if not len(valid):
            continue
        lowest = valid[np.flatnonzero(bit[valid] == bit[valid].min())[-1]]
        if bit[stop]-bit[lowest] < 500:
            continue
        bha = bha_for(iso(time[stop])[:10], hole[stop], runs, trip=True)
        for left, right, c0, c1 in history.trip_stages(lowest, stop):
            begin, end = history.bounds(left, right)
            observed = bit[left:right]
            finite = observed[np.isfinite(observed)]
            if len(finite) < 2 or finite[-1] <= finite[0]:
                continue
            movement = np.diff(finite)
            if -movement[movement<0].sum() > .1*movement[movement>0].sum():
                continue
            yield row("trip_stage", begin, finite[-1], hole[stop], mean(flow[left:right]),
                      mean(inlet[left:right]), begin, end, bha, bit_start_ft=finite[0],
                      partial_trip=bit[lowest] > 100.,
                      following_flow_gpm=mean(flow[c0:c1]) if c0 is not None else np.nan,
                      following_duration_s=history.duration(c0,c1) if c0 is not None else np.nan)


def available_counts(archive, history, samples, output):
    """Collect only finite/null flags for the two reserved temperature channels."""
    # Keep target counts in time bins without retaining any measured values.
    availability = np.zeros((len(history.time), len(CHANNELS)), dtype=np.uint16)
    differential = np.zeros(len(history.time))
    differential_n = np.zeros(len(history.time), dtype=np.uint16)
    by_pump = Counter()
    time_index = {stamp: i for i, stamp in enumerate(history.time)}
    with zipfile.ZipFile(archive) as outer, zipfile.ZipFile(io.BytesIO(outer.read("56-32_Pason_Archive.zip"))) as inner:
        for member in sorted(inner.namelist()):
            if not member.endswith(".csv") or "__MACOSX" in member:
                continue
            with io.TextIOWrapper(inner.open(member), encoding="utf-8-sig", newline="") as stream:
                reader = csv.reader(stream)
                header = next(reader)
                date, clock, flow = (header.index(k) for k in
                                     ("YYYY/MM/DD", "HH:MM:SS", "Total Pump Output (gal_per_min)"))
                ids = [header.index(k) for k in CHANNELS.values()]
                dp_index = header.index("Differential Pressure (psi)")
                for row in reader:
                    if not row:
                        continue
                    stamp = timestamp(row[date]+" "+row[clock])
                    idx = time_index.get(stamp//10*10)
                    rate = number(row[flow])
                    state = ("pumping" if 100 < rate <= 2000 else
                             "off" if 0 <= rate < 50 else "other_or_missing")
                    by_pump[state, "rows"] += 1
                    dp = number(row[dp_index])
                    if idx is not None and state == "pumping" and np.isfinite(dp):
                        differential[idx] += dp
                        differential_n[idx] += 1
                    for column, (name, j) in enumerate(zip(CHANNELS, ids)):
                        present = np.isfinite(number(row[j]))
                        by_pump[state, name] += int(present)
                        if present and idx is not None:
                            availability[idx, column] += 1
    records(output/"availability-by-pump.csv", (
        {"pump_state": state, "rows": by_pump[state, "rows"]} |
        {f"{k}_available": by_pump[state, k] for k in CHANNELS}
        for state in ("pumping", "off", "other_or_missing")))
    for sample in samples:
        lo, hi = np.searchsorted(history.time, [timestamp(sample["sample_start"]), timestamp(sample["sample_end"])])
        sample.update({f"{k}_available_rows": int(availability[lo:hi, j].sum())
                       for j, k in enumerate(CHANNELS)})
        if sample["kind"] == "drilling":
            selected = (history.flow[lo:hi] > 300) & (np.abs(history.bit[lo:hi]-history.hole[lo:hi]) <= 5)
            sums, counts = differential[lo:hi][selected], differential_n[lo:hi][selected]
            sample["motor_differential_psi"] = sums.sum()/counts.sum() if counts.sum() else np.nan
        if sample.get("preceding_circ_start"):
            a, b = np.searchsorted(history.time, [timestamp(sample["preceding_circ_start"]), timestamp(sample["preceding_circ_end"])])
            counts = differential_n[a:b].sum()
            sample["preceding_motor_differential_psi"] = differential[a:b].sum()/counts if counts else np.nan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    h, rop, inlet = read_rig()
    samples = sorted(forecast_conditions(h, rop, inlet), key=lambda row: (row["time"], row["kind"]))
    for i, sample in enumerate(samples, 1):
        sample["sample_id"] = f"56b-{i:04}"
    available_counts(args.archive, h, samples, args.output)
    records(args.output/"conditions.csv", samples)
    source = dict(submission="GDR 1295", archive_sha256=sha(args.archive),
                  member="56-32_Pason_Archive.zip",
                  thermal_access="finite/null availability only")
    (args.output/"source-availability.json").write_text(
        json.dumps(source, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(Counter(r["kind"] for r in samples))


if __name__ == "__main__":
    main()
