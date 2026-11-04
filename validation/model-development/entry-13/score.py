"""Score tapered joint variants with the entry 12 procedure.

Circulation uses the entry 8 rotary sources and rheology, with entry 10's
geometry and pipe friction. Run-in keeps the existing observed initial
fluid state, static history and Dittus-Boelter films; its conditioning
circulation receives the candidate pipe friction. No transient equation
changes. The saved entry 10 smooth calculation supplies the working comparison;
entry 12's archive supplies installed_primary and installed_no_local.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import shutil
import time
from types import SimpleNamespace

import numpy as np
import scipy

from predict import load, geometry as candidate_geometry, apply_geometry

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DECLARATION = ''
adapter = load('entry8_score', HERE.parent/'entry-8/score.py')
frozen = adapter.score
m1, energy = adapter.m1, adapter.energy
VARIANTS = ('working','tapered_primary','tapered_long','tapered_steep','tapered_pin_length')


def typed(path):
    rows = frozen.read_csv(path)
    for row in rows:
        for key, value in row.items():
            if key in ('success', 'calibrated_insulation', 'energy_flagged', 'archived_available', 'deep_run'):
                row[key] = value == 'True'
            elif value == '':
                row[key] = None
            elif key not in ('sample_id', 'well', 'bha', 'event_id', 'group'):
                try:
                    row[key] = float(value)
                except ValueError:
                    pass
    return rows


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(variant, output, scratch):
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    if (output/'manifest.json').exists():
        manifest = frozen.read_json(output/'manifest.json')
        for name, digest in manifest['results_sha256'].items():
            if sha(output/name) != digest:
                raise ValueError(f'Changed completed result: {variant}/{name}')
        print(f'{variant}: completed archive verified', flush=True)
        return
    started = time.perf_counter()
    plan = frozen.read_json(frozen.PLAN)
    options = frozen.read_json(HERE/'options.json')
    archived = HERE.parent/'entry-10/results/smooth'
    if variant == 'working':
        for name in ('circulation.csv', 'run-in.csv', 'scoreboard.csv'):
            shutil.copy2(archived/name, output/name)
        rows, events = typed(output/'circulation.csv'), typed(output/'run-in.csv')
        # The parser must preserve the frozen reductions before any new solve.
        expected = typed(output/'scoreboard.csv')
        actual = frozen.scoreboard(rows, events)
        assert len(expected) == len(actual)
        for old, new in zip(expected, actual):
            for key, value in new.items():
                if isinstance(value, (int, float)):
                    assert abs(value-old[key]) < 1e-9, (key, value, old[key])
                else:
                    assert value == old[key], (key, value, old[key])
        new_solves = reused = 0
    else:
        original_geometry, original_solve = frozen.geometry, m1.solve_seeded
        original_fluid, original_run_in = energy.fluid_for, frozen.RunIn
        rotary = adapter.rotary.Rotary(plan, original_geometry)
        geometry_context = SimpleNamespace(plan=plan, whole=adapter.whole,
            score=SimpleNamespace(geometry=original_geometry, wg=frozen.wg))
        state, applied = {}, []
        friction = options['variants'][variant]['friction']
        roughness = options['variants'][variant]['roughness_m']

        def geometry(sample, plan_, mode):
            state['sample'] = sample
            return candidate_geometry(geometry_context, sample, variant)

        def fluid_for(sample, mode):
            if sample['well'] == '16B' and mode == 's1_original':
                mode = 's2_revised'
            fluid, pv, yp = adapter.FROZEN_FLUID(sample, mode)
            state['yp'] = yp
            return fluid, pv, yp

        def solve(*args, **kw):
            sample = state.get('sample')
            kw['friction'], kw['roughness'] = friction, roughness
            if sample is not None:
                heat, basis = rotary.heat(sample)
                kw['Q_face'] += heat.bit_W
                kw['film_mult'] = 1.
                kw['annulus_heat'] = heat.annulus
                kw['annulus_model'] = adapter.MODEL
                kw['fluid'].rheology = adapter.hypotheses.rheology(
                    sample, kw['fluid'], state['yp'], 'no-yield')
                applied.append(dict(sample_id=sample['id'], well=sample['well'], bha=sample['run'],
                    bit_W=heat.bit_W, friction_W=heat.friction_W, factor_basis=basis))
            return original_solve(*args, **kw)

        class RunIn(original_run_in):
            def geometry(self, run_, bit):
                return apply_geometry(super().geometry(run_,bit),'16A',variant)

        rows = typed(output/'circulation.csv') if (output/'circulation.csv').exists() else []
        done = {r['sample_id'] for r in rows}
        reused = 0
        todo = [s for s in plan['samples'] if s['id'] not in done]
        frozen.geometry, m1.solve_seeded, energy.fluid_for = geometry, solve, fluid_for
        frozen.RunIn = RunIn
        try:
            for start in range(0, len(todo), 25):
                batch = {**plan, 'samples': todo[start:start+25]}
                chunk = frozen.circulation(batch, 'current', scratch)
                rows.extend({**r, 'candidate': variant, 'calculation_basis': 'calculated'} for r in chunk)
                by_id = {r['sample_id']: r for r in rows}
                rows = [by_id[s['id']] for s in plan['samples'] if s['id'] in by_id]
                frozen.write_csv(output/'circulation.csv', rows)
                print(f'{variant}: {len(rows)}/{len(plan["samples"])} circulation rows, '
                      f'{time.perf_counter()-started:.0f} s', flush=True)
            state['sample'] = None
            if (output/'run-in.csv').exists():
                events = typed(output/'run-in.csv')
            else:
                print(f'{variant}: run-in conditioning and transients', flush=True)
                events = frozen.run_in(frozen.read_json(frozen.HERE/'transient-inputs.json'),
                                       'current', plan, output)
            frozen.write_csv(output/'scoreboard.csv', frozen.scoreboard(rows, events))
            if applied:
                frozen.write_csv(output/'rotary-heat-applied.csv', applied)
        finally:
            frozen.geometry, m1.solve_seeded = original_geometry, original_solve
            energy.fluid_for, frozen.RunIn = original_fluid, original_run_in
        new_solves = len(plan['samples'])-reused
    assert len(rows) == len(plan['samples'])
    model_sources = ['model1_coupled.py', 'hydraulic_losses.py', 'fluids.py', 'well_geometry.py',
                     'rock_response.py', 'rotary_heat.py', 'studies/pressure_comparison.py']
    manifest = dict(declaration_commit=DECLARATION, variant=variant, complete=True,
        python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
        settings=options, circulation_rows=len(rows), new_circulation_calculations=new_solves,
        reused_circulation_rows=reused, before_source=archived.relative_to(ROOT).as_posix(),
        baseline_reuse=variant == 'working',
        run_in_basis=('entry 10 smooth archive' if variant == 'working' else
            'existing transient calculation with candidate conditioning friction; original initial-state convention and Dittus-Boelter films'),
        circulation_failures=[r['sample_id'] for r in rows if not r['success']],
        energy_flags=[r['sample_id'] for r in rows if r.get('energy_flagged')],
        run_in_failures=[r['event_id'] for r in events if r['archived_available'] and not r['success']],
        run_in_originally_unavailable=[r['event_id'] for r in events if not r['archived_available']],
        installed_tool_uncertainty='unquantified; no installed-tool loss band available; no additional tool source',
        source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in
            (Path(__file__), HERE/'predict.py', HERE/'options.json', HERE.parent/'entry-12/predict.py', HERE.parent/'entry-12/options.json', HERE.parent/'entry-8/score.py',
             frozen.PLAN, frozen.HERE/'scoreboard.py', frozen.HERE/'transient-inputs.json',
             HERE.parent/'entry-4/rotary.py', HERE.parent/'entry-4/rotary_inputs.csv',
             HERE.parent/'entry-6/hypotheses.py')},
        model_sha256={name: sha(ROOT/'src/borethm'/name) for name in model_sources},
        results_sha256={p.name: sha(p) for p in output.glob('*.csv')},
        runtime_s=time.perf_counter()-started)
    frozen.write_json(output/'manifest.json', manifest)
    print(f'{variant}: complete; {len(manifest["circulation_failures"])} circulation failures, '
          f'{len(manifest["run_in_failures"])} run-in failures; {manifest["runtime_s"]:.0f} s', flush=True)


def main():
    global DECLARATION
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--declaration',required=True)
    parser.add_argument('--variants', nargs='+', choices=VARIANTS, default=list(VARIANTS))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(ROOT.resolve()):parser.error('Bulk score output must be outside the repository')
    DECLARATION=args.declaration
    for variant in args.variants:
        run(variant, args.output/variant, args.scratch/variant)


if __name__ == '__main__':
    main()
