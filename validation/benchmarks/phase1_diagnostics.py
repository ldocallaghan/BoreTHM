"""Isolate changes to the Phase 0 circulation comparisons."""
from pathlib import Path
from unittest.mock import patch

import numpy as np

from borethm import fluids
from validation.benchmarks import run_circulation as bench
from validation.benchmarks.kabir1996 import Case

model = bench.model


def brown():
    films = model.annulus_films

    def no_hole_film(*args, **kwargs):
        inner, outer = films(*args, **kwargs)
        return inner, np.full_like(outer, np.inf)

    with patch.object(model, "annulus_films", no_hole_film):
        for row in bench.brown_cases():
            yield {k: v for k, v in row.items() if k not in ("passed", "tolerance_K")}


def kabir():
    for name, kw in bench.cases():
        cp, r, ua, rt, ut, td, _ = bench.fixed_coefficients(kw)
        g = kw["geometry"]
        case = Case.from_properties(g.md_bit, kw["T_inj"], kw["T_surf"], kw["G"],
                                    cp, kw["k_rock"], r, ua, rt, ut, td)
        z = np.linspace(0., g.md_bit, 2001)
        base = case.closed_form(z)

        def fixed(z, *args, **kwargs):
            return np.full_like(z, cp/case.B), np.full_like(z, cp/case.A), model.P_of_z(z)

        def nozzle_only(m_dot, rho, tfa=model.BIT_TFA_DEFAULT, cd=model.NOZZLE_CD):
            return model.nozzle_dp(m_dot, rho, tfa, cd)

        mud = fluids.Mud(kw["fluid"]["rho"], pv_ref=kw["fluid"]["mu"], yield_point=0.)
        with patch.object(model, "conductances", fixed):
            variable = model.solve(**(kw | {"fluid": mud}))
            with patch.object(model, "nozzle_dp", return_value=0.):
                friction = model.solve(**(kw | {"friction_heat": True}))
            rho = kw["fluid"]["rho"]
            nozzle = model.solve(**(kw | {"Q_face": nozzle_only(kw["m_dot"], rho)*kw["m_dot"]/rho}))
        live = model.solve(**kw)
        default = model.solve(**(kw | {"fluid": mud}))
        for label, result in (("variable properties, fixed films", variable),
                              ("distributed friction alone", friction),
                              ("nozzle alone, zero bit heat", nozzle),
                              ("live films, constant properties", live),
                              ("Phase 0 variable properties and live films", default)):
            solution = result["sol"].sol(z)
            delta = solution-base
            data = dict(case=name, change=label, converged=result["success"],
                        max_pipe_K=np.max(abs(delta[0])), max_annulus_K=np.max(abs(delta[1])),
                        bit_delta_K=delta[0,-1], return_delta_K=delta[1,0])
            if result is live or result is default:
                fluid = mud if result is default else kw["fluid"]
                rho, _, mu, _ = model.fluid_props(solution[1], model.P_of_z(z), fluid)
                geo = g.at(z)
                v = kw["m_dot"]/(rho*geo["A_ann"])
                flow = fluids.hb_annulus(rho, 0., mu, 1., v, geo["Dh_ann"],
                                         band="erge", kappa=geo["r_out"]/geo["r_wall"])
                blend = flow["blend"]
                data |= dict(annulus_Re_min=np.min(rho*v*geo["Dh_ann"]/mu),
                             annulus_Re_max=np.max(rho*v*geo["Dh_ann"]/mu),
                             laminar_points=np.count_nonzero(blend==0),
                             transition_points=np.count_nonzero((blend>0)&(blend<1)),
                             turbulent_points=np.count_nonzero(blend==1))
            yield data


if __name__ == "__main__":
    out = Path(__file__).parent / "phase1"
    out.mkdir(exist_ok=True)
    bench.write_csv(out/"brown-no-outer-film.csv", brown())
    bench.write_csv(out/"kabir-decomposition.csv", kabir())
