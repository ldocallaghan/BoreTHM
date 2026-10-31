"""Evaluate the declared pressure diagnosis with the entry 8 calculation.

The input archive is read unchanged. Full circulation solves check the
isothermal shortcut on the frozen scoreboard samples. Trip pressures are
evaluated at measured temperature limits on 16A and mean inlet/return on
16B. Missing equipment or channels remain explicit exclusions.
"""
import argparse
from collections import defaultdict
import csv
from dataclasses import replace
from datetime import datetime, timezone
import gzip
import importlib.util
import json
import math
from pathlib import Path
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DECLARATION = '38c352c45b94e3276ec80bc5c747468c5c37b561'


def load(path):
    spec = importlib.util.spec_from_file_location('pressure_entry8', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def finite(value):
    try:
        x = float(value)
        return x if math.isfinite(x) and x != -999.25 else None
    except (TypeError, ValueError):
        return None


def epoch(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()


def trim_geometry(full, bit_m, wg):
    """Retain the bottom of a recorded string, with the upper part at surface."""
    cut = full.md_bit-bit_m
    if cut < -1e-6 or bit_m <= 0:
        raise ValueError('Requested depth is outside the constructed string')
    top = 0.
    segments = []
    for segment in full.string:
        end = top+segment.length
        if end > cut:
            segments.append(replace(segment, length=end-max(top, cut)))
        top = end
    holes = [replace(h, md_bottom=min(h.md_bottom, bit_m+1e-6))
             for h in full.hole if h.md_top < bit_m]
    return wg.WellGeometry(segments, holes, full.survey)


class Calculation:
    def __init__(self):
        self.adapter = load(HERE.parent/'entry-8/score.py')
        self.score = self.adapter.score
        self.m1, self.whole = self.score.m1, self.score.whole
        self.plan = self.score.read_json(self.score.PLAN)
        self.templates = {}
        for s in self.plan['samples']:
            self.templates.setdefault((s['well'], s['run']), []).append(s)
        self.surface = self.score.hl.SurfaceLoss.api_case(5)
        self.rotary = self.adapter.rotary.Rotary(self.plan, self.score.geometry)
        self.clocks = {}

    def fluid(self, sample):
        mode = 's2_revised' if sample['well'] == '16B' else 'blind_original'
        _, pv, yp = self.adapter.FROZEN_FLUID(sample, mode)
        fluid = self.score.Mud(sample['density_ppg']*self.whole.PPG,
            pv_ref=None if pv is None else pv*.001,
            yield_point=yp*self.whole.YP_PA, pv_ref_T=26.7)
        fluid.rheology = self.adapter.hypotheses.rheology(sample, fluid, yp, 'no-yield')
        return fluid, pv, yp

    def trip_sample(self, row):
        choices = self.templates[row['well'], row['assembly']]
        # The closest recorded time supplies the frozen period's mud/nozzles.
        return min(choices, key=lambda s: abs(s['time_s']-epoch(row['start'])))

    def geometry(self, sample, bit_ft, hole_ft):
        depth = max(bit_ft, hole_ft, sample['bit_ft'])
        extended = {**sample, 'bit_ft': depth}
        full = self.score.geometry(extended, self.plan, 'current')
        return trim_geometry(full, bit_ft*self.whole.FT, self.score.wg)

    def pressure(self, sample, geometry, q_gpm, temperature, mass_rate=None, result=None):
        fluid, _, _ = self.fluid(sample)
        if mass_rate is None:
            rho = float(self.m1.fluid_props(np.array([temperature]),
                        np.array([self.m1.P_SURF]), fluid)[0][0])
            mass_rate = q_gpm*self.whole.GPM*rho
        hyd = self.m1.hydraulics(mass_rate, geometry, result=result, T_avg=temperature,
            tfa=sample['tfa_m2'], fluid=fluid, hydraulics_model='v1.6.0',
            surface=self.surface, annulus_model=self.adapter.MODEL)
        if result is None:
            # The uniform temperature represents the downhole liquid. The
            # surface line retains the recorded flow and its inlet density.
            # In particular, a hot downhole state cannot define a boiling
            # surface inlet in this diagnostic.
            q = q_gpm*self.whole.GPM
            surface = float(self.surface.pressure(mass_rate/q, q))
            hyd['spp'] += surface-hyd['dp_surface']
            hyd['dp_surface'] = surface
            hyd['pump_power'] = hyd['spp']*q
            hyd['over_pump_limit'] = hyd['spp']>self.m1.PUMP_LIMIT
        return hyd

    def solve(self, sample):
        well = sample['well']
        if well not in self.clocks:
            if well == '16A':
                t, c, d, _ = self.adapter.energy.clock_a(ROOT/'validation/forge16a')
            else:
                _, t, c, d = self.whole.clock(ROOT/'validation/forge16b')
            self.clocks[well] = t, c, d
        t, clock, depth = self.clocks[well]
        g = self.score.geometry(sample, self.plan, 'current')
        fluid, _, _ = self.fluid(sample)
        q = sample['flow_gpm']*self.whole.GPM
        rho = float(self.m1.fluid_props(np.array([sample['T_in_C']]),
                    np.array([self.m1.P_SURF]), fluid)[0][0])
        exposure = self.m1.smooth_exposure(self.m1.exposure_from_history(
            clock, depth, float(np.interp(sample['time_s'], t, clock))), g.md_bit)
        form = self.score.b.T_FORM if well == '16B' else self.score.a.formation('216', g.survey)[0]
        heat, _ = self.rotary.heat(sample)
        result = self.m1.solve_seeded(exposure, self.m1.exposure_breaks(exposure, g.md_bit),
            m_dot=q*rho, T_inj=sample['T_in_C'], geotherm=form, geometry=g,
            target_rock_T=float(form(g.survey.tvd(g.md_bit))),
            Q_face=sample['motor_heat_psi']*self.whole.PSI*q+heat.bit_W,
            k_rock=self.score.b.K_ROCK, rhocp_rock=self.score.b.RHOCP_ROCK,
            friction_heat=True, tfa=sample['tfa_m2'], film_mult=1., fluid=fluid,
            verbose=False, hydraulics_model='v1.6.0', surface=self.surface,
            annulus_heat=heat.annulus, annulus_model=self.adapter.MODEL)
        return g, result, q*rho


def shortcut(calc, output, limit):
    path = output/'shortcut-check.csv'
    rows = read(path) if path.exists() else []
    done = {r['sample_id'] for r in rows}
    archived = {r['sample_id']: r for r in read(HERE.parent/'entry-8/results/film-1.00/circulation.csv')}
    started = time.perf_counter()
    processed = 0
    for s in calc.plan['samples']:
        if s['id'] in done:
            continue
        if limit is not None and processed >= limit:
            break
        row = dict(sample_id=s['id'], well=s['well'], assembly=s['run'], success=False)
        try:
            g, result, mdot = calc.solve(s)
            row.update(solver_status=int(result['sol'].status), success=bool(result['success']))
            if result['success']:
                full = calc.pressure(s, g, s['flow_gpm'], s['T_in_C'], mdot, result)
                full_psi = full['spp']/calc.whole.PSI
                row.update(full_spp_psi=full_psi, bit_C=float(result['Td'][-1]),
                    return_C=float(result['Tu'][0]), archive_spp_psi=float(archived[s['id']]['spp_psi']),
                    archive_bit_C=float(archived[s['id']]['bit_C']),
                    archive_return_C=float(archived[s['id']]['return_C']))
                row['archive_difference_psi'] = full_psi-row['archive_spp_psi']
                for kind, temp in [('inlet_return', (s['T_in_C']+row['return_C'])/2),
                                   ('bit_return', (row['bit_C']+row['return_C'])/2)]:
                    # Preserve the full solve's mass rate when isolating the shortcut.
                    hyd = calc.pressure(s, g, s['flow_gpm'], temp, mdot)
                    value = hyd['spp']/calc.whole.PSI
                    row[kind+'_C'] = temp
                    row[kind+'_spp_psi'] = value
                    row[kind+'_error_percent'] = 100*(value/full_psi-1)
        except Exception as error:
            row.update(error_type=type(error).__name__, error=str(error))
        rows.append(row)
        write(path, rows)
        processed += 1
        if processed % 10 == 0:
            print(f'Shortcut check: {len(rows)}/{len(calc.plan["samples"])} samples, '
                  f'{time.perf_counter()-started:.0f} s', flush=True)
    return rows


def temperature_inputs():
    """Measured channel extrema and distinct joined rig minutes per 16A window."""
    windows = read(HERE/'inputs/16a-steady-windows.csv')
    by_source = defaultdict(dict)
    for assembly in {r['assembly'] for r in windows}:
        by_source[assembly] = {i: r for i, r in enumerate(
            read(ROOT/f'validation/forge16a/sanvean_BHA{assembly}_10s.csv'), 2)}
    observations = defaultdict(list)
    with gzip.open(HERE/'inputs/16a-observations.csv.gz', 'rt', encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            observations[row['assembly']].append(row)
    answer = {}
    for window in windows:
        records = [r for r in observations[window['assembly']]
                   if window['start'] <= r['time'] <= window['end']]
        channels = defaultdict(list)
        minutes = set()
        for r in records:
            source = by_source[window['assembly']][int(r['source_row'])]
            for key in ('top_sub_C', 'bit_box_C'):
                value = finite(source.get(key))
                if value is not None:
                    channels[key].append(value)
            value = finite(r.get('temp_out_F'))
            if value is not None:
                channels['return_proxy_C'].append((value-32)/1.8)
            if r['rig_source_row_first'] and finite(r.get('spp_psi')) is not None:
                minutes.add(r['time'][:16])
        values = [x for group in channels.values() for x in group]
        answer[window['window_id']] = dict(rig_minutes=len(minutes),
            bracket_available=all(channels[k] for k in ('top_sub_C', 'bit_box_C', 'return_proxy_C')),
            temperature_low_C=min(values) if values else None,
            temperature_high_C=max(values) if values else None,
            **{k+'_count': len(channels[k]) for k in ('top_sub_C', 'bit_box_C', 'return_proxy_C')})
    return answer


def observed_shortcut(calc, output):
    """Check the trip shortcut's measured inlet/return inputs on saved solves."""
    path = output/'shortcut-check.csv'
    rows = read(path)
    samples = {s['id']:s for s in calc.plan['samples']}
    for row in rows:
        if row['success'] not in ('True',True):
            continue
        s = samples[row['sample_id']]
        g = calc.score.geometry(s, calc.plan, 'current')
        fluid, _, _ = calc.fluid(s)
        rho = float(calc.m1.fluid_props(np.array([s['T_in_C']]),np.array([calc.m1.P_SURF]),fluid)[0][0])
        temp = (s['T_in_C']+s['measured_return_C'])/2
        mdot = s['flow_gpm']*calc.whole.GPM*rho
        hyd = calc.pressure(s, g, s['flow_gpm'], temp, mdot)
        value = hyd['spp']/calc.whole.PSI
        row.update(observed_inlet_return_C=temp,observed_inlet_return_spp_psi=value,
                   observed_inlet_return_error_percent=100*(value/float(row['full_spp_psi'])-1))
        for kind in ['inlet_return','bit_return']:
            hyd = calc.pressure(s, g, s['flow_gpm'], float(row[kind+'_C']), mdot)
            value = hyd['spp']/calc.whole.PSI
            row[kind+'_spp_psi'] = value
            row[kind+'_error_percent'] = 100*(value/float(row['full_spp_psi'])-1)
    write(path, rows)
    return rows


def phase_reference(calc, output):
    """Model-only reference for separating a hot fluid state from inlet density."""
    sample = next(s for s in calc.plan['samples'] if s['well']=='16A' and s['run']=='18')
    fluid, _, _ = calc.fluid(sample)
    rows = []
    for pressure in [calc.m1.P_SURF, calc.score.hl.PROPERTY_FLOOR]:
        rho = float(calc.m1.fluid_props(np.array([110.]),np.array([pressure]),fluid)[0][0])
        rows.append(dict(temperature_C=110.,pressure_Pa=pressure,density_kg_m3=rho,
                         recorded_nominal_density_kg_m3=fluid.rho_surface,
                         input_sample_id=sample['id'],basis='model-only property reference'))
    write(output/'phase-reference.csv',rows)


def trips(calc, output, limit):
    path = output/'windows.csv'
    rows = read(path) if path.exists() else []
    done = {(r['well'], r['window_id']) for r in rows}
    temperatures = temperature_inputs()
    started = time.perf_counter()
    processed = 0
    for well in ('16A', '16B'):
        windows = read(HERE/f'inputs/{well.lower()}-steady-windows.csv')
        for source in windows:
            if (well, source['window_id']) in done:
                continue
            if limit is not None and processed >= limit:
                break
            base = dict(well=well, window_id=source['window_id'], assembly=source['assembly'],
                excursion=source['excursion'], assignment=source['assignment'],
                role='secondary' if source['assignment']=='report sequence inferred' else 'primary',
                start=source['start'], end=source['end'], bit_depth_ft=float(source['bit_depth_ft']),
                hole_depth_ft=float(source['hole_depth_ft']), flow_gpm=float(source['flow_gpm']),
                measured_spp_psi=finite(source['spp_psi']), raw_differential_psi=source['reported_differential_psi'],
                motor=source['motor'], status='excluded', variant='none')
            if well == '16A':
                base.update(temperatures[source['window_id']])
            reason = ''
            variants = []
            if not source['assembly']:
                reason = 'assembly unassigned'
            elif (well, source['assembly']) not in calc.templates:
                reason = 'assembly absent from frozen geometry and mud plan'
            elif base['measured_spp_psi'] is None:
                reason = 'missing standpipe pressure'
            elif well == '16A':
                if not base['bracket_available']:
                    reason = 'missing measured temperature-bracket channel'
                else:
                    variants = [('measured_low', base['temperature_low_C']),
                                ('measured_high', base['temperature_high_C'])]
            elif int(source['temp_in_F_count']) < 12 or int(source['temp_out_F_count']) < 12:
                reason = 'incomplete inlet or return channel'
            else:
                variants = [('inlet_return', ((float(source['temp_in_F'])+float(source['temp_out_F']))/2-32)/1.8)]
            if reason:
                rows.append({**base, 'reason': reason})
            else:
                sample = calc.trip_sample({**source, 'well': well})
                for variant, temperature in variants:
                    row = {**base, 'variant': variant, 'temperature_C': temperature,
                           'input_sample_id': sample['id']}
                    try:
                        g = calc.geometry(sample, base['bit_depth_ft'], base['hole_depth_ft'])
                        fluid, pv, yp = calc.fluid(sample)
                        inlet = (float(source['temp_in_F'])-32)/1.8 if well=='16B' else 20.
                        rho_in = (float(calc.m1.fluid_props(np.array([inlet]),
                                  np.array([calc.m1.P_SURF]), fluid)[0][0])
                                  if well=='16B' else fluid.rho_surface)
                        mdot = base['flow_gpm']*calc.whole.GPM*rho_in
                        hyd = calc.pressure(sample, g, base['flow_gpm'], temperature, mdot)
                        row.update(status='ok', reason='', modelled_spp_psi=hyd['spp']/calc.whole.PSI,
                            mass_rate_kg_s=mdot, mass_conversion_temperature_C=inlet,
                            mass_conversion_basis=('measured inlet density' if well=='16B'
                                                   else 'recorded nominal surface mud density; inlet unknown'),
                            pipe_bore_psi=hyd['dp_string']/calc.whole.PSI,
                            annulus_psi=hyd['dp_annulus']/calc.whole.PSI,
                            nozzle_psi=hyd['dp_bit']/calc.whole.PSI,
                            surface_psi=hyd['dp_surface']/calc.whole.PSI,
                            density_ppg=sample['density_ppg'], pv_cP=pv, yp_lbf_100ft2=yp,
                            pv_ref_T_C=26.7, annulus_model=calc.adapter.MODEL,
                            rheology='entry 6 no-yield', flags=';'.join(hyd['flags']))
                        row['residual_psi'] = row['modelled_spp_psi']-row['measured_spp_psi']
                        row['measured_modelled_ratio'] = (row['measured_spp_psi']/row['modelled_spp_psi']
                                                         if row['modelled_spp_psi'] else None)
                    except Exception as error:
                        row.update(status='calculation_error', reason=str(error), error_type=type(error).__name__)
                    rows.append(row)
            processed += 1
            if processed % 100 == 0:
                write(path, rows)
                print(f'Trip windows: {processed}, {time.perf_counter()-started:.0f} s', flush=True)
        write(path, rows)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('part', choices=['shortcut', 'observed-shortcut', 'trips'])
    parser.add_argument('--output', type=Path, default=HERE/'results')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    calc = Calculation()
    if args.part=='shortcut':rows = shortcut(calc, args.output, args.limit)
    elif args.part=='observed-shortcut':rows = observed_shortcut(calc, args.output)
    else:rows = trips(calc, args.output, args.limit)
    phase_reference(calc, args.output)
    print(f'{args.part}: {len(rows)} rows, {time.perf_counter()-started:.1f} s', flush=True)


if __name__ == '__main__':
    main()
