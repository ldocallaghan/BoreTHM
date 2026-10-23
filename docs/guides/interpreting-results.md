# Interpreting an assessment

Start with the reading at the top of the report, also exported as `reading`
in JSON. Its controlling constraint restates the first reason in `status`.
Follow that into the detailed component checks, pressure bounds and
equipment histories. The verdict applies to the specified programme and inputs.

## Reading the opening block

| Entry | What it reports |
|---|---|
| Calculation | Whether the numerical solves, fluid iteration and pressure-bound refinement converged; other entries are not assessed when this fails |
| Scenarios at the target | Counts of stress and strength cases passing each target stability check, including any fluid conditions; each case combines one stress profile with one strength |
| Whole programme | Whether one drilling fluid and one trip fluid meet the pressure limits across every evaluated depth, state and case; closed windows name the lower and upper bounds and their source cases and depths |
| Equipment | The tool against its temperature limit, and the coating against its stated rating |

For example, the [Larderello reference assessment](../../results/v1.3.4/checkpoint-1/larderello.json)
has open pressure windows and passes the equipment checks. Its verdict is
CONDITIONAL on the specified fluids:

> **Calculation:** Valid: the reported numerical checks converged.
>
> **Scenarios at the target:** Cases passing target stability, including stated fluid conditions: drilling 5/5; connection 5/5; connection, fresh rock 5/5; trip 5/5.
>
> **Whole programme:** One drilling fluid and one trip fluid satisfy the pressure limits at every evaluated depth, state and case. Surface densities at 20 C: drilling fluid 1.036 to 1.230 SG; trip fluid 1.094 to 1.331 SG. Conditions: A drilling fluid of 1.036 SG at surface. A trip fluid of 1.094 SG at surface.
>
> **Equipment:** The tool passes its 200 C temperature check. The TK-Drakon coating reaches 85.5 C against its stated 204 C rating (within rating).
>
> **Controlling constraint:** A drilling fluid of 1.036 SG at surface.

The case counts describe selected scenarios, with the programme's thermal
and hydraulic solution reused across them. They supply no probability of
success. The whole-programme entry combines the density constraints through
the hole, so all target cases can pass while no fluid works at every depth.
Any failing pump or reference-rig capacity check is reported there too.

## Status precedence and conditions

The evaluator applies these checks in order:

| Order | Check | Status when it applies |
|---|---|---|
| 1 | A circulation solve, fluid iteration or pressure-bound refinement did not converge | INDETERMINATE; physical checks are not assessed |
| 2 | A decisive pressure, tool or pump-pressure check fails | NO-GO; this takes precedence over unresolved coating qualification |
| 3 | Coating temperature exceeds its stated rating and qualification is unknown, without another decisive failure | INDETERMINATE |
| 4 | Additional fluid, operating or equipment conditions apply | CONDITIONAL; the reasons name them |
| 5 | The assessed checks pass with none of those conditions | GO |

In the default whole-hole calculation, either closed fluid window produces
NO-GO. GO records the assessed checks; it supplies no probability of success
or validation of deep-site input assumptions.

A CONDITIONAL result can require different actions:

| Condition | What to inspect |
|---|---|
| Prescribed drilling or trip fluid | The surface density in the status reason and the corresponding whole-hole window |
| Tool circulation schedule | The connection or run-in schedule and its temperature history |
| More pump capacity than the reference rig | Required flow and standpipe pressure in `components.pumps` |
| Hole cleaning below the FORGE reference velocity | The annular velocity and its comparison basis in `components.hole_cleaning` |
| Frictionally inadmissible cases excluded | The excluded labels in `components.admissibility` and the stress assumptions behind them |

An overall NO-GO can coexist with an INDETERMINATE coating check. Exceeding a
stated rating raises a qualification question; it does not establish a
particular failure mode.

## A worked JSON excerpt

This excerpt selects one of the nine target cases and part of the whole-hole pressure results from a [saved Soultz assessment](../../results/v1.3.4/ci/38186784798-1/reference/soultz.json). Extra fields are omitted and the exported numbers are unchanged. It uses the base assumption of immediate breakout formation.

```json
{
  "status": {
    "label": "NO-GO",
    "reasons": [
      "the wall is not held: drilling, trip, drilling common window, trip common window",
      "tool: running in needs continuous circulation"
    ]
  },
  "programme": {
    "drilling_prescribed_rho_surface": 1378.9248543105493,
    "drilling_simulated_rho_surface": 1378.8398200810834
  },
  "cycle": {
    "cases": [
      {
        "label": "SHmax upper bound (1.05 Sv), lab UCS 100",
        "drill_SG": 1.3128721484030792
      }
    ]
  },
  "windows": {
    "drilling_fluid": {
      "lo": 1378.9248543105493,
      "hi": 1312.558895990804,
      "open": false
    },
    "trip_fluid": {
      "open": false
    }
  }
}
```

The overall status is NO-GO. Its reasons identify the trip and drilling pressure failures and a tool-temperature failure. The target case's `drill_SG` is approximately 1.313 SG-equivalent. The programme's required drilling-fluid surface density is approximately 1,379 kg/m³ at 20 °C. Its simulated density is recorded separately; neither is an allowable prescription when the window is closed.

Across the whole hole, the required minimum drilling-fluid density is approximately 1,379 kg/m³ but the permitted maximum is approximately 1,313 kg/m³. Those bounds cross, so `open` is false: no drilling-fluid density satisfies both. The trip-fluid window is also closed. A target pressure requirement cannot be used as a whole-hole prescription without these checks.

## Pressure units and density bounds

A mud-weight window is the allowable range of fluid density: enough pressure for borehole stability while staying below the modelled fracture-pressure limit. The programme combines constraints across evaluated depths, operating states and stress and strength cases, separately for drilling and trips. The terminal report calls these combined bounds “Common windows”.

The density quantities answer different questions:

| Quantity | Unit and meaning |
|---|---|
| `cycle.cases[].drill_SG` | SG-equivalent at the target, including the connection checks. Pressure is expressed as an equivalent static column, with the evaluation's friction and wellhead-pressure treatment. |
| `cycle.cases[].drill_SG_hi` | The target upper drilling pressure limit in SG-equivalent. An open local interval does not establish the full-cycle verdict. |
| `drill_rho_surface` in a study's case record, when supplied | Surface density at 20 °C matching that target case's drilling requirement, in kg/m³. The [timing reports](../science/breakout-timing.md#paired-results) supply this additional field. |
| `programme.drilling_prescribed_rho_surface`, `.drilling_simulated_rho_surface` | Whole-programme required and actually simulated drilling-fluid surface densities, in kg/m³ at 20 °C. |
| `windows.drilling_fluid.lo`, `.hi` | Lower and upper surface-density bounds over the evaluated hole for the drilling fluid, in kg/m³ at 20 °C. |
| `windows.trip_fluid.lo`, `.hi` | Corresponding bounds for the trip fluid. |
| `lo_by`, `hi_by` within each window | State, stress and strength case, and measured depth that sets the bound. |

Divide a surface density by 1,000 kg/m³ to obtain surface SG at 20 °C. A target SG-equivalent value represents pressure at depth; its numerical value can differ from the surface SG because the fluid temperature and pressure vary along the column.

A positive target interval does not prove that a fluid works throughout the hole. The target stability-cycle verdict also checks connections and trips. The case table reuses the programme's thermal and hydraulic solution across the stress and strength cases; it does not redesign the coupled programme separately for every case. Where whole-hole bounds cross, reported attempted densities are calculation inputs and cannot be prescribed.

## What sets the upper pressure bound

The full evaluation obtains its local pressure bounds from `mud_window`.
The upper bound is minimum horizontal stress, Shmin, less the model's
0.05 SG margin. Circulating annular friction and the trip surge allowance
further restrict the permitted static column in their respective states.
The evaluator converts these state pressures to surface-density bounds
using the column temperatures, wellhead pressure and fluid properties,
then intersects them across depths and cases.

Tensile-fracture initiation at the wall is a separate diagnostic from the
effective hoop-stress check. It does not replace the Shmin-based upper bound
or independently set the full evaluation's status. The
[local mud-window API](../api.md#mud_window) gives the equations and pressure
conventions. These checks have different meanings: initiation of a wall
fracture and a fluid-pressure limit for the evaluated programme.

## Tool temperature and schedule identity

Inspect `tools.drilling` and `tools.connection` for those states, and `tools.trip_in` for run-in. The `staged` record describes a run-in with circulation pauses and reports its peak, location and staging settings. Establish which schedule a peak belongs to before comparing temperatures.

Some study exports also include a schedule search under `tools.robustness_search`, with its attempts and best peak. The best attempted peak is the lowest among the schedules searched; a wider search could find a lower one. It can differ from the reference-practice history under `tools.trip_in.staged`. Study wrappers may record these quantities under `metrics`. Inspect the fields present in your export and the study's definitions.

Coating temperatures and time above rating are separate from tool temperature. A coating history can use a different schedule from the best tool attempt. The [reference-programme comparison](../science/design-comparisons.md#independent-programme-failures) illustrates that distinction.

## Other outputs to inspect

| JSON field | What it describes |
|---|---|
| `site`, `input_warnings` | Reported site inputs, supplied provenance and validation warnings |
| `site_file`, when supplied | Input file path and SHA-256; keep the matching file and measured data with the result |
| `reading` | The opening explanation of numerical validity, target cases, whole-programme checks and equipment |
| `programme` | Pipe and flow, required and simulated fluid densities, thermal results and hydraulic losses |
| `cycle.cases[]` | Target stability-cycle results for each stress and strength case |
| `components` | Numerical, pressure and equipment checks contributing to status |
| `sensitivities` | The comparisons actually supplied |
| `versions`, `evaluation` | Software and runtime provenance, and the calculation mode |

A single assessment does not establish a complete flow range, a joint stress-uncertainty envelope or a probability of successful drilling. Some evaluation modes supply `flow_ceiling` or `shmin_margin`; interpret those fields only when present, using that mode's definitions. Their absence is not a numerical margin.

See the [example results](../../README.md#example-results) for the reference programmes and the [limitations guide](../science/limitations.md) for the unresolved physical assumptions.
