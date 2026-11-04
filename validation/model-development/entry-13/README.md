# Tapered drill-pipe joint transitions

4 November 2026. This entry replaces the abrupt bore change at ordinary drill-pipe joints on FORGE 16A and 16B with conical transitions at an angle derived from a published internal-upset taper, with a declared sensitivity range. It compares with the working calculation, entry 8 with entry 10's smooth Colebrook friction, and with entry 12's `installed_primary` and `installed_no_local`. The package defaults remain unchanged. FORGE 58-32 supplies no data to this entry.

## Prior exposure

**Measured prior exposure.** The tapered treatment was examined after the following results had been seen: the entry 12 scores, its measured/modelled slope ratios of 0.49–0.61 under the abrupt treatment and 1.54–2.30 without joint local losses, the joint-local-loss bound of 29.7–44.8% of the abrupt value, and an informal mapping of that bound to an included angle of roughly 13–20°, made during the review of entry 12. The decision to study a taper therefore followed the slope comparison. The primary angle is the value computed from the published taper, and no angle, length or coefficient in this entry was chosen from agreement with G1, G2 or the trip slopes.

**Calculated check of the exposed mapping.** With the coefficients below and the 16B dimensions, a bore local-loss fraction of 29.7–44.8% corresponds to included angles of 17.0–25.8°. This differs from the informal mapping. Neither range supplies a model input.

## Sources and values

**Measured source records.** [references.json](references.json) gives each source, locator and limit.

| Quantity | Value | Source |
| --- | --- | --- |
| Body ID, 5 in 19.5 lb/ft | 4.276 in | EP0756682B1, Table I, D1; the same pipe as 16A in the installed record |
| Upset bore | 3.500 in | EP0756682B1, Table I, D5, the mandrel diameter stated to match the upset end bore |
| Internal taper length Miu | 3.838 in (97.50 mm) | Tsukano et al. (1988), IADC/SPE 17206, Figure 9, as quoted in EP0756682B1 |
| Patent transition length L8 | 7.000 in (177.80 mm) | EP0756682B1, Table I |

**Measured source limit.** The Tsukano et al. paper could not be accessed, so it is cited as quoted, and its own upset bore is unknown. The 11.5° angle therefore combines the quoted Miu with the bore from a separate patent design. Both sources describe a curved transition, with radius 11.714 in at the body juncture in the paper and 63.33 in over L8 in the patent. A cone over the same length is a chord approximation. The paper and patent concern fatigue and forging, and neither states a hydraulic coefficient.

**Calculated angles.** The included angle over Miu is 2·atan(0.388/3.838) = 11.55°, and over L8 is 2·atan(0.388/7.0) = 6.35°. The variants use the declared rounded values, 11.5° and 6.3°. The difference in the primary coefficient from this rounding is 0.4%.

**Measured coefficients.** Crane Technical Paper 410 itself was not accessible. Its A-26 formulas were verified against AFT Arrow 10's *Area Change Loss Model* (Crane 1988) and against the `fluids` library source (Crane 2009), which labels them formulas 1 to 4. The two statements agree with each other, and neither differs from the form below. With `K` on the smaller-bore velocity and `β = d_small/d_large`:

| Change | θ ≤ 45° | 45° < θ ≤ 180° |
| --- | --- | --- |
| Enlargement | `2.6 sin(θ/2) (1 − β²)²` | `(1 − β²)²` |
| Contraction | `0.8 sin(θ/2) (1 − β²)` | `0.5 √(sin(θ/2)) (1 − β²)` |

**Measured source limit.** No accessible statement gives a numerical Reynolds range, so none is recorded. The sources differ on the equality case at exactly 45°: the library places it in the upper branch. No declared variant lies at 45°. Crane's errata of November 2013, page 1, correcting Eq. 2-16 on page 2-11, gives the sudden contraction `K = 0.5(1 − d₁²/d₂²)`, which equals the conical contraction at 180°.

**Measured abrupt treatment.** The existing treatment uses Idelchik (2006), third edition, diagrams 4-1 and 4-9, as documented by Modelica 4.0.0: `K_exp = (1 − r)²` and `K_con = 0.5 (1 − r)^0.75`, with `r = A_small/A_large`. At 180° Crane's enlargement is identical. Crane's contraction, `0.5(1 − r)`, is lower: 0.2932 against 0.3351 at the 16A area ratio and 0.2937 against 0.3355 at 16B. No blend is applied.

**Inferred source gaps.** No source was found for the transition from upset bore to tool-joint bore inside the weld neck, or for 5-1/2 in upset dimensions. A spec-sheet note that tool-joint ID means the pin bore where pin and box bores differ could not be verified at its source; it supports one sensitivity and supplies no number.

## Variants and fixed settings

**Calculated variants.** Everything not listed follows entry 12's `installed_primary`: installed body and tool-joint dimensions, restriction length 25 in on 16A and 22 in on 16B, and smooth Colebrook friction with zero roughness.

| Variant | Ordinary-pipe joints |
| --- | --- |
| `tapered_primary` | Tapered, 11.5°, from the published Miu |
| `tapered_long` | Tapered, 6.3°, from the patent's 7.0-in transition |
| `tapered_steep` | Tapered, 30°, a sensitivity bound without a source |
| `tapered_pin_length` | `tapered_primary` with the restriction length set to the pin tong length only: 11 in on 16A and 10 in on 16B |

**Inferred scope.** Each ordinary joint has one conical contraction from body bore to tool-joint bore and one conical expansion back. This extends the published angle beyond the published span: from 4.276 to 2.750 in on 16A, where the source covers 4.276 to 3.500 in. The 5-in angle is applied to 16B as a transferred value, because no 5-1/2 in upset dimensions were found. The local loss uses the existing heat assignment. The source describes the bore, so the annulus side of each ordinary joint keeps the abrupt treatment of `installed_primary`. The 16B insulated pipe with its EIS joints and all HWDP keep the abrupt treatment in every variant. The [geometry audit](predictions/geometry-audit.csv) records each joint on the selected windows.

**Calculated neglected friction.** The cone lengths are added to neither the body nor the restriction, and their wall friction is neglected. The body friction over the same length remains in the model, so the neglected quantity is the excess. It is small against the local loss, as the [representative figures](predictions/joint-fractions.csv) for one joint show, at each well's median-flow window and inlet state.

| Well | Angle, ° | Flow, US gpm | Each cone, in | Wall friction, two cones, psi | Body friction retained, psi | Neglected excess, psi | Tapered local loss, psi |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 16A | 6.3 | 620 | 13.86 | 0.628 | 0.197 | 0.431 | 0.609 |
| 16A | 11.5 | 620 | 7.58 | 0.343 | 0.108 | 0.235 | 1.110 |
| 16A | 30.0 | 620 | 2.85 | 0.129 | 0.040 | 0.088 | 2.866 |
| 16B | 6.3 | 647 | 15.17 | 0.256 | 0.079 | 0.177 | 0.435 |
| 16B | 11.5 | 647 | 8.29 | 0.140 | 0.043 | 0.097 | 0.793 |
| 16B | 30.0 | 647 | 3.12 | 0.052 | 0.016 | 0.036 | 2.048 |

## Model-only predictions

**Calculated joint fractions.** The bore local loss of one ordinary joint as a fraction of the abrupt value depends on the angle and almost not on the well, because the two area ratios nearly coincide.

| Well | Angle, ° | K contraction | K expansion | K total | Abrupt K total | Fraction of abrupt |
| --- | --- | --- | --- | --- | --- | --- |
| 16A | 6.3 | 0.0258 | 0.0491 | 0.0749 | 0.6789 | 0.1103 |
| 16A | 11.5 | 0.0470 | 0.0896 | 0.1366 | 0.6789 | 0.2012 |
| 16A | 30.0 | 0.1214 | 0.2314 | 0.3528 | 0.6789 | 0.5197 |
| 16B | 6.3 | 0.0258 | 0.0493 | 0.0751 | 0.6804 | 0.1104 |
| 16B | 11.5 | 0.0471 | 0.0899 | 0.1369 | 0.6804 | 0.2012 |
| 16B | 30.0 | 0.1216 | 0.2321 | 0.3537 | 0.6804 | 0.5199 |

**Calculated preparation.** The entry 10 selection is retained: one lower-median-depth operating window per assembly, restricted to Sanvean on-bottom samples for 16A, giving 22 windows, nine on 16A and 13 on 16B. [model-only.csv](predictions/model-only.csv) gives every window's G1 pressure and G2 hydraulic-power change for every variant, against `installed_primary` in the `_change` columns and against working in the `_vs_working` columns. No measured target enters these predictions. The 154 rows have no solver failures or energy flags. With the option unset, [the replay](predictions/entry12-replay-check.csv) matches entry 12's archived predictions for working, `installed_primary` and `installed_no_local`, the largest differences being 1.3e-08 psi, 5.4e-09 °C and 2e-09 kW.

**Calculated changes against `installed_primary`.** These ranges include the expected G3 bit, G5 return and G6 sensor-proxy changes. The temperature columns are rough estimates from full coupled solves on representative inputs, and the upper limit of zero on 16B belongs to the full-IDP trial, which has no ordinary pipe.

| Variant | Well | Pressure, psi | Hydraulic power, kW | Bit, °C | Sensor proxy, °C | Return, °C |
| --- | --- | --- | --- | --- | --- | --- |
| tapered_primary | 16A | -1213.3 to -483.8 | -350.7 to -118.3 | -6.98 to -2.06 | -6.98 to -2.06 | -1.59 to -0.70 |
| tapered_primary | 16B | -1126.5 to 0.0 | -559.3 to 0.0 | -8.13 to 0.00 | -8.13 to 0.00 | -1.75 to 0.00 |
| tapered_long | 16A | -1350.8 to -538.8 | -390.3 to -131.7 | -7.77 to -2.30 | -7.77 to -2.30 | -1.77 to -0.78 |
| tapered_long | 16B | -1254.6 to 0.0 | -622.8 to 0.0 | -9.05 to 0.00 | -9.05 to 0.00 | -1.95 to 0.00 |
| tapered_steep | 16A | -730.4 to -291.0 | -211.4 to -71.2 | -4.22 to -1.24 | -4.22 to -1.24 | -0.96 to -0.42 |
| tapered_steep | 16B | -677.4 to 0.0 | -336.4 to 0.0 | -4.91 to 0.00 | -4.91 to 0.00 | -1.05 to 0.00 |
| tapered_pin_length | 16A | -1407.1 to -564.4 | -406.5 to -138.0 | -8.05 to -2.40 | -8.05 to -2.40 | -1.85 to -0.81 |
| tapered_pin_length | 16B | -1240.8 to 0.0 | -616.0 to 0.0 | -8.70 to 0.00 | -8.70 to 0.00 | -1.93 to 0.00 |

**Calculated changes against the working calculation.**

| Variant | Well | Pressure, psi | Hydraulic power, kW | Bit, °C | Return, °C |
| --- | --- | --- | --- | --- | --- |
| tapered_primary | 16A | -27.3 to -3.7 | -7.8 to -0.9 | -0.17 to -0.02 | -0.04 to -0.01 |
| tapered_primary | 16B | 0.0 to 283.8 | 0.0 to 140.7 | 0.00 to 1.70 | 0.00 to 0.44 |
| tapered_long | 16A | -156.4 to -59.5 | -45.1 to -14.5 | -0.91 to -0.25 | -0.20 to -0.09 |
| tapered_long | 16B | 0.0 to 155.7 | 0.0 to 77.2 | 0.00 to 0.79 | 0.00 to 0.24 |
| tapered_steep | 16A | 188.2 to 463.9 | 46.0 to 133.9 | 0.80 to 2.64 | 0.27 to 0.61 |
| tapered_steep | 16B | 0.0 to 732.9 | 0.0 to 363.6 | 0.00 to 4.92 | 0.00 to 1.14 |
| tapered_pin_length | 16A | -212.7 to -85.2 | -61.3 to -20.8 | -1.19 to -0.35 | -0.28 to -0.12 |
| tapered_pin_length | 16B | 0.0 to 169.5 | 0.0 to 84.1 | 0.00 to 1.13 | 0.00 to 0.26 |

**Inferred expected scores.** All tapered variants reduce pressure, hydraulic power, bit and return temperatures against `installed_primary`. The primary sits close to working in pressure on 16A and between working and `installed_primary` on 16B. Interpolating entry 12's archived scores by each variant's modelled slope fraction, defined as `(S_candidate − S_no-local)/(S_abrupt − S_no-local)` on the five regular-pipe groups, gives the rough values below. This uses already exposed scores and is not part of the recommendation rule. The pin-length variant changes the restriction term as well, so it is excluded from this interpolation.

| Variant | Modelled slope fraction | G5 return bias, °C | G6 regular bias, °C | G6 trial bias, °C |
| --- | --- | --- | --- | --- |
| tapered_primary | 0.217–0.226 | -4.65 | +3.86 | +10.08 |
| tapered_long | 0.128–0.138 | -4.79 | +3.51 | +9.73 |
| tapered_steep | 0.530–0.535 | -4.19 | +5.09 | +11.29 |

**Calculated modelled slope fraction.** For `tapered_primary` this fraction is 0.217–0.226, slightly above the bore fraction of 0.201 because the retained abrupt annulus loss remains in the numerator. It lies below entry 12's 0.297–0.448 bound, so the primary is predicted to give a modelled rise smaller than measured on the regular-pipe groups.

**Calculated trip predictions.** [Trip slopes](predictions/trips/slopes.csv) use all 186 frozen input windows from the six entry 9 groups and the same clustering and regression. Each cell gives the modelled slope in psi per 1000 ft, followed in brackets by the predicted multiplier of the archived working ratio, `R_candidate = R_working × working model slope / candidate model slope`. No new measured slope or ratio is calculated before scoring. EOW 19 adds insulated pipe with EIS joints, so its response differs from the groups that add ordinary pipe.

| EOW / added pipe | Excursion | Flow, US gpm | tapered_primary | tapered_long | tapered_steep | tapered_pin_length |
| --- | --- | --- | --- | --- | --- | --- |
| 17 / ordinary | 27 | 500 | 74.76 (0.7781) | 66.46 (0.8753) | 103.88 (0.5600) | 68.67 (0.8472) |
| 19 / insulated | 29 | 600 | 49.47 (0.9878) | 49.40 (0.9893) | 49.73 (0.9826) | 49.35 (0.9902) |
| 20 / ordinary | 31 | 600 | 66.70 (0.7127) | 57.14 (0.8320) | 100.23 (0.4743) | 59.82 (0.7946) |
| 27 / ordinary | 40 | 400 | 31.24 (0.7152) | 27.09 (0.8248) | 45.79 (0.4879) | 27.83 (0.8027) |
| 27 / ordinary | 40 | 600 | 82.11 (0.7284) | 69.29 (0.8632) | 127.08 (0.4707) | 75.33 (0.7940) |
| 38 / ordinary | 52 | 600 | 74.50 (0.7260) | 64.28 (0.8415) | 110.37 (0.4901) | 67.22 (0.8046) |

**Calculated Reynolds numbers.** At the inlet state of the 22 windows, the [tool-joint Reynolds number](predictions/joint-reynolds.csv) on the plastic viscosity is 58,227–101,798 on 16A and 133,993–1,135,887 on 16B. The flow is therefore turbulent in the joint on this measure, while application of the correlation to mud remains an approximation.

## Scoring and recommendation rule

**Calculated scoring plan.** After this declaration is committed, the entry 12 scripts score each tapered variant on all 467 frozen circulation samples and all original run-in event identities, reporting G1–G6 before and after, with every unavailable sample and solver failure retained. The working values are `entry-10/results/smooth/`, and the `installed_primary` and `installed_no_local` values are entry 12's archived results. Trip slopes are a secondary measure with EOW 19 labelled. The entry 12 shallow diagnostic is repeated and should be unchanged, because those windows contain no ordinary pipe.

**Inferred recommendation rule, fixed before scoring.** Recommend `tapered_primary` as the joint treatment for the working calculation if its scored changes reproduce the model-only predictions within entry 12's tolerances of 1 psi, 0.1 °C and 0.1% of power, paired coverage is retained, and the angle and coefficients are within the source's stated range of application. This applies whatever the direction of the score change. The scores and slopes are reported and do not select the angle. Adoption of entry 12's geometry and of this treatment are maintainer decisions.

**Inferred assessment of the range criterion, fixed before scoring.** The angle criterion is met if the angle lies within the formula branch to 45°. No numerical Reynolds range is stated in the accessible sources, so none can be exceeded, and this is recorded as a limit of the check. The check rests on secondary statements of Crane, and the extension of the angle beyond the published bore span and the transfer to 16B are limits of the geometry, which the rule does not test.

**Calculated archive method.** `predict.py` and `summarise_predictions.py` build the model-only archive. `trip_slopes.py --model-only` builds input-only trip predictions. `score.py` requires an external bulk output directory, `compare.py` records all gaps and prediction checks, and `shallow_check.py` repeats the shallow diagnostic. Compact results and checksums are retained here, with rebuildable bulk files external and identified by hash. The whole entry stays below 5 MB.

## Scored comparison

**Calculated.** The [results](results/README.md) report every gap and the secondary trip groups with paired coverage. The source choices and model-only predictions above remain unchanged. Rebuildable bulk outputs are external and identified by hashes in [bulk-manifest.json](bulk-manifest.json).
