"""Geometry and paired reductions for the target-free 58-32 budget."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'validation/forge58-32/pressure-test/predict_budget.py'
spec = importlib.util.spec_from_file_location('forge58_budget', SOURCE)
budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget)


@pytest.mark.parametrize('depth,ordinary,hwdp', [(552.4, 0., 244.82), (1884., 1304.42, 272.)])
def test_bottom_assembly_and_unfilled_bit(depth, ordinary, hwdp):
    settings = json.loads((SOURCE.parent/'protocol.json').read_text())
    components = budget.read(SOURCE.parent/'inputs/components.csv')
    assert components[0]['reported_ID_in'] == ''
    for original in (True, False):
        g = budget.geometry({'bit_depth_ft':depth}, components, settings,
            settings['scenarios']['primary'], budget.wg.Survey.vertical(), original)
        assert g.md_bit/budget.FT == pytest.approx(depth)
        assert sum(s.length/budget.FT for s in g.string if s.pipe.name=='ordinary-pipe') == pytest.approx(ordinary)
        assert sum(s.length/budget.FT for s in g.string if s.pipe.name=='BHA-17-HWDP') == pytest.approx(hwdp)
        assert not any(s.pipe.name.startswith('BHA-01-') for s in g.string)
        assert (g.string[0].pipe.hydraulic_joint is None) == original
        assert np.isfinite(g.at(np.linspace(0., g.md_bit, 20))['A_ann']).all()


def test_event_budget_uses_identical_successful_windows():
    variants = ('original','working_entry10','secondary_entry8')
    samples = [dict(window_id=w,event_id='event') for w in ('a','b','c')]
    rows = []
    for variant in variants:
        for i, window in enumerate(('a','b','c'), 1):
            row = dict(event_id='event', window_id=window, variant=variant,
                success=not (variant=='original' and window=='c'), spp_psi=21.*i)
            row.update({part:float((j+1)*i) for j,part in enumerate(budget.PARTS)})
            rows.append(row)
    summaries, _ = budget.aggregate(rows, [], samples, variants)
    assert len(summaries) == 3
    for row in summaries:
        assert row['planned_windows'] == 3
        assert row['paired_windows'] == 2
        assert row['paired_ids'] == 'a;b'
        assert row['spp_psi'] == 31.5
        assert row['median_spp_psi'] == 31.5
        assert row['sum_residual_psi'] == 0.


def test_protocol_guard_allows_only_access_status():
    settings = json.loads((SOURCE.parent/'protocol.json').read_text())
    expected = json.loads((SOURCE.parent/'inputs/manifest.json').read_text())['source_sha256']['protocol.json']
    assert budget.frozen_protocol_sha(settings) == expected
    settings['window_pressure_targets_read'] = True
    settings['window_pressure_target_access_date'] = '2026-11-01'
    assert budget.frozen_protocol_sha(settings) == expected
    settings['common']['pv_ref_T_C'] = 48.9
    assert budget.frozen_protocol_sha(settings) != expected
