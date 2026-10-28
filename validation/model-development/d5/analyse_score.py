"""Pair D5 with the frozen baseline and retain every unavailable sample.

This script calculates descriptive tables from saved results. It does not run
the model or change the frozen scoreboard or its populations.
"""
import argparse
from collections import defaultdict
import csv
import importlib.util
import json
import hashlib
from pathlib import Path
import subprocess

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('frozen_scoreboard',ROOT/'validation/scoreboard/scoreboard.py')
score=importlib.util.module_from_spec(spec);spec.loader.exec_module(score)


def truth(row):return str(row.get('success'))=='True'


def numeric(row):
    return {k:(None if v=='' else v=='True' if v in ('True','False') else
        float(v) if k not in ('sample_id','well','bha','source','event_id','status','error_type') else v)
        for k,v in row.items()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--score',type=Path,required=True)
    args=parser.parse_args();output=args.score
    roots={'legacy':ROOT/'validation/scoreboard/baseline','entry1':ROOT/'validation/model-development/entry-1','d5':output}
    cases={key:score.read_csv(path/'circulation.csv') for key,path in roots.items()}
    events={key:score.read_csv(path/'run-in.csv') for key,path in roots.items()}
    indexed={key:{r['sample_id']:r for r in rows} for key,rows in cases.items()}
    paired_ids={r['sample_id'] for r in cases['d5'] if truth(r)}
    event_ids={r['event_id'] for r in events['d5'] if truth(r)}
    # Full-population columns preserve unavailable counts. Paired columns
    # give a like-for-like comparison when an input prevents a new solve.
    all_scores={key:{(r['gap'],r['well'],r['group']):r for r in score.read_csv(path/'scoreboard.csv')}
                for key,path in roots.items()}
    matched={}
    for key in roots:
        rows=[numeric(r) for r in cases[key] if r['sample_id'] in paired_ids]
        es=[numeric(r) for r in events[key] if r['event_id'] in event_ids]
        matched[key]={(r['gap'],r['well'],r['group']):r for r in score.scoreboard(rows,es)}
    comparison=[]
    for identity,reference in all_scores['legacy'].items():
        row=dict(zip(('gap','well','group'),identity),units=reference['units'])
        for key in roots:
            value=all_scores[key].get(identity,{})
            for field in ('planned','compared','unavailable','model_mean','measured_mean','bias','MAE','mean_percent_error'):
                row[key+'_'+field]=value.get(field)
            for field in ('compared','model_mean','measured_mean','bias','MAE','mean_percent_error'):
                row[key+'_paired_'+field]=matched[key].get(identity,{}).get(field)
        comparison.append(row)
    score.write_csv(output/'comparison.csv',comparison)
    plan=score.read_json(score.PLAN);samples={s['id']:s for s in plan['samples']}
    bounds=[];groups=defaultdict(list);failures=[]
    for current in cases['d5']:
        sample=samples[current['sample_id']]
        if not truth(current):
            failures.append(dict(sample_id=current['sample_id'],well=current['well'],bha=current['bha'],
                reason='unresolved recorded instrument bore' if current['bha'] in ('23','38','39') and current['well']=='16A' else current.get('error_type')))
        if (sample.get('measured_bit_box_C') if sample['well']=='16A' else sample.get('measured_MWD_C')) is None:continue
        row=dict(sample_id=current['sample_id'],well=current['well'],bha=current['bha'],available=truth(current))
        if truth(current):
            g=score.geometry(sample,plan,'legacy')
            _,pv,yp=score.energy.fluid_for(sample,'s1_original' if sample['well']=='16B' else 'blind_original')
            fluid=score.Mud(sample['density_ppg']*score.whole.PPG,pv_ref=None if pv is None else pv*.001,
                yield_point=yp*score.whole.YP_PA,pv_ref_T=26.7)
            rho=float(score.m1.fluid_props(np.array([sample['T_in_C']]),np.array([score.m1.P_SURF]),fluid)[0][0])
            mass=sample['flow_gpm']*score.whole.GPM*rho
            for reference in ('legacy','entry1'):
                old=indexed[reference][current['sample_id']]
                cp=float(score.m1._cp(np.array([float(old['bit_C'])]),np.array([score.m1.P_of_z(g.survey.tvd(g.md_bit))]),fluid)[0])
                power=float(current['model_hydraulic_W'])-float(old['model_hydraulic_W'])
                scale=power/(mass*cp)
                position=84 if sample['well']=='16B' and sample['run'] in score.TRIAL|{'27','38'} else 22
                sensor='bit_C' if sample['well']=='16A' else f'bore_{position}ft_C'
                row.update({reference+'_bit_change_C':float(current['bit_C'])-float(old['bit_C']),
                    reference+'_sensor_change_C':float(current[sensor])-float(old[sensor]),
                    reference+'_return_change_C':float(current['return_C'])-float(old['return_C']),
                    reference+'_added_in_hole_W':power,reference+'_bulk_scale_C':scale,
                    reference+'_cp_J_kgK':cp,'mass_rate_kg_s':mass,'sensor_column':sensor})
        bounds.append(row);groups[row['well'],row['bha']].append(row)
    summaries=[]
    for (well,bha),items in sorted(groups.items()):
        good=[r for r in items if r['available']]
        row=dict(well=well,bha=bha,planned=len(items),compared=len(good),unavailable=len(items)-len(good))
        for key in good[0] if good else ():
            if key.startswith(('legacy_','entry1_')) or key=='mass_rate_kg_s':row[key]=float(np.mean([r[key] for r in good]))
        summaries.append(row)
    score.write_csv(output/'bit-energy-samples.csv',bounds)
    score.write_csv(output/'bit-energy-assemblies.csv',summaries)
    if failures:score.write_csv(output/'unavailable.csv',failures)
    else:(output/'unavailable.csv').write_text('sample_id,well,bha,reason\n',encoding='utf-8')
    # Extra per-assembly summaries do not replace the frozen well totals.
    extra=[]
    for well,bha in sorted(groups):
        ids={r['sample_id'] for r in cases['d5'] if r['well']==well and r['bha']==bha}
        for key in roots:
            rows=[numeric(r) for r in cases[key] if r['sample_id'] in ids&paired_ids]
            for field,observed,gap,unit in (('model_hydraulic_W','measured_hydraulic_W','G2','kW'),('return_C','measured_return_C','G5','degC')):
                if gap=='G5' and well!='16A':continue
                pairs=[(r[field]/1000 if unit=='kW' else r[field],r[observed]/1000 if unit=='kW' else r[observed])
                    for r in rows if r.get(observed) is not None]
                planned=(sum(r['raw_spp_psi']!='' for r in cases['d5'] if r['sample_id'] in ids)
                         if gap=='G2' else len(ids))
                extra.append(dict(variant=key,**score.aggregate(gap,well,bha,pairs,planned,units=unit)))
    score.write_csv(output/'assembly-power-return.csv',extra)
    manifest=score.read_json(output/'manifest.json')
    manifest['supplement_sha256']={name:score.sha(output/name) for name in
        ('comparison.csv','bit-energy-samples.csv','bit-energy-assemblies.csv','unavailable.csv','assembly-power-return.csv')}
    manifest['comparison']='Paired columns use identical available sample IDs across all three calculations'
    manifest['assembly_audit_sha256']=score.sha(ROOT/'validation/model-development/d5/components.json')
    manifest.setdefault('declaration_commit','11fc892')
    manifest.setdefault('implementation_commit','dd2545c')
    original_audit=subprocess.check_output(['git','show','dd2545c:validation/model-development/d5/components.json'],cwd=ROOT)
    old_rows=json.loads(original_audit)
    new_rows=score.read_json(ROOT/'validation/model-development/d5/components.json')
    changed={(old['well'],old['bha'],old['item']) for old,new in zip(old_rows,new_rows) if old!=new}
    assert len(old_rows)==len(new_rows) and changed=={('16A','23',6),('16A','38',3),('16A','39',3)}
    manifest['retained_assembly_audit_sha256']=hashlib.sha256(original_audit).hexdigest()
    manifest['authorised_instrument_records']=[list(key) for key in sorted(changed)]
    manifest['unaffected_audit_records_identical']=True
    qualifications=[]
    for well,bha in sorted(groups):
        components=[r for r in new_rows if (r['well'],r['bha'])==(well,bha)]
        qualifications.append(dict(well=well,bha=bha,
            motor_loss='motor loss unknown' if any(r['motor'] for r in components) else 'no motor recorded',
            thermal_only_instrument_items=';'.join(str(r['item']) for r in components
                if not r['motor'] and not r['bit'] and r['hydraulic_id_in'] is None),
            fitted_insulation=well=='16B' and bha in ('18','19'),
            transferred_connection_pitch=well=='16B',
            source='components.csv; well, bha, item, reported_id_in, thermal_id_in, hydraulic_id_in, flags'))
    score.write_csv(output/'assembly-qualifications.csv',qualifications)
    manifest['supplement_sha256']['assembly-qualifications.csv']=score.sha(output/'assembly-qualifications.csv')
    score.write_json(output/'manifest.json',manifest)


if __name__=='__main__':main()
