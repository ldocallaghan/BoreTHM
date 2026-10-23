"""Build an isolated wheel environment and check it outside the checkout."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path, default=Path('dist'))
    args = parser.parse_args()
    wheels = list(args.dist.resolve().glob('*.whl'))
    if len(wheels) != 1:
        parser.error('the distribution directory must contain exactly one wheel')
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


if __name__ == '__main__':
    main()
