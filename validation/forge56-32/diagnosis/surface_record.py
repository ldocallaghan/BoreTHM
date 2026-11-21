"""Build the 56-32 surface temperature record from the Pason archive.

usage: surface_record.py ARCHIVE OUTPUT [--bins PATH]

ARCHIVE is GDR 1295 (`1295.zip`), read in place. One pass over the four
weekly Pason files collects sums and counts of the channels below in 10 s
bins. OUTPUT receives:

  surface_record_10min.csv  8 February to 1 March 2021 at 10-minute
                            resolution, with the active assembly
  window_surface.csv        means over the qualified seconds of each
                            scored drilling window
  pvt_tank_selection.csv    every change of the PVT tank selection codes
  surface_record-source.json  archive hash, members, rules and counts

`Temp IN` and `Temp OUT` are converted with (F-32)/1.8 and a converted
second outside 0 to 120 C is missing, as the scoring protocol does for the
return. --bins also writes the 10 s sums and counts (gzip CSV).
"""
import argparse
import csv
from datetime import datetime, timedelta
import gzip
import hashlib
from importlib import import_module
import io
import json
import math
from pathlib import Path
import zipfile

import numpy as np

from validation.forge16b.sanvean.build_extracts import iso, number, timestamp

prepare = import_module("validation.forge56-32.prepare_thermal")
HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
CHANNELS = {
    "inlet_C": "Temp IN (Degrees)",
    "return_C": "Temp OUT (Degrees)",
    "mwd_C": "MWD Temp (Fahrenheit)",
    "flow_gpm": "Total Pump Output (gal_per_min)",
    "spp_psi": "Standpipe Pressure (psi)",
    "differential_psi": "Differential Pressure (psi)",
    "bit_ft": "Bit Depth (feet)",
    "hole_ft": "Hole Depth (feet)",
    "mud_volume_bbl": "Total Mud Volume (barrels)",
    "trip_tank_bbl": "Trip Tank 1 Volume (barrels)",
    **{f"tank{i}_bbl": f"Mud Tank {i} Volume (barrels)" for i in range(1, 6)},
}
CODES = {"pvt_tanks_included": "PVT Mud Tanks Included (unitless)",
         "pvt_tanks_included_2": "PVT Mud Tanks Included 2 (unitless)"}
FAHRENHEIT = ("inlet_C", "return_C", "mwd_C")
RANGES = {"inlet_C": (0., 120.), "return_C": (0., 120.), "mwd_C": (0., 250.),
          "flow_gpm": (0., 2000.), "spp_psi": (0., 10000.), "differential_psi": (-2000., 5000.)}
START, END = datetime(2021, 2, 8), datetime(2021, 3, 2)
TEN_MINUTES = 600


def sha256(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def valid(key, value):
    if not math.isfinite(value):
        return False
    low, high = RANGES.get(key, (-math.inf, math.inf))
    return low < value <= high if key in FAHRENHEIT else low <= value <= high


def read_bins(archive):
    """Sums and counts in 10 s bins, keyed by the bin's start in seconds,
    and every change of the PVT tank selection codes."""
    sums, counts = {}, {}
    members, changes, current = [], [], dict.fromkeys(CODES)
    with zipfile.ZipFile(archive) as outer, \
            zipfile.ZipFile(io.BytesIO(outer.read("56-32_Pason_Archive.zip"))) as inner:
        for member in sorted(inner.namelist()):
            if not member.endswith(".csv") or "__MACOSX" in member:
                continue
            rows = 0
            with io.TextIOWrapper(inner.open(member), encoding="utf-8-sig", newline="") as stream:
                reader = csv.reader(stream)
                header = next(reader)
                date, clock = header.index("YYYY/MM/DD"), header.index("HH:MM:SS")
                index = {key: header.index(name) for key, name in CHANNELS.items()}
                codes = {key: header.index(name) for key, name in CODES.items()}
                for row in reader:
                    if not row:
                        continue
                    rows += 1
                    second = timestamp(row[date]+" "+row[clock])
                    for key, i in codes.items():
                        value = row[i].strip()
                        if value and value != current[key]:
                            changes.append(dict(time=iso(second), channel=CODES[key],
                                                before=current[key] or "", after=value))
                            current[key] = value
                    stamp = second//10*10
                    s = sums.setdefault(stamp, dict.fromkeys(CHANNELS, 0.))
                    c = counts.setdefault(stamp, dict.fromkeys(CHANNELS, 0))
                    for key, i in index.items():
                        value = number(row[i])
                        if key in FAHRENHEIT:
                            value = (value-32)/1.8
                        if valid(key, value):
                            s[key] += value
                            c[key] += 1
            members.append(dict(member=member, rows=rows))
            print(member, rows, "rows", flush=True)
    return sums, counts, members, changes


def assembly(date, hole_ft, runs):
    """The assembly whose calendar dates and depth interval hold the record, if unique."""
    if not math.isfinite(hole_ft):
        return ""
    return prepare.bha_for(date, hole_ft, runs, trip=True)


def ten_minute_table(sums, counts, runs):
    rows = []
    first, last = timestamp(START.isoformat(sep=" ")), timestamp(END.isoformat(sep=" "))
    for start in range(first, last, TEN_MINUTES):
        total = dict.fromkeys(CHANNELS, 0.)
        n = dict.fromkeys(CHANNELS, 0)
        pumping = 0
        for stamp in range(start, start+TEN_MINUTES, 10):
            if stamp not in sums:
                continue
            for key in CHANNELS:
                total[key] += sums[stamp][key]
                n[key] += counts[stamp][key]
            if counts[stamp]["flow_gpm"] and sums[stamp]["flow_gpm"]/counts[stamp]["flow_gpm"] > 100:
                pumping += 1
        row = dict(time=iso(start))
        for key in CHANNELS:
            row[key] = total[key]/n[key] if n[key] else ""
            if key in ("inlet_C", "return_C", "flow_gpm"):
                row[key+"_seconds"] = n[key]
        row["pumping_bins"] = pumping
        row["return_minus_inlet_C"] = (row["return_C"]-row["inlet_C"]
                                       if row["return_C"] != "" and row["inlet_C"] != "" else "")
        row["bha"] = assembly(row["time"][:10], row["hole_ft"] if row["hole_ft"] != "" else math.nan, runs)
        rows.append(row)
    return rows


def window_table(sums, counts):
    """Per-second means over each scored window's qualified 10 s bins."""
    extract = import_module("validation.forge56-32.extract_return_temperature")
    score = import_module("validation.forge56-32.score_thermal")
    _, owner = extract.qualified_bins()
    scored = {r["sample_id"]: r for r in score.read_csv(STUDY/"scores/windows.csv") if r["status"] == "scored"}
    conditions = {r["sample_id"]: r for r in score.read_csv(STUDY/"predictions-v1.8.0/conditions.csv")}
    bins = {}
    for stamp, sample in owner.items():
        if sample in scored:
            bins.setdefault(sample, []).append(stamp)
    rows = []
    for sample in sorted(scored):
        w, inputs = scored[sample], conditions[sample]
        row = dict(sample_id=sample, time=w["time"], bha=w["bha"], bit_ft=w["bit_ft"],
                   tvd_ft=inputs["tvd_ft"], hole_ft=inputs["hole_ft"], density_ppg=inputs["density_ppg"],
                   forecast_flow_gpm=w["flow_gpm"], forecast_inlet_C=w["inlet_C"],
                   measured_return_C=w["measured_C"], v180_return_C=w["v1.8.0"])
        for key in CHANNELS:
            n = sum(counts.get(s, {}).get(key, 0) for s in bins[sample])
            total = sum(sums.get(s, {}).get(key, 0.) for s in bins[sample])
            row[key] = total/n if n else ""
            row[key+"_seconds"] = n
        rows.append(row)
    return rows


def write(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_bins(path, sums, counts):
    with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["time", *(f"{k}_sum" for k in CHANNELS), *(f"{k}_n" for k in CHANNELS)])
        for stamp in sorted(sums):
            writer.writerow([iso(stamp), *(repr(sums[stamp][k]) for k in CHANNELS),
                             *(counts[stamp][k] for k in CHANNELS)])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--bins", type=Path)
    args = parser.parse_args()
    sums, counts, members, changes = read_bins(args.archive)
    runs = prepare.pressure.read("bha_crosswalk.csv")
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output/"surface_record_10min.csv", ten_minute_table(sums, counts, runs))
    write(args.output/"pvt_tank_selection.csv", changes)
    write(args.output/"window_surface.csv", window_table(sums, counts))
    if args.bins:
        write_bins(args.bins, sums, counts)
    source = dict(submission="GDR 1295", archive_sha256=sha256(args.archive),
                  member="56-32_Pason_Archive.zip", files=members, channels=CHANNELS,
                  conversion="(F-32)/1.8 for " + ", ".join(FAHRENHEIT),
                  valid_ranges={k: list(v) for k, v in RANGES.items()},
                  temperature_range_rule="a converted second at or below the lower bound or above the upper bound is missing",
                  assembly_rule="prepare_thermal.bha_for with the trip allowance, on the 10-minute mean hole depth",
                  period=[START.isoformat(sep=" "), END.isoformat(sep=" ")])
    (args.output/"surface_record-source.json").write_text(json.dumps(source, indent=2)+"\n",
                                                           encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
