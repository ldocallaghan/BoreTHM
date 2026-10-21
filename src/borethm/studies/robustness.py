"""C5 comparisons for the reviewed C1-C4 programme, without a design search.

python -m borethm.studies.robustness --sites soultz united-downs pannonian
Scoped overrides exist only during each comparison and are restored on exit.
The fluid weights, pipe, flow and exposure rate stay at the reviewed values.
"""
import argparse
from contextlib import ExitStack
from dataclasses import replace
import json
import hashlib
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np

from borethm import drilling_cycle as dc
from borethm import fluids
from borethm import geo_constants as C
from borethm import model1_coupled as m1
from borethm import pressure as pr
from borethm import site_evaluation as se
from borethm import tool_thermal as tt
from borethm import wall_thermal as wt
from borethm import well_geometry as wg

from borethm._paths import repository_root, repository_path, require_path

ROOT = repository_root()
CHECKPOINT = repository_path('results/v1.3.4/checkpoint-1')
IDS = tuple('A' + str(i) for i in range(1, 10))


def fresh_output(output):
    """Keep numerical profiles, discard derived caches between comparisons."""
    out = dict(output)
    out['m1'] = {k: v for k, v in output['m1'].items()
                 if k not in ('trip_columns', 'pause_columns')}
    for key in ('_trip_circulation', 'cycle', 'windows', 'tools', 'components', 'status'):
        out.pop(key, None)
    return out


def finish(site, output, trip_h=None, tools=True):
    out = fresh_output(output)
    scale = 1. if trip_h is None else trip_h / dc.trip_hours(out['z'], dc.forge_timings())
    out['cycle'] = se.site_cycle(site, out, trip_scale=scale)
    out['windows'] = se.common_windows(site, out)
    out['tools'] = recorded_tool_gates(site, out, trip_h=trip_h) if tools else output['tools']
    out['components'] = se.component_statuses(out)
    out['status'] = se.site_status(out['components'])
    return out


def recorded_tool_gates(site, out, **kwargs):
    """Retain the best attempted stage, including a failed schedule search."""
    original = tt.trip_in
    attempts = []
    def recording(*args, **options):
        history, depths = original(*args, **options)
        bottom = args[2] if len(args) > 2 else options['md_bottom']
        stages = args[7] if len(args) > 7 else options.get('stages', ())
        duration = args[8] if len(args) > 8 else options.get('stage_s', 0.)
        if abs(bottom - out['z']) < 1e-6 and len(stages):
            attempts.append(dict(peak_C=history.peak()[0], stage_seconds=duration,
                                 stages=len(stages), spacing_m=float(stages[1] - stages[0])
                                 if len(stages) > 1 else None))
        return history, depths
    with patch.object(tt, 'trip_in', recording):
        tools = se.tool_gates(site, out, **kwargs)
    tools['robustness_search'] = dict(attempts=attempts,
                                      best=min(attempts, key=lambda a: a['peak_C']) if attempts else None)
    return tools


def reviewed_base(key):
    site = replace(se.find_site(key), coupled=True)
    checkpoint = require_path(CHECKPOINT, 'Reviewed programme evidence')
    saved = json.loads((checkpoint / (key + '.json')).read_text())
    p = saved['programme']
    pipe = next(pipe for pipe in se.SITE_PIPES if pipe.name == p['pipe'])
    water_rho = fluids.water().rho_surface
    material = lambda rho: None if rho <= water_rho + 1e-6 else fluids.Mud(rho)
    fluid = material(p['drilling_simulated_rho_surface'])
    trip = material(p['trip_simulated_rho_surface'])
    # Exposure used by the reviewed solve, as opposed to its next ROP estimate.
    rop = p['fluid_passes'][-1]['rop_m_h'] / 3600.
    run = se.circulate(site, site.target(), site.temperature(), pipe,
                       se.mass_flow(p['flow'], fluid),
                       m1.exposure_from_rop(site.target(), rop * 3600.),
                       P_surface=m1.P_SURF, fluid=fluid)
    chosen = dict(pipe=pipe, m_dot=p['flow'], run=run,
                  conflict=p['conflict'], tried=[])
    with patch.object(se, 'choose_circulation', return_value=chosen):
        out = se._evaluate_v12(site, True, True, fluid, rop=rop, light=True)
    out.update(circulation='v1.3.4', apply_trip_fluid=True,
               coverage_corrected=True, trip_fluid=trip, _make_fluid=fluids.Mud,
               fluid_passes=p['fluid_passes'], fluid_converged=p['fluid_converged'])
    out = finish(site, out)
    for name in ('drilling_fluid', 'trip_fluid'):
        for side in ('lo', 'hi'):
            if abs(out['windows'][name][side] - saved['windows'][name][side]) > 2.:
                raise ValueError(f'{key}: reconstructed {name} {side} differs from reviewed checkpoint')
    if out['status'] != saved['status']:
        raise ValueError(f'{key}: reconstructed status differs from reviewed checkpoint')
    return site, out


def metrics(out):
    tools = out['tools']
    connection = tools['connection'].get('schedule') or tools['connection']
    trip = tools['trip_in'].get('schedule') or tools['trip_in']['staged']
    best = tools.get('robustness_search', {}).get('best')
    peaks = dict(drilling=float(tools['drilling']['T']),
                 connection=float(connection['peak']), run_in=float(best['peak_C'] if best else trip['peak']))
    windows = out['windows']
    densities = {name: fluids.water().rho_surface if material is None else material.rho_surface
                 for name, material in (('drilling_fluid', out['fluid']), ('trip_fluid', out['trip_fluid']))}
    return dict(status=out['status'],
        pressure_margin_SG={name: (windows[name]['hi'] - windows[name]['lo']) / 1000.
                            for name in ('drilling_fluid', 'trip_fluid')},
        actual_fluid_slack_SG={name: dict(lower=(densities[name] - windows[name]['lo']) / 1000.,
                                         upper=(windows[name]['hi'] - densities[name]) / 1000.)
                              for name in densities},
        tool_peaks_C=peaks, tool_margin_C=tools['limit'] - max(peaks.values()),
        run_in_margin_C=tools['limit'] - peaks['run_in'],
        practice_run_in_peak_C=tools['trip_in']['staged']['peak'],
        practice_run_in_margin_C=tools['limit'] - tools['trip_in']['staged']['peak'],
        run_in_search=tools.get('robustness_search'),
        windows={name: windows[name] for name in ('drilling_fluid', 'trip_fluid')},
        solver_ok=out['components']['solver']['ok'],
        coating=tools['coating'], pumps=out['components']['pumps'])


def difference(base, changed):
    return dict(pressure_margin_SG={name: changed['pressure_margin_SG'][name] - base['pressure_margin_SG'][name]
                                   for name in base['pressure_margin_SG']},
                actual_fluid_slack_SG={name: {side: changed['actual_fluid_slack_SG'][name][side] -
                                                   base['actual_fluid_slack_SG'][name][side]
                                             for side in ('lower', 'upper')}
                                      for name in base['actual_fluid_slack_SG']},
                tool_margin_C=changed['tool_margin_C'] - base['tool_margin_C'],
                run_in_margin_C=changed['run_in_margin_C'] - base['run_in_margin_C'],
                practice_run_in_margin_C=changed['practice_run_in_margin_C'] - base['practice_run_in_margin_C'])


def direction(delta, tolerance=1e-8):
    return 'towards pass' if delta > tolerance else ('towards failure' if delta < -tolerance else 'unchanged')


def threshold_unresolved(margin, change):
    return abs(change) > 0.2 * abs(margin)


def run_in_bracket(lump, column, md_bottom, speed, T0, h_static_out, h_static_in,
                   stages=(), stage_s=0., circulating=None, dt=30.,
                   turnover=None, evolving=None):
    """Existing two-node equations with C5's warm-stage or elapsed-time bracket.

    Store the complete stage history so a peak before cold coolant arrives
    cannot disappear when the stage ends. Forced films remain as in the base.
    """
    depth, times, steel, fluid, labels = [0.], [0.], [T0], [T0], ['']
    md, elapsed, Ts, Tf = 0., 0., T0, T0
    temperature = lambda d, t: float(column(d) if evolving is None else evolving(d, t))

    def append(hist, at_depth, label):
        nonlocal elapsed, Ts, Tf
        times.extend(elapsed + hist.t[1:])
        steel.extend(hist.T_s[1:]); fluid.extend(hist.T_f[1:])
        depth.extend([at_depth] * (len(hist.t) - 1)); labels.extend([label] * (len(hist.t) - 1))
        elapsed += float(hist.t[-1])
        Ts, Tf = float(hist.T_s[-1]), float(hist.T_f[-1])

    for target in sorted(d for d in stages if 0. < d < md_bottom) + [md_bottom]:
        while md < target - 1e-9:
            step = min(speed * dt, target - md)
            seconds = step / speed
            md += step
            seg = tt.Segment(seconds, temperature(md, elapsed + seconds), h_static_out, h_static_in)
            append(tt.run(lump, [seg], Ts, Tf, dt=seconds), md, 'running in')
        if target < md_bottom and stage_s > 0 and circulating is not None:
            cold, h_in, h_out = circulating(md)
            delay = min(stage_s, float(turnover(md))) if turnover is not None else 0.
            if delay > 0.:
                warm = temperature(md, elapsed)
                seg = tt.Segment(delay, warm, h_out, h_in, T_flow=warm)
                append(tt.run(lump, [seg], Ts, Tf), md, 'warm stage')
            if stage_s > delay:
                seg = tt.Segment(stage_s - delay, cold, h_out, h_in, T_flow=cold)
                append(tt.run(lump, [seg], Ts, Tf), md, 'cold stage')
    return tt.History(np.asarray(times), np.asarray(steel), np.asarray(fluid), labels), np.asarray(depth)


def string_turnover(run, md):
    """Internal string volume divided by inlet volume flow, at stage depth."""
    pipe = run['geometry'].string[0].pipe
    g = wg.WellGeometry(wg.wu2025_string(md, pipe),
                        [wg.open_hole(0., md, 0.22)])
    volume = sum(seg.length * np.pi * seg.pipe.r_bore ** 2 for seg in g.string)
    rho_in = float(np.ravel(m1.fluid_props([run['Td'][0]], [run['P_surface']], run.get('fluid'))[0])[0])
    return volume * rho_in / run['m_dot']


def time_column(site, out, max_elapsed_s):
    """The existing static nodes, sampled once through the extended trip.

    C5 A5 advances the open-hole nodes. The cased column retains the base
    approximation, whose limitations remain explicit in the report.
    """
    run, z = out['m1'], out['z']
    g = run['geometry']
    shoe = max(h.md_top for h in g.hole)
    rop = out['drill']['ROP'] * 3600.
    trip_s = out['cycle']['trip_h'] * 3600.
    depths = np.linspace(shoe, z, int(np.ceil((z - shoe) / se.TRIP_COLUMN_DZ)) + 1)
    clocks = np.linspace(trip_s, trip_s + max_elapsed_s, 501)
    table = []
    for d in depths:
        rock = float(site.temperature()(d))
        bc = se._bottom_conditions(run, d)
        capacity, film = se._static_node(rock, d, bc['r_wall'], 0., out['trip_fluid'])
        pre = ((z - d) / rop + bc['bu_h']) * 3600.
        result = wt.run([wt.State('circulating', pre, T_fluid=bc['Tu'], h=bc['h']),
                         wt.State('static', trip_s + max_elapsed_s, h=film, C=capacity)],
                        rock, bc['r_wall'], site.k_rock, C.RHO_ROCK * C.CP_ROCK, n=120, growth=1.2)
        after = result.t > pre
        table.append(np.interp(clocks, np.r_[0., result.t[after] - pre],
                               np.r_[bc['Tu'], result.T_node[after]]))
    table = np.asarray(table)
    frozen_depths, frozen_T = se.trip_temperatures(site, out, run, out['cycle']['trip_h'])

    def column(md, elapsed_s):
        if md < shoe:
            return float(np.interp(g.survey.tvd(md), frozen_depths, frozen_T))
        profile = np.array([np.interp(trip_s + elapsed_s, clocks, row) for row in table])
        return float(np.interp(md, depths, profile))
    return column


def numerical_overrides(radial=False, temporal=False, window=False):
    stack = ExitStack()
    if radial:
        original = wt.run
        def refined(history, T_rock, a, k, rhocp, n=200, **kwargs):
            old_n = n
            n = 2 * (n - 1) + 1
            if kwargs.get('T0') is not None and len(kwargs['T0']) != n:
                radius = kwargs.get('r_max') or wt.r_max_for(a, k / rhocp, sum(s.duration for s in history))
                old_r = wt.Grid(a, radius, old_n).build()[0]
                new_r = wt.Grid(a, radius, n).build()[0]
                kwargs['T0'] = np.interp(new_r, old_r, kwargs['T0'])
            return original(history, T_rock, a, k, rhocp, n=n, **kwargs)
        stack.enter_context(patch.object(wt, 'run', refined))
    if temporal:
        original_steps, original_tool, original_trip = wt.time_steps, tt.run, tt.trip_in
        def half_steps(*args, **kwargs):
            steps = original_steps(*args, **kwargs)
            return [half for step in steps for half in (step / 2., step / 2.)]
        def half_tool(lump, segments, Ts, Tf, dt=10.):
            # A run-in step was already halved by half_trip.
            chosen = dt if len(segments) == 1 and dt == segments[0].duration else dt / 2.
            return original_tool(lump, segments, Ts, Tf, dt=chosen)
        def half_trip(*args, dt=30., **kwargs):
            return original_trip(*args, dt=dt / 2., **kwargs)
        stack.enter_context(patch.object(wt, 'time_steps', half_steps))
        stack.enter_context(patch.object(tt, 'run', half_tool))
        stack.enter_context(patch.object(tt, 'trip_in', half_trip))
    if window:
        stack.enter_context(patch.object(se, 'WINDOW_DZ', se.WINDOW_DZ / 2.))
    return stack


def shallow_comparison(site, base):
    """A7 changes the local ceiling at a binding shallow depth only."""
    out = dict(base)
    out['windows'] = {**base['windows'], **{name: dict(base['windows'][name])
                       for name in ('drilling_fluid', 'trip_fluid')}}
    details = []
    for name in ('drilling_fluid', 'trip_fluid'):
        window = out['windows'][name]
        for side in ('lo', 'hi'):
            point = window[side + '_by']
            d = point['md']
            if d is None or d >= out['z'] - 1e-6:
                continue
            if side != 'hi':
                raise ValueError('A7 requires a shallow lower-bound wall-history comparison')
            pipe = base['circ']['pipe']
            holes = [replace(h, md_bottom=min(h.md_bottom, d))
                     for h in base['m1']['geometry'].hole if h.md_top < d]
            geometry = wg.WellGeometry(wg.wu2025_string(d, pipe), holes,
                                        base['m1']['geometry'].survey)
            with patch.object(se, 'site_well', return_value=geometry):
                run = se.circulate(site, d, site.temperature(), pipe, base['m1']['m_dot'],
                                   m1.exposure_from_rop(d, base['circ']['rop'] * 3600.),
                                   P_surface=base['m1']['P_surface'], fluid=base['fluid'])
            if not run['success']:
                raise ValueError('A7 partial-depth circulation did not converge')
            rock = float(site.temperature()(d))
            _, cases = se.stability_inputs(site, d, rock, T_wall=rock,
                                           ecd_SG=pr.TRIP_ALLOWANCE_SG if name == 'trip_fluid' else 0.)
            case = next(c for c in cases if c['label'] == point['case'])
            ceiling = case['window']['Pw_hi']
            if name == 'drilling_fluid':
                ceiling -= pr.annulus_friction(run, d)
            bp = run['backpressure']
            rho = pr.surface_density_for((ceiling - bp) / pr.sg_per_pa(d), d,
                                          pr.circulating_temperatures(run), fluids.Mud, bp)
            if rho is None:
                rho = fluids.water().rho_surface
            details.append(dict(window=name, bound=side, depth_m=d,
                                old_surface_SG=window[side] / 1000., new_surface_SG=rho / 1000.,
                                bit_C=float(run['T_bottom_delivered']), solver_ok=bool(run['success'])))
            window[side] = rho
            window['open'] = window['lo'] <= window['hi']
            window['fluid'] = window['lo'] if window['open'] else None
    out['components'] = se.component_statuses(out)
    out['status'] = se.site_status(out['components'])
    return out, details


def comparisons(site, base, only=IDS):
    """Yield each completed comparison promptly for resumable evidence."""
    base_metrics = metrics(base)
    def row(identifier, variants, details=None):
        results = {}
        for label, out in variants.items():
            m = metrics(out)
            results[label] = dict(metrics=m, change=difference(base_metrics, m))
        return dict(id=identifier, variants=results, details=details or {},
                    decision_relevant=any(v['metrics']['status']['label'] in ('GO', 'CONDITIONAL')
                                          for v in results.values()))

    if 'A1' in only:
        run = base['m1']
        passes = []
        for _ in range(2):
            tvd, temp = pr.circulating_temperatures(run)
            pressure = pr.column(tvd, temp, base['fluid'], run['backpressure']) + pr.P_ATM
            with patch.object(m1, 'P_of_z', lambda depth, P_surface=m1.P_SURF:
                              np.interp(depth, tvd, pressure) + P_surface - run['P_surface']):
                run = se.circulate(site, base['z'], site.temperature(), base['circ']['pipe'],
                    base['m1']['m_dot'], m1.exposure_from_rop(base['z'], base['circ']['rop'] * 3600.),
                    P_surface=base['m1']['P_surface'], fluid=base['fluid'])
            passes.append(dict(bit_C=float(run['T_bottom_delivered']), success=bool(run['success']),
                               bottom_property_pressure_MPa=float(pressure[-1] / 1e6)))
        changed = fresh_output(base); changed['m1'] = run
        changed['circ'] = {**base['circ'], 'hyd': run['hyd'], 'bhct': float(run['T_bottom_delivered'])}
        # All later property evaluations for this bracket use its final profile.
        tvd, temp = pr.circulating_temperatures(run)
        pressure = pr.column(tvd, temp, base['fluid'], run['backpressure']) + pr.P_ATM
        with patch.object(m1, 'P_of_z', lambda d, P_surface=m1.P_SURF: np.interp(d, tvd, pressure)):
            changed = finish(site, changed)
        yield row('A1', {'budget profile, one update': changed}, {'passes': passes})
    if 'A2' in only:
        heat = base['drill']['Q_face']
        with patch.object(se, 'Q_FACE_SITE', heat):
            run = se.circulate(site, base['z'], site.temperature(), base['circ']['pipe'],
                base['m1']['m_dot'], m1.exposure_from_rop(base['z'], base['circ']['rop'] * 3600.),
                P_surface=base['m1']['P_surface'], fluid=base['fluid'])
            changed = fresh_output(base); changed['m1'] = run
            changed['circ'] = {**base['circ'], 'hyd': run['hyd'], 'bhct': float(run['T_bottom_delivered'])}
            changed = finish(site, changed)
        yield row('A2', {'Model 3 face load': changed}, {'face_load_W': float(heat), 'base_face_load_W': 30000.})
    if 'A3' in only:
        trip_run = se._trip_circulation(site, base, base['m1'])
        turnover = lambda md: string_turnover(trip_run, md)
        def delayed(*args, **kwargs):
            return run_in_bracket(*args, turnover=turnover, **kwargs)
        with patch.object(tt, 'trip_in', delayed):
            changed = finish(site, base)
        yield row('A3', {'instant, optimistic': base, 'one turnover, adverse': changed},
                  {'bottom_turnover_min': turnover(base['z']) / 60.,
                   'stage_minutes': base['tools']['trip_in']['staged']['minutes'],
                   'forced_films': 'held at the base steady-circulation values'})
    if 'A4' in only:
        trip = base['tools']['trip_in']
        schedule = trip['schedule'] or trip['staged']
        shoe = max(h.md_top for h in base['m1']['geometry'].hole)
        stages = len(np.arange(shoe + schedule['spacing_m'], base['z'], schedule['spacing_m']))
        extra = stages * schedule['minutes'] / 60.
        changed = finish(site, base, trip_h=base['cycle']['trip_h'] + extra)
        yield row('A4', {'staging time added': changed}, {'added_hours': extra, 'stages': stages,
                  'schedule_basis': 'selected schedule' if trip['schedule'] else 'FORGE practice; no passing schedule found'})
    if 'A5' in only:
        timing = dc.forge_timings()
        # Covers every schedule the existing search tries, including its longest stages.
        max_elapsed = base['z'] / (timing.trip_in_ft_h * dc.FT) * 3600.
        max_elapsed += (base['z'] / (timing.stand_ft * dc.FT) + 1) * timing.stage_minutes * 60. * max(se.STAGE_DURATION_FACTORS)
        evolving = time_column(site, base, max_elapsed)
        def advancing(*args, **kwargs):
            return run_in_bracket(*args, evolving=evolving, **kwargs)
        with patch.object(tt, 'trip_in', advancing):
            changed = finish(site, base)
        yield row('A5', {'column advances during run-in': changed}, {'maximum_elapsed_hours': max_elapsed / 3600.,
                  'cased_column': 'held at the base profile, as in the existing static-node model'})
    if 'A6' in only:
        changed = fresh_output(base); changed['trip_fluid'] = base['fluid']
        changed = finish(site, changed)
        yield row('A6', {'uniform trip fluid': base, 'drilling fluid throughout': changed})
    if 'A7' in only:
        changed, details = shallow_comparison(site, base)
        yield row('A7', {'partial-depth binding ceiling' if details else 'not binding': changed},
                  {'binding_comparisons': details, 'scope': 'local shallow binding ceilings; deeper constraints retained'})
    if 'A8' in only:
        variants = {}
        for allowance in (0., 0.04):
            with patch.object(pr, 'TRIP_ALLOWANCE_SG', allowance):
                variants[f'{allowance:.2f} SG per bound'] = finish(site, base, tools=False)
        yield row('A8', variants)
    if 'A9' in only:
        variants = {}
        for label, switches in [('radial spacing halved', (True, False, False)),
                                ('timesteps halved', (False, True, False)),
                                ('window spacing halved', (False, False, True)),
                                ('all three halved', (True, True, True))]:
            with numerical_overrides(*switches):
                variants[label] = finish(site, base)
        result = row('A9', variants)
        result['details']['unresolved_thresholds'] = {label: dict(
            pressure={name: threshold_unresolved(base_metrics['pressure_margin_SG'][name],
                                                 value['change']['pressure_margin_SG'][name])
                      for name in base_metrics['pressure_margin_SG']},
            tool=threshold_unresolved(base_metrics['tool_margin_C'], value['change']['tool_margin_C']),
            run_in=threshold_unresolved(base_metrics['run_in_margin_C'], value['change']['run_in_margin_C']),
            FORGE_practice=threshold_unresolved(base_metrics['practice_run_in_margin_C'],
                                                value['change']['practice_run_in_margin_C']))
            for label, value in result['variants'].items()}
        yield result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sites', nargs='+', default=['soultz', 'united-downs', 'pannonian'])
    parser.add_argument('--only', nargs='+', choices=IDS)
    parser.add_argument('--output', type=Path, default=repository_path('results/robustness'))
    parser.add_argument('--legacy-threshold', action='store_true',
                        help='also check the original v1.3.3 Pannonian 0.041 C tool threshold')
    args = parser.parse_args()
    args.output = require_path(args.output, 'Robustness output')
    require_path(CHECKPOINT, 'Reviewed programme evidence')
    args.output.mkdir(parents=True, exist_ok=True)
    for key in args.sites:
        destination = args.output / (key + '.json')
        ledger = json.loads(destination.read_text()) if destination.exists() else {}
        print('Reconstructing reviewed programme:', key, flush=True)
        site, base = reviewed_base(key)
        ledger.update(site=key, base=metrics(base), versions=se.versions(),
                      source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      programme=json.loads((CHECKPOINT / (key + '.json')).read_text())['programme'])
        done = {item['id']: item for item in ledger.get('comparisons', [])}
        requested = args.only or (['A9'] if key == 'pannonian' else IDS)
        for identifier in requested:
            print('Comparison:', key, identifier, flush=True)
            started = time.perf_counter()
            item = next(comparisons(site, base, [identifier]))
            item['elapsed_seconds'] = time.perf_counter() - started
            done[identifier] = item
            ledger['comparisons'] = [done[k] for k in IDS if k in done]
            destination.write_text(json.dumps(se._jsonable(ledger), indent=2) + '\n')
            print(json.dumps(dict(site=key, id=identifier, variants={name: dict(
                status=value['metrics']['status']['label'], change=value['change'])
                for name, value in item['variants'].items()})), flush=True)
    if args.legacy_threshold:
        legacy_pannonian_threshold(args.output)


def legacy_pannonian_threshold(destination):
    """Apply D5 to the historical threshold as well as the corrected programme."""
    site = replace(se.find_site('pannonian'), coupled=True)
    print('Evaluating original Pannonian threshold', flush=True)
    base = se.evaluate(site, circulation='v1.3.3')
    peak = base['tools']['trip_in']['staged']['peak']
    margin = C.BHA_SURVIVAL_TEMP - peak
    pinned = json.loads((require_path(ROOT, 'Historical regression goldens') / 'tests/golden/v133_site_table.json').read_text())[site.name]['tools']['running_in']
    if abs(peak - pinned) > 0.001:
        raise ValueError('original threshold did not reproduce to 0.001 C')
    record = dict(site='pannonian', evaluation='v1.3.3 historical threshold',
                  base_peak_C=float(peak), base_margin_C=float(margin), variants={},
                  versions=se.versions(), source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    for label, switches in [('radial spacing halved', (True, False, False)),
                            ('timesteps halved', (False, True, False)),
                            ('radial spacing and timesteps halved', (True, True, False))]:
        with numerical_overrides(*switches):
            tools = se.tool_gates(site, fresh_output(base))
        changed = float(tools['trip_in']['staged']['peak'])
        record['variants'][label] = dict(peak_C=changed, change_in_margin_C=peak - changed,
                                        unresolved=threshold_unresolved(margin, peak - changed),
                                        practice_tool_passes=changed < C.BHA_SURVIVAL_TEMP)
        (destination / 'pannonian-v133-threshold.json').write_text(json.dumps(record, indent=2) + '\n')
        print('Historical threshold:', label, record['variants'][label], flush=True)
    return record


if __name__ == '__main__':
    try:
        main()
    except ValueError as error:
        raise SystemExit(str(error)) from None
