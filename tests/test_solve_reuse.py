"""Evaluation-scoped solve reuse preserves inputs, results and isolation."""
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from copy import deepcopy
import inspect
import json

import numpy as np
import pytest
from scipy.interpolate import RegularGridInterpolator
from borethm import model1_coupled as m1, site_evaluation as se, well_geometry as wg
from borethm.studies import levers


@pytest.fixture
def small_solve(monkeypatch):
    grid = (m1.wt.T_GRID, m1.wt.P_GRID)
    shape = tuple(len(axis) for axis in grid)
    monkeypatch.setattr(m1.wt, '_INTERP', {
        name: RegularGridInterpolator(grid, np.full(shape, value), bounds_error=False, fill_value=None)
        for name, value in [('RHO', 1000.), ('CP', 4180.), ('MU', .001), ('K', .6)]})
    original = m1.solve_bvp
    calls = []
    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(m1, 'solve_bvp', counted)
    kwargs = dict(m_dot=25., geometry=wg.WellGeometry.single(1000., wg.uniform_wall(45.)),
                  n_nodes=12, verbose=False)
    return kwargs, calls


def arguments(**kwargs):
    bound = inspect.signature(m1.solve).bind(**kwargs)
    bound.apply_defaults()
    return bound.arguments


def test_hit_matches_fresh_solve_and_copies_every_result(small_solve):
    kwargs, calls = small_solve
    fresh = m1.solve(**kwargs)
    expected = m1._cache_value(fresh)
    with m1._solve_cache_scope() as cache:
        first = m1.solve(**kwargs)
        assert m1._cache_value(first) == expected
        first['Td'][0] = -1.
        first['sol'].sol.c[:] = -1.
        first['old'] = first
        hit = m1.solve(**kwargs)
        assert m1._cache_value(hit) == expected
        hit['Tu'][:] = -2.
        hit['geometry']._r_bore[:] = -2.
        hit['sol'].y[:] = -2.
        again = m1.solve(**kwargs)
        assert m1._cache_value(again) == expected
        assert cache.hits == 2 and cache.misses == 1 and len(calls) == 2
    assert not cache.entries and not cache.active and m1._SOLVE_CACHE.get() is None
    assert m1._cache_value(m1.solve(**kwargs)) == expected and len(calls) == 3


def test_every_bound_parameter_is_part_of_the_key():
    base = arguments()
    changes = dict(m_dot=3., T_inj=41., G=.04, T_surf=16., target_rock_T=400.,
        Q_face=29000., t_years=2., pipe=wg.DUAL_WALL, k_rock=3., n_nodes=161,
        verbose=False, geotherm=lambda z: z, target_depth=1000.,
        geometry=wg.WellGeometry.single(1000., wg.uniform_wall(45.)),
        exposure=lambda z: z, fluid=dict(rho=1100., cp=3500., mu=.002, k=.5),
        rhocp_rock=3e6, friction_heat=True, tfa=.001, film_mult=.75,
        breaks=(500.,), init={'z': np.array([0., 1.])}, P_surface=2e5)
    assert set(changes) == set(base)
    original = m1._solve_key(base)
    for name, value in changes.items():
        assert m1._solve_key(dict(base, **{name: value})) != original, name


def test_cache_copies_interpolators_with_module_backends(monkeypatch, small_solve):
    kwargs, calls = small_solve
    original = m1.solve_bvp
    def with_backend(*args, **kw):
        result = original(*args, **kw)
        result.sol.backend = np
        return result
    monkeypatch.setattr(m1, 'solve_bvp', with_backend)
    with m1._solve_cache_scope() as cache:
        first = m1.solve(**kwargs)
        expected = m1._cache_value(first)
        first['sol'].sol.c[:] = -1.
        second = m1.solve(**kwargs)
        assert m1._cache_value(second) == expected
        assert second['sol'].sol.backend is first['sol'].sol.backend is np
        assert not np.shares_memory(first['sol'].sol.c, second['sol'].sol.c)
        second['Td'][:] = -2.
        third = m1.solve(**kwargs)
        assert m1._cache_value(third) == expected
        assert cache.hits == 2 and cache.misses == 1 and len(calls) == 1


@pytest.mark.parametrize('a,b', [(1, 1.), (True, 1), (0., -0.),
    (1., np.nextafter(1., 2.)), (np.float64(1.), 1.),
    (np.array([1.]), np.array([1.], dtype=np.float32)),
    (np.array([1.]), np.array([[1.]])),
    (np.array([0.]), np.array([-0.]))])
def test_types_shapes_and_float_bits_are_distinct(a, b):
    assert m1._cache_value(a) != m1._cache_value(b)


def test_geometry_and_fluid_compare_by_value_and_track_mutation(small_solve):
    kwargs, _ = small_solve
    fluid = dict(rho=1100., cp=3500., mu=.002, k=.5)
    original = arguments(**kwargs, fluid=fluid)
    copied = deepcopy(original)
    assert m1._solve_key(original) == m1._solve_key(copied)
    copied['geometry'].survey.tvd_at[-1] += 1.
    assert m1._solve_key(original) != m1._solve_key(copied)
    copied = deepcopy(original)
    copied['fluid']['cp'] += 1.
    assert m1._solve_key(original) != m1._solve_key(copied)


def test_callable_identity_is_retained():
    a, b = (lambda z: z), (lambda z: z)
    first = m1._solve_key(arguments(geotherm=a, exposure=a))
    assert first == m1._solve_key(arguments(geotherm=a, exposure=a))
    assert first != m1._solve_key(arguments(geotherm=b, exposure=a))
    assert first != m1._solve_key(arguments(geotherm=a, exposure=b))
    assert any(isinstance(part[1], m1._Identity) and part[1].value is a for _, part in first)


def test_complete_seed_state_is_included(small_solve):
    kwargs, _ = small_solve
    seed = m1.solve(**kwargs)
    original = m1._solve_key(arguments(**kwargs, init=seed))
    copied = deepcopy(seed)
    assert m1._solve_key(arguments(**kwargs, init=copied)) == original
    copied['sol'].sol.c.flat[0] = np.nextafter(copied['sol'].sol.c.flat[0], np.inf)
    assert m1._solve_key(arguments(**kwargs, init=copied)) != original


@pytest.mark.parametrize('scalar', [float, np.float64, np.float32])
def test_only_the_known_rop_formula_shares_immutable_captures(scalar):
    a = m1.exposure_from_rop(1000., scalar(20.), 0.)
    b = m1.exposure_from_rop(1000., scalar(20.), 0.)
    other = m1.exposure_from_rop(1000., np.nextafter(20., 30.), 0.)
    assert a is not b and m1._cache_exposure(a) == m1._cache_exposure(b)
    assert m1._cache_exposure(a) != m1._cache_exposure(other)
    z = np.linspace(0., 1000., 101)
    assert np.array_equal(a(z).view(np.uint64), b(z).view(np.uint64))
    array_a = m1.exposure_from_rop(np.array([1000.]), 20., 0.)
    array_b = m1.exposure_from_rop(np.array([1000.]), 20., 0.)
    assert m1._cache_exposure(array_a) != m1._cache_exposure(array_b)


def test_misses_keep_existing_behaviour(small_solve):
    kwargs, calls = small_solve
    expected = m1._cache_value(m1.solve(**kwargs, T_inj=41.))
    with m1._solve_cache_scope() as cache:
        m1.solve(**kwargs)
        actual = m1.solve(**kwargs, T_inj=41.)
        assert m1._cache_value(actual) == expected
        assert cache.hits == 0 and cache.misses == 2 and len(calls) == 3


def test_unknown_fluid_and_cyclic_inputs_bypass_the_cache(small_solve):
    kwargs, calls = small_solve
    class Fluid:
        def props(self, t, p):
            return tuple(np.full(np.shape(t), q) for q in (1000., 4180., .001, .6))
    with m1._solve_cache_scope() as cache:
        a = m1.solve(**kwargs, fluid=Fluid())
        b = m1.solve(**kwargs, fluid=Fluid())
        assert np.array_equal(a['Td'].view(np.uint64), b['Td'].view(np.uint64))
        assert cache.bypassed == 2 and not cache.entries and len(calls) == 2
    cycle = []
    cycle.append(cycle)
    with pytest.raises(TypeError, match='cyclic'):
        m1._cache_value(cycle)
    class CallableState:
        def __call__(self):
            return 1
    with pytest.raises(TypeError, match='unsupported'):
        m1._cache_value(CallableState())
    class Mapping(dict):
        __slots__ = ('hidden',)
    with pytest.raises(TypeError, match='custom mapping'):
        m1._cache_value(Mapping(value=1))


def test_nested_scopes_share_and_exception_exit_clears(small_solve):
    kwargs, calls = small_solve
    with pytest.raises(RuntimeError):
        with m1._solve_cache_scope() as outer:
            m1.solve(**kwargs)
            with m1._solve_cache_scope() as inner:
                assert inner is outer
                m1.solve(**kwargs)
            assert outer.hits == 1 and len(calls) == 1
            raise RuntimeError('end evaluation')
    assert not outer.entries and not outer.active and m1._SOLVE_CACHE.get() is None


def test_inherited_context_does_not_share_between_threads(small_solve):
    kwargs, calls = small_solve
    def child():
        assert m1._current_solve_cache() is None
        with m1._solve_cache_scope() as cache:
            m1.solve(**kwargs)
            m1.solve(**kwargs)
            assert cache.hits == cache.misses == 1
        return cache
    with m1._solve_cache_scope() as parent:
        m1.solve(**kwargs)
        context = copy_context()
        with ThreadPoolExecutor(max_workers=1) as executor:
            finished = executor.submit(context.run, child).result()
        assert finished is not parent and not finished.entries
        assert parent.misses == 1 and parent.hits == 0 and len(calls) == 2
        m1.solve(**kwargs)
        assert parent.hits == 1


def test_two_evaluations_have_equal_exports_and_separate_empty_caches(monkeypatch, small_solve):
    kwargs, calls = small_solve
    scopes = []
    def assessment(*args, **kw):
        scopes.append(m1._current_solve_cache())
        a, b = m1.solve(**kwargs), m1.solve(**kwargs)
        assert np.array_equal(a['Td'].view(np.uint64), b['Td'].view(np.uint64))
        return {'Td': a['Td'], 'Tu': a['Tu'], 'bottom': a['T_bottom_delivered']}
    monkeypatch.setattr(se, '_evaluate_v13', assessment)
    site = se.find_site('newberry')
    first = json.dumps(se._jsonable(se.evaluate(site)))
    assert m1._SOLVE_CACHE.get() is None and not scopes[0].entries
    second = json.dumps(se._jsonable(se.evaluate(site)))
    assert first == second and len(calls) == 2
    assert scopes[0] is not scopes[1] and all(not s.entries and not s.active for s in scopes)


def test_trial_scope_covers_nested_evaluation_and_cleans_file_cache_hit(monkeypatch, small_solve, tmp_path):
    kwargs, calls = small_solve
    scopes = []
    def settings(*args):
        scopes.append(m1._current_solve_cache())
        result = se.evaluate(se.find_site('newberry'))
        assert m1._current_solve_cache() is scopes[-1]
        m1.solve(**kwargs)
        return result
    def assessment(*args, **kw):
        m1.solve(**kwargs)
        return {}
    monkeypatch.setattr(levers, 'evaluate_settings', settings)
    monkeypatch.setattr(se, '_evaluate_v13', assessment)
    monkeypatch.setattr(levers, 'gates', lambda out: {})
    monkeypatch.setattr(levers.rb, 'metrics', lambda out: {})
    monkeypatch.setattr(se, 'result_dict', lambda out: out)
    config = levers.Settings(flow_L_s=25.)
    first = levers.trial('newberry', 'scope-test', config, tmp_path)
    assert len(calls) == 1 and scopes[0].hits == 1
    assert not scopes[0].entries and not scopes[0].active and m1._SOLVE_CACHE.get() is None
    assert levers.trial('newberry', 'scope-test', config, tmp_path) == first
    assert len(calls) == 1 and m1._SOLVE_CACHE.get() is None
