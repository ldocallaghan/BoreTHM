"""Build an isolated wheel environment and check it outside the checkout."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tarfile
import zipfile


def distribution_inventory(directory):
    """Check archive contents and record compressed distribution sizes."""
    result = {}
    for suffix, kind in (('*.whl', 'wheel'), ('*.tar.gz', 'sdist')):
        paths = list(Path(directory).resolve().glob(suffix))
        if len(paths) != 1:
            raise ValueError(f'{directory}: expected exactly one {kind}')
        path = paths[0]
        if kind == 'wheel':
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
        else:
            with tarfile.open(path) as archive:
                names = archive.getnames()
        forbidden = [name for name in names if 'forge16a' in Path(name).parts]
        if forbidden:
            raise ValueError(f'{path.name}: FORGE 16A archive must not ship: {forbidden}')
        result[kind] = dict(name=path.name, bytes=path.stat().st_size,
                            members=len(names), forge16a_archive_members=forbidden)
    return result


def compare_distributions(directory, baseline):
    current = distribution_inventory(directory)
    previous = distribution_inventory(baseline)
    for kind, record in current.items():
        before = previous[kind]['bytes']
        record.update(baseline_bytes=before, delta_bytes=record['bytes']-before,
                      delta_percent=100*(record['bytes']/before-1))
    return dict(current=current, baseline=previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path, default=Path('dist'))
    parser.add_argument('--baseline-dist', type=Path, help='Compare wheel/sdist sizes with a saved release')
    parser.add_argument('--report', type=Path, help='Write distribution inventory and successful installation status')
    args = parser.parse_args()
    wheels = list(args.dist.resolve().glob('*.whl'))
    if len(wheels) != 1:
        parser.error('the distribution directory must contain exactly one wheel')
    report = (compare_distributions(args.dist, args.baseline_dist) if args.baseline_dist
              else dict(current=distribution_inventory(args.dist)))
    print(json.dumps(report, indent=2), flush=True)
    check = Path(__file__).resolve().with_name('check_install.py')
    environment = dict(os.environ)
    environment.pop('PYTHONPATH', None)
    with tempfile.TemporaryDirectory(prefix='borethm-wheel-') as directory:
        work = Path(directory)
        root = work / 'venv'
        def run(*command):
            subprocess.run([str(part) for part in command], cwd=work, env=environment, check=True)
        run(sys.executable, '-m', 'venv', root)
        scripts = root / ('Scripts' if os.name == 'nt' else 'bin')
        suffix = '.exe' if os.name == 'nt' else ''
        python = scripts / ('python' + suffix)
        run(python, '-m', 'pip', 'install', wheels[0])
        run(python, '-m', 'pip', 'check')
        run(python, '-c', "from importlib.util import find_spec; assert find_spec('matplotlib') is None")
        for name in ('borethm-new-site', 'borethm-evaluate', 'borethm-sites', 'borethm-water-table'):
            run(scripts / (name + suffix), '--help')
        run(python, check)
    report['installed_check'] = 'passed'
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
