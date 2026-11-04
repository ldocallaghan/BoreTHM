"""Reduce target-free per-window predictions and audit the geometry change."""
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import statistics as st
from predict import diagnosis,geometry,selection,write
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def read(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))


def main():
    p=HERE/'predictions';m=json.loads((p/'manifest.json').read_text(encoding='utf-8'))
    assert m['windows']==22 and not m['targets_compared'] and not m['solver_failures']
    rows=read(p/'model-only.csv');assert len(rows)==132
    grouped=defaultdict(list)
    for r in rows:grouped[r['variant'],r['well']].append(r)
    summary=[]
    fields=('spp_psi_change','model_hydraulic_kW_change','bit_C_change','sensor_bore_C_change','return_C_change')
    for (variant,well),group in sorted(grouped.items()):
        r=dict(variant=variant,well=well,windows=len(group))
        for name in fields:
            values=[float(x[name]) for x in group]
            r.update({name+'_min':min(values),name+'_max':max(values),name+'_mean':st.mean(values)})
        summary.append(r)
    write(p/'rough-effects.csv',summary)
    old={r['sample_id']:r for r in read(HERE.parent/'entry-10/predictions/model-only.csv') if r['variant']=='smooth'}
    checks=[]
    for r in rows:
        if r['variant']!='working':continue
        for name in ('spp_psi','model_hydraulic_kW','bit_C','return_C'):
            a,b=float(old[r['sample_id']][name]),float(r[name])
            tolerance=1. if name=='spp_psi' else .001*max(abs(a),1) if name=='model_hydraulic_kW' else .1
            checks.append(dict(sample_id=r['sample_id'],field=name,entry10_working=a,replayed_working=b,
                               difference=b-a,tolerance=tolerance,passed=abs(b-a)<=tolerance))
    assert all(r['passed'] for r in checks)
    write(p/'working-replay-check.csv',checks)
    calc=diagnosis.Calculation();samples=[s for s in calc.plan['samples'] if not(s['well']=='16A' and s.get('source')!='Sanvean on-bottom')]
    audit=[]
    for s in selection.select(samples):
        for variant in ('working','installed_primary','installed_premium','installed_no_local'):
            g=geometry(calc,s,variant)
            for n,segment in enumerate(g.string):
                joint=segment.pipe.hydraulic_joint
                if joint is None:continue
                audit.append(dict(sample_id=s['id'],well=s['well'],assembly=s['run'],variant=variant,segment=n,
                    name=segment.pipe.name,length_ft=segment.length/.3048,body_OD_in=2*segment.pipe.r_out/.0254,
                    body_ID_in=2*segment.pipe.r_bore/.0254,joint_OD_in=joint.outer_diameter/.0254,
                    joint_ID_in=joint.bore_diameter/.0254,restriction_in=joint.restriction_length/.0254,
                    spacing_ft=joint.spacing/.3048,transition=joint.transition,source=joint.source))
    write(p/'geometry-audit.csv',audit)
    m['source_sha256_summaries']={Path(__file__).relative_to(ROOT).as_posix():hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    m['derived_sha256']={name:hashlib.sha256((p/name).read_bytes()).hexdigest() for name in ('rough-effects.csv','working-replay-check.csv','geometry-audit.csv')}
    (p/'manifest.json').write_bytes((json.dumps(m,indent=2)+'\n').encode('utf-8'))
    print('22 working windows replayed; 132 declared prediction rows and geometry audit complete.')


if __name__=='__main__':main()
