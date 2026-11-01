"""Recompute source arithmetic and pressure bounds; no model functions or solves.

The flow factor is a diagnostic bound only. Event pressure terms are means,
while observations are medians, as recorded in the inherited event budget.
"""
import argparse
import csv
from datetime import datetime
import hashlib
import io
import math
from pathlib import Path
import statistics as st
import zipfile

from pypdf import PdfReader
from build_flow import write

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read(path):
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def displacement(diameter, stroke):
    return 3 * math.pi / 4 * diameter**2 * stroke / 231


def flow_bound(row, exponent):
    target = float(row['median_target_psi'])
    assert float(row['surface_psi']) == 0, 'Original calculation must have no surface term'
    def pressure(k):
        return (float(row['bit_nozzles_psi']) * k**2
                + (float(row['pipe_bore_psi']) + float(row['bha_bore_psi'])) * k**exponent
                + float(row['annulus_psi']) * k + float(row['buoyancy_psi']))
    lower, upper = 0., 1.
    assert pressure(lower) <= target <= pressure(upper)
    for _ in range(80):
        k = (lower + upper) / 2
        if pressure(k) < target:
            lower = k
        else:
            upper = k
    k = (lower + upper) / 2
    assert abs(pressure(k) - target) < 1e-8
    return k, pressure(k)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw58', type=Path, required=True)
    a = p.parse_args()
    results = HERE / 'results'
    days = {well: read(results / (well + '-ratios-by-day.csv')) for well in ('58-32', '16A', '16B')}
    regimes = []
    periods = [('2017-07-31', '2017-08-02'), ('2017-08-03', '2017-08-11'),
               ('2017-08-12', '2017-09-02'), ('2017-09-03', '2017-09-13')]
    for start, end in periods:
        for combination in sorted({r['combination'] for r in days['58-32']}):
            selected = [r for r in days['58-32'] if start <= r['day'] <= end and r['combination'] == combination]
            x = [float(r['median_gal_stroke']) for r in selected]
            regimes.append(dict(classification='calculated',start_date=start,end_date=end,
                combination=combination,days=len(x),median_of_daily_medians=st.median(x),
                minimum_daily_median=min(x),maximum_daily_median=max(x),
                native_rows=sum(int(r['native_rows']) for r in selected),
                source='58-32-ratios-by-day.csv: day,combination,median_gal_stroke,native_rows',
                qualification='Daily regime summary; transient departures remain in daily extrema and rebuildable native extracts'))
    write(results / 'flow-regimes.csv', regimes)
    def median(well, start, end):
        return st.median(float(r['median_gal_stroke']) for r in days[well] if start <= r['day'] <= end)
    registered = median('58-32','2017-08-03','2017-08-11')
    later = median('58-32','2017-08-12','2017-09-02')
    before = median('16B','2023-04-26','2023-05-03')
    after = median('16B','2023-05-06','2023-07-21')
    # Overall median of the daily summaries identifies the predominant regime;
    # initial/final 16A departures remain included in the source table.
    a16 = st.median(float(r['median_gal_stroke']) for r in days['16A'])
    arithmetic = [
        ('58-32_registered_regime', registered, 'US gal/stroke', '58-32 daily medians, 3-11 August'),
        ('58-32_later_regime', later, 'US gal/stroke', '58-32 daily medians, 12 August-2 September'),
        ('58-32_regime_ratio', registered / later, 'ratio', 'Registered regime divided by later regime'),
        ('nominal_5.5575_over_5.85', 5.5575 / 5.85, 'ratio', 'Rounded regime arithmetic only'),
        ('D2L_for_5.85', 5.85 * 231 / (3 * math.pi / 4), 'in3', 'Triplex at 100 percent efficiency'),
        ('liner_for_5.85_L10', math.sqrt(5.85 * 231 / (3 * math.pi / 4 * 10)), 'in', 'Triplex at 100 percent efficiency; assumed published 10-in stroke'),
        ('published_D6.75_L10', displacement(6.75,10), 'US gal/stroke', 'Later published specification; 2017 applicability unverified'),
        ('D6_L12', displacement(6,12), 'US gal/stroke', 'Recorded six-inch liner with 12-in stroke'),
        ('D5.5_L12', displacement(5.5,12), 'US gal/stroke', 'Recorded 5.5-in liner with unconfirmed 12-in stroke'),
        ('16A_predominant_daily_regime', a16, 'US gal/stroke', 'Median of all archived 16A daily total-stroke medians'),
        ('16A_efficiency_equivalent', a16/displacement(6,12), 'ratio', 'Assumes 12-in stroke; 11-in source conflict remains'),
        ('16B_before_daily_regime', before, 'US gal/stroke', 'Median of archived daily pump-combination medians, 26 April-3 May'),
        ('16B_after_daily_regime', after, 'US gal/stroke', 'Median of archived daily pump-combination medians, 6 May-21 July'),
        ('16B_before_efficiency_equivalent', before/displacement(6,12), 'ratio', '12-in stroke unconfirmed'),
        ('16B_after_efficiency_equivalent', after/displacement(5.5,12), 'ratio', '12-in stroke unconfirmed'),
        ('16B_measured_regime_ratio', after/before, 'ratio', 'After/before source-summary ratio'),
        ('16B_liner_area_ratio', (5.5/6)**2, 'ratio', 'Ratio of recorded liner areas'),
    ]
    write(results / 'pump-displacement-arithmetic.csv', [dict(classification='calculated',quantity=q,value=v,unit=u,basis=b) for q,v,u,b in arithmetic])
    budgets = read(ROOT / 'validation/forge58-32/pressure-test/results/event-budget.csv')
    bounds = []
    for r in budgets:
        if (r['scenario'], r['cohort'], r['variant']) != ('primary','scenario','original'):
            continue
        k175,p175 = flow_bound(r,1.75); k185,p185 = flow_bound(r,1.85)
        bounds.append(dict(classification='calculated bound',event_id=r['event_id'],
            measured_event_median_psi=r['median_target_psi'],original_event_median_psi=r['median_predicted_psi'],
            original_event_mean_psi=r['mean_predicted_psi'],
            k_n175=k175,k_n185=k185,k_min=min(k175,k185),k_max=max(k175,k185),
            scaled_sum_n175_psi=p175,scaled_sum_n185_psi=p185,
            uniform_pressure_gain=float(r['median_predicted_psi'])/float(r['median_target_psi']),
            bha_plus_annulus_psi=float(r['bha_bore_psi'])+float(r['annulus_psi']),
            nozzle_plus_annulus_psi=float(r['bit_nozzles_psi'])+float(r['annulus_psi']),
            pipe_bore_psi=r['pipe_bore_psi'],bha_bore_psi=r['bha_bore_psi'],bit_nozzles_psi=r['bit_nozzles_psi'],
            annulus_psi=r['annulus_psi'],buoyancy_psi=r['buoyancy_psi'],
            source='P3 event-budget.csv; primary,scenario,original; term means and measured median',
            qualification='Fixed friction exponents and rheology; no temperature change. Bound only, never used as input'))
    assert len(bounds)==7
    write(results/'flow-factor-bounds.csv',bounds)
    intervals = read(results/'A2-report-comparison.csv')
    intervals.sort(key=lambda r:(r['day'],float(r['depth_start_ft']),r['interval_id']))
    increments=[];previous=None
    for r in intervals:
        row=dict(classification='calculated',interval_id=r['interval_id'],report_no=r['report_no'],day=r['day'],
            median_bit_depth_ft=r['median_bit_depth_ft'],median_pressure_psi=r['median_pressure_psi'],
            median_flow_gpm=r['median_flow_gpm'],native_rows=r['native_rows'],status=r['status'],
            previous_interval_id=previous['interval_id'] if previous else '',depth_change_ft='',pressure_change_psi='',
            pressure_change_psi_per_ft='',qualification='Differences of pooled interval medians, not a controlled depth gradient; flow and operating state also change')
        if previous and all(x['median_bit_depth_ft'] and x['median_pressure_psi'] for x in (previous,r)):
            dz=float(r['median_bit_depth_ft'])-float(previous['median_bit_depth_ft'])
            dp=float(r['median_pressure_psi'])-float(previous['median_pressure_psi'])
            row.update(depth_change_ft=dz,pressure_change_psi=dp,
                pressure_change_psi_per_ft=dp/dz if dz else '',status='available' if dz else 'zero depth difference')
        increments.append(row);previous=r
    write(results/'A2-depth-increments.csv',increments)
    # A new source extract, retaining the original search inventory unchanged.
    nested='DailyDrillingReports_Well58-32.zip';member='DailyReportSummaryRpt9-20170804.pdf'
    with zipfile.ZipFile(a.raw58) as z,zipfile.ZipFile(io.BytesIO(z.read(nested))) as child:
        data=child.read(member)
    sweep=[]
    for page_no,page in enumerate(PdfReader(io.BytesIO(data)).pages,1):
        for line_no,line in enumerate((page.extract_text() or '').splitlines(),1):
            if 'Pumped sweep and circulated for survey' in line:
                sweep.append(dict(classification='measured source record',source_member=a.raw58.name+'!'+nested+'!'+member,
                    source_sha256=hashlib.sha256(data).hexdigest(),page=page_no,line_start=line_no,line_end=line_no,
                    source_text=line,report_date='2017-08-04',start='2017-08-04 23:15:00',end='2017-08-04 23:45:00',
                    qualification='Report calendar times; independent clock alignment not established'))
    assert len(sweep)==1,sweep
    write(HERE/'sources/sweep-record.csv',sweep)
    windows=read(ROOT/'validation/forge58-32/pressure-test/inputs/windows.csv')
    chosen=[r for r in windows if r['event_id']=='58-32-off0162']
    start=min(r['window_start'] for r in chosen);end=max(r['window_end'] for r in chosen)
    assert datetime.fromisoformat(start)>=datetime.fromisoformat(sweep[0]['start'])
    assert datetime.fromisoformat(end)<=datetime.fromisoformat(sweep[0]['end'])
    write(results/'sweep-coincidence.csv',[dict(classification='calculated',event_id='58-32-off0162',windows=len(chosen),
        first_window_start=start,last_window_end=end,report_start=sweep[0]['start'],report_end=sweep[0]['end'],
        contained_in_report_interval=True,source='inputs/windows.csv and sources/sweep-record.csv',
        qualification='Calendar-clock coincidence; pressure effect not measured or quantified')])
    print('Recomputed regime arithmetic, seven flow bounds, 42 depth intervals and the source-qualified sweep coincidence.')


if __name__=='__main__':
    main()
