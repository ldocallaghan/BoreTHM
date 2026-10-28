"""Set the entry 4 score beside the legacy baseline and the working calculation.

Reads saved scoreboard outputs only; runs no model. The working calculation
is entry 1 with D5 and entry 3. A row is paired only when all three calculations compare
the same number of samples.
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
         'working': ROOT/'validation/model-development/entry-3/results'}


def number(value):
    return None if value in ('', None) else float(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--score', type=Path, default=Path(__file__).with_name('results'))
    args = parser.parse_args()
    roots = {**ROOTS, 'entry4': args.score}
    boards = {k: {(r['gap'], r['well'], r['group']): r for r in score.read_csv(p/'scoreboard.csv')} for k, p in roots.items()}
    rows = []
    for key, new in boards['entry4'].items():
        row = dict(gap=key[0], well=key[1], group=key[2], units=new['units'], planned=int(new['planned']))
        counts = {k: boards[k][key]['compared'] for k in boards}
        row['paired'] = len(set(counts.values())) == 1
        for name in boards:
            old = boards[name][key]
            row[f'{name}_compared'] = int(old['compared'])
            row[f'{name}_model_mean'] = number(old['model_mean'])
            row[f'{name}_bias'] = number(old['bias'])
        if row['paired'] and row['entry4_bias'] is not None:
            row['change_from_working'] = row['entry4_bias']-row['working_bias']
        row['measured_mean'] = number(new['measured_mean'])
        rows.append(row)
    score.write_csv(args.score/'comparison.csv', rows)

    cases = {k: {r['sample_id']: r for r in score.read_csv(roots[k]/'circulation.csv')} for k in ('working', 'entry4')}
    groups = defaultdict(lambda: defaultdict(list))
    for sample_id, new in cases['entry4'].items():
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
    manifest.update(declaration_commit='e157fdf', implementation_commit='a25a9d5', inputs_commit='b4b8b36',
        working_calculation='validation/model-development/entry-3/results',
        rotary_heat_sha256=score.sha(ROOT/'src/borethm/rotary_heat.py'),
        comparison_script_sha256=score.sha(Path(__file__)),
        scored_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        derived_sha256={p.name: score.sha(args.score/p.name) for p in (Path('comparison.csv'), Path('assembly-changes.csv'))})
    score.write_json(args.score/'manifest.json', manifest)
    print(f'{len(rows)} scoreboard rows, {sum(not r["paired"] for r in rows)} unpaired; {len(changes)} assemblies')


if __name__ == '__main__':
    main()
