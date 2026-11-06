"""Write predictions/assembly-tools-audit.csv from the printed assembly records.

Each 16B entry below is transcribed from the end-of-well report (EOWR, GDR 1516,
SHA256 b35f25ed...f5d) and the daily reports. Each 16A row comes from the audited
component table of entry 9, which gives the report member, page and hash. The
declared column is read from the original predictions/assembly-tools.csv.
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
CLASSES = ('mwd_pulser', 'rotary_steerable', 'mud_motor', 'filter_sub', 'float_sub')
FORMS = {'mud_motor': ('motor', 'mud motor'), 'filter_sub': ('filter sub',), 'float_sub': ('float sub',)}
EOWR = 'EOWR'
HANGOFF = {'3': ('Hangoff sub, 9.500 in; the word pulser is not printed; MWD batteries named in the operations plan', 'EOWR p38, row 6; p185; DailyReport15 p1'),
           '4': ('Hangoff sub; the word pulser is not printed; MWD named at pick-up', 'EOWR p185; DailyReport16 p1')}
SHEETS = {
    '3': dict(sheet='p38, p185', motor='9.15 mud motor, row 2'),
    '4': dict(sheet='p185', motor='Mud motor'),
    '11': dict(sheet='p71, p187', motor='7.15 mud motor, row 9', filter='6 3/4 filter sub, row 10', halo='HALO RSS w/HFTO, row 2', pulser='Pulser 128-481'),
    '12': dict(sheet='p75, p187', none='NO MOTOR ASSIST', filter='6 3/4 filter sub, row 9', float='6 3/4 float sub, row 8', halo='HALO RSS w/HFTO, row 2', pulser='Pulser 128-474'),
    '13': dict(sheet='p80, p188', none='NO MOTOR ASSIST', filter='6 3/4 filter sub, row 8', float='6 3/4 float sub, row 7', halo='HALO RSS w/HFTO, row 2', pulser='Pulser 128-474'),
    '14': dict(sheet='p85, p188', none='NO MOTOR ASSIST', filter='6 3/4 filter sub', float='6 3/4 float sub', halo='HALO RSS w/HFTO', pulser='Pulser 213-006', scored=False),
    '15': dict(sheet='p93, p188', none='NO MOTOR ASSIST', filter='6 3/4 filter sub', float='6 3/4 float sub', halo='HALO RSS w/HFTO', pulser='Pulser 122-1243F'),
    '16': dict(sheet='p97, p188', none='NO MOTOR ASSIST', filter='6 3/4 filter sub', float='6 3/4 float sub', halo='HALO RSS w/HFTO', pulser='Pulser 213-004F'),
    '17': dict(sheet='p102, p189', motor='7.15 mud motor, row 2', filter='6 3/4 filter sub, row 10', pulser='6 3/4 pulser sub, row 6'),
    '18': dict(sheet='p111, p189', motor='7.15 mud motor, row 2', filter='6 3/4 filter sub, row 10', float='6 3/4 float sub, row 11', pulser='6 3/4 pulser sub, row 6'),
    '19': dict(sheet='p115, p189', motor='7.15 mud motor, row 2', filter='6 3/4 filter sub, row 10', float='6 3/4 float sub, row 11', pulser='6 3/4 pulser sub, row 6'),
    '20': dict(sheet='p129, p189', motor='7.15 mud motor, row 2', filter='6 3/4 filter sub, row 10', float='6 3/4 float sub, row 11', pulser='6 3/4 pulser sub, row 6'),
    '27': dict(sheet='p191', motor='Mud motor', filter='Filter sub', float='Float sub', pulser='Pulser sub'),
    '38': dict(sheet='p160, p194', motor='7.15 mud motor, row 2', filter='6 3/4 filter sub, row 11', float='6 3/4 float sub, row 12', pulser='6 3/4 pulser sub, row 6'),
}
ORDER_16A = ('18', '23', '30', '34', '35r1', '35r2', '38', '39', '42')


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def rows_16b(declared):
    rows = []
    for assembly, sheet in SHEETS.items():
        source = f'{EOWR} {sheet["sheet"]}'
        for tool in CLASSES:
            if tool == 'mwd_pulser':
                printed, where = HANGOFF.get(assembly, (sheet.get('pulser', ''), source))
            elif tool == 'rotary_steerable':
                printed, where = sheet.get('halo', ''), source
            elif tool == 'mud_motor':
                printed, where = sheet.get('motor', ''), source
            else:
                printed, where = sheet.get(tool.split('_')[0], ''), source
            rows.append(row('16B', assembly, tool, printed, where, declared, sheet.get('none') if tool == 'mud_motor' and not printed else None, sheet.get('scored', True)))
    return rows


def rows_16a(declared):
    inventory = [r for r in read(HERE.parent/'entry-9/tool-source-inventory.csv') if r['well'] == '16A']
    rows = []
    for assembly in ORDER_16A:
        items = [r for r in inventory if r['assembly'] == assembly]
        source = items[0]['source'].split('; SHA256')[0].replace('16A(78)-32_Daily_Reports/drilling/', '')
        for tool in CLASSES:
            if tool == 'mwd_pulser':
                found = [r['component'] for r in items if ('with MWD' in r['component'] or 'w/ MWD' in r['component'] or r['component'].startswith('MWD Tool')) and 'UBHO' not in r['component'] and 'PUK' not in r['component']]
            elif tool == 'rotary_steerable':
                found = []
            else:
                found = [r['component'] for r in items if any(r['component'].lower().startswith(f) or f+'-' in r['component'].lower() or f+' ' in r['component'].lower() for f in FORMS[tool])]
            rows.append(row('16A', assembly, tool, '; '.join(found), source, declared, None, True))
    return rows


def row(well, assembly, tool, printed, source, declared, negative, scored):
    present = bool(printed)
    was = (well, assembly, tool) in declared
    if not scored:
        difference = 'not scored'
    elif present == was:
        difference = 'none'
    elif tool == 'mwd_pulser':
        difference = 'pulser added: sheet prints it; figure 187.7 psi at 600 US gal/min'
    else:
        difference = 'added to the record: default zero, no change in any result'
    return dict(well=well, assembly=assembly, tool_class=tool, printed=printed or (negative or 'not printed'), present=present, source=source, in_declared_assignment=was, difference=difference)


def main():
    declared = {(r['well'], r['assembly'], r['tool_class']) for r in read(HERE/'predictions/assembly-tools.csv')}
    rows = rows_16a(declared)+rows_16b(declared)
    with (HERE/'predictions/assembly-tools-audit.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    for r in rows:
        if r['difference'] != 'none':
            print(r['well'], r['assembly'], r['tool_class'], '|', r['printed'], '|', r['difference'])
    print(len(rows), 'rows')


if __name__ == '__main__':
    main()
