"""Create, validate and export a user's site without physical solves."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from borethm import site_evaluation as se
from borethm import site_files as sf
from borethm.studies import lever_flow_limit as flow


@pytest.mark.parametrize('key', ['soultz', 'larderello', 'united-downs', 'pannonian', 'newberry'])
def test_create_and_check_starting_site(tmp_path, key, monkeypatch, capsys):
    path = tmp_path / 'my site.toml'
    sf.main(['--from', key, str(path)])
    creation = capsys.readouterr().out
    assert '--check' in creation and '--json' in creation
    assert path.read_text(encoding='utf-8') == sf.site_text(key)
    cache = tmp_path / 'empty-cache'
    monkeypatch.setenv('BORETHM_CACHE_DIR', str(cache))
    monkeypatch.setattr(se, 'evaluate', lambda *a, **k: pytest.fail('check reached evaluation'))
    se.main(['--site-file', str(path), '--check'])
    loaded = capsys.readouterr().out
    assert se.find_site(key).tier in loaded
    assert not cache.exists()
    if key != 'soultz':
        se.main(['--site', key, '--check'])
        assert capsys.readouterr().out == loaded
    else:
        assert 'warning:' not in loaded


def test_writer_refuses_overwrite_and_force_replaces(tmp_path):
    path = tmp_path / 'site.toml'
    path.write_text('my data', encoding='utf-8')
    with pytest.raises(SystemExit, match='file exists; use --force'):
        sf.main([str(path)])
    assert path.read_text() == 'my data'
    sf.main([str(path), '--force'])
    assert path.read_text() == sf.template_text()


@pytest.mark.parametrize('arguments,message', [
    (['--from', 'unknown', 'out.toml'], '--from'),
    (['absent-directory/out.toml'], 'absent-directory'),
])
def test_writer_errors_are_one_line_exit_one(tmp_path, arguments, message):
    result = subprocess.run([sys.executable, '-m', 'borethm.site_files', *arguments],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 1
    assert message in result.stderr
    assert len(result.stderr.splitlines()) == 1


@pytest.mark.parametrize('arguments', [[], ['--site', 'soultz', '--site-file', 'x.toml']])
def test_evaluator_requires_exactly_one_source(arguments, capsys):
    with pytest.raises(SystemExit) as error:
        se.main(arguments)
    assert error.value.code == 2
    message = capsys.readouterr().err
    assert '--site' in message and '--site-file' in message


@pytest.mark.parametrize('file_name,text,message', [
    ('absent.toml', None, 'file'),
    ('bad.toml', 'name = [', 'TOML'),
    ('site.py', sf.template_text(), 'site files are TOML'),
], ids=['missing', 'invalid-toml', 'python-file'])
def test_unloadable_file_errors(tmp_path, file_name, text, message):
    path = tmp_path / file_name
    if text is not None:
        path.write_text(text, encoding='utf-8')
    with pytest.raises(SystemExit) as error:
        se.main(['--site-file', str(path), '--check'])
    assert message in str(error.value)
    assert len(str(error.value).splitlines()) == 1
    if file_name.endswith('.py'):
        assert 'docs/guides/new-site.md' in str(error.value)


def test_invalid_physical_inputs_use_parser_error(tmp_path, capsys):
    path = tmp_path / 'site.toml'
    path.write_text(sf.template_text().replace('target_depth = 10700.0', 'target_depth = 10.7'))
    with pytest.raises(SystemExit) as error:
        se.main(['--site-file', str(path), '--check'])
    assert error.value.code == 2
    assert 'target_depth' in capsys.readouterr().err


@pytest.mark.parametrize('initial,argument,mode,expected', [
    (False, None, 'v1.3.4', True), (False, None, 'v1.3.3', True),
    (False, None, 'v1.3', False), (True, None, 'v1.3', True),
    (True, None, 'v1.3.4', True), (False, True, 'v1.3', True),
    (True, True, 'v1.3', True), (False, False, 'v1.3.4', False),
    (True, False, 'v1.3.4', False), (True, False, 'v1.3', False),
])
def test_coupling_override_reaches_downstream_without_mutating_input(monkeypatch, initial, argument, mode, expected):
    site = replace(se.SOULTZ, coupled=initial)
    seen = []
    def capture(profile, *args, **kwargs):
        seen.append(profile.coupled)
        return {}
    monkeypatch.setattr(se, '_evaluate_v13', capture)
    se.evaluate(site, circulation=mode, coupled=argument)
    assert seen == [expected]
    assert site.coupled is initial


def test_provenance_is_optional_and_preserves_path(tmp_path, monkeypatch):
    monkeypatch.setattr(se, 'versions', lambda: {'test': 'fixed'})
    path = tmp_path / 'site.toml'
    path.write_text(sf.template_text(), encoding='utf-8')
    result = dict(site=se.SOULTZ, z=10700., T_rock=400.)
    baseline = se.result_dict(result)
    assert 'site_file' not in baseline
    data = se.result_dict(result, site_file=path)
    assert data.pop('site_file') == dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    assert data == baseline
    output = tmp_path / 'out.json'
    se.export_result(result, output, site_file=path)
    assert json.loads(output.read_text()) == se.result_dict(result, site_file=path)


def test_cli_captures_file_identity_before_evaluation(tmp_path, monkeypatch):
    path = tmp_path / 'site.toml'
    path.write_text(sf.template_text(), encoding='utf-8')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    def evaluate(site, **kwargs):
        path.write_text('# edited during evaluation', encoding='utf-8')
        return dict(site=site, z=site.target(), T_rock=400.)
    monkeypatch.setattr(se, 'evaluate', evaluate)
    monkeypatch.setattr(se, 'report', lambda result: None)
    output = tmp_path / 'result.json'
    se.main(['--site-file', str(path), '--json', str(output)])
    assert json.loads(output.read_text())['site_file'] == dict(path=str(path), sha256=digest)


@pytest.mark.parametrize('arguments,expected', [([], flow.lv.RESULTS), (['--output', 'elsewhere'], Path('elsewhere'))])
def test_flow_limit_output_is_passed_to_main(monkeypatch, arguments, expected):
    seen = []
    monkeypatch.setattr(flow, 'main', lambda root: seen.append(root))
    flow.cli(arguments)
    assert seen == [expected]
