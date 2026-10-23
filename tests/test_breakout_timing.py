"""Breakout timing: fresh paired runs, fixed-grid brackets and published values."""
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import breakout_timing as timing

pytestmark = pytest.mark.slow
RESULTS = ROOT / 'results/v1.3.6/breakout-timing'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


@pytest.fixture(scope='module')
def golden():
    return read(ROOT / 'tests/golden/v136_breakout_timing.json')


@pytest.fixture(scope='module')
def fresh(tmp_path_factory):
    directory = tmp_path_factory.mktemp('breakout-timing')
    records = {}

    def run(key, minutes):
        if (key, minutes) not in records:
            records[key, minutes], _ = timing.run_case(key, minutes, directory)
        return records[key, minutes]

    return directory, run


def assert_window(actual, expected):
    for side in ('lo', 'hi'):
        assert actual[side] / 1000 == pytest.approx(expected[side] / 1000, abs=0.002)
        assert actual[side + '_by']['state'] == expected[side + '_by']['state']
        assert actual[side + '_by']['case'] == expected[side + '_by']['case']
        assert actual[side + '_by']['md'] == pytest.approx(expected[side + '_by']['md'], abs=0.01)
    assert actual['open'] == expected['open']


@pytest.mark.parametrize('key', timing.SITES)
@pytest.mark.parametrize('minutes', (0, 60))
def test_paired_runs_reproduce_the_reviewed_requirements(key, minutes, golden, fresh):
    actual = fresh[1](key, minutes)
    expected = golden['pairs'][key][str(minutes)]
    assert actual['settings'] == expected['settings']
    assert actual['z_m'] == pytest.approx(expected['z_m'], abs=0.01)
    assert actual['status']['label'] == expected['programme_verdict'] == 'NO-GO'
    assert actual['components']['solver']['ok']
    assert actual['windows']['refinement']['converged']
    assert len(actual['cycle']['cases']) == len(expected['cases'])
    for case, pin in zip(actual['cycle']['cases'], expected['cases']):
        assert (case['label'], case['UCS']) == (pin['label'], pin['UCS'])
        assert case['drill_SG'] == pytest.approx(pin['drill_SG'], abs=0.002)
        assert case['drill_rho_surface'] / 1000 == pytest.approx(pin['drill_rho_surface'] / 1000, abs=0.002)
        assert case['states'] == pin['states']
        assert case['verdict'] == pin['verdict']
    for name in ('drilling_fluid', 'trip_fluid'):
        assert_window(actual['windows'][name], expected['windows'][name])


@pytest.mark.parametrize('key', timing.SITES)
def test_scan_reproduces_the_reviewed_opening_bracket(key, golden, fresh):
    expected = golden['scans'][key]
    if timing.levers.fingerprint() == golden['provenance']['source_sha256']:
        actual = read(RESULTS / f'scan-{key}.json')
    else:
        actual = timing.run_scan(key, fresh[0], reuse=True)
    assert actual['scan_minutes'] == expected['scan_minutes'] == list(timing.SCAN_MINUTES)
    assert len(actual['trials']) == len(expected['trials'])
    for trial, pin in zip(actual['trials'], expected['trials']):
        assert trial['delay_min'] == pin['delay_min']
        assert trial['deciding_case'] == pin['deciding_case']
        assert trial['drill_SG'] == pytest.approx(pin['drill_SG'], abs=0.002)
        assert_window(trial['drilling_fluid'], pin['drilling_fluid'])
    assert timing.critical_delay(actual['trials']) == expected['critical_delay']
    assert actual['critical_delay'] == expected['critical_delay']
