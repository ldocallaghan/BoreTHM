"""Read site inputs from TOML data files."""
from dataclasses import MISSING, fields
from importlib.resources import files
from pathlib import Path
import tomllib

import numpy as np

from borethm.site_evaluation import SiteProfile, StressProfile, layered_geotherm, transitional_bounds


def template_text():
    """Return the packaged Soultz site template as UTF-8 text."""
    return files('borethm').joinpath('templates/site_template.toml').read_text(encoding='utf-8')


def site_text(key):
    """Return a packaged starting site, selected by its exact built-in key."""
    keys = ('soultz', 'larderello', 'united-downs', 'pannonian', 'newberry')
    if key not in keys:
        raise ValueError(f'--from {key!r}: choose one of ' + ', '.join(keys))
    if key == 'soultz':
        return template_text()
    return files('borethm').joinpath(f'templates/sites/{key}.toml').read_text(encoding='utf-8')


def _segment_geotherm(segments, boundary='below'):
    """Build a piecewise linear geotherm, with depth in m and temperature in C."""
    def geotherm(z):
        z = np.asarray(z, dtype=float)
        conditions = [(z <= next_segment[0] if boundary == 'above' else z < next_segment[0])
                      for next_segment in segments[1:]]
        temperatures = [T + gradient * (z - top) for top, T, gradient in segments]
        if not conditions:
            return temperatures[0]
        return np.select(conditions, temperatures[:-1], default=temperatures[-1])
    return geotherm


def _error(path, key, message):
    return ValueError(' '.join(f'{path}: {key}: {message}'.splitlines()))


def _table(value, path, key):
    if not isinstance(value, dict):
        raise _error(path, key, 'expected a table')


def _keys(value, allowed, required, path, key=''):
    _table(value, path, key or 'site')
    for name in value:
        if name not in allowed:
            raise _error(path, f'{key}.{name}' if key else name, 'unknown key')
    for name in sorted(required):
        if name not in value:
            raise _error(path, f'{key}.{name}' if key else name, 'missing required key')


def _number(value, path, key):
    if type(value) not in (int, float):
        raise _error(path, key, 'expected a number')
    return value


def _string(value, path, key):
    if not isinstance(value, str):
        raise _error(path, key, 'expected a string')
    return value


def _array(value, path, key, length=None):
    if not isinstance(value, list) or (length is not None and len(value) != length):
        message = 'expected an array' if length is None else f'expected an array of {length} values'
        raise _error(path, key, message)


def _numeric_rows(value, width, path, key):
    _array(value, path, key)
    if not value:
        raise _error(path, key, 'expected at least one row')
    for index, row in enumerate(value):
        row_key = f'{key}[{index}]'
        _array(row, path, row_key, width)
        for column, number in enumerate(row):
            _number(number, path, f'{row_key}[{column}]')
    return tuple(tuple(row) for row in value)


def _geotherm(value, path, key):
    _table(value, path, key)
    if 'form' not in value:
        raise _error(path, f'{key}.form', 'missing required key')
    form = _string(value['form'], path, f'{key}.form')
    if form == 'segments':
        _keys(value, {'form', 'segments', 'boundary'}, {'segments'}, path, key)
        boundary = value.get('boundary', 'below')
        if boundary not in ('above', 'below'):
            raise _error(path, f'{key}.boundary', "expected 'above' or 'below'")
        segments = _numeric_rows(value['segments'], 3, path, f'{key}.segments')
        return _segment_geotherm(segments, boundary)
    if form == 'points':
        _keys(value, {'form', 'points', 'gradient_below'}, {'points', 'gradient_below'}, path, key)
        points = _numeric_rows(value['points'], 2, path, f'{key}.points')
        gradient = _number(value['gradient_below'], path, f'{key}.gradient_below')
        return layered_geotherm(points, gradient)
    raise _error(path, f'{key}.form', f'unknown geotherm form {form!r}')


def _dataclass_keys(value, cls, path, key='', extra=()):
    definitions = fields(cls)
    required = {f.name for f in definitions if f.default is MISSING and f.default_factory is MISSING}
    _keys(value, {f.name for f in definitions} | set(extra), required, path, key)


def _stress_cases(value, path):
    _array(value, path, 'stress_cases')
    cases = []
    for index, case in enumerate(value):
        key = f'stress_cases[{index}]'
        _dataclass_keys(case, StressProfile, path, key)
        case = dict(case)
        for name, item in case.items():
            item_key = f'{key}.{name}'
            if name in ('label', 'source', 'regime'):
                _string(item, path, item_key)
            elif name == 'z_data':
                _array(item, path, item_key, 2)
                for column, number in enumerate(item):
                    _number(number, path, f'{item_key}[{column}]')
                case[name] = tuple(item)
            else:
                _number(item, path, item_key)
        cases.append(StressProfile(**case))
    return tuple(cases)


def _stress_rule(value, path):
    key = 'stress_rule'
    _keys(value, {'form', 'Sv_grad', 'source', 'Sv_int', 'Pp_grad', 'mu', 'fractions'},
          {'form', 'Sv_grad', 'source'}, path, key)
    form = _string(value['form'], path, 'stress_rule.form')
    if form != 'transitional':
        raise _error(path, 'stress_rule.form', f'unknown stress rule form {form!r}')
    arguments = {name: item for name, item in value.items() if name != 'form'}
    for name, item in arguments.items():
        item_key = f'{key}.{name}'
        if name == 'source':
            _string(item, path, item_key)
        elif name == 'fractions':
            _array(item, path, item_key)
            for index, number in enumerate(item):
                _number(number, path, f'{item_key}[{index}]')
            arguments[name] = tuple(item)
        else:
            _number(item, path, item_key)
    return transitional_bounds(**arguments)


def load_site(path):
    """Read a TOML site file and return its SiteProfile.

    path is a string or path-like object. Top-level keys use SiteProfile
    field names: depths are m, temperatures degrees C, stress and pressure
    gradients Pa/m, stress intercepts Pa gauge, strengths and Young's
    modulus Pa, and conductivity W/(m K). Ratios and friction coefficients are
    dimensionless. Optional keys retain SiteProfile's defaults.

    geotherm and optional geotherm_v11 are tables. A segments form gives
    [depth, temperature, gradient] rows in m, degrees C and degrees C/m;
    boundary='below' assigns a boundary depth to the segment starting there,
    and boundary='above' to the preceding segment. A points form gives
    [depth, temperature] rows and gradient_below in degrees C/m.

    stress_cases is an array of StressProfile tables, with z_data as two
    depths in m. Alternatively, a transitional stress_rule gives Sv_grad
    [Pa/m] and source, with optional Sv_int [Pa gauge], Pp_grad [Pa/m], mu
    and fractions [dimensionless]. Its defaults are transitional_bounds'
    defaults, including mu=0.8, independently of the site's own mu.
    strength_cases contains [label, UCS in Pa] pairs; data_basis maps input
    names to [basis, source] pairs. Arrays become the corresponding tuples.

    File, TOML and schema errors raise a one-line ValueError naming the
    file and key. This function parses data and executes no file content.
    Call validate_site on the returned profile to check physical ranges,
    temperature and stress consistency, and provenance labels and sources.
    """
    try:
        value = tomllib.loads(Path(path).read_text(encoding='utf-8'))
    except OSError as error:
        raise _error(path, 'file', error.strerror or str(error)) from None
    except (tomllib.TOMLDecodeError, UnicodeError) as error:
        raise _error(path, 'TOML', str(error)) from None

    _dataclass_keys(value, SiteProfile, path, extra=('stress_rule',))
    if 'stress_cases' in value and 'stress_rule' in value:
        raise _error(path, 'stress_rule', 'cannot be supplied together with stress_cases')
    arguments = {}
    definitions = {f.name: f for f in fields(SiteProfile)}
    for name, item in value.items():
        if name in ('geotherm', 'geotherm_v11'):
            arguments[name] = _geotherm(item, path, name)
        elif name == 'stress_cases':
            arguments[name] = _stress_cases(item, path)
        elif name == 'stress_rule':
            arguments['stress_cases'] = _stress_rule(item, path)
        elif name == 'strength_cases':
            _array(item, path, name)
            for index, pair in enumerate(item):
                _array(pair, path, f'{name}[{index}]', 2)
                _string(pair[0], path, f'{name}[{index}][0]')
                _number(pair[1], path, f'{name}[{index}][1]')
            arguments[name] = tuple(tuple(pair) for pair in item)
        elif name == 'data_basis':
            _table(item, path, name)
            for input_name, pair in item.items():
                _array(pair, path, f'{name}.{input_name}', 2)
                for index, text in enumerate(pair):
                    _string(text, path, f'{name}.{input_name}[{index}]')
            arguments[name] = {input_name: tuple(pair) for input_name, pair in item.items()}
        elif definitions[name].type is bool:
            if type(item) is not bool:
                raise _error(path, name, 'expected a boolean')
            arguments[name] = item
        elif definitions[name].type is str:
            arguments[name] = _string(item, path, name)
        else:
            arguments[name] = _number(item, path, name)
    return SiteProfile(**arguments)


def main(argv=None):
    """Write a starter TOML site file without overwriting an existing file."""
    import argparse
    import shlex

    parser = argparse.ArgumentParser(description='Write a starter site file to edit and evaluate.')
    parser.add_argument('path', help='path for the TOML site file')
    parser.add_argument('--from', dest='site', default='soultz', metavar='KEY',
                        help='start from soultz, larderello, united-downs, pannonian or newberry')
    parser.add_argument('--force', action='store_true', help='overwrite an existing file')
    arguments = parser.parse_args(argv)
    try:
        text = site_text(arguments.site)
        with Path(arguments.path).open('w' if arguments.force else 'x', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
    except FileExistsError:
        raise SystemExit(f'{arguments.path}: file exists; use --force to overwrite') from None
    except (ValueError, OSError) as error:
        raise SystemExit(' '.join(str(error).splitlines())) from None
    path = shlex.quote(arguments.path)
    print(f'Wrote {arguments.path}. Edit the site inputs, then run:')
    print(f'borethm-evaluate --site-file {path} --check')
    print(f'borethm-evaluate --site-file {path} --json {shlex.quote(str(Path(arguments.path).with_suffix(".json")))}')


if __name__ == '__main__':
    main()
