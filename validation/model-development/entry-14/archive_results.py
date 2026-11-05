"""Archive compact entry 14 results and hash the external bulk outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXTERNAL = {'entry14/circulation.csv', 'entry14/rotary-heat-applied.csv'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scores', type=Path, required=True)
    parser.add_argument('--declaration', required=True)
    args = parser.parse_args()
    source = args.scores.resolve()
    if source.is_relative_to(ROOT.resolve()):
        parser.error('Complete scores must be outside the repository')
    records = {}
    for path in sorted(source.rglob('*')):
        if path.is_file():
            name = path.relative_to(source).as_posix()
            records[name] = dict(sha256=sha(path), bytes=path.stat().st_size)
            if name not in EXTERNAL:
                target = HERE/'results'/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    command = (f'python validation/model-development/entry-14/score.py --declaration {args.declaration} --output <bulk> --scratch <scratch>; '
               f'python validation/model-development/entry-14/compare.py --declaration {args.declaration} --results <bulk> --reference <entry 13 bulk>/tapered_primary')
    manifest = dict(declaration_commit=args.declaration, method='Compact results retained; the per-sample score tables are external',
                    all_external_files=records, rebuildable_files={n: dict(records[n], rebuild_command=command) for n in sorted(EXTERNAL)})
    (HERE/'bulk-manifest.json').write_bytes((json.dumps(manifest, indent=2)+'\n').encode('utf-8'))
    print('Retained compact results; recorded', len(EXTERNAL), 'external outputs of', len(records))


if __name__ == '__main__':
    main()
