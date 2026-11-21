"""Build the 78B-32 thermal forecast inputs from the GDR 1330 archive.

Writes to OUTPUT (default `inputs/` beside this file):

- `rig_inputs_10s.csv.gz`: the open channels of the ten-second Pason export
  (time, bit and hole depth, true vertical depth, total pump output, on-bottom
  ROP, rotary speed, weight on bit, block height, pump strokes and the inlet
  temperature). No other column is read. The last column of the export holds
  free text and is never read; columns are taken by position.
- `operations.csv`: every operations row of every daily report. A
  description that mentions a pressure or a temperature is replaced by a
  suppression marker before it is written.
- `mud_reports.csv`: density, funnel viscosity, plastic viscosity, yield
  point, gels and the inlet ("In") temperature of each mud check. Each value
  cell is matched to the nearest heading word of its column. The outlet
  ("Out") cell is dropped before the record is built.
- `report_flows.csv`: the Drilling Parameters rows (depth interval, ROP,
  WOB, RPM, torque and flow). The pressure cell is dropped before the record
  is built.
- `bit_reports.csv`: the bit rows of the Bit/BHA/Workstring table up to the
  flow column, and the printed nozzles. Pump pressure and the columns derived
  from it are dropped.
- `bha_reports.csv`: the assembly named by each report ("BHA -No. N").
- `casing_reports.csv`: the Casing/Tubular Information rows.
- `survey.csv`: the directional survey.
- `manifest.json`: archive hash, member hashes, counts and output hashes.

The slow-circulation block, the comments and the management summary are not
read.

Usage: python build_inputs.py ARCHIVE [--output DIR] [--skip-rig]
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

HERE = Path(__file__).resolve().parent
ARCHIVE_SHA256 = "b56e77dbc8b5081352418fc8976e9c20da1f57bdd67fdc25961134ea99ced79f"
TEN_S = "78B-32 10 sec data 27200701.csv"
REPORTS = "78B-32-DailyDrillingReports-6-27thru7-31.pdf"
SURVEY_ZIP = "78B-32 directional survey (1).zip"
SURVEY_CSV = "directional survey78B.csv"

RIG = {
    "hole_depth_ft": "Hole Depth (feet)",
    "bit_depth_ft": "Bit Depth (feet)",
    "tvd_ft": "True Vertical Depth (feet)",
    "flow_gpm": "Total Pump Output (gal_per_min)",
    "rop_ft_h": "On Bottom ROP (ft_per_hr)",
    "rpm": "Rotary RPM (RPM)",
    "wob_klbf": "Weight on Bit (klbs)",
    "block_height_ft": "Block Height (feet)",
    "inlet_temperature_source_degrees": "TEMP IN (Degrees) (no_unit)",
}
PUMPS = re.compile(r"^Pump (\d) strokes/min \(SPM\)$")
SUPPRESS = re.compile(r"psi|kpa|mpa|\bspp\b|differential|press|temp|deg|°|\bcool|flow ?line|outlet|\bmrt\b|\bbht\b|\bhot\b|\bheat", re.I)
MUD_KEEP = {"Dens.": "mud_weight_ppg", "Vis": "funnel_viscosity_s", "PV": "plastic_viscosity_cP",
            "YP": "yield_point_lbf_100ft2", "10s": "gel_10s", "10m": "gel_10min", "30m": "gel_30min",
            "In": "report_inlet_F"}
PARAM_NAMES = ["depth_from_ft", "depth_to_ft", "rop_avg_ft_h", "rop_max_ft_h", "wob_avg", "wob_max",
               "rpm_avg", "rpm_max", "torque_avg", "torque_max", "flow_avg_gpm", "flow_max_gpm"]
BIT_NAMES = ["bit_no", "run", "make", "model", "diameter_in", "depth_in_ft", "distance_ft", "hours",
             "rop_avg", "rop_max", "wob", "rpm", "torque", "mud_weight_ppg", "flow_gpm"]
DATE = re.compile(r"Report For\s*(\d{1,2}-[A-Za-z]{3}-\d{2})")
MONTHS = {m: i for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
                                      "Sep", "Oct", "Nov", "Dec"), 1)}


def number(text):
    try:
        x = float(str(text).replace(",", "").strip())
    except (TypeError, ValueError):
        return math.nan
    return x if math.isfinite(x) and x != -999.25 else math.nan


def iso_date(text):
    d, m, y = text.split("-")
    return f"20{y}-{MONTHS[m.title()]:02d}-{int(d):02d}"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path, rows, fields=None):
    rows = list(rows)
    fields = fields or list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def fmt(x):
    return "" if not math.isfinite(x) else repr(round(x, 4))


# ---------- Pason ----------

def rig(zf, out):
    rows = 0
    with io.TextIOWrapper(zf.open(TEN_S), encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        ix = {k: header.index(v) for k, v in RIG.items()}
        for j, name in enumerate(header):
            m = PUMPS.match(name)
            if m:
                ix[f"pump{m[1]}_spm"] = j
        di, ti = header.index("YYYY/MM/DD"), header.index("HH:MM:SS")
        fields = ["time"] + list(ix)
        path = out/"rig_inputs_10s.csv.gz"
        with path.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz, \
                io.TextIOWrapper(gz, encoding="utf-8", newline="") as text:
            w = csv.writer(text, lineterminator="\n")
            w.writerow(fields)
            for row in reader:
                if not row:
                    continue
                stamp = row[di].replace("/", "-") + " " + row[ti]
                w.writerow([stamp] + [fmt(number(row[j])) for j in ix.values()])
                rows += 1
    return dict(rows=rows, columns={k: header[j] for k, j in ix.items()})


# ---------- daily reports ----------

def heading_words(page, row):
    """Words inside a table row's box, grouped by line, each with its x centre."""
    top, bottom = row.bbox[1], row.bbox[3]
    lines = {}
    for w in page.extract_words():
        if w["top"] >= top - 0.5 and w["bottom"] <= bottom + 0.5:
            lines.setdefault(round(w["top"]), []).append(((w["x0"] + w["x1"]) / 2, w["text"]))
    return [sorted(v) for _, v in sorted(lines.items())]


def cells(row_text, row_obj):
    return [((b[0] + b[2]) / 2, (c or "").strip()) for c, b in zip(row_text, row_obj.cells)
            if b is not None and c not in (None, "")]


def nearest(x, heads, tolerance=9.0):
    best = min(heads, key=lambda h: abs(h[0] - x))
    return best if abs(best[0] - x) <= tolerance else None


def reports(zf, out):
    import pdfplumber
    data = zf.read(REPORTS)
    operations, mud, flows, bits, bhas, casings, audit = [], [], [], [], [], [], []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for pn, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            d = DATE.search(text)
            if not d:
                continue
            report_date = iso_date(d[1])
            for table in page.find_tables():
                rows = table.extract()
                for ri, (row, robj) in enumerate(zip(rows, table.rows)):
                    occupied = [c.strip() for c in row if c not in (None, "")]
                    joined = " ".join(occupied)
                    # Operations rows: from and to times first.
                    if (len(occupied) >= 6 and re.fullmatch(r"\d{1,2}:\d{2}", occupied[0])
                            and re.fullmatch(r"\d{1,2}:\d{2}", occupied[1])):
                        desc = " ".join(occupied[5:])
                        safe = not SUPPRESS.search(desc)
                        operations.append(dict(report_date=report_date, time_from=occupied[0], time_to=occupied[1],
                                               elapsed_hours=occupied[2], end_md_ft=occupied[3], code=occupied[4],
                                               description=desc if safe else "[suppressed: pressure or temperature wording]",
                                               page=pn))
                    elif joined.startswith("Mud Information") and ri + 3 < len(rows):
                        heads = heading_words(page, table.rows[ri + 1])[-1]
                        keep = [h for h in heads if h[1] in MUD_KEEP]
                        sample = rows[ri + 2][0] or ""
                        sm = re.search(r"(\d{1,2}-[A-Za-z]{3}-\d{2})\s+(\d{1,2}:\d{2})\s+at Depth\s+([\d,]+)", sample)
                        rec = dict(report_date=report_date, sample_date=iso_date(sm[1]) if sm else "",
                                   sample_time=sm[2] if sm else "", sample_depth_ft=fmt(number(sm[3])) if sm else "")
                        values = cells(rows[ri + 3], table.rows[ri + 3])
                        assigned = 0
                        for x, v in values:
                            h = nearest(x, heads)
                            # Only kept headings are written; the outlet and
                            # every other column are dropped here.
                            if h is not None and h in keep:
                                rec[MUD_KEEP[h[1]]] = v
                                assigned += 1
                        rec.update(page=pn, value_cells=len(values), kept_cells=assigned)
                        mud.append(rec)
                    elif joined.startswith("Drilling Parameters") and ri + 3 < len(rows):
                        heads = heading_words(page, table.rows[ri + 1])[-1]
                        named = list(zip(heads, PARAM_NAMES))
                        k = ri + 2
                        while k < len(rows):
                            values = cells(rows[k], table.rows[k])
                            if not values or not re.fullmatch(r"[\d,.]+", values[0][1]):
                                break
                            rec = dict(report_date=report_date, page=pn)
                            for x, v in values:
                                h = nearest(x, heads)
                                for head, name in named:
                                    if h is head:
                                        rec[name] = v
                            flows.append(rec)
                            k += 1
                    elif joined.startswith("Bit/BHA/Workstring") and ri + 2 < len(rows):
                        heads = heading_words(page, table.rows[ri + 1])[-1]
                        named = list(zip(heads, BIT_NAMES))
                        k = ri + 2
                        while k + 1 < len(rows):
                            values = cells(rows[k], table.rows[k])
                            jets_row = " ".join(c for c in rows[k + 1] if c)
                            if not values or not jets_row.startswith("Jets:"):
                                break
                            rec = dict(report_date=report_date, page=pn)
                            for x, v in values:
                                h = nearest(x, heads)
                                for head, name in named:
                                    if h is head:
                                        rec[name] = v
                            jm = re.match(r"Jets:\s*([\d ]*)", jets_row)
                            om = re.search(r"Out:\s*([\d,]*)", jets_row)
                            rec["jets_32nds"] = " ".join((jm[1] if jm else "").split())
                            rec["depth_out_ft"] = om[1] if om else ""
                            bits.append(rec)
                            k += 2
                    elif joined.startswith("BHA -"):
                        m = re.search(r"BHA\s*-\s*No\.\s*(\d+)\s*-\s*(.*)", joined)
                        if m:
                            bhas.append(dict(report_date=report_date, bha_id=m[1],
                                             description=re.sub(r"\s+", " ", m[2]), page=pn))
                    elif joined.startswith("Casing/Tubular"):
                        names = ["type", "size_in", "top_md_ft", "top_tvd_ft", "bottom_md_ft", "bottom_tvd_ft",
                                 "hole_section", "oh_diameter_in", "weight_lb_ft", "grade", "lot_ppg"]
                        k = ri + 2
                        while k < len(rows) and re.fullmatch(r"(FULL|LINER|OPEN|TIEBACK)", (rows[k][0] or "").strip(), re.I):
                            heads = heading_words(page, table.rows[ri + 1])
                            occ = [c.strip() for c in rows[k] if c not in (None, "")]
                            casings.append(dict(report_date=report_date, cells=" | ".join(occ), page=pn))
                            k += 1
            audit.append(dict(page=pn, report_date=report_date))
    counts = dict(pages_with_report_date=len(audit), report_dates=len({a["report_date"] for a in audit}),
                  operations=write_csv(out/"operations.csv", operations),
                  operations_suppressed=sum(o["description"].startswith("[suppressed") for o in operations),
                  mud_checks=write_csv(out/"mud_reports.csv", mud),
                  drilling_parameter_rows=write_csv(out/"report_flows.csv", flows),
                  bit_rows=write_csv(out/"bit_reports.csv", bits),
                  bha_lines=write_csv(out/"bha_reports.csv", bhas),
                  casing_rows=write_csv(out/"casing_reports.csv", casings))
    return dict(member=REPORTS, sha256=digest(data), **counts)


def survey(zf, out):
    inner = zipfile.ZipFile(io.BytesIO(zf.read(SURVEY_ZIP)))
    data = inner.read(SURVEY_CSV)
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    (out/"survey-source.csv").write_bytes(data)
    return dict(member=f"{SURVEY_ZIP}!{SURVEY_CSV}", sha256=digest(data), rows=len(rows))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive", type=Path)
    ap.add_argument("--output", type=Path, default=HERE/"inputs")
    ap.add_argument("--skip-rig", action="store_true")
    ap.add_argument("--skip-hash", action="store_true", help="skip the archive hash check (development only)")
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = dict(archive="1330.zip", archive_sha256=ARCHIVE_SHA256)
    if not args.skip_hash and file_sha(args.archive) != ARCHIVE_SHA256:
        raise SystemExit("archive hash does not match")
    manifest["archive_hash_checked"] = not args.skip_hash
    with zipfile.ZipFile(args.archive) as zf:
        if not args.skip_rig:
            manifest["rig"] = rig(zf, args.output)
        manifest["reports"] = reports(zf, args.output)
        manifest["survey"] = survey(zf, args.output)
    manifest["outputs"] = {p.name: file_sha(p) for p in sorted(args.output.iterdir())
                           if p.is_file() and p.name != "manifest.json"}
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k != "outputs"}, indent=1))


if __name__ == "__main__":
    main()
