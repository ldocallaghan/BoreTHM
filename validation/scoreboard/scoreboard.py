"""Score frozen FORGE development observations without fitting any parameter.

The legacy baseline retains the original recorded-mud substitutions, including
the disclosed fitted trial insulation conductivity. Only 16A/16B archives are
read. Saved predictions are reproduction references, never solver inputs.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import platform
import statistics as st
import time

import numpy as np
import scipy
import iapws

from borethm import model1_coupled as m1, hydraulic_losses as hl, well_geometry as wg
from borethm import tool_thermal as tt, wall_thermal as wt
from borethm import ToolLump
from borethm.fluids import Mud
from borethm.studies import validate_forge16a as a, validate_forge16b as b
from borethm.studies import validate_forge16b_wholewell as whole, forge16_energy as energy
from borethm.studies import validate_forge16a_transients as transient
from borethm.studies.pressure_comparison import serial_development_geometry

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PLAN = ROOT / 'validation/forge16b/s2/plan.json'
REGULAR = {'11', '12', '13', '15', '16', '27', '38'}
TRIAL = {'17', '18', '19', '20'}
MOTORLESS = {'12', '13', '15', '16'}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.write_bytes((json.dumps(value, indent=2, allow_nan=False)+'\n').encode('utf-8'))


def read_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def sha(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def freeze_transients(study, output):
    """Extract original event inputs, without running any model or copying logs."""
    primary = read_json(study/'s1/plan.json')
    plan = read_json(study/'s2/plan.json')
    events = [e for e in plan['events'] if e['kind'] == 'run-in leg']
    availability = {r['event_id']: r for r in read_csv(ROOT/'validation/forge16a/transient-events.csv')}
    for event in events:
        event['archived_available'] = availability[event['event_id']]['success'] == 'True'
        event['archived_unavailable_reason'] = availability[event['event_id']]['failure']
    write_json(output, dict(events=events, components=primary['components'],
        mud_and_nozzles=primary['mud_and_nozzles'],
        source_sha256={'original-16A-circulation-plan': sha(study/'s1/plan.json'),
                       'original-16A-transient-plan': sha(study/'s2/plan.json'),
                       'archived-event-inventory': sha(ROOT/'validation/forge16a/transient-events.csv')},
        selection='All eleven original run-in legs; original availability retained; fluid node, bit, internal fluid'))


def geometry(sample, plan, mode):
    if sample['well'] == '16A':
        legacy = a.geometry(sample['run'], sample['bit_ft'], plan['components_a'])
    else:
        legacy = whole.geometry(sample, plan['components_b'], plan['k_idp'])
    if mode == 'legacy':
        return legacy
    scenario = 'NC50' if sample['well'] == '16A' else 'EIS'
    return serial_development_geometry(sample, plan['components_a' if sample['well'] == '16A' else 'components_b'], legacy, scenario)


def legacy_heat(result, geometry, fluid, breaks):
    """Original one-metre quadrature and geometry-ramp treatment of heat."""
    top, _ = m1._pieces(geometry, breaks)
    changes = top[1:]
    z = np.unique(np.r_[np.linspace(0, geometry.md_bit, int(np.ceil(geometry.md_bit))+1),
                        changes, changes-.5*m1.BLEND, changes+.5*m1.BLEND])
    z = z[(z >= 0) & (z <= geometry.md_bit)]
    td, tu = result['sol'].sol(z)
    pressure = m1.P_of_z(geometry.survey.tvd(z))
    def rates(at=None):
        g = geometry.at(z if at is None else at)
        return result['m_dot']*(m1._friction_gradient(result['m_dot'], td, pressure, g['A_bore'], g['Dh_bore'], fluid)
                               + m1._friction_gradient(result['m_dot'], tu, pressure, g['A_ann'], g['Dh_ann'], fluid))
    power = rates()
    for change in changes:
        mask = abs(z-change) < .5*m1.BLEND
        weight = (z[mask]-change)/m1.BLEND+.5
        left, right = rates(np.full_like(z, change-m1.BLEND)), rates(np.full_like(z, change+m1.BLEND))
        power[mask] = (1-weight)*left[mask]+weight*right[mask]
    return float(np.trapezoid(power, z))


def circulation(plan, mode, output):
    ta, ca, da, _ = energy.clock_a(ROOT/'validation/forge16a')
    _, tb, cb, db = whole.clock(ROOT/'validation/forge16b')
    rows = []
    for sample in plan['samples']:
        row = dict(sample_id=sample['id'], well=sample['well'], bha=sample['run'],
                   source=sample.get('source', 'EYE on-bottom'), success=False,
                   calibrated_insulation=sample['well'] == '16B' and sample['run'] in ('18', '19'),
                   measured_bit_C=sample.get('measured_bit_box_C') if sample['well'] == '16A' else sample['measured_MWD_C'],
                   measured_return_C=sample['measured_return_C'],
                   raw_spp_psi=sample['spp_psi'], raw_differential_psi=sample['raw_differential_psi'],
                   film_multiplier=1., pv_ref_T_C=26.7)
        try:
            g = geometry(sample, plan, mode)
            form = b.T_FORM if sample['well'] == '16B' else a.formation('216', g.survey)[0]
            _, pv, yp = energy.fluid_for(sample, 's1_original' if sample['well'] == '16B' else 'blind_original')
            fluid = Mud(sample['density_ppg']*whole.PPG, pv_ref=None if pv is None else pv*.001,
                        yield_point=yp*whole.YP_PA, pv_ref_T=26.7)
            q = sample['flow_gpm']*whole.GPM
            rho = float(m1.fluid_props(np.array([sample['T_in_C']]), np.array([m1.P_SURF]), fluid)[0][0])
            times, clock, depth = (tb, cb, db) if sample['well'] == '16B' else (ta, ca, da)
            exposure = m1.smooth_exposure(m1.exposure_from_history(clock, depth, float(np.interp(sample['time_s'], times, clock))), g.md_bit)
            breaks = m1.exposure_breaks(exposure, g.md_bit)
            hydraulic_mode = 'v1.5.0' if mode == 'legacy' else 'v1.6.0'
            surface = None if mode == 'legacy' else hl.SurfaceLoss.api_case(5)
            result = m1.solve_seeded(exposure, breaks, m_dot=q*rho, T_inj=sample['T_in_C'], geotherm=form,
                geometry=g, target_rock_T=float(form(g.survey.tvd(g.md_bit))),
                Q_face=sample['motor_heat_psi']*whole.PSI*q, k_rock=b.K_ROCK, rhocp_rock=b.RHOCP_ROCK,
                friction_heat=True, tfa=sample['tfa_m2'], film_mult=1., fluid=fluid, verbose=False,
                hydraulics_model=hydraulic_mode, surface=surface)
            hyd = m1.hydraulics(q*rho, g, result=result, fluid=fluid, tfa=sample['tfa_m2'],
                                hydraulics_model=hydraulic_mode, surface=surface)
            row.update(success=bool(result['success']), solver_status=int(result['sol'].status),
                spp_psi=hyd['spp']/whole.PSI, bit_C=float(result['Td'][-1]), return_C=float(result['Tu'][0]),
                energy_flagged=result.get('energy_check', {}).get('flagged', False))
            for position in (0, 22, 40, 69, 84, 85):
                row[f'bore_{position}ft_C'] = float(np.interp(g.md_bit-position*whole.FT, result['z'], result['Td']))
                row[f'annulus_{position}ft_C'] = float(np.interp(g.md_bit-position*whole.FT, result['z'], result['Tu']))
            if sample['spp_psi'] is not None:
                if mode == 'legacy':
                    distributed = legacy_heat(result, g, fluid, breaks)
                    bit_pressure = float(m1.P_of_z(g.survey.tvd(g.md_bit)))
                    rho_bit = float(m1.fluid_props(np.array([result['Td'][-1]]), np.array([bit_pressure]), fluid)[0][0])
                    nozzle = m1.nozzle_dp(q*rho, rho_bit, sample['tfa_m2'])*q*rho/rho_bit
                else:
                    check = result['energy_check']
                    distributed = sum(sum(t.values()) for t in check['assigned_terms_W'].values())
                    nozzle = check['nozzle_W']
                row.update(model_hydraulic_W=distributed+float(nozzle)+sample['motor_heat_psi']*whole.PSI*q,
                    measured_hydraulic_W=sample['spp_psi']*whole.PSI*q,
                    model_standpipe_flow_W=hyd['spp']*q, surface_W=hyd.get('dp_surface', 0.)*q)
        except Exception as error:
            row['error_type'] = type(error).__name__
        rows.append(row)
    write_csv(output/'circulation.csv', rows)
    return rows


class Records(dict):
    """Keep one run's original ten-second records in memory."""
    def __missing__(self, run):
        self.clear()
        self[run] = transient.record(run)
        return self[run]


class RunIn(transient.Study):
    """Original wall/history method, with explicit circulation-mode selection."""
    def __init__(self, inputs, mode, plan):
        self.mode, self.components, self.comparison = mode, inputs['components'], plan
        self.records = Records()
        self.path = a.survey()
        self.form = a.formation('216', self.path)[0]
        self.mudlog = a.mudlog()
        cr = a.read('rig_history_1min.csv')
        self.rig_times = np.array([a.epoch(r['time']) for r in cr])
        self.rig_circ = np.cumsum([a.number(r['circulating_fraction'], 0)*60 for r in cr])
        last = 0.; depth = []
        for r in cr:
            last = max(last, a.number(r['hole_depth_ft'], last)); depth.append(last*a.FT)
        self.rig_depth = np.array(depth)
        self.rig_pumping = np.array([a.number(r['circulating_fraction'], 0) > 0 for r in cr])
        self.inputs = {r['run']: r for r in inputs['mud_and_nozzles']}
        self.profiles, self.walls, self.geometries = {}, {}, {}

    def fluid(self, run):
        p = self.inputs[run]
        return Mud(p['mud_weight_ppg']*119.8264273, pv_ref=p['pv_cP']*.001,
                   yield_point=p['yp_lbf_100ft2']*.4788025898, pv_ref_T=26.7)

    def geometry(self, run, bit):
        bit = max(float(bit), 1.)
        key = run, bit
        if key not in self.geometries:
            full = a.geometry(run, max(bit, 6000.), self.components)
            if self.mode != 'legacy':
                sample = dict(well='16A', run=run, bit_ft=max(bit, 6000.))
                full = serial_development_geometry(sample, self.components, full, 'NC50')
            cut = full.md_bit-bit*a.FT; top = 0.; segments = []
            for segment in full.string:
                end = top+segment.length
                if end > cut:
                    segments.append(wg.StringSegment(end-max(top, cut), segment.pipe,
                        local_loss=segment.local_loss, tool_loss=segment.tool_loss))
                top = end
            holes = [wg.HoleInterval(h.md_top, min(h.md_bottom, bit*a.FT+1e-6), h.r_wall, h.layers)
                     for h in full.hole if h.md_top < bit*a.FT]
            self.geometries[key] = wg.WellGeometry(segments, holes, self.path)
        return self.geometries[key]

    def profile(self, run, records):
        mean = lambda k: float(np.mean([a.number(r[k], 0) for r in records]))
        bit = np.ceil(mean('bit_depth_ft')/200)*200
        q = max(100., round(mean('flow_gpm')/25)*25)
        tin_f = round(float(np.interp(mean('hole_depth_ft'), *self.mudlog['temp_in_F']))/2)*2
        dp = max(0., round(mean('motor_differential_psi')/50)*50)
        epoch = round(records[0]['epoch']/1800)*1800
        key = run, float(bit), q, tin_f, dp, epoch
        if key not in self.profiles:
            g = self.geometry(run, bit); fluid = self.fluid(run); tin = (tin_f-32)/1.8
            rho = float(m1.fluid_props(np.array([tin]), np.array([m1.P_SURF]), fluid)[0][0])
            exposure = m1.smooth_exposure(m1.exposure_from_history(self.rig_circ, self.rig_depth,
                float(np.interp(epoch, self.rig_times, self.rig_circ))), g.md_bit)
            surface = None if self.mode == 'legacy' else hl.SurfaceLoss.api_case(5)
            result = m1.solve_seeded(exposure, m1.exposure_breaks(exposure, g.md_bit), m_dot=q*a.GPM*rho,
                T_inj=tin, geotherm=self.form, geometry=g, target_rock_T=float(self.form(self.path.tvd(g.md_bit))),
                Q_face=dp*a.PSI*q*a.GPM, k_rock=a.K_ROCK, rhocp_rock=a.RHOCP_ROCK, friction_heat=True,
                tfa=self.inputs[run]['tfa_m2'], film_mult=1., fluid=fluid, verbose=False,
                hydraulics_model='v1.5.0' if self.mode == 'legacy' else 'v1.6.0', surface=surface)
            if not result['success']:
                raise RuntimeError('Run-in conditioning circulation did not converge')
            ga = g.at(np.clip(result['z'], .01, g.md_bit-.01))
            common = dict(fluid=fluid)
            h_ann = m1.h_dittus(result['m_dot'], ga['A_ann'], ga['Dh_ann'], result['Tu'], m1.P_of_z(ga['tvd']), **common)
            h_bore = m1.h_dittus(result['m_dot'], ga['A_bore'], ga['Dh_bore'], result['Td'], m1.P_of_z(ga['tvd']), **common)
            self.profiles[key] = dict(z=result['z'], Td=result['Td'], Tu=result['Tu'], h_ann=h_ann,
                                      h_bore=h_bore, profile_id=hashlib.sha256(json.dumps(key).encode()).hexdigest()[:20])
        return self.profiles[key]


def run_in(inputs, mode, plan, output):
    study = RunIn(inputs, mode, plan)
    rows = []
    for event in inputs['events']:
        row = dict(event_id=event['event_id'], bha=event['run'], success=False,
                   archived_available=event['archived_available'], measured_peak_C=event['observed_peak_C'])
        if not event['archived_available']:
            row['status'] = 'originally unavailable'
            rows.append(row)
            continue
        try:
            records = study.records[event['run']][int(event['start_i']):int(event['end_i'])+1]
            sensed = [r for r in records if a.number(r['bit_box_C_count'], 0) > 0]
            start = records[0]['epoch']; fluid = study.fluid(event['run'])
            z0, z1 = (a.number(r['bit_depth_ft'])*a.FT for r in (sensed[0], sensed[-1]))
            duration = sensed[-1]['epoch']-sensed[0]['epoch']
            depth = np.linspace(z0, z1, max(2, int(np.ceil((z1-z0)/a.FT/200))+1))
            column = [float(study.wall(event['run'], float(z), start, True)['T'][-1]) for z in depth]
            t0 = a.number(sensed[0]['bit_box_C'])
            g = study.geometry(event['run'], a.number(sensed[-1]['bit_depth_ft']))
            ga = g.at(np.array([depth[-1]]))
            rho, cp, _, k = [float(x[0]) for x in m1.fluid_props(np.array([t0]), m1.P_of_z(ga['tvd']), fluid)]
            lump = ToolLump.of_pipe(float(ga['r_bore'][0]), float(ga['r_out'][0]), rho*cp)
            _, h_out, _ = study.static(event['run'], float(depth[-1]), a.number(sensed[-1]['bit_depth_ft']), fluid)
            h_in = wt.NU_LAMINAR*k/lump.D_in
            history, _ = tt.trip_in(lump, lambda z: float(np.interp(z+depth[0], depth, column)),
                float(depth[-1]-depth[0]), float((depth[-1]-depth[0])/duration), t0, h_out, h_in, dt=10.)
            obs_time = np.array([r['epoch']+5-start for r in sensed])
            predicted = np.interp(obs_time, history.t+obs_time[0], history.T_f)
            row.update(success=bool(np.all(np.isfinite(predicted))), status='calculated', model_peak_C=float(max(predicted)),
                       peak_error_C=float(max(predicted))-event['observed_peak_C'])
        except Exception as error:
            row.update(status='calculation failed', error_type=type(error).__name__)
        rows.append(row)
    write_csv(output/'run-in.csv', rows)
    return rows


def aggregate(gap, well, group, pairs, planned, **extra):
    pairs = list(pairs)
    result = dict(gap=gap, well=well, group=group, planned=planned, compared=len(pairs), unavailable=planned-len(pairs), **extra)
    if pairs:
        errors = [model-observed for model, observed in pairs]
        result.update(model_mean=st.mean(m for m, _ in pairs), measured_mean=st.mean(o for _, o in pairs),
                      bias=st.mean(errors), MAE=st.mean(map(abs, errors)))
        if extra.get('units') in ('psi', 'kW'):
            percentages = [100*(m-o)/o for m, o in pairs if o != 0]
            result['mean_percent_error'] = st.mean(percentages) if percentages else None
    return result


def scoreboard(rows, events):
    out = []
    for well in ('16A', '16B'):
        subset = [r for r in rows if r['well'] == well]
        pressure = [r for r in subset if r['raw_spp_psi'] is not None and
                    (well == '16A' or r['bha'] in MOTORLESS)]
        for bha in sorted({r['bha'] for r in pressure}):
            group = [r for r in pressure if r['bha'] == bha]
            pairs = [(r['spp_psi'], r['raw_spp_psi']-r['raw_differential_psi'] if well == '16A' else r['raw_spp_psi'])
                     for r in group if r['success'] and (well != '16A' or r['raw_differential_psi'] is not None)]
            out.append(aggregate('G1', well, bha, pairs, len(group), units='psi'))
        power = [r for r in subset if r['raw_spp_psi'] is not None]
        out.append(aggregate('G2', well, 'paired pressure samples',
            [(r['model_hydraulic_W']/1000, r['measured_hydraulic_W']/1000) for r in power if r['success']], len(power), units='kW'))
    aa = [r for r in rows if r['well'] == '16A']
    for bha in sorted({r['bha'] for r in aa}):
        group = [r for r in aa if r['bha'] == bha and r['measured_bit_C'] is not None]
        out.append(aggregate('G3', '16A', bha, [(r['bit_C'], r['measured_bit_C']) for r in group if r['success']],
                             len(group), units='degC', deep_run=bha in ('38', '39', '42')))
    for event in events:
        pairs = [(event['model_peak_C'], event['measured_peak_C'])] if event['success'] else []
        out.append(aggregate('G4', '16A', event['event_id'], pairs, 1, units='degC'))
    for name, group in [('ALL', aa)]+[(s, [r for r in aa if r['source'] == s]) for s in sorted({r['source'] for r in aa})]:
        out.append(aggregate('G5', '16A', name, [(r['return_C'], r['measured_return_C']) for r in group if r['success']], len(group), units='degC'))
    bb = [r for r in rows if r['well'] == '16B']
    for name, group in [('independent regular pipe', [r for r in bb if r['bha'] in REGULAR]),
                        ('trial', [r for r in bb if r['bha'] in TRIAL])]+[(n, [r for r in bb if r['bha'] == n]) for n in sorted({r['bha'] for r in bb}, key=int)]:
        pairs = [(r['bore_84ft_C'] if r['bha'] in TRIAL|{'27', '38'} else r['bore_22ft_C'],
                  r['measured_bit_C']) for r in group if r['success']]
        out.append(aggregate('G6', '16B', name, pairs, len(group), units='degC'))
    return out


def reproduction(rows, events, plan):
    samples = {s['id']: s for s in plan['samples']}
    references = {r['sample']: r for r in map(json.loads, (ROOT/'validation/forge16b/s2/results.jsonl').read_text().splitlines())
                  if r['rheology_case'] in ('s1_original', 'blind_original')}
    checks = []
    def check(identity, field, old, new, tolerance):
        checks.append(dict(sample=identity, field=field, archived=old, reproduced=new, difference=new-old,
                           tolerance=tolerance, passed=abs(new-old) <= tolerance))
    for row in rows:
        if not row['success']:
            checks.append(dict(sample=row['sample_id'], field='solver', passed=False)); continue
        saved = samples[row['sample_id']]['saved_primary']
        check(row['sample_id'], 'return_C', float(saved['return_C']), row['return_C'], .1)
        for field in ('bore_22ft_C', 'bore_84ft_C') if row['well'] == '16B' else ('bore_bit_C', 'annulus_bit_C', 'bore_40ft_C', 'annulus_40ft_C'):
            actual = row['bit_C'] if field == 'bore_bit_C' else row['annulus_0ft_C'] if field == 'annulus_bit_C' else row[field]
            check(row['sample_id'], field, float(saved[field]), actual, .1)
        reference = references[row['sample_id']]
        if row['raw_spp_psi'] is not None:
            check(row['sample_id'], 'spp_psi', reference['spp']/whole.PSI, row['spp_psi'], 1.)
            old = reference['thermal_friction_power_W']+reference['thermal_nozzle_power_W']+reference['motor_face_power_W']
            check(row['sample_id'], 'model_hydraulic_W', old, row['model_hydraulic_W'], max(1., .001*abs(old)))
    archived = {r['event_id']: r for r in read_csv(ROOT/'validation/forge16a/transient-comparisons.csv')
                if r['kind'] == 'run-in leg' and r['static_treatment'] == 'fluid node' and r['above_bit_ft'] == '0' and r['tool_quantity'] == 'internal fluid'}
    for event in events:
        if event['archived_available'] and event['success']:
            check(event['event_id'], 'model_peak_C', float(archived[event['event_id']]['model_peak_C']), event['model_peak_C'], .1)
        elif event['archived_available']:
            checks.append(dict(sample=event['event_id'], field='run-in solver', passed=False))
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    prepare = sub.add_parser('freeze-transients')
    prepare.add_argument('--study', type=Path, required=True)
    prepare.add_argument('--output', type=Path, default=HERE/'transient-inputs.json')
    run = sub.add_parser('run')
    run.add_argument('--mode', choices=('legacy', 'current'), required=True)
    run.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'freeze-transients':
        freeze_transients(args.study, args.output); return
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Choose an empty output directory for a complete comparison')
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter(); plan = read_json(PLAN)
    inputs = read_json(HERE/'transient-inputs.json')
    rows = circulation(plan, args.mode, args.output)
    events = run_in(inputs, args.mode, plan, args.output)
    write_csv(args.output/'scoreboard.csv', scoreboard(rows, events))
    checks = reproduction(rows, events, plan) if args.mode == 'legacy' else []
    if checks:
        write_csv(args.output/'baseline-reproduction.csv', checks)
    sources = [PLAN, HERE/'transient-inputs.json', Path(__file__),
               ROOT/'validation/forge16a/circulation-primary.csv', ROOT/'validation/forge16a/transient-comparisons.csv',
               ROOT/'validation/forge16b/s2/results.jsonl']
    model_sources = ['model1_coupled.py', 'hydraulic_losses.py', 'fluids.py', 'pressure.py',
                     'well_geometry.py', 'wall_thermal.py', 'tool_thermal.py',
                     'studies/validate_forge16a.py', 'studies/validate_forge16a_transients.py',
                     'studies/validate_forge16b_wholewell.py', 'studies/validate_forge16b.py',
                     'studies/forge16_energy.py', 'studies/pressure_comparison.py']
    manifest = dict(mode=args.mode, settings=dict(pv_ref_T_C=26.7, film_multiplier=1., exposure='cumulative',
                    mud='original recorded-mud substitutions'),
        calibration='Historical fitted trial insulation conductivity retained; no new fit',
        versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__, iapws=iapws.__version__),
        sources_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in sources},
        model_sources_sha256={name: sha(ROOT/'src/borethm'/name) for name in model_sources},
        results_sha256={p.name: sha(p) for p in sorted(args.output.glob('*.csv'))})
    write_json(args.output/'manifest.json', manifest)
    print(json.dumps(dict(runtime_s=time.perf_counter()-started, circulation_cases=len(rows),
        circulation_failures=sum(not r['success'] for r in rows), run_in_events=len(events),
        run_in_failures=sum(r['archived_available'] and not r['success'] for r in events),
        originally_unavailable_run_in=sum(not r['archived_available'] for r in events),
        reproduction_failures=sum(not r['passed'] for r in checks)), indent=2), flush=True)


if __name__ == '__main__':
    main()
