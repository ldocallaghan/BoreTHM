# Installed ordinary drill pipe

4 November 2026. This entry corrects the ordinary-pipe connection geometry for FORGE 16A and 16B using independently supplied equipment dimensions. It compares with the working calculation, entry 8 with entry 10's smooth Colebrook friction. The package defaults remain unchanged. FORGE 58-32 supplies no data to this entry.

## Recorded dimensions and source

**Measured source record.** Kevin England, personal communication via John McLennan, November 2026, from the drill pipe data sheets. The numeric values may be redistributed with this citation; no correspondence text is reproduced. [options.json](options.json) records each value.

| Quantity | 16A | 16B new pipe | 16B premium reference |
| --- | --- | --- | --- |
| Nominal size and weight | 5 in, 19.5 lb/ft | 5.5 in, 24.7 lb/ft | Same nominal size |
| Grade and connection | S-135, 4-1/2 IF (NC50) | S-135, 5-1/2 FH | Same connection |
| Body OD, in | 5.000 | 5.500 | 5.334 |
| Body ID, in | 4.276 | 4.670 | 4.670 |
| Tool-joint OD, in | 6.625 | 7.250 | 7.006 |
| Tool-joint ID, in | 2.750 | 3.000 | 3.063 |
| Pin tong length, in | 11 | 10 | 4 |
| Box tong length, in | 14 | 12 | 6 |
| Pin plus box, in | 25 | 22 | 10 |

Both ordinary strings are uncoated. Their approximate joint length is 31.5 ft. The retained model pitch is 31.5 ft on 16A and the existing 2378/75 = 31.706667 ft on 16B. The standpipe transducer is reported on the rig-floor manifold. This supports the retained standpipe-referenced surface allowance; no line dimension or surface loss changes. The source covers ordinary pipe only, so insulated-pipe EIS dimensions remain 7 × 4 in, with the existing 29-in restriction and recorded pitch. HWDP retains its existing recorded bore and connection scenario.

## Upset, made-up bore and coefficient sources

**Measured source records.** [references.json](references.json) gives editions and page/table locators. The inspected API Spec 5DP first-edition (August 2009) copy is committee-draft watermarked. Table C.14, printed p97, gives IEU nominal upset IDs 3.562 and 3.812 in for the two sizes, with 4.250-in internal upset length and minimum internal taper length `m_iu` of 3.000 in. Its note b distinguishes upset dimensions from finished machining. The note on printed p32 allows the upset bore and taper length to change for a particular tool joint. Figure B.6, printed p71, defines the geometry. This copy is not treated as verified final installed geometry, and none of these numbers is adopted.

**Measured supplier catalogue.** America West Drilling Supply's undated *Drill Pipe* page, Internal-External Upset table, gives end bores 3.6875 and 4.000 in, 2.25-in internal upset lengths and 2-in minimum internal tapers in the 5-in 19.5-lb/ft and 5.5-in 24.7-lb/ft rows. These are different catalogue values without identification of the installed machining. Neither source gives the finished continuous path from each body bore through its weld and made-up tool joint. No installed taper angle is supplied.

**Inferred source gap and fallback.** A minimum nominal upset length does not establish the finished hydraulic taper. No independent made-up constant-bore length was found for these installed connections. The restriction uses the recorded pin plus box tong lengths: 25 and 22 in, or 10 in for the premium sensitivity. This is a source-length approximation. External tong lengths do not measure the complete internal passage. No length is chosen from a pressure or slope result.

**Measured correlation source.** AFT Arrow 10's *Area Change Loss Model* documents Crane TP-410 (1988), A-26. Both equation images were inspected. With included angle `theta`, the expansion coefficient on upstream velocity is `2.6 sin(theta/2)(1-A_up/A_down)^2` below 45°, and `(1-A_up/A_down)^2` above 45°. For contraction, with `r=A_down/A_up`, its upstream coefficient is `0.8 sin(theta/2)(1-r)/r²` below 45° and `0.5(1-r)sqrt(sin(theta/2))/r²` above 45°. Converting contraction to the smaller-area velocity multiplies the coefficient by `r²`. The accessible implementation does not give a numerical Reynolds-number range or the equality case at 45°. It states that the Crane contraction at 180° differs from the retained Idelchik abrupt correlation. No blend is invented to force an endpoint match.

**Inferred transition choice, fixed before scoring.** The finished geometry and correlation applicability are unresolved. `installed_primary` therefore uses the prescribed abrupt fallback and equals `installed_abrupt`. This is an approximation pending a finished bore drawing. No new tapered option is added to the package. The existing abrupt coefficients use the smaller-area velocity: `K_exp=(1-r)²`, `K_con=0.5(1-r)^0.75`, where `r=A_small/A_large`. Modelica 4.0.0 documents Idelchik (2006), third edition, p208 diagram 4-1 and pp216–217 diagram 4-9: smooth turbulent single-phase flow, expansion Re>3300 and contraction Re>10000. Their annular and mud use remains approximate and flagged.

**Measured roughness source and inferred transfer.** No independently applicable roughness value was found for these uncoated installed strings. The steel sensitivity retains entry 10's 45.72 micrometres, converted from EPA EPANET 2.2 (2020), printed p18, Table 3.2, new water-pipe steel at 0.15 millifeet. It is a transferred value. The existing global option applies roughness in the supported pipe-friction paths, including internally coated insulated pipe. The Herschel–Bulkley circulation annulus correlation has no roughness argument and remains unchanged. The extension to insulated pipe is an additional sensitivity qualification, without an installed roughness measurement.

## Variants and fixed settings

**Calculated variants.** All comparisons use smooth Colebrook friction, recorded flow and PV referenced to 26.7 °C. The cumulative clock, entry 8 annulus and rotary heat are unchanged. Film multiplier is 1.0. The historical fitted trial-insulation conductivity is retained and disclosed. No new tool-loss curve is added.

| Variant | Difference from the working calculation |
| --- | --- |
| `installed_primary` | Sourced new ordinary-pipe joints; 25-in restriction on 16A and 22 in on 16B; abrupt fallback; zero roughness |
| `installed_abrupt` | Identical to primary because the primary uses the declared abrupt fallback; results may be reused explicitly |
| `installed_no_local` | Primary geometry with zero connection local loss as an idealised bound; includes retained HWDP and EIS insulated connections, with their dimensions unchanged |
| `installed_premium` | Primary with only 16B ordinary-joint ID 3.063 in and 4+6-in tong approximation; primary body and joint OD retained; 16A equals primary |
| `installed_steel` | Primary with the existing global transferred steel roughness of 45.72 micrometres |

**Calculated geometry scope.** Ordinary body dimensions already equal the supplied values. Thermal layers and thermal joint fractions are unchanged. `predict.py` identifies ordinary pipe separately from IDP by its recorded name and body geometry. The [geometry audit](predictions/geometry-audit.csv) records every joint-bearing segment on the selected windows. Three focused tests verify that an identical body bore does not transfer installed ordinary-pipe joints into insulation, that HWDP is preserved, and that the premium scope and thermal geometry are retained.

**Measured prior exposure.** Entry 10's catalogue FH variant has already been scored: its 16B G1 assembly-bias RMS is 152.8 psi, and regular-pipe trip-slope ratios are 0.47–0.59. It used 7.5 × 3.0-in joints with the 29-in restriction and abrupt treatment, including a catalogue transfer to insulation. The subsequently supplied installed ordinary-pipe bore is also 3.0 in. This prior result is disclosed, without using its agreement to select transition treatment or restriction length. Installed values are fixed by the personal communication.

## Model-only predictions

**Calculated preparation.** The entry 10 selection is retained: one lower-median-depth operating window per assembly, restricted to Sanvean on-bottom samples for 16A. There are 22 windows, nine on 16A and 13 on 16B. [model-only.csv](predictions/model-only.csv) gives every selected sample's G1 pressure and G2 hydraulic-power change for every variant. The table also gives the expected G3 bit-temperature, G5 return-temperature and G6 sensor-proxy changes. These are rough effect estimates from full coupled solves on representative inputs, not full-scoreboard means. Each distinct case starts from the usual seeds. Identical abrupt and 16A premium cases are reused explicitly.

The working replay matches the archived entry 10 smooth model-only outputs within 1 psi, 0.1 °C and 0.1% of hydraulic power, as recorded in [working-replay-check.csv](predictions/working-replay-check.csv). No observation-based residual or score is calculated here. The 132 rows have no solver failures or energy flags. [rough-effects.csv](predictions/rough-effects.csv) supplies these modelled change ranges:

| Variant | Well | Pressure change, psi | Hydraulic power change, kW | Bit change, °C | Sensor proxy change, °C | Return change, °C |
| --- | --- | --- | --- | --- | --- | --- |
| installed_abrupt | 16A | 479.3 to 1194.4 | 117.2 to 345.2 | 2.04 to 6.86 | 2.04 to 6.86 | 0.69 to 1.57 |
| installed_abrupt | 16B | 0.0 to 1410.3 | 0.0 to 700.0 | 0.00 to 9.83 | 0.00 to 9.84 | 0.00 to 2.19 |
| installed_no_local | 16A | -372.2 to -147.2 | -107.3 to -36.0 | -2.10 to -0.61 | -2.10 to -0.61 | -0.49 to -0.21 |
| installed_no_local | 16B | -129.2 to 8.9 | -40.0 to 4.1 | -0.58 to 0.02 | -0.58 to 0.02 | -0.18 to 0.01 |
| installed_premium | 16A | 479.3 to 1194.4 | 117.2 to 345.2 | 2.04 to 6.86 | 2.04 to 6.86 | 0.69 to 1.57 |
| installed_premium | 16B | 0.0 to 1120.5 | 0.0 to 556.1 | 0.00 to 8.00 | 0.00 to 8.00 | 0.00 to 1.74 |
| installed_primary | 16A | 479.3 to 1194.4 | 117.2 to 345.2 | 2.04 to 6.86 | 2.04 to 6.86 | 0.69 to 1.57 |
| installed_primary | 16B | 0.0 to 1410.3 | 0.0 to 700.0 | 0.00 to 9.83 | 0.00 to 9.84 | 0.00 to 2.19 |
| installed_steel | 16A | 593.2 to 1425.3 | 145.2 to 412.9 | 2.81 to 8.87 | 2.81 to 8.87 | 0.85 to 1.85 |
| installed_steel | 16B | 198.6 to 1652.7 | 56.1 to 813.9 | 0.90 to 13.14 | 0.89 to 13.13 | 0.27 to 2.55 |

**Inferred predicted directions.** Smaller ordinary-joint bores increase internal loss and its heat. This tends to increase bit temperatures and surface returns. The shorter restriction competes with the bore change. The zero-local-loss bound can reduce pressure despite the smaller bores. The full-IDP trial has no ordinary-pipe correction, while mixed strings retain only their ordinary-pipe changes. The run-in model is unchanged; G4 may change indirectly through its conditioning circulation. No bulk heat-over-capacity bound is imposed on the bit-temperature change.

**Calculated trip predictions.** [Trip slopes](predictions/trips/slopes.csv) use all 186 frozen input windows from the six entry 9 groups and the same clustering and modelled regression. EOW 19 is added insulated pipe. Absolute observation/model ratios require measured slopes, so before scoring the prediction is expressed as `R_candidate = R_working × multiplier`, where `multiplier = working model slope / candidate model slope`. No new measured slope or ratio is calculated in preparation. The previously seen FH ratios remain the exposure disclosure above.

| Variant | EOW | Excursion | Flow group, US gpm | Predicted slope, psi/1000 ft | Predicted ratio multiplier |
| --- | --- | --- | --- | --- | --- |
| installed_primary | 17 | 27 | 500 | 147.74 | 0.3938 |
| installed_primary | 19 | 29 | 600 | 50.12 | 0.9750 |
| installed_primary | 20 | 31 | 600 | 150.75 | 0.3153 |
| installed_primary | 27 | 40 | 400 | 67.72 | 0.3299 |
| installed_primary | 27 | 40 | 600 | 194.83 | 0.3070 |
| installed_primary | 38 | 52 | 600 | 164.40 | 0.3290 |
| installed_abrupt | 17 | 27 | 500 | 147.74 | 0.3938 |
| installed_abrupt | 19 | 29 | 600 | 50.12 | 0.9750 |
| installed_abrupt | 20 | 31 | 600 | 150.75 | 0.3153 |
| installed_abrupt | 27 | 40 | 400 | 67.72 | 0.3299 |
| installed_abrupt | 27 | 40 | 600 | 194.83 | 0.3070 |
| installed_abrupt | 38 | 52 | 600 | 164.40 | 0.3290 |
| installed_no_local | 17 | 27 | 500 | 54.50 | 1.0675 |
| installed_no_local | 19 | 29 | 600 | 33.37 | 1.4646 |
| installed_no_local | 20 | 31 | 600 | 42.26 | 1.1250 |
| installed_no_local | 27 | 40 | 400 | 20.56 | 1.0864 |
| installed_no_local | 27 | 40 | 600 | 49.61 | 1.2056 |
| installed_no_local | 38 | 52 | 600 | 48.38 | 1.1179 |
| installed_premium | 17 | 27 | 500 | 130.39 | 0.4462 |
| installed_premium | 19 | 29 | 600 | 49.93 | 0.9788 |
| installed_premium | 20 | 31 | 600 | 130.94 | 0.3630 |
| installed_premium | 27 | 40 | 400 | 58.68 | 0.3808 |
| installed_premium | 27 | 40 | 600 | 170.91 | 0.3500 |
| installed_premium | 38 | 52 | 600 | 143.30 | 0.3774 |
| installed_steel | 17 | 27 | 500 | 163.29 | 0.3563 |
| installed_steel | 19 | 29 | 600 | 62.62 | 0.7804 |
| installed_steel | 20 | 31 | 600 | 166.19 | 0.2860 |
| installed_steel | 27 | 40 | 400 | 72.92 | 0.3064 |
| installed_steel | 27 | 40 | 600 | 228.89 | 0.2613 |
| installed_steel | 38 | 52 | 600 | 181.94 | 0.2973 |

These secondary ratios do not select a geometry or enter the recommendation rule. EOW 19 retains EIS insulated joints, so its added-length response can differ from groups that add ordinary pipe. The zero-local-loss and global roughness sensitivities also affect the retained insulated connections as explicitly declared.

## Scoring and recommendation rule

**Calculated scoring plan.** After this declaration is committed, use the entry 10 scoring procedure and unchanged frozen scoreboard reductions for all 467 circulation samples and all original run-in event identities. Report G1–G6 before and after, retaining original unavailable coverage and all solver failures. Before is `entry-10/results/smooth/`; the catalogue FH result is a separate previously scored reference. Use exactly the same six secondary trip groups, with EOW 19 labelled as added insulated pipe. No 58-32 data is opened or used.

**Inferred recommendation rule, fixed before scoring.** Recommend the independently sourced installed geometry for the working calculation if paired coverage is retained and its model-only changes are reproduced within entry 10's tolerances: 1 psi, 0.1 °C and 0.1% of modelled hydraulic power at the declared windows. The direction of a score change cannot select geometry. Recommend the abrupt fallback solely as an unresolved-profile approximation; a sourced applicable taper can be considered in a later declaration. Trip slopes and score improvements do not choose the transition. The maintainer decides whether to adopt anything; package defaults remain unchanged.

**Calculated archive method.** `predict.py` and `summarise_predictions.py` build the representative model-only archive. `trip_slopes.py --model-only` builds input-only trip predictions; its scoring mode uses the original entry 9 regression. `score.py` adapts the entry 10 procedure and requires an external bulk output directory. `compare.py` records all gaps and the prediction checks. Compact final results and checksums are retained here; rebuildable bulk files remain external with hashes and recipes. The whole entry stays below 5 MB. Source downloads and inspection images are external. The [development log](../../../docs/science/model-development.md) records the declaration and later results.

## Scored comparison

**Calculated.** The [results](results/README.md) report every gap and the secondary trip groups with paired coverage. The original source choices and model-only predictions above remain unchanged. Rebuildable bulk outputs are external and identified by hashes in [bulk-manifest.json](bulk-manifest.json).
