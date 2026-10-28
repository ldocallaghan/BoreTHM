"""Reproduce the declared median-depth component pressure diagnosis.

Uses the unchanged frozen scoreboard inputs and current NC50/EIS scenarios.
No correlation, geometry or sample is selected from a pressure residual.
"""
from collections import defaultdict
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('frozen_scoreboard', ROOT/'validation/scoreboard/scoreboard.py')
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)
m1, hl, a, b, whole, energy = score.m1, score.hl, score.a, score.b, score.whole, score.energy
TERMS = ('body', 'joint_replacement', 'joint_local', 'geometric_local', 'supplied_local', 'tool')


def select(samples):
    """Lower median depth rank, with time and identifier resolving ties."""
    groups = defaultdict(list)
    for sample in samples:
        if sample['spp_psi'] is not None:
            groups[sample['well'], sample['run']].append(sample)
    return [sorted(group, key=lambda s: (s['bit_ft'], s['time'], s['id']))[(len(group)-1)//2]
            for _, group in sorted(groups.items())]


def provenance(sample, plan, segment_index):
    well, run = sample['well'], sample['run']
    if well == '16B' and run in score.TRIAL:
        return 'Original trial aggregate: src/borethm/data/forge16b/run_observations.csv and validate_forge16b.string; EOW Figure 90 HWDP pitch'
    records = plan['components_a' if well == '16A' else 'components_b'][run]
    if segment_index == 0:
        return ('Original regular-pipe dimensions from validate_forge16a.geometry; NOV GPDS50-compatible NC50 scenario; 31.5-ft catalogue pitch'
                if well == '16A' else 'Original regular-pipe dimensions from validate_forge16b_wholewell.geometry; NOV EIS scenario; 2378-ft/75 transferred pitch')
    component = list(reversed(records))[segment_index-1]
    if well == '16A':
        return '; '.join(str(component.get(key, '')) for key in ('report_date', 'member', 'sha256', 'input_note'))
    return '; '.join(str(component.get(key, '')) for key in ('length_source', 'dimension_source', 'input_note'))


def calculate(sample, plan, clocks):
    geometry = score.geometry(sample, plan, 'current')
    form = b.T_FORM if sample['well'] == '16B' else a.formation('216', geometry.survey)[0]
    _, pv, yp = energy.fluid_for(sample, 's1_original' if sample['well'] == '16B' else 'blind_original')
    fluid = score.Mud(sample['density_ppg']*whole.PPG, pv_ref=None if pv is None else pv*.001,
                      yield_point=yp*whole.YP_PA, pv_ref_T=26.7)
    flow = sample['flow_gpm']*whole.GPM
    rho = float(m1.fluid_props(np.array([sample['T_in_C']]), np.array([m1.P_SURF]), fluid)[0][0])
    times, clock, depth = clocks[sample['well']]
    exposure = m1.smooth_exposure(m1.exposure_from_history(clock, depth,
        float(np.interp(sample['time_s'], times, clock))), geometry.md_bit)
    breaks = m1.exposure_breaks(exposure, geometry.md_bit)
    surface = hl.SurfaceLoss.api_case(5)
    result = m1.solve_seeded(exposure, breaks, m_dot=flow*rho, T_inj=sample['T_in_C'], geotherm=form,
        geometry=geometry, target_rock_T=float(form(geometry.survey.tvd(geometry.md_bit))),
        Q_face=sample['motor_heat_psi']*whole.PSI*flow, k_rock=b.K_ROCK, rhocp_rock=b.RHOCP_ROCK,
        friction_heat=True, tfa=sample['tfa_m2'], film_mult=1., fluid=fluid, verbose=False,
        hydraulics_model='v1.6.0', surface=surface)
    if not result['success']:
        raise RuntimeError('Circulation did not converge: '+str(result['sol'].message))
    budget = m1.hydraulics(flow*rho, geometry, result=result, fluid=fluid,
        tfa=sample['tfa_m2'], hydraulics_model='v1.6.0', surface=surface)
    return geometry, result, budget


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidate', type=Path,
                        help='Optional completed scoreboard archive for a repeated-pressure check')
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Choose an empty output directory')
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    plan = score.read_json(score.PLAN)
    ta, ca, da, _ = energy.clock_a(ROOT/'validation/forge16a')
    _, tb, cb, db = whole.clock(ROOT/'validation/forge16b')
    clocks = {'16A': (ta, ca, da), '16B': (tb, cb, db)}
    references = {row['sample']: row for row in map(json.loads,
        (ROOT/'validation/forge16b/s2/results.jsonl').read_text().splitlines())
        if row['rheology_case'] in ('s1_original', 'blind_original')}
    candidate = ({row['sample_id']: row for row in score.read_csv(args.candidate/'circulation.csv')}
                 if args.candidate is not None else {})
    selected = select(plan['samples'])
    inventory = [dict(sample_id=s['id'], well=s['well'], bha=s['run'], time=s['time'],
        bit_depth_ft=s['bit_ft'], flow_gpm=s['flow_gpm'], selection='lower median depth rank; time and identifier ties') for s in selected]
    score.write_csv(args.output/'selected-windows.csv', inventory)
    summaries, pieces = [], []
    for sample, identity in zip(selected, inventory):
        row = dict(identity, success=False)
        try:
            geometry, result, budget = calculate(sample, plan, clocks)
            target = sample['spp_psi']-(sample['raw_differential_psi'] or 0.) if sample['well']=='16A' else sample['spp_psi']
            terms = {f'{side}_{term}_psi': budget['terms'][side][term]/whole.PSI
                     for side in ('bore', 'annulus') for term in TERMS}
            extra = {name+'_psi': budget[name]/whole.PSI for name in ('dp_bit', 'dp_buoyancy', 'dp_surface')}
            total = sum(terms.values())+sum(extra.values())
            baseline = references[sample['id']]
            row.update(success=True, **terms, **extra, spp_psi=budget['spp']/whole.PSI,
                target_psi=target, residual_psi=budget['spp']/whole.PSI-target,
                archived_legacy_string_psi=baseline['dp_string']/whole.PSI,
                current_string_psi=budget['dp_string']/whole.PSI,
                string_increase_psi=(budget['dp_string']-baseline['dp_string'])/whole.PSI,
                legacy_spp_psi=baseline['spp']/whole.PSI,
                sum_residual_psi=total-budget['spp']/whole.PSI,
                budget_flagged=abs(total-budget['spp']/whole.PSI)>1.,
                scoreboard_difference_psi=(budget['spp']/whole.PSI-float(candidate[sample['id']]['spp_psi'])
                                          if sample['id'] in candidate else None),
                energy_flagged=result.get('energy_check', {}).get('flagged', False),
                unknown_proprietary_operating_losses=True, scenario='NC50' if sample['well']=='16A' else 'EIS',
                flags='; '.join(budget['flags']))
            for piece in budget['pieces']:
                i = int(geometry.segment_index((piece['md_top']+piece['md_bottom'])/2))
                segment = geometry.string[i]
                joint = segment.pipe.hydraulic_joint
                details = dict(identity, segment_index=i, component=segment.pipe.name,
                    md_top_m=piece['md_top'], md_bottom_m=piece['md_bottom'],
                    segment_length_m=segment.length, bore_in=2*segment.pipe.r_bore/whole.INCH,
                    outside_in=2*segment.pipe.r_out/whole.INCH,
                    geometry_source=provenance(sample, plan, i),
                    joint_bore_in=joint.bore_diameter/whole.INCH if joint else None,
                    joint_outside_in=joint.outer_diameter/whole.INCH if joint else None,
                    joint_length_m=joint.restriction_length if joint else None,
                    joint_pitch_m=joint.spacing if joint else None,
                    joint_source=joint.source if joint else '',
                    supplied_tool_source=segment.tool_loss.source if segment.tool_loss else '',
                    bore_Re_min=piece['bore_Re'], annulus_Re_min=piece['annulus_Re'])
                details.update({f'{side}_{term}_psi': piece[side+'_terms'][term]/whole.PSI
                    for side in ('bore', 'annulus') for term in TERMS})
                pieces.append(details)
        except Exception as error:
            row['error'] = f'{type(error).__name__}: {error}'
        summaries.append(row)
        score.write_csv(args.output/'pressure-budget.csv', summaries)
        if pieces:
            score.write_csv(args.output/'component-budget.csv', pieces)
        print(json.dumps(dict(well=row['well'], bha=row['bha'], success=row['success'])), flush=True)
    manifest = dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        declaration='f99825f; entry 2 input-selection method declared in 1ee2ac8',
        settings=dict(PV_reference_C=26.7, film_multiplier=1., exposure='cumulative',
                      mud='original blind', scenarios={'16A': 'NC50', '16B': 'EIS'}),
        selection='One pressure-available window per assembly, lower median depth rank with time and identifier ties',
        runtime_s=time.perf_counter()-started, selected=len(selected), failures=sum(not r['success'] for r in summaries),
        sources_sha256={str(p.relative_to(ROOT)):score.sha(p) for p in (Path(__file__),score.PLAN,ROOT/'validation/scoreboard/scoreboard.py')},
        results_sha256={p.name:score.sha(p) for p in sorted(args.output.glob('*.csv'))})
    score.write_json(args.output/'manifest.json', manifest)
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == '__main__':
    main()
