"""Reduce completed entry 10 scores; apply only the declared acceptance rule."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics as st

from score import typed, frozen, VARIANTS, DECLARATION

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=HERE/'results')
    args = parser.parse_args()
    results = args.results
    boards, circulation, events = {}, {}, {}
    for variant in VARIANTS:
        assert frozen.read_json(results/variant/'manifest.json')['complete']
        boards[variant] = {(r['gap'], r['well'], r['group']): r
                           for r in typed(results/variant/'scoreboard.csv')}
        circulation[variant] = typed(results/variant/'circulation.csv')
        events[variant] = typed(results/variant/'run-in.csv')
    comparisons, summaries, changes, prediction_checks = [], [], [], []
    base_rows = {r['sample_id']: r for r in circulation['baseline']}
    for variant in VARIANTS:
        for key, old in boards['baseline'].items():
            new = boards[variant][key]
            before = ids(key, circulation['baseline'], events['baseline'])
            after = ids(key, circulation[variant], events[variant])
            paired = before == after and old['compared'] == new['compared']
            comparisons.append(dict(candidate=variant, gap=key[0], well=key[1], group=key[2],
                units=old['units'], planned=old['planned'], before_compared=old['compared'],
                after_compared=new['compared'], paired=paired,
                before_model_mean=old.get('model_mean'), after_model_mean=new.get('model_mean'),
                measured_mean=old.get('measured_mean'), before_bias=old.get('bias'), after_bias=new.get('bias'),
                before_MAE=old.get('MAE'), after_MAE=new.get('MAE'),
                before_percent=old.get('mean_percent_error'), after_percent=new.get('mean_percent_error'),
                bias_change=(new['bias']-old['bias'] if paired and old.get('bias') is not None
                             and new.get('bias') is not None else None)))
        board = boards[variant]
        get = lambda gap, well, group: board[gap, well, group].get('bias')
        summary = dict(candidate=variant,
            G1_16A_RMS_psi=rms(r.get('bias') for k,r in board.items() if k[:2] == ('G1','16A')),
            G1_16B_RMS_psi=rms(r.get('bias') for k,r in board.items() if k[:2] == ('G1','16B')),
            G2_16A_bias_kW=get('G2','16A','paired pressure samples'),
            G2_16B_bias_kW=get('G2','16B','paired pressure samples'),
            G3_16A_RMS_C=rms(r.get('bias') for k,r in board.items() if k[0] == 'G3'),
            G4_peak_error_RMS_C=rms(r.get('bias') for k,r in board.items() if k[0] == 'G4'),
            G5_16A_return_bias_C=get('G5','16A','ALL'),
            G6_regular_bias_C=get('G6','16B','independent regular pipe'),
            G6_trial_bias_C=get('G6','16B','trial'))
        summaries.append(summary)
        for row in circulation[variant]:
            old = base_rows[row['sample_id']]
            entry = dict(candidate=variant, sample_id=row['sample_id'], well=row['well'], assembly=row['bha'],
                         paired=bool(row['success'] and old['success']))
            if entry['paired']:
                proxy = 'bore_84ft_C' if row['well']=='16B' and row['bha'] in frozen.TRIAL|{'27','38'} else 'bore_22ft_C'
                if row['well']=='16A':
                    proxy = 'bit_C'
                for name, field in [('bit_C','bit_C'),('sensor_bore_C',proxy),('return_C','return_C'),
                                    ('spp_psi','spp_psi'),('model_hydraulic_kW','model_hydraulic_W')]:
                    a, b = old.get(field), row.get(field)
                    scale = 1000. if name.endswith('kW') else 1.
                    entry[name+'_change'] = None if a is None or b is None else (b-a)/scale
            changes.append(entry)
    frozen.write_csv(results/'comparison.csv', comparisons)
    frozen.write_csv(results/'summary.csv', summaries)
    frozen.write_csv(results/'sample-changes.csv', changes)
    grouped = defaultdict(list)
    for row in changes:
        if row['paired']:
            grouped[row['candidate'],row['well'],row['assembly']].append(row)
    assembly_changes = []
    for (variant,well,bha), group in sorted(grouped.items()):
        row = dict(candidate=variant,well=well,assembly=bha,samples=len(group))
        for field in ('bit_C_change','sensor_bore_C_change','return_C_change','spp_psi_change','model_hydraulic_kW_change'):
            values = [r[field] for r in group if r.get(field) is not None]
            row[field+'_mean'] = st.mean(values) if values else None
            row[field+'_min'] = min(values) if values else None
            row[field+'_max'] = max(values) if values else None
        assembly_changes.append(row)
    frozen.write_csv(results/'assembly-changes.csv',assembly_changes)
    by_sample = {(r['candidate'],r['sample_id']):r for r in changes}
    for old in typed(HERE/'predictions/model-only.csv'):
        # The prediction archive calls the assembly column assembly and the variant variant.
        new = by_sample[old['variant'],old['sample_id']]
        for field in ('bit_C_change','sensor_bore_C_change','return_C_change','spp_psi_change','model_hydraulic_kW_change'):
            value = new.get(field)
            tolerance = 1. if field=='spp_psi_change' else (.001*max(abs(old['model_hydraulic_kW']),1.)
                        if field=='model_hydraulic_kW_change' else .1)
            prediction_checks.append(dict(candidate=old['variant'],sample_id=old['sample_id'],field=field,
                declared=old[field],scored=value,difference=None if value is None else value-old[field],
                tolerance=tolerance,passed=value is not None and abs(value-old[field])<=tolerance))
    frozen.write_csv(results/'prediction-checks.csv',prediction_checks)
    uncertainty = [dict(candidate=v,well=w,assembly=b,additional_lower_psi=None,additional_upper_psi=None,
        band_quantified=False,basis='Installed tool loss range unavailable; no finite band inferred from other motor models')
        for v,w,b in grouped]
    frozen.write_csv(results/'pressure-uncertainty.csv',uncertainty)
    primary = next(r for r in summaries if r['candidate']=='smooth')
    baseline = summaries[0]
    checks = [dict(criterion='paired frozen coverage',passed=all(r['paired'] for r in comparisons if r['candidate']=='smooth')),
              dict(criterion='declared model-only effects reproduced',passed=all(r['passed'] for r in prediction_checks if r['candidate']=='smooth'))]
    for well in ('16A','16B'):
        field = f'G1_{well}_RMS_psi'
        difference = primary[field]-baseline[field]
        checks.append(dict(criterion=f'G1 {well} assembly-bias RMS',before=baseline[field],after=primary[field],
                           deterioration=difference,tolerance=1.,units='psi',passed=difference<=1.))
        key = ('G2',well,'paired pressure samples')
        old,new = boards['baseline'][key],boards['smooth'][key]
        difference = abs(new['bias'])-abs(old['bias'])
        tolerance = .001*abs(old['measured_mean'])
        checks.append(dict(criterion=f'G2 {well} absolute well-mean error',before=old['bias'],after=new['bias'],
                           deterioration=difference,tolerance=tolerance,units='kW',passed=difference<=tolerance))
    for key,old in boards['baseline'].items():
        if key[0] in ('G3','G6') or key == ('G5','16A','ALL'):
            new = boards['smooth'][key]
            available = old.get('bias') is not None and new.get('bias') is not None
            difference = abs(new['bias'])-abs(old['bias']) if available else None
            checks.append(dict(criterion=' '.join(key)+' absolute bias',before=old.get('bias'),after=new.get('bias'),
                deterioration=difference,tolerance=2.,units='C',passed=available and difference<=2.))
    frozen.write_json(results/'decision.json',dict(declaration_commit=DECLARATION,
        rule=frozen.read_json(HERE/'options.json')['decision_rule'],checks=checks,
        recommendation='recommend keep smooth pipe friction' if all(r['passed'] for r in checks) else 'recommend against adopting smooth pipe friction under the declared rule',
        adoption='pending user decision; package defaults unchanged',
        secondary_slopes_affect_decision=False))
    derived = [p for p in results.glob('*') if p.suffix in ('.csv','.json') and p.name!='manifest.json']
    frozen.write_json(results/'manifest.json',dict(declaration_commit=DECLARATION,
        comparison_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        variants=list(VARIANTS),source_manifests={v:hashlib.sha256((results/v/'manifest.json').read_bytes()).hexdigest() for v in VARIANTS},
        results_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in derived}))
    print(json.dumps(summaries,indent=2))
    print('Acceptance checks:',sum(r['passed'] for r in checks),'/',len(checks))


if __name__ == '__main__':
    main()
