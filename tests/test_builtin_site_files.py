"""Site snapshots, exact round-trips and independent numerical derivations."""
import copy
from importlib.resources import as_file, files
from pathlib import Path
import subprocess
import sys
import tomllib

import numpy as np
import pytest

from borethm import find_site, load_site, validate_site
from site_helpers import assert_sites_equal
from site_record_helpers import (INPUT_ROUNDOFF_RTOL, assert_loaded_record,
                                 assert_record_values, profile_depths)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_site_files as builder

KEYS = ('larderello', 'united-downs', 'pannonian', 'newberry')


def stored_record(key):
    text = files('borethm').joinpath(f'templates/sites/{key}.toml').read_text(encoding='utf-8')
    return dict(header=text.split('\n\n', 1)[0].splitlines(), data=tomllib.loads(text))


@pytest.fixture(scope='module')
def generated(tmp_path_factory):
    directory = tmp_path_factory.mktemp('site-files')
    command = subprocess.run([sys.executable, str(ROOT / 'tools/build_site_files.py'),
                              '--output', str(directory)], cwd=directory,
                             capture_output=True, text=True, timeout=30)
    assert command.returncode == 0, command.stderr
    assert {path.name for path in directory.iterdir()} == {key + '.toml' for key in KEYS}
    return directory


@pytest.mark.parametrize('key', KEYS)
def test_packaged_file_preserves_its_record_exactly(key):
    with as_file(files('borethm').joinpath(f'templates/sites/{key}.toml')) as path:
        site = load_site(path)
    assert_loaded_record(site, stored_record(key)['data'])
    assert site.tier == find_site(key).tier
    assert validate_site(site) == validate_site(find_site(key))


@pytest.mark.parametrize('key', KEYS)
def test_generated_file_equals_current_python_definition_exactly(key, generated):
    path = generated / (key + '.toml')
    site, reference = load_site(path), find_site(key)
    assert_sites_equal(site, reference)
    data = tomllib.loads(path.read_text(encoding='utf-8'))
    assert_loaded_record(site, data)
    for name in ('geotherm', 'geotherm_v11'):
        expected = getattr(reference, name)
        if expected is not None:
            z = profile_depths(data)
            assert_record_values(getattr(site, name)(z), expected(z), path=name)


@pytest.mark.parametrize('key', KEYS)
def test_fixed_record_serialization_reproduces_committed_bytes(key, monkeypatch):
    record = stored_record(key)
    def forbidden(*args, **kwargs):
        pytest.fail('formatting a captured record recomputed its derivation')
    monkeypatch.setattr(builder, 'capture_sites', forbidden)
    monkeypatch.setattr(np, 'polyfit', forbidden)
    text = builder.render_record(record)
    assert text.encode('utf-8') == (ROOT / 'src/borethm/templates/sites' / (key + '.toml')).read_bytes()
    assert_record_values(tomllib.loads(text), record['data'])


@pytest.mark.parametrize('key', KEYS)
def test_current_capture_agrees_with_the_snapshot_numerically(key, generated):
    current = builder.capture_sites()[key + '.toml']
    assert_record_values(current, stored_record(key), rtol=INPUT_ROUNDOFF_RTOL)
    generated_data = tomllib.loads((generated / (key + '.toml')).read_text(encoding='utf-8'))
    assert_record_values(generated_data, current['data'])


@pytest.mark.parametrize('key', KEYS)
def test_an_input_changed_by_one_bit_fails_the_exact_check(key):
    data = stored_record(key)['data']
    changed = copy.deepcopy(data)
    changed['target_depth'] = float(np.nextafter(changed['target_depth'], np.inf))
    with pytest.raises(AssertionError, match='target_depth'):
        assert_record_values(changed, data)


@pytest.mark.parametrize('key', KEYS)
@pytest.mark.parametrize('change', ['numeric', 'label', 'boolean', 'structure'])
def test_reference_comparison_rejects_changes_beyond_roundoff(key, change):
    data = stored_record(key)['data']
    changed = copy.deepcopy(data)
    if change == 'numeric':
        changed['target_depth'] *= 1. + INPUT_ROUNDOFF_RTOL * 10
    elif change == 'label':
        changed['name'] += ' changed'
    elif change == 'boolean':
        changed['coupled'] = not changed['coupled']
    else:
        changed['unexpected'] = 1.
    with pytest.raises(AssertionError):
        assert_record_values(changed, data, rtol=INPUT_ROUNDOFF_RTOL)


@pytest.mark.parametrize('value', [0.001, 1., 1e6, -1e6])
def test_roundoff_budget_has_the_same_relative_meaning_at_each_scale(value):
    inside = value * (1. + INPUT_ROUNDOFF_RTOL / 2)
    outside = value * (1. + INPUT_ROUNDOFF_RTOL * 2)
    assert_record_values(inside, value, rtol=INPUT_ROUNDOFF_RTOL)
    with pytest.raises(AssertionError, match='relative difference'):
        assert_record_values(outside, value, rtol=INPUT_ROUNDOFF_RTOL)


@pytest.mark.parametrize('a,b', [(1, True), (True, 1), (1., 1), (1, 1.), (0., 1e-30), (1e-30, 0.),
                                (np.nan, np.nan), (np.inf, np.inf), (-np.inf, -np.inf)])
def test_roundoff_mode_rejects_type_changes_nonfinite_values_and_nonzero_for_zero(a, b):
    with pytest.raises(AssertionError):
        assert_record_values(a, b, rtol=INPUT_ROUNDOFF_RTOL)


def test_exact_mode_preserves_signed_zero():
    with pytest.raises(AssertionError):
        assert_record_values(-0., 0.)
    assert_record_values(-0., -0.)
