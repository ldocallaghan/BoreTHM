"""Stable release projections and fresh CI generation of reviewed C1-C6 results."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import lever_flow_limit
import lever_pairs
import levers as lv
import site_evaluation as se

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / 'tests/golden'
SITES = ('soultz', 'united-downs', 'larderello', 'pannonian', 'newberry')


def windows_row(windows):
    return {name: dict(open=windows[name]['open'],
                      lower_SG=windows[name]['lo'] / 1000., upper_SG=windows[name]['hi'] / 1000.,
                      lower_by=windows[name]['lo_by'], upper_by=windows[name]['hi_by'])
            for name in ('drilling_fluid', 'trip_fluid')}


def reference_row(data):
    p, c = data['programme'], data['components']
    return dict(status=data['status']['label'], target_m=data['z_m'],
        pipe=p['pipe'], flow=p['flow'], flow_unit=p['flow_unit'], bit_C=p['bit_C'],
        weights_SG={k: p[k] / 1000. for k in (
            'drilling_simulated_rho_surface', 'drilling_prescribed_rho_surface',
            'trip_simulated_rho_surface', 'trip_prescribed_rho_surface')},
        windows=windows_row(data['windows']), fluid_converged=p['fluid_converged'],
        solver_ok=c['solver']['ok'], refinement_converged=c['window_refinement']['converged'],
        tool_ok=c['tool']['ok'], coating=c['coating']['status'],
        pumps_ok=c['pumps']['ok'], rig_ok=c['pumps']['within_rig'])


def lever_row(record):
    a = record['assessment']
    row = dict(settings=record['settings'], reopened=a['reopened'], verdict=a['verdict'],
               failures=a['failures'], qualification=a['qualification_indeterminate'])
    if record['metrics'] is not None:
        row.update(reference=reference_row(record['result']),
                   tool_peaks_C=record['metrics']['tool_peaks_C'],
                   pressure_margin_SG=record['metrics']['pressure_margin_SG'],
                   coating_peaks_C={name: record['metrics']['coating'][name] if name == 'circulating_max'
                                     else record['metrics']['coating'][name]['max']
                                    for name in ('circulating_max', 'connection', 'trip_in')},
                   pump_pressure_Pa=record['result']['components']['pumps']['spp'], mpd=record['mpd'])
    return row


def bracket_row(bracket, records):
    if bracket is None:
        return None
    by_path = {r['evidence']: r for r in records}
    return dict(tolerance=bracket['tolerance'], unresolved=bracket.get('unresolved', False),
        failing=dict(intervention=bracket['failing']['intervention'],
                     trial=lever_row(by_path[bracket['failing']['evidence']])),
        passing=dict(intervention=bracket['passing']['intervention'], trial=lever_row(bracket['minimum'])))


def lever_tables(directory):
    sites = {}
    for key in SITES[:2]:
        rows = {}
        for number in range(1, 9):
            label = f'L{number}'
            s = json.loads((directory / key / label / 'summary.json').read_text())
            rows[label] = dict(trials=[lever_row(r) for r in s['trials']],
                               reopening_bracket=bracket_row(s.get('bracket'), s['trials']))
            for source, field in (('coating_threshold', 'coating_brackets'), ('bit_flow_limit', 'bit_brackets')):
                if s.get(source, {}).get('bracket'):
                    rows[label][field] = [bracket_row(s[source][b], s['trials'])
                                          for b in ('bracket', 'refined_bracket')]
        pairs = list((directory / key).glob('PAIR-*/summary.json'))
        if len(pairs) != 1:
            raise ValueError(f'{key}: exactly one reviewed pair is required')
        pair = json.loads(pairs[0].read_text())
        rows['pair'] = dict(levers=pair['pair'], trial=lever_row(pair['trial']))
        sites[key] = rows
    return sites


def assert_reviewed(actual, reviewed, path=''):
    """Compare physical release rows; metadata and timings are outside the pins."""
    if isinstance(reviewed, dict):
        assert actual.keys() == reviewed.keys(), path
        for key in reviewed:
            assert_reviewed(actual[key], reviewed[key], path + '/' + key)
    elif isinstance(reviewed, list):
        assert len(actual) == len(reviewed), path
        for i, (a, b) in enumerate(zip(actual, reviewed)):
            assert_reviewed(a, b, path + '/' + str(i))
    elif isinstance(reviewed, bool) or reviewed is None or isinstance(reviewed, str):
        assert actual == reviewed, (path, actual, reviewed)
    else:
        tolerance = 1.e-8
        if '/settings/' in path:
            tolerance = 1. if path.endswith('/bhp_Pa') else 1.e-8
        elif '_SG' in path:
            tolerance = 0.002
        elif '_C' in path:
            tolerance = 0.1
        elif '_Pa' in path:
            tolerance = 10000.
        elif path.endswith('/md'):
            tolerance = 100.
        elif path.endswith('/target_m'):
            tolerance = 0.1
        assert abs(actual - reviewed) <= tolerance, (path, actual, reviewed, tolerance)


def generate_levers(directory):
    for key in SITES[:2]:
        for number in range(1, 9):
            lv.run_lever(key, f'L{number}', root=directory)
    lever_flow_limit.main(root=directory)
    lever_pairs.main(['--output', str(directory)])
    return lever_tables(directory)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(se._jsonable(value), indent=2) + '\n', encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / 'results/v1.3.4/ci').resolve()):
        parser.error('release evidence must be beneath results/v1.3.4/ci')
    if output.exists() and any(output.iterdir()):
        parser.error('choose an empty output directory for fresh CI generation')
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    reference = {}
    for key in SITES:
        print('Release reference:', key, flush=True)
        data = se.result_dict(se.evaluate(se.find_site(key), circulation='v1.3.4'))
        reviewed = json.loads((ROOT / 'results/v1.3.4/checkpoint-1' / (key + '.json')).read_text())
        reference[key] = reference_row(data)
        assert_reviewed(reference[key], reference_row(reviewed))
        write(output / 'reference' / (key + '.json'), data)
    tables = generate_levers(output / 'levers')
    assert_reviewed(tables, lever_tables(ROOT / 'results/levers'))
    files = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in output.rglob('*.json')}
    provenance = dict(versions=se.versions(), source_sha256=lv.fingerprint(),
        github_run_id=os.environ.get('GITHUB_RUN_ID'), github_run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
        evidence_directory=output.relative_to(ROOT).as_posix(), elapsed_seconds=time.perf_counter() - started)
    write(GOLDEN / 'v134_site_table.json', dict(schema_version=1, provenance=provenance, sites=reference))
    write(GOLDEN / 'v134_lever_tables.json', dict(schema_version=1, provenance=provenance, sites=tables))
    write(output / 'manifest.json', dict(provenance=provenance, evidence_files_sha256=files))
    print('Reviewed tables reproduced; CI goldens and all bracketing evidence written', flush=True)


if __name__ == '__main__':
    main()
