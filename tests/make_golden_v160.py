"""Regenerate the current-mode five-site table.

Run from the repository root:

    python tests/make_golden_v160.py [--sites soultz ...] [--rock logarithmic]

Each built-in site is evaluated in the default mode (circulation 'v1.3.4'
with the v1.6.0 calculation) and recorded in the same rows as the v1.3.4
release table, so the two can be compared row by row. The table is written
to tests/golden/v160_site_table.json. With --rock logarithmic the rows use
the original logarithmic rock term and are written to a separate file named
with --output, for diagnosis only.
"""
import argparse
import json
from pathlib import Path
import time
from unittest.mock import patch

from borethm import model1_coupled as m1
from borethm import site_evaluation as se
from borethm.studies import release_v134 as release

OUT = Path(__file__).resolve().parent / 'golden' / 'v160_site_table.json'


def evaluate(key, rock=None):
    site = se.find_site(key)
    if rock is None:
        return se.evaluate(site, circulation='v1.3.4')
    solve = m1.solve

    def with_rock(*args, **kwargs):
        kwargs.setdefault('rock_response', rock)
        return solve(*args, **kwargs)
    with patch.object(m1, 'solve', with_rock):
        return se.evaluate(site, circulation='v1.3.4')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sites', nargs='+', choices=release.SITES, default=list(release.SITES))
    parser.add_argument('--rock', choices=('logarithmic',))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    output = args.output or (OUT if args.rock is None else None)
    if output is None:
        parser.error('a diagnostic run needs --output')
    table = json.loads(output.read_text()) if output.exists() else dict(schema_version=1, sites={})
    for key in args.sites:
        print('Current mode:', key, flush=True)
        started = time.perf_counter()
        data = se.result_dict(evaluate(key, args.rock))
        table['sites'][key] = release.reference_row(data)
        table['versions'] = se.versions()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(se._jsonable(table), indent=2) + '\n', encoding='utf-8', newline='\n')
        row = table['sites'][key]
        print(key, row['status'], row['flow'], row['flow_unit'], round(row['bit_C'], 2),
              'seconds', round(time.perf_counter() - started), flush=True)


if __name__ == '__main__':
    main()
