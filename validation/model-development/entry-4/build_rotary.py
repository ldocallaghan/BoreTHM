"""Rotary-drive inputs for each frozen circulation sample.

Reads the rig ten-second records and writes `rotary_inputs.csv`. Only surface
rotary speed, top-drive torque, weight on bit, flow and the on-bottom flag are
read. No temperature, pressure or residual is used.

16A: GDR 1283 member `16A(78)-32_time_data_10s_intervals_standard.csv`. Its
timestamps have one-minute resolution with about six rows per minute; all
rows are kept. The file labels top-drive torque kft-lbs, but its values are
in ft-lbf: the median while rotating on bottom is about 4,300, and the daily
report for 26 November 2020 gives "Torque 6,500" at 50 rpm. The raw 10-s file
labels the same channel ft-lbs.
16B: GDR 1516 member `16B_Pason.zip`, file `10 Second Data.csv`.

On-bottom window: 16A, rows within 15 minutes of the sample centre (the
frozen 16A temperature window); 16B, the frozen window's source rows. Rows
count when the on-bottom flag is set and flow exceeds 300 gal/min, the
existing drilling-flow threshold.

Off-bottom reference: rows from two hours before the window start to the
window end with the on-bottom flag clear, flow above 300 gal/min and rotary
speed above 20 rpm. Its median torque is the off-bottom rotating torque.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PLAN = ROOT/'validation/forge16b/s2/plan.json'
MEMBER_16A = '16A(78)-32_time_data_10s_intervals_standard.csv'
COLUMNS_16A = {'Date': 'time', 'On Bottom': 'on_bottom', 'Top Drive Revolutions per Minute': 'rpm',
               'Top Drive Torque': 'torque_ft_lbf', 'Flow In': 'flow_gpm', 'Weight on Bit': 'wob_klbf'}
COLUMNS_16B = {'Rotary RPM (RPM)': 'rpm', 'Top Drive Torque (kft_lb)': 'torque_kft_lbf',
               'Weight on Bit (klbs)': 'wob_klbf', 'Total Pump Output (gal_per_min)': 'flow_gpm',
               'On Bottom (unitless)': 'on_bottom', 'Bit Depth (feet)': 'bit_depth_ft',
               'Hole Depth (feet)': 'hole_depth_ft'}
FLOW_MIN, RPM_MIN, REFERENCE_H, MIN_ROWS = 300.0, 20.0, 2.0, 3


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read_16a(path):
    if path.suffix == '.zip':
        with zipfile.ZipFile(path) as z, z.open(MEMBER_16A) as f:
            frame = pd.read_csv(f, skiprows=[1], usecols=list(COLUMNS_16A), low_memory=False)
    else:
        frame = pd.read_csv(path, skiprows=[1], usecols=list(COLUMNS_16A), low_memory=False)
    frame = frame.rename(columns=COLUMNS_16A)
    frame['time'] = pd.to_datetime(frame['time'])
    return frame.sort_values('time', kind='stable').reset_index(drop=True)


def read_16b(path):
    if path.name != '16B_Pason.zip':
        with zipfile.ZipFile(path) as outer:
            data = io.BytesIO(outer.read('16B_Pason.zip'))
    else:
        data = path
    with zipfile.ZipFile(data) as z:
        with z.open('10 Second Data.csv') as f:
            header = next(csv.reader(io.TextIOWrapper(f, encoding='utf-8-sig')))
        date, clock = header[0], header[1]
        with z.open('10 Second Data.csv') as f:
            chunks = pd.read_csv(io.TextIOWrapper(f, encoding='utf-8-sig'), usecols=[date, clock, *COLUMNS_16B],
                                 na_values=['-999.25'], dtype={date: str, clock: str}, chunksize=200000)
            frame = pd.concat(list(chunks), ignore_index=True)
    frame['source_row'] = np.arange(2, len(frame)+2)
    frame['time'] = pd.to_datetime(frame[date].str.replace('/', '-')+' '+frame[clock])
    frame = frame.rename(columns=COLUMNS_16B)
    frame['torque_ft_lbf'] = frame['torque_kft_lbf']*1000.
    return frame


def summarise(on, off):
    row = dict(on_rows=len(on), off_rows=len(off))
    if len(on):
        row.update(rpm_on=float(on['rpm'].mean()), torque_on_ft_lbf=float(on['torque_ft_lbf'].mean()),
                   wob_on_klbf=float(on['wob_klbf'].median()),
                   rotary_power_on_W=float((2*np.pi/60*on['rpm']*on['torque_ft_lbf']*1.3558179483314004).mean()))
    if len(off) >= MIN_ROWS:
        row.update(rpm_off=float(off['rpm'].median()), torque_off_ft_lbf=float(off['torque_ft_lbf'].median()))
    return row


def qualified(frame):
    return frame[(frame['on_bottom'] == 1) & (frame['flow_gpm'] > FLOW_MIN)]


def reference(frame):
    return frame[(frame['on_bottom'] == 0) & (frame['flow_gpm'] > FLOW_MIN) & (frame['rpm'] > RPM_MIN)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gdr1283', type=Path, required=True, help='GDR 1283 ZIP, or its 10-s standard CSV member')
    parser.add_argument('--gdr1516', type=Path, required=True, help='GDR 1516 ZIP, or its 16B_Pason.zip member')
    parser.add_argument('--output', type=Path, default=HERE/'rotary_inputs.csv')
    args = parser.parse_args()
    samples = json.loads(PLAN.read_text(encoding='utf-8'))['samples']
    rows = []
    a = read_16a(args.gdr1283)
    times = a['time'].to_numpy()
    for s in (x for x in samples if x['well'] == '16A'):
        centre = np.datetime64(pd.Timestamp(s['time']))
        start, end = centre-np.timedelta64(15, 'm'), centre+np.timedelta64(15, 'm')
        window = a.iloc[np.searchsorted(times, start, 'left'):np.searchsorted(times, end, 'right')]
        history = a.iloc[np.searchsorted(times, start-np.timedelta64(int(REFERENCE_H*60), 'm'), 'left'):
                         np.searchsorted(times, end, 'right')]
        rows.append(dict(sample_id=s['id'], well='16A', bha=s['run'], window_start=str(start), window_end=str(end),
                         **summarise(qualified(window), reference(history))))
    b = read_16b(args.gdr1516)
    index = b.set_index('source_row')
    times = b['time'].to_numpy()
    for s in (x for x in samples if x['well'] == '16B'):
        first, last = int(s['source_row_first']), int(s['source_row_last'])
        window = index.loc[first:last]
        start, end = window['time'].iloc[0], window['time'].iloc[-1]
        history = b.iloc[np.searchsorted(times, np.datetime64(start)-np.timedelta64(int(REFERENCE_H*60), 'm'), 'left'):
                         np.searchsorted(times, np.datetime64(end), 'right')]
        rows.append(dict(sample_id=s['id'], well='16B', bha=s['run'], window_start=str(start), window_end=str(end),
                         **summarise(qualified(window), reference(history))))
    fields = ['sample_id', 'well', 'bha', 'window_start', 'window_end', 'on_rows', 'rpm_on', 'torque_on_ft_lbf',
              'wob_on_klbf', 'rotary_power_on_W', 'off_rows', 'rpm_off', 'torque_off_ft_lbf']
    with args.output.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    manifest = dict(sources={'GDR 1283': dict(file=args.gdr1283.name, sha256=sha(args.gdr1283)),
                             'GDR 1516': dict(file=args.gdr1516.name, sha256=sha(args.gdr1516))},
                    plan_sha256=sha(PLAN), output_sha256=sha(args.output),
                    rules=dict(flow_min_gpm=FLOW_MIN, rpm_min=RPM_MIN, reference_hours=REFERENCE_H,
                               minimum_reference_rows=MIN_ROWS))
    args.output.with_name('rotary_inputs_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(f'{len(rows)} samples; {sum(r["on_rows"] == 0 for r in rows)} without on-bottom rows; '
          f'{sum("torque_off_ft_lbf" not in r for r in rows)} without an off-bottom reference')


if __name__ == '__main__':
    main()
