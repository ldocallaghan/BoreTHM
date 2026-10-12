# Interpreting an assessment

Start with `status.label` and `status.reasons`. A verdict belongs to the evaluated programme and assumptions. Then inspect the components that decide it; an overall NO-GO can coexist with unresolved coating qualification.

## Status and conditions

| Status | Interpretation |
|---|---|
| GO | The modeled checks pass without additional conditions listed by the evaluator. |
| CONDITIONAL | Read the stated fluid, operating or equipment conditions before using the result. |
| NO-GO | One or more modeled gates fail for this programme and these assumptions. |
| INDETERMINATE | A required numerical result is unresolved, or an equipment qualification is unknown without another decisive failure. |

## Find the deciding outputs

| JSON field | What to inspect |
|---|---|
| `site`, `input_warnings` | Target depth, input sources and limitations in the evidence |
| `programme` | Pipe, flow and units; required versus simulated densities; temperatures and hydraulic losses |
| `cycle.cases[]` | Target stability-cycle verdict for each stress/strength case, including connections and the trip |
| `windows.drilling_fluid`, `windows.trip_fluid` | Surface-density bounds, whether a range exists, and the depths, states and cases that set each bound |
| `tools` | Tool temperatures, schedule identity and separate coating qualification |
| `components` | Numerical, pressure, hydraulic and equipment checks contributing to the overall status |
| `sensitivities` | The named comparisons actually supplied; these are not a complete uncertainty analysis |
| `versions`, `evaluation` | Code/runtime provenance and calculation mode |

The CLI prints a subset of the JSON detail. Its label “Common windows” corresponds to the density bounds described below. The reader terminology does not rename the stored fields.

## Pressure units and density bounds

A mud-weight window is the allowable range of fluid density: enough pressure for borehole stability while staying below the modeled fracture-pressure limit. The programme combines the constraints across evaluated depths, operating states and stress/strength cases, separately for drilling and trips.

Target `drill_SG` and `drill_SG_hi` in `cycle.cases[]` are static-column SG-equivalent pressures with the existing friction/backpressure treatment. They are local diagnostics, not surface mud-density prescriptions. A favourable drilling interval does not by itself determine the stability-cycle verdict, which also checks connections and the trip.

The `lo` and `hi` values under `windows` are surface densities in kg/m³. Divide by 1,000 to express surface SG at 20 °C. Width is upper minus lower. If the minimum exceeds the maximum, no surface density satisfies both limits. Attempted densities for that case are calculation inputs, not feasible prescriptions. The `lo_by` and `hi_by` records identify the controlling constraint.

The target-case table reuses a site's reference thermal/hydraulic solution across stress/strength cases. It is not a coupled redesign for every scenario. Open target intervals neither prove one fluid works throughout the hole nor prove the attempted fluid lies inside the local interval.

## Tool schedules and coating qualification

The reference-practice run-in history and the best attempted schedule search are distinct. The retained reference JSON reports the practice history under `tools.trip_in.staged`; the settings-matched base trials in the [design-study evidence](../../results/v1.3.4/ci/38186784798-1/levers/) record `metrics.tool_peaks_C`, `practice_run_in_peak_C` and `run_in_search`. Best attempted means the lowest peak among those saved attempts, not an optimum over all schedules.

Coating histories are separate from the best attempted tool schedule. Exceeding a stated rating leaves qualification INDETERMINATE; it is not a validated prediction of a particular failure mode.

## What a single assessment does not provide

The five retained reference JSON files contain neither `flow_ceiling` nor `shmin_margin`. Some historical or optional evaluation modes can supply those fields; check whether they exist and what was evaluated before interpreting them. The current reference result does not establish a complete flow range, joint stress uncertainty or overall probability of successful drilling.

See the [example results](../../README.md#example-results) for saved assessments, and [limitations](../science/limitations.md) for the open physical questions.
