"""Public call defaults for circulating temperatures."""
from borethm import geo_constants as C
from borethm import model1_coupled as _model


def circulating_temperatures(m_dot=2.0, T_inj=40.0, G=C.GEOTHERM_GRADIENT,
                            T_surf=C.SURFACE_TEMP, target_rock_T=C.TARGET_ROCK_TEMP,
                            Q_face=28000.0, t_years=1.0, pipe=None, k_rock=C.K_ROCK,
                            n_nodes=160, verbose=False, geotherm=None,
                            target_depth=None, geometry=None, exposure=None, fluid=None,
                            rhocp_rock=C.RHO_ROCK * C.CP_ROCK, friction_heat=False,
                            tfa=_model.BIT_TFA_DEFAULT, film_mult=1.0, breaks=(),
                            init=None, P_surface=_model.P_SURF,
                            hydraulics_model='v1.6.0', surface=None, transitions='abrupt',
                            rock_response=None, annulus_heat=None, annulus_model='v1.6.0'):
    """Compute circulating bore and annulus temperatures along a well.

    Supply either a PipeType or a WellGeometry. Mass flow m_dot is kg/s;
    T_inj, T_surf and target_rock_T are degrees C; G is K/m; Q_face is W.
    Rock conductivity k_rock is W/(m K), rhocp_rock is J/(m3 K), and
    t_years is years. A geotherm maps true vertical depth in m to degrees C;
    exposure maps measured depth in m to seconds and overrides t_years.
    The circulation rock term floors exposure at 3,600 s, or t_years at
    0.001 years (about 8.8 hours) when exposure=None. These floors apply
    only to circulation. rock_response='cylinder' uses the exact
    constant-wall-temperature step response of a cylindrical hole, and
    'logarithmic' the original quasi-steady term ln(1 + 2 sqrt(alpha t)/r).
    None selects cylinder with v1.6.0 and logarithmic with v1.5.0, which
    accepts only the logarithmic term. annulus_heat is an optional callable
    returning heat [W/m] released into the annulus fluid at measured depth
    [m], for example rotary friction from rotary_heat.partition; v1.5.0
    rejects it. Heat released at the bit is part of Q_face.
    annulus_model 'v1.6.0' is the released annulus heat transfer and the
    apparent-viscosity criterion for laminar flow of a Bingham mud.
    'herschel-bulkley' is a development candidate: the Founargiotakis slot
    model of a Herschel-Bulkley mud (fluid.rheology, a
    fluids.HerschelBulkley) for the annulus pressure loss and flow regime,
    and Gnielinski's annulus correlation on the wall viscosity and laminar
    annulus values for each wall, blended over the same transition band.
    'herschel-bulkley-erge' is the same with the transition band of Erge et
    al. (2015) and Gnielinski on the plastic viscosity. v1.5.0 accepts only
    'v1.6.0'.
    The separate radial wall-temperature solver uses its supplied state
    durations, with fluid-temperature and film-coefficient boundaries from
    circulation. The exposure floors set no breakout formation delay.
    With a geotherm and a pipe, target_depth must give the measured depth
    in m. Geometry supplies the depth when given. P_surface is absolute
    pressure [Pa], default 100,000 Pa. Property pressures follow the
    approximate hydrostatic profile P_surface + 10,000 Pa/m times true
    vertical depth. tfa is the bit nozzle flow area in m2. Friction heating
    is optional; film_mult
    scales the annulus film coefficient. breaks are measured depths in m;
    init is a previous circulation result used to seed the solver.

    hydraulics_model selects v1.6.0's shared Bingham/Newtonian pressure
    and dissipation kernel, or the exact v1.5.0 legacy calculation.
    surface is a SurfaceLoss, included in standpipe pressure with no
    downhole heat. transitions is abrupt or the zero-local-loss gradual
    idealisation. New geometry fields supply connection and tool losses.
    energy_check reports assigned and applied heat in W when enabled.
    Residuals above 1 W or 0.1% of power, whichever is larger, are flagged.
    The diagnostic does not change solver success; an unavailable diagnostic is
    returned with its error and a flag.

    fluid=None uses water. A constant fluid dictionary supplies rho [kg/m3],
    cp [J/(kg K)], mu [Pa s] and k [W/(m K)]; a fluid object may provide props.
    Return a dictionary with z [measured depth, m], Td, Tu and Trock [degrees C],
    Q_product [W], m_dot [kg/s], P_bottom [Pa absolute from that approximate
    hydrostatic profile], geometry and success, plus
    the underlying solution. Check success before using a profile.
    verbose=False suppresses the solver's printed report by default.
    """
    return _model.solve(**locals())
