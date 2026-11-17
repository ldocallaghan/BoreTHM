"""Read the reported mud temperatures and operating notes for 56-32.

usage: report_temperatures.py ARCHIVE OUTPUT

ARCHIVE is GDR 1295 (`1295.zip`), read in place. OUTPUT receives:

  report_temperatures.csv  the daily drilling report "In" and "Out"
                           mud temperatures, and the mud logger's
                           "Temp In" and "Temp Out" by depth
  report_notes.csv         every line in the daily drilling reports,
                           the mud logger's reports, the end of well
                           report and operating_notes.csv that matches
                           NOTE_PATTERN, with its date and page

The daily report columns are found by the x position of their header
words. "In" must lie within HEADER_TOLERANCE of IN_X and "Out" within it
of OUT_X, or the page is recorded as failing the header check and gives
no value. A value cell is taken when its centre lies in the column's
interval, as build_extracts.py does for "In".
"""
import argparse
import csv
import io
import re
from pathlib import Path
import zipfile

import pdfplumber

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
IN_X, OUT_X, HEADER_TOLERANCE = 508.5, 532.9, 2.0
COLUMNS = {"in_F": (495., 522.), "out_F": (522., 549.)}
NOTE_PATTERN = re.compile(
    r"heater|heating|steam|boiler|chiller|cooler|cooling|cool(ed)? |freez|frozen|thaw|"
    r"\btanks?\b|\bpits?\b|mix(ed|ing)?\b|transfer|flow ?line|sensor|probe|"
    r"temp(erature)? (in|out)|fresh water|water truck|reserve pit", re.I)
SAMPLE_LINE = re.compile(r"^\d{2}-[A-Za-z]{3}-\d{2} \d{2}:\d{2} at Depth [\d,]+ ft Mud Pits$")


def report_date(text):
    match = re.search(r"Report For\s*(\d{2})-([A-Za-z]{3})-(\d{2})", text)
    if not match:
        return ""
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    return f"20{match[3]}-{months.index(match[2].title())+1:02}-{match[1]}"


def header_positions(page, bbox):
    """x centres of the last 'In' and 'Out' words in the header cell."""
    words = page.within_bbox(bbox).extract_words()
    found = {}
    for word in words:
        if word["text"] in ("In", "Out"):
            found[word["text"]] = (word["x0"]+word["x1"])/2
    return found.get("In"), found.get("Out")


def daily_rows(z, member):
    rows = []
    with pdfplumber.open(io.BytesIO(z.read(member))) as doc:
        for pn, page in enumerate(doc.pages, 1):
            text = page.extract_text() or ""
            date = report_date(text)
            for table in page.find_tables():
                cells = table.extract()
                for ri, row in enumerate(cells):
                    if " ".join(c or "" for c in row).strip() != "Mud Information" or ri+3 >= len(cells):
                        continue
                    x_in, x_out = header_positions(page, table.rows[ri+1].bbox)
                    sample = cells[ri+2][0] or ""
                    m = re.search(r"(\d{2}-[A-Za-z]{3}-\d{2})\s+(\d{2}:\d{2})\s+at Depth\s+([\d,]+)\s*ft\s*(.*)", sample)
                    entry = dict(source="daily drilling report", report_date=date,
                                 sample=sample.strip(), sample_time=m[2] if m else "",
                                 depth_ft=m[3].replace(",", "") if m else "",
                                 sample_location=m[4].strip() if m else "",
                                 header_in_x=round(x_in, 1) if x_in else "",
                                 header_out_x=round(x_out, 1) if x_out else "")
                    ok = (x_in is not None and abs(x_in-IN_X) <= HEADER_TOLERANCE and
                          x_out is not None and abs(x_out-OUT_X) <= HEADER_TOLERANCE)
                    entry["header_check"] = "pass" if ok else "fail"
                    values, boxes = cells[ri+3], table.rows[ri+3].cells
                    for key, (left, right) in COLUMNS.items():
                        picked = [str(values[i] or "") for i, box in enumerate(boxes)
                                  if box and left <= (box[0]+box[2])/2 <= right]
                        entry[key] = " ".join(picked).strip() if ok else ""
                    entry.update(member="56-32 Daily Drilling Reports.zip!"+member, page=pn)
                    rows.append(entry)
    return rows


def logger_rows(z, member):
    """The mud logger's 100 ft Temp In and Temp Out lines, and the cooling tower depth."""
    rows = []
    with pdfplumber.open(io.BytesIO(z.read(member))) as doc:
        for pn, page in enumerate(doc.pages, 1):
            text = page.extract_text() or ""
            period = re.search(r"Report:\s*(\d+)/(\d+)/(\d{4})\s+0:00hrs to (\d+)/(\d+)/(\d{4})", text)
            tower = re.search(r"Cooling Tower on @\s*([\d,]*)", text)
            lines = text.splitlines()
            try:
                start = next(i for i, line in enumerate(lines) if line.startswith("(deg F) (deg F)"))
            except StopIteration:
                continue
            for line in lines[start+1:]:
                if line.startswith("Lithology"):
                    break
                m = re.match(r"(\d{3,5})\s+(\d{2,3})\s+(\d{2,3})(\s|$)", line)
                if m:
                    rows.append(dict(source="mud logger morning report",
                                     report_date=f"{period[6]}-{int(period[4]):02}-{int(period[5]):02}" if period else "",
                                     period_start=f"{period[3]}-{int(period[1]):02}-{int(period[2]):02}" if period else "",
                                     depth_ft=m[1], in_F=m[2], out_F=m[3],
                                     cooling_tower_on_at_ft=tower[1].replace(",", "") if tower else "",
                                     member="56-32 Daily Mud Logs.zip!"+member, page=pn))
    return rows


def note_hits(label, date, page, text):
    for line in text.splitlines():
        if NOTE_PATTERN.search(line):
            kind = "mud sample location" if SAMPLE_LINE.match(line.strip()) else "text"
            yield dict(source=label, date=date, page=page, kind=kind, text=line.strip())


def pdf_notes(data, label, dated):
    with pdfplumber.open(io.BytesIO(data)) as doc:
        for pn, page in enumerate(doc.pages, 1):
            text = page.extract_text() or ""
            yield from note_hits(label, dated(text), pn, text)


def logger_date(text):
    m = re.search(r"Report:\s*(\d+)/(\d+)/(\d{4})\s+0:00hrs to (\d+)/(\d+)/(\d{4})", text)
    return f"{m[3]}-{int(m[1]):02}-{int(m[2]):02} to {m[6]}-{int(m[4]):02}-{int(m[5]):02}" if m else ""


def write(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    temperatures, notes = [], []
    with zipfile.ZipFile(args.archive) as top:
        with zipfile.ZipFile(io.BytesIO(top.read("56-32 Daily Drilling Reports.zip"))) as z:
            for member in sorted(n for n in z.namelist() if n.endswith(".pdf") and "__MACOSX" not in n):
                temperatures += daily_rows(z, member)
                notes += pdf_notes(z.read(member), "56-32 Daily Drilling Reports.zip!"+member, report_date)
        with zipfile.ZipFile(io.BytesIO(top.read("56-32 Daily Mud Logs.zip"))) as z:
            for member in sorted(n for n in z.namelist() if "Morning Report" in n and n.endswith(".pdf")):
                temperatures += logger_rows(z, member)
                notes += pdf_notes(z.read(member), "56-32 Daily Mud Logs.zip!"+member, logger_date)
        notes += pdf_notes(top.read("56-32 EOWR - Final 22 July 2021.pdf"), "56-32 EOWR - Final 22 July 2021.pdf",
                           lambda text: "")
    with open(STUDY/"operating_notes.csv", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            notes += note_hits("operating_notes.csv ("+row["source_member"]+")", row["report_date"],
                               row["page"], row["description"])
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output/"report_temperatures.csv", temperatures)
    write(args.output/"report_notes.csv", notes)
    failed = [r for r in temperatures if r.get("header_check") == "fail"]
    print(len(temperatures), "temperature rows;", len(failed), "daily tables failing the header check;",
          len(notes), "note lines")


if __name__ == "__main__":
    main()
