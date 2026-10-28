"""Model-only predictions for entry 4, before its score.

The same windows as entry 3: one per assembly, at the lower median bit-depth
rank among the frozen circulation samples. Each is solved with the working
calculation (entry 1 with D5 and entry 3), without and with rotary heat.
Rotary inputs are surface speed, torque and weight on bit; no measured
temperature, pressure or residual is read.
"""
import argparse
import csv
import importlib.util
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


entry3 = load('entry3_predict', ROOT/'validation/model-development/entry-3/predict.py')
rotary = load('entry4_rotary', HERE/'rotary.py')
score, m1, whole = entry3.score, entry3.m1, entry3.whole


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'predictions.csv')
    args = parser.parse_args()
    started = time.perf_counter()
    plan = score.read_json(score.PLAN)
    ta, ca, da, _ = entry3.energy.clock_a(ROOT/'validation/forge16a')
    _, tb, cb, db = whole.clock(ROOT/'validation/forge16b')
    clocks = {'16A': (ta, ca, da), '16B': (tb, cb, db)}
    source = rotary.Rotary(plan, score.geometry)
    samples = [s for s in plan['samples'] if not (s['well'] == '16A' and s.get('source') != 'Sanvean on-bottom')]
    rows = []
    original = m1.solve_seeded
    for sample in entry3.select(samples):
        heat, basis = source.heat(sample)
        base = entry3.solve(sample, plan, clocks, 'cylinder')
        q = sample['flow_gpm']*whole.GPM
        face = sample['motor_heat_psi']*whole.PSI*q

        def patched(*a, **kw):
            kw['Q_face'] = face+heat.bit_W
            return original(*a, annulus_heat=heat.annulus, **kw)
        m1.solve_seeded = patched
        try:
            added = entry3.solve(sample, plan, clocks, 'cylinder')
        finally:
            m1.solve_seeded = original
        row = dict(well=sample['well'], bha=sample['run'], sample_id=sample['id'], bit_ft=sample['bit_ft'],
                   friction_factor=heat.friction_factor, factor_basis=basis, capped=heat.capped,
                   rotary_power_kW=(heat.bit_W+heat.friction_W)/1e3, friction_kW=heat.friction_W/1e3,
                   bit_kW=heat.bit_W/1e3, success=bool(base['success'] and added['success']),
                   bit_change_C=float(added['Td'][-1]-base['Td'][-1]),
                   return_change_C=float(added['Tu'][0]-base['Tu'][0]))
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
