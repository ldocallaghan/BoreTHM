# FORGE 16B whole-well comparison: input protocol

S0, 26 October 2026. Baseline `85f23db51f6661e6ca09bd05c16b9ffb48881d83`, on branch `forge16b-wholewell`. This protocol and its candidate samples precede any new model prediction or error calculation. Input questions below require review before the corresponding comparisons can run.

## Quantities and independence

Compare the Pason `EYE TEMP (F)` channel with bore-fluid temperature at the documented EYE position. This retains the comparison quantity of the existing 16B study. Its four trial daily means reproduce the source report values to within 1.2 °F. That agreement identifies the temperature channel; it does not independently establish sensor response or the sensing medium.

Use the unfitted annulus-film multiplier of 1.0 as primary, with 0.75 as a fixed sensitivity. Do not invoke the existing film or pipe-conductivity fitting entry points. For insulated pipe, retain the previously fitted effective conductivity of 4.9237482416889895 W/(m K), recorded in the baseline `tests/golden/validate_forge16b.json`, in both film cases. State its fitted-input dependency. Regular-pipe periods have no insulated-pipe parameter.

EOW means the End of Well Report; its BHA identifiers count every assembly. The Eavor and contractor identifiers use a different sequence. EOW BHAs 17, 18, 19 and 20 correspond to trial BHAs 10, 11, 12 and 13. Trial 10 and 13 contributed to the existing film fit; trial 11 contributed to the insulated-pipe fit; trial 12 was held out. Other periods contributed to neither fit. Report those groups separately, including in pooled metrics.

## Source record and units

Read GDR 1516's `16B_Pason.zip/10 Second Data.csv` by header name. `EYE TEMP (F)` is column 92 when counted from one. It has 746,904 rows and 412 columns, from 26 April to 21 July 2023. Replace only the source null `-999.25` with a missing value. Do not forward-fill the EYE channel. Retain source row numbers in the selected scratch record and sampled comparisons.

Keep the source clock as displayed. When an epoch coordinate is needed, attach UTC without shifting the displayed times; this is a deterministic coordinate, not an assertion of the rig's time zone. Check report timing against drilling depths. Daily reports describe the preceding reporting interval ending at 06:00; a report date is not a midnight boundary.

Interpret the Pason inlet/outlet channels as °F. The independent LAS headers explicitly label `MTIA.F` and `MTOA.F`; their same-depth comparison is saved separately. A final depth-indexed composite is not an exact time match and must not replace the measured time-series inlet. Read LAS dates from headers, because some filenames have inconsistent month labels.

## EYE quality rules

Apply the following to the source series before selecting model samples. Keep every rejection and its source row.

- Accept temperatures strictly above 32 °F and no higher than 482 °F, corresponding to above 0 °C through 250 °C. The upper bound is deliberately wider than the measured whole-well temperature range. A value such as 337 °F is not rejected by that bound alone.
- To identify isolated jumps, compute a centred 31-minute rolling median of physical-range values, requiring at least 30 non-null source rows. A candidate differs from that median by more than 40 °F. Group consecutive candidates, breaking at a source gap longer than 20 s. Reject a group only when it lasts at most ten minutes and there are at least six non-candidate physical-range rows on each side within ten minutes. Their two median reference values must differ by at most 15 °F; each rejected row must differ from each reference by more than 40 °F. This can identify a short burst containing several erroneous levels.
- A comparison window requires at least two distinct accepted EYE temperature levels and at least 90 qualified accepted source rows, representing 15 minutes at the stated cadence. Distinct levels do not prove independent telemetry updates: the series is quantised, and held values remain a limitation. The rule excludes some genuinely stable or sparsely updated periods; retain their counts and raw observations.

These rules remove nine physical-range rows and 497 isolated-jump rows from the complete source series. The raw daily trial check is retained alongside the filtered check. Its definition differs from the more restrictive comparison sampling below.

## Sampling and coverage

Place sample centres on the displayed clock's half-hour grid. Use each half-open centred window `[centre - 15 min, centre + 15 min)`. A source row qualifies while flow is greater than 300 and no greater than 2,000 US gal/min, the bit is within 5 ft of hole depth, and the reported penetration rate is greater than 1 ft/h. Require at least 0.5 ft of hole-depth range in the qualified window. This excludes circulation at bottom without documented drilling progress.

Assign periods using the EOW bit-record depth intervals in `run_definitions.csv`. Exclude rows within 5 ft of either interval boundary from comparison sampling, avoiding ambiguous crossover rows. Inventory raw EYE coverage over the full depth interval separately. BHA 26 has no documented MWD in its listed assembly and no usable two-level candidate window; do not treat its held EYE value as a downhole observation.

Average temperature and all paired operating inputs over the same accepted qualified rows. Reject a window with missing paired inlet, outlet, standpipe or reported differential-pressure data. Preserve both the unrounded means and the source-row range. Apply no offset to any temperature. The present rules produce 109 candidate windows, with no candidate for the short EOW BHA 14 run or the BHA 26 interval. The candidate list and all rejected windows are saved before model errors are calculated.

## Well, string and fluid inputs

Use the existing 16B surveyed trajectory and the existing 16A 216-day formation-temperature profile by true vertical depth, without an extra 300 ft temperature shift. The spatial relationship is already represented by each well's true vertical depth. Retain the baseline rock conductivity and volumetric heat capacity. Do not fit the formation temperature.

The early 14.75-inch hole predates intermediate casing. Its primary geometry must represent the casing present during that run, without placing the later 11.75-inch casing throughout an unfinished hole. The deeper 9.5-inch periods use the recorded casing programme and the existing geometry-construction treatment. This changes study inputs by period, not a package function.

Preserve both EOW and contractor BHA identifiers. Use the component dimensions and lengths with their individual source locators. The drawings give an EYE offset of 22 ft for the pre-trial EOW BHAs 11–16. EOW BHAs 19 and 20 explicitly give 84 ft. Retaining 84 ft for trial 17/18 follows the existing comparison and the trial's stated assembly continuity. The following require S0 rulings:

- EOW BHA 3 has a 69-ft survey offset, but no verified temperature-element offset. BHA 4's temperature offset is unresolved. Do not silently identify a survey marker as the EYE temperature position.
- EOW BHAs 27 and 38 have a lower-component sequence consistent with the 84-ft trial position, but that offset has not been independently identified for these later assemblies. Label 84 ft as an assumption if approved.
- Trial geometry sources disagree. Figure 90 gives a 35-ft motor for EOW BHA 17, while Appendix B gives 41.87 ft; the existing comparison combines its stated dimensions with trial aggregate lengths. For continuity, the proposed primary retains the existing aggregate treatment on the four trial runs and records the source discrepancy. New runs need their own component lengths, with any borrowed dimensions identified.

The ordinary drill pipe is recorded as 5.5-inch, 24.7 lb/ft. IDP is confined to the trial's full and partial strings in the identified comparison periods; receipt or storage of IDP before the trial does not establish that it was in a drilling string. Preserve the trial's 2,378.5 ft lower regular-pipe section in its partial-IDP run. Record the actual bit nozzles per run; EOW BHA 27 has three 14/32-inch and six 13/32-inch nozzles in the 4 June report.

Retain mud sample density and rheology with their report date and sample description. Missing PV or YP is missing, not zero. The 14.75-inch periods used heavier, more viscous mud than the later low-solids programme. The existing trial model uses water properties. Before S1, decide whether that approximation is retained as the common primary or replaced with recorded per-period mud inputs, and specify the missing-rheology treatment. Do not interpolate or copy a rheology measurement across a fluid-system change without an explicit basis.

Represent cooler effects through measured inlet temperature. Keep cooler annotations as contextual inputs. The rig's 23 May report says one unit was running and a second was turned on at 8,346 ft; the trial summary describes initially stopped chillers and one later brought online. Report that difference. Do not infer cooler counts from inlet temperature alone.

## Exposure and recovery diagnostic

The primary uses the existing cumulative circulation clock and its exposure floors. Reconstruct the clock with observed flow, preserving data gaps and missing-flow counts. A missing flow value does not establish a known pumps-off interval.

For the optimistic recovery bound, reset exposure after a continuously observed pumps-off spell longer than two hours, with the same full-recovery assumption and existing floor as the 16A diagnostic. Use the identical samples and comparison quantity in each pair. Record a long-off interval separately from a trip to surface, which additionally requires a recorded bit depth shallower than 1,000 ft. This is an input-clock diagnostic, without a new transient calculation.

## Pressure and energy comparisons

Archive the Pason channel under `reported_differential_psi`. The header says differential pressure, and does not establish that the value is the total motor loss. Motorless runs have this channel, and some candidate means are negative. For the requested diagnostic, report raw measured standpipe pressure, reported differential pressure and their difference, with the basis explicit. Report the friction/nozzle model alongside both pressure descriptions; residuals can include unmodelled MWD and motor losses. Do not label the residual as a friction error alone.

For face heat, the proposed treatment follows the existing evaluator: use a non-negative differential-pressure load for documented motor assemblies; use zero motor-face heat where the report explicitly states no motor. Keep the unclamped source differential in the outputs. This distinction requires S0 review because the signal is not a verified motor-only measurement.

Report measured hydraulic power as measured standpipe pressure times measured volumetric flow. Keep modelled distributed friction power, nozzle power and motor-face power separately identified, avoiding double counting. Compare paired outlet-minus-inlet temperatures in both wells. Do not interpret a temperature-rise difference as a friction-power discrepancy without the heat exchanged with the rock and pipe. Preserve the frozen 16A primary sample centres for its Q3 comparisons.

## Matched depths and reporting

For Q4, use predeclared 500-ft measured-depth bins over the shared drilled interval. Also report each well's true vertical depth and the adopted formation temperature; equal measured depth does not imply equal formation temperature. List flow and measured inlet beside geometry, mud properties, nozzle areas and motor-pressure treatment. Include the sensor position and its evidence basis, cooler annotations, reported penetration and the time since the last observed trip. Report unmatched bins and sample counts, without selecting a narrower set based on temperature errors.

Report errors in °C and °F per run and depth bin. Give pooled results only beside those breakdowns. Distinguish regular-pipe observations independent of prior fitting from the trial fit and held-out groups. Keep every solver failure. Any later method change must preserve the present sample list and protocol as the earlier version, with its reason stated.
