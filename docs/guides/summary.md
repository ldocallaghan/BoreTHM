# BoreTHM: cooling and borehole stability in superhot geothermal drilling

*Prepared 17 November 2026. Calculation basis: v1.9.0.*

## The question and approach

Can a drilling programme keep equipment cool while maintaining borehole stability in superhot rock? BoreTHM couples fluid circulation and heat transfer with pressure and stability calculations through the drilling cycle. It checks connections, when circulation stops to add pipe, and trips, when pipe is withdrawn or run into the hole.

Cold fluid travels down an insulated drill string and returns through the annulus, the space around the string. Insulation limits heating of the downgoing fluid. The fluid pressure needed to support the wall also affects frictional losses and cooling. A programme must meet the pressure and equipment limits throughout the exposed hole and operating cycle.

The reference programmes use TK-Drakon coated pipe and target rock near 400 °C. Separate drilling and trip fluids are calculated, using water-based mud weighted with barite, a dense mineral, where required. The heavier trip fluid is assumed to occupy the whole column from trip start.

## Results for the five built-in sites

Each site was evaluated with the v1.9.0 defaults on 17 November 2026, and the [results archive](../../results/v1.9.0/sites/README.md) keeps the full results. A fluid window is the range of surface densities that meets the pressure limits at every evaluated depth, state and case. It is closed when its lower limit is above its upper limit. The status follows the [assessment rules](interpreting-results.md): NO-GO when a decisive pressure, tool or pump-pressure check fails, CONDITIONAL when additional fluid, operating or equipment conditions apply, and GO when the assessed checks pass with none of those conditions.

| Site and target | Status and controlling constraint | Tool peaks, °C: drilling / best attempted run-in | Fluid windows, SG at 20 °C |
|---|---|---|---|
| Soultz, 10.7 km | **NO-GO**: no drilling or trip fluid meets every pressure limit | 194.0 / 198.2 | Drilling closed (lower 1.38, upper 1.24); trip closed (1.44, 1.37) |
| United Downs, 12.9 km | **NO-GO**: no drilling or trip fluid meets every pressure limit, and the bit reaches 226.4 °C while drilling | 226.4 / 242.5 | Drilling closed (1.35, 1.26); trip closed (1.41, 1.38) |
| Larderello, 2.40 km | **CONDITIONAL**: a prescribed drilling fluid of 1.03 SG and trip fluid of 1.09 SG | 46.2 / 49.2 | Drilling 1.03 to 1.26; trip 1.09 to 1.32 |
| Pannonian, 9.71 km | **NO-GO**: no single drilling or trip fluid meets the limits in every state | 193.6 / 198.1 | Drilling closed (1.47, 1.25); trip closed (1.55, 1.35) |
| Newberry, 3.63 km | **GO** with water | 92.3 / 97.3 | Drilling 1.00 to 1.22; trip 1.00 to 1.24 |

<!-- PAGEBREAK -->

The tool limit is 200 °C. At Soultz and Pannonian the tool passes only with the staged circulation schedule found for running in. At Soultz the drilling fluid's lower limit is set by a connection at the target, and its upper limit by drilling at the 4,000 m casing shoe. Target stability passes in 2 of 9 drilling cases at Soultz and 1 of 4 at United Downs, and no fluid works through the whole hole.

The TK-Drakon coating reaches 231.0, 298.1 and 229.6 °C while running in at Soultz, United Downs and Pannonian, against its stated 204 °C rating, so its qualification is unresolved.

## Earlier studies

Three earlier studies examined the deep-site programmes with earlier calculations. The [design comparisons](../science/design-comparisons.md) tested changes to the design, the [breakout-timing study](../science/breakout-timing.md) assumed delays before breakouts form, and the [approximation comparisons](../science/approximation-comparisons.md) changed one approximation at a time. Under their calculations, none made a deep-site programme pass. The current defaults change their numbers, and they have not been repeated.

## Evidence

Circulation temperatures have been compared with Utah FORGE observations and a published simulator, and standpipe pressure with FORGE 56-32, a well that played no part in the model's development. The [validation guide](../science/validation.md#results-at-a-glance) gives each comparison's error and the calculation it used. The [limitations guide](../science/limitations.md) explains the remaining assumptions.

## Questions for specialist discussion

1. How soon do breakouts form and grow after hot crystalline rock is exposed? Early and repeated image logs could test the timing assumption.
2. Which fluids maintain the required properties through circulation and hot trips? Measurements at the relevant temperatures and pressures would constrain the fluid model.
3. What test records qualify insulated pipe and managed-pressure equipment for the complete hot cycle?

[Repository and setup](https://github.com/ldocallaghan/BoreTHM) · [Documentation guide](../README.md) · [Scientific sources](../science/sources.md)
