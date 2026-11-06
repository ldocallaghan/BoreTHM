# Tool-loss allowances and motor no-load drop on the adopted calculation

5 November 2026. This entry adds generic pressure-loss allowances for downhole tools, taken from published specification sheets, to the working calculation adopted in entry 13. It compares the result on the frozen FORGE 16A and 16B samples with entry 13's `tapered_primary`. The same allowances become package defaults in the release that follows, with the working calculation's settings. FORGE 56-32 temperatures, 58-32 thermal targets and 78B-32 data supply nothing to this entry, and they remain the unseen-well tests.

## Prior exposure

**Measured prior exposure.** Three earlier results were known before any value below was chosen.

Entry 9 reported a shallow 16B excess of 188–481 psi of measured over modelled pump pressure, with a dependence on flow.

On 5 November 2026, before this entry, published analogue figures were compared informally with the 16B shallow gap. At about 600 gpm they gave about 170–390 psi against 222–241 psi measured, and at about 230 gpm they gave about 25–60 psi against about 190–250 psi measured.

The zero yield stress of entry 8 was chosen after entries 6 and 7 had been scored, so 16A and 16B do not test it.

No value, rule or exponent below was chosen from agreement with G1–G6, the trip slopes or the shallow windows. Every FORGE score in this entry follows the commit of this declaration.

## Sources and rule

**Measured source records.** [`tool_losses.csv`](../../../src/borethm/data/tool_losses.csv) has one row for each published figure, 49 in all, with its document, edition, page or table, URL and file hash. Its [README](../../../src/borethm/data/tool-losses-README.md) defines the columns and the limits of the figures. [`tools/build_tool_losses.py`](../../../tools/build_tool_losses.py) writes the defaults from it.

**Calculated rule, fixed before any score.** For each tool class and size band:

1. Each usable row is converted to water at 8.34 lbm/galUS and the band's reference flow. A row with two or more points or a formula uses its own exponent, and a single point uses 2. Pressure drop scales linearly with density.
2. Variants of one tool family in one band reduce to their median, so that a maker with a long table counts once. This step extends the stated rule, which counts sources, because a table of several variants of one tool is one source.
3. The default is the median across sources, and the exponent is the median of the exponents of sources with two or more points or a formula, or 2 with none.
4. A tool takes the band nearest to its collar size. The bands and reference flows are 4.75 in at 250 US gal/min, 6.75 in at 600, 8 in at 800 and 9.5 in at 1,000.
5. A single source is used and flagged. A class and band with no source has a default of zero, with a warning in every result that uses it.

The tool loss is ΔP_ref × (ρ/ρ_ref) × (Q/Q_ref)^n, where ΔP_ref is the reference pressure drop at flow Q_ref and density ρ_ref, and n is the exponent. Its heat enters the fluid at the tool's depth, as the existing local losses do.

**Inferred source decisions, fixed before any score.** An upper bound, such as the "<200 psi" printed for the APS SureSteer RSS675, gives no value to convert, so it is recorded and not used. A figure with no printed density is taken as water, and the table says so. A figure with no collar size goes to the band chosen by its printed flow. The column alignment of the TelePacer table was checked against the PDF and agrees with the expected order; the same table's millimetre labels for 6¾ and 9½ in appear to be misprinted, so the inch sizes are used. The PowerDrive Orbit 1100 is outside the bands. The formula sheets print no output unit, and psi is inferred from their field-unit form.

**Calculated defaults.**

| Class | Band, in | Reference flow, US gal/min | Default in water, psi | Exponent | Range of sources, psi | Status | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MWD pulser | 4.75 | 250 | 149.9 | 1.61 | 107.6–208.5 | multiple sources | gordon-gt-mwd, telepacer, xbolt-g2-l, xbolt-g2-r |
| MWD pulser | 6.75 | 600 | 187.7 | 2.00 | 87.0–293.9 | multiple sources | ap400p, gordon-gt-mwd, kambi, phx-p360, telepacer, telescope, xbolt-g2-l, xbolt-g2-r |
| MWD pulser | 8.0 | 800 | 185.0 | 1.82 | 94.3–309.2 | multiple sources | gordon-gt-mwd, telepacer, xbolt-g2-l, xbolt-g2-r |
| MWD pulser | 9.5 | 1,000 | 100.0 | 1.00 | 100.0 | single source | telepacer |
| Rotary steerable | 4.75 | 250 | 69.0 | 2.00 | 35.9–102.0 | multiple sources | aps-rss475, powerdrive-orbit |
| Rotary steerable | 6.75 | 600 | 91.8 | 2.00 | 53.6–130.0 | multiple sources | aps-rsm675, powerdrive-orbit |
| Rotary steerable | 8.0 | 800 | 0.0 | 2.00 | none | no source | none |
| Rotary steerable | 9.5 | 1,000 | 32.2 | 2.00 | 32.2 | single source | powerdrive-orbit |
| Mud motor, no load | 4.75 | 250 | 0.0 | 2.00 | none | no source | none |
| Mud motor, no load | 6.75 | 600 | 0.0 | 2.00 | none | no source | none |
| Mud motor, no load | 8.0 | 800 | 0.0 | 2.00 | none | no source | none |
| Mud motor, no load | 9.5 | 1,000 | 0.0 | 2.00 | none | no source | none |
| Filter sub | 4.75 | 250 | 0.0 | 2.00 | none | no source | none |
| Filter sub | 6.75 | 600 | 0.0 | 2.00 | none | no source | none |
| Filter sub | 8.0 | 800 | 0.0 | 2.00 | none | no source | none |
| Filter sub | 9.5 | 1,000 | 0.0 | 2.00 | none | no source | none |
| Float sub | 4.75 | 250 | 0.0 | 2.00 | none | no source | none |
| Float sub | 6.75 | 600 | 0.0 | 2.00 | none | no source | none |
| Float sub | 8.0 | 800 | 0.0 | 2.00 | none | no source | none |
| Float sub | 9.5 | 1,000 | 0.0 | 2.00 | none | no source | none |

**Measured gaps.** No published no-load figure with a stated flow was found for a mud motor. The sheets retrieved print one figure for a whole flow range: BICO 300–700 psi, Sniper 110 psi, GeoGuidance 100 psi, Drilformance 126–150 psi and Black Diamond 87–193 psi. The Baker Hughes patent's field log gives 200–300 psi off bottom, with no flow attached. These are recorded and not used, so the motor default is zero in every band. A maker's curve against flow may exist that this search did not find. No published figure was found for a filter sub or a float sub, and none for a rotary steerable tool in the 8-in band. Some pages could not be retrieved, including the Wenzel and Dynomax sheets and the NOV motor handbook. Scientific Drilling's HALO and TiTAN22 figures are not public and are not used.

## Motor no-load treatment

**Calculated change.** Off bottom, a motor's pressure drop is its no-load drop, from the default or a user's figure. On bottom, the drop is the no-load drop plus the differential, and the heat released at the motor is (no-load + differential) × flow. Both the motor's mechanical output and its internal losses become heat within a few metres of the bit, so the two are released at the same place. The differential remains the rig's reported differential.

With the zero default, the motor terms on 16A and 16B are the same as in `tapered_primary`, and a warning records the zero.

## FORGE configuration

**Calculated configuration.** Inputs follow entry 13's `tapered_primary`: installed pipe dimensions, tapered ordinary-joint transitions at 11.5°, abrupt treatments elsewhere, smooth Colebrook pipe friction and the no-yield rheology of entry 8. Only the tools named in [`options.json`](options.json) are added. [`predictions/assembly-tools.csv`](predictions/assembly-tools.csv) lists each one by assembly.

**Inferred tool assignment.** Each tool is identified from the assembly records already in the frozen geometry.

- HALO is the Scientific Drilling rotary steerable system on EOW 11, 12, 13, 15 and 16. It integrates steering, measurement and pulser, so it takes the rotary steerable default and no separate pulser.
- Pulser subs, hangoff subs and collars recorded with MWD (measurement while drilling) take the pulser default at the nearest band.
- The aggregated trial assembly on EOW 17–20 takes a 6¾-in pulser and a 6¾-in filter sub, as the end-of-well reports record inside the aggregate.

Each tool is additive to the friction already calculated on its segment. Filter subs, float subs and motors have a zero default and add nothing here.

## Model-only predictions

**Calculated.** [`predict.py`](predict.py) solves all 467 frozen samples, with and without the tools, using no measured target: 467 sample pairs, no solver failures and no energy flags. Per-sample changes in pressure, power, bit, sensor and return temperature are in [`predictions/model-only.csv`](predictions/model-only.csv).

**Calculated default route.** [`route_check.py`](route_check.py) solves five samples again with the joint transitions and named tools left to the package's v1.8.0 defaults, and the results in [`predictions/default-route-check.csv`](predictions/default-route-check.csv) are identical to the harness values. The score therefore applies to the package route for these two settings. The test suite covers the remaining preset rows and the rheology conversion.

### Changes by assembly

| Well | Assembly | Tools with a figure | Samples | Flow, US gal/min | Pressure, psi | Hydraulic power, kW | Bit, °C | Return, °C |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 16A | 18 | mwd pulser (6.75 in) | 48 | 346–597 | +65.4 to +193.9 | +38.7 | +1.32 | +0.21 |
| 16A | 23 | mwd pulser (6.75 in) | 50 | 439–692 | +108.2 to +266.7 | +47.8 | +1.69 | +0.24 |
| 16A | 30 | mwd pulser (6.75 in) | 72 | 547–599 | +165.3 to +198.7 | +46.1 | +1.76 | +0.23 |
| 16A | 34 | mwd pulser (6.75 in) | 23 | 373–600 | +76.7 to +200.2 | +48.0 | +1.85 | +0.23 |
| 16A | 35r1 | mwd pulser (6.75 in) | 12 | 647–659 | +233.2 to +242.5 | +69.3 | +2.68 | +0.29 |
| 16A | 35r2 | mwd pulser (6.75 in) | 9 | 623–648 | +216.9 to +234.9 | +64.9 | +2.64 | +0.27 |
| 16A | 38 | mwd pulser (6.75 in) | 45 | 620–665 | +214.7 to +247.9 | +69.2 | +2.85 | +0.28 |
| 16A | 39 | mwd pulser (6.75 in) | 61 | 641–657 | +230.2 to +241.2 | +68.8 | +2.78 | +0.27 |
| 16A | 42 | mwd pulser (6.75 in) | 38 | 318–654 | +56.1 to +242.5 | +62.9 | +3.06 | +0.23 |
| 16B | 3 | mwd pulser (9.5 in) | 3 | 1105–1149 | +117.3 to +121.9 | +59.3 | +0.48 | +0.18 |
| 16B | 4 | mwd pulser (9.5 in) | 2 | 1072–1097 | +115.4 to +118.0 | +55.2 | +0.45 | +0.18 |
| 16B | 11 | rotary steerable (6.75 in) | 4 | 544–651 | +75.7 to +108.0 | +27.5 | +0.88 | +0.13 |
| 16B | 12 | rotary steerable (6.75 in) | 12 | 597–611 | +90.6 to +94.7 | +24.5 | +0.89 | +0.11 |
| 16B | 13 | rotary steerable (6.75 in) | 14 | 591–604 | +88.9 to +92.8 | +24.1 | +0.94 | +0.10 |
| 16B | 15 | rotary steerable (6.75 in) | 4 | 594–604 | +90.1 to +92.9 | +24.2 | +1.03 | +0.10 |
| 16B | 16 | rotary steerable (6.75 in) | 15 | 596–603 | +92.2 to +94.4 | +24.8 | +1.22 | +0.09 |
| 16B | 17 | mwd pulser (6.75 in) | 14 | 586–610 | +183.0 to +198.4 | +50.3 | +2.60 | +0.17 |
| 16B | 18 | mwd pulser (6.75 in) | 10 | 647–700 | +216.5 to +254.8 | +67.1 | +1.40 | +0.31 |
| 16B | 19 | mwd pulser (6.75 in) | 10 | 653–709 | +223.8 to +265.2 | +77.6 | +2.48 | +0.30 |
| 16B | 20 | mwd pulser (6.75 in) | 11 | 595–712 | +196.3 to +276.0 | +74.9 | +3.74 | +0.19 |
| 16B | 27 | mwd pulser (6.75 in) | 5 | 579–716 | +186.3 to +276.6 | +74.9 | +4.06 | +0.20 |
| 16B | 38 | mwd pulser (6.75 in) | 5 | 603–656 | +198.1 to +239.2 | +63.1 | +3.92 | +0.17 |

### G1, pump pressure

| Well | Assembly | Predicted change, psi | `tapered_primary` bias, psi | Expected bias, psi |
| --- | --- | --- | --- | --- |
| 16A | 18 | +169.8 | -1216.1 | -1046.3 |
| 16A | 23 | +188.8 | -1483.2 | -1294.4 |
| 16A | 30 | +182.0 | -1055.0 | -873.0 |
| 16A | 34 | +195.0 | -1088.5 | -893.4 |
| 16A | 35r1 | +237.3 | -1296.8 | -1059.5 |
| 16A | 35r2 | +227.8 | -1194.8 | -967.0 |
| 16A | 38 | +237.8 | -728.3 | -490.5 |
| 16A | 39 | +235.6 | -590.3 | -354.7 |
| 16A | 42 | +228.4 | -1901.7 | -1673.3 |
| 16B | 12 | +92.5 | -356.0 | -263.5 |
| 16B | 13 | +91.4 | -301.7 | -210.3 |
| 16B | 15 | +91.6 | -285.2 | -193.6 |
| 16B | 16 | +92.9 | -375.1 | -282.1 |

The expected assembly-bias RMS is 1030.4 psi on 16A, from 1228.4, and 240.2 psi on 16B, from 331.6.

### G2, hydraulic power

| Well | Samples | Predicted change, kW | Range, kW | `tapered_primary` bias, kW | Expected bias, kW |
| --- | --- | --- | --- | --- | --- |
| 16A | 135 | +57.6 | +39.7 to +81.6 | -287.5 | -230.0 |
| 16B | 109 | +47.4 | +18.1 to +90.2 | -190.7 | -143.3 |

### G3, 16A bit temperature

All nine assemblies warm by the added heat. The expected RMS of the assembly biases is 5.11 °C, from 6.00 °C.

| Assembly | Predicted change, °C | `tapered_primary` bias, °C | Expected bias, °C |
| --- | --- | --- | --- |
| 18 | +1.44 | -3.06 | -1.62 |
| 23 | +1.70 | +1.36 | +3.06 |
| 30 | +1.78 | +5.25 | +7.03 |
| 34 | +2.02 | +0.87 | +2.89 |
| 35r1 | +2.69 | +0.30 | +2.99 |
| 35r2 | +2.66 | -3.35 | -0.69 |
| 38 | +2.86 | -3.16 | -0.29 |
| 39 | +2.79 | -4.74 | -1.95 |
| 42 | +3.18 | -15.50 | -12.32 |

### G5 and G6, return and sensor temperatures

Return temperatures warm slightly and the 16B sensor proxies warm by more, so the warm 16B biases are expected to grow.

| Measure | Samples | Predicted change, °C | Range, °C | `tapered_primary` bias, °C | Expected bias, °C |
| --- | --- | --- | --- | --- | --- |
| G5, 16A return, all samples | 358 | +0.24 | +0.08 to +0.37 | -4.65 | -4.41 |
| G6, 16B independent regular pipe | 59 | +1.42 | +0.62 to +4.43 | +3.82 | +5.25 |
| G6, 16B trial runs | 45 | +2.39 | +1.15 to +3.96 | +10.17 | +12.55 |

G4, the run-in peak error, has no sample-by-sample prediction. Entry 13's variants moved it by less than 0.05 °C for changes in power of up to about 250 kW, so a change of less than 0.1 °C from 34.86 °C is expected.

### Shallow windows

[`predictions/shallow-windows.csv`](predictions/shallow-windows.csv) gives the ten primary 16B windows of entry 9. Each uses that entry's recorded flow and temperature. No measured value enters this table.

| Window | Assembly | Bit depth, ft | Flow, US gal/min | Tools with a figure | Before, psi | Predicted, psi | Change, psi |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 16B-00456 | 11 | 370 | 572 | rotary steerable | 416.0 | 499.7 | +83.7 |
| 16B-00457 | 11 | 370 | 573 | rotary steerable | 416.8 | 500.8 | +84.0 |
| 16B-00464 | 12 | 309 | 572 | rotary steerable | 365.8 | 448.4 | +82.6 |
| 16B-00465 | 12 | 309 | 572 | rotary steerable | 365.8 | 448.6 | +82.8 |
| 16B-01342 | 20 | 35 | 216 | MWD pulser | 30.5 | 55.1 | +24.7 |
| 16B-01343 | 20 | 35 | 222 | MWD pulser | 32.1 | 58.1 | +26.0 |
| 16B-01812 | 27 | 335 | 492 | MWD pulser | 188.1 | 315.4 | +127.3 |
| 16B-03261 | 38 | 346 | 423 | MWD pulser | 136.2 | 230.2 | +94.0 |
| 16B-03262 | 38 | 346 | 238 | MWD pulser | 44.3 | 73.9 | +29.6 |
| 16B-03263 | 38 | 346 | 237 | MWD pulser | 44.1 | 73.6 | +29.5 |

### Trip-slope ratios

[`predictions/trip-slopes.csv`](predictions/trip-slopes.csv) gives the prediction, and slopes are in psi per 1000 ft. The added terms do not depend on pipe length, so the expectation was no change in the ratios. The model-only calculation shows small changes, with multipliers of 0.919–1.024.

**Calculated explanation.** The flow differs among the depth stages of each group, inside its ±2.5% band, and the allowance depends on flow. The slope of the 6.75-in pulser allowance against depth, from the stage flows alone in [`predictions/trip-slope-drift.csv`](predictions/trip-slope-drift.csv), accounts for each change to within 0.14 psi per 1000 ft. The pipe friction and joint losses do not change.

| Group | Stage flows, US gal/min | Modelled slope before | After | Allowance slope from stage flows | Slope change | Ratio multiplier | Archived ratio | Predicted ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EOW 17, 500 gpm | 489–512 | 74.76 | 81.31 | +6.64 | +6.55 | 0.919 | 1.13 | 1.03 |
| EOW 19, 600 gpm (insulated) | 590–604 | 49.47 | 50.07 | +0.63 | +0.60 | 0.988 | 0.96 | 0.95 |
| EOW 20, 600 gpm | 592–606 | 66.70 | 65.88 | -0.69 | -0.82 | 1.013 | 1.12 | 1.13 |
| EOW 27, 400 gpm | 400–406 | 31.24 | 30.51 | -0.67 | -0.73 | 1.024 | 1.30 | 1.33 |
| EOW 27, 600 gpm | 597–612 | 82.11 | 88.69 | +6.52 | +6.57 | 0.926 | 1.39 | 1.29 |
| EOW 38, 600 gpm | 591–609 | 74.50 | 76.00 | +1.60 | +1.49 | 0.980 | 1.35 | 1.32 |

The predicted ratio is the archived entry 13 ratio times the multiplier. No new measured slope is calculated for it. EOW 19 adds insulated pipe.

## What counts as reproduced

**Rule.** The scored changes must match the model-only predictions within entry 12's tolerances: 1 psi, 0.1 °C and 0.1% of power. As in entries 12 and 13, this tests the implementation. The model-only calculation and the score use the same solver on the same inputs, so agreement is not evidence that the defaults are right. The unseen wells are the test of the defaults.

The unexplained part of the shallow gap stays open whatever the score shows. No term is added for it.

## Reproducing

```
python validation/model-development/entry-14/predict.py
python validation/model-development/entry-14/route_check.py
python validation/model-development/entry-14/summarise_predictions.py --reference <entry 13 bulk>/tapered_primary
python validation/model-development/entry-14/score.py --declaration <commit> --output <bulk> --scratch <scratch>
python validation/model-development/entry-14/compare.py --declaration <commit> --results <bulk> --reference <entry 13 bulk>/tapered_primary
```

## Amendment: tool assignment

**Date and status.** 6 November 2026. This amendment corrects the tool assignment of entry 14. It was committed before any rescoring. The tool table, the rule and the package defaults do not change, and the original declaration, predictions and archive stay as committed.

**Measured error.** Entry 14 gave each HALO assembly the rotary steerable default and no MWD (measurement while drilling) pulser, on the ground that HALO integrates steering, measurement and pulser. The 16B end-of-well report prints a pulser serial number in the comments of every HALO sheet, beside the HALO, Eye, gamma and battery. The steering figures in the tool table cover the steering unit only, so a HALO assembly carries both allowances.

| BHA | Report page | Printed |
| --- | --- | --- |
| 11 | 71 | Halo 7600-0781; Pulser 128-481 |
| 12 | 75 | Halo 7600-1125; Pulser 128-474 |
| 13 | 80 | Halo 7600-1125; Pulser 128-474 |
| 14 | 85 | Halo 7600-0233; Pulser 213-006 |
| 15 | 93 | Halo 7600-1711; Pulser 122-1243F |
| 16 | 97 | Halo 7600-0406; Pulser 213-004F |

BHA 14 has no sample in the scoreboard.

**Disclosure.**

- The error was found in review after the entry 14 scores had been seen.
- The review estimated that the pulser adds about 170 psi at EOW 12's flow, against the 144–145 psi remainder reported.
- The correction comes from the printed BHA sheets, and the scores do not choose it.

**Measured tool audit.** [`predictions/assembly-tools-audit.csv`](predictions/assembly-tools-audit.csv) records the MWD pulser, rotary steerable, motor, filter sub and float sub of each scoreboard assembly, with the source page of each, and [`amended/build_audit.py`](amended/build_audit.py) writes it. The differences from the declared assignment are:

| Assemblies | Printed | Declared | Correction | Effect |
| --- | --- | --- | --- | --- |
| 16B EOW 11, 12, 13, 15 and 16 | Pulser serial number in the sheet comments | No pulser | 6¾-in MWD pulser allowance added | 187.7 psi in water at 600 US gal/min |
| 16B EOW 18, 19 and 20 | 6¾ float sub, sheet row 11 and Appendix B page 189 | No float sub | Added to the record | None, because the float sub default is zero |

The motor, filter sub, rotary steerable and other float sub rows agree with the declared assignment on all 22 assemblies.

**Measured limits of the audit.** On 16B EOW 3 and 4 the word "pulser" is not printed. The daily reports name MWD on these runs and the sheets list a hangoff sub, so the declared 9.5-in pulser stays. On 16A the component tables name MWD and do not print the word "pulser", so the declared 6¾-in pulser stays. The 16A rows use the component table already audited in entry 9, which gives each report member, page and hash. The sheet for EOW 13 repeats the comment of EOW 12, while its own row 2 and Appendix E name HALO 0233, so that sheet's pulser serial number is uncertain, though a pulser is printed. The daily reports of 23–25 May 2023 record that the pulser failed at 8,585 ft, the end of EOW 18. The reports do not say when it failed or what happened to its pressure loss, so EOW 18 keeps its allowance.

**Inferred position.** The sheets do not print the pulser's position in a HALO assembly. They print the Eye at 22 ft and gamma at 17 ft from the bit, inside the HALO row's first 36 ft, so the allowance is placed on the HALO segment. The position does not alter the pressure loss. It sets where the heat enters.

**Calculated predictions.** [`amended.py`](amended.py) runs the entry 14 scripts with [`amended/options.json`](amended/options.json), and its outputs are in [`amended/predictions`](amended/predictions). All 467 sample pairs solved with no measured target, no solver failures and no energy flags. The 49 samples of the five HALO assemblies change. The other 418 samples are identical to the original predictions, within 1e-9 in every field. The default-route check again gives zero difference on its five samples. Changes in this section are from the original entry 14 predictions.

| Assembly | Samples | Flow, US gal/min | Pressure, psi | Hydraulic power, kW | Bit, °C | Sensor proxy, °C | Return, °C |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 11 | 4 | 544–651 | +204.1 | +56.4 | +1.80 | +1.59 | +0.27 |
| 12 | 12 | 597–611 | +189.4 | +50.3 | +1.83 | +1.63 | +0.23 |
| 13 | 14 | 591–604 | +187.2 | +49.4 | +1.93 | +1.74 | +0.21 |
| 15 | 4 | 594–604 | +187.5 | +49.7 | +2.12 | +1.93 | +0.21 |
| 16 | 15 | 596–603 | +190.5 | +51.0 | +2.52 | +2.32 | +0.19 |

**G1, pump pressure.** The expected assembly-bias RMS on the motorless 16B assemblies is 60.1 psi, from 240.2 psi in the original entry 14 and 331.6 psi in `tapered_primary`. 16A does not change.

| Assembly | `tapered_primary` bias, psi | Original entry 14 bias, psi | Predicted change, psi | Expected bias, psi |
| --- | --- | --- | --- | --- |
| 12 | -356.0 | -263.5 | +189.4 | -74.1 |
| 13 | -301.7 | -210.3 | +187.2 | -23.1 |
| 15 | -285.2 | -193.6 | +187.5 | -6.1 |
| 16 | -375.1 | -282.1 | +190.5 | -91.6 |

**G2, hydraulic power.** The 16B well bias is expected to change by +22.8 kW, to -120.5 kW. 16A does not change.

**G3, G4 and G5.** These measures use only 16A, so the expected change in each is zero, and their values stay at 5.11 °C, 34.83 °C and −4.41 °C.

**G6, 16B sensor proxies.** Every HALO assembly warms by 1.6–2.3 °C. EOW 11, 12 and 13 move toward zero or through it, and EOW 15 and 16, already warm, grow. The trial bias does not change.

| Measure | Samples | `tapered_primary` bias, °C | Original entry 14 bias, °C | Predicted change, °C | Expected bias, °C |
| --- | --- | --- | --- | --- | --- |
| G6, 16B independent regular pipe | 59 | +3.82 | +5.25 | +1.57 | +6.82 |
| G6, EOW 11 | 4 | -4.92 | -4.15 | +1.59 | -2.56 |
| G6, EOW 12 | 12 | -2.53 | -1.73 | +1.63 | -0.11 |
| G6, EOW 13 | 14 | -1.44 | -0.60 | +1.74 | +1.14 |
| G6, EOW 15 | 4 | +5.38 | +6.31 | +1.93 | +8.24 |
| G6, EOW 16 | 15 | +11.70 | +12.83 | +2.32 | +15.14 |

**Shallow windows.** Only the EOW 11 and 12 windows change. The measured values are the archived values of entry 13, which were known before this amendment. At about 572 US gal/min the model is expected to read 22–25 psi above the measurement on these four windows, where the original entry 14 read 144–150 psi below it. The other six windows, on EOW 20, 27 and 38, do not change, including all four at 216–238 US gal/min.

| Window | Assembly | Flow, US gal/min | Original entry 14, psi | Predicted, psi | Change, psi | Archived measured, psi | Expected gap, psi |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 16B-01342 | 20 | 216 | 55.1 | 55.1 | +0.0 | 218.2 | 163.1 |
| 16B-01343 | 20 | 222 | 58.1 | 58.1 | +0.0 | 224.8 | 166.7 |
| 16B-03263 | 38 | 237 | 73.6 | 73.6 | +0.0 | 293.1 | 219.6 |
| 16B-03262 | 38 | 238 | 73.9 | 73.9 | +0.0 | 289.0 | 215.1 |
| 16B-03261 | 38 | 423 | 230.2 | 230.2 | +0.0 | 538.6 | 308.5 |
| 16B-01812 | 27 | 492 | 315.4 | 315.4 | +0.0 | 668.8 | 353.4 |
| 16B-00464 | 12 | 572 | 448.4 | 617.4 | +169.0 | 592.7 | -24.7 |
| 16B-00456 | 11 | 572 | 499.7 | 671.0 | +171.2 | 649.4 | -21.5 |
| 16B-00465 | 12 | 572 | 448.6 | 617.9 | +169.3 | 594.0 | -23.9 |
| 16B-00457 | 11 | 573 | 500.8 | 672.5 | +171.8 | 649.4 | -23.1 |

**Trip slopes.** The six groups use EOW 17, 19, 20, 27 and 38, none of which changes, so every slope and ratio is expected to stay at its original entry 14 value.

**What counts as reproduced.** As in the original declaration, the scored changes must match these predictions within 1 psi, 0.1 °C and 0.1% of power. This tests the implementation. The unseen wells are the test of the defaults.

```
python validation/model-development/entry-14/amended/build_audit.py
python validation/model-development/entry-14/amended.py predict
python validation/model-development/entry-14/amended.py route
python validation/model-development/entry-14/amended.py summarise --reference <entry 13 bulk>/tapered_primary
python validation/model-development/entry-14/amended.py score --declaration <commit> --output <bulk> --scratch <scratch>
python validation/model-development/entry-14/amended.py compare --declaration <commit> --results <bulk> --reference <entry 13 bulk>/tapered_primary
python validation/model-development/entry-14/amended.py archive --declaration <commit> --scores <bulk>
```
