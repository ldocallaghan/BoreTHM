"""Body-passage Reynolds numbers at the archived baseline operating windows.

The entry 9 adapter reproduces the entry 8 baseline for the same 22 inputs
as predict.py. Only modelled fields are compared with the saved baseline.
The existing prediction table and figures are read without modification.
No measured target or residual enters this calculation.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import time

import numpy as np
import scipy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'predictions')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    driver = load('entry10_predict', HERE/'predict.py')
    calc = driver.diagnosis.Calculation()
    saved_path = HERE/'predictions/model-only.csv'
    before = hashlib.sha256(saved_path.read_bytes()).hexdigest()
    with saved_path.open(encoding='utf-8', newline='') as f:
        saved = {r['sample_id']: r for r in csv.DictReader(f) if r['variant'] == 'baseline'}
    samples = {s['id']: s for s in calc.plan['samples']}
    rows, checks = [], []
    for i, (identity, old) in enumerate(saved.items(), 1):
        sample = samples[identity]
        g, result, mass = calc.solve(sample)
        fluid, _, _ = calc.fluid(sample)
        hyd = calc.pressure(sample, g, sample['flow_gpm'], sample['T_in_C'], mass, result)
        actual = dict(bit_C=float(result['Td'][-1]), return_C=float(result['Tu'][0]),
                      spp_psi=hyd['spp']/calc.whole.PSI)
        for key, value in actual.items():
            tolerance = 1. if key == 'spp_psi' else .1
            checks.append(dict(sample_id=identity, field=key, archived=float(old[key]),
                replayed=value, difference=value-float(old[key]), tolerance=tolerance,
                passed=bool(result['success'] and abs(value-float(old[key])) <= tolerance)))
        ends = np.cumsum([0., *[s.length for s in g.string]])
        z = np.unique(np.r_[np.linspace(0., g.md_bit, 401), (ends[:-1]+ends[1:])/2])
        temperature = np.interp(z, result['z'], result['Td'])
        prop_p = np.maximum(calc.m1.P_of_z(g.survey.tvd(z)), calc.score.hl.PROPERTY_FLOOR)
        rho, _, mu, _ = calc.m1.fluid_props(np.clip(temperature, 1., 480.), prop_p, fluid)
        state = g.at(z)
        velocity = mass/(rho*state['A_bore'])
        re_pv = rho*velocity*state['Dh_bore']/mu
        mu_app = mu+fluid.yield_point*state['Dh_bore']/(6*velocity)
        re_app = rho*velocity*state['Dh_bore']/mu_app
        loss_model = calc.score.hl.LossModel(g)
        segment_index = g.segment_index(z)
        for j, segment in enumerate(g.string):
            mask = segment_index == j
            if not mask.any():
                continue
            dp_bore = (4.276 if sample['well'] == '16A' else 4.67)*calc.whole.INCH
            role = 'drill-pipe body' if (segment.pipe.hydraulic_joint is not None and
                    np.isclose(2*segment.pipe.r_bore, dp_bore)) else 'assembly body'
            rows.append(dict(well=sample['well'], assembly=sample['run'], sample_id=identity,
                variant='baseline', segment=j, component=segment.pipe.name, role=role,
                md_top_m=ends[j], md_bottom_m=ends[j+1], bore_m=2*segment.pipe.r_bore,
                body_loss_included=not bool(loss_model.replaced[j]), points=int(mask.sum()),
                Re_PV_min=float(re_pv[mask].min()), Re_PV_max=float(re_pv[mask].max()),
                Re_apparent_min=float(re_app[mask].min()), Re_apparent_max=float(re_app[mask].max()),
                body_points_above_1e5=int((re_pv[mask] > 1e5).sum())))
        print(f'{i}/{len(saved)} {sample["well"]} {sample["run"]}', flush=True)
    write(args.output/'body-reynolds.csv', rows)
    write(args.output/'reynolds-baseline-check.csv', checks)
    assert hashlib.sha256(saved_path.read_bytes()).hexdigest() == before
    source_paths = [Path(__file__), HERE/'predict.py', HERE.parent/'entry-9/diagnose.py',
                    calc.score.PLAN, ROOT/'src/borethm/hydraulic_losses.py',
                    ROOT/'src/borethm/model1_coupled.py', ROOT/'src/borethm/fluids.py']
    manifest = dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
        windows=len(saved), runtime_s=time.perf_counter()-started,
        source_variant='baseline', sampling='401 uniform MD stations plus every component midpoint; physical body bore, no joint restriction; solved bore temperatures interpolated as in the pressure budget; 5 MPa property floor',
        definition='Re_PV = rho v D/mu_p; Re_apparent includes the retained pipe yield contribution. The turbulent factor uses Re_PV.',
        targets_compared=False, existing_model_only_csv_sha256=before,
        solver_or_reproduction_failures=sum(not r['passed'] for r in checks),
        source_sha256={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
        output_sha256={name: hashlib.sha256((args.output/name).read_bytes()).hexdigest()
                       for name in ('body-reynolds.csv', 'reynolds-baseline-check.csv')})
    (args.output/'reynolds-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if 'sha256' not in k}), flush=True)


if __name__ == '__main__':
    main()
