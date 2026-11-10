# Evaluating a new site

Create a TOML site file from an installed BoreTHM package, replace its inputs
and check them before running an assessment. Python 3.11 or later is required.

## 1. Create a site file

```bash
python -m pip install borethm
borethm-new-site mysite.toml
```

The starter contains Soultz's inputs, with comments explaining each field,
its units and accepted range. Edit a copy for the site you are assessing.
`borethm-new-site` refuses to overwrite an existing file; add `--force` when
you intend to replace it.

You can start from any built-in site:

```bash
borethm-new-site --from newberry mysite.toml
```

| Key | What the file illustrates |
|---|---|
| `soultz` | A segment geotherm and measured stress and strength ranges; the default starter |
| `united-downs` | Measured stresses, calibrated strengths and a replacement temperature profile and target |
| `larderello` | Two temperature profiles and a stress rule for a known faulting regime |
| `pannonian` | A regional segment geotherm and a stress rule for a known faulting regime |
| `newberry` | Temperature survey points, a fitted deep gradient and inputs derived from logs |

The packaged files preserve snapshots of the built-in site inputs. Numerical
fits recomputed on another platform can differ in their last floating-point
digits. Loading a file preserves its supplied values. The files retain each
site's provenance, including missing sources. The Soultz starter additionally
identifies its conductivity and stiffness as assumed values.

## 2. Replace the inputs and sources

TOML is a data format that permits comments. Loading a file parses its data;
it executes no expressions or Python code. Top-level keys use `SiteProfile`
field names. Unknown keys and malformed values produce errors naming the file
and key. Optional fields take the defaults in the [API reference](../api.md#siteprofile).

| Inputs | Meaning and units |
|---|---|
| `name` | Site name |
| `target_depth`, `target_T` | Target depth in m and rock temperature in °C |
| `geotherm` | Temperature profile, using one of the forms below |
| `k_rock`, `E_rock` | Rock conductivity in W/(m K) and Young's modulus in Pa |
| `T_inj` | Fluid temperature at the pumps in °C; defaults to 40 |
| `stress_cases` or `stress_rule` | Linear stress profiles or the rule that constructs them |
| `stress_basis` | Description of the stress-case basis; `data_basis` determines the evidence tier |
| `strength_cases` | Label and uniaxial compressive strength (UCS) at 25 °C, in Pa |
| `temperature_data_to` | Deepest measured temperature depth in m; omit when unknown |
| `mu` | Site friction coefficient; defaults to 0.8 |
| `data_basis` | Basis and source for each input |

The historical fields `Sv_grad`, `K0_min`, `SHmax_over_Sv`, `rho_fluid_grad`
and `UCS` remain required. They describe overburden gradient, minimum and
maximum horizontal stress ratios, fluid-pressure gradient and strength for
the original evaluation modes. The starter explains their units and ranges.
Current evaluations use the supplied stress and strength cases.

### Temperature profiles

A geotherm maps depth in m to rock temperature in °C. The `segments` form
specifies each segment's starting depth, temperature and gradient in °C/m:

```toml
[geotherm]
form = "segments"
boundary = "above"
segments = [[0.0, 12.0, 0.090], [1400.0, 138.0, 0.0172], [5000.0, 200.0, 0.035]]
```

Temperature within a segment is `T_top + gradient * (z - z_top)`. The first
segment applies from the surface. At a segment boundary, `"below"` (the
default) uses the segment starting there; `"above"` uses the one ending
there. Soultz uses `"above"`. Where a profile has a temperature step, this
choice changes the value at the exact boundary.

The `points` form interpolates measured depth and temperature pairs:

```toml
[geotherm]
form = "points"
points = [[0.0, 12.0], [1400.0, 138.0], [5000.0, 200.0]]
gradient_below = 0.035
```

List depths in increasing order. Temperature is linear between the points,
uses the first point's temperature at shallower depths, and extends below
the deepest point at `gradient_below` in °C/m. These example points illustrate
the format; they give a different interpolation from the segment example.

The file format covers every built-in geotherm. Other shapes can be sampled
as points. New analytic forms can be added with named parameters; the format
accepts no free-form expressions. Python users can supply a callable.

Optional `[geotherm_v11]` and `target_depth_v11` replace the original profile
and target in current evaluations. The table accepts either form above.
Larderello and United Downs illustrate these compatibility fields; their
original `geotherm` and `target_depth` remain required.

### Stresses and strengths

Each stress case is linear with depth, `S(z) = gradient * z + intercept`:

```toml
[[stress_cases]]
label = "Example stress case"
Sv_grad = 25500.0
Sv_int = -1300000.0
Shmin_grad = 14060.0
Shmin_int = -1780000.0
SHmax_grad = 24865.0
SHmax_int = -1270000.0
Pp_grad = 10000.0
Pp_datum = 0.0
source = "Replace with the source of these stresses"
z_data = [1500.0, 5000.0]
```

Sv is vertical stress; Shmin and SHmax are minimum and maximum horizontal
stress. Gradients are Pa/m and intercepts are Pa gauge, relative to the
model's atmosphere of 0.1 MPa absolute. Pore pressure is
`Pp_grad * max(z - Pp_datum, 0)`, with `Pp_datum` in m. It defaults to a
10,000 Pa/m gradient from surface. `z_data` gives the measured depth range;
omit it for a case without measured magnitudes. Optional `mu` gives the
coefficient used for that case. Optional `regime` is `"normal"`,
`"strike-slip"` or `"reverse"`; validation checks the stress order.

When only a normal/strike-slip transition regime is known, use a stress
rule. Remove the `[[stress_cases]]` tables before adding it:

```toml
[stress_rule]
form = "transitional"
Sv_grad = 25506.0
source = "Replace with the source of the regime and overburden"
mu = 0.8
fractions = [0.0, 0.25, 0.5, 0.75, 1.0]
```

`Sv_grad` and `source` are required. The rule sets SHmax equal to Sv and
places Shmin at the supplied fractions between its frictional floor and Sv.
Optional `Sv_int` defaults to 0 Pa, `Pp_grad` to 10,000 Pa/m, `mu` to 0.8,
and `fractions` to the five values shown. The rule's `mu` is independent of
the site's top-level `mu`. A file gives either a rule or explicit cases.
These forms cover all linear `StressProfile` cases the evaluator accepts.
If both are omitted, `SiteProfile` constructs a case from the required
historical stress ratios.

Give strength cases as top-level pairs, before any TOML table header:

```toml
strength_cases = [["lower lab strength", 100e6], ["upper lab strength", 130e6]]
```

Each strength is UCS at 25 °C in Pa. Every strength case is checked against
every stress case. If omitted, the evaluator uses the site's required `UCS`.

### Sources and evidence tier

Record provenance in `[data_basis]`, for example:

```toml
[data_basis]
stress = ["measured range", "Publication, well and measured depths"]
conductivity = ["assumed", "Explain the adopted conductivity and its basis"]
```

Provide entries for stress, strength, pore pressure, temperature and the
check against a real well, plus conductivity and stiffness. The template
shows the exact keys. The evidence tier uses stress, strength and well-check
provenance: stress magnitudes and strength must be measured or calibrated,
and the stability calculation checked against a well at the site. Other
sites are labelled speculative. An evidence-based tier does not mean every
input is measured. Validation checks the supplied labels and sources;
it does not verify the underlying measurement or publication.

### Provenance basis labels

Use these exact strings as the first item of each `[basis, source]` pair:

| Label | Description of the input basis |
|---|---|
| `calibrated` | Fitted to observations |
| `measured` | Reported measurement |
| `measured range` | Range supported by measurements |
| `measured (lab)` | Laboratory measurement |
| `log-derived` | Inferred from a well log |
| `checked` | Compared against observations |
| `regime bounds` | Constructed from a stress regime |
| `extrapolated` | Extended beyond the measured range |
| `regional` | Regional estimate |
| `assumed` | Stated modelling assumption |
| `not reproduced` | The stated observation is not reproduced |
| `unsourced` | No supporting source identified |
| `none` | No basis supplied |

The label records how an input was obtained. Validation does not establish
that its source is accurate. The [API reference](../api.md#validate_site)
lists the numerical ranges and validation checks.

## 3. Check the file

```bash
borethm-evaluate --site-file mysite.toml --check
```

This prints warnings and the evidence tier without evaluating or creating
the water-property cache. Invalid units or values produce an error.
`validate_site` checks the accepted ranges, a finite rising geotherm through
the open hole, the target temperature within 5 °C, and consistent stresses
with pore pressure below Shmin. Missing sources produce warnings.
An `[operations]` table is checked as well: a value outside its range is an
error, and a value outside the evaluator's reference range or without a
source produces a warning ([operating choices](#operating-choices)).

## 4. Evaluate and read the result

```bash
borethm-evaluate --site-file mysite.toml --json mysite.json
```

Evaluations can take several minutes. The evaluator builds a missing water
cache outside the installed package. Start with the reading at the top of
the report, then follow the controlling constraint into the detailed checks.
The [output guide](interpreting-results.md) explains each entry and the
difference between target checks and a fluid that works throughout the hole.

JSON records the supplied provenance, input warnings and the loaded file's
path and SHA-256. Keep your site file and measured data with the output.
The JSON does not contain the complete file or a complete programme definition.

## What you can change

The site file supplies geology and site inputs. The evaluator selects the
well geometry, pipe, flow and drilling cycle through its reference rules.
The optional `[programme]` table states the string and hole, and the
optional `[operations]` table states the operating choices.

| Task | Interface |
|---|---|
| Evaluate a built-in site | `borethm-evaluate --site KEY` |
| Assess a new site under the evaluator's programme rules | A TOML file with `--site-file`, or `SiteProfile` in Python for a custom geotherm |
| Assess your own pipe, flow, limits, timings or fluids | The [`[operations]` table](#operating-choices), or `Operations` in Python |
| Specify a circulation, stability, wall-temperature or tool calculation | Public component functions in the [Python API](../api.md) |
| Reproduce documented design interventions | Internal [study modules](../science/design-comparisons.md#evidence-and-reproduction), which provide no stable programme-configuration interface |

## Default physics and downhole tools

The optional `[programme]` table of a site file sets how the circulation is calculated. By default a result uses the v1.8.0 physics:

| Setting | v1.8.0 default | v1.7.0 value |
|---|---|---|
| Annulus pressure, flow regime and heat transfer | Herschel-Bulkley slot model with the Erge transition band, `annulus_model = "herschel-bulkley-erge"` | Bingham pressure with Dittus-Boelter heat transfer, `"v1.6.0"` |
| Pipe friction | `friction = "colebrook"` on a smooth wall, `roughness = 0.0` | `"blasius"` |
| Ordinary drill-pipe joint transitions | Tapered at 11.5°, from the published internal-upset taper of entry 13 | Abrupt |
| Tool pressure losses | Generic allowances for the tools named on the string | Zero unless entered |
| Motor pressure drop | No-load drop plus differential | Differential only |

`physics = "v1.7.0"` in the table, `--physics v1.7.0` on `borethm-evaluate` and `borethm-sites`, or `physics='v1.7.0'` in Python restores the previous values of all of these. A setting given explicitly overrides its row, so `friction = "blasius"` under the default keeps the other v1.8.0 settings.

### Mud rheology from PV and YP

Plastic viscosity (PV) and yield point (YP) are the usual field readings of a drilling mud. When a fluid gives only these, the default annulus converts them to a power law through the 600 and 300 rpm viscometer readings, θ600 = 2 PV + YP and θ300 = PV + YP, with zero yield stress. This is the no-yield conversion of [entry 8](../science/model-development.md#31-october-2026-entry-8-score). A fluid with a `fluids.HerschelBulkley` rheology uses it as given, and a fluid with neither is treated as Newtonian.

The zero yield stress was chosen after two comparisons with FORGE 16A and 16B, so those wells do not test it. The yield stress can matter: in entry 7, a yield stress at the 10-second gel made the 16A bit temperature 4–19 °C colder. If you have low-shear readings for your mud, enter them through `fluids.HerschelBulkley`.

### Tools on the string

The reference programme of every built-in site and of a new site file declares one MWD (measurement while drilling) mud pulser at the 6¾-in size of its collar. The loss is a generic allowance taken from published specification sheets. It describes no particular tool in that well.

The allowances are in [`tool_losses.csv`](../../src/borethm/data/tool_losses.csv), and its [README](../../src/borethm/data/tool-losses-README.md) gives each source. A tool's loss is ΔP_ref × (ρ/ρ_ref) × (Q/Q_ref)^n, and the heat enters the fluid at the tool's depth. **Enter the maker's figure for the actual tool when you have it.** A tool with no figure takes the allowance for its class and the size band nearest to its collar:

```toml
[programme]

[[programme.bha_tools]]
tool_class = "mwd_pulser"
collar_in = 6.75
dp_ref_psi = 130.0
flow_ref_gpm = 600.0
density_ref_ppg = 8.34
exponent = 1.8  # optional; 2 if omitted
source = "Maker's sheet, edition, page"

[[programme.bha_tools]]
tool_class = "rotary_steerable"
collar_in = 6.75
```

The classes are `mwd_pulser`, `rotary_steerable`, `mud_motor`, `filter_sub` and `float_sub`. A segment of a custom `programme.segments` list accepts the same entries under `tools`, and a motor's `differential_psi` gives its on-bottom differential.

No published no-load figure with a stated flow was found for a mud motor, and no figure was found for filter or float subs. These classes default to zero, and the result carries a warning. The 9.5-in pulser and rotary steerable allowances each come from one source, and rotary steerable tools have no allowance at 8 in.

### Named pipes in a custom string

A custom string in `[programme]` lists its segments from surface to bit,
with lengths that add up to the target depth. A segment gives either `pipe`,
naming one of the model's pipe types, or a single wall layer through
`bore_diameter` and `outer_diameter` [m] and `conductivity` [W/(m K)], with an
optional `name` and `source`. `pipe` cannot be combined with those keys,
since the named type gives its own wall; an unknown name is an error that
lists the names. The names are `"TK-Drakon coated"`, `"internally coated"`,
`"externally coated"`, `"conventional"`, `"dual-wall"` and
`"vacuum-insulated (sensitivity)"`; the last two are not on sale. A segment
with `pipe` may still give `hydraulic_joint`, `local_loss`, `tool_loss` and
`tools`. Starter files end with a commented example.

```toml
[programme]
[[programme.segments]]
length = 1000.0
pipe = "vacuum-insulated (sensitivity)"
[[programme.segments]]
length = 9233.2
pipe = "TK-Drakon coated"
[[programme.segments]]
length = 466.8
name = "drill collar"
bore_diameter = 0.0714
outer_diameter = 0.1714
conductivity = 45.0
```

## Operating choices

The evaluator chooses the pipe, the flow, the tool and pump limits, the
connection and trip timings, the rate of penetration and the drilling and
trip fluids by fixed rules. The optional `[operations]` table states any of
these. A key left out keeps the evaluator's rule, so a file without the
table gives the result it gave before. Every starter file written by
`borethm-new-site` ends with the table commented out, with units, ranges and
defaults; remove the leading `# ` from `[operations]` and from each key you
state.

| Key | Unit | Accepted range | Default when left out |
|---|---|---|---|
| `pipes` | pipe names, tried in order | built-in names | `"TK-Drakon coated"`, `"internally coated"`, `"externally coated"`, `"conventional"` |
| `mass_flow_kg_s` | kg/s | 1 to 300 | the flow search |
| `volume_flow_L_s` | L/s at surface | 1 to 300 | the flow search |
| `mass_flows_kg_s` | kg/s, rising | each 1 to 300 | 5 to 50 in steps of 5, then 60 to 100 in steps of 10, in kg/s with water |
| `volume_flows_L_s` | L/s at surface, rising | each 1 to 300 | the same numbers in L/s with a weighted fluid |
| `tool_limit_C` | °C | 50 to 400 | 200 |
| `pump_pressure_limit_Pa` | Pa | 1e6 to 150e6 | 51.7e6 (7,500 psi) |
| `rig_pumps` | pumps | 1 to 10 | 3 |
| `min_annular_velocity_m_s` | m/s | 0.05 to 5 | 1.245 |
| `precirculation_min` | min | 0 to 240 | 0.33 |
| `connection_median_min` | min | 0.1 to 480 | 2.83 |
| `connection_p90_min` | min | 0.1 to 480 | 6.33 |
| `trip_hours` | h | 0.5 to 500 | FORGE 16B speeds and surface time, scaled to the target depth |
| `trip_scale` | factor on that rule | 0.05 to 20 | 1 |
| `stage_spacing_m` | m | 10 to 10,000 | 144.88, then the staging search |
| `stage_minutes` | min | 0.5 to 600 | 15.51, then the staging search |
| `rop_m_h` | m/h | 0.1 to 100 | Model 3, iterated with the wall's exposure for a coupled site |
| `drilling_fluid_kg_m3` | kg/m³ at 20 °C | 990 to 2,600 | the drilling fluid's common window lower bound, iterated |
| `trip_fluid_kg_m3` | kg/m³ at 20 °C | 990 to 2,600 | the larger of the drilling fluid and the trip window's lower bound |
| `[operations.coating_ratings_C]` | pipe name to °C | each 50 to 400 | `"TK-Drakon coated" = 204.0` |
| `[operations.sources]` | key to `[basis, source]` | the basis labels above | none |

A flow is a mass flow in kg/s or a volume flow in L/s at surface, at the
fluid's density at 20 °C; the mass flow is the volume times that density.
The evaluator's own flow grid is in kg/s with water and in L/s with a
weighted fluid, so its pumps deliver the same volume whatever the fluid's
weight. A flow stated in the evaluator's own unit is used unchanged, and
the other unit is converted at the fluid's density, so stating the flow the
evaluator chose gives the same circulation. The connection practice
is the circulation after the last new hole (`precirculation_min`) followed by
the 90th-percentile pumps-off time (`connection_p90_min`); the median sets
the shorter pumps-off times the schedule search tries. `precirculation_min`,
the two connection times and the staging defaults are FORGE 16B values.

A stated value is used as given. Where the evaluator would otherwise search,
stating the value ends the search, and a check the value fails is reported
as failed:

- a stated `mass_flow_kg_s` or `volume_flow_L_s` is the flow evaluated. A flow over the pump limit makes
  the status NO-GO, and `programme.conflict` names each check the flow fails;
- `precirculation_min` or `connection_p90_min` ends the connection schedule
  search, and `stage_spacing_m` or `stage_minutes` ends the run-in staging
  search. If the stated practice takes the tool past its limit, the tool fails;
- `rop_m_h` replaces Model 3's rate and ends the iteration of rate and
  exposure;
- a stated fluid outside its common window makes the status NO-GO. A stated
  fluid inside it and heavier than water makes the status CONDITIONAL: the
  condition names the fluid and its window, and says whether the window
  admits water. A value below water's 998.2 kg/m³ is water.

Give at most one of the four flow keys, and at most one of `trip_hours` and
`trip_scale`. `coating_ratings_C` replaces the whole table, so a pipe it
leaves out has no rating. `pipes` cannot be combined with custom
`programme.segments`, which fix the string. Operations apply to the default
calculation mode, `--circulation v1.3.4`; with another mode a stated value
is an error.

```toml
[operations]
volume_flow_L_s = 30.0
tool_limit_C = 175.0
stage_spacing_m = 100.0
stage_minutes = 20.0

[operations.sources]
volume_flow_L_s = ["assumed", "two pumps at 90 strokes/min"]
tool_limit_C = ["measured", "MWD maker's rating sheet, edition, page"]
stage_spacing_m = ["assumed", "planned run-in practice"]
stage_minutes = ["assumed", "planned run-in practice"]
```

The check warns about a flow outside 5 to 100, a pipe that is not on sale,
a coating rating for a pipe that is not a candidate, a tool limit above
300 °C, a pump limit above the reference pumps' 7,475 psi rating, a median
connection longer than the 90th percentile, a staging interval shorter than
a stand, a rate of penetration above Model 3's 20 m/h ceiling, a fluid
below water's density, a trip fluid lighter than the drilling fluid, and a
stated value without a source. Each message names its key, as in
`operations.tool_limit_C: no source is given`. The result records each operating choice as
stated or default ([interpreting results](interpreting-results.md#operations-and-limit-checks)),
and the [limitations guide](../science/limitations.md#operating-choices-that-remain-fixed)
lists the choices that remain fixed.

## Python route

`load_site` returns a `SiteProfile`. Use it with the public validation,
evaluation and export functions, as in the [README example](../../README.md#run-your-own-assessment).
You can also construct a `SiteProfile` directly with `StressProfile` objects.
`Operations` states operating choices in Python, as
`evaluate(site, operations=Operations(volume_flow_L_s=30.0))` or on
`SiteProfile.operations`. `validate_operations` checks it and returns records
with the field, a level (`error` or `warning`) and the message;
`operation_defaults(site, programme)` gives each field's default value, unit,
rule and source, with the values that depend on the site and programme.
The public `layered_geotherm` builds a temperature callable from measured points.

For a temperature shape beyond the file's forms, supply your own callable.
This example uses an illustrative curved profile; replace its coefficients
and provenance with your site's temperature evidence:

```python
from dataclasses import replace
import numpy as np
from borethm import load_site, validate_site

def my_geotherm(depth):
    z = np.asarray(depth, dtype=float)
    return 12.0 + 0.035 * z + 1.2e-7 * z * z

site = load_site("mysite.toml")
basis = dict(site.data_basis)
basis["temperature"] = ("assumed", "Illustrative curved profile; replace with site evidence")
site = replace(site, name="Example site", geotherm=my_geotherm, geotherm_v11=None,
               target_T=float(my_geotherm(site.target())), data_basis=basis)
print(validate_site(site))
```

In Python, `evaluate(site, coupled=False)` switches coupling off explicitly.
The flag affects the site's stiffness in thermal stress, the drilling-rate
model's use of site circulation, and the iteration of rate of penetration
and exposure. Current calculation modes enable coupling by default, so a
file's initial `coupled = false` does not disable that default. The
[evaluate docstring](../api.md#evaluate) gives the selection table.

## Worked reference example from a checkout

The installed-package workflow above needs no checkout. For a reproduction
check, follow the README's locked setup at the release tag, then run:

```bash
python examples/new_site.py
python examples/new_site.py --evaluate --json ../borethm-soultz-example.json
```

This script loads the packaged Soultz template, compares its inputs with the
built-in site and, with `--evaluate`, checks the result against the reviewed
Soultz row. It is a reference check; use `--site-file` for your edited file.
The old Python template `examples/site_template.py` was replaced by the
packaged TOML template in v1.5.0.
