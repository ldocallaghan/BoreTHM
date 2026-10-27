"""Check archived FORGE whole-well comparison arithmetic without new solves.

Expected summaries are from the reviewed S1/S2 evidence and S2b accounting.
These tests verify saved statistics, preservation and accounting identities;
they do not validate a future physical model against the observations.
"""
import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1]/'validation/forge16b'
COUNTS = {3: 3, 4: 2, 11: 4, 12: 12, 13: 14, 15: 4, 16: 15,
          17: 14, 18: 10, 19: 10, 20: 11, 27: 5, 38: 5}
# One declared sensor branch per run. Extra unresolved/sensitivity branches
# remain in the evidence and are checked against the complete summary table.
S1_BIAS = {3: -4.803387058110474, 4: -24.173605, 11: -16.175196,
           12: -18.273939, 13: -8.415683, 15: -4.208807, 16: -4.798524,
           17: 3.180577, 18: 1.693255, 19: 1.178351, 20: 1.486791,
           27: -3.800043, 38: -1.563843}


def read(path):
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope='module')
def s2():
    plan = json.loads((DATA/'s2/plan.json').read_text())
    samples = {s['id']: s for s in plan['samples']}
    rows = [json.loads(line) for line in (DATA/'s2/results.jsonl').read_text().splitlines()]
    return plan, samples, rows


def test_complete_cases_and_unchanged_replays(s2):
    plan, _, rows = s2
    assert len(rows) == 934
    assert {r['case_id'] for r in rows} == {r['case_id'] for r in plan['cases']}
    assert all(r['success'] and r['solver_success'] for r in rows)
    replays = [r for r in rows if 'max_saved_temperature_difference_C' in r]
    assert len(replays) == 467
    assert max(r['max_saved_temperature_difference_C'] for r in replays) == 0
    assert Counter(r['rheology_case'] for r in rows) == {
        's1_original': 109, 's2_revised': 109,
        'blind_original': 358, 'water_rheology_sensitivity': 358}


@pytest.mark.parametrize('run', tuple(COUNTS))
def test_blind_run_summary(s2, run):
    _, samples, rows = s2
    data = [r for r in rows if r['well'] == '16B' and
            r['rheology_case'] == 's1_original' and int(r['run']) == run]
    assert len(data) == COUNTS[run]
    branch = 'bore_22ft_C' if run <= 16 else 'bore_84ft_C'
    bias = statistics.mean(r[branch]-samples[r['sample']]['measured_MWD_C'] for r in data)
    assert bias == pytest.approx(S1_BIAS[run], abs=1e-6, rel=0)


def test_both_protocol_versions_and_every_sensor_branch(s2):
    _, samples, rows = s2
    comparisons = read(DATA/'s2/16b-primary-revision.csv')
    assert len(comparisons) == 18
    for c in comparisons:
        for version, mode in [('S1_v1', 's1_original'), ('S2_v2', 's2_revised')]:
            data = [r for r in rows if r['well'] == '16B' and
                    r['rheology_case'] == mode and r['run'] == c['run']]
            model = statistics.mean(r[f"bore_{c['position_ft']}ft_C"] for r in data)
            observed = statistics.mean(samples[r['sample']]['measured_MWD_C'] for r in data)
            assert len(data) == int(c['n'])
            assert model == pytest.approx(float(c[version+'_model_mean_C']), abs=1e-10, rel=0)
            assert model-observed == pytest.approx(float(c[version+'_bias_C']), abs=1e-10, rel=0)
        change = float(c['S2_v2_model_mean_C'])-float(c['S1_v1_model_mean_C'])
        assert change == pytest.approx(float(c['change_model_C']), abs=1e-10, rel=0)
    changed = {int(c['run']) for c in comparisons if abs(float(c['change_model_C'])) > 1e-10}
    assert changed == {11, 12, 16, 17, 18}


def test_matched_bins_and_pressure_coverage(s2):
    _, samples, _ = s2
    bins = read(DATA/'s2/matched-primary-comparison.csv')
    assert len(bins) == 13
    assert sum(r['shared'] == 'True' for r in bins) == 10
    assert sum(s['well'] == '16A' and s['spp_psi'] is not None for s in samples.values()) == 135
    assert sum(s['well'] == '16A' and s['spp_psi'] is None for s in samples.values()) == 223


def test_motorless_included_terms_and_replays():
    rows = read(DATA/'s2b/pressure-samples.csv')
    assert len(rows) == 90
    assert Counter((r['run'], r['rheology_case']) for r in rows) == {
        (str(run), mode): count for run, count in ((12, 12), (13, 14), (15, 4), (16, 15))
        for mode in ('s1_original', 's2_revised')}
    for r in rows:
        total = sum(float(r[k]) for k in ('pipe_body_psi', 'bha_hwdp_psi',
            'bha_lower_aggregate_psi', 'bit_nozzles_psi', 'annulus_psi', 'density_column_psi'))
        assert total == pytest.approx(float(r['model_spp_psi']), abs=1e-9, rel=0)
        assert float(r['tool_joints_psi']) == float(r['surface_lines_psi']) == 0.
        assert float(r['motor_allowance_psi']) == 0.
        assert r['unknown_tool_loss_psi'] == ''
    replays = read(DATA/'s2b/replays.csv')
    assert len(replays) == 90 and all(r['success'] == 'True' for r in replays)
    assert max(float(r['max_temperature_difference_C']) for r in replays) == 0.
    assert max(abs(float(r['pressure_difference_psi'])) for r in replays) == 0.
    primary = [r for r in rows if r['rheology_case'] == 's2_revised']
    assert sum(float(r['raw_differential_psi']) < 0 for r in primary) == 7


def test_external_estimate_accounting():
    rows = read(DATA/'s2b/scenario-budgets.csv')
    assert len(rows) == 6480
    assert set(Counter(r['case_id'] for r in rows).values()) == {72}
    for r in rows:
        increment = sum(float(r[k]) for k in ('bha_bore_increment_psi',
            'bha_annulus_increment_psi', 'joint_internal_increment_psi',
            'joint_annulus_increment_psi', 'joint_local_increment_psi',
            'bha_local_increment_psi', 'surface_lines_estimate_psi'))
        total = float(r['model_spp_psi'])+increment
        assert total == pytest.approx(float(r['accounted_psi']), abs=1e-9, rel=0)
        assert float(r['measured_spp_psi'])-total == pytest.approx(
            float(r['remaining_residual_psi']), abs=1e-9, rel=0)
        assert total/float(r['measured_spp_psi']) == pytest.approx(
            float(r['accounted_fraction']), abs=1e-12, rel=0)
        assert r['unknown_tool_loss_psi'] == ''


@pytest.mark.parametrize('stage', ('s1', 's2', 's2b'))
def test_archived_file_hashes(stage):
    folder = DATA/stage
    manifest = json.loads((folder/'execution-manifest.json').read_text())
    for name, expected in manifest['archived_output_sha256'].items():
        assert hashlib.sha256((folder/name).read_bytes()).hexdigest() == expected, name


def test_original_s1_and_s2_preserved_during_pressure_accounting():
    plan = json.loads((DATA/'s2b/plan.json').read_text())
    assert len(plan['preserved_archives']) == 66
    for name, expected in plan['preserved_archives'].items():
        assert hashlib.sha256((DATA/name).read_bytes()).hexdigest() == expected, name
