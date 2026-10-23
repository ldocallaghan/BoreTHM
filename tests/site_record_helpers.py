"""Exact file checks and numerical comparisons of independently captured inputs."""
from dataclasses import asdict, is_dataclass
import math

import numpy as np

from borethm import StressProfile
from borethm.site_evaluation import transitional_bounds


# Input snapshots only: one part in a trillion, in any input's own units.
# Zero remains zero. Physical regression tolerances are defined elsewhere.
INPUT_ROUNDOFF_RTOL = 1e-12


def assert_record_values(actual, expected, *, rtol=0., path='site'):
    """Compare structure exactly; rtol permits finite float round-off only.

    With rtol=0, floats must have identical binary representations. With a
    positive rtol, |a-b| <= rtol * max(|a|, |b|); no absolute floor is used.
    Integers, booleans, strings and nulls always retain their exact types and
    values. Non-finite floats fail in either mode. Errors name the full path.
    """
    if is_dataclass(actual):
        actual = asdict(actual)
    if is_dataclass(expected):
        expected = asdict(expected)
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and actual.keys() == expected.keys(), path
        for key, value in expected.items():
            assert_record_values(actual[key], value, rtol=rtol, path=f'{path}.{key}')
    elif isinstance(expected, (tuple, list, np.ndarray)):
        assert isinstance(actual, (tuple, list, np.ndarray)), path
        assert len(actual) == len(expected), path
        for i, (a, b) in enumerate(zip(actual, expected)):
            assert_record_values(a, b, rtol=rtol, path=f'{path}[{i}]')
    elif isinstance(expected, (float, np.floating)):
        assert isinstance(actual, (float, np.floating)), path
        a, b = float(actual), float(expected)
        assert math.isfinite(a) and math.isfinite(b), f'{path}: non-finite input'
        if rtol == 0.:
            assert a.hex() == b.hex(), f'{path}: {a!r} != {b!r}'
        else:
            difference = abs(a - b)
            scale = max(abs(a), abs(b))
            relative = difference / scale if scale else 0.
            assert difference <= rtol * scale, (
                f'{path}: {a!r} != {b!r}; absolute difference {difference:g}, '
                f'relative difference {relative:g}, allowed relative difference {rtol:g}')
    else:
        assert type(actual) is type(expected) and actual == expected, path


def profile_depths(data):
    """Sample the grid and each table boundary, including adjacent floats."""
    boundaries = [0.]
    for name in ('geotherm', 'geotherm_v11'):
        if name in data:
            table = data[name]
            rows = table['segments'] if table['form'] == 'segments' else table['points']
            boundaries.extend(row[0] for row in rows)
    z = np.array(boundaries, dtype=float)
    return np.unique(np.concatenate((np.arange(0., 20001., 10.), z,
                                     np.nextafter(z[z > 0], -np.inf), np.nextafter(z, np.inf))))


def assert_loaded_record(site, data):
    """Check loaded inputs against the supplied record, without refitting data."""
    for name, value in data.items():
        if name in ('geotherm', 'geotherm_v11'):
            z = profile_depths(data)
            if value['form'] == 'segments':
                rows = np.asarray(value['segments'], dtype=float)
                side = 'right' if value.get('boundary', 'below') == 'below' else 'left'
                indices = np.maximum(0, np.searchsorted(rows[:, 0], z, side=side) - 1)
                top, temperature, gradient = rows[indices].T
                expected = temperature + gradient * (z - top)
            else:
                depths, temperatures = np.asarray(value['points'], dtype=float).T
                expected = np.where(z <= depths[-1], np.interp(z, depths, temperatures),
                                    temperatures[-1] + value['gradient_below'] * (z - depths[-1]))
            assert_record_values(getattr(site, name)(z), expected, path=name)
        elif name == 'stress_rule':
            arguments = {key: item for key, item in value.items() if key != 'form'}
            assert_record_values(site.stress_cases, transitional_bounds(**arguments), path=name)
        elif name == 'stress_cases':
            assert_record_values(site.stress_cases, [StressProfile(**case) for case in value], path=name)
        else:
            assert_record_values(getattr(site, name), value, path=name)
