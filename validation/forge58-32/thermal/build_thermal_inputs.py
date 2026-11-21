"""Build the 58-32 thermal forecast inputs from open sources only.

Opens 1006.zip and the PT118 archive read-only. From 1006.zip it reads the
daily-report operations tables, the Pason columns Date, Time and Pump
Pressure, and nothing else. Report descriptions that mention a pressure or
a temperature are suppressed before they are written. No Pason Flow Out or
Temp Out cell, no PT-log value and no report outlet temperature is read
into an output. The PT118 log of 8 November 2018 is the formation reference.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
import zipfile
from datetime import datetime, timedelta

HERE = Path(__file__).resolve().parent
WELL = HERE.parent
SHA_1006 = "43615d79d000104ae698de23dd5aee6a981bcaa9b9a72548690556eef5fb6caa"
SHA_PT118 = "04de1f0aebe92e6b3963fcc43f054033d0898cab3d9a238f78d8038ec2826ec8"
# The extract's own suppression rule, widened to the report wording for
# return and cooler temperatures and survey maxima.
MASK = re.compile(r"pressure|\bpsi\b|\bSPP\b|\bkPa\b|\bMPa\b|temp|\d\s*[CF]\b|MRT|BHT|"
                  r"cooler|flow ?line|deg\.? ?[CF]\b|°|\bout\b\s*\d", re.I)
CLOCK = re.compile(r"\d{1,2}:?\d{2}")
FT_TO_M = 0.3048


def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path, rows, fields=None):
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    if path.suffix == ".gz":
        # Fixed gzip header (no name, zero time) so rebuilds are byte-identical.
        with path.open("wb") as handle, gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0) as raw, \
                io.TextIOWrapper(raw, encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    else:
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


def num(text):
    try:
        value = float(str(text).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value != -999.25 else None


def hhmm(text):
    text = text.replace(":", "")
    return text.zfill(4)


def operations(top):
    """Every operations-table row of every summary report, descriptions masked."""
    import pdfplumber
    original = {(r["report_date"], r["start_hhmm"].zfill(4), r["end_hhmm"].zfill(4), r["code"])
                for r in csv.DictReader((WELL/"operations.csv").open(encoding="utf-8"))}
    rows = []
    with zipfile.ZipFile(io.BytesIO(top.read("DailyDrillingReports_Well58-32.zip"))) as z:
        for name in sorted(z.namelist()):
            if not name.lower().endswith(".pdf") or "__MACOSX" in name or "Summary" not in name:
                continue
            source = "1006.zip!DailyDrillingReports_Well58-32.zip!"+name
            with pdfplumber.open(io.BytesIO(z.read(name))) as doc:
                report_date = ""
                for pn, page in enumerate(doc.pages, 1):
                    text = page.extract_text() or ""
                    match = re.search(r"Report For\s+(\d{2}-[A-Za-z]{3}-\d{2})", text)
                    if match:
                        report_date = datetime.strptime(match[1], "%d-%b-%y").date().isoformat()
                    for obj in page.find_tables():
                        for row in obj.extract():
                            cells = [str(c).strip() for c in row if c is not None]
                            if len(cells) < 6 or not (CLOCK.fullmatch(cells[0]) and CLOCK.fullmatch(cells[1])):
                                continue
                            desc = " ".join(cells[5].split())
                            if MASK.search(desc):
                                desc = "[mixed observation description suppressed]"
                            key = (report_date, hhmm(cells[0]), hhmm(cells[1]), cells[4])
                            rows.append(dict(report_date=report_date, start_hhmm=hhmm(cells[0]),
                                             end_hhmm=hhmm(cells[1]), elapsed_h=num(cells[2]),
                                             end_MD_ft=num(cells[3]), code=cells[4], description=desc,
                                             in_original_extract=key in original,
                                             source_member=source, page=pn))
    return rows


# Daily-report activity codes used for the exposure clock where Pason is absent.
# 3-2 drilling, 3-3 reaming and 3-5 circulating pump through the bit; every other code is
# taken as pumps off. A suppressed description keeps its code.
CIRCULATING_CODES = ("3-2", "3-3", "3-5")


def report_clock(ops, start, stop, report_flow):
    """Ten-second exposure-clock bins between start and stop from report rows.

    Drilling rows deepen the hole linearly from the previous end depth to their
    own; other rows hold it. Circulating rows carry the report flow; the rest
    carry zero flow.
    """
    rows = sorted((r for r in ops if start.date().isoformat() <= r["report_date"] < stop.date().isoformat()),
                  key=lambda r: (r["report_date"], r["start_hhmm"]))
    previous_depth = None
    for r in ops:
        if r["report_date"] < start.date().isoformat() and r["end_MD_ft"] is not None:
            previous_depth = max(previous_depth or 0., r["end_MD_ft"])
    intervals = []
    for r in rows:
        day = datetime.fromisoformat(r["report_date"])
        t0 = day+timedelta(hours=int(r["start_hhmm"][:2]), minutes=int(r["start_hhmm"][2:]))
        t1 = day+timedelta(hours=int(r["end_hhmm"][:2]), minutes=int(r["end_hhmm"][2:]))
        if t1 <= t0:
            t1 += timedelta(days=1)
        code = r["code"]
        pumped = any(code == c or code.startswith(c+"-") for c in CIRCULATING_CODES)
        drilling = code == "3-2" or code.startswith("3-2-")
        end = r["end_MD_ft"] if r["end_MD_ft"] is not None else previous_depth
        intervals.append((t0, t1, previous_depth, max(previous_depth, end) if drilling else previous_depth,
                          pumped, code, r["source_member"], r["page"]))
        if drilling:
            previous_depth = max(previous_depth, end)
    out = []
    t = start
    while t < stop:
        row = dict(time=t.isoformat(sep=" "), source="daily report", hole_depth_ft="", flow_gpm=0.,
                   report_code="", source_member="", page="")
        for t0, t1, d0, d1, pumped, code, member, page in intervals:
            if t0 <= t < t1:
                frac = (t-t0)/(t1-t0)
                row.update(hole_depth_ft=d0+(d1-d0)*frac, flow_gpm=report_flow if pumped else 0.,
                           report_code=code, source_member=member, page=page)
                break
        out.append(row)
        t += timedelta(seconds=10)
    return out, intervals


def flow_scale():
    """Median of report flow over Pason Flow In on the September A2 rows."""
    path = WELL.parent/"model-development/entry-11/results/A2-report-comparison.csv"
    used = []
    for r in csv.DictReader(path.open(encoding="utf-8")):
        if r["status"] != "available" or not r["day"].startswith("2017-09"):
            continue
        used.append(dict(report_no=r["report_no"], day=r["day"], interval_id=r["interval_id"],
                         reported_flow_gpm=float(r["reported_flow_gpm"]),
                         pason_median_flow_gpm=float(r["median_flow_gpm"]),
                         ratio=float(r["reported_flow_gpm"])/float(r["median_flow_gpm"])))
    ratios = sorted(r["ratio"] for r in used)
    n = len(ratios)
    median = ratios[n//2] if n % 2 else (ratios[n//2-1]+ratios[n//2])/2
    return dict(scale=median, rows=used, source="validation/model-development/entry-11/results/A2-report-comparison.csv",
                source_sha256=sha(path), rule="median of reported_flow_gpm/median_flow_gpm over rows with status "
                "'available' and a September 2017 day")


def pump_pressure(top):
    """Ten-second means of Pason Pump Pressure (native column 8), with counts."""
    out = []
    with zipfile.ZipFile(io.BytesIO(top.read("Pason_Logs.zip"))) as z:
        for name in sorted(z.namelist()):
            if not name.endswith(".csv") or "__MACOSX" in name:
                continue
            bins = {}
            with io.TextIOWrapper(z.open(name), encoding="utf-8-sig", newline="") as stream:
                header_ok = False
                for row in csv.reader(stream):
                    if not header_ok:
                        if row and row[0].strip() == "Date":
                            cells = [c.strip() for c in row]
                            single = len(cells) > 8 and cells[8] == "Pump Pressure"
                            split = cells[14:16] == ["Pump", "Press"]
                            if not (single or split):
                                raise ValueError(f"unexpected Pason header in {name}")
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
                    stamp = stamp.replace(second=stamp.second//10*10)
                    value = num(row[8])
                    entry = bins.setdefault(stamp, [0., 0])
                    if value is not None:
                        entry[0] += value
                        entry[1] += 1
            for stamp, (total, count) in sorted(bins.items()):
                out.append(dict(time=stamp.isoformat(sep=" "),
                                pump_pressure_psi=total/count if count else "", pump_pressure_count=count))
    out.sort(key=lambda r: r["time"])
    return out


def formation(archive_path):
    """PT118 temperature in 10 ft measured-depth bins: median of finite readings."""
    with zipfile.ZipFile(archive_path) as z:
        name = "UOFU_MU-ESW1_PT118.las"
        lines = z.read(name).decode("latin1").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("~A"))+1
    curves = []
    mode = ""
    for line in lines[:start]:
        if line.startswith("~"):
            mode = line[1].upper()
        elif mode == "C" and "." in line:
            curves.append(line.split(".", 1)[0].strip())
    depth_i, temp_i = curves.index("DEPT"), curves.index("T")
    bins = {}
    for line in lines[start:]:
        parts = line.split()
        if len(parts) != len(curves):
            continue
        depth, temp = num(parts[depth_i]), num(parts[temp_i])
        if depth is None or temp is None:
            continue
        bins.setdefault(int(depth//10), []).append(temp)
    survey = [(float(r["MD_ft"]), float(r["TVD_ft"])) for r in csv.DictReader((WELL/"survey.csv").open())]
    survey.sort()

    def tvd(md):
        if md <= survey[0][0]:
            return md*(survey[0][1]/survey[0][0]) if survey[0][0] > 0 else md
        for (m0, v0), (m1, v1) in zip(survey, survey[1:]):
            if md <= m1:
                return v0+(v1-v0)*(md-m0)/(m1-m0)
        (m0, v0), (m1, v1) = survey[-2], survey[-1]
        return v1+(md-m1)*(v1-v0)/(m1-m0)

    out = []
    for key in sorted(bins):
        values = sorted(bins[key])
        n = len(values)
        median = values[n//2] if n % 2 else (values[n//2-1]+values[n//2])/2
        md = key*10+5.
        out.append(dict(md_ft=md, tvd_ft=round(tvd(md), 3), temperature_F=round(median, 4),
                        temperature_C=round((median-32)/1.8, 4), readings=n))
    return out, dict(member=name, log_date="2018-11-08", kb_ft=21.5, fluid_level_ft=317.0, tag_depth_ft=7539.0,
                     unit="degF (curve T.DEGF), converted by (F-32)/1.8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw-1006", type=Path, required=True, help="1006.zip")
    parser.add_argument("--pt118", type=Path, required=True, help="58-32_Temp_Pres_11_08_18.zip")
    parser.add_argument("--output", type=Path, default=HERE/"inputs")
    args = parser.parse_args()
    if sha(args.raw_1006) != SHA_1006 or sha(args.pt118) != SHA_PT118:
        raise SystemExit("source archive hash mismatch")
    args.output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.raw_1006) as top:
        ops = operations(top)
        spp = pump_pressure(top)
    write_csv(args.output/"operations-extended.csv", ops)
    write_csv(args.output/"pump_pressure_10s.csv.gz", spp, ["time", "pump_pressure_psi", "pump_pressure_count"])
    scale = flow_scale()
    report_flow = {r["day"]: float(r["reported_flow_gpm"]) for r in
                   csv.DictReader((WELL.parent/"model-development/entry-11/results/A2-report-comparison.csv").open())}
    gap_flow = sorted({report_flow[d] for d in report_flow if "2017-08-27" <= d <= "2017-08-31"})
    if len(gap_flow) != 1:
        raise SystemExit("report flow differs within the Pason gap")
    clock, intervals = report_clock(ops, datetime(2017, 8, 27), datetime(2017, 9, 1), gap_flow[0])
    write_csv(args.output/"report_clock_10s.csv.gz", clock)
    write_csv(args.output/"report-clock-intervals.csv",
              [dict(start=a.isoformat(sep=" "), end=b.isoformat(sep=" "), hole_start_ft=c, hole_end_ft=d,
                    pumped=e, code=f, source_member=g, page=h) for a, b, c, d, e, f, g, h in intervals])
    profile, meta = formation(args.pt118)
    write_csv(args.output/"formation-pt118.csv", profile)
    manifest = dict(sources={"1006.zip": SHA_1006, "58-32_Temp_Pres_11_08_18.zip": SHA_PT118},
                    flow_scale=scale, report_flow_27_31_august_gpm=gap_flow[0], formation=meta,
                    counts=dict(operations=len(ops), operations_added=sum(not r["in_original_extract"] for r in ops),
                                operations_suppressed=sum(r["description"].startswith("[mixed") for r in ops),
                                pump_pressure_bins=len(spp), report_clock_bins=len(clock),
                                formation_bins=len(profile)),
                    outputs={p.name: sha(p) for p in sorted(args.output.iterdir()) if p.name != "manifest.json"},
                    code_sha256=sha(Path(__file__)))
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps(manifest["counts"], indent=2), scale["scale"])


if __name__ == "__main__":
    main()
