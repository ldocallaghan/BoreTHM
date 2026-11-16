"""The comparison with the recorded release results, within a relative
tolerance on every platform."""
import copy
import json

import make_golden_reproduction as golden


def recorded_newberry():
    return json.loads(golden.path('newberry', 'v1.8.0').read_text(encoding='utf-8'))


def test_the_platform_record_names_system_python_and_numpy():
    record = json.loads(golden.PLATFORM.read_text(encoding='utf-8'))
    assert set(record) == {'system', 'python', 'numpy'}
    assert record['python'].count('.') == 1


def test_the_recorded_platform_also_uses_the_tolerance_comparison(monkeypatch):
    record = json.loads(golden.PLATFORM.read_text(encoding='utf-8'))
    monkeypatch.setattr(golden, 'this_platform', lambda: dict(record))
    text = golden.comparison()
    assert text.startswith('relative tolerance 1e-09') and f"running on {record['system']}" in text
    monkeypatch.setattr(golden, 'this_platform', lambda: dict(record, system='Windows'))
    text = golden.comparison()
    assert text.startswith('relative tolerance 1e-09') and 'running on Windows' in text


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
