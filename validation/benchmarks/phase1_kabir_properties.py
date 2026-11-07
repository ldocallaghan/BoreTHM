"""Compare the published fluid inputs with the historical mud substitution."""
from pathlib import Path
from unittest.mock import patch

import numpy as np

from borethm.fluids import Mud
from validation.benchmarks import run_circulation as bench
from validation.benchmarks.kabir1996 import Case


def compare():
    model = bench.model
    for name, inputs in bench.cases():
        fluid = inputs["fluid"]
        mud = Mud(fluid["rho"], pv_ref=fluid["mu"], yield_point=0.)
        mass_cp, radius, ua, pipe_radius, ut, td, _ = bench.fixed_coefficients(inputs)
        depth = inputs["geometry"].md_bit
        case = Case.from_properties(depth, inputs["T_inj"], inputs["T_surf"],
                                    inputs["G"], mass_cp, inputs["k_rock"],
                                    radius, ua, pipe_radius, ut, td)
        grid = np.linspace(0., depth, 2001)
        reference = case.closed_form(grid)
        def fixed(z, *args, **kwargs):
            return (np.full_like(z, mass_cp/case.B), np.full_like(z, mass_cp/case.A),
                    model.P_of_z(z))

        with patch.object(model, "conductances", fixed):
            fixed_published = model.solve(**inputs)
            fixed_mud = model.solve(**(inputs | {"fluid": mud}))
        for label, properties, fixed_result in (
            ("published", fluid, fixed_published),
            ("historical mud", mud, fixed_mud),
        ):
            result = model.solve(**(inputs | {"fluid": properties}))
            profile = result["sol"].sol(grid)
            fixed_profile = fixed_result["sol"].sol(grid)
            delta = profile - reference
            for station, index in (("inlet", 0), ("bit", -1)):
                temperature = fixed_profile[0, index]
                pressure = model.P_of_z(grid[index])
                rho, cp, mu, k = model.fluid_props(temperature, pressure, properties)
                yield dict(case=name, properties=label, station=station,
                           converged=result["success"] and fixed_result["success"], temperature_C=temperature,
                           pressure_Pa=float(pressure), rho_kg_m3=np.asarray(rho).item(),
                           cp_J_kg_K=np.asarray(cp).item(), mu_Pa_s=np.asarray(mu).item(), k_W_m_K=np.asarray(k).item(),
                           fixed_film_bit_delta_K=fixed_profile[0, -1] - reference[0, -1], live_film_bit_delta_K=delta[0, -1], return_delta_K=delta[1, 0])


if __name__ == "__main__":
    bench.write_csv(Path(__file__).with_name("phase1") / "kabir-property-audit.csv", compare())
