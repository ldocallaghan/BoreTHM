"""Tapered variants may change ordinary-pipe joints only."""
import importlib.util
from pathlib import Path

import pytest

from borethm import well_geometry as wg
from borethm.hydraulic_losses import HydraulicJoint

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('tapered_joint_prediction',ROOT/'validation/model-development/entry-13/predict.py')
prediction=importlib.util.module_from_spec(spec);spec.loader.exec_module(prediction)
INCH=.0254


def pipe(name,od,bore,joint_od,joint_id):
    return wg.PipeType(name,(wg.Layer(bore*INCH/2,od*INCH/2,45.),),
        hydraulic_joint=HydraulicJoint(joint_od*INCH,joint_id*INCH,29*INCH,31.5*.3048))


def geometry(pipes):
    return wg.WellGeometry([wg.StringSegment(20.,p) for p in pipes],[wg.open_hole(0.,20*len(pipes),12.25*INCH)])


@pytest.mark.parametrize('variant,angle',[('tapered_primary',11.5),('tapered_long',6.3),('tapered_steep',30.)])
def test_ordinary_joints_taper_while_insulation_and_hwdp_stay_abrupt(variant,angle):
    insulated=pipe('IDP, k_eff 4.92',5.5,4.67,7.,4.);hwdp=pipe('HWDP',5.5,3.5,7.,3.5)
    new=prediction.apply_geometry(geometry([pipe('ordinary',5.5,4.67,7.,4.),insulated,hwdp]),'16B',variant)
    joint=new.string[0].pipe.hydraulic_joint
    assert joint.transition=='tapered' and joint.taper_angle_deg==angle
    assert joint.bore_diameter/INCH==pytest.approx(3.) and joint.restriction_length/INCH==pytest.approx(22.)
    assert new.string[1].pipe==insulated and new.string[2].pipe==hwdp


@pytest.mark.parametrize('well,od,bore,length',[('16A',5.,4.276,11.),('16B',5.5,4.67,10.)])
def test_pin_length_variant_changes_only_the_restriction(well,od,bore,length):
    old=geometry([pipe('ordinary',od,bore,7.,4.)])
    primary=prediction.apply_geometry(old,well,'tapered_primary').string[0].pipe.hydraulic_joint
    pin=prediction.apply_geometry(old,well,'tapered_pin_length').string[0].pipe.hydraulic_joint
    assert pin.restriction_length/INCH==pytest.approx(length)
    assert pin.taper_angle_deg==primary.taper_angle_deg and pin.bore_diameter==primary.bore_diameter


def test_entry_12_variants_stay_abrupt_or_zero_local():
    old=geometry([pipe('ordinary',5.,4.276,7.,4.)])
    assert prediction.apply_geometry(old,'16A','installed_primary').string[0].pipe.hydraulic_joint.resolved('v1.7.0').transition=='abrupt'
    assert prediction.apply_geometry(old,'16A','installed_no_local').string[0].pipe.hydraulic_joint.transition=='gradual'
    assert prediction.apply_geometry(old,'16A','working')==old
