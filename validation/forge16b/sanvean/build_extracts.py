"""Build source extracts from GDR 1561 exports and selected GDR 1516 Pason data."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timedelta
import gzip
import hashlib
import io
import math
from pathlib import Path
import re

import numpy as np

from validation.forge16b.sanvean.events import History, availability, pause_class

HERE = Path(__file__).resolve().parent
EPOCH = datetime(1970, 1, 1)
EXPORTS = (
    "FORGE 16B(78)-32 May13-18_new - SN5105 - output data.csv",
    "FORGE 16B(78)-32 - May13-16 - 5104_new - run 1 - output data.csv",
    "FORGE 16B(78)-32 - May13-16 - 5104_new - run 2 - output data.csv",
    "FORGE 16B(78)-32 - May17-27 - 2232_new - run 1. - slice 001. - output data.csv",
    "FORGE 16B(78)-32 - May17-27 - 2232_new - run 2. - slice 001. - slice 001. - output data.csv",
    "FORGE 16B(78)-32 - May17-27 - 2232_new - run 3. - slice 001. - output data.csv",
    "FORGE 16B(78)-32 - May17-27 - 2232_new - run 4. - slice 001. - slice 001. - output data.csv",
)
SURFACE = {
    "hole_depth_ft": ("Hole Depth", "MD"),
    "bit_depth_ft": ("Bit Depth", "BitDepth"),
    "flow_gpm": ("Total Pump Output", "Flow"),
    "spp_psi": ("Standpipe Pressure", "SPP"),
    "hook_load_klbs": ("Hook Load", "Hookload"),
    "block_height_ft": ("Block Height", "BlockPosition"),
    "rotary_rpm": ("Rotary RPM", "RotRPM"),
}
TEMPS = {
    "sanvean_C": r"SN\d+_Temperature\(C\)",
    "bb_mean_C": r"Black Box_BBHF_Temp_mean\(C\)",
    "bb_min_C": r"Black Box_BBHF_Temp_min\(C\)",
    "bb_max_C": r"Black Box_BBHF_Temp_max\(C\)",
    "eye_C": r"Black Box_EYE_TEMP\(au\)",
    "custom2_C": r"Custom_Custom2\(C\)",
}
TARGETS = tuple(TEMPS)[:-1]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def number(text):
    try:
        x = float(text)
    except (ValueError, TypeError):
        return math.nan
    return x if math.isfinite(x) and x != -999.25 else math.nan


def timestamp(value):
    return int((datetime.fromisoformat(value.replace("/", "-")) - EPOCH).total_seconds())


def iso(value):
    return (EPOCH + timedelta(seconds=int(value))).isoformat(sep=" ")


def serial(value):
    return "" if isinstance(value, float) and not math.isfinite(value) else value


def write(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        data = gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) if path.suffix == ".gz" else raw
        with io.TextIOWrapper(data, encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(fields)
            writer.writerows(tuple(map(serial, row)) for row in rows)


def read_export(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.reader(line for line in stream if not line.startswith("#"))
        header = next(row for row in rows if row and row[0] == "DateTime")
        def index(pattern):
            return next((i for i, name in enumerate(header) if re.fullmatch(pattern, name)), None)

        surfaces = [index(rf"Surface_{name}\([^)]*\)") for name, _ in SURFACE.values()]
        flow_index = list(SURFACE).index("flow_gpm")
        if surfaces[flow_index] is None:
            surfaces[flow_index] = index(r"Surface_Flow\(GPM\)")
        copies = [index(rf"Black Box_{name}\([^)]*\)") for _, name in SURFACE.values()]
        memory = index(r"SN\d+_Memory Index\(counts\)")
        loss = index(r"SN\d+_Data Loss\(%\)")
        temps = [index(pattern) for pattern in TEMPS.values()]
        positions = surfaces + [memory, loss] + copies + temps
        selected = {}
        repeats = 0
        for row in rows:
            if not row or not row[0]:
                continue
            stamp = timestamp(row[0])
            repeats += stamp in selected
            selected[stamp] = tuple(number(row[i]) if i is not None and i < len(row) else math.nan
                                    for i in positions)
    stamps = sorted(selected)
    values = np.array([selected[s] for s in stamps]).T
    available = np.isfinite(values[-len(temps):])
    data = dict(zip((*SURFACE, "memory_index", "data_loss_pct"), values))
    comparison = {}
    for i, name in enumerate(SURFACE):
        surface, copy = values[i], values[len(surfaces) + 2 + i]
        paired = np.isfinite(surface) & np.isfinite(copy)
        delta = np.abs(surface[paired] - copy[paired])
        comparison[name] = (int(paired.sum()), int((delta < 1e-6).sum()),
                            float(np.mean(delta)) if len(delta) else math.nan,
                            float(np.max(delta)) if len(delta) else math.nan)
    return (np.array(stamps, dtype=np.int64), data, available, values[-len(temps):],
            repeats, comparison, header[surfaces[flow_index]])


def read_pason(path, start, end):
    columns = ("time", "bit_depth_ft", "hole_depth_ft", "flow_gpm", "temp_in_F", "temp_out_F")
    rows = []
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            t = timestamp(row["time"])
            if start <= t <= end:
                rows.append((t, *(number(row[k]) for k in columns[1:])))
    if not rows:
        raise ValueError("no overlapping Pason rows")
    return np.array(rows).T


def nearest_indices(reference, t):
    right = np.clip(np.searchsorted(reference, t), 1, len(reference) - 1)
    left = right - 1
    return np.where(np.abs(t - reference[left]) <= np.abs(t - reference[right]), left, right)


def clock_offset(time, bit, flow, pason):
    """Maximise mean Pearson correlation of bit-depth and flow levels."""
    pt, pb, _, pf = pason[:4]
    select = (pt >= time[0] + 7200) & (pt <= time[-1] - 7200)
    pt, pb, pf = pt[select], pb[select], pf[select]
    if len(pt) < 50:
        raise ValueError("too little common history for clock alignment")

    def scores(offset):
        shifted = pt - offset
        i = nearest_indices(time, shifted)
        matched = np.abs(time[i] - shifted) <= 1
        result = []
        for a, b in ((pb, bit[i]), (pf, flow[i])):
            ok = matched & np.isfinite(a) & np.isfinite(b)
            if ok.sum() < max(30, len(pt) // 2) or min(np.std(a[ok]), np.std(b[ok])) == 0:
                return -np.inf, -np.inf
            result.append(float(np.corrcoef(a[ok], b[ok])[0, 1]))
        return tuple(result)

    def best(offsets):
        return max(((o, *scores(o)) for o in offsets), key=lambda x: ((x[1]+x[2])/2, -abs(x[0])))

    coarse, *_ = best(range(-7200, 7201, 10))
    result = best(range(max(-7200, coarse - 9), min(7200, coarse + 9) + 1))
    if not np.isfinite(result[1]):
        raise ValueError("flow and depth could not be correlated")
    return result


def temperatures(raw):
    output = raw[:len(TARGETS)].copy()
    output[4] = (output[4] - 32.) / 1.8
    return output


def event_records(history, available, loss, *, amended=False):
    for stage, (left, right, c0, c1) in enumerate(history.trip_stages(), 1):
        start, end = history.bounds(left, right)
        circulation = (None, None) if c0 is None else history.bounds(c0, c1)
        row = {
            "id": f"stage-{stage:02}", "kind": "trip_stage", "start": iso(start), "end": iso(end),
            "duration_s": end-start, "bit_start_ft": history.bit[left],
            "bit_end_ft": history.bit[right-1],
            "off_s": int(((history.flow[left:right] >= 0) & (history.flow[left:right] < 50)).sum()),
            "mean_trip_ft_min": 60 * (history.bit[right-1] - history.bit[left]) / (end-start),
            "circ_start": "" if c0 is None else iso(circulation[0]),
            "circ_end": "" if c0 is None else iso(circulation[1]),
            "circ_duration_s": "" if c0 is None else circulation[1]-circulation[0],
            "circ_mean_gpm": "" if c0 is None else np.mean(history.flow[c0:c1]),
        }
        yield row | event_flags(history, available, loss, start, end, circulation[0] if amended else None, False, amended=amended)
    pauses = (history.ramped_pauses() if amended else
              ((left, right, lead, left, None) for left, right, lead in history.drilling_pauses()))
    for event, (left, right, lead, lead_end, pump) in enumerate(pauses, 1):
        start, end = history.bounds(left, right)
        bit = history.bit[left:right]
        movement = np.ptp(bit[np.isfinite(bit)]) if np.isfinite(bit).any() else math.nan
        rotation = history.rpm[left:right]
        row = {
            "id": f"pause-{event:02}", "kind": pause_class(end-start), "start": iso(start),
            "end": iso(end), "duration_s": end-start, "bit_start_ft": bit[0], "bit_end_ft": bit[-1],
            "hole_start_ft": history.hole[left], "movement_ft": movement,
            "mean_rpm": np.mean(rotation[np.isfinite(rotation)]) if np.isfinite(rotation).any() else math.nan,
            "preceding_duration_s": history.duration(lead, lead_end),
            "preceding_mean_gpm": np.mean(history.flow[lead:lead_end]),
        }
        next_pumping = np.flatnonzero((history.time >= end) & (history.flow > 100))
        restart = int(history.time[next_pumping[0]]) if len(next_pumping) else None
        if amended:
            restart = int(history.time[pump])
        row["pump_on"] = iso(restart) if restart is not None else ""
        yield row | event_flags(history, available, loss, start, end, restart, movement > 100, amended=amended)


def event_flags(history, masks, loss, start, end, restart, moved, *, amended=False):
    observed = (history.time >= start) & (history.time < end)
    if restart is not None:
        observed |= (history.time >= restart) & (history.time < restart+300)
    high_loss = bool(np.any(loss[observed] > 1))
    if amended:
        valid_loss = loss[observed & np.isfinite(loss)]
        mean_loss = float(valid_loss.mean()) if len(valid_loss) else math.nan
        high_loss = mean_loss > 1
    flags = {"bit_moved_over_100ft": moved, "sanvean_data_loss_over_1pct": high_loss}
    if amended:
        flags["sanvean_mean_data_loss_pct"] = mean_loss
    for key, mask in zip(TEMPS, masks):
        fraction, gap = availability(history, mask, start, end)
        post_fraction, post_gap = (availability(history, mask, restart, restart+300)
                                   if restart is not None else ("", 0))
        flags[f"{key}_fraction"] = fraction
        flags[f"{key}_post_fraction"] = post_fraction
        flags[f"{key}_gap_s"] = max(gap, post_gap)
        flags[f"{key}_eligible"] = max(gap, post_gap) <= 10 and not moved and not (high_loss and (not amended or key in ("sanvean_C", "custom2_C")))
    return flags


def describe(history, events, temps):
    bit, black_box = temps[:2]
    time = history.time
    for event in events:
        start, end = timestamp(event["start"]), timestamp(event["end"])
        stage = event["kind"] == "trip_stage"
        pump = (timestamp(event["circ_start"]) if event["circ_start"] else None) if stage else end
        if not stage:
            pump = timestamp(event["pump_on"]) if event["pump_on"] else None
        circ_end = timestamp(event["circ_end"]) if stage and event["circ_end"] else None
        for label, value in (("bit", bit), ("black_box", black_box)):
            result = {"event_id": event["id"], "class": event["kind"], "sensor": label,
                      "pump_on": iso(pump) if pump is not None else ""}
            for prefix, mask in (
                ("during", (time >= start) & (time < end)),
                ("restart", (time >= pump) & (time < pump+300) if pump is not None else time < 0),
            ):
                indices = np.flatnonzero(mask & np.isfinite(value))
                if len(indices):
                    i = indices[np.argmax(value[indices])]
                    result |= {f"{prefix}_peak_C": value[i], f"{prefix}_peak_time": iso(time[i]),
                               f"{prefix}_bit_minus_black_box_C": bit[i]-black_box[i]}
                    if pump is not None:
                        result[f"{prefix}_peak_seconds_from_pump_on"] = time[i]-pump
                    if prefix == "during":
                        result["event_end_minus_start_C"] = value[indices[-1]]-value[indices[0]]
            if circ_end is not None:
                indices = np.flatnonzero((time >= pump) & (time < circ_end) & np.isfinite(value))
                if len(indices):
                    result["end_circulation_C"] = value[indices[-1]]
                steady = (time >= pump+300) & (time < circ_end) & np.isfinite(bit-black_box)
                if steady.any():
                    result["steady_mean_bit_minus_black_box_C"] = np.mean((bit-black_box)[steady])
            yield result


def records(path, rows):
    rows = list(rows)
    fields = tuple(dict.fromkeys(key for row in rows for key in row))
    write(path, fields, ([row.get(k, "") for k in fields] for row in rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exports", type=Path)
    parser.add_argument("pason_selected", type=Path)
    parser.add_argument("--output", type=Path, default=HERE)
    args = parser.parse_args()
    manifest, checks, counts, alignment = [], [], [], []
    for run, filename in enumerate(EXPORTS, 11):
        source = args.exports / filename
        time, data, present, raw, duplicates, comparison, flow_source = read_export(source)
        history = History(time, data["bit_depth_ft"], data["hole_depth_ft"],
                          data["flow_gpm"], data["rotary_rpm"], 1)
        rig = read_pason(args.pason_selected, time[0]-172800, time[-1]+7200)
        try:
            offset, bit_r, flow_r = clock_offset(time, history.bit, history.flow, rig)
            alignment.append(dict(eow_bha=run, pason_minus_sanvean_s=offset,
                                  bit_depth_r=bit_r, flow_r=flow_r))
        except ValueError as error:
            offset = None
            alignment.append(dict(eow_bha=run, status=str(error)))
        temp = temperatures(raw)
        data.update({f"{key}_available": present[i].astype(int) for i, key in enumerate(TEMPS)})
        out_file = args.output / f"bha-{run}-inputs.csv.gz"
        info = dict(eow_bha=run, source=filename, source_sha256=sha(source), rows=len(time),
                    duplicates=duplicates, flow_source=flow_source)
        if run == 17:
            data.update(zip(TARGETS, temp))
            if offset is not None:
                corrected = time + offset
                i = nearest_indices(rig[0], corrected)
                for key, x in zip(("pason_temp_in_C", "pason_temp_out_C"), rig[4:6]):
                    data[key] = np.where(np.abs(rig[0][i]-corrected) <= 5, (x[i]-32.)/1.8, np.nan)
            else:
                data["pason_temp_in_C"] = data["pason_temp_out_C"] = np.full(len(time), np.nan)
        else:
            sealed = args.output / "sealed" / f"bha-{run}-temperatures.csv.gz"
            write(sealed, ("time", *TARGETS), zip(map(iso, time), *temp))
            info |= dict(sealed_sha256=sha(sealed), sealed_rows=len(time),
                         sealed_values_outside_range=int(np.count_nonzero((temp < -10) | (temp > 350))))
        write(out_file, ("time", *data), zip(map(iso, time), *data.values()))
        manifest.append(info | dict(input_sha256=sha(out_file)))
        for key, (paired, equal, mean, maximum) in comparison.items():
            checks.append(dict(eow_bha=run, channel=key, paired=paired, equal=equal,
                               mean_absolute_difference=mean, max_absolute_difference=maximum))
        events = list(event_records(history, present, data["data_loss_pct"]))
        records(args.output / f"bha-{run}-events.csv", events)
        classes = ("trip_stage", "connection", "stop", "long_stop")
        for kind in classes:
            subset = [event for event in events if event["kind"] == kind]
            counts.append(dict(eow_bha=run, event_class=kind, candidates=len(subset)) |
                          {f"{key}_eligible": sum(event[f"{key}_eligible"] for event in subset)
                           for key in TEMPS})
        if run == 17:
            records(args.output / "bha-17-development.csv", describe(history, events, temp))
            eye = temp[-1]
            changed = np.r_[False, np.isfinite(eye[1:]) & np.isfinite(eye[:-1]) & (eye[1:] != eye[:-1])]
            records(args.output / "bha-17-eye-updates.csv", (
                dict(flow_class=kind, seconds=int(mask.sum()), available=int(np.sum(mask & np.isfinite(eye))),
                     changed=int(np.sum(mask & changed)))
                for kind, mask in (("pumps_on", history.flow > 100),
                                   ("pumps_off", (history.flow >= 0) & (history.flow < 50)))))
        print(f"EOWR {run}: {len(time)} rows, {len(events)} events", flush=True)
    records(args.output / "extracts.csv", manifest)
    records(args.output / "surface-channel-comparison.csv", checks)
    records(args.output / "event-counts.csv", counts)
    records(args.output / "clock-alignment.csv", alignment)


if __name__ == "__main__":
    main()
