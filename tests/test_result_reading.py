"""Result readings explain existing checks without changing their outcomes."""
import copy
from types import SimpleNamespace

import pytest

from borethm import site_evaluation as se
from result_helpers import report_input, retained


KEYS = ('soultz', 'united-downs', 'larderello', 'pannonian', 'newberry')


@pytest.fixture(autouse=True)
def stored_water_density(monkeypatch):
    water_rho = retained('newberry')['programme']['drilling_simulated_rho_surface']
    monkeypatch.setattr(se.fluids, 'water', lambda: SimpleNamespace(rho_surface=water_rho))


@pytest.mark.parametrize('key', KEYS)
def test_reading_agrees_with_retained_checks(key):
    data = retained(key)
    original = copy.deepcopy(data)
    reading = se.reading(data)
    assert data == original
    assert set(reading) == {'calculation', 'scenarios_at_target', 'whole_programme', 'equipment', 'controlling_constraint'}
    assert reading['calculation'].startswith('Valid:')
    for state in data['cycle']['cases'][0]['states']:
        passed = sum(case['states'][state] in ('GO', 'CONDITIONAL') for case in data['cycle']['cases'])
        assert f'{state} {passed}/{len(data["cycle"]["cases"])}' in reading['scenarios_at_target']
    both_open = all(data['windows'][key]['open'] for key in ('drilling_fluid', 'trip_fluid'))
    assert reading['whole_programme'].startswith('One drilling fluid') == both_open
    for name in ('drilling_fluid', 'trip_fluid'):
        window = data['windows'][name]
        if not window['open']:
            for side in ('lo', 'hi'):
                by = window[side + '_by']
                assert by['state'] in reading['whole_programme']
                assert by['case'] in reading['whole_programme']
                assert f'{by["md"]:.0f} m' in reading['whole_programme']
    assert ('The tool passes' in reading['equipment']) == data['components']['tool']['ok']
    assert ('qualification is unresolved' in reading['equipment']) == (data['components']['coating']['status'] == 'INDETERMINATE')
    assert f'{data["tools"]["limit"]:g} C' in reading['equipment']
    assert f'{data["tools"]["coating"]["rating"]:g} C' in reading['equipment']
    if key == 'soultz':
        assert reading['controlling_constraint'].startswith('Pressure checks fail for: drilling, trip,')
    if key == 'larderello':
        assert 'A drilling fluid of 1.036 SG at surface.' == reading['controlling_constraint']
        assert all(reason.lower() in reading['whole_programme'].lower() for reason in data['status']['reasons'])


@pytest.mark.parametrize('kind', ['fluid', 'run', 'refinement'])
def test_failed_calculation_does_not_assess_physical_checks(kind):
    data = retained('newberry')
    if kind == 'fluid':
        data['components']['solver'].update(ok=False, converged=False)
    elif kind == 'run':
        data['components']['solver'].update(ok=False, runs_ok=False)
    else:
        data['components']['window_refinement']['converged'] = False
    data['status'] = se.site_status(data['components'])
    reading = se.reading(data)
    assert reading['calculation'].startswith('Not valid:')
    for name in ('scenarios_at_target', 'whole_programme', 'equipment'):
        assert reading[name].startswith('Not assessed')
    assert 'did not' in reading['controlling_constraint']


@pytest.mark.parametrize('kind,phrase', [
    ('fluid', 'drilling fluid of'), ('schedule', 'circulation schedule'),
    ('rig', 'pump capacity'), ('cleaning', 'hole cleaning'), ('excluded', 'cases outside the frictional limit'),
])
def test_conditional_reading_names_only_the_actual_condition(kind, phrase):
    data = retained('newberry')
    c = data['components']
    if kind == 'fluid':
        c['prescription']['drilling_fluid'].update(heavier_than_water=True, fluid=1050.)
    elif kind == 'schedule':
        c['tool']['detail'] = 'PASS with the schedule found'
    elif kind == 'rig':
        c['pumps']['within_rig'] = False
    elif kind == 'cleaning':
        c['hole_cleaning']['ok'] = False
    else:
        c['admissibility']['inadmissible'] = ['excluded case']
    data['status'] = se.site_status(c)
    assert data['status']['label'] == 'CONDITIONAL'
    assert len(data['status']['reasons']) == 1
    reading = se.reading(data)
    conditions = reading['whole_programme'].split(' Conditions: ', 1)[1].lower()
    assert phrase in conditions
    for other in ('drilling fluid of', 'circulation schedule', 'pump capacity', 'hole cleaning', 'cases outside the frictional limit'):
        assert (other in conditions) == (other == phrase)


def test_pump_failure_and_unrated_coating_are_explicit():
    data = retained('newberry')
    data['components']['pumps'].update(ok=False, within_rig=False)
    data['tools']['coating']['rating'] = None
    data['status'] = se.site_status(data['components'])
    reading = se.reading(data)
    assert 'standpipe pressure exceeds the pump limit' in reading['whole_programme']
    assert 'pumping duty exceeds the reference rig capacity' in reading['whole_programme']
    assert 'No coating rating is stated' in reading['equipment']


@pytest.mark.parametrize('key', KEYS)
def test_report_inserts_reading_under_heading_and_export_uses_same_text(key, capsys):
    result = report_input(key)
    se.report(result)
    lines = capsys.readouterr().out.splitlines()
    data = se.result_dict(result)
    assert data['reading'] == se.reading(retained(key))
    for index, (name, label) in enumerate(se._READING_LABELS, start=3):
        assert lines[index] == f'  {label}: {data["reading"][name]}'
    assert lines[8].startswith('  Target:')
    assert f'  STATUS: {result["status"]["label"]}' in lines


@pytest.mark.parametrize('omitted', ['components', 'status'])
def test_partial_result_does_not_gain_a_reading(omitted):
    result = report_input('newberry')
    result.pop(omitted)
    assert 'reading' not in se.result_dict(result)
