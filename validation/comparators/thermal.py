"""Thermal comparators for an independently selected sample or run-in leg."""
import numpy as np

from borethm import fluids, model1_coupled as m1, physics, rock_response
from validation.benchmarks.kabir1996 import Case, hasan_kabir_td


def previous_physics(**kwargs):
    return m1.solve(**(kwargs | {"physics": "v1.7.0"}))


def analytical(geometry, fluid, mass_flow, inlet_C, formation, exposure, k_rock, rock_heat_capacity):
    """Use local v1.8.0 conductances with the analytical transient rock term."""
    depth = geometry.md_bit
    z = np.array([depth])
    temperature = np.array([inlet_C])
    setting = physics.resolve("v1.8.0")
    fluid = fluids.with_default_rheology(fluid)
    ui, uo, pressure = m1.conductances(
        z, temperature, temperature, mass_flow, 0., k_rock, geometry,
        exposure=exposure, fluid=fluid, rhocp_rock=rock_heat_capacity,
        rock_response="cylinder", annulus_model=setting["annulus_model"])
    _, cp, _, _ = m1.fluid_props(temperature, pressure, fluid)
    dimensions = geometry.at(z)
    radius = float(dimensions["r_rock"][0])
    pipe_radius = float(dimensions["r_out"][0])
    alpha = k_rock / rock_heat_capacity
    seconds = float(m1.exposure_seconds(z, 0., exposure)[0])
    rock = rock_response.resistance(seconds, alpha, radius, k_rock)
    ua = 1/(1/uo[0] - rock)/(2*np.pi*radius)
    ut = ui[0]/(2*np.pi*pipe_radius)
    surface = float(formation(geometry.survey.tvd(0.)))
    bottom = float(formation(geometry.survey.tvd(depth)))
    return Case.from_properties(depth, inlet_C, surface, (bottom-surface)/depth,
                                mass_flow*cp[0], k_rock, radius, ua, pipe_radius, ut,
                                hasan_kabir_td(alpha*seconds/radius**2))


def undisturbed_formation(sensor_md, survey, formation):
    return formation(survey.tvd(np.asarray(sensor_md, dtype=float)))


def persistence(leg_start, observation_times, values, prediction_times):
    stamps, values = np.asarray(observation_times), np.asarray(values, dtype=float)
    good = np.flatnonzero((stamps < leg_start) & np.isfinite(values))
    initial = values[good[np.argmax(stamps[good])]] if len(good) else np.nan
    return np.full(np.shape(prediction_times), initial, dtype=float)
