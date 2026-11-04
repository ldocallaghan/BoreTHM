"""Conical drill-pipe joint transitions against hand calculations."""
from dataclasses import replace
import math

import pytest

from borethm.hydraulic_losses import HydraulicJoint,conical_change,hydraulics,local_change
from borethm.well_geometry import Layer,PipeType,WellGeometry

INCH=.0254
RHO,FLOW=1000.,.0379   # kg/m3 and m3/s, about 600 US gpm
BODY,BORE=4.276*INCH,2.75*INCH
WATER=dict(rho=1000.,mu=.02,cp=4000.,k=.6)


def area(diameter):
    return math.pi*diameter**2/4


def coefficient(up,down,angle):
    return float(conical_change(area(up),area(down),RHO,RHO*FLOW,angle)[1])


# Independent arithmetic on beta^2 = (2.75/4.276)^2 = 0.413606: expansion then contraction.
@pytest.mark.parametrize('angle,expansion,contraction',[
    (6.3,2.6*0.054950*0.586394**2,0.8*0.054950*0.586394),
    (11.5,2.6*0.100188*0.586394**2,0.8*0.100188*0.586394),
    (30.,2.6*0.258819*0.586394**2,0.8*0.258819*0.586394)])
def test_coefficients_match_hand_calculations(angle,expansion,contraction):
    assert coefficient(BORE,BODY,angle)==pytest.approx(expansion,rel=2e-5)
    assert coefficient(BODY,BORE,angle)==pytest.approx(contraction,rel=2e-5)


def test_pressure_loss_uses_the_small_bore_velocity():
    loss,k=conical_change(area(BODY),area(BORE),RHO,RHO*FLOW,11.5)
    velocity=FLOW/area(BORE)
    assert float(loss)==pytest.approx(float(k)*.5*RHO*velocity**2,rel=1e-14)


def test_180_degrees_reproduces_the_abrupt_expansion_exactly():
    tapered=coefficient(BORE,BODY,180.)
    abrupt=float(local_change(area(BORE),area(BODY),RHO,RHO*FLOW,.001,BORE)[1])
    assert tapered==abrupt


def test_180_degree_contraction_differs_from_idelchik_by_the_stated_amount():
    ratio=(BORE/BODY)**2
    tapered=coefficient(BODY,BORE,180.)
    abrupt=float(local_change(area(BODY),area(BORE),RHO,RHO*FLOW,.001,BORE)[1])
    assert tapered==pytest.approx(.5*(1-ratio))
    assert abrupt==pytest.approx(.5*(1-ratio)**.75)
    assert abrupt-tapered==pytest.approx(.5*((1-ratio)**.75-(1-ratio)))
    assert tapered<abrupt


@pytest.mark.parametrize('angle',[6.3,11.5,30.,45.,60.,180.])
def test_zero_area_change_gives_zero_loss(angle):
    loss,k=conical_change(area(BODY),area(BODY),RHO,RHO*FLOW,angle)
    assert float(loss)==0 and float(k)==0


def test_branches_meet_the_formula_stated_for_their_angle():
    assert coefficient(BODY,BORE,45.)==pytest.approx(.8*math.sin(math.radians(22.5))*(1-(BORE/BODY)**2))
    assert coefficient(BORE,BODY,46.)==pytest.approx((1-(BORE/BODY)**2)**2)


def string(joint):
    pipe=PipeType('hand case',(Layer(.04,.05,45.),),hydraulic_joint=joint)
    return WellGeometry.single(1000.,pipe,r_hole=.10)


def test_hydraulics_applies_the_cones_to_the_bore_and_keeps_the_abrupt_annulus():
    abrupt=HydraulicJoint(.12,.06,.6,10.)
    tapered=replace(abrupt,transition='tapered',taper_angle_deg=11.5)
    a=hydraulics(.2,string(abrupt),fluid=WATER,bit=False)
    t=hydraulics(.2,string(tapered),fluid=WATER,bit=False)
    ab,aj=math.pi*.08**2/4,math.pi*.06**2/4
    k=float(conical_change(ab,aj,1000.,.2,11.5)[1]+conical_change(aj,ab,1000.,.2,11.5)[1])
    assert t['terms']['bore']['joint_local']==pytest.approx(100*k*.5*1000.*(.2/1000./aj)**2,rel=1e-10)
    assert t['terms']['annulus']==a['terms']['annulus']
    assert t['terms']['bore']['joint_replacement']==a['terms']['bore']['joint_replacement']
    assert t['terms']['bore']['body']==a['terms']['bore']['body']
    assert 'joint_taper_no_stated_Reynolds_range' in t['flags']
    assert 'joint_taper_no_stated_Reynolds_range' not in a['flags']


def test_option_unset_is_identical_and_defaults_to_abrupt():
    implicit=HydraulicJoint(.12,.06,.6,10.)
    explicit=HydraulicJoint(.12,.06,.6,10.,'abrupt','',None)
    assert implicit==explicit and implicit.transition=='abrupt' and implicit.taper_angle_deg is None
    a,b=(hydraulics(.2,string(j),fluid=WATER,bit=False) for j in (implicit,explicit))
    assert a['spp']==b['spp'] and a['terms']==b['terms'] and a['flags']==b['flags']


@pytest.mark.parametrize('settings',[dict(transition='tapered'),
    dict(transition='tapered',taper_angle_deg=0.),dict(transition='tapered',taper_angle_deg=181.),
    dict(transition='tapered',taper_angle_deg=float('nan')),dict(taper_angle_deg=11.5),
    dict(transition='gradual',taper_angle_deg=11.5)])
def test_invalid_taper_settings_are_rejected(settings):
    with pytest.raises(ValueError):
        HydraulicJoint(.12,.06,.6,10.,**settings)
