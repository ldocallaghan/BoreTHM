"""Describe finite MWD record intervals using rig inputs and availability only."""
import argparse
import csv
import io
import math
from pathlib import Path
import zipfile

from validation.forge16b.sanvean.build_extracts import iso, number, records, timestamp


def intervals(archive):
    with zipfile.ZipFile(archive) as outer:
        with zipfile.ZipFile(io.BytesIO(outer.read("56-32_Pason_Archive.zip"))) as rig:
            for name in sorted(rig.namelist()):
                if not name.endswith(".csv") or "__MACOSX" in name:
                    continue
                with io.TextIOWrapper(rig.open(name), encoding="utf-8-sig", newline="") as stream:
                    reader = csv.DictReader(stream)
                    for row in reader:
                        if not math.isfinite(number(row.get("MWD Temp (Fahrenheit)"))):
                            continue
                        yield (timestamp(row["YYYY/MM/DD"]+" "+row["HH:MM:SS"]),
                               number(row["Bit Depth (feet)"]), number(row["Hole Depth (feet)"]),
                               number(row["Total Pump Output (gal_per_min)"]))


def summarise(rows):
    group = []
    for row in rows:
        if group and row[0] != group[-1][0]+1:
            yield summary(group)
            group = []
        group.append(row)
    if group:
        yield summary(group)


def summary(group):
    out = dict(start=iso(group[0][0]), end=iso(group[-1][0]), seconds=len(group))
    for i, key in enumerate(("bit_ft", "hole_ft", "pump_gpm"), 1):
        values = [row[i] for row in group if math.isfinite(row[i])]
        out[key+"_min"] = min(values) if values else ""
        out[key+"_max"] = max(values) if values else ""
    out["pumping_seconds"] = sum(100 < r[3] <= 2000 for r in group)
    out["drilling_candidate_seconds"] = sum(300 < r[3] <= 2000 and abs(r[1]-r[2]) <= 5 for r in group)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    records(args.output, summarise(intervals(args.archive)))


if __name__ == "__main__":
    main()
