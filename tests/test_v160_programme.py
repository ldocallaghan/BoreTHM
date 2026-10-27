"""Site-file configuration and evaluator precedence, without field solves."""
from dataclasses import replace

import pytest
from borethm import HydraulicProgramme, SurfaceLoss, load_site
from borethm import site_evaluation as se, well_geometry as wg
from borethm.programme import programme_from_dict
from test_site_files import MINIMAL, SEGMENTS


def test_site_file_loads_custom_components_and_new_fields(tmp_path):
    text=MINIMAL+SEGMENTS+'''
[programme]
transitions = "gradual"
[programme.surface]
coefficient = 0.22
[[programme.segments]]
length = 10700.0
bore_diameter = 0.08
outer_diameter = 0.10
name = "client pipe"
[programme.segments.hydraulic_joint]
outer_diameter = 0.14
bore_diameter = 0.06
restriction_length = 0.6
spacing = 9.5
[[programme.hole]]
md_top = 0.0
md_bottom = 10700.0
r_wall = 0.11
'''
    path=tmp_path/'site.toml'
    path.write_text(text)
    site=load_site(path)
    p=site.programme
    assert p.reference is None and p.surface.value==.22
    assert p.segments[0].pipe.hydraulic_joint.bore_diameter==.06
    assert p.segments[0].tool_loss is None
    assert p.geometry(10700.,p.segments[0].pipe).md_bit==10700.


def test_override_precedence_and_original_profile_preserved(monkeypatch):
    a=HydraulicProgramme.reference_programme(surface=SurfaceLoss.api_case(1))
    b=HydraulicProgramme.reference_programme(surface=SurfaceLoss.api_case(2))
    site=replace(se.SOULTZ,programme=a)
    seen=[]
    monkeypatch.setattr(se,'_evaluate_v13',lambda s,*args,**kwargs: seen.append(s.programme) or {})
    se.evaluate(site)
    se.evaluate(site,programme=b)
    se.evaluate(site,programme=b,surface=SurfaceLoss.coefficient(0.))
    assert seen[0]==a and seen[1]==b and seen[2].surface.value==0
    assert site.programme==a
    se.evaluate(se.SOULTZ,hydraulics_model='v1.5.0')
    assert seen[-1].hydraulics_model=='v1.5.0' and seen[-1].surface is None
    assert not seen[-1].joints and not seen[-1].tools
    with pytest.raises(ValueError,match='legacy programme rejects'):
        HydraulicProgramme.reference_programme('v1.5.0',joints=True)
    assert se.SOULTZ.programme is None


@pytest.mark.parametrize('value',[
    dict(segments=[dict(length=100.,bore_diameter=.08,outer_diameter=.10,conductivity=float('nan'))]),
    dict(segments=[dict(length=True,bore_diameter=.08,outer_diameter=.10)]),
    dict(hole=[dict(md_top=0.,md_bottom=100.,r_wall=float('inf'))]),
    dict(hole=[dict(md_top=0.,md_bottom=100.,r_wall=.10,layers=[[.10,.12,-1.]])]),
    dict(joints='false'),
])
def test_bad_numeric_or_boolean_programme_inputs_fail_before_solving(value):
    with pytest.raises(ValueError):
        programme_from_dict(value)


def test_unknown_nested_key_names_the_file_and_key(tmp_path):
    path=tmp_path/'site.toml'
    path.write_text(MINIMAL+SEGMENTS+'\n[programme.surface]\ncase = 5\ntypo = 1\n')
    with pytest.raises(ValueError,match=r'site.toml.*programme.surface.typo'):
        load_site(path)


@pytest.mark.parametrize('depth',[500.,1500.,5000.])
def test_reference_hole_ends_cleanly_inside_or_below_casings(depth):
    g=HydraulicProgramme.reference_programme().geometry(depth,wg.CONVENTIONAL)
    assert all(0<=h.md_top<h.md_bottom<=depth for h in g.hole)
    assert g.hole[-1].md_bottom==depth
