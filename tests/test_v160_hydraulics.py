"""Independent formula, legacy and energy checks for hydraulic additions."""
from dataclasses import replace
import math

import numpy as np
import pytest

from borethm import (HydraulicJoint, LocalLoss, ReferenceToolLoss, SurfaceLoss,
                     HydraulicProgramme, PipeType, Layer, StringSegment,
                     WellGeometry, open_hole, hydraulics, circulating_temperatures)
from borethm import hydraulic_losses as hl, well_geometry as wg, model1_coupled as m1, fluids, pressure
from borethm.programme import programme_from_dict
from reference_v150_pressure import frozen_hydraulics


WATER=dict(rho=1000.,mu=.02,cp=4000.,k=.6)


class Bingham:
    yield_point=5.

    def props(self,t,p):
        shape=np.broadcast(t,p).shape
        return tuple(np.full(shape,WATER[k]) for k in ('rho','cp','mu','k'))


@pytest.mark.parametrize('fluid',[None,WATER,fluids.Mud(1200.)])
@pytest.mark.parametrize('profile',[False,True])
def test_legacy_is_bit_exact_against_frozen_function(fluid,profile):
    g=wg.WellGeometry([StringSegment(300,wg.CONVENTIONAL),StringSegment(600,wg.WU_HWDP),StringSegment(150,wg.WU_COLLAR)],
                      [open_hole(0,200,.25),open_hole(200,1050,.22)])
    z=np.linspace(0,1050,101)
    result=dict(z=z,Td=25+.02*z,Tu=75+.01*z) if profile else None
    expected=frozen_hydraulics(20,g,result=result,fluid=fluid)
    actual=hydraulics(20,g,result=result,fluid=fluid,hydraulics_model='v1.5.0')
    assert actual==expected


@pytest.mark.parametrize('tau,fluid',[(0.,WATER),(5.,Bingham())])
def test_joint_body_replacement_and_local_losses_against_hand_calculation(tau,fluid):
    L=1000.
    joint=HydraulicJoint(.12,.06,.6,10.)
    pipe=PipeType('hand case',(Layer(.04,.05,45.),),hydraulic_joint=joint)
    g=WellGeometry.single(L,pipe,r_hole=.10)
    mass=.2
    rho,mu=1000.,.02
    def grad(area,diameter,annulus):
        v=mass/rho/area
        if annulus and tau:
            return 48*mu*v/diameter**2+6*tau/diameter
        if tau:
            return 32*mu*v/diameter**2+16*tau/(3*diameter)
        return 32*mu*v/diameter**2
    result=hydraulics(mass,g,fluid=fluid,bit=False)
    for annulus,key in ((False,'dp_string'),(True,'dp_annulus')):
        ab=math.pi*((.2**2-.1**2) if annulus else .08**2)/4
        aj=math.pi*((.2**2-.12**2) if annulus else .06**2)/4
        db,dj=(.10,.08) if annulus else (.08,.06)
        ratio=min(ab,aj)/max(ab,aj)
        k=(1-ratio)**2+.5*(1-ratio)**.75
        local=k*.5*rho*(mass/rho/min(ab,aj))**2
        expected=L*grad(ab,db,annulus)+L/10*((grad(aj,dj,annulus)-grad(ab,db,annulus))*.6+local)
        assert result[key]==pytest.approx(expected,rel=2e-13)


@pytest.mark.parametrize('case,coefficient',[(1,1.),(2,.36),(3,.22),(4,.15),(5,.15)])
@pytest.mark.parametrize('density',[998.,1350.])
def test_API_surface_cases(case,coefficient,density):
    flow=.025
    expected=coefficient*(density/119.826)*(flow/6.30902e-5/100)**1.86*6894.757
    assert SurfaceLoss.api_case(case).pressure(density,flow)==pytest.approx(expected,rel=1e-15)


def test_tool_density_and_flow_squared_scaling():
    tool=ReferenceToolLoss(2e5,.02,1000.)
    assert tool.pressure(1200.,.04)==960000.
    low=ReferenceToolLoss(100*hl.PSI,900*hl.GPM,1000.)
    high=ReferenceToolLoss(100*hl.PSI,400*hl.GPM,1000.)
    assert low.pressure(1000.,600*hl.GPM)<high.pressure(1000.,600*hl.GPM)


@pytest.mark.parametrize('fluid',[WATER,Bingham()])
def test_supplied_local_K_uses_its_declared_reference_area(fluid):
    pipe=wg.uniform_wall(45.,.04,.05)
    bare=WellGeometry.single(100,pipe,r_hole=.11)
    local=LocalLoss(2.,3.,.003,.012,'declared test restrictions')
    g=WellGeometry([StringSegment(100,pipe,local_loss=local)],bare.hole)
    a=hydraulics(.2,bare,fluid=fluid,bit=False)
    b=hydraulics(.2,g,fluid=fluid,bit=False)
    assert b['dp_string']-a['dp_string']==pytest.approx(2*.5*1000*(.2/1000/.003)**2,abs=1e-9)
    assert b['dp_annulus']-a['dp_annulus']==pytest.approx(3*.5*1000*(.2/1000/.012)**2,abs=1e-9)


@pytest.mark.parametrize('length',[.8,2.,15.])
def test_whole_tool_replaces_internal_passage_and_conserves_short_tool_integral(length):
    pipe=wg.uniform_wall(45.,.04,.05)
    tool=ReferenceToolLoss(1e6,.02,1000.,basis='total_internal')
    g=WellGeometry([StringSegment(100-length,pipe),StringSegment(length,pipe,tool_loss=tool)], [open_hole(0,100,.22)])
    result=hydraulics(20,g,fluid=WATER,bit=False)
    assert result['terms']['bore']['tool']==pytest.approx(1e6,rel=2e-13)
    reference=hydraulics(20,WellGeometry.single(100-length,pipe,r_hole=.11),fluid=WATER,bit=False)
    assert result['terms']['bore']['body']==pytest.approx(reference['dp_string'],rel=2e-13)


def test_internal_tool_span_suppresses_its_internal_transition():
    a=wg.uniform_wall(45.,.04,.05)
    b=wg.uniform_wall(45.,.03,.06)
    g=WellGeometry([StringSegment(80,a),StringSegment(10,a,tool_loss=ReferenceToolLoss(1e6,.02,1000.,'total_internal',2)),StringSegment(10,b)], [open_hole(0,100,.22)])
    result=hydraulics(20,g,fluid=WATER,bit=False)
    assert result['terms']['bore']['geometric_local']==0
    assert result['terms']['annulus']['geometric_local']>0


def test_overlap_and_closed_joint_are_rejected():
    tool=ReferenceToolLoss(1e5,.02,1000.,span_segments=2)
    p=wg.CONVENTIONAL
    g=WellGeometry([StringSegment(50,p,tool_loss=tool),StringSegment(50,p,tool_loss=replace(tool,span_segments=1))], [open_hole(0,100,.22)])
    with pytest.raises(ValueError,match='non-overlapping'):
        hydraulics(20,g,fluid=WATER)
    closed=replace(p,hydraulic_joint=HydraulicJoint(.23,.10,.5,10))
    with pytest.raises(ValueError,match='closes'):
        hydraulics(20,WellGeometry.single(100,closed,r_hole=.11),fluid=WATER)


def test_legacy_rejects_new_fields_and_surface():
    g=WellGeometry.single(100,wg.CONVENTIONAL)
    with pytest.raises(ValueError,match='rejects'):
        hydraulics(20,g,fluid=WATER,surface=SurfaceLoss.api_case(5),hydraulics_model='v1.5.0')
    joint=replace(wg.CONVENTIONAL,hydraulic_joint=HydraulicJoint(.17,.10,.5,10))
    with pytest.raises(ValueError,match='rejects'):
        circulating_temperatures(geometry=WellGeometry.single(100,joint),hydraulics_model='v1.5.0')


def test_reference_lengths_dual_wall_and_zero_allowances():
    p=HydraulicProgramme.reference_programme()
    for pipe in (wg.DUAL_WALL,wg.VACUUM_INSULATED):
        g=p.geometry(1500,pipe,shoes=(50,300,750))
        assert g.string[0].pipe.hydraulic_joint.bore_diameter==2*pipe.r_bore
        assert g.string[0].pipe.with_joints(.1).hydraulic_joint==g.string[0].pipe.hydraulic_joint
        assert sum(s.length for s in g.string[2:-1])==143.
        assert sum(s.length for s in g.string)==1500.
    g=HydraulicProgramme.reference_programme(tools=False,joints=False,surface=None).geometry(1500,wg.CONVENTIONAL,shoes=(50,300,750))
    assert all(s.tool_loss is None and s.pipe.hydraulic_joint is None for s in g.string)


@pytest.mark.parametrize('fluid',[WATER,Bingham()])
def test_energy_balance_with_joints_tool_and_surface_excluded_from_hole(fluid):
    p=HydraulicProgramme.reference_programme()
    g=p.geometry(1500,wg.DUAL_WALL,shoes=(50,300,750))
    string=list(g.string)
    string[-1]=replace(string[-1],local_loss=LocalLoss(1.,.5,source='test component'))
    g=WellGeometry(string,g.hole,g.survey)
    r=circulating_temperatures(m_dot=20,geometry=g,fluid=fluid,friction_heat=True,surface=p.surface)
    assert r['success']
    check=r['energy_check']
    assert check['passed'] and abs(check['residual_W']) <= check['tolerance_W']
    assert check['surface_W_in_hole']==check['density_column_W']==0
    assert check['assigned_terms_W']['bore']['tool']>0
    assert check['assigned_terms_W']['annulus']['tool']==0
    assert check['assigned_terms_W']['annulus']['supplied_local']>0
    h=hydraulics(20,g,result=r,fluid=fluid)
    assert h['dp_surface']>0
    assert sum(sum(v.values()) for v in h['terms'].values())+h['dp_bit']+h['dp_buoyancy']+h['dp_surface']==pytest.approx(h['spp'],rel=1e-15)
    r['hyd']=h
    depths=np.linspace(0,g.md_bit,51)
    dp=[pressure.annulus_friction(r,x) for x in depths]
    assert np.all(np.diff(dp)>=0)
    assert dp[0]==0 and dp[-1]==h['dp_annulus']


def test_strict_programme_and_custom_string_have_no_reference_tool():
    p=programme_from_dict(dict(segments=[dict(length=100.,bore_diameter=.08,outer_diameter=.10)],surface=dict(enabled=False)))
    g=p.geometry(100.,wg.DUAL_WALL)
    assert g.string[0].pipe.r_bore==.04 and g.string[0].tool_loss is None and p.surface is None
    with pytest.raises(ValueError,match='unknown key'):
        programme_from_dict(dict(surface=dict(case=5,coefficient_typo=1)))
    with pytest.raises(ValueError,match='choose exactly one'):
        programme_from_dict(dict(surface=dict(case=5,coefficient=.15)))
    with pytest.raises(ValueError,match='unknown key'):
        programme_from_dict(dict(segments=[dict(length=100.,bore_diameter=.08,outer_diameter=.10,tool_loss=dict(dp_ref=1.,flow_ref=.01,density_ref=1000.,typo=1))]))


@pytest.mark.parametrize('mud_density', [None, 1200.])
def test_variable_property_energy_balance(mud_density):
    """Actual water and mud properties preserve the in-hole energy balance."""
    from borethm.fluids import Mud
    fluid=None if mud_density is None else Mud(mud_density)
    programme=HydraulicProgramme.reference_programme()
    geometry=programme.geometry(1500.,wg.DUAL_WALL,shoes=(50.,300.,750.))
    string=list(geometry.string)
    string[-1]=replace(string[-1],local_loss=LocalLoss(1.,.5,source='synthetic bit-body restriction'))
    geometry=WellGeometry(string,geometry.hole,geometry.survey)
    result=circulating_temperatures(m_dot=20.,geometry=geometry,fluid=fluid,
                                   friction_heat=True,surface=programme.surface)
    assert result['success']
    check=result['energy_check']
    assert check['passed']
    assert abs(check['residual_W']) <= max(1.,.001*max(abs(check['assigned_W']),abs(check['applied_W'])))
    assert check['surface_W_in_hole'] == check['density_column_W'] == 0.
    pressure=hydraulics(20.,geometry,result=result,fluid=fluid)
    assert pressure['dp_surface'] > 0.


def test_short_bit_component_keeps_boundary_conditions_at_the_well_ends():
    geometry=WellGeometry((wg.StringSegment(99.75,wg.CONVENTIONAL),
                           wg.StringSegment(.25,wg.WU_COLLAR)),
                          (wg.open_hole(0.,100.,.25),))
    result=circulating_temperatures(m_dot=20.,geometry=geometry,fluid=WATER,
                                   friction_heat=True)
    assert result['success']
    assert result['sol'].x[0] == 0.
    assert result['sol'].x[-1] == geometry.md_bit
    assert result['energy_check']['passed']


def test_overlapping_geometry_ramps_converge_for_short_serial_components():
    geometry=WellGeometry((wg.StringSegment(70.,wg.CONVENTIONAL),
                           wg.StringSegment(.3,wg.WU_COLLAR),
                           wg.StringSegment(.3,wg.WU_HWDP),
                           wg.StringSegment(29.4,wg.CONVENTIONAL)),
                          (wg.open_hole(0.,100.,.25),))
    result=circulating_temperatures(m_dot=20.,geometry=geometry,fluid=WATER,
                                   friction_heat=True)
    assert result['success']
    assert result['sol'].status == 0
    assert result['sol'].x[-1] == geometry.md_bit
    assert result['energy_check']['passed']


def test_turnaround_accuracy_meets_the_deep_well_energy_tolerance():
    from borethm import site_evaluation as se
    site=se.SOULTZ
    programme=HydraulicProgramme.reference_programme()
    geometry=programme.geometry(site.target(),wg.TK_DRAKON)
    result=circulating_temperatures(m_dot=se.mass_flow(40.,None),geometry=geometry,
        T_inj=site.T_inj,k_rock=site.k_rock,geotherm=site.temperature(),
        target_rock_T=float(site.temperature()(site.target())),Q_face=se.Q_FACE_SITE,
        friction_heat=True,surface=programme.surface)
    assert result['success']
    check=result['energy_check']
    assert check['passed']
    assert abs(check['applied_turnaround_W']-check['nozzle_W']-check['face_W']) <= check['tolerance_W']


@pytest.mark.parametrize('unavailable',[False,True])
def test_energy_diagnostic_cannot_reject_a_converged_solve(monkeypatch,unavailable):
    def diagnostic(*args,**kwargs):
        if unavailable:
            raise RuntimeError('synthetic diagnostic failure')
        return dict(enabled=True,passed=False,flagged=True,status='power residual flagged')
    monkeypatch.setattr(hl,'energy_check',diagnostic)
    geometry=WellGeometry((wg.StringSegment(100.,wg.CONVENTIONAL),),
                          (wg.open_hole(0.,100.,.25),))
    result=circulating_temperatures(m_dot=20.,geometry=geometry,fluid=WATER,friction_heat=True)
    assert result['sol'].success and result['success']
    assert result['energy_check']['flagged']
    assert not result['energy_check']['passed']
