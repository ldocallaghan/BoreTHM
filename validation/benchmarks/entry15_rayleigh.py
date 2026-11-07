"""Calculate model-only gap Rayleigh numbers from the conduction-floor state."""
from pathlib import Path

import numpy as np

from borethm import model1_coupled as model
from borethm.run_in_column import RadialColumn, gap_rayleigh
from borethm.wall_thermal import NU_LAMINAR
from validation.benchmarks import entry15_recovery as well4
from validation.benchmarks.run_circulation import write_csv
from validation.scoreboard.scoreboard import HERE, PLAN, RunIn, read_json


def rayleigh(fluid, temperature, wall, pressure, radius, inner, height, properties=None):
    samples = np.array([temperature-.1, temperature, temperature+.1])
    density, cp, viscosity, conductivity = model.fluid_props(
        samples, np.full(3, pressure), fluid)
    expansion = (density[0]-density[2])/(.2*density[1])
    if properties is not None:
        density, cp, viscosity, conductivity = (np.full(3, value) for value in properties)
    gap = radius-inner
    buoyancy = density[1]*9.80665*expansion*abs(wall-temperature)*gap
    return dict(buoyancy_stress_Pa=buoyancy, fluid_C=temperature, wall_C=wall, gap_m=gap, height_m=height,
                aspect_ratio=None if height is None else height/gap,
                rayleigh=gap_rayleigh(gap, wall-temperature, density[1], cp[1],
                                      viscosity[1], conductivity[1], expansion),
                local_PV_Pa_s=viscosity[1])


def forge16a():
    inputs = read_json(HERE/"transient-inputs.json")
    study = RunIn(inputs, "current", read_json(PLAN))
    for event in inputs["events"]:
        run = event["run"]
        fluid = study.fluid(run)
        last = study.records[run][int(event["end_i"])]
        depth = float(event["depth_end_ft"])*.3048
        base = dict(event=event["event_id"], run=run, depth_m=depth,
                    reference_PV_Pa_s=fluid.pv_ref, yield_point_Pa=fluid.yield_point)
        try:
            bit = depth/.3048
            state = study.wall(run, depth, last["epoch"]+10., True)
            radius = study.static(run, depth, bit, fluid)[2]
            inner = float(study.geometry(run, bit).at(np.array([depth]))["r_out"][0])
            pressure = model.P_of_z(study.path.tvd(depth))
            values = rayleigh(fluid, state["T"][-1], state["wall"][-1],
                              pressure, radius, inner, depth)
            stress = values["buoyancy_stress_Pa"]
            yield base | values | dict(yield_to_buoyancy=fluid.yield_point/stress if stress > 0 else None,
                                       status="calculated")
        except (ValueError, IndexError) as error:
            yield base | {"status": str(error)}


def benchmark_cases():
    for hours, depth, cold, hot in ((36, 12600*.3048, (199-32)*5/9, (244-32)*5/9),
                                    (756, 10000*.3048, (162.5-32)*5/9, (210-32)*5/9)):
        for inner in (0., well4.R_LINER):
            yield (f"Well 4, {hours} h", hours, depth, cold, hot, well4.R_WALL, inner,
                   well4.K_ROCK, well4.K_ROCK/well4.DIFFUSIVITY, well4.WATER_CAPACITY,
                   well4.WATER_CONDUCTIVITY, None, np.array(well4.HOURS)*3600)
    yield ("Khaled", 3.5, 2657., 114., 40+.0691*2657, 8.75*.0254/2, 5*.0254/2,
           2.31, 2800*930, 1067*3750, .75, (1067., 3750., .014, .75),
           np.array([5, 10, 15, 30, 60, 120, 240, 480, 960, 1440])*60)


def benchmarks():
    for name, hours, depth, cold, hot, radius, inner, k, rock_cp, liquid_cp, liquid_k, props, times in benchmark_cases():
        column = RadialColumn(radius, hot, k, rock_cp, hours*3600+times[-1])
        column.circulate(hours*3600, cold, np.inf)
        capacity = np.pi*(radius**2-inner**2)*liquid_cp
        film = NU_LAMINAR*liquid_k/(2*(radius-inner))
        for seconds, dt in zip(times, np.diff(np.r_[0., times]), strict=True):
            state = column.shut_in(dt, capacity, film)
            yield dict(case=name, shut_in_s=seconds, inner_radius_m=inner) | rayleigh(
                None, column.temperature_C, state.T_wall[-1], model.P_of_z(depth),
                radius, inner, None, props)


if __name__ == "__main__":
    folder = Path(__file__).parent
    write_csv(folder/"entry15-rayleigh-16a.csv", forge16a())
    write_csv(folder/"entry15-rayleigh-benchmarks.csv", benchmarks())
