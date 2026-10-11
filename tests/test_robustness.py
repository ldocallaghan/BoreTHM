"""Independent bracket checks and the C5 direction regression."""
import json
import hashlib
import time

import numpy as np
import pytest

import robustness as rb
import tool_thermal as tt
import wall_thermal as wt


def test_warm_stage_peak_is_retained_after_cold_coolant_arrives():
    lump = tt.Lump.of_pipe(0.04, 0.08, 4.e6)
    kwargs = dict(md_bottom=20., speed=10., T0=20., h_static_out=0., h_static_in=0.,
                  stages=[10.], stage_s=10., circulating=lambda md: (60., 1000., 1000.), dt=1.)
    optimistic, _ = tt.trip_in(lump, lambda md: 250., **kwargs)
    adverse, depth = rb.run_in_bracket(lump, lambda md: 250., turnover=lambda md: 5., **kwargs)
    assert optimistic.peak()[0] == 60.
    assert adverse.peak()[0] == 250.
    assert adverse.T_f[-1] == pytest.approx(60.)
    assert depth[np.argmax(adverse.T_f)] == 10.
    assert adverse.t[-1] == pytest.approx(12.)


def test_elapsed_column_includes_stage_time():
    sampled = []
    def evolving(md, elapsed):
        sampled.append((md, elapsed))
        return 20. + elapsed
    lump = tt.Lump.of_pipe(0.04, 0.08, 4.e6)
    result, _ = rb.run_in_bracket(lump, lambda md: 20., md_bottom=20., speed=10.,
        T0=20., h_static_out=100., h_static_in=100., stages=[10.], stage_s=10.,
        circulating=lambda md: (20., 1000., 1000.), dt=1., evolving=evolving)
    assert sampled[0] == (10., 1.)
    assert sampled[-1] == (20., 12.)
    assert result.t[-1] == pytest.approx(12.)


def test_radial_refinement_halves_log_spacing_and_can_continue_a_field():
    state = wt.State('circulating', 10., T_fluid=20., h=100.)
    base = wt.run([state], 200., 0.11, 2.6, 2.7e6, n=20, r_max=30.)
    with rb.numerical_overrides(radial=True):
        fine = wt.run([state], 200., 0.11, 2.6, 2.7e6, n=20, r_max=30.)
        continued = wt.run([state], 200., 0.11, 2.6, 2.7e6, n=20, r_max=30., T0=fine.fields[-1])
    assert len(fine.r) == 39
    np.testing.assert_allclose(np.diff(np.log(fine.r)), np.diff(np.log(base.r))[0] / 2.)
    assert continued.T_wall[-1] < fine.T_wall[-1]
    assert wt.run([state], 200., 0.11, 2.6, 2.7e6, n=20).r.size == 20


def test_time_refinement_splits_every_step_without_changing_the_duration():
    base = wt.time_steps(117., dt0=1., growth=1.2)
    with rb.numerical_overrides(temporal=True):
        fine = wt.time_steps(117., dt0=1., growth=1.2)
    np.testing.assert_allclose(np.asarray(fine).reshape(-1, 2).sum(axis=1), base)
    assert max(fine) == pytest.approx(max(base) / 2.)
    assert sum(fine) == pytest.approx(117.)


@pytest.mark.parametrize('margin', [0.041, -0.041])
def test_twenty_percent_threshold_rule(margin):
    assert not rb.threshold_unresolved(margin, 0.008)
    assert rb.threshold_unresolved(margin, -0.009)


# D/T signs are changes in the common-window widths. Temperature signs are
# changes in the best tested tool margin. Magnitudes are intentionally free.
SIGNS = {
    'soultz': {
        'A1': [(-1, -1, -1)], 'A2': [(1, 1, 1)],
        'A3': [(0, 0, 0), (0, 0, -1)], 'A4': [(0, -1, -1)],
        'A5': [(0, 0, -1)], 'A6': [(0, 0, 0), (0, 1, 1)],
        'A7': [(-1, -1, 0)], 'A8': [(0, 1, 0), (0, -1, 0)],
        'A9': [(-1, -1, -1), (1, -1, 1), (0, 0, 0), (-1, -1, 1)]},
    'united-downs': {
        'A1': [(-1, 1, -1)], 'A2': [(1, -1, 1)],
        'A3': [(0, 0, 0), (0, 0, -1)], 'A4': [(0, -1, -1)],
        'A5': [(0, 0, -1)], 'A6': [(0, 0, 0), (0, 1, 1)],
        'A7': [(0, 0, 0)], 'A8': [(0, 1, 0), (0, -1, 0)],
        'A9': [(-1, -1, -1), (-1, -1, 1), (-1, 0, 0), (-1, -1, 1)]},
    'pannonian': {'A9': [(-1, -1, -1), (1, -1, 1), (-1, 0, 0), (-1, -1, 1)]}}


@pytest.mark.slow
@pytest.mark.parametrize('key', ['soultz', 'united-downs', 'pannonian'])
def test_live_comparisons_run_and_their_signs_are_pinned(key):
    """Run every ledger definition; retain its evidence before asserting signs."""
    site, base = rb.reviewed_base(key)
    destination = rb.ROOT / 'results/robustness' / (key + '.json')
    ledger = dict(site=key, base=rb.metrics(base), versions=rb.se.versions(),
                  source_sha256=hashlib.sha256(rb.Path(rb.__file__).read_bytes()).hexdigest(),
                  programme=json.loads((rb.CHECKPOINT / (key + '.json')).read_text())['programme'],
                  comparisons=[])
    requested = ['A9'] if key == 'pannonian' else rb.IDS
    for identifier in requested:
        print('Live direction check:', key, identifier, flush=True)
        started = time.perf_counter()
        item = next(rb.comparisons(site, base, [identifier]))
        item['elapsed_seconds'] = time.perf_counter() - started
        ledger['comparisons'].append(item)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(rb.se._jsonable(ledger), indent=2) + '\n')
    for item in ledger['comparisons']:
        assert not item['decision_relevant'], (key, item['id'])
        actual = []
        for name, value in item['variants'].items():
            change = value['change']
            assert value['metrics']['solver_ok'], (key, item['id'], name)
            assert value['metrics']['status']['label'] == 'NO-GO', (key, item['id'], name)
            scalars = [change['pressure_margin_SG']['drilling_fluid'],
                       change['pressure_margin_SG']['trip_fluid'], change['tool_margin_C']]
            actual.append(tuple(0 if abs(delta) < 1e-8 else int(np.sign(delta)) for delta in scalars))
            if item['id'] == 'A6' and name == 'drilling fluid throughout':
                # Its lighter weight is adverse for breakout even if the
                # family of feasible weights widens as temperatures change.
                assert change['actual_fluid_slack_SG']['trip_fluid']['lower'] < 0.
                assert change['actual_fluid_slack_SG']['trip_fluid']['upper'] > 0.
        assert actual == SIGNS[key][item['id']], (key, item['id'], actual)
