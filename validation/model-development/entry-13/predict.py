"""Tapered ordinary-pipe joint predictions on the frozen operating inputs.

One lower-median-depth sample per assembly, selected as in entry 3. No
measured target or residual enters the calculation or the output. Geometry,
mud, cumulative exposure and rotary heat use the entry 8 calculation via
entry 9's Calculation adapter. Only the declared joint options change. Each
variant is solved separately with the usual seeds. Changes are stated against
installed_primary and against the working calculation. The existing frozen
scoreboard is not modified or run here.
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
entry12 = load('entry12_predict', HERE.parent/'entry-12/predict.py')
OPTIONS = json.loads((HERE/'options.json').read_text(encoding='utf-8'))
VARIANTS = tuple(OPTIONS['variants'])


def apply_geometry(g, well, variant):
    """Apply entry 12's installed joints, then the declared ordinary-pipe taper.

    Only joints that entry 12 marks with the installed source become tapered,
    so HWDP and the EIS insulated connections stay abrupt in every variant.
    """
    if variant == 'working':
        return g
    settings = OPTIONS['variants'][variant]
    base = entry12.apply_geometry(g, well, 'installed_no_local' if variant == 'installed_no_local' else 'installed_primary')
    if 'taper_angle_deg' not in settings:
        return base
    from borethm import well_geometry as wg
    values = OPTIONS['installed'][well]
    string = []
    for segment in base.string:
        pipe = segment.pipe
        joint = pipe.hydraulic_joint
        if joint is not None and joint.source.startswith(OPTIONS['installed_source']):
            length = values[settings['restriction']]
            joint = replace(joint, transition='tapered', taper_angle_deg=settings['taper_angle_deg'],
                restriction_length=length*.0254,
                source=OPTIONS['installed_source']+'; '+settings['basis'])
            pipe = replace(pipe, hydraulic_joint=joint)
        string.append(replace(segment, pipe=pipe))
    return wg.WellGeometry(string, g.hole, g.survey)


def geometry(calc, sample, variant):
    g=calc.score.geometry(sample,calc.plan,'current')
    return apply_geometry(g,sample['well'],variant)


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
        friction='colebrook',
        roughness=0.)
    h = calc.m1.hydraulics(q*rho, g, result=r, tfa=sample['tfa_m2'], fluid=fluid)
    check = r['energy_check']
    offset = 0 if well == '16A' else (84 if sample['run'] in ('17', '18', '19', '20', '27', '38') else 22)
    power = (sum(sum(v.values()) for v in check['assigned_terms_W'].values())+check['nozzle_W'])/1000
    return dict(success=bool(r['success']), solver_status=int(r['sol'].status),
        bit_C=float(r['Td'][-1]), return_C=float(r['Tu'][0]),
        sensor_offset_ft=offset, sensor_bore_C=float(np.interp(g.md_bit-offset*calc.whole.FT, r['z'], r['Td'])),
        spp_psi=h['spp']/calc.whole.PSI,
        bore_joint_local_psi=h['terms']['bore']['joint_local']/calc.whole.PSI,
        annulus_joint_local_psi=h['terms']['annulus']['joint_local']/calc.whole.PSI,
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
        values = {variant: solve(calc, sample, variant) for variant in VARIANTS}
        for variant in VARIANTS:
            row = dict(well=sample['well'], assembly=sample['run'], sample_id=sample['id'],
                bit_ft=sample['bit_ft'], flow_gpm=sample['flow_gpm'], variant=variant, **values[variant])
            for key in ('bit_C', 'sensor_bore_C', 'return_C', 'spp_psi', 'friction_and_nozzle_kW', 'model_hydraulic_kW'):
                row[key+'_change'] = values[variant][key]-values['installed_primary'][key]
                row[key+'_vs_working'] = values[variant][key]-values['working'][key]
            rows.append(row)
        write(args.output/'model-only.csv', rows)
        print(f'{i}/{len(windows)} {sample["well"]} {sample["run"]}', flush=True)
    inputs = [HERE/'predict.py', HERE/'options.json', HERE.parent/'entry-9/diagnose.py',
              HERE.parent/'entry-8/score.py', calc.score.PLAN,
              ROOT/'validation/scoreboard/scoreboard.py',
              ROOT/'src/borethm/fluids.py', ROOT/'src/borethm/hydraulic_losses.py',
              ROOT/'src/borethm/model1_coupled.py', ROOT/'src/borethm/_api.py',
              ROOT/'src/borethm/well_geometry.py', ROOT/'src/borethm/studies/pressure_comparison.py',
              HERE.parent/'entry-12/predict.py', HERE.parent/'entry-12/options.json', HERE.parent/'entry-3/predict.py', HERE.parent/'entry-4/rotary.py',
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
