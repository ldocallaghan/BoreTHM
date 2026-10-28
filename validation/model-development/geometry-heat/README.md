# Thermal geometry and hydraulic heat separation

The declared comparison uses all 244 original bit-temperature windows, paired with their surface returns. The 223 additional return-only 16A samples remain in the full scoreboard but are outside this diagnostic. Each temperature change is relative to the approved legacy calculation, in °C. The bit column is the actual bottom-of-bore temperature, including for 16B; the frozen G6 sensor proxy remains separately defined in the scoreboard.

Case A uses legacy thermal geometry and entry-1 heat sources. Case B uses entry-1 thermal geometry and legacy heat sources. `controls.csv` records both matched controls at all 22 median-depth windows. `samples.csv` retains every mixed case and solver outcome. `assemblies.csv` gives equal-sample means. The power scale is added archived in-hole dissipation divided by inlet mass flow and legacy bit heat capacity. It is a single-pass scale, with no general pointwise counterflow bound.

| Well | BHA | Samples | Complete bit | A bit | B bit | Complete return | A return | B return | Power scale |
|---|---|---|---|---|---|---|---|---|---|
| 16A | 18 | 15 | 8.41 | 8.40 | 0.00 | 1.64 | 1.64 | -0.00 | 2.03 |
| 16A | 23 | 13 | 9.86 | 9.85 | 0.00 | 1.67 | 1.67 | -0.00 | 2.19 |
| 16A | 30 | 29 | 12.55 | 12.54 | 0.00 | 1.96 | 1.96 | -0.00 | 2.63 |
| 16A | 34 | 9 | 12.17 | 12.16 | 0.00 | 1.89 | 1.89 | -0.00 | 2.54 |
| 16A | 35r1 | 5 | 14.21 | 14.20 | 0.00 | 2.01 | 2.01 | -0.00 | 2.70 |
| 16A | 35r2 | 4 | 13.98 | 13.97 | 0.00 | 1.90 | 1.90 | -0.00 | 2.61 |
| 16A | 38 | 20 | 15.20 | 15.19 | 0.00 | 1.99 | 1.99 | -0.00 | 2.76 |
| 16A | 39 | 25 | 16.07 | 16.06 | 0.00 | 2.10 | 2.10 | -0.00 | 2.96 |
| 16A | 42 | 15 | 15.71 | 15.70 | 0.00 | 1.71 | 1.71 | -0.00 | 2.60 |
| 16B | 11 | 4 | 1.52 | 1.52 | 0.00 | 0.62 | 0.62 | -0.00 | 0.70 |
| 16B | 12 | 12 | 1.06 | 1.06 | 0.00 | 0.47 | 0.47 | -0.00 | 0.54 |
| 16B | 13 | 14 | 1.76 | 1.76 | 0.00 | 0.40 | 0.40 | -0.00 | 0.52 |
| 16B | 15 | 4 | 2.09 | 2.09 | 0.00 | 0.44 | 0.44 | -0.00 | 0.57 |
| 16B | 16 | 15 | 2.38 | 2.38 | 0.00 | 0.45 | 0.45 | -0.00 | 0.61 |
| 16B | 17 | 14 | 1.95 | 1.95 | 0.00 | 0.40 | 0.40 | 0.00 | 0.56 |
| 16B | 18 | 10 | 0.82 | 0.82 | -0.00 | 0.53 | 0.53 | 0.00 | 0.61 |
| 16B | 19 | 10 | 0.68 | 0.68 | -0.00 | 0.25 | 0.25 | 0.00 | 0.31 |
| 16B | 20 | 11 | 1.31 | 1.31 | -0.00 | 0.20 | 0.20 | -0.00 | 0.31 |
| 16B | 27 | 5 | 2.75 | 2.75 | 0.00 | 0.27 | 0.27 | -0.00 | 0.45 |
| 16B | 3 | 3 | 0.99 | 1.00 | -0.00 | 0.52 | 0.52 | 0.00 | 0.57 |
| 16B | 38 | 5 | 2.72 | 2.71 | 0.00 | 0.24 | 0.24 | -0.00 | 0.42 |
| 16B | 4 | 2 | 0.90 | 0.90 | -0.00 | 0.49 | 0.49 | 0.00 | 0.53 |

Columns come from `assemblies.csv`: `archived_bit_rise_C`, `bit_change_C`, `archived_return_rise_C`, `return_change_C` and `bulk_heating_scale_C`, with A/B rows paired by well and BHA. Complete denotes the original entry-1 calculation before D5. All cases retain 26.7 °C PV reference, film multiplier 1.0 and the cumulative exposure clock.

![Thermal geometry and heat split](thermal-heat-split.png)

The diagnostic composes the original conductance and source functions. Its standalone mesh merges coincident boundaries at 10-nanometre resolution, far below the physical reporting resolution. Matched controls verify the composition at 0.1 °C. `entry1_geometry` preserves the pre-D5 assembly representation for reproduction. No equipment input was selected from these diagnostic results. The equipment correction is declared independently in the [development log](../../../docs/science/model-development.md).
