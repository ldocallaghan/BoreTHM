# FORGE 78B-32 blind thermal forecast protocol

This protocol declares a blind forecast of the downhole temperature measured while drilling Utah FORGE well 78B-32, drilled from 28 June to 29 July 2021. Part A, the headline, is the temperature reported by the measurement-while-drilling (MWD) tool during drilling. Part B covers the second downhole channel, the return temperature at surface and the temperatures of two Sanvean sensor subs. Part E declares a physical-bounds check, applied after the targets are read. The forecasts, the scorer and this protocol are committed before any of these temperature records is read, and the targets are extracted only after that commit is public.

The forecasts use BoreTHM 1.9.0 as released on PyPI. Its default physics is that of v1.8.0. The method follows the [56-32 thermal protocol](../forge56-32/thermal_protocol.md) and the [58-32 thermal protocol](../forge58-32/thermal_protocol.md). Each change is listed with its reason. The [input archive](thermal/README.md) lists the files and how to rebuild them.

## Data status

**Records held back.** None of these has been read. The targets and every other temperature record of the well:

- in the Pason exports: `MWD Temp`, `EYE TEMP`, `TEMP OUT`, `Tool Temperature` and `Mud Temperature`, with `Return Flow`, the `Flow` paddle (taken to be the flow out, inferred), standpipe pressure, `SPP MWD`, the unfiltered pressures and the differential pressures;
- the Sanvean sensor archive, `Forge 78 B-32 WOO - 1 Sensor Data RM.zip`;
- the temperature logs of 22 July and 30 July 2021, the cement bond log, and the temperature curves (`CTEM`, `GTEM`, `MTEM`) of every wireline file;
- in the daily reports, the mud log and the end-of-well report: every downhole, return, outlet, flow-line, cooler or maximum temperature, and every standpipe or pump pressure.

Pressure stays held back for a later test.

**Read before this declaration.** The column headings and the first row of the ten-second export were read when this test was planned. That row is 00:00:00 on 28 June 2021 with the bit at 16.4 ft and no flow (measured). It lies outside every drilling window: the first window is centred at 03:00 on 28 June. No window is excluded on its account. Since then, only these have been read:

- the archive listing, with column headings read by [list_archive.py](thermal/list_archive.py), which prints no data row, and for LAS files the curve mnemonics and units only;
- counts of finite readings and counts of updates (a finite reading that differs from the previous finite reading) of the held-back channels, by [count_availability.py](thermal/count_availability.py), which keeps flags only ([availability/](thermal/availability/));
- the Sanvean output files' names, column headings and row counts, by [sanvean_headers.py](thermal/sanvean_headers.py);
- report text located with every digit masked; the open fields were then extracted by code that drops the held-back cells first ([build_inputs.py](thermal/build_inputs.py));
- the BHA sheets of the end-of-well report, which are images. A first OCR pass printed them with every digit masked and listed any word suggesting a temperature or pressure; the only such words were motor bend angles. The component rows were then read in full ([build_bha_sheets.py](thermal/build_bha_sheets.py)).

**Earlier use of 78B-32.** None. Every mention of 78B-32 in this repository and its history, before this test, states that its data are reserved or excluded (calculated: a search of all lines added or removed in the history).

**Other wells.** FORGE 16B runs 11 to 16 remain sealed and are not used. 16A, 16B runs 1 to 10, 56-32 and 58-32 are development data.

The message of `13aa9b7` says no forecast had been run from its code. A scratch forecast had been run from the uncommitted code to fill the protocol's counts. The declared forecast in `d874e0f` was run from the committed code and is identical.

## Inputs

All inputs come from `1330.zip` (GDR 1330, 15,431,810,676 bytes, SHA-256 `b56e77dbc8b5081352418fc8976e9c20da1f57bdd67fdc25961134ea99ced79f`). Times are on the Pason clock.

**Rig record.** The ten-second Pason export, `78B-32 10 sec data 27200701.csv`, from 00:00 on 28 June to 10 August 2021. Its rows are the ten-second bins. Its last column holds free text and is never read. The `_standard` exports are mostly empty (calculated: bit depth is present in 10,000 of 322,559 rows) and are not used. The one-second export has no temperature channel and is not used.

**Flow (calculated).** Pason `Total Pump Output`, unscaled. Under the rule of entry 11 table A2, the median Pason output over the Drilling Parameters rows of the daily reports agrees with the reported flow to a median ratio of 0.991, and 14 of the 16 rows agree within 10 % ([flow-check.csv](thermal/inputs/flow-check.csv)). The two others are the surface hole on 28 June (0.82) and the coring run on 13 July (1.42).

**Inlet temperature.** The Pason `TEMP IN` channel, read as Fahrenheit under the daily-report convention and converted by (F − 32)/1.8. It is recorded from 9 July onward. From 28 June to 8 July the inlet is the "In" temperature of that day's mud check in the daily report, and these windows are flagged (`inlet_source` = report). 4 July has no mud check; its windows take the nearest check in time, with ties to the earlier. Compared with the Pason mean over the 30 minutes around each mud check, the report value differs by more than 5 K on 10 July (+5.6 K), 17 July (−5.2 K) and on 18 to 20 and 22 to 27 July, when every report repeats one 11:00 check of 98 °F (calculated, [inlet-check.csv](thermal/inputs/inlet-check.csv)). Windows on those days are flagged, and each result is also reported without them. The report value is taken only from the "In" cell of the mud table: every value cell is assigned to the nearest heading of its column, and the outlet cell is dropped before any record is built.

**Gaps (calculated).** The export starts before the first circulation, at 00:44 on 28 June with the hole at 128 ft; the 27 June report covers rig-up only. While drilling, four gaps exceed ten minutes: 14 minutes on 30 June after circulation at 981 US gal/min, and three with the pumps off on 7 and 20 July. No report clock is needed. The circulation clock counts ten seconds for each bin with flow above 100 US gal/min, so a missing bin counts no circulation.

**Operations.** Every operations row of every daily report, with any description that mentions a pressure or a temperature replaced by a suppression marker ([operations.csv](thermal/inputs/operations.csv)); 56 of 400 rows are suppressed.

**Assemblies.** Each BHA sheet of the end-of-well report gives the assembly's depth and date in and out and its components with length, outside diameter and bore. Twenty of the 22 sheets have component lengths that sum to the printed BHA length, after corrections read from the page images and listed in the builder; BHA 2 and BHA 5 differ and have no window that is forecast. A window takes the assembly whose sheet depth interval, widened by 1 ft, contains the hole depths of its qualified bins and whose sheet times, widened by 12 hours, contain the window centre. A window with no such assembly, or more than one, is unassigned. The 12 hours allow for the sheet times, which are approximate: BHA 10 is "out" at 11:30 on 11 July and drills on the Pason record until 20:45. The BHA 22 sheet prints its depth out as 10 ft; the bit record gives 9,500 ft, which is used.

**Tool on the assembly.** The SLB MWD is listed as an `MWD` item on BHA 1, 3, 4, 6, 7, 8, 9 and 10. The Scientific Drilling assemblies, BHA 14, 15 and 22, list no `MWD` item; their tool is taken to be in the lower monel collar, below the pulser sub (inferred from the component order). No other assembly carries a tool. `MWD Temp` has finite readings on days with no MWD in the hole and on the coring assembly BHA 11, with no update in any of BHA 11's three windows (calculated). The channel holds its last value (inferred).

**Sensor position, MWD.** No sheet or report states a sensor offset. The sensor is placed at the midpoint of the MWD item (BHA 1: 23.73 ft above the bit; BHA 3 and 4: 36.05 ft; BHA 6: 36.73 ft; BHA 7: 53.95 ft; BHA 8 and 9: 56.08 ft; BHA 10: 56.74 ft) and of the lower monel for the Scientific Drilling tool (BHA 14: 54.25 ft; BHA 15: 65.39 ft; BHA 22: 49.94 ft) (calculated from the sheets). The 84 ft offset of the 56-32 rule lies above the MWD item of every assembly and is not used.

**Sensor position, Sanvean.** The cubic sensor subs are listed on the sheets with serial numbers. BHA 3 and 4 carry CSS-008 at 62.65 to 64.83 ft and CSS-007 at 119.72 to 121.80 ft above the bit; their positions are the midpoints, 63.74 ft and 120.76 ft (calculated). BHA 15 carries CSS-006 and CS-04; the 15 July report states "Placed cubic sensors at 50.96', 132.86'", which is used (the sheet puts the tops of the two subs at 50.50 ft and 131.53 ft). The files map to assemblies by serial number and hole size (inferred): `Forge 14.75 Run 1` to BHA 3, `Forge 14.75 Run 2` to BHA 4 and `Forge 10.625` to BHA 15.

**Nozzles.** The nozzle area of a window is that of the bit record whose diameter equals the sheet's bit and whose depth in is within 1 ft of the sheet's depth in. An assembly with no such record, or with records giving different nozzle sets, has no nozzle area and its windows are not forecast (BHA 2 and BHA 19, one window each).

**Passages and heat.** A component without a recorded bore follows the 56-32 rule: a crossover or bit sub takes the drill-pipe envelope and is flagged. A mud motor's internal thermal geometry uses the bore of the component above it. A roller reamer or stabiliser listed at or above the bit diameter, which is its cutter or blade gauge (the roller reamers of BHA 11 and 13), takes the outside diameter of the drill collar above it and is flagged. Motor heat is zero: the differential pressure is held back and no declared source gives it. Friction heating is on and no rotary power is supplied, as for 58-32.

**Drill pipe.** The reports name 5 in pipe to 3,009 ft, 5.5 in pipe from 4 July in the 10-5/8 in section, and 3.5 in pipe in the 5-3/4 in section; none states weight or bore. The 5 in pipe is 19.5 lb/ft with a 4.276 in bore and the NC50 connection scenario of the 56-32 protocol (6.625 by 3.25 in, 29 in, 31.5 ft pitch). The 5.5 in pipe came from the 16A location (daily report, 3 July) and takes the 24.7 lb/ft, 4.670 in bore of the package 16B study, with no connection, as in that study. The 3.5 in pipe takes 13.30 lb/ft with a 2.764 in bore, a catalogue value not checked against a source here, and is flagged. The pipe follows the bit: 5 in pipe above a 22 in or 14-3/4 in bit, 5.5 in pipe above a 10-5/8 in or 8-3/4 in core bit, and 3.5 in pipe above a 5-3/4 in bit. The 3.5 in pipe enters one window, on BHA 21, which is forecast for the return temperature only (calculated). BHA 22 has no window: its on-bottom pump output has a median of 289 US gal/min, below the 300 US gal/min of the window rule (calculated).

**Casing.** From the end-of-well casing table: a 24 in conductor with 0.5 in wall (23.000 in bore) to 128.5 ft; 16 in 65 lb/ft K-55 (15.250 in bore) to 416 ft in 22 in hole; 11-3/4 in 54 lb/ft K-55 (10.880 in bore) to 2,990 ft in 14-3/4 in hole; 7 in 41 lb/ft T-110 (5.820 in bore) to 8,509 ft in 10-5/8 in hole. Cement fills each annulus out to the next casing or the drilled hole; rock starts at the conductor's outside diameter. The casing in place is every casing whose bore is larger than the assembly's bit, which sets it by the section being drilled. Below the deepest shoe the hole is open at the drilled diameter: 22 in to 421 ft, 14-3/4 in to 3,009 ft, 10-5/8 in to 8,545 ft (the cored intervals were reamed to 10-5/8 in) and 5-3/4 in below, except that the hole below the assembly's depth in takes the assembly's bit diameter.

**Mud.** As in the 56-32 protocol: the nearest recorded density and the nearest paired plastic viscosity and yield point in the same hole section, in either direction in time, with ties to the earlier sample. From 5 July the hole was on fresh water: the reports give 8.3 lb/gal with plastic viscosity 0 to 2 cP. A density at or below that of water takes the package's water (`fluids.water()`). The reported plastic viscosity of a mud is referred to 48.9 °C, an assumption carried over from 56-32. A reported plastic viscosity below that of water at 48.9 °C takes water's viscosity: the one fresh-water check denser than water, 8.4 lb/gal on 6 July, reports 0 cP. The hole section of a mud check is set by the Pason hole depth at its time.

**Formation.** The FORGE 16A 216-day temperature survey, transferred by true vertical depth with the 78B-32 survey and held at its end values beyond the log, as for 56-32. The released package does not ship the 16A data, so the survey is read from the repository copy ([formation_temperature_216day.csv](../forge16a/formation_temperature_216day.csv)) with the package's interpolation. The 78B-32 survey has 100 stations to 9,500 ft measured depth and 9,497.3 ft true vertical depth.

**Rock.** The FORGE rock conductivity and volumetric heat capacity of `borethm.studies.validate_forge16b`, as for 56-32 and 58-32.

## Part A: MWD temperature while drilling

This is the headline test. The primary target is `MWD Temp`, chosen before any value was read as the downhole channel with the most drilling-window coverage: 163 windows with at least 80 % finite qualified bins, against 42 for `EYE TEMP` and 3 for `Tool Temperature` (calculated, [availability-summary.json](thermal/availability/availability-summary.json)). `Tool Temperature` is finite only where `MWD Temp` is.

**Windows.** As for 56-32: half-hour windows centred on the hour and half hour, each the half-open interval from 15 minutes before to 15 minutes after. A ten-second bin qualifies when the pump output is above 300 US gal/min, the bit is within 5 ft of hole depth and the on-bottom rate of penetration is above 1 ft/h. A window needs at least 90 qualified bins, at least 0.5 ft of new hole and one assembly. Its inputs are the means over its qualified bins. Part A takes the windows on BHA 1, 3, 4, 6, 7, 8, 9 and 10.

**Forecast.** The drill-string fluid temperature at the MWD sensor position, from the v1.9.0 circulation solve (`Td` at the sensor's measured depth). The sheets list the MWD as a collar with a 3.500 in bore and name no annular sensor, and the 16B comparisons in this repository use the bore temperature at the sensor.

**Measured value, after unsealing.** `MWD Temp` updates about once per window (calculated: a median of one update per window, and 51 of the 160 windows on MWD assemblies have none), so most qualified bins carry a reading held from earlier. The measured value is the mean of the fresh readings in the window's qualified bins. A reading is fresh when it is finite and differs from the channel's previous finite reading anywhere in the export. Readings are Fahrenheit and are converted by (F − 32)/1.8. Empty and non-numeric cells and the null value −999.25 are missing.

| Rule | Applies to | Effect |
| --- | --- | --- |
| R2 | Each reading | A converted reading at or below 0 °C or above 250 °C is missing |
| R1 | Window | Excluded if fewer than 80 % of its qualified bins have a valid reading |
| R3 | Window | Excluded if it has no valid fresh reading |

R2 applies first, then R1 and R3. No other exclusion is allowed after the targets are read.

**Declared secondary.** The 56-32 measure on the same windows: the mean of the valid readings over all qualified bins, with R2 and R1 as above and R3 excluding a window whose valid readings are all equal.

**Groups.** Metrics are reported overall, by assembly, and by quartile of bit depth, of flow and of inlet temperature. Quartile edges come from all part A windows with converged predictions, and each quartile includes its upper edge. Each result is also reported for the windows with a Pason inlet only, since most part A windows take the inlet from a single daily mud check.

## Part B: secondary targets

**EYE TEMP.** The second downhole channel, on the Scientific Drilling assemblies BHA 14, 15 and 22, in the form of part A: the same windows rule, forecast at the lower-monel sensor position, the fresh-reading measure and rules R1 to R3. Overall and by assembly. BHA 22 has no window, so the windows are those of BHA 14 and 15.

**Return temperature.** Pason `TEMP OUT`, read as Fahrenheit, as in the 58-32 part A: the mean of the valid readings over the qualified bins; R2 removes a converted reading at or below 0 °C or above 120 °C; R1 at 80 %; R3 removes a window whose valid readings are all equal. The windows are every assigned drilling window with a Pason inlet, from 9 July onward. The forecast is the surface return temperature.

**Sanvean sensors.** The temperature of each cubic sensor sub, on BHA 3, 4 and 15, forecast as the drill-string fluid temperature at its position. The Sanvean clock is aligned after unsealing with inputs only, by [extract_targets.py](thermal/extract_targets.py): the offset, searched in 10 s steps over plus or minus 24 hours, that maximises the share of overlapping ten-second bins in which the Sanvean and Pason pump states agree (pumping above 100 US gal/min). A file is scored only if that share is at least 0.95 and the median difference between the Sanvean and Pason hole depths at that offset is at most 5 ft. A window is scored for a sensor when the aligned record covers it: the measured value is the mean of the valid readings in its qualified bins (degrees Celsius as recorded; R2 at or below 0 °C or above 250 °C); R1 requires a valid reading in at least 80 % of the qualified bins; R3 removes a window whose valid readings are all equal. A window with no aligned reading is outside the Sanvean record and is not counted as excluded.

## Part C: temperature log of 22 July 2021

Not forecast. The log exists only as a PDF; no LAS file gives whitelisted header fields for it, so its time and the circulation before it cannot be established from permitted fields. It stays held back.

## Part D: predictors and skill

The primary prediction is BoreTHM 1.9.0 with its defaults. The comparators are the same package with `physics='v1.7.0'` and the analytical comparator of `validation/comparators/thermal.py` (tubing temperature at the sensor depth, annulus temperature at surface for the return), each with the same inputs.

Errors are prediction minus measurement, in °C. Skill against a comparator is 1 − RMSE(v1.9.0)/RMSE(comparator) on the same samples.

Persistence, the measured value of the preceding scored part A window on the same assembly, is reported as context only. A forecast never sees a measured value, so persistence uses information that no forecast in this test has.

## Part E: physical-bounds check

Declared now and applied after unsealing, to part A. A scored window is flagged if its measured temperature is more than 3 °C below its inlet temperature, or more than 10 °C above the formation temperature at the sensor's true vertical depth. The headline result uses all scored windows. The result on unflagged windows is the declared secondary.

## Part F: results

There is no pass mark. For each predictor the results are the count, bias, mean absolute error, root mean square error (RMSE), the shares of errors within 2 °C and within 5 °C, and skill, overall and by group. For context: in the 16B comparisons the run-average MWD temperature on regular pipe was 180 °F on BHA 10 and 220 °F on BHA 13, against 192 °F and 228 °F from the model with the film coefficient unfitted; the 58-32 return temperature had an RMSE of 1.95 °C.

[score_thermal.py](thermal/score_thermal.py) reads the samples, the prediction file and the target files, refuses any file whose SHA-256 differs from its manifest or recorded hash, applies R1 to R3 and part E as declared, and writes the scores, counts and figures. It was tested on synthetic targets before this commit.

## Changes from the 56-32 and 58-32 rules

| Earlier rule | 78B-32 rule | Reason |
| --- | --- | --- |
| Assembly by crosswalk dates (56-32) or by run and report end of day (58-32) | Assembly by the BHA sheet's depth interval and widened times | The reports' assembly line does not describe the end of the day; the run rule left 59 MWD windows unassigned and gave 25 windows that BHA 10's sheet covers to BHA 9 (calculated) |
| Sensor 84 ft above the bit | Midpoint of the MWD item or lower monel | The 84 ft point lies above the MWD item or lower monel on every assembly |
| Measured value, mean over qualified seconds | Mean of the fresh readings | The channel updates about once per window and holds its value between updates |
| One-second Pason files | Ten-second export | The one-second export has no temperature channel |
| Pason inlet throughout | Report inlet from 28 June to 8 July, flagged | The Pason inlet starts on 9 July |
| Energy-balance consistency rule (58-32) | Physical-bounds check | The energy ratio was unreliable where the heat gain was small |
| Return temperature as headline | Downhole temperature as headline | A downhole channel exists |

## Counts before unsealing

Calculated by [prepare_thermal.py](thermal/prepare_thermal.py) and [predict_thermal.py](thermal/predict_thermal.py); every count below is fixed before any target is read.

- Drilling windows: 214, with 33,260 qualified bins. 211 are assigned to one assembly; 3 are unassigned (13 July 16:00, 19 July 01:30, 21 July 02:30). 209 have complete inputs; BHA 2 and BHA 19 have no nozzle area (one window each).
- Part A: 160 windows (BHA 1: 3, BHA 3: 21, BHA 4: 19, BHA 6: 29, BHA 7: 62, BHA 9: 1, BHA 10: 25; BHA 8 has none). 134 take the report inlet, 15 of them on 4 July from the nearest mud check; 26 take the Pason inlet, 1 of them on a flagged day. All three predictors converged on all 160.
- Part B, EYE TEMP: 45 windows (BHA 14: 22, BHA 15: 23), all with three converged predictions.
- Part B, return temperature: 76 windows with a Pason inlet (BHA 9: 1, BHA 10: 25, BHA 11: 3, BHA 14: 22, BHA 15: 23, BHA 19: 1, BHA 21: 1), 2 of them on flagged days. 75 are forecast; the BHA 19 window has no nozzle area.
- Part B, Sanvean: 63 windows for each sensor (BHA 3: 21, BHA 4: 19, BHA 15: 23), all with three converged predictions. How many fall inside the aligned Sanvean record is known only after unsealing.
- Fluid, over all 214 windows: water on 126, mud on 49 and mud with water's viscosity on 39 (the 6 July check, BHA 7).
- Flagged geometry: the roller reamer of BHA 11 takes the collar diameter on 3 windows. No component takes the drill-pipe envelope in a forecast window.

## Frozen after declaration

The predictions, rules and thresholds do not change after this protocol is committed. A change before unsealing is a dated amendment; a change after unsealing is a separately labelled post-hoc analysis. No declared file is edited.
