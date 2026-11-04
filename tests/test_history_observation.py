"""Optional thermal-history output preserves the default numerical results."""
import numpy as np
from borethm import wall_thermal as wall, tool_thermal as tool


def test_wall_observation_is_detached_and_bitwise_passive():
    schedule = [wall.State('circulating',120,T_fluid=40,h=200),
                wall.State('static',90,h=10,C=1.e5),
                wall.State('fixed',60,T_wall=80),wall.State('flux',60,q=-100)]
    plain = wall.run(schedule,150,.1,2.5,2.7e6,n=48)
    frames = []
    def observe(frame):
        frames.append({**frame,'radius_m':frame['radius_m'].copy(),'temperature_C':frame['temperature_C'].copy()})
        frame['temperature_C'][:] = -999
        frame['radius_m'][:] = -1
    watched = wall.run(schedule,150,.1,2.5,2.7e6,n=48,observe=observe)
    for key in ('t','T_wall','T_node','q_wall','r','vol'):
        np.testing.assert_array_equal(getattr(plain,key),getattr(watched,key))
    for a,b in zip(plain.fields,watched.fields):np.testing.assert_array_equal(a,b)
    assert (plain.energy_in,plain.energy_far,plain.stored)==(watched.energy_in,watched.energy_far,watched.stored)
    accepted = [f for f in frames if f['sample_kind']=='accepted_step']
    np.testing.assert_array_equal([f['time_s'] for f in accepted],plain.t[1:])
    np.testing.assert_array_equal([f['wall_temperature_C'] for f in accepted],plain.T_wall[1:])
    assert len(frames)==len(plain.t)-1+len(schedule)
    for i in range(1,len(schedule)):
        start = next(j for j,f in enumerate(frames) if f['state_index']==i)
        assert frames[start-1]['time_s']==frames[start]['time_s']
        assert frames[start-1]['event_side']=='left' and frames[start]['event_side']=='right'
        np.testing.assert_array_equal(frames[start-1]['temperature_C'],frames[start]['temperature_C'])
    assert frames[-1]['stored_J_m']==plain.stored


def test_tool_retained_stage_samples_preserve_legacy_endpoints():
    lump=tool.Lump.of_pipe(.04,.08,4.2e6)
    args=dict(lump=lump,column=lambda z:30+z*.1,md_bottom=100.,speed=1.,T0=20.,
              h_static_out=10.,h_static_in=10.,stages=[50.],stage_s=55.,
              circulating=lambda z:(125.,300.,200.),dt=30.)
    legacy,md_legacy=tool.trip_in(**args)
    full,md_full=tool.trip_in(**args,retain_stage_samples=True)
    assert len(full.t)>len(legacy.t)
    indices=[int(np.flatnonzero(full.t==time)[0]) for time in legacy.t]
    np.testing.assert_array_equal(full.T_s[indices],legacy.T_s)
    np.testing.assert_array_equal(full.T_f[indices],legacy.T_f)
    np.testing.assert_array_equal(md_full[indices],md_legacy)
    assert sum(x=='staging' for x in full.labels)==6
    assert full.peak()[0]==max(full.T_f)


def test_tool_explicit_distinct_initial_nodes():
    lump=tool.Lump.of_pipe(.04,.08,4.2e6)
    history,_=tool.trip_in(lump,lambda z:60.,10.,1.,20.,10.,10.,dt=10.,T_s0=50.,T_f0=30.)
    expected=tool.run(lump,[tool.Segment(10.,60.,10.,10.)],50.,30.,dt=10.)
    np.testing.assert_array_equal(history.T_s,expected.T_s)
    np.testing.assert_array_equal(history.T_f,expected.T_f)


def test_static_node_carries_only_when_requested():
    schedule = [wall.State('circulating', 120, T_fluid=40, h=200),
                wall.State('static', 90, h=10, C=1.e5),
                wall.State('static', 90, h=10, C=1.e5)]
    frames = []
    wall.run(schedule, 150, .1, 2.5, 2.7e6, n=48,
             carry_static_node=True, observe=frames.append)
    before = [f for f in frames if f['state_index'] == 1][-1]
    after = [f for f in frames if f['state_index'] == 2][0]
    assert before['fluid_node_temperature_C'] == after['fluid_node_temperature_C']
    plain = []
    wall.run(schedule, 150, .1, 2.5, 2.7e6, n=48, observe=plain.append)
    assert [f for f in plain if f['state_index'] == 2][0]['fluid_node_temperature_C'] == 40.


def test_stored_radial_grid_allows_local_rounding_only():
    import pytest
    grid = wall.Grid(.1, 30., 48)
    radii, _, _ = grid.build()
    stored = radii.copy()
    stored[5] = np.nextafter(stored[5], np.inf)
    actual, _, _ = grid.build(stored)
    np.testing.assert_array_equal(actual, stored)
    actual[5] = -1
    assert stored[5] > 0
    stored[5] = radii[5] + 32 * np.spacing(radii[5])
    with pytest.raises(ValueError):
        grid.build(stored)
