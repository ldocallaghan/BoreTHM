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

The generated files reproduce the built-in sites exactly. They retain each
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

| Task | Interface |
|---|---|
| Evaluate a built-in site | `borethm-evaluate --site KEY` |
| Assess a new site under the evaluator's programme rules | A TOML file with `--site-file`, or `SiteProfile` in Python for a custom geotherm |
| Specify a circulation, stability, wall-temperature or tool calculation | Public component functions in the [Python API](../api.md) |
| Reproduce documented design interventions | Internal [study modules](../science/design-comparisons.md#evidence-and-reproduction), which provide no stable programme-configuration interface |

## Python route

`load_site` returns a `SiteProfile`. Use it with the public validation,
evaluation and export functions, as in the [README example](../../README.md#run-your-own-assessment).
You can also construct a `SiteProfile` directly with `StressProfile` objects.
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
