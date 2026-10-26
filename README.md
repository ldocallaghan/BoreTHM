# BoreTHM: models of circulating temperature and borehole stability for drilling into superhot rock

BoreTHM is an open-source Python model for assessing drilling programmes in superhot geothermal rock. It couples circulating-fluid and downhole-tool temperatures with thermal stress at the borehole wall to calculate the mud-weight window: the range of fluid densities that meets the pressure constraints through drilling, connections and trips.

BoreTHM is intended for drilling engineers and researchers assessing a well design or reusing the thermal and stability calculations. Its reference cases support comparisons with field observations and published models.

- [Documentation](https://ldocallaghan.github.io/BoreTHM/): guides, scientific explanations and the Python interface.
- [Get started](https://github.com/ldocallaghan/BoreTHM/blob/main/README.md#get-started): set up Python and run an assessment.
- [Read a result](https://github.com/ldocallaghan/BoreTHM/blob/main/README.md#reading-a-result): understand the outputs and status labels.
- [Explore the examples](https://github.com/ldocallaghan/BoreTHM/blob/main/README.md#example-results): site findings and their controlling constraints.
- [Understand the models](https://github.com/ldocallaghan/BoreTHM/blob/main/README.md#models-and-evidence): methods and field comparisons.

## Get started

Install BoreTHM with Python 3.11 or later:

```bash
python -m pip install borethm
```

For figures, install `"borethm[plot]"`. Build the water-property cache and run a first assessment:

```bash
borethm-water-table
borethm-evaluate --site newberry --json newberry.json
```

The IAPWS-95 cache is built once, outside the installed package, in the platform's user cache directory. Set `BORETHM_CACHE_DIR` to choose another location. The evaluator also builds a missing cache on first use. The assessment command prints its result and writes JSON with the reported site inputs, evaluated checks and runtime provenance. Evaluations take several minutes; weighted-fluid cases require repeated coupled solves and can take longer.

The same assessment through the [public Python interface](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/api.md):

```python
from borethm import evaluate, export_result, find_site
site = find_site("newberry")
result = evaluate(site)
export_result(result, "newberry.json")
print(result["status"]["label"])
```

### Reproduce the reference calculations

Use Python 3.14.4 and the locked dependencies in a source checkout:

```bash
git clone https://github.com/ldocallaghan/BoreTHM.git
cd BoreTHM
git checkout v1.5.0
python -m venv .venv
```

Use `python3` if your system does not provide `python`. Activate the environment with `.\.venv\Scripts\Activate.ps1` in PowerShell, or `source .venv/bin/activate` on Linux and macOS, then install:

```bash
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
borethm-water-table
```

Commands for releases before v1.4.0 are in their [release records](https://github.com/ldocallaghan/BoreTHM/tree/main/docs/releases) and run from that release's tag.

## Run your own assessment

Create a site file, edit its inputs and check them before running the assessment. These commands work from any directory after installation:

```bash
python -m pip install borethm
borethm-new-site mysite.toml
# edit mysite.toml
borethm-evaluate --site-file mysite.toml --check
borethm-evaluate --site-file mysite.toml --json mysite.json
```

The starter contains Soultz's inputs. Replace the temperature profile, target, stresses, rock properties and sources with the site's measurements or stated assumptions. The comments explain units and accepted ranges; the [site-input guide](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/guides/new-site.md) describes the file format and provenance labels. `--check` reports input warnings and the evidence tier without running the model or building the water-property cache.

Use `borethm-new-site --from newberry mysite.toml` to start from another built-in site. The available keys are `soultz`, `united-downs`, `larderello`, `pannonian` and `newberry`. Existing files require `--force` to overwrite.

The same steps through the public Python interface:

```python
from borethm import load_site, validate_site, evaluate, export_result

site = load_site("mysite.toml")
for warning in validate_site(site):
    print(warning)
result = evaluate(site)
export_result(result, "mysite.json", site_file="mysite.toml")
```

Keep the file unchanged between loading and exporting through this Python example. The CLI captures the input checksum before evaluation. Keep the site file and measured data with the result: JSON retains supplied provenance and input warnings, with the file path and SHA-256 when supplied, but does not contain the complete site file or programme definition.

To evaluate a built-in site directly, run `borethm-evaluate --site soultz --json soultz.json`. `borethm-sites` reports all five. Use `borethm-evaluate --help` for the options.

### What you can change

A site file supplies geology and site inputs. The evaluator selects the well geometry, pipe, flow and drilling cycle through its reference rules.

| Task | Interface |
|---|---|
| Evaluate a built-in site | `borethm-evaluate --site KEY` |
| Assess a new site under the evaluator's programme rules | A TOML file with `--site-file`, or `SiteProfile` in Python for a custom geotherm |
| Specify a circulation, stability, wall-temperature or tool calculation | Public component functions in the [Python API](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/api.md) |
| Reproduce the documented design interventions | Internal study modules described in the [design comparisons](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/science/design-comparisons.md); these provide no stable programme-configuration interface |

## Reading a result

Start with the reading at the top of the report. It describes numerical validity, the stress and strength cases at the target, the whole-hole pressure limits and the equipment checks. Its controlling constraint identifies the first status reason; follow that into `components`, the density bounds in `windows`, and the detailed report. The same text is exported under `reading` in JSON.

For example, the [Newberry reference assessment](https://github.com/ldocallaghan/BoreTHM/blob/main/results/v1.3.4/checkpoint-1/newberry.json) gives:

> **Calculation:** Valid: the reported numerical checks converged.
>
> **Scenarios at the target:** Cases passing target stability, including stated fluid conditions: drilling 6/6; connection 6/6; connection, fresh rock 6/6; trip 6/6.
>
> **Whole programme:** One drilling fluid and one trip fluid satisfy the pressure limits at every evaluated depth, state and case. Surface densities at 20 C: drilling fluid 0.998 to 1.237 SG; trip fluid 0.998 to 1.233 SG.
>
> **Equipment:** The tool passes its 200 C temperature check. The TK-Drakon coating reaches 139.4 C against its stated 204 C rating (within rating).
>
> **Controlling constraint:** The status lists no additional constraint.

The [output guide](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/guides/interpreting-results.md) explains the four entries, status precedence, pressure units and schedule identity. The full report and JSON retain the individual evaluated cases and supplied input provenance.

| Status | Meaning for the evaluated programme and assumptions |
|---|---|
| GO | The modelled checks pass without the additional conditions listed by the evaluator. |
| CONDITIONAL | The assessment depends on stated conditions, such as prescribed fluids or a circulation schedule. Read those conditions before using the result. |
| NO-GO | A modelled gate fails for this programme and these assumptions; the reasons identify the failing components. |
| INDETERMINATE | A required numerical result did not converge, or an equipment qualification remains unresolved without another decisive failure. |

An overall NO-GO can coexist with an INDETERMINATE coating check. Exceeding a manufacturer's stated coating rating identifies a qualification question. It does not predict a particular failure mode.

A **mud-weight window** is the allowable range of fluid density: enough pressure to keep the borehole stable while staying below the modelled fracture-pressure limit. BoreTHM calculates the range that satisfies all evaluated depths, operating states and stress/strength cases, separately for drilling and trips.

Two pressure descriptions appear in the outputs:

- **Target SG-equivalent** expresses pressure as an equivalent static column at the target. It is a local stability diagnostic, with the existing friction/backpressure treatment.
- **Surface SG at 20 °C** is fluid density divided by 1,000 kg/m³. The combined pressure constraints set the allowable range of that surface density.

A positive target interval does not establish a workable whole-hole fluid. If the required minimum density exceeds the permitted maximum, no mud density satisfies both pressure limits. The densities reported in that situation are calculation inputs and cannot be prescribed.

## Example results

The reference assessments target rock at 400 °C. The table reports the base case with immediate breakout formation. Each status applies to the specified design and inputs.

| Site | Target, km | Status | Main finding |
|---|---:|---|---|
| Soultz-sous-Forêts | 10.70 | NO-GO | No drilling or trip fluid density satisfies all pressure limits; the best attempted run-in exceeds the tool limit. |
| United Downs | 12.86 | NO-GO | No drilling or trip fluid density satisfies all pressure limits; drilling and run-in exceed the tool limit. |
| Larderello | 2.40 | CONDITIONAL | Requires weighted drilling and trip fluids. |
| Pannonian Basin | 9.71 | NO-GO | No drilling or trip fluid density satisfies all pressure limits; coating qualification is unresolved. |
| Newberry | 3.63 | GO | The evaluated programme passes with water. |

These sites have different evidence quality. Soultz and United Downs use measured or calibrated stresses and strengths, extrapolated to the targets. Larderello and Pannonian retain unsourced strength assumptions. Newberry's well check does not reproduce the observed pattern in every rock type. The [input-source records](https://github.com/ldocallaghan/BoreTHM/blob/main/src/borethm/data/sites/stress_sources.md) explain those differences.

### Local stability and the complete programme

At Soultz and United Downs, some stress and strength cases have an open drilling window at the target depth. Neither reference programme has a fluid density that satisfies the pressure limits throughout the hole. The [reference-programme comparison](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/science/design-comparisons.md#reference-programmes) gives the case tables, whole-hole pressure bounds and equipment temperatures.

### Breakout timing

The assumed time between rock exposure and breakout formation can change the **whole-hole drilling-fluid window**. In the saved scan, that window first opens between delays of 15 and 20 minutes at Soultz, and between 10 and 15 minutes at United Downs. These are brackets from calculations with assumed delays. Breakout formation time in hot granite has not been measured in the studies reviewed here. Both complete programmes remain NO-GO because other checks still fail. The [breakout-timing study](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/science/breakout-timing.md) explains the assumptions and results.

### Design comparisons

No evaluated design change or evaluated pair made either deep-site programme pass. The [design comparisons](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/science/design-comparisons.md) describe the tested settings and remaining failures. They do not establish a complete operating envelope or show that every possible design would fail.

The [study summary](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/guides/summary.md), also available as a [two-page PDF](https://github.com/ldocallaghan/BoreTHM/blob/main/output/pdf/summary.pdf), brings the findings and open questions together.

## Models and evidence

The circulation model solves the downgoing and returning fluid temperatures with frictional heating and heat transfer through the pipe, casing and surrounding rock. Rock conduction carries each depth through its exposure and circulation pauses. Fluid properties and pressure losses feed back into the stability and tool calculations.

| Model or check | Role | Evidence and detail |
|---|---|---|
| Circulation | Fluid temperatures, heat transfer and hydraulics | [Utah FORGE comparisons and published-model benchmark](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/science/validation.md#circulation) |
| Rock reheating | Temperature recovery when circulation stops | [Analytic checks and the limits of the FORGE pause comparison](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/science/validation.md#rock-reheating) |
| Borehole stability | Breakout width and pressure requirements | [UD-1 strength calibration and other well checks](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/science/validation.md#stability-checks) |
| Spallation, drilling rate and creep | Exploratory estimates of quench effects and closure | [Physical models and their limits](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/science/models.md#drilling-rate-and-creep) |

The [run-in tool check can be non-conservative](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/science/limitations.md#tool-temperature-and-programme-timing): at FORGE 16A it underpredicted measured peaks by about 20–50 °C on partial legs with approximate initial states.

The circulation/FORGE comparisons, strength calibration and other checks have distinct scopes. They do not validate a complete 10-13 km drilling programme. Governing equations, implementation assumptions and diagnostic figures are in the [physical-model guide](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/science/models.md); the [bibliography](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/science/sources.md#references), [material properties](https://github.com/ldocallaghan/BoreTHM/blob/main/src/borethm/data/materials.md) and [site inputs](https://github.com/ldocallaghan/BoreTHM/blob/main/src/borethm/data/sites/stress_sources.md) retain their sources.

## Scope and limitations

A passing result depends on the modelled inputs and checks. A failed assessment does not establish that a different design or existing technology could not drill the site.

The deep targets lie below measured stress data. Strength calibration depends on the assumed stress profile, and the reference mud's viscosity and constant barite properties are approximations. Qualification of insulated pipe and managed-pressure equipment over the full hot drilling cycle remains unresolved.

The base case assumes that breakouts form immediately after rock exposure, before cooling can reduce the initial pressure requirement. Experiments with an assumed delay show how that requirement changes; they do not demonstrate that breakouts wait an hour to form.

The [approximation comparisons](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/science/approximation-comparisons.md) test individual assumptions and numerical resolution. None changes either deep-site programme to a pass, but the study does not cover every combination of uncertainty. The [limitations guide](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/science/limitations.md) explains the input uncertainties and the approximations in coolant delivery, trip timing and fluid displacement.

## Tests and reproducibility

Run the fast suite in the activated environment:

```bash
python -m pytest
```

The default skips physical regressions marked `slow`. To run the complete suite after building the water-property cache:

```bash
python -m pytest --runslow
```

Full physical runs can take an hour or more. Single-threaded BLAS avoids oversubscription during repeated solves; set `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` and `MKL_NUM_THREADS=1` before starting Python for those runs.

Saved reference outputs and numerical regression tables support comparison with the published calculations. The [changelog](https://github.com/ldocallaghan/BoreTHM/blob/main/CHANGELOG.md) records changes. Historical diagnostic figures use their stated programmes and should be interpreted with their captions.

## Find your way around the repository

| Location | Contents |
|---|---|
| [src/borethm/](https://github.com/ldocallaghan/BoreTHM/tree/main/src/borethm) | Installed package, physical models and study modules |
| [scripts/](https://github.com/ldocallaghan/BoreTHM/blob/main/scripts/README.md) | Standalone diagnostic and figure scripts |
| [benchmarks/](https://github.com/ldocallaghan/BoreTHM/blob/main/benchmarks/README.md) | Reference dataset with inputs, expected outputs and tolerances |
| [examples/](https://github.com/ldocallaghan/BoreTHM/tree/main/examples) | Worked reference example |
| [docs/](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/README.md) | Reading guide, model use, science and historical records |
| [src/borethm/data/](https://github.com/ldocallaghan/BoreTHM/tree/main/src/borethm/data) | Packaged observations and input-source records |
| [results/](https://github.com/ldocallaghan/BoreTHM/tree/main/results) | Retained numerical evaluations and trial evidence |
| [tests/](https://github.com/ldocallaghan/BoreTHM/tree/main/tests) | Unit checks and physical regressions, including fixed reference tables |
| [figures/](https://github.com/ldocallaghan/BoreTHM/tree/main/figures) | Diagnostic and field-comparison figures |

## How to cite and data credits

Cite BoreTHM using the [software DOI](https://doi.org/10.5281/zenodo.23549104). [CITATION.cff](https://github.com/ldocallaghan/BoreTHM/blob/main/CITATION.cff) provides the citation metadata. The [scientific bibliography](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/science/sources.md#references) lists the scientific sources.

The [benchmark dataset](https://github.com/ldocallaghan/BoreTHM/blob/main/benchmarks/README.md#how-to-cite) is published separately as [version 1.0 on Zenodo](https://doi.org/10.5281/zenodo.23565448).

The FORGE data come from the Geothermal Data Repository: [well 16A drilling data (GDR 1283)](https://doi.org/10.15121/1776602), [well 16A logs (GDR 1292)](https://doi.org/10.15121/1777912), [well 16B drilling data](https://doi.org/10.15121/1998591) and [deep-well temperature surveys](https://doi.org/10.15121/1893533). The Newberry extracts come from [well 55-29 stimulation data](https://doi.org/10.15121/1357916). These datasets are used under CC BY 4.0. The UD-1 image interpretation contains NERC materials ©NERC 2024.

The [FORGE 16A](https://github.com/ldocallaghan/BoreTHM/blob/main/validation/forge16a/README.md), [FORGE 16B](https://github.com/ldocallaghan/BoreTHM/blob/main/src/borethm/data/forge16b/README.md) and [Newberry](https://github.com/ldocallaghan/BoreTHM/blob/main/src/borethm/data/newberry/README.md) data guides describe the extracts and how to rebuild them. Other input sources are recorded alongside the corresponding data.

## Questions and contributions

Use [GitHub issues](https://github.com/ldocallaghan/BoreTHM/issues) for questions and problem reports. See [SUPPORT.md](https://github.com/ldocallaghan/BoreTHM/blob/main/SUPPORT.md) for what to include and [CONTRIBUTING.md](https://github.com/ldocallaghan/BoreTHM/blob/main/CONTRIBUTING.md) for development setup and proposing changes.

## Licence

The code in `src/`, `scripts/`, `tools/`, `tests/` and `examples/` is released under the [Apache License 2.0](https://github.com/ldocallaghan/BoreTHM/blob/main/LICENSE). The documentation, figures, results and summary PDF are released under [CC BY 4.0](https://github.com/ldocallaghan/BoreTHM/blob/main/LICENSE-docs). Data in `src/borethm/data/` and `benchmarks/data/` keep their source licences, as recorded in their data guides and in [NOTICE](https://github.com/ldocallaghan/BoreTHM/blob/main/NOTICE). Releases up to v1.3.4 were published under the MIT licence.
