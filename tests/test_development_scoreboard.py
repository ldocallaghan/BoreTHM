"""Fixed comparison targets, population weights and unavailable event coverage."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('development_scoreboard', ROOT/'validation/scoreboard/scoreboard.py')
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)


def row(well, bha, measured=50., at22=55., at84=60.):
    return dict(well=well, bha=bha, success=True, raw_spp_psi=800., raw_differential_psi=100.,
        spp_psi=600., measured_bit_C=measured, bit_C=55., source='fixed source',
        measured_return_C=75., return_C=70., model_hydraulic_W=100000., measured_hydraulic_W=200000.,
        bore_22ft_C=at22, bore_84ft_C=at84)


def test_pressure_targets_and_motorless_subset_are_distinct():
    result = score.scoreboard([row('16A', '38'), row('16B', '12'), row('16B', '17')], [])
    pressure = {(r['well'], r['group']): r for r in result if r['gap'] == 'G1'}
    assert pressure['16A', '38']['bias'] == -100.
    assert pressure['16B', '12']['bias'] == -200.
    assert ('16B', '17') not in pressure


def test_regular_pipe_pool_uses_its_declared_positions_and_excludes_trials():
    result = score.scoreboard([row('16B', '12', 55., 60., 100.),
                              row('16B', '38', 100., 80., 95.),
                              row('16B', '17', 50., 90., 55.)], [])
    groups = {r['group']: r for r in result if r['gap'] == 'G6'}
    assert groups['independent regular pipe']['compared'] == 2
    assert groups['independent regular pipe']['bias'] == 0.
    assert groups['trial']['bias'] == 5.


def test_original_unavailable_run_in_events_remain_in_the_population():
    inputs = json.loads((ROOT/'validation/scoreboard/transient-inputs.json').read_text())
    events = inputs['events']
    assert len(events) == len({e['event_id'] for e in events}) == 11
    assert {e['event_id'] for e in events if not e['archived_available']} == {'23-off006', '35r2-off008'}
    summary = score.aggregate('G4', '16A', 'unavailable', [], 1, units='degC')
    assert summary['compared'] == 0 and summary['unavailable'] == 1
    assert 'bias' not in summary


def test_frozen_baseline_sources_and_results_match_their_checksums():
    archive = ROOT/'validation/scoreboard/baseline'
    manifest = json.loads((archive/'manifest.json').read_text())
    for name, expected in manifest['sources_sha256'].items():
        assert score.sha(ROOT/name) == expected, name
    # Model digests describe the baseline calculation. Candidate code may change.
    assert manifest['model_sources_sha256']
    assert all(len(value) == 64 for value in manifest['model_sources_sha256'].values())
    for name, expected in manifest['results_sha256'].items():
        assert score.sha(archive/name) == expected, name
    checks = score.read_csv(archive/'baseline-reproduction.csv')
    assert checks and all(row['passed'] == 'True' for row in checks)
