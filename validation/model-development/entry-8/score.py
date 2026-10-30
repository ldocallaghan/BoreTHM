"""Score entry 8 with the frozen scoreboard functions.

The working calculation is entry 5's: the frozen `circulation` and `run_in`
functions in current mode, with each circulation sample's rotary heat (entry
4) and the S2 mud for 16B (entry 5). Entry 8 attaches the power-law
rheology through each mud's 600 and 300 rpm readings (entry 6's hypothesis
'no-yield') and solves with annulus_model 'herschel-bulkley-erge' from the
usual seeds (m1.solve_seeded). The annulus film coefficients are scaled by
--film: 1.0 for the score, 0.85 and 1.05 for the declared uncertainty band.
The standpipe budget inherits the annulus model and uses the same mud.
Run-in transients keep their Dittus-Boelter films.

For every circulation sample, regime.csv records the shares of drill-pipe
annulus length that are laminar and transitional at the solved state, and
the shares that would be laminar and transitional at that state if the
yield stress equalled the 10-s gel (entry 6's hypothesis 'gel'). The gel
shares are evaluated without a new solve; they flag where an unmeasured
yield stress would change the flow regime.
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
hypotheses = load('entry6_hypotheses', ROOT/'validation/model-development/entry-6/hypotheses.py')
energy = score.energy
FROZEN_FLUID = energy.fluid_for
m1, whole = score.m1, score.whole
from borethm import fluids  # noqa: E402

MODEL = 'herschel-bulkley-erge'
FILMS = (1.0, 0.85, 1.05)


def regime(result, g, fluid, m_dot, gel):
    """Shares of drill-pipe annulus length laminar and transitional at the
    solved state, under the attached rheology and under gel."""
    edges = np.linspace(0, g.md_bit, 401)
    z = .5*(edges[1:]+edges[:-1]); dz = np.diff(edges)
    pipe = np.array([g.string[i].pipe.hydraulic_joint is not None for i in g.segment_index(z)])
    if not pipe.any():
        return dict(laminar=None, transitional=None, gel_laminar=None, gel_transitional=None)
    geo = g.at(z)
    T = result['sol'].sol(z)[1]
    rho, _, mu, _ = m1.fluid_props(T, m1.P_of_z(g.survey.tvd(z)), fluid)
    v = m_dot/(rho*geo['A_ann'])
    w = dz[pipe]/dz[pipe].sum()
    shares = {}
    for name, rheology in (('', fluid.rheology), ('gel_', gel)):
        tau0, K, n = rheology.at(T, mu, fluid)
        blend = fluids.hb_annulus(rho, tau0, K, n, v, geo['Dh_ann'], band='erge',
                                  kappa=geo['r_out']/geo['r_wall'])['blend']
        shares[name+'laminar'] = float(w @ (blend == 0)[pipe])
        shares[name+'transitional'] = float(w @ ((blend > 0) & (blend < 1))[pipe])
    return shares


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--film', type=float, choices=FILMS, default=1.0)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or HERE/'results'/f'film-{args.film:.2f}'
    if output.exists() and any(output.iterdir()):
        parser.error('Choose an empty output directory for a complete comparison')
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    plan = score.read_json(score.PLAN)
    inputs = score.read_json(score.HERE/'transient-inputs.json')
    source = rotary.Rotary(plan, score.geometry)
    frozen_geometry, frozen_solve = score.geometry, m1.solve_seeded
    state, applied, mud, rheology, regimes = {}, [], [], [], []

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
        kw['film_mult'] = args.film
        if len(applied) % 25 == 0:
            print(f'{len(applied)} of {len(plan["samples"])} circulation samples, '
                  f'{time.perf_counter()-started:.0f} s', flush=True)
        fluid = kw['fluid']
        fluid.rheology = hypotheses.rheology(sample, fluid, state['yp'], 'no-yield')
        r = fluid.rheology
        rheology.append(dict(sample_id=sample['id'], well=sample['well'], bha=sample['run'],
                             tau0_Pa=r.tau0, n=r.n, K_Pa_sn=r.K))
        result = frozen_solve(*a, annulus_heat=heat.annulus, annulus_model=MODEL, **kw)
        row = dict(sample_id=sample['id'], well=sample['well'], bha=sample['run'], success=bool(result['success']))
        if result['success']:
            gel = hypotheses.rheology(sample, fluid, state['yp'], 'gel')
            row.update(regime(result, kw['geometry'], fluid, kw['m_dot'], gel))
        regimes.append(row)
        return result

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
    score.write_csv(output/'regime.csv', regimes)
    model_sources = ['model1_coupled.py', 'rotary_heat.py', 'rock_response.py', 'hydraulic_losses.py', 'fluids.py',
                     'well_geometry.py', 'studies/pressure_comparison.py']
    manifest = dict(mode=f'current with entries 4 and 5 and the entry 8 annulus, film multiplier {args.film:.2f}',
        settings=dict(pv_ref_T_C=26.7, film_multiplier=args.film, exposure='cumulative', annulus_model=MODEL,
                      rheology='power law through the 600 and 300 rpm readings (entry 6 no-yield)',
                      mud='16A recorded mud; 16B S2 mud (s2_revised); 10-s gels from gel_inputs.csv for regime.csv'),
        calibration='Historical fitted trial insulation conductivity retained; friction factors from off-bottom torque',
        versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
        sources_sha256={p.relative_to(ROOT).as_posix(): score.sha(p) for p in
                        (score.PLAN, score.HERE/'transient-inputs.json', Path(score.__file__),
                         ROOT/'validation/model-development/entry-4/rotary_inputs.csv',
                         ROOT/'validation/model-development/entry-4/rotary.py',
                         ROOT/'validation/model-development/entry-6/gel_inputs.csv',
                         ROOT/'validation/model-development/entry-6/hypotheses.py', Path(__file__))},
        model_sources_sha256={name: score.sha(ROOT/'src/borethm'/name) for name in model_sources},
        results_sha256={p.name: score.sha(p) for p in sorted(output.glob('*.csv'))},
        runtime_s=time.perf_counter()-started)
    score.write_json(output/'manifest.json', manifest)
    print(json.dumps(dict(film=args.film, runtime_s=manifest['runtime_s'], circulation_cases=len(rows),
        circulation_failures=sum(not r['success'] for r in rows), heat_applications=len(applied),
        rheology_applications=len(rheology), revised_mud_samples=len(set(mud)),
        run_in_failures=sum(r['archived_available'] and not r['success'] for r in events)), indent=2), flush=True)


if __name__ == '__main__':
    main()
