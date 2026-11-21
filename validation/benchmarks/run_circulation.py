"""Run the declared circulation benchmarks and write numerical results."""
import argparse
import csv
from pathlib import Path
from unittest.mock import patch

import numpy as np

from borethm import model1_coupled as model, rock_response, well_geometry as wg
from validation.benchmarks.kabir1996 import Case, hasan_kabir_td

IN = .0254
FT = .3048
LB = .45359237
GAL = .003785411784
BTU = 1055.05585262
HOUR = 3600.
FAHRENHEIT = 5 / 9


def make_case(name, length, hole, od, bore, flow, inlet, surface, gradient, hours, fluid, rock):
    pipe = wg.uniform_wall(wg.K_STEEL, bore / 2, od / 2)
    geometry = wg.WellGeometry.single(length, pipe, hole / 2)
    kw = dict(geometry=geometry, m_dot=flow*fluid["rho"], G=gradient, T_surf=surface,
              T_inj=inlet, target_rock_T=surface+gradient*length, Q_face=0.,
              k_rock=rock[0], rhocp_rock=rock[1], t_years=hours*HOUR/model.SECONDS_PER_YEAR,
              fluid=fluid, verbose=False)
    return name, kw


def cases():
    yield make_case(
        "Holmes and Swift", 15000*FT, 8.375*IN, 6.625*IN, 5.965*IN,
        300*42*GAL/HOUR, (75-32)*FAHRENHEIT, (59.5-32)*FAHRENHEIT,
        .0127*FAHRENHEIT/FT, 44,
        dict(rho=10*LB/GAL, cp=.4*BTU/LB/FAHRENHEIT, mu=110*LB/FT/HOUR,
             k=BTU/FT/FAHRENHEIT/HOUR),
        (1.3*BTU/FT/FAHRENHEIT/HOUR, 165*LB/FT**3*.2*BTU/LB/FAHRENHEIT))
    yield make_case(
        "Khaled FORGE", 2657., 8.75*IN, 5.*IN, 4.276*IN,
        600*GAL/60, 40., 40., .0691, 3.5,
        dict(rho=1067., cp=3750., mu=.014, k=.75), (2.31, 2800*930.))


def fixed_coefficients(kw):
    g = kw["geometry"]
    z = np.array([0.])
    inlet = np.array([kw["T_inj"]])
    m_cp = kw["m_dot"]*kw["fluid"]["cp"]
    ui, uo, _ = model.conductances(
        z, inlet, inlet, kw["m_dot"], kw["t_years"], kw["k_rock"], g,
        fluid=kw["fluid"], rhocp_rock=kw["rhocp_rock"],
        rock_response="cylinder", annulus_model="herschel-bulkley-erge")
    r = g.at(z)
    k = kw["k_rock"]
    td_time = k / kw["rhocp_rock"] * kw["t_years"] * model.SECONDS_PER_YEAR / r["r_rock"][0]**2
    td = 1 / rock_response.cylinder_flux(td_time)
    r_rock = td / (2*np.pi*k)
    ua = 1 / (1/uo[0] - r_rock) / (2*np.pi*r["r_rock"][0])
    ut = ui[0] / (2*np.pi*r["r_out"][0])
    return m_cp, r["r_rock"][0], ua, r["r_out"][0], ut, td, td_time


def matched_solution(kw, case, reverse):
    """Freeze the two per-length conductances within the benchmark only.

    Reverse flow negates both native energy derivatives, sets annulus inlet
    and retains equality at the turnaround. The package exposes forward flow.
    """
    def conductances(z, *args, **kwargs):
        return (np.full_like(z, mass_cp/case.B), np.full_like(z, mass_cp/case.A),
                model.P_of_z(z))

    def reverse_boundary(odes, boundary, z, seed, **options):
        return native_bvp(lambda x, y: -odes(x, y),
                          lambda top, bottom: case.boundary(top, bottom, True),
                          z, seed, **options)

    mass_cp = kw["m_dot"] * kw["fluid"]["cp"]
    native_bvp = model.solve_bvp
    with patch.object(model, "conductances", conductances):
        if reverse:
            with patch.object(model, "solve_bvp", reverse_boundary):
                return model.solve(**kw)
        return model.solve(**kw)


def comparisons(name, kw):
    mass_cp, r, ua, rt, ut, td, td_time = fixed_coefficients(kw)
    case = Case.from_properties(kw["geometry"].md_bit, kw["T_inj"], kw["T_surf"], kw["G"],
                                mass_cp, kw["k_rock"], r, ua, rt, ut, td)
    grid = np.linspace(0, case.length, 2001)
    default = model.solve(**kw)
    for reverse in (False, True):
        analytical = case.closed_form(grid, reverse)
        numerical = case.numerical(reverse)
        matched = matched_solution(kw, case, reverse)
        row = dict(case=name, direction="reverse" if reverse else "forward",
                   U_a_W_m2K=ua, U_t_W_m2K=ut, formation_T_D=td, converged=matched["success"],
                   independent_difference_K=np.max(np.abs(numerical.sol(grid)-analytical)),
                   pipe_difference_K=np.max(np.abs(matched["sol"].sol(grid)[0]-analytical[0])),
                   annulus_difference_K=np.max(np.abs(matched["sol"].sol(grid)[1]-analytical[1])),
                   analytical_bottom_C=analytical[0, -1])
        row["matched_pass"] = (numerical.success and matched["success"]
                               and row["independent_difference_K"] <= 1e-6
                               and max(row["pipe_difference_K"], row["annulus_difference_K"]) <= .1)
        if not reverse:
            kabir = Case.from_properties(case.length, case.inlet, case.surface, case.gradient,
                                         mass_cp, kw["k_rock"], r, ua, rt, ut, hasan_kabir_td(td_time))
            row |= dict(kabir_annulus_maximum_ft=kabir.annulus_maximum()[0]/FT,
                        default_converged=default["success"], default_bottom_C=default["T_bottom_delivered"],
                        default_pipe_difference_K=np.max(np.abs(default["sol"].sol(grid)[0]-analytical[0])),
                        default_annulus_difference_K=np.max(np.abs(default["sol"].sol(grid)[1]-analytical[1])))
        yield row


def brown_cases():
    length, bore, od, hole = 5000., .1214, .1397, .2159
    def pipe(resistance):
        k = np.log(od/bore)/(2*np.pi*resistance)
        return wg.uniform_wall(k, bore/2, od/2)

    steel = pipe(.000508)
    for label, target, string in (
        ("steel", 178.7, [wg.StringSegment(length, steel)]),
        ("insulated", 73.6, [wg.StringSegment(length-100., pipe(.01)), wg.StringSegment(100., steel)]),
    ):
        geometry = wg.WellGeometry(string, [wg.open_hole(0., length, hole)])
        rho = float(model.fluid_props(np.array([30.]), np.array([model.P_SURF]))[0][0])
        result = model.solve_seeded(model.exposure_from_rop(length, 12.), geometry=geometry,
                                    m_dot=rho*2.5/60., T_inj=30., T_surf=10., G=.05,
                                    target_rock_T=260., k_rock=2.5, rhocp_rock=2700*790.,
                                    Q_face=0., friction_heat=False, roughness=.00005, verbose=False)
        maxima = result["sol"].sol(np.linspace(0., length, 10001)).max(axis=1)
        measured = float(max(maxima))
        yield dict(case=label, published_C=target, calculated_C=measured,
                   difference_K=measured-target, tolerance_K=.02*target,
                   converged=result["success"], passed=result["success"] and abs(measured-target) <= .02*target)


def write_csv(path, rows):
    rows = list(rows)
    fields = tuple(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output/"kabir-comparison.csv", (r for name, kw in cases() for r in comparisons(name, kw)))
    write_csv(args.output/"brown-comparison.csv", brown_cases())


if __name__ == "__main__":
    main()
