"""Inventory GDR 1006 thermal records by metadata and availability alone."""
import argparse
from collections import defaultdict
import csv
from datetime import datetime
import gzip
import io
from pathlib import Path
import re
import zipfile

import numpy as np
from openpyxl import load_workbook

from validation.forge16b.sanvean.build_extracts import iso, number, records, timestamp

HERE = Path(__file__).resolve().parent


def rig_inputs():
    with gzip.open(HERE/"rig_inputs_10s.csv.gz", "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = ("time", "flow_gpm", "bit_depth_ft", "inlet_temperature_source_degrees")
        return [(timestamp(r["time"]), *(number(r[key]) for key in fields[1:])) for r in reader]


def coverage(history, when):
    stamps, flow, bit, inlet = history.T
    t = timestamp(when)
    q = np.isfinite(flow)
    prior = np.flatnonzero(q & (flow > 100) & (stamps < t))
    nearby = (stamps < t) & (stamps >= t-24*3600)
    if not nearby.any() or not len(prior):
        return dict(coverage="no nearby rig history")
    i = prior[-1]
    tail = (stamps >= stamps[i]) & (stamps <= t)
    expected = max(1, int((t-stamps[i])/10))
    complete = (np.isfinite(flow[tail]+bit[tail]+inlet[tail]).sum() >= .98*expected)
    return dict(last_above_100gpm_bin=iso(stamps[i]), seconds_since_last_pumped_bin=t-int(stamps[i]),
                prior_24h_input_bins=int(nearby.sum()), prior_24h_flow_bins=int(np.sum(q & nearby)),
                prior_24h_bit_bins=int(np.sum(np.isfinite(bit) & nearby)),
                prior_24h_inlet_bins=int(np.sum(np.isfinite(inlet) & nearby)),
                coverage="near-continuous from last pumped bin" if complete else "gaps in history since last pumped bin")


def las_metadata(archive, name):
    meta = {}
    curves = []
    mode = ""
    count = available = 0
    with io.TextIOWrapper(archive.open(name), encoding="latin1") as stream:
        for raw in stream:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("~"):
                mode = line[1].upper()
                continue
            if mode == "W" and "." in line:
                key, data = line.split(".", 1)
                meta[key.strip()] = data.split(":", 1)[0].strip()
            elif mode == "C":
                curves.append(line.split(".", 1)[0].strip())
            elif mode == "A":
                count += 1
                col = curves.index("T")
                row = line.split()
                available += int(len(row) > col and np.isfinite(number(row[col])))
    when = datetime.strptime(meta["DATE"], "%a %b %d %H-%M-%S %Y")
    axis_start, axis_end = (float(meta[k].split()[-1]) for k in ("STRT", "STOP"))
    depth = re.search(r"\d+", meta.get("TDL1", ""))
    return when, axis_start, axis_end, count, available, int(depth[0]) if depth else ""


def profile_inventory(archive, history):
    for name in archive.namelist():
        if not name.endswith(".las"):
            continue
        when, start, end, n, available, logger_depth = las_metadata(archive, name)
        timed = "_TIME" in name
        if not timed:
            row = dict(depth_start_ft=start, depth_end_ft=end)
        else:
            row = dict(elapsed_start_s=start, elapsed_end_s=end, logger_depth_ft=logger_depth)
        yield dict(source=name, kind="PT time series" if timed else "PT depth log",
                   header_log_date=when.isoformat(sep=" "), records=n, temperature_available=available) | row | coverage(history, when.isoformat())
    name = "PT/Nov 2 PT survey.xlsx"
    book = load_workbook(io.BytesIO(archive.read(name)), read_only=True, data_only=True)
    sheet = book["Sheet1"]
    depths = []
    available = 0
    # Columns A/B contain the imperial depth and temperature representation.
    # The metric columns duplicate it and are not counted as new records.
    for depth, temperature in sheet.iter_rows(min_row=2, min_col=1, max_col=2, values_only=True):
        if isinstance(depth, (int, float)) and np.isfinite(depth):
            depths.append(depth)
            available += int(isinstance(temperature, (int, float)) and np.isfinite(number(temperature)))
    yield dict(source=name, kind="PT depth log", header_log_date="2017-11-02",
               records=len(depths), temperature_available=available, depth_start_ft=min(depths),
               depth_end_ft=max(depths), coverage="outside dated Pason coverage")


def return_inventory(archive):
    def file_date(name):
        return datetime.strptime(Path(name).stem, "%m-%d-%y")
    last_pump = None
    files = [name for name in archive.namelist() if name.lower().endswith(".csv")]
    for name in sorted(files, key=file_date):
        if not name.lower().endswith(".csv"):
            continue
        with io.TextIOWrapper(archive.open(name), encoding="latin1", newline="") as stream:
            reader = csv.reader(stream)
            header = next((r for r in reader if r and r[0] == "Date"), None)
            if header is None:
                yield dict(source=name, kind="surface return", coverage="rig header absent")
                continue
            idx = [header.index(k) if k in header else None
                   for k in ("Depth", "Bit Depth", "Flow In", "Temp In", "Temp Out")]
            needed = max(i for i in idx if i is not None)
            rows = available = inputs = 0
            lo = float("inf")
            hi = float("-inf")
            first = last = ""
            age = []
            for row in reader:
                if len(row) <= needed or not row[0] or not row[0][0].isdigit():
                    continue
                stamp = row[0]+" "+row[1]
                if not first:
                    first = stamp
                last = stamp
                rows += 1
                depth, bit, flow, inlet = (number(row[i]) if i is not None else np.nan for i in idx[:-1])
                t = datetime.strptime(stamp, "%m/%d/%Y %H:%M:%S")
                if 100 < flow <= 2000:
                    last_pump = t
                if np.isfinite(depth):
                    lo, hi = min(lo, depth), max(hi, depth)
                inputs += int(np.isfinite(bit+flow+inlet))
                has_return = idx[-1] is not None and np.isfinite(number(row[idx[-1]]))
                available += int(has_return)
                if has_return and last_pump is not None and t >= last_pump:
                    age.append((t-last_pump).total_seconds())
            yield dict(source=name, kind="surface return", first_rig_time=first, last_rig_time=last,
                       records=rows, temperature_available=available, depth_start_ft=lo, depth_end_ft=hi,
                       all_circulation_input_rows=inputs,
                       return_rows_with_pumped_history=len(age),
                       min_seconds_since_pumped=min(age) if age else "",
                       max_seconds_since_pumped=max(age) if age else "",
                       coverage=("flow, inlet and bit-depth counts on the same source clock"
                                 if idx[-1] is not None else "return channel absent"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    history = np.array(rig_inputs())
    with zipfile.ZipFile(args.archive) as top:
        with zipfile.ZipFile(io.BytesIO(top.read("58-32_PT_logs.zip"))) as archive:
            records(HERE/"thermal-inventory/pt-availability.csv", profile_inventory(archive, history))
        with zipfile.ZipFile(io.BytesIO(top.read("Pason_Logs.zip"))) as archive:
            records(HERE/"thermal-inventory/return-availability.csv", return_inventory(archive))


if __name__ == "__main__":
    main()
