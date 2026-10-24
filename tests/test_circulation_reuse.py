"""Circulation property reuse preserves helper arithmetic and clipping."""
import numpy as np
import pytest
from scipy.interpolate import RegularGridInterpolator
from borethm import model1_coupled as m1, well_geometry as wg


@pytest.fixture(autouse=True)
def synthetic_water_table(monkeypatch):
    # Exercise the solve without building the physical first-use cache.
    grid=(m1.wt.T_GRID,m1.wt.P_GRID)
    shape=tuple(len(axis) for axis in grid)
    monkeypatch.setattr(m1.wt,'_INTERP',{
        name:RegularGridInterpolator(grid,np.full(shape,value),bounds_error=False,fill_value=None)
        for name,value in [('RHO',1000.),('CP',4180.),('MU',.001),('K',.6)]})


@pytest.mark.parametrize('friction',[False,True])
@pytest.mark.parametrize('weighted',[False,True])
def test_small_solve_looks_up_each_rhs_property_once(monkeypatch,friction,weighted):
    fluid=dict(rho=1100.,cp=3500.,mu=.002,k=.5) if weighted else None
    geometry=wg.WellGeometry.single(1000.,wg.uniform_wall(45.))
    original_props,original_bvp=m1.fluid_props,m1.solve_bvp
    calls=[]
    active=[None]
    def props(*args,**kwargs):
        if active[0] is not None:
            active[0].append((np.array(args[0],copy=True),np.array(args[1],copy=True)))
        return original_props(*args,**kwargs)
    def bvp(fun,bc,*args,**kwargs):
        def counted(z,y):
            active[0]=[]
            try:
                return fun(z,y)
            finally:
                calls.append(active[0])
                active[0]=None
        return original_bvp(counted,bc,*args,**kwargs)
    monkeypatch.setattr(m1,'fluid_props',props)
    monkeypatch.setattr(m1,'solve_bvp',bvp)
    result=m1.solve(m_dot=25.,geometry=geometry,fluid=fluid,
                    friction_heat=friction,n_nodes=12,verbose=False)
    assert result['success'] and calls
    assert all(len(call)==(4 if friction else 2) for call in calls)
    if friction:
        for call in calls:
            for temperature,pressure in call[-2:]:
                assert np.all((temperature>=1)&(temperature<=480))
                assert np.all(pressure>=m1.P_LIQUID)


def test_precomputed_properties_preserve_helper_results():
    T=np.array([20.,100.,300.])
    P=np.array([1e6,50e6,120e6])
    fluid=dict(rho=1100.,cp=3500.,mu=.002,k=.5)
    properties=m1.fluid_props(T,P,fluid)
    before=m1.h_dittus(25.,.01,.1,T,P,fluid=fluid)
    after=m1.h_dittus(25.,.01,.1,T,P,fluid=fluid,properties=properties)
    assert np.array_equal(before.view(np.uint64),after.view(np.uint64))
    assert np.array_equal(m1._cp(T,P,fluid).view(np.uint64),
                          m1._cp(T,P,fluid,properties=properties).view(np.uint64))


def test_water_heat_capacity_keeps_its_distinct_clipping(monkeypatch):
    class Table:
        def __call__(self,points):
            assert np.array_equal(points,[[480.,220e6]])
            return np.array([1234.])
    monkeypatch.setitem(m1.wt.__dict__,'CP',Table())
    assert m1._cp(np.array([500.]),np.array([230e6]),
                  properties=(None,np.array([-1.]),None,None))[0]==1234.


@pytest.mark.parametrize('offset_geometry',[False,True])
def test_conductance_reuse_keeps_true_depth_and_geometry_sample_distinct(offset_geometry):
    geometry=wg.WellGeometry([wg.StringSegment(1000.,wg.uniform_wall(45.))],
        [wg.open_hole(0.,500.,.22),wg.open_hole(500.,1000.,.25)],
        survey=wg.Survey([0.,1000.],[0.,600.]))
    z=np.array([50.,500.,950.])
    geom_z=np.array([100.,450.,900.]) if offset_geometry else None
    Td,Tu=np.array([40.,50.,60.]),np.array([50.,60.,70.])
    fluid=dict(rho=1100.,cp=3500.,mu=.002,k=.5)
    expected=m1.conductances(z,Td,Tu,25.,1.,2.9,geometry,fluid=fluid,geom_z=geom_z)
    g=geometry.at(z if geom_z is None else geom_z)
    tvd=geometry.survey.tvd(z)
    pressure=m1.P_of_z(tvd)
    actual=m1.conductances(z,Td,Tu,25.,1.,2.9,geometry,fluid=fluid,geom_z=geom_z,
        geometry_values=g,tvd_values=tvd,pressure=pressure,
        properties_d=m1.fluid_props(Td,pressure,fluid),
        properties_u=m1.fluid_props(Tu,pressure,fluid))
    for a,b in zip(actual,expected):
        assert np.array_equal(a.view(np.uint64),b.view(np.uint64))
