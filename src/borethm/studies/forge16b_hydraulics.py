"""Motorless FORGE 16B pressure accounting, with external geometric estimates.

Calls the existing circulation and hydraulics functions unchanged. External
loss estimates are post-processing only and never alter a model result.
The protocol is validation/forge16b/comparison_protocol_s2b.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from borethm import fluids, model1_coupled as m1
from borethm.studies import forge16_energy as energy
from borethm.studies import validate_forge16b as trial
from borethm.studies import validate_forge16b_wholewell as whole

FT, INCH, GPM, PSI = whole.FT, whole.INCH, whole.GPM, whole.PSI
RUNS = (12, 13, 15, 16)
JOINTS = {'EIS': (7., 4.), 'GPDS55': (7.25, 3.5)}
SURFACE = {1: 1., 2: .36, 3: .22, 4: .15, 5: .15}
JOINT_PITCH_FT = 2378. / 75.
JOINT_LENGTHS_IN = (0., 29., 58.)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(data, s2, output):
    output.mkdir(parents=True, exist_ok=True)
    if (output/'plan.json').exists():
        raise FileExistsError('S2b plan already exists')
    original = json.loads((s2/'plan.json').read_text(encoding='utf-8'))
    expected = {r['case_id']: r for r in map(json.loads,
                (s2/'results.jsonl').read_text().splitlines())}
    samples = [s for s in original['samples']
               if s['well'] == '16B' and int(s['run']) in RUNS]
    assert len(samples) == 45 and all(not s['documented_motor'] for s in samples)
    ids = {s['id'] for s in samples}
    cases = [c for c in original['cases'] if c['sample'] in ids]
    assert len(cases) == 90
    preserved = {p.relative_to(data).as_posix(): digest(p)
                 for sub in ('s1', 's2') for p in sorted((data/sub).rglob('*'))
                 if p.is_file() and '__pycache__' not in p.parts}
    plan = dict(baseline=original['baseline'], script_sha256=digest(__file__),
                protocol_sha256=digest(data/'comparison_protocol_s2b.md'),
                s2_plan_sha256=digest(s2/'plan.json'),
                calculation_hashes=original['calculation_hashes'],
                source_hashes=original['source_b'], preserved_archives=preserved,
                samples=samples, cases=cases,
                expected={c['case_id']: expected[c['case_id']] for c in cases},
                components=original['components_b'], k_idp=original['k_idp'],
                joint_scenarios=JOINTS, surface_cases=SURFACE,
                joint_pitch_ft=JOINT_PITCH_FT, joint_lengths_in=JOINT_LENGTHS_IN,
                versions={**original['versions'], 'Python': platform.python_version()})
    whole.dump(output/'plan.json', plan)
    (output/'plan.sha256').write_text(digest(output/'plan.json')+'\n', encoding='utf-8')
    print('Frozen', len(samples), 'samples and', len(cases), 'replays')


def local_change(area_up, area_down, rho, mass_rate, mu, dh_small):
    """Idelchik sudden-change estimate and its documented Re applicability."""
    small, large = min(area_up, area_down), max(area_up, area_down)
    ratio = small/large
    velocity = mass_rate/(rho*small)
    expansion = area_down > area_up
    k = (1-ratio)**2 if expansion else .5*(1-ratio)**.75
    re = rho*velocity*dh_small/mu
    threshold = 3300. if expansion else 10000.
    return k*.5*rho*velocity**2, k, re, bool(re > threshold or k == 0)


def properties(s, g, result, fluid, md, annulus=False):
    temp = float(np.interp(md, result['z'], result['Tu' if annulus else 'Td']))
    pressure = float(m1.P_of_z(g.survey.tvd(md)))
    rho, _, mu, _ = (float(x[0]) for x in m1.fluid_props(
        np.array([temp]), np.array([pressure]), fluid))
    return temp, pressure, rho, mu


def gradient(rho, mu, fluid, mass_rate, area, dh, annulus=False):
    velocity = mass_rate/(rho*area)
    if fluid.yield_point > 0:
        value, re = fluids.bingham_gradient(rho, mu, fluid.yield_point,
                                            velocity, dh, annulus)
        return float(value), float(re)
    re = rho*velocity*dh/mu
    return float(m1.friction_factor(re))*rho*velocity**2/(2*dh), re


def breakdown(s, case, g, fluid, result, mass_rate, plan):
    ident = dict(case_id=case['case_id'], sample=s['id'], run=s['run'],
                 rheology_case=case['rheology_case'])
    hyd = m1.hydraulics(mass_rate, g, result=result, tfa=s['tfa_m2'], fluid=fluid)
    model_pieces = []
    included = dict(pipe_body_psi=0., bha_hwdp_psi=0., bha_lower_aggregate_psi=0.)
    for p in hyd['pieces']:
        mid = (p['md_top']+p['md_bottom'])/2
        segment = int(g.segment_index(mid))
        key = ('pipe_body_psi' if segment == 0 else
               'bha_hwdp_psi' if 'HWDP' in g.string[segment].pipe.name else
               'bha_lower_aggregate_psi')
        included[key] += p['dp_bore']/PSI
        model_pieces.append({**ident, **p, 'segment': segment,
                             'pipe': g.string[segment].pipe.name, 'category': key})
    included.update(bit_nozzles_psi=hyd['dp_bit']/PSI,
                    annulus_psi=hyd['dp_annulus']/PSI,
                    density_column_psi=hyd['dp_buoyancy']/PSI,
                    tool_joints_psi=0., surface_lines_psi=0.)
    assert abs(sum(included.values())-hyd['spp']/PSI) < 1e-8

    # Serial lower BHA passages use their recorded dimensions and lengths.
    lower = [dict(c) for c in reversed(plan['components'][str(s['eow_bha'])])
             if c['kind'] != 'HWDP']
    for c in lower:
        # A gauge-size cutting bit is not a solid, sealed annular cylinder.
        # Keep the existing lower-assembly OD over this short face interval.
        c['annulus_od_used_in'] = (float(2*g.at(np.array([g.md_bit]))['r_out'][0])/INCH
                                  if 'bit' in c['component'].lower() else c['od_in'])
    md = float(g._seg_ends[1])
    component_rows = []
    refined_bore = refined_ann = 0.
    for c in lower:
        length = c['length_ft']*FT
        midpoint = md+length/2
        _, _, rb, mub = properties(s, g, result, fluid, midpoint)
        _, _, ra, mua = properties(s, g, result, fluid, midpoint, True)
        inside, outside = c['id_in']*INCH, c['annulus_od_used_in']*INCH
        hole = float(2*g.at(np.array([midpoint]))['r_wall'][0])
        bore_area = math.pi*inside**2/4
        ann_area = math.pi*(hole**2-outside**2)/4
        gb, reb = gradient(rb, mub, fluid, mass_rate, bore_area, inside)
        ga, rea = gradient(ra, mua, fluid, mass_rate, ann_area, hole-outside, True)
        refined_bore += gb*length/PSI
        refined_ann += ga*length/PSI
        component_rows.append({**ident, **c, 'md_top_ft': md/FT,
            'md_bottom_ft': (md+length)/FT, 'bore_friction_psi': gb*length/PSI,
            'annulus_friction_psi': ga*length/PSI, 'bore_Re_apparent': reb,
            'annulus_Re_apparent': rea,
            'extra_internal_psi_per_K': .5*rb*(mass_rate/(rb*bore_area))**2/PSI,
            'proprietary_or_valve_loss_psi': '',
            'unquantified_restriction': any(word in c['component'].lower()
                for word in ('halo', 'float', 'filter', 'black box'))})
        md += length
    assert abs(md-g.md_bit) < 1e-6
    lower_ann = sum(p['dp_ann']/PSI for p in hyd['pieces']
                    if p['md_top'] >= g._seg_ends[1]-1e-6)
    delta_bore = refined_bore-included['bha_lower_aggregate_psi']
    delta_ann = refined_ann-lower_ann

    # BHA transitions include the ordinary-pipe/HWDP boundary and both
    # sides of every serial component; the terminal nozzle is separate.
    sequence = [dict(component='ordinary pipe', length_ft=g.string[0].length/FT,
                     id_in=4.670, od_in=5.5),
                next(c for c in plan['components'][str(s['eow_bha'])]
                     if c['kind'] == 'HWDP'), *lower]
    transitions = []
    md = 0.
    for upper, down in zip(sequence, sequence[1:]):
        md += upper['length_ft']*FT
        hole = float(2*g.at(np.array([md]))['r_wall'][0])
        for annulus in (False, True):
            _, _, rho, mu = properties(s, g, result, fluid, md, annulus)
            if annulus:  # Upward flow: lower component is upstream.
                down_od = down.get('annulus_od_used_in', down['od_in'])
                upper_od = upper.get('annulus_od_used_in', upper['od_in'])
                au = math.pi*(hole**2-(down_od*INCH)**2)/4
                ad = math.pi*(hole**2-(upper_od*INCH)**2)/4
                dh = hole-max(upper_od, down_od)*INCH
            else:
                au, ad = (math.pi*(c['id_in']*INCH)**2/4 for c in (upper, down))
                dh = min(upper['id_in'], down['id_in'])*INCH
            dp, k, re, valid = local_change(au, ad, rho, mass_rate, mu, dh)
            transitions.append({**ident, 'upper': upper['component'],
                'lower': down['component'], 'md_ft': md/FT,
                'conduit': 'annulus' if annulus else 'bore',
                'loss_psi': dp/PSI, 'K': k, 'Re_small': re,
                'newtonian_Re_domain': valid})
    transition_sum = sum(r['loss_psi'] for r in transitions)

    # Connection losses replace body-length friction, not the full string.
    joints = []
    for name, (od, inside) in JOINTS.items():
        for segno in (0, 1):
            top = 0. if segno == 0 else float(g._seg_ends[0])
            bot = float(g._seg_ends[segno])
            count = (bot-top)/FT/JOINT_PITCH_FT if segno == 0 else 30.
            number = max(1, int(math.ceil(count)))
            weight = count/number
            body_id = 4.670 if segno == 0 else 3.625
            joint_id = inside if segno == 0 else body_id
            for i in range(number):
                z = top+(i+.5)*(bot-top)/number
                hole = float(2*g.at(np.array([z]))['r_wall'][0])
                for annulus in (False, True):
                    _, _, rho, mu = properties(s, g, result, fluid, z, annulus)
                    if annulus:
                        abody = math.pi*(hole**2-(5.5*INCH)**2)/4
                        ajoint = math.pi*(hole**2-(od*INCH)**2)/4
                        db, dj = hole-5.5*INCH, hole-od*INCH
                    else:
                        abody = math.pi*(body_id*INCH)**2/4
                        ajoint = math.pi*(joint_id*INCH)**2/4
                        db, dj = body_id*INCH, joint_id*INCH
                    body_gradient, _ = gradient(rho, mu, fluid, mass_rate, abody, db, annulus)
                    joint_gradient, re_app = gradient(rho, mu, fluid, mass_rate, ajoint, dj, annulus)
                    # Symmetric entry/exit: sum of sudden contraction and expansion.
                    entry = local_change(abody, ajoint, rho, mass_rate, mu, dj)
                    exit_ = local_change(ajoint, abody, rho, mass_rate, mu, dj)
                    joints.append({**ident, 'geometry': name,
                        'segment': 'ordinary_pipe' if segno == 0 else 'HWDP',
                        'conduit': 'annulus' if annulus else 'bore',
                        'md_ft': z/FT, 'joint_count_weight': weight,
                        'body_ID_in': body_id, 'joint_OD_in': od,
                        'joint_ID_in': joint_id,
                        'increment_psi_per_inch': weight*(joint_gradient-body_gradient)*INCH/PSI,
                        'sudden_local_psi': weight*(entry[0]+exit_[0])/PSI,
                        'Re_apparent': re_app, 'Re_plastic': entry[2],
                        'newtonian_Re_domain': entry[3] and exit_[3]})

    sample = {**ident, 'time': s['time'], 'depth_ft_MD': s['bit_ft'],
        'flow_gpm': s['flow_gpm'], 'inlet_C': s['T_in_C'],
        'density_ppg': s['density_ppg'], 'PV_cP': (s['original_mud'] if
            case['rheology_case'] == 's1_original' else s['revised_mud'])['PV_cP'],
        'YP_lbf_100ft2': (s['original_mud'] if case['rheology_case'] ==
            's1_original' else s['revised_mud'])['YP_lbf_100ft2'],
        'tfa_in2': s['tfa_m2']/INCH**2, 'measured_spp_psi': s['spp_psi'],
        'raw_differential_psi': s['raw_differential_psi'], 'motor_allowance_psi': 0.,
        **included, 'bha_included_total_psi': included['bha_hwdp_psi']+included['bha_lower_aggregate_psi'],
        'model_spp_psi': hyd['spp']/PSI,
        'model_accounted_fraction': hyd['spp']/PSI/s['spp_psi'],
        'model_residual_psi': s['spp_psi']-hyd['spp']/PSI,
        'serial_bha_bore_psi': refined_bore,
        'serial_bha_annulus_psi': refined_ann,
        'bha_bore_increment_psi': delta_bore,
        'bha_annulus_increment_psi': delta_ann,
        'bha_transition_sudden_psi': transition_sum,
        'unknown_tool_loss_psi': '',
        'dp_joint_expected_count': g.string[0].length/FT/JOINT_PITCH_FT,
        'hwdp_joint_count': 30}
    budgets = []
    for name in JOINTS:
        jj = [r for r in joints if r['geometry'] == name]
        for length in JOINT_LENGTHS_IN:
            internal = sum(r['increment_psi_per_inch']*length for r in jj if r['conduit'] == 'bore')
            external = sum(r['increment_psi_per_inch']*length for r in jj if r['conduit'] == 'annulus')
            for shape in ('gradual_zero_local', 'sudden'):
                local = sum(r['sudden_local_psi'] for r in jj) if shape == 'sudden' else 0.
                bha_local = transition_sum if shape == 'sudden' else 0.
                for surface_case, coefficient in {0: 0., **SURFACE}.items():
                    surface = coefficient*s['density_ppg']*(s['flow_gpm']/100)**1.86
                    added = delta_bore+delta_ann+internal+external+local+bha_local+surface
                    accounted = sample['model_spp_psi']+added
                    budgets.append({**ident, 'joint_geometry': name,
                        'joint_length_in': length, 'local_shape': shape,
                        'surface_case': surface_case, 'surface_coefficient': coefficient,
                        'measured_spp_psi': s['spp_psi'], 'model_spp_psi': sample['model_spp_psi'],
                        'bha_bore_increment_psi': delta_bore,
                        'bha_annulus_increment_psi': delta_ann,
                        'joint_internal_increment_psi': internal,
                        'joint_annulus_increment_psi': external,
                        'joint_local_increment_psi': local,
                        'bha_local_increment_psi': bha_local,
                        'surface_lines_estimate_psi': surface,
                        'estimated_increment_psi': added,
                        'accounted_psi': accounted, 'accounted_fraction': accounted/s['spp_psi'],
                        'remaining_residual_psi': s['spp_psi']-accounted,
                        'unknown_tool_loss_psi': '',
                        'raw_differential_psi': s['raw_differential_psi']})
    return sample, model_pieces, component_rows, transitions, joints, budgets


def verify_sources(data, output):
    plan = json.loads((output/'plan.json').read_text(encoding='utf-8'))
    assert digest(output/'plan.json') == (output/'plan.sha256').read_text().strip()
    assert digest(__file__) == plan['script_sha256']
    assert digest(data/'comparison_protocol_s2b.md') == plan['protocol_sha256']
    for name, value in plan['source_hashes'].items():
        assert digest(data/name) == value, name
    for name, value in plan['calculation_hashes'].items():
        assert digest(Path(m1.__file__).parent/name) == value, name
    for name, value in plan['preserved_archives'].items():
        assert digest(data/name) == value, name
    return plan


def run(data, output):
    plan = verify_sources(data, output)
    samples = {s['id']: s for s in plan['samples']}
    _, times, circ, depth = whole.clock(data)
    tables = [[] for _ in range(6)]
    replays = []
    (output/'profiles').mkdir(exist_ok=True)
    for case in plan['cases']:
        s = samples[case['sample']]
        start = time.perf_counter()
        g = whole.geometry(s, plan['components'], plan['k_idp'])
        fluid, _, _ = energy.fluid_for(s, case['rheology_case'])
        rho = float(m1.fluid_props(np.array([s['T_in_C']]), np.array([m1.P_SURF]), fluid)[0][0])
        mass_rate = s['flow_gpm']*GPM*rho
        exposure = m1.smooth_exposure(m1.exposure_from_history(circ, depth,
            float(np.interp(s['time_s'], times, circ))), g.md_bit)
        breaks = m1.exposure_breaks(exposure, g.md_bit)
        result = m1.solve_seeded(exposure, breaks, m_dot=mass_rate, T_inj=s['T_in_C'],
            geotherm=trial.T_FORM, geometry=g,
            target_rock_T=float(trial.T_FORM(g.survey.tvd(g.md_bit))), Q_face=0.,
            k_rock=trial.K_ROCK, rhocp_rock=trial.RHOCP_ROCK, friction_heat=True,
            tfa=s['tfa_m2'], film_mult=1., fluid=fluid, verbose=False)
        assert result['success'], case
        expected = plan['expected'][case['case_id']]
        difference = max(abs(float(result['Td'][-1])-expected['bore_0ft_C']),
                         abs(float(result['Tu'][0])-expected['return_C']))
        values = breakdown(s, case, g, fluid, result, mass_rate, plan)
        assert abs(values[0]['model_spp_psi']-expected['spp']/PSI) < 1e-8
        assert difference < 1e-10
        tables[0].append(values[0])
        for dest, rows in zip(tables[1:], values[1:]):
            dest.extend(rows)
        np.savez_compressed(output/'profiles'/f"{case['case_id']}.npz",
                            z=result['z'], Td=result['Td'], Tu=result['Tu'])
        replays.append(dict(case_id=case['case_id'], success=bool(result['success']),
            max_temperature_difference_C=difference,
            pressure_difference_psi=values[0]['model_spp_psi']-expected['spp']/PSI,
            duration_s=time.perf_counter()-start))
        print(case['case_id'], s['run'], case['rheology_case'], 'verified', flush=True)
    names = ('pressure-samples', 'model-pieces', 'bha-components',
             'bha-transitions', 'tool-joints', 'scenario-budgets')
    for name, rows in zip(names, tables):
        whole.csv_out(output/(name+'.csv'), rows)
    whole.csv_out(output/'replays.csv', replays)
    verify_sources(data, output)
    print('Verified', len(replays), 'replays;', len(tables[-1]), 'scenario budgets')


def summaries(output):
    samples = whole.read(output/'pressure-samples.csv')
    budgets = whole.read(output/'scenario-budgets.csv')
    def aggregate(rows, keys):
        groups = defaultdict(list)
        for r in rows:
            groups[tuple(r[k] for k in keys)].append(r)
        answer = []
        for group, data in groups.items():
            row = dict(zip(keys, group))
            row['n'] = len(data)
            numeric = [k for k in data[0] if k.endswith(('_psi', '_fraction'))
                       and all(r.get(k) not in ('', None) for r in data)]
            for k in numeric:
                numbers = [float(r[k]) for r in data]
                row[k+'_mean'] = statistics.mean(numbers)
                row[k+'_min'] = min(numbers)
                row[k+'_max'] = max(numbers)
            answer.append(row)
        return answer
    runs = aggregate(samples, ['rheology_case', 'run'])
    scenario_runs = aggregate(budgets, ['rheology_case', 'run', 'joint_geometry',
        'joint_length_in', 'local_shape', 'surface_case'])
    whole.csv_out(output/'pressure-run-summary.csv', runs)
    whole.csv_out(output/'scenario-run-summary.csv', scenario_runs)
    print('Wrote', len(runs), 'run summaries and', len(scenario_runs), 'scenario/run summaries')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'run', 'summarise'))
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--s2', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.action == 'prepare':
        if args.s2 is None:
            p.error('--s2 is required for prepare')
        prepare(args.data.resolve(), args.s2.resolve(), args.output.resolve())
    elif args.action == 'run':
        run(args.data.resolve(), args.output.resolve())
    else:
        summaries(args.output.resolve())


if __name__ == '__main__':
    main()
