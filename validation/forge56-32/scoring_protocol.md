# FORGE 56-32 return temperature scoring protocol

This protocol scores the [v1.8.0 model-only predictions](predictions-v1.8.0/README.md)
recorded in commit `ba564450f2129fa1adfe522cc3880ce651e4a1d9` on
7 November 2026. It was written and committed before any 56-32 return
temperature value was read. The [scorer](score_thermal.py) implements it.
The [thermal protocol](thermal_protocol.md) defines the windows and the
forecast. Its MWD availability audit limits the test to return
temperature.

**Forecast record.** The manifest hashes were checked against
`ba56445`, where every listed file matches, and `predictions.csv`
matches `predictions_sha256` at the head of the branch. After the
forecast, entry 15 commits `711707f`, `03ee02e`, `e5d1d73` and `16b2b44`
changed `src/borethm/wall_thermal.py`. The return predictions come from
the circulation solve in `model1_coupled.py`, which is unchanged. The
committed `predictions.csv` is the scored file and is not regenerated.
The scorer refuses a predictions file whose hash differs from the
manifest.

**Measure.** Only drilling windows are scored. A window's qualified
10 s bins are those selected by the thermal protocol: valid flow above
300 US gal/min, bit within 5 ft of hole depth and on-bottom penetration
above 1 ft/h, within the half-open half hour centred on the window time.
Their number must equal `qualified_bins` in the
[conditions table](predictions-v1.8.0/conditions.csv). A 1 s archive row
belongs to a bin when its source time, truncated to 10 s, equals the bin
time. These rows are the window's qualified seconds. The measured value
is the mean of the converted `Temp OUT (Degrees)` over the qualified
seconds with a valid reading. Empty, non-numeric and non-finite fields
and the Pason null value −999.25 are missing. Under rule R2 below, a
converted reading at or below 0 °C (32 °F) or above 120 °C is also
missing. Pauses, connections and trip stages are
not scored: their return values refer to the preceding circulation,
and 56-32 has no usable downhole temperature in the selected windows.

**Unit.** The archive header labels `Temp IN` and `Temp OUT` as
`Degrees` and has no units row. The thermal protocol reads the Pason
inlet as Fahrenheit under the daily report convention. The extract
[README](README.md) records the same label for both channels. The
return is read under the same convention and converted to °C as
(F − 32)/1.8, recorded in the targets file as `(F-32)/1.8`. The
`report_inlet_F` field of the [mud table](mud_reports.csv) is the
daily report Mud Information column headed "Temp" over "In", for
example in `56-32 Daily Drilling Reports.zip!DailyReportDetailRpt_210210081912.pdf`,
page 1. The neighbouring "Out" column is not extracted.

**Targets file.** The extraction writes
`targets/return_temperature.csv` with one row for each window that has
converged v1.8.0, v1.7.0 and analytical return predictions, and no other
rows. Its columns are `sample_id`, `qualified_bins`,
`qualified_seconds`, `finite_seconds`, `mean_C`, `min_C`, `max_C` and
`unit_conversion`. The finite seconds are the qualified seconds with a
valid reading after rule R2. The mean, minimum and maximum are over
those seconds; the minimum and maximum are needed for rule R3. The
scorer stops without output if a predicted window is missing, an extra
window is present, a bin count differs from the forecast inputs, the
conversion differs from the one stated here, or a value lies outside
the R2 range.

**Validity.** Rule R2 applies to seconds. Rules R1 and R3 apply to
windows, after R2.

| Rule | Applies to | Effect |
| --- | --- | --- |
| R2 | Each qualified second | A converted reading at or below 0 °C (32 °F) or above 120 °C is missing. |
| R1 | Window | Excluded if fewer than 80 % of its qualified seconds have a valid reading. |
| R3 | Window | Excluded if every valid qualified second has the same value. |

A single reading does not exclude a window. Every excluded window is
listed in `scores/windows.csv` with each rule that applies. Windows without converged predictions are listed with
their input or calculation status and are not scored. No other
exclusion is allowed after the targets are read.

**Unit check.** The scorer counts the scored windows whose converted
return is more than 5 °C below the window's converted inlet
temperature, `inlet_C` in the conditions table. The count is reported
in `scores/counts.csv` and each such window is marked in
`scores/windows.csv`. The check excludes no window.

**Predictions scored.** The v1.8.0 return is the primary prediction.
The comparators are the v1.7.0 return, the analytical comparator's
return and persistence. Persistence is the measured value of the
preceding scored window, in time order, with the same assembly. The
first scored window of each assembly has no persistence value.

**Metrics.** Errors are model minus measured, in °C. For each predictor
the scorer reports the count, bias, mean absolute error, root mean
square error (RMSE) and the fractions of windows with an absolute error
of at most 2 °C and at most 5 °C. The three model predictions are
compared on all scored windows. All four predictors are also compared
on the scored windows that have a persistence value. The skill of
v1.8.0 against a comparator on the same windows is
1 − RMSE(v1.8.0)/RMSE(comparator). For v1.8.0 the same metrics are
reported for each assembly and for each quartile of bit depth, flow and
inlet temperature. The quartile edges are computed from the input values
of all windows with converged predictions, and each quartile includes
its upper edge.

**Outputs.** `scores/summary.csv` holds the metrics and skill.
`scores/windows.csv` holds one row for each drilling window, with its
inputs, status, rules, measured value, predictions and errors.
`scores/counts.csv` holds the window counts. `scores/sources.json`
records the hashes of the predictions, targets and scorer. The figures
are measured against predicted for each predictor, and the v1.8.0 error
against bit depth, time and flow, with one panel for each assembly.

**Expectation.** The Phase 0
[gap coverage table](../model-development/phase-0/gap-exposure.md),
labelled inferred, gives development return residual intervals for
266 of the 422 return forecasts. Their endpoints span −12.0 to +2.9 °C.
The per-window intervals are in the
[conditional residual ranges](../model-development/phase-0/56-32-conditional-residual-ranges.csv).
These envelopes describe overlapping development cases and are not
calibrated uncertainty intervals. The FORGE 16A blind comparison gave
a surface return mean error of −6.00 °C and an RMSE of 6.43 °C at 135
samples ([validation](../../docs/science/validation.md#forge-16a-blind-circulation-comparison)).
Both are context. Neither is a pass mark.

**Frozen after unsealing.** The model, the predictions, this protocol
and the scorer do not change once the targets are read. If the scorer is
found to be wrong after unsealing, the correction is a separate commit
and both results are reported.

**Counts before unsealing.** Of 422 drilling windows, 402 have a
complete input status and converged v1.8.0, v1.7.0 and analytical
return predictions. Nineteen have no uniquely assigned circulation
assembly and one lacks a required input. All 422 have finite `Temp OUT`
availability within the half-hour window in the conditions table. The
finite count over qualified seconds is taken at extraction.

**Tests.** The [scorer tests](../../tests/test_forge5632_scoring.py)
build synthetic targets from the committed predictions with a known
offset and noise, and windows that trip each rule. They are created
during the test and are not stored as data.
