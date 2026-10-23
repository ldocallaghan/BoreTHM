"""Exact comparison of site inputs for tests and the checkout example."""
from dataclasses import fields

import numpy as np


def assert_sites_equal(actual, expected, allow_extra_basis=False):
    """Compare all fields, sampling geotherms every 10 m from 0 to 20,000 m."""
    depths = np.arange(0.0, 20000.0 + 10.0, 10.0)
    for definition in fields(expected):
        name = definition.name
        value, reference = getattr(actual, name), getattr(expected, name)
        if name in ('geotherm', 'geotherm_v11') and reference is not None:
            assert callable(value), name
            np.testing.assert_array_equal(value(depths), reference(depths), err_msg=name)
        elif name == 'data_basis' and allow_extra_basis:
            assert {key: value[key] for key in reference} == reference, name
        else:
            assert value == reference, name
