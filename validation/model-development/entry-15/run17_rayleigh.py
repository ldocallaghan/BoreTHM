"""Screen run 17 static coupling at each event's final bit depth.

This diagnostic uses the last observed circulation at each depth. It
lumps older circulating exposure into the same boundary conditions.
"""
from pathlib import Path

import numpy as np

from borethm import model1_coupled as model
from borethm.run_in_column import RadialColumn
from borethm.studies import validate_forge16a as forge16a
from borethm.studies import validate_forge16b as forge16b
from borethm.studies import validate_forge16b_wholewell as whole
from borethm.wall_thermal import NU_LAMINAR
from validation.benchmarks.entry15_rayleigh import rayleigh
from validation.benchmarks.run_circulation import write_csv
from validation.forge16b.sanvean.build_extracts import timestamp
from validation.forge16b.sanvean.trip_history import rows
from validation.scoreboard.scoreboard import PLAN, ROOT, geometry, read_json

HERE = Path(__file__).parent
FORGE = ROOT/"validation/forge16b"


def conditioning(event, plan, form, clocks, definitions):
    time, clock, depth = clocks
    if event["status"] != "observed":
        raise ValueError(f"{event['event']}: missing circulation input")
    md = float(event["depth_ft"])*forge16b.FT
    bit_ft = float(event["mean_bit_ft"])
    inlet = float(event["mean_inlet_C"])
    flow = float(event["mean_flow_gpm"])*forge16b.GPM
    prior_run = 16 if event["event_kind"] == "trip_stage" else 17
    g = geometry(dict(well="16B", run=str(prior_run), eow_bha=prior_run,
                      bit_ft=bit_ft), plan, "current")
    stamp = timestamp(event["circulation_end"])
    exposure = model.exposure_from_history(clock, depth, float(np.interp(stamp, time, clock)))
    smooth = model.smooth_exposure(exposure, g.md_bit)
    rho = model.fluid_props(np.array([inlet]), np.array([model.P_SURF]))[0][0]
    mass_flow = rho*flow
    tfa = sum(np.pi/4*(int(j)*forge16b.INCH/32)**2
              for j in definitions[prior_run]["jets_32nds"].split(";"))
    result = model.solve_seeded(
        smooth, model.exposure_breaks(smooth, g.md_bit), m_dot=mass_flow, T_inj=inlet,
        geometry=g, geotherm=form, target_rock_T=float(form(g.survey.tvd(g.md_bit))),
        k_rock=forge16b.K_ROCK, rhocp_rock=forge16b.RHOCP_ROCK,
        friction_heat=True, Q_face=0., tfa=tfa, physics="v1.8.0", verbose=False)
    if not result["success"]:
        raise RuntimeError(f"{event['event']}: conditioning solve did not converge")
    return g, result, mass_flow, exposure, stamp, prior_run


def audit():
    plan = read_json(PLAN)
    form = forge16a.formation("216", forge16a.survey())[0]
    _, time, clock, depth = whole.clock(FORGE)
    definitions = {int(row["eow_bha"]): row for row in rows(FORGE/"run_definitions.csv")}
    for event in rows(HERE/"run17-boundaries.csv"):
        md = float(event["depth_ft"])*forge16b.FT
        g, result, mass_flow, exposure, stamp, prior_run = conditioning(
            event, plan, form, (time, clock, depth), definitions)
        station = np.array([min(md, g.md_bit-1e-4)])
        dimensions = g.at(station)
        tu = float(result["sol"].sol(station)[1, 0])
        tvd = float(g.survey.tvd(md))
        pressure = model.P_of_z(tvd)
        current = geometry(dict(well="16B", run="17", eow_bha=17,
                                bit_ft=md/forge16b.FT), plan, "current")
        local = current.at(np.array([md-1e-4]))
        inner, radius = float(local["r_out"][0]), float(local["r_wall"][0])
        circulated = max(float(exposure(md)), float(event["duration_s"]))
        off = timestamp(event["end_pason"])-stamp
        column = RadialColumn(radius, float(form(tvd)), forge16b.K_ROCK,
                              forge16b.RHOCP_ROCK, circulated+off)
        _, h_outer = model.annulus_films(
            mass_flow, dimensions, np.array([tu]), np.array([pressure]), band="erge", viscosity="plastic")
        column.circulate(circulated, tu, float(h_outer[0]))
        density, cp, _, k = (float(x[0]) for x in model.fluid_props(
            np.array([tu]), np.array([pressure])))
        film = NU_LAMINAR*k/(2*(radius-inner))
        capacity = density*cp*np.pi*(radius**2-inner**2)
        recovered = column.shut_in(off, capacity, film)
        yield dict(event=event["event"], kind=event["event_kind"], conditioning_run=prior_run,
                   depth_m=md, lumped_circulation_s=circulated, static_s=off,
                   initial_annulus_C=tu, circulating_film_W_m2_K=float(h_outer[0])) | rayleigh(
                       None, column.temperature_C, recovered.T_wall[-1],
                       pressure, radius, inner, md)


if __name__ == "__main__":
    write_csv(HERE/"run17-rayleigh.csv", audit())
