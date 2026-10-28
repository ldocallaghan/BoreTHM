"""Audit development-well assembly inputs without consulting observations.

Original blanks are recovered from the report-cell extract. Adopted dimensions
from earlier studies are retained separately, including explicit transfers.
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent


def read(path):
    with path.open(newline='',encoding='utf-8-sig') as stream:return list(csv.DictReader(stream))


def build():
    plan=json.loads((ROOT/'validation/forge16b/s2/plan.json').read_text())
    raw=read(ROOT/'validation/forge16a/bha_components.csv')
    rows=[]
    for well,key in (('16A','components_a'),('16B','components_b')):
        for bha,components in plan[key].items():
            for c in components:
                label=c['component'];item=int(c['item'])
                motor='motor' in label.lower();bit='bit' in label.lower()
                if well=='16A':
                    source=next(r for r in raw if r['member']==c['member'] and int(r['item'])==item)
                    original_id=float(source['ID_in']) if source['ID_in'] else None
                    original_od=float(source['OD_in']) if source['OD_in'] else None
                    loc=f"GDR 1283; {c['member']}; page 1; SHA256 {c['sha256']}"
                    old_id=c['primary_id_in']
                else:
                    transferred='borrowed' in c['dimension_source']
                    original_id=None if transferred else c['id_in']
                    original_od=None if transferred else c['od_in']
                    loc=f"GDR 1516; End of Well Report (May 2024); length: {c['length_source']}; dimensions: {c['dimension_source']}"
                    old_id=c['id_in']
                adopted_id=old_id;hydraulic_id=old_id;thermal_id=old_id
                treatment='recorded passage';flags=[]
                if original_id is None:flags.append('earlier filled or transferred ID')
                if original_od is None:flags.append('earlier filled or transferred OD')
                if motor:
                    collar=next(x for x in components[item:] if any(word in x['component'].lower() for word in ('collar','nmdc','pony')))
                    thermal_id=collar.get('primary_id_in',collar.get('id_in'))
                    hydraulic_id=None;adopted_id=None
                    treatment='motor: total internal tool loss; thermal-only adjacent collar bore assumption'
                    flags.append('motor loss unknown')
                elif bit:
                    adopted_id=hydraulic_id=thermal_id=None
                    treatment='nozzle boundary; no bit-body passage or finite thermal segment'
                elif well=='16A' and original_id is None:
                    adopted_id=hydraulic_id=thermal_id=None
                    treatment='unresolved bore; assembly calculation unavailable'
                    if (bha,item) in (('23',6),('38',3),('39',3)):
                        thermal_id=3.25
                        treatment='instrument: thermal-only 3.25 in assumption; internal hydraulic loss unknown'
                        flags.append('internal instrument loss unknown')
                        loc+='; thermal-only bore: declared engineering assumption, 28 October 2026'
                tool=motor or any(x in label.lower() for x in ('sensor','mwd','puk','pulser','float','filter','black box','jar'))
                rows.append(dict(well=well,bha=bha,item=item,component=label,kind=c['kind'],
                    length_ft=c['length_ft'],reported_od_in=original_od,reported_id_in=original_id,
                    earlier_od_in=c['od_in'],earlier_id_in=old_id,adopted_od_in=c['od_in'],
                    adopted_id_in=adopted_id,hydraulic_id_in=hydraulic_id,thermal_id_in=thermal_id,
                    reported_bore_below_2in=original_id is not None and original_id<2,
                    earlier_bore_below_2in=old_id<2,tool=tool,motor=motor,bit=bit,
                    treatment=treatment,flags='; '.join(flags),source=loc,
                    earlier_note=c.get('input_note','')))
    trial=read(ROOT/'src/borethm/data/forge16b/string_components.csv')
    for bha in ('17','18','19','20'):
        for c in (r for r in trial if r['bha']=='17'):
            motor=c['item']=='2';bit=c['item']=='1'
            # The original trial model transferred Figure 90 to all four runs.
            rows.append(dict(well='16B',bha=bha,item=int(c['item']),component=c['description'],kind='trial aggregate input',
                length_ft=float(c['length_ft']),reported_od_in=float(c['od_in']) if bha=='17' else None,
                reported_id_in=float(c['id_in']) if bha=='17' else None,earlier_od_in=float(c['od_in']),
                earlier_id_in=float(c['id_in']),adopted_od_in=float(c['od_in']),
                adopted_id_in=None if bit or motor else float(c['id_in']),
                hydraulic_id_in=None if bit or motor else float(c['id_in']),
                thermal_id_in=None if bit else 3.25 if motor else float(c['id_in']),
                reported_bore_below_2in=False,earlier_bore_below_2in=False,
                tool=motor or any(x in c['description'] for x in ('pulser','filter','black box')),
                motor=motor,bit=bit,
                treatment='motor: total internal tool loss; thermal-only adjacent collar bore assumption' if motor else
                    'nozzle boundary; no bit-body passage' if bit else 'remaining trial aggregate; earlier transfer retained',
                flags=('motor loss unknown; ' if motor else '')+('earlier inter-assembly transfer' if bha!='17' else ''),
                source='GDR 1516; End of Well Report, page 102, Figure 90; original trial aggregate input',
                earlier_note='Motor length 35 ft in Figure 90; 41.87 ft in Appendix B page 189. Existing 35-ft trial convention retained.' if motor else ''))
    return rows


def main():
    rows=build()
    (HERE/'components.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    with (HERE/'components.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,rows[0].keys(),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    sources=('validation/forge16b/s2/plan.json','validation/forge16a/bha_components.csv',
             'src/borethm/data/forge16b/string_components.csv')
    manifest=dict(components=len(rows),assemblies=len({(r['well'],r['bha']) for r in rows}),
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in sources})
    (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
