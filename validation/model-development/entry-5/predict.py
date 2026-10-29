"""Model-only predictions for entry 5, before its score.

The 16B windows of entries 3 and 4: one per assembly, at the lower median
bit-depth rank among the frozen circulation samples. Each is solved with the
working calculation (entry 1 with D5, entry 3 and entry 4's rotary heat),
once with the scoreboard's original 16B mud ("s1_original") and once with
the S2 mud ("s2_revised"). The inputs are the frozen operating inputs, the
rotary inputs and the two mud records; no scored temperature or pressure
target, and no residual, is read. 16A is unchanged by this entry.
"""
import argparse
import csv
import importlib.util
from pathlib import Path
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


entry3 = load('entry3_predict', ROOT/'validation/model-development/entry-3/predict.py')
rotary = load('entry4_rotary', ROOT/'validation/model-development/entry-4/rotary.py')
score, m1, whole, energy = entry3.score, entry3.m1, entry3.whole, entry3.energy
FROZEN_FLUID = energy.fluid_for


def with_mud(case):
    """fluid_for with the scoreboard's 16B mud rule replaced by case."""
    def fluid_for(sample, mode):
        if sample['well'] == '16B' and mode == 's1_original':
            mode = case
        return FROZEN_FLUID(sample, mode)
    return fluid_for


def solve(sample, plan, clocks, heat, case):
    q = sample['flow_gpm']*whole.GPM
    face = sample['motor_heat_psi']*whole.PSI*q
    original = m1.solve_seeded

    def patched(*a, **kw):
        kw['Q_face'] = face+heat.bit_W
        return original(*a, annulus_heat=heat.annulus, **kw)
    m1.solve_seeded, energy.fluid_for = patched, with_mud(case)
    try:
        r = entry3.solve(sample, plan, clocks, 'cylinder')
        _, pv, yp = energy.fluid_for(sample, 's1_original')
    finally:
        m1.solve_seeded, energy.fluid_for = original, FROZEN_FLUID
    fluid = score.Mud(sample['density_ppg']*whole.PPG, pv_ref=None if pv is None else pv*.001,
                      yield_point=yp*whole.YP_PA, pv_ref_T=26.7)
    rho = float(m1.fluid_props(np.array([sample['T_in_C']]), np.array([m1.P_SURF]), fluid)[0][0])
    hyd = m1.hydraulics(q*rho, r['geometry'], result=r, tfa=sample['tfa_m2'], fluid=fluid)
    return r, hyd, pv, yp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'predictions.csv')
    args = parser.parse_args()
    started = time.perf_counter()
    plan = score.read_json(score.PLAN)
    ta, ca, da, _ = energy.clock_a(ROOT/'validation/forge16a')
    _, tb, cb, db = whole.clock(ROOT/'validation/forge16b')
    clocks = {'16A': (ta, ca, da), '16B': (tb, cb, db)}
    source = rotary.Rotary(plan, score.geometry)
    samples = [s for s in plan['samples'] if s['well'] == '16B']
    rows = []
    for sample in entry3.select(samples):
        heat, _ = source.heat(sample)
        row = dict(well=sample['well'], bha=sample['run'], sample_id=sample['id'], bit_ft=sample['bit_ft'])
        out = {}
        for case in ('s1_original', 's2_revised'):
            r, hyd, pv, yp = solve(sample, plan, clocks, heat, case)
            out[case] = dict(success=bool(r['success']), pv_cP=pv, yp_lbf_100ft2=yp, bit_C=float(r['Td'][-1]),
                             return_C=float(r['Tu'][0]), spp_psi=hyd['spp']/whole.PSI)
        row['success'] = all(o['success'] for o in out.values())
        for case, values in out.items():
            name = 'original' if case == 's1_original' else 'revised'
            row.update({f'{name}_{k}': v for k, v in values.items() if k != 'success'})
        row.update(bit_change_C=row['revised_bit_C']-row['original_bit_C'],
                   return_change_C=row['revised_return_C']-row['original_return_C'],
                   spp_change_psi=row['revised_spp_psi']-row['original_spp_psi'])
        rows.append(row)
        print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
    with args.output.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    print(dict(windows=len(rows), failures=sum(not r['success'] for r in rows),
               runtime_s=round(time.perf_counter()-started, 1)))


if __name__ == '__main__':
    main()
