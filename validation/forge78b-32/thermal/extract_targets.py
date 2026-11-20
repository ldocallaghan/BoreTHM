"""Extract the 78B-32 thermal targets after unsealing. Run once, then commit
the outputs with their SHA-256 before scoring.

Reads the archive and the committed samples. Writes to OUTPUT:

- `downhole.csv`: for every qualified bin of every window, the recorded
  `MWD Temp`, `EYE TEMP` and `TEMP OUT` cells of the ten-second export, as
  written, with a fresh flag for the two downhole channels. A reading is
  fresh when it is finite and differs from the channel's previous finite
  reading anywhere in the export.
- `sanvean.csv`: for each Sanvean output file, the readings of its two
  sensor temperatures whose aligned time falls in a qualified bin of a window
  on the file's assembly.
- `sanvean-alignment.json`: the clock offset of each Sanvean file and the
  agreement measures that support it.

The Sanvean clock is aligned with inputs only: the offset, searched in
10 s steps over plus or minus 24 hours, that maximises the share of
overlapping ten-second bins in which the Sanvean and Pason pump states agree
(pumping when total pump output is above 100 US gal/min). The hole-depth
difference at that offset is recorded. No temperature enters the alignment.

Usage: python extract_targets.py ARCHIVE OUTPUT [--samples DIR] [--skip-hash]
"""
import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

import numpy as np

HERE = Path(__file__).resolve().parent
ARCHIVE_SHA256 = "b56e77dbc8b5081352418fc8976e9c20da1f57bdd67fdc25961134ea99ced79f"
TEN_S = "78B-32 10 sec data 27200701.csv"
CHANNELS = {"mwd_temp": "MWD Temp (Fahrenheit) (no_unit)", "eye_temp": "EYE TEMP (F) (no_unit)",
            "temp_out": "TEMP OUT (Degrees) (no_unit)"}
FRESH = ("mwd_temp", "eye_temp")
SANVEAN_ZIP = "Forge 78 B-32 WOO - 1 Sensor Data RM.zip"
# File: (assembly, lower sensor, upper sensor). Assemblies by sensor serial
# numbers and hole size on the BHA sheets.
SANVEAN = {
    "Forge 78 B-32 (WOO - 1) Sensor Data/Forge 14.75 Run 1 - output data.csv": ("3", "CSS-008", "CSS-007"),
    "Forge 78 B-32 (WOO - 1) Sensor Data/Forge 14.75 Run 2 - output data.csv": ("4", "CSS-008", "CSS-007"),
    "Forge 78 B-32 (WOO - 1) Sensor Data/Forge 10.625 - output data.csv": ("15", "CSS-006", "CSS-004"),
}
PUMPING_GPM = 100.
SEARCH_S = 24*3600
TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S.%f",
                "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M", "%Y/%m/%d %H:%M:%S", "%d/%m/%Y %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f")


def number(text):
    try:
        x = float(str(text).replace(",", ""))
    except (TypeError, ValueError):
        return math.nan
    return x if math.isfinite(x) and x != -999.25 else math.nan


def epoch(text):
    text = text.strip()
    for fmt in TIME_FORMATS:
        try:
            return int(datetime.strptime(text, fmt).replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue
    raise ValueError("unrecognised time format")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_samples(samples):
    with open(samples/"windows.csv", encoding="utf-8", newline="") as fh:
        windows = {r["sample_id"]: r for r in csv.DictReader(fh)}
    bins = {}
    with gzip.open(samples/"qualified-bins.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            bins.setdefault(epoch(r["bin_time"]), []).append(r["sample_id"])
    return windows, bins


def downhole(zf, bins, out):
    n = 0
    with io.TextIOWrapper(zf.open(TEN_S), encoding="utf-8-sig", newline="") as stream, \
            open(out/"downhole.csv", "w", encoding="utf-8", newline="") as dest:
        reader = csv.reader(stream)
        header = next(reader)
        ix = {k: header.index(v) for k, v in CHANNELS.items()}
        di, ti = header.index("YYYY/MM/DD"), header.index("HH:MM:SS")
        w = csv.writer(dest, lineterminator="\n")
        w.writerow(["sample_id", "bin_time", "channel", "recorded", "fresh"])
        last = {k: None for k in FRESH}
        for row in reader:
            if not row:
                continue
            t = epoch(row[di].replace("/", "-") + " " + row[ti])
            fresh = {}
            for k in FRESH:
                x = number(row[ix[k]])
                fresh[k] = math.isfinite(x) and last[k] is not None and x != last[k]
                if math.isfinite(x):
                    last[k] = x
            for sid in bins.get(t // 10 * 10, ()):
                stamp = datetime.fromtimestamp(t // 10 * 10, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                for k, j in ix.items():
                    w.writerow([sid, stamp, k, row[j].strip(), int(fresh[k]) if k in fresh else ""])
                    n += 1
    return n


def pason_pumping(inputs):
    path = inputs/"rig_inputs_10s.csv.gz"
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    t = np.array([epoch(r["time"]) for r in rows])
    q = np.array([number(r["flow_gpm"]) for r in rows])
    h = np.array([number(r["hole_depth_ft"]) for r in rows])
    return t, q, h


def sanvean_file(zf_inner, name):
    """Rows of one Sanvean output file: time, pump output, hole depth and the sensor columns."""
    with zf_inner.open(name) as fh:
        lines = (raw.decode("utf-8", "replace").rstrip("\r\n") for raw in fh)
        header = None
        for line in lines:
            if line.startswith("#") or not line.strip():
                continue
            header = [c.strip() for c in line.split(",")]
            break
        cols = {c: i for i, c in enumerate(header)}
        temps = {c.split("_")[0]: i for c, i in cols.items() if c.endswith("_Temperature(C)")}
        out = dict(time=[], pump=[], hole=[], **{k: [] for k in temps})
        for line in lines:
            cells = line.split(",")
            if len(cells) < len(header):
                continue
            try:
                t = epoch(cells[cols["DateTime"]])
            except ValueError:
                out.setdefault("unparsed_rows", 0)
                out["unparsed_rows"] = out.get("unparsed_rows", 0) + 1
                continue
            out["time"].append(t)
            out["pump"].append(number(cells[cols["Total Pump Output(GPM)"]]))
            out["hole"].append(number(cells[cols["Hole Depth(ft)"]]))
            for k, i in temps.items():
                out[k].append(cells[i].strip())
    return out


def align(st, sq, sh, pt, pq, ph):
    """Offset (s) added to the Sanvean clock that best matches the Pason pump state."""
    sbin = st // 10 * 10
    order = np.argsort(sbin)
    sbin, sq, sh = sbin[order], sq[order], sh[order]
    uniq, first = np.unique(sbin, return_index=True)
    s_pump = np.array([np.nanmean(sq[a:b]) > PUMPING_GPM if np.isfinite(sq[a:b]).any() else np.nan
                       for a, b in zip(first, np.r_[first[1:], len(sbin)])], dtype=float)
    s_hole = np.array([np.nanmedian(sh[a:b]) if np.isfinite(sh[a:b]).any() else np.nan
                       for a, b in zip(first, np.r_[first[1:], len(sbin)])])
    # Pason on a dense ten-second grid; missing bins are NaN.
    t0 = int(pt.min()) // 10 * 10
    size = (int(pt.max()) - t0) // 10 + 1
    g_pump = np.full(size, np.nan)
    g_hole = np.full(size, np.nan)
    k = (pt.astype(np.int64) - t0) // 10
    g_pump[k] = np.where(np.isfinite(pq), (pq > PUMPING_GPM).astype(float), np.nan)
    g_hole[k] = ph
    base = (uniq.astype(np.int64) - t0) // 10
    best = (-1., None, 0)
    for step in range(-SEARCH_S // 10, SEARCH_S // 10 + 1):
        j = base + step
        ok = (j >= 0) & (j < size)
        if ok.sum() < 360:
            continue
        a, b = s_pump[ok], g_pump[j[ok]]
        valid = np.isfinite(a) & np.isfinite(b)
        if valid.sum() < 360:
            continue
        share = float((a[valid] == b[valid]).mean())
        if share > best[0]:
            best = (share, step * 10, int(valid.sum()))
    share, off, n = best
    if off is None:
        return dict(offset_s=None, pump_agreement=None, overlap_bins=0)
    j = base + off // 10
    ok = (j >= 0) & (j < size)
    dh = np.abs(s_hole[ok] - g_hole[j[ok]])
    return dict(offset_s=off, pump_agreement=share, overlap_bins=n,
                hole_depth_median_abs_diff_ft=float(np.nanmedian(dh)) if np.isfinite(dh).any() else None)


def sanvean(zf, windows, bins, out, inputs):
    pt, pq, ph = pason_pumping(inputs)
    by_bha = {}
    for t, sids in bins.items():
        for sid in sids:
            by_bha.setdefault(windows[sid]["bha"], {}).setdefault(t, []).append(sid)
    report, n = {}, 0
    inner = zipfile.ZipFile(zf.open(SANVEAN_ZIP))
    with open(out/"sanvean.csv", "w", encoding="utf-8", newline="") as dest:
        w = csv.writer(dest, lineterminator="\n")
        w.writerow(["sample_id", "file", "sensor", "position", "aligned_time", "recorded_C"])
        for name, (bha, lower, upper) in SANVEAN.items():
            data = sanvean_file(inner, name)
            st = np.array(data["time"])
            res = align(st, np.array(data["pump"]), np.array(data["hole"]), pt, pq, ph)
            res.update(assembly=bha, rows=len(st), unparsed_rows=data.get("unparsed_rows", 0))
            report[name] = res
            if res["offset_s"] is None:
                continue
            table = by_bha.get(bha, {})
            for i, t in enumerate(st):
                tb = (int(t) + res["offset_s"]) // 10 * 10
                for sid in table.get(tb, ()):
                    stamp = datetime.fromtimestamp(int(t) + res["offset_s"], timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                    for sensor, pos in ((lower, "lower"), (upper, "upper")):
                        w.writerow([sid, name.rsplit("/", 1)[-1], sensor, pos, stamp, data[sensor][i]])
                        n += 1
    (out/"sanvean-alignment.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return n, report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--samples", type=Path, default=HERE/"samples")
    ap.add_argument("--inputs", type=Path, default=HERE/"inputs")
    ap.add_argument("--skip-hash", action="store_true", help="development only")
    args = ap.parse_args()
    if not args.skip_hash and sha(args.archive) != ARCHIVE_SHA256:
        raise SystemExit("archive hash does not match")
    args.output.mkdir(parents=True, exist_ok=True)
    windows, bins = read_samples(args.samples)
    with zipfile.ZipFile(args.archive) as zf:
        n_down = downhole(zf, bins, args.output)
        n_san, report = sanvean(zf, windows, bins, args.output, args.inputs)
    for name in ("downhole.csv", "sanvean.csv", "sanvean-alignment.json"):
        p = args.output/name
        (args.output/f"{name}.sha256").write_text(f"{sha(p)}  {name}\n", encoding="utf-8")
    print(json.dumps(dict(downhole_rows=n_down, sanvean_rows=n_san,
                          alignment={k.rsplit('/', 1)[-1]: {kk: v[kk] for kk in ('offset_s', 'pump_agreement', 'overlap_bins')}
                                     for k, v in report.items()}), indent=1))


if __name__ == "__main__":
    main()
