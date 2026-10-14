# BoreTHM: cooling and borehole stability in superhot geothermal drilling

## The question and approach

Can a drilling programme keep equipment cool while maintaining borehole stability in superhot geothermal rock? BoreTHM examines that interaction by coupling fluid circulation and heat transfer with pressure and stability calculations through drilling, connections and trips.

Cold fluid travels down an insulated drill string and returns through the annulus. Insulation helps protect the tools, while fluid pressure supports the borehole wall. The fluid needed for stability also changes frictional losses and cooling. A programme must satisfy those requirements throughout the exposed hole and operating cycle.

The reference design uses TK-Drakon coated pipe, a 4,000 m intermediate casing shoe at the deep sites, and barite-weighted water-based fluids where required. Soultz and United Downs are evaluated at 40 and 50 L/s, respectively, with rock-temperature targets near 400 °C. Separate drilling and trip fluids are calculated; the heavier trip fluid is assumed to occupy the whole column from trip start.

## What the evaluated programmes show

Both deep-site programmes are **NO-GO for this programme and these assumptions**. No drilling or trip-fluid density satisfies all the evaluated pressure limits, and tool temperatures exceed the assumed 200 °C limit in at least one state.

| Site and target | Open target drilling intervals | Pressure check throughout the hole | Tool peaks: drilling / best attempted run-in |
|---|---|---|---|
| Soultz, 10.70 km | 8 of 9 cases | No allowable drilling or trip-fluid density | 197.0 / 201.2 °C |
| United Downs, 12.86 km | 2 of 4 cases | No allowable drilling or trip-fluid density | 205.7 / 224.5 °C |

The counts describe selected stress/strength scenarios at the target, using each site's saved reference thermal/hydraulic solution. They are not probabilities of successful drilling or coupled redesigns for each case. An open target drilling interval does not establish a fluid that works throughout the hole; the stability-cycle verdict also checks connections and the trip. The [complete case table](../../README.md#local-stability-and-the-complete-programme) retains those distinctions and the pressure units.

Best attempted means the lowest peak in the retained run-in schedule search. Soultz's reference FORGE-practice tool run-in reaches 214.5 °C, separately from its best attempted 201.2 °C. Reference-practice coating run-in maxima are 274.3 °C at Soultz and 287.4 °C at United Downs, against the stated 204 °C rating. Both retain **INDETERMINATE qualification**; the temperature exceedance does not establish a particular coating failure mode. Those coating histories need not belong to the best attempted tool schedule.

The other evaluated sites give Pannonian NO-GO, Larderello CONDITIONAL with prescribed fluids, and Newberry GO with water, for this programme and these assumptions.

## What the design comparisons establish

No evaluated single-lever setting or evaluated pair made either deep-site programme pass. Some changes clear individual checks: deeper casing admits a trip fluid at Soultz, and lower viscosity can admit a drilling fluid at United Downs. Other pressure or equipment failures remain. Stronger insulation cools the tools but leaves pressure and pump constraints.

Only one pair per site and selected continuous settings were evaluated. These results screen defined programmes; they establish neither a complete operating envelope nor a general limit on drilling with existing technology. Full settings and qualification evidence are in the [design study](../science/design-comparisons.md).

<!-- PAGEBREAK -->

## What supports the calculation

The circulation model is checked against temperatures measured during the insulated-pipe trial in Utah FORGE well 16B. Parameters were fitted using regular-pipe runs and the fully insulated run; the partial-insulation run was predicted without further fitting. A comparison with a published drill-pipe insulation model supplies a separate benchmark, with coated-pipe interpretation still unresolved.

Rock reheating is checked against analytic conduction solutions. The FORGE return-temperature comparison after trips is too coarse to confirm or reject that model. Rock strength is calibrated against UD-1 breakouts; the Soultz and Newberry well checks test its application elsewhere. Newberry's observed pattern is not reproduced in every rock type. These checks have distinct scopes and do not validate a complete 10-13 km drilling programme.

Automated tests and saved numerical outputs support reproduction of the calculations. The [validation guide](../science/validation.md) explains the observations, fitting and limitations; the [source records](../science/sources.md) identify the publications and input data.

## What remains uncertain

**Stress and strength at depth.** The deep targets lie below the measurements used to construct their stress profiles. Strength calibration depends on those assumed stresses. The selected scenarios expose sensitivity to the inputs without assigning a probability to them.

**Fluid behaviour through the cycle.** The reference mud uses approximate rheology and constant barite heat-capacity and expansion properties. Better high-temperature, high-pressure measurements could constrain its density and pressure losses. Coolant delivery and the timing of fluid displacement also remain approximations.

**Breakout growth and cooling.** The base model checks wall failure immediately on exposure and judges breakout width using the temperature at the estimated depth of an uncooled breakout, its skin heuristic. These assumptions prevent cooling from reducing the initial drilling demand. Breakouts observed within minutes in sediment do not establish their growth law in hot crystalline rock. The failure-delay experiments test hypotheses that no data yet support. They give no evidence that the wall can be cooled for an hour without failing. Near-bit pre-cooling remains a separate open question.

**Equipment qualification.** A circulating-temperature or mechanical pressure rating does not establish qualification through repeated connections and hot trips. Availability of a pipe or operating practice alone does not qualify the complete programme.

The base deep-site verdicts persist across the [A1-A9 comparisons performed](../science/approximation-comparisons.md). These generally change one approximation at a time and do not span every joint uncertainty. The [limitations guide](../science/limitations.md) records the unresolved assumptions in detail.

## Questions for specialist discussion

1. What governs breakout width in the first minutes after hot crystalline rock is exposed? Early and repeated image logs could test the exposure rule and skin heuristic.
2. Which fluids maintain the required density and rheology through circulation and hot trips? Measurements under the relevant temperature and pressure conditions would constrain the fluid assumptions.
3. How are insulated pipe and managed-pressure equipment qualified for the complete hot cycle? Public qualification procedures or test records would clarify the scope of their ratings.

Model development is paused for specialist feedback on these assumptions and their practical applicability. A relevant measurement, qualification record or clearly discriminating hypothesis can guide the next focused study.

[Repository and setup](https://github.com/ldocallaghan/BoreTHM) · [Documentation guide](../README.md) · [Saved reference evidence](../../results/v1.3.4/ci/38186784798-1/reference/)
