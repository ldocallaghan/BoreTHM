"""Model-only predictions for entry 6, before its score.

The windows of entries 3 and 4: one per assembly, at the lower median
bit-depth rank among the frozen circulation samples (16A Sanvean on-bottom
and 16B). Each is solved with the working calculation (entries 1-5 with D5:
entry 4's rotary heat and entry 5's S2 mud for 16B), once with the current
annulus (annulus_model 'v1.6.0') and once under each declared yield-stress
hypothesis (hypotheses.py) with annulus_model 'herschel-bulkley', started
from the working solution (hypotheses.solve_continued). For each
it reports the bit and return temperatures, the standpipe pressure and the
share of the drill-pipe annulus that the slot model puts in laminar,
transitional and turbulent flow at the solved temperatures. The inputs are
the frozen operating inputs, the rotary inputs, the mud records and the
gel inputs; no scored temperature or pressure target, and no residual, is
read.
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
hypotheses = load('entry6_hypotheses', HERE/'hypotheses.py')
score, m1, whole, energy = entry3.score, entry3.m1, entry3.whole, entry3.energy
from borethm import fluids  # noqa: E402

FROZEN_FLUID = energy.fluid_for


def fluid_for(sample, mode):
    """Entry 5: the 16B S2 mud wherever the scoreboard asks for S1."""
    if sample['well'] == '16B' and mode == 's1_original':
        mode = 's2_revised'
    return FROZEN_FLUID(sample, mode)


def solve(sample, plan, clocks, heat, name):
    """The working calculation; name None for the current annulus, or a
    hypothesis name for annulus_model 'herschel-bulkley'."""
    q = sample['flow_gpm']*whole.GPM
    face = sample['motor_heat_psi']*whole.PSI*q
    original = m1.solve_seeded
    _, pv, yp = fluid_for(sample, 's1_original')

    def attach(fluid):
        if name is not None:
            fluid.rheology = hypotheses.rheology(sample, fluid, yp, name)
        return fluid

    def patched(*a, **kw):
        kw['Q_face'] = face+heat.bit_W
        attach(kw['fluid'])
        if name is None:
            return original(*a, annulus_heat=heat.annulus, **kw)
        return hypotheses.solve_continued(original, *a, annulus_heat=heat.annulus, **kw)
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


def regime_shares(r, fluid, m_dot):
    """Shares of drill-pipe annulus length with blend 0 (laminar), between
    and 1 (turbulent) in the slot model at the solved annulus temperatures."""
    g = r['geometry']
    edges = np.linspace(0, g.md_bit, 401)
    z = .5*(edges[1:]+edges[:-1]); dz = np.diff(edges)
    pipe = np.array([g.string[i].pipe.hydraulic_joint is not None for i in g.segment_index(z)])
    geo = g.at(z)
    T = r['sol'].sol(z)[1]
    rho, _, mu, _ = m1.fluid_props(T, m1.P_of_z(g.survey.tvd(z)), fluid)
    tau0, K, n = fluid.rheology.at(T, mu, fluid)
    state = fluids.hb_annulus(rho, tau0, K, n, m_dot/(rho*geo['A_ann']), geo['Dh_ann'])
    b, w = state['blend'][pipe], dz[pipe]
    total = w.sum()
    return dict(laminar=float(w[b == 0].sum()/total), transitional=float(w[(b > 0) & (b < 1)].sum()/total),
                turbulent=float(w[b == 1].sum()/total), re_median=float(np.median(state['re'][pipe])),
                re2_median=float(np.median(state['re2'][pipe])))


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
    windows = entry3.select(samples)
    rows = []
    for j, sample in enumerate(windows, 1):
        heat, _ = source.heat(sample)
        r0, h0, _, _ = solve(sample, plan, clocks, heat, None)
        gel = hypotheses.GELS[sample['well'], sample['run']]
        row = dict(well=sample['well'], bha=sample['run'], sample_id=sample['id'], bit_ft=sample['bit_ft'],
                   gel_10s_lbf_100ft2=gel, current_bit_C=float(r0['Td'][-1]), current_return_C=float(r0['Tu'][0]),
                   current_spp_psi=h0['spp']/whole.PSI)
        ok = bool(r0['success'])
        for name in hypotheses.HYPOTHESES:
            r, h, fluid, m_dot = solve(sample, plan, clocks, heat, name)
            ok = ok and bool(r['success'])
            shares = regime_shares(r, fluid, m_dot)
            row.update({f'{name}_bit_change_C': float(r['Td'][-1])-row['current_bit_C'],
                        f'{name}_return_change_C': float(r['Tu'][0])-row['current_return_C'],
                        f'{name}_spp_change_psi': h['spp']/whole.PSI-row['current_spp_psi'],
                        **{f'{name}_pipe_annulus_{k}': v for k, v in shares.items()}})
        row['success'] = ok
        rows.append(row)
        print(f'[{j}/{len(windows)}]', row['well'], row['bha'],
              {n: (round(row[f'{n}_bit_change_C'], 2), round(row[f'{n}_spp_change_psi']),
                   round(row[f'{n}_pipe_annulus_laminar'], 2)) for n in hypotheses.HYPOTHESES}, flush=True)
    with args.output.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    print(dict(windows=len(rows), failures=sum(not r['success'] for r in rows),
               runtime_s=round(time.perf_counter()-started, 1)))


if __name__ == '__main__':
    main()
