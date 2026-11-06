# Entry 14 amendment: results with the corrected tool assignment

**Calculated scope.** Bias is model minus observation, on the same frozen samples and gap definitions as entries 12, 13 and 14. Declaration commit `facf5897aba844e0858a4da01f2feaf270969aae`. All 467 circulation samples and all available run-in events converged, with no energy flags. The original archive is unchanged.

**Calculated reproduction, and what it tests.** All 2,112 per-sample checks pass within 1 psi, 0.1 °C and 0.1% of power, and the largest difference is 3.6e-13 of its tolerance. Eleven frozen groups moved from the original entry 14, all on 16B: G1 on four assemblies, G2, the regular-pipe G6 and G6 on five assemblies. These are the groups the amendment predicted, and each moved by its predicted amount. The model-only calculation and the score use the same solver on the same inputs, so this tests the implementation.

## Six gaps

| Measure | `tapered_primary` | Original entry 14 | Expected | Amended entry 14 | Direction from the original |
| --- | --- | --- | --- | --- | --- |
| G1 16A RMS, psi | 1228.41 | 1030.36 | 1030.36 | 1030.36 | unchanged |
| G1 16B RMS, psi | 331.56 | 240.17 | 60.11 | 60.11 | lower error |
| G2 16A bias, kW | -287.53 | -229.95 | -229.95 | -229.95 | unchanged |
| G2 16B bias, kW | -190.66 | -143.27 | -120.47 | -120.47 | smaller deficit |
| G3 16A RMS, °C | 6.00 | 5.11 | 5.11 | 5.11 | unchanged |
| G4 RMS, °C | 34.86 | 34.83 | 34.83 | 34.83 | unchanged |
| G5 return bias, °C | -4.65 | -4.41 | -4.41 | -4.41 | unchanged |
| G6 regular bias, °C | 3.82 | 5.25 | +6.82 | 6.82 | larger warm bias |
| G6 trial bias, °C | 10.17 | 12.55 | +12.55 | 12.55 | unchanged |

**Calculated direction.** Pump pressure and hydraulic power on 16B move toward the measurements, and the 16B regular-pipe temperature bias, already warm, grows from +5.25 to +6.82 °C. Every 16A measure, G4, the 16B trial bias and the trip slopes are unchanged from the original entry 14.

**Inferred limit.** The low G1 16B value uses the wells and the generic figures this entry already used, and the correction was found after the original score had been seen. It tests no unseen well.

### G1 on the motorless 16B assemblies

| Assembly | `tapered_primary`, psi | Original entry 14, psi | Amended entry 14, psi | Predicted change from the original, psi | Scored change, psi |
| --- | --- | --- | --- | --- | --- |
| 12 | -355.97 | -263.49 | -74.11 | +189.38 | +189.38 |
| 13 | -301.67 | -210.27 | -23.09 | +187.18 | +187.18 |
| 15 | -285.17 | -193.62 | -6.09 | +187.54 | +187.54 |
| 16 | -375.08 | -282.13 | -91.61 | +190.53 | +190.53 |

### G6 on the 16B HALO assemblies

| Measure | Samples | `tapered_primary`, °C | Original entry 14, °C | Amended entry 14, °C | Predicted change from the original, °C | Scored change, °C |
| --- | --- | --- | --- | --- | --- | --- |
| Independent regular pipe | 59 | +3.82 | +5.25 | +6.82 | +1.57 | +1.57 |
| EOW 11 | 4 | -4.92 | -4.15 | -2.56 | +1.59 | +1.59 |
| EOW 12 | 12 | -2.53 | -1.73 | -0.11 | +1.63 | +1.63 |
| EOW 13 | 14 | -1.44 | -0.60 | +1.14 | +1.74 | +1.74 |
| EOW 15 | 4 | +5.38 | +6.31 | +8.24 | +1.93 | +1.93 |
| EOW 16 | 15 | +11.70 | +12.83 | +15.14 | +2.32 | +2.32 |

**Calculated.** EOW 11, 12 and 13 now lie between -2.56 and +1.14 °C. EOW 15 and 16, the deepest of the five, read warmer, at +8.24 and +15.14 °C.

## Shallow windows

**Calculated.** The gap is measured minus modelled standpipe pressure, and "accounted" is the rise that the corrected allowances add to `tapered_primary`. "Motor" comes from the assembly's BHA sheet.

| Window | Assembly | Motor | Flow, US gal/min | Measured, psi | Before, psi | After, psi | Gap before, psi | Accounted, psi | Gap after, psi | Part accounted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 16B-01342 | 20 | yes | 216 | 218.2 | 30.5 | 55.1 | 187.8 | 24.7 | 163.1 | 13% |
| 16B-01343 | 20 | yes | 222 | 224.8 | 32.1 | 58.1 | 192.7 | 26.0 | 166.7 | 13% |
| 16B-03263 | 38 | yes | 237 | 293.1 | 44.1 | 73.6 | 249.0 | 29.5 | 219.6 | 12% |
| 16B-03262 | 38 | yes | 238 | 289.0 | 44.3 | 73.9 | 244.7 | 29.6 | 215.1 | 12% |
| 16B-03261 | 38 | yes | 423 | 538.6 | 136.2 | 230.2 | 402.5 | 94.0 | 308.5 | 23% |
| 16B-01812 | 27 | yes | 492 | 668.8 | 188.1 | 315.4 | 480.7 | 127.3 | 353.4 | 26% |
| 16B-00464 | 12 | no | 572 | 592.7 | 365.8 | 617.4 | 226.9 | 251.6 | -24.7 | 111% |
| 16B-00456 | 11 | yes | 572 | 649.4 | 416.0 | 671.0 | 233.5 | 255.0 | -21.5 | 109% |
| 16B-00465 | 12 | no | 572 | 594.0 | 365.8 | 617.9 | 228.2 | 252.1 | -23.9 | 110% |
| 16B-00457 | 11 | yes | 573 | 649.4 | 416.8 | 672.5 | 232.6 | 255.8 | -23.1 | 110% |

**Calculated low flow, still unexplained.** At 216–238 US gal/min, in four windows of EOW 20 and 38, the measured excess over the model was 188–249 psi. The allowances account for 25–30 psi of it, which is 12–13%, and 163–220 psi remains. These windows do not change in the amendment.

**Calculated high flow, still partly unexplained.** At 423–492 US gal/min, in two windows of EOW 27 and 38, the excess was 402–481 psi. The allowances account for 94–127 psi, which is 23–26%, and 308–353 psi remains. These windows also do not change. At 572–573 US gal/min, in four windows of EOW 11 and 12, the excess was 227–233 psi. The allowances add 252–256 psi, which is 109–111% of it, so the model reads 22–25 psi above the measurement.

**Inferred.** The closure on EOW 11 and 12 is a sum of generic figures for tools that are not HALO's own, and the 6¾-in sources span 87.0–293.9 psi for a pulser and 53.6–130 psi for a rotary steerable tool at 600 US gal/min. It shows that generic figures for the printed tools are large enough to account for the gap at this flow. It does not establish HALO's loss. The earlier inference from EOW 12, that a motor loss could not be the whole gap because 144–145 psi remained with no motor, depended on the missing pulser and is withdrawn. Every window with a remaining gap is on an assembly with a motor, but EOW 11 also has a motor and has no remaining gap at 572 US gal/min. The windows at low flow all have motors and the windows without a motor all have a flow near 572 US gal/min, so these ten windows cannot separate flow from assembly. The source of the remainder is unknown, and no term is added for it.

## Trip slopes

**Calculated.** Slopes are in psi per 1000 ft, and every value equals the original entry 14 value, as declared. EOW 19 adds insulated pipe.

| Group | Measured slope ± 95% | Modelled before | Modelled after | Ratio before | Ratio after |
| --- | --- | --- | --- | --- | --- |
| EOW 17, 500 gpm | 84.2 ± 28.2 | 74.8 | 81.3 | 1.13 | 1.03 |
| EOW 19, 600 gpm (insulated) | 47.4 ± 16.9 | 49.5 | 50.1 | 0.96 | 0.95 |
| EOW 20, 600 gpm | 74.5 ± 12.6 | 66.7 | 65.9 | 1.12 | 1.13 |
| EOW 27, 400 gpm | 40.6 ± 6.4 | 31.2 | 30.5 | 1.30 | 1.33 |
| EOW 27, 600 gpm | 114.0 ± 87.5 | 82.1 | 88.7 | 1.39 | 1.29 |
| EOW 38, 600 gpm | 100.3 ± 12.8 | 74.5 | 76.0 | 1.35 | 1.32 |

## G4

**Calculated.** The run-in peak error RMS remains 34.83 °C, as declared, since G4 uses only 16A.
