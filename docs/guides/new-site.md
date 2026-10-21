# Evaluating a new site

This guide takes a site from its inputs to a result in JSON. Install BoreTHM
as described in the [getting-started guide](../../README.md#get-started).
The [public Python interface](../api.md) provides `SiteProfile`,
`StressProfile` and the evaluation functions. To use the worked scripts below,
clone the repository and follow the README's reference-calculation setup.

## 1. Copy the template

[examples/site_template.py](../../examples/site_template.py) defines one site, as a `SiteProfile`, with every
field documented: its units, the range `validate_site` accepts, and where its
value comes from. The values in the template are those of Soultz-sous-Forets,
the reference case. Copy the file and replace each value with the site's own.

The fields fall into four groups.

- **Temperature.** A geotherm, any function from depth in metres to rock
  temperature in °C, and the target depth and temperature. For measured
  points, supply an interpolation function and state how it extrapolates
  below the deepest measurement. The geotherm must rise with depth through the open hole and give
  the target temperature at the target depth within 5 °C.
- **Stress.** One or more stress cases, each a linear profile of Sv, Shmin and
  SHmax with depth, with the pore pressure, the depths the magnitude data
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
  unrecognised basis labels. The template uses internal helpers for its
  Soultz reference inputs; those helpers are outside the public interface.

## 2. Validate the inputs

```bash
python examples/new_site.py
```

`validate_site` raises an error listing every problem it finds: a value
outside its plausible range (most often a unit slip, kilometres for metres or
megapascals for pascals), temperature falling down the open hole, stresses
out of order, or pore pressure above Shmin. It returns, as warnings, any
input without a source and any temperature fall above the casing shoe.

## 3. Evaluate the site

`examples/new_site.py` builds the site from the template, validates it and,
with `--evaluate`, runs it:

The worked script imports `make_site` from `examples/site_template.py`. If you give your template copy another module name, update that import in your copy of `examples/new_site.py` before running it.

```
python examples/new_site.py --evaluate --json result.json
```

Evaluations take several minutes. Weighted-fluid cases take longer because the fluid density is iterated with circulation and hydraulics. With the template unchanged, the
script reports that the site is the repository's Soultz and compares its
row of the site table with the pinned one.

To run one of the built-in sites from any directory after installing the package:

```
borethm-evaluate --site soultz --json soultz.json
```

## 4. Read the result

The report and JSON describe the same assessment; the JSON retains additional detail and input provenance. Start with `status` and its reasons, then inspect the pressure bounds and independent equipment checks. The [output guide](interpreting-results.md) maps the current JSON fields, explains the units and distinguishes a target stability case from a complete programme.

The retained reference evaluations do not include a complete flow operating range or stress-uncertainty envelope. Those must not be inferred from a single assessment. Optional margin fields in other evaluation modes are described in the output guide.
