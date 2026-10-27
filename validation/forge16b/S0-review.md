# FORGE 16B whole-well comparison: S0 review

Baseline: `85f23db51f6661e6ca09bd05c16b9ffb48881d83`, branch `forge16b-wholewell`, 26 October 2026. This stage extracts observations and records the comparison method. No new model prediction, error calculation or fit has been run. Existing model files and saved physical results are unchanged.

## Coverage

The source has 746,904 ten-second rows. The EYE downhole-temperature channel has 59,960 non-null values. Its quality checks reject nine freezing-point values and 497 rows in short isolated jumps. The [protocol](comparison_protocol.md) defines the thresholds and half-hour sampling before comparison with the model. The present rules retain **109 candidate samples**.

EOW denotes the End of Well Report. Its bottom-hole assembly (BHA) numbers differ from the contractor and Eavor trial numbers. EOW 17–20 correspond to trial 10–13. MD denotes measured depth along the hole. Counts below are source rows, including repeated or held telemetry. A ten-second row is not necessarily a new downhole measurement.

| EOW BHA | Contractor/trial | Dates with on-bottom EYE | Run depth, ft MD | Pipe | Accepted drilling EYE rows | Candidate samples | Temperature position above bit |
|---|---|---|---:|---|---:|---:|---|
| 3 | 2 | 2023-04-30–2023-05-01 | 1181–4353 | regular | 788 | 3 | Unresolved |
| 4 | 3 | 2023-05-01–2023-05-02 | 4353–4845 | regular | 547 | 2 | Unresolved |
| 11 | 4 | 2023-05-13–2023-05-13 | 4980–5269 | regular | 765 | 4 | 22 ft, drawing comments |
| 12 | 5 | 2023-05-13–2023-05-15 | 5269–5957 | regular | 3666 | 12 | 22 ft, drawing comments |
| 13 | 6 | 2023-05-15–2023-05-16 | 5957–6545 | regular | 3500 | 14 | 22 ft, drawing comments |
| 14 | 7 | 2023-05-16–2023-05-18 | 6545–6610 | regular | 181 | 0 | 22 ft, drawing comments |
| 15 | 8 | 2023-05-18–2023-05-18 | 6610–6950 | regular | 2156 | 4 | 22 ft, drawing comments |
| 16 | 9 | 2023-05-18–2023-05-21 | 6950–7584 | regular | 4510 | 15 | 22 ft, drawing comments |
| 17 | 10 | 2023-05-21–2023-05-21 | 7584–8085 | regular | 2667 | 14 | 84 ft, assumed |
| 18 | 11 | 2023-05-21–2023-05-23 | 8085–8585 | full IDP | 2030 | 10 | 84 ft, assumed |
| 19 | 12 | 2023-05-25–2023-05-25 | 8585–9255 | partial IDP | 1836 | 10 | 84 ft, drawing comments |
| 20 | 13 | 2023-05-25–2023-05-27 | 9255–9800 | regular | 1752 | 11 | 84 ft, drawing comments |
| 26 | not assigned | 2023-06-03–2023-06-04 | 9853–9863 | regular | 0 | 0 | No documented MWD; excluded |
| 27 | not assigned | 2023-06-04–2023-06-04 | 9863–10250 | regular | 1032 | 5 | 84 ft, assumed |
| 38 | not assigned | 2023-06-17–2023-06-17 | 10503–10947 | regular | 874 | 5 | 84 ft, assumed |

The [period inventory](period_inventory.csv) also preserves raw counts and rejection counts. Its raw coverage uses the full run depth interval and the on-bottom/flow test; accepted drilling counts add the penetration-rate test, quality checks and 5-ft boundary exclusions. These counts therefore have different denominators.

The short EOW 14 interval has no qualifying half-hour window. EOW 26 has no documented measurement-while-drilling (MWD) assembly and its held channel is excluded. The two-level requirement also removes some stable or sparsely updated periods. The retained samples cover selected drilling windows, not every circulation period. In particular, the supplied 17 June daily mean and the retained drilling-window means use different selections and must remain separately labelled.

## Trial channel check

The daily check uses bit depth within 5 ft of hole depth and flow above 300 US gal/min, without the later drilling-progress and quality criteria. The source has no flow above 2,000 gal/min in these selected daily rows. These are calendar-day means; Eavor reports run averages.

| Date | Trial BHA | Source rows | Pason daily mean, °F | Supplied daily check, °F | Eavor run mean, °F | Pason minus Eavor, °F |
|---|---:|---:|---:|---:|---:|---:|
| 2023-05-21 | 10 | 3350 | 179.935 | 179.9 | 180 | -0.065 |
| 2023-05-23 | 11 | 2480 | 149.641 | 149.6 | 149 | +0.641 |
| 2023-05-25 | 12 | 2226 | 165.166 | 165.2 | 164 | +1.166 |
| 2023-05-27 | 13 | 2157 | 220.473 | 220.5 | 220 | +0.473 |

All four supplied daily checks reproduce within 0.06 °F. Agreement with Eavor identifies the channel used by the existing trial comparison; it does not independently identify sensor response or the sensing medium. Filtered daily means are saved separately in [trial_mean_check.csv](trial_mean_check.csv).

## Operating inputs

Ranges below describe accepted drilling EYE rows, before half-hour coverage exclusions. Temperatures are the paired Pason inlet and outlet. Cooler counts are report annotations; a count is not inferred from temperature. The [input summary](period_input_summary.csv) includes every run's cooler context, nozzle sizes, sensor evidence and mud-report locators.

| EOW BHA | Flow, US gal/min | Inlet, °F | Outlet, °F |
|---|---:|---:|---:|
| 3 | 603.1–1220.3 | 122.0–133.9 | 140.9–145.5 |
| 4 | 1003.6–1239.5 | 69.4–133.8 | 113.4–145.3 |
| 11 | 536.1–710.0 | 74.9–109.8 | 98.6–118.9 |
| 12 | 534.7–639.9 | 75.5–116.8 | 87.3–122.6 |
| 13 | 531.2–640.7 | 80.5–86.8 | 91.7–102.7 |
| 14 | 596.8–607.0 | 72.5–84.2 | 98.0–99.9 |
| 15 | 534.8–624.6 | 73.8–83.9 | 80.7–97.1 |
| 16 | 531.4–637.4 | 67.9–89.6 | 86.1–107.6 |
| 17 | 568.6–651.1 | 79.1–106.8 | 99.1–118.0 |
| 18 | 552.5–734.1 | 84.2–129.5 | 138.6–158.2 |
| 19 | 362.9–743.3 | 83.7–104.6 | 124.2–139.8 |
| 20 | 545.6–713.3 | 75.8–105.0 | 92.5–129.3 |
| 26 | none | none | none |
| 27 | 546.2–778.0 | 80.3–98.5 | 102.4–124.0 |
| 38 | 593.5–736.3 | 82.7–103.8 | 103.0–118.7 |

All 54 mud-temperature LAS files explicitly identify inlet and outlet in °F. Comparing rounded-depth Pason means with the final composite LAS gives mean inlet and outlet differences of +5.12 and +4.09 °F over 8,756 usable paired depths. Two physically invalid pairs are listed separately. The composite represents a different aggregation, so these differences do not support a temperature correction or establish a sensor bias.

The mud-report extraction contains 72 rows with page and sample descriptions. Eight merged-cell rows retain only the unambiguous density, funnel viscosity, plastic viscosity (PV) and yield point (YP); their remaining cells remain in the parsing audit. Later reports often omit PV and YP. Missing measurements have not been converted to zero. Mud ranges in the input summary describe reports dated from the first EYE day through the day after the last EYE day; the reports end at 06:00 and their samples can be older. These ranges are context, not applied fluid boundary conditions. Sample descriptions must govern any later assignment.

The early 14.75-inch section used approximately 8.8–9.1 lb/US gal mud. Later sections generally used 8.3–8.6 lb/US gal. The installed trial evaluator uses water properties. That difference and the missing rheology need an explicit treatment before whole-well calculation.

Coolers were installed during rig-up (EOW p199). During trial 10, units were switched off at 7,584 and 7,867 ft (p259). The 23 May report says one unit was running before a second was turned on at 8,346 ft (p261); the trial narrative describes initially stopped chillers and one later started. Both accounts are retained. Reports on 26, 28 and 29 May state three operating units (pp266/268/272). Exact counts during other temperature windows are unverified. Measured inlet temperature supplies the thermal boundary.

## Inputs requiring review before S1

1. **Temperature positions.** EOW 3 gives a 69-ft survey offset without identifying the temperature element. EOW 4 is unresolved. Their temperature-offset fields remain blank. EOW 27 and 38 have a lower-component sequence consistent with 84 ft, which is recorded as an assumption requiring review. The pre-trial EOW 11–16 drawings explicitly say EYE = 22 ft; EOW 19/20 say EYE = 84 ft. Retaining 84 ft for trial 17/18 follows the existing trial treatment.
2. **Trial geometry.** The motor length for EOW 17 differs between Figure 90 (35 ft) and Appendix B (41.87 ft). Proposed treatment: retain the existing aggregate geometry for the four trial comparisons and identify borrowed component dimensions for other runs. Early geometry must represent the 14.75-inch hole before intermediate casing was installed.
3. **Mud.** Decide whether the existing water-property approximation remains the primary comparison, or recorded mud properties are used by period. The latter needs a stated missing-PV/YP treatment. No rheology has been filled across fluid-system changes.
4. **Pressure and motor heat.** The Pason header only says differential pressure. Motorless assemblies have values, and some candidate means are negative. Proposed treatment: publish the raw differential and standpipe-minus-differential diagnostics; use the existing non-negative differential load for motor-face heat only on documented motor assemblies, with zero motor-face heat for documented motorless assemblies. This cannot establish a measured motor-only pressure loss. Pressure residuals can include motor/MWD losses absent from the model.

The [comparison protocol](comparison_protocol.md) also fixes the unfitted film multiplier of 1.0, the 0.75 sensitivity and the existing fitted insulated-pipe conductivity. It defines the optimistic full-recovery diagnostic separately from the cumulative exposure clock. For that clock, circulation is recorded at flow greater than 100 and no greater than 2,000 US gal/min; observed off spells use 0–100 US gal/min. Missing flow and source gaps do not establish known off time. Reset candidates require an observed spell longer than two hours; no pumps-off or run-in transient model is included.

The [source manifest](source_manifest.json) identifies source files and hashes. Rebuild commands and data attribution are in the [archive guide](README.md). Work stops here for S0 review.
