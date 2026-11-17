"""Evaluate the five built-in sites with the package defaults and archive the results.

Run from the repository root, with the package installed:

    python results/v1.9.0/sites/run_sites.py

Each site's full result is written to <site>.json beside this script. The rows
that tests/golden/v180_site_table.json records are written to table.json, and
compared with that table. manifest.json records the code, the environment, the
timings and the SHA-256 of every input and output file. At most four sites are
evaluated at once, each with one numerical thread.
"""
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
GOLDEN = HERE.parents[2] / 'tests' / 'golden' / 'v180_site_table.json'
WORKERS = 4


def evaluate(key):
    from borethm import site_evaluation as se
    from borethm.studies import release_v134 as release
    started = time.perf_counter()
    data = se._jsonable(se.result_dict(se.evaluate(se.find_site(key), circulation='v1.3.4')))
    (HERE / f'{key}.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8', newline='\n')
    return key, release.reference_row(data), round(time.perf_counter() - started, 1)


def largest_difference(a, b, path=''):
    """The largest absolute difference between numbers at the same place in two rows, and where."""
    if isinstance(a, dict) and isinstance(b, dict):
        found = (0.0, None)
        for k in set(a) | set(b):
            if k not in a or k not in b:
                return (math.inf, f'{path}/{k} missing')
            d = largest_difference(a[k], b[k], f'{path}/{k}')
            found = max(found, d, key=lambda x: x[0])
        return found
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return (abs(a - b), path)
    return (0.0, None) if a == b else (math.inf, f'{path}: {a!r} != {b!r}')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[name] = '1'
    from borethm import site_evaluation as se
    from borethm.studies import release_v134 as release
    import borethm
    started_utc = datetime.now(timezone.utc).isoformat(timespec='seconds')
    rows, seconds = {}, {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for key, row, elapsed in pool.map(evaluate, release.SITES):
            rows[key], seconds[key] = row, elapsed
            print(key, row['status'], row['flow'], row['flow_unit'], round(row['bit_C'], 1), 'seconds', elapsed, flush=True)
    versions = se.versions()
    table = dict(schema_version=1, sites={k: rows[k] for k in release.SITES}, versions=versions)
    (HERE / 'table.json').write_text(json.dumps(se._jsonable(table), indent=2) + '\n', encoding='utf-8', newline='\n')
    golden = json.loads(GOLDEN.read_text(encoding='utf-8'))
    comparison = {}
    for key in release.SITES:
        diff, where = largest_difference(se._jsonable(rows[key]), golden['sites'][key])
        comparison[key] = dict(largest_absolute_difference=diff, at=where)
    package = Path(borethm.__file__).resolve().parent
    sources = {p.relative_to(package).as_posix(): sha256(p) for p in sorted(package.rglob('*'))
               if p.is_file() and '__pycache__' not in p.parts}
    outputs = {p.name: sha256(p) for p in sorted(HERE.glob('*.json')) if p.name != 'manifest.json'}
    manifest = dict(
        purpose='The five built-in sites with the package defaults, for the study summary.',
        command='python results/v1.9.0/sites/run_sites.py',
        started_utc=started_utc, finished_utc=datetime.now(timezone.utc).isoformat(timespec='seconds'),
        workers=WORKERS, threads_per_worker=1, circulation='v1.3.4', physics='package default',
        versions=versions, seconds=seconds,
        compared_with=dict(file='tests/golden/v180_site_table.json', golden_versions=golden.get('versions'), sites=comparison),
        package_files_sha256=sources, script_sha256=sha256(__file__), outputs_sha256=outputs)
    (HERE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('compared with the v1.8.0 golden table:', {k: v['largest_absolute_difference'] for k, v in comparison.items()})


if __name__ == '__main__':
    main()
