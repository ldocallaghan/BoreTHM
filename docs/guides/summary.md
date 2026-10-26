# BoreTHM: cooling and borehole stability in superhot geothermal drilling

*Prepared 22 October 2026. Calculation basis: v1.4.0.*

## The question and approach

Can a drilling programme keep equipment cool while maintaining borehole stability in superhot rock? BoreTHM couples fluid circulation and heat transfer with pressure and stability calculations through the drilling cycle. It checks connections, when circulation stops to add pipe, and trips, when pipe is withdrawn or run into the hole.

Cold fluid travels down an insulated drill string and returns through the annulus, the space around the string. Insulation limits heating of the downgoing fluid. The fluid pressure needed to support the wall also affects frictional losses and cooling. A programme must meet the pressure and equipment limits throughout the exposed hole and operating cycle.

The reference programmes use TK-Drakon coated pipe and target rock near 400 °C. Soultz and United Downs use intermediate casing ending at 4,000 m and flows of 40 and 50 L/s, respectively. Separate drilling and trip fluids are calculated, using water-based mud weighted with barite, a dense mineral, where required. The heavier trip fluid is assumed to occupy the whole column from trip start.

## Reference results with immediate breakout formation

Breakouts are local failures of rock at the borehole wall. The base case assumes they form as soon as rock is exposed. Both deep-site programmes are **NO-GO**: no drilling or trip-fluid density satisfies all pressure limits throughout the hole, and tool temperatures exceed the assumed 200 °C limit.

| Site and target | Open target drilling intervals | Whole-hole pressure check | Tool peaks: drilling / best attempted run-in |
|---|---|---|---|
| Soultz, 10.70 km | 8 of 9 cases | No allowable drilling or trip-fluid density | 197.0 / 201.2 °C |
| United Downs, 12.86 km | 2 of 4 cases | No allowable drilling or trip-fluid density | 205.7 / 224.5 °C |

The counts describe selected stress and strength cases using each site's reference thermal and hydraulic solution. They are not probabilities of success. An open target interval does not establish a fluid that works throughout the hole. Run-in peaks are the lowest among the schedules searched. Coating qualification remains **INDETERMINATE** because the evaluated cycle exceeds the stated rating; this does not predict a particular failure mode. The [reference comparison](../science/design-comparisons.md#reference-programmes) gives the cases and equipment histories.

## How breakout timing changes the drilling window

With an assumed one-hour formation delay, the whole-hole drilling-fluid window opens at both sites. The saved scan brackets the opening at **15–20 minutes at Soultz** and **10–15 minutes at United Downs**. These brackets come from calculations with assumed delays. They do not measure formation time. Both full programmes remain NO-GO because trip-fluid windows remain closed and tool temperatures exceed the limit. The [timing study](../science/breakout-timing.md) gives the paired results and scan.

<!-- PAGEBREAK -->

## Other sites and design comparisons

The other reference programmes give Pannonian NO-GO, Larderello CONDITIONAL with prescribed fluids, and Newberry GO with water. These verdicts apply to the stated designs and inputs; their [source records](../../src/borethm/data/sites/stress_sources.md) describe differences in evidence quality.

No evaluated individual design change or pair made Soultz or United Downs pass. Deeper casing permits a trip fluid at Soultz, and lower viscosity can permit a drilling fluid at United Downs, while other checks still fail. Only one pair per site and selected continuous settings were evaluated. The [design study](../science/design-comparisons.md) establishes no complete operating envelope or general limit on drilling with existing technology.

## Evidence and its limits

Circulation temperatures have been compared with Utah FORGE measurements. In well 16B, parameters were fitted using regular-pipe runs and the fully insulated run; the partial-insulation run was predicted without further fitting. A published-model comparison supplies another benchmark, with the coated-pipe interpretation unresolved.

The [unfitted FORGE 16A comparison](../science/validation.md#forge-16a-blind-circulation-comparison) underpredicted the deeper downhole temperatures and the surface return. Run-in peaks there were underpredicted by about 20–50 °C on partial legs with approximate initial states, so the [run-in tool check can be non-conservative](../science/limitations.md#tool-temperature-and-programme-timing).

Rock reheating is checked against analytical conduction solutions. The FORGE return-temperature comparison after trips is too coarse to confirm or reject the reheating model. Rock strength is calibrated against United Downs breakouts, with separate checks at Soultz and Newberry. Newberry's observed pattern is not reproduced in every rock type. These checks do not validate a complete 10–13 km drilling programme. The [validation guide](../science/validation.md) explains the fitting and comparisons.

## What remains uncertain

The deep targets lie beyond measured stresses, and strength calibration depends on the assumed stress profile. The reference mud uses approximate flow properties, with constant barite heat capacity and thermal expansion. Coolant travel time and fluid displacement during trips remain approximations.

The studies reviewed here provide no measurement of breakout formation time in hot crystalline rock. Observations in sediment do not establish that timing or a growth law in granite. Near-bit pre-cooling remains a separate question. Equipment ratings also require qualification for repeated connections and hot trips.

The [approximation comparisons](../science/approximation-comparisons.md) generally change one assumption at a time and do not cover every joint uncertainty. The [limitations guide](../science/limitations.md) explains the remaining assumptions.

## Questions for specialist discussion

1. How soon do breakouts form and grow after hot crystalline rock is exposed? Early and repeated image logs could test the timing assumption.
2. Which fluids maintain the required properties through circulation and hot trips? Measurements at the relevant temperatures and pressures would constrain the fluid model.
3. What test records qualify insulated pipe and managed-pressure equipment for the complete hot cycle?

[Repository and setup](https://github.com/ldocallaghan/BoreTHM) · [Documentation guide](../README.md) · [Scientific sources](../science/sources.md)
