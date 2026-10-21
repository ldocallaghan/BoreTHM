"""Locations of source-checkout files and the user water-property cache."""
import os
from pathlib import Path
import sys
import tomllib


def repository_root():
    """Return the source checkout root, or None for an installed package."""
    package = Path(__file__).resolve().parent
    root = package.parent.parent
    if package != root / 'src' / 'borethm':
        return None
    metadata = root / 'pyproject.toml'
    try:
        with metadata.open('rb') as handle:
            project = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    return root if project.get('project', {}).get('name') == 'borethm' else None


def repository_path(relative):
    """Return a checkout-relative path, or None when no checkout is present."""
    root = repository_root()
    return root / relative if root is not None else None


def require_path(path, purpose):
    """Require an explicit path or source checkout when repository IO starts."""
    if path is None:
        raise RuntimeError(f'{purpose} requires a BoreTHM source checkout or an explicit path')
    return Path(path)


def cache_directory():
    """Use BORETHM_CACHE_DIR or the platform's user cache directory."""
    override = os.environ.get('BORETHM_CACHE_DIR')
    if override:
        return Path(override).expanduser()
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'borethm/Cache'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Caches/borethm'
    return Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'borethm'
