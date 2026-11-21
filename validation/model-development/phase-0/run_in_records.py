"""Attribute the frozen 16A run-in observations using source clocks and depths."""
import argparse
from collections import defaultdict
import csv
import io
import json
from pathlib import Path
import zipfile

import numpy as np

from borethm.studies import validate_forge16a as a
from validation.forge16b.sanvean.build_extracts import iso, number, records, timestamp

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = "16A(78)-32_time_data_10s_intervals_standard.csv"


def rig(archive):
    acc = defaultdict(list)
    with zipfile.ZipFile(archive) as z, io.TextIOWrapper(z.open(SOURCE), encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        next(reader)  # unit row
        for row in reader:
            stamp = timestamp(row["Date"])
            acc[stamp].append([number(row[key]) for key in ("Pump Pressure", "Flow In", "Bit Depth")])
    stamps = sorted(acc)
    def mean_valid(values):
        x = np.array(values)
        n = np.isfinite(x).sum(axis=0)
        return np.divide(np.nansum(x, axis=0), n, out=np.full(x.shape[1], np.nan), where=n > 0)
    return np.array(stamps), np.array([mean_valid(acc[t]) for t in stamps]).T


def alignment(rig_time, pressure, sample):
    """Correlate pressure against the rig's minute clock."""
    merged = defaultdict(list)
    for row in sample:
        value = number(row["pump_pressure_psi"])
        if np.isfinite(value):
            merged[timestamp(row["time"])//60*60].append(value)
    if not merged:
        return []
    ticks = np.array(sorted(merged))
    measured = np.array([np.mean(merged[t]) for t in ticks])
    candidates = []
    for offset in range(-7200, 7201, 60):
        t = ticks+offset
        index = np.clip(np.searchsorted(rig_time, t), 0, len(rig_time)-1)
        good = (rig_time[index] == t) & np.isfinite(pressure[index])
        if good.sum() >= max(20, len(ticks)//2):
            c = np.corrcoef(pressure[index][good], measured[good])[0, 1]
            candidates.append((offset, float(c), int(good.sum())))
    return candidates


def legs(events, rig_time, rig_flow, rig_bit, source):
    path = a.survey()
    form = a.formation("216", path)[0]
    for event in events:
        name, run = event["event_id"], event["run"]
        rows = source[run]
        i, j = int(event["start_i"]), int(event["end_i"])+1
        time = np.array([timestamp(row["time"]) for row in rows])
        bit = np.array([number(row["bit_depth_ft"]) for row in rows])
        flow = np.array([number(row["flow_gpm"]) for row in rows])
        bad = np.array([number(row["invalid_flow_count"]) for row in rows])
        value = np.array([number(row["bit_box_C"]) for row in rows])
        pressure = np.array([number(row["pump_pressure_psi"]) for row in rows])
        stamped = np.arange(len(time))
        after = (stamped >= j) & (time <= time[j-1]+900)
        candidates = np.flatnonzero(after & (flow > 100) & (flow <= 2000) & (bad == 0))
        pump = time[candidates[0]] if len(candidates) else None
        observed = np.flatnonzero((stamped >= i) & (stamped < j) & np.isfinite(value))
        peak = observed[np.argmax(value[observed])]
        state = "restart outside the available window" if pump is None else "before pump-on" if time[peak] < pump else "after pump-on"
        restart = np.flatnonzero((time >= pump) & (time < pump+300) & np.isfinite(value)) if pump is not None else []
        end_peak = restart[np.argmax(value[restart])] if len(restart) else None
        near = np.flatnonzero((stamped >= i) & (time < pump if pump is not None else stamped < j)
                              & (np.abs(bit-np.array([number(r["hole_depth_ft"]) for r in rows])) <= 5))
        dwell = int(pump-time[near[0]]) if len(near) and pump is not None else ""
        local = slice(i, j)
        form_at_bit = form(path.tvd(bit[local]*a.FT))
        temperature = value[local]
        deltas = np.diff(temperature)
        changes = np.flatnonzero(np.r_[True, (deltas != 0), True])
        flat = max(np.diff(changes), default=0)*10
        spike = int(np.sum((np.abs(deltas[:-1]) > 10) & (np.abs(deltas[1:]) > 10)
                           & (deltas[:-1]*deltas[1:] < 0)))
        reports = [r for r in a.read("bha_components.csv") if r["BHA"] == run[:2]]
        floats = [r["component"] for r in reports if "float" in r["component"].lower()]
        carrier = next(r for r in a.read("run_inputs.csv") if r["run"] == run)
        record = dict(event_id=name, run=run, channel="bit_box_C", start=iso(time[i]), end=iso(time[j-1]+10),
                      bit_box_reported_offset_ft=carrier["bit_box_offset_ft"],
                      PUK_carrier_bottom_ft=carrier["reported_PUK_sub_bottom_ft_above_bit"],
                      PUK_carrier_top_ft=carrier["reported_PUK_sub_top_ft_above_bit"],
                      peak_C=value[peak], peak_time=iso(time[peak]), peak_phase=state,
                      pump_on=iso(pump) if pump is not None else "",
                      peak_seconds_from_pump_on=time[peak]-pump if pump is not None else "",
                      pressure_at_peak_psi=pressure[peak], pump_on_pressure_psi=pressure[candidates[0]] if len(candidates) else "",
                      dwell_at_bottom_s=dwell, above_formation_bins=int(np.sum(temperature > form_at_bit)),
                      isolated_temperature_spike_bins=spike, longest_flatline_s=flat,
                      float_record=" / ".join(sorted(set(floats))) if floats else "no explicit float entry")
        if end_peak is not None:
            record.update(restart_5min_peak_C=value[end_peak], restart_5min_peak_time=iso(time[end_peak]),
                          restart_peak_seconds_from_pump_on=time[end_peak]-pump)
        profile = []
        local_depths = bit[local][np.isfinite(bit[local])]
        for depth in np.arange(np.ceil(local_depths[0]/25)*25, local_depths[-1]+1, 25.):
            passing = np.flatnonzero((stamped >= i) & (stamped < j) & (bit >= depth))
            if not len(passing):
                continue
            reached = time[passing[0]]
            local_circ = np.flatnonzero((time < reached) & (bit >= depth) & (flow > 100) & (flow <= 2000) & (bad == 0))
            prior = np.flatnonzero((rig_time < reached-60) & (rig_bit >= depth) & (rig_flow > 100) & (rig_flow <= 2000))
            last_local = time[local_circ[-1]]+10 if len(local_circ) else -np.inf
            last_rig = rig_time[prior[-1]]+60 if len(prior) else -np.inf
            last = max(last_local, last_rig)
            profile.append(dict(event_id=name, depth_ft=depth, pass_time=iso(reached),
                                last_pumped_at_depth=iso(last) if np.isfinite(last) else "",
                                static_s=reached-last if np.isfinite(last) else "",
                                source="Sanvean 10 s" if last_local >= last_rig and np.isfinite(last)
                                else "Pason minute" if np.isfinite(last) else "missing"))
        yield record, profile


def paired_steps(source):
    for run, rows in source.items():
        t = np.array([timestamp(r["time"]) for r in rows])
        flow = np.array([number(r["flow_gpm"]) for r in rows])
        bit = np.array([number(r["bit_depth_ft"]) for r in rows])
        hole = np.array([number(r["hole_depth_ft"]) for r in rows])
        flag = np.array([number(r["on_bottom_flag"]) for r in rows])
        delta = np.array([number(r["bit_box_C"])-number(r["top_sub_C"]) for r in rows])
        stable = np.isfinite(delta+bit+hole+flow+flag) & (flow > 100) & (flow <= 2000)
        masks = {"on": stable & (flag > .5) & (np.abs(bit-hole) <= 5),
                 "off": stable & (flag <= .5) & (hole-bit > 5)}
        classified = np.flatnonzero(masks["on"] | masks["off"])
        for left, right in zip(classified[:-1], classified[1:]):
            first_state = "on" if masks["on"][left] else "off"
            second_state = "off" if first_state == "on" else "on"
            if not masks[second_state][right] or t[right]-t[left] > 120:
                continue
            before = np.flatnonzero(masks[first_state] & (t >= t[left]-120) & (t <= t[left]))[-6:]
            after = np.flatnonzero(masks[second_state] & (t >= t[right]) & (t <= t[right]+120))[:6]
            if len(before) != 6 or len(after) != 6:
                continue
            if masks[second_state][before[0]:left+1].any() or masks[first_state][right:after[-1]+1].any():
                continue
            rates = flow[np.r_[before, after]]
            if np.ptp(rates) <= 25:
                yield dict(run=run, time=iso(t[right]), from_state=first_state, mean_flow_gpm=float(rates.mean()),
                           bit_minus_top_before_C=float(delta[before].mean()),
                           bit_minus_top_after_C=float(delta[after].mean()))


def raw_peak_checks(archive, events):
    by_run = defaultdict(list)
    for event in events:
        by_run[event["run"]].append((event["event_id"], timestamp(event["start"]),
                                    timestamp(event["end_last_bin"])+10))
    manifest = {r["run"]: r for r in json.loads((a.DATA/"sanvean_sources.json").read_text(encoding="utf-8"))}
    checks = {event["event_id"]: {"raw_flow_above_100000_count": 0} for event in events}
    with zipfile.ZipFile(archive) as top, top.open("Forge 16A(78)-32 Sanvean Log.zip") as inner:
        with zipfile.ZipFile(inner) as logs:
            for run, intervals in by_run.items():
                source = manifest[run]
                with zipfile.ZipFile(io.BytesIO(logs.read(source["archive"]))) as data:
                    with io.TextIOWrapper(data.open(source["csv"]), encoding="utf-8-sig", newline="") as stream:
                        reader = csv.DictReader(line for line in stream if line.strip() and not line.startswith("#"))
                        for row in reader:
                            t = timestamp(row["DateTime"])
                            for event, start, end in intervals:
                                if not start <= t < end:
                                    continue
                                values = checks[event]
                                temperature = number(row.get("Bit Box_Temperature(C)"))
                                flow = number(row.get("Surface_Flow In(GPM)"))
                                values["raw_flow_above_100000_count"] += int(flow > 100000)
                                if np.isfinite(temperature) and temperature > values.get("raw_peak_C", -np.inf):
                                    values.update(raw_peak_C=temperature, raw_peak_time=iso(t),
                                                  raw_flow_at_peak_gpm=flow)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rig_archive", type=Path)
    parser.add_argument("sanvean_archive", type=Path)
    args = parser.parse_args()
    t, (pressure, flow, bit) = rig(args.rig_archive)
    plan = json.loads((ROOT/"scoreboard/transient-inputs.json").read_text(encoding="utf-8"))
    events = [r for r in plan["events"] if r["kind"] == "run-in leg"]
    source = {r["run"]: a.read(f"sanvean_BHA{r['run']}_10s.csv") for r in a.read("run_inputs.csv")}
    offsets = []
    dst = timestamp("2020-11-01 02:00:00")
    for run, rows in source.items():
        for label, selection in (("before", [r for r in rows if timestamp(r["time"]) < dst]),
                                 ("after", [r for r in rows if timestamp(r["time"]) >= dst])):
            options = alignment(t, pressure, selection)
            if options:
                offset, correlation, pairs = max(options, key=lambda x: x[1])
                offsets.append(dict(run=run, dst_side=label, rig_minus_sanvean_s=offset,
                                    pressure_r=correlation, paired_minutes=pairs))
    if not any(row["dst_side"] == "before" for row in offsets):
        offsets.append(dict(run="all", dst_side="before", status="no overlapping Sanvean pressure records"))
    records(HERE/"16a-pressure-clock.csv", offsets)
    raw = raw_peak_checks(args.sanvean_archive, events)
    details, times = [], []
    for row, profile in legs(events, t, flow, bit, source):
        details.append(row | raw[row["event_id"]])
        times.extend(profile)
    records(HERE/"16a-run-in-attribution.csv", details)
    records(HERE/"16a-static-time-by-depth.csv", times)
    records(HERE/"16a-bit-and-top-sub-steps.csv", paired_steps(source))


if __name__ == "__main__":
    main()
