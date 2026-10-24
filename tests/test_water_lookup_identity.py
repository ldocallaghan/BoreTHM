"""Property lookup arithmetic agrees with public SciPy interpolators exactly."""
import os
import numpy as np
import pytest
from scipy.interpolate import RegularGridInterpolator
from borethm import water_table as wt


@pytest.fixture(autouse=True)
def interpolation_tables(monkeypatch):
    if os.environ.get('BORETHM_TEST_CACHED_TABLE')=='1':
        assert wt._CACHE.is_file(), 'physical table must be built before this check'
        wt._interpolators()
        return
    # Varied positive tables cover the physical grid without an IAPWS build.
    rng=np.random.default_rng(419)
    grid=(wt.T_GRID,wt.P_GRID)
    shape=tuple(len(axis) for axis in grid)
    monkeypatch.setattr(wt,'_INTERP',{
        name:RegularGridInterpolator(grid,rng.uniform(.5,1.5,shape)*scale,
                                     bounds_error=False,fill_value=None)
        for name,scale in [('RHO',1000.),('CP',4000.),('MU',.001),('K',.6)]})


def assert_identical(temperature,pressure):
    points=wt._clip(temperature,pressure)
    expected=tuple(wt._interpolators()[name](points) for name in ['RHO','CP','MU','K'])
    actual=wt.props(temperature,pressure)
    assert isinstance(actual,tuple) and len(actual)==4
    for name,a,b in zip(['RHO','CP','MU','K'],actual,expected):
        assert a.dtype==b.dtype and a.shape==b.shape,name
        assert np.array_equal(a.view(np.uint64),b.view(np.uint64)),name
    a,b=wt.cp(temperature,pressure),expected[1]
    assert a.dtype==b.dtype and a.shape==b.shape
    assert np.array_equal(a.view(np.uint64),b.view(np.uint64))


def test_every_grid_node():
    t,p=np.meshgrid(wt.T_GRID,wt.P_GRID,indexing='ij')
    assert_identical(t.ravel(),p.ravel())


def test_every_cell_midpoint():
    t,p=np.meshgrid((wt.T_GRID[:-1]+wt.T_GRID[1:])/2,
                    (wt.P_GRID[:-1]+wt.P_GRID[1:])/2,indexing='ij')
    assert_identical(t.ravel(),p.ravel())


def test_one_million_fixed_seed_points():
    rng=np.random.default_rng(20261024)
    assert_identical(rng.uniform(wt.T_GRID[0],wt.T_GRID[-1],1_000_000),
                     rng.uniform(wt.P_GRID[0],wt.P_GRID[-1],1_000_000))


def test_edges_adjacent_float_values_and_corners():
    def edges(grid):
        return np.array([x for edge in [grid[0],grid[-1]]
            for x in [np.nextafter(edge,-np.inf),edge,np.nextafter(edge,np.inf)]])
    t,p=np.meshgrid(edges(wt.T_GRID),wt.P_GRID,indexing='ij')
    assert_identical(t.ravel(),p.ravel())
    t,p=np.meshgrid(wt.T_GRID,edges(wt.P_GRID),indexing='ij')
    assert_identical(t.ravel(),p.ravel())
    t,p=np.meshgrid(edges(wt.T_GRID),edges(wt.P_GRID),indexing='ij')
    assert_identical(t.ravel(),p.ravel())
    assert_identical([-np.inf,np.inf],[np.inf,-np.inf])


def test_nan_inputs():
    assert_identical([np.nan,20.,np.nan,20.],[1e6,np.nan,np.nan,1e6])


@pytest.mark.parametrize('dtype',[np.float32,np.float64])
def test_scalars_arrays_strides_and_empty_inputs(dtype):
    assert_identical(dtype(20.),dtype(1e6))
    t=np.array([20.,40.,250.,478.],dtype=dtype)
    p=np.array([1e5,40e6,100e6,218e6],dtype=dtype)
    assert_identical(t,p)
    assert_identical(t[::-1],p[::-1])
    assert_identical(t[:,None],p[:,None])
    t.flags.writeable=p.flags.writeable=False
    assert_identical(t,p)
    assert_identical(t[:0],p[:0])


def test_direct_property_objects_keep_their_scipy_interface():
    for name in ['RHO','CP','MU','K']:
        assert isinstance(getattr(wt,name),RegularGridInterpolator)
        assert getattr(wt,name) is wt._interpolators()[name]


@pytest.mark.parametrize('variant',['float32','readonly','nearest'])
def test_other_interpolator_paths_keep_their_original_results(monkeypatch,variant):
    tables={}
    for name,original in wt._interpolators().items():
        values=original.values.astype(np.float32) if variant=='float32' else original.values.copy()
        if variant=='readonly':
            values.flags.writeable=False
        tables[name]=RegularGridInterpolator(original.grid,values,
            method='nearest' if variant=='nearest' else 'linear',bounds_error=False,fill_value=None)
    monkeypatch.setattr(wt,'_INTERP',tables)
    assert_identical([20.2,150.3,300.4],[1e6,50e6,100e6])
