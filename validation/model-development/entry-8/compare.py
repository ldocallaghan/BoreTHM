"""Set the entry 8 scores beside the legacy baseline, the working calculation
and entry 7's no-yield score.

Reads saved scoreboard outputs only; runs no model. The working calculation
is entry 5's (entries 1-5 with D5). A row is paired only when all
calculations compare the same number of samples and the same successful
samples: the same sample IDs in the row's well for the circulation gaps, and
the same events for G4. The declared summary measures are the root-mean-
square of the nine 16A assembly bit biases (G3), the 16A standpipe biases
(G1) and the 16A return bias (G5).

The decision check compares every circulation sample at film multiplier 1.0
with entry 7's no-yield score: bit and return temperatures within 0.01 C and
standpipe pressure within 1 psi. regime-summary.csv gives, by assembly, the
mean shares of drill-pipe annulus that regime.csv records.
"""
from collections import defaultdict
import argparse
import importlib.util
import math
from pathlib import Path
import statistics as st
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('frozen_scoreboard', ROOT/'validation/scoreboard/scoreboard.py')
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)
FILMS = ('film-1.00', 'film-0.85', 'film-1.05')
REFERENCE = {'legacy': ROOT/'validation/scoreboard/baseline',
             'working': ROOT/'validation/model-development/entry-5/results',
             'entry7-no-yield': ROOT/'validation/model-development/entry-7/results/no-yield'}
TOLERANCE = dict(bit_C=0.01, return_C=0.01, spp_psi=1.0)


def number(value):
    return None if value in ('', None) else float(value)


def successes(root):
    ids = defaultdict(set)
    for r in score.read_csv(root/'circulation.csv'):
        if r['success'] == 'True':
            ids[r['well']].add(r['sample_id'])
    ids['G4'] = {r['event_id'] for r in score.read_csv(root/'run-in.csv') if r['success'] == 'True'}
    return ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=HERE/'results')
    args = parser.parse_args()
    roots = {**REFERENCE, **{f: args.results/f for f in FILMS}}
    boards = {k: {(r['gap'], r['well'], r['group']): r for r in score.read_csv(p/'scoreboard.csv')} for k, p in roots.items()}
    succeeded = {k: successes(p) for k, p in roots.items()}
    rows = []
    for key, ref in boards['working'].items():
        row = dict(gap=key[0], well=key[1], group=key[2], units=ref['units'], planned=int(ref['planned']))
        counts = {k: boards[k][key]['compared'] for k in boards}
        samples = {k: frozenset(succeeded[k]['G4' if key[0] == 'G4' else key[1]]) for k in boards}
        row['paired'] = len(set(counts.values())) == 1 and len(set(samples.values())) == 1
        for name in boards:
            old = boards[name][key]
            row[f'{name}_compared'] = int(old['compared'])
            row[f'{name}_bias'] = number(old['bias'])
        for f in FILMS:
            if row['paired'] and row[f'{f}_bias'] is not None and row['working_bias'] is not None:
                row[f'{f}_change_from_working'] = row[f'{f}_bias']-row['working_bias']
        row['measured_mean'] = number(ref['measured_mean'])
        rows.append(row)
    score.write_csv(args.results/'comparison.csv', rows)

    summary = []
    for name in boards:
        g3 = [r[f'{name}_bias'] for r in rows if r['gap'] == 'G3' and r['well'] == '16A' and r[f'{name}_bias'] is not None]
        g1 = [r[f'{name}_bias'] for r in rows if r['gap'] == 'G1' and r['well'] == '16A' and r[f'{name}_bias'] is not None]
        g5 = [r[f'{name}_bias'] for r in rows if r['gap'] == 'G5' and r['group'] == 'ALL']
        summary.append(dict(calculation=name, g3_16A_assemblies=len(g3),
                            g3_16A_rms_C=math.sqrt(st.mean(x*x for x in g3)) if g3 else None,
                            g3_16A_mean_C=st.mean(g3) if g3 else None,
                            g1_16A_rms_psi=math.sqrt(st.mean(x*x for x in g1)) if g1 else None,
                            g5_16A_return_bias_C=g5[0] if g5 else None))
    score.write_csv(args.results/'summary.csv', summary)

    working = {r['sample_id']: r for r in score.read_csv(REFERENCE['working']/'circulation.csv')}
    changes = []
    for f in FILMS:
        groups = defaultdict(lambda: defaultdict(list))
        for r in score.read_csv(args.results/f/'circulation.csv'):
            old = working[r['sample_id']]
            if r['success'] != 'True' or old['success'] != 'True':
                continue
            for field in ('bit_C', 'return_C', 'spp_psi'):
                if r.get(field) not in ('', None) and old.get(field) not in ('', None):
                    groups[r['well'], r['bha']][field].append(float(r[field])-float(old[field]))
        for (w, b), v in sorted(groups.items()):
            changes.append(dict(calculation=f, well=w, bha=b, samples=len(v['bit_C']),
                                bit_change_mean_C=st.mean(v['bit_C']), bit_change_min_C=min(v['bit_C']),
                                bit_change_max_C=max(v['bit_C']), return_change_mean_C=st.mean(v['return_C']),
                                spp_change_mean_psi=st.mean(v['spp_psi']) if v['spp_psi'] else None))
    score.write_csv(args.results/'assembly-changes.csv', changes)

    entry7 = {r['sample_id']: r for r in score.read_csv(REFERENCE['entry7-no-yield']/'circulation.csv')}
    check = []
    for r in score.read_csv(args.results/'film-1.00'/'circulation.csv'):
        old = entry7[r['sample_id']]
        row = dict(sample_id=r['sample_id'], well=r['well'], bha=r['bha'],
                   success=r['success'] == 'True' and old['success'] == 'True')
        for field, tol in TOLERANCE.items():
            a, b = number(r.get(field)), number(old.get(field))
            row[f'{field}_difference'] = None if a is None or b is None else a-b
        row['within_tolerance'] = row['success'] and all(
            row[f'{field}_difference'] is None or abs(row[f'{field}_difference']) <= tol for field, tol in TOLERANCE.items())
        check.append(row)
    score.write_csv(args.results/'entry7-reproduction.csv', check)

    regime = []
    for f in FILMS:
        groups = defaultdict(lambda: defaultdict(list))
        for r in score.read_csv(args.results/f/'regime.csv'):
            if r['success'] == 'True' and r.get('laminar') not in ('', None):
                for field in ('laminar', 'transitional', 'gel_laminar', 'gel_transitional'):
                    groups[r['well'], r['bha']][field].append(float(r[field]))
        for (w, b), v in sorted(groups.items()):
            regime.append(dict(calculation=f, well=w, bha=b, samples=len(v['laminar']),
                               **{f'{k}_mean': st.mean(x) for k, x in v.items()}))
    score.write_csv(args.results/'regime-summary.csv', regime)

    for f in FILMS:
        manifest = score.read_json(args.results/f/'manifest.json')
        manifest.update(declaration_commit='f3c39f8', working_calculation='validation/model-development/entry-5/results',
                        comparison_script_sha256=score.sha(Path(__file__)),
                        scored_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
        score.write_json(args.results/f/'manifest.json', manifest)
    derived = ('comparison.csv', 'summary.csv', 'assembly-changes.csv', 'entry7-reproduction.csv', 'regime-summary.csv')
    score.write_json(args.results/'derived-sha256.json', {p: score.sha(args.results/p) for p in derived})
    print(f'{len(rows)} scoreboard rows, {sum(not r["paired"] for r in rows)} unpaired; {len(changes)} assembly rows')
    worst = {field: max(abs(r[f'{field}_difference']) for r in check if r[f'{field}_difference'] is not None)
             for field in TOLERANCE}
    print(f'entry 7 reproduction: {sum(r["within_tolerance"] for r in check)} of {len(check)} within tolerance; '
          f'largest differences {worst}')
    for s in summary:
        print(s)


if __name__ == '__main__':
    main()
