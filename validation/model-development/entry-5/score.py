"""Score entry 5 with the frozen scoreboard functions.

The working calculation is entry 4's: the frozen `circulation` and `run_in`
functions in current mode, with each circulation sample's rotary heat (see
entry 4's score.py). Entry 5 changes one input rule. Where the frozen
functions ask for a 16B sample's original S1 mud ("s1_original"), they
receive its S2 mud ("s2_revised"). 16A muds and the run-in inputs are
unchanged.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import time

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


score = load('frozen_scoreboard', ROOT/'validation/scoreboard/scoreboard.py')
rotary = load('entry4_rotary', ROOT/'validation/model-development/entry-4/rotary.py')
energy = score.energy
FROZEN_FLUID = energy.fluid_for
m1, whole = score.m1, score.whole


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'results')
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Choose an empty output directory for a complete comparison')
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    plan = score.read_json(score.PLAN)
    inputs = score.read_json(score.HERE/'transient-inputs.json')
    source = rotary.Rotary(plan, score.geometry)
    frozen_geometry, frozen_solve = score.geometry, m1.solve_seeded
    state, applied = {}, []

    def geometry(sample, plan_, mode):
        state['sample'] = sample
        return frozen_geometry(sample, plan_, mode)

    def solve(*a, **kw):
        sample = state.get('sample')
        if sample is None:
            return frozen_solve(*a, **kw)
        heat, basis = source.heat(sample)
        applied.append(dict(sample_id=sample['id'], well=sample['well'], bha=sample['run'],
                            friction_factor=heat.friction_factor, factor_basis=basis, capped=heat.capped,
                            friction_W=heat.friction_W, bit_W=heat.bit_W))
        kw['Q_face'] = kw['Q_face']+heat.bit_W
        return frozen_solve(*a, annulus_heat=heat.annulus, **kw)

    mud = []

    def fluid_for(sample, mode):
        if sample['well'] == '16B' and mode == 's1_original':
            mode = 's2_revised'
            mud.append(sample['id'])
        return FROZEN_FLUID(sample, mode)

    score.geometry, m1.solve_seeded, energy.fluid_for = geometry, solve, fluid_for
    try:
        rows = score.circulation(plan, 'current', args.output)
        state['sample'] = None
        events = score.run_in(inputs, 'current', plan, args.output)
    finally:
        score.geometry, m1.solve_seeded, energy.fluid_for = frozen_geometry, frozen_solve, FROZEN_FLUID
    score.write_csv(args.output/'scoreboard.csv', score.scoreboard(rows, events))
    score.write_csv(args.output/'rotary-heat-applied.csv', applied)
    model_sources = ['model1_coupled.py', 'rotary_heat.py', 'rock_response.py', 'hydraulic_losses.py', 'fluids.py',
                     'well_geometry.py', 'studies/pressure_comparison.py']
    manifest = dict(mode='current with entry 4 rotary heat and entry 5 16B mud', settings=dict(pv_ref_T_C=26.7, film_multiplier=1.,
                    exposure='cumulative', mud='16A recorded mud; 16B S2 mud (s2_revised)'),
        calibration='Historical fitted trial insulation conductivity retained; friction factors from off-bottom torque',
        versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
        sources_sha256={p.relative_to(ROOT).as_posix(): score.sha(p) for p in
                        (score.PLAN, score.HERE/'transient-inputs.json', Path(score.__file__),
                         ROOT/'validation/model-development/entry-4/rotary_inputs.csv',
                         ROOT/'validation/model-development/entry-4/rotary.py', Path(__file__))},
        model_sources_sha256={name: score.sha(ROOT/'src/borethm'/name) for name in model_sources},
        results_sha256={p.name: score.sha(p) for p in sorted(args.output.glob('*.csv'))},
        runtime_s=time.perf_counter()-started)
    score.write_json(args.output/'manifest.json', manifest)
    print(json.dumps(dict(runtime_s=manifest['runtime_s'], circulation_cases=len(rows),
        circulation_failures=sum(not r['success'] for r in rows), heat_applications=len(applied),
        revised_mud_requests=len(mud), revised_mud_samples=len(set(mud)),
        run_in_failures=sum(r['archived_available'] and not r['success'] for r in events)), indent=2), flush=True)


if __name__ == '__main__':
    main()
