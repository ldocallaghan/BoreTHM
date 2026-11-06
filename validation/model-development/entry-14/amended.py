"""Run the entry 14 scripts with the corrected tool assignment of the amendment.

The scripts and the original archive stay as they were. This file replaces the
options that forge_tools reads with amended/options.json, directs the outputs
to amended/predictions and results/entry14-amended, and adds the comparison
with the original entry 14 score. Bulk score output stays outside the repository.

    python amended.py predict
    python amended.py route
    python amended.py summarise --reference <entry 13 bulk>/tapered_primary
    python amended.py score --declaration <commit> --output <bulk> --scratch <scratch>
    python amended.py compare --declaration <commit> --results <bulk> --reference <entry 13 bulk>/tapered_primary
    python amended.py archive --declaration <commit> --scores <bulk>
"""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys

import forge_tools

HERE = forge_tools.HERE
AMENDED = HERE/'amended'
PREDICTIONS = AMENDED/'predictions'
RESULTS = HERE/'results'/'entry14-amended'
EXTERNAL = {'entry14/circulation.csv', 'entry14/rotary-heat-applied.csv'}
forge_tools.OPTIONS = json.loads((AMENDED/'options.json').read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def write(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def run(name, arguments):
    sys.argv = [name+'.py', *arguments]
    forge_tools.load('entry14_'+name, HERE/(name+'.py')).main()


def against_original(path):
    """The declared bias of each frozen gap group beside the original entry 14 score."""
    original = {(r['gap'], r['well'], r['group']): r for r in read(HERE/'results/comparison.csv')}
    rows = []
    for row in read(path):
        before = original[row['gap'], row['well'], row['group']]['entry14_bias']
        predicted = row['predicted_bias']
        rows.append(dict(gap=row['gap'], well=row['well'], group=row['group'], units=row['units'], samples=row['samples'], tapered_primary_bias=row['tapered_primary_bias'],
                         original_entry14_bias=before, predicted_bias=predicted,
                         predicted_change_from_original='' if '' in (before, predicted) else float(predicted)-float(before)))
    write(PREDICTIONS/'expected-against-original.csv', rows)


def archive(arguments):
    declaration = arguments[arguments.index('--declaration')+1]
    source = Path(arguments[arguments.index('--scores')+1]).resolve()
    records = {}
    for path in sorted(source.rglob('*')):
        if path.is_file():
            name = path.relative_to(source).as_posix()
            records[name] = dict(sha256=sha(path), bytes=path.stat().st_size)
            if name not in EXTERNAL:
                target = RESULTS/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    manifest = dict(declaration_commit=declaration, options_sha256=sha(AMENDED/'options.json'), script_sha256=sha(Path(__file__)),
                    method='Compact results retained; the per-sample score tables are external', all_external_files=records)
    (AMENDED/'bulk-manifest.json').write_bytes((json.dumps(manifest, indent=2)+'\n').encode('utf-8'))


def main():
    command, arguments = sys.argv[1], sys.argv[2:]
    if command == 'predict':
        PREDICTIONS.mkdir(parents=True, exist_ok=True)
        run('predict', ['--output', str(PREDICTIONS), *arguments])
    elif command == 'route':
        sys.argv = ['route_check.py', *arguments]
        checking = forge_tools.load('entry14_route_check', HERE/'route_check.py')
        checking.HERE = AMENDED
        checking.main()
    elif command == 'summarise':
        run('summarise_predictions', ['--output', str(PREDICTIONS), *arguments])
        against_original(PREDICTIONS/'expected-gaps.csv')
    elif command == 'score':
        run('score', arguments)
    elif command == 'compare':
        sys.argv = ['compare.py', *arguments]
        comparing = forge_tools.load('entry14_compare', HERE/'compare.py')
        comparing.HERE = AMENDED
        comparing.main()
    elif command == 'archive':
        archive(arguments)
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
