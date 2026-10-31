"""Reproduce the additions declared after the entry 9 pressure comparison.

The original tables are read unchanged. No circulation solve, parameter
fit to the physical model, or protected-well target is used.
"""
from collections import defaultdict
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path

import numpy as np

import analyse
from diagnose import Calculation, HERE, ROOT, read, write


BASE = HERE/'results'
OUT = BASE/'additions'
KEY = (*analyse.KEYS, 'excursion')
PPG = 119.8264273
GPM = .003785411784/60
PSI = 6894.757293168


def nozzle_floor(q_gpm, density_ppg, area_m2):
    """Ideal nozzle kinetic head [psi], Cd=1; no other pressure terms."""
    if q_gpm <= 0 or density_ppg <= 0 or area_m2 <= 0:
        raise ValueError('Nozzle floor requires positive flow, density and area')
    return density_ppg*PPG/2*(q_gpm*GPM/area_m2)**2/PSI


def group_key(row, fields=KEY):
    return tuple(str(row[k]) for k in fields)


def shallow_excess(rows):
    """Level means and all separated pairs, within an excursion and 5 ft."""
    groups = defaultdict(list)
    for row in rows:
        groups[group_key(row)].append(row)
    levels_out, pairs = [], []
    for key, items in sorted(groups.items()):
        for index, depth in enumerate(analyse.clustered(items,'bit_depth_ft',5.)):
            levels = defaultdict(list)
            for row in depth:
                levels[round(row['flow_gpm']/25)*25].append(row)
            if len(levels)<2:
                continue
            base = dict(zip(KEY,key))
            base.update(depth_group=index+1,depth_min_ft=min(r['bit_depth_ft'] for r in depth),
                        depth_max_ft=max(r['bit_depth_ft'] for r in depth))
            means = []
            for centre, values in sorted(levels.items()):
                mean = {**base,'flow_centre_gpm':centre,'windows':len(values),
                        'window_ids':';'.join(r['window_id'] for r in values)}
                for field in ['flow_gpm','measured_spp_psi','modelled_spp_psi']:
                    mean[field] = float(np.mean([r[field] for r in values]))
                mean['excess_psi'] = mean['measured_spp_psi']-mean['modelled_spp_psi']
                mean['excess_min_psi'] = min(r['measured_spp_psi']-r['modelled_spp_psi'] for r in values)
                mean['excess_max_psi'] = max(r['measured_spp_psi']-r['modelled_spp_psi'] for r in values)
                mean['motor'] = ';'.join(sorted({r.get('motor','') for r in values}))
                means.append(mean)
            for low, high in combinations(means,2):
                if high['flow_gpm']-low['flow_gpm']<25:
                    continue
                positive = low['excess_psi']>0 and high['excess_psi']>0
                pairs.append({**base,'low_gpm':low['flow_gpm'],'high_gpm':high['flow_gpm'],
                    'low_excess_psi':low['excess_psi'],'high_excess_psi':high['excess_psi'],
                    'exponent_b':math.log(high['excess_psi']/low['excess_psi'])/
                        math.log(high['flow_gpm']/low['flow_gpm']) if positive else None,
                    'status':'positive excess pair' if positive else 'non-positive excess',
                    'low_window_ids':low['window_ids'],'high_window_ids':high['window_ids']})
            levels_out.extend(means)
    return levels_out,pairs


def side_by_side(original, filtered, kind):
    """Retain every original fit and identify fits lost after filtering."""
    fields = (*KEY,'flow_centre_gpm') if kind=='slopes' else KEY
    answer, used = [], set()
    for old in original:
        candidates = [(i,new) for i,new in enumerate(filtered)
                      if group_key(old,fields)==group_key(new,fields)]
        if kind=='flow':
            old_ids = set(old['window_ids'].split(';'))
            candidates = [(i,new) for i,new in candidates
                          if old_ids & set(new['window_ids'].split(';'))]
        if len(candidates)>1:
            raise ValueError('Ambiguous fit correspondence')
        new = candidates[0][1] if candidates else {}
        if candidates:used.add(candidates[0][0])
        row = {k:old[k] for k in fields}
        row['filtered_status'] = 'fit available' if new else 'insufficient coverage'
        for prefix, source in [('declared',old),('filtered',new)]:
            row.update({prefix+'_'+k:v for k,v in source.items() if k not in fields})
        answer.append(row)
    for i,new in enumerate(filtered):
        if i not in used:
            answer.append({**{k:new[k] for k in fields},'filtered_status':'new eligible group',
                           **{'filtered_'+k:v for k,v in new.items() if k not in fields}})
    return answer


def pipe_inputs(rows, slopes):
    """Archive actual ordinary-pipe hydraulic geometry at every slope window."""
    calc = Calculation()
    stages = read(BASE/'depth-stages.csv')
    selected = set()
    for fit in slopes:
        for stage in stages:
            if group_key(stage,(*KEY,'flow_centre_gpm'))==group_key(fit,(*KEY,'flow_centre_gpm')):
                selected.update((stage['role'],s) for s in stage['window_ids'].split(';'))
    result = []
    for row in rows:
        if (row['role'],row['window_id']) not in selected:
            continue
        sample = calc.trip_sample(row)
        geometry = calc.geometry(sample,row['bit_depth_ft'],float(row['hole_depth_ft']))
        _,pv,yp = calc.fluid(sample)
        for segment in geometry.string:
            pipe = segment.pipe
            if not (pipe.name.startswith('IDP,') or pipe.name in
                    ('5-1/2 in 24.7 lb/ft drill pipe','heavy-weight drill pipe')):
                continue
            joint = pipe.hydraulic_joint
            result.append({**{k:row[k] for k in (*KEY,'window_id','input_sample_id')},
                'bit_depth_ft':row['bit_depth_ft'],'pipe_type':pipe.name,
                'flow_centre_gpm':round(row['flow_gpm']/25)*25,
                'length_ft':segment.length/.3048,'body_od_in':2*pipe.r_out/.0254,
                'body_bore_in':2*pipe.r_bore/.0254,'joint_od_in':joint.outer_diameter/.0254,
                'joint_bore_in':joint.bore_diameter/.0254,
                'joint_restriction_in':joint.restriction_length/.0254,
                'joint_pitch_ft':joint.spacing/.3048,'joint_transition':joint.transition,
                'joint_source':joint.source,'density_ppg':sample['density_ppg'],
                'pv_cP':pv,'yp_lbf_100ft2':yp,'pv_ref_T_C':26.7,
                'temperature_C':row.get('temperature_C',''),
                'flow_gpm':row['flow_gpm'],'rheology':'entry 6 no-yield',
                'pipe_friction':'existing smooth Blasius/Bingham kernel; no roughness input'})
    return result


def eow18():
    groups = defaultdict(list)
    for stage in read(BASE/'depth-stages.csv'):
        if stage['well']=='16B' and stage['assembly']=='18':
            groups[group_key(stage,(*KEY,'flow_centre_gpm'))].append(stage)
    answer = []
    for key, stages in sorted(groups.items()):
        if len(stages)!=2:
            continue
        stages.sort(key=lambda s:float(s['bit_depth_ft']))
        a,b = stages
        span = float(b['bit_depth_ft'])-float(a['bit_depth_ft'])
        result = dict(zip((*KEY,'flow_centre_gpm'),key))
        result.update(addition_role='secondary descriptive endpoint difference',
            stages=2,windows=sum(int(s['windows']) for s in stages),
            depth_min_ft=float(a['bit_depth_ft']),depth_max_ft=float(b['bit_depth_ft']),depth_span_ft=span,
            window_ids=';'.join(s['window_ids'] for s in stages))
        for kind in ['measured','modelled']:
            result[kind+'_slope'] = (float(b[kind+'_spp_psi'])-float(a[kind+'_spp_psi']))/span*1000
        result['slope_ratio'] = result['measured_slope']/result['modelled_slope']
        answer.append(result)
    return answer


def main():
    OUT.mkdir(exist_ok=True)
    raw = analyse.numeric(read(BASE/'windows.csv'))
    exploratory = analyse.numeric(read(BASE/'exploratory-windows.csv'))
    valid = [r for r in raw+exploratory if r['status']=='ok']
    plan = json.loads((ROOT/'validation/forge16b/s2/plan.json').read_text(encoding='utf-8'))
    samples = {s['id']:s for s in plan['samples']}
    floor_rows, kept = [], []
    for row in valid:
        sample = samples[row['input_sample_id']]
        floor = nozzle_floor(row['flow_gpm'],sample['density_ppg'],sample['tfa_m2'])
        passed = row['measured_spp_psi']>=floor
        floor_rows.append({**{k:row[k] for k in (*KEY,'window_id','input_sample_id')},
            'recorded_flow_gpm':row['flow_gpm'],'nominal_density_ppg':sample['density_ppg'],
            'recorded_tfa_m2':sample['tfa_m2'],'discharge_coefficient':1.,
            'nozzle_floor_psi':floor,'measured_spp_psi':row['measured_spp_psi'],
            'margin_psi':row['measured_spp_psi']-floor,'passes':passed})
        if passed:kept.append(row)
    write(OUT/'nozzle-floor.csv',floor_rows)
    groups = defaultdict(list)
    for row in floor_rows:
        groups[group_key(row,('well','role','assembly'))].append(row)
    write(OUT/'floor-removals.csv',[{**dict(zip(('well','role','assembly'),key)),
        'evaluated_predictions':len(items),'removed_predictions':sum(not r['passes'] for r in items),
        'physical_windows':len({r['window_id'] for r in items}),
        'removed_physical_windows':len({r['window_id'] for r in items if not r['passes']})}
        for key,items in sorted(groups.items())])
    sl,st,om = analyse.slopes(kept)
    write(OUT/'filtered-slopes.csv',sl)
    write(OUT/'filtered-depth-stages.csv',st)
    write(OUT/'filtered-slope-exclusions.csv',om)
    flow = analyse.flow_steps(kept)
    write(OUT/'filtered-flow-steps.csv',flow)
    write(OUT/'slope-comparison.csv',side_by_side(read(BASE/'slopes.csv'),sl,'slopes'))
    write(OUT/'flow-step-comparison.csv',side_by_side(read(BASE/'flow-steps.csv'),flow,'flow'))
    levels,pairs = shallow_excess(analyse.numeric(read(BASE/'near-surface.csv')))
    write(OUT/'shallow-flow-levels.csv',levels)
    write(OUT/'shallow-flow-exponents.csv',pairs)
    descriptive = eow18()
    write(OUT/'eow18-descriptive.csv',descriptive)
    write(OUT/'pipe-inputs.csv',pipe_inputs(valid,[*read(BASE/'slopes.csv'),*descriptive]))
    primary = [r for r in analyse.numeric(read(BASE/'near-surface.csv')) if r['role']=='primary']
    write(OUT/'shallow-ratio-extrema.csv',[{'extreme':name,**row} for name,row in
        [('minimum',min(primary,key=lambda r:r['measured_modelled_ratio'])),
         ('maximum',max(primary,key=lambda r:r['measured_modelled_ratio']))]])
    sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    sources = [Path(__file__),HERE/'analyse.py',HERE/'diagnose.py',
        ROOT/'validation/forge16b/s2/plan.json',BASE/'manifest.json',*sorted(BASE.glob('*.csv'))]
    manifest = dict(accepted_results_commit='ee1dec182818855b3cb0d9d7c61290874488ecaf',
        model_changed=False,full_solves=0,nozzle_floor_coefficient=1.,
        original_inputs_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sources},
        files_sha256={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='manifest.json'})
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'predictions':len(valid),'floor_removed':sum(not r['passes'] for r in floor_rows),
        'filtered_slopes':len(sl),'filtered_flow_fits':len(flow),'shallow_pairs':len(pairs)}))


if __name__=='__main__':
    main()
