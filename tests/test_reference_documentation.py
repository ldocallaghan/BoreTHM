"""Published reference tables and summary values follow their linked evidence."""
import json
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESIGN = (ROOT / 'docs/science/design-comparisons.md').read_text(encoding='utf-8')
SUMMARY = (ROOT / 'docs/guides/summary.md').read_text(encoding='utf-8')
SITES = {'soultz': 'Soultz', 'united-downs': 'United Downs'}
WORDS = ('zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine')


def evidence(pattern):
    paths = set(re.findall(pattern, DESIGN.split('## Evaluation and search', 1)[0]))
    assert len(paths) == 1, paths
    return json.loads((ROOT / paths.pop()).read_text(encoding='utf-8'))


def source(key):
    return evidence(r'\]\(\.\./\.\./([^)]*/reference/' + key + r'\.json)\)')


def base_trial(key):
    data = evidence(r'\]\(\.\./\.\./([^)]*/levers/' + key + r'/L4/summary\.json)\)')
    expected = dict(pipe='TK-Drakon coated', shoe_m=4000., flow_L_s=40 if key == 'soultz' else 50,
                    pv_fraction=1., allowance_SG=.02, form_h=0., bhp_Pa=None, coating_rating_C=204.)
    matches = [trial for trial in data['trials'] if trial['settings'] == expected]
    assert len(matches) == 1
    trial = matches[0]
    assert trial['metrics']['tool_peaks_C']['run_in'] == min(
        attempt['peak_C'] for attempt in trial['metrics']['run_in_search']['attempts'])
    return trial


def test_target_cases_and_whole_hole_bounds_match_the_reference_tables():
    for key, name in SITES.items():
        data = source(key)
        for case in data['cycle']['cases']:
            label = case['label']
            if key == 'soultz':
                label = label.removesuffix(f", lab UCS {case['UCS'] / 1e6:.0f}")
            else:
                label = label.removeprefix('Reinecker et al. (2021), ')
            row = f"| {name}: {label} | {case['UCS'] / 1e6:.0f} | {case['drill_SG']:.3f} / {case['drill_SG_hi']:.3f} | {case['verdict']} |"
            assert row in DESIGN
        for key, state in (('drilling_fluid', 'drilling'), ('trip_fluid', 'trip')):
            w = data['windows'][key]
            assert f"| {name} {state} | {w['lo'] / 1000:.5f} / {w['hi'] / 1000:.5f} | {(w['hi'] - w['lo']) / 1000:+.5f} |" in DESIGN


def test_tool_peaks_and_coating_qualification_match_the_reference_records():
    peaks = []
    coatings = []
    for key, name in SITES.items():
        p = base_trial(key)['metrics']['tool_peaks_C']
        peaks.append(f"{name}: {p['drilling']:.1f} / {p['connection']:.1f} / {p['run_in']:.1f} °C")
        coatings.append(source(key)['tools']['coating'])
    assert '; '.join(peaks) + '.' in DESIGN
    assert all(c['rating'] == 204. and c['status'] == 'INDETERMINATE' for c in coatings)
    sentence = (f"Reference-practice coating run-in maxima are {coatings[0]['trip_in']['max']:.1f} °C "
                f"at Soultz and {coatings[1]['trip_in']['max']:.1f} °C at United Downs, against the stated 204 °C rating.")
    assert sentence in DESIGN
    practice = base_trial('soultz')['metrics']['practice_run_in_peak_C']
    assert f"Soultz's reference FORGE-practice run-in reaches {practice:.1f} °C" in DESIGN


@pytest.mark.parametrize('key,name', SITES.items())
def test_summary_counts_bounds_and_tool_peaks_follow_the_same_evidence(key, name):
    data = source(key)
    cases = data['cycle']['cases']
    opened = sum(case['drill_SG'] <= case['drill_SG_hi'] + 1e-9 for case in cases)
    assert f'{WORDS[opened]} of {WORDS[len(cases)]}' in DESIGN.lower()
    assert data['status']['label'] == 'NO-GO'
    for field in ('drilling_fluid', 'trip_fluid'):
        w = data['windows'][field]
        assert w['lo'] > w['hi'] and not w['open']
    peaks = base_trial(key)['metrics']['tool_peaks_C']
    row = (f"| {name}, {data['site']['target_depth_m'] / 1000:.2f} km | {opened} of {len(cases)} cases | "
           f"No allowable drilling or trip-fluid density | {peaks['drilling']:.1f} / {peaks['run_in']:.1f} °C |")
    assert row in SUMMARY
