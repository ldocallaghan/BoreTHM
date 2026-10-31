# Additional pressure checks

These reductions were declared after the original entry 9 results at `ee1dec1` were seen. They use the same recorded windows and saved pressures. The [development log](../../../../../docs/science/model-development.md#31-october-2026-additions-declared-after-the-pressure-results) gives their rules and predictions. Run `validation/model-development/entry-9/additions.py` from the repository root to rebuild the CSV files. No circulation solve is required.

The original P1 result files are unchanged. Primary, inferred secondary and earlier exploratory assignments retain their original roles. A filtered result is a sensitivity and does not replace a declared result.

| File | Contents |
|---|---|
| `pipe-inputs.csv` | Pipe geometry and period fluid inputs at every window contributing to a slope or EOW 18 endpoint difference; `flow_centre_gpm` identifies the group |
| `pipe-source-check.json` | EOW 19 pipe order checked against the original report, with page and source hash |
| `eow18-descriptive.csv` | Secondary differences between two depth stages on the full-insulated run; no regression confidence interval |
| `shallow-flow-levels.csv`, `shallow-flow-exponents.csv` | Every contributing shallow level and each separated-flow excess exponent |
| `nozzle-floor.csv` | Recorded flow, nominal density, recorded period nozzle area and ideal nozzle floor, by evaluated prediction |
| `floor-removals.csv` | Removals by well, assignment role and assembly, distinguishing physical windows from paired temperature predictions |
| `filtered-slopes.csv`, `filtered-depth-stages.csv`, `filtered-slope-exclusions.csv` | The original slope rule applied after the nozzle check |
| `filtered-flow-steps.csv` | The original flow-step rule applied after the nozzle check |
| `slope-comparison.csv`, `flow-step-comparison.csv` | Declared and filtered fits beside each other, including lost or newly eligible groups |
| `shallow-ratio-extrema.csv` | Exact primary shallow ratio endpoints, with the original observation columns |
| `manifest.json` | Accepted comparison commit, input and result hashes |

The floor is `rho_nominal * (Q/A)^2 / 2`, using SI units and discharge coefficient one. This ideal coefficient gives a lower floor than the calculation's coefficient 0.95. It introduces no fitted nozzle coefficient or other pressure term. The kinetic-energy equation is given by [NASA Glenn](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/bernoullis-equation/). [Ashena et al. (2021)](https://doi.org/10.1007/s13202-021-01203-4), in the discharge-coefficient subsection, discuss the drilling-nozzle convention and its uncertainty. The floor is conditional on intact nominal nozzles, the recorded density and single-phase circulation. Pressure recovery and unrecorded flow paths are not established by these records. A failed floor check flags inconsistent inputs or pressure under these assumptions; it does not diagnose a specific instrument fault. Windows excluded from the original pressure calculation remain excluded and do not acquire a nozzle definition from another assembly.

Flow exponents use excess defined as measured minus modelled pressure. The two EOW 38 observations near 237 gpm fall on opposite sides of a rounding boundary in the original 25-gpm centres. Their observed separation is below 25 gpm, so no exponent is calculated between them; each is paired with the 423-gpm observation. The two exponents describe one assembly and one excursion, with no repeat-run uncertainty estimate.

Removing a window can change eligibility under the unchanged minimum flow-level separation rule. The comparison table identifies any resulting new group. It does not select the retained observations by fit quality. EOW 18's negative endpoint differences are reported as observed; the full-insulated run does not supply a primary three-stage slope.
