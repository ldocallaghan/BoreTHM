"""Reduce the model-only predictions to the declared expected gap changes.

The frozen sample groups come from entry 13's compare.py. Membership of a group
uses the archived tapered_primary circulation table, and the expected bias is
that archive's scoreboard bias plus the mean model-only change over the group.
No new measured target enters a calculation.
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import statistics as st

import numpy as np

from borethm import hydraulic_losses as hl
from borethm import tool_losses
from forge_tools import ENTRY13, HERE, load

comparing = load('entry13_compare', ENTRY13/'compare.py')
frozen = comparing.frozen
typed = comparing.typed
ROOT = HERE.parents[2]
FIELD = {'G1': 'spp_psi_change', 'G2': 'model_hydraulic_kW_change', 'G3': 'bit_C_change', 'G5': 'return_C_change', 'G6': 'sensor_bore_C_change'}


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def expected_changes(rows, reference, board, events):
    """One row per frozen gap group, with the predicted change in its bias."""
    table = {r['sample_id']: r for r in rows}
    out = []
    for key, row in board.items():
        gap, well, group = key
        if gap == 'G4':
            continue
        members = comparing.ids(key, reference, events)
        changes = [float(table[i][FIELD[gap]]) for i in members if i in table]
        mean = st.mean(changes) if changes else 0.
        out.append(dict(gap=gap, well=well, group=group, units=row['units'], samples=len(changes),
                        predicted_change=mean, predicted_change_min=min(changes, default=0.), predicted_change_max=max(changes, default=0.),
                        tapered_primary_bias=row.get('bias'), predicted_bias=None if row.get('bias') is None else row['bias']+mean))
    return out


def by_assembly(rows):
    grouped = defaultdict(list)
    for r in rows:
        grouped[r['well'], r['assembly']].append(r)
    out = []
    for (well, assembly), group in sorted(grouped.items()):
        row = dict(well=well, assembly=assembly, samples=len(group),
                   flow_gpm_min=min(float(r['flow_gpm']) for r in group), flow_gpm_max=max(float(r['flow_gpm']) for r in group))
        for name in ('spp_psi', 'model_hydraulic_kW', 'bit_C', 'sensor_bore_C', 'return_C'):
            values = [float(r[name+'_change']) for r in group]
            row.update({name+'_change_mean': st.mean(values), name+'_change_min': min(values), name+'_change_max': max(values)})
        out.append(row)
    return out


def slope_drift(output):
    """The slope of the 6.75-in pulser allowance against depth, from each trip group's stage flows.

    A tool loss does not depend on pipe length, so a slope can change only
    through the flow differences among the depth stages of a group.
    """
    allowance = tool_losses.default_for('mwd_pulser', 6.75)
    windows = {r['window_id']: r for r in read(HERE.parent/'entry-9/results/windows.csv')}
    stages = [r for r in read(ENTRY13/'results/secondary/depth-stages.csv') if r['candidate'] == 'tapered_primary']
    out = []
    for slope in read(output/'trip-slopes.csv'):
        group = [r for r in stages if (r['assembly'], r['excursion'], r['flow_centre_gpm']) == (slope['assembly'], slope['excursion'], slope['flow_centre_gpm'])]
        depth, loss = [], []
        for stage in group:
            chosen = [windows[w] for w in stage['window_ids'].split(';')]
            density = [float(w['mass_rate_kg_s'])/(float(w['flow_gpm'])*hl.GPM)/(tool_losses.WATER_PPG*hl.PPG) for w in chosen]
            loss.append(st.mean(allowance.dp_ref_psi*d*(float(w['flow_gpm'])/allowance.flow_ref_gpm)**allowance.exponent for d, w in zip(density, chosen)))
            depth.append(float(stage['bit_depth_ft'])/1000)
        out.append(dict(assembly=slope['assembly'], excursion=slope['excursion'], flow_centre_gpm=slope['flow_centre_gpm'],
                        stage_flow_min_gpm=min(float(r['flow_gpm']) for r in group), stage_flow_max_gpm=max(float(r['flow_gpm']) for r in group),
                        allowance_slope_from_stage_flows=float(np.polyfit(depth, loss, 1)[0]),
                        slope_change=float(slope['slope_after'])-float(slope['slope_before'])))
    return out


def write(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, list(dict.fromkeys(k for r in rows for k in r)), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True, help='entry 13 tapered_primary bulk folder')
    parser.add_argument('--output', type=Path, default=HERE/'predictions')
    args = parser.parse_args()
    rows = read(args.output/'model-only.csv')
    reference, events = typed(args.reference/'circulation.csv'), typed(args.reference/'run-in.csv')
    board = {(r['gap'], r['well'], r['group']): r for r in typed(ENTRY13/'results/tapered_primary/scoreboard.csv')}
    write(args.output/'expected-gaps.csv', expected_changes(rows, reference, board, events))
    write(args.output/'assembly-changes.csv', by_assembly(rows))
    write(args.output/'trip-slope-drift.csv', slope_drift(args.output))
    manifest = json.loads((args.output/'manifest.json').read_text(encoding='utf-8'))
    manifest['reference_circulation_sha256'] = hashlib.sha256((args.reference/'circulation.csv').read_bytes()).hexdigest()
    manifest['derived_sha256'] = {n: hashlib.sha256((args.output/n).read_bytes()).hexdigest() for n in ('expected-gaps.csv', 'assembly-changes.csv', 'trip-slope-drift.csv', 'default-route-check.csv')}
    (args.output/'manifest.json').write_bytes((json.dumps(manifest, indent=2)+'\n').encode('utf-8'))


if __name__ == '__main__':
    main()
