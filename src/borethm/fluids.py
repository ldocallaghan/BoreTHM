"""
fluids.py
=========
The drilling fluid: water, or a water-based mud weighted with barite.

Density. The mud is water and barite. The barite's volume fraction phi is set
by the mud's density at surface conditions (T_REF, atmospheric):

    phi = (rho_surface - rho_w(T_REF)) / (rho_barite(T_REF) - rho_w(T_REF))

The surface volume fraction determines a barite mass fraction x. That mass
fraction is conserved down the hole. Water follows IAPWS-95 at the local
temperature and pressure; incompressible barite expands thermally:

    rho(T, P) = 1 / (x / rho_barite(T) + (1 - x) / rho_w(T, P))

The local volume fraction is x rho / rho_barite.

so a weighted mud expands less with temperature than water does. Other
solids (clay, polymers) are left out: at these weights barite is most of the
solids by volume.

Rheology. Bingham plastic, with the plastic viscosity and yield point of a
barite-weighted water-based mud measured by Anawe and Folayan (2018) at
80 F (PV 27 cP, YP 28 lbf/100 ft2). They give no density, so the rheology
does not vary with it. At the site flows the annulus is turbulent, where the
loss follows the plastic viscosity and not the yield point, so the
sensitivity halves the plastic viscosity. Between 80 and 200 F their plastic
viscosity falls from 27 to 9 cP, as water's viscosity does to within about
7%, so the plastic viscosity is taken as the water's at the local temperature
and pressure times its ratio at T_REF. Their yield point halves over the same
range; with no law beyond 200 F it is held at its 80 F value, which gives
the larger annular friction, the conservative side for the fracture bound.

Thermal properties. Heat capacity by mass fraction; conductivity by the
Maxwell relation for dispersed spheres.

Herschel-Bulkley annulus (development entry 6; HerschelBulkley and
hb_annulus). A mud may also carry a Herschel-Bulkley rheology,
tau = tau_0 + K gamma^n, built from its report: the 600 and 300 rpm dial
readings implied by PV and YP, and a low-shear yield stress tau_0 (for
example the 10-s gel). K follows the plastic viscosity's temperature
dependence, as the high-shear viscosity of water-based muds follows water's
(Alderman et al. 1988). tau_0 is held constant or, as an option, rises
above a characteristic temperature T* as Alderman et al. measured. The
annulus is then a slot, with laminar, transitional and turbulent flow after
Founargiotakis et al. (2008).

Hydraulics (bingham_gradient): the laminar pressure loss of a Bingham plastic
in pipe and in the narrow-slot annulus, with the apparent-viscosity Reynolds
number for the change to turbulence, after Bourgoyne et al. (1986), ch. 4;
in turbulence the plastic viscosity in the Blasius friction factor on the
hydraulic diameter, the correlation model1_coupled uses for water.

Sources:
  Anawe, P.A.L. and Folayan, J.A. (2018). Data analyses on temperature-
    dependent behaviour of water based drilling fluid rheological models.
    Data in Brief 21, 289-298. doi:10.1016/j.dib.2018.09.100
  API Specification 13A: drilling-grade barite, specific gravity 4.20.
  Robie, R.A. and Hemingway, B.S. (1995). Thermodynamic properties of
    minerals. USGS Bulletin 2131: barite heat capacity at 298 K.
  Bourgoyne, A.T., Millheim, K.K., Chenevert, M.E. and Young, F.S. (1986).
    Applied Drilling Engineering. SPE Textbook Series 2, ch. 4.
  Founargiotakis, K., Kelessidis, V.C. and Maglione, R. (2008). Laminar,
    transitional and turbulent flow of Herschel-Bulkley fluids in concentric
    annulus. Can. J. Chem. Eng. 86, 676-683.
  Alderman, N.J., Gavignet, A., Guillot, D. and Maitland, G.C. (1988).
    High-temperature, high-pressure rheology of water-based muds. SPE 18035.
  Erge, O., Ozbayoglu, E.M., Miska, S.Z., Yu, M., Takach, N., Saasen, A.
    and May, R. (2015). The effects of drillstring-eccentricity, -rotation,
    and -buckling configurations on annular frictional pressure losses while
    circulating yield-power-law fluids. SPE Drill. Complet. 30(3), 257-271.
  API Recommended Practice 13D (2010). Rheology and hydraulics of oil-well
    drilling fluids: a Fann dial degree is 1.0678 lbf/100 ft2, and 600 and
    300 rpm give 1022 and 511 1/s in the standard R1-B1 geometry.
"""
import numpy as np

from borethm import water_table as wt

T_REF = 20.0                  # C, the surface conditions a mud weight is quoted at
P_ATM = 1.0e5                 # Pa

BARITE_RHO = 4200.0           # kg/m3 at T_REF, API 13A drilling-grade barite
BARITE_CP = 436.0             # J/kg/K, 101.8 J/mol/K / 0.2334 kg/mol (Robie and Hemingway 1995)
BARITE_K = 1.5                # W/m/K; to be confirmed against a cited value
BARITE_BETA = 5.0e-5          # 1/K, volumetric thermal expansion; to be confirmed

PV_REF = 27.0e-3              # Pa s at 80 F (26.7 C), Anawe and Folayan (2018)
PV_REF_T = 26.7               # C
LBF_100FT2 = 0.4788026        # Pa
YP_REF = 28.0 * LBF_100FT2    # Pa (28 lbf/100 ft2 at 80 F), held in temperature

# conventional water-based muds start to break down above about 300 F
# (secondary source; to be confirmed against a drilling-fluids text)
MUD_T_LIMIT = 150.0           # C

RE_CRITICAL = 2100.0          # apparent-viscosity Reynolds number (Bourgoyne et al. 1986)
# Annulus flow treatments: the Bingham plastic with the apparent-viscosity
# Reynolds number above (the original), or the Herschel-Bulkley slot model
# of Founargiotakis et al. (2008) (hb_annulus).
REGIMES = ('apparent-viscosity', 'herschel-bulkley')

# Transition bands for hb_annulus (transition_band): Founargiotakis et al.
# (2008) from the Dodge-Metzner chart, or Erge et al. (2015) with the
# annulus diameter ratio.
BANDS = ('founargiotakis', 'erge')

DIAL_PA = 1.0678 * LBF_100FT2      # Pa per Fann dial degree (API RP 13D)
RATE_600 = 1022.0                  # 1/s at 600 rpm (API RP 13D)
RATE_300 = 511.0                   # 1/s at 300 rpm


def _water(T, P):
    return wt.props(np.asarray(T, float), np.asarray(P, float))


def _rho_water_ref():
    return float(np.ravel(_water([T_REF], [P_ATM])[0])[0])


class Mud:
    """A barite-weighted water-based mud of density rho_surface [kg/m3] at
    T_REF and atmospheric pressure. With rho_surface at water's density and
    yield_point 0 it is water (pv_ref None takes water's own viscosity)."""

    def __init__(self, rho_surface, pv_ref=PV_REF, yield_point=YP_REF, pv_ref_T=PV_REF_T,
                 conserve_mass=True):
        if not np.isfinite(rho_surface) or rho_surface <= 0:
            raise ValueError('surface mud density must be positive and finite')
        rho_w = _rho_water_ref()
        if rho_surface < rho_w:
            raise ValueError("a barite mud is no lighter than water")
        if rho_surface >= BARITE_RHO:
            raise ValueError('surface density implies a barite mass fraction at least one')
        self.rho_surface = float(rho_surface)
        self.phi = (rho_surface - rho_w) / (BARITE_RHO - rho_w)
        self.x = self.phi * BARITE_RHO / self.rho_surface
        # Explicit reproduction switch for the v1.3.3 regression table.
        self.conserve_mass = bool(conserve_mass)
        self.yield_point = float(yield_point)
        mu_w_ref = float(np.ravel(_water([pv_ref_T], [P_ATM])[2])[0])
        self.mu_ratio = 1.0 if pv_ref is None else pv_ref / mu_w_ref
        # plastic viscosity at the reference state, for HerschelBulkley's K(T)
        self.pv_ref = mu_w_ref * self.mu_ratio
        # optional Herschel-Bulkley rheology for annulus_model 'herschel-bulkley'
        self.rheology = None

    @property
    def sg(self):
        return self.rho_surface / 1000.0

    def props(self, T, P):
        """rho, cp, mu (the plastic viscosity), k at temperature T [C] and
        pressure P [Pa absolute], as model1_coupled.fluid_props."""
        rho_w, cp_w, mu_w, k_w = _water(T, P)
        if self.x == 0.0:
            return rho_w, cp_w, mu_w * self.mu_ratio, k_w
        T = np.asarray(T, float)
        rho_b = BARITE_RHO / (1.0 + BARITE_BETA * (T - T_REF))
        if self.conserve_mass:
            rho = 1.0 / (self.x / rho_b + (1.0 - self.x) / rho_w)
            phi = self.x * rho / rho_b
            x_b = self.x
        else:
            phi = self.phi
            rho = phi * rho_b + (1.0 - phi) * rho_w
            x_b = phi * rho_b / rho
        cp = x_b * BARITE_CP + (1.0 - x_b) * cp_w
        # Maxwell: spheres of conductivity k_b at volume fraction phi in water
        k_b = BARITE_K
        k = k_w * (k_b + 2 * k_w + 2 * phi * (k_b - k_w)) / (k_b + 2 * k_w - phi * (k_b - k_w))
        return rho, cp, mu_w * self.mu_ratio, k


def water():
    """Water as a Mud: no barite, no yield point, water's viscosity."""
    return Mud(_rho_water_ref(), pv_ref=None, yield_point=0.0)


def bingham_turbulent(rho, mu_p, tau_y, v, D, annulus):
    """True where a Bingham plastic is turbulent by the apparent-viscosity
    Reynolds number of bingham_gradient."""
    rho, mu_p, D = (np.asarray(x, float) for x in (rho, mu_p, D))
    v = np.maximum(np.abs(np.asarray(v, float)), 1e-9)
    mu_a = mu_p + tau_y * D / ((8.0 if annulus else 6.0) * v)
    return rho * v * D / mu_a > RE_CRITICAL


def bingham_gradient(rho, mu_p, tau_y, v, D, annulus):
    """Frictional pressure gradient [Pa/m] of a Bingham plastic at mean
    velocity v in a pipe of diameter D, or an annulus of hydraulic diameter D
    (outer less inner diameter). Laminar, from the plug-flow limits of
    Bourgoyne et al. (1986), ch. 4:

        pipe:    32 mu_p v / D^2 + 16 tau_y / (3 D)
        annulus: 48 mu_p v / D^2 +  6 tau_y / D        (narrow slot)

    (in field units mu_p v / (1500 d^2) + tau_y / (225 d) and
    mu_p v / (1000 (d2 - d1)^2) + tau_y / (200 (d2 - d1)), psi/ft). The flow
    is turbulent when the Reynolds number on the apparent viscosity, the
    Newtonian viscosity giving the same laminar loss, exceeds RE_CRITICAL;
    then the Blasius friction factor on the plastic viscosity."""
    rho, mu_p, v, D = (np.asarray(x, float) for x in (rho, mu_p, v, D))
    v = np.maximum(np.abs(v), 1e-9)
    if annulus:
        lam = 48.0 * mu_p * v / D ** 2 + 6.0 * tau_y / D
        mu_a = mu_p + tau_y * D / (8.0 * v)
    else:
        lam = 32.0 * mu_p * v / D ** 2 + 16.0 * tau_y / (3.0 * D)
        mu_a = mu_p + tau_y * D / (6.0 * v)
    Re_a = rho * v * D / mu_a
    turb = 0.316 * (rho * v * D / mu_p) ** -0.25 * rho * v ** 2 / (2.0 * D)
    return np.where(Re_a > RE_CRITICAL, turb, lam), Re_a


class HerschelBulkley:
    """Herschel-Bulkley rheology, tau = tau_0 + K gamma^n, of a mud report.

    from_report takes the plastic viscosity PV [cP], yield point YP and a
    low-shear yield stress tau_0 [both lbf/100 ft2, i.e. Fann dial degrees]
    and uses the dial readings they imply, R600 = 2 PV + YP and
    R300 = PV + YP:

        n = ln((R600 - tau_0) / (R300 - tau_0)) / ln(1022 / 511)
        K = (R300 - tau_0) DIAL_PA / 511^n

    K is taken at the mud's reference state and scales with its plastic
    viscosity, K(T, P) = K mu_p(T, P) / mu_p,ref. tau_0 is constant, or with
    rise = (T_star [K], E_H [K]) follows Alderman et al. (1988, eqs. 8-9):

        tau_0(T) = tau_0                                 T <= T*
        tau_0(T) = tau_0 exp(E_H (1/T* - 1/T))           T >  T*
    """

    def __init__(self, tau0, n, K, rise=None):
        if not (np.isfinite(tau0) and tau0 >= 0):
            raise ValueError('yield stress must be non-negative')
        if not (np.isfinite(n) and 0 < n <= 2 and np.isfinite(K) and K > 0):
            raise ValueError('flow index and consistency must be positive')
        if rise is not None and not (len(rise) == 2 and rise[0] > 0 and rise[1] >= 0):
            raise ValueError('rise is (T_star [K] > 0, E_H [K] >= 0)')
        self.tau0, self.n, self.K = float(tau0), float(n), float(K)
        self.rise = None if rise is None else (float(rise[0]), float(rise[1]))

    @classmethod
    def from_report(cls, pv_cP, yp, tau0, rise=None):
        r600, r300 = 2.0 * pv_cP + yp, pv_cP + yp
        if not (0 <= tau0 < r300):
            raise ValueError('the low-shear yield stress must lie below the 300 rpm reading')
        n = np.log((r600 - tau0) / (r300 - tau0)) / np.log(RATE_600 / RATE_300)
        K = (r300 - tau0) * DIAL_PA / RATE_300 ** n
        return cls(tau0 * DIAL_PA, n, K, rise)

    def at(self, T_C, mu, mud):
        """tau_0 [Pa], K [Pa s^n] and n at temperature T_C, where mu is the
        mud's plastic viscosity there (fluid_props)."""
        T_C, mu = np.broadcast_arrays(np.asarray(T_C, float), np.asarray(mu, float))
        tau0 = np.full(T_C.shape, self.tau0)
        if self.rise is not None and self.tau0 > 0:
            # the solver can try temperatures outside the physical range; the
            # loss model clips the same way
            t_star, e_h = self.rise
            T_K = np.clip(T_C, 1.0, 480.0) + 273.15
            tau0 = tau0 * np.exp(e_h * np.maximum(1.0 / t_star - 1.0 / T_K, 0.0))
        return tau0, self.K * mu / mud.pv_ref, self.n


def _slot_velocity(tau_w, tau0, K, n, h):
    """Mean velocity of laminar Herschel-Bulkley flow in a slot of gap h at
    wall shear stress tau_w (Founargiotakis et al. 2008, eq. 5)."""
    m = 1.0 / n
    xi = np.clip(tau0 / tau_w, 0.0, 1.0)
    return (h / 2.0) * (tau_w / K) ** m * (1.0 - xi) ** (m + 1) * (xi + m + 1) / ((m + 1) * (m + 2))


def dodge_metzner(re, n_prime, iterations=5):
    """Fanning friction factor of Dodge and Metzner (1959) as adjusted to
    the annulus by Founargiotakis et al. (2008, eq. 16):

        1/f^0.5 = (4 / n'^0.75) log10(Re f^(1 - n'/2)) - 0.395 / n'^1.2

    solved for x = f^-0.5 by Newton's method."""
    re, n_prime = np.broadcast_arrays(np.asarray(re, float), np.asarray(n_prime, float))
    a = 4.0 / n_prime ** 0.75
    b = a * np.log10(re) - 0.395 / n_prime ** 1.2
    c = a * (2.0 - n_prime) / np.log(10.0)
    # start from the explicit fit f = 0.0791 Re^-0.25 / n'^0.5 (within ~20%)
    x = np.sqrt(n_prime / 0.0791) * np.maximum(re, 1.0) ** 0.125
    for _ in range(iterations):
        g = x - b + c * np.log(np.maximum(x, 1e-12))
        x = np.maximum(x - g / (1.0 + c / x), 0.5)
    return x ** -2.0


def _illinois(residual, lo, hi, r_lo, r_hi, active, iterations, tol=1e-10):
    """Vectorised Illinois (regula falsi) root of residual(x) on [lo, hi],
    where r_lo < 0 < r_hi elementwise; only active elements move."""
    side = np.zeros(lo.shape)
    x = lo.copy()
    for _ in range(iterations):
        x = np.where(active, (lo * r_hi - hi * r_lo) / (r_hi - r_lo), x)
        r = residual(x)
        upper = r > 0
        hi, r_hi = np.where(active & upper, x, hi), np.where(active & upper, r, r_hi)
        lo, r_lo = np.where(active & ~upper, x, lo), np.where(active & ~upper, r, r_lo)
        # Illinois: halve the stale end's residual after two moves on one side
        r_lo = np.where(active & upper & (side == 1), r_lo / 2, r_lo)
        r_hi = np.where(active & ~upper & (side == -1), r_hi / 2, r_hi)
        side = np.where(upper, 1, -1)
        active = active & (hi - lo > tol * np.maximum(np.abs(hi), 1.0))
        if not np.any(active):
            break
    return x


def transition_band(n_prime, band='founargiotakis', kappa=None, eccentricity=0.0):
    """Start and end of the laminar-turbulent transition, Re1 and Re2, on
    the generalised Reynolds number 12 rho V^2 / tau_w of hb_annulus.

    founargiotakis: Re1 = 3250 - 1150 n', Re2 = 4150 - 1150 n' (Founargiotakis
    et al. 2008, eqs. 18-19, after Guillot from Dodge and Metzner's chart).

    erge: Erge et al. (2015, eqs. 17-18), with the diameter ratio kappa =
    d_inner / d_outer and eccentricity e = 2E / (d_outer - d_inner):

        Re1 = 2100 [N^0.331 (1 + 1.402 kappa - 0.977 kappa^2) - 0.019 e N^-0.868 kappa]
        Re2 = 2900 N^(-0.039 Re1^0.307)

    with N = n'. Eq. 17 is stated for 0.1 < N < 1. Eq. 18 was fitted at
    kappa = 0.5 for 0.15 < N < 0.4; outside that range it is evaluated at
    the nearest end, which keeps Re2 above Re1 for every N up to 1."""
    n_prime = np.asarray(n_prime, float)
    if band == 'founargiotakis':
        return 3250.0 - 1150.0 * n_prime, 4150.0 - 1150.0 * n_prime
    if band != 'erge':
        raise ValueError(f'band must be one of {BANDS}')
    if kappa is None:
        raise ValueError('the erge band needs the diameter ratio kappa')
    kappa = np.asarray(kappa, float)
    re1 = 2100.0 * (n_prime ** 0.331 * (1.0 + 1.402 * kappa - 0.977 * kappa ** 2)
                    - 0.019 * eccentricity * n_prime ** -0.868 * kappa)
    re2 = 2900.0 * np.clip(n_prime, 0.15, 0.4) ** (-0.039 * re1 ** 0.307)
    return re1, re2


def _power_law_annulus(rho, K, n, v, gap, band, kappa):
    """hb_annulus with no yield stress, solved explicitly. For a power-law
    fluid n' = n and K' = K ((2n + 1) / 3n)^n at every wall stress
    (Founargiotakis et al. 2008, eqs. 14-15 with xi = 0), so the generalised
    Reynolds number does not depend on the wall stress: Re = 12 rho V^2 /
    tau_lam, with the laminar stress tau_lam = K ((2n + 1) / 3n 12 V / gap)^n
    (eq. 5 with xi = 0). The friction factor then follows directly, and
    tau_w = f rho V^2 / 2. hb_annulus's iterative solution gives the same
    root, since there its residual has a single crossing."""
    m = 1.0 / n
    g_lam = (m + 2.0) / 3.0 * 12.0 * v / gap          # (2n+1)/(3n) x 12 V / gap
    tau_lam = K * g_lam ** n
    re = 12.0 * rho * v ** 2 / tau_lam
    n_p = n
    k_p = K * ((m + 2.0) / 3.0) ** n
    re1, re2 = transition_band(n_p, band, kappa)
    blend = np.clip((re - re1) / (re2 - re1), 0.0, 1.0)
    both = dodge_metzner(np.concatenate([re2.ravel(), np.maximum(re, re2).ravel()]),
                         np.concatenate([n_p.ravel(), n_p.ravel()]))
    f_t2, f_dm = both[:re.size].reshape(re.shape), both[re.size:].reshape(re.shape)
    f_lam = 24.0 / re
    f = np.where(re <= re1, f_lam, np.where(re >= re2, f_dm, 24.0 / re1 + blend * (f_t2 - 24.0 / re1)))
    f = np.maximum(f, f_lam)
    tau_w = f * rho * v ** 2 / 2.0
    gamma_w = (tau_w / K) ** m
    gamma_nw = 3.0 / (m + 2.0) * gamma_w                # the laminar relation at this wall stress
    return dict(f=f, re=re, n_prime=n_p, k_prime=k_p, re1=re1, re2=re2, blend=blend, gamma_nw=gamma_nw,
                tau_w=tau_w, gradient=4.0 * tau_w / gap, mu_a=rho * v * gap / re, mu_w=tau_w / gamma_w)


def hb_annulus(rho, tau0, K, n, v, gap, iterations=40, band='founargiotakis', kappa=None):
    """Herschel-Bulkley flow in a concentric annulus modelled as a slot,
    after Founargiotakis et al. (2008). gap is d_outer - d_inner [m], so the
    slot of their eqs. 2-5 has h = gap / 2. Returns a dict of arrays:

    tau_w     wall shear stress [Pa]
    gradient  frictional pressure gradient 4 tau_w / gap = 2 f rho V^2 / gap [Pa/m] (eq. 17)
    f         Fanning friction factor
    re        generalised Reynolds number rho V^(2-n') gap^n' / (K' 12^(n'-1)) (eq. 13)
    n_prime   local flow index (eq. 14); k_prime, K' (eq. 15)
    re1, re2  start and end of transition (transition_band; by default 3250 - 1150 n'
              and 4150 - 1150 n', eqs. 18-19; band 'erge' needs kappa = d_inner / d_outer)
    blend     0 below Re1, 1 above Re2, linear in Re between (eq. 21)
    mu_a      Metzner-Reed apparent viscosity rho V gap / re
    mu_w      wall viscosity tau_w / gamma_w, with the wall shear rate
              gamma_w = ((tau_w - tau_0) / K)^(1/n) of the rheology at the wall stress
    gamma_nw  Newtonian wall shear rate 12 V_lam(tau_w) / gap (eq. 9)

    The laminar wall stress solves eq. 5 at the mean velocity. Where its
    Reynolds number exceeds Re1 the flow is transitional or turbulent: for a
    wall stress tau_w the laminar relation gives gamma_Nw, n' and K', the
    friction factor is Dodge-Metzner (eq. 16) above Re2 or the linear
    interpolation between 24/Re1 and the Dodge-Metzner value at Re2 (eqs.
    20-21), and tau_w = f rho V^2 / 2, solved above the laminar stress on
    ln tau_w (their fig. 2 bisects; here regula falsi, Illinois variant).

    The friction factor is bounded below by the laminar 24/Re at the same
    Re. In Dodge and Metzner's chart the transitional and turbulent curves
    lie above the laminar line; their correlation falls below it only for
    n' under about 0.4, outside their data (n' 0.36-1.0), which a yield
    stress near the wall stress produces. With the bound the wall stress is
    never below the laminar one, and a root always lies above it."""
    rho, tau0, K, n, v, gap = np.broadcast_arrays(*(np.asarray(x, float) for x in (rho, tau0, K, n, v, gap)))
    if kappa is not None:
        kappa = np.broadcast_to(np.asarray(kappa, float), rho.shape)
    v = np.maximum(np.abs(v), 1e-9)
    h = gap / 2.0

    def state(tau_w):
        v_lam = _slot_velocity(tau_w, tau0, K, n, h)
        g_nw = np.maximum(12.0 * v_lam / gap, 1e-300)
        xi = np.clip(tau0 / tau_w, 0.0, 1.0)
        n_p = n * (1 - xi) * (n * xi + n + 1) / (1 + n + 2 * n * xi + 2 * n * n * xi * xi)
        n_p = np.maximum(n_p, 1e-3)
        k_p = tau_w / g_nw ** n_p
        re = rho * v ** (2 - n_p) * gap ** n_p / (k_p * 12.0 ** (n_p - 1))
        re1, re2 = transition_band(n_p, band, kappa)
        blend = np.clip((re - re1) / (re2 - re1), 0.0, 1.0)
        both = dodge_metzner(np.concatenate([re2.ravel(), np.maximum(re, re2).ravel()]),
                             np.concatenate([n_p.ravel(), n_p.ravel()]))
        f_t2, f_dm = both[:re.size].reshape(re.shape), both[re.size:].reshape(re.shape)
        f_lam = 24.0 / np.maximum(re, 1e-300)
        f = np.where(re <= re1, f_lam,
                     np.where(re >= re2, f_dm, 24.0 / re1 + blend * (f_t2 - 24.0 / re1)))
        f = np.maximum(f, f_lam)
        return dict(f=f, re=re, n_prime=n_p, k_prime=k_p, re1=re1, re2=re2, blend=blend, gamma_nw=g_nw)

    if not np.any(tau0):
        return _power_law_annulus(rho, K, n, v, gap, band, kappa)

    # laminar: ln tau_w with V_lam(tau_w) = V, monotonic in tau_w
    def laminar(x):
        return np.log(_slot_velocity(np.exp(x), tau0, K, n, h) / v)

    lo = np.log(tau0 * (1 + 1e-9) + 1e-12)
    hi = np.log(tau0 + 1.0)
    r_hi = laminar(hi)
    for _ in range(200):
        short = r_hi <= 0
        if not np.any(short):
            break
        hi = np.where(short, hi + np.log(10.0), hi)
        r_hi = np.where(short, laminar(hi), r_hi)
    r_lo = np.maximum(np.nan_to_num(laminar(lo), nan=-1e3, neginf=-1e3), -1e3)
    r_lo = np.minimum(r_lo, -1e-300)
    x = _illinois(laminar, lo, hi, r_lo, r_hi, np.ones(lo.shape, bool), iterations)
    tau_w = np.exp(x)
    st = state(tau_w)
    moving = st['re'] > st['re1']
    if np.any(moving):
        def excess(x):
            t = np.exp(x)
            return 1.0 - state(t)['f'] * rho * v ** 2 / (2.0 * t)
        lo = np.log(tau_w)
        hi = np.log(np.maximum(10.0 * tau_w, rho * v ** 2))
        r_lo, r_hi = excess(lo), excess(hi)
        for _ in range(50):
            low = moving & (r_hi <= 0)
            if not np.any(low):
                break
            hi = np.where(low, hi + np.log(10.0), hi)
            r_hi = np.where(low, excess(hi), r_hi)
        # at the laminar stress the bounded friction gives excess <= 0
        settled = moving & (r_lo >= 0)
        active = moving & ~settled
        x = _illinois(excess, lo, hi, np.minimum(r_lo, -1e-300), r_hi, active, iterations)
        tau_w = np.where(active, np.exp(x), tau_w)
        st = state(tau_w)
    gamma_w = (np.maximum(tau_w - tau0, 1e-300) / K) ** (1.0 / n)
    st.update(tau_w=tau_w, gradient=4.0 * tau_w / gap, mu_a=rho * v * gap / st['re'], mu_w=tau_w / gamma_w)
    return st
