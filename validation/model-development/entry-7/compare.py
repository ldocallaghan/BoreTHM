"""Set the three entry 7 hypotheses beside the legacy baseline and the working
calculation.

Reads saved scoreboard outputs only; runs no model. The working calculation
is entry 5's (entries 1-5 with D5). A row is paired only when all
calculations compare the same number of samples and the same successful
samples: the same sample IDs in the row's well for the circulation gaps, and
the same events for G4. The declared summary measures are the root-mean-
square of the nine 16A assembly bit biases (G3), the 16A standpipe biases
(G1) and the 16A return bias (G5).
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
HYPOTHESES = ('no-yield', 'gel', 'gel-rising')
REFERENCE = {'legacy': ROOT/'validation/scoreboard/baseline',
             'working': ROOT/'validation/model-development/entry-5/results'}


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
    roots = {**REFERENCE, **{h: args.results/h for h in HYPOTHESES}}
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
        for h in HYPOTHESES:
            if row['paired'] and row[f'{h}_bias'] is not None and row['working_bias'] is not None:
                row[f'{h}_change_from_working'] = row[f'{h}_bias']-row['working_bias']
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
    for h in HYPOTHESES:
        groups = defaultdict(lambda: defaultdict(list))
        for r in score.read_csv(args.results/h/'circulation.csv'):
            old = working[r['sample_id']]
            if r['success'] != 'True' or old['success'] != 'True':
                continue
            for field in ('bit_C', 'return_C', 'spp_psi'):
                if r.get(field) not in ('', None) and old.get(field) not in ('', None):
                    groups[r['well'], r['bha']][field].append(float(r[field])-float(old[field]))
        for (w, b), v in sorted(groups.items()):
            changes.append(dict(hypothesis=h, well=w, bha=b, samples=len(v['bit_C']),
                                bit_change_mean_C=st.mean(v['bit_C']), bit_change_min_C=min(v['bit_C']),
                                bit_change_max_C=max(v['bit_C']), return_change_mean_C=st.mean(v['return_C']),
                                spp_change_mean_psi=st.mean(v['spp_psi']) if v['spp_psi'] else None))
    score.write_csv(args.results/'assembly-changes.csv', changes)

    for h in HYPOTHESES:
        manifest = score.read_json(args.results/h/'manifest.json')
        manifest.update(declaration_commit='d3c5419', working_calculation='validation/model-development/entry-5/results',
                        comparison_script_sha256=score.sha(Path(__file__)),
                        scored_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
        score.write_json(args.results/h/'manifest.json', manifest)
    score.write_json(args.results/'derived-sha256.json',
                     {p: score.sha(args.results/p) for p in ('comparison.csv', 'summary.csv', 'assembly-changes.csv')})
    print(f'{len(rows)} scoreboard rows, {sum(not r["paired"] for r in rows)} unpaired; {len(changes)} assembly rows')
    for s in summary:
        print(s)


if __name__ == '__main__':
    main()
