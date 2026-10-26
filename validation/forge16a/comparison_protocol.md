# FORGE 16A comparison protocol

S1 input definition, 26 October 2026, following the reviewed S0 inputs and subsequent rulings. This method was fixed before calculating a thermal prediction or error. The S0 version is preserved in the private input-review evidence.

## Calculation identity and inputs

Use the existing calculation at commit `b9a8a93f49f1b53b7bd71a713b8ca4988e7c21c6`, described as `v1.5.0-1-gb9a8a93`. Use the 16B study's treatment of geometry construction, steel/cement layers, friction heating, motor differential-pressure face heat, nozzle area and exposure from the circulation clock. Substitute the recorded 16A inputs. Do not change a package calculation, default, constant, stored regression result or tolerance.

The primary annulus-film multiplier is 1.0. Use 0.75 as the previously fitted 16B sensitivity. Fit nothing on 16A. Use the existing 16B rock inputs: conductivity `(2.149 + 2.341 + 3.002) / 3 = 2.4973333333 W/(m K)` and volumetric heat capacity `((2680 + 2600 + 2650) / 3) * ((864.8 + 862.3 + 1091.1) / 3) = 2,483,147.3333 J/(m3 K)`. The conductivity endpoints are 2.041 and 3.087 W/(m K).

Use the 216-day temperature log as primary and the 57-day log only within its measured depth coverage. Convert MD to TVD with the actual survey. The original workbook polynomial TVD is kept for provenance. Beyond 10,740 ft MD, keep the 216-day endpoint constant in the primary case. As a separate sensitivity at primary film and rock conductivity, extend its final temperature using the endpoint-to-endpoint mean gradient over its final 500 ft MD, converted to a TVD gradient with the survey. List every affected sample. No 57-day extrapolation is used. Continue the final measured inclination, 68.6 degrees, beyond 10,955 ft MD.

Use the 16A casing and BHA tables, with the 8.75-inch lower hole. Ordinary drill pipe is 5-inch OD, 19.5 lb/ft, 4.276-inch ID. BHA 18 and 23 list 1,380 and 1,384.33 ft of HWDP with 3.25-inch ID; retain that bore for the heavy-weight sections. Other listed HWDP keeps its reported bore. BHA 42 lists ordinary-pipe sections of 2,185.39 and 1,226.43 ft with 3.25-inch ID. Their classification is unresolved: use 4.276-inch ID as primary and repeat BHA 42 with 3.25-inch ID in those two identified sections, leaving the unlisted upper ordinary pipe at 4.276 inches.

The 13-3/8-inch 68 lb/ft casing has nominal ID 12.415 inches; the 9-5/8-inch 40 lb/ft casing has nominal ID 8.835 inches. The latter shoe is 5,110 ft MD; daily tables sometimes give 5,113 ft. The 13-3/8-inch shoe is 1,629 ft; conductor shoe 130 ft. Derive the 20-inch conductor wall from 54 lb/ft and steel density 7,850 kg/m3. Its external cement thickness is unreported: put the shallow rock interface at conductor OD, explicitly omitting that unknown external cement layer. Use the reported 17.5- and 12.25-inch casing boreholes, nested steel/cement layers and the 16B conductivities.

Use length-weighted OD and ID for the compact BHA, following the 16B representation; keep long HWDP and ordinary-pipe sections separate and in component order. Explicit nominal sizes in descriptions resolve overlapped OD cells. Missing motor bore uses the 1.25-inch bore of matching 16A motors. Missing MWD/sensor bore uses 3.25 inches from matching 16A components. Include bit length in the compact assembly with motor bore; nozzle area is treated separately. These are dimensional assumptions, with every substituted cell recorded in string-inputs.csv. Use the 9 December drilling table for both BHA 35 runs. Do not use the subsequent packer table.

Use the arithmetic mean of the run-associated daily mud observations for mud weight, PV and YP, with report provenance saved. Treat reported mud weight as surface density at 20 degrees C; the report's measurement temperature is unknown. Pass the existing mass-conserving Mud object to the unchanged circulation solver. PV is converted from cP to Pa s and YP from lbf/100 ft2 to Pa. Calculate nozzle area from the documented jet counts: BHA 34 uses 3x13 plus 4x12; the other eight use 3x14 plus 3x13. Rounded report areas are 0.830 and 0.840 in2 respectively.

## Sensor quantity

For each available channel, report both bore and annulus temperatures at the bit and at 40 ft above it. This bracket covers the reported PUK-sub span without assuming an element position. BHA 42 lacks a top-sub channel; preserve that absence.

If the source establishes bore-fluid sensing, compare with modelled bore temperature at the sensor MD. If body sensing is specified, or the sensing medium remains unknown, show both bore and annulus temperatures at that MD. Do not choose one based on its error. Do not add a sensor-transfer or electronics model. A required new model is separate work.

Report the full minimum-to-maximum range of those four predictions for each channel, with all four error metrics retained. Separately report the position spread within each medium and the bore/annulus spread at each position. Do not score the closest endpoint as a primary result.

## On-bottom sampling

Use the source timestamps as recorded. A fixed -12 to +12 integer-hour check against independent depth and flow selects zero offset for every run. No time shift is selected from temperature agreement. Time-zone identity is unconfirmed; the clocks are used as a shared recorded clock.

Use the extraction's predeclared flow-valid interval of 0 to 2,000 gal/min. Select raw drilling observations with flow above 300 gal/min, on-bottom flag true, bit within 5 ft of hole depth and penetration above 1 ft/h. Invalid or missing flow is excluded. The full history's circulation clock uses the fraction of valid observations above 100 gal/min per minute. Missing coverage is retained as missing and must be reported before constructing exposure.

Choose sample centres at least 30 minutes apart, starting at the first qualifying observation in each run. A central bin must have complete valid flow, flow above 300 gal/min, the on-bottom flag and positive penetration above the threshold. Average measured sensor temperature over the centred 30-minute interval, using only drilling-qualified values. The extract preserves these means and counts separately from the complete thermal record. Use count weighting to reconstruct the source-observation mean. Require at least 15 minutes of qualifying coverage within the window, estimated from the 10-second bin fractions, and report coverage and the number of observations for each channel. Missing top-sub data do not remove an otherwise valid bit-box comparison.

Model inputs at each centre come from the local depth, flow and motor differential-pressure record, with inlet from the one-foot mud log at the depth being drilled. The mean observed temperature over a window is distinct from the model solution at its centre. This measured-window definition is specific to 16A; the 16B study samples its surface record every 30 minutes and compares with published run observations. No parameter will be selected by either window's errors.

## Inlet, return and disturbed intervals

Treat the mud-log temperatures as Fahrenheit, supported by its graphical annotations and the standard rig file's stated temperature unit. Interpolate valid inlet values at drilled MD without tuning smoothing to the prediction errors. The rig mud-temperature channel is outlet-like and cannot supply inlet temperature. For later transients use the last mud-log inlet value before the event, with its depth/time association recorded. Use the last hole depth drilled before the event to locate that value. Surface cooling has no additional fitted heat-removal term.

For return temperature, compare the model's surface annulus outlet with mud-log `TEMPOUT` at the corresponding drilled depth. Keep flowline-versus-wellhead measurement uncertainty explicit. For whole-well comparisons, bit depth must be inferred from hole depth during positively flagged drilling where the rig bit-depth channel is missing. Report those samples separately from the Sanvean-supported intervals.

Flag the report-documented 7 November seepage-loss interval for the whole-well return comparison. The timing/depth extent needs a report-based association before samples are labelled. Flag both BHA 35 deployments for the documented drill-pipe washout concern and report totals with and without those flagged runs. Do not infer formation loss from a pressure drop, a lost bit component or the word "lost" alone. No empirical loss correction is fitted.

## Metrics and later phases

Report measured and modelled values side by side. Signed error is model minus measurement. Per channel and run, report measured/modelled means, mean signed error, mean absolute error, RMS error and maximum absolute error, in degC and degF. Overall metrics pool all accepted observations, with their counts explicit. Keep bore and annulus comparisons separate wherever the sensing medium is unresolved.

The primary percentage metric uses absolute Kelvin temperature: `MAPE_K = 100 * mean(abs(Tmodel_K - Tmeasured_K) / Tmeasured_K)`. The temperature unit is part of the metric's definition. Comparing published percentage errors requires matching the measured quantity and temperature unit. The external literature comparison remains to be checked against the paper itself.

Run the full film (1.0, 0.75), rock conductivity (central and two endpoints) and formation-log grid for the nine Sanvean runs, with the 57-day log restricted to bit depths within its coverage. Tail-gradient and unresolved-pipe sensitivities are additional runs at primary film, rock conductivity and 216-day log. Broader rig return-only samples use the primary configuration. The latter require flow over 300 gal/min, positive on-bottom flag, ROP above 1 ft/h, a unique depth-overlapping reviewed bit/BHA and a timestamp within one day of that assembly's Sanvean coverage. Hole depth supplies inferred bit depth. Other rig intervals are excluded with counts and reasons; this is a partial whole-well comparison. Do not invent dimensions for earlier assemblies. A 7 November seepage-loss comparison will consequently be unavailable if those earlier assemblies remain unresolved.

As in 16B, the exposure clock counts observed circulation only. Missing circulation fractions contribute zero observed seconds; missing hole depth is forward-filled with the running maximum. Report both missing counts. The returned final solver status and seed status are saved for every attempted case. Unconverged predictions are excluded from error metrics and listed separately. The complete sample/case plan and input hashes are frozen before solving.

Run-in and pumps-off work follows a separate circulation-results review. Use the existing transient functions and stated static treatments without a refit or new sensor model. Their event selection and comparison quantities will be shown before those prediction errors are examined. Documentation integration and regression tests follow the subsequent results reviews. No merge or release is part of this input review.
