"""Check a wheel installation from a working directory outside the checkout."""
import importlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import borethm as bt
from borethm._paths import repository_root


def main():
    assert repository_root() is None, 'run with an installed wheel, not an editable checkout'
    assert bt.__version__ == version('borethm')
    assert set(bt.named_sites()) == {'soultz', 'larderello', 'united-downs', 'pannonian', 'newberry'}
    site = bt.find_site('newberry')
    bt.validate_site(site)
    assert bt.thermal_hoop_stress(300., 150.) < 0.
    pipe = bt.uniform_wall(45.0)
    assert bt.WellGeometry.single(100., pipe).md_bit == 100.
    assert callable(bt.load_site) and callable(bt.layered_geotherm)
    scripts = Path(sys.executable).parent
    suffix = '.exe' if os.name == 'nt' else ''
    with tempfile.TemporaryDirectory() as directory:
        for key in ('soultz', 'newberry'):
            name = key + '.toml'
            create = [str(scripts / ('borethm-new-site' + suffix))]
            if key != 'soultz':
                create += ['--from', key]
            subprocess.run([*create, name], cwd=directory, check=True)
            subprocess.run([str(scripts / ('borethm-evaluate' + suffix)),
                            '--site-file', name, '--check'], cwd=directory, check=True)
    from borethm import drilling_cycle
    assert drilling_cycle.forge_timings()
    # Every study must import outside a checkout, even if running it needs evidence.
    for name in ('benchmark_utaustin', 'checkpoint_v134', 'crosscheck_soultz',
                 'lever_flow_limit', 'lever_pairs', 'levers', 'release_v134',
                 'robustness', 'validate_forge16b', 'validate_forge_pauses'):
        importlib.import_module('borethm.studies.' + name)
    from borethm import site_evaluation
    from borethm.studies import levers
    provenance = site_evaluation.versions()
    assert provenance['commit'] is None and provenance['dirty'] is False
    try:
        levers.base_settings('soultz')
    except RuntimeError as error:
        assert 'source checkout' in str(error)
    else:
        raise AssertionError('installed study unexpectedly read checkout evidence')
    print(json.dumps(dict(version=bt.__version__, package=bt.__file__,
                          source_sha256=levers.fingerprint(), versions=provenance), indent=2))
    print('Installed API, packaged site data, study imports and provenance: PASS')


if __name__ == '__main__':
    main()
