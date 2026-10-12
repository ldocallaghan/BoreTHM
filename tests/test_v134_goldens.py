"""Reviewed release rows, with fresh solves when the source or runtime changes."""
import hashlib
import json
from pathlib import Path
import tempfile

import pytest

import release_v134 as release
import levers as lv
import site_evaluation as se


def read_pin(name):
    path = release.GOLDEN / name
    if not path.exists():
        pytest.skip('reviewed v1.3.4 golden awaiting CI generation')
    return json.loads(path.read_text())


def test_reviewed_comparison_retains_the_physical_tolerance_and_gate():
    pin = dict(window_SG=1.4, tool_ok=False)
    release.assert_reviewed(dict(window_SG=1.401, tool_ok=False), pin)
    with pytest.raises(AssertionError):
        release.assert_reviewed(dict(window_SG=1.403, tool_ok=False), pin)
    with pytest.raises(AssertionError):
        release.assert_reviewed(dict(window_SG=1.4, tool_ok=True), pin)
    with pytest.raises(AssertionError):
        release.assert_reviewed(dict(settings=dict(allowance_SG=0.021)),
                                dict(settings=dict(allowance_SG=0.02)))


def test_release_evidence_checksums_and_brackets():
    pin = read_pin('v134_lever_tables.json')
    directory = release.ROOT / pin['provenance']['evidence_directory']
    manifest = json.loads((directory / 'manifest.json').read_text())
    for name, digest in manifest['evidence_files_sha256'].items():
        assert hashlib.sha256((release.ROOT / name).read_bytes()).hexdigest() == digest, name
    release.assert_reviewed(release.lever_tables(directory / 'levers'), pin['sites'])
    for rows in pin['sites'].values():
        for label in ('L5', 'L8'):
            for field in ('coating_brackets', 'bit_brackets'):
                if field not in rows[label]:
                    continue
                coarse, fine = rows[label][field]
                assert fine['tolerance'] == coarse['tolerance'] / 2.
                assert coarse['failing']['intervention'] <= fine['failing']['intervention']
                assert fine['passing']['intervention'] <= coarse['passing']['intervention']
                assert fine['passing']['intervention'] - fine['failing']['intervention'] <= fine['tolerance']


@pytest.mark.slow
@pytest.mark.parametrize('key', release.SITES)
def test_corrected_reference_matches_ci_golden(key, evaluated):
    pin = read_pin('v134_site_table.json')
    data = se.result_dict(evaluated(se.find_site(key), circulation='v1.3.4'))
    release.assert_reviewed(release.reference_row(data), pin['sites'][key])


@pytest.mark.slow
def test_lever_tables_match_ci_golden():
    pin = read_pin('v134_lever_tables.json')
    # Exact-source CI evidence is reusable; model/data/runtime changes force
    # full coupled solves and compare their output with the reviewed pin.
    if pin['provenance']['source_sha256'] == lv.fingerprint():
        directory = release.ROOT / pin['provenance']['evidence_directory'] / 'levers'
        actual = release.lever_tables(directory)
    else:
        temporary = release.ROOT / '.ci-v134'
        temporary.mkdir(exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix='live-', dir=temporary))
        actual = release.generate_levers(directory)
    release.assert_reviewed(actual, pin['sites'])
