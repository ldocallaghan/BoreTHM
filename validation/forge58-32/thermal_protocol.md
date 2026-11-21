# FORGE 58-32 blind thermal forecast protocol

This protocol declares a blind forecast of two kinds of temperature record from FORGE well 58-32 (MU-ESW1), drilled from July to September 2017. Part A is the return temperature, the temperature of the drilling fluid measured at surface as it leaves the well, during drilling. Part B is the four pressure-temperature depth logs recorded on 3 and 4 September 2017 and the timed station at the foot of each. Part D declares a test of measurement consistency based on the energy balance, applied after the targets are read. The forecasts, the part D bounds and this protocol are committed before any of these temperature records is read, and the targets are extracted only after that commit is public.

The forecasts use BoreTHM 1.9.0 as released on PyPI. Its default physics is that of v1.8.0. The method follows the [56-32 thermal protocol](../forge56-32/thermal_protocol.md) and the 56-32 [scoring protocol](../forge56-32/scoring_protocol.md) as committed at `93bd21c`. Each change for 58-32 is listed with its reason. The [input archive](thermal/README.md) lists the files and how to rebuild them.

An earlier set-up of this test was stopped before anything was declared, because its script for reading the PT-log headers printed fields beyond the permitted metadata. That work was discarded without any commit. The inputs, protocol and forecasts here were prepared afresh by a separate run that did not see any target value, and the header fields it read are limited by the committed whitelist script.

## Data status

**Records held back.** The targets are the Pason `Temp Out` channel and every value in `58-32_PT_logs.zip`: `MU-ESW1_RUN1_PT.las` to `MU-ESW1_RUN4_PT.las`, `MU-ESW1_TIME1_PT.las` to `MU-ESW1_TIME4_PT.las` and `Nov 2 PT survey.xlsx`. In the daily reports, the end-of-well report and the mud log, every return, outlet or maximum temperature is also held back: the flow-line and mud-cooler temperatures, the mud-check outlet temperature and the maximum recorded temperature (MRT) in survey lines. The Pason `Flow Out` channel is held back with them. None of these values has been read.

**Header fields read from the PT logs.** [read_pt_headers.py](thermal/read_pt_headers.py) reads each LAS file's `~Well` section and keeps only the keys `DATE`, `STRT`, `STOP`, `STEP`, `TDL1` (total depth logged), `TLOB1` (time logger on bottom) and `TCS1` (time circulation stopped). It stops reading at the end of `~Well`, so no later section or data row is opened. For the workbook it lists the sheet names. Its output is [pt-headers.csv](thermal/pt-headers.csv).

**Earlier use of 58-32 records.** Measured records from 58-32 have been used before in this repository, in five ways. The Pason header was inspected for the pressure test (`16d5dca`), and native row 4 of `8-04-17.csv` was displayed during that inspection. The pump pressure in the 62 windows of the [pressure test](pressure-test/README.md) was read on 1 November 2026 and has been development data since. Two slow-circulation pressures in report 10 for 5 August 2017 were seen while that test was prepared ([pressure protocol](pressure-test/protocol.md)). The [thermal inventory](thermal-inventory/README.md) of `8fabdec` records log dates, depth ranges and counts of available readings, with no temperature. [Entry 11](../model-development/entry-11/README.md) swept the report sources for flow, pressure and pump records and compared report flow with Pason `Flow In` in its table A2. No return temperature, PT-log value or report outlet temperature appears in the repository or its history.

**Correction to the inventory (calculated).** The Pason files for 1 to 26 August carry their heading as 36 split cells above 18 data columns. The inventory at `8fabdec` searched for the single cells `Temp In` and `Temp Out` and, finding neither, recorded the return channel as absent in August. The split heading names `Temp`, `In`, `Temp`, `Out` in the same order as the September heading, so native column 16 is the inlet and column 17 the return in every file. The input extract already reads column 16 as the inlet in August, as the pressure test did. Part A therefore covers August and September.

**Formation reference.** `UOFU_MU-ESW1_PT118.las` in `58-32_Temp_Pres_11_08_18.zip` (SHA-256 `04de1f0aebe92e6b3963fcc43f054033d0898cab3d9a238f78d8038ec2826ec8`) was logged on 8 November 2018 to 7,539 ft, more than a year after drilling. It serves as the formation reference and lies outside the targets. Its header gives a kelly bushing (KB) elevation of 21.5 ft and a fluid level of 317 ft.

**Other wells.** 78B-32 and FORGE 16B runs 11 to 16 remain sealed and are not used. 56-32, 16A and 16B runs 1 to 10 are development data.

## Inputs

All inputs come from `1006.zip` (GDR 1006, SHA-256 `43615d79d000104ae698de23dd5aee6a981bcaa9b9a72548690556eef5fb6caa`), the PT118 archive and the existing 58-32 extracts. Times are on the Pason clock. Report times agree with it: on 3 September the report's pull out of hole from 02:30 matches the fall of Pason bit depth from 02:30.

**Flow, primary (calculated).** Pason `Flow In` multiplied by one constant, 0.70551. The constant is the median of report flow divided by the median Pason `Flow In` over the eleven September drilling-parameter rows with Pason data in entry 11's [table A2](../model-development/entry-11/results/A2-report-comparison.csv): reports 37, 38, 39, 40, 41, 43, 44, 46, 47, 48 and 49. The ratios range from 0.6474 to 0.7435, so Pason `Flow In` is 1.345 to 1.545 times the report flow on these rows. The median is report 43's ratio. Entry 11 found no recorded 2017 liner size or pump displacement; the report flow per Pason stroke fits the 2021 Rig 10 pump sheet (6.75 by 10 in) at 85 to 90 % efficiency, and Pason's implied 5.85 US gal per stroke does not.

**Flow, secondary.** Pason `Flow In` without scaling. Both forecasts are declared and scored. The window selection, the circulation clock and the circulation spells below use Pason `Flow In` as recorded, so both forecasts share the same samples.

**Pason gap, 27 to 31 August.** No Pason file exists for these days, when the hole was deepened from 5,708 ft to 6,507 ft. The circulation clock uses ten-second bins built from the daily-report operations rows for 27 to 31 August ([report-clock-intervals.csv](thermal/inputs/report-clock-intervals.csv)). Rows coded 3-2 (drilling), 3-3 (reaming) and 3-5 (circulating) carry the report flow, 414 US gal/min on each of these days; every other row carries zero flow. A drilling row deepens the hole linearly from the previous row's depth to its own end depth. Every forecast after 31 August has a wall history that passes through these days; `history_through_report_clock` marks them in the conditions table.

**Inlet temperature.** The Pason `Temp In` channel, read as Fahrenheit under the daily-report convention and converted by (F − 32)/1.8, on every day with Pason data. The fallback written for August before the split heading was identified (the mud-check inlet, or the 1 to 13 September median) is not used, because the Pason inlet exists on those days.

**Operations.** The operations extract missed every row whose clock time has a one-digit hour, including all of 3 September. [build_thermal_inputs.py](thermal/build_thermal_inputs.py) re-reads every summary report with one- or two-digit hours and writes [operations-extended.csv](thermal/inputs/operations-extended.csv), with 479 rows of which 271 are new. A description that mentions a pressure or a temperature is replaced by a suppression marker before it is written, by the extract's rule widened to cooler, flow-line, degree and outlet wording; 70 rows are suppressed. The original extract is unchanged.

**Motor heat and unknown passages.** Motor heat is zero, because the 58-32 archive has no motor differential-pressure channel; the motor is declared as a named tool with zero differential. No component of any assembly except BHA 2 has a recorded passage ID. Under the 56-32 rule, a component without a recorded bore takes the ordinary drill-pipe envelope and is flagged. Every assembly except BHA 2 is therefore ordinary pipe to the bit, with the recorded lengths. BHA 1 has no component table and is ordinary pipe throughout. BHA 2 uses the Figure 14 bores of the pressure test's [component table](pressure-test/inputs/components.csv).

**Pipe and casing.** Ordinary pipe is the pressure test's primary catalogue scenario: 4.000 in, 14.00 lb/ft, 3.340 in bore, 5.250 by 2.563 in joint, 29 in restriction and 31.5 ft pitch ([references](pressure-test/references.json)). The casings are the 20 in conductor to 84 ft (weight unreported; the 56-32 transferred 19.000 in ID), 13.375 in 54.5 lb/ft to 338 ft (end-of-well report p25; ID 12.615 in) and 9.625 in 40 lb/ft K-55 to 2,172 ft (end-of-well report p31; ID 8.835 in). The IDs are the nominal values of the Cudd Well Control Technical Data Book (2021), printed p48. Cement fills each annulus out to the next casing or the drilled hole: 17.5 in to 342 ft, 12.25 in to 2,180 ft and 8.75 in below. The casing in place is set by the section being drilled.

**Formation.** PT118 temperature in 10 ft measured-depth bins, the median of the finite readings in each bin, converted from Fahrenheit, mapped to true vertical depth with the 58-32 survey ([formation-pt118.csv](thermal/inputs/formation-pt118.csv)), and interpolated linearly by true vertical depth. The log's first bin is centred at 15 ft and its last at 7,555 ft. The end values are held beyond the log: above it this reaches 15 ft, below it no forecast depth is reached, since the deepest forecast bit depth is 7,531 ft. The log is used as recorded above the 317 ft fluid level, where the tool was in air. Its depths are taken as equal to the drilling depths, without a correction for any difference in KB.

**Mud.** As in the 56-32 protocol: the nearest recorded density and the nearest non-missing paired plastic viscosity (PV) and yield point in the same hole section, in either direction in time, with ties to the earlier sample. The sections are the 17.5 in hole to 342 ft, the 12.25 in hole to 2,180 ft and the 8.75 in hole below. The 58-32 mud extract has no sample depth, so each sample takes the hole depth at its sample time. The reported PV is referred to 48.9 °C, an assumption carried over from 56-32.

**Rock.** The FORGE rock conductivity and volumetric heat capacity of `borethm.studies.validate_forge16b`, as for 56-32.

## Part A: drilling-window return temperature

This is the headline test.

**Windows.** As for 56-32: half-hour windows centred on the hour and half hour, each the half-open interval from 15 minutes before to 15 minutes after. A ten-second bin qualifies when Pason `Flow In` is above 300 US gal/min, the bit is within 5 ft of hole depth and the rate of penetration is above 1 ft/h. A window needs at least 90 qualified bins, at least 0.5 ft of new hole and one assembly for all its bins. Its inputs are the means over its qualified bins. Only drilling windows are forecast; 56-32 forecast pauses and trips as well, but only its drilling windows were scored.

**Assembly assignment.** The 56-32 crosswalk gave each assembly its dates and depth interval. The 58-32 reports name only the assembly in the hole at the end of each report day, with no depth in or out. A run is the interval between two trips to surface, or between a trip and a gap of more than ten minutes in the Pason record. A trip to surface is at least six consecutive bins with the bit above 350 ft and above 20 % of hole depth; a bit depth deeper than −100 ft is required, so a recording fault of −4,742 ft on 23 August does not count as one. These thresholds are set by the record (calculated): during bit changes the Pason bit depth stays between 124 and 324 ft. A run takes an assembly when every report whose end of day falls inside the run names that one assembly. A run with no such report, or whose reports disagree, stays unassigned and its windows are not forecast. As for 56-32, an ambiguous identity stays unresolved: the 1 September report names BHA 13 and the 2 September report BHA 14 within one run with no trip between them, so that run is unassigned.

**Bit nozzles.** The total flow area is the sum of the circular areas of the nozzles printed in the bit table. The bit table of the day an assembly changes can still list the previous bit, so the nozzles are those printed on the run's last report day. A run whose last report prints no nozzles, such as the coring runs, has no nozzle area and is not forecast.

**Changes from the 56-32 rules.** Each is forced by a difference in the 58-32 records.

| 56-32 rule | 58-32 rule | Reason |
| --- | --- | --- |
| Assembly by the crosswalk's dates and depth interval | Assembly by run and report end of day | The reports name the assembly at the end of the day only, with no depth in or out |
| Nozzle area from the BHA sheet or bit record | Nozzles printed on the run's last report day | The bit table can lag by a day when the assembly changes |
| Mud section from the sample depth | Mud section from the hole depth at the sample time | The 58-32 mud extract has no sample depth |
| Motor heat from the measured differential | Zero motor heat | No differential channel |
| Recorded bores; blank bores filled from neighbours or the pipe envelope | Ordinary pipe envelope for every component except BHA 2 | No passage ID is recorded for any other assembly |
| Pauses and trip stages forecast as well | Drilling windows only | Only drilling windows were scored for 56-32 |
| 16A formation profile | PT118 | A native formation log exists for 58-32 |

**Measured value, after unsealing.** As in the 56-32 scoring protocol at `93bd21c`, with the native column 17 (`Temp Out`) of the Pason files. A one-second row belongs to a bin when its time truncated to ten seconds equals the bin time. The window's qualified seconds are the rows of its qualified bins. The measured value is the mean of the converted return over the qualified seconds with a valid reading. The return is read as Fahrenheit, as the inlet is, and converted by (F − 32)/1.8. Empty, non-numeric and non-finite cells and the null value −999.25 are missing.

| Rule | Applies to | Effect |
| --- | --- | --- |
| R2 | Each qualified second | A converted reading at or below 0 °C or above 120 °C is missing |
| R1 | Window | Excluded if fewer than 80 % of its qualified seconds have a valid reading |
| R3 | Window | Excluded if every valid qualified second has the same value |

R2 applies first, then R1 and R3. No other exclusion is allowed after the targets are read. As for 56-32, the scorer counts the windows whose measured return is more than 5 °C below their inlet; the count excludes no window.

**Groups.** Metrics are reported overall, by assembly, and by quartile of bit depth, of primary flow and of inlet temperature. Quartile edges come from all windows with converged predictions, and each quartile includes its upper edge.

## Part B: recovery logs

**Logs forecast.** The four depth logs RUN1 to RUN4 and the four timed logs TIME1 to TIME4. All were recorded on wireline in the open 8.75 in hole after the string was pulled on 3 September (report 39: pull out of hole for P/T surveys from 02:30, logging crew and lubricator from 08:00). The November workbook is not forecast: it was recorded on 2 November 2017, after the 7 in casing was cemented to 7,375 ft from 17 September, with no time of day, and its circulation history after 13 September lies outside the rig inputs.

**Timing (calculated).** The header `DATE` of each file is on the logging unit's clock. Report 39 records the start of the first survey at 08:50; RUN1's `DATE` is 06:49:50 on the same day. The logger clock is therefore taken as two hours behind the rig clock, and every header time is moved forward by two hours. A depth log starts at the surface at its `DATE` and reaches 6,798 ft (`TDL1`) at the `DATE` of its timed log; depth is taken as linear in time between the two. The four depth logs take 1 h 57 min to 2 h 0 min to reach bottom. The `TLOB1` entries are 1 h 1 min to 1 h 3 min after the timed log's `DATE` and are not used; `TCS1` is blank in every file. A timed log is at 6,798 ft from its `DATE` for its `STOP` seconds.

**Circulation before the logs.** The last circulation is the last spell of bins with Pason `Flow In` above 100 US gal/min and the bit within 100 ft of hole depth before the first log. It runs from 21:56:30 on 2 September to 01:48:50 on 3 September, at 6,789 ft mean bit depth and 6,800 ft hole depth. The static period of every log starts at 01:48:50. RUN1 starts 7.0 h later and RUN4 reaches bottom 24.8 h later. After 01:48:50 and before the last log ends, 222 pumped bins with the bit at 6,263 ft or shallower carry about 9,400 US gal of Pason flow, during the trip out and as short pulses with the bit at surface. These are not modelled. The circulation's assembly is the one named by the reports of 2 and 3 September, BHA 14, with the nozzles printed on 3 September (four of 13/32 in). The run rule of part A leaves this run unassigned, as above.

**Forecast.** For each forecast and each depth, the fluid column temperature at the log time, calculated as in the v1.9.0 trip column of the tool assessment (`site_evaluation.trip_temperatures`):

| Setting | Value | Source |
| --- | --- | --- |
| Circulating state | Annulus temperature and hole-wall film coefficient of the circulation solve at the end of the last circulation, for the solve's exposure at that depth | 56-32 thermal protocol (clock, exposure); `model1_coupled.annulus_films` for v1.8.0 physics, `h_dittus` for v1.7.0 physics |
| Static state | One well-mixed fluid node filling the hole, with no string, laminar film (Nusselt number 4.36) | `site_evaluation._static_node(T_rock, z, r_wall, 0)` as in `trip_temperatures` |
| Initial node temperature | The annulus temperature at the end of circulation | `pause_temperatures` (`T_node0`) |
| Wall radius | 4.375 in in the 8.75 in hole | Drilled diameter |
| Wall solver | 120 radial nodes, time-step growth 1.2 | `trip_temperatures` |
| Cased hole, above 2,172 ft | The annulus temperature at the end of circulation | `trip_temperatures` takes Model 1's annulus temperatures above the shoe |
| Cased hole, sensitivity | The same wall calculation at the 8.835 in casing bore, with rock properties | Declared sensitivity, reported beside the headline |
| Formation, rock | PT118; FORGE rock properties | Inputs above |
| Static time | Rig time of the log point minus 01:48:50 on 3 September | Timing above |

**Forecast points.** Every 10 ft of measured depth from the log's start depth (or 0 ft) to the lesser of its end depth and 6,800 ft, at the time the tool passes that depth; and every 10 s of a timed log at 6,798 ft. [log-points.csv](thermal/samples/log-points.csv) lists them.

**Measured value, after unsealing.** The curve unit is read from the file's curve section at extraction and stated. For a depth log, the measured value at a forecast depth is the mean of the finite readings within 5 ft of it; for a timed log, the mean of the finite readings within 5 s of the forecast time. A reading at or below 0 °C or above 250 °C is missing. A point with no valid reading is not scored. Depths are compared as recorded, without a shift between the logger and drilling depth references.

**Groups.** Each log separately, the four depth logs together, the four timed logs together, and the depth logs split into cased (above 2,172 ft) and open hole.

## Part C: predictors and skill

The primary prediction is BoreTHM 1.9.0 with its defaults. The comparators are the same package with `physics='v1.7.0'` and the analytical comparator of `validation/comparators/thermal.py`, each with the same inputs. In part B the analytical comparator has no static solution and supplies its circulating annulus temperature at the end of circulation, as in the 56-32 protocol; the PT118 formation temperature at each depth is reported as context.

Errors are prediction minus measurement, in °C. Skill against a comparator is 1 − RMSE(v1.9.0)/RMSE(comparator) on the same samples.

Persistence, the measured value of the preceding scored window with the same assembly, is reported for part A as context only. A forecast never sees a measured return, so persistence uses information that no forecast in this test has.

## Part D: measurement consistency

Declared now and applied after unsealing, to part A.

1. **Measured heat gain.** Q = ṁ c_p (T_return − T_inlet). The mass flow ṁ is the volume flow times the mud density at the inlet temperature and surface pressure, from BoreTHM's `fluid_props` for the window's mud. The specific heat c_p is from the same function at the mean of the inlet and measured return temperatures.
2. **Upper bound.** The hydraulic power, the window's mean Pason pump pressure times the volume flow, plus a maximum rock heat. The rock heat is the larger of two calculated bounds. The first is the v1.9.0 circulation solve with heat-maximising settings: the PT118 profile, no casing or cement (the hole open at its drilled diameter to surface), the one-hour exposure floor of `model1_coupled` at every depth, the annulus film coefficients multiplied by 1,000 and friction heating off; its rock heat is ṁ c_p (T_return − T_inlet) with c_p at the mean of the two. The second is radial conduction from the PT118 profile into a wall held at the inlet temperature for the same hour, summed over depth with only the depths where the rock is hotter than the inlet: 2πk (T_rock − T_inlet) G(t_D) per unit length, where G is the dimensionless cylinder flux of `rock_response.cylinder_flux`. Both bounds are calculated for each window and each flow and committed with the predictions. Rotary power is not in the bound; the input extract has no torque channel.
3. **Rule.** A window is energy-inconsistent when its measured Q exceeds 1.25 times the sum of the rock bound and the hydraulic power. The factor allows 10 % for the flow and 15 % for density, c_p and the two temperatures. A window without pump pressure is unclassified.

The classification uses the primary flow; the secondary flow's classification is reported beside it. The headline part A score uses all windows. The score on energy-consistent windows is the declared secondary result.

## Part E: what counts as a result

There is no pass mark. For each predictor the results are the count, bias, mean absolute error, root mean square error (RMSE), the shares of errors within 2 °C and within 5 °C, and skill, overall and by group. For context, the 56-32 deep-section result was an RMSE of 0.87 to 2.14 °C by assembly, and the FORGE 16A blind comparison gave a surface return bias of −6.00 °C and an RMSE of 6.43 °C.

## Counts before unsealing

Of 821 drilling windows, 760 have complete inputs, and all 760 have converged v1.9.0, v1.7.0 and analytical return predictions and part D bounds for both flows. Of the other 61, 52 lie in the run with no unique assembly (1 to 3 September) and 9 have no recorded nozzle set: eight on BHA 4, whose only report prints blank nozzle cells, and one on the coring assembly BHA 15. The 169 windows from 1 September onward (`58t-0653` to `58t-0821`, of which 116 are complete) have wall histories that pass through the report clock of 27 to 31 August. Part B has 2,879 forecast points: 2,723 on the four depth logs and 156 on the four timed logs. The [prediction manifest](predictions-v1.9.0/manifest.json) gives the counts by predictor.

## Frozen after declaration

The predictions, bounds, rules and thresholds do not change after this protocol is committed. A change before unsealing is a dated amendment; a change after unsealing is a separately labelled post-hoc analysis. No declared file is edited.
