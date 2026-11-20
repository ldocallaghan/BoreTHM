"""Compare Pason flow and inlet temperature with the daily reports. Inputs only.

Flow, after entry 11 table A2: for each Drilling Parameters row, take the
Pason rows of the report's calendar day with the bit inside the printed
depth interval, the bit within 5 ft of hole depth, on-bottom ROP above
1 ft/h and positive summed pump strokes. Report the median Pason pump
output, the count, and the ratio of the report's average flow to it.

Inlet: for each mud check, the mean Pason inlet over the 30 minutes centred
on the sample time, against the report "In" value. Both are read as
Fahrenheit. The difference is converted to kelvin.

Usage: python check_flow_inlet.py [INPUTS_DIR]
"""
import csv
import gzip
import json
import math
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent


def number(text):
    try:
        x = float(str(text).replace(",", ""))
    except (TypeError, ValueError):
        return math.nan
    return x if math.isfinite(x) else math.nan


def main():
    inputs = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE/"inputs"
    with gzip.open(inputs/"rig_inputs_10s.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        rig = list(csv.DictReader(fh))
    for r in rig:
        for k in ("bit_depth_ft", "hole_depth_ft", "flow_gpm", "rop_ft_h", "pump1_spm", "pump2_spm", "pump3_spm",
                  "inlet_temperature_source_degrees"):
            r[k] = number(r[k])
    by_day = {}
    for r in rig:
        by_day.setdefault(r["time"][:10], []).append(r)

    flows = []
    with open(inputs/"report_flows.csv", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            lo, hi = number(row["depth_from_ft"]), number(row["depth_to_ft"])
            q_report = number(row["flow_avg_gpm"])
            sel = [r["flow_gpm"] for r in by_day.get(row["report_date"], [])
                   if lo <= r["bit_depth_ft"] <= hi and abs(r["bit_depth_ft"]-r["hole_depth_ft"]) <= 5
                   and r["rop_ft_h"] > 1 and math.isfinite(r["flow_gpm"])
                   and sum(x for x in (r["pump1_spm"], r["pump2_spm"], r["pump3_spm"]) if math.isfinite(x)) > 0]
            med = statistics.median(sel) if sel else math.nan
            flows.append(dict(report_date=row["report_date"], depth_from_ft=lo, depth_to_ft=hi,
                              report_flow_gpm=q_report, pason_rows=len(sel), pason_median_gpm=round(med, 1),
                              report_over_pason=round(q_report/med, 4) if sel and med > 0 else ""))
    ratios = [f["report_over_pason"] for f in flows if f["report_over_pason"] != ""]

    inlet = []
    with open(inputs/"mud_reports.csv", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if not row["sample_date"] or not row["sample_time"]:
                continue
            hh, mm = map(int, row["sample_time"].split(":"))
            t = hh*3600 + mm*60
            day = by_day.get(row["sample_date"], [])
            vals = []
            for r in day:
                h, m, s = map(int, r["time"][11:].split(":"))
                if abs(h*3600+m*60+s - t) <= 900 and math.isfinite(r["inlet_temperature_source_degrees"]):
                    vals.append(r["inlet_temperature_source_degrees"])
            rep = number(row["report_inlet_F"])
            pas = statistics.fmean(vals) if vals else math.nan
            inlet.append(dict(sample_date=row["sample_date"], sample_time=row["sample_time"], report_in_F=rep,
                              pason_rows=len(vals), pason_mean_F=round(pas, 2) if vals else "",
                              difference_K=round((rep-pas)/1.8, 2) if vals and math.isfinite(rep) else "",
                              flag_over_5K=bool(vals and math.isfinite(rep) and abs(rep-pas)/1.8 > 5)))
    days = sorted(by_day)
    inlet_days = sorted(d for d in days if any(math.isfinite(r["inlet_temperature_source_degrees"]) for r in by_day[d]))
    out = HERE/"inputs"
    for name, rows in (("flow-check.csv", flows), ("inlet-check.csv", inlet)):
        with open(out/name, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    summary = dict(flow_rows=len(flows), flow_rows_with_pason=len(ratios),
                   ratio_median=statistics.median(ratios) if ratios else None,
                   ratio_min=min(ratios) if ratios else None, ratio_max=max(ratios) if ratios else None,
                   rows_within_10_percent=sum(0.9 <= x <= 1.1 for x in ratios),
                   inlet_checks=len(inlet), inlet_checks_with_pason=sum(1 for i in inlet if i["pason_rows"]),
                   inlet_flags_over_5K=sum(i["flag_over_5K"] for i in inlet),
                   pason_inlet_first_day=inlet_days[0] if inlet_days else None,
                   pason_inlet_last_day=inlet_days[-1] if inlet_days else None)
    (out/"flow-inlet-summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
