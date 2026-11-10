"""Operations: the stated operating choices, their checks, site files and
the functions that use them, on synthetic inputs without Model 1 solves."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import re
import subprocess
import sys

import numpy as np
import pytest

import borethm
from borethm import drilling_cycle as dc
from borethm import operations as op
from borethm import site_evaluation as se
from borethm import well_geometry as wg
from borethm.operations import Operations, operations_from_dict, operations_toml, validate_operations
from borethm.site_files import load_site, site_text, template_text

SOURCES = {name: ('assumed', 'test value') for name in op.UNITS}


def stated(**fields):
    """Operations with a source for each stated field, so validation warns only about values."""
    return Operations(**fields, sources={k: SOURCES[k] for k in fields})


# ------------------------------------------------------------ the dataclass
def test_empty_operations_state_nothing_and_keep_the_forge_timings():
    ops = Operations()
    assert ops.stated() == {}
    base = dc.forge_timings()
    assert ops.timings(base) is base
    assert not ops.fixed_connection and not ops.fixed_staging
    assert validate_operations(ops) == []


def test_public_interface_exports_operations():
    assert borethm.Operations is Operations
    assert borethm.validate_operations is validate_operations
    assert 'operations' in borethm.evaluate.__code__.co_varnames


def test_values_are_normalised_and_frozen():
    ops = Operations(mass_flow_kg_s=30, mass_flows_kg_s=[5, 10], rig_pumps=2, coating_ratings_C={'conventional': 180},
                     sources={'mass_flow_kg_s': ['assumed', 'pump sheet']})
    assert ops.mass_flow_kg_s == 30.0 and isinstance(ops.mass_flow_kg_s, float)
    assert ops.mass_flows_kg_s == (5.0, 10.0)
    assert ops.coating_ratings_C == {'conventional': 180.0}
    assert ops.sources == {'mass_flow_kg_s': ('assumed', 'pump sheet')}
    with pytest.raises(AttributeError):
        ops.mass_flow_kg_s = 20.0


@pytest.mark.parametrize('fields,message', [
    (dict(mass_flow_kg_s='30'), 'mass_flow_kg_s: expected a finite number'),
    (dict(volume_flow_L_s=float('nan')), 'volume_flow_L_s: expected a finite number'),
    (dict(tool_limit_C=True), 'tool_limit_C: expected a finite number'),
    (dict(rig_pumps=2.5), 'rig_pumps: expected a whole number'),
    (dict(mass_flows_kg_s=30), 'mass_flows_kg_s: expected a sequence'),
    (dict(coating_ratings_C=[204.0]), 'coating_ratings_C: expected a mapping'),
    (dict(sources={'mass_flow_kg_s': 'assumed'}), 'sources.mass_flow_kg_s: expected a'),
])
def test_wrong_types_are_rejected(fields, message):
    with pytest.raises(ValueError, match=message):
        Operations(**fields)


def test_pipes_must_be_pipe_types():
    with pytest.raises(TypeError, match='pipes'):
        Operations(pipes=('conventional',))
    with pytest.raises(TypeError, match='pipes'):
        Operations(pipes=wg.CONVENTIONAL)


def test_stated_timings_replace_only_their_own_values():
    base = dc.forge_timings()
    t = Operations(precirculation_min=2.0, connection_p90_min=12.0, stage_minutes=30.0).timings(base)
    assert (t.fresh_circ_p10_min, t.connection_p90_min, t.stage_minutes) == (2.0, 12.0, 30.0)
    assert t.connection_median_min == base.connection_median_min
    assert t.stage_spacing_ft == base.stage_spacing_ft
    assert Operations(connection_p90_min=12.0).fixed_connection
    assert Operations(stage_spacing_m=100.0).fixed_staging


# ------------------------------------------------------------ validation
@pytest.mark.parametrize('fields,field,message', [
    (dict(mass_flow_kg_s=0.5), 'mass_flow_kg_s', '0.5 is outside 1 to 300 kg/s'),
    (dict(volume_flow_L_s=400.0), 'volume_flow_L_s', '400 is outside 1 to 300 L/s at surface'),
    (dict(pump_pressure_limit_Pa=7500.0), 'pump_pressure_limit_Pa', '7500 is outside'),
    (dict(tool_limit_C=473.15), 'tool_limit_C', '473.15 is outside'),
    (dict(connection_p90_min=0.0), 'connection_p90_min', '0 is outside'),
    (dict(drilling_fluid_kg_m3=1.1), 'drilling_fluid_kg_m3', '1.1 is outside'),
    (dict(rig_pumps=0), 'rig_pumps', '0 is outside'),
    (dict(mass_flows_kg_s=(10.0, 5.0)), 'mass_flows_kg_s', 'the flows must rise strictly'),
    (dict(volume_flows_L_s=()), 'volume_flows_L_s', 'the grid is empty'),
    (dict(pipes=()), 'pipes', 'the list is empty'),
    (dict(mass_flow_kg_s=30.0, volume_flow_L_s=30.0), 'operations', 'give at most one of mass_flow_kg_s'),
    (dict(mass_flow_kg_s=30.0, mass_flows_kg_s=(10.0, 20.0)), 'operations', 'give at most one of mass_flow_kg_s'),
    (dict(mass_flows_kg_s=(10.0, 20.0), volume_flows_L_s=(10.0, 20.0)), 'operations', 'give at most one'),
    (dict(trip_hours=10.0, trip_scale=2.0), 'operations', 'give at most one of trip_hours and trip_scale'),
    (dict(coating_ratings_C={'conventional': 20.0}), 'coating_ratings_C', "the rating for 'conventional', 20"),
    (dict(sources={'tool': ('assumed', 'x')}), 'sources', "'tool' is not an operations field"),
    (dict(sources={'mass_flow_kg_s': ('guessed', 'x')}), 'mass_flow_kg_s', "the basis 'guessed' is not one of"),
])
def test_invalid_values_are_error_records(fields, field, message):
    records = validate_operations(Operations(**fields))
    errors = [r for r in records if r['level'] == 'error']
    assert errors and errors[0]['field'] == field and message in errors[0]['message'], records


@pytest.mark.parametrize('fields,field,warning', [
    (dict(mass_flow_kg_s=150.0), 'mass_flow_kg_s', "150 kg/s is outside the evaluator's flow grid"),
    (dict(volume_flows_L_s=(2.0, 50.0)), 'volume_flows_L_s', "2 L/s at surface is outside the evaluator's flow grid"),
    (dict(pipes=(wg.DUAL_WALL,)), 'pipes', 'not a drill pipe on sale'),
    (dict(coating_ratings_C={'dual-wall': 180.0}), 'coating_ratings_C', 'not a candidate pipe'),
    (dict(tool_limit_C=320.0), 'tool_limit_C', 'above 300 C'),
    (dict(pump_pressure_limit_Pa=60e6), 'pump_pressure_limit_Pa', '7,475 psi rating'),
    (dict(connection_median_min=8.0, connection_p90_min=6.0), 'connection_median_min', 'longer than connection_p90_min'),
    (dict(stage_spacing_m=20.0), 'stage_spacing_m', 'shorter than a stand'),
    (dict(rop_m_h=25.0), 'rop_m_h', "above Model 3's 20 m/h ceiling"),
    (dict(drilling_fluid_kg_m3=995.0), 'drilling_fluid_kg_m3', 'the drilling fluid is water'),
    (dict(drilling_fluid_kg_m3=1200.0, trip_fluid_kg_m3=1100.0), 'trip_fluid_kg_m3', 'lighter than drilling_fluid_kg_m3'),
])
def test_questionable_values_are_warning_records(fields, field, warning):
    records = validate_operations(stated(**fields))
    assert all(r['level'] == 'warning' for r in records)
    assert any(r['field'] == field and warning in r['message'] for r in records), records


def test_a_stated_value_without_a_source_warns():
    record = dict(field='tool_limit_C', level='warning', message='no source is given')
    assert validate_operations(Operations(tool_limit_C=175.0)) == [record]
    assert validate_operations(Operations(tool_limit_C=175.0, sources={'tool_limit_C': ('assumed', '')})) == [record]
    assert validate_operations(stated(tool_limit_C=175.0)) == []


def test_validate_site_adds_operation_warnings_and_names_the_site():
    site = replace(se.find_site('newberry'), operations=Operations(tool_limit_C=175.0))
    assert se.validate_site(site)[-1] == 'operations.tool_limit_C: no source is given'
    assert se.validate_site(replace(site, operations=Operations())) == se.validate_site(
        se.find_site('newberry'))
    with pytest.raises(ValueError, match=r'^Newberry.*: operations.mass_flow_kg_s: 0.5 is outside'):
        se.validate_site(replace(site, operations=Operations(mass_flow_kg_s=0.5)))
    with pytest.raises(ValueError, match='operations must be Operations or None'):
        se.validate_site(replace(site, operations={'mass_flow_kg_s': 30.0}))


# ------------------------------------------------------------ evaluate's argument
def test_evaluate_rejects_operations_it_cannot_apply():
    site = se.find_site('newberry')
    with pytest.raises(TypeError, match='operations must be Operations or None'):
        se.evaluate(site, operations={'mass_flow_kg_s': 30.0})
    with pytest.raises(ValueError, match="circulation='v1.3.4' only"):
        se.evaluate(site, circulation='v1.3.3', operations=Operations(mass_flow_kg_s=30.0))
    with pytest.raises(ValueError, match="circulation='v1.3.4' only"):
        se.evaluate(replace(site, operations=Operations(mass_flow_kg_s=30.0)), v10=True)
    custom = borethm.HydraulicProgramme(reference=None, segments=(wg.StringSegment(site.target(), wg.CONVENTIONAL),))
    with pytest.raises(ValueError, match='custom segments'):
        se.evaluate(site, programme=custom, operations=Operations(pipes=(wg.CONVENTIONAL,)))


# ------------------------------------------------------------ site files
EXAMPLE = '''
[operations]
pipes = ["TK-Drakon coated", "conventional"]
mass_flow_kg_s = 30.0
tool_limit_C = 175.0
pump_pressure_limit_Pa = 45.0e6
rig_pumps = 2
trip_hours = 20.0
stage_spacing_m = 100.0
stage_minutes = 20.0
drilling_fluid_kg_m3 = 1050.0

[operations.coating_ratings_C]
"TK-Drakon coated" = 190.0

[operations.sources]
tool_limit_C = ["assumed", "high-temperature MWD rating"]
mass_flow_kg_s = ["assumed", "two pumps at 90 strokes/min"]
'''


def write(tmp_path, text, name='site.toml'):
    path = tmp_path / name
    path.write_text(text, encoding='utf-8')
    return path


def test_site_file_operations_table_is_parsed(tmp_path):
    site = load_site(write(tmp_path, template_text() + EXAMPLE))
    ops = site.operations
    assert ops.pipes == (wg.TK_DRAKON, wg.CONVENTIONAL)
    assert (ops.mass_flow_kg_s, ops.tool_limit_C, ops.pump_pressure_limit_Pa, ops.rig_pumps) == (30.0, 175.0, 45e6, 2)
    assert (ops.trip_hours, ops.stage_spacing_m, ops.stage_minutes) == (20.0, 100.0, 20.0)
    assert ops.drilling_fluid_kg_m3 == 1050.0
    assert ops.coating_ratings_C == {'TK-Drakon coated': 190.0}
    assert ops.sources['tool_limit_C'] == ('assumed', 'high-temperature MWD rating')
    warnings = se.validate_site(site)
    assert sum(w.startswith('operations') for w in warnings) == 8   # stated values without a source
    assert load_site(write(tmp_path, template_text(), 'plain.toml')).operations is None


@pytest.mark.parametrize('line,message', [
    ('tool_limit = 175.0', 'operations: tool_limit: unknown key'),
    ('mass_flow_kg_s = "30"', 'operations: mass_flow_kg_s: expected a number'),
    ('volume_flow_L_s = true', 'operations: volume_flow_L_s: expected a number'),
    ('flow = 30.0', 'operations: flow: unknown key'),
    ('rig_pumps = 2.0', 'operations: rig_pumps: expected a whole number'),
    ('pipes = ["steel"]', "operations: pipes: unknown pipe 'steel'"),
    ('pipes = "conventional"', 'operations: pipes: expected an array of pipe names'),
    ('mass_flows_kg_s = [5, "10"]', r'operations: mass_flows_kg_s\[1\]: expected a number'),
    ('coating_ratings_C = 204.0', 'operations: coating_ratings_C: expected a table'),
    ('sources = { mass_flow_kg_s = ["assumed"] }', 'operations: sources.mass_flow_kg_s: expected \\[basis, source\\]'),
])
def test_site_file_operations_are_strict(tmp_path, line, message):
    path = write(tmp_path, template_text() + '\n[operations]\n' + line + '\n')
    with pytest.raises(ValueError, match=message) as error:
        load_site(path)
    assert str(path) in str(error.value)


def test_operations_must_be_a_table(tmp_path):
    text = 'operations = 3\n' + template_text()
    with pytest.raises(ValueError, match='operations: expected a table'):
        load_site(write(tmp_path, text))


def test_operations_round_trip_through_toml(tmp_path):
    ops = Operations(pipes=(wg.INTERNALLY_COATED,), mass_flows_kg_s=(10.0, 20.0, 40.0), tool_limit_C=180.0,
                     coating_ratings_C={'internally coated': 150.0}, rig_pumps=4,
                     min_annular_velocity_m_s=1.0, precirculation_min=5.0, connection_median_min=3.0,
                     connection_p90_min=8.0, trip_scale=1.5, rop_m_h=6.5, trip_fluid_kg_m3=1150.0,
                     sources={'tool_limit_C': ('assumed', 'rating "sheet"')})
    site = load_site(write(tmp_path, template_text() + '\n' + operations_toml(ops)))
    assert site.operations == ops
    assert load_site(write(tmp_path, template_text() + '\n' + operations_toml(Operations()), 'b.toml')).operations == Operations()


@pytest.mark.parametrize('key', ['soultz', 'larderello', 'united-downs', 'pannonian', 'newberry'])
def test_starter_files_carry_the_operations_table_commented_out(tmp_path, key):
    from borethm.programme import TEMPLATE as PROGRAMME
    text = site_text(key)
    assert text.endswith(op.TEMPLATE + PROGRAMME)
    path = tmp_path / 'mysite.toml'
    command = subprocess.run([sys.executable, '-m', 'borethm.site_files', str(path), '--from', key],
                             capture_output=True, text=True, timeout=60)
    assert command.returncode == 0, command.stderr
    assert load_site(path).operations is None
    # every key in the commented table is a valid example once uncommented
    lines = op.TEMPLATE.splitlines()
    keys = [line[2:] for line in lines if line.startswith('# ') and ('=' in line or line.startswith('# ['))]
    keys = [line for line in keys if not line.startswith(('volume_flow_L_s', 'mass_flows_kg_s', 'volume_flows_L_s', 'trip_scale'))]
    path.write_text(path.read_text(encoding='utf-8') + '\n' + '\n'.join(keys) + '\n', encoding='utf-8')
    ops = load_site(path).operations
    assert ops.mass_flow_kg_s == 30.0 and ops.tool_limit_C == 200.0 and ops.trip_hours == 17.5
    assert ops.coating_ratings_C == se.COATING_RATINGS
    assert ops.pipes == se.SITE_PIPES
    assert ops.pump_pressure_limit_Pa == se.m1.PUMP_LIMIT and ops.rig_pumps == se.RIG_PUMPS
    assert ops.min_annular_velocity_m_s == se.m1.HOLE_CLEANING_V
    t = dc.forge_timings()
    assert (ops.precirculation_min, ops.connection_median_min, ops.connection_p90_min) == pytest.approx(
        (t.fresh_circ_p10_min, t.connection_median_min, t.connection_p90_min), abs=0.005)
    assert (ops.stage_spacing_m, ops.stage_minutes) == pytest.approx(
        (t.stage_spacing_ft * dc.FT, t.stage_minutes), abs=0.005)


def test_template_documents_the_default_flow_grid_and_pipes():
    assert '# mass_flows_kg_s = [' + ', '.join(f'{f:g}' for f in se.SITE_FLOWS) + ']' in op.TEMPLATE
    assert '# volume_flows_L_s = [' + ', '.join(f'{f:g}' for f in se.SITE_FLOWS) + ']' in op.TEMPLATE
    assert '# pipes = [' + ', '.join(f'"{p.name}"' for p in se.SITE_PIPES) + ']' in op.TEMPLATE
    assert set(op.PIPES) >= {p.name for p in se.SITE_PIPES}


def test_check_command_reports_operation_warnings(tmp_path):
    path = write(tmp_path, template_text() + EXAMPLE)
    command = subprocess.run([sys.executable, '-m', 'borethm.site_evaluation', '--site-file', str(path),
                              '--check'], capture_output=True, text=True, timeout=60)
    assert command.returncode == 0, command.stderr
    assert 'warning: operations.pipes: no source is given' in command.stdout
    assert 'inputs valid' in command.stdout


# ------------------------------------------------------------ circulation choice
@pytest.fixture
def fake_circulation(monkeypatch):
    """circulate replaced by a table: the bit temperature falls with flow and
    with better insulation, the standpipe pressure rises with flow."""
    calls = []
    insulation = {wg.TK_DRAKON.name: 0.0, wg.INTERNALLY_COATED.name: 20.0, wg.EXTERNALLY_COATED.name: 30.0,
                  wg.CONVENTIONAL.name: 40.0}

    def circulate(site, z, geotherm, pipe, m_dot, exposure=None, film_mult=1.0, P_surface=None,
                  fluid=None, retry=True, programme=None):
        calls.append((pipe.name, m_dot))
        hyd = dict(spp=1e6 * m_dot, v_ann_min=0.04 * m_dot, over_pump_limit=1e6 * m_dot > se.m1.PUMP_LIMIT,
                   cleans_hole=0.04 * m_dot >= se.m1.HOLE_CLEANING_V)
        se._stated_limits(site, hyd)
        return dict(success=True, T_bottom_delivered=300.0 - 4.0 * m_dot + insulation[pipe.name], hyd=hyd,
                    m_dot=m_dot)

    monkeypatch.setattr(se, 'circulate', circulate)
    return calls


def choose(ops, pipes=se.SITE_PIPES):
    site = replace(se.find_site('newberry'), operations=ops)
    return se.choose_circulation(site, 3000.0, None, pipes=pipes)


def test_default_search_takes_the_lowest_flow_that_survives_and_cleans(fake_circulation):
    c = choose(Operations())
    assert (c['pipe'], c['m_dot'], c['conflict']) == (wg.TK_DRAKON, 35, None)   # 160 C, 1.4 m/s


def test_tool_limit_sets_the_survival_flow(fake_circulation):
    assert choose(Operations(tool_limit_C=175.0))['m_dot'] == 35
    assert choose(Operations(tool_limit_C=150.0))['m_dot'] == 40
    c = choose(Operations(tool_limit_C=60.0))
    assert c['conflict'] == 'no pipe keeps the bit below 60 C within the pump limit'


def test_stated_flow_grid_is_searched(fake_circulation):
    c = choose(Operations(mass_flows_kg_s=(33.0, 44.0)))
    assert c['m_dot'] == 33.0
    assert [m for _, m in fake_circulation] == [33.0]


def test_stated_pipes_are_tried_in_order(fake_circulation):
    c = choose(Operations(pipes=(wg.CONVENTIONAL, wg.TK_DRAKON), tool_limit_C=150.0))
    assert c['pipe'] == wg.CONVENTIONAL and c['m_dot'] == 50
    assert {name for name, _ in fake_circulation} == {wg.CONVENTIONAL.name}


def test_hole_cleaning_velocity_sets_the_cleaning_flow(fake_circulation):
    assert choose(Operations(min_annular_velocity_m_s=2.0))['m_dot'] == 50


def test_pump_limit_ends_the_search(fake_circulation):
    c = choose(Operations(pump_pressure_limit_Pa=30e6))
    assert c['tried'][0]['pump_limited_at'] == 35
    assert 'pump limit' in c['conflict']


def test_a_stated_flow_is_used_as_given_and_its_failures_reported(fake_circulation):
    c = choose(Operations(mass_flow_kg_s=20.0))
    assert c['m_dot'] == 20.0 and c['pipe'] == wg.TK_DRAKON
    assert c['conflict'] == ('at the stated flow of 20 kg/s, the bit reaches 220 C, at or above the 200 C '
                             'tool limit; the annular velocity is below the hole-cleaning velocity')
    assert all(m == 20.0 for _, m in fake_circulation)
    c = choose(Operations(mass_flow_kg_s=60.0))
    assert c['m_dot'] == 60.0 and c['run']['hyd']['over_pump_limit']
    assert c['conflict'] == 'at the stated flow of 60 kg/s, the standpipe pressure exceeds the pump limit'
    assert choose(Operations(mass_flow_kg_s=40.0))['conflict'] is None


def test_a_stated_flow_takes_a_pipe_that_passes(fake_circulation):
    c = choose(Operations(mass_flow_kg_s=40.0, pipes=(wg.CONVENTIONAL, wg.TK_DRAKON), tool_limit_C=150.0))
    assert c['pipe'] == wg.TK_DRAKON and c['conflict'] is None


def test_stated_limits_change_only_their_flags():
    hyd = dict(spp=40e6, v_ann_min=1.0, over_pump_limit=False, cleans_hole=False)
    se._stated_limits(SimpleNamespace(operations=None), hyd)
    assert hyd == dict(spp=40e6, v_ann_min=1.0, over_pump_limit=False, cleans_hole=False)
    se._stated_limits(SimpleNamespace(operations=Operations(pump_pressure_limit_Pa=35e6,
                                                            min_annular_velocity_m_s=0.9)), hyd)
    assert hyd['over_pump_limit'] is True and hyd['cleans_hole'] is True


def test_rig_capacity_scales_with_the_stated_pumps():
    assert se.rig_capacity_gpm(20e6, 2) == pytest.approx(se.rig_capacity_gpm(20e6) * 2 / 3)


def test_trip_hours_follow_the_stated_value_or_scale():
    t = dc.forge_timings()
    site = SimpleNamespace(operations=None)
    assert se._trip_hours(site, 3000.0, t) == dc.trip_hours(3000.0, t)
    site.operations = Operations(trip_scale=2.0)
    assert se._trip_hours(site, 3000.0, t) == pytest.approx(2 * dc.trip_hours(3000.0, t))
    site.operations = Operations(trip_hours=9.0)
    assert se._trip_hours(site, 3000.0, t) == 9.0
    assert se._tool_limit(SimpleNamespace(operations=Operations(tool_limit_C=175.0))) == 175.0
    assert se._tool_limit(SimpleNamespace(operations=None)) == se.C.BHA_SURVIVAL_TEMP


# ------------------------------------------------------------ fluids and rate of penetration
@pytest.fixture
def fake_passes(monkeypatch):
    """drilling_fluid's passes with the window bounds fixed: drilling 1080 and
    trip 1120 kg/m3; each pass records the fluids it was given."""
    seen = []

    def passes(site, thermal, budget, fluid, rop=None, light=False):
        seen.append((fluid, rop))
        return dict(circ=dict(rop=12.0 / 3600.0), drill=dict(ROP=12.0 / 3600.0), m1=dict(success=True),
                    z=3000.0, rop_passes=[])

    monkeypatch.setattr(se, '_evaluate_v12', passes)
    monkeypatch.setattr(se, 'site_cycle', lambda site, o: dict(drill_SG=1.0))
    monkeypatch.setattr(se, 'common_windows', lambda site, o: dict(drilling_fluid=dict(lo=1080.0),
                                                                   trip_fluid=dict(lo=1120.0)))
    monkeypatch.setattr(se, 'tool_gates', lambda site, o: dict(tool='PASS'))
    monkeypatch.setattr(se, 'ecd_sg', lambda run, z: 0.0)
    monkeypatch.setattr(se.fluids, 'water', lambda: SimpleNamespace(rho_surface=998.2))
    return seen


def iterate(ops):
    site = replace(se.find_site('newberry'), operations=ops, coupled=False)
    return se.drilling_fluid(site, corrected=True)


def test_fluid_iteration_takes_the_window_bounds_by_default(fake_passes):
    fluid, passes, converged, _ = iterate(Operations())
    assert converged and fluid.rho_surface == 1080.0
    assert passes[-1]['trip_simulated_rho_surface'] == 1120.0
    assert fake_passes[0][0] is None


def test_stated_fluids_are_used_from_the_first_pass(fake_passes):
    fluid, passes, converged, _ = iterate(Operations(drilling_fluid_kg_m3=1050.0, trip_fluid_kg_m3=1100.0))
    assert converged and len(passes) == 1
    assert fake_passes[0][0].rho_surface == 1050.0
    assert passes[-1]['simulated_rho_surface'] == 1050.0
    assert passes[-1]['trip_simulated_rho_surface'] == 1100.0


def test_a_stated_drilling_fluid_keeps_the_trip_rule(fake_passes):
    fluid, passes, converged, _ = iterate(Operations(drilling_fluid_kg_m3=1050.0))
    assert converged and fluid.rho_surface == 1050.0
    assert passes[-1]['trip_simulated_rho_surface'] == 1120.0


def test_a_stated_fluid_lighter_than_water_is_water(fake_passes):
    fluid, passes, converged, _ = iterate(Operations(drilling_fluid_kg_m3=995.0, trip_fluid_kg_m3=995.0))
    assert converged and fluid is None and fake_passes[0][0] is None
    assert passes[-1]['trip_simulated_rho_surface'] == 998.2


def test_stated_rate_of_penetration_ends_the_coupled_iteration(monkeypatch):
    seen = []

    def circulation(site, z, geotherm, exposure=None, **kwargs):
        seen.append(exposure)
        run = dict(T_bottom_delivered=150.0, old=dict(T_bottom_delivered=140.0), m_dot=30.0,
                   T_return_surface=60.0, Q_product=1e6, hyd=dict(spp=1e7), success=True)
        return dict(pipe=wg.TK_DRAKON, m_dot=30, run=run, conflict=None, tried=[])

    monkeypatch.setattr(se, 'choose_circulation', circulation)
    monkeypatch.setattr(se, 'water_column', lambda *args: (3e7, 0.0))
    monkeypatch.setattr(se, 'ecd_sg', lambda run, z: 0.0)
    monkeypatch.setattr(se, 'flow_gpm', lambda run: 500.0)
    site = replace(se.find_site('newberry'), coupled=True, operations=Operations(rop_m_h=4.5))
    out = se._evaluate_v12(site, budget=True, light=True)
    assert len(seen) == 1 and out['rop_passes'] == []
    assert out['circ']['rop'] * 3600 == pytest.approx(4.5)
    assert out['drill']['ROP'] * 3600 == pytest.approx(4.5)
    assert out['drill']['model_ROP'] != out['drill']['ROP']
    z = site.target()
    assert seen[0](z - 4.5) == pytest.approx(3600.0)    # the wall 4.5 m up was drilled an hour ago


# ------------------------------------------------------------ status and reading
def components(**changes):
    c = dict(solver=dict(ok=True, converged=True), tool=dict(ok=True, detail='PASS'),
             coating=dict(status='within rating', pipe='TK-Drakon coated'),
             hole_cleaning=dict(ok=True), pumps=dict(ok=True, within_rig=True),
             admissibility=dict(inadmissible=[]), stability=dict(verdict='GO', states={}),
             prescription=dict(drilling_fluid=dict(open=True, fluid=998.2, heavier_than_water=False),
                               trip_fluid=dict(open=True, fluid=998.2, heavier_than_water=False)))
    for key, value in changes.items():
        c[key] = {**c[key], **value}
    return c


WINDOWS = dict(drilling_fluid=dict(open=True, lo=1040.0, hi=1200.0),
               trip_fluid=dict(open=True, lo=1060.0, hi=float('inf')))


@pytest.fixture
def water(monkeypatch):
    monkeypatch.setattr(se.fluids, 'water', lambda: SimpleNamespace(rho_surface=998.2))


def test_status_is_unchanged_without_stated_values(water):
    for c in (components(), components(hole_cleaning=dict(ok=False)), components(pumps=dict(within_rig=False))):
        assert se.site_status(c) == se.site_status(c, windows=WINDOWS, operations=Operations())


def test_a_stated_fluid_outside_its_window_is_a_no_go(water):
    status = se.site_status(components(), windows=WINDOWS, operations=Operations(drilling_fluid_kg_m3=1250.0))
    assert status == dict(label='NO-GO', reasons=[
        'the stated drilling fluid, 1.250 SG at surface, is outside its common window, 1.040 SG to 1.200 SG'])
    status = se.site_status(components(), windows=WINDOWS, operations=Operations(trip_fluid_kg_m3=1000.0))
    assert status['reasons'] == [
        'the stated trip fluid, 1.000 SG at surface, is outside its common window, 1.060 SG to no upper bound']


def test_a_stated_fluid_inside_its_window_is_named_as_the_condition(water):
    status = se.site_status(components(), windows=WINDOWS,
                            operations=Operations(drilling_fluid_kg_m3=1100.0, trip_fluid_kg_m3=1100.0))
    assert status == dict(label='CONDITIONAL', reasons=[
        'the stated drilling fluid of 1.100 SG at surface, within its common window, 1.040 SG to 1.200 SG; '
        'the window needs a fluid heavier than water',
        'the stated trip fluid of 1.100 SG at surface, within its common window, 1.060 SG to no upper bound; '
        'the window needs a fluid heavier than water'])


def test_a_stated_fluid_where_water_would_do_says_so(water):
    windows = dict(drilling_fluid=dict(lo=998.2, hi=1163.0, open=True),
                   trip_fluid=dict(lo=998.2, hi=1221.0, open=True))
    status = se.site_status(components(), windows=windows, operations=Operations(drilling_fluid_kg_m3=1100.0))
    assert status == dict(label='CONDITIONAL', reasons=[
        'the stated drilling fluid of 1.100 SG at surface, within its common window, 0.998 SG to 1.163 SG; '
        'the window admits water, so the condition is the stated fluid heavier than water'])
    assert se.site_status(components(), windows=windows) == se.site_status(components())


def test_stated_cleaning_velocity_and_pumps_are_named(water):
    c = components(hole_cleaning=dict(ok=False), pumps=dict(within_rig=False))
    status = se.site_status(c, operations=Operations(min_annular_velocity_m_s=1.5, rig_pumps=2))
    assert status['reasons'] == ['more pump capacity than the stated 2 pumps',
                                 'hole cleaning below the stated 1.5 m/s annular velocity']


def test_reading_names_the_stated_values_behind_the_controlling_constraint():
    o = dict(site=SimpleNamespace(operations=Operations(tool_limit_C=175.0, rig_pumps=2)), fluid=None)
    assert se._stated_inputs(o, 'tool: 180 C at the bit while drilling') == (
        ' Stated operations used in this check: tool limit 175 C.')
    assert se._stated_inputs(o, 'more pump capacity than the stated 2 pumps') == (
        ' Stated operations used in this check: rig pumps 2 pumps.')
    assert se._stated_inputs(o, 'the standpipe pressure exceeds the pump limit') == ''
    o['site'].operations = Operations(mass_flow_kg_s=40.0, drilling_fluid_kg_m3=1100.0)
    assert se._stated_inputs(o, 'the stated drilling fluid, 1.100 SG at surface, is outside') == (
        ' Stated operations used in this check: drilling fluid 1100 kg/m3 at 20 C; mass flow 40 kg/s.')
    assert se._stated_inputs(dict(site=SimpleNamespace(operations=None)), 'tool: x') == ''


# ------------------------------------------------------------ window profile
def test_window_profile_keeps_each_depth_and_mechanism():
    rows = {('drilling', 'A', 3000.0): dict(lo=1100.0, lo_by='breakout width', hi=1300.0, hi_by=se.UPPER_MECHANISM),
            ('connection', 'A', 3000.0): dict(lo=1150.0, lo_by='pore pressure', hi=1250.0, hi_by=se.UPPER_MECHANISM),
            ('drilling', 'A', 2000.0): dict(lo=None, lo_by=None, hi=1280.0, hi_by=se.UPPER_MECHANISM),
            ('trip', 'A', 2000.0): dict(lo=1050.0, lo_by='breakout width', hi=1400.0, hi_by=se.UPPER_MECHANISM)}
    p = se._window_profile(rows, ['A'])
    assert p['depths_m'] == [3000.0, 2000.0]
    assert p['states']['drilling']['A']['hi_kg_m3'] == [1300.0, 1280.0]
    assert p['states']['drilling']['A']['lo_kg_m3'] == [1100.0, None]
    assert p['states']['fresh rock'] == {}
    d = p['drilling_fluid']
    assert d['lo_kg_m3'] == [1150.0, None]
    assert d['lo_by'][0] == dict(state='connection', case='A', mechanism='pore pressure')
    assert d['hi_kg_m3'] == [1250.0, 1280.0]
    assert d['width_kg_m3'] == [100.0, None]
    assert p['trip_fluid']['lo_kg_m3'] == [None, 1050.0]


def test_lower_mechanism_is_pore_pressure_where_it_binds():
    assert se._lower_mechanism(dict(Pp=30e6, window=dict(Pw_lo=30e6))) == 'pore pressure'
    assert se._lower_mechanism(dict(Pp=30e6, window=dict(Pw_lo=31e6))) == 'breakout width'


def test_common_windows_record_matches_the_windows(monkeypatch):
    """The profile at each window's binding depth gives the window's bound."""
    from borethm import fluids, pressure as pr
    geometry = wg.WellGeometry([wg.StringSegment(1100., wg.CONVENTIONAL)],
                               [wg.HoleInterval(0., 100., 0.15), wg.HoleInterval(100., 1100., 0.15)])
    site = replace(se.SOULTZ, target_depth=1100., geotherm=lambda z: np.asarray(z) * 0.04 + 20.)
    run = dict(geometry=geometry, fluid=None, z=np.linspace(0., 1100., 12), Tu=np.full(12, 20.))
    case = dict(label='scenario', Pp=0.0, window=dict(Pw_lo=1000. * pr.G * 1100., Pw_hi=2000. * pr.G * 1100.))
    cycle = dict(trip_h=10., cases=dict(drilling=[case], connection=[case]))
    out = dict(z=1100., drill={'ROP': 10. / 3600.}, m1=run, cycle=cycle, coverage_corrected=True)
    monkeypatch.setattr(fluids, '_water', lambda T, P: tuple(
        np.full(np.broadcast(np.asarray(T), np.asarray(P)).shape, value) for value in (1000., 4000., 0.001, 0.6)))
    monkeypatch.setattr(pr, 'column', lambda tvd, T, fluid=None, P_surface=0.:
                        P_surface + pr.G * np.asarray(tvd) * getattr(fluid, 'rho_surface', 1000.))
    monkeypatch.setattr(pr, 'annulus_friction', lambda *args: 0.)
    monkeypatch.setattr(se, 'trip_temperatures', lambda *args: (run['z'], run['Tu']))
    monkeypatch.setattr(se, '_ref_depth', lambda *args: 0.)
    monkeypatch.setattr(se, '_static_node', lambda *args: (1000., 10.))
    monkeypatch.setattr(se, '_bottom_conditions', lambda *args: dict(r_wall=0.15, r_string=0.05, Tu=20., h=100., bu_h=1.))
    monkeypatch.setattr(se.wall_thermal, 'run', lambda *args, **kwargs: SimpleNamespace(
        r=np.array([0.15, 0.25]), fields=[np.array([20., 20.])]))

    def inputs(site, depth, rock, T_wall=None, ecd_SG=0., **kwargs):
        pore = 1200. if depth < 400 else 0.
        lo = max(pore, 1000. + 0.3 * depth if T_wall == rock else 1100. + 0.1 * depth)
        hi = 1900. - 0.2 * depth
        cases = [dict(label='scenario', Pp=pore * pr.G * depth,
                      window=dict(Pw_lo=lo * pr.G * depth, Pw_hi=hi * pr.G * depth))]
        return cases[0], cases

    monkeypatch.setattr(se, 'stability_inputs', inputs)
    profile = {}
    windows = se.common_windows(site, out, record=profile)
    assert se._jsonable(windows) == se._jsonable(se.common_windows(site, out))
    for name in ('drilling_fluid', 'trip_fluid'):
        w, p = windows[name], profile[name]
        for side, pick in (('lo', max), ('hi', min)):
            values = [v for v in p[side + '_kg_m3'] if v is not None]
            assert pick(values) == pytest.approx(w[side])
            md = w[side + '_by']['md']
            if md is not None:
                i = profile['depths_m'].index(md)
                assert p[side + '_kg_m3'][i] == w[side]
                assert p[side + '_by'][i]['state'] == w[side + '_by']['state']
    assert set(profile['depths_m']) >= set(windows['depths'])
    mechanisms = {m for case in profile['states']['fresh rock'].values() for m in case['lo_mechanism']}
    assert mechanisms == {'breakout width', 'pore pressure'}


# ------------------------------------------------------------ public defaults
def test_operation_defaults_give_value_unit_rule_and_source():
    defaults = borethm.operation_defaults()
    assert set(defaults) == set(op.UNITS)
    for name, entry in defaults.items():
        assert set(entry) == {'value', 'unit', 'rule', 'source', 'restates_default'}, name
        assert entry['unit'] == op.UNITS[name]
        assert entry['rule'] and entry['source'], name
    t = dc.forge_timings()
    assert defaults['tool_limit_C']['value'] == se.C.BHA_SURVIVAL_TEMP
    assert defaults['pump_pressure_limit_Pa']['value'] == se.m1.PUMP_LIMIT
    assert defaults['rig_pumps']['value'] == se.RIG_PUMPS
    assert defaults['mass_flows_kg_s']['value'] is None and defaults['volume_flows_L_s']['value'] is None
    assert 'first fluid pass' in defaults['mass_flows_kg_s']['rule']
    assert defaults['pipes']['value'] == [p.name for p in se.SITE_PIPES]
    assert defaults['coating_ratings_C']['value'] == se.COATING_RATINGS
    assert defaults['connection_p90_min']['value'] == t.connection_p90_min
    assert defaults['stage_spacing_m']['value'] == t.stage_spacing_ft * dc.FT
    for searched in ('mass_flow_kg_s', 'volume_flow_L_s', 'rop_m_h', 'drilling_fluid_kg_m3', 'trip_fluid_kg_m3'):
        assert defaults[searched]['value'] is None
    assert defaults['trip_hours']['value'] is None


# A sample value for each field, to build an Operations stating it alone.
SAMPLES = dict(pipes=(wg.TK_DRAKON,), mass_flow_kg_s=30.0, volume_flow_L_s=30.0, mass_flows_kg_s=(20.0, 30.0),
               volume_flows_L_s=(20.0, 30.0), tool_limit_C=200.0, coating_ratings_C={'TK-Drakon coated': 204.0},
               pump_pressure_limit_Pa=51.7e6, rig_pumps=3, min_annular_velocity_m_s=1.245,
               precirculation_min=0.33, connection_median_min=2.83, connection_p90_min=6.33, trip_hours=17.0,
               trip_scale=1.0, stage_spacing_m=144.9, stage_minutes=15.51, rop_m_h=5.0,
               drilling_fluid_kg_m3=1050.0, trip_fluid_kg_m3=1050.0)
# The evaluator iterates these with the circulation (drilling_fluid and the
# rate-of-penetration passes), so a stated value ends the iteration.
ITERATED = ('rop_m_h', 'drilling_fluid_kg_m3', 'trip_fluid_kg_m3')


def test_fields_the_evaluator_searches_never_restate_the_default():
    assert set(SAMPLES) == set(op.UNITS)
    searched = set(ITERATED)
    for name, value in SAMPLES.items():
        ops = Operations(**{name: value})
        if ops.fixed_flow or ops.flow_grid or ops.fixed_connection or ops.fixed_staging:
            searched.add(name)
    assert searched == set(op.SEARCHED)
    site = se.find_site('newberry')
    custom = borethm.HydraulicProgramme(reference=None, segments=(wg.StringSegment(site.target(), wg.TK_DRAKON),))
    for defaults in (borethm.operation_defaults(), borethm.operation_defaults(site),
                     borethm.operation_defaults(site, custom)):
        for name, entry in defaults.items():
            if name in searched or entry['value'] is None:
                assert entry['restates_default'] is False, name
    assert borethm.operation_defaults(site)['trip_hours']['restates_default'] is True
    assert borethm.operation_defaults(site, custom)['pipes']['restates_default'] is False
    assert borethm.operation_defaults(site)['pipes']['restates_default'] is True


def test_operation_defaults_name_their_sources_in_words():
    site = se.find_site('newberry')
    for defaults in (borethm.operation_defaults(), borethm.operation_defaults(site)):
        for name, entry in defaults.items():
            for text in (entry['rule'], entry['source']):
                assert '_' not in text and 'data/' not in text, (name, text)
                assert not re.search(r'[A-Za-z]\.[A-Za-z]', text), (name, text)
    defaults = borethm.operation_defaults(site)
    assert defaults['pump_pressure_limit_Pa']['rule'] == "51.7 MPa, from the reference design's 7,500 psi"
    assert defaults['tool_limit_C']['rule'].startswith('200 C')
    assert defaults['trip_hours']['rule'].startswith('17.459 h at the target depth')
    assert defaults['min_annular_velocity_m_s']['rule'].startswith('1.245 m/s')


def test_operation_defaults_for_a_site_and_a_programme():
    site = se.find_site('newberry')
    defaults = borethm.operation_defaults(site)
    assert defaults['trip_hours']['value'] == dc.trip_hours(site.target(), dc.forge_timings())
    custom = borethm.HydraulicProgramme(reference=None, segments=(wg.StringSegment(site.target(), wg.VACUUM_INSULATED),))
    defaults = borethm.operation_defaults(site, custom)
    assert defaults['pipes']['value'] == ['vacuum-insulated (sensitivity)']
    assert 'custom string' in defaults['pipes']['rule']


# ------------------------------------------------------------ flow units
def flow_pairs(name, values, fluid):
    return se._stated_flows(name, values, fluid)


def test_a_flow_in_the_evaluators_unit_is_used_unchanged(water):
    from borethm import fluids
    mud = fluids.Mud(1200.0)
    assert flow_pairs('mass_flow_kg_s', (30.0,), None) == [(30.0, 30.0)]
    assert flow_pairs('volume_flow_L_s', (30.0,), mud) == [(30.0, se.mass_flow(30.0, mud))]
    (md, m), = flow_pairs('volume_flow_L_s', (30.0,), None)
    assert md == m == 30.0 * 998.2 / 1000.0
    (md, m), = flow_pairs('mass_flow_kg_s', (36.0,), mud)
    assert m == 36.0 and md == pytest.approx(30.0)


@pytest.mark.parametrize('name', ['mass_flow_kg_s', 'volume_flow_L_s'])
@pytest.mark.parametrize('weighted', [False, True])
def test_stating_the_chosen_flow_in_either_unit_gives_the_same_circulation(fake_circulation, monkeypatch, name, weighted):
    """The stated flow, converted at the fluid's surface density, is the mass
    flow the search passed to circulate, to the last bit."""
    from borethm import fluids
    monkeypatch.setattr(se.fluids, 'water', lambda: SimpleNamespace(rho_surface=998.2012723757281))
    fluid = fluids.Mud(1150.5) if weighted else None
    site = replace(se.find_site('newberry'), operations=Operations())
    chosen = se.choose_circulation(site, 3000.0, None, fluid=fluid)
    mass = chosen['run']['m_dot']
    rho = fluid.rho_surface if weighted else 998.2012723757281
    value = mass if name == 'mass_flow_kg_s' else (chosen['m_dot'] if weighted else mass * 1000.0 / rho)
    stated = se.choose_circulation(replace(site, operations=Operations(**{name: value})), 3000.0, None, fluid=fluid)
    assert stated['run']['m_dot'] == mass
    assert stated['m_dot'] == pytest.approx(chosen['m_dot'], rel=1e-15)
    assert stated['pipe'] == chosen['pipe'] and stated['run']['T_bottom_delivered'] == chosen['run']['T_bottom_delivered']


def test_a_stated_grid_in_either_unit_searches_the_same_flows(fake_circulation):
    site = replace(se.find_site('newberry'), operations=Operations(volume_flows_L_s=(33.0, 44.0)))
    se.choose_circulation(site, 3000.0, None)
    from borethm import fluids
    assert fake_circulation[0][1] == pytest.approx(33.0 * fluids.water().rho_surface / 1000.0)


# ------------------------------------------------------------ named pipes in site files
NAMED_STRING = '''
[programme]
[[programme.segments]]
length = 1000.0
pipe = "vacuum-insulated (sensitivity)"
[[programme.segments]]
length = 9233.2
pipe = "TK-Drakon coated"
[programme.segments.hydraulic_joint]
outer_diameter = 0.1778
bore_diameter = 0.1016
restriction_length = 0.7366
spacing = 9.677
source = "test joint"
[[programme.segments]]
length = 466.8
name = "drill collar"
bore_diameter = 0.0714
outer_diameter = 0.1714
conductivity = 45.0
'''


def test_named_pipes_round_trip_through_a_site_file(tmp_path):
    from borethm.hydraulic_losses import HydraulicJoint, SurfaceLoss
    site = load_site(write(tmp_path, template_text() + NAMED_STRING))
    segments = site.programme.segments
    assert segments[0].pipe == wg.VACUUM_INSULATED
    assert segments[1].pipe == replace(wg.TK_DRAKON, hydraulic_joint=HydraulicJoint(0.1778, 0.1016, 0.7366, 9.677, source='test joint'))
    assert segments[2].pipe.layers == (wg.Layer(0.0357, 0.0857, 45.0),)
    expected = borethm.HydraulicProgramme(reference=None, segments=(
        wg.StringSegment(1000.0, wg.VACUUM_INSULATED), wg.StringSegment(9233.2, segments[1].pipe),
        wg.StringSegment(466.8, segments[2].pipe)))
    assert site.programme == expected
    geometry = site.programme.geometry(site.target(), wg.CONVENTIONAL)
    assert [s.pipe.name for s in geometry.string] == ['vacuum-insulated (sensitivity)', 'TK-Drakon coated', 'drill collar']


def test_the_starter_files_programme_example_parses(tmp_path):
    from borethm.programme import TEMPLATE as PROGRAMME
    keys = [line[2:] for line in PROGRAMME.splitlines() if line.startswith('# ') and ('=' in line or line.startswith('# ['))]
    site = load_site(write(tmp_path, template_text() + '\n' + '\n'.join(keys) + '\n'))
    assert [s.pipe.name for s in site.programme.segments] == ['vacuum-insulated (sensitivity)', 'TK-Drakon coated', 'drill collar']
    assert sum(s.length for s in site.programme.segments) == pytest.approx(site.target())


@pytest.mark.parametrize('segment,message', [
    ('length = 10700.0\npipe = "steel"', "unknown pipe 'steel'; choose from 'TK-Drakon coated'"),
    ('length = 10700.0\npipe = "conventional"\nbore_diameter = 0.1', 'remove bore_diameter'),
    ('length = 10700.0\npipe = "conventional"\nname = "mine"', 'remove name'),
    ('length = 10700.0\npipe = 3', 'pipe must be text'),
])
def test_named_pipes_are_strict(tmp_path, segment, message):
    text = template_text() + '\n[programme]\n[[programme.segments]]\n' + segment + '\n'
    with pytest.raises(ValueError, match=message):
        load_site(write(tmp_path, text))
