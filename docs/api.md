# Python API

Names listed here and in `borethm.__all__` follow semantic versioning from 1.4.0 and change incompatibly only with a major release. Other modules and objects are internal and may change in any release.

Import these names from `borethm`. Temperatures are in degrees C and pressures in Pa unless stated otherwise; SG denotes density relative to 1,000 kg/m3.

Construct a pipe with `uniform_wall` or `PipeType` and `Layer`. `WellGeometry.single` builds a single-segment well; `StringSegment`, `HoleInterval`, `open_hole`, `cased` and `Survey` describe other geometries. `WallState` supplies a wall history and `ToolLump.of_pipe` constructs the heat capacities needed by `tool_trip_in`.

```python
from borethm import uniform_wall, WellGeometry, thermal_hoop_stress
pipe = uniform_wall(k=45.0, r_in=0.05, r_out=0.06)
well = WellGeometry.single(3000.0, pipe, r_hole=0.11)
stress_Pa = thermal_hoop_stress(300.0, 150.0)
```

## Pressure conventions

Absolute pressure is measured from vacuum; gauge pressure is measured from
the model's atmosphere, P_SURF = 0.1 MPa absolute. Thus P_absolute equals
P_gauge + 0.1 MPa. Pressure arguments and outputs use Pa unless labelled otherwise.

water_properties uses absolute pressure. circulating_temperatures and
hydraulics take an absolute P_surface, defaulting to 0.1 MPa, for their
approximate hydrostatic property-pressure profile. The circulation result's
P_bottom is also absolute.

The wall-pressure budget uses gauge pressure, as do the in-situ stresses,
pore pressures and fluid-support pressures used in the stability comparisons.
mud_window takes a gauge P_surface, defaulting to zero. These conventions
also apply to StressProfile and the pressure arguments of breakout_check
and breakout_width. Rock strengths and thermal-stress changes use Pa and
receive no atmospheric offset.

Standpipe pressure and friction losses are pressure differences. In a
hydraulics result, spp, dp_string, dp_annulus, dp_bit and dp_buoyancy are
differences, as are the per-piece dp_bore and dp_ann entries. Their values
receive no atmospheric offset.

## HydraulicJoint

```python
HydraulicJoint(outer_diameter: float, bore_diameter: float, restriction_length: float, spacing: float, transition: str = 'abrupt', source: str = '') -> None
```

Repeated connection geometry [m], independent of thermal joints.

restriction_length is the effective narrow-passage length; spacing is
the connection pitch. transition is abrupt or the zero-local-loss
gradual idealisation. source records the catalogue and assumptions.

## LocalLoss

```python
LocalLoss(bore_coefficient: float = 0.0, annulus_coefficient: float = 0.0, bore_reference_area: float | None = None, annulus_reference_area: float | None = None, source: str = '') -> None
```

Additional component K values; reference areas are m2.

None uses that component's body bore/annulus area. These coefficients
must exclude geometric transitions already represented automatically.

## ReferenceToolLoss

```python
ReferenceToolLoss(dp_ref: float, flow_ref: float, density_ref: float, basis: str = 'additional', span_segments: int = 1, source: str = '', flow_range: tuple | None = None, temperature_max_C: float | None = None, include_boundary_changes: bool = True, unresolved: bool = False) -> None
```

Tool pressure loss [Pa] at reference flow [m3/s] and density [kg/m3].

Scales as density times flow squared. total_internal replaces internal
passage losses over span_segments contiguous segments, including the
segment carrying this input; additional supplies an extra restriction.
Optional flow_range is m3/s and temperature_max_C is a qualification.
include_boundary_changes=False excludes internal entry/exit restrictions
inferred from a thermal-only bore. unresolved qualifies an omitted loss
and requires zero reference pressure; it never makes a solve fail.

## SurfaceLoss

```python
SurfaceLoss(value: float, source: str = '') -> None
```

API surface-layout coefficient, in the psi/ppg/US-gpm convention.

## HydraulicProgramme

```python
HydraulicProgramme(hydraulics_model: str = 'v1.6.0', reference: str | None = 'wu2025-with-hydraulic-allowances', segments: tuple = (), hole: tuple = (), surface: borethm.hydraulic_losses.SurfaceLoss | None = None, transitions: str = 'abrupt', joints: bool = True, tools: bool = True, joint_restriction_length: float = 0.7365999999999999, hwdp_restriction_length: float = 1.2191999999999998) -> None
```

Hydraulic mode, surface layout and reference or custom string.

Python lengths are metres and losses use SI. reference_programme()
selects the documented built-in allowances, including surface case 5.
A custom string must explicitly supply its own tool curves. Optional
hole intervals otherwise retain the reference well's casing scenario.

## evaluate

```python
evaluate(site: SiteProfile, v10=False, thermal=True, circulation='v1.3.4', coupled=None, programme=None, hydraulics_model=None, surface=None)
```

Evaluate a SiteProfile through circulation, connections and trips.

Site inputs use m, Pa, degrees C and SI thermal properties. Validate the
profile first with validate_site. Stresses and the wall-pressure budget
use Pa gauge, relative to a 0.1 MPa absolute atmosphere. Circulation
property pressures are absolute, and hydraulic losses are pressure
differences. The default circulation='v1.3.4' uses
the whole-hole programme calculation. This calculation-mode identifier
is independent of the package version. v10 selects the original model;
thermal enables wall cooling and coupled overrides the site's coupling.
Earlier circulation modes remain available for reproducing old releases.

Coupling uses the site's stiffness in thermal stress, evaluates the
drilling-rate model with the site's circulation, and iterates rate of
penetration and exposure together. For modes other than v10:

| Site flag | coupled argument | Effective flag |
|---|---|---|
| False | None | On for v1.3.3 and v1.3.4; off for earlier modes |
| True | None | On |
| Either | True | On |
| Either | False | Off |

v10 retains the site's flag for None or True; explicit False switches
it off. The input profile itself is unchanged.

Return a dictionary containing the site and target depth z [m], rock
temperature T_rock [degrees C], the circulation and operating programme,
cycle cases, mud windows, tool gates and status. Whole-programme windows
use surface fluid density [kg/m3 at 20 degrees C]; cycle SG values are
equivalent static densities. Use result_dict for a serialisable record.
This evaluation can require substantial computation.

programme overrides the site's HydraulicProgramme. hydraulics_model
optionally selects v1.6.0 or exact v1.5.0 legacy hydraulics. With
neither given, v10 and the earlier circulation modes use v1.5.0, which
also keeps the original logarithmic rock term, so they reproduce the
releases they belong to; circulation='v1.3.4' uses v1.6.0. surface
optionally overrides its SurfaceLoss. An explicit zero coefficient
disables an allowance. Unspecified settings use the effective
programme. The input SiteProfile is unchanged.

## result_dict

```python
result_dict(o, *, site_file=None)
```

Convert an evaluate result into a JSON-compatible dictionary.

Inputs and outputs retain the evaluation's units: depth [m], temperature
[degrees C], pressure [Pa], flow [kg/s or L/s as labelled], and surface
density [kg/m3 at 20 degrees C]. SG-equivalent values remain labelled SG.
Stresses, pore pressures and wall-pressure quantities are gauge.
programme.backpressure_Pa is gauge; programme.spp_Pa is a pressure
difference. The gauge reference is 0.1 MPa absolute.
Includes input sources and runtime versions; does not run calculations.
Results with components and status also include a reading of the
existing checks and controlling constraint.
site_file optionally gives the TOML path, recorded as supplied with its
current SHA-256. A previously captured {path, sha256} record may be
supplied to preserve the identity of the file loaded before evaluation.

## export_result

```python
export_result(o, path, *, site_file=None)
```

Write result_dict(o) as JSON to an explicit path.

o is an evaluate result. Values retain their labelled SI units and
temperatures in degrees C. Returns None; creates or overwrites the file.
site_file accepts the optional TOML path or captured provenance record
described in result_dict.

## SiteProfile

```python
SiteProfile(name: str, geotherm: Callable, target_depth: float, target_T: float, Sv_grad: float, K0_min: float, SHmax_over_Sv: float, rho_fluid_grad: float, k_rock: float, E_rock: float, UCS: float, T_inj: float = 40.0, stress_cases: tuple = (), stress_basis: str = 'v1.0 ratios', strength_cases: tuple = (), data_basis: dict = <factory>, geotherm_v11: Callable = None, target_depth_v11: float = None, temperature_data_to: float = None, mu: float = 0.8, coupled: bool = False, programme: borethm.programme.HydraulicProgramme | None = None) -> None
```

Site inputs for evaluate, with temperature and stress profiles.

geotherm maps depth [m] to rock temperature [degrees C]; target_depth is
m and target_T is degrees C. Sv is vertical stress; Shmin and SHmax are
minimum and maximum horizontal stress. Stress and fluid pressure
gradients are Pa/m and use the gauge convention of StressProfile;
K0_min and SHmax_over_Sv are dimensionless ratios.
k_rock is W/(m K); E_rock and UCS are Pa; T_inj is degrees C. UCS is the
uniaxial compressive strength supplied at 25 degrees C.
stress_cases contains StressProfile objects; strength_cases contains
(label, UCS [Pa]) pairs. data_basis maps input names to (basis, source).
validate_site documents accepted ranges and provenance labels.

geotherm_v11 and target_depth_v11 optionally replace geotherm and
target_depth in current evaluations; their names are compatibility
fields. temperature_data_to is the deepest measured temperature depth
[m], or None. mu is a dimensionless friction coefficient. coupled
enables the site's stiffness in the coupled thermal-stress calculation.
Construct a profile, then call validate_site.

programme optionally supplies a HydraulicProgramme. None selects the
documented reference programme during circulation. A custom string
keeps its supplied pipes and does not receive reference tool curves.

The target() method returns the effective depth [m]; temperature()
returns the effective geotherm callable. Passing v10=True selects the
original profile for historical evaluation modes.

## StressProfile

```python
StressProfile(label: str, Sv_grad: float, Shmin_grad: float, SHmax_grad: float, Sv_int: float = 0.0, Shmin_int: float = 0.0, SHmax_int: float = 0.0, Pp_grad: float = 10000.0, Pp_datum: float = 0.0, source: str = '', z_data: tuple = None, mu: float = None, regime: str = None) -> None
```

Linear in-situ stress with depth: S(z) = grad * z + intercept [Pa, z in m].

Pore pressure is Pp_grad * (z - Pp_datum) below a static fluid level at
Pp_datum [m], zero above it. z_data is the depth range [m] the magnitude data
actually cover, or None when the profile rests on regime bounds alone.

Inputs ending in _grad are Pa/m; stress intercepts are Pa gauge.
The constructor orders Sv, Shmin, then SHmax gradients. Methods Sv(z),
Shmin(z), SHmax(z) and Pp(z) return Pa gauge for depth z [m]. The gauge
reference is the model's atmosphere, 0.1 MPa absolute. mu is dimensionless;
regime is normal, strike-slip or reverse when specified.

## validate_site

```python
validate_site(site)
```

Check a SiteProfile before evaluation; return a list of warning strings.

Invalid values raise ValueError. Scalar ranges are inclusive:

| Field | Accepted range | Unit |
|---|---|---|
| effective target depth | 500 to 20,000 | m |
| target_T | 50 to 600 | degrees C |
| k_rock | 0.5 to 7 | W/(m K) |
| E_rock | 5e9 to 150e9 | Pa |
| UCS and every strength-case UCS | 10e6 to 500e6 | Pa |
| T_inj | 0 to 100 | degrees C |
| mu | 0.2 to 1.5 | dimensionless |
| rho_fluid_grad | 8,000 to 20,000 | Pa/m |
| Sv_grad | 15,000 to 35,000 | Pa/m |

The geotherm must be finite, rise through the sampled open hole and
reach target_T within 5 degrees C at the effective target depth. A
non-rising interval above the casing shoe produces a warning. Stress
profiles are sampled from the target to the shoe at 500 m intervals,
including the shoe: stresses must be finite and positive, SHmax must
be at least Shmin, and pore pressure must be below Shmin. If a regime
is supplied, its order must be normal (Sv >= SHmax >= Shmin),
strike-slip (SHmax >= Sv >= Shmin), or reverse (SHmax >= Shmin >= Sv).

Each data_basis value is a (basis, source) pair. Accepted basis labels
are: calibrated, measured, measured range, measured (lab), log-derived,
checked, regime bounds, extrapolated, regional, assumed, not reproduced,
unsourced, none. Unrecognised labels raise ValueError. Missing sources
or missing required provenance entries produce warnings; these checks
do not verify the cited measurement or publication.

These checks catch unit slips and implausible inputs. Acceptance does
not establish that every fluid state remains inside the water-property
table's temperature and absolute-pressure limits.

## load_site

```python
load_site(path)
```

Read a TOML site file and return its SiteProfile.

path is a string or path-like object. Top-level keys use SiteProfile
field names: depths are m, temperatures degrees C, stress and pressure
gradients Pa/m, stress intercepts Pa gauge, strengths and Young's
modulus Pa, and conductivity W/(m K). Ratios and friction coefficients are
dimensionless. Optional keys retain SiteProfile's defaults.

geotherm and optional geotherm_v11 are tables. A segments form gives
[depth, temperature, gradient] rows in m, degrees C and degrees C/m;
boundary='below' assigns a boundary depth to the segment starting there,
and boundary='above' to the preceding segment. A points form gives
[depth, temperature] rows and gradient_below in degrees C/m.

stress_cases is an array of StressProfile tables, with z_data as two
depths in m. Alternatively, a transitional stress_rule gives Sv_grad
[Pa/m] and source, with optional Sv_int [Pa gauge], Pp_grad [Pa/m], mu
and fractions [dimensionless]. Its defaults are transitional_bounds'
defaults, including mu=0.8, independently of the site's own mu.
strength_cases contains [label, UCS in Pa] pairs; data_basis maps input
names to [basis, source] pairs. Arrays become the corresponding tuples.

File, TOML and schema errors raise a one-line ValueError naming the
file and key. This function parses data and executes no file content.
Call validate_site on the returned profile to check physical ranges,
temperature and stress consistency, and provenance labels and sources.

## layered_geotherm

```python
layered_geotherm(points, gradient_below)
```

A geotherm from measured (depth [m], temperature [C]) points, linear
between them, and extended below the deepest at gradient_below [C/m].

## named_sites

```python
named_sites()
```

Return a dictionary mapping short site keys to SiteProfile objects.

The keys are soultz, larderello, united-downs, pannonian and newberry.
Profile depths are m, temperatures degrees C and stresses Pa.

## find_site

```python
find_site(name)
```

Find one built-in SiteProfile by key or unambiguous name substring.

name is case-insensitive; spaces match hyphens. Returns a SiteProfile
with depth [m], temperature [degrees C] and stress [Pa] inputs.
Raises ValueError for an unknown or ambiguous name.

## circulating_temperatures

```python
circulating_temperatures(m_dot=2.0, T_inj=40.0, G=0.035, T_surf=15.0, target_rock_T=450.0, Q_face=28000.0, t_years=1.0, pipe=None, k_rock=2.5, n_nodes=160, verbose=False, geotherm=None, target_depth=None, geometry=None, exposure=None, fluid=None, rhocp_rock=2700000.0, friction_heat=False, tfa=0.0007759, film_mult=1.0, breaks=(), init=None, P_surface=100000.0, hydraulics_model='v1.6.0', surface=None, transitions='abrupt', rock_response=None, annulus_heat=None, annulus_model='v1.6.0')
```

Compute circulating bore and annulus temperatures along a well.

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

## hydraulics

```python
hydraulics(m_dot, geometry, result=None, T_avg=80.0, tfa=0.0007759, friction='blasius', bit=True, fluid=None, P_surface=100000.0, hydraulics_model=None, surface=None, transitions=None, annulus_model=None)
```

Pressure budget [Pa] with named pressure/heat loss terms.

Existing arguments retain their order and units. New calls use
v1.6.0; a supplied circulation result supplies its mode and surface
settings unless overridden. Use hydraulics_model='v1.5.0' for the
exact legacy midpoint calculation, which rejects new loss inputs.
surface is a SurfaceLoss or None; an explicit coefficient of zero
disables an inherited surface allowance. transitions is abrupt or
gradual (zero geometric-local loss). See hydraulic_losses for sources.

## mud_window

```python
mud_window(Shmin, SHmax, Pp, z, Pw_hydro, T_rock, T_wall=None, UCS=None, dsigma_T=0.0, W_max=90.0, margin_SG=0.05, T0=0.0, ecd_SG=0.0, P_surface=0.0)
```

Local mud window and verdict for the supplied wall state.

This helper is stateless. Supply T_wall and dsigma_T for the state being
checked; it does not advance time or calculate wall reheating. The
programme evaluator evaluate includes separate wall histories and
checks connections and trips as well as drilling.

The lower bound is the static pressure needed to keep a breakout lobe
at or below W_max, and cannot be below pore pressure. The upper bound
is Shmin - (margin_SG + ecd_SG) * 1000 * g * z, in Pa.
ecd_SG represents annular friction as an SG equivalent; set it to zero
for a static upper-bound check. GO means the hydrostatic pressure
passes the width and upper-bound checks; CONDITIONAL means another
pressure in the local window passes; NO-GO means the bounds cross.

Tensile-fracture initiation is reported separately and does not set
these window bounds. The diagnostic uses effective
3 Shmin - SHmax - Pw - Pp + dsigma_T < -T0. Initiation alone is not a
prediction that the complete well cannot be drilled.

Arguments start with Shmin then SHmax. Shmin, SHmax, Pp and Pw_hydro
are Pa gauge, relative to the model's 0.1 MPa absolute atmosphere.
P_surface is wellhead pressure [Pa gauge], default zero. UCS, dsigma_T
and T0 are Pa, with no atmospheric offset; z is true vertical depth [m].
T_rock and T_wall
are degrees C. W_max is degrees; margin_SG and ecd_SG are SG
equivalents. T_wall=None uses min(T_rock, 200 degrees C). UCS=None uses the reference
strength of 200e6 Pa at 25 degrees C.

Returns SG_lo, SG_hi and SG_hydro as (P - P_surface)/(1000 g z), where
P_surface is gauge wellhead pressure. Pw_lo, Pw_hi and Pw_mud are Pa gauge;
widths are degrees. Includes verdict and tensile diagnostics. An infeasible
Pw_mud is None. These local SG-equivalent bounds differ from the
whole-programme surface-density bounds returned by evaluate.

## thermal_hoop_stress

```python
thermal_hoop_stress(T_rock, T_wall, site=None)
```

Thermal hoop stress [Pa] at a wall cooled from T_rock to T_wall.

dsigma_T = -E alpha / (1 - nu) * (T_rock - T_wall): the fully constrained
thermoelastic stress Model 2 applies at the cutting face, with E and alpha
from Model 2 at the rock temperature, as Model 2 evaluates them. Negative
(less compressive) when the wall is cooled. For a coupled site, E is the
site's own E_rock scaled by Model 2's temperature factor.

Both temperature arguments are degrees C, in the order rock then wall.
Returns the hoop-stress change in Pa; site optionally supplies rock stiffness.

## breakout_check

```python
breakout_check(Shmin, SHmax, Pw, Pp, T_rock, T_wall=None, UCS=None, dsigma_T=0.0)
```

Effective-stress breakout check at the Shmin azimuth.

Checks whether total hoop stress minus pore pressure exceeds the
Mohr-Coulomb strength at T_wall, including fluid support Pw - Pp.
The criterion is sigma_theta - Pp > strength + K (Pw - Pp), where
strength is the temperature-adjusted UCS and
K = (1 + sin(phi))/(1 - sin(phi)) with phi = 35 degrees.
No additional filter-cake support is assumed.

Arguments start with Shmin then SHmax. Shmin, SHmax, Pw and Pp are Pa
gauge, relative to the model's 0.1 MPa absolute atmosphere. UCS and
dsigma_T are Pa, with no atmospheric offset; T_rock and T_wall are
degrees C. Returns a dictionary:
sigma_theta, mc_hot, mc_cold and P_need [Pa], overbalance_MPa [MPa],
dimensionless over_hydro, and breaks and frac_limited flags. sigma_theta
is total hoop stress; mc_hot and mc_cold are total-stress limits at the
rock and wall temperatures, each including pore pressure. These total
stresses retain the inputs' gauge reference. P_need is the gauge
pressure required to prevent failure at this azimuth. overbalance_MPa
is the pressure difference P_need - Pw in MPa; frac_limited
compares it with Shmin. UCS=None uses the reference strength of 200e6 Pa at 25 degrees C;
T_wall=None uses min(T_rock, 200 degrees C).

## breakout_width

```python
breakout_width(SHmax, Shmin, Pw, Pp, T_wall, UCS=None, dsigma_T=0.0)
```

Width [degrees] of one breakout lobe, centred on the Shmin azimuth.

Uses the effective-stress Mohr-Coulomb criterion around the wall.
Let strength be the temperature-adjusted UCS,
K = (1 + sin(phi))/(1 - sin(phi)) with phi = 35 degrees,
a = SHmax + Shmin - Pw + dsigma_T - Pp - strength - K (Pw - Pp),
and d = 2 (SHmax - Shmin). The full lobe width is arccos(-a/d),
clipped to 0 when no wall failure occurs and 180 when failure extends
all round. Equal horizontal stresses give 0 or 180 degrees directly.

Argument order is SHmax then Shmin, opposite to breakout_check and
mud_window. SHmax, Shmin, Pw and Pp are Pa gauge, relative to the model's
0.1 MPa absolute atmosphere. UCS and dsigma_T are Pa with no atmospheric
offset; T_wall is degrees C.
Returns the width in degrees; UCS=None uses the reference strength
of 200e6 Pa at 25 degrees C.

## wall_temperatures

```python
wall_temperatures(history, T_rock, a, k, rhocp, n=200, r_max=None, T0=None, dt0=1.0, growth=1.08, probe_r=None)
```

Conduct heat through the history of states. T_rock: far-field and
initial temperature (or T0, an initial field on the grid).

history contains WallState objects with durations [s]. T_rock and T0
are degrees C; a and r_max are radii [m], k is W/(m K), and rhocp is
J/(m3 K). T0, if supplied, is an initial temperature array on the grid.
n sets grid size; dt0 is seconds; growth is dimensionless; probe_r is m.
Returns a Result with t [s], r [m], T_wall, T_node and fields [degrees C],
q_wall [W/m into rock], energy_in, energy_far and stored [J/m].

## tool_trip_in

```python
tool_trip_in(lump, column, md_bottom, speed, T0, h_static_out, h_static_in, stages=(), stage_s=0.0, circulating=None, dt=30.0)
```

Run the string into the hole at speed [m/s] to md_bottom, through a
column whose temperature is column(md), from T0 at surface, holding for
stage_s of circulation at each of the measured depths in stages;
circulating(md) gives (T_flow, h_in, h_out) there. Returns the History
and the depth [m] at each of its times.

lump is a ToolLump; column maps measured depth [m] to degrees C.
T0 and circulating temperatures are degrees C; h_static_out and
h_static_in are W/(m2 K). md_bottom and stages are measured depths [m];
stage_s and dt are seconds. Returns (History, depths), with History.t [s],
History.T_s and History.T_f [degrees C], and depths [m]. History.peak()
returns (peak internal-fluid temperature [degrees C], time [s]).

## water_properties

```python
water_properties(T_C, P_Pa)
```

Return water properties for T_C [degrees C] and P_Pa [Pa absolute].

Inputs may be scalars or matching arrays. Returns (rho [kg/m3],
cp [J/(kg K)], mu [Pa s], k [W/(m K)]) as arrays. Values are
interpolated from the cached IAPWS-95 table, whose grid spans
1 to 479 degrees C and 100,000 to 218,100,000 Pa absolute, with
2-degree C and 2 MPa spacing. Inputs outside these ranges are
clipped to the nearest grid edge before interpolation.
The table is built on first use when no cache is present.

## WellGeometry

```python
WellGeometry(string, hole, survey=None)
```

The string and hole, with per-node lookups vectorised over s.

string is a sequence of StringSegment objects from surface to bit;
hole is a contiguous sequence of HoleInterval objects covering the string;
survey is a Survey, defaulting to vertical. Depths and radii are m.
WellGeometry.single(length, pipe, r_hole=0.108, survey=None) constructs
a single segment in open hole, with length and hole radius in m.
Returns geometry with md_bit [m], survey, and vectorised at(s) properties
for measured depths s [m], including radii [m] and resistances [K m/W].

## PipeType

```python
PipeType(name: str, layers: tuple, joint_fraction: float = 0.0, source: str = '', hydraulic_joint: borethm.hydraulic_losses.HydraulicJoint | None = None) -> None
```

A drill pipe's wall, inside out. A tool joint is modelled as bare steel
across the same bore and outside radius.

layers is a tuple of Layer objects, with radii [m] and conductivity
[W/(m K)]. joint_fraction is dimensionless. Returns a pipe with r_bore
and r_out [m]; resistance methods return K m/W. source records provenance.

## WallState

```python
WallState(kind: str, duration: float, T_fluid: float = None, h: float = None, C: float = 0.0, T_node0: float = None, T_wall: float = None, q: float = None, label: str = '') -> None
```

One state of the well. kind: "circulating" (T_fluid, h), "static"
(h, C; the fluid node starts at T_node0, or at the last circulating fluid
temperature if None), "fixed" (T_wall) or "flux" (q, W/m into the wall,
negative when heat is drawn out).

Construct one history item for wall_temperatures. duration is seconds;
temperatures are degrees C; h is W/(m2 K); C is fluid heat capacity per
unit length [J/(m K)]; q is W/m into the rock. kind selects the required
boundary inputs. The label is descriptive text.

## ToolLump

```python
ToolLump(C_s: float, C_f: float, P_in: float, P_out: float, D_in: float) -> None
```

A length of string per metre: steel heat capacity C_s and internal
fluid heat capacity C_f [J/m/K], and the inner and outer perimeters [m].

D_in is the internal diameter [m]. Construct directly, or call
ToolLump.of_pipe(r_bore, r_out, rhocp_fluid), with radii [m] and fluid
volumetric heat capacity [J/(m3 K)]. The result is input to tool_trip_in.

## Layer

```python
Layer(r_in: float, r_out: float, k: float) -> None
```

A concentric wall layer, with inner and outer radii [m] and k [W/(m K)].

Construct from r_in, r_out, k. resistance() returns K m/W.

## StringSegment

```python
StringSegment(length: float, pipe: borethm.well_geometry.PipeType, local_loss: borethm.hydraulic_losses.LocalLoss | None = None, tool_loss: borethm.hydraulic_losses.ReferenceToolLoss | None = None) -> None
```

A drill-string segment of length [m], using the supplied PipeType.

Construct in surface-to-bit order as an input to WellGeometry.

## HoleInterval

```python
HoleInterval(md_top: float, md_bottom: float, r_wall: float, layers: tuple = ()) -> None
```

From md_top to md_bottom: the annulus's outer radius r_wall and the
layers outside it, up to the rock. layers=() is open hole.

All measured depths and radii are m. layers is a tuple of Layer
objects with conductivity [W/(m K)]. resistance() returns K m/W.

## Survey

```python
Survey(md, tvd)
```

Measured depth to true vertical depth. Built from survey stations
(minimum curvature) or from a table of TVD against MD; interpolated
linearly between stations.

Construct with matching measured-depth md and true-vertical-depth tvd
arrays [m]. tvd(s) returns true vertical depth [m]. vertical() gives a
vertical survey; from_stations takes depths [m], inclination and azimuth
[degrees] and initial true vertical depth tvd0 [m].

## uniform_wall

```python
uniform_wall(k, r_in=0.05, r_out=0.06, name=None)
```

One wall layer of conductivity k, on the model's original 100 mm bore
and 120 mm outside diameter unless given.

k is W/(m K); r_in and r_out are radii [m]. Returns a PipeType.

## open_hole

```python
open_hole(md_top, md_bottom, d_hole)
```

Construct an open HoleInterval from measured depths [m] and hole diameter [m].

Arguments are md_top, md_bottom, d_hole; returned r_wall is a radius [m].

## cased

```python
cased(md_top, md_bottom, casing_id, casing_od, d_hole, k_cement=1.0)
```

A single casing string cemented into a hole of diameter d_hole.

Measured depths and all diameters are m; k_cement is W/(m K).
Returns a HoleInterval containing casing steel and cement layers.

## __version__

The installed package version, read from its distribution metadata.
