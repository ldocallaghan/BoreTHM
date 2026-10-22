# Interpreting an assessment

Start with `status.label` and `status.reasons` in the JSON you exported. The verdict applies to the specified programme and inputs. Check the reasons before interpreting an individual temperature or fluid-density margin.

## Status and conditions

| Status | Interpretation |
|---|---|
| GO | The modelled checks pass without additional conditions listed by the evaluator. |
| CONDITIONAL | Read the stated fluid, operating or equipment conditions before using the result. |
| NO-GO | At least one modelled requirement fails. The reasons identify the failures. |
| INDETERMINATE | A required numerical result is unresolved, or equipment qualification is unknown without another decisive failure. |

An overall NO-GO can coexist with an INDETERMINATE coating check. Exceeding a stated rating raises a qualification question; it does not establish a particular failure mode.

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

## Tool temperature and schedule identity

Inspect `tools.drilling` and `tools.connection` for those states, and `tools.trip_in` for run-in. The `staged` record describes a run-in with circulation pauses and reports its peak, location and staging settings. Establish which schedule a peak belongs to before comparing temperatures.

Some study exports also include a schedule search under `tools.robustness_search`, with its attempts and best peak. The best attempted peak is the lowest among the schedules searched; a wider search could find a lower one. It can differ from the reference-practice history under `tools.trip_in.staged`. Study wrappers may record these quantities under `metrics`. Inspect the fields present in your export and the study's definitions.

Coating temperatures and time above rating are separate from tool temperature. A coating history can use a different schedule from the best tool attempt. The [reference-programme comparison](../science/design-comparisons.md#independent-programme-failures) illustrates that distinction.

## Other outputs to inspect

| JSON field | What it describes |
|---|---|
| `site`, `input_warnings` | Effective target depth, sources and input uncertainties |
| `programme` | Pipe and flow, required and simulated fluid densities, thermal results and hydraulic losses |
| `cycle.cases[]` | Target stability-cycle results for each stress and strength case |
| `components` | Numerical, pressure and equipment checks contributing to status |
| `sensitivities` | The comparisons actually supplied |
| `versions`, `evaluation` | Software and runtime provenance, and the calculation mode |

A single assessment does not establish a complete flow range, a joint stress-uncertainty envelope or a probability of successful drilling. Some evaluation modes supply `flow_ceiling` or `shmin_margin`; interpret those fields only when present, using that mode's definitions. Their absence is not a numerical margin.

See the [example results](../../README.md#example-results) for the reference programmes and the [limitations guide](../science/limitations.md) for the unresolved physical assumptions.
