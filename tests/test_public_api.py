"""The documented package interface works without importing internal helpers."""
import inspect
from pathlib import Path
import re
import subprocess
import sys
import tomllib

import numpy as np
import pytest

import borethm as bt

ROOT = Path(__file__).resolve().parents[1]


def test_public_names_are_documented():
    page = (ROOT / 'docs/api.md').read_text(encoding='utf-8')
    assert len(bt.__all__) == len(set(bt.__all__))
    for name in bt.__all__:
        assert '\n## ' + name + '\n' in page
        assert getattr(bt, name) is not None
        if name != '__version__':
            assert inspect.getdoc(getattr(bt, name))


def test_package_and_citation_versions_match():
    metadata = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    citation = (ROOT / 'CITATION.cff').read_text(encoding='utf-8')
    assert bt.__version__ == metadata['project']['version']
    assert re.search(r'^version: "' + re.escape(bt.__version__) + '"$', citation, re.M)
    notice = (ROOT / 'NOTICE').read_text(encoding='utf-8').split('If you use BoreTHM in research', 1)[1]
    doi = re.search(r'^doi: "([^"]+)"$', citation, re.M)[1]
    assert doi in notice
    assert not re.search(r'\bversion\s+\d', notice, re.I)


def test_api_page_matches_its_generator():
    sys.path.insert(0, str(ROOT / 'tools'))
    from build_api_docs import render
    assert render() == (ROOT / 'docs/api.md').read_text(encoding='utf-8')


def test_geometry_and_thermal_inputs_can_be_built_from_public_names():
    pipe = bt.PipeType('steel', (bt.Layer(0.05, 0.06, 45.0),))
    survey = bt.Survey([0., 100.], [0., 100.])
    well = bt.WellGeometry([bt.StringSegment(100., pipe)],
                          [bt.open_hole(0., 100., 0.22)], survey)
    assert well.md_bit == 100.
    assert bt.cased(0., 100., 0.22, 0.24, 0.30).r_rock == 0.15
    assert bt.uniform_wall(45.0).r_bore == 0.05
    state = bt.WallState('fixed', 10., T_wall=200.)
    wall = bt.wall_temperatures([state], 200., 0.11, 2.6, 2.7e6, n=20)
    np.testing.assert_allclose(wall.T_wall, 200.)
    lump = bt.ToolLump.of_pipe(0.05, 0.06, 4.2e6)
    history, depths = bt.tool_trip_in(lump, lambda md: 20., 100., 1., 20., 5., 5.)
    assert depths[-1] == 100.
    np.testing.assert_allclose(history.T_f, 20.)


def test_circulation_wrapper_preserves_arguments_and_only_changes_verbosity(monkeypatch):
    from borethm import model1_coupled as model
    original = inspect.signature(model.solve)
    seen = []
    monkeypatch.setattr(model, 'solve', lambda **kwargs: seen.append(kwargs) or kwargs)
    wrapper = inspect.signature(bt.circulating_temperatures)
    assert tuple(wrapper.parameters) == tuple(original.parameters)
    for name, parameter in wrapper.parameters.items():
        expected = original.parameters[name]
        assert parameter.kind == expected.kind
        assert parameter.default == (False if name == 'verbose' else expected.default)
    result = bt.circulating_temperatures(3., 30., pipe='pipe')
    assert result['m_dot'] == 3. and result['T_inj'] == 30.
    assert result['pipe'] == 'pipe' and result['verbose'] is False
    assert bt.circulating_temperatures(verbose=True)['verbose'] is True
    args = [p.default for p in wrapper.parameters.values()]
    args[list(wrapper.parameters).index('verbose')] = True
    assert bt.circulating_temperatures(*args)['verbose'] is True


@pytest.mark.parametrize('module, option', [
    ('site_evaluation', '--site'),
    ('studies.robustness', '--sites'),
    ('studies.checkpoint_v134', '--sites'),
])
def test_unknown_site_is_a_library_error_and_a_one_line_command_error(module, option, tmp_path):
    with pytest.raises(ValueError, match='choose one of'):
        bt.find_site('unknown-test-site')
    arguments = [sys.executable, '-m', 'borethm.' + module, option, 'unknown-test-site']
    if module.startswith('studies.'):
        arguments += ['--output', str(tmp_path)]
    command = subprocess.run(arguments, capture_output=True, text=True)
    assert command.returncode == 1
    assert command.stderr.startswith("--site 'unknown-test-site': choose one of ")
    assert 'Traceback' not in command.stderr


@pytest.mark.parametrize('module', ['site_evaluation', 'comparative_sites', 'water_table'])
def test_module_help_exits_before_computing(module):
    command = subprocess.run([sys.executable, '-m', 'borethm.' + module, '--help'],
                             capture_output=True, text=True, timeout=30)
    assert command.returncode == 0
    assert 'usage:' in command.stdout
    assert command.stderr == ''
