"""Offline checks of reader tables against retained v1.3.4 evidence.

No model imports or coupled solves. Run: python tools/verify_v135_docs.py
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'results/v1.3.4/ci/38186784798-1'
SITES = {'soultz': 'Soultz', 'united-downs': 'United Downs'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def source(key):
    return read(EVIDENCE / f'reference/{key}.json')


def label(key, case):
    # Strength is in its own table column; preserve the complete stress case.
    text = case['label']
    if key == 'soultz':
        suffix = f", lab UCS {case['UCS'] / 1e6:.0f}"
        assert text.endswith(suffix)
        text = text.removesuffix(suffix)
    else:
        prefix = 'Reinecker et al. (2021), '
        assert text.startswith(prefix)
        text = text.removeprefix(prefix)
    return f'{SITES[key]}: {text}'


def case_table():
    rows = ['| Case | UCS, MPa | Drilling need / limit, SG-equivalent | Target stability-cycle verdict |',
            '|---|---:|---|---|']
    for key in SITES:
        for case in source(key)['cycle']['cases']:
            rows.append(f"| {label(key, case)} | {case['UCS'] / 1e6:.0f} | "
                        f"{case['drill_SG']:.3f} / {case['drill_SG_hi']:.3f} | {case['verdict']} |")
    return '\n'.join(rows)


def window_table():
    rows = ['| Site and state | Lower / upper, surface SG | Width, SG |',
            '|---|---|---:|']
    for key, name in SITES.items():
        for field, state in [('drilling_fluid', 'drilling'), ('trip_fluid', 'trip')]:
            w = source(key)['windows'][field]
            rows.append(f"| {name} {state} | {w['lo'] / 1000:.5f} / {w['hi'] / 1000:.5f} | "
                        f"{(w['hi'] - w['lo']) / 1000:+.5f} |")
    return '\n'.join(rows)


def base_trial(key):
    expected = dict(pipe='TK-Drakon coated', shoe_m=4000.0,
                    flow_L_s=40 if key == 'soultz' else 50, pv_fraction=1.0,
                    allowance_SG=0.02, form_h=0.0, bhp_Pa=None, coating_rating_C=204.0)
    matches = [t for t in read(EVIDENCE / f'levers/{key}/L4/summary.json')['trials']
               if t['settings'] == expected]
    assert len(matches) == 1, (key, len(matches))
    trial = matches[0]
    peaks = trial['metrics']['tool_peaks_C']
    attempts = trial['metrics']['run_in_search']['attempts']
    assert peaks['run_in'] == min(t['peak_C'] for t in attempts)
    return trial


def tool_sentence():
    groups = []
    for key, name in SITES.items():
        peaks = base_trial(key)['metrics']['tool_peaks_C']
        groups.append(f"{name}: {peaks['drilling']:.1f} / {peaks['connection']:.1f} / {peaks['run_in']:.1f} °C")
    return '; '.join(groups) + '.'


def coating_sentence():
    coatings = [source(k)['tools']['coating'] for k in SITES]
    assert all(c['rating'] == 204.0 and c['status'] == 'INDETERMINATE' for c in coatings)
    return (f"Reference-practice coating run-in maxima are {coatings[0]['trip_in']['max']:.1f} °C "
            f"at Soultz and {coatings[1]['trip_in']['max']:.1f} °C at United Downs, against the stated 204 °C rating.")


def summary_rows():
    """Compact briefing rows, independently derived from retained evidence."""
    rows = []
    for key, name in SITES.items():
        data = source(key)
        cases = data['cycle']['cases']
        opened = sum(c['drill_SG'] <= c['drill_SG_hi'] + 1e-9 for c in cases)
        for field in ('drilling_fluid', 'trip_fluid'):
            bounds = data['windows'][field]
            assert bounds['lo'] > bounds['hi'] and not bounds['open']
        peaks = base_trial(key)['metrics']['tool_peaks_C']
        assert data['tools']['limit'] == 200.0
        rows.append(f"| {name}, {data['site']['target_depth_m'] / 1000:.2f} km | "
                    f"{opened} of {len(cases)} cases | No allowable drilling or trip-fluid density | "
                    f"{peaks['drilling']:.1f} / {peaks['run_in']:.1f} °C |")
    return rows


def verify():
    hashes = read(EVIDENCE / 'manifest.json')['evidence_files_sha256']
    assert len(hashes) == 112
    for path, expected in hashes.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    counts = {}
    for key, expected in [('soultz', (9, 8)), ('united-downs', (4, 2))]:
        cases = source(key)['cycle']['cases']
        # Matches site_evaluation.py's saved diagnostic comparison tolerance.
        opened = sum(c['drill_SG'] <= c['drill_SG_hi'] + 1e-9 for c in cases)
        assert (len(cases), opened) == expected
        assert source(key)['status']['label'] == 'NO-GO'
        counts[key] = opened
    assert round(source('soultz')['site']['target_depth_m'] / 1000, 2) == 10.70
    assert round(source('united-downs')['site']['target_depth_m'] / 1000, 2) == 12.86
    assert f"{base_trial('soultz')['metrics']['practice_run_in_peak_C']:.1f}" == '214.5'
    case_deficit = max(c['drill_SG'] - c['drill_SG_hi'] for c in source('soultz')['cycle']['cases'])
    assert f'{case_deficit:.3f}' == '0.017'
    excess = base_trial('soultz')['metrics']['tool_peaks_C']['run_in'] - source('soultz')['tools']['limit']
    assert f'{excess:.1f}' == '1.2'
    l2 = read(EVIDENCE / 'levers/soultz/L2/summary.json')
    shoe_trials = [t for t in l2['trials'] if t['settings']['shoe_m'] == 10200.0]
    assert len(shoe_trials) == 1
    assert f"{shoe_trials[0]['metrics']['pressure_margin_SG']['trip_fluid']:.5f}" == '0.00137'
    pair = read(EVIDENCE / 'levers/soultz/PAIR-L2-L4/summary.json')
    assert pair['pair'] == ['L2', 'L4']
    assert f"{-pair['trial']['metrics']['pressure_margin_SG']['drilling_fluid']:.5f}" == '0.00949'
    expected_status = {'soultz': 'NO-GO', 'united-downs': 'NO-GO', 'pannonian': 'NO-GO',
                       'larderello': 'CONDITIONAL', 'newberry': 'GO'}
    assert {k: source(k)['status']['label'] for k in expected_status} == expected_status
    assert all('flow_ceiling' not in source(k) and 'shmin_margin' not in source(k)
               for k in expected_status), 'Update the output guide if retained fields change'
    for report, archive, boundary in [
            ('science/approximation-comparisons.md', 'archive/v1.3.4/approximation-review.md',
             '## Evidence and verification'),
            ('science/design-comparisons.md', 'archive/v1.3.4/design-review.md',
             '## Reproduction and review')]:
        original = (ROOT / 'docs' / archive).read_text(encoding='utf-8').split(boundary)[0]
        current = (ROOT / 'docs' / report).read_text(encoding='utf-8')
        # Published study data rows remain identical to the historical review.
        # Headers can change (e.g. removing an internal requirement identifier).
        rows = [line for line in original.splitlines() if line.startswith('|')
                and re.match(r'^\| (?:Soultz|United Downs|Pannonian|A\d|L\d|PAIR|[0-9]|first|half|radial|timesteps|window|all three)', line)]
        without_links = lambda text: re.sub(r'\[([^\]]*)\]\([^)]+\)', r'\1', text)
        assert rows and all(without_links(line) in without_links(current) for line in rows), report
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    for key, name in [('soultz', 'Soultz-sous-Forêts'), ('united-downs', 'United Downs'),
                      ('larderello', 'Larderello'), ('pannonian', 'Pannonian Basin'), ('newberry', 'Newberry')]:
        data = source(key)
        prefix = f"| {name} | {data['site']['target_depth_m'] / 1000:.2f} | {data['status']['label']} |"
        assert prefix in readme, (key, 'headline table')
    for table in [case_table(), window_table(), tool_sentence(), coating_sentence()]:
        assert table in readme, 'README.md: missing or mismatched evidence panel'
    summary = (ROOT / 'docs/guides/summary.md').read_text(encoding='utf-8')
    for row in summary_rows():
        assert row in summary, 'Summary: missing or mismatched evidence row'
    assert coating_sentence() in summary
    assert "Soultz's reference FORGE-practice tool run-in reaches 214.5 °C" in summary
    docs = ['README.md', 'CHANGELOG.md', *(p.relative_to(ROOT).as_posix()
                                         for p in (ROOT / 'docs').rglob('*.md'))]
    for doc in docs:
        text = (ROOT / doc).read_text(encoding='utf-8')
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
            if '://' not in link:
                path, _, anchor = link.partition('#')
                target = ((ROOT / doc).parent / path) if path else ROOT / doc
                assert target.exists(), (doc, link)
                if anchor and target.suffix == '.md':
                    headings = [line.lstrip('# ').strip().lower() for line in
                                target.read_text(encoding='utf-8').splitlines() if line.startswith('#')]
                    slugs = {re.sub(r'[^\w -]', '', heading).replace(' ', '-') for heading in headings}
                    assert anchor in slugs, (doc, link, 'missing heading')
    metadata = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    assert metadata['project']['version'] == '1.3.5'
    assert 'version: "1.3.5"' in (ROOT / 'CITATION.cff').read_text(encoding='utf-8')
    licence = (ROOT / 'LICENSE').read_text(encoding='utf-8')
    assert licence.lstrip().startswith('Apache License') and 'Version 2.0, January 2004' in licence
    assert 'Attribution 4.0 International' in (ROOT / 'LICENSE-docs').read_text(encoding='utf-8')
    assert "Copyright 2026 Liam O'Callaghan" in (ROOT / 'NOTICE').read_text(encoding='utf-8')
    assert metadata['project']['license'] == 'Apache-2.0'
    assert metadata['project']['urls']['Repository'].endswith('/BoreTHM')
    citation = (ROOT / 'CITATION.cff').read_text(encoding='utf-8')
    assert 'license: Apache-2.0' in citation
    assert 'repository-code: "https://github.com/ldocallaghan/BoreTHM"' in citation
    old_name = 'geothermal-thermo-' + 'hydraulic-model'
    files = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
                           cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    for name in files:
        if name.startswith('docs/archive/') or not (ROOT / name).is_file():
            continue
        assert old_name.encode() not in (ROOT / name).read_bytes(), (name, 'old repository name')
    print('13 README case rows, compact summary rows, counts 8/9 and 2/4, 4 signed density bounds,')
    print('coating status, 5 site statuses, 112 evidence checksums, reader links, version and')
    print('licence metadata verified.')


if __name__ == '__main__':
    verify()
