"""Checks for shallow-string geometry and descriptive pressure reductions."""
import importlib.util
import csv
import json
from pathlib import Path
import sys

import pytest

from borethm import well_geometry as wg


HERE = Path(__file__).resolve().parents[1]/'validation/model-development/entry-9'


def module(name):
    sys.path.insert(0,str(HERE))
    try:
        spec = importlib.util.spec_from_file_location('diagnosis_'+name,HERE/(name+'.py'))
        result = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(result)
        return result
    finally:
        sys.path.remove(str(HERE))


def test_shallow_string_retains_bottom_components_in_order():
    diagnose = module('diagnose')
    pipe = wg.PipeType('pipe',(wg.Layer(.04,.05,wg.K_STEEL),))
    collar = wg.PipeType('collar',(wg.Layer(.03,.07,wg.K_STEEL),))
    tool = wg.PipeType('tool',(wg.Layer(.02,.08,wg.K_STEEL),))
    full = wg.WellGeometry([wg.StringSegment(100.,pipe),wg.StringSegment(20.,collar),
                           wg.StringSegment(10.,tool)],[wg.open_hole(0,130.,.4)])
    cut = diagnose.trim_geometry(full,15.,wg)
    assert cut.md_bit==pytest.approx(15.)
    assert [(s.pipe.name,s.length) for s in cut.string]==[('collar',5.),('tool',10.)]
    assert cut.hole[-1].md_bottom==pytest.approx(15.,abs=2e-6)
    with pytest.raises(ValueError):diagnose.trim_geometry(full,140.,wg)


def observation(depth,pressure,variant='inlet_return',q=600.):
    return dict(well='16B',role='primary',assembly='12',variant=variant,
        excursion='1',window_id=str(depth)+variant+str(q),bit_depth_ft=depth,flow_gpm=q,
        measured_spp_psi=pressure,modelled_spp_psi=pressure/2)


def test_slopes_use_depth_stages_and_keep_temperature_limits_separate():
    analyse = module('analyse')
    rows = [observation(1000.,150.) for _ in range(20)]
    rows += [observation(2000.,250.),observation(3000.,350.)]
    rows += [observation(d,p,'measured_high') for d,p in [(1000.,100.),(2000.,200.),(3000.,300.)]]
    slopes,_,_ = analyse.slopes(rows)
    assert len(slopes)==2
    assert all(s['stages']==3 for s in slopes)
    assert all(s['measured_slope']==pytest.approx(100.) for s in slopes)
    assert all(s['modelled_slope']==pytest.approx(50.) for s in slopes)
    assert analyse.slopes(rows[:20])[0]==[]


def test_fixed_depth_flow_fit_preserves_quadratic_coefficient():
    analyse = module('analyse')
    rows = [observation(2000.,150.+2*(q/100)**2,q=q) for q in [300.,400.,500.]]
    fits = analyse.flow_steps(rows)
    assert len(fits)==1
    assert fits[0]['measured_q2_slope']==pytest.approx(2.)
    assert fits[0]['measured_q2_intercept']==pytest.approx(150.)
    rows[-1]['bit_depth_ft']+=6.
    assert analyse.flow_steps(rows)==[]


def test_16a_temperature_bracket_preserves_recorded_nominal_mass_flow():
    root=HERE.parents[2]
    samples={s['id']:s for s in json.loads(
        (root/'validation/forge16b/s2/plan.json').read_text(encoding='utf-8'))['samples']}
    with (HERE/'results/windows.csv').open(encoding='utf-8',newline='') as stream:
        rows=[r for r in csv.DictReader(stream) if r['well']=='16A' and r['status']=='ok']
    assert rows
    for row in rows:
        density=samples[row['input_sample_id']]['density_ppg']*119.8264273
        expected=float(row['flow_gpm'])*0.003785411784/60*density
        # The package's gpm conversion is rounded; one part per million
        # checks the physical conversion without requiring extra digits.
        assert float(row['mass_rate_kg_s'])==pytest.approx(expected,rel=1e-6)
        assert float(row['mass_conversion_temperature_C'])==20.
    by_window={}
    for row in rows:by_window.setdefault(row['window_id'],[]).append(row)
    assert all({r['variant'] for r in pair}=={'measured_low','measured_high'}
               and len({r['mass_rate_kg_s'] for r in pair})==1 for pair in by_window.values())
    assert all(len({r['surface_psi'] for r in pair})==1 for pair in by_window.values())
