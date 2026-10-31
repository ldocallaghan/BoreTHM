"""Model-only pressure-option predictions on entry 8's operating inputs.

One lower-median-depth sample per assembly, selected as in entry 3. No
measured target or residual enters the calculation or the output. Geometry,
mud, cumulative exposure and rotary heat use the entry 8 calculation via
entry 9's Calculation adapter. Only the declared friction and joint options
change. Each variant is solved from the usual seeds; no result seeds another
variant. The existing frozen scoreboard is not modified or run here.
"""
import argparse
import csv
from dataclasses import replace
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


diagnosis = load('pressure_diagnosis', HERE.parent/'entry-9/diagnose.py')
selection = load('entry3_selection', HERE.parent/'entry-3/predict.py')
VARIANTS = ('baseline', 'smooth', 'steel', 'gpds', 'fh', 'gradual')


def geometry(calc, sample, variant):
    """Catalogue options change only 16B's 5.5-in drill-pipe connections.

    HWDP retains its recorded bore and geometry. Insulated connections use
    the same transferred catalogue option as regular pipe, flagged in the
    declaration. No coating thickness is inferred from the patent.
    """
    g = calc.score.geometry(sample, calc.plan, 'current')
    string = []
    for segment in g.string:
        joint = segment.pipe.hydraulic_joint
        if joint is not None:
            if sample['well'] == '16B' and variant in ('gpds', 'fh') and np.isclose(
                    2*segment.pipe.r_bore/calc.whole.INCH, 4.67):
                od, bore = (7.25, 3.5) if variant == 'gpds' else (7.5, 3.)
                joint = replace(joint, outer_diameter=od*calc.whole.INCH,
                    bore_diameter=bore*calc.whole.INCH,
                    source=f'Entry 10 {variant} catalogue scenario; installed machining unknown')
            if variant == 'gradual':
                joint = replace(joint, transition='gradual')
            segment = replace(segment, pipe=replace(segment.pipe, hydraulic_joint=joint))
        string.append(segment)
    return calc.score.wg.WellGeometry(string, g.hole, g.survey)


def solve(calc, sample, variant):
    well = sample['well']
    if well not in calc.clocks:
        if well == '16A':
            t, c, d, _ = calc.adapter.energy.clock_a(ROOT/'validation/forge16a')
        else:
            _, t, c, d = calc.whole.clock(ROOT/'validation/forge16b')
        calc.clocks[well] = t, c, d
    t, clock, depth = calc.clocks[well]
    g = geometry(calc, sample, variant)
    fluid, _, _ = calc.fluid(sample)
    q = sample['flow_gpm']*calc.whole.GPM
    rho = float(calc.m1.fluid_props(np.array([sample['T_in_C']]),
                np.array([calc.m1.P_SURF]), fluid)[0][0])
    exposure = calc.m1.smooth_exposure(calc.m1.exposure_from_history(
        clock, depth, float(np.interp(sample['time_s'], t, clock))), g.md_bit)
    form = calc.score.b.T_FORM if well == '16B' else calc.score.a.formation('216', g.survey)[0]
    heat, _ = calc.rotary.heat(sample)
    r = calc.m1.solve_seeded(exposure, calc.m1.exposure_breaks(exposure, g.md_bit),
        m_dot=q*rho, T_inj=sample['T_in_C'], geotherm=form, geometry=g,
        target_rock_T=float(form(g.survey.tvd(g.md_bit))),
        Q_face=sample['motor_heat_psi']*calc.whole.PSI*q+heat.bit_W,
        k_rock=calc.score.b.K_ROCK, rhocp_rock=calc.score.b.RHOCP_ROCK,
        friction_heat=True, tfa=sample['tfa_m2'], film_mult=1., fluid=fluid,
        verbose=False, hydraulics_model='v1.6.0', surface=calc.surface,
        annulus_heat=heat.annulus, annulus_model=calc.adapter.MODEL,
        friction='blasius' if variant == 'baseline' else 'colebrook',
        roughness=45.72e-6 if variant == 'steel' else 0.)
    h = calc.m1.hydraulics(q*rho, g, result=r, tfa=sample['tfa_m2'], fluid=fluid)
    check = r['energy_check']
    offset = 0 if well == '16A' else (84 if sample['run'] in ('17', '18', '19', '20', '27', '38') else 22)
    power = (sum(sum(v.values()) for v in check['assigned_terms_W'].values())+check['nozzle_W'])/1000
    return dict(success=bool(r['success']), solver_status=int(r['sol'].status),
        bit_C=float(r['Td'][-1]), return_C=float(r['Tu'][0]),
        sensor_offset_ft=offset, sensor_bore_C=float(np.interp(g.md_bit-offset*calc.whole.FT, r['z'], r['Td'])),
        spp_psi=h['spp']/calc.whole.PSI,
        friction_and_nozzle_kW=power,
        model_hydraulic_kW=power+sample['motor_heat_psi']*calc.whole.PSI*q/1000,
        energy_residual_W=check['residual_W'], energy_flagged=check['flagged'])


def write(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'predictions')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    calc = diagnosis.Calculation()
    samples = [s for s in calc.plan['samples'] if not (
        s['well'] == '16A' and s.get('source') != 'Sanvean on-bottom')]
    rows = []
    windows = selection.select(samples)
    for i, sample in enumerate(windows, 1):
        baseline = solve(calc, sample, 'baseline')
        for variant in VARIANTS:
            values = baseline if variant == 'baseline' else solve(calc, sample, variant)
            row = dict(well=sample['well'], assembly=sample['run'], sample_id=sample['id'],
                bit_ft=sample['bit_ft'], flow_gpm=sample['flow_gpm'], variant=variant, **values)
            for key in ('bit_C', 'sensor_bore_C', 'return_C', 'spp_psi', 'friction_and_nozzle_kW', 'model_hydraulic_kW'):
                row[key+'_change'] = values[key]-baseline[key]
            rows.append(row)
        write(args.output/'model-only.csv', rows)
        print(f'{i}/{len(windows)} {sample["well"]} {sample["run"]}', flush=True)
    inputs = [HERE/'predict.py', HERE/'options.json', HERE.parent/'entry-9/diagnose.py',
              HERE.parent/'entry-8/score.py', calc.score.PLAN,
              ROOT/'validation/scoreboard/scoreboard.py',
              ROOT/'src/borethm/fluids.py', ROOT/'src/borethm/hydraulic_losses.py',
              ROOT/'src/borethm/model1_coupled.py', ROOT/'src/borethm/_api.py',
              ROOT/'src/borethm/well_geometry.py', ROOT/'src/borethm/studies/pressure_comparison.py',
              HERE.parent/'entry-3/predict.py', HERE.parent/'entry-4/rotary.py',
              HERE.parent/'entry-4/rotary_inputs.csv', HERE.parent/'entry-6/hypotheses.py',
              HERE/'references.json']
    manifest = dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
        runtime_s=time.perf_counter()-started, windows=len(windows), variants=list(VARIANTS),
        calculations=len(rows), solver_failures=[dict(sample_id=r['sample_id'], variant=r['variant'])
            for r in rows if not r['success']], energy_flags=sum(r['energy_flagged'] for r in rows),
        targets_compared=False,
        power_definition='model_hydraulic_kW equals the frozen G2 definition: distributed dissipation plus nozzles plus raw motor differential face power; surface power and rotary work are excluded.',
        sha256={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    manifest['model_only_csv_sha256'] = hashlib.sha256((args.output/'model-only.csv').read_bytes()).hexdigest()
    (args.output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k != 'sha256'}), flush=True)


if __name__ == '__main__':
    main()
