"""Tapered-joint effect on the ten pre-existing primary shallow windows.

The selection is entry 9's frozen near-surface table, role=primary. Its
recorded mass and mean inlet/return temperature are unchanged. The prediction
is geometry identity because the partial strings contain no ordinary pipe. A
difference is reported explicitly. No circulation solve or fit is involved.
"""
import argparse
import hashlib
from pathlib import Path
from types import SimpleNamespace
from predict import diagnosis,geometry
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CHECKED=('installed_primary','tapered_primary','tapered_long','tapered_steep','tapered_pin_length')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True);calc=diagnosis.Calculation()
    source=HERE.parent/'entry-9/results/near-surface.csv'
    chosen=[r for r in diagnosis.read(source) if r['well']=='16B' and r['role']=='primary']
    assert len(chosen)==10
    samples={s['id']:s for s in calc.plan['samples']};rows=[]
    for r in chosen:
        sample=samples[r['input_sample_id']]
        base=calc.geometry(sample,float(r['bit_depth_ft']),float(r['hole_depth_ft']))
        context=SimpleNamespace(plan=calc.plan,whole=calc.whole,score=SimpleNamespace(wg=calc.score.wg,geometry=lambda *args:base))
        mass=float(r['mass_rate_kg_s']);q=float(r['flow_gpm'])*calc.whole.GPM
        fluid,_,_=calc.fluid(sample);target=float(r['measured_spp_psi'])
        def pressure(g):
            h=calc.m1.hydraulics(mass,g,T_avg=float(r['temperature_C']),tfa=sample['tfa_m2'],fluid=fluid,
                hydraulics_model='v1.6.0',surface=calc.surface,annulus_model=calc.adapter.MODEL,friction='colebrook',roughness=0.)
            return (h['spp']+float(calc.surface.pressure(mass/q,q))-h['dp_surface'])/calc.whole.PSI
        working=pressure(base)
        for variant in CHECKED:
            changed=geometry(context,sample,variant);value=pressure(changed)
            rows.append(dict(window_id=r['window_id'],assembly=r['assembly'],candidate=variant,bit_depth_ft=r['bit_depth_ft'],
                flow_gpm=r['flow_gpm'],geometry_identical=base.string==changed.string and base.hole==changed.hole,
                measured_spp_psi=target,working_spp_psi=working,candidate_spp_psi=value,pressure_change_psi=value-working,
                candidate_deficit_psi=target-value))
    diagnosis.write(a.output/'shallow-diagnostic.csv',rows)
    calc.score.write_json(a.output/'shallow-manifest.json',dict(method='Existing primary shallow identities and frozen isothermal state',
        selection='All ten primary near-surface windows from entry 9',new_circulation_solves=0,
        input_sha256={source.relative_to(ROOT).as_posix():hashlib.sha256(source.read_bytes()).hexdigest()},
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        output_sha256=hashlib.sha256((a.output/'shallow-diagnostic.csv').read_bytes()).hexdigest()))
    print('Shallow rows:',len(rows),'identical geometries:',sum(r['geometry_identical'] for r in rows),
        'remaining deficit range:',min(r['candidate_deficit_psi'] for r in rows),max(r['candidate_deficit_psi'] for r in rows))


if __name__=='__main__':main()
