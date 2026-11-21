import numpy as np
import pytest

from borethm.column_replay import ColumnStep, Move, ToolContact, replay, split_durations
from borethm.layered_tool import LayeredTool
from borethm.moving_column import MovingColumn
from borethm.run_in_column import RadialColumn


@pytest.mark.parametrize("float_valve", [False, True])
def test_descent_pause_and_restart_share_bore_inventory(float_valve):
    rock = [RadialColumn(.1, 120., 2.5, 2.5e6, 3600., radial_nodes=40,
                         temperature_C=t) for t in (50., 70., 90.)]
    column = MovingColumn(rock, [10., 10., 10.], [2., 2., 2.], 4.18e6, [1.], [35.])
    tool = LayeredTool(.025, .08, column.fluid_heat_capacity, 20.)
    films = (50., 50., 0.)
    initial = ToolContact(tool, 2., 0, 0, 50., 400.)
    lowered = ToolContact(tool, 2., 1, 1, 50., 400.)
    steps = [
        ColumnStep(10., films, (initial,)),
        ColumnStep(10., films, (lowered,), np.array([2., 1.5, 2.]), .2,
                   float_valve, 25.),
        ColumnStep(30., films, (lowered,)),
        ColumnStep(30., films, (lowered,), flow=.01, inlet_C=25., active_cells=2),
    ]
    output = list(replay(column, steps))
    assert [step.elapsed for step in output] == [10., 20., 50., 80.]
    assert output[1].returned_J > 0.
    assert output[-1].returned_J > 0.
    assert column.annulus_temperature[-1] == pytest.approx(90.)
    assert output[-1].sensors_C[0][0] == column.bore_temperature[1]
    assert max(abs(step.energy_residual_J) for step in output) < 1e-4
    np.testing.assert_allclose(column.bore_volume, [.2, 1.] if float_valve else [1., .2])


def test_restart_throughput_splits_a_recorded_step_and_resets_after_pause():
    from borethm.column_replay import circulation_phases

    steps = [ColumnStep(10., (0.,), flow=2., inlet_C=20.),
             ColumnStep(20., (0.,), flow=3., inlet_C=21.),
             ColumnStep(10., (0.,)),
             ColumnStep(2., (0.,), flow=4., inlet_C=21.)]
    phases = list(circulation_phases(steps, flush_volume=35.))
    assert [(kind, step.duration) for kind, step in phases] == [
        ("restart", 10.), ("restart", 5.), ("steady", 15.),
        ("static", 10.), ("restart", 2.)]


def _slug_column():
    rock = [RadialColumn(.1, 120., 2.5, 2.5e6, 3600., radial_nodes=20,
                         temperature_C=40.) for _ in range(4)]
    # A short hot slug sits in the bore two tool lengths above the tool.
    column = MovingColumn(rock, [10.]*4, [2.]*4, 4.18e6, [1., .05, .2, .05, 1.],
                          [20., 20., 80., 20., 20.])
    tool = LayeredTool(.025, .08, column.fluid_heat_capacity, 20.)
    # The tool's bore span is 1.25 to 1.30 and its annulus span 4.0 to 4.4.
    return column, ToolContact(tool, .5, 0, 0, 50., 400., ((4., 4.4), (1.25, 1.3)))


def test_sub_stepped_exchange_meets_liquid_shorter_than_the_step():
    hot = []
    for volume in (None, .02):
        column, contact = _slug_column()
        step = ColumnStep(1., (0.,)*4, (contact,), flow=.5, inlet_C=20., active_cells=4,
                          exchange_volume=volume)
        result = next(replay(column, [step]))
        readings = [s[1][0][0] for s in result.samples] or [result.sensors_C[0][0]]
        hot.append(max(readings))
        assert abs(result.energy_residual_J) < 1e-6*result.supplied_J
        if volume:
            assert len(result.samples) == 25
            assert result.samples[-1][0] == pytest.approx(1.)
    # One step moves 0.5 past the tool; the slug passes between the two
    # exchanges of the single step and only the split step meets it.
    assert hot[0] < 21.
    assert hot[1] > 70.


def test_advect_matches_restart_step_without_wall_exchange():
    a, _ = _slug_column()
    b, _ = _slug_column()
    out_a, _ = a.restart_step(1., .3, 20., (0.,)*4, active_cells=4)
    out_b = b.advect(.3, 20., active_cells=4)
    assert out_a == pytest.approx(out_b)
    np.testing.assert_allclose(a.bore_temperature, b.bore_temperature)


def _descending(flow):
    """A bit at 20 m entering hot static liquid, with a 1.25 m tool at the bit."""
    def annulus(bit):
        return np.array([2.-.05*min(max(bit-10.*i, 0.), 10.) for i in range(4)])

    def to(depth, bit):
        return .2*depth-.05*min(depth, bit)
    rock = [RadialColumn(.1, 120., 2.5, 2.5e6, 3600., radial_nodes=20, temperature_C=t)
            for t in (20., 20., 80., 80.)]
    column = MovingColumn(rock, [10.]*4, annulus(20.), 4.18e6, [.2], [20.])
    tool = LayeredTool(.025, .08, column.fluid_heat_capacity, 20.)

    def move(bit, before):
        contact = ToolContact(tool, 1.25, 0, 0, 50., 400.,
                              ((to(bit-1.25, bit), to(bit, bit)), (.01*bit-.0125, .01*bit)))
        return Move(annulus(bit), (contact,), added_bore_volume=.01*(bit-before),
                    bit_volumes=(to(bit, before), to(bit, bit)),
                    circuit_end=to(bit, bit) if flow else None)

    def step(duration, depths, before):
        moves = []
        for bit in depths:
            moves.append(move(bit, before))
            before = bit
        return ColumnStep(duration, (0.,)*4, moves[-1].contacts, float_valve=True, fill_C=20.,
                          flow=flow, inlet_C=20. if flow else None,
                          active_cells=3 if flow else None, moves=tuple(moves))
    return column, tool, step


@pytest.mark.parametrize("flow", [0., .02])
def test_moving_parts_do_not_depend_on_the_step_division(flow):
    whole, whole_tool, step = _descending(flow)
    one = list(replay(whole, [step(4., [21., 22., 23., 24.], 20.)]))
    split, split_tool, step = _descending(flow)
    two = list(replay(split, [step(2., [21., 22.], 20.), step(2., [23., 24.], 22.)]))
    # Without wall films only the division into steps differs.
    np.testing.assert_allclose(whole_tool.temperature_C, split_tool.temperature_C, rtol=0, atol=1e-10)
    np.testing.assert_allclose(whole.annulus_temperature, split.annulus_temperature, rtol=0, atol=1e-10)
    assert len(one[0].samples) == 4 and one[0].samples[-1][0] == pytest.approx(4.)
    # The displaced hot liquid passes the tool.
    assert max(s[1][0][-1] for s in one[0].samples) > 21.
    inventory = whole.fluid_heat_capacity*np.dot(whole.annulus_volume, whole.annulus_temperature)
    assert max(abs(r.energy_residual_J) for r in one+two) < 1e-9*inventory
    # One descent per step drops the displaced liquid into the footprint at
    # once, so the tool depends on how the motion is divided.
    coarse, coarse_tool, step = _descending(flow)
    list(replay(coarse, [step(4., [24.], 20.)]))
    halves, halves_tool, step = _descending(flow)
    list(replay(halves, [step(2., [22.], 20.), step(2., [24.], 22.)]))
    assert abs(coarse_tool.temperature_C[-1]-halves_tool.temperature_C[-1]) > 1e-3


def test_split_static_step_matches_its_parts_and_resolves_the_stop():
    def stopped(film):
        column, tool, step = _descending(0.)
        list(replay(column, [step(4., [21., 22., 23., 24.], 20.)]))
        contact = replace_film(step(1., [24.], 24.).contacts[0], film)
        return column, tool, ColumnStep(2., (300.,)*4, (contact,))

    def replace_film(contact, film):
        return ToolContact(contact.tool, contact.length, 0, 0, contact.inside_film, film,
                           contact.footprint)

    assert split_durations(2., 3) == [.25, .25, .5, 1.] and sum(split_durations(2., 10)) == 2.
    whole, whole_tool, static = stopped(np.inf)
    one = list(replay(whole, [ColumnStep(**{**static.__dict__, "split": 3})]))
    parts, parts_tool, static = stopped(np.inf)
    many = list(replay(parts, [ColumnStep(**{**static.__dict__, "duration": d})
                               for d in split_durations(2., 3)]))
    np.testing.assert_allclose(whole_tool.temperature_C, parts_tool.temperature_C, rtol=0, atol=1e-12)
    np.testing.assert_allclose(whole.annulus_temperature, parts.annulus_temperature, rtol=0, atol=1e-12)
    assert [s[0] for s in one[0].samples] == pytest.approx([.25, .5, 1., 2.])
    np.testing.assert_allclose(one[0].samples[0][1][0], many[0].sensors_C[0], rtol=0, atol=1e-12)
    inventory = whole.fluid_heat_capacity*np.dot(whole.annulus_volume, whole.annulus_temperature)
    assert abs(one[0].energy_residual_J) < 1e-9*inventory
    with pytest.raises(ValueError):
        next(replay(whole, [ColumnStep(1., (300.,)*4, static.contacts, flow=.01, inlet_C=20., split=2)]))
