"""Build equipment-source and scale tables without running a well model."""
import csv
from datetime import datetime, timedelta
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (HERE/name).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def friction(reynolds, roughness, diameter):
    f = .02
    for _ in range(100):
        f = (-2*math.log10(roughness/diameter/3.7+2.51/(reynolds*math.sqrt(f))))**-2
    return f


def main():
    audit = read(ROOT/'validation/model-development/d5/components.csv')
    inventory = []
    represented = set()
    for row in audit:
        represented.add((row['well'], row['bha']))
        component = row['component'].lower()
        tool = any(word in component for word in ['motor', 'mwd', 'rss', 'halo', 'filter', 'float', 'sensor', 'puk'])
        inventory.append(dict(well=row['well'], assembly=row['bha'], item=row['item'],
            component=row['component'], source=row['source'],
            recorded_id_in=row['reported_id_in'],
            source_status='audited component record',
            tool_loss_status='operating loss curve not identified for installed equipment' if tool
            else 'no separate proprietary tool curve requested for this component',
            candidate_reference='halo' if 'halo' in component else (
                'geoguidance; transferred configuration requires a declaration' if 'motor' in component and row['well']=='16A' else '')))
    runs = read(ROOT/'validation/forge16a/run_inputs.csv')
    components = read(ROOT/'validation/forge16a/bha_components.csv')
    for run in runs:
        if ('16A',run['run']) in represented:
            continue
        start = datetime.fromisoformat(run['start']).date()
        end = datetime.fromisoformat(run['end']).date()+timedelta(days=1)
        chosen = [row for row in components if row['BHA'] == run['run']
                  and start <= datetime.strptime(row['report_date'],'%m/%d/%Y').date() <= end]
        for row in chosen:
            inventory.append(dict(well='16A', assembly=run['run'], item=row['item'],
                component=row['component'], source=f"GDR 1283; {row['archive']}; {row['member']}; page {row['page']}; SHA256 {row['sha256']}",
                recorded_id_in=row['ID_in'], source_status='report transcription; dimensions not added to frozen model',
                tool_loss_status='no installed operating loss curve identified', candidate_reference=''))
        if not chosen:
            inventory.append(dict(well='16A',assembly=run['run'],item='',component='assembly record unavailable',
                source='validation/forge16a/run_inputs.csv',recorded_id_in='',source_status='missing',
                tool_loss_status='unknown',candidate_reference=''))
    for run in read(ROOT/'validation/forge16b/run_definitions.csv'):
        if ('16B',run['eow_bha']) not in represented:
            inventory.append(dict(well='16B',assembly=run['eow_bha'],item='',component='additional assembly not in frozen component audit',
                source='GDR 1516 End of Well Report, page '+run['eow_page'],recorded_id_in='',
                source_status='drawing identified; full passage and tool mapping unresolved',
                tool_loss_status='unknown',candidate_reference=''))
    write('tool-source-inventory.csv',inventory)
    scales = []
    for label,reynolds,diameter in [('mud-reference',40000,4.276*.0254),('water-reference',500000,4.670*.0254)]:
        blasius=.3164/reynolds**.25
        for roughness in [0.,45.72e-6]:
            colebrook=friction(reynolds,roughness,diameter)
            scales.append(dict(case=label,Re=reynolds,diameter_m=diameter,roughness_m=roughness,
                darcy_blasius=blasius,darcy_colebrook=colebrook,
                friction_change_percent=100*(colebrook/blasius-1),
                basis='illustrative circular pipe; no well pressure or temperature target used'))
    write('candidate-scales.csv',scales)
    references=json.loads((HERE/'references.json').read_text(encoding='utf-8'))
    known={r['id'] for r in references}
    if not {'halo','epa-roughness','colebrook','nc50-supplier','nov-connections'} <= known:
        raise ValueError('Missing source reference')
    print('Equipment rows:',len(inventory),'reference scale cases:',len(scales))


if __name__ == '__main__':
    main()
