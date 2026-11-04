"""Reduce tapered-joint scores against the working and entry 12 archives.

The scored variants and the working copy come from the external score output.
installed_primary and installed_no_local come from entry 12's retained
scoreboards, run-in tables and sample changes, without a new solve. Their
per-sample values relative to working are entry 12's sample-changes.csv.
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics as st

from score import typed, frozen, VARIANTS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
E12 = HERE.parent/'entry-12/results'
TAPERED = VARIANTS[1:]
ARCHIVED = ('installed_primary', 'installed_no_local')
FIELDS = ('bit_C', 'sensor_bore_C', 'return_C', 'spp_psi', 'model_hydraulic_kW')


def ids(key, rows, events):
    gap, well, group = key
    if gap == 'G4':
        return {r['event_id'] for r in events if r['event_id'] == group and r['success']}
    selected = [r for r in rows if r['well'] == well and r['success']]
    if gap == 'G1':
        selected = [r for r in selected if r['bha'] == group and r['raw_spp_psi'] is not None
                    and (well != '16A' or r['raw_differential_psi'] is not None)]
    elif gap == 'G2':
        selected = [r for r in selected if r['raw_spp_psi'] is not None]
    elif gap == 'G3':
        selected = [r for r in selected if r['bha'] == group and r['measured_bit_C'] is not None]
    elif gap == 'G5':
        selected = [r for r in selected if group == 'ALL' or r['source'] == group]
    elif gap == 'G6':
        selected = [r for r in selected if (r['bha'] in frozen.REGULAR if group == 'independent regular pipe'
                    else r['bha'] in frozen.TRIAL if group == 'trial' else r['bha'] == group)]
    return {r['sample_id'] for r in selected}


def rms(values):
    values = [v for v in values if v is not None]
    return math.sqrt(st.mean(v*v for v in values)) if values else None


def read(path):
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def number(value):
    return None if value in ('', None) else float(value)


def summary(variant, board):
    get = lambda gap, well, group: board[gap, well, group].get('bias')
    return dict(candidate=variant,
        G1_16A_RMS_psi=rms(r.get('bias') for k, r in board.items() if k[:2] == ('G1', '16A')),
        G1_16B_RMS_psi=rms(r.get('bias') for k, r in board.items() if k[:2] == ('G1', '16B')),
        G2_16A_bias_kW=get('G2', '16A', 'paired pressure samples'),
        G2_16B_bias_kW=get('G2', '16B', 'paired pressure samples'),
        G3_16A_RMS_C=rms(r.get('bias') for k, r in board.items() if k[0] == 'G3'),
        G4_peak_error_RMS_C=rms(r.get('bias') for k, r in board.items() if k[0] == 'G4'),
        G5_16A_return_bias_C=get('G5', '16A', 'ALL'),
        G6_regular_bias_C=get('G6', '16B', 'independent regular pipe'),
        G6_trial_bias_C=get('G6', '16B', 'trial'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--declaration', required=True)
    parser.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    results = args.results
    boards, circulation, events = {}, {}, {}
    for variant in VARIANTS:
        assert frozen.read_json(results/variant/'manifest.json')['complete']
        boards[variant] = {(r['gap'], r['well'], r['group']): r for r in typed(results/variant/'scoreboard.csv')}
        circulation[variant] = typed(results/variant/'circulation.csv')
        events[variant] = typed(results/variant/'run-in.csv')
    for variant in ARCHIVED:
        boards[variant] = {(r['gap'], r['well'], r['group']): r for r in typed(E12/variant/'scoreboard.csv')}
    archived = defaultdict(dict)
    for row in read(E12/'sample-changes.csv'):
        archived[row['candidate']][row['sample_id']] = row
    comparisons, summaries, changes, checks = [], [], [], []
    base = {r['sample_id']: r for r in circulation['working']}
    for variant in ('working', *ARCHIVED, *TAPERED):
        for key, old in boards['working'].items():
            new = boards[variant][key]
            paired = old['compared'] == new['compared']
            if variant in VARIANTS:
                paired = paired and ids(key, circulation['working'], events['working']) == ids(key, circulation[variant], events[variant])
            primary = boards['installed_primary'][key]
            comparisons.append(dict(candidate=variant, gap=key[0], well=key[1], group=key[2], units=old['units'],
                planned=old['planned'], working_compared=old['compared'], candidate_compared=new['compared'], paired=paired,
                measured_mean=old.get('measured_mean'), working_bias=old.get('bias'), installed_primary_bias=primary.get('bias'),
                candidate_bias=new.get('bias'), candidate_model_mean=new.get('model_mean'), candidate_MAE=new.get('MAE'),
                candidate_percent=new.get('mean_percent_error')))
        summaries.append(summary(variant, boards[variant]))
    for variant in TAPERED:
        for row in circulation[variant]:
            old = base[row['sample_id']]
            reference = archived['installed_primary'].get(row['sample_id'])
            entry = dict(candidate=variant, sample_id=row['sample_id'], well=row['well'], assembly=row['bha'],
                         paired=bool(row['success'] and old['success'] and reference['paired'] == 'True'))
            if entry['paired']:
                proxy = 'bore_84ft_C' if row['well'] == '16B' and row['bha'] in frozen.TRIAL | {'27', '38'} else 'bore_22ft_C'
                if row['well'] == '16A':
                    proxy = 'bit_C'
                for name, field in (('bit_C', 'bit_C'), ('sensor_bore_C', proxy), ('return_C', 'return_C'),
                                    ('spp_psi', 'spp_psi'), ('model_hydraulic_kW', 'model_hydraulic_W')):
                    a, b = old.get(field), row.get(field)
                    scale = 1000. if name.endswith('kW') else 1.
                    working = None if a is None or b is None else (b-a)/scale
                    shift = number(reference.get(name+'_change'))
                    entry[name+'_vs_working'] = working
                    entry[name+'_change'] = None if working is None or shift is None else working-shift
            changes.append(entry)
    frozen.write_csv(results/'comparison.csv', comparisons)
    frozen.write_csv(results/'summary.csv', summaries)
    frozen.write_csv(results/'sample-changes.csv', changes)
    grouped = defaultdict(list)
    for row in changes:
        if row['paired']:
            grouped[row['candidate'], row['well'], row['assembly']].append(row)
    assembly = []
    for (variant, well, bha), group in sorted(grouped.items()):
        row = dict(candidate=variant, well=well, assembly=bha, samples=len(group))
        for name in FIELDS:
            values = [r[name+'_change'] for r in group if r.get(name+'_change') is not None]
            row[name+'_change_mean'] = st.mean(values) if values else None
            row[name+'_change_min'] = min(values) if values else None
            row[name+'_change_max'] = max(values) if values else None
        assembly.append(row)
    frozen.write_csv(results/'assembly-changes.csv', assembly)
    by_sample = {(r['candidate'], r['sample_id']): r for r in changes}
    for old in typed(HERE/'predictions/model-only.csv'):
        if old['variant'] not in TAPERED:
            continue
        new = by_sample[old['variant'], old['sample_id']]
        for name in FIELDS:
            value = new.get(name+'_change')
            declared = old[name+'_change']
            tolerance = 1. if name == 'spp_psi' else (.001*max(abs(old['model_hydraulic_kW']), 1.)
                        if name == 'model_hydraulic_kW' else .1)
            checks.append(dict(candidate=old['variant'], sample_id=old['sample_id'], well=old['well'], field=name+'_change',
                declared=declared, scored=value, difference=None if value is None else value-declared,
                tolerance=tolerance, passed=value is not None and abs(value-declared) <= tolerance))
    frozen.write_csv(results/'prediction-checks.csv', checks)
    options = frozen.read_json(HERE/'options.json')
    angle = options['variants']['tapered_primary']['taper_angle_deg']
    criteria = []
    for variant in TAPERED:
        criteria.append(dict(criterion='paired frozen coverage', candidate=variant,
            passed=all(r['paired'] for r in comparisons if r['candidate'] == variant)
                   and all(r['paired'] for r in changes if r['candidate'] == variant)))
        criteria.append(dict(criterion='declared model-only effects reproduced', candidate=variant,
            passed=all(r['passed'] for r in checks if r['candidate'] == variant)))
    criteria.append(dict(criterion='angle within the formula branch to 45 degrees', candidate='tapered_primary', passed=0 < angle <= 45))
    primary_ok = all(r['passed'] for r in criteria if r['candidate'] == 'tapered_primary')
    frozen.write_json(results/'decision.json', dict(declaration_commit=args.declaration, rule=options['recommendation_rule'],
        source_range_assessment=options['source_range_assessment'], checks=criteria,
        recommendation=('recommend tapered_primary as the joint treatment for the working calculation' if primary_ok else
                        'do not recommend tapered_primary until the failed criterion is resolved'),
        adoption='pending maintainer decision; package defaults unchanged', secondary_slopes_affect_decision=False))
    derived = [p for p in results.glob('*') if p.suffix in ('.csv', '.json') and p.name != 'manifest.json']
    frozen.write_json(results/'manifest.json', dict(declaration_commit=args.declaration,
        comparison_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), variants=list(VARIANTS),
        archived_from_entry_12=list(ARCHIVED),
        source_manifests={v: hashlib.sha256((results/v/'manifest.json').read_bytes()).hexdigest() for v in VARIANTS},
        results_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in derived}))
    print(json.dumps(summaries, indent=2))
    print('Prediction and coverage checks:', sum(r['passed'] for r in criteria), '/', len(criteria))


if __name__ == '__main__':
    main()
