"""Build the 10-s gel strength for each assembly, the low-shear yield stress
input of entry 6. Reads report inputs only; no target or residual.

16A: the mean of the daily-report 10-s gels over the run's report dates,
the same rows and averaging that give the frozen samples' PV and YP
(validation/forge16a/daily_well_inputs.csv and run_inputs.csv).

16B: the S2 rule (validation/forge16b/comparison_protocol_s2.md) applied to
the 10-s gel: the run's S2 source rows; a missing value is the nearest
actual measurement in either time direction within the same fluid system,
an exact tie resolved to the earlier one; a system with no gel measurement
has no yield stress (the S2 rule's zero water yield point).
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from borethm.studies import forge16_energy as energy

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def read(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main():
    rows = []
    runs = {r['run']: r for r in read(ROOT/'validation/forge16a/run_inputs.csv')}
    daily = read(ROOT/'validation/forge16a/daily_well_inputs.csv')
    plan = json.loads((ROOT/'validation/forge16b/s2/plan.json').read_text(encoding='utf-8'))  # the frozen sample plan
    plan_runs = sorted({s['run'] for s in plan['samples'] if s['well'] == '16A'})
    for run in plan_runs:
        dates = runs[run]['report_dates'].split('; ')
        found = [r for r in daily if r['BHA'] == run[:2] and r['report_date'] in dates]
        gels = [number(r['gel_10s']) for r in found]
        if not found or any(g is None for g in gels):
            raise ValueError(f'16A run {run}: missing 10-s gel')
        rows.append(dict(well='16A', run=run, gel_10s_lbf_100ft2=float(np.mean(gels)),
                         method='mean over run report dates', sources='; '.join(
                             f"{r['member'].split('/')[-1]} p{r['page']}" for r in found), donor_offset_days=''))
    data = ROOT/'validation/forge16b'
    observations = {}
    for filename in ['mud_samples.csv', 'mud_supplement_s1.csv']:
        for i, r in enumerate(read(data/filename), 1):
            t = datetime.strptime(r['sample'][:15], '%d-%b-%y %H:%M').replace(tzinfo=timezone.utc).timestamp()
            observations[f'{filename}:{i}'] = {**r, 'time_s': t, 'fluid_system': energy.fluid_system(t),
                                               'source_id': f'{filename}:{i}'}
    for run in read(data/'s2/revised-mud.csv'):
        values, notes, offsets = [], [], []
        for sid in run['source_ids'].split(';'):
            r = observations[sid]
            value = number(r.get('gel_10s'))
            if value is not None:
                values.append(value); notes.append(f'{sid} reported'); offsets.append(0.)
                continue
            candidates = [x for x in observations.values()
                          if x['fluid_system'] == r['fluid_system'] and number(x.get('gel_10s')) is not None]
            if candidates:
                donor = min(candidates, key=lambda x: (abs(x['time_s']-r['time_s']), x['time_s'], x['source_id']))
                values.append(number(donor['gel_10s']))
                notes.append(f"{sid} nearest {donor['source_id']} ({donor['sample'][:15]}, p{donor['page']})")
                offsets.append((donor['time_s']-r['time_s'])/86400)
            else:
                values.append(0.); notes.append(f"{sid} no gel in {r['fluid_system']}: zero"); offsets.append(None)
        rows.append(dict(well='16B', run=run['eow_bha'], gel_10s_lbf_100ft2=float(np.mean(values)),
                         method='S2 rule applied to the 10-s gel', sources='; '.join(notes),
                         donor_offset_days='; '.join('' if o is None else f'{o:+.3f}' for o in offsets)))
    with open(HERE/'gel_inputs.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    for r in rows:
        print(r['well'], r['run'], r['gel_10s_lbf_100ft2'], r['sources'][:90])


if __name__ == '__main__':
    main()
