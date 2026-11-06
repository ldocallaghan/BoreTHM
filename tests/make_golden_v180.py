"""Regenerate the five-site table at the v1.8.0 default physics.

Run from the repository root:

    python tests/make_golden_v180.py [--sites soultz ...] [--exports DIRECTORY]

Each built-in site is evaluated with the package defaults and recorded in the
same rows as the v1.6.0 table, so the two can be compared row by row. The table
is written to tests/golden/v180_site_table.json. With --exports each full JSON
export is also written to the named directory.
"""
import argparse
import json
from pathlib import Path
import time

from borethm import site_evaluation as se
from borethm.studies import release_v134 as release

OUT = Path(__file__).resolve().parent / 'golden' / 'v180_site_table.json'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sites', nargs='+', choices=release.SITES, default=list(release.SITES))
    parser.add_argument('--exports', type=Path)
    args = parser.parse_args(argv)
    table = json.loads(OUT.read_text()) if OUT.exists() else dict(schema_version=1, sites={})
    for key in args.sites:
        started = time.perf_counter()
        data = se.result_dict(se.evaluate(se.find_site(key), circulation='v1.3.4'))
        table['sites'][key] = release.reference_row(data)
        table['versions'] = se.versions()
        OUT.write_text(json.dumps(se._jsonable(table), indent=2) + '\n', encoding='utf-8', newline='\n')
        if args.exports:
            args.exports.mkdir(parents=True, exist_ok=True)
            (args.exports / f'{key}.json').write_text(json.dumps(se._jsonable(data), indent=2) + '\n', encoding='utf-8', newline='\n')
        row = table['sites'][key]
        print(key, row['status'], row['flow'], row['flow_unit'], round(row['bit_C'], 2),
              'seconds', round(time.perf_counter() - started), flush=True)


if __name__ == '__main__':
    main()
