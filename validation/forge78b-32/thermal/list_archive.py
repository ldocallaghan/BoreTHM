"""List the members of the 78B-32 archive (GDR 1330) with their column names.

No data row is printed. For each member the script prints its name and size.
Nested zip archives are listed member by member. Column names come from:

- delimited text: the first line, unless one of its cells is a number, and
  any further leading lines that contain no digit (a split heading or a units
  row); reading stops at the first line with a digit, which is never printed,
  and every printed line has its digits masked;
- LAS files: the curve mnemonics and units from the ~Curve section only; the
  ~Well, ~Parameter and ~Other sections are skipped unread;
- spreadsheets: the sheet names and the first row of each sheet, with every
  digit masked;
- every other file: name and size only.

Usage: python list_archive.py ARCHIVE [--json OUT]
"""
import argparse
import io
import json
import re
import sys
import zipfile

TEXT = ('.csv', '.txt', '.tsv', '.dat', '.asc')
LAS = ('.las',)
SHEET = ('.xlsx', '.xlsm')
MAX_HEADING_LINES = 4
NUMBER = re.compile(r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$')


def mask(text):
    return re.sub(r'\d+', '#', text)


def split_cells(line):
    for sep in (',', '\t', ';'):
        if sep in line:
            return [c.strip().strip('"') for c in line.split(sep)]
    return [c for c in line.split() if c]


def has_number(cells):
    return any(NUMBER.match(c) for c in cells)


def text_heading(fh):
    """Return the leading heading lines of a delimited text stream.

    The first line is kept unless one of its cells is a number. A later line
    is kept only if it holds no digit at all. Every kept line is masked, each
    run of digits becoming a single '#'.
    """
    lines = []
    for raw in fh:
        line = raw.decode('utf-8', 'replace').rstrip('\r\n')
        if not line.strip():
            if lines:
                break
            continue
        cells = split_cells(line)
        if not lines and has_number(cells):
            return {'heading': None, 'note': 'first line has a numeric cell; not printed'}
        if lines and re.search(r'\d', line):
            break
        lines.append([mask(c) for c in cells])
        if len(lines) >= MAX_HEADING_LINES:
            break
    return {'heading': lines}


def las_curves(fh):
    """Return (mnemonic, unit) pairs from the ~Curve section only."""
    curves, section = [], None
    for raw in fh:
        line = raw.decode('latin-1').strip()
        if line.startswith('~'):
            section = line[1:2].upper()
            if section == 'A':
                break
            continue
        if section != 'C' or not line or line.startswith('#'):
            continue
        left = line.split(':', 1)[0]
        mnemonic, _, rest = left.partition('.')
        unit = rest.split(' ', 1)[0] if rest and not rest.startswith(' ') else ''
        curves.append((mnemonic.strip(), unit.strip()))
    return {'curves': curves}


def sheet_heading(data):
    try:
        import openpyxl
    except ImportError:
        return {'note': 'openpyxl not installed'}
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    out = {}
    for ws in wb.worksheets:
        first = next(ws.iter_rows(max_row=1, values_only=True), ())
        out[ws.title] = [mask(str(v)) for v in first if v is not None]
    return {'sheets': out}


def describe(name, opener, size):
    low = name.lower()
    entry = {'name': name, 'size': size}
    try:
        if low.endswith(TEXT):
            with opener() as fh:
                entry.update(text_heading(fh))
        elif low.endswith(LAS):
            with opener() as fh:
                entry.update(las_curves(fh))
        elif low.endswith(SHEET):
            with opener() as fh:
                entry.update(sheet_heading(fh.read()))
    except Exception as exc:  # report and continue
        entry['note'] = f'not read: {type(exc).__name__}'
    return entry


def walk(zf, prefix=''):
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = prefix + info.filename
        if info.filename.lower().endswith('.zip'):
            yield {'name': name, 'size': info.file_size, 'kind': 'zip'}
            with zf.open(info) as inner_fh:
                inner = zipfile.ZipFile(inner_fh)
                yield from walk(inner, name + '!')
        else:
            yield describe(name, lambda i=info: zf.open(i), info.file_size)


def render(entry):
    depth = entry['name'].count('!')
    pad = '  ' * depth
    print(f"{pad}{entry['size']:>15,}  {entry['name'].rsplit('!', 1)[-1]}")
    pad += '    '
    for row in entry.get('heading') or []:
        print(f'{pad}| ' + ' | '.join(row))
    if entry.get('curves'):
        print(pad + 'curves: ' + ', '.join(f'{m} [{u}]' if u else m for m, u in entry['curves']))
    for title, row in (entry.get('sheets') or {}).items():
        print(f'{pad}sheet {mask(title)}: ' + ' | '.join(row))
    if entry.get('note'):
        print(f"{pad}({entry['note']})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('archive')
    ap.add_argument('--json')
    args = ap.parse_args()
    entries = []
    with zipfile.ZipFile(args.archive) as zf:
        for entry in walk(zf):
            render(entry)
            sys.stdout.flush()
            entries.append(entry)
    if args.json:
        with open(args.json, 'w') as fh:
            json.dump(entries, fh, indent=1)


if __name__ == '__main__':
    main()
