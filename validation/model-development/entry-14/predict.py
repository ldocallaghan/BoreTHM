"""Model-only predictions for entry 14, before any score.

Every frozen circulation sample is solved with the entry 13 tapered_primary
inputs, with and without the v1.8.0 tool defaults. The ten entry 9 shallow
windows and the 186 trip windows are evaluated with the same isothermal
reductions as entry 13. No measured target enters a calculation or an output.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import platform
import time
from types import SimpleNamespace

import numpy as np
import scipy

from borethm import physics
from forge_tools import HERE, entry13, identified, with_tools, load

ROOT = HERE.parents[2]
FIELDS = ('bit_C', 'sensor_bore_C', 'return_C', 'spp_psi', 'friction_and_nozzle_kW', 'model_hydraulic_kW')
base_geometry = entry13.geometry


def geometry(calc, sample, variant):
    g = base_geometry(calc, sample, 'tapered_primary')
    return with_tools(g) if variant == 'entry14' else g


def write(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, list(dict.fromkeys(k for r in rows for k in r)), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def samples(calc, output, limit=None):
    entry13.geometry = geometry
    rows = []
    started = time.perf_counter()
    selected = calc.plan['samples'][:limit]
    for i, sample in enumerate(selected, 1):
        before, after = (entry13.solve(calc, sample, v) for v in ('tapered_primary', 'entry14'))
        row = dict(well=sample['well'], assembly=sample['run'], sample_id=sample['id'], bit_ft=sample['bit_ft'], flow_gpm=sample['flow_gpm'],
                   success=before['success'] and after['success'], energy_flagged=before['energy_flagged'] or after['energy_flagged'])
        for key in FIELDS:
            row[key+'_before'], row[key+'_after'], row[key+'_change'] = before[key], after[key], after[key]-before[key]
        rows.append(row)
        if i % 25 == 0 or i == len(selected):
            write(output/'model-only.csv', rows)
            print(f'{i}/{len(selected)} samples, {time.perf_counter()-started:.0f} s', flush=True)
    return rows


def shallow(calc, output):
    source = HERE.parent/'entry-9/results/near-surface.csv'
    chosen = [r for r in entry13.diagnosis.read(source) if r['well'] == '16B' and r['role'] == 'primary']
    assert len(chosen) == 10
    table = {s['id']: s for s in calc.plan['samples']}
    rows = []
    for r in chosen:
        sample = table[r['input_sample_id']]
        base = calc.geometry(sample, float(r['bit_depth_ft']), float(r['hole_depth_ft']))
        context = SimpleNamespace(plan=calc.plan, whole=calc.whole, score=SimpleNamespace(wg=calc.score.wg, geometry=lambda *args: base))
        mass, q = float(r['mass_rate_kg_s']), float(r['flow_gpm'])*calc.whole.GPM
        fluid, _, _ = calc.fluid(sample)

        def pressure(g):
            h = calc.m1.hydraulics(mass, g, T_avg=float(r['temperature_C']), tfa=sample['tfa_m2'], fluid=fluid,
                hydraulics_model='v1.6.0', surface=calc.surface, annulus_model=calc.adapter.MODEL, friction='colebrook', roughness=0.)
            return (h['spp']+float(calc.surface.pressure(mass/q, q))-h['dp_surface'])/calc.whole.PSI
        tapered = base_geometry(context, sample, 'tapered_primary')
        tools = with_tools(tapered)
        rows.append(dict(window_id=r['window_id'], assembly=r['assembly'], bit_depth_ft=r['bit_depth_ft'], flow_gpm=r['flow_gpm'],
                         tools=';'.join(sorted({f"{t['tool_class']}@{t['band_in']}" for t in identified(tools)})),
                         spp_before_psi=pressure(tapered), spp_after_psi=pressure(tools),
                         change_psi=pressure(tools)-pressure(tapered)))
    write(output/'shallow-windows.csv', rows)
    return rows


def trips(calc, output):
    slopes = load('entry14_trip_slopes', HERE.parent/'entry-13/trip_slopes.py')
    options = calc.score.read_json(HERE.parent/'entry-13/options.json')
    groups = options['secondary_measures']['trip_slopes']['groups']
    identities = {(g['assembly'], g['excursion'], g['flow_centre_gpm']) for g in groups}
    read = entry13.diagnosis.read
    stages = read(HERE.parent/'entry-9/results/depth-stages.csv')
    window_ids = {w for r in stages if r['role'] == 'primary' and (r['assembly'], r['excursion'], r['flow_centre_gpm']) in identities for w in r['window_ids'].split(';')}
    windows = [r for r in read(HERE.parent/'entry-9/results/windows.csv') if r['well'] == '16B' and r['window_id'] in window_ids]
    table = {s['id']: s for s in calc.plan['samples']}
    out = {}
    for variant in ('tapered_primary', 'entry14'):
        rows = []
        for r in windows:
            sample = table[r['input_sample_id']]
            base = calc.geometry(sample, float(r['bit_depth_ft']), float(r['hole_depth_ft']))
            context = SimpleNamespace(plan=calc.plan, whole=calc.whole, score=SimpleNamespace(wg=calc.score.wg, geometry=lambda *args: base))
            g = base_geometry(context, sample, 'tapered_primary')
            if variant == 'entry14':
                g = with_tools(g)
            mass, q = float(r['mass_rate_kg_s']), float(r['flow_gpm'])*calc.whole.GPM
            fluid, _, _ = calc.fluid(sample)
            h = calc.m1.hydraulics(mass, g, T_avg=float(r['temperature_C']), tfa=sample['tfa_m2'], fluid=fluid, hydraulics_model='v1.6.0',
                                   surface=calc.surface, annulus_model=calc.adapter.MODEL, friction='colebrook', roughness=0.)
            rows.append(dict(assembly=r['assembly'], variant=r['variant'], role='primary', well='16B', excursion=r['excursion'], window_id=r['window_id'],
                             bit_depth_ft=float(r['bit_depth_ft']), flow_gpm=float(r['flow_gpm']),
                             modelled_spp_psi=(h['spp']+float(calc.surface.pressure(mass/q, q))-h['dp_surface'])/calc.whole.PSI))
        out[variant] = {(s['assembly'], s['excursion'], s['flow_centre_gpm']): s for s in slopes.model_slopes(rows)[0]}
    table = []
    for key, before in sorted(out['tapered_primary'].items()):
        after = out['entry14'][key]
        table.append(dict(assembly=key[0], excursion=key[1], flow_centre_gpm=key[2], added_pipe='insulated' if key[0] == '19' else 'regular',
                          slope_before=before['modelled_slope'], slope_after=after['modelled_slope'],
                          predicted_ratio_multiplier=before['modelled_slope']/after['modelled_slope']))
    write(output/'trip-slopes.csv', table)
    return table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'predictions')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with physics.using('v1.7.0'):
        calc = entry13.diagnosis.Calculation()
        audit = {}
        for sample in calc.plan['samples']:
            key = (sample['well'], sample['run'])
            if key not in audit:
                audit[key] = identified(with_tools(base_geometry(calc, sample, 'tapered_primary')))
        write(args.output/'assembly-tools.csv', [dict(well=k[0], assembly=k[1], **row) for k, rows in audit.items() for row in rows])
        trip = trips(calc, args.output)
        near = shallow(calc, args.output)
        rows = samples(calc, args.output, args.limit)
    inputs = [HERE/'predict.py', HERE/'forge_tools.py', HERE/'options.json', ROOT/'src/borethm/data/tool_losses.csv',
              ROOT/'src/borethm/tool_losses.py', ROOT/'src/borethm/hydraulic_losses.py', ROOT/'src/borethm/model1_coupled.py']
    manifest = dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__, targets_compared=False,
        runtime_s=time.perf_counter()-started, samples=len(rows), solver_failures=[r['sample_id'] for r in rows if not r['success']],
        energy_flags=[r['sample_id'] for r in rows if r['energy_flagged']], shallow_windows=len(near), trip_groups=len(trip),
        tool_classes=dict(Counter(t['tool_class'] for r in audit.values() for t in r)),
        sha256={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        outputs_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output.glob('*.csv')})
    (args.output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in manifest.items() if k not in ('sha256', 'outputs_sha256')}), flush=True)


if __name__ == '__main__':
    main()
