# Installed-pipe comparison results

**Calculated comparisons.** All variants use the declared frozen samples and settings. Bias is model minus observation. G1 on 16A compares standpipe pressure with measured standpipe minus raw motor differential; 16B G1 uses the four motorless assemblies. The two wells' G1 RMS values give equal weight to assembly biases. G2 uses the frozen in-hole hydraulic-power definition, including the retained raw motor face source, with surface power excluded. G3 is the 16A bit comparison. G4 retains the original run-in events and initial-state convention. G5 pools the 16A return observations. G6 separates regular and trial pipe on 16B.

## Six-gap results

**Calculated pressure and heat.** [summary.csv](summary.csv), columns `G1_16A_RMS_psi`, `G1_16B_RMS_psi`, `G2_16A_bias_kW`, `G2_16B_bias_kW`. The historical FH row comes unchanged from [entry 10 summary.csv](../../entry-10/results/summary.csv).

| Calculation | G1 16A RMS, psi | G1 16B RMS, psi | G2 16A bias, kW | G2 16B bias, kW |
| --- | --- | --- | --- | --- |
| working | 1214.61 | 432.42 | -283.66 | -225.25 |
| installed_primary | 556.82 | 129.42 | -40.75 | -36.35 |
| installed_abrupt | 556.82 | 129.42 | -40.75 | -36.35 |
| installed_no_local | 1476.99 | 450.75 | -359.27 | -238.59 |
| installed_premium | 556.82 | 51.98 | -40.75 | -72.73 |
| installed_steel | 537.80 | 324.65 | 7.85 | 27.50 |
| entry10_fh | 1214.61 | 152.85 | -283.66 | 20.18 |

**Calculated temperatures.** The same file supplies `G3_16A_RMS_C`, `G4_peak_error_RMS_C`, `G5_16A_return_bias_C`, `G6_regular_bias_C` and `G6_trial_bias_C`.

| Calculation | G3 16A bias RMS, °C | G4 peak-error RMS, °C | G5 return bias, °C | G6 regular bias, °C | G6 trial bias, °C |
| --- | --- | --- | --- | --- | --- |
| working | 5.94 | 34.86 | -4.63 | 3.14 | 9.54 |
| installed_primary | 5.72 | 34.83 | -3.50 | 6.95 | 13.13 |
| installed_abrupt | 5.72 | 34.83 | -3.50 | 6.95 | 13.13 |
| installed_no_local | 6.79 | 34.87 | -4.99 | 2.97 | 9.20 |
| installed_premium | 5.72 | 34.83 | -3.50 | 6.22 | 12.46 |
| installed_steel | 6.53 | 34.82 | -3.29 | 8.94 | 14.84 |
| entry10_fh | 5.94 | 34.86 | -4.63 | 7.12 | 14.37 |

**Calculated direction of effects.** Primary lowers G1 assembly-bias RMS from 1214.61 to 556.82 psi on 16A and from 432.42 to 129.42 psi on 16B. The G2 well biases move from -283.66 to -40.75 kW and from -225.25 to -36.35 kW, respectively. G6 regular-pipe bias increases from +3.14 to +6.95 °C, and trial bias from +9.54 to +13.13 °C. G4 run-in error RMS remains about 34.8 °C. These changes come from the summary columns above. **Inferred limit.** Improved aggregate pressure and power errors leave substantial temperature errors. The residual temperature errors and finished transition profile remain unresolved; the joint-loss contrast below addresses the additional warming.

**Calculated assembly and event coverage.** [comparison.csv](comparison.csv) retains every gap, well and assembly/event group, its paired identifiers and before/after means, biases and errors. [comparison-with-entry10-fh.csv](comparison-with-entry10-fh.csv) adds the corresponding historical FH bias and model mean. [sample-changes.csv](sample-changes.csv) records each frozen sample's pressure, heat and temperature changes; [assembly-changes.csv](assembly-changes.csv) gives assembly means and ranges.

## G1 by assembly

**Calculated biases, psi.** Each value is `bias` in the relevant `results/<variant>/scoreboard.csv`, selected by `gap=G1`, `well` and `group`. The FH reference is `entry-10/results/fh/scoreboard.csv`. Primary and abrupt are identical by the declared source fallback, so they share a display column; both variants remain separate in the archive.

### 16A G1 assembly biases

| Assembly | Working | Entry 10 FH | Primary/abrupt | No local | Premium | Steel |
| --- | --- | --- | --- | --- | --- | --- |
| 18 | -1211.64 | -1211.64 | -730.65 | -1359.16 | -730.65 | -617.24 |
| 23 | -1478.35 | -1478.35 | -818.08 | -1678.34 | -818.08 | -710.38 |
| 30 | -1049.67 | -1049.67 | -319.17 | -1270.26 | -319.17 | -185.43 |
| 34 | -1081.08 | -1081.08 | -253.31 | -1332.51 | -253.31 | -103.01 |
| 35r1 | -1271.18 | -1271.18 | -254.00 | -1601.09 | -254.00 | -16.75 |
| 35r2 | -1169.57 | -1169.57 | -173.15 | -1492.87 | -173.15 | 58.65 |
| 38 | -700.46 | -700.46 | 389.61 | -1054.18 | 389.61 | 644.21 |
| 39 | -571.47 | -571.47 | 609.96 | -939.71 | 609.96 | 839.67 |
| 42 | -1884.73 | -1884.73 | -896.08 | -2189.45 | -896.08 | -740.70 |
### 16B G1 assembly biases

| Assembly | Working | Entry 10 FH | Primary/abrupt | No local | Premium | Steel |
| --- | --- | --- | --- | --- | --- | --- |
| 12 | -441.62 | 35.58 | 15.10 | -454.42 | -74.42 | 193.54 |
| 13 | -400.45 | 144.67 | 120.59 | -414.74 | 17.79 | 300.45 |
| 15 | -394.02 | 207.24 | 179.88 | -410.67 | 66.75 | 370.73 |
| 16 | -487.15 | 168.24 | 140.98 | -515.31 | 22.27 | 395.49 |

## Secondary trip slopes

**Calculated measured/modelled ratios.** [secondary/slopes.csv](secondary/slopes.csv), columns `candidate`, `assembly`, `excursion`, `flow_centre_gpm`, `slope_ratio` and `added_pipe`. A ratio below one means the modelled pressure rise with added length is larger than measured. The FH reference comes from [entry 10 secondary/slopes.csv](../../entry-10/results/secondary/slopes.csv). EOW 19 adds insulated pipe and retains EIS connections in all installed variants; other groups add ordinary pipe. The no-local and global steel sensitivities have their separately declared scope.

| EOW / added pipe | Excursion | Flow, US gpm | Working | Entry 10 FH | Primary/abrupt | No local | Premium | Steel |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 17 / ordinary | 27 | 500 | 1.45 | 0.55 | 0.57 | 1.54 | 0.65 | 0.52 |
| 19 / insulated | 29 | 600 | 0.97 | 0.29 | 0.95 | 1.42 | 0.95 | 0.76 |
| 20 / ordinary | 31 | 600 | 1.57 | 0.48 | 0.49 | 1.76 | 0.57 | 0.45 |
| 27 / ordinary | 40 | 400 | 1.82 | 0.57 | 0.60 | 1.97 | 0.69 | 0.56 |
| 27 / ordinary | 40 | 600 | 1.91 | 0.57 | 0.58 | 2.30 | 0.67 | 0.50 |
| 38 / ordinary | 52 | 600 | 1.86 | 0.59 | 0.61 | 2.07 | 0.70 | 0.55 |

## Pressure compensation and joint-loss bound

**Calculated:** [Installed-primary scoreboard](installed_primary/scoreboard.csv) and [working scoreboard](working/scoreboard.csv), selected by `gap=G1`, `well=16B` and `group`, give the motorless assembly biases below. Bias is model minus measured pressure. Working biases span -487.15 to -394.02 psi; installed-primary biases span +15.10 to +179.88 psi.

| 16B assembly | Working bias, psi | Installed-primary bias, psi |
| --- | --- | --- |
| 12 | -441.62 | +15.10 |
| 13 | -400.45 | +120.59 |
| 15 | -394.02 | +179.88 |
| 16 | -487.15 | +140.98 |

**Calculated:** The installed-primary 16A assembly biases span -896.08 to +609.96 psi in the same scoreboard, selected by `well=16A`. BHA 38 is +389.61 psi and BHA 39 is +609.96 psi.

**Calculated:** [shallow-diagnostic.csv](shallow-diagnostic.csv), columns `bit_depth_ft`, `installed_primary_deficit_psi` and `pressure_change_psi`, gives ten shallow 16B windows at 35.34–370.38 ft. Their partial strings contain no ordinary pipe, and every installed correction is zero. The model still reads low by 187.75–480.67 psi, about 188–481 psi. The four full-depth motorless assembly means now read high by 15.10–179.88 psi.

**Calculated:** In [secondary/slopes.csv](secondary/slopes.csv), regular-pipe measured/modelled slope ratios span 0.4942–0.6104 under `installed_primary`, about 0.49–0.61, and 1.5442–2.2971 under `installed_no_local`, about 1.54–2.30. Thus the abrupt modelled rise is 1.64–2.02 times the measured rise; the no-local rise is 0.44–0.65 times measured. The measured rise lies between them. All five flow groups across four assemblies are retained, including both EOW 27 flow groups.

**Inferred:** The shallow pressure shortfall, positive full-depth biases and excessive per-length rise together indicate that the abrupt joint treatment with the installed 3.0-in bore overstates the loss added with ordinary pipe on 16B. This excess per-length pressure offsets missing near-surface tool and surface losses at full depth. The G1 RMS reduction from 432.42 to 129.42 psi therefore includes compensation between two errors. Improved full-depth G1 does not establish that the abrupt treatment is physically appropriate.

**Calculated bound, never an input:** Approximate each modelled slope as a body-friction baseline plus joint local loss. Use the no-local slope `S_0` as that baseline, the abrupt slope `S_a`, and the unchanged measured slope `S_m`. The fraction `f = (S_m - S_0)/(S_a - S_0)` gives the joint-local-loss share that would match the measured slope under this approximation. All slope columns below are psi per 1000 ft.

| EOW | Excursion | Flow group, US gpm | Measured slope | No-local slope | Abrupt slope | Joint-local-loss fraction |
| --- | --- | --- | --- | --- | --- | --- |
| 17 | 27 | 500 | 84.155 | 54.498 | 147.740 | 0.3181 |
| 20 | 31 | 600 | 74.497 | 42.257 | 150.754 | 0.2972 |
| 27 | 40 | 400 | 40.607 | 20.564 | 67.725 | 0.4250 |
| 27 | 40 | 600 | 113.963 | 49.611 | 194.829 | 0.4431 |
| 38 | 52 | 600 | 100.344 | 48.380 | 164.404 | 0.4479 |

The fractions span 0.2972–0.4479, or 29.7–44.8% of the abrupt contribution. This assumes additive slopes and the same trip groups with their fixed temperature treatment. Other modelled contributions, including distributed restriction friction, are absorbed into the no-local baseline. It is a diagnostic bound, without a measured loss coefficient. It selects no treatment and supplies no model input.

**Calculated:** [summary.csv](summary.csv), columns `G6_regular_bias_C` and `G6_trial_bias_C`, gives:

| Calculation | G6 regular bias, °C | G6 trial bias, °C |
| --- | --- | --- |
| working | +3.14 | +9.54 |
| installed_primary | +6.95 | +13.13 |
| installed_no_local | +2.97 | +9.20 |

Primary warms the regular and trial comparisons by 3.81 and 3.59 °C relative to working. Its contrast with the same installed geometry without joint local losses is 3.98 and 3.93 °C, respectively. The no-local biases remain close to working.

**Inferred:** Nearly all of the extra G6 warming is associated with the joint-local-loss term and its dissipation in this calculation. If the abrupt joint loss is overstated, that additional warming is overstated with it. This concerns the increment from the connection treatment; the earlier temperature biases remain unresolved.

**Inferred source gap:** A sourced transition treatment requires the installed pipe's internal upset diameter and taper length at the weld neck, and the bore length through the made-up tool joint, from the drill-pipe data sheets or manufacturer drawings. No taper angle or loss coefficient is selected from these bounds.


**Calculated prediction reproduction.** 660/660 representative circulation-field checks pass the declared 1-psi, 0.1-°C and 0.1%-power tolerances in [prediction-checks.csv](prediction-checks.csv). 36/36 modelled trip-slope checks pass 1 psi/1000 ft in [secondary/prediction-checks.csv](secondary/prediction-checks.csv). The trip predictions were expressed before scoring as multipliers of the archived working ratio, with no new measured-pressure ratio computed. The scored values retain the original measured slopes and memberships. These are secondary diagnostics and do not select a transition or geometry.

## Coverage and limitations

**Calculated coverage.** Each variant retains all 467 circulation samples. Available and unavailable run-in identities are preserved. The child manifests identify every failed sample/event and every energy flag. Flags do not change solver success.

| Calculation | Circulation rows | Failed circulation | Failed available run-in | Originally unavailable run-in | Energy flags |
| --- | --- | --- | --- | --- | --- |
| working | 467 | 0 | 0 | 2 | 0 |
| installed_primary | 467 | 0 | 0 | 2 | 0 |
| installed_abrupt | 467 | 0 | 0 | 2 | 0 |
| installed_no_local | 467 | 0 | 0 | 2 | 0 |
| installed_premium | 467 | 0 | 0 | 2 | 0 |
| installed_steel | 467 | 0 | 0 | 2 | 0 |

**Measured equipment record and inferred limits.** The ordinary-pipe dimensions are independently supplied by Kevin England, personal communication via John McLennan, November 2026, from the drill pipe data sheets. The declaration gives the complete source tables. The finished upset/weld/tool-joint profile remains unresolved. Restriction lengths are the recorded pin-plus-box tong approximations. The abrupt primary remains a source-gap fallback; score agreement does not establish a physical sharp transition. The zero-local-loss case is an idealised bound. The steel value is transferred from water pipe, with its global extension to insulated pipe explicitly qualified. No source supplies installed tool operating-loss curves.

**Calculated shallow diagnostic.** Entry 9 found 188–483 psi of modelled deficit in ten primary near-surface 16B windows. [shallow-diagnostic.csv](shallow-diagnostic.csv) replays all ten identities at their frozen mass rate and mean inlet/return temperature with working Colebrook and installed-primary geometry. Every partial-string geometry is identical and every installed pressure change is zero. The current remaining deficit is 187.75–480.67 psi; the small difference from the historical range is the retained Colebrook calculation. No circulation solve or coefficient fit is made. The source is [entry 9 near-surface.csv](../../entry-9/results/near-surface.csv); `shallow-manifest.json` records input and code hashes.

| Window | EOW | Bit depth, ft | Measured pressure, psi | Working/primary pressure, psi | Remaining deficit, psi | Installed change, psi |
| --- | --- | --- | --- | --- | --- | --- |
| 16B-00456 | 11 | 370.38 | 649.45 | 415.98 | 233.46 | 0.00 |
| 16B-00457 | 11 | 370.38 | 649.38 | 416.76 | 232.61 | 0.00 |
| 16B-00464 | 12 | 309.12 | 592.68 | 365.81 | 226.87 | 0.00 |
| 16B-00465 | 12 | 309.12 | 594.00 | 365.80 | 228.20 | 0.00 |
| 16B-01342 | 20 | 35.34 | 218.22 | 30.46 | 187.75 | 0.00 |
| 16B-01343 | 20 | 35.34 | 224.83 | 32.10 | 192.73 | 0.00 |
| 16B-01812 | 27 | 335.49 | 668.82 | 188.15 | 480.67 | 0.00 |
| 16B-03261 | 38 | 346.35 | 538.65 | 136.17 | 402.48 | 0.00 |
| 16B-03262 | 38 | 346.35 | 289.01 | 44.31 | 244.70 | 0.00 |
| 16B-03263 | 38 | 346.35 | 293.14 | 44.11 | 249.03 | 0.00 |

**Inferred remaining equipment gap.** The ordinary-pipe correction has no effect on these shallow partial strings. The 16B surface and BHA-tool losses remain unresolved at about 188–481 psi under this fixed-state diagnostic. No operating curve or extra surface allowance is obtained from that residual. The 16A shallow comparison remains unavailable because its recording periods have no shallow trip coverage; the tables above give its evaluated assembly changes.

**Inferred interpretation limit.** The G4 calculation retains the original approximate starting states, and changes can arise through conditioning circulation only. The historical trial-insulation fit remains present. FORGE 16A and 16B are development data. A new source correction or temperature improvement is not independent validation. No 58-32 data is used.

## Recommendation

**Calculated declared checks.** [decision.json](decision.json) records the paired-coverage and prediction checks without using score improvement as an adoption criterion.

**Inferred recommendation.** Recommend installed ordinary-pipe geometry for the working calculation. The recommendation follows the independently sourced geometry and the declared reproduction rule, regardless of score direction. The abrupt treatment is the existing working treatment; the regular-pipe trip slopes show that it overstates per-length loss at the installed 3.0-in bore. It remains the declared unresolved-profile fallback. A later transition treatment requires an applicable sourced internal profile. No roughness or restriction length is fitted. Adoption of the sourced geometry, including whether to adopt before the transition treatment is sourced, remains Liam's decision as maintainer. Nothing is adopted in the package here.

## Reproduction and storage

**Calculated archive.** Complete per-sample score and rotary-application outputs are external. The entry-root [bulk-manifest.json](../bulk-manifest.json) records hashes, sizes and rebuild commands. Compact scoreboard, run-in and comparison results are committed. The child manifests distinguish their committed results from rebuildable bulk files. Rebuild the full scores in an external output directory using the declaration hash in the manifest, then run `compare.py` and the scoring mode of `trip_slopes.py`. `archive_results.py` rebuilds this compact archive. Input and code hashes are recorded in the final entry manifest. The declaration manifest describes the original declaration commit; later result documentation is identified separately. No package default or golden file changes.
