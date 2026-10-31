# Sourced pressure options

This archive contains the declaration inputs, model-only predictions and subsequent development comparison for [entry 10](../../../docs/science/model-development.md#31-october-2026-entry-10-sourced-pressure-options). The original predictions remain under `predictions/`; the scored comparisons are under `results/`.

`options.json` defines the primary friction option and separate equipment scenarios. `references.json` records their sources and applicability. It includes the entry 9 source inventory so that recorded equipment information remains distinguishable from catalogue examples. No new installed tool curve is assumed. In particular, the published 100-psi and 110-psi motor examples do not establish an uncertainty interval for an installed motor or for HALO.

`predict.py` uses entry 9's adapter to entry 8's calculation. It selects one lower-median-depth operating window per assembly by the entry 3 rule. The six variants isolate friction and equipment uncertainty without a full factorial combination. The GPDS55 and conventional FH scenarios change only the connections on 16B's 5.5-in drill pipe, including their explicitly transferred application to insulated pipe. Heavy-weight drill pipe retains its recorded bore. The zero-local-loss connection scenario is an idealised limit, with no claim that a real taper eliminates all local loss.

The prediction script uses the recorded operating inputs and the model's output. It excludes measured targets from its calculations and reductions. The earlier exploratory comparisons and entry 9 results were available before this declaration, as disclosed in the log.

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

## Scoring archives

`score.py` applies the declared options through the entry 8 adapter and the unchanged frozen scoreboard reductions. Each candidate directory under `results/` contains its circulation samples and the six-gap reductions, with a manifest identifying sources and calculation reuse. The before comparison is the archived entry 8 result at film multiplier 1.0. Its original CSVs are preserved, and their loaded values are checked against a fresh reduction before use. Every original sample remains in the coverage count.

The circulation comparison retains the recorded mud protocol, PV reference of 26.7 °C and cumulative exposure clock. The rotary sources remain those of entry 8. The run-in calculation retains its observed initial internal-fluid state and static-history convention, with Dittus-Boelter films. Its conditioning circulation receives the candidate pipe friction; the zero-local-loss connection option also applies to that conditioning geometry. The transient equations are unchanged. The GPDS55 and conventional FH options alter only 16B geometry, so their 16A circulation and run-in results reuse the smooth candidate explicitly. `calculation_basis` and the manifests identify reused rows. The historical trial-insulation fit remains disclosed.

`trip_slopes.py` evaluates only the six declared entry 9 primary groups. Their window membership and temperature treatment are frozen. The same grouping and regression functions produce `results/secondary/`, with EOW 19 labelled as added insulated pipe. The before result is checked against the entry 9 slopes. These ratios are secondary measures and do not enter the acceptance rule.

`compare.py` records before and after for every frozen gap in `results/comparison.csv`. Its paired-coverage check uses the actual successful sample or event identifiers. `summary.csv` contains well/group summaries; `sample-changes.csv` and `assembly-changes.csv` retain changes at their stated levels. `prediction-checks.csv` checks the declared model-only effects at their saved windows. `decision.json` applies the declared primary acceptance rule without selecting an equipment scenario. `pressure-uncertainty.csv` records the unavailable installed-tool band beside each assembly; its endpoints remain blank. `plot_scores.py` produces figures from the saved comparison files.

The scoring scripts accept an output directory. `score.py` also requires a separate scratch directory for intermediate batch files and supports resuming saved circulation rows. A completed candidate archive is reused only after checking its result hashes. No coefficient is obtained from a residual, and no package default is changed by these scripts.

## Decision recorded 31 October 2026

Smooth Colebrook met the declared acceptance rule. The maintainer retained it as an available package option without adopting it into the working calculation or the default. The working calculation remains entry 8 with Blasius pipe friction, and the package default remains Blasius with zero roughness. Later entries continue comparing against entry 8. The [development log](../../../docs/science/model-development.md#interpretation-and-recommendation) records the dated decision beside the recommendation to adopt. `results/decision.json` preserves the numerical checks and recommendation at scoring; the result archive is unchanged.

In `results/secondary/slopes.csv`, the measured/modelled `slope_ratio` is 0.95–1.15 for the five regular-pipe GPDS55 groups. EOW 19's insulated-increment ratio is 0.97 under smooth Colebrook with EIS joints and 0.59 under GPDS55, which transfers the 3.5-in joints to insulated pipe. These scored development comparisons cannot identify installed connections or select a variant. The log sets out pipe-specific alternatives and their separating checks.
