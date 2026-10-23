"""Retained breakout-timing evidence and published numbers, without fresh solves."""
import hashlib
import json
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import breakout_timing as timing

RESULTS = ROOT / 'results/v1.3.6/breakout-timing'
PAGE = ROOT / 'docs/science/breakout-timing.md'
NAMES = {'soultz': 'Soultz', 'united-downs': 'United Downs'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


@pytest.fixture(scope='module')
def golden():
    return read(ROOT / 'tests/golden/v136_breakout_timing.json')


def test_retained_scan_files_match_the_reviewed_evidence(golden):
    for name, digest in golden['provenance']['evidence_sha256'].items():
        assert hashlib.sha256((RESULTS / name).read_bytes()).hexdigest() == digest, name
    for key in timing.SITES:
        scan = read(RESULTS / f'scan-{key}.json')
        for trial in scan['trials']:
            path = RESULTS / trial['evidence']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == trial['evidence_sha256']
            record = read(path)
            assert record['source_sha256'] == scan['source_sha256']
            assert record['settings']['form_h'] == trial['delay_min'] / 60
            assert record['windows']['drilling_fluid'] == trial['drilling_fluid']
            assert record['cycle']['drill_SG'] == trial['drill_SG']


def block(page, name):
    start, end = f'<!-- {name}:start -->', f'<!-- {name}:end -->'
    assert page.count(start) == page.count(end) == 1, name
    return page.split(start)[1].split(end)[0]


def numbers(text):
    return re.findall(r'(?<![\w.])\d+(?:\.\d+)?(?![\w.])', text)


def table(text):
    rows = [[cell.strip() for cell in line.strip('|').split('|')]
            for line in text.splitlines() if line.startswith('|')]
    return rows[0], rows[2:]


def test_document_numbers_match_the_result_files():
    page = PAGE.read_text(encoding='utf-8')
    pairs = {(key, m): read(RESULTS / f'{key}-{m}min.json')
             for key in timing.SITES for m in (0, 60)}
    scans = {key: read(RESULTS / f'scan-{key}.json') for key in timing.SITES}
    deciding = lambda key, m: next(c for c in pairs[key, m]['cycle']['cases']
                                   if c['label'] == pairs[key, m]['cycle']['deciding_case'])
    overview = [f"{deciding(key, m)['drill_SG']:.2f}" for key in timing.SITES for m in (0, 60)]
    overview += [str(scans[key]['critical_delay']['bracket'][side])
                 for key in timing.SITES for side in ('closed_min', 'open_min')]
    assert numbers(block(page, 'timing-overview')) == overview
    failures = [f"{pairs[key, 60]['tools']['robustness_search']['best']['peak_C']:.1f}"
                for key in timing.SITES]
    failures += [f"{pairs['soultz', 60]['tools']['limit']:.0f}",
                 f"{pairs['united-downs', 0]['tools']['drilling']['T']:.1f}"]
    assert numbers(block(page, 'timing-failures')) == failures
    for key in timing.SITES:
        base, delayed = pairs[key, 0], pairs[key, 60]
        assert numbers(block(page, f'target-{key}')) == [f"{base['z_m']:.3f}"]
        headers, rows = table(block(page, f'paired-{key}'))
        assert all('SG-equivalent' in headers[i] for i in (2, 3))
        assert all('kg/m³ at 20 °C' in headers[i] for i in (4, 5))
        expected_rows = []
        for c, d in zip(base['cycle']['cases'], delayed['cycle']['cases']):
            expected_rows.append([c['label'], f"{c['UCS'] / 1e6:.0f}",
                f"{c['drill_SG']:.6f}", f"{d['drill_SG']:.6f}",
                f"{c['drill_rho_surface']:.3f}", f"{d['drill_rho_surface']:.3f}",
                f"{c['states']['drilling']} → {d['states']['drilling']}",
                f"{c['verdict']} → {d['verdict']}"])
        assert rows == expected_rows
        headers, rows = table(block(page, f'windows-{key}'))
        assert all('surface SG at 20 °C' in headers[i] for i in (2, 4))
        expected_rows = []
        for m in (0, 60):
            for name in ('drilling_fluid', 'trip_fluid'):
                w = pairs[key, m]['windows'][name]
                bound = lambda b: f"{b['state']}; {b['case']}; {b['md']:.2f}"
                expected_rows.append([str(m // 60), name, f"{w['lo'] / 1000:.6f}",
                                      bound(w['lo_by']), f"{w['hi'] / 1000:.6f}",
                                      bound(w['hi_by']), str(w['open'])])
        assert rows == expected_rows
    _, rows = table(block(page, 'scan-summary'))
    assert rows == [[NAMES[key], str(scans[key]['critical_delay']['bracket']['closed_min']),
                     str(scans[key]['critical_delay']['bracket']['open_min']),
                     f"{scans[key]['elapsed_seconds']:.1f}"] for key in timing.SITES]
    headers, rows = table(block(page, 'scan-table'))
    assert all('surface SG' in headers[i] for i in (2, 3)) and 'SG-equivalent' in headers[5]
    assert rows == [[NAMES[key], str(t['delay_min']), f"{t['drilling_fluid']['lo'] / 1000:.6f}",
                     f"{t['drilling_fluid']['hi'] / 1000:.6f}", str(t['drilling_fluid']['open']),
                     f"{t['drill_SG']:.6f}"] for key in timing.SITES for t in scans[key]['trials']]
    case_note = page.split('<!-- scan-table:end -->')[1].split('## Reproduce')[0]
    assert numbers(case_note) == [f"{deciding('soultz', 0)['UCS'] / 1e6:.0f}",
                                 re.search(r', (\d+) K', deciding('united-downs', 0)['label'])[1]]
