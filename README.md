# BoreTHM: models of circulating temperature and borehole stability for drilling into superhot rock

BoreTHM is an open-source Python toolkit for assessing drilling programmes in superhot geothermal rock. It couples fluid circulation and heat transfer with borehole stability to help researchers and engineers examine fluid pressure limits and equipment temperatures under different well designs and operating conditions.

The circulation model is checked against Utah FORGE field data. Worked site assessments show how the models are applied, with assumptions and limitations reported alongside the results.

- [Documentation guide](docs/README.md): choose a reading path.
- [Get started](#get-started): set up Python and run an assessment.
- [Read a result](#reading-a-result): understand the outputs and status labels.
- [Explore the examples](#example-results): site findings and their controlling constraints.
- [Understand the models](#models-and-evidence): methods and field comparisons.

## Get started

Use Python 3.14.4 with the locked dependencies to reproduce the reference calculations. The models run directly from `src/`.

```bash
git clone https://github.com/ldocallaghan/BoreTHM.git
cd BoreTHM
python -m venv .venv
```

Use `python3` for the environment-creation command if your system does not provide `python`. Activate the environment with `.\.venv\Scripts\Activate.ps1` in Windows PowerShell, or `source .venv/bin/activate` on Linux and macOS. Then install the dependencies and build the water-property cache:

```bash
python -m pip install -r requirements-lock.txt
python src/water_table.py
```

The IAPWS-95 cache is a one-time build. Run a first assessment from the repository root:

```bash
python src/site_evaluation.py --site newberry --json newberry.json
```

The command prints the assessment and saves its inputs, results and calculation provenance as JSON. Evaluations take several minutes; weighted-fluid cases require repeated coupled solves and can take longer.

## Run your own assessment

The built-in site keys are `soultz`, `united-downs`, `larderello`, `pannonian` and `newberry`.

```bash
python src/site_evaluation.py --site soultz --json soultz.json
python src/comparative_sites.py
```

The first command evaluates one site; the second reports all five. Use `python src/site_evaluation.py --help` for the CLI options.

For a new site, follow the [site-input guide](docs/guides/new-site.md) and copy [the documented template](examples/site_template.py). It records units and sources, and checks the inputs before evaluation. The worked example can validate the template without running the full calculation:

```bash
python examples/new_site.py
python examples/new_site.py --evaluate --json result.json
```

The template starts with Soultz's inputs. Replace them with the new site's measurements or explicitly sourced assumptions.

## Reading a result

The [output guide](docs/guides/interpreting-results.md) maps the JSON fields and explains schedule identity.

Start with `status` and its reasons, then inspect the components that set it. The report includes the operating programme, thermal and hydraulic outputs, stability in each cycle state, allowable mud densities and equipment checks. The JSON retains every evaluated case and the source of each input.

| Status | Meaning for the evaluated programme and assumptions |
|---|---|
| GO | The modeled checks pass without the additional conditions listed by the evaluator. |
| CONDITIONAL | The assessment depends on stated conditions, such as prescribed fluids or a circulation schedule. Read those conditions before using the result. |
| NO-GO | A modeled gate fails for this programme and these assumptions; the reasons identify the failing components. |
| INDETERMINATE | A required numerical result did not converge, or an equipment qualification remains unresolved without another decisive failure. |

An overall NO-GO can coexist with an INDETERMINATE coating check. Exceeding a manufacturer's stated coating rating identifies a qualification question. It does not predict a particular failure mode.

A **mud-weight window** is the allowable range of fluid density: enough pressure to keep the borehole stable while staying below the modeled fracture-pressure limit. BoreTHM calculates the range that satisfies all evaluated depths, operating states and stress/strength cases, separately for drilling and trips.

Two pressure descriptions appear in the outputs:

- **Target SG-equivalent** expresses pressure as an equivalent static column at the target. It is a local stability diagnostic, with the existing friction/backpressure treatment.
- **Surface SG at 20 °C** is fluid density divided by 1,000 kg/m³. The combined pressure constraints set the allowable range of that surface density.

A positive target interval does not establish a workable whole-hole fluid. If the required minimum density exceeds the permitted maximum, no mud density satisfies both pressure limits. The densities reported in that situation are calculation inputs and cannot be prescribed.

## Example results

The worked assessments target rock at 400 °C. Every status below refers to **this programme and these assumptions**.

| Site | Target, km | Status | Main finding |
|---|---:|---|---|
| Soultz-sous-Forêts | 10.70 | NO-GO | No drilling or trip fluid density satisfies all pressure limits; the best attempted run-in exceeds the tool limit. |
| United Downs | 12.86 | NO-GO | No drilling or trip fluid density satisfies all pressure limits; drilling and run-in exceed the tool limit. |
| Larderello | 2.40 | CONDITIONAL | Requires weighted drilling and trip fluids. |
| Pannonian Basin | 9.71 | NO-GO | No drilling or trip fluid density satisfies all pressure limits; coating qualification is unresolved. |
| Newberry | 3.63 | GO | The evaluated programme passes with water. |

These sites have different evidence quality. Soultz and United Downs use measured or calibrated stresses and strengths, extrapolated to the targets. Larderello and Pannonian retain unsourced strength assumptions. Newberry's well check does not reproduce the observed pattern in every rock type. The [input-source records](data/sites/stress_sources.md) explain those differences.

### Local stability and the complete programme

At Soultz, eight of nine selected stress/strength cases have an open target drilling interval; at United Downs, two of four do. Both complete programmes remain **NO-GO for this programme and these assumptions** because no mud density satisfies the pressure limits throughout the evaluated hole, and tool-temperature limits are exceeded.

<details>
<summary>Target-depth case table and its interpretation</summary>

Need and limit are static-column SG-equivalent values at the target. They differ from the surface mud densities a programme would prescribe. The saved target stability-cycle verdict also checks connections and the trip; it excludes separate whole-hole, tool and equipment gates. Each site's reference thermal/hydraulic solution is reused across cases without a fresh coupled evaluation for each case. An open interval does not prove the saved attempted fluid lies inside it.

| Case | UCS, MPa | Drilling need / limit, SG-equivalent | Target stability-cycle verdict |
|---|---:|---|---|
| Soultz: SHmax lower bound (0.90 Sv) | 100 | 1.230 / 1.296 | CONDITIONAL |
| Soultz: SHmax lower bound (0.90 Sv) | 115 | 1.209 / 1.296 | CONDITIONAL |
| Soultz: SHmax lower bound (0.90 Sv) | 130 | 1.189 / 1.296 | CONDITIONAL |
| Soultz: SHmax mid-range | 100 | 1.271 / 1.296 | CONDITIONAL |
| Soultz: SHmax mid-range | 115 | 1.251 / 1.296 | CONDITIONAL |
| Soultz: SHmax mid-range | 130 | 1.230 / 1.296 | CONDITIONAL |
| Soultz: SHmax upper bound (1.05 Sv) | 100 | 1.313 / 1.296 | NO-GO |
| Soultz: SHmax upper bound (1.05 Sv) | 115 | 1.292 / 1.296 | CONDITIONAL |
| Soultz: SHmax upper bound (1.05 Sv) | 130 | 1.272 / 1.296 | CONDITIONAL |
| United Downs: intact, 0 K | 203 | 1.169 / 1.220 | CONDITIONAL |
| United Downs: intact, 40 K | 172 | 1.205 / 1.220 | CONDITIONAL |
| United Downs: weak zones, 0 K | 147 | 1.234 / 1.220 | NO-GO |
| United Downs: weak zones, 40 K | 118 | 1.267 / 1.220 | NO-GO |

Soultz target 10.70 km; United Downs target 12.86 km. Sv is vertical stress. United Downs retains the existing 0 K / 40 K strength-calibration cases; these labels do not specify a newly applied cooling intervention. These 13 selected scenarios are not samples from a probability distribution. Eight of nine and two of four count the cases with an open target drilling interval. They do not estimate a probability of successful drilling. All verdicts refer to this programme and these assumptions.

</details>

### Independent programme failures

The bounds below combine the pressure constraints across the evaluated depths, states and cases. They are expressed as surface SG at 20 °C; width is upper minus lower. A negative width means the required minimum density exceeds the permitted maximum. Both sites remain **NO-GO for this programme and these assumptions**.

| Site and state | Lower / upper, surface SG | Width, SG |
|---|---|---:|
| Soultz drilling | 1.37892 / 1.31256 | -0.06637 |
| Soultz trip | 1.44362 / 1.36461 | -0.07901 |
| United Downs drilling | 1.33132 / 1.28519 | -0.04613 |
| United Downs trip | 1.40134 / 1.36503 | -0.03631 |

**Tool peaks, drilling / connection / best attempted run-in:** Soultz: 197.0 / 197.3 / 201.2 °C; United Downs: 205.7 / 206.1 / 224.5 °C. The limit is 200 °C. Best attempted means the lowest peak among the schedules searched. A wider search could find a lower one. Soultz's reference FORGE-practice run-in reaches 214.5 °C, separately from the 201.2 °C search result.

Reference-practice coating run-in maxima are 274.3 °C at Soultz and 287.4 °C at United Downs, against the stated 204 °C rating. Both retain **INDETERMINATE qualification**. The coating histories are not necessarily those of the best attempted tool schedule.

Soultz's 0.017 SG-equivalent target drilling deficit and 1.2 °C tool excess are local facts. They do not measure how close the entire programme is to passing: incompatible density requirements elsewhere in the hole and coating qualification remain independent issues.

Sources: [Soultz reference](results/v1.3.4/ci/38186784798-1/reference/soultz.json), [United Downs reference](results/v1.3.4/ci/38186784798-1/reference/united-downs.json), and settings-matched L4 base trials for [Soultz](results/v1.3.4/ci/38186784798-1/levers/soultz/L4/summary.json) and [United Downs](results/v1.3.4/ci/38186784798-1/levers/united-downs/L4/summary.json). The [reader summary](docs/guides/summary.md), also available as a [two-page PDF](output/pdf/summary-v135.pdf), gives the findings and open questions together.

### Design comparisons

No evaluated single-lever setting or evaluated pair made either deep site's programme pass. Deeper casing gives Soultz an allowable trip-fluid density range while drilling and tools still fail. Lower viscosity can give United Downs an allowable drilling-fluid density range while other gates still fail. Stronger insulation cools tools but leaves pressure and pump constraints.

Only one pair per site was evaluated, and continuous searches sampled settings. The [lever study](docs/science/design-comparisons.md) gives the tested settings, remaining failures and equipment-availability evidence. It establishes no complete operating envelope or general impossibility.

## Models and evidence

The circulation model solves the downgoing and returning fluid temperatures with frictional heating and heat transfer through the pipe, casing and surrounding rock. Rock conduction carries each depth through its exposure and circulation pauses. Fluid properties and pressure losses feed back into the stability and tool calculations.

| Model or check | Role | Evidence and detail |
|---|---|---|
| Circulation | Fluid temperatures, heat transfer and hydraulics | [Utah FORGE comparisons and published-model benchmark](docs/science/validation.md#circulation) |
| Rock reheating | Temperature recovery when circulation stops | [Analytic checks and the limits of the FORGE pause comparison](docs/science/validation.md#rock-reheating) |
| Borehole stability | Breakout width and pressure requirements | [UD-1 strength calibration and other well checks](docs/science/validation.md#stability-checks) |
| Spallation, drilling rate and creep | Exploratory estimates of quench effects and closure | [Physical models and their limits](docs/science/models.md#drilling-rate-and-creep) |

The circulation/FORGE comparisons, strength calibration and other checks have distinct scopes. They do not validate a complete 10-13 km drilling programme. Full derivations and diagnostic figures are in the [physical-model guide](docs/science/models.md); the [bibliography](docs/science/sources.md#references), [material properties](data/materials.md) and [site inputs](data/sites/stress_sources.md) retain their sources.

## Scope and limitations

BoreTHM screens a stated drilling programme. A passing result is conditional on the modeled inputs and checks; a failure does not settle whether a different design or existing technology could drill the site. Reservoir production and detailed well-integrity design are outside the assessments.

The deep targets lie well below measured stress data. Strength calibration depends on the assumed stress profile, and the reference mud's rheology and constant barite properties are approximations. Full-cycle qualification of insulated pipe and managed-pressure equipment remains unresolved for the hot conditions studied.

Immediate exposure and the skin heuristic prevent cooling from reducing the initial drilling demand in the base model. The failure-delay experiments test hypotheses that no data yet support. They give no evidence that breakouts wait an hour to form. Near-bit pre-cooling and breakout growth remain separate open questions.

The base deep-site verdicts remain NO-GO for this programme and these assumptions across the [A1-A9 comparisons performed](docs/science/approximation-comparisons.md). These generally change one approximation at a time and do not cover every joint uncertainty. Coolant delivery, trip timing and fluid displacement are among the [deferred approximations](docs/science/limitations.md). Pannonian's historical 0.041 °C tool threshold remains numerically unresolved.

## Development and feedback

Model expansion is paused for specialist feedback on the assumptions and practical applicability. Corrections to demonstrated defects remain in scope. Feedback is most useful when it identifies a relevant observation or qualification record, or explains which assumption changes a decision. The [reader summary](docs/guides/summary.md#questions-for-specialist-discussion) sets out the focused research questions.

**H-01 trigger met; implementation deferred by project priority.** Soultz's casing and paired interventions meet the proximity trigger for a common event timeline, but other gates still fail and no operating range is claimed. Revisit before a near-threshold feasibility claim, or when feedback or new data makes timing decision-relevant. Coolant delivery and fluid displacement retain distinct triggers in the [development priorities](docs/maintenance/development.md).

## Tests and reproducibility

Run the fast suite in the activated environment:

```bash
python -m pytest
```

The default excludes physical regressions marked `slow`. To include the complete suite after building the water-property cache:

```bash
python -m pytest -m "slow or not slow"
```

Full physical runs can take an hour or more. Single-threaded BLAS avoids oversubscription during repeated solves; set `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1` before starting Python for those runs.

Saved reference outputs and numerical regression tables support comparison with the published calculations. [Release records](docs/releases/README.md) document the environment and verification; the [changelog](CHANGELOG.md) records changes. Historical diagnostic figures use their stated programmes and should be interpreted with their captions.

## Find your way around the repository

| Location | Contents |
|---|---|
| [src/](src) | Physical models and evaluation scripts |
| [examples/](examples) | Site template and worked example |
| [docs/](docs/README.md) | Reading guide, model use, science and historical records |
| [data/](data) | Extracted observations and input-source records |
| [results/](results) | Retained numerical evaluations and trial evidence |
| [tests/](tests) | Unit checks and physical regressions, including fixed reference tables |
| [figures/](figures) | Diagnostic and field-comparison figures |

## Citation and data credits

Use [CITATION.cff](CITATION.cff) for the software citation. The [scientific bibliography](docs/science/sources.md#references) lists the scientific sources.

The FORGE data come from the Geothermal Data Repository: [well 16B drilling data](https://doi.org/10.15121/1998591) and [deep-well temperature surveys](https://doi.org/10.15121/1893533). The Newberry extracts come from [well 55-29 stimulation data](https://doi.org/10.15121/1357916). These datasets are used under CC-BY 4.0. The UD-1 image interpretation contains NERC materials ©NERC 2024.

The [FORGE](data/forge16b/README.md) and [Newberry](data/newberry/README.md) data guides describe the extracts and how to rebuild them. Other input sources are recorded alongside the corresponding data.

## Licence

The code in `src/`, `tools/`, `tests/` and `examples/` is released under the [Apache License 2.0](LICENSE). The documentation, figures, results and summary PDF are released under [CC BY 4.0](LICENSE-docs). Data in `data/` keep their source licences, as recorded in their data guides and in [NOTICE](NOTICE). Releases up to v1.3.4 were published under the MIT licence.
