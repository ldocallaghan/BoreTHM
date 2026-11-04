"""Frozen trip groups for tapered-joint prediction and later scoring.

Model-only mode reads operating inputs and calculates modelled slopes only.
It expresses a predicted measured/modelled ratio as a multiplier of the
archived working ratio, without recomputing an observation-based score.
Scoring mode uses entry 10's unchanged entry 9 grouping and regression.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

from predict import load,geometry as candidate_geometry
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'entry-9'))
reduction=load('entry13_trip_reduction',HERE.parent/'entry-9/analyse.py')
diagnosis=load('entry13_trip_calculation',HERE.parent/'entry-9/diagnose.py')


def model_slopes(rows):
    grouped=defaultdict(list)
    for r in rows:
        centre=round(r['flow_gpm']/25)*25
        if centre>0 and abs(r['flow_gpm']/centre-1)<=.025:
            grouped[tuple(r[k] for k in reduction.KEYS)+(r['excursion'],centre)].append(r)
    summaries=[];stages=[]
    for key,items in sorted(grouped.items()):
        base=dict(zip((*reduction.KEYS,'excursion','flow_centre_gpm'),key));means=[]
        for i,group in enumerate(reduction.clustered(items,'bit_depth_ft',100.)):
            row=dict(**base,stage=i+1,windows=len(group),window_ids=';'.join(r['window_id'] for r in group))
            for field in ('bit_depth_ft','flow_gpm','modelled_spp_psi'):
                row[field]=sum(r[field] for r in group)/len(group)
            means.append(row);stages.append(row)
        span=max(r['bit_depth_ft'] for r in means)-min(r['bit_depth_ft'] for r in means)
        assert len(means)>=3 and span>=1000
        fit=reduction.regression([r['bit_depth_ft']/1000 for r in means],[r['modelled_spp_psi'] for r in means])
        summaries.append(dict(**base,stages=len(means),windows=len(items),depth_span_ft=span,
                              **{'modelled_'+k:v for k,v in fit.items()}))
    return summaries,stages


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-only',action='store_true');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--declaration',default='');a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True);started=time.perf_counter()
    calc=diagnosis.Calculation();options=calc.score.read_json(HERE/'options.json')
    groups=options['secondary_measures']['trip_slopes']['groups']
    identities={(g['assembly'],g['excursion'],g['flow_centre_gpm']) for g in groups}
    stages=diagnosis.read(HERE.parent/'entry-9/results/depth-stages.csv')
    window_ids={w for r in stages if r['role']=='primary' and (r['assembly'],r['excursion'],r['flow_centre_gpm']) in identities for w in r['window_ids'].split(';')}
    windows=[r for r in diagnosis.read(HERE.parent/'entry-9/results/windows.csv') if r['well']=='16B' and r['window_id'] in window_ids]
    assert len(windows)==len(window_ids)
    samples={s['id']:s for s in calc.plan['samples']}
    all_windows=[];all_slopes=[];all_stages=[];checks=[]
    for variant,settings in options['variants'].items():
        rows=[]
        for source in windows:
            sample=samples[source['input_sample_id']]
            base=calc.geometry(sample,float(source['bit_depth_ft']),float(source['hole_depth_ft']))
            context=SimpleNamespace(plan=calc.plan,whole=calc.whole,score=SimpleNamespace(wg=calc.score.wg,geometry=lambda *args:base))
            g=candidate_geometry(context,sample,variant);fluid,_,_=calc.fluid(sample)
            mass,temperature=float(source['mass_rate_kg_s']),float(source['temperature_C'])
            q_gpm=float(source['flow_gpm'])
            hyd=calc.m1.hydraulics(mass,g,T_avg=temperature,tfa=sample['tfa_m2'],fluid=fluid,
                hydraulics_model='v1.6.0',surface=calc.surface,annulus_model=calc.adapter.MODEL,
                friction=settings['friction'],roughness=settings['roughness_m'])
            q=q_gpm*calc.whole.GPM;surface=float(calc.surface.pressure(mass/q,q))
            pressure=(hyd['spp']+surface-hyd['dp_surface'])/calc.whole.PSI
            row=dict(well='16B',role='primary',assembly=source['assembly'],variant=source['variant'],candidate=variant,
                excursion=source['excursion'],window_id=source['window_id'],bit_depth_ft=float(source['bit_depth_ft']),
                hole_depth_ft=float(source['hole_depth_ft']),flow_gpm=q_gpm,temperature_C=temperature,mass_rate_kg_s=mass,
                modelled_spp_psi=pressure,flags=';'.join(hyd['flags']),installed_tool_band_available=False)
            if not a.model_only:
                row.update(measured_spp_psi=float(source['measured_spp_psi']),residual_psi=pressure-float(source['measured_spp_psi']))
            rows.append(row)
        if a.model_only:
            summaries,reduced_stages=model_slopes(rows)
        else:
            summaries,reduced_stages,exclusions=reduction.slopes(rows);assert not exclusions
        assert len(summaries)==len(groups)
        for row in summaries:row.update(candidate=variant,added_pipe='insulated' if row['assembly']=='19' else 'regular')
        all_windows.extend(rows);all_slopes.extend(summaries)
        all_stages.extend({**r,'candidate':variant} for r in reduced_stages)
        print(variant,len(rows),'windows',len(summaries),'slope groups',flush=True)
    if a.model_only:
        baseline={(r['assembly'],r['excursion'],r['flow_centre_gpm']):r for r in all_slopes if r['candidate']=='working'}
        for row in all_slopes:
            old=baseline[row['assembly'],row['excursion'],row['flow_centre_gpm']]
            row.update(model_slope_change=row['modelled_slope']-old['modelled_slope'],
                predicted_ratio_multiplier=old['modelled_slope']/row['modelled_slope'],
                ratio_definition='R_candidate = archived R_working times this multiplier; no new measured slope or ratio calculated before declaration')
    else:
        old={(r['assembly'],r['excursion'],str(r['flow_centre_gpm'])):r for r in diagnosis.read(HERE.parent/'entry-10/results/secondary/slopes.csv') if r['candidate']=='smooth'}
        declared={(r['candidate'],r['assembly'],r['excursion'],str(r['flow_centre_gpm'])):r for r in diagnosis.read(HERE/'predictions/trips/slopes.csv')}
        for row in all_slopes:
            key=row['assembly'],row['excursion'],str(row['flow_centre_gpm'])
            previous=old[key];pred=declared[row['candidate'],*key]
            assert row['windows']==int(previous['windows']) and row['stages']==int(previous['stages'])
            assert abs(row['measured_slope']-float(previous['measured_slope']))<1e-9
            checks.append(dict(candidate=row['candidate'],assembly=row['assembly'],excursion=row['excursion'],
                flow_centre_gpm=row['flow_centre_gpm'],declared_modelled_slope=pred['modelled_slope'],
                scored_modelled_slope=row['modelled_slope'],difference=row['modelled_slope']-float(pred['modelled_slope']),
                tolerance=1.,passed=abs(row['modelled_slope']-float(pred['modelled_slope']))<=1.,
                working_slope_ratio=float(previous['slope_ratio'])))
    for name,data in [('windows.csv',all_windows),('slopes.csv',all_slopes),('depth-stages.csv',all_stages),('prediction-checks.csv',checks)]:
        if data:diagnosis.write(a.output/name,data)
    sources=[Path(__file__),HERE/'predict.py',HERE/'options.json',HERE.parent/'entry-9/analyse.py',HERE.parent/'entry-9/diagnose.py',HERE.parent/'entry-9/results/windows.csv',HERE.parent/'entry-9/results/depth-stages.csv']
    calc.score.write_json(a.output/'manifest.json',dict(declaration_commit=a.declaration,model_only=a.model_only,
        targets_compared=not a.model_only,runtime_s=time.perf_counter()-started,windows_per_variant=len(windows),groups_per_variant=len(groups),
        candidates=list(options['variants']),acceptance_use=False,exclusions=[],
        source_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        results_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in a.output.glob('*.csv')}))


if __name__=='__main__':main()
