"""Checkout discovery, provenance and platform cache boundaries."""
from pathlib import Path
import subprocess

import pytest

from borethm import _paths
from borethm import site_evaluation as se


def test_only_the_actual_source_layout_is_a_checkout(tmp_path, monkeypatch):
    (tmp_path / 'pyproject.toml').write_text('[project]\nname = "borethm"\n')
    monkeypatch.setattr(_paths, '__file__', str(tmp_path / 'src/borethm/_paths.py'))
    assert _paths.repository_root() == tmp_path
    monkeypatch.setattr(_paths, '__file__', str(tmp_path / '.venv/Lib/site-packages/borethm/_paths.py'))
    assert _paths.repository_root() is None
    assert _paths.repository_path('results') is None
    with pytest.raises(RuntimeError, match='source checkout or an explicit path'):
        _paths.require_path(None, 'Saved study evidence')


def test_other_projects_are_not_borethm_checkouts(tmp_path, monkeypatch):
    (tmp_path / 'pyproject.toml').write_text('[project]\nname = "another-project"\n')
    monkeypatch.setattr(_paths, '__file__', str(tmp_path / 'src/borethm/_paths.py'))
    assert _paths.repository_root() is None


def test_missing_git_does_not_prevent_recording_results(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError('git')
    monkeypatch.setattr(subprocess, 'run', missing)
    provenance = se.versions()
    assert provenance['commit'] is None and provenance['dirty'] is False
    assert provenance['packages']['borethm']


def test_installed_package_never_asks_git_for_a_checkout_commit(monkeypatch):
    monkeypatch.setattr(_paths, 'repository_root', lambda: None)
    monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: pytest.fail('git called for a wheel'))
    assert se.versions()['commit'] is None


@pytest.mark.parametrize('platform, variable, relative', [
    ('win32', 'LOCALAPPDATA', 'borethm/Cache'),
    ('linux', 'XDG_CACHE_HOME', 'borethm'),
    ('darwin', None, 'Library/Caches/borethm'),
])
def test_platform_cache_and_override(tmp_path, monkeypatch, platform, variable, relative):
    monkeypatch.setattr(_paths.sys, 'platform', platform)
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    monkeypatch.delenv('BORETHM_CACHE_DIR', raising=False)
    if variable:
        monkeypatch.setenv(variable, str(tmp_path))
    assert _paths.cache_directory() == tmp_path / relative
    monkeypatch.setenv('BORETHM_CACHE_DIR', str(tmp_path / 'custom'))
    assert _paths.cache_directory() == tmp_path / 'custom'
