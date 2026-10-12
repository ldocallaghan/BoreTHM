# BoreTHM v1.3.5: a summary for readers

*Draft for Liam O'Callaghan's final editorial pass. All numerical evidence is retained from v1.3.4.*

At Soultz, eight of nine stress/strength cases have an open target-depth drilling-fluid interval in the saved reference calculation; at United Downs, two of four do. These are local stability checks, not successful drilling programmes. The stated programme remains **NO-GO for this programme and these assumptions** at both sites because its whole-hole pressure windows close and tool-temperature limits are exceeded. Stress, strength, fluid properties and full-cycle equipment qualification remain key uncertainties.

## Target-depth stability diagnostic

Need and limit are static-column SG-equivalent values at the target with the existing friction/backpressure treatment, not surface mud-density prescriptions. The saved target stability-cycle verdict includes connections and the trip, excluding separate whole-hole, tool and equipment gates. Each site's reference solution is reused across cases without fresh coupled reruns. A positive interval proves neither a workable whole-hole fluid nor that the attempted fluid lies inside it.

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

Soultz target 10.70 km; United Downs target 12.86 km. Sv is vertical stress. United Downs retains the existing 0 K / 40 K strength-calibration cases; these labels do not specify a newly applied cooling intervention. The 13 cases are selected scenarios, not samples from a probability distribution. Eight of nine and two of four describe open target drilling intervals, not probabilities of successful drilling. All verdicts refer to this programme and these assumptions.

## Common-programme result

These common-programme windows intersect the evaluated depths, states and stress/strength cases. Surface SG at 20 °C is density divided by 1,000 kg/m³. Width is upper minus lower; negative means closed. Both sites remain **NO-GO for this programme and these assumptions**.

| Site and state | Lower / upper, surface SG | Width, SG |
|---|---|---:|
| Soultz drilling | 1.37892 / 1.31256 | -0.06637 |
| Soultz trip | 1.44362 / 1.36461 | -0.07901 |
| United Downs drilling | 1.33132 / 1.28519 | -0.04613 |
| United Downs trip | 1.40134 / 1.36503 | -0.03631 |

<!-- PAGEBREAK -->

## Tool survival and coating qualification

**Tools, drilling / connection / best attempted run-in:** Soultz: 197.0 / 197.3 / 201.2 °C; United Downs: 205.7 / 206.1 / 224.5 °C. The tool limit is 200 °C. Best attempted means the lowest peak in the saved schedule search, not an optimum over all possible schedules. Soultz's reference FORGE-practice run-in reaches 214.5 °C; it is separate from the 201.2 °C search result.

Reference-practice coating run-in maxima are 274.3 °C at Soultz and 287.4 °C at United Downs, against the stated 204 °C rating. Both retain **INDETERMINATE qualification**. Exceeding the stated rating is not a validated prediction of a particular failure mode. These coating histories are not necessarily those of the best attempted tool schedule.

Sources: retained [Soultz reference](../../results/v1.3.4/ci/38186784798-1/reference/soultz.json) and [United Downs reference](../../results/v1.3.4/ci/38186784798-1/reference/united-downs.json); settings-matched L4 base trials for [Soultz](../../results/v1.3.4/ci/38186784798-1/levers/soultz/L4/summary.json) and [United Downs](../../results/v1.3.4/ci/38186784798-1/levers/united-downs/L4/summary.json). See [release provenance](../releases/v1.3.4.md).

## Scope of the result and design study

The reference programme uses TK-Drakon coated pipe, a 4,000 m intermediate shoe and 40/50 L/s at Soultz/United Downs. The five-site headline remains NO-GO at Soultz, United Downs and Pannonian, CONDITIONAL at Larderello, and GO at Newberry, for this programme and these assumptions. One defined programme has been screened; drilling these sites with existing technology remains an open question.

Soultz's 0.017 SG-equivalent target drilling deficit and 1.2 °C tool excess are local facts. Whole-hole deficits and coating qualification are independent barriers. No evaluated single-lever setting or evaluated pair reopened either deep site. Only one pair per site was evaluated, and continuous searches sampled settings. The [lever study](../science/design-comparisons.md) establishes no complete operating envelope or general impossibility.

The base deep-site verdicts remain NO-GO for this programme and these assumptions across the [A1-A9 comparisons performed](../science/approximation-comparisons.md). These generally change one approximation at a time and do not cover every joint uncertainty. Circulation is checked against Utah FORGE measurements; strength calibration and other well checks are separate. Those checks do not validate a complete 10-13 km drilling programme.

## The open cooling question and development pause

Immediate exposure and the skin heuristic prevent cooling from reducing the initial drilling demand in the base model. Images within minutes in sediment do not establish timing or growth in hot crystalline rock. Failure-delay experiments are unsupported hypotheses, not evidence that breakouts wait an hour. Near-bit pre-cooling and breakout growth remain separate unresolved questions.

**H-01 trigger met; implementation deferred by project priority.** Soultz L2's 0.00137 SG trip width and the L2+L4 pair's 0.00949 SG drilling deficit meet the trigger, but other gates still fail. Revisit the timeline before claiming a near-threshold programme is feasible, or when feedback or new data makes timing decision-relevant. Coolant delivery and fluid displacement retain distinct [development triggers](../science/limitations.md#development-pause). Pannonian's historical 0.041 °C tool threshold remains numerically unresolved.

Model expansion is paused for specialist feedback; demonstrated defects can still be corrected. Reader interest, usable observations or a discriminating hypothesis can justify a separate near-bit or FORGE image-log study. Neither is initiated here.

## Questions for specialist discussion

1. What governs breakout width in the first minutes after hot crystalline rock is exposed? Paired early and later images could test immediate exposure and the skin heuristic.
2. Which fluids maintain the required density and rheology through circulation and hot trips? Measured properties would test the reference mud and viscosity bounds.
3. How are insulated pipe and managed-pressure equipment qualified for the complete hot cycle? Steady temperature or pressure ratings alone do not establish that qualification.

The [release record](../releases/v1.3.5.md) distinguishes this reader patch from its retained calculation and evidence. Interfaces and examples enable external use; readers and users will establish practical usefulness.
