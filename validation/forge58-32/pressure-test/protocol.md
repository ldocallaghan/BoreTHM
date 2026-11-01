# FORGE 58-32 registered pressure comparison

This comparison asks whether the adopted entry 8 calculation with entry 10 smooth Colebrook reduces standpipe-pressure error against the original v1.5.0 calculation on the same motorless circulation events. The numerical settings are in [protocol.json](protocol.json). The [input archive](README.md) identifies every window and its source records.

## Data statement and scope

The sampling list was registered at `8bbfe2c44658dade8972a647970e3308047b6380`. Before this numerical protocol, two slow-circulation pressure readings were viewed in report 10 for 5 August 2017, in `1006.zip!58-32_EOWR.zip!58-32_EOWR/DailyDrillingReport.pdf`, PDF p13. No Pason window pressure target has been inspected or used to choose an input, coefficient or sampling rule. Interpret and publish the comparison with that prior report-pressure exposure disclosed.

The primary observations are the existing 62 `motorless_primary` windows in seven events, all on BHA 2. Their IDs and assignments remain those in [off_bottom_windows.csv](../off_bottom_windows.csv). They span the 12.25-in section only. This is a shallow, single-assembly comparison; it cannot establish whole-well skill. Motor windows remain excluded because their installed no-load losses are unresolved. No thermal target, PT log or other well's target enters this comparison.

## Sampling and assignment

The existing [sampling amendment](../../forge56-32/protocol-amendment.md#short-off-bottom-windows) supplies the input-only rule: six ten-second bins for settling followed by six for measurement, flow above 100 US gpm, within-window mean-flow span at most 5%, at least eight native observations per bin, bit depth at least 100 ft, at least 10 ft off bottom and bit-depth span at most 2 ft. Event membership and conservative daily-report BHA assignment are unchanged. The full rule, including flow-epoch restarts and event boundaries, remains the registered amendment. No window is added from the more precise BHA dates in Figure 14.

An event represents contiguous off-bottom occupancy and may contain several windows. Keep all original candidate exclusions in the well's [count table](../off_bottom_counts.csv). The 62 planned windows stay in every coverage table, including incomplete inputs and numerical failures. Input completion is separate from sampling qualification.

Timestamps retain the source clock. Its time zone and alignment with the daily reports are unverified. A UTC label may supply numerical coordinates, without asserting the original time zone. No clock offset is selected from pressure.

## Recorded equipment and length reconciliation

The source is Geothermal Resource Group (2017), end-of-well report, PDF p29, Figure 14, in GDR 1006. Its BHA 2 diagram gives all 17 components, their bores and reported dates 3 August 05:00 and 6 August 00:00. The midnight date-out is a calendar-record qualification, without a more precise trip time. The [transcription](bha2-figure14.json) preserves the printed values. The daily summary reports eleven component lengths more precisely; [components.csv](inputs/components.csv) uses those lengths for items 1–11 and the diagram's rounded lengths for the six omitted items. It records the source for every dimension. No blank bit bore is filled.

The diagram's component lengths sum to 580 ft, while its header reports 581.73 ft. Combining the daily lengths with the six diagram lengths gives 580.94 ft, leaving a 0.79-ft discrepancy. Preserve the discrepancy without rescaling. The nine heavy-weight drill-pipe joints have a combined length of 272 ft; their model spacing is 272/9 ft. The 16 non-bit components span 579.58 ft. These values and their calculation are recorded in [geometry.json](inputs/geometry.json).

The bit is the nozzle boundary and has no body-passage pressure loss. Its source length stays in the ledger. As in the existing D5 geometry, ordinary pipe fills the remaining modelled measured depth above the non-bit assembly. At shallow circulation depths, retain the lower assembly and truncate its top; never shorten the lower components or create a negative ordinary-pipe length. Stabiliser gauge ODs are uniform annular envelopes, with unreported body shapes flagged. Jar and shock-sub nominal passages are included, but their additional proprietary operating losses remain unquantified. No operating curve is inferred from pressure.

## Catalogue assumptions and separate sensitivities

The installed ordinary-pipe OD and weight are unconfirmed. Figure 14 gives 4-in heavy-weight pipe and a `TSD40` top-thread label. That label does not establish the ordinary pipe's body size, length or connection machining. Use the following independently sourced TSC catalogue scenarios, whose [references](references.json) identify revision 9, 22 May 2025, PDF p1 for each sheet. The primary is an explicit same-OD continuation assumption. The 4.5-in alternative records that the same catalogue connection is also offered on a larger body.

| Scenario | Ordinary-pipe OD, in | Nominal weight, lb/ft | Body ID, in | Joint OD, in | Joint ID, in |
|---|---|---|---|---|---|
| `primary` | 4.000 | 14.00 | 3.340 | 5.250 | 2.563 |
| `heavy_pipe` | 4.000 | 15.70 | 3.240 | 5.250 | 2.563 |
| `wide_joint` | 4.000 | 14.00 | 3.340 | 5.250 | 2.688 |
| `larger_pipe` | 4.500 | 16.60 | 3.826 | 5.250 | 2.563 |

The printed decimal dimensions are used. The catalogue does not identify the installed string. Each sensitivity changes one unresolved equipment choice and is reported separately with both models. There is no factorial combination or selection by residual. Ordinary-pipe joint spacing is the catalogue's 31.5 ft. Retain the existing 29-in effective restriction length and abrupt local-loss treatment as transferred modelling assumptions; the catalogue's external box/pin lengths do not measure a constant-bore hydraulic restriction. For heavy-weight pipe, retain its recorded 2.500-in bore through the joint, with the 5.250-in external envelope transferred and flagged. Additional tool-loss and installed surface-layout uncertainty have no finite sourced pressure band.

During these windows the surface casing is 13.375-in, 54.5-lb/ft N80, as reported on end-of-well PDF p25. Use nominal ID 12.615 in from Cudd Well Control (2021), printed p48, Casing Capacity table. The daily shoe is 338 ft; preserve the report's 337.6-ft value as the source rounding difference. Model steel and cement out to the original 17.5-in hole, followed by 12.25-in open hole. The later 9.625-in casing is absent from these calculations. The well's own MD/TVD survey applies, with linear interpolation and final-inclination continuation if needed.

## Mud, inlet and exposure history

The declared fluid section runs between the Figure 14 BHA dates. Section 6.3.5, PDF p30, describes a planned polymer mud. Continuity within that section is an assumption because the extracts contain no daily fluid-system identifier. Choose the nearest measured density and nearest non-missing paired PV/YP within those dates, in either time direction; an equal time distance selects the earlier sample. Record measurement time and signed transfer age. No cross-section substitution or weighted reference-mud fallback is made. The prepared cohort has an available measured pair, including transfers from a later measurement.

Use PV referenced to 26.7 °C for all calculations, as in entry 8, with the recorded yield point. This numerical protocol supersedes the earlier 58-32 protocol's 48.9 °C primary convention; the raw extract's historical convention columns are retained. The actual field PV test temperature remains unknown. No additional PV-reference comparison is part of this pressure test. Mud weight is interpreted as reference density at 20 °C, following the existing evaluator, with its unreported measurement temperature flagged.

Each inlet value is the equal-weight mean of the six input-bin means, converted from Fahrenheit by `(T - 32)/1.8`. Every bin needs at least eight finite native inlet observations. The source label is generic `Degrees`; the Fahrenheit interpretation follows the existing DDR convention and remains an input qualification. Missing inlet makes the numerical case incomplete, without removing its planned ID. No pressure or temperature error chooses a unit, fallback or time shift.

The cumulative circulation clock counts ten seconds for an observed input bin with flow above 100 US gpm and at least eight native flow samples. Hole depth is the running maximum of finite bin depths with at least eight native samples. Missing source periods add no circulation time. There is no trip reset or inferred recovery. [circulation-clock.csv.gz](inputs/circulation-clock.csv.gz) preserves this preparation-period history. For each model, apply the existing `exposure_from_history`, `smooth_exposure` and exposure-break rules, including the one-hour floor. Use the full history up to the window centre, with the existing interpolation convention.

Use the existing FORGE 216-day formation profile against TVD, constant beyond its endpoint, as the transferred boundary declared in the earlier well protocol. Retain the existing FORGE rock conductivity and volumetric heat capacity, with their values fixed in `protocol.json`. These are transferred rock inputs for this shallow section. No 58-32 formation-temperature observation is read or fitted.

## Models and fixed calculation inputs

The model source includes D6 at `c15984da8a8da745f26851ebe578d749e2b9c076` and D7 at `29fe035551bee900d732b292bedc28daa0d39f6f`; the working-calculation decision is corrected at `41147f3` on 1 November 2026. The adopted working calculation is entry 8 with entry 10 smooth Colebrook and zero roughness. Entry 8 with Blasius is reported as secondary. The original v1.5.0 release commit is `edc27007759de575baa7b3c6f4969139cea8d616`; its equations are retained in the current package and covered by the legacy reproduction tests. The original reference uses those equations with D6's occupancy-weighted treatment of overlapping thermal ramps and D7's clipping of the numerical mesh to the physical well interval. Unmodified v1.5.0 fails to converge on this assembly. Neither correction changes a physical equation, recorded geometry, solver tolerance, node limit or seed sequence. All calculations use the same recorded dimensions, mud and exposure inputs. The legacy geometry has no `HydraulicJoint` objects or new tool-loss objects, as required by the original interface.

| Calculation | Pipe friction | Hydraulic mode | Annulus model | Rock response | Surface allowance | Repeated joints |
|---|---|---|---|---|---|---|
| `original` | Blasius | `v1.5.0` | `v1.6.0`, original plastic-viscosity film treatment | `logarithmic` | Original treatment, no new surface object | Original treatment |
| `working_entry10` | Smooth Colebrook | `v1.6.0` | `herschel-bulkley-erge`, no-yield power law | `cylinder` | API surface case 5 | Declared serial geometry and joints |
| `secondary_entry8` | Blasius | `v1.6.0` | `herschel-bulkley-erge`, no-yield power law | `cylinder` | API surface case 5 | Declared serial geometry and joints |

All calculations use zero roughness and film multiplier 1.0. The working harness passes `friction='colebrook'` explicitly. The original and secondary calculations pass `friction='blasius'`. The working mud's power-law parameters use the same PV/YP-to-600/300-rpm conversion as entry 8, with zero low-shear yield stress. The original mode retains its Bingham treatment. No steel-roughness, GPDS55, FH, gradual or fitted film scenario is adopted. The package defaults are unchanged.

The surface scenario is API RP 13D, sixth edition (2009), section 7.3, equation 60 and table 4, case 5. Its empirical coefficient is retained from the existing implementation. Actual rig plumbing and transducer position are unconfirmed.

Convert inlet flow to mass flow using each model's fluid density at its common inlet temperature and surface pressure, as in the existing evaluator. Bit jets are three 22/32-in nozzles, recorded in the BHA 2 bit table; use their summed circular area and nozzle coefficient 0.95. Off-bottom rock-cutting face power and motor heat are zero. Additional rotary string heat is zero because no independent off-bottom torque input has been supplied. This is a declared missing heat input, even if the recorded RPM is nonzero.

Use `solve_seeded` with its existing seeds and numerical settings. Retain all failed attempts and solver status. A diagnostic energy flag does not fail a solve. Pressure properties and evaluation points follow each mode, including the revised 5 MPa property guard; there is no extra legacy guard or pressure-profile substitution. Report the full pressure budget and calculated bit/return temperatures as model diagnostics. Those temperatures have no measured comparison in this protocol.

## Target reduction and paired coverage

The pressure source is `1006.zip!Pason_Logs.zip`, channel `Pump Pressure`, with psi as the DDR convention. Use only native rows in the registered half-open window interval. A ten-second pressure bin requires at least eight finite observations; a complete window requires all six bins. Its target is the equal-weight mean of the six pressure-bin means. Source null `-999.25` and non-finite values are missing. Finite zero and negative values remain observations. No value or residual threshold selects a case. The prepared [source-bin locators](inputs/source-bins.csv) identify the raw members and native row bounds.

Publish a window table for every planned ID, with both predictions and target availability. A paired window has complete registered inputs, convergence in both models and a complete target. The same paired IDs are used for both models and every reported before/after error. Each equipment sensitivity has its own explicitly identified paired cohort; also report the common cohort across scenarios. No scenario may gain apparent skill by concealing missing cases.

For each event, take the median target and median prediction for each model over exactly the same paired windows, then subtract those medians. Keep events with no paired windows as unavailable. Every available event has equal weight in the primary BHA/well summary. This prevents the 35-window event from receiving more weight than a one-window event. Also report window-weighted measures as secondary quantities.

## Model-only pressure budget and scope of the test

Before target access, `predict_budget.py` solves every registered window under the primary geometry for the original, adopted working and secondary calculations. The budget script reads the prepared input archive only, with the already declared transferred formation profile. It imports no target-extraction or scoreboard module. `model-only/window-budget.csv` records standpipe pressure and the surface, drill-pipe bore, bit-nozzle and annulus contributions, with buoyancy retained separately so the budget sums to the total. `model-only/component-budget.csv` records each BHA component's bore loss, including zero for a component truncated above the current bit depth and for the bit body. Joint and geometric changes are included in their owning component's bore total; named terms remain separate columns.

`model-only/event-budget.csv` gives arithmetic mean parts and their sum on identical successful windows in all three calculations for each event. Median total pressure and coverage are also reported. `model-only/event-components.csv` uses the same cohort for each BHA component. Means make the displayed budget additive. The primary skill calculation continues to use event medians on target-complete paired windows. No measured pressure appears in these files.

Before running, starting-profile agreement for each original window is set at 0.01 °C in bit and return temperature and 1 psi in standpipe pressure. Each original result uses the usual seed sequence. A separate original solve through `solve(init=...)` starts from the converged working profile, with the original geometry and equations unchanged. `model-only/starting-profile.csv` records every difference and convergence message. These extra calculations do not replace a failed seeded result. All failures remain in the coverage record.

The windows place the bit at 552–1,884 ft with a reported BHA length of about 581 ft. Modelled pressure is therefore expected to consist mainly of bit-nozzle, BHA-bore and surface-line losses. Ordinary-pipe friction is a smaller part of this shallow comparison. The model-only budget tests that expectation without a measured target.

Additional installed tool losses for the jar, shock sub and any other tool without an operating curve are absent from all calculations. These omissions are expected to lower predicted pressure by the missing losses. Entry 9 found 188–483 psi unaccounted near surface on 16B, in [near-surface.csv](../../model-development/entry-9/results/near-surface.csv); that development result does not establish a numerical loss band for 58-32's tools. The skill score compares calculations that share these omissions. It measures change relative to v1.5.0 and provides limited evidence about absolute pressure accuracy. Seven events from one motorless assembly provide weak evidence for either an increase or a decrease in model skill.

## Measures and interpretation

Residual is predicted minus observed pressure. Report it in psi and as a percentage of the observed value; a zero denominator gives no percentage and retains the absolute residual. For each model publish event-weighted bias, MAE and RMSE, with the event residuals and their ranges. Publish BHA counts from planned through input-ready, converged and target-complete to paired, separately for events and windows.

The primary skill is `1 - RMSE_working / RMSE_original`, using the same event cohort. Positive skill means reduced RMSE; zero means equal RMSE. If original RMSE is zero, skill is undefined and both RMSE values remain reported. Publish the corresponding window-weighted skill separately. Failures and missing targets remain visible even when no paired skill is available. There is no fitted acceptance threshold or outlier removal.

Plot measured against modelled pressure by window, and residual against flow, depth and BHA. Keep catalogue scenarios separate. Agreement cannot identify installed pipe or select an equipment assumption. Source inspections and actual string records would test those assumptions. Any later source clarification or new measure requires a dated amendment that records whether targets had already been accessed. No parameter is changed to improve a pressure residual.

The numerical comparison of unmodified v1.5.0 and D6 identifies a mesh-blending defect. It does not identify a physical pressure-error cause or estimate a missing tool loss. The earlier interrupted attempts remain part of the external provenance; the registered original reference is explicitly the v1.5.0 equations with D6 and D7.
