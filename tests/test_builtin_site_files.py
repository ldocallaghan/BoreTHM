"""Packaged site files reproduce the Python definitions and their generator."""
from importlib.resources import as_file, files
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from borethm import load_site, validate_site
from borethm import comparative_sites as cs
from borethm import crosscheck_newberry as nb
from site_helpers import assert_sites_equal


ROOT = Path(__file__).resolve().parents[1]
KEYS = ('larderello', 'united-downs', 'pannonian', 'newberry')


@pytest.mark.parametrize('key,reference', [
    ('larderello', cs.LARDERELLO),
    ('united-downs', cs.CORNWALL),
    ('pannonian', cs.PANNONIAN),
    ('newberry', cs.NEWBERRY),
])
def test_packaged_site_equals_python_definition(key, reference):
    resource = files('borethm').joinpath(f'templates/sites/{key}.toml')
    with as_file(resource) as path:
        site = load_site(path)
    assert_sites_equal(site, reference)
    assert site.tier == reference.tier
    assert validate_site(site) == validate_site(reference)
    boundaries = np.array([0., 1400., 2200., 2815., 4000., 5000.])
    if key == 'newberry':
        boundaries = np.concatenate((boundaries, nb.ST_TVD * nb.FT))
    depths = np.unique(np.concatenate((boundaries, np.nextafter(boundaries[boundaries > 0], -np.inf),
                                      np.nextafter(boundaries, np.inf))))
    for name in ('geotherm', 'geotherm_v11'):
        expected = getattr(reference, name)
        if expected is not None:
            np.testing.assert_array_equal(getattr(site, name)(depths), expected(depths))


def test_generator_reproduces_committed_files(tmp_path):
    command = subprocess.run([sys.executable, str(ROOT / 'tools/build_site_files.py'),
                              '--output', str(tmp_path)], cwd=tmp_path,
                             capture_output=True, text=True, timeout=30)
    assert command.returncode == 0, command.stderr
    assert {path.name for path in tmp_path.iterdir()} == {key + '.toml' for key in KEYS}
    for key in KEYS:
        name = key + '.toml'
        assert (tmp_path / name).read_bytes() == (
            ROOT / 'src/borethm/templates/sites' / name).read_bytes()
