# Tool-loss allowance comparison results

**Calculated comparisons.** Bias is model minus observation, on the same frozen samples and gap definitions as entries 12 and 13. The reference is entry 13's archived `tapered_primary`. Declaration commit `b75e9abd35211779bf64d9db722ab9c551225b06`. All 467 circulation samples and all available run-in events converged, with no energy flags. Per-sample tables are outside the repository, with their hashes in [`bulk-manifest.json`](../bulk-manifest.json).

## Six gaps

**Calculated.** [summary.csv](summary.csv) and [comparison.csv](comparison.csv). [assembly-changes.csv](assembly-changes.csv) and [sample-changes.csv](sample-changes.csv) give the changes by assembly and sample.

| Measure | `tapered_primary` | Expected | Entry 14 | Direction |
| --- | --- | --- | --- | --- |
| G1 16A RMS, psi | 1228.41 | 1030.36 | 1030.36 | lower error |
| G1 16B RMS, psi | 331.56 | 240.17 | 240.17 | lower error |
| G2 16A bias, kW | -287.53 | -229.95 | -229.95 | smaller deficit |
| G2 16B bias, kW | -190.66 | -143.27 | -143.27 | smaller deficit |
| G3 16A RMS, °C | 6.00 | 5.11 | 5.11 | lower error |
| G4 RMS, °C | 34.86 | within 0.1 of 34.86 | 34.83 | unchanged within 0.03 °C |
| G5 return bias, °C | -4.65 | -4.41 | -4.41 | smaller cold bias |
| G6 regular bias, °C | 3.82 | +5.25 | 5.25 | larger warm bias |
| G6 trial bias, °C | 10.17 | +12.55 | 12.55 | larger warm bias |

The direction is mixed. Pump pressure, hydraulic power, 16A bit temperature and 16A return temperature move toward the measurements on these aggregate measures. The 16B sensor biases, which were already warm, grow. On 16A, the five assemblies with cold bit biases come closer to the measurements, and the four with warm bit biases (23, 30, 34 and 35r1) move further from them.

### G1 on 16A

| Assembly | `tapered_primary`, psi | Entry 14, psi | Change, psi | Predicted, psi |
| --- | --- | --- | --- | --- |
| 18 | -1216.10 | -1046.27 | +169.83 | +169.83 |
| 23 | -1483.20 | -1294.42 | +188.78 | +188.78 |
| 30 | -1054.96 | -873.00 | +181.97 | +181.97 |
| 34 | -1088.47 | -893.42 | +195.05 | +195.05 |
| 35r1 | -1296.78 | -1059.53 | +237.25 | +237.25 |
| 35r2 | -1194.81 | -967.03 | +227.79 | +227.79 |
| 38 | -728.26 | -490.48 | +237.78 | +237.78 |
| 39 | -590.25 | -354.69 | +235.56 | +235.56 |
| 42 | -1901.70 | -1673.35 | +228.35 | +228.35 |

### G1 on the motorless 16B assemblies

| Assembly | `tapered_primary`, psi | Entry 14, psi | Change, psi | Predicted, psi |
| --- | --- | --- | --- | --- |
| 12 | -355.97 | -263.49 | +92.48 | +92.48 |
| 13 | -301.67 | -210.27 | +91.40 | +91.40 |
| 15 | -285.17 | -193.62 | +91.55 | +91.55 |
| 16 | -375.08 | -282.13 | +92.95 | +92.95 |

### G3 on 16A

| Assembly | `tapered_primary`, °C | Entry 14, °C | Change, °C |
| --- | --- | --- | --- |
| 18 | -3.06 | -1.62 | +1.44 |
| 23 | +1.36 | +3.06 | +1.70 |
| 30 | +5.25 | +7.03 | +1.78 |
| 34 | +0.87 | +2.89 | +2.02 |
| 35r1 | +0.30 | +2.99 | +2.69 |
| 35r2 | -3.35 | -0.69 | +2.66 |
| 38 | -3.16 | -0.29 | +2.86 |
| 39 | -4.74 | -1.95 | +2.79 |
| 42 | -15.50 | -12.32 | +3.18 |

## Reproduction of the predictions

**Calculated.** All 2,112 per-sample checks in [prediction-checks.csv](prediction-checks.csv) pass within 1 psi, 0.1 °C and 0.1% of power, and the largest difference is 2.8e-13 of its tolerance. The scoreboard records hydraulic power only on samples with a measured pressure, so 223 return-only samples have four checks and the others five. The model-only calculation and the score use the same solver on the same inputs, so this tests the implementation. It does not test the defaults, and the unseen wells do that.

## Shallow windows

**Calculated.** [shallow-windows.csv](shallow-windows.csv), sorted here by flow. The gap is measured minus modelled standpipe pressure, and "accounted" is the rise that the defaults add.

| Window | Assembly | Flow, US gal/min | Measured, psi | Before, psi | After, psi | Gap before, psi | Accounted, psi | Gap after, psi | Part accounted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 16B-01342 | 20 | 216 | 218.2 | 30.5 | 55.1 | 187.8 | 24.7 | 163.1 | 13% |
| 16B-01343 | 20 | 222 | 224.8 | 32.1 | 58.1 | 192.7 | 26.0 | 166.7 | 13% |
| 16B-03263 | 38 | 237 | 293.1 | 44.1 | 73.6 | 249.0 | 29.5 | 219.6 | 12% |
| 16B-03262 | 38 | 238 | 289.0 | 44.3 | 73.9 | 244.7 | 29.6 | 215.1 | 12% |
| 16B-03261 | 38 | 423 | 538.6 | 136.2 | 230.2 | 402.5 | 94.0 | 308.5 | 23% |
| 16B-01812 | 27 | 492 | 668.8 | 188.1 | 315.4 | 480.7 | 127.3 | 353.4 | 26% |
| 16B-00464 | 12 | 572 | 592.7 | 365.8 | 448.4 | 226.9 | 82.6 | 144.2 | 36% |
| 16B-00456 | 11 | 572 | 649.4 | 416.0 | 499.7 | 233.5 | 83.7 | 149.7 | 36% |
| 16B-00465 | 12 | 572 | 594.0 | 365.8 | 448.6 | 228.2 | 82.8 | 145.4 | 36% |
| 16B-00457 | 11 | 573 | 649.4 | 416.8 | 500.8 | 232.6 | 84.0 | 148.6 | 36% |

**Calculated low-flow result.** At 216–238 US gal/min, in four windows of EOW 20 and 38, the measured excess over the model was 188–249 psi. The defaults account for 25–30 psi of it, which is 12–13%, and 163–220 psi remains. Most of the low-flow gap is unexplained.

**Calculated higher-flow result.** At 423–573 US gal/min, in six windows of EOW 11, 12, 27 and 38, the excess was 227–481 psi. The defaults account for 83–127 psi, which is 23–36%, and 144–353 psi remains.

**Inferred.** The allowances scale close to the square of the flow, so they are small at low flow, and the remaining gap changes much less with flow than the allowances do: on EOW 38 the allowance rises by a factor of 3.2 from 237 to 423 US gal/min, and the remaining gap by a factor of 1.4. A loss that varies little with flow would look like this, and the recorded motor sheets print no-load figures of about 100–300 psi that are not used because no flow is stated. This does not identify the source. EOW 12 has no motor and still has 144–145 psi remaining, so a motor loss cannot be the whole gap. No term is added for it, and it stays open.

## Trip slopes

**Calculated measured/modelled ratios.** [trip-slopes.csv](trip-slopes.csv), in psi per 1000 ft. EOW 19 adds insulated pipe and is labelled. The modelled slopes change only through the flow differences among depth stages, as the declaration states.

| Group | Measured slope ± 95% | Modelled before | Modelled after | Ratio before | Ratio after |
| --- | --- | --- | --- | --- | --- |
| EOW 17, 500 gpm | 84.2 ± 28.2 | 74.8 | 81.3 | 1.13 | 1.03 |
| EOW 19, 600 gpm (insulated) | 47.4 ± 16.9 | 49.5 | 50.1 | 0.96 | 0.95 |
| EOW 20, 600 gpm | 74.5 ± 12.6 | 66.7 | 65.9 | 1.12 | 1.13 |
| EOW 27, 400 gpm | 40.6 ± 6.4 | 31.2 | 30.5 | 1.30 | 1.33 |
| EOW 27, 600 gpm | 114.0 ± 87.5 | 82.1 | 88.7 | 1.39 | 1.29 |
| EOW 38, 600 gpm | 100.3 ± 12.8 | 74.5 | 76.0 | 1.35 | 1.32 |

## G4

**Calculated.** The run-in peak error RMS moves from 34.86 to 34.83 °C, within the declared 0.1 °C.
