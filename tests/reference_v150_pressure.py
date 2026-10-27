"""Frozen pressure reference from f61a5d918285948c7254f1458c83992cdfb935cb.

The calculation is copied unchanged from BoreTHM v1.5.0. Shared property
and friction helpers are unchanged by v1.6.0. Licensed under Apache-2.0.
"""
import numpy as np
from borethm.model1_coupled import (
    _pieces, P_of_z, fluid_props, friction_factor, nozzle_dp,
    BIT_TFA_DEFAULT, P_SURF, G_GRAV, PUMP_LIMIT, HOLE_CLEANING_V,
)


def frozen_hydraulics(m_dot, geometry, result=None, T_avg=80.0, tfa=BIT_TFA_DEFAULT,
               friction="blasius", bit=True, fluid=None, P_surface=P_SURF):
    """Pressure losses along the string and annulus, bit nozzle loss,
    standpipe pressure and annular velocity.

    With a circulating_temperatures result, water properties use each piece's
    bore or annulus temperature and the approximate absolute pressure
    P_surface + 10,000 Pa/m times true vertical depth. The standpipe pressure
    includes the buoyancy of the hot annulus against the cold bore. Without
    one, properties are at T_avg and mid-depth pressure throughout.

      SPP = dP_string + dP_bit + dP_annulus + integral (rho_ann - rho_bore) g dTVD

    The first two arguments, m_dot [kg/s] and geometry [WellGeometry],
    are required. result is a circulating_temperatures result; T_avg is
    degrees C, tfa is m2 and P_surface is Pa absolute, default 100,000 Pa.
    bit enables nozzle loss;
    friction selects the friction law. fluid=None uses water; otherwise
    use a constant property dictionary or an object providing props.
    Return a dictionary with dp_string, dp_annulus, dp_bit, dp_buoyancy and
    spp [Pa as pressure differences]. The per-piece dp_bore and dp_ann
    entries are also pressure differences [Pa]. Other outputs include
    annular velocities [m/s], hydraulic pump power [W], and flow diagnostics.
    """
    top, bot = _pieces(geometry)
    mid = 0.5 * (top + bot)
    g = geometry.at(mid)
    dtvd = geometry.survey.tvd(bot) - geometry.survey.tvd(top)
    if result is None:
        P = P_of_z(geometry.survey.tvd(geometry.md_bit / 2), P_surface)
        rho, _, mu, _ = (float(np.ravel(x)[0]) for x in
                         fluid_props(np.array([T_avg]), np.array([P]), fluid))
        rho_b = rho_a = np.full_like(mid, rho)
        mu_b = mu_a = np.full_like(mid, mu)
        rho_bit = rho
    else:
        P = P_of_z(g["tvd"], P_surface)
        T_b = np.interp(mid, result["z"], result["Td"])
        T_a = np.interp(mid, result["z"], result["Tu"])
        rho_b, _, mu_b, _ = fluid_props(T_b, P, fluid)
        rho_a, _, mu_a, _ = fluid_props(T_a, P, fluid)
        rho_bit = float(rho_b[-1])

    tau_y = getattr(fluid, "yield_point", 0.0)

    def loss(rho, mu, area, Dh, annulus):
        v = m_dot / (rho * area)
        if tau_y > 0.0:     # a Bingham plastic (fluids.Mud)
            from borethm import fluids
            return fluids.bingham_gradient(rho, mu, tau_y, v, Dh, annulus)[0] * (bot - top), v
        f = friction_factor(rho * v * Dh / mu, friction)
        return f * ((bot - top) / Dh) * 0.5 * rho * v ** 2, v

    dp_bore, _ = loss(rho_b, mu_b, g["A_bore"], g["Dh_bore"], False)
    dp_ann, v_ann = loss(rho_a, mu_a, g["A_ann"], g["Dh_ann"], True)
    dp_bit = nozzle_dp(m_dot, rho_bit, tfa) if bit else 0.0
    dp_buoy = float(np.sum((rho_a - rho_b) * G_GRAV * dtvd))
    spp = float(dp_bore.sum() + dp_ann.sum()) + dp_bit + dp_buoy
    return dict(
        pieces=[dict(md_top=a, md_bottom=b, dp_bore=x, dp_ann=y, v_ann=v)
                for a, b, x, y, v in zip(top, bot, dp_bore, dp_ann, v_ann)],
        dp_string=float(dp_bore.sum()), dp_annulus=float(dp_ann.sum()),
        dp_bit=dp_bit, dp_buoyancy=dp_buoy, spp=spp,
        over_pump_limit=spp > PUMP_LIMIT,
        v_ann_min=float(v_ann.min()), cleans_hole=float(v_ann.min()) >= HOLE_CLEANING_V,
        pump_power=spp * m_dot / float(np.mean(rho_b)))
