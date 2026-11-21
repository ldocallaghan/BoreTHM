"""Compare the Pason inlet and return with the reported mud temperatures.

usage: compare_sources.py

Reads surface_record_10min.csv and report_temperatures.csv in this folder
and writes source_comparison.csv. Each reported value is set against the
Pason means over the 10-minute bins within 30 minutes of it in which mean
flow exceeded 300 US gal/min:

  daily drilling report  the bins around the mud sample's date and time
  mud logger report      the bins, within the report's 24 hours, around
                         the first bin whose hole depth reaches the
                         reported depth

A logger line whose depth was already reached when its report period began
repeats an earlier report and is not matched. A reported value without
matching bins is kept with blank Pason columns and the reason.
"""
import csv
from datetime import datetime, timedelta
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
WINDOW = timedelta(minutes=30)
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def read(name):
    with open(HERE/name, encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def value(row, key):
    return float(row[key]) if row.get(key) not in ("", None) else None


def f_to_c(text):
    return (float(text)-32)/1.8 if text not in ("", None) else None


def pason_near(record, when):
    near = [r for r in record if abs(r["_t"]-when) <= WINDOW and (value(r, "flow_gpm") or 0) > 300]
    out = {}
    for key in ("inlet_C", "return_C", "flow_gpm", "hole_ft"):
        vals = [value(r, key) for r in near if value(r, key) is not None]
        out["pason_"+key] = sum(vals)/len(vals) if vals else ""
    out["pason_bins"] = len(near)
    return out


def main():
    record = read("surface_record_10min.csv")
    for r in record:
        r["_t"] = datetime.fromisoformat(r["time"])+timedelta(minutes=5)
    rows = []
    for r in read("report_temperatures.csv"):
        if r["source"] == "daily drilling report":
            m = re.match(r"(\d{2})-([A-Za-z]{3})-(\d{2})\s+(\d{2}):(\d{2})", r["sample"])
            if not m or not (r["in_F"] or r["out_F"]):
                continue
            when = datetime(2000+int(m[3]), MONTHS.index(m[2].title())+1, int(m[1]), int(m[4]), int(m[5]))
            row = dict(source=r["source"], time=when.isoformat(sep=" "), depth_ft=r["depth_ft"],
                       sample_location=r["sample_location"], member=r["member"], page=r["page"])
        else:
            start = datetime.fromisoformat(r["period_start"]) if r["period_start"] else None
            if start is None:
                continue
            depth = float(r["depth_ft"])
            period = [x for x in record if start <= x["_t"] < start+timedelta(days=1)]
            reached = [x for x in period if (value(x, "hole_ft") or 0) >= depth]
            carried = bool(reached) and reached[0] is period[0]
            when = reached[0]["_t"] if reached and not carried else None
            row = dict(source=r["source"], time=when.isoformat(sep=" ") if when else "",
                       depth_ft=r["depth_ft"], sample_location="", member=r["member"], page=r["page"],
                       match="depth reached before the report period" if carried else
                       "" if when else "depth not reached in the report period")
        row.update(report_in_C=f_to_c(r["in_F"]) if r["in_F"] else "",
                   report_out_C=f_to_c(r["out_F"]) if r["out_F"] else "")
        row.update(pason_near(record, when) if when else dict(pason_bins=0))
        for a, b, key in (("report_in_C", "pason_inlet_C", "in_minus_pason_C"),
                          ("report_out_C", "pason_return_C", "out_minus_pason_C")):
            row[key] = row[a]-row[b] if row[a] != "" and row.get(b, "") != "" else ""
        rows.append(row)
    rows.sort(key=lambda r: (r["source"], r["time"]))
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with open(HERE/"source_comparison.csv", "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(len(rows), "rows")


if __name__ == "__main__":
    main()
