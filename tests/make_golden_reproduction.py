"""Record full results for the exact-reproduction tests.

Run from the repository root with the v1.8.0 release code (30664bf) on the
path, before any change to the evaluator:

    python tests/make_golden_reproduction.py [--sites newberry soultz] [--physics v1.8.0 v1.7.0]

Each site is evaluated with circulation='v1.3.4' under each physics choice
and its result_dict is written to tests/golden/reproduction/<site>-<physics>.json,
without the versions record. Result keys added after v1.8.0 are dropped, so
the script gives the same files when run on later code that reproduces the
release. The values are floating-point results of one environment (the
locked dependencies, one BLAS thread). platform.json records its operating
system, Python minor version and NumPy version. On that platform
test_operations_slow.py compares the results exactly; elsewhere it compares
them with a relative tolerance (comparison()).
"""
import argparse
import json
from pathlib import Path
import platform
import sys
import time

from borethm import site_evaluation as se

OUT = Path(__file__).resolve().parent / 'golden' / 'reproduction'
SITES = ('newberry', 'soultz')
PHYSICS = ('v1.8.0', 'v1.7.0')
# Keys added to result_dict after v1.8.0; absent from the recorded results.
ADDED_KEYS = ('operations', 'window_profile', 'window_width', 'pump_check', 'tool_check',
              'coating_check')


PLATFORM = OUT / 'platform.json'
# Elsewhere than the recorded platform: the relative tolerance of every
# number, and the absolute floor of the energy balance's residual [W].
RELATIVE = 1e-9
RESIDUAL_FLOOR_W = 1e-7


def this_platform():
    """The operating system, Python minor version and NumPy version running now."""
    import numpy
    return dict(system=platform.system(), python=f'{sys.version_info.major}.{sys.version_info.minor}',
                numpy=numpy.__version__)


def comparison():
    """'exact' on the platform the results were recorded on, 'tolerance' elsewhere,
    with a line that says which comparison runs and why."""
    recorded_on = json.loads(PLATFORM.read_text(encoding='utf-8'))
    now = this_platform()
    describe = lambda p: f"{p['system']}, Python {p['python']}, NumPy {p['numpy']}"
    if now == recorded_on:
        return 'exact', f'exact comparison: running on the recorded platform ({describe(now)})'
    return 'tolerance', (f'relative tolerance {RELATIVE:g}, energy-balance residual floor '
                         f'{RESIDUAL_FLOOR_W:g} W: recorded on {describe(recorded_on)}, '
                         f'running on {describe(now)}')


def differences(result, golden, path=''):
    """Paths where result and golden differ beyond the tolerance comparison:
    numbers within RELATIVE of each other, the energy balance's residual_W
    within RESIDUAL_FLOOR_W and its relative_residual within that floor over
    the assigned power; text, flags and structure exactly."""
    found = []
    if isinstance(golden, dict) and isinstance(result, dict):
        if set(golden) != set(result):
            return [f'{path}: keys {sorted(set(golden) ^ set(result))}']
        for key in golden:
            if key == 'relative_residual' and 'assigned_W' in golden:
                floor = RESIDUAL_FLOOR_W / abs(golden['assigned_W'])
                if abs(result[key] - golden[key]) > floor:
                    found.append(f'{path}/{key}: {result[key]!r} != {golden[key]!r}')
                continue
            if key == 'residual_W':
                if abs(result[key] - golden[key]) > RESIDUAL_FLOOR_W:
                    found.append(f'{path}/{key}: {result[key]!r} != {golden[key]!r}')
                continue
            found += differences(result[key], golden[key], f'{path}/{key}')
        return found
    if isinstance(golden, list) and isinstance(result, list):
        if len(golden) != len(result):
            return [f'{path}: length {len(result)} != {len(golden)}']
        for i, (a, b) in enumerate(zip(result, golden)):
            found += differences(a, b, f'{path}[{i}]')
        return found
    numbers = (int, float)
    if (isinstance(golden, numbers) and isinstance(result, numbers)
            and not isinstance(golden, bool) and not isinstance(result, bool)):
        if not abs(result - golden) <= RELATIVE * max(abs(result), abs(golden)):
            found.append(f'{path}: {result!r} != {golden!r}')
        return found
    if result != golden:
        found.append(f'{path}: {result!r} != {golden!r}')
    return found


def recorded(data):
    """A result_dict without its versions record and the keys added after v1.8.0."""
    return {k: v for k, v in data.items() if k != 'versions' and k not in ADDED_KEYS}


def path(key, physics):
    return OUT / f'{key}-{physics}.json'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sites', nargs='+', choices=SITES, default=list(SITES))
    parser.add_argument('--physics', nargs='+', choices=PHYSICS, default=list(PHYSICS))
    args = parser.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    PLATFORM.write_text(json.dumps(this_platform(), indent=1) + '\n', encoding='utf-8', newline='\n')
    for key in args.sites:
        for physics in args.physics:
            started = time.perf_counter()
            data = recorded(se.result_dict(se.evaluate(se.find_site(key), physics=physics)))
            path(key, physics).write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8', newline='\n')
            print(key, physics, data['status']['label'], 'seconds', round(time.perf_counter() - started),
                  flush=True)


if __name__ == '__main__':
    main()
