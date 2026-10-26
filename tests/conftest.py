"""Shared fixtures for the installed package."""
import os
import sys

import pytest

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden")


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", default=False,
                     help="also run the physical regressions marked slow")


def pytest_collection_modifyitems(config, items):
    """Skip tests marked slow unless --runslow is given. An explicit -m
    expression (for example -m slow) selects tests on its own terms."""
    if config.getoption("--runslow") or config.getoption("markexpr"):
        return
    skip = pytest.mark.skip(reason="slow: run with --runslow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def evaluated():
    """site_evaluation.evaluate, run once per site and set of arguments for the
    whole session. The results are only read by the tests."""
    from borethm import site_evaluation as se
    cache = {}

    def get(site, **kw):
        # Existing model and historical-table regressions retain their mode.
        # Corrected reference tests request v1.3.4 explicitly.
        kw.setdefault('circulation', 'v1.3.3')
        key = (site.name, tuple(sorted(kw.items())))
        if key not in cache:
            cache[key] = se.evaluate(site, **kw)
        return cache[key]

    return get
