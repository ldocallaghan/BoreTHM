"""Model-only pressure budgets on the registered 58-32 input windows.

Only the prepared input projection and the declared transferred formation
profile are read. No raw archive, target channel or scoreboard is opened.
Every variant starts from the usual independent solve_seeded sequence.
Event budget means use identical successful windows in all calculations;
median totals are retained separately from the additive mean budget.
"""
import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import platform
import statistics
import time

import numpy as np
import scipy

from borethm import model1_coupled as m1, well_geometry as wg
from borethm.fluids import Mud, HerschelBulkley
from borethm.hydraulic_losses import HydraulicJoint, SurfaceLoss

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FT, INCH, GPM, PPG, YP_PA, PSI = .3048, .0254, 6.30902e-5, 119.8264273, .4788025898, 6894.757
TERMS = ('body', 'joint_replacement', 'joint_local', 'geometric_local', 'supplied_local', 'tool')
PARTS = ('surface_psi', 'pipe_bore_psi', 'bha_bore_psi', 'bit_nozzles_psi', 'annulus_psi', 'buoyancy_psi')


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_protocol_sha(settings):
    """Allow only the dated access-status update in the frozen protocol."""
    frozen = dict(settings)
    frozen['window_pressure_targets_read'] = False
    frozen.pop('window_pressure_target_access_date', None)
    return hashlib.sha256((json.dumps(frozen, indent=2)+'\n').encode('utf-8')).hexdigest()


def write(path, rows):
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, keys, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def epoch(stamp):
    return datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc).timestamp()


def pipe(name, od, bore, source, joint=None):
    return wg.PipeType(name, (wg.Layer(bore*INCH/2, od*INCH/2, wg.K_STEEL),),
                       source=source, hydraulic_joint=joint)


def geometry(sample, components, settings, scenario, survey, original=False):
    """Keep the bottom of the assembly and truncate its top at shallow depth."""
    depth = float(sample['bit_depth_ft'])*FT
    common = settings['common']
    bottom_up = []
    remaining = depth
    for row in components[1:]:  # bit is the nozzle boundary
        length = min(float(row['total_length_ft'])*FT, remaining)
        if length <= 1e-9:
            continue
        item = int(row['item'])
        joint = None
        if row['component'] == 'HWDP' and not original:
            joint = HydraulicJoint(settings['joint_OD_in']*INCH,
                settings['HWDP_joint_ID_in']*INCH, common['joint_restriction_in']*INCH,
                settings['HWDP_joint_pitch_ft']*FT, source='Recorded body bore retained; transferred joint envelope')
        part = pipe(f"BHA-{item:02d}-{row['component']}", float(row['reported_OD_in']),
                    float(row['reported_ID_in']), row['ID_source'], joint)
        bottom_up.append(wg.StringSegment(length, part))
        remaining -= length
    if remaining > 1e-9:
        joint = None if original else HydraulicJoint(settings['joint_OD_in']*INCH,
            scenario['joint_ID_in']*INCH, common['joint_restriction_in']*INCH,
            settings['pipe_joint_pitch_ft']*FT, source='Primary catalogue scenario; installed machining unknown')
        part = pipe('ordinary-pipe', scenario['pipe_OD_in'], scenario['pipe_ID_in'],
                    'Registered primary pipe scenario', joint)
        bottom_up.append(wg.StringSegment(remaining, part))
    shoe = min(common['casing_shoe_ft']*FT, depth)
    hole = [wg.cased(0., shoe, common['casing_ID_in']*INCH,
                    common['casing_OD_in']*INCH, common['cased_original_hole_in']*INCH)]
    if depth > shoe:
        hole.append(wg.open_hole(shoe, depth, common['open_hole_in']*INCH))
    return wg.WellGeometry(list(reversed(bottom_up)), hole, survey)


def calculate(sample, variant, settings, components, survey, history, formation,
              initial_profile=None, return_solution=False, scenario='primary'):
    config = settings['models'][variant]
    common = settings['common']
    original = variant == 'original'
    g = geometry(sample, components, settings, settings['scenarios'][scenario], survey, original)
    fluid = Mud(float(sample['density_ppg'])*PPG, pv_ref=float(sample['pv_cP'])*.001,
                yield_point=float(sample['yp_lbf_100ft2'])*YP_PA, pv_ref_T=common['pv_ref_T_C'])
    if not original:
        fluid.rheology = HerschelBulkley.from_report(float(sample['pv_cP']),
                                                    float(sample['yp_lbf_100ft2']), 0.)
    tin = float(sample['inlet_C'])
    rho = float(m1.fluid_props(np.array([tin]), np.array([m1.P_SURF]), fluid)[0][0])
    mass_rate = float(sample['flow_gpm'])*GPM*rho
    times, clock, depth = history
    # Restrict history to data available by the window centre.
    keep = times <= epoch(sample['time'])
    exposure = m1.smooth_exposure(m1.exposure_from_history(clock[keep], depth[keep],
        float(np.interp(epoch(sample['time']), times, clock))), g.md_bit)
    tfa = common['jet_count']*np.pi*(common['jet_diameter_32nds']/32*INCH)**2/4
    surface = None if config['surface_case'] is None else SurfaceLoss.api_case(config['surface_case'])
    arguments = dict(
        m_dot=mass_rate, T_inj=tin, geotherm=formation, geometry=g,
        target_rock_T=float(formation(g.survey.tvd(g.md_bit))), Q_face=0.,
        k_rock=common['k_rock_W_mK'], rhocp_rock=common['rhocp_rock_J_m3K'],
        friction_heat=True, tfa=tfa, film_mult=common['film_multiplier'], fluid=fluid,
        verbose=False, hydraulics_model=config['hydraulics_model'], surface=surface,
        rock_response=config['rock_response'], annulus_model=config['annulus_model'],
        friction=config['friction'], roughness=config['roughness_m'])
    breaks = m1.exposure_breaks(exposure, g.md_bit)
    if initial_profile is None:
        result = m1.solve_seeded(exposure, breaks, **arguments)
    else:
        result = m1.solve(exposure=exposure, breaks=breaks, init=initial_profile, **arguments)
    identity = dict(window_id=sample['window_id'], event_id=sample['event_id'], bha_id=sample['bha_id'],
                    variant=variant, bit_depth_ft=float(sample['bit_depth_ft']),
                    flow_gpm=float(sample['flow_gpm']))
    row = dict(identity, success=bool(result['success']), solver_status=int(result['sol'].status),
               solver_message=str(result['sol'].message))
    if not result['success']:
        return (row, [], result) if return_solution else (row, [])
    budget = m1.hydraulics(mass_rate, g, result=result, tfa=tfa, fluid=fluid)
    component_loss = defaultdict(float)
    term_loss = defaultdict(lambda: defaultdict(float))
    for piece in budget['pieces']:
        segment = g.string[int(g.segment_index((piece['md_top']+piece['md_bottom'])/2))]
        component_loss[segment.pipe.name] += piece['dp_bore']/PSI
        if not original:
            for term in TERMS:
                term_loss[segment.pipe.name][term] += piece['bore_terms'][term]/PSI
    parts = dict(surface_psi=budget.get('dp_surface', 0.)/PSI,
        pipe_bore_psi=component_loss['ordinary-pipe'],
        bha_bore_psi=sum(v for k, v in component_loss.items() if k != 'ordinary-pipe'),
        bit_nozzles_psi=budget['dp_bit']/PSI, annulus_psi=budget['dp_annulus']/PSI,
        buoyancy_psi=budget['dp_buoyancy']/PSI)
    residual = sum(parts.values())-budget['spp']/PSI
    row.update(**parts, spp_psi=budget['spp']/PSI, sum_residual_psi=residual,
        budget_flagged=abs(residual)>1., bit_C=float(result['Td'][-1]), return_C=float(result['Tu'][0]),
        energy_residual_W=result.get('energy_check', {}).get('residual_W'),
        energy_flagged=result.get('energy_check', {}).get('flagged', False),
        flags='; '.join(budget.get('flags', [])))
    pieces = []
    for component in components:
        item = int(component['item'])
        key = f"BHA-{item:02d}-{component['component']}"
        present = next((s for s in g.string if s.pipe.name == key), None)
        terms = {term+'_psi': (component_loss[key] if term == 'body' else 0.)
                 if original else term_loss[key][term] for term in TERMS}
        pieces.append(dict(identity, item=item, component=component['component'],
            modelled_length_ft=0. if present is None else present.length/FT,
            reported_bore_in=component['reported_ID_in'], source=component['ID_source'],
            bore_loss_psi=component_loss[key], **terms))
    return (row, pieces, result) if return_solution else (row, pieces)


def aggregate(rows, pieces, samples, variants):
    budgets, components = [], []
    for event in dict.fromkeys(s['event_id'] for s in samples):
        planned = [s['window_id'] for s in samples if s['event_id'] == event]
        success = {v: {r['window_id'] for r in rows if r['event_id'] == event
                      and r['variant'] == v and r['success']} for v in variants}
        paired = set.intersection(*success.values())
        for variant in variants:
            group = [r for r in rows if r['event_id'] == event and r['variant'] == variant
                     and r['window_id'] in paired]
            row = dict(event_id=event, bha_id='2', variant=variant, planned_windows=len(planned),
                       converged_windows=len(success[variant]), paired_windows=len(paired))
            if group:
                row.update({k: statistics.fmean(r[k] for r in group) for k in (*PARTS, 'spp_psi')})
                row['median_spp_psi'] = statistics.median(r['spp_psi'] for r in group)
                row['sum_residual_psi'] = sum(row[k] for k in PARTS)-row['spp_psi']
                row['budget_flagged'] = abs(row['sum_residual_psi'])>1.
                row['paired_ids'] = ';'.join(w for w in planned if w in paired)
            budgets.append(row)
            for item in range(1, 18):
                chosen = [r for r in pieces if r['event_id'] == event and r['variant'] == variant
                          and r['window_id'] in paired and r['item'] == item]
                identity = dict(event_id=event, bha_id='2', variant=variant, item=item,
                                paired_windows=len(paired))
                if chosen:
                    identity.update(component=chosen[0]['component'],
                        **{k: statistics.fmean(r[k] for r in chosen) for k in
                           ('bore_loss_psi', 'modelled_length_ft', *(t+'_psi' for t in TERMS))})
                components.append(identity)
    return budgets, components


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scenario', choices=('primary', 'heavy_pipe', 'wide_joint', 'larger_pipe'),
                        default='primary', help='Registered equipment scenario')
    parser.add_argument('--models', nargs='+', choices=('original','working_entry10','secondary_entry8'),
                        default=['original','working_entry10','secondary_entry8'],
                        help='Registered calculations; the original uses the D6/D7 numerical treatment')
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Choose an empty output directory')
    started = time.perf_counter()
    settings = json.loads((HERE/'protocol.json').read_text(encoding='utf-8'))
    manifest = json.loads((HERE/'inputs/manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['source_sha256'].items():
        actual = frozen_protocol_sha(settings) if name == 'protocol.json' else sha(HERE/name)
        if actual != expected:
            raise ValueError('Registered source has changed: '+name)
    for name, expected in manifest['output_sha256'].items():
        if sha(HERE/'inputs'/name) != expected:
            raise ValueError('Registered input has changed: '+name)
    for name, expected in settings['source_model_sha256'].items():
        if sha(ROOT/'src/borethm'/name) != expected:
            raise ValueError('Registered model has changed: '+name)
    samples = read(HERE/'inputs/windows.csv')
    components = read(HERE/'inputs/components.csv')
    stations = read(HERE.parent/'survey.csv')
    md = np.array([float(r['MD_ft']) for r in stations])*FT
    tvd = np.array([float(r['TVD_ft']) for r in stations])*FT
    md = np.r_[md, md[-1]+12000*FT]
    tvd = np.r_[tvd, tvd[-1]+12000*FT*np.cos(np.deg2rad(float(stations[-1]['inclination_deg']))) ]
    survey = wg.Survey(md, tvd)
    source_form = ROOT/'validation/forge16a/formation_temperature_216day.csv'
    form = read(source_form)
    fz = np.array([float(r['tvd_ft'])*FT for r in form])
    ft = np.array([float(r['temp_C']) for r in form])
    formation = lambda z: np.interp(z, fz, ft)
    with gzip.open(HERE/'inputs/circulation-clock.csv.gz', 'rt', encoding='utf-8') as stream:
        clock = list(csv.DictReader(stream))
    history = (np.array([epoch(r['time']) for r in clock]),
               np.array([float(r['cumulative_circulating_s']) for r in clock]),
               np.array([float(r['monotone_hole_depth_ft'])*FT for r in clock]))
    args.output.mkdir(parents=True, exist_ok=True)
    rows, pieces, initial_checks = [], [], []
    variants = tuple(args.models or settings['models'])
    for i, sample in enumerate(samples, 1):
        solutions, values = {}, {}
        for variant in variants:
            print(f'{i}/{len(samples)} {sample["window_id"]} {variant}: starting', flush=True)
            try:
                row, parts, result = calculate(sample, variant, settings, components, survey,
                    history, formation, return_solution=True, scenario=args.scenario)
                solutions[variant] = result
            except Exception as error:
                row, parts = dict(window_id=sample['window_id'], event_id=sample['event_id'],
                    bha_id=sample['bha_id'], variant=variant, success=False,
                    solver_message=f'{type(error).__name__}: {error}'), []
            rows.append(row)
            values[variant] = row
            pieces.extend(parts)
            write(args.output/'window-budget.csv', rows)
            write(args.output/'component-budget.csv', pieces)
            print(f'{variant}: success={row["success"]}, '
                  f'{time.perf_counter()-started:.1f} s', flush=True)
        if 'original' in variants and 'working_entry10' in variants:
            check = dict(window_id=sample['window_id'], event_id=sample['event_id'],
                         seeded_success=values['original']['success'], passed=False)
            working = solutions.get('working_entry10')
            if working is not None and working['success']:
                try:
                    warm, _ = calculate(sample, 'original', settings, components, survey,
                        history, formation, initial_profile=working, scenario=args.scenario)
                    check.update(initialised_success=warm['success'],
                        solver_status=warm['solver_status'], solver_message=warm['solver_message'])
                    if check['seeded_success'] and warm['success']:
                        for key in ('bit_C', 'return_C', 'spp_psi'):
                            check[key+'_difference'] = warm[key]-values['original'][key]
                        limits = settings['starting_profile_check']
                        check['passed'] = (abs(check['bit_C_difference']) <= limits['temperature_tolerance_C']
                            and abs(check['return_C_difference']) <= limits['temperature_tolerance_C']
                            and abs(check['spp_psi_difference']) <= limits['pressure_tolerance_psi'])
                except Exception as error:
                    check['solver_message'] = f'{type(error).__name__}: {error}'
            else:
                check['solver_message'] = 'Working profile unavailable'
            initial_checks.append(check)
            write(args.output/'starting-profile.csv', initial_checks)
        write(args.output/'window-budget.csv', rows)
        write(args.output/'component-budget.csv', pieces)
        print(f'{i}/{len(samples)} windows, {len(rows)} calculations, '
              f'{sum(not r["success"] for r in rows)} failures, '
              f'{time.perf_counter()-started:.1f} s', flush=True)
    budgets, event_parts = aggregate(rows, pieces, samples, variants)
    write(args.output/'event-budget.csv', budgets)
    write(args.output/'event-components.csv', event_parts)
    sources = [Path(__file__), HERE/'protocol.json', HERE/'protocol.md', HERE/'inputs/manifest.json',
               HERE.parent/'survey.csv', source_form]
    sources += [HERE/'inputs'/n for n in manifest['output_sha256']]
    summary = dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
        runtime_s=time.perf_counter()-started, windows=len(samples), events=len(budgets)//len(variants),
        calculations=len(rows), variants=list(variants), scenario=args.scenario,
        failures=[{k:r.get(k) for k in ('window_id','variant','solver_status','solver_message')}
                  for r in rows if not r['success']],
        energy_flags=sum(bool(r.get('energy_flagged')) for r in rows),
        budget_flags=sum(bool(r.get('budget_flagged')) for r in rows),
        original_reference='v1.5.0 equations with D6 occupancy blend and D7 physical-boundary mesh clipping',
        starting_profile_checks=len(initial_checks),
        starting_profile_failures=[r['window_id'] for r in initial_checks if not r['passed']],
        starting_profile_max_difference={key: max((abs(r.get(key+'_difference', 0.))
            for r in initial_checks), default=None) for key in ('bit_C','return_C','spp_psi')},
        targets_read=False, prior_report_pressure_exposure=True,
        source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sources},
        model_sha256=settings['source_model_sha256'],
        output_sha256={p.name:sha(p) for p in sorted(args.output.glob('*.csv'))})
    (args.output/'manifest.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({k:v for k,v in summary.items() if 'sha256' not in k},indent=2),flush=True)


if __name__ == '__main__':
    main()
