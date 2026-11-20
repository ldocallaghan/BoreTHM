"""Count available readings of the 78B-32 temperature channels without their values.

Each sealed cell is passed to `finite` and only the resulting flag is kept.
For the two downhole channels a second flag records an update: a finite
reading that differs from the channel's previous finite reading. The
previous reading is held in memory for that one comparison only. No sealed
value is stored, printed or written. The open rig inputs (time,
bit and hole depth, pump output, on-bottom rate of penetration) select the
drilling windows by the 56-32 rule:

- a ten-second bin qualifies when pump output is above 300 US gal/min, the
  bit is within 5 ft of hole depth and on-bottom ROP is above 1 ft/h;
- windows are centred on the hour and half hour and cover the half-open
  interval from 15 minutes before to 15 minutes after;
- a window needs at least 90 qualified bins and at least 0.5 ft of new hole.

The assembly condition of the rule needs the assembly assignment, which is
built with the inputs; these counts are made before it and do not apply it.

The bins are the rows of the ten-second export. Rows of the two `_standard`
exports join a bin when their time truncated to ten seconds equals the bin
time. A row of the ten-second export can carry more cells than its heading
because the last column holds free text; columns are read by position and
the free-text cells are never read.

Usage: python count_availability.py ARCHIVE OUTPUT_DIR
"""
import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
import io
import json
import math
from pathlib import Path
import zipfile

import numpy as np

TEN_S = "78B-32 10 sec data 27200701.csv"
STD_10S = "78B-32 10 sec data 27200701_standard.csv"
STD_1S = "78B-32 1 sec data 27200701_standard.csv"

# Open inputs of the ten-second export.
OPEN_10S = {
    "bit_ft": "Bit Depth (feet)",
    "hole_ft": "Hole Depth (feet)",
    "pump_gpm": "Total Pump Output (gal_per_min)",
    "rop_ft_h": "On Bottom ROP (ft_per_hr)",
}
# Channels counted as flags only. TEMP IN is an open input and is counted
# beside the others for comparison.
FLAGS_10S = {
    "mwd_temp": "MWD Temp (Fahrenheit) (no_unit)",
    "eye_temp": "EYE TEMP (F) (no_unit)",
    "temp_out": "TEMP OUT (Degrees) (no_unit)",
    "temp_in": "TEMP IN (Degrees) (no_unit)",
}
FLAGS_STD = {
    "tool_temperature": "Tool Temperature",
    "mud_temperature": "Mud Temperature",
    "return_flow": "Return Flow",
}
UPDATES = ("mwd_temp", "eye_temp")
BAND_FT = 1000
R1_SHARE = 0.8


def number(text):
    try:
        x = float(text)
    except (TypeError, ValueError):
        return math.nan
    return x if math.isfinite(x) and x != -999.25 else math.nan


def finite(text):
    return math.isfinite(number(text))


def epoch(text):
    stamp = datetime.strptime(text.replace("-", "/"), "%Y/%m/%d %H:%M:%S")
    return int(stamp.replace(tzinfo=timezone.utc).timestamp())


def day(t):
    return datetime.fromtimestamp(int(t), timezone.utc).date().isoformat()


def iso(t):
    return datetime.fromtimestamp(int(t), timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def rows(zf, member, skip=0):
    with io.TextIOWrapper(zf.open(member), encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        for _ in range(skip):
            next(reader)
        yield header
        for row in reader:
            if row:
                yield row


def read_ten_second(zf, notes):
    it = rows(zf, TEN_S)
    header = next(it)
    di, ti = header.index("YYYY/MM/DD"), header.index("HH:MM:SS")
    open_ix = {k: header.index(v) for k, v in OPEN_10S.items()}
    flag_ix = {k: header.index(v) for k, v in FLAGS_10S.items()}
    width = len(header)
    time, values, flags = [], defaultdict(list), defaultdict(list)
    wide = 0
    last = {k: None for k in UPDATES}
    for row in it:
        wide += len(row) > width
        time.append(epoch(row[di] + " " + row[ti]))
        for k, j in open_ix.items():
            values[k].append(number(row[j]))
        for k, j in flag_ix.items():
            flags[k].append(finite(row[j]))
        for k in UPDATES:
            x = number(row[flag_ix[k]])
            changed = math.isfinite(x) and last[k] is not None and x != last[k]
            flags[k + "_update"].append(changed)
            if math.isfinite(x):
                last[k] = x
            del x
    time = np.array(time)
    notes["ten_second_rows"] = len(time)
    notes["ten_second_rows_wider_than_heading"] = wide
    notes["ten_second_rows_off_ten_second_mark"] = int((time % 10 != 0).sum())
    notes["ten_second_clock_reversals"] = int((np.diff(time) < 0).sum())
    bins = time // 10 * 10
    notes["ten_second_duplicate_bins"] = int(len(bins) - len(np.unique(bins)))
    return (bins, {k: np.array(v) for k, v in values.items()},
            {k: np.array(v, dtype=bool) for k, v in flags.items()})


def read_standard(zf, member, index, notes, key, bit_10s=None):
    """Return per-bin row counts and finite counts of the standard channels."""
    it = rows(zf, member, skip=1)          # second heading line holds units
    header = next(it)
    di = header.index("Date")
    flag_ix = {k: header.index(v) for k, v in FLAGS_STD.items()}
    bit_ix = header.index("Bit Depth")
    size = max(index.values()) + 1
    count = np.zeros(size, dtype=np.int32)
    finite_count = {k: np.zeros(size, dtype=np.int32) for k in FLAGS_STD}
    totals = Counter()
    bit_checked = bit_agree = 0
    for row in it:
        t = epoch(row[di])
        totals["rows"] += 1
        flags = {k: finite(row[j]) for k, j in flag_ix.items()}
        for k, f in flags.items():
            totals[k] += f
        i = index.get(t // 10 * 10)
        if i is None:
            totals["rows_without_ten_second_bin"] += 1
            continue
        count[i] += 1
        for k, f in flags.items():
            finite_count[k][i] += f
        if bit_10s is not None and t % 10 == 0:
            a, b = number(row[bit_ix]), bit_10s[i]
            if math.isfinite(a) and math.isfinite(b):
                bit_checked += 1
                bit_agree += int(abs(a - b) <= 0.5)
    notes[key] = dict(totals)
    if bit_10s is not None:
        notes[key]["bit_depth_compared_at_ten_second_marks"] = bit_checked
        notes[key]["bit_depth_within_0.5_ft"] = bit_agree
    return count, finite_count


def write_csv(path, records):
    records = list(records)
    fields = list(dict.fromkeys(k for r in records for k in r))
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fields, lineterminator="\n")
        w.writeheader()
        w.writerows(records)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    notes = {}
    with zipfile.ZipFile(args.archive) as zf:
        notes["members"] = {m: dict(bytes=zf.getinfo(m).file_size, crc32=f"{zf.getinfo(m).CRC:08x}")
                            for m in (TEN_S, STD_10S, STD_1S)}
        bins, val, flag = read_ten_second(zf, notes)
        index = {}
        for i, b in enumerate(bins):
            index.setdefault(int(b), i)
        c10, f10 = read_standard(zf, STD_10S, index, notes, "standard_10s", bit_10s=val["bit_ft"])
        c1, f1 = read_standard(zf, STD_1S, index, notes, "standard_1s")

    # Per-row availability on the ten-second bins. A bin taken by a duplicate
    # row keeps the first row's standard counts only.
    first = np.zeros(len(bins), dtype=bool)
    first[list(index.values())] = True
    avail = {k: flag[k] for k in FLAGS_10S}
    for k in FLAGS_STD:
        avail[k + "_10s"] = (f10[k] > 0) & first
    one_s_rows = np.where(first, c1, 0)
    one_s_finite = {k: np.where(first, f1[k], 0) for k in FLAGS_STD}

    bit, hole, pump, rop = val["bit_ft"], val["hole_ft"], val["pump_gpm"], val["rop_ft_h"]
    with np.errstate(invalid="ignore"):
        qualified = (pump > 300) & (np.abs(bit - hole) <= 5) & (rop > 1)
    days = np.array([day(b) for b in bins])
    band = np.where(np.isfinite(bit), np.floor(np.nan_to_num(bit, nan=0) / BAND_FT) * BAND_FT, np.nan)

    def tally(mask):
        out = dict(bins=int(mask.sum()))
        for k, a in avail.items():
            out[k] = int((a & mask).sum())
        out["rows_1s"] = int(one_s_rows[mask].sum())
        for k in FLAGS_STD:
            out[k + "_1s"] = int(one_s_finite[k][mask].sum())
        return out

    by_day = []
    for d in sorted(set(days)):
        m = days == d
        by_day.append(dict(day=d, scope="all") | tally(m))
        by_day.append(dict(day=d, scope="qualified_bins") | tally(m & qualified))
    write_csv(args.output / "availability-by-day.csv", by_day)

    by_band = []
    for b in sorted(set(band[np.isfinite(band)])):
        m = band == b
        label = f"{int(b)}-{int(b + BAND_FT)}"
        by_band.append(dict(bit_depth_ft=label, scope="all") | tally(m))
        by_band.append(dict(bit_depth_ft=label, scope="qualified_bins") | tally(m & qualified))
    by_band.append(dict(bit_depth_ft="missing", scope="all") | tally(~np.isfinite(band)))
    write_csv(args.output / "availability-by-depth.csv", by_band)

    window_id = (bins + 900) // 1800
    windows = []
    for w in np.unique(window_id[qualified]):
        take = np.flatnonzero(qualified & (window_id == w))
        if len(take) < 90 or np.ptp(hole[take]) < 0.5:
            continue
        rec = dict(centre=iso(int(w) * 1800), qualified_bins=len(take),
                   hole_from_ft=round(float(hole[take].min()), 1),
                   hole_to_ft=round(float(hole[take].max()), 1),
                   mean_bit_ft=round(float(np.nanmean(bit[take])), 1),
                   mean_pump_gpm=round(float(np.nanmean(pump[take])), 1))
        for k in ("mwd_temp", "eye_temp", "tool_temperature_10s", "temp_out", "mud_temperature_10s", "temp_in"):
            rec[k] = int(avail[k][take].sum())
        for k in UPDATES:
            rec[k + "_updates"] = int(flag[k + "_update"][take].sum())
        rec["qualified_seconds_1s"] = int(one_s_rows[take].sum())
        rec["tool_temperature_1s"] = int(one_s_finite["tool_temperature"][take].sum())
        rec["mud_temperature_1s"] = int(one_s_finite["mud_temperature"][take].sum())
        windows.append(rec)
    write_csv(args.output / "availability-windows.csv", windows)

    def coverage(key, denominator):
        meet = sum(1 for r in windows if r[denominator] and r[key] / r[denominator] >= R1_SHARE)
        return dict(windows_at_least_80_percent=meet,
                    windows_with_any=sum(1 for r in windows if r[key] > 0),
                    finite_in_windows=sum(r[key] for r in windows),
                    possible_in_windows=sum(r[denominator] for r in windows))

    summary = dict(
        windows=len(windows),
        qualified_bins=int(qualified.sum()),
        assembly_condition="not applied",
        coverage={
            "mwd_temp": coverage("mwd_temp", "qualified_bins"),
            "eye_temp": coverage("eye_temp", "qualified_bins"),
            "tool_temperature_10s": coverage("tool_temperature_10s", "qualified_bins"),
            "tool_temperature_1s": coverage("tool_temperature_1s", "qualified_seconds_1s"),
            "temp_out": coverage("temp_out", "qualified_bins"),
            "temp_in": coverage("temp_in", "qualified_bins"),
        },
        joint_availability_10s={},
        notes=notes,
    )
    pairs = [("mwd_temp", "tool_temperature_10s"), ("eye_temp", "tool_temperature_10s"),
             ("mwd_temp", "eye_temp"), ("temp_out", "mud_temperature_10s"),
             ("temp_in", "mud_temperature_10s")]
    for a, b in pairs:
        x, y = avail[a] & first, avail[b] & first
        summary["joint_availability_10s"][f"{a} | {b}"] = dict(
            both=int((x & y).sum()), first_only=int((x & ~y).sum()),
            second_only=int((~x & y).sum()), neither=int((~x & ~y & first).sum()))
    (args.output / "availability-summary.json").write_text(
        json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: summary[k] for k in ("windows", "qualified_bins", "coverage")}, indent=1))


if __name__ == "__main__":
    main()
