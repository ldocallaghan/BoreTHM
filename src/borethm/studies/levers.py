"""C6: one lever at a time from the reviewed v1.3.4 programme.

python src/levers.py --sites soultz united-downs --levers L1 L2 L3 L4 L5 L6 L7 L8
Identical completed trials can be resumed. Every new trial reruns the coupled
fluid iteration, whole-hole windows, thermal gates and pump/rig checks.
"""
import argparse
from contextlib import ExitStack
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np
from scipy.optimize import brentq

from borethm import fluids
from borethm import model1_coupled as m1
from borethm import pressure as pr
from borethm.studies import robustness as rb
from borethm import site_evaluation as se
from borethm import well_geometry as wg

from borethm._paths import repository_path, require_path

ROOT = rb.ROOT
PACKAGE = Path(__file__).resolve().parent.parent
RESULTS = repository_path('results/levers')
PSI = 6894.757
MPD_LIMIT_PA = 2500. * PSI  # Nabors Integra onshore dynamic working-pressure class.
NATIVE_CYCLE, NATIVE_WINDOWS = se.site_cycle, se.common_windows
NATIVE_BUDGET, NATIVE_CIRCULATE = pr.bottomhole_pressure, se.circulate
RATING_PHYSICS = {}


class SolveFailure(ValueError):
    """A prerequisite failed, so later gates have no physical inputs."""


@dataclass(frozen=True)
class Settings:
    flow_L_s: float
    pipe: str = wg.TK_DRAKON.name
    shoe_m: float = 4000.
    pv_fraction: float = 1.
    coating_rating_C: float = 204.
    allowance_SG: float = 0.02
    form_h: float = 0.
    bhp_Pa: float = None


def water_pv_fraction():
    mu = float(np.ravel(fluids._water([fluids.PV_REF_T], [fluids.P_ATM])[2])[0])
    return mu / fluids.PV_REF


def feasible_intervals(grid, delta):
    """Keep both branches of a zero-backpressure clamp for later intersection."""
    grid, delta = np.asarray(grid), np.asarray(delta)
    ids = np.flatnonzero(delta >= -1.e-5)
    intervals = []
    for group in np.split(ids, np.flatnonzero(np.diff(ids) > 1) + 1):
        if not len(group):
            continue
        a, b = group[0], group[-1]
        lo = grid[a] if a == 0 else np.interp(0., [delta[a - 1], delta[a]], grid[a - 1:a + 1])
        hi = grid[b] if b == len(grid) - 1 else np.interp(0., [-delta[b], -delta[b + 1]], grid[b:b + 2])
        intervals.append((float(lo), float(hi)))
    return intervals


def controlled_column(target, temperatures, material, friction=0.):
    """Nonnegative surface pressure holding nominal bottomhole pressure.

    The hydrostatic integral uses the candidate backpressure in its property
    pressures. Negative required backpressure is retained as a control failure.
    """
    tvd, temperature = temperatures
    zero = pr.column(tvd, temperature, material, 0.)
    residual = lambda bp: float(pr.column(tvd, temperature, material, bp)[-1]) + friction - target
    requested = target - float(zero[-1]) - friction
    if requested <= 0.:
        bp = 0.
    else:
        bp = brentq(residual, 0., max(requested * 1.1, 1.), xtol=0.1)
    pressure = pr.column(tvd, temperature, material, bp)
    return dict(pressure=pressure, backpressure=bp, requested_at_zero=requested,
                error_Pa=float(pressure[-1]) + friction - target,
                controllable=requested >= -1000.)


class MPD:
    """D7 constant-BHP policy, including the losses replaced at connections."""
    def __init__(self, target):
        self.target = target

    def reference_run(self, run):
        """Keep the native static-water skin reference at connection SBP."""
        cold = pr.circulating_temperatures(run)
        control = controlled_column(self.target, cold, run.get('fluid'))
        reference = dict(run)
        reference['backpressure'] = control['backpressure']
        return reference

    def circulate(self, site, z, geotherm, pipe, mass_flow, exposure=None, film_mult=1.,
                  P_surface=m1.P_SURF, fluid=None, retry=True):
        bp = max(0., P_surface - m1.P_SURF)
        run = None
        for _ in range(8):
            run = NATIVE_CIRCULATE(site, z, geotherm, pipe, mass_flow, exposure, film_mult,
                                   m1.P_SURF + bp, fluid, retry)
            if not run['success']:
                raise SolveFailure(run.get('failure', 'MPD circulation did not converge'))
            control = controlled_column(self.target, pr.circulating_temperatures(run), fluid,
                                         pr.annulus_friction(run, z))
            if abs(control['backpressure'] - bp) < 500.:
                break
            bp = control['backpressure']
        run['backpressure'] = run['P_surface'] - m1.P_SURF
        actual = float(pr.column(*pr.circulating_temperatures(run), fluid, run['backpressure'])[-1])
        actual += pr.annulus_friction(run, z)
        run['mpd_control'] = dict(target_Pa=self.target, actual_Pa=actual,
                                  error_Pa=actual - self.target,
                                  controllable=control['controllable'])
        # A closed annulus adds surface backpressure to the pump discharge.
        run['hyd'] = dict(run['hyd'])
        old_spp = run['hyd']['spp']
        run['hyd']['spp'] += run['backpressure']
        if abs(old_spp) > 1.:
            run['hyd']['pump_power'] *= run['hyd']['spp'] / old_spp
        run['hyd']['over_pump_limit'] = run['hyd']['spp'] > m1.PUMP_LIMIT
        return run

    def budget(self, state, z, temperatures=None, fluid=None, run=None, P_surface=0.,
               allowance_SG=0., grad=None):
        if grad is not None or temperatures is None:
            return NATIVE_BUDGET(state, z, temperatures, fluid, run, P_surface, allowance_SG, grad)
        friction = pr.annulus_friction(run, z) if state == 'drilling' else 0.
        bottom_friction = pr.annulus_friction(run, run['geometry'].md_bit) if state == 'drilling' else 0.
        control = controlled_column(self.target, temperatures, fluid, bottom_friction)
        static = float(np.interp(z, temperatures[0], control['pressure']))
        allowance = allowance_SG * pr.sg_per_pa(z)
        return dict(state=state, z=z, P_surface=control['backpressure'], P_static=static,
                    friction=friction, allowance=allowance, P_lo=static + friction - allowance,
                    P_hi=static + friction + allowance,
                    SG=(static - control['backpressure']) / pr.sg_per_pa(z))

    def windows(self, site, out, cycle=None, run=None, node=True, extra_depths=(), refine=True):
        cycle, run = cycle or out['cycle'], run or out['m1']
        original_inputs = se.stability_inputs
        calls = []
        def collect(*args, **kwargs):
            result = original_inputs(*args, **kwargs)
            calls.append((args[1], result[1]))
            return result
        # The native implementation supplies exactly fresh, trip and exposure
        # case sets at each depth. All wall histories and the skin rule are reused.
        with patch.object(se, 'stability_inputs', collect):
            native = NATIVE_WINDOWS(site, out, cycle, self.reference_run(run), node, extra_depths, False)
        if len(calls) != 3 * len(native['depths']):
            raise ValueError('MPD case collection no longer matches the native window states')
        constraints = []
        for index, (depth, cases) in enumerate(calls):
            state = ('connection', 'trip', 'drilling')[index % 3]
            constraints.extend((state, depth, case) for case in cases)
        constraints.extend(('connection', out['z'], case) for case in cycle['cases']['connection'])
        target_constraints = [(state, case) for state, depth, case in constraints if abs(depth - out['z']) < 1e-6]
        target_floor = max(case['window']['Pw_lo'] +
                           (pr.TRIP_ALLOWANCE_SG * pr.sg_per_pa(out['z']) if state == 'trip' else 0.)
                           for state, case in target_constraints)
        # Native trip Pw_hi already has the surge allowance removed.
        target_ceiling = min(case['window']['Pw_hi'] for state, case in target_constraints)
        factory = out['_make_fluid']
        water = fluids.water().rho_surface
        grid = np.r_[water, se.RHO_GRID[1:]]
        cold = pr.circulating_temperatures(run)
        hot = se.trip_temperatures(site, out, run, cycle['trip_h'], node)
        total_friction = pr.annulus_friction(run, out['z'])
        tables = {}
        for state, temperatures, friction in [('drilling', cold, total_friction),
                                               ('connection', cold, 0.), ('trip', hot, 0.)]:
            controls = [controlled_column(self.target, temperatures, factory(rho), friction) for rho in grid]
            tables[state] = (temperatures[0], controls)
        records = {'drilling_fluid': [], 'trip_fluid': []}

        def interval(delta, location):
            return dict(intervals=feasible_intervals(grid, delta), location=location,
                        empty_gap_kg_m3=max(1., -float(delta.max()) / location['pa_per_SG'] * 1000.))

        for state, depth, case in constraints:
            group = 'trip_fluid' if state == 'trip' else 'drilling_fluid'
            tvd = float(run['geometry'].survey.tvd(depth))
            axis, controls = tables[state]
            pressure = np.array([np.interp(tvd, axis, item['pressure']) for item in controls])
            if state == 'drilling':
                pressure += pr.annulus_friction(run, depth)
            allowance = pr.TRIP_ALLOWANCE_SG * pr.sg_per_pa(tvd) if state == 'trip' else 0.
            start_axis, starts = tables['connection'] if state == 'trip' else tables[state]
            upper_pressure = np.array([np.interp(tvd, start_axis, item['pressure']) for item in starts])
            if state == 'trip':
                # With constant BHP the hot column needs extra surface pressure.
                # Its shallow pressure can exceed the cold trip-start value.
                upper_pressure = trip_upper_pressure(pressure, upper_pressure)
            if state == 'drilling':
                upper_pressure += pr.annulus_friction(run, depth)
            point = dict(state=state, md=depth, case=case['label'], pa_per_SG=pr.sg_per_pa(tvd))
            records[group].append(interval(pressure - allowance - case['window']['Pw_lo'],
                                           dict(point, pressure_bound='lower')))
            records[group].append(interval(case['window']['Pw_hi'] - upper_pressure,
                                           dict(point, pressure_bound='upper')))
        # Working-pressure and nonnegative-choke limits are density constraints too.
        for state, (_, controls) in tables.items():
            group = 'trip_fluid' if state == 'trip' else 'drilling_fluid'
            point = dict(state=state, md=out['z'], case='RCD/choke working pressure',
                         pa_per_SG=pr.sg_per_pa(out['z']))
            bp = np.array([c['backpressure'] for c in controls])
            requested = np.array([c['requested_at_zero'] for c in controls])
            records[group].append(interval(MPD_LIMIT_PA - bp, dict(point, pressure_bound='working pressure')))
            records[group].append(interval(requested, dict(point, pressure_bound='nonnegative control')))
            if state == 'connection':
                # Trip starts in the same cold column, but with trip material.
                records['trip_fluid'].extend(records[group][-2:])

        result = dict(depths=native['depths'], states={}, mpd=True,
                      mpd_target_interval_Pa=[target_floor, target_ceiling])
        for name, candidates in records.items():
            floor = dict(state='water floor', md=out['z'], case='water floor')
            families = [dict(lo=water, hi=float(grid[-1]), lo_by=floor, hi_by=floor)]
            closed = None
            for candidate in candidates:
                compatible = []
                for family in families:
                    for lo, hi in candidate['intervals']:
                        a, b = max(lo, family['lo']), min(hi, family['hi'])
                        if a <= b:
                            compatible.append(dict(lo=a, hi=b,
                                lo_by=candidate['location'] if lo > family['lo'] else family['lo_by'],
                                hi_by=candidate['location'] if hi < family['hi'] else family['hi_by']))
                if not compatible:
                    family = families[0]
                    if candidate['intervals']:
                        lo, hi = min(candidate['intervals'], key=lambda p: max(p[0], family['lo']) - min(p[1], family['hi']))
                        closed = dict(lo=max(lo, family['lo']), hi=min(hi, family['hi']),
                            lo_by=candidate['location'] if lo > family['lo'] else family['lo_by'],
                            hi_by=candidate['location'] if hi < family['hi'] else family['hi_by'])
                    else:
                        closed = dict(lo=family['lo'], hi=family['lo'] - candidate['empty_gap_kg_m3'],
                                      lo_by=candidate['location'], hi_by=candidate['location'])
                    break
                families = compatible
            opened = closed is None
            chosen = closed or min(families, key=lambda f: f['lo'])
            result[name] = dict(**chosen, open=opened,
                                fluid=chosen['lo'] if opened else None,
                                note=None if opened else 'no density satisfies constant-BHP and equipment constraints')
        if refine:
            previous, accumulated, levels = result, list(extra_depths), []
            shoe = max(h.md_top for h in run['geometry'].hole)
            for spacing in (se.WINDOW_DZ / 2., se.WINDOW_DZ / 4.):
                for name in records:
                    for side in ('lo_by', 'hi_by'):
                        d = previous[name][side]['md']
                        accumulated.extend(np.arange(max(shoe, d - se.WINDOW_DZ),
                                                     min(out['z'], d + se.WINDOW_DZ) + spacing * 0.5, spacing))
                finer = self.windows(site, out, cycle, run, node, accumulated, False)
                changes = {name: {side: abs(finer[name][side] - previous[name][side]) / 1000.
                                  for side in ('lo', 'hi')} for name in records}
                levels.append(dict(spacing_m=spacing, changes=changes))
                previous = finer
            previous['refinement'] = dict(levels=levels, tolerance_SG=se.FLUID_TOL_SG,
                converged=all(c <= se.FLUID_TOL_SG for level in levels
                              for delta in level['changes'].values() for c in delta.values()))
            result = previous
        # Constant BHP changes the feasible density family. The native target
        # verdict assumed the circulating backpressure persisted through pauses.
        cycle['site_verdict'] = 'CONDITIONAL' if all(result[n]['open'] for n in records) else 'NO-GO'
        cycle['verdicts'] = {state: cycle['site_verdict'] for state in ('drilling', 'connection', 'trip')}
        return result


def trip_upper_pressure(hot, cold):
    """Fracture check at both ends of the controlled, uniform-fluid trip."""
    return np.maximum(hot, cold)


def gates(out):
    """A C6 candidate may retain an explicit coating qualification unknown."""
    c = out['components']
    failures = []
    for name, ok in [('solver', c['solver']['ok']), ('tool', c['tool']['ok']),
                     ('pump limit', c['pumps']['ok']), ('rig capacity', c['pumps']['within_rig']),
                     ('hole cleaning', c['hole_cleaning']['ok']),
                     ('depth refinement', c['window_refinement']['converged'])]:
        if not ok:
            failures.append(name)
    failures.extend(name for name in ('drilling_fluid', 'trip_fluid') if not out['windows'][name]['open'])
    if c['stability']['verdict'].split()[0] == 'NO-GO':
        failures.append('wall stability')
    for name, material in (('drilling_fluid', out['fluid']), ('trip_fluid', out['trip_fluid'])):
        rho = fluids.water().rho_surface if material is None else material.rho_surface
        if out['windows'][name]['open'] and not out['windows'][name]['lo'] - 0.001 <= rho <= out['windows'][name]['hi'] + 0.001:
            failures.append(name + ' actual weight outside window')
    if c['admissibility']['inadmissible']:
        failures.append('frictional admissibility')
    if out.get('mpd_gate') and not out['mpd_gate']['ok']:
        failures.append('MPD pressure control / working-pressure rating')
    qualification = ['coating qualification'] if c['coating']['status'] in ('INDETERMINATE', 'no rating') else []
    if out.get('mpd_gate'):
        qualification.append('RCD thermal qualification at the evaluated return temperature')
    reopened = not failures
    label = ('CONDITIONAL' if qualification or out['status']['label'] != 'GO' else 'GO') if reopened else out['status']['label']
    return dict(reopened=reopened, verdict=label, failures=failures,
                qualification_indeterminate=qualification, evaluated_status=out['status'])


def evaluate_settings(key, settings):
    site = replace(se.find_site(key), coupled=True)
    se.validate_site(site)
    pipe = wg.PIPE_TYPES[settings.pipe]
    factory = lambda rho: fluids.Mud(rho, fluids.PV_REF * settings.pv_fraction, fluids.YP_REF)
    controller = MPD(settings.bhp_Pa) if settings.bhp_Pa is not None else None

    def geometry(depth, chosen_pipe):
        return wg.wu2025_well(depth, chosen_pipe,
                              shoes=(min(100., 0.05 * depth), min(1000., 0.25 * depth), settings.shoe_m))

    def selected(site, z, geotherm, exposure=None, **kwargs):
        fluid = kwargs.get('fluid')
        run = se.circulate(site, z, geotherm, pipe, se.mass_flow(settings.flow_L_s, fluid), exposure,
                           P_surface=kwargs.get('P_surface', m1.P_SURF), fluid=fluid,
                           retry=kwargs.get('retry', True))
        if not run['success']:
            raise SolveFailure(run.get('failure', 'selected circulation did not converge'))
        return dict(pipe=pipe, m_dot=settings.flow_L_s, run=run, conflict=None, tried=[])

    def cycle(site, out, **kwargs):
        if controller:
            kwargs['run'] = controller.reference_run(out['m1'])
        return NATIVE_CYCLE(site, out, form_h=settings.form_h, **kwargs)

    with ExitStack() as scope:
        scope.enter_context(patch.object(se, 'site_well', geometry))
        scope.enter_context(patch.object(se, 'choose_circulation', selected))
        scope.enter_context(patch.object(se, 'site_cycle', cycle))
        scope.enter_context(patch.object(pr, 'TRIP_ALLOWANCE_SG', settings.allowance_SG))
        ratings = dict(se.COATING_RATINGS)
        if settings.pipe == wg.TK_DRAKON.name:
            ratings[settings.pipe] = settings.coating_rating_C
        scope.enter_context(patch.object(se, 'COATING_RATINGS', ratings))
        if controller:
            scope.enter_context(patch.object(se, 'circulate', controller.circulate))
            # The native skin rule references static water in a connection.
            # Its pressure boundary follows the connection control setting.
            scope.enter_context(patch.object(se, 'common_windows', controller.windows))
        fluid, trip, rop, visited, passes = None, None, None, [], []
        converged = False
        water = fluids.water().rho_surface
        for _ in range(se.FLUID_MAX_PASSES):
            out = se._evaluate_v12(site, True, True, fluid, rop=rop, light=True)
            out.update(circulation='v1.3.4', _make_fluid=factory, apply_trip_fluid=True,
                       coverage_corrected=True, trip_fluid=trip, form_h=settings.form_h)
            out['cycle'] = se.site_cycle(site, out)
            out['windows'] = se.common_windows(site, out)
            drilling_window, trip_window = out['windows']['drilling_fluid'], out['windows']['trip_fluid']
            if drilling_window['open'] and trip_window['open'] and drilling_window['lo'] > trip_window['hi']:
                trip_window.update(lo=drilling_window['lo'], open=False, fluid=None,
                                   note='the trip weight cannot be at least the drilling weight inside its window')
            out['tools'] = rb.recorded_tool_gates(site, out)
            used_d = water if fluid is None else fluid.rho_surface
            used_t = water if trip is None else trip.rho_surface
            rho_d = max(water, out['windows']['drilling_fluid']['lo'])
            rho_t = max(rho_d, out['windows']['trip_fluid']['lo'])
            # Conservative 0.1 kg/m3 weight quantization is much smaller than
            # C2's 2 kg/m3 tolerance and avoids returning a weight just below
            # the lower bound. Use the midpoint for a narrower feasible window.
            def implementable(rho, name):
                window = out['windows'][name]
                if rho <= water + 1e-6 or not window['open']:
                    return rho
                if rho > window['hi']:
                    return rho
                rounded = np.ceil(rho * 10.) / 10.
                return rounded if rounded <= window['hi'] else (rho + window['hi']) / 2.
            rho_d = implementable(rho_d, 'drilling_fluid')
            rho_t = implementable(max(rho_d, rho_t), 'trip_fluid')
            rop_used, next_rop = out['circ']['rop'], out['drill']['ROP']
            valid = bool(out['m1']['success'] and out.get('_trip_circulation', out['m1'])['success'])
            passes.append(dict(simulated_rho_surface=used_d, prescribed_rho_surface=rho_d,
                trip_simulated_rho_surface=used_t, trip_prescribed_rho_surface=rho_t,
                density_residual_SG=(rho_d - used_d) / 1000., trip_residual_SG=(rho_t - used_t) / 1000.,
                fluid_SG=None if fluid is None else fluid.sg, success=valid,
                rop_m_h=rop_used * 3600., tool=out['tools']['tool']))
            if not valid or not np.isfinite(rho_t) or rho_t >= fluids.BARITE_RHO:
                passes[-1]['stop'] = 'failed solve or unimplementable density'
                break
            densities_ok = max(abs(rho_d - used_d), abs(rho_t - used_t)) < se.FLUID_TOL_SG * 1000.
            inside = all(not out['windows'][name]['open'] or
                         out['windows'][name]['lo'] - 0.001 <= used <= out['windows'][name]['hi'] + 0.001
                         for name, used in (('drilling_fluid', used_d), ('trip_fluid', used_t)))
            if densities_ok and inside and abs(next_rop - rop_used) <= se.ROP_TOL * rop_used:
                converged = True
                break
            if not densities_ok and any(max(abs(rho_d - d), abs(rho_t - t)) < se.FLUID_TOL_SG * 1000.
                                        for d, t in visited):
                passes[-1]['stop'] = 'cycling'
                break
            visited.append((used_d, used_t))
            if len(passes) < se.FLUID_MAX_PASSES:
                fluid = None if rho_d <= water + 1e-6 else factory(rho_d)
                trip = None if rho_t <= water + 1e-6 else factory(rho_t)
                rop = next_rop
        out.update(fluid_passes=passes, fluid_converged=converged, cycle_sensitivity={}, trip_profile=[])
        out['components'] = se.component_statuses(out)
        out['status'] = se.site_status(out['components'])
        if controller:
            cold = pr.circulating_temperatures(out['m1'])
            hot = se.trip_temperatures(site, out, out['m1'], out['cycle']['trip_h'])
            policies = {state: controlled_column(settings.bhp_Pa, temperatures, material, friction)
                        for state, temperatures, material, friction in (
                ('drilling', cold, fluid, pr.annulus_friction(out['m1'], out['z'])),
                ('connection', cold, fluid, 0.), ('trip start', cold, trip, 0.), ('trip end', hot, trip, 0.))}
            runs = [out['m1'], out.get('_trip_circulation', out['m1'])]
            out['mpd_gate'] = dict(ok=all(c['controllable'] and c['backpressure'] <= MPD_LIMIT_PA + 100.
                                          and abs(c['error_Pa']) < 1000. for c in policies.values())
                                      and all(abs(r['mpd_control']['error_Pa']) < 1000. for r in runs),
                target_bhp_Pa=settings.bhp_Pa, rating_Pa=MPD_LIMIT_PA,
                surface_backpressure_Pa={s: c['backpressure'] for s, c in policies.items()},
                control_errors_Pa={s: c['error_Pa'] for s, c in policies.items()})
            # Export the actual controlled pressure budget. Density requirements
            # for MPD live in the all-depth windows, not the native fixed-SBP
            # target-only inversion diagnostics.
            out['cycle']['budget']['pressures'] = {
                state: controller.budget(state, out['z'],
                    hot if state == 'trip' else cold,
                    trip if state == 'trip' else fluid, out['m1'],
                    allowance_SG=settings.allowance_SG if state == 'trip' else 0.)
                for state in ('drilling', 'connection', 'trip')}
            for field in ('drill_SG', 'drill_SG_hi', 'trip_SG', 'trip_SG_hi'):
                out['cycle'][field] = None
            out['cycle']['per_case'] = []
            out['cycle']['safe_pause_h'] = None
            for field in ('drill_rho_surface', 'trip_rho_surface', 'trip_SG_start',
                          'trip_dP_heating', 'water_dP_heating'):
                out['cycle']['budget'][field] = None
        return out


def fingerprint():
    # Schedule helpers and benchmark data affect the gates too. Include the
    # runtime so CI cannot silently reuse a trial from a different environment.
    files = {p for p in PACKAGE.rglob('*.py') if 'data' not in p.relative_to(PACKAGE).parts}
    files.update(p for p in (PACKAGE / 'data').rglob('*')
                 if p.is_file() and p.suffix in ('.csv', '.json', '.npy', '.npz'))
    versions = se.versions()
    environment = dict(python=versions['python'], packages=versions['packages'])
    digest = hashlib.sha256(json.dumps(environment, sort_keys=True).encode())
    for path in sorted(files):
        label = path.relative_to(PACKAGE).as_posix()
        digest.update(label.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def trial(key, lever, settings, root=RESULTS):
    root = require_path(root, 'Lever study output')
    parameters = asdict(settings)
    signature = fingerprint()
    identifier = hashlib.sha256(json.dumps([parameters, signature], sort_keys=True).encode()).hexdigest()[:16]
    path = root / key / lever / (identifier + '.json')
    if path.exists():
        return json.loads(path.read_text())
    print('Trial', key, lever, json.dumps(parameters), flush=True)
    started = time.perf_counter()
    rating_key = (key, replace(settings, coating_rating_C=204.))
    reused = None
    if lever == 'L5' and rating_key in RATING_PHYSICS:
        reference, reused = RATING_PHYSICS[rating_key]
        out = dict(reference)
        out['tools'] = dict(reference['tools'])
        ratings = dict(se.COATING_RATINGS, **{settings.pipe: settings.coating_rating_C})
        with patch.object(se, 'COATING_RATINGS', ratings):
            out['tools'] = rb.recorded_tool_gates(out['site'], out)
        out['components'] = se.component_statuses(out)
        out['status'] = se.site_status(out['components'])
    else:
        try:
            out = evaluate_settings(key, settings)
        except SolveFailure as error:
            record = dict(site=key, lever=lever, settings=parameters, source_sha256=signature,
                versions=se.versions(), assessment=dict(reopened=False, verdict='INDETERMINATE',
                    failures=['solver'], qualification_indeterminate=[],
                    evaluated_status=dict(label='INDETERMINATE', reasons=[str(error)])),
                metrics=None, result=dict(prerequisite_failure=str(error),
                    other_gates='INDETERMINATE because the selected circulation failed'), mpd=None,
                elapsed_seconds=time.perf_counter() - started,
                evidence=path.relative_to(ROOT).as_posix() if ROOT is not None and path.is_relative_to(ROOT) else path.as_posix(), rating_only_physics_reused_from=None)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
            print('Unresolved trial', key, lever, str(error), flush=True)
            return record
    record = dict(site=key, lever=lever, settings=parameters, source_sha256=signature,
                  versions=se.versions(), assessment=gates(out), metrics=rb.metrics(out),
                  result=se.result_dict(out), mpd=out.get('mpd_gate'),
                  elapsed_seconds=time.perf_counter() - started, evidence=path.relative_to(ROOT).as_posix() if ROOT is not None and path.is_relative_to(ROOT) else path.as_posix())
    record['rating_only_physics_reused_from'] = reused
    if lever == 'L5' and reused is None:
        RATING_PHYSICS[rating_key] = (out, record['evidence'])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(se._jsonable(record), indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Result', key, lever, record['assessment'], 'seconds', record['elapsed_seconds'], flush=True)
    return record


def bisect_minimum(evaluate, failing, passing, tolerance, predicate=None):
    """Smallest intervention, with both classifications retained in the bracket."""
    lo, hi = failing, passing
    passed = predicate or (lambda record: record['assessment']['reopened'])
    if passed(lo[1]) or not passed(hi[1]):
        raise ValueError('minimum search needs a failing and a passing run')
    while hi[0] - lo[0] > tolerance:
        x = (lo[0] + hi[0]) / 2.
        record = evaluate(x)
        if predicate is None and ('solver' in record['assessment']['failures'] or
                                   'depth refinement' in record['assessment']['failures']):
            return dict(unresolved=True, failing=dict(intervention=lo[0], evidence=lo[1]['evidence']),
                        passing=dict(intervention=hi[0], evidence=hi[1]['evidence']),
                        tolerance=tolerance, minimum=hi[1], unresolved_trial=record['evidence'])
        lo, hi = (lo, (x, record)) if passed(record) else ((x, record), hi)
    return dict(failing=dict(intervention=lo[0], evidence=lo[1]['evidence']),
                passing=dict(intervention=hi[0], evidence=hi[1]['evidence']),
                tolerance=tolerance, minimum=hi[1])


def base_settings(key):
    checkpoint = require_path(rb.CHECKPOINT, 'Reviewed programme evidence')
    data = json.loads((checkpoint / (key + '.json')).read_text())
    return Settings(flow_L_s=data['programme']['flow'])


def run_lever(key, lever, root=RESULTS):
    root = require_path(root, 'Lever study output')
    base = base_settings(key)
    target = se.find_site(key).target()
    summary = dict(site=key, lever=lever, trials=[], bracket=None)
    if lever == 'L4':
        for pipe in (wg.TK_DRAKON, wg.DUAL_WALL, wg.VACUUM_INSULATED):
            summary['trials'].append(trial(key, lever, replace(base, pipe=pipe.name), root))
    elif lever == 'L5':
        # Rating has its own qualification threshold even if other gates fail.
        for rating in (204., 300., 400.):
            summary['trials'].append(trial(key, lever, replace(base, coating_rating_C=rating), root))
        peak = max(summary['trials'][0]['metrics']['coating'][name] if name == 'circulating_max' else
                   summary['trials'][0]['metrics']['coating'][name]['max']
                   for name in ('circulating_max', 'connection', 'trip_in'))
        def rating_trial(rating):
            record = trial(key, lever, replace(base, coating_rating_C=float(rating)), root)
            summary['trials'].append(record)
            return record
        predicate = lambda record: record['metrics']['coating']['status'] == 'within rating'
        coarse = bisect_minimum(rating_trial, (204., summary['trials'][0]),
                                 (400., summary['trials'][2]), 0.1, predicate)
        f = (coarse['failing']['intervention'], next(r for r in summary['trials'] if r['evidence'] == coarse['failing']['evidence']))
        p = (coarse['passing']['intervention'], coarse['minimum'])
        fine = bisect_minimum(rating_trial, f, p, 0.05, predicate)
        summary['coating_threshold'] = dict(peak_C=peak, coarse_tolerance_C=0.1,
            refined_tolerance_C=0.05, bracket=coarse, refined_bracket=fine,
            note='qualification threshold; full-site reopening assessed separately')
    else:
        if lever == 'L1':
            site = replace(se.find_site(key), coupled=True)
            rock = float(site.temperature()(target))
            cases = se.stability_inputs(site, target, rock, T_wall=rock)[1]
            floor = max(c['window']['Pw_lo'] for c in cases)
            ceiling = min(c['window']['Pw_hi'] for c in cases)
            setting = lambda q: replace(base, bhp_Pa=floor + 10000. + q * max(0., ceiling - floor - 20000.))
            tolerance = 10000. / max(1., ceiling - floor)
            summary['target_interval_Pa'] = [floor, ceiling]
        elif lever == 'L2':
            setting = lambda q: replace(base, shoe_m=4000. + q * (target - 4500.))
            tolerance = 50. / (target - 4500.)
        elif lever == 'L3':
            setting = lambda q: replace(base, pv_fraction=1. - q * (1. - water_pv_fraction()))
            tolerance = 0.02
        elif lever == 'L6':
            setting = lambda q: replace(base, allowance_SG=0.02 * (1. - q))
            tolerance = 0.05
            summary['trials'].append(trial(key, lever, replace(base, allowance_SG=0.04), root))
        elif lever == 'L7':
            setting = lambda q: replace(base, form_h=2. * q)
            tolerance = 0.025
        elif lever == 'L8':
            setting = lambda q: replace(base, flow_L_s=base.flow_L_s - q * (base.flow_L_s - 5.))
            tolerance = 0.5 / (base.flow_L_s - 5.)
        else:
            raise ValueError(lever)
        measured = []
        def evaluate(q):
            record = trial(key, lever, setting(q), root)
            summary['trials'].append(record)
            return record
        for q in (0., 0.5, 1.):
            measured.append((q, evaluate(q)))
        if lever == 'L1' and not any(item[1]['assessment']['reopened'] for item in measured):
            proposed = []
            for _, record in measured:
                band = record.get('result', {}).get('windows', {}).get('mpd_target_interval_Pa')
                if band and band[0] < band[1]:
                    proposed.append((band[0] + band[1]) / 2.)
            for pressure in sorted(set(round(p / 1000.) * 1000. for p in proposed)):
                q = (pressure - floor - 10000.) / max(1., ceiling - floor - 20000.)
                if 0. <= q <= 1.:
                    measured.append((q, evaluate(q)))
        passes = [item for item in measured if item[1]['assessment']['reopened']]
        if passes:
            first = min(passes, key=lambda item: item[0])
            failures = [item for item in measured if item[0] < first[0] and not item[1]['assessment']['reopened']]
            if failures:
                summary['bracket'] = bisect_minimum(evaluate, max(failures, key=lambda item: item[0]), first, tolerance)
                coarse = summary['bracket']
                f = (coarse['failing']['intervention'], next(r for r in summary['trials'] if r['evidence'] == coarse['failing']['evidence']))
                p = (coarse['passing']['intervention'], coarse['minimum'])
                if not coarse.get('unresolved'):
                    summary['refined_bracket'] = bisect_minimum(evaluate, f, p, tolerance / 2.)
            else:
                summary['minimum_endpoint'] = first[1]
    path = root / key / lever / 'summary.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(se._jsonable(summary), indent=2) + '\n', encoding='utf-8', newline='\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sites', nargs='+', choices=('soultz', 'united-downs'), default=['soultz', 'united-downs'])
    parser.add_argument('--levers', nargs='+', choices=['L' + str(i) for i in range(1, 9)], default=['L' + str(i) for i in range(1, 9)])
    parser.add_argument('--output', type=Path, default=RESULTS)
    args = parser.parse_args()
    args.output = require_path(args.output, 'Lever study output')
    for key in args.sites:
        for lever in args.levers:
            run_lever(key, lever, args.output)


if __name__ == '__main__':
    try:
        main()
    except ValueError as error:
        raise SystemExit(str(error)) from None
