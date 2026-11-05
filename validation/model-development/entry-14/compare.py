"""Reduce the entry 14 score against entry 13 tapered_primary and the predictions.

The reference is entry 13's archived tapered_primary, with its per-sample table
read from the external output whose hash entry 13's manifest records. Shallow
measurements and measured slopes come from entry 13's archived tables.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics as st

from forge_tools import ENTRY13, HERE, OPTIONS, load
from summarise_predictions import comparing, frozen, read, typed, write

FIELDS = (('bit_C', 'bit_C', 1.), ('return_C', 'return_C', 1.), ('spp_psi', 'spp_psi', 1.), ('model_hydraulic_kW', 'model_hydraulic_W', 1000.))
TOL = OPTIONS['tolerances']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proxy(row):
    if row['well'] == '16A':
        return 'bit_C'
    return 'bore_84ft_C' if row['bha'] in frozen.TRIAL | {'27', '38'} else 'bore_22ft_C'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--declaration', required=True)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True, help='entry 13 tapered_primary bulk folder')
    args = parser.parse_args()
    results = args.results
    assert frozen.read_json(results/'entry14/manifest.json')['complete']
    assert sha(args.reference/'circulation.csv') == frozen.read_json(ENTRY13/'results/tapered_primary/manifest.json')['rebuildable_result_sha256']['circulation.csv']
    old, new = typed(args.reference/'circulation.csv'), typed(results/'entry14/circulation.csv')
    old_events, new_events = typed(args.reference/'run-in.csv'), typed(results/'entry14/run-in.csv')
    old_board = {(r['gap'], r['well'], r['group']): r for r in typed(ENTRY13/'results/tapered_primary/scoreboard.csv')}
    new_board = {(r['gap'], r['well'], r['group']): r for r in typed(results/'entry14/scoreboard.csv')}
    assert old_board.keys() == new_board.keys()

    expected = {(r['gap'], r['well'], r['group']): r for r in read(HERE/'predictions/expected-gaps.csv')}
    comparison = []
    for key, before in old_board.items():
        after = new_board[key]
        paired = before['compared'] == after['compared'] and comparing.ids(key, old, old_events) == comparing.ids(key, new, new_events)
        change = None if before.get('bias') is None or after.get('bias') is None else after['bias']-before['bias']
        forecast = expected.get(key)
        comparison.append(dict(gap=key[0], well=key[1], group=key[2], units=before['units'], planned=before['planned'], compared=after['compared'],
            paired=paired, measured_mean=before.get('measured_mean'), tapered_primary_bias=before.get('bias'), entry14_bias=after.get('bias'), change=change,
            predicted_change=None if forecast is None else float(forecast['predicted_change']),
            tapered_primary_MAE=before.get('MAE'), entry14_MAE=after.get('MAE')))
    write(results/'comparison.csv', comparison)
    write(results/'summary.csv', [comparing.summary('tapered_primary', old_board), comparing.summary('entry14', new_board)])

    table = {r['sample_id']: r for r in old}
    changes = []
    for row in new:
        before = table[row['sample_id']]
        entry = dict(sample_id=row['sample_id'], well=row['well'], assembly=row['bha'], paired=bool(row['success'] and before['success']))
        for name, field, scale in FIELDS:
            entry[name+'_change'] = (row[field]-before[field])/scale
        entry['sensor_bore_C_change'] = row[proxy(row)]-before[proxy(row)]
        changes.append(entry)
    write(results/'sample-changes.csv', changes)
    grouped = defaultdict(list)
    for row in changes:
        grouped[row['well'], row['assembly']].append(row)
    write(results/'assembly-changes.csv', [dict(well=k[0], assembly=k[1], samples=len(v),
        **{f+'_change_mean': st.mean(r[f+'_change'] for r in v) for f in ('bit_C', 'sensor_bore_C', 'return_C', 'spp_psi', 'model_hydraulic_kW')})
        for k, v in sorted(grouped.items())])

    scored = {r['sample_id']: r for r in changes}
    checks = []
    for row in read(HERE/'predictions/model-only.csv'):
        for name in ('bit_C', 'sensor_bore_C', 'return_C', 'spp_psi', 'model_hydraulic_kW'):
            declared, value = float(row[name+'_change']), scored[row['sample_id']][name+'_change']
            tolerance = TOL['pressure_psi'] if name == 'spp_psi' else TOL['power_fraction']*max(abs(float(row['model_hydraulic_kW_after'])), 1.) if name == 'model_hydraulic_kW' else TOL['temperature_C']
            checks.append(dict(sample_id=row['sample_id'], well=row['well'], field=name+'_change', declared=declared, scored=value,
                difference=value-declared, tolerance=tolerance, passed=abs(value-declared) <= tolerance))
    write(results/'prediction-checks.csv', checks)

    shallow_before = [r for r in read(ENTRY13/'results/shallow-diagnostic.csv') if r['candidate'] == 'tapered_primary']
    forecast = {r['window_id']: r for r in read(HERE/'predictions/shallow-windows.csv')}
    shallow = []
    for r in shallow_before:
        p = forecast[r['window_id']]
        measured, before, after = float(r['measured_spp_psi']), float(r['candidate_spp_psi']), float(p['spp_after_psi'])
        shallow.append(dict(window_id=r['window_id'], assembly=r['assembly'], bit_depth_ft=float(r['bit_depth_ft']), flow_gpm=float(r['flow_gpm']), tools=p['tools'],
            measured_spp_psi=measured, spp_before_psi=before, spp_after_psi=after, replay_difference_psi=float(p['spp_before_psi'])-before,
            gap_before_psi=measured-before, accounted_psi=after-before, gap_after_psi=measured-after, fraction_accounted=(after-before)/(measured-before)))
    write(results/'shallow-windows.csv', shallow)

    measured = {(r['assembly'], r['excursion'], r['flow_centre_gpm']): r for r in read(ENTRY13/'results/secondary/slopes.csv') if r['candidate'] == 'tapered_primary'}
    slopes = []
    for r in read(HERE/'predictions/trip-slopes.csv'):
        m = measured[r['assembly'], r['excursion'], r['flow_centre_gpm']]
        assert abs(float(m['modelled_slope'])-float(r['slope_before'])) < 1e-6
        slopes.append(dict(assembly=r['assembly'], excursion=r['excursion'], flow_centre_gpm=r['flow_centre_gpm'], added_pipe=r['added_pipe'],
            measured_slope=float(m['measured_slope']), measured_ci95_half=float(m['measured_ci95_half']),
            slope_before=float(r['slope_before']), slope_after=float(r['slope_after']), ratio_before=float(m['slope_ratio']),
            ratio_after=float(m['measured_slope'])/float(r['slope_after']), predicted_multiplier=float(r['predicted_ratio_multiplier'])))
    write(results/'trip-slopes.csv', slopes)

    fails = sum(not r['passed'] for r in checks)
    derived = [p for p in results.glob('*.csv')]
    frozen.write_json(results/'manifest.json', dict(declaration_commit=args.declaration, comparison_script_sha256=sha(Path(__file__)),
        reference='entry 13 tapered_primary', source_manifest_sha256=sha(results/'entry14/manifest.json'),
        checks=len(checks), checks_failed=fails, largest_fraction_of_tolerance=max(abs(r['difference'])/r['tolerance'] for r in checks),
        paired_coverage=all(r['paired'] for r in comparison), results_sha256={p.name: sha(p) for p in derived}))
    print('checks', len(checks), 'failed', fails, 'paired', all(r['paired'] for r in comparison))
    print(json.dumps(read(results/'summary.csv'), indent=1))


if __name__ == '__main__':
    main()
