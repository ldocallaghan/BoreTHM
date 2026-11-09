"""Record full results for the exact-reproduction tests.

Run from the repository root with the v1.8.0 release code (30664bf) on the
path, before any change to the evaluator:

    python tests/make_golden_reproduction.py [--sites newberry soultz] [--physics v1.8.0 v1.7.0]

Each site is evaluated with circulation='v1.3.4' under each physics choice
and its result_dict is written to tests/golden/reproduction/<site>-<physics>.json,
without the versions record. Result keys added after v1.8.0 are dropped, so
the script gives the same files when run on later code that reproduces the
release. The values are floating-point results of one environment (Python
3.14.4, the locked dependencies, one BLAS thread); test_operations_slow.py
compares them exactly.
"""
import argparse
import json
from pathlib import Path
import time

from borethm import site_evaluation as se

OUT = Path(__file__).resolve().parent / 'golden' / 'reproduction'
SITES = ('newberry', 'soultz')
PHYSICS = ('v1.8.0', 'v1.7.0')
# Keys added to result_dict after v1.8.0; absent from the recorded results.
ADDED_KEYS = ('operations', 'window_profile', 'window_width', 'pump_check', 'tool_check',
              'coating_check')


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
    for key in args.sites:
        for physics in args.physics:
            started = time.perf_counter()
            data = recorded(se.result_dict(se.evaluate(se.find_site(key), physics=physics)))
            path(key, physics).write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8', newline='\n')
            print(key, physics, data['status']['label'], 'seconds', round(time.perf_counter() - started),
                  flush=True)


if __name__ == '__main__':
    main()
