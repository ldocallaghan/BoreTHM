"""Extract the 58-32 thermal targets after the declaration was made public.

Part A: the measured return of each forecast drilling window, from native
column 17 (Temp Out) of the Pason files, over the window's qualified seconds,
with rule R2 applied. Part B: the PT-log temperature at each forecast point.
Writes return_temperature.csv, log_temperature.csv and manifest.json with
the SHA-256 of each target file and source member.
"""
import argparse
import csv
from datetime import datetime
import gzip
import hashlib
from importlib import import_module
import io
import json
import math
from pathlib import Path
import subprocess
import zipfile

import numpy as np

c = import_module("validation.forge58-32.thermal.common")
DECLARATION = "82ec06c930ddff1d921614fb1f2dd18241d68e66"
RETURN_RANGE_C = (0., 120.)      # rule R2
LOG_RANGE_C = (0., 250.)         # part B validity
DEPTH_HALF_FT, TIME_HALF_S = 5., 5.
UNIT_CONVERSION = "(F-32)/1.8"


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def number(text):
    try:
        value = float(str(text).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value != -999.25 else None


def qualified_bins(conditions):
    """The qualified ten-second bins of every forecast window, rebuilt from the rig inputs."""
    h = c.rig()
    t = h["time"]
    seconds = t.astype("datetime64[s]").astype(np.int64)
    valid = (h["flow_gpm"] > 300) & (np.abs(h["bit_depth_ft"]-h["hole_depth_ft"]) <= 5) & (h["rop_ft_h"] > 1)
    centre = (seconds+900)//1800
    owner = {}
    for row in conditions:
        mid = int(np.datetime64(row["time"].replace(" ", "T"), "s").astype(np.int64))
        take = np.flatnonzero(valid & (centre == mid//1800))
        if len(take) != int(row["qualified_bins"]):
            raise SystemExit(f"{row['sample_id']}: {len(take)} qualified bins, conditions say {row['qualified_bins']}")
        for i in take:
            owner[int(seconds[i])] = row["sample_id"]
    return owner


def returns(top, conditions):
    owner = qualified_bins(conditions)
    seconds = {r["sample_id"]: [] for r in conditions}
    members = {}
    with zipfile.ZipFile(io.BytesIO(top.read("Pason_Logs.zip"))) as z:
        for name in sorted(z.namelist()):
            if not name.endswith(".csv") or "__MACOSX" in name:
                continue
            data = z.read(name)
            members["1006.zip!Pason_Logs.zip!"+name] = sha_bytes(data)
            header_ok = False
            for row in csv.reader(io.TextIOWrapper(io.BytesIO(data), encoding="utf-8-sig", newline="")):
                if not header_ok:
                    if row and row[0].strip() == "Date":
                        cells = [x.strip() for x in row]
                        single = len(cells) > 17 and cells[17] == "Temp Out"
                        split = cells[34:36] == ["Temp", "Out"]
                        if not (single or split):
                            raise SystemExit(f"unexpected heading in {name}")
                        header_ok = True
                    continue
                if len(row) > 18 and not any(s.strip() for s in row[18:]):
                    row = row[:18]
                if len(row) != 18:
                    continue
                try:
                    stamp = datetime.strptime(row[0].strip()+" "+row[1].strip(), "%m/%d/%Y %H:%M:%S")
                except ValueError:
                    continue
                key = int(np.datetime64(stamp, "s").astype(np.int64))//10*10
                sample = owner.get(key)
                if sample is None:
                    continue
                value = number(row[17])
                if value is not None:
                    value = (value-32)/1.8
                    if not RETURN_RANGE_C[0] < value <= RETURN_RANGE_C[1]:
                        value = None
                seconds[sample].append(value)
    out = []
    for row in conditions:
        values = seconds[row["sample_id"]]
        finite = [v for v in values if v is not None]
        out.append(dict(sample_id=row["sample_id"], qualified_bins=int(row["qualified_bins"]),
                        qualified_seconds=len(values), finite_seconds=len(finite),
                        mean_C=float(np.mean(finite)) if finite else "",
                        min_C=min(finite) if finite else "", max_C=max(finite) if finite else "",
                        unit_conversion=UNIT_CONVERSION))
    return out, members


def read_las(data):
    mode, curves, rows = "", [], []
    for raw in io.TextIOWrapper(io.BytesIO(data), encoding="latin1"):
        line = raw.strip()
        if line.startswith("~"):
            mode = line[1].upper()
            continue
        if mode == "C" and line and not line.startswith("#"):
            curves.append(line.split(":")[0].split()[0])
        elif mode == "A" and line:
            rows.append([number(x) for x in line.split()])
    names = [x.split(".")[0] for x in curves]
    units = {x.split(".")[0]: x.split(".", 1)[1] for x in curves}
    return names, units, rows


def logs(top, points):
    out, members = [], {}
    with zipfile.ZipFile(io.BytesIO(top.read("58-32_PT_logs.zip"))) as z:
        files = {n.split("MU-ESW1_")[1].split("_PT")[0]: n for n in z.namelist() if n.endswith(".las")}
        for log in sorted({p["log"] for p in points}):
            data = z.read(files[log])
            members["1006.zip!58-32_PT_logs.zip!"+files[log]] = sha_bytes(data)
            names, units, rows = read_las(data)
            index = names[0]
            if units["T"] != "DEGF" or index not in ("DEPT", "TIME"):
                raise SystemExit(f"{log}: unexpected curves {names} {units}")
            x = np.array([r[0] if r[0] is not None else np.nan for r in rows])
            temp = np.array([(r[names.index("T")]-32)/1.8 if r[names.index("T")] is not None else np.nan for r in rows])
            temp[~((temp > LOG_RANGE_C[0]) & (temp <= LOG_RANGE_C[1]))] = np.nan
            for p in (p for p in points if p["log"] == log):
                at = float(p["md_ft"]) if index == "DEPT" else float(p["elapsed_s"])
                half = DEPTH_HALF_FT if index == "DEPT" else TIME_HALF_S
                near = np.abs(x-at) <= half
                good = near & np.isfinite(temp)
                out.append(dict(log=log, md_ft=p["md_ft"], elapsed_s=p["elapsed_s"], rig_time=p["rig_time"],
                                index_curve=index, window=half, readings=int(near.sum()), finite_readings=int(good.sum()),
                                mean_C=float(temp[good].mean()) if good.any() else "",
                                unit=f"T.{units['T']}", unit_conversion=UNIT_CONVERSION))
    return out, members


def write(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("archive", type=Path, help="1006.zip")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = c.WELL.parent.parent
    ancestor = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", DECLARATION, "HEAD"])
    if ancestor.returncode:
        raise SystemExit("the declaration commit is not in this history")
    if c.sha(args.archive) != "43615d79d000104ae698de23dd5aee6a981bcaa9b9a72548690556eef5fb6caa":
        raise SystemExit("1006.zip hash mismatch")
    predictions = c.read(c.WELL/"predictions-v1.9.0/predictions.csv")
    forecast = {r["sample_id"] for r in predictions if all(r.get(f"{f}_{n}_return_C")
                for f in ("primary", "secondary") for n in ("v1.9.0", "v1.7.0", "analytical"))}
    conditions = [r for r in c.read(c.HERE/"samples/conditions.csv") if r["sample_id"] in forecast]
    points = c.read(c.HERE/"samples/log-points.csv")
    args.output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.archive) as top:
        ret, m1 = returns(top, conditions)
        pt, m2 = logs(top, points)
    write(args.output/"return_temperature.csv", ret)
    write(args.output/"log_temperature.csv", pt)
    commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    manifest = dict(declaration_commit=DECLARATION, head_at_extraction=commit,
                    extraction_code_sha256=c.sha(Path(__file__)),
                    targets_sha256={n: c.sha(args.output/n) for n in ("return_temperature.csv", "log_temperature.csv")},
                    source_members_sha256=m1 | m2, archive_sha256=c.sha(args.archive),
                    counts=dict(return_windows=len(ret), return_windows_with_finite=sum(bool(r["finite_seconds"]) for r in ret),
                                log_points=len(pt), log_points_with_finite=sum(bool(r["finite_readings"]) for r in pt)))
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8", newline="\n")
    for name, sha in manifest["targets_sha256"].items():
        (args.output/f"{name}.sha256").write_text(f"{sha}  {name}\n", encoding="utf-8", newline="\n")
    print(json.dumps(manifest["counts"], indent=2))


if __name__ == "__main__":
    main()
