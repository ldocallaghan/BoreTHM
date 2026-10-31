"""The six declared entry 9 primary slope groups under entry 10 options.

Window membership, temperature and mass rate are frozen in entry 9.
Its original grouping and regression functions are reused unchanged.
EOW 19 remains a separate insulated-length comparison. No selection or
coefficient depends on the new pressure results.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

from predict import load, geometry as candidate_geometry

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent/'entry-9'))
reduction = load('entry9_reductions', HERE.parent/'entry-9/analyse.py')
diagnosis = load('entry9_calculation', HERE.parent/'entry-9/diagnose.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'results/secondary')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    calc = diagnosis.Calculation()
    options = calc.score.read_json(HERE/'options.json')
    groups = options['secondary_measures']['trip_slopes']['groups']
    identities = {(g['assembly'], g['excursion'], g['flow_centre_gpm']) for g in groups}
    stages = diagnosis.read(HERE.parent/'entry-9/results/depth-stages.csv')
    window_ids = {w for r in stages if r['role'] == 'primary' and
                  (r['assembly'], r['excursion'], r['flow_centre_gpm']) in identities
                  for w in r['window_ids'].split(';')}
    windows = [r for r in diagnosis.read(HERE.parent/'entry-9/results/windows.csv')
               if r['well'] == '16B' and r['window_id'] in window_ids]
    assert len(windows) == len(window_ids)
    samples = {s['id']: s for s in calc.plan['samples']}
    old_slopes = {(r['assembly'], r['excursion'], r['flow_centre_gpm']): r
                  for r in diagnosis.read(HERE.parent/'entry-9/results/slopes.csv')
                  if r['role'] == 'primary'}
    all_windows, all_slopes, all_stages, checks = [], [], [], []
    for variant, settings in options['variants'].items():
        rows = []
        for source in windows:
            sample = samples[source['input_sample_id']]
            base = calc.geometry(sample, float(source['bit_depth_ft']), float(source['hole_depth_ft']))
            context = SimpleNamespace(plan=calc.plan, whole=calc.whole,
                score=SimpleNamespace(wg=calc.score.wg, geometry=lambda *a: base))
            g = candidate_geometry(context, sample, variant)
            fluid, _, _ = calc.fluid(sample)
            mass, temperature = float(source['mass_rate_kg_s']), float(source['temperature_C'])
            q_gpm = float(source['flow_gpm'])
            hyd = calc.m1.hydraulics(mass, g, T_avg=temperature, tfa=sample['tfa_m2'],
                fluid=fluid, hydraulics_model='v1.6.0', surface=calc.surface,
                annulus_model=calc.adapter.MODEL, friction=settings['friction'],
                roughness=settings['roughness_m'])
            # Entry 9: surface pressure uses recorded inlet volumetric flow.
            q = q_gpm*calc.whole.GPM
            surface = float(calc.surface.pressure(mass/q, q))
            pressure = (hyd['spp']+surface-hyd['dp_surface'])/calc.whole.PSI
            rows.append(dict(well='16B', role='primary', assembly=source['assembly'],
                variant=source['variant'], candidate=variant, excursion=source['excursion'],
                window_id=source['window_id'], bit_depth_ft=float(source['bit_depth_ft']),
                hole_depth_ft=float(source['hole_depth_ft']), flow_gpm=q_gpm,
                temperature_C=temperature, mass_rate_kg_s=mass,
                measured_spp_psi=float(source['measured_spp_psi']), modelled_spp_psi=pressure,
                residual_psi=pressure-float(source['measured_spp_psi']),
                entry9_modelled_spp_psi=float(source['modelled_spp_psi']),
                flags=';'.join(hyd['flags']), installed_tool_band_available=False))
        summaries, reduced_stages, exclusions = reduction.slopes(rows)
        assert not exclusions
        assert len(summaries) == len(groups)
        for row in summaries:
            key = (row['assembly'], row['excursion'], str(row['flow_centre_gpm']))
            old = old_slopes[key]
            assert row['stages'] == int(old['stages']) and row['windows'] == int(old['windows'])
            assert abs(row['measured_slope']-float(old['measured_slope'])) < 1e-9
            row.update(candidate=variant, added_pipe='insulated' if row['assembly'] == '19' else 'regular')
            if variant == 'baseline':
                checks.append(dict(assembly=row['assembly'], excursion=row['excursion'],
                    flow_centre_gpm=row['flow_centre_gpm'], old_modelled_slope=float(old['modelled_slope']),
                    replayed_modelled_slope=row['modelled_slope'],
                    difference_psi_per_1000ft=row['modelled_slope']-float(old['modelled_slope']),
                    measured_slope_difference=row['measured_slope']-float(old['measured_slope'])))
        all_windows.extend(rows)
        all_slopes.extend(summaries)
        all_stages.extend({**r, 'candidate': variant} for r in reduced_stages)
        print(f'{variant}: {len(rows)} windows, {len(summaries)} slope groups', flush=True)
    for name, rows in [('windows.csv', all_windows), ('slopes.csv', all_slopes),
                       ('depth-stages.csv', all_stages), ('baseline-check.csv', checks)]:
        diagnosis.write(args.output/name, rows)
    sources = [Path(__file__), HERE/'predict.py', HERE/'options.json',
               HERE.parent/'entry-9/analyse.py', HERE.parent/'entry-9/diagnose.py',
               HERE.parent/'entry-9/results/windows.csv', HERE.parent/'entry-9/results/depth-stages.csv',
               HERE.parent/'entry-9/results/slopes.csv']
    manifest = dict(declaration_commit='2d183acdfd6a8bf867a2d79220484fda157f6338',
        windows_per_variant=len(windows), groups_per_variant=len(groups),
        candidates=list(options['variants']), runtime_s=time.perf_counter()-started,
        acceptance_use=False, failures=[], exclusions=[],
        source_sha256={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        results_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output.glob('*.csv')})
    calc.score.write_json(args.output/'manifest.json', manifest)


if __name__ == '__main__':
    main()
