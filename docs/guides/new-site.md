# Evaluating a new site

This guide takes a site from its inputs to a result in JSON. Install BoreTHM
as described in the [getting-started guide](../../README.md#get-started).
The [public Python interface](../api.md) provides `SiteProfile`,
`StressProfile`, `load_site` and the evaluation functions. To use the worked example,
clone the repository and follow the README's reference-calculation setup.

## 1. Copy the template

[site_template.toml](../../src/borethm/templates/site_template.toml) describes one site, with every
field documented: its units, the range `validate_site` accepts, and where its
value comes from. The values in the template are those of Soultz-sous-Forets,
the reference case. Copy the file as `mysite.toml` and replace each value with the site's own.

The fields fall into four groups.

- **Temperature.** A geotherm, any function from depth in metres to rock
  temperature in °C, and the target depth and temperature. For measured
  points in a TOML file, use `form = "points"` with a `gradient_below` in °C/m;
  `form = "segments"` gives piecewise linear gradients. The geotherm must rise with depth through the open hole and give
  the target temperature at the target depth within 5 °C.
- **Stress.** One or more cases, each giving vertical stress Sv, minimum
  horizontal stress Shmin and maximum horizontal stress SHmax as linear
  profiles with depth, with the pore pressure, the depths the magnitude data
  cover and the source. A measured range is given as several cases (Soultz
  has three, across its range of SHmax). Below the data, SHmax is capped at
  the frictional limit at the site's friction coefficient. A case may state
  its faulting regime, and its stresses are then checked against that
  regime's order.
- **Rock.** Thermal conductivity, Young's modulus (which sets the thermal
  stress) and strength. Strength is given as one or more strength cases,
  each a uniaxial compressive strength; each is run against every stress
  case.
- **Sources.** `data_basis` records, for the stress, strength, pore pressure,
  temperature and the check against a real well, the basis of the value
  (for example, `measured`, `calibrated` or `extrapolated`)
  and its source. The site is evidence-based only if its stresses and
  strength are measured or calibrated there and the stability model has been
  checked against a well at the site; otherwise it is reported as
  speculative, in a separate table. Sources for the conductivity and the
  modulus go under `conductivity` and `stiffness`. `validate_site` rejects
  unrecognised basis labels; the accepted labels are listed below.

## Provenance basis labels

Use these exact strings as the first item of each `(basis, source)` pair:

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

## 2. Validate the inputs

```python
from borethm import load_site, validate_site

site = load_site("mysite.toml")
for warning in validate_site(site):
    print(warning)
print(site.tier)
```

`validate_site` raises an error listing every problem it finds: a value
outside its plausible range (most often a unit slip, kilometres for metres or
megapascals for pascals), temperature falling down the open hole, stresses
out of order, or pore pressure above Shmin. It returns, as warnings, any
input without a source and any temperature fall above the casing shoe.

## 3. Evaluate the site

```python
from borethm import evaluate, export_result, load_site

result = evaluate(load_site("mysite.toml"))
export_result(result, "result.json")
```

Evaluations take several minutes. Weighted-fluid cases take longer because the fluid density is iterated with circulation and hydraulics.

From a source checkout, `python examples/new_site.py` validates the packaged
Soultz template and compares its inputs with the built-in site. Add
`--evaluate --json result.json` to evaluate that reference case and check it
against the saved Soultz result. To assess your own edited file, use the
Python calls above.

To run one of the built-in sites from any directory after installing the package:

```
borethm-evaluate --site soultz --json soultz.json
```

## 4. Read the result

The report and JSON describe the same assessment; the JSON retains additional detail and input provenance. Start with `status` and its reasons, then inspect the pressure bounds and independent equipment checks. The [output guide](interpreting-results.md) maps the current JSON fields, explains the units and distinguishes a target stability case from a complete programme.

The reference assessments do not include a complete flow operating range or stress-uncertainty envelope. Those must not be inferred from a single assessment. Optional margin fields in other evaluation modes are described in the output guide.
