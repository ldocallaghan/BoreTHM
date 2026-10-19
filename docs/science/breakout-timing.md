# Breakout timing

When the bit exposes new rock, the rock a few centimetres behind the wall is still at formation temperature. The drilling fluid starts to cool it at once, and cooling relieves the compressive hoop stress that causes breakouts. Whether that cooling helps depends on timing. If breakouts form as soon as the rock is exposed, the drilling fluid must support the wall as if it were uncooled. If they take longer to form than cooling takes to reach the rock where they start, cooling lowers the fluid weight needed.

Heat diffusion sets a timescale for cooling. With a thermal diffusivity of 0.7 to 1.5 × 10⁻⁶ m²/s for granite, the characteristic time d²/α over a distance of 2 to 3 cm is roughly 5 to 20 minutes. The time to stabilise the wall also depends on how much cooling the wall needs and how cold the fluid is at that depth. BoreTHM calculates the temperature behind the wall and its effect on the stability criterion. The [physical-model guide](models.md#borehole-stability) explains the skin heuristic used in that calculation.

<!-- timing-overview:start -->

The failure-delay experiment, lever L7, assumes breakouts form a set time after exposure. With a one-hour delay at Soultz, the target drilling requirement in the most demanding case falls from 1.31 to 1.18 SG-equivalent, and the whole-hole drilling window opens: without the delay, the fluid needed at the bottom would fracture the rock below the casing shoe. At United Downs the target requirement falls from 1.27 to 1.14 SG-equivalent. The fixed scan places the opening bracket at 15–20 minutes at Soultz and 10–15 minutes at United Downs.

<!-- timing-overview:end -->

<!-- timing-failures:start -->

The complete programme remains NO-GO at both sites with and without the delay because the trip-fluid windows remain closed and tool-temperature limits are exceeded. With a one-hour delay, the best attempted run-in tool peaks are 201.2 °C at Soultz and 210.3 °C at United Downs, against the 200 °C limit. Without a delay, United Downs also exceeds the limit while drilling, at 205.7 °C.

<!-- timing-failures:end -->

The studies reviewed in this project provide no measurement of breakout formation time in hot granite. These results show how much the drilling-window verdict depends on it. They give no evidence that breakouts take an hour to form. A repeat image log taken soon after drilling and again later in a hot granite well would test the assumption. The [observational discussion](models.md#wall-reheating-and-thermal-stress) distinguishes the sediment breakout observations from the open question in hot crystalline rock.

## Paired results

Each delay is a coupled programme evaluation, with the fluid and circulation iterated together. Each programme's thermal and hydraulic solution is shared across its stress and strength cases. `drill_SG` is the target drilling-fluid requirement, including connection checks, expressed as SG-equivalent at the target. `drill_rho_surface` is the matching surface density at 20 °C. The target full-cycle verdict excludes separate whole-hole and tool checks.

The whole-hole window combines every evaluated depth, state and case. Its `lo` and `hi` values are surface densities; dividing by 1,000 kg/m³ gives surface SG at 20 °C. A closed window has no valid fluid prescription. Where cases share the same bound, the saved result names the first case.

### Soultz

<!-- target-soultz:start -->

Target depth: 10700.000 m MD. Complete programme verdict at both delays: **NO-GO**.

<!-- target-soultz:end -->

[Zero-delay JSON](../../results/v1.3.6/breakout-timing/soultz-0min.json) and [one-hour JSON](../../results/v1.3.6/breakout-timing/soultz-60min.json) contain the settings and calculation versions.

<!-- paired-soultz:start -->

| Case | UCS, MPa | drill_SG, 0 h, target SG-equivalent | drill_SG, 1 h, target SG-equivalent | drill_rho_surface, 0 h, kg/m³ at 20 °C | drill_rho_surface, 1 h, kg/m³ at 20 °C | Target drilling verdict, 0 h → 1 h | Target full-cycle verdict, 0 h → 1 h |
|---|---:|---:|---:|---:|---:|---|---|
| SHmax lower bound (0.90 Sv), lab UCS 100 | 100 | 1.230037 | 1.092514 | 1296.418 | 1154.634 | CONDITIONAL → CONDITIONAL | CONDITIONAL → CONDITIONAL |
| SHmax lower bound (0.90 Sv), lab UCS 115 | 115 | 1.209457 | 1.069089 | 1275.764 | 1130.973 | CONDITIONAL → CONDITIONAL | CONDITIONAL → CONDITIONAL |
| SHmax lower bound (0.90 Sv), lab UCS 130 | 130 | 1.188878 | 1.045665 | 1255.089 | 1107.278 | CONDITIONAL → CONDITIONAL | CONDITIONAL → CONDITIONAL |
| SHmax mid-range, lab UCS 100 | 100 | 1.271454 | 1.133931 | 1337.918 | 1196.394 | CONDITIONAL → CONDITIONAL | CONDITIONAL → CONDITIONAL |
| SHmax mid-range, lab UCS 115 | 115 | 1.250875 | 1.110507 | 1317.308 | 1172.788 | CONDITIONAL → CONDITIONAL | CONDITIONAL → CONDITIONAL |
| SHmax mid-range, lab UCS 130 | 130 | 1.230296 | 1.087083 | 1296.678 | 1149.151 | CONDITIONAL → CONDITIONAL | CONDITIONAL → CONDITIONAL |
| SHmax upper bound (1.05 Sv), lab UCS 100 | 100 | 1.312872 | 1.175349 | 1379.333 | 1238.058 | NO-GO → CONDITIONAL | NO-GO → NO-GO |
| SHmax upper bound (1.05 Sv), lab UCS 115 | 115 | 1.292293 | 1.151925 | 1358.765 | 1214.506 | CONDITIONAL → CONDITIONAL | CONDITIONAL → CONDITIONAL |
| SHmax upper bound (1.05 Sv), lab UCS 130 | 130 | 1.271714 | 1.128501 | 1338.177 | 1190.924 | CONDITIONAL → CONDITIONAL | CONDITIONAL → CONDITIONAL |

<!-- paired-soultz:end -->

<!-- windows-soultz:start -->

| Delay, h | Window | lo / 1000, surface SG at 20 °C | Lower bound: state; case; depth, m MD | hi / 1000, surface SG at 20 °C | Upper bound: state; case; depth, m MD | Open |
|---:|---|---:|---|---:|---|---|
| 0 | drilling_fluid | 1.378925 | connection; SHmax upper bound (1.05 Sv), lab UCS 100; 10700.00 | 1.312559 | drilling; SHmax lower bound (0.90 Sv), lab UCS 100; 4000.00 | False |
| 0 | trip_fluid | 1.443624 | trip; SHmax upper bound (1.05 Sv), lab UCS 100; 10700.00 | 1.364611 | trip; SHmax lower bound (0.90 Sv), lab UCS 100; 4000.00 | False |
| 1 | drilling_fluid | 1.238763 | connection; SHmax upper bound (1.05 Sv), lab UCS 100; 10550.00 | 1.304633 | drilling; SHmax lower bound (0.90 Sv), lab UCS 100; 4000.00 | True |
| 1 | trip_fluid | 1.440962 | trip; SHmax upper bound (1.05 Sv), lab UCS 100; 10700.00 | 1.363156 | trip; SHmax lower bound (0.90 Sv), lab UCS 100; 4000.00 | False |

<!-- windows-soultz:end -->

The failing checks, with their quantities and locations, are recorded in the [zero-delay report](../../results/v1.3.6/breakout-timing/soultz-0min.md#failing-checks) and [one-hour report](../../results/v1.3.6/breakout-timing/soultz-60min.md#failing-checks). The saved best attempted run-in peak has no exported depth; its reported practice peak has a separate depth. Coating qualification remains INDETERMINATE.

### United Downs

<!-- target-united-downs:start -->

Target depth: 12857.143 m MD. Complete programme verdict at both delays: **NO-GO**.

<!-- target-united-downs:end -->

[Zero-delay JSON](../../results/v1.3.6/breakout-timing/united-downs-0min.json) and [one-hour JSON](../../results/v1.3.6/breakout-timing/united-downs-60min.json) contain the settings and calculation versions.

<!-- paired-united-downs:start -->

| Case | UCS, MPa | drill_SG, 0 h, target SG-equivalent | drill_SG, 1 h, target SG-equivalent | drill_rho_surface, 0 h, kg/m³ at 20 °C | drill_rho_surface, 1 h, kg/m³ at 20 °C | Target drilling verdict, 0 h → 1 h | Target full-cycle verdict, 0 h → 1 h |
|---|---:|---:|---:|---:|---:|---|---|
| Reinecker et al. (2021), intact, 0 K | 203 | 1.169343 | 1.028780 | 1234.369 | 1089.641 | CONDITIONAL → CONDITIONAL | CONDITIONAL → CONDITIONAL |
| Reinecker et al. (2021), intact, 40 K | 172 | 1.204859 | 1.069222 | 1269.879 | 1130.358 | CONDITIONAL → CONDITIONAL | CONDITIONAL → CONDITIONAL |
| Reinecker et al. (2021), weak zones, 0 K | 147 | 1.233501 | 1.101835 | 1298.465 | 1163.119 | NO-GO → CONDITIONAL | NO-GO → CONDITIONAL |
| Reinecker et al. (2021), weak zones, 40 K | 118 | 1.266726 | 1.139667 | 1331.571 | 1201.042 | NO-GO → CONDITIONAL | NO-GO → NO-GO |

<!-- paired-united-downs:end -->

<!-- windows-united-downs:start -->

| Delay, h | Window | lo / 1000, surface SG at 20 °C | Lower bound: state; case; depth, m MD | hi / 1000, surface SG at 20 °C | Upper bound: state; case; depth, m MD | Open |
|---:|---|---:|---|---:|---|---|
| 0 | drilling_fluid | 1.331318 | connection; Reinecker et al. (2021), weak zones, 40 K; 12857.14 | 1.285186 | drilling; Reinecker et al. (2021), intact, 0 K; 12857.14 | False |
| 0 | trip_fluid | 1.401337 | trip; Reinecker et al. (2021), weak zones, 40 K; 12857.14 | 1.365025 | trip; Reinecker et al. (2021), intact, 0 K; 12857.14 | False |
| 1 | drilling_fluid | 1.201990 | connection; Reinecker et al. (2021), weak zones, 40 K; 12707.14 | 1.288498 | drilling; Reinecker et al. (2021), intact, 0 K; 12857.14 | True |
| 1 | trip_fluid | 1.398845 | trip; Reinecker et al. (2021), weak zones, 40 K; 12857.14 | 1.361258 | trip; Reinecker et al. (2021), intact, 0 K; 12857.14 | False |

<!-- windows-united-downs:end -->

The failing checks, with their quantities and locations, are recorded in the [zero-delay report](../../results/v1.3.6/breakout-timing/united-downs-0min.md#failing-checks) and [one-hour report](../../results/v1.3.6/breakout-timing/united-downs-60min.md#failing-checks). The saved best attempted run-in peak has no exported depth; its reported practice peak has a separate depth. Coating qualification remains INDETERMINATE.

## Delay scan

The critical delay is the shortest delay in the fixed scan at which the whole-hole drilling window is open, with its preceding closed sample. No value inside the bracket is interpolated, and the grid is not refined. This criterion concerns the drilling-fluid window. Every complete programme in the scan remains NO-GO.

<!-- scan-summary:start -->

| Site | Last closed sample, min | First open sample, min | Scan wall time, s |
|---|---:|---:|---:|
| Soultz | 15 | 20 | 517.4 |
| United Downs | 10 | 15 | 654.2 |

<!-- scan-summary:end -->

Each scan reused the paired runs at its zero-delay and one-hour points. Its JSON records the fresh-run count and elapsed time. The [Soultz scan](../../results/v1.3.6/breakout-timing/scan-soultz.json) and [United Downs scan](../../results/v1.3.6/breakout-timing/scan-united-downs.json) include the evidence-file checksums.

<!-- scan-table:start -->

| Site | Delay, min | lo / 1000, surface SG at 20 °C | hi / 1000, surface SG at 20 °C | Drilling window open | drill_SG, SG-equivalent at target |
|---|---:|---:|---:|---|---:|
| Soultz | 0 | 1.378925 | 1.312559 | False | 1.312872 |
| Soultz | 5 | 1.378925 | 1.312559 | False | 1.312872 |
| Soultz | 10 | 1.361320 | 1.313039 | False | 1.295916 |
| Soultz | 15 | 1.326528 | 1.313998 | False | 1.261815 |
| Soultz | 20 | 1.303416 | 1.314622 | True | 1.239169 |
| Soultz | 30 | 1.275969 | 1.314257 | True | 1.211735 |
| Soultz | 45 | 1.252765 | 1.304382 | True | 1.189041 |
| Soultz | 60 | 1.238763 | 1.304633 | True | 1.175349 |
| Soultz | 90 | 1.221937 | 1.304937 | True | 1.158881 |
| Soultz | 120 | 1.211755 | 1.305123 | True | 1.148904 |
| United Downs | 0 | 1.331318 | 1.285186 | False | 1.266726 |
| United Downs | 5 | 1.331318 | 1.285186 | False | 1.266726 |
| United Downs | 10 | 1.311613 | 1.285694 | False | 1.246006 |
| United Downs | 15 | 1.277113 | 1.286534 | True | 1.212521 |
| United Downs | 20 | 1.256425 | 1.287063 | True | 1.192516 |
| United Downs | 30 | 1.232512 | 1.287685 | True | 1.169358 |
| United Downs | 45 | 1.213353 | 1.288193 | True | 1.150741 |
| United Downs | 60 | 1.201990 | 1.288498 | True | 1.139667 |
| United Downs | 90 | 1.188436 | 1.288862 | True | 1.126464 |
| United Downs | 120 | 1.180277 | 1.289086 | True | 1.118508 |

<!-- scan-table:end -->

The deciding target case is Soultz's SHmax upper bound with lab UCS 100 MPa, and United Downs' weak-zone case with the 40 K strength calibration. The calibration label does not specify a new cooling intervention.

## Reproduce the results

From the repository root, install the locked dependencies and run the reporting tool. For the recorded execution settings, set `OPENBLAS_NUM_THREADS`, `OMP_NUM_THREADS` and `MKL_NUM_THREADS` to one. The JSON files record the Python and library versions.

```sh
python -m pip install -r requirements-lock.txt
python tools/breakout_timing.py --output ../borethm-timing-reproduction
python tools/breakout_timing.py --scan --reuse --output ../borethm-timing-reproduction
```

The commands write a separate reproduction beside the checkout. The recorded release evidence remains in `results/v1.3.6/breakout-timing/`, the tool's default output directory. `--reuse` accepts completed results only when their settings and model/data/runtime fingerprint match. Each new physical run repeats the coupled programme evaluation. The model, inputs and defaults are unchanged from v1.3.5.
