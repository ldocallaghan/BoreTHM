"""Soft-string placement of rotary heat."""
import numpy as np
import pytest

from borethm import model1_coupled as m1, rotary_heat as rh, well_geometry as wg


def pipe(r_in=0.05, r_out=0.06):
    return wg.PipeType('test pipe', (wg.Layer(r_in, r_out, 45.0),))


def well(length=1000.0):
    return wg.WellGeometry([wg.StringSegment(length, pipe())], [wg.open_hole(0., length, .25)],
                           wg.Survey(np.array([0., length]), np.array([0., length])))


def test_straight_inclined_hole_presses_with_the_weight_component():
    grid = np.linspace(0., 1000., 501)
    inc = np.full_like(grid, np.radians(40.))
    w = np.full_like(grid, 300.)
    force = rh.contact_force(grid, inc, np.zeros_like(grid), w, 50e3)
    assert np.allclose(force, 300.*np.sin(np.radians(40.)))


def test_tension_in_a_build_acts_against_the_weight():
    grid = np.linspace(0., 300., 301)
    kappa = np.radians(3.)/30.                      # 3 degrees per 30 m
    inc = np.radians(30.)+kappa*grid
    w = np.full_like(grid, 200.)
    force = rh.contact_force(grid, inc, np.zeros_like(grid), w, 0.)
    theta = 0.5*(inc[1:]+inc[:-1])
    tension = np.array([np.sum((w[:-1]*np.cos(theta)*np.diff(grid))[i:]) for i in range(300)])
    expected = np.abs(200.*np.sin(theta)-(tension-0.5*w[:-1]*np.cos(theta))*kappa)
    assert np.allclose(force, expected, rtol=1e-9, atol=1e-9)


def test_partition_conserves_measured_power_and_recovers_the_factor():
    g = well()
    md, inc, azi = np.array([0., 1000.]), np.array([30., 30.]), np.array([0., 0.])
    weight, radius = rh.string_properties(g, np.array([500.]))
    lever = weight[0]*(1-1000./rh.STEEL_DENSITY)*np.sin(np.radians(30.))*radius[0]*1000.
    heat = rh.partition(g, md, inc, azi, 1000., 60., 0.4*lever, 0.25*lever, 0.)
    assert heat.friction_factor == pytest.approx(0.25, rel=1e-9)
    omega = 2*np.pi
    assert heat.friction_W+heat.bit_W == pytest.approx(omega*0.4*lever, rel=1e-9)
    assert heat.bit_W == pytest.approx(omega*0.15*lever, rel=1e-6)
    capped = rh.partition(g, md, inc, azi, 1000., 60., 0.2*lever, 0.25*lever, 0.)
    assert capped.capped and capped.bit_W == 0.
    assert capped.friction_W == pytest.approx(omega*0.2*lever, rel=1e-9)
    with pytest.raises(ValueError):
        rh.partition(g, md, np.zeros(2), azi, 1000., 60., 1e3, 1e3, 0.)


def test_joints_set_contact_radius_and_add_steel():
    from borethm import hydraulic_losses as hl
    joint = hl.HydraulicJoint(0.17, 0.08, 0.5, 9.0)
    jointed = wg.PipeType('jointed', (wg.Layer(0.05, 0.06, 45.0),), hydraulic_joint=joint)
    g = wg.WellGeometry([wg.StringSegment(100., jointed)], [wg.open_hole(0., 100., .25)],
                        wg.Survey(np.array([0., 100.]), np.array([0., 100.])))
    weight, radius = rh.string_properties(g, np.array([50.]))
    plain, _ = rh.string_properties(well(100.), np.array([50.]))
    assert radius[0] == 0.085 and weight[0] > plain[0]


def test_annulus_heat_warms_the_return_and_is_recorded():
    base = dict(verbose=False, pipe=wg.LEGACY_VACUUM, m_dot=20.0)
    without = m1.solve(**base)
    added = m1.solve(**base, annulus_heat=lambda z: np.full_like(np.asarray(z, float), 20.0))
    assert added['T_return_surface'] > without['T_return_surface']
    assert added['annulus_heat_W'] == pytest.approx(20.0*added['L'], rel=1e-9)
    with pytest.raises(ValueError, match='annulus heat'):
        m1.solve(**base, hydraulics_model='v1.5.0', annulus_heat=lambda z: 0*z)


def test_friction_source_is_smooth_and_continuous_to_the_well_ends():
    g = well()
    md, inc, azi = np.array([0., 400., 1000.]), np.array([0., 20., 40.]), np.zeros(3)
    heat = rh.partition(g, md, inc, azi, 1000., 60., 5e3, 4e3, 50e3)
    ends = heat.annulus(np.array([0., 0.5, 999.5, 1000.]))
    assert ends[0] == ends[1] and ends[2] == ends[3] and np.all(ends > 0)
    z = np.linspace(0., 1000., 2001)
    assert np.max(np.abs(np.diff(heat.annulus(z)))) < 0.05*np.max(heat.annulus(z))
    assert np.sum(heat.density*np.diff(np.unique(np.r_[np.arange(0., 1000., 2.), 1000.]))) == pytest.approx(heat.friction_W)
