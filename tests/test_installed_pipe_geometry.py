"""Installed ordinary-pipe records must not change insulation or HWDP."""
import importlib.util
from pathlib import Path

import pytest

from borethm import well_geometry as wg
from borethm.hydraulic_losses import HydraulicJoint

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('installed_pipe_prediction',ROOT/'validation/model-development/entry-12/predict.py')
prediction=importlib.util.module_from_spec(spec);spec.loader.exec_module(prediction)
INCH=.0254


def pipe(name,od,bore,joint_od,joint_id):
    return wg.PipeType(name,(wg.Layer(bore*INCH/2,od*INCH/2,45.),),
        hydraulic_joint=HydraulicJoint(joint_od*INCH,joint_id*INCH,29*INCH,31.5*.3048))


def geometry(pipes):
    return wg.WellGeometry([wg.StringSegment(20.,p) for p in pipes],[wg.open_hole(0.,20*len(pipes),12.25*INCH)])


def test_same_bore_does_not_identify_the_insulated_connection():
    ordinary=pipe('ordinary',5.5,4.67,7.,4.)
    insulated=pipe('IDP, k_eff 4.92',5.5,4.67,7.,4.)
    hwdp=pipe('HWDP',5.5,3.5,7.,3.5)
    old=geometry([ordinary,insulated,hwdp]);new=prediction.apply_geometry(old,'16B','installed_primary')
    joint=new.string[0].pipe.hydraulic_joint
    assert joint.bore_diameter/INCH==pytest.approx(3.)
    assert joint.restriction_length/INCH==pytest.approx(22.)
    assert new.string[1].pipe==insulated and new.string[2].pipe==hwdp
    assert new.string[0].pipe.layers==ordinary.layers
    assert new.string[0].pipe.hydraulic_joint.spacing==ordinary.hydraulic_joint.spacing


def test_premium_changes_only_the_declared_16b_id_and_tong_length():
    old=geometry([pipe('ordinary',5.5,4.67,7.,4.)])
    primary=prediction.apply_geometry(old,'16B','installed_primary')
    premium=prediction.apply_geometry(old,'16B','installed_premium')
    a,b=primary.string[0].pipe,premium.string[0].pipe
    assert b.layers==a.layers and b.hydraulic_joint.outer_diameter==a.hydraulic_joint.outer_diameter
    assert b.hydraulic_joint.bore_diameter/INCH==pytest.approx(3.063)
    assert b.hydraulic_joint.restriction_length/INCH==pytest.approx(10.)


def test_installed_16a_and_abrupt_alias_preserve_thermal_geometry():
    old=geometry([pipe('ordinary',5.,4.276,6.625,3.25)])
    primary=prediction.apply_geometry(old,'16A','installed_primary')
    abrupt=prediction.apply_geometry(old,'16A','installed_abrupt')
    assert primary.string==abrupt.string
    assert primary.string[0].pipe.layers==old.string[0].pipe.layers
    joint=primary.string[0].pipe.hydraulic_joint
    assert joint.bore_diameter/INCH==pytest.approx(2.75)
    assert joint.restriction_length/INCH==pytest.approx(25.)
    assert joint.resolved('v1.7.0').transition=='abrupt'
