"""Extract the measured return temperature for the scored 56-32 drilling windows.

usage: extract_return_temperature.py ARCHIVE OUTPUT [--r2-counts PATH]

ARCHIVE is GDR 1295 (`1295.zip`). Only the date, time and `Temp OUT (Degrees)`
columns of the four weekly Pason files are read, and `Temp OUT` only for the
qualified seconds of windows with converged predictions. The rules are in the
scoring protocol. OUTPUT receives return_temperature.csv and its SHA-256.
"""
import argparse
import csv
from importlib import import_module
import io
import math
from pathlib import Path
import zipfile

import numpy as np

from validation.forge16b.sanvean.build_extracts import number, timestamp

prepare = import_module("validation.forge56-32.prepare_thermal")
score = import_module("validation.forge56-32.score_thermal")
CHANNEL = "Temp OUT (Degrees)"


def qualified_bins():
    """Map each qualified 10 s bin time to its predicted drilling window."""
    history, rop, _ = prepare.read_rig()
    bit, hole, flow, time = history.bit, history.hole, history.flow, history.time
    valid = (flow > 300) & (np.abs(bit-hole) <= 5) & (rop > 1)
    bins = (time+900)//1800
    owner = {}
    windows = [w for w in score.drilling_windows() if w["predicted"]]
    for w in windows:
        centre = timestamp(w["time"])
        if centre % 1800:
            raise ValueError(f"{w['sample_id']}: window centre is not on the half hour")
        take = time[valid & (bins == centre//1800)]
        if len(take) != w["qualified_bins"]:
            raise ValueError(f"{w['sample_id']}: {len(take)} qualified bins against {w['qualified_bins']}")
        for stamp in take:
            owner[int(stamp)] = w["sample_id"]
    return [w["sample_id"] for w in windows], owner


def extract(archive, owner, ids):
    tally = {k: dict(qualified_seconds=0, finite_seconds=0, r2_missing=0, total=0.,
                     low=math.inf, high=-math.inf) for k in ids}
    with zipfile.ZipFile(archive) as outer, \
            zipfile.ZipFile(io.BytesIO(outer.read("56-32_Pason_Archive.zip"))) as inner:
        for member in sorted(inner.namelist()):
            if not member.endswith(".csv") or "__MACOSX" in member:
                continue
            with io.TextIOWrapper(inner.open(member), encoding="utf-8-sig", newline="") as stream:
                reader = csv.reader(stream)
                header = next(reader)
                date, clock, column = (header.index(k) for k in ("YYYY/MM/DD", "HH:MM:SS", CHANNEL))
                for row in reader:
                    if not row:
                        continue
                    sample = owner.get(timestamp(row[date]+" "+row[clock])//10*10)
                    if sample is None:
                        continue
                    entry = tally[sample]
                    entry["qualified_seconds"] += 1
                    reading = number(row[column])
                    if not math.isfinite(reading):
                        continue
                    value = score.to_celsius(reading)
                    if not score.valid_second(value):
                        entry["r2_missing"] += 1
                        continue
                    entry["finite_seconds"] += 1
                    entry["total"] += value
                    entry["low"] = min(entry["low"], value)
                    entry["high"] = max(entry["high"], value)
    return tally


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--r2-counts", type=Path, help="write the seconds set missing by R2 for each window")
    args = parser.parse_args()
    ids, owner = qualified_bins()
    bins = {w["sample_id"]: w["qualified_bins"] for w in score.drilling_windows() if w["predicted"]}
    tally = extract(args.archive, owner, ids)
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output/"return_temperature.csv"
    with open(target, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, score.TARGET_FIELDS, lineterminator="\n")
        writer.writeheader()
        for sample in sorted(ids):
            entry = tally[sample]
            n = entry["finite_seconds"]
            writer.writerow(dict(sample_id=sample, qualified_bins=bins[sample],
                                 qualified_seconds=entry["qualified_seconds"], finite_seconds=n,
                                 mean_C=repr(entry["total"]/n) if n else "",
                                 min_C=repr(entry["low"]) if n else "", max_C=repr(entry["high"]) if n else "",
                                 unit_conversion=score.UNIT_CONVERSION))
    digest = score.sha256(target)
    (args.output/"return_temperature.csv.sha256").write_text(
        f"{digest}  return_temperature.csv\n", encoding="utf-8", newline="\n")
    if args.r2_counts:
        with open(args.r2_counts, "w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["sample_id", "qualified_seconds", "r2_missing_seconds"])
            for sample in sorted(ids):
                writer.writerow([sample, tally[sample]["qualified_seconds"], tally[sample]["r2_missing"]])
    print("windows", len(ids), "sha256", digest)
    print("R2 missing seconds", sum(e["r2_missing"] for e in tally.values()),
          "in", sum(e["r2_missing"] > 0 for e in tally.values()), "windows")


if __name__ == "__main__":
    main()
