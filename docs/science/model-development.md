# Model development: what changed and how it was tested

This page summarises the [development log](https://github.com/ldocallaghan/BoreTHM/blob/main/validation/model-development/LOG.md), which records changes to BoreTHM's physical calculations and their comparison with development observations.

## Method

FORGE 16A and 16B are development data. Their observations have already been examined and cannot provide an independent validation of changes motivated by their errors. Other FORGE wells were held back for blind tests.

A declaration describes the equations, inputs and predicted effects before a new comparison. Each comparison scores the same frozen samples from 16A and 16B and reports the differences between model and measurement, called gaps: standpipe pressure, hydraulic power, 16A bit temperature, the 16A run-in peak, 16A return temperature and 16B temperature. Bias is model minus measurement, and RMS is the root mean square of the assembly biases.

Every candidate stays in the log's disclosure table, whether it was kept or reverted.

## Changes in the current defaults

The default physics contains six changes from the log. Release v1.6.0 introduced the first two, and v1.8.0 the other four.

| Change | Log entry | Declared | Effect on the development gaps | Release |
|---|---|---|---|---|
| Pressure losses calculated component by component, each released as heat where it occurs | [Entry 1](https://github.com/ldocallaghan/BoreTHM/blob/main/validation/model-development/LOG.md#27-october-2026-entry-1-hydraulic-losses-and-heat-placement), with the equipment correction (D5) | Before scoring; the equipment correction followed the first score | 16A in-hole hydraulic power rose from 500 to 654 kW, against 928 kW measured. 16A bit temperatures rose by 1.3–3.7 °C. The 16B regular-pipe bias moved from −8.8 to −7.2 °C | v1.6.0 |
| Rock response of an infinite cylinder, from the exact solution | [Entry 3](https://github.com/ldocallaghan/BoreTHM/blob/main/validation/model-development/LOG.md#28-october-2026-entry-3-declaration-cylindrical-rock-response-r1) | Before scoring | Bit temperatures rose by 0.2–2.2 °C. Cold biases shrank, and the 16B trial bias grew from +3.0 to +4.6 °C | v1.6.0 |
| One flow-regime criterion for annulus pressure and heat transfer: a Herschel-Bulkley slot model with no yield stress, Gnielinski's correlation on the plastic viscosity and the Erge transition band | [Entry 8](https://github.com/ldocallaghan/BoreTHM/blob/main/validation/model-development/LOG.md#31-october-2026-entry-8-score) | Retrospective: the zero yield stress was chosen after entries 6 and 7 had been scored | The RMS of the nine 16A bit-temperature biases became 6.0 °C, against 5.6 °C before | v1.8.0 |
| Colebrook friction on a smooth pipe wall | [Entry 10](https://github.com/ldocallaghan/BoreTHM/blob/main/validation/model-development/LOG.md#31-october-2026-entry-10-sourced-pressure-options) | Before scoring | Pressure RMS fell from 479 to 432 psi on 16B and from 1,223 to 1,215 psi on 16A | v1.8.0 |
| Conical bore transitions at 11.5° in ordinary drill-pipe joints | [Entry 13](https://github.com/ldocallaghan/BoreTHM/blob/main/validation/model-development/LOG.md#4-november-2026-entry-13-tapered-drill-pipe-joints) | Before scoring, after the entry 12 scores had been seen | Pressure RMS fell from 432 to 332 psi on 16B and rose by 14 psi on 16A. 16B temperature biases grew by 0.6–0.7 °C | v1.8.0 |
| Generic pressure-loss allowances for named downhole tools, and the motor's no-load drop | [Entry 14](https://github.com/ldocallaghan/BoreTHM/blob/main/validation/model-development/LOG.md#5-november-2026-entry-14-tool-loss-allowances-on-the-adopted-calculation) | Before scoring | Pressure RMS fell from 1,228 to 1,030 psi on 16A and from 332 to 240 psi on 16B. The 16A bit RMS fell from 6.0 to 5.1 °C, and the warm 16B biases grew by 1.4–2.4 °C | v1.8.0 |

The FORGE comparisons also use kept inputs that change no site default: measured rotary power (entry 4), measured 16B mud properties (entry 5) and the installed drill-pipe dimensions (entry 12).

## Tried and not kept

Of the variants scored on the frozen samples, 17 were not kept, and one more candidate was removed before it was scored. The log keeps each with its score. Four examples:

- The first form of the hydraulic-loss change (entry 1) warmed every 16A bit by 8.4–16.1 °C. The warming came from motor passages modelled as narrow straight pipes, and the change was kept only after the equipment correction removed them.
- A Herschel-Bulkley annulus with a yield stress (entry 6) raised the RMS of the 16A bit biases to 10.0–24.6 °C, against 5.6 °C. It was not adopted, because the downhole yield stress is unmeasured.
- Catalogue connection dimensions for 16B (entry 10) brought the 16B pressure RMS as low as 153 psi. No measured bore supports them, and no correlation coefficient may be selected from a FORGE residual.
- A 30° joint taper (entry 13) has no published source and was scored as a sensitivity only.

## Where development stands

The latest scores, from the [entry 14 amendment](https://github.com/ldocallaghan/BoreTHM/blob/main/validation/model-development/LOG.md#entry-14-amendment-6-november-2026-score) of 6 November 2026, leave these gaps.

| Gap | Latest value |
|---|---|
| 16A standpipe pressure, RMS | 1,030 psi |
| 16B standpipe pressure on motorless assemblies, RMS | 60 psi |
| 16A hydraulic power, bias | −230 kW |
| 16B hydraulic power, bias | −120 kW |
| 16A bit temperature, RMS | 5.1 °C |
| 16A run-in peak, RMS | 34.8 °C |
| 16A return temperature, bias | −4.4 °C |
| 16B regular-pipe temperature, bias | +6.8 °C |
| 16B trial-pipe temperature, bias | +12.6 °C |

The 16B pressure value includes a correction to the tool assignment that was declared after the entry 14 scores had been seen. It tests no unseen well. At 216–238 US gal/min, 163–220 psi of the shallow 16B pressure gap remains unexplained.

## Blind tests so far

A blind test uses a well whose measurements were read only after the method, inputs and predictions had been committed.

**56-32 standpipe pressure.** On 196 ten-minute drilling windows at 7,219–8,809 ft, with measured standpipe pressure less the reported motor differential as the target, the lower end of the v1.6.0 interval has a median residual of -9.2% for BHA 9 and +7.2% for BHA 10. The [validation page](validation.md#forge-56-32-standpipe-pressure-on-an-unseen-well) gives the details.

**56-32 return temperature.** The forecast of surface return temperature with the v1.8.0 defaults was scored on 15 November 2026, in commit [`c1b9e27`](https://github.com/ldocallaghan/BoreTHM/commit/c1b9e27b022b3226c9982e2aa6ab424f28d80135) on the `gap-closure` branch. Over 401 windows the root-mean-square error is 20.8 °C. On assemblies 6 to 11 it is 0.9–2.1 °C, and on the shallower assemblies 2 to 5 the bias is −28.8 to −39.2 °C. A check made after scoring found that the inlet temperature recorded before 18:12 on 15 February 2021 is inconsistent with the energy balance in 113 of the 136 shallow windows. On the 288 windows whose data pass that check, the root-mean-square error is 5.5 °C. The [diagnosis](https://github.com/ldocallaghan/BoreTHM/blob/fd15780/validation/forge56-32/diagnosis/README.md) gives the evidence.

**58-32 standpipe pressure.** On 1 November 2026, the working calculation of that date read high in all 62 windows of one motorless assembly, by 140–274% of the measured event median. The log records input inconsistencies that the comparison could not resolve, and it changed no default.

## Full record

The [development log](https://github.com/ldocallaghan/BoreTHM/blob/main/validation/model-development/LOG.md) gives every declaration, score and decision, with links to the results archives.
