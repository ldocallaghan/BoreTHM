"""Frozen FORGE 16A comparison statistics, without rerunning S1.

Expected numbers come from the original S1 report. This tests archival data
and summary arithmetic, not the accuracy of a changed physical calculation.
"""
import hashlib
import json
from pathlib import Path

import pytest
from borethm.studies import forge16a_evidence as evidence


@pytest.fixture(scope='module')
def summary():
    return evidence.primary_summary()


@pytest.fixture(scope='module')
def pinned():
    return json.loads((Path(__file__).parent/'golden/validate_forge16a.json').read_text())


@pytest.mark.parametrize('section',('q1','q2'))
def test_archived_comparison_statistics(summary,pinned,section):
    assert summary[section].keys()==pinned[section].keys()
    for key,expected in pinned[section].items():
        assert summary[section][key]['n']==expected['n'],key
        for field,value in expected.items():
            if field!='n':assert summary[section][key][field]==pytest.approx(value,abs=1e-9,rel=0), (key,field)


def test_archive_identity_and_complete_primary_coverage():
    manifest=json.loads((evidence.DATA/'evidence-manifest.json').read_text())
    assert manifest['baseline_commit']=='b9a8a93f49f1b53b7bd71a713b8ca4988e7c21c6'
    for name,expected in manifest['archived_output_sha256'].items():
        assert hashlib.sha256((evidence.DATA/name).read_bytes()).hexdigest()==expected,name
    rows=evidence.primary_records()
    assert len(rows)==358
    assert len({r['sample_id'] for r in rows})==358
    sanvean=[r for r in rows if r['source']=='Sanvean on-bottom']
    assert len(sanvean)==135
    assert sum(bool(r['measured_top_sub_C']) for r in sanvean)==118


def test_external_archive_and_missing_installed_archive(monkeypatch):
    archive=evidence.DATA
    monkeypatch.setattr(evidence,"DATA",None)
    with pytest.raises(RuntimeError,match="explicit path"):
        evidence.primary_records()
    assert evidence.primary_summary(archive)["q1"]["ALL|bit_box_C|bore_bit_C"]["n"]==135


def test_explicit_archive_preparation_does_not_require_git(tmp_path,monkeypatch):
    from borethm.studies import validate_forge16a as study
    monkeypatch.setattr(study,'repository_root',lambda:None)
    monkeypatch.setattr(study.subprocess,'check_output',lambda *a,**kw:pytest.fail('Git called outside checkout'))
    study.prepare(tmp_path)
    plan=json.loads((tmp_path/'plan.json').read_text())
    assert plan['baseline'] is None
    assert plan['describe'].startswith('installed borethm ')
    assert len(plan['samples'])==358
    assert not (tmp_path/'results.jsonl').exists()
