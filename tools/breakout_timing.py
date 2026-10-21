"""Report the shipped L7 breakout-formation-delay experiment.

Run from the repository root:
    python tools/breakout_timing.py
    python tools/breakout_timing.py --scan --reuse

The coupled programme evaluates every built-in stress and strength case.
"""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

from borethm import fluids
from borethm.studies import levers
from borethm import pressure
from borethm import site_evaluation as se

RESULTS = ROOT / 'results/v1.3.6/breakout-timing'
SITES = ('soultz', 'united-downs')
SCHEMA = 1
SCAN_MINUTES = (0, 5, 10, 15, 20, 30, 45, 60, 90, 120)


def plain(value):
    """Convert the numerical return values to JSON-compatible objects."""
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if hasattr(value, 'tolist'):
        return plain(value.tolist())
    if isinstance(value, float) and not (-float('inf') < value < float('inf')):
        return str(value)
    return value


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plain(value), indent=2, allow_nan=False) + '\n',
                    encoding='utf-8', newline='\n')


def failure_evidence(out):
    """Keep the returned quantities behind the programme's failing checks."""
    failures = []
    for name in ('drilling_fluid', 'trip_fluid'):
        window = out['windows'][name]
        if not window['open']:
            failures.append(dict(check=name, quantity='rho_surface', unit='kg/m3 at 20 C',
                                 lo=window['lo'], hi=window['hi'],
                                 lo_by=window['lo_by'], hi_by=window['hi_by']))
    cycle = out['cycle']
    for case in cycle['per_case']:
        for state in ('drilling', 'trip'):
            if case['states'][state] != 'NO-GO':
                continue
            need = case['drill_SG'] if state == 'drilling' else max(case['trip_SG'], case['trip_SG_start'])
            failures.append(dict(check='target stability', state=state, case=case['label'],
                md=out['z'], quantity='drill_SG' if state == 'drilling' else 'max(trip_SG, trip_SG_start)',
                value=need, hi=case['drill_SG_hi'] if state == 'drilling' else case['trip_SG_hi'],
                unit='SG-equivalent at target', verdict=case['states'][state]))
    tools = out['tools']
    if not tools['drilling']['ok']:
        failures.append(dict(check='tool', state='drilling', case='common programme', md=out['z'],
            quantity='T', value=tools['drilling']['T'], limit=tools['limit'], unit='C'))
    if tools['connection']['schedule'] is None:
        failures.append(dict(check='tool', state='connection', case='common programme', md=out['z'],
            quantity='peak', value=tools['connection']['peak'], limit=tools['limit'], unit='C',
            schedule=tools['connection']['schedule'],
            search_skipped=not tools['drilling']['ok']))
    if tools['trip_in']['schedule'] is None:
        practice = tools['trip_in']['staged']
        best = tools.get('robustness_search', {}).get('best')
        failures.append(dict(check='tool', state='running in', case='common programme',
            md=practice['md'], quantity='staged.peak', value=practice['peak'],
            limit=tools['limit'], unit='C', schedule=None, best_attempt=best,
            best_attempt_md=None,
            depth_note='md locates the practice peak; the best-attempt peak depth is not returned',
            search_skipped=not tools['drilling']['ok']))
    return failures


def report_result(key, settings, out, elapsed):
    """Read the L7 return object without changing the programme or its results."""
    if not out['components']['solver']['ok']:
        raise ValueError(f'{key}: the coupled solve did not converge')
    if not out['windows']['refinement']['converged']:
        raise ValueError(f'{key}: the depth refinement did not converge')
    cycle = out['cycle']
    budget = cycle['budget']
    temperatures = budget['temperatures']['circulating']
    make_fluid = lambda rho: fluids.Mud(rho, fluids.PV_REF * settings.pv_fraction, fluids.YP_REF)
    cases = []
    for case in cycle['per_case']:
        row = {k: v for k, v in case.items() if k != 'profile'}
        rho = pressure.surface_density_for(case['drill_SG'], out['z'], temperatures,
                                          make_fluid, budget['backpressure'])
        row['drill_rho_surface'] = fluids.water().rho_surface if rho is None else rho
        cases.append(row)
    return dict(schema_version=SCHEMA, site=key, z_m=out['z'], settings=asdict(settings),
        versions=se.versions(), source_sha256=levers.fingerprint(),
        reporting_tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        units=dict(drill_SG='equivalent static SG at target; includes connection checks',
                   drill_rho_surface='kg/m3 at 20 C and atmospheric pressure',
                   window_lo_hi='kg/m3 at 20 C; divide by 1000 for surface SG', md='m measured depth'),
        elapsed_seconds=elapsed,
        cycle=dict(drill_SG=cycle['drill_SG'], deciding_case=cycle['deciding_case'],
                   site_verdict=cycle['site_verdict'], verdicts=cycle['verdicts'], cases=cases),
        windows=out['windows'], tools=out['tools'], components=out['components'],
        status=out['status'], assessment=levers.gates(out), failures=failure_evidence(out))


def run_case(key, minutes, output, reuse=False):
    """Run one complete L7 programme; reuse requires matching physics and settings."""
    settings = replace(levers.base_settings(key), form_h=minutes / 60.)
    path = output / f'{key}-{minutes:g}min.json'
    if reuse and path.exists():
        saved = json.loads(path.read_text(encoding='utf-8'))
        if (saved.get('schema_version') == SCHEMA and saved.get('settings') == asdict(settings)
                and saved.get('source_sha256') == levers.fingerprint()):
            print(f'Reuse {key} {minutes:g} min: {path}', flush=True)
            return saved, True
    print(f'Run {key} {minutes:g} min', flush=True)
    started = time.perf_counter()
    out = levers.evaluate_settings(key, settings)
    record = report_result(key, settings, out, time.perf_counter() - started)
    write_json(path, record)
    print(f"Result {key} {minutes:g} min: {record['status']['label']}; "
          f"drilling window open={record['windows']['drilling_fluid']['open']}; "
          f"{record['elapsed_seconds']:.1f} s", flush=True)
    return record, False


def describe_bound(bound):
    return f"{bound['state']}; {bound['case']}; {bound['md']:.2f} m MD"


def case_table(record):
    rows = ['| Case | UCS, MPa | drill_SG, SG-equivalent at target | drill_rho_surface, kg/m3 at 20 C | Target drilling verdict | Target full-cycle verdict |',
            '|---|---:|---:|---:|---|---|']
    for case in record['cycle']['cases']:
        rows.append(f"| {case['label']} | {case['UCS'] / 1e6:.0f} | {case['drill_SG']:.6f} | "
                    f"{case['drill_rho_surface']:.3f} | {case['states']['drilling']} | {case['verdict']} |")
    return '\n'.join(rows)


def render_result(record):
    minutes = record['settings']['form_h'] * 60.
    rows = [f"# {record['site']}: breakout formation delay {minutes:g} min", '',
            f"Target: {record['z_m']:.3f} m MD. Complete programme: **{record['status']['label']}**.", '',
            'The target drilling-fluid requirement includes the connection checks. The coupled programme evaluates every built-in case. Target SG-equivalents and surface densities have separate columns.', '',
            case_table(record), '',
            '| Window | lo / 1000, surface SG at 20 C | Lower bound: state; case; depth | hi / 1000, surface SG at 20 C | Upper bound: state; case; depth | Open |',
            '|---|---:|---|---:|---|---|']
    for name in ('drilling_fluid', 'trip_fluid'):
        window = record['windows'][name]
        rows.append(f"| {name} | {window['lo'] / 1000:.6f} | {describe_bound(window['lo_by'])} | "
                    f"{window['hi'] / 1000:.6f} | {describe_bound(window['hi_by'])} | {window['open']} |")
    rows += ['', '## Failing checks', '']
    for failure in record['failures']:
        if 'lo_by' in failure:
            rows.append(f"- {failure['check']}: lower {failure['lo'] / 1000:.6f} surface SG "
                        f"({describe_bound(failure['lo_by'])}); upper {failure['hi'] / 1000:.6f} surface SG "
                        f"({describe_bound(failure['hi_by'])}). The window is closed.")
        else:
            upper = failure.get('hi', failure.get('limit'))
            rows.append(f"- {failure['check']}, {failure['state']}, {failure['case']}, "
                        f"{failure['md']:.2f} m MD: {failure['quantity']} = {failure['value']:.6f}; "
                        f"upper limit {upper:.6f} {failure['unit']}.")
            if failure.get('best_attempt'):
                best = failure['best_attempt']
                rows.append(f"  Best attempted run-in schedule: peak {best['peak_C']:.6f} C; "
                            f"{best['stages']} stages, spacing {best['spacing_m']:.6f} m, "
                            f"{best['stage_seconds']:.1f} s per stage. Its peak depth is not returned. "
                            f"The depth above belongs to the practice peak. Schedule found: none.")
            if failure.get('search_skipped'):
                rows.append('  The schedule search was skipped because the drilling tool temperature exceeds its limit.')
    coating = record['tools']['coating']
    rows += ['', f"Coating qualification: {coating['status']}; rating {coating['rating']:g} C. "
             'This is separate from the failing checks above.', '',
             '## Settings and provenance', '', '```json',
             json.dumps(dict(settings=record['settings'], versions=record['versions'],
                             source_sha256=record['source_sha256'],
                             reporting_tool_sha256=record['reporting_tool_sha256'],
                             elapsed_seconds=record['elapsed_seconds']), indent=2), '```', '',
             'Reproduce from the repository root:', '', '```sh',
             f"python tools/breakout_timing.py --sites {record['site']}", '```', '']
    return '\n'.join(rows)


def critical_delay(trials):
    """Return the first open sampled window and its preceding closed sample."""
    first = next((i for i, row in enumerate(trials) if row['drilling_fluid']['open']), None)
    if first is None:
        return dict(minutes=None, bracket=None, status='no open window in the scan')
    passing = trials[first]['delay_min']
    bracket = (dict(closed_min=trials[first - 1]['delay_min'], open_min=passing)
               if first else None)
    return dict(minutes=passing, bracket=bracket, status='first open sampled window')


def run_scan(key, output, reuse=False):
    """Evaluate the fixed grid with the same coupled L7 entry point as the pair."""
    started = time.perf_counter()
    trials = []
    for minutes in SCAN_MINUTES:
        record, reused = run_case(key, minutes, output, reuse)
        path = output / f'{key}-{minutes:g}min.json'
        trials.append(dict(delay_min=minutes, form_h=record['settings']['form_h'],
            drilling_fluid=record['windows']['drilling_fluid'],
            drill_SG=record['cycle']['drill_SG'], deciding_case=record['cycle']['deciding_case'],
            programme_verdict=record['status']['label'],
            evidence=path.name, evidence_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            reused=reused, elapsed_seconds=record['elapsed_seconds']))
    scan = dict(site=key, scan_minutes=list(SCAN_MINUTES), trials=trials,
                critical_delay=critical_delay(trials),
                elapsed_seconds=time.perf_counter() - started,
                fresh_runs=sum(not row['reused'] for row in trials),
                reused_runs=sum(row['reused'] for row in trials),
                fresh_solve_seconds=sum(row['elapsed_seconds'] for row in trials if not row['reused']),
                versions=se.versions(), source_sha256=levers.fingerprint(),
                reporting_tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                criterion='first sampled delay with drilling_fluid.open true; no interpolation or refinement')
    write_json(output / f'scan-{key}.json', scan)
    print(f"Critical delay {key}: {scan['critical_delay']}; scan {scan['elapsed_seconds']:.1f} s", flush=True)
    return scan


def render_scans(scans):
    rows = ['# Breakout formation delay scan', '',
            'The window bounds are surface SG at 20 C. drill_SG is the deciding case\'s SG-equivalent requirement at the target and includes its connection checks.', '',
            '| Site | Delay, min | lo / 1000, surface SG | hi / 1000, surface SG | Drilling window open | drill_SG, SG-equivalent at target | Deciding case | Complete programme |',
            '|---|---:|---:|---:|---|---:|---|---|']
    for scan in scans:
        for trial in scan['trials']:
            w = trial['drilling_fluid']
            rows.append(f"| {scan['site']} | {trial['delay_min']} | {w['lo'] / 1000:.6f} | "
                        f"{w['hi'] / 1000:.6f} | {w['open']} | {trial['drill_SG']:.6f} | "
                        f"{trial['deciding_case']} | {trial['programme_verdict']} |")
    rows += ['', '## Critical delay brackets', '',
             'These brackets describe the first passing sampled drilling-fluid window. The fixed grid has no interpolation or refinement. They do not establish a measured breakout formation time.', '']
    for scan in scans:
        critical = scan['critical_delay']
        bracket = critical['bracket']
        if bracket:
            rows.append(f"- {scan['site']}: closed at {bracket['closed_min']} min; open at "
                        f"{bracket['open_min']} min. First passing sampled delay: {critical['minutes']} min.")
        else:
            rows.append(f"- {scan['site']}: {critical['status']}; first passing delay {critical['minutes']}.")
        rows.append(f"  Scan wall time: {scan['elapsed_seconds']:.1f} s; {scan['fresh_runs']} fresh runs "
                    f"({scan['fresh_solve_seconds']:.1f} s of solves), {scan['reused_runs']} reused runs. "
                    'Each JSON trial retains its own original calculation time and provenance.')
    rows += ['', 'Reproduce from the repository root:', '', '```sh',
             'python tools/breakout_timing.py',
             'python tools/breakout_timing.py --scan --reuse', '```', '']
    return '\n'.join(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sites', nargs='+', choices=SITES, default=list(SITES))
    parser.add_argument('--output', type=Path, default=RESULTS)
    parser.add_argument('--reuse', action='store_true', help='reuse matching completed results')
    parser.add_argument('--scan', action='store_true', help='scan the fixed 0 to 120 minute grid')
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    if args.scan:
        scans = []
        for key in args.sites:
            scans.append(run_scan(key, args.output, args.reuse))
            (args.output / 'scan.md').write_text(render_scans(scans), encoding='utf-8', newline='\n')
        return
    for key in args.sites:
        for minutes in (0, 60):
            record, _ = run_case(key, minutes, args.output, args.reuse)
            path = args.output / f'{key}-{minutes:g}min.md'
            path.write_text(render_result(record), encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
