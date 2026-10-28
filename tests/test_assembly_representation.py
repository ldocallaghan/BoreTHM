"""Equipment identities separate thermal assumptions from hydraulic passages."""
import json
from pathlib import Path

import numpy as np
import pytest

from borethm import hydraulic_losses as hl, well_geometry as wg
from borethm.studies import pressure_comparison as study, validate_forge16a as a

ROOT=Path(__file__).resolve().parents[1]


def test_original_blanks_and_the_real_small_sensor_bore_are_distinct():
    rows=study.assembly_audit()
    bits=[r for r in rows if r['well']=='16A' and r['bit']]
    assert len(bits)==9 and all(r['reported_id_in'] is None for r in bits)
    assert all(r['hydraulic_id_in'] is None and r['thermal_id_in'] is None for r in bits)
    puk=next(r for r in rows if (r['well'],r['bha'],r['item'])==('16A','18',3))
    assert puk['reported_id_in']==puk['hydraulic_id_in']==1.25


def test_motor_placeholder_removes_passage_and_assumed_boundary_losses_only():
    def pipe(name,inside,outside):
        return wg.PipeType(name,(wg.Layer(inside/2,outside/2,wg.K_STEEL),))
    geometry=wg.WellGeometry([
        wg.StringSegment(10.,pipe('collar',.08,.16)),
        wg.StringSegment(10.,pipe('motor thermal assumption',.06,.17),tool_loss=study.unknown_motor('test record')),
        wg.StringSegment(10.,pipe('collar',.08,.16))],
        [wg.open_hole(0.,30.,.25)],wg.Survey(np.array([0.,30.]),np.array([0.,30.])))
    model=hl.LossModel(geometry)
    assert model.replaced.tolist()==[False,True,False]
    assert all(annulus for annulus,*_ in model.boundaries)
    at=model.gradients(np.array([15.]),np.array([40.]),np.array([1e7]),20.,blend=False)
    assert at['body'][0]==at['tool'][0]==at['total'][0]==0.
    assert 'internal_tool_loss_unknown' in at['flags']
    annulus=model.gradients(np.array([15.]),np.array([40.]),np.array([1e7]),20.,annulus=True,blend=False)
    assert annulus['body'][0]>0
    with pytest.raises(ValueError,match='zero reference'):
        hl.ReferenceToolLoss(1.,1.,1000.,unresolved=True)


def test_corrected_motor_and_nozzle_boundary_preserve_depth_and_real_sub():
    plan=json.loads((ROOT/'validation/forge16b/s2/plan.json').read_text())
    legacy=a.geometry('18',6500.,plan['components_a'])
    geometry=study.serial_development_geometry(dict(well='16A',run='18'),plan['components_a'],legacy,'NC50')
    assert geometry.md_bit==pytest.approx(legacy.md_bit,abs=1e-9)
    motor=next(s for s in geometry.string if s.tool_loss is not None)
    assert 2*motor.pipe.r_bore/study.INCH==3.25
    assert motor.tool_loss.unresolved and motor.tool_loss.dp_ref==0
    assert not any('drill bit' in s.pipe.name.lower() for s in geometry.string)
    assert any(2*s.pipe.r_bore/study.INCH==1.25 and 'PUK' in s.pipe.name for s in geometry.string)


@pytest.mark.parametrize('run,item',[('23',6),('38',3),('39',3)])
def test_unknown_instrument_bores_cannot_be_filled_silently(run,item):
    plan=json.loads((ROOT/'validation/forge16b/s2/plan.json').read_text())
    legacy=a.geometry(run,10000.,plan['components_a'])
    with pytest.raises(ValueError,match=f'item {item}'):
        study.serial_development_geometry(dict(well='16A',run=run),plan['components_a'],legacy,'NC50')


@pytest.mark.parametrize('run',['17','18','19','20'])
def test_trial_motor_is_separate_and_partial_insulated_layout_survives(run):
    from borethm.studies import validate_forge16b as b
    trial={'17':'BHA10','18':'BHA11','19':'BHA12','20':'BHA13'}[run]
    legacy=b.geometry(trial,sum(b.DEPTHS[trial])/2,4.9237482416889895)
    result=study.serial_development_geometry(dict(well='16B',run=run),{},legacy,'EIS')
    assert result.md_bit==pytest.approx(legacy.md_bit,abs=1e-9)
    assert [s.pipe.layers for s in result.string[:-2]]==[s.pipe.layers for s in legacy.string[:-1]]
    assert [s.length for s in result.string[:-2]]==[s.length for s in legacy.string[:-1]]
    assert result.string[-1].tool_loss.unresolved
    assert result.string[-1].length==35*study.FT
    assert 2*result.string[-1].pipe.r_bore/study.INCH==3.25
