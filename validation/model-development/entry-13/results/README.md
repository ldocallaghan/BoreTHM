# Tapered-joint comparison results

**Calculated comparisons.** All variants use the declared frozen samples and settings. Bias is model minus observation. Gap definitions follow entry 12. The tapered variants and the working copy were scored for this entry. `installed_primary` and `installed_no_local` are entry 12's archived [results](../../entry-12/results/README.md) and were not solved again.

## Six-gap results

**Calculated.** [summary.csv](summary.csv). [comparison.csv](comparison.csv) retains every gap, well and assembly or event group with its paired counts, and [sample-changes.csv](sample-changes.csv) and [assembly-changes.csv](assembly-changes.csv) give the changes by sample and assembly. The `_change` columns are against `installed_primary` and the `_vs_working` columns against working.

| Calculation | G1 16A RMS, psi | G1 16B RMS, psi | G2 16A bias, kW | G2 16B bias, kW | G3 16A RMS, °C | G4 RMS, °C | G5 return bias, °C | G6 regular bias, °C | G6 trial bias, °C |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Working | 1214.61 | 432.42 | -283.66 | -225.25 | 5.94 | 34.86 | -4.63 | 3.14 | 9.54 |
| `installed_primary` (abrupt) | 556.82 | 129.42 | -40.75 | -36.35 | 5.72 | 34.83 | -3.50 | 6.95 | 13.13 |
| `installed_no_local` | 1476.99 | 450.75 | -359.27 | -238.59 | 6.79 | 34.87 | -4.99 | 2.97 | 9.20 |
| `tapered_primary`, 11.5° | 1228.41 | 331.56 | -287.53 | -190.66 | 6.00 | 34.86 | -4.65 | 3.82 | 10.17 |
| `tapered_long`, 6.3° | 1324.28 | 381.83 | -315.45 | -208.14 | 6.28 | 34.86 | -4.78 | 3.47 | 9.83 |
| `tapered_steep`, 30° | 908.41 | 157.84 | -189.39 | -129.23 | 5.34 | 34.85 | -4.19 | 5.07 | 11.34 |
| `tapered_pin_length`, 11.5° | 1362.94 | 368.79 | -326.89 | -203.19 | 6.38 | 34.86 | -4.84 | 3.58 | 9.95 |

## G1 by assembly

**Calculated biases, psi.** The field `candidate_bias` in [comparison.csv](comparison.csv), selected by `gap=G1` and `well`.

### 16B motorless assemblies

| Calculation | BHA 12 | BHA 13 | BHA 15 | BHA 16 |
| --- | --- | --- | --- | --- |
| Working | -441.62 | -400.45 | -394.02 | -487.15 |
| `installed_primary` (abrupt) | +15.10 | +120.59 | +179.88 | +140.98 |
| `installed_no_local` | -454.42 | -414.74 | -410.67 | -515.31 |
| `tapered_primary`, 11.5° | -355.97 | -301.67 | -285.17 | -375.08 |
| `tapered_long`, 6.3° | -398.15 | -349.67 | -338.03 | -433.71 |
| `tapered_steep`, 30° | -207.99 | -133.29 | -99.74 | -169.36 |
| `tapered_pin_length`, 11.5° | -388.14 | -339.16 | -326.40 | -414.50 |

### 16A

| Calculation | BHA 18 | BHA 23 | BHA 30 | BHA 34 | BHA 35r1 | BHA 35r2 | BHA 38 | BHA 39 | BHA 42 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Working | -1211.64 | -1478.35 | -1049.67 | -1081.08 | -1271.18 | -1169.57 | -700.46 | -571.47 | -1884.73 |
| `installed_primary` (abrupt) | -730.65 | -818.08 | -319.17 | -253.31 | -254.00 | -173.15 | +389.61 | +609.96 | -896.08 |
| `installed_no_local` | -1359.16 | -1678.34 | -1270.26 | -1332.51 | -1601.09 | -1492.87 | -1054.18 | -939.71 | -2189.45 |
| `tapered_primary`, 11.5° | -1216.10 | -1483.20 | -1054.96 | -1088.47 | -1296.78 | -1194.81 | -728.26 | -590.25 | -1901.70 |
| `tapered_long`, 6.3° | -1271.24 | -1558.72 | -1138.48 | -1183.22 | -1415.00 | -1310.63 | -854.96 | -726.24 | -2015.77 |
| `tapered_steep`, 30° | -1022.64 | -1218.20 | -761.87 | -755.87 | -881.68 | -788.13 | -283.33 | -112.62 | -1501.26 |
| `tapered_pin_length`, 11.5° | -1297.10 | -1596.32 | -1180.06 | -1228.52 | -1452.52 | -1347.24 | -895.29 | -781.85 | -2061.14 |

## Secondary trip slopes

**Calculated measured/modelled ratios.** [secondary/slopes.csv](secondary/slopes.csv), column `slope_ratio`. Regular pipe is added on every group except EOW 19, which adds insulated pipe. These are secondary diagnostics and do not affect the recommendation.

| Calculation | EOW 17, 500 gpm | EOW 19, 600 gpm (insulated) | EOW 20, 600 gpm | EOW 27, 400 gpm | EOW 27, 600 gpm | EOW 38, 600 gpm |
| --- | --- | --- | --- | --- | --- | --- |
| Working | 1.45 | 0.97 | 1.57 | 1.82 | 1.91 | 1.86 |
| `installed_primary` (abrupt) | 0.57 | 0.95 | 0.49 | 0.60 | 0.58 | 0.61 |
| `installed_no_local` | 1.54 | 1.42 | 1.76 | 1.97 | 2.30 | 2.07 |
| `tapered_primary`, 11.5° | 1.13 | 0.96 | 1.12 | 1.30 | 1.39 | 1.35 |
| `tapered_long`, 6.3° | 1.27 | 0.96 | 1.30 | 1.50 | 1.64 | 1.56 |
| `tapered_steep`, 30° | 0.81 | 0.95 | 0.74 | 0.89 | 0.90 | 0.91 |
| `tapered_pin_length`, 11.5° | 1.23 | 0.96 | 1.25 | 1.46 | 1.51 | 1.49 |

## Findings

**Calculated joint-loss fraction.** At the sourced angle of 11.5° the bore local loss of one ordinary joint is 20.1% of the abrupt value. On the five regular-pipe trip groups the modelled slope fraction of `tapered_primary`, which also includes the retained abrupt annulus loss, is 21.7–22.6%. Entry 12's bound is 29.7–44.8%, so the sourced angle lies below it on every group. The unsourced 30° sensitivity lies above it, at 53.0–53.5%. Columns come from [secondary/slopes.csv](secondary/slopes.csv); slopes are in psi per 1000 ft.

| EOW, flow | Measured slope ± 95% | `tapered_primary` slope ± 95% | Entry 12 bound | `tapered_long` | `tapered_primary` | `tapered_pin_length` | `tapered_steep` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 17, 500 gpm | 84.2 ± 28.2 | 74.8 ± 54.9 | 0.318 | 0.128 | 0.217 | 0.152 | 0.530 |
| 20, 600 gpm | 74.5 ± 12.6 | 66.7 ± 6.0 | 0.297 | 0.137 | 0.225 | 0.162 | 0.534 |
| 27, 400 gpm | 40.6 ± 6.4 | 31.2 ± 2.4 | 0.425 | 0.138 | 0.226 | 0.154 | 0.535 |
| 27, 600 gpm | 114.0 ± 87.5 | 82.1 ± 40.5 | 0.443 | 0.136 | 0.224 | 0.177 | 0.533 |
| 38, 600 gpm | 100.3 ± 12.8 | 74.5 ± 7.8 | 0.448 | 0.137 | 0.225 | 0.162 | 0.534 |

**Calculated slope ratios.** Measured/modelled regular-pipe ratios are 1.12–1.39 under `tapered_primary`, against 0.49–0.61 under `installed_primary`, 1.54–2.30 under `installed_no_local` and 1.45–1.91 for working. A ratio above one means that the modelled rise with added pipe is smaller than measured. The measured and modelled 95% intervals in the table overlap on EOW 17 at 500 gpm, EOW 20 at 600 gpm and EOW 27 at 600 gpm and are separate on EOW 27 at 400 gpm and EOW 38 at 600 gpm, so the shortfall is resolved on those two groups only. EOW 19 adds insulated pipe, retains EIS connections and moves little in every variant.

**Calculated G6 change.** Against `installed_primary`, `tapered_primary` changes the G6 regular-pipe bias by -3.12 °C, from +6.95 to +3.82 °C, and the trial bias by -2.96 °C, from +13.13 to +10.17 °C. Against working the changes are +0.68 and +0.63 °C. Of the G6 contrast between `installed_no_local` and `installed_primary`, 21.5% on regular pipe and 24.6% on trial pipe remains.

**Calculated pressure and power.** Against `installed_primary`, G1 assembly-bias RMS rises from 556.82 to 1228.41 psi on 16A and from 129.42 to 331.56 psi on 16B. Against working it is +13.80 psi on 16A and -100.86 psi on 16B. G2 well biases are -287.53 and -190.66 kW, against -40.75 and -36.35 kW under `installed_primary` and -283.66 and -225.25 kW for working.

**Calculated near-surface gap.** All ten primary shallow 16B windows have identical geometry under every variant, and every pressure change is zero. The remaining deficit is 187.75–480.67 psi, about 188–481 psi, as in entry 12. The windows are in [shallow-diagnostic.csv](shallow-diagnostic.csv), columns `candidate_deficit_psi`, `pressure_change_psi` and `geometry_identical`.

**Inferred pressure balance.** The four motorless 16B assemblies now read low by 285.17–375.08 psi at full depth, which is the same order as the near-surface gap. This is consistent with entry 12's finding that the abrupt per-length excess offset missing near-surface losses. It does not establish that those losses account for the full-depth deficit: only EOW 12 appears in both sets, at 226.9–228.2 psi in the shallow windows and 356.0 psi at full depth, at different depths and flows. The 16A deficits are larger, at 590.25–1901.70 psi, and have no shallow comparison.

**Inferred slope shortfall.** The sourced angle and the coefficients as stated give a smaller central per-length rise than the measured slope on all five regular-pipe groups, so a conical treatment at this angle does not by itself reproduce the measured rise, although the intervals resolve the difference on only two groups. The 30° case is not a sourced alternative, and no angle is selected from the bracket that the 11.5° and 30° cases form. The curved published profile, the unsourced step from upset to tool-joint bore, the transfer of the angle to 16B and the application of the correlation to mud are all unresolved.

**Calculated reproduction, and what it tests.** Scored changes reproduce the model-only predictions in 440/440 checks across the 22 declared windows, with the largest difference 3.2e-08 of its declared tolerance, in [prediction-checks.csv](prediction-checks.csv). All 42 modelled trip-slope checks pass in [secondary/prediction-checks.csv](secondary/prediction-checks.csv). The model-only calculation and the score use the same solver on the same inputs, so these checks establish that the score applied the declared treatment; they are not a forecast of an independent result. The forecast that could differ is the interpolation of entry 12's scores given in the declaration, whose largest difference from the score is 0.10 °C.

| Variant | G5 expected | G5 scored | G6 regular expected | G6 regular scored | G6 trial expected | G6 trial scored |
| --- | --- | --- | --- | --- | --- | --- |
| `tapered_primary`, 11.5° | -4.65 | -4.65 | +3.86 | +3.82 | +10.08 | +10.17 |
| `tapered_long`, 6.3° | -4.79 | -4.78 | +3.51 | +3.47 | +9.73 | +9.83 |
| `tapered_steep`, 30° | -4.19 | -4.19 | +5.09 | +5.07 | +11.29 | +11.34 |

## Coverage

**Calculated.** Each variant retains all 467 circulation samples. The two originally unavailable run-in events, `23-off006` and `35r2-off008`, remain unavailable.

| Calculation | Circulation rows | Failed circulation | Failed available run-in | Originally unavailable run-in | Energy flags |
| --- | --- | --- | --- | --- | --- |
| Working | 467 | 0 | 0 | 2 | 0 |
| `tapered_primary`, 11.5° | 467 | 0 | 0 | 2 | 0 |
| `tapered_long`, 6.3° | 467 | 0 | 0 | 2 | 0 |
| `tapered_steep`, 30° | 467 | 0 | 0 | 2 | 0 |
| `tapered_pin_length`, 11.5° | 467 | 0 | 0 | 2 | 0 |

## Recommendation

**Inferred recommendation under the declared rule.** Recommend `tapered_primary` as the joint treatment for the working calculation. The scored changes reproduce the model-only predictions within 1 psi, 0.1 °C and 0.1% of power, paired coverage is retained, and the angle lies within the formula branch to 45°. The rule applies whatever the direction of the score change, and the direction is mixed. Against `installed_primary`, G1, G2, G3 and G5 are worse and G6 is better. Against working, G1 and G2 are better on 16B, G1 and G2 are slightly worse on 16A, and G6 is slightly worse. The rule's reproduction test is a test of implementation, as stated above. Its range test is limited: no numerical Reynolds range is stated in the accessible sources, the Crane formulas were checked through secondary statements, and the angle is extended beyond the published bore span and transferred to 16B. Adoption of entry 12's geometry and of this treatment remains Liam's decision as maintainer. Package defaults and golden files are unchanged. The full check list is in [decision.json](decision.json).

## Reproduction and storage

**Calculated archive.** Complete per-sample score outputs are external. [bulk-manifest.json](../bulk-manifest.json) records their hashes, sizes and rebuild commands, and the child manifests distinguish committed results from rebuildable files. Input and code hashes are recorded in the final [entry manifest](../manifest.json).
