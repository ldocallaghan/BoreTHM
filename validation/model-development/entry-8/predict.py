"""Model-only predictions for entry 8, before its score.

Entry 8 makes entry 7's annulus treatment, with no yield stress, the working
calculation: annulus_model 'herschel-bulkley-erge' with each mud's power-law
fit to its PV and YP (entry 6's hypothesis 'no-yield'), solved from the
usual seeds. For the windows of entries 3 and 4 this script reports:

- the change from the working calculation in bit and return temperature
  and standpipe pressure;
- the shares of drill-pipe annulus length that each calculation's pressure
  loss and heat transfer treat as laminar, at its own solved temperatures:
  the working calculation's Bingham pressure criterion (apparent-viscosity
  Reynolds number <= 2100) and its heat-transfer criterion (Reynolds number
  on PV < 2300), and entry 8's single criterion (Erge et al. band);
- the bit temperature with entry 8's annulus film coefficients scaled by
  0.85 and 1.05, the uncertainty band declared in the development log;
- the shares of drill-pipe annulus that would be transitional if the
  downhole yield stress equalled the 10-s gel, from entry 7's predictions.

The inputs are the frozen operating inputs, the rotary inputs, the mud
records and the gel inputs; no scored temperature or pressure target, and
no residual, is read.
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
hypotheses = load('entry6_hypotheses', ROOT/'validation/model-development/entry-6/hypotheses.py')
score, m1, whole, energy = entry3.score, entry3.m1, entry3.whole, entry3.energy
from borethm import fluids  # noqa: E402

MODEL = 'herschel-bulkley-erge'
FROZEN_FLUID = energy.fluid_for
BAND = (0.85, 1.05)


def fluid_for(sample, mode):
    """Entry 5: the 16B S2 mud wherever the scoreboard asks for S1."""
    if sample['well'] == '16B' and mode == 's1_original':
        mode = 's2_revised'
    return FROZEN_FLUID(sample, mode)


def solve(sample, plan, clocks, heat, candidate, film=1.0):
    """The working calculation (candidate False) or entry 8's (True), with
    the annulus film coefficients scaled by film."""
    q = sample['flow_gpm']*whole.GPM
    face = sample['motor_heat_psi']*whole.PSI*q
    original = m1.solve_seeded
    _, pv, yp = fluid_for(sample, 's1_original')

    def attach(fluid):
        if candidate:
            fluid.rheology = hypotheses.rheology(sample, fluid, yp, 'no-yield')
        return fluid

    def patched(*a, **kw):
        kw['Q_face'] = face+heat.bit_W
        kw['film_mult'] = film
        attach(kw['fluid'])
        if candidate:
            kw['annulus_model'] = MODEL
        return original(*a, annulus_heat=heat.annulus, **kw)
    m1.solve_seeded, energy.fluid_for = patched, fluid_for
    try:
        r = entry3.solve(sample, plan, clocks, 'cylinder')
    finally:
        m1.solve_seeded, energy.fluid_for = original, FROZEN_FLUID
    fluid = attach(score.Mud(sample['density_ppg']*whole.PPG, pv_ref=None if pv is None else pv*.001,
                             yield_point=yp*whole.YP_PA, pv_ref_T=26.7))
    rho = float(m1.fluid_props(np.array([sample['T_in_C']]), np.array([m1.P_SURF]), fluid)[0][0])
    hyd = m1.hydraulics(q*rho, r['geometry'], result=r, tfa=sample['tfa_m2'], fluid=fluid)
    return r, hyd, fluid, q*rho


def laminar_shares(r, fluid, m_dot, candidate):
    """Shares of drill-pipe annulus length treated as laminar by the pressure
    loss and by the heat transfer, at the solved annulus temperatures."""
    g = r['geometry']
    edges = np.linspace(0, g.md_bit, 401)
    z = .5*(edges[1:]+edges[:-1]); dz = np.diff(edges)
    pipe = np.array([g.string[i].pipe.hydraulic_joint is not None for i in g.segment_index(z)])
    geo = g.at(z)
    T = r['sol'].sol(z)[1]
    rho, _, mu, _ = m1.fluid_props(T, m1.P_of_z(g.survey.tvd(z)), fluid)
    v = m_dot/(rho*geo['A_ann'])
    w = dz[pipe]/dz[pipe].sum()
    if candidate:
        tau0, K, n = fluid.rheology.at(T, mu, fluid)
        state = fluids.hb_annulus(rho, tau0, K, n, v, geo['Dh_ann'], band='erge', kappa=geo['r_out']/geo['r_wall'])
        laminar = state['blend'] == 0
        return float(w @ laminar[pipe]), float(w @ laminar[pipe])
    _, re_a = fluids.bingham_gradient(rho, mu, fluid.yield_point, v, geo['Dh_ann'], True)
    pressure = (re_a <= fluids.RE_CRITICAL) if fluid.yield_point > 0 else (rho*v*geo['Dh_ann']/mu < 2300)
    heat = rho*v*geo['Dh_ann']/mu < 2300
    return float(w @ pressure[pipe]), float(w @ heat[pipe])


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
    samples = [s for s in plan['samples'] if not (s['well'] == '16A' and s.get('source') != 'Sanvean on-bottom')]
    gel_regime = {(r['well'], r['bha']): r for r in
                  csv.DictReader(open(ROOT/'validation/model-development/entry-7/predictions.csv', encoding='utf-8'))}
    rows = []
    windows = entry3.select(samples)
    for j, sample in enumerate(windows, 1):
        heat, _ = source.heat(sample)
        r0, h0, f0, m0 = solve(sample, plan, clocks, heat, False)
        r8, h8, f8, m8 = solve(sample, plan, clocks, heat, True)
        p0, t0 = laminar_shares(r0, f0, m0, False)
        p8, _ = laminar_shares(r8, f8, m8, True)
        row = dict(well=sample['well'], bha=sample['run'], sample_id=sample['id'], bit_ft=sample['bit_ft'],
                   success=bool(r0['success'] and r8['success']),
                   working_bit_C=float(r0['Td'][-1]), working_return_C=float(r0['Tu'][0]), working_spp_psi=h0['spp']/whole.PSI,
                   bit_change_C=float(r8['Td'][-1]-r0['Td'][-1]), return_change_C=float(r8['Tu'][0]-r0['Tu'][0]),
                   spp_change_psi=(h8['spp']-h0['spp'])/whole.PSI,
                   working_pressure_laminar_share=p0, working_heat_laminar_share=t0, entry8_laminar_share=p8)
        for film in BAND:
            rf, _, _, _ = solve(sample, plan, clocks, heat, True, film)
            row['success'] = row['success'] and bool(rf['success'])
            row[f'film_{film:.2f}_bit_change_C'] = float(rf['Td'][-1]-r8['Td'][-1])
        g = gel_regime[sample['well'], sample['run']]
        row['gel_transitional_share'] = float(g['gel_pipe_annulus_transitional'])
        row['gel_laminar_share'] = float(g['gel_pipe_annulus_laminar'])
        rows.append(row)
        print(f'[{j}/{len(windows)}]', row['well'], row['bha'], round(row['bit_change_C'], 2),
              'laminar shares', round(p0, 2), round(t0, 2), round(p8, 2),
              'band', round(row['film_0.85_bit_change_C'], 2), round(row['film_1.05_bit_change_C'], 2), flush=True)
    with args.output.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    print(dict(windows=len(rows), failures=sum(not r['success'] for r in rows),
               runtime_s=round(time.perf_counter()-started, 1)))


if __name__ == '__main__':
    main()
