"""The comparison with the recorded release results: exact on the recorded
platform, within a relative tolerance elsewhere."""
import copy
import json

import make_golden_reproduction as golden


def recorded_newberry():
    return json.loads(golden.path('newberry', 'v1.8.0').read_text(encoding='utf-8'))


def test_the_platform_record_names_system_python_and_numpy():
    record = json.loads(golden.PLATFORM.read_text(encoding='utf-8'))
    assert set(record) == {'system', 'python', 'numpy'}
    assert record['python'].count('.') == 1


def test_another_platform_selects_the_tolerance_comparison(monkeypatch):
    record = json.loads(golden.PLATFORM.read_text(encoding='utf-8'))
    monkeypatch.setattr(golden, 'this_platform', lambda: dict(record))
    kind, text = golden.comparison()
    assert kind == 'exact' and text.startswith('exact comparison')
    monkeypatch.setattr(golden, 'this_platform', lambda: dict(record, system='Windows'))
    kind, text = golden.comparison()
    assert kind == 'tolerance'
    assert 'relative tolerance 1e-09' in text and 'running on Windows' in text


def test_differences_allow_last_digits_and_the_residual_floor():
    data = recorded_newberry()
    assert golden.differences(data, data) == []
    check = data['programme']['energy_check']
    nudged = copy.deepcopy(data)
    nudged['T_rock_C'] = data['T_rock_C'] * (1 + 1e-12)
    nudged['programme']['energy_check']['residual_W'] = check['residual_W'] + 5e-8
    nudged['programme']['energy_check']['relative_residual'] = (
        check['relative_residual'] + 5e-8 / check['assigned_W'])
    assert golden.differences(nudged, data) == []
    moved = copy.deepcopy(data)
    moved['T_rock_C'] = data['T_rock_C'] * (1 + 1e-6)
    moved['programme']['energy_check']['residual_W'] = check['residual_W'] + 1e-6
    moved['status']['label'] = 'GO' if data['status']['label'] != 'GO' else 'NO-GO'
    found = golden.differences(moved, data)
    assert sorted(line.split(':')[0] for line in found) == [
        '/T_rock_C', '/programme/energy_check/residual_W', '/status/label']
