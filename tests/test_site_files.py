"""Site-file schema, exact reference inputs and errors before evaluation."""
from dataclasses import fields
from importlib.resources import as_file, files
import json
import tomllib

import numpy as np
import pytest

import borethm
from borethm import SiteProfile, StressProfile, layered_geotherm, load_site, validate_site
from borethm import comparative_sites as cs
from borethm import site_evaluation as se
from borethm import site_files as sf
from site_helpers import assert_sites_equal


MINIMAL = '''name = "Test site"
target_depth = 10700.0
target_T = 400.0
Sv_grad = 25996.5
K0_min = 0.54
SHmax_over_Sv = 1.0
rho_fluid_grad = 10000.0
k_rock = 2.9
E_rock = 55e9
UCS = 170e6
'''
SEGMENTS = '''[geotherm]
form = "segments"
boundary = "above"
segments = [[0.0, 12.0, 0.090], [1400.0, 138.0, 0.0172], [5000.0, 200.0, 0.035]]
'''


def write_site(tmp_path, text=MINIMAL + SEGMENTS):
    path = tmp_path / 'site.toml'
    path.write_text(text, encoding='utf-8')
    return path


def test_template_resource_and_sources():
    resource = files('borethm').joinpath('templates/site_template.toml')
    assert sf.template_text() == resource.read_text(encoding='utf-8')
    with as_file(resource) as path:
        site = load_site(path)
    assert_sites_equal(site, se.SOULTZ, allow_extra_basis=True)
    assert validate_site(site) == []
    for key in ('conductivity', 'stiffness'):
        basis, source = site.data_basis[key]
        assert basis == 'assumed'
        assert source
    assert se.SOULTZ.data_basis.keys() == site.data_basis.keys() - {'conductivity', 'stiffness'}


def test_optional_fields_keep_dataclass_defaults(tmp_path):
    site = load_site(str(write_site(tmp_path)))
    expected = SiteProfile(name='Test site', geotherm=se.urg_geotherm,
                           target_depth=10700.0, target_T=400.0, Sv_grad=25996.5,
                           K0_min=0.54, SHmax_over_Sv=1.0, rho_fluid_grad=10000.0,
                           k_rock=2.9, E_rock=55e9, UCS=170e6)
    assert_sites_equal(site, expected)


@pytest.mark.parametrize('segments,boundary,reference', [
    ([(0, 12, .09), (1400, 138, .0172), (5000, 200, .035)], 'above', se.urg_geotherm),
    ([(0, 15, .152), (2200, 350, .077)], None, cs.LARDERELLO.geotherm),
    ([(0, 15, .152), (2200, 350, .2504), (2815, 504, .1)], None, cs.LARDERELLO.geotherm_v11),
    ([(0, 15, .035), (5000, 190, .028)], None, cs.CORNWALL.geotherm),
    ([(0, 15, .033), (5000, 180, .028)], None, cs.CORNWALL.geotherm_v11),
    ([(0, 15, .04625), (4000, 200, .035)], None, cs.PANNONIAN.geotherm),
])
def test_segment_profiles_equal_reference_at_boundaries(tmp_path, segments, boundary, reference):
    table = '[geotherm]\nform = "segments"\nsegments = ' + json.dumps(segments) + '\n'
    if boundary is not None:
        table += f'boundary = "{boundary}"\n'
    geotherm = load_site(write_site(tmp_path, MINIMAL + table)).geotherm
    boundaries = np.array([row[0] for row in segments[1:]], dtype=float)
    depths = np.unique(np.concatenate((np.arange(0., 20001., 10.), boundaries,
                                      np.nextafter(boundaries, -np.inf),
                                      np.nextafter(boundaries, np.inf))))
    np.testing.assert_array_equal(geotherm(depths), reference(depths))
    for depth in depths:
        assert float(geotherm(depth)) == float(reference(depth))


def test_single_segment_applies_from_surface(tmp_path):
    site = load_site(write_site(tmp_path, MINIMAL + '''[geotherm]
form = "segments"
segments = [[100.0, 20.0, 0.04]]
'''))
    np.testing.assert_array_equal(site.geotherm([0., 100., 1000.]), [16., 20., 56.])


def test_boundary_choice_retains_temperature_steps(tmp_path):
    above = load_site(write_site(tmp_path))
    below = load_site(write_site(tmp_path, (MINIMAL + SEGMENTS).replace('"above"', '"below"')))
    assert float(above.geotherm(5000.0)) == 138.0 + .0172 * 3600.0
    assert float(below.geotherm(5000.0)) == 200.0


def test_optional_historical_replacements(tmp_path):
    text = MINIMAL + 'target_depth_v11 = 2400.0\n' + SEGMENTS + '''[geotherm_v11]
form = "segments"
segments = [[0.0, 15.0, 0.152], [2200.0, 350.0, 0.2504], [2815.0, 504.0, 0.1]]
'''
    site = load_site(write_site(tmp_path, text))
    assert site.target() == 2400.0
    assert site.target(v10=True) == 10700.0
    depths = np.unique(np.append(np.arange(0., 20001., 10.), 2815.))
    np.testing.assert_array_equal(site.temperature()(depths), cs.LARDERELLO.geotherm_v11(depths))
    np.testing.assert_array_equal(site.temperature(v10=True)(depths), se.urg_geotherm(depths))


def test_points_uses_unchanged_public_function(tmp_path):
    assert 'layered_geotherm' in borethm.__all__
    assert layered_geotherm is se.layered_geotherm
    points = [[500., 30.], [0., 10.], [2000., 100.]]
    site = load_site(write_site(tmp_path, MINIMAL + '''[geotherm]
form = "points"
points = [[500.0, 30.0], [0.0, 10.0], [2000.0, 100.0]]
gradient_below = 0.03
'''))
    depths = np.arange(0., 20001., 10.)
    np.testing.assert_array_equal(site.geotherm(depths), layered_geotherm(points, .03)(depths))


@pytest.mark.parametrize('optional,kwargs', [
    ('', {}),
    ('Sv_int = -1300000.0\nPp_grad = 9494.0\nmu = 0.6\nfractions = [0.1, 0.3, 0.9]\n',
     dict(Sv_int=-1300000., Pp_grad=9494., mu=.6, fractions=(.1, .3, .9))),
])
def test_transitional_rule_matches_python_with_independent_mu(tmp_path, optional, kwargs):
    text = MINIMAL + 'mu = 0.55\n' + SEGMENTS + '''[stress_rule]
form = "transitional"
Sv_grad = 25996.5
source = "Test regime source"
''' + optional
    site = load_site(write_site(tmp_path, text))
    assert site.mu == .55
    assert site.stress_cases == se.transitional_bounds(25996.5, 'Test regime source', **kwargs)


def test_stress_case_optional_fields_and_tuples(tmp_path):
    text = MINIMAL + 'coupled = true\nstrength_cases = [["first", 100e6], ["second", 130e6]]\n' + SEGMENTS + '''[[stress_cases]]
label = "Test case"
Sv_grad = 26000
Shmin_grad = 14000
SHmax_grad = 25000
Sv_int = -1300000
Shmin_int = -1780000
SHmax_int = -1170000
Pp_grad = 9494
Pp_datum = 61
source = "Test source"
z_data = [1500, 5000]
mu = 0.6
regime = "normal"
[data_basis]
stress = ["measured", "Test source"]
'''
    site = load_site(write_site(tmp_path, text))
    assert site.coupled is True
    assert site.strength_cases == (('first', 100e6), ('second', 130e6))
    assert site.data_basis == {'stress': ('measured', 'Test source')}
    assert site.stress_cases == (StressProfile(
        label='Test case', Sv_grad=26000, Shmin_grad=14000, SHmax_grad=25000,
        Sv_int=-1300000, Shmin_int=-1780000, SHmax_int=-1170000, Pp_grad=9494,
        Pp_datum=61, source='Test source', z_data=(1500, 5000), mu=.6, regime='normal'),)


def test_stress_case_defaults(tmp_path):
    text = MINIMAL + SEGMENTS + '''[[stress_cases]]
label = "Test case"
Sv_grad = 26000
Shmin_grad = 14000
SHmax_grad = 25000
'''
    site = load_site(write_site(tmp_path, text))
    assert site.stress_cases == (StressProfile('Test case', 26000, 14000, 25000),)


def test_load_defers_physical_ranges_and_basis_labels(tmp_path):
    text = (MINIMAL + SEGMENTS).replace('10700.0', '10.7') + '''[data_basis]
stress = ["not a basis label", "Test source"]
'''
    site = load_site(write_site(tmp_path, text))
    assert site.target_depth == 10.7
    with pytest.raises(ValueError, match='target_depth'):
        validate_site(site)
    site.target_depth = 10700.0
    with pytest.raises(ValueError, match='not a basis label'):
        validate_site(site)


@pytest.mark.parametrize('key', [f.name for f in fields(SiteProfile)
                                if f.name in tomllib.loads(MINIMAL)])
def test_every_required_scalar_rejects_wrong_type(tmp_path, key):
    lines = [f'{key} = []' if line.startswith(key + ' =') else line
             for line in MINIMAL.splitlines()]
    path = write_site(tmp_path, '\n'.join(lines) + '\n' + SEGMENTS)
    with pytest.raises(ValueError) as error:
        load_site(path)
    assert key in str(error.value)
    assert str(path) in str(error.value)


@pytest.mark.parametrize('key', list(tomllib.loads(MINIMAL)) + ['geotherm'])
def test_every_required_field_must_be_present(tmp_path, key):
    text = MINIMAL if key == 'geotherm' else '\n'.join(
        line for line in MINIMAL.splitlines() if not line.startswith(key + ' =')) + '\n' + SEGMENTS
    path = write_site(tmp_path, text)
    with pytest.raises(ValueError) as error:
        load_site(path)
    assert str(path) in str(error.value)
    assert f'{key}: missing required key' in str(error.value)


@pytest.mark.parametrize('text,key', [
    ('name = [', 'TOML'),
    (MINIMAL + 'unknown = 1\n' + SEGMENTS, 'unknown'),
    (MINIMAL + SEGMENTS.replace('"segments"', '"expression"'), 'geotherm.form'),
    (MINIMAL + SEGMENTS.replace('form = "segments"\n', ''), 'geotherm.form'),
    (MINIMAL + SEGMENTS.replace('"above"', '"invalid"'), 'geotherm.boundary'),
    (MINIMAL + SEGMENTS.replace('"above"', 'true'), 'geotherm.boundary'),
    (MINIMAL + SEGMENTS + 'unknown = 1\n', 'geotherm.unknown'),
    (MINIMAL + SEGMENTS.replace('[[0.0, 12.0, 0.090], [1400.0, 138.0, 0.0172], [5000.0, 200.0, 0.035]]', '[]'), 'geotherm.segments'),
    (MINIMAL + '[geotherm]\nform = "segments"\nsegments = [[0, 12]]', 'geotherm.segments[0]'),
    (MINIMAL + '[geotherm]\nform = "segments"\nsegments = [[0, 12, "0.04"]]', 'geotherm.segments[0][2]'),
    (MINIMAL + '[geotherm]\nform = "points"\npoints = [[0, 12]]', 'geotherm.gradient_below'),
    (MINIMAL + '[geotherm]\nform = "points"\npoints = [[0, 12]]\ngradient_below = false', 'geotherm.gradient_below'),
    (MINIMAL + 'geotherm = "not a table"', 'geotherm'),
    (MINIMAL + 'target_depth_v11 = "2400"\n' + SEGMENTS, 'target_depth_v11'),
    (MINIMAL + 'coupled = 1\n' + SEGMENTS, 'coupled'),
    (MINIMAL.replace('10700.0', 'true') + SEGMENTS, 'target_depth'),
    (MINIMAL + 'strength_cases = [["test", true]]\n' + SEGMENTS, 'strength_cases[0][1]'),
    (MINIMAL + 'strength_cases = [["test"]]\n' + SEGMENTS, 'strength_cases[0]'),
    (MINIMAL + SEGMENTS + '[data_basis]\nstress = ["measured", 1]', 'data_basis.stress[1]'),
    (MINIMAL + SEGMENTS + '[data_basis]\nstress = "measured"', 'data_basis.stress'),
    (MINIMAL + SEGMENTS + '[stress_rule]\nform = "other"\nSv_grad = 26000\nsource = "test"', 'stress_rule.form'),
    (MINIMAL + SEGMENTS + '[stress_rule]\nform = "transitional"\nSv_grad = 26000', 'stress_rule.source'),
    (MINIMAL + SEGMENTS + '[stress_rule]\nform = "transitional"\nSv_grad = 26000\nsource = "test"\nunknown = 1', 'stress_rule.unknown'),
    (MINIMAL + SEGMENTS + '[stress_rule]\nform = "transitional"\nSv_grad = 26000\nsource = "test"\nfractions = [false]', 'stress_rule.fractions[0]'),
    (MINIMAL + 'stress_cases = []\n' + SEGMENTS + '[stress_rule]\nform = "transitional"\nSv_grad = 26000\nsource = "test"', 'stress_rule'),
    (MINIMAL + 'stress_cases = "case"\n' + SEGMENTS, 'stress_cases'),
    (MINIMAL + SEGMENTS + '[[stress_cases]]\nlabel = "test"\nSv_grad = 26000\nShmin_grad = 14000\nSHmax_grad = 25000\nunknown = 1', 'stress_cases[0].unknown'),
    (MINIMAL + SEGMENTS + '[[stress_cases]]\nlabel = "test"\nSv_grad = 26000\nShmin_grad = 14000', 'stress_cases[0].SHmax_grad'),
    (MINIMAL + SEGMENTS + '[[stress_cases]]\nlabel = "test"\nSv_grad = 26000\nShmin_grad = 14000\nSHmax_grad = 25000\nz_data = [1000]', 'stress_cases[0].z_data'),
])
def test_bad_file_has_one_line_with_path_and_key(tmp_path, text, key):
    path = write_site(tmp_path, text)
    with pytest.raises(ValueError) as error:
        load_site(path)
    message = str(error.value)
    assert len(message.splitlines()) == 1
    assert str(path) in message
    assert key in message


def test_missing_file_and_invalid_utf8(tmp_path):
    path = tmp_path / 'missing.toml'
    with pytest.raises(ValueError, match='file') as error:
        load_site(path)
    assert str(path) in str(error.value)
    path.write_bytes(b'\xff')
    with pytest.raises(ValueError, match='TOML') as error:
        load_site(path)
    assert len(str(error.value).splitlines()) == 1


def test_file_content_is_data_and_never_executed(tmp_path):
    marker = tmp_path / 'executed'
    expression = f"__import__('pathlib').Path({str(marker)!r}).touch()"
    text = (MINIMAL + SEGMENTS).replace('"Test site"', json.dumps(expression))
    site = load_site(write_site(tmp_path, text))
    assert site.name == expression
    with pytest.raises(ValueError, match='TOML'):
        load_site(write_site(tmp_path, expression))
    assert not marker.exists()


def test_public_loader_export():
    assert 'load_site' in borethm.__all__
    assert load_site is sf.load_site
