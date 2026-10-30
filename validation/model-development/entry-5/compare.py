"""Set the entry 5 score beside the legacy baseline and the working calculation.

Reads saved scoreboard outputs only; runs no model. The working calculation
is entry 1 with D5, entry 3 and entry 4. A row is paired only when all three calculations compare
the same number of samples and the same successful samples: the same
sample IDs in the row's well for the circulation gaps, and the same events
for G4.
"""
from collections import defaultdict
import argparse
import importlib.util
from pathlib import Path
import statistics as st
import subprocess

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('frozen_scoreboard', ROOT/'validation/scoreboard/scoreboard.py')
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)
ROOTS = {'legacy': ROOT/'validation/scoreboard/baseline',
         'working': ROOT/'validation/model-development/entry-4/results'}


def number(value):
    return None if value in ('', None) else float(value)


def successes(root):
    """Successful sample IDs by well, and successful run-in events."""
    ids = defaultdict(set)
    for r in score.read_csv(root/'circulation.csv'):
        if r['success'] == 'True':
            ids[r['well']].add(r['sample_id'])
    ids['G4'] = {r['event_id'] for r in score.read_csv(root/'run-in.csv') if r['success'] == 'True'}
    return ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--score', type=Path, default=Path(__file__).with_name('results'))
    args = parser.parse_args()
    roots = {**ROOTS, 'entry5': args.score}
    boards = {k: {(r['gap'], r['well'], r['group']): r for r in score.read_csv(p/'scoreboard.csv')} for k, p in roots.items()}
    succeeded = {k: successes(p) for k, p in roots.items()}
    rows = []
    for key, new in boards['entry5'].items():
        row = dict(gap=key[0], well=key[1], group=key[2], units=new['units'], planned=int(new['planned']))
        counts = {k: boards[k][key]['compared'] for k in boards}
        samples = {k: frozenset(succeeded[k]['G4' if key[0] == 'G4' else key[1]]) for k in boards}
        row['paired'] = len(set(counts.values())) == 1 and len(set(samples.values())) == 1
        for name in boards:
            old = boards[name][key]
            row[f'{name}_compared'] = int(old['compared'])
            row[f'{name}_model_mean'] = number(old['model_mean'])
            row[f'{name}_bias'] = number(old['bias'])
        if row['paired'] and row['entry5_bias'] is not None:
            row['change_from_working'] = row['entry5_bias']-row['working_bias']
        row['measured_mean'] = number(new['measured_mean'])
        rows.append(row)
    score.write_csv(args.score/'comparison.csv', rows)

    cases = {k: {r['sample_id']: r for r in score.read_csv(roots[k]/'circulation.csv')} for k in ('working', 'entry5')}
    groups = defaultdict(lambda: defaultdict(list))
    for sample_id, new in cases['entry5'].items():
        old = cases['working'][sample_id]
        if new['success'] != 'True' or old['success'] != 'True':
            continue
        for field in ('bit_C', 'return_C'):
            groups[new['well'], new['bha']][field].append(float(new[field])-float(old[field]))
    changes = [dict(well=w, bha=b, samples=len(v['bit_C']),
                    bit_change_mean_C=st.mean(v['bit_C']), bit_change_min_C=min(v['bit_C']), bit_change_max_C=max(v['bit_C']),
                    return_change_mean_C=st.mean(v['return_C']))
               for (w, b), v in sorted(groups.items())]
    score.write_csv(args.score/'assembly-changes.csv', changes)

    manifest = score.read_json(args.score/'manifest.json')
    manifest.update(declaration_commit='72b5281',
        working_calculation='validation/model-development/entry-4/results',
        mud_ledger_sha256=score.sha(ROOT/'validation/forge16b/s2/mud-revision-ledger.csv'),
        comparison_script_sha256=score.sha(Path(__file__)),
        scored_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        derived_sha256={p.name: score.sha(args.score/p.name) for p in (Path('comparison.csv'), Path('assembly-changes.csv'))})
    score.write_json(args.score/'manifest.json', manifest)
    print(f'{len(rows)} scoreboard rows, {sum(not r["paired"] for r in rows)} unpaired; {len(changes)} assemblies')


if __name__ == '__main__':
    main()
