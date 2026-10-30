"""Score one entry 6 hypothesis with the frozen scoreboard functions.

The working calculation is entry 5's: the frozen `circulation` and `run_in`
functions in current mode, with each circulation sample's rotary heat (entry
4) and the S2 mud for 16B (entry 5). Entry 6 attaches the named hypothesis's
Herschel-Bulkley rheology (hypotheses.py) to every circulation sample's mud
and solves with annulus_model 'herschel-bulkley', started from the working
solution (hypotheses.solve_continued). The standpipe budget inherits the
annulus model and uses the same mud. Run-in transients keep their
Dittus-Boelter films and the working calculation's conditioning solve.
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
hypotheses = load('entry6_hypotheses', HERE/'hypotheses.py')
energy = score.energy
FROZEN_FLUID = energy.fluid_for
m1, whole = score.m1, score.whole


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hypothesis', choices=list(hypotheses.HYPOTHESES), required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or HERE/'results'/args.hypothesis
    if output.exists() and any(output.iterdir()):
        parser.error('Choose an empty output directory for a complete comparison')
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    plan = score.read_json(score.PLAN)
    inputs = score.read_json(score.HERE/'transient-inputs.json')
    source = rotary.Rotary(plan, score.geometry)
    frozen_geometry, frozen_solve = score.geometry, m1.solve_seeded
    state, applied, mud, rheology = {}, [], [], []

    def geometry(sample, plan_, mode):
        state['sample'] = sample
        return frozen_geometry(sample, plan_, mode)

    def fluid_for(sample, mode):
        if sample['well'] == '16B' and mode == 's1_original':
            mode = 's2_revised'
            mud.append(sample['id'])
        fluid, pv, yp = FROZEN_FLUID(sample, mode)
        state['yp'] = yp
        return fluid, pv, yp

    def solve(*a, **kw):
        sample = state.get('sample')
        if sample is None:
            return frozen_solve(*a, **kw)
        heat, basis = source.heat(sample)
        applied.append(dict(sample_id=sample['id'], well=sample['well'], bha=sample['run'],
                            friction_factor=heat.friction_factor, factor_basis=basis, capped=heat.capped,
                            friction_W=heat.friction_W, bit_W=heat.bit_W))
        kw['Q_face'] = kw['Q_face']+heat.bit_W
        if len(applied) % 25 == 0:
            print(f'{len(applied)} of {len(plan["samples"])} circulation samples, '
                  f'{time.perf_counter()-started:.0f} s', flush=True)
        fluid = kw['fluid']
        fluid.rheology = hypotheses.rheology(sample, fluid, state['yp'], args.hypothesis)
        r = fluid.rheology
        rheology.append(dict(sample_id=sample['id'], well=sample['well'], bha=sample['run'],
                             gel_10s_lbf_100ft2=hypotheses.GELS[sample['well'], sample['run']],
                             tau0_Pa=r.tau0, n=r.n, K_Pa_sn=r.K, rise_T_star_K=None if r.rise is None else r.rise[0],
                             rise_E_H_K=None if r.rise is None else r.rise[1]))
        return hypotheses.solve_continued(frozen_solve, *a, annulus_heat=heat.annulus, **kw)

    score.geometry, m1.solve_seeded, energy.fluid_for = geometry, solve, fluid_for
    try:
        rows = score.circulation(plan, 'current', output)
        state['sample'] = None
        events = score.run_in(inputs, 'current', plan, output)
    finally:
        score.geometry, m1.solve_seeded, energy.fluid_for = frozen_geometry, frozen_solve, FROZEN_FLUID
    score.write_csv(output/'scoreboard.csv', score.scoreboard(rows, events))
    score.write_csv(output/'rotary-heat-applied.csv', applied)
    score.write_csv(output/'rheology-applied.csv', rheology)
    model_sources = ['model1_coupled.py', 'rotary_heat.py', 'rock_response.py', 'hydraulic_losses.py', 'fluids.py',
                     'well_geometry.py', 'studies/pressure_comparison.py']
    manifest = dict(mode=f'current with entries 4 and 5 and the entry 6 Herschel-Bulkley annulus, hypothesis {args.hypothesis}',
        settings=dict(pv_ref_T_C=26.7, film_multiplier=1., exposure='cumulative', annulus_model='herschel-bulkley',
                      hypothesis=args.hypothesis, **{k: v for k, v in hypotheses.HYPOTHESES[args.hypothesis].items()},
                      mud='16A recorded mud; 16B S2 mud (s2_revised); 10-s gels from gel_inputs.csv'),
        calibration='Historical fitted trial insulation conductivity retained; friction factors from off-bottom torque',
        versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
        sources_sha256={p.relative_to(ROOT).as_posix(): score.sha(p) for p in
                        (score.PLAN, score.HERE/'transient-inputs.json', Path(score.__file__),
                         ROOT/'validation/model-development/entry-4/rotary_inputs.csv',
                         ROOT/'validation/model-development/entry-4/rotary.py', HERE/'gel_inputs.csv',
                         HERE/'hypotheses.py', Path(__file__))},
        model_sources_sha256={name: score.sha(ROOT/'src/borethm'/name) for name in model_sources},
        results_sha256={p.name: score.sha(p) for p in sorted(output.glob('*.csv'))},
        runtime_s=time.perf_counter()-started)
    score.write_json(output/'manifest.json', manifest)
    print(json.dumps(dict(hypothesis=args.hypothesis, runtime_s=manifest['runtime_s'], circulation_cases=len(rows),
        circulation_failures=sum(not r['success'] for r in rows), heat_applications=len(applied),
        rheology_applications=len(rheology), revised_mud_samples=len(set(mud)),
        run_in_failures=sum(r['archived_available'] and not r['success'] for r in events)), indent=2), flush=True)


if __name__ == '__main__':
    main()
