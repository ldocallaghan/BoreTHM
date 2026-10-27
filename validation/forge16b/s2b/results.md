# Motorless FORGE 16B: motorless pressure accounting

## Finding and scope

The unchanged model accounts for 42–49% of the mean measured standpipe pressure on EOW 12, 13, 15 and 16 under the revised S2 mud rule. Resolving the recorded lower-assembly passages adds about 30–37 psi of bore friction; abrupt component transitions add about 24–27 psi. Representative tool joints add about 72–285 psi across the four run means, depending on their declared geometry. The API top-drive surface case adds about 35 psi.

With 29-in representative joint restrictions, abrupt transitions and the API top-drive surface case, mean accounted fractions range from 57% to 79%, leaving mean residuals of 249–532 psi. These are conditional geometric scenarios. The installed joint machining, the surface piping downstream of the pressure tap and the HALO/float/filter operating restrictions remain unresolved. Their unknown losses are not zero. No scenario is selected by its residual and no coefficient is inferred from pressure agreement.

The other historic API surface cases are retained. Applying their most restrictive layout can bring some sample totals above measured pressure, while the run-mean residuals remain positive in the 29-in abrupt scenarios. That layout includes a kelly and is not established for this top-drive rig. The tabulated range is not a confidence interval or an as-built pressure bound. No cause is assigned to the temperature discrepancies.

Forty-five fixed half-hour samples are evaluated under both original and revised mud rules, with equal sample weights. All 90 circulation replays converge and reproduce saved S2 pressure and temperature endpoints exactly. External estimates are post-processing only; they are never supplied to a circulation solve. The [frozen protocol](../comparison_protocol_s2b.md) states the method and source assumptions.

## What the existing model includes

| Requested term | Included treatment | Excluded contribution / separate estimate |
|---|---|---|
| Pipe body friction | Ordinary 5.5-in pipe, 4.670-in bore; midpoint fluid properties per constant-geometry piece | No roughness allowance or joint restriction in this term |
| Tool joints | No separate hydraulic joint term | Both internal and annular replacement-length friction, plus entry/exit losses, are estimated in two catalogue geometries |
| BHA components | HWDP is a distinct segment; lower components are represented by length-weighted bore and OD | Serial recorded bores and ODs replace the aggregate losses in the diagnostic; transition losses are additional; tool-specific mechanisms remain unquantified |
| Bit nozzles | Recorded total nozzle area; local density and mass flow; discharge coefficient 0.95 | No new nozzle adjustment or fitted coefficient |
| Annulus | Concentric clean-fluid friction using recorded hole/casing geometry and aggregate string segments | Joint effects and serial component OD increments are reported separately; eccentricity, rotation and cuttings are not added |
| Surface lines | None | All five historic API connection cases, and zero allowance, are retained as separate scenarios |
| Density-column correction | Signed annulus-minus-bore density integral over TVD | Separate from the six dissipative categories; retained when summing standpipe pressure |

BHA means bottom-hole assembly, including heavy-weight drill pipe (HWDP). Pressure losses are in psi. Standpipe pressure (SPP) is a pressure difference. The raw Pason differential channel is shown as recorded and is not subtracted on these motorless runs. Its negative values prevent interpreting it as a strictly positive motor loss.

## Included terms: revised-mud primary

| EOW | n | Measured SPP | Pipe | HWDP | Lower BHA | Nozzles | Annulus | Density column | Model total |
|---|---|---|---|---|---|---|---|---|---|
| 12 | 12 | 1174.9 | 127.2 | 86.7 | 117.6 | 191.3 | 20.2 | -3.9 | 539.1 |
| 13 | 14 | 1166.0 | 149.3 | 86.9 | 116.9 | 189.3 | 24.1 | -5.0 | 561.5 |
| 15 | 4 | 1189.5 | 163.6 | 86.0 | 115.4 | 191.0 | 27.1 | -5.6 | 577.5 |
| 16 | 15 | 1244.0 | 146.6 | 69.2 | 92.8 | 193.1 | 24.6 | -7.0 | 519.4 |

Tool-joint and surface terms are zero in the included model total. HWDP plus lower BHA gives the requested BHA category. Each sample's original six-term split and signed density correction is in [pressure-samples.csv](pressure-samples.csv); [model-pieces.csv](model-pieces.csv) retains the exact pieces. The [run table](pressure-run-summary.csv) reports both mud versions and per-sample extrema.

## External estimates and source limits

The [recorded assembly inputs](../component_inputs_s1.csv) give the lengths and bores of every lower component and all 30 HWDP joints. The bit's gauge OD would describe a sealed annulus if treated as a solid cylinder; it does not resolve junk-slot flow. The existing aggregate OD is retained over the short bit-body interval only and is labelled in [bha-components.csv](bha-components.csv). No drawing dimension is edited.

[NOV's connection tables](https://www.nov.com/products/gpds-and-eis-connections) give two 5.5-in, 24.7-lb/ft geometries compatible with the recorded FH connection family: EIS 7.000-in OD / 4.000-in ID and GPDS 55 7.250-in OD / 3.500-in ID. The installed machining is unknown. A 29-in effective restriction length is assumed, with 0-in and 58-in sensitivities. The pipe tally on EOW p266 gives 2,378 ft per 75 joints; its use for earlier runs is an explicit transferred input. HWDP joint OD follows each catalogue scenario, with its recorded 3.625-in bore retained; internal machining and centre pads are unresolved. Joint-length body losses are subtracted before replacement losses are added.

The [Modelica Association's documented Idelchik correlations](https://doc.modelica.org/Modelica%204.0.0/Resources/helpOM/Modelica.Fluid.Dissipation.Utilities.SharedDocumentation.PressureLoss.Orifice.dp_suddenChange.html) supply abrupt expansion and contraction coefficients from area ratios. Zero local loss is also retained for gradual-transition scenarios. These correlations describe smooth turbulent Newtonian flow. All revised-mud geometric checks exceed their stated Reynolds-number thresholds, but applying them to Bingham mud and annular changes remains an approximation. Original S1 mud has 3,990 joint and 60 BHA transition rows outside those Reynolds thresholds; their estimates are retained and flagged, not treated as validated predictions.

For surface equipment, API RP 13D (2009), §7.3 equation60/table4, gives P = C rho_ppg (Q_gpm/100)^1.86 psi, with the five C values 1.00, 0.36, 0.22, 0.15 and 0.15. Case5 represents a top-drive system; all are generic complete layouts. No as-built dimensions or exact Pason pressure-tap position were found. Including a complete layout is conditional because part could be upstream of that tap. [API document text](https://studylib.net/doc/27198826/api-recommended-practice-13d-rheology-and-hydraulics-of-o...). The old standard is used for explicit scenarios, not as a claim of current-edition compliance.

API §7.6.2 requires a tool-specific reference pressure-loss coefficient. The [HALO manufacturer sheet](https://scientificdrilling.com/assets/uploads/sites/3/2018/09/SC_TDS_HALO_9.24v3.pdf) identifies an integrated steering assembly and MWD pulser but provides no operating loss curve. Its 20,000-psi hydrostatic rating is not an operating loss. The recorded float and filter subs likewise lack port/open-area data. A full numerical estimate of these terms cannot be obtained from body IDs alone without an unsupported coefficient. Their open-passage friction is estimated above, and the following dynamic heads give pressure per unit *additional* local-loss coefficient K at the recorded bore. Actual K and additional loss remain blank in the evidence, not set to zero. The motor contribution is zero because no motor is documented.

| EOW | HALO RSS psi per K | Black box psi per K | Float sub psi per K | Filter sub psi per K |
|---|---|---|---|---|
| 12 | 25.52 | 15.93 | 5.98 | 3.66 |
| 13 | 25.26 | 15.77 | 5.91 | 3.62 |
| 15 | 25.26 | 15.77 | 5.92 | 3.62 |
| 16 | 25.54 | 15.94 | 5.98 | 3.66 |

These heads use the recorded unobstructed body bore as their velocity reference. An internal probe can have a smaller actual flow area. The table does not assert a sharp orifice, assign K = 1 to a tool or use the remaining residual to infer K.

## Representative 29-in abrupt-joint scenarios

Both catalogue geometries and all surface cases remain in the archive. The table below uses surface case5 only, to show the top-drive scenario explicitly. Components are increments to the unchanged model. Serial-annulus correction is about −0.02 to −0.04 psi and remains included without rounding it to zero in the CSV.

| EOW | Joint geometry | Serial BHA bore | Joint bore | Joint annulus | Joint local | BHA local | Surface | Accounted | Mean sample fraction | Residual |
|---|---|---|---|---|---|---|---|---|---|---|
| 12 | EIS | 35.6 | 10.5 | 1.7 | 59.6 | 24.6 | 35.5 | 706.6 | 60.1% | 468.4 |
| 12 | GPDS55 | 35.6 | 28.5 | 2.3 | 176.0 | 24.6 | 35.5 | 841.6 | 71.6% | 333.3 |
| 13 | EIS | 35.0 | 12.4 | 2.4 | 68.8 | 24.3 | 35.0 | 739.4 | 63.4% | 426.6 |
| 13 | GPDS55 | 35.0 | 33.5 | 3.4 | 201.9 | 24.3 | 35.0 | 894.6 | 76.7% | 271.4 |
| 15 | EIS | 37.3 | 13.6 | 3.0 | 76.3 | 26.9 | 35.0 | 769.4 | 64.7% | 420.0 |
| 15 | GPDS55 | 37.3 | 36.7 | 4.2 | 223.2 | 26.9 | 35.0 | 940.6 | 79.1% | 248.8 |
| 16 | EIS | 29.9 | 12.2 | 2.9 | 85.0 | 27.2 | 35.1 | 711.7 | 57.2% | 532.3 |
| 16 | GPDS55 | 29.9 | 32.9 | 4.1 | 247.9 | 27.2 | 35.1 | 896.5 | 72.1% | 347.6 |

The fraction is the mean of per-sample accounted/measured ratios; it need not equal the ratio of the displayed run means. Residual is measured SPP minus accounted pressure, with the differential left untouched. No proprietary tool allowance has been supplied.

![Motorless pressure accounting](pressure-accounting.png)

*Revised S2 mud; representative 29-in restrictions and abrupt local changes. Both connection geometries use API surface case5. Black ticks are measured run-mean SPP. Negative density-column corrections remain in each total. No missing tool loss is assigned to fill the gap.*

### Surface and geometry sensitivity

| EOW | Joint geometry | Case5 accounted / residual | Case1 accounted / residual |
|---|---|---|---|
| 12 | EIS | 706.6 / 468.4 | 907.7 / 267.2 |
| 12 | GPDS55 | 841.6 / 333.3 | 1042.8 / 132.2 |
| 13 | EIS | 739.4 / 426.6 | 937.7 / 228.3 |
| 13 | GPDS55 | 894.6 / 271.4 | 1092.9 / 73.1 |
| 15 | EIS | 769.4 / 420.0 | 967.6 / 221.9 |
| 15 | GPDS55 | 940.6 / 248.8 | 1138.8 / 50.7 |
| 16 | EIS | 711.7 / 532.3 | 910.7 / 333.3 |
| 16 | GPDS55 | 896.5 / 347.6 | 1095.5 / 148.6 |

[scenario-budgets.csv](scenario-budgets.csv) contains all 6,480 sample scenarios: both mud versions, both joint geometries, three restricted lengths, two local-loss shapes, all five API surface layouts and zero surface allowance. [scenario-run-summary.csv](scenario-run-summary.csv) gives their run summaries. No cases are selected by agreement. Larger assumed allowances can over-account individual pressures; the remaining residual is not a measured HALO loss.

## Sample-by-sample primary accounting

The next table retains every revised-primary sample. Both representative joint geometries use 29-in restrictions, abrupt local changes and surface case5. The complete included and estimated split, fractions and residuals for both mud versions are in [nominal-sample-accounting.csv](nominal-sample-accounting.csv).

| Sample time | EOW | MD ft | Measured | Model | EIS accounted / residual | GPDS accounted / residual | Raw differential |
|---|---|---|---|---|---|---|---|
| 2023-05-13 23:00:00 | 12 | 5318 | 1155.3 | 517.1 | 675.6 / 479.7 | 798.5 / 356.8 | 77.8 |
| 2023-05-14 00:00:00 | 12 | 5412 | 1167.9 | 520.2 | 680.9 / 487.0 | 807.3 / 360.6 | 85.2 |
| 2023-05-14 00:30:00 | 12 | 5459 | 1177.0 | 519.9 | 681.3 / 495.8 | 809.1 / 367.9 | 94.1 |
| 2023-05-14 01:30:00 | 12 | 5500 | 1169.2 | 532.2 | 698.3 / 470.9 | 830.7 / 338.5 | 8.6 |
| 2023-05-14 02:00:00 | 12 | 5524 | 1165.8 | 531.3 | 697.4 / 468.4 | 830.3 / 335.5 | 10.2 |
| 2023-05-14 18:30:00 | 12 | 5558 | 1149.7 | 554.3 | 723.1 / 426.5 | 857.9 / 291.8 | 7.3 |
| 2023-05-14 19:30:00 | 12 | 5593 | 1159.1 | 548.3 | 717.4 / 441.7 | 853.4 / 305.7 | 16.7 |
| 2023-05-14 20:00:00 | 12 | 5617 | 1157.0 | 538.0 | 704.5 / 452.6 | 838.8 / 318.3 | 14.6 |
| 2023-05-14 23:30:00 | 12 | 5773 | 1176.3 | 545.3 | 716.0 / 460.3 | 856.6 / 319.7 | 33.9 |
| 2023-05-15 00:00:00 | 12 | 5794 | 1188.3 | 545.3 | 716.3 / 472.0 | 857.5 / 330.8 | 45.9 |
| 2023-05-15 00:30:00 | 12 | 5818 | 1217.0 | 559.0 | 733.9 / 483.1 | 878.8 / 338.2 | 74.6 |
| 2023-05-15 01:00:00 | 12 | 5839 | 1216.4 | 558.6 | 734.3 / 482.1 | 880.4 / 336.0 | 6.9 |
| 2023-05-15 19:30:00 | 13 | 5987 | 1124.9 | 565.1 | 741.4 / 383.5 | 890.8 / 234.1 | 10.6 |
| 2023-05-15 20:00:00 | 13 | 6013 | 1124.7 | 552.9 | 725.9 / 398.8 | 873.0 / 251.8 | 10.4 |
| 2023-05-15 20:30:00 | 13 | 6057 | 1119.9 | 540.5 | 710.3 / 409.5 | 855.4 / 264.5 | 5.6 |
| 2023-05-15 22:00:00 | 13 | 6067 | 1167.6 | 551.2 | 724.4 / 443.2 | 872.5 / 295.1 | 25.6 |
| 2023-05-15 22:30:00 | 13 | 6170 | 1207.2 | 560.6 | 738.0 / 469.2 | 891.6 / 315.6 | 65.2 |
| 2023-05-16 00:00:00 | 13 | 6148 | 1171.2 | 559.4 | 735.3 / 435.9 | 887.0 / 284.2 | -4.3 |
| 2023-05-16 01:00:00 | 13 | 6196 | 1161.2 | 561.2 | 738.4 / 422.8 | 892.1 / 269.1 | -5.4 |
| 2023-05-16 01:30:00 | 13 | 6218 | 1157.8 | 563.6 | 741.7 / 416.1 | 896.6 / 261.2 | 12.1 |
| 2023-05-16 02:00:00 | 13 | 6239 | 1170.7 | 565.8 | 744.8 / 425.9 | 900.8 / 269.9 | 9.5 |
| 2023-05-16 06:00:00 | 13 | 6423 | 1168.1 | 563.0 | 742.9 / 425.2 | 902.8 / 265.3 | -10.9 |
| 2023-05-16 06:30:00 | 13 | 6444 | 1182.8 | 569.6 | 751.8 / 431.0 | 914.1 / 268.7 | 12.7 |
| 2023-05-16 07:00:00 | 13 | 6466 | 1184.5 | 571.6 | 754.8 / 429.7 | 918.3 / 266.2 | 0.8 |
| 2023-05-16 07:30:00 | 13 | 6485 | 1179.4 | 569.2 | 751.8 / 427.6 | 915.2 / 264.2 | 6.2 |
| 2023-05-16 08:30:00 | 13 | 6523 | 1204.2 | 567.6 | 750.2 / 454.0 | 914.2 / 290.0 | 80.9 |
| 2023-05-18 01:00:00 | 15 | 6627 | 1144.1 | 584.1 | 776.6 / 367.4 | 946.0 / 198.0 | -45.5 |
| 2023-05-18 03:30:00 | 15 | 6742 | 1215.1 | 578.7 | 771.2 / 443.9 | 942.7 / 272.4 | 4.3 |
| 2023-05-18 20:30:00 | 15 | 6838 | 1198.3 | 576.7 | 768.8 / 429.5 | 941.1 / 257.2 | 0.6 |
| 2023-05-18 21:30:00 | 15 | 6868 | 1200.3 | 570.5 | 761.1 / 439.2 | 932.7 / 267.7 | 39.1 |
| 2023-05-20 07:30:00 | 16 | 6986 | 1239.2 | 518.3 | 705.3 / 533.9 | 879.8 / 359.4 | 31.4 |
| 2023-05-20 08:30:00 | 16 | 7034 | 1237.9 | 514.1 | 701.0 / 537.0 | 876.3 / 361.6 | 29.3 |
| 2023-05-20 09:00:00 | 16 | 7064 | 1245.2 | 514.3 | 701.9 / 543.4 | 878.3 / 366.9 | 36.6 |
| 2023-05-20 09:30:00 | 16 | 7094 | 1196.0 | 520.6 | 710.4 / 485.6 | 889.4 / 306.6 | -12.6 |
| 2023-05-20 11:30:00 | 16 | 7198 | 1227.4 | 513.8 | 703.1 / 524.3 | 883.4 / 344.0 | 6.3 |
| 2023-05-20 14:00:00 | 16 | 7321 | 1243.0 | 524.2 | 718.7 / 524.4 | 905.8 / 337.2 | -0.1 |
| 2023-05-20 14:30:00 | 16 | 7343 | 1254.9 | 523.0 | 717.4 / 537.4 | 904.9 / 350.0 | 11.7 |
| 2023-05-20 15:00:00 | 16 | 7365 | 1259.5 | 522.0 | 716.3 / 543.2 | 904.0 / 355.5 | 16.4 |
| 2023-05-20 15:30:00 | 16 | 7385 | 1252.1 | 525.9 | 721.9 / 530.2 | 911.6 / 340.5 | 9.0 |
| 2023-05-20 16:30:00 | 16 | 7423 | 1251.6 | 521.2 | 715.4 / 536.2 | 903.7 / 347.8 | 22.4 |
| 2023-05-20 17:00:00 | 16 | 7442 | 1254.6 | 520.2 | 714.4 / 540.2 | 903.1 / 351.5 | 25.5 |
| 2023-05-20 17:30:00 | 16 | 7460 | 1248.7 | 518.6 | 712.4 / 536.3 | 900.9 / 347.8 | 0.5 |
| 2023-05-20 18:00:00 | 16 | 7478 | 1241.6 | 517.0 | 710.3 / 531.3 | 898.6 / 343.0 | -6.6 |
| 2023-05-20 19:30:00 | 16 | 7522 | 1249.8 | 518.7 | 713.0 / 536.8 | 902.8 / 346.9 | 16.5 |
| 2023-05-20 20:00:00 | 16 | 7540 | 1258.9 | 519.1 | 713.8 / 545.1 | 904.4 / 354.5 | 25.6 |

## Reported differential on motorless runs

| EOW | n | Mean psi | Minimum psi | Maximum psi | Negative sample windows |
|---|---|---|---|---|---|
| 12 | 12 | 39.65 | 6.89 | 94.12 | 0 |
| 13 | 14 | 15.65 | -10.93 | 80.95 | 3 |
| 15 | 4 | -0.37 | -45.52 | 39.13 | 1 |
| 16 | 15 | 14.12 | -12.60 | 36.60 | 3 |

The original S1 diagnostic also includes EOW14, which has no accepted temperature sample. The present accounting introduces no EOW14 sample. Its [original differential table](../s1/motorless-differential.csv) is preserved.

## Archive and provenance

All 90 replays converged and reproduce the archived temperature endpoints and standpipe pressures exactly. No coefficient was fitted.

[plan.json](plan.json) freezes inputs and hashes; [audit.json](audit.json) records verification. [bha-transitions.csv](bha-transitions.csv) retains local coefficients and applicability flags. [tool-joints.csv.gz](tool-joints.csv.gz) retains the connection calculations. [replayed-profiles.npz](replayed-profiles.npz) contains saved bore/annulus profiles, keyed by original S2 case ID. [execution-manifest.json](execution-manifest.json) records published file hashes.

The source data are GDR1516, [DOI 10.15121/1998591](https://doi.org/10.15121/1998591), CC BY4.0. This diagnostic adds pressure calculations and aggregation to those extracts; original downloads remain unchanged. The source report locators and estimate references are listed in the protocol. No new temperature prediction is substituted for S1 or S2.
