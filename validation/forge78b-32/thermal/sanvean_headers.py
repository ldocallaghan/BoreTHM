"""Column names and row counts of the readable Sanvean output files.

Only the three `- output data.csv` files are read; the raw sensor archives
inside the Sanvean zip are password protected. Each file opens with a block
of lines that start with '#'. The script counts those lines and prints the
last two with every run of digits masked. It prints the first line after
the block as the column heading unless one of its cells is a number, and
any following lines that contain no digit (units). Every later line is
counted and never printed.

Usage: python sanvean_headers.py ARCHIVE [--json OUT]
"""
import argparse
import io
import json
import re
import zipfile

SANVEAN = "Forge 78 B-32 WOO - 1 Sensor Data RM.zip"
NUMBER = re.compile(r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$')


def mask(text):
    return re.sub(r'\d+', '#', text)


def cells(line):
    sep = ',' if ',' in line else '\t' if '\t' in line else None
    parts = line.split(sep) if sep else line.split()
    return [p.strip().strip('"') for p in parts]


def describe(fh):
    preamble, heading, units, rows = [], None, [], 0
    state = 'preamble'
    for raw in fh:
        line = raw.decode('utf-8', 'replace').rstrip('\r\n')
        if state == 'preamble':
            if line.startswith('#') or not line.strip():
                preamble.append(line)
                continue
            state = 'heading'
        if state == 'heading':
            c = cells(line)
            if any(NUMBER.match(x) for x in c):
                heading = None
                state, rows = 'data', 1
            else:
                heading = [mask(x) for x in c]
                state = 'units'
            continue
        if state == 'units':
            if not re.search(r'\d', line) and line.strip():
                units.append([mask(x) for x in cells(line)])
                continue
            state = 'data'
        if line.strip():
            rows += 1
    tail = [mask(p) for p in preamble if p.strip()][-2:]
    return dict(preamble_lines=len(preamble), preamble_tail=tail,
                heading=heading, units=units, data_rows=rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('archive')
    ap.add_argument('--json')
    args = ap.parse_args()
    out = {}
    with zipfile.ZipFile(args.archive) as outer, zipfile.ZipFile(outer.open(SANVEAN)) as z:
        for info in z.infolist():
            if info.filename.endswith('output data.csv'):
                with z.open(info) as fh:
                    out[info.filename] = describe(fh)
    for name, d in out.items():
        print('==', name)
        print('   preamble lines:', d['preamble_lines'], '| data rows:', d['data_rows'])
        for p in d['preamble_tail']:
            print('   preamble tail |', p[:200])
        if d['heading'] is None:
            print('   heading: first line after the preamble has a numeric cell; not printed')
        else:
            print('   heading |', ' | '.join(d['heading']))
        for u in d['units']:
            print('   units   |', ' | '.join(u))
    if args.json:
        with open(args.json, 'w') as fh:
            json.dump(out, fh, indent=1)


if __name__ == '__main__':
    main()
