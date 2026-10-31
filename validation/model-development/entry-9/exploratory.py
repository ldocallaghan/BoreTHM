"""Reproduce the described one-minute 16B exploratory reduction.

The original executable was not archived. Operational details are stated
in the results README. Its inferred segment labels are kept separate from
the report-constrained ten-second comparison.
"""
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import time

import numpy as np

from diagnose import Calculation, HERE, ROOT, finite, read, write


def select():
    rows = read(ROOT/'validation/forge16b/pason_selected_1min.csv')
    definitions = read(ROOT/'validation/forge16b/run_definitions.csv')
    segments = defaultdict(list)
    previous = None
    below = False
    group = 0
    for i, row in enumerate(rows, 2):
        bit = finite(row['bit_depth_ft'])
        hole = finite(row['hole_depth_ft'])
        if bit is None or hole is None:
            continue
        now = datetime.fromisoformat(row['time'])
        shallow = bit < 200
        if previous is not None and ((now-previous).total_seconds()>6*3600 or (shallow and not below)):
            group += 1
        segments[group].append({**row, 'source_row': i})
        below, previous = shallow, now
    windows, inventory = [], []
    for segment, items in segments.items():
        low = min(float(r['hole_depth_ft']) for r in items)
        high = max(float(r['hole_depth_ft']) for r in items)
        choices = [d['eow_bha'] for d in definitions if
                   low >= float(d['depth_in_ft'])-20 and high <= float(d['depth_out_ft'])+20
                   and high > float(d['depth_in_ft'])+5]
        assembly = choices[0] if len(choices)==1 else ''
        inventory.append(dict(segment=segment, start=items[0]['time'], end=items[-1]['time'],
            minimum_hole_ft=low, maximum_hole_ft=high, assembly=assembly,
            candidates=';'.join(choices), source_rows=len(items)))
        bins = defaultdict(list)
        for row in items:
            stamp = datetime.fromisoformat(row['time'])
            bins[stamp.replace(minute=stamp.minute//2*2, second=0)].append(row)
        for _, records in sorted(bins.items()):
            if len(records)!=2 or (datetime.fromisoformat(records[1]['time'])-
                                  datetime.fromisoformat(records[0]['time'])).total_seconds()!=60:
                continue
            q = [finite(r['flow_gpm']) for r in records]
            bit = [float(r['bit_depth_ft']) for r in records]
            hole = [float(r['hole_depth_ft']) for r in records]
            if any(x is None or not 100<x<=2000 for x in q):
                continue
            if max(q)-min(q)>.02*np.mean(q) or max(bit)-min(bit)>5:
                continue
            if not all(h-b>=10 for h,b in zip(hole,bit)):
                continue
            row = dict(window_id=f'explore-{len(windows)+1:05d}', assembly=assembly,
                excursion=segment, start=records[0]['time'], end=records[-1]['time'],
                source_row_first=records[0]['source_row'], source_row_last=records[-1]['source_row'])
            for field in ['bit_depth_ft','hole_depth_ft','flow_gpm','spp_psi',
                          'reported_differential_psi','temp_in_F','temp_out_F']:
                values = [finite(r[field]) for r in records]
                row[field] = float(np.mean(values)) if all(x is not None for x in values) else None
            windows.append(row)
    return inventory, windows


def main():
    output = HERE/'results'
    calc = Calculation()
    segments, windows = select()
    write(output/'exploratory-segments.csv', segments)
    rows = []
    start = time.perf_counter()
    for w in windows:
        row = {**w, 'well': '16B', 'role': 'exploratory', 'variant': 'inlet_return',
               'measured_spp_psi': w['spp_psi'], 'status': 'excluded', 'reason': ''}
        if not w['assembly']:
            row['reason'] = 'segment assignment unresolved'
        elif ('16B',w['assembly']) not in calc.templates:
            row['reason'] = 'assembly absent from frozen geometry and mud plan'
        elif any(w[k] is None for k in ['spp_psi','temp_in_F','temp_out_F']):
            row['reason'] = 'missing comparison channel'
        else:
            try:
                sample = calc.trip_sample({**w, 'well': '16B'})
                g = calc.geometry(sample, w['bit_depth_ft'], w['hole_depth_ft'])
                temp = ((w['temp_in_F']+w['temp_out_F'])/2-32)/1.8
                inlet = (w['temp_in_F']-32)/1.8
                fluid, _, _ = calc.fluid(sample)
                rho = float(calc.m1.fluid_props(np.array([inlet]),np.array([calc.m1.P_SURF]),fluid)[0][0])
                hyd = calc.pressure(sample, g, w['flow_gpm'], temp, w['flow_gpm']*calc.whole.GPM*rho)
                model = hyd['spp']/calc.whole.PSI
                row.update(status='ok', modelled_spp_psi=model, residual_psi=model-w['spp_psi'],
                    measured_modelled_ratio=w['spp_psi']/model, temperature_C=temp,
                    input_sample_id=sample['id'])
            except Exception as error:
                row.update(status='calculation_error', reason=str(error), error_type=type(error).__name__)
        rows.append(row)
    write(output/'exploratory-windows.csv', rows)
    print(f'Exploratory reduction: {len(windows)} windows, '
          f'{sum(r["status"]=="ok" for r in rows)} evaluated, {time.perf_counter()-start:.1f} s')


if __name__ == '__main__':
    main()
