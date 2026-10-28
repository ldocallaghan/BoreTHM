"""Model-only predictions for entry 3, before its score.

One window per assembly: the lower median bit-depth rank among the frozen
circulation samples, with time and identifier resolving ties. Each window is
solved with the working development calculation (entry 1 with D5) twice,
with the logarithmic and the cylindrical rock response. No measured
temperature, pressure or residual is read.
"""
from collections import defaultdict
import argparse
import csv
import importlib.util
from pathlib import Path
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('frozen_scoreboard', ROOT/'validation/scoreboard/scoreboard.py')
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)
m1, hl, a, b, whole, energy = score.m1, score.hl, score.a, score.b, score.whole, score.energy


def select(samples):
    groups = defaultdict(list)
    for sample in samples:
        groups[sample['well'], sample['run']].append(sample)
    return [sorted(group, key=lambda s: (s['bit_ft'], s['time'], s['id']))[(len(group)-1)//2]
            for _, group in sorted(groups.items())]


def solve(sample, plan, clocks, response):
    g = score.geometry(sample, plan, 'current')
    form = b.T_FORM if sample['well'] == '16B' else a.formation('216', g.survey)[0]
    _, pv, yp = energy.fluid_for(sample, 's1_original' if sample['well'] == '16B' else 'blind_original')
    fluid = score.Mud(sample['density_ppg']*whole.PPG, pv_ref=None if pv is None else pv*.001,
                      yield_point=yp*whole.YP_PA, pv_ref_T=26.7)
    q = sample['flow_gpm']*whole.GPM
    rho = float(m1.fluid_props(np.array([sample['T_in_C']]), np.array([m1.P_SURF]), fluid)[0][0])
    times, clock, depth = clocks[sample['well']]
    exposure = m1.smooth_exposure(m1.exposure_from_history(clock, depth, float(np.interp(sample['time_s'], times, clock))), g.md_bit)
    breaks = m1.exposure_breaks(exposure, g.md_bit)
    result = m1.solve_seeded(exposure, breaks, m_dot=q*rho, T_inj=sample['T_in_C'], geotherm=form,
        geometry=g, target_rock_T=float(form(g.survey.tvd(g.md_bit))),
        Q_face=sample['motor_heat_psi']*whole.PSI*q, k_rock=b.K_ROCK, rhocp_rock=b.RHOCP_ROCK,
        friction_heat=True, tfa=sample['tfa_m2'], film_mult=1., fluid=fluid, verbose=False,
        hydraulics_model='v1.6.0', surface=hl.SurfaceLoss.api_case(5), rock_response=response)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('predictions.csv'))
    args = parser.parse_args()
    started = time.perf_counter()
    plan = score.read_json(score.PLAN)
    ta, ca, da, _ = energy.clock_a(ROOT/'validation/forge16a')
    _, tb, cb, db = whole.clock(ROOT/'validation/forge16b')
    clocks = {'16A': (ta, ca, da), '16B': (tb, cb, db)}
    samples = [s for s in plan['samples'] if not (s['well'] == '16A' and s.get('source') != 'Sanvean on-bottom')]
    rows = []
    for sample in select(samples):
        row = dict(well=sample['well'], bha=sample['run'], sample_id=sample['id'], bit_ft=sample['bit_ft'])
        results = {name: solve(sample, plan, clocks, name) for name in ('logarithmic', 'cylinder')}
        row.update(success=all(r['success'] for r in results.values()))
        for name, r in results.items():
            row[f'{name}_bit_C'] = float(r['Td'][-1])
            row[f'{name}_return_C'] = float(r['Tu'][0])
        row.update(bit_change_C=row['cylinder_bit_C']-row['logarithmic_bit_C'],
                   return_change_C=row['cylinder_return_C']-row['logarithmic_return_C'])
        rows.append(row)
        print(row['well'], row['bha'], round(row['bit_change_C'], 2), round(row['return_change_C'], 2), flush=True)
    with args.output.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    print(dict(windows=len(rows), failures=sum(not r['success'] for r in rows), runtime_s=round(time.perf_counter()-started, 1)))


if __name__ == '__main__':
    main()
