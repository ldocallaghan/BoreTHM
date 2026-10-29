"""C1-C4 checkpoint evidence. Run from the repository root.

python -m borethm.studies.checkpoint_v134 --output results/v1.3.4/checkpoint-1
This writes run evidence. Reviewed regression goldens remain unchanged.
"""
import argparse
import json
from pathlib import Path
import time

from borethm import fluids
from borethm import pressure as pr
from borethm import site_evaluation as se


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sites', nargs='+', default=list(se.named_sites()))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    from borethm._paths import repository_root, require_path
    root = require_path(repository_root(), 'Historical regression goldens')
    baseline = json.loads((root / 'tests/golden/v133_site_table.json').read_text())
    comparison_path = args.output / 'comparison.json'
    rows = json.loads(comparison_path.read_text()) if comparison_path.exists() else []
    for key in args.sites:
        site = se.find_site(key)
        print('Evaluating C1-C4:', key, flush=True)
        started = time.perf_counter()
        output = se.evaluate(site, circulation='v1.3.4', hydraulics_model='v1.5.0')    # the release's calculation
        se.export_result(output, args.output / (key + '.json'))
        data = se.result_dict(output)
        old = baseline[site.name]
        row = dict(site=key, baseline=old, corrected=dict(status=data['status'],
            programme=data['programme'], windows=data['windows'], components=data['components'],
            trip_h=data['cycle']['trip_h']), elapsed_seconds=time.perf_counter() - started,
            versions=data['versions'])
        if key in ('soultz', 'united-downs'):
            # Hold surface weight and the complete thermal profile fixed.
            # The difference isolates C1's composition accounting.
            current = output['trip_fluid']
            rho = fluids.water().rho_surface if current is None else current.rho_surface
            legacy = fluids.Mud(rho, conserve_mass=False)
            conserved = fluids.Mud(rho)
            tvd, temperatures = se.trip_temperatures(site, output, output['m1'], output['cycle']['trip_h'])
            bp = output['m1'].get('backpressure', 0.)
            before = float(pr.column(tvd, temperatures, legacy, bp)[-1])
            after = float(pr.column(tvd, temperatures, conserved, bp)[-1])
            row['C1_fixed_profile_trip_pressure'] = dict(surface_density_kg_m3=rho,
                legacy_Pa=before, conserved_Pa=after, change_Pa=after - before,
                interpretation='same surface density and temperature profile; composition accounting only')
        rows = [previous for previous in rows if previous['site'] != key]
        rows.append(row)
        comparison_path.write_text(json.dumps(rows, indent=2) + '\n')
        print(json.dumps(dict(site=key, status=data['status'],
            drilling_surface_SG=data['programme']['drilling_simulated_rho_surface'] / 1000.,
            trip_surface_SG=data['programme']['trip_simulated_rho_surface'] / 1000.,
            bit_C=data['programme']['bit_C'], elapsed_seconds=row['elapsed_seconds']), indent=2), flush=True)


if __name__ == '__main__':
    try:
        main()
    except ValueError as error:
        raise SystemExit(str(error)) from None
