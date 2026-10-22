# Assumptions, limitations and open questions

BoreTHM screens a stated drilling programme using the supplied inputs. A failed assessment does not establish that no other well design or existing technology can drill the site. The [validation guide](validation.md) describes what each comparison and check establishes.

## Input evidence

The deep targets extend beyond the measured stress and temperature records. Stress extrapolation and the strength assumptions affect the pressure requirements. At United Downs, strength is calibrated using an assumed stress profile, so that comparison cannot independently verify both quantities. Larderello and Pannonian retain unsourced strength assumptions. The [site-input records](../../src/borethm/data/sites/stress_sources.md) identify the sources and uncertainties.

The circulation comparisons use FORGE observations at depths and temperatures below the deep targets. Newberry's well check reproduces the volcanic breakouts but also predicts failure in granodiorite where none was logged. These checks do not establish the accuracy of a complete deep drilling programme.

## Breakout formation and cooling

The base case assumes breakouts form as soon as the bit exposes the rock. A skin-depth heuristic approximates where failure begins behind the wall; immediate formation prevents cooling from reducing the initial drilling pressure requirement. The [physical-model guide](models.md#borehole-stability) explains that approximation.

The [breakout-timing study](breakout-timing.md) tests assumed delays between exposure and failure. Its results show when the whole-hole drilling-fluid window opens under those assumptions. They do not measure breakout formation time. Images showing breakouts within minutes in sediment do not establish timing or growth in hot crystalline rock. Near-bit pre-cooling and the growth of breakouts remain open questions.

## Fluid properties and equipment qualification

The fluid model represents one reference mud. Its yield point is fixed and its plastic viscosity is scaled from water. Barite heat capacity and thermal expansion are treated as constants. The [design study's barite source check](design-comparisons.md#barite-source-check) gives the supporting values and their limits.

A published potassium-formate fluid retained a plastic viscosity of 30 mPa s after ageing at 200 °C, measured after cooling to 49 °C. That result does not qualify the modelled mud during a 400 °C trip. The [fluid and equipment sources](design-comparisons.md#sources-and-qualification-limits) describe the conditions behind the comparisons.

The manufacturer's 204 °C coating rating does not establish survival through a hotter drilling cycle. The cited managed-pressure drilling equipment has a stated mechanical pressure rating; qualification for the modelled thermal cycle remains unknown.

## Tool temperature and programme timing

The tool is represented by a lumped thermal model of the collar and enclosed fluid. During a staging pause, coolant is supplied at its steady temperature without accounting for its travel time through the string. Staging duration is absent from the base trip clock. During run-in, the trip-fluid temperature column is frozen and a uniform heavier fluid is assumed present from the start.

These approximations matter when interpreting a small tool-temperature margin or a narrow allowable density range. The [approximation comparisons](approximation-comparisons.md) test selected alternatives. Their results do not replace a calculation with a common timeline and explicit fluid displacement.

## Other design limits and study scope

The assessments do not include detailed casing and cement integrity, string loads and fatigue, circulation losses, or creep coupled to the drilling cycle. The hole-cleaning reference and cycle timings come from one well. Rig capacity is checked against three pumps of one published rating. The 0.02 SG allowance for pressure changes during pipe movement is a sensitivity assumption, with no verified field range for these 10 to 13 km wells.

The [approximation study](approximation-comparisons.md) generally changes one assumption at a time and does not cover every joint uncertainty. The [design study](design-comparisons.md) samples selected settings and one pair per site. Neither study makes either deep-site programme pass or establishes a complete operating envelope.

The conditions for further implementation work are recorded in the [maintenance priorities](../maintenance/development.md). The [study summary](../guides/summary.md#questions-for-specialist-discussion) lists questions for specialist discussion.
