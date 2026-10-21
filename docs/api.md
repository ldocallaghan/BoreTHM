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

## evaluate

```python
evaluate(site: SiteProfile, v10=False, thermal=True, circulation='v1.3.4', coupled=None)
```

Evaluate a SiteProfile through circulation, connections and trips.

Site inputs use m, Pa, degrees C and SI thermal properties. Validate the
profile first with validate_site. The default circulation='v1.3.4' uses
the corrected programme calculation. v10 selects the original model;
thermal enables wall cooling and coupled overrides the site's coupling.
Earlier circulation modes remain available for reproducing old releases.

Return a dictionary containing the site and target depth z [m], rock
temperature T_rock [degrees C], the circulation and operating programme,
cycle cases, mud windows, tool gates and status. Whole-programme windows
use surface fluid density [kg/m3 at 20 degrees C]; cycle SG values are
equivalent static densities. Use result_dict for a serialisable record.
This evaluation can require substantial computation.

## result_dict

```python
result_dict(o)
```

Convert an evaluate result into a JSON-compatible dictionary.

Inputs and outputs retain the evaluation's units: depth [m], temperature
[degrees C], pressure [Pa], flow [kg/s or L/s as labelled], and surface
density [kg/m3 at 20 degrees C]. SG-equivalent values remain labelled SG.
Includes input sources and runtime versions; does not run calculations.

## export_result

```python
export_result(o, path)
```

Write result_dict(o) as JSON to an explicit path.

o is an evaluate result. Values retain their labelled SI units and
temperatures in degrees C. Returns None; creates or overwrites the file.

## SiteProfile

```python
SiteProfile(name: str, geotherm: Callable, target_depth: float, target_T: float, Sv_grad: float, K0_min: float, SHmax_over_Sv: float, rho_fluid_grad: float, k_rock: float, E_rock: float, UCS: float, T_inj: float = 40.0, stress_cases: tuple = (), stress_basis: str = 'v1.0 ratios', strength_cases: tuple = (), data_basis: dict = <factory>, geotherm_v11: Callable = None, target_depth_v11: float = None, temperature_data_to: float = None, mu: float = 0.8, coupled: bool = False) -> None
```

Site inputs for evaluate, with temperature and stress profiles.

geotherm maps depth [m] to rock temperature [degrees C]; target_depth is
m and target_T is degrees C. Stress and fluid pressure gradients are
Pa/m; K0_min and SHmax_over_Sv are dimensionless stress ratios.
k_rock is W/(m K); E_rock and UCS are Pa; T_inj is degrees C.
stress_cases contains StressProfile objects; strength_cases contains
(label, UCS [Pa]) pairs. data_basis maps input names to (basis, source).
temperature_data_to and optional replacement target depths are m.
mu is a dimensionless friction coefficient; coupled enables coupling to
the site's circulation. Construct a profile, then call validate_site.
Methods target() and temperature() give the effective depth [m] and
temperature [degrees C], including a replacement geotherm when supplied.

## StressProfile

```python
StressProfile(label: str, Sv_grad: float, Shmin_grad: float, SHmax_grad: float, Sv_int: float = 0.0, Shmin_int: float = 0.0, SHmax_int: float = 0.0, Pp_grad: float = 10000.0, Pp_datum: float = 0.0, source: str = '', z_data: tuple = None, mu: float = None, regime: str = None) -> None
```

Linear in-situ stress with depth: S(z) = grad * z + intercept [Pa, z in m].

Pore pressure is Pp_grad * (z - Pp_datum) below a static fluid level at
Pp_datum [m], zero above it. z_data is the depth range [m] the magnitude data
actually cover, or None when the profile rests on regime bounds alone.

Inputs ending in _grad are Pa/m; stress intercepts are Pa.
The constructor orders Sv, Shmin, then SHmax gradients. Methods Sv(z),
Shmin(z), SHmax(z) and Pp(z) return Pa for depth z [m]. mu is dimensionless;
regime is normal, strike-slip or reverse when specified.

## validate_site

```python
validate_site(site)
```

Check a site's inputs before an evaluation. Raises ValueError listing
every problem found; returns warnings (inputs without a stated source).

  * every scalar input within INPUT_RANGES, and every strength case's UCS;
  * temperature rising with depth down the open hole, from the casing
    shoe to the target, and reaching target_T there within 5 C (a fall
    above the shoe, such as a cold aquifer, is a warning);
  * in every stress case, at the target and at each 500 m above it to
    the casing shoe (the open hole, where the stresses are used): the
    stresses positive, SHmax at least Shmin, Shmin above the pore
    pressure, and the order of the stated regime;
  * every data-basis entry with a basis from BASES and a source.

Input is a SiteProfile in the units documented on that class. Returns a
list of warning strings; invalid inputs raise ValueError.

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
circulating_temperatures(m_dot=2.0, T_inj=40.0, G=0.035, T_surf=15.0, target_rock_T=450.0, Q_face=28000.0, t_years=1.0, pipe=None, k_rock=2.5, n_nodes=160, verbose=False, geotherm=None, target_depth=None, geometry=None, exposure=None, fluid=None, rhocp_rock=2700000.0, friction_heat=False, tfa=0.0007759, film_mult=1.0, breaks=(), init=None, P_surface=100000.0)
```

Compute circulating bore and annulus temperatures along a well.

Supply either a PipeType or a WellGeometry. Mass flow m_dot is kg/s;
T_inj, T_surf and target_rock_T are degrees C; G is K/m; Q_face is W.
Rock conductivity k_rock is W/(m K), rhocp_rock is J/(m3 K), and
t_years is years. A geotherm maps true vertical depth in m to degrees C;
exposure maps measured depth in m to seconds and overrides t_years.
With a geotherm and a pipe, target_depth must give the measured depth
in m. Geometry supplies the depth when given. P_surface is Pa; tfa is
the bit nozzle flow area in m2. Friction heating is optional; film_mult
scales the annulus film coefficient. breaks are measured depths in m;
init is a previous circulation result used to seed the solver.

fluid=None uses water. A constant fluid dictionary supplies rho [kg/m3],
cp [J/(kg K)], mu [Pa s] and k [W/(m K)]; a fluid object may provide props.
Return a dictionary with z [measured depth, m], Td, Tu and Trock [degrees C],
Q_product [W], m_dot [kg/s], P_bottom [Pa], geometry and success, plus
the underlying solution. Check success before using a profile.
verbose=False suppresses the solver's printed report by default.

## hydraulics

```python
hydraulics(m_dot, geometry, result=None, T_avg=80.0, tfa=0.0007759, friction='blasius', bit=True, fluid=None, P_surface=100000.0)
```

Pressure losses along the string and annulus, bit nozzle loss,
standpipe pressure and annular velocity.

With a solve() result, water properties are taken at each piece's local
bore or annulus temperature and pressure, and the standpipe pressure
includes the buoyancy of the hot annulus against the cold bore. Without
one, properties are at T_avg and mid-depth pressure throughout.

  SPP = dP_string + dP_bit + dP_annulus + integral (rho_ann - rho_bore) g dTVD

The first two arguments, m_dot [kg/s] and geometry [WellGeometry],
are required. result is a circulating_temperatures result; T_avg is
degrees C, tfa is m2 and P_surface is Pa. bit enables nozzle loss;
friction selects the friction law. fluid=None uses water; otherwise
use a constant property dictionary or an object providing props.
Return a dictionary with pressure losses and spp [Pa], annular velocities
[m/s], hydraulic pump power [W], and flow diagnostics.

## mud_window

```python
mud_window(Shmin, SHmax, Pp, z, Pw_hydro, T_rock, T_wall=None, UCS=None, dsigma_T=0.0, W_max=90.0, margin_SG=0.05, T0=0.0, ecd_SG=0.0, P_surface=0.0)
```

Mud window and drillability verdict, judged on breakout width.

The two bounds are checked under the conditions that set them. Breakout,
the lower bound, at static mud weight: with the pumps off at a connection,
for minutes while the wall is still cool, it sees only the static column.
A trip takes the hole out of circulation for a day or more at these
depths, and the wall reheats towards rock temperature; that is closer to
the uncooled sensitivity, and reheating is not modelled. Fracture, the
upper bound, at circulating pressure: the static mud plus ecd_SG, the
annular friction loss as an equivalent density, must stay below Shmin less
the margin. ecd_SG = 0 is the static check on both.

Lower bound: the lightest mud keeping the breakout lobe at or below W_max,
and never below pore pressure (no underbalanced drilling). Upper bound:
Shmin less margin_SG of mud (lost returns). Verdict: GO if the lobe is
within W_max at hydrostatic mud, CONDITIONAL if a mud weight inside the
window gets it there, NO-GO if none does. Tensile-fracture initiation at
the wall (effective 3 Shmin - SHmax - Pw - Pp + dsigma_T < -T0) is
reported and does not bound the window: UD-1 logged tensile fractures and
still reached TD, so initiation alone doesn't stop a well.

The SG figures are equivalent static densities, (P - P_surface) / (1000 g z),
with P_surface the wellhead pressure.

Arguments start with Shmin then SHmax. Stresses and pressures, UCS,
dsigma_T and tensile strength T0 are Pa; z is true vertical depth [m];
T_rock and T_wall are degrees C. W_max is degrees; margin_SG and ecd_SG
are SG equivalents. Returns a dictionary with SG_lo, SG_hi, SG_hydro,
Pw_lo, Pw_hi and Pw_mud [pressures in Pa], widths [degrees],
verdict and tensile diagnostics. An infeasible Pw_mud is None.
These bounds describe the supplied local state. Whole-programme surface
density bounds from evaluate account for the fluid's temperature profile.

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

Fails when sigma_theta - Pp > sigma_cm(T_wall, UCS) + KMC (Pw - Pp): the
Kirsch hoop stress from model5.hoop_stress, Mohr-Coulomb in effective
stress, with no filter-cake credit beyond Pw - Pp. With Pp = 0 and
dsigma_T = 0 it is breakout_v10 exactly. Same keys as breakout_v10, with
sigma_theta the total hoop stress and mc_cold / mc_hot the total-stress
limits (Pp plus the effective strength), so the two stay comparable.

Arguments start with Shmin then SHmax. All stresses, pressures, UCS
and dsigma_T are Pa; T_rock and T_wall are degrees C. Returns a dictionary:
sigma_theta, mc_hot, mc_cold and P_need [Pa], overbalance_MPa [MPa],
dimensionless over_hydro, and breaks and frac_limited flags. UCS=None
uses the model's intact strength; T_wall=None uses the existing wall cap.

## breakout_width

```python
breakout_width(SHmax, Shmin, Pw, Pp, T_wall, UCS=None, dsigma_T=0.0)
```

Width [deg] of one breakout lobe, centred on the Shmin azimuth.

Closed form of the effective-stress Mohr-Coulomb criterion (see
_width_threshold) around the circumference: the lobe spans
|phi| < arccos(-a/d) / 2, so its full width is arccos(-a/d). 0 when the
wall holds everywhere, 180 when it fails all round (two lobes meeting).

Argument order is SHmax then Shmin, opposite to breakout_check and
mud_window. Stresses, Pw, Pp, UCS and dsigma_T are Pa; T_wall is degrees C.
Returns the width in degrees; UCS=None uses the model's intact strength.

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

Return water properties for temperature T_C [degrees C] and P_Pa [Pa].

Inputs may be scalars or matching arrays. Returns (rho [kg/m3],
cp [J/(kg K)], mu [Pa s], k [W/(m K)]) as arrays. Values are
interpolated from the cached IAPWS-95 table; inputs outside its
temperature and pressure range are clipped to the table boundaries.
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
PipeType(name: str, layers: tuple, joint_fraction: float = 0.0, source: str = '') -> None
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
StringSegment(length: float, pipe: borethm.well_geometry.PipeType) -> None
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
