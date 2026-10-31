# Sourced pressure options

This archive contains the declaration inputs and model-only predictions for [development entry 10](../../../docs/science/model-development.md#31-october-2026-entry-10-sourced-pressure-options). It contains no new comparison with measured pressure or temperature.

`options.json` defines the primary friction option and separate equipment scenarios. `references.json` records their sources and applicability. It includes the entry 9 source inventory so that the unpublished installed equipment information remains distinguishable from catalogue examples. No new installed tool curve is assumed. In particular, the published 100-psi and 110-psi motor examples do not establish an uncertainty interval for an installed motor or for HALO.

`predict.py` uses entry 9's adapter to entry 8's calculation. It selects one lower-median-depth operating window per assembly by the entry 3 rule. The six variants isolate friction and equipment uncertainty without a full factorial combination. The GPDS55 and conventional FH scenarios change only the connections on 16B's 5.5-in drill pipe, including their explicitly transferred application to insulated pipe. Heavy-weight drill pipe retains its recorded bore. The zero-local-loss connection scenario is an idealised limit, with no claim that a real taper eliminates all local loss.

The measured observations in the frozen plan do not enter any calculation or reduction in this script. The script uses the recorded operating inputs and the model's output. No residual or new acceptance score is calculated. The earlier exploratory comparisons and entry 9 results were available before this declaration, as disclosed in the log.

## Prediction columns

`predictions/model-only.csv` has one row per sample and variant:

| Columns | Meaning |
|---|---|
| `well`, `assembly`, `sample_id`, `bit_ft`, `flow_gpm` | Frozen input identity and operating conditions; feet and US gallons per minute |
| `variant` | A key in `options.json`, including the entry 8 `baseline` |
| `success`, `solver_status` | Circulation convergence and the underlying boundary-value solver status |
| `spp_psi` | Calculated standpipe pressure, including the retained surface allowance |
| `bit_C`, `return_C` | Calculated bore temperature at the bit and annulus temperature at surface |
| `sensor_offset_ft`, `sensor_bore_C` | Bore proxy at the frozen comparison position: the bit on 16A; 84 ft above the bit on the four 16B trials and EOW 27/38; 22 ft on the other 16B runs |
| `friction_and_nozzle_kW` | In-hole distributed dissipation plus nozzle power, excluding the fixed motor differential face source |
| `model_hydraulic_kW` | Frozen G2 power definition: distributed dissipation plus nozzle power and the fixed raw motor differential face source; surface power and rotary work are excluded |
| Columns ending `_change` | The variant's modelled value minus the same window's baseline modelled value, in the parent column's units |
| `energy_residual_W`, `energy_flagged` | Diagnostic power residual and flag; neither changes solver success |

These 22 windows give rough effect estimates. The full scoreboard uses its own frozen samples and weights for well and assembly means. The historical fitted trial insulation remains present. Connection pitch on 16B remains the recorded 2,378 ft / 75; no new value is obtained from a pressure residual.

`predictions/manifest.json` gives the software versions and runtime, with checksums of the direct source files and output. The existing entry 8 archive identifies the inherited input sources. `predict.py --output` accepts a separate directory for rebuilding the predictions.

`plot.py` rebuilds the [16A](predictions/16a-model-only.png) and [16B](predictions/16b-model-only.png) figures directly from the prediction CSV. The axes show changes from entry 8, with no measured observations. GPDS55 and conventional FH affect only 16B; their 16A predictions equal `smooth`.


`passage_reynolds.py` rebuilds `predictions/body-reynolds.csv` from the same 22 baseline windows. It records sampled Reynolds-number extrema on plastic and apparent viscosity by physical body segment, with the sampling convention in `predictions/reynolds-manifest.json`. Drill-pipe bodies are labelled separately; `body_loss_included` identifies passages whose friction contributes to the model. `predictions/reynolds-baseline-check.csv` checks the replay against the original saved model fields without using measured observations. The prediction table and figures remain unchanged.