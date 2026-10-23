"""Dataset values remain tied to retained inputs and evidence, without solves."""
import ast
import csv
from dataclasses import asdict
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import shutil
import sys
import zipfile

import pytest

from borethm import site_evaluation as se

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / 'benchmarks'
sys.path.insert(0, str(ROOT / 'tools'))
import build_benchmarks as builder
from site_record_helpers import INPUT_ROUNDOFF_RTOL, assert_record_values


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def plain(value):
    return json.loads(json.dumps(value))


def test_manifest_covers_every_file_and_copied_sources_match():
    manifest = read(DATASET / 'manifest.json')
    assert manifest['dataset_version'] == '1.0'
    actual = {p.relative_to(DATASET).as_posix() for p in DATASET.rglob('*') if p.is_file()}
    assert actual == set(manifest['files']) | {'manifest.json'}
    for name, digest in manifest['files'].items():
        assert hashlib.sha256((DATASET / name).read_bytes()).hexdigest() == digest, name
    origins = read(DATASET / 'sources.json')['files']
    assert set(origins) == actual - {'manifest.json', 'sources.json'}
    for name, origin in origins.items():
        if origin['kind'] == 'copy':
            source = (ROOT / origin['path']).read_bytes()
            assert (DATASET / name).read_bytes() == source, name
            assert hashlib.sha256(source).hexdigest() == origin['sha256'], name


@pytest.mark.parametrize('case', builder.CASES)
def test_expected_values_are_exact_copies_of_existing_goldens(case):
    golden = builder.CASES[case][0]
    assert read(DATASET / case / 'expected.json') == read(ROOT / 'tests/golden' / golden)


@pytest.mark.parametrize('key', ['soultz', 'united-downs', 'larderello', 'pannonian', 'newberry'])
def test_all_profile_fields_and_geotherm_samples_match_their_sources(key):
    original = asdict(se.named_sites()[key])
    exported = read(DATASET / 'sites' / (key + '.json'))
    saved = read(ROOT / 'results/v1.3.4/checkpoint-1' / (key + '.json'))
    assert len(exported['stress_cases']) == len(saved['site']['stress_cases'])
    for actual, retained in zip(exported['stress_cases'], saved['site']['stress_cases']):
        for name in ('Sv', 'Shmin', 'SHmax'):
            assert_record_values([actual[name + '_grad'], actual[name + '_int']], retained[name])
        assert_record_values([actual['Pp_grad'], actual['Pp_datum']], retained['Pp'])
    functions = {name: value for name, value in original.items() if callable(value)}
    for name, function in functions.items():
        record = exported.pop(name)
        assert record['callable']['module'] == function.__module__
        assert record['callable']['name'] == function.__qualname__
        assert (ROOT / record['callable']['path']).is_file()
        original.pop(name)
    assert_record_values(exported, plain(original), rtol=INPUT_ROUNDOFF_RTOL)
    with (DATASET / 'sites' / (key + '-geotherms.csv')).open(newline='') as handle:
        samples = list(csv.DictReader(handle))
    assert [float(row['depth_m']) for row in samples] == saved['windows']['depths']
    for row in samples:
        for name, function in functions.items():
            assert_record_values(float(row[name + '_C']), float(function(float(row['depth_m']))),
                                 rtol=INPUT_ROUNDOFF_RTOL, path=key + '.' + name)


@pytest.mark.parametrize('case', builder.ATTRIBUTES)
def test_exported_parameters_match_the_named_source_attributes(case):
    inputs = read(DATASET / case / 'inputs.json')
    for module_name, attributes in inputs['attributes'].items():
        module = importlib.import_module(module_name)
        assert attributes == plain({name: getattr(module, name) for name in attributes})
    if case == 'ut-austin':
        module = importlib.import_module('borethm.studies.benchmark_utaustin')
        for field, source in [('pipes', module.PIPES), ('whole_wall_pipes', module.WHOLE_WALL)]:
            assert inputs[field] == plain({name: asdict(pipe) for name, pipe in source.items()})
        for name, value in inputs['run_defaults'].items():
            if name != 'source':
                assert value == inspect.signature(module.run).parameters[name].default


def test_programme_settings_and_scan_grid_match_retained_cases():
    inputs = read(DATASET / 'breakout-timing-v136/inputs.json')
    golden = read(ROOT / 'tests/golden/v136_breakout_timing.json')
    for key, pairs in golden['pairs'].items():
        assert inputs['paired_settings'][key] == {delay: row['settings'] for delay, row in pairs.items()}
        assert inputs['scan_minutes'][key] == golden['scans'][key]['scan_minutes']
    for name, digest in golden['provenance']['evidence_sha256'].items():
        assert hashlib.sha256((DATASET / 'breakout-timing-v136/evidence' / name).read_bytes()).hexdigest() == digest
    for key in se.named_sites():
        assert read(DATASET / 'site-reference-v134/evidence' / (key + '.json')) == read(
            ROOT / 'results/v1.3.4/checkpoint-1' / (key + '.json'))


@pytest.mark.parametrize('case', builder.CASES)
def test_numerical_tolerances_already_exist_in_the_cited_regression(case):
    policy = read(DATASET / case / 'tolerances.json')
    path, _, function = policy['source'].partition('::')
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    if function:
        tree = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
    constants = {n.value for n in ast.walk(tree)
                 if isinstance(n, ast.Constant) and type(n.value) in (float, int)}
    for rule in policy['rules']:
        for key in ('absolute', 'relative'):
            if key in rule:
                assert rule[key] in constants, (case, rule)


def test_rebuild_is_exact_and_calls_no_model_or_calibration(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('dataset construction called a model or calibration')
    targets = {
        'borethm.site_evaluation': ['evaluate', 'circulate', 'common_windows'],
        'borethm.model1_coupled': ['solve', 'solve_seeded', 'hydraulics'],
        'borethm.wall_thermal': ['run', 'cooling_shape'],
        'borethm.tool_thermal': ['run', 'trip_in'],
        'borethm.calibrate_ud1': ['calibrate', 'calibrate_skin'],
        'borethm.studies.benchmark_utaustin': ['run', 'golden_rows'],
        'borethm.studies.validate_forge16b': ['run_all', 'fit_film', 'fit_idp'],
        'borethm.studies.validate_forge_pauses': ['check'],
        'borethm.studies.crosscheck_soultz': ['crosscheck', 'width', 'onset'],
    }
    for module_name, names in targets.items():
        module = importlib.import_module(module_name)
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    output, archive = tmp_path / 'dataset', tmp_path / 'borethm-benchmarks-1.0.zip'
    generated = builder.assemble(output, archive)
    retained = {p.relative_to(DATASET).as_posix(): p.read_bytes() for p in DATASET.rglob('*') if p.is_file()}
    assert generated == retained
    first = archive.read_bytes()
    assert builder.assemble(output, archive) == retained
    assert archive.read_bytes() == first
    with zipfile.ZipFile(archive) as bundle:
        assert {name.removeprefix('borethm-benchmarks-1.0/') for name in bundle.namelist()} == set(retained)
        for name, content in retained.items():
            assert bundle.read('borethm-benchmarks-1.0/' + name) == content


def test_zip_must_stay_outside_the_repository(tmp_path):
    with pytest.raises(ValueError, match='outside the repository'):
        builder.assemble(tmp_path / 'dataset', ROOT / 'upload.zip')


@pytest.mark.parametrize('change', ['file', 'manifest', 'extra'])
def test_published_snapshot_packaging_rejects_modified_archive_inputs(tmp_path, change):
    dataset = tmp_path / 'benchmarks'
    shutil.copytree(DATASET, dataset)
    if change == 'file':
        path = dataset / 'sites/soultz.json'
        path.write_bytes(path.read_bytes() + b'\n')
    elif change == 'manifest':
        path = dataset / 'manifest.json'
        path.write_bytes(path.read_bytes() + b'\n')
    else:
        (dataset / 'extra.txt').write_text('unexpected')
    with pytest.raises(ValueError, match='checksum|file list'):
        builder.build_files(tmp_path)
