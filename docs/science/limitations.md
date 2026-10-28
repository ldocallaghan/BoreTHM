# Assumptions, limitations and open questions

BoreTHM screens a stated drilling programme using the supplied inputs. A failed assessment does not establish that no other well design or existing technology can drill the site. The [validation guide](validation.md) describes what each comparison and check establishes.

## Input evidence

The deep targets extend beyond the measured stress and temperature records. Stress extrapolation and the strength assumptions affect the pressure requirements. At United Downs, strength is calibrated using an assumed stress profile, so that comparison cannot independently verify both quantities. Larderello and Pannonian retain unsourced strength assumptions. The [site-input records](../../src/borethm/data/sites/stress_sources.md) identify the sources and uncertainties.

The circulation comparisons use FORGE observations at depths and temperatures below the deep targets. Newberry's well check reproduces the volcanic breakouts but also predicts failure in granodiorite where none was logged. These checks do not establish the accuracy of a complete deep drilling programme.

The unfitted [FORGE 16A comparison](validation.md#forge-16a-blind-circulation-comparison) underpredicts the deeper downhole temperatures and surface return. Its circulation exposure clock omits recovery during trips. An optimistic reset-clock diagnostic can span several downhole means but leaves every logged mean return above the warm result. Recovery is not established as the cause. The partial run-in checks also depend on approximate initial wall histories and do not independently validate complete-trip tool temperatures.

## Applicability and numerical guards

Input acceptance, property-table coverage and field evidence impose different limits:

| Item | Range or treatment |
|---|---|
| Accepted site inputs | `validate_site` applies the [scalar ranges below](#accepted-scalar-ranges) to catch unit slips and implausible inputs. It checks a finite geotherm sampled every 100 m, including the target; the sampled open hole must warm with depth, and the target temperature must agree within 5 °C. It samples stress profiles every 500 m from the target to the casing shoe, including the shoe, checking finite positive stresses, maximum horizontal stress at least equal to minimum horizontal stress, the ordering of any declared faulting regime, and pore pressure below the minimum horizontal stress. It also checks provenance labels and reports missing sources. These checks do not establish that every fluid state remains inside the property table. |
| Water-property table | `water_properties`, implemented by `water_table.props`, interpolates over 1 to 479 °C and 0.1 to 218.1 MPa absolute. Each grid has a spacing of 2 in its stated units. Inputs outside those limits are clipped to the nearest edge before interpolation. These are the cached grid's limits. |
| Other numerical guards | The water-only heat-capacity path, `model1_coupled._cp`, clips its inputs to 1 to 480 °C and 0.1 to 220 MPa absolute, then calls the heat-capacity interpolator directly. That interpolator extrapolates over the small intervals beyond the final grid nodes at 479 °C and 218.1 MPa. `model1_coupled.solve` marks a circulation solution unsuccessful if either sampled fluid profile reaches 480 °C. The friction-heating lookup in `model1_coupled._friction_gradient` uses a minimum property pressure of 5 MPa absolute and clips temperature to 1 to 480 °C. The separate `hydraulics` function uses the approximate hydrostatic property pressure directly. |
| Fluid model | Circulation represents one single-phase fluid. The weighted-fluid model treats barite as a dispersed solid in water. There is no two-phase liquid-vapour flow calculation or vapour-fraction balance. |
| Circulation property pressure | `model1_coupled.P_of_z` supplies the approximate absolute pressure `P_surface + 10 MPa/km × TVD`, with true vertical depth (TVD) measured from surface and a default surface pressure of 0.1 MPa absolute. This property pressure is separate from the wall-pressure budget. The [property-pressure comparison, A1](approximation-comparisons.md#what-each-comparison-changes), tests a different treatment at fixed programme inputs. |
| Field comparison range | The original FORGE 16B circulation trial spans about 2.31 to 2.99 km measured depth, or 2.12 to 2.41 km true vertical depth, with adopted formation temperatures of about 182 to 205 °C. The whole-well comparison expands accepted samples to about 1.26 to 3.30 km measured depth and 1.26 to 2.54 km true vertical depth, with adopted formation temperatures of about 121 to 218 °C from neighbouring well 16A. These conditions are below the deep reference targets; the [validation guide](validation.md#circulation) describes the errors and fitted-input dependencies. |
| Site conditions | Deep stress and temperature profiles extend beyond the measured intervals. Strength assumptions and the transfer of calibrated parameters remain site-specific uncertainties, as described in [input evidence](#input-evidence). |

### Accepted scalar ranges

The inclusive limits below are those in `site_evaluation.INPUT_RANGES`. Unconfined compressive strength (UCS) is supplied at 25 °C. Invalid values raise `ValueError`; missing provenance produces warnings.

| Input | Accepted range | Unit |
|---|---|---|
| Effective target depth | 500 to 20,000 | m |
| Target rock temperature | 50 to 600 | °C |
| Rock conductivity | 0.5 to 7 | W/(m K) |
| Rock Young's modulus | 5 to 150 | GPa |
| UCS and every strength-case UCS | 10 to 500 | MPa |
| Injection temperature | 0 to 100 | °C |
| Friction coefficient | 0.2 to 1.5 | dimensionless |
| Reference fluid-pressure gradient | 8,000 to 20,000 | Pa/m |
| Reference vertical-stress gradient | 15,000 to 35,000 | Pa/m |

These scalar limits are distinct from the temperature and pressure domain of the property table.

## Breakout formation and cooling

The circulation rock term uses a minimum exposure of one hour for a depth-dependent history, or 0.001 years (about 8.8 hours) for a uniform `t_years`. The cylindrical rock response does not need these floors; they are kept so that results remain comparable with earlier releases. The separate radial wall-temperature calculation resolves early cooling with its supplied state durations, using fluid-temperature and film-coefficient boundaries from circulation. It does not apply the circulation exposure floors. Those floors set no breakout formation delay. The [circulation equations](models.md#circulation-heat-balance) describe their scope.

The base case assumes breakouts form as soon as the bit exposes the rock. A skin-depth heuristic approximates where failure begins behind the wall; immediate formation prevents cooling from reducing the initial drilling pressure requirement. The [physical-model guide](models.md#borehole-stability) explains that approximation.

The [breakout-timing study](breakout-timing.md) tests assumed delays between exposure and failure. Its results show when the whole-hole drilling-fluid window opens under those assumptions. They do not measure breakout formation time. Images showing breakouts within minutes in sediment do not establish timing or growth in hot crystalline rock. Near-bit pre-cooling and the growth of breakouts remain open questions.

## Fluid properties and equipment qualification

The fluid model represents one reference mud. Its yield point is fixed and its plastic viscosity is scaled from water. Barite heat capacity and thermal expansion are treated as constants. The [design study's barite source check](design-comparisons.md#barite-source-check) gives the supporting values and their limits.

A published potassium-formate fluid retained a plastic viscosity of 30 mPa s after ageing at 200 °C, measured after cooling to 49 °C. That result does not qualify the modelled mud during a 400 °C trip. The [fluid and equipment sources](design-comparisons.md#sources-and-qualification-limits) describe the conditions behind the comparisons.

The manufacturer's 204 °C coating rating does not establish survival through a hotter drilling cycle. The cited managed-pressure drilling equipment has a stated mechanical pressure rating; qualification for the modelled thermal cycle remains unknown.

## Circulation hydraulics and heat input

The calculation now includes connection, assembly-component, local and surface losses, and supplied tool curves, each from a cited source or a declared catalogue scenario. Its accuracy rests on inputs that are rarely measured: connection bores and restriction lengths, surface plumbing, and tool and motor loss curves with their reference flow. On the unseen well 56-32, the NC50 connection scenario alone contributes 620–730 psi of a predicted standpipe pressure near 3,300 psi, and the motor's unstated reference flow leaves a range of about 2,000 psi ([56-32 comparison](validation.md#forge-56-32-standpipe-pressure-on-an-unseen-well)). On 16A, where every motor's loss is unknown and set to zero, the calculated pressure remains 560–1,880 psi low. A pump-limit check is only as good as these inputs: with an unknown tool or motor loss left at zero it still underpredicts the pump pressure needed, which is non-conservative near the pump limit. The modelled annulus friction used in bottom-hole circulating pressure is affected much less by these inputs.

The thermal and hydraulic routines also use different treatments of yield point. Heat-transfer Reynolds numbers use plastic viscosity; Bingham hydraulic regimes use apparent viscosity including yield point. In the saved FORGE samples, every annulus cell uses the turbulent heat-transfer branch, although the hydraulic calculation classifies substantial lengths as laminar. Distributed friction heating retains its plastic-viscosity friction factor and minimum property pressure of 5 MPa. The [regime and film diagnostics](validation.md#annulus-regime-and-film-coefficient) report these distinctions without changing the functions.

The modelled friction, nozzle and motor-face heat totals are below measured standpipe pressure times inlet flow in both wells. That power comparison does not establish a missing downhole heating rate: surface losses, mechanical work and the location of dissipation affect how energy enters the circulating fluid. A small numerical temperature-balance residual checks the implemented equations, not the completeness of the physical energy budget. The [energy comparison](validation.md#pressure-and-heat-input-accounting) therefore does not validate the pump-pressure check or identify a cause of the temperature errors. A positive temperature margin alone does not establish a conservative hydraulic or thermal prediction.

## Tool temperature and programme timing

At FORGE 16A, the run-in tool calculation underpredicted measured peaks by about 20–50 °C on partial legs with approximate initial states. The run-in tool check can therefore be non-conservative: it can predict a lower peak than the tool experiences. The [validation section](validation.md#forge-16a-conditional-transient-checks) gives the comparison and its initial-state limitations.

The tool is represented by a lumped thermal model of the collar and enclosed fluid. During a staging pause, coolant is supplied at its steady temperature without accounting for its travel time through the string. Staging duration is absent from the base trip clock. During run-in, the trip-fluid temperature column is frozen and a uniform heavier fluid is assumed present from the start.

These approximations matter when interpreting a small tool-temperature margin or a narrow allowable density range. The [approximation comparisons](approximation-comparisons.md) test selected alternatives. Their results do not replace a calculation with a common timeline and explicit fluid displacement.

## Other design limits and study scope

The assessments do not include detailed casing and cement integrity, string loads and fatigue, circulation losses, or creep coupled to the drilling cycle. The hole-cleaning reference and cycle timings come from one well. Rig capacity is checked against three pumps of one published rating. The 0.02 SG allowance for pressure changes during pipe movement is a sensitivity assumption, with no verified field range for these 10 to 13 km wells.

The [approximation study](approximation-comparisons.md) generally changes one assumption at a time and does not cover every joint uncertainty. The [design study](design-comparisons.md) samples selected settings and one pair per site. Neither study makes either deep-site programme pass or establishes a complete operating envelope.

The conditions for further implementation work are recorded in the [maintenance priorities](../maintenance/development.md). The [study summary](../guides/summary.md#questions-for-specialist-discussion) lists questions for specialist discussion.
