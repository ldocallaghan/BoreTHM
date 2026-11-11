"""Defaults that restate the default result.

For each built-in site under the current physics, each field that
operation_defaults marks restates_default, stated alone at the value it
returns, gives the default result_dict exactly, apart from the operations
record, the sentence that names the stated operations behind a check, and
the input warnings validate_operations gives for the stated value. Each
value is stated with a source, as a site file would give it.
"""
import json
import re

import pytest

from borethm import operation_defaults
from borethm import site_evaluation as se
from borethm.operations import Operations
from borethm.programme import NAMED_PIPES

pytestmark = [pytest.mark.slow, pytest.mark.default_physics]
PHYSICS = 'v1.8.0'
SITES = ('soultz', 'united-downs', 'larderello', 'pannonian', 'newberry')
STATED = re.compile(r' Stated operations used in this check: [^.]*(?:\.\d[^.]*)*\.')


def restated(key):
    defaults = operation_defaults(se.find_site(key))
    return [name for name, entry in defaults.items() if entry['restates_default']]


CASES = [(key, name) for key in SITES for name in restated(key)]


@pytest.fixture(scope='module')
def default_results():
    cache = {}

    def get(key):
        if key not in cache:
            cache[key] = se.result_dict(se.evaluate(se.find_site(key), physics=PHYSICS))
        return cache[key]

    return get


def without_stated(data):
    """A result_dict as JSON text, without the versions and operations
    records, the sentences naming stated operations and the warnings on the
    stated operations."""
    data = {k: v for k, v in data.items() if k not in ('versions', 'operations')}
    data['input_warnings'] = [w for w in data['input_warnings'] if not w.startswith('operations.')]
    return STATED.sub('', json.dumps(data, sort_keys=True))


@pytest.mark.parametrize('key,name', CASES)
def test_stating_a_restated_default_reproduces_the_default_result(default_results, key, name):
    site = se.find_site(key)
    value = operation_defaults(site)[name]['value']
    if name == 'pipes':
        value = tuple(NAMED_PIPES[pipe] for pipe in value)
    operations = Operations(**{name: value}, sources={name: ('assumed', 'the model default')})
    stated = se.result_dict(se.evaluate(site, physics=PHYSICS, operations=operations))
    assert stated['operations'][name]['stated'] is True
    assert without_stated(stated) == without_stated(default_results(key))
