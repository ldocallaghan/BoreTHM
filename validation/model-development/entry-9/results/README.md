# Pressure diagnosis results

The declaration is commit `38c352c45b94e3276ec80bc5c747468c5c37b561`. This archive compares the existing calculation with development observations. No new correction or fitted coefficient enters it. The [development log](../../../../docs/science/model-development.md#31-october-2026-entry-9-pressure-diagnosis-results) presents the findings and their limits.

## Calculation

`diagnose.py` imports the entry 8 adapter. Every pressure calculation explicitly selects `herschel-bulkley-erge`, the entry 6 no-yield rheology, PV referenced to 26.7 °C and surface case 5. The package default is unchanged.

The frozen geometry, nozzles and period mud are supplied by the nearest recorded scoreboard input in the same assembly. This is a transfer of period inputs to trip observations and is identified by `input_sample_id` in `windows.csv`. Assemblies missing from that frozen geometry/mud plan remain excluded. The string is constructed at a depth covering the recorded hole, then trimmed from its upper end to the measured bit depth. This retains the bottom components in order. The trial strings retain the existing aggregate treatment, including the partial insulated-pipe layout. The historical insulation-conductivity fit is retained and disclosed as inherited calibration; no new fit is made.

For 16B, mass flow comes from recorded surface volume flow and mud density at measured inlet temperature. Isothermal pressure properties use mean inlet/return temperature. For 16A, both temperature limits use the same mass flow: recorded surface volume flow times the recorded nominal surface mud density, whose package reference is 20 °C. The inlet temperature is unknown, so this is a stated mass-conversion approximation. The surface-loss object is evaluated at this same recorded surface flow and inlet/reference density in every isothermal calculation. Its term replaces the helper's uniform-temperature surface term; downhole gradients are unchanged. This keeps a hot downhole hypothesis from defining an atmospheric surface state. A hot downhole temperature cannot define an atmospheric liquid inlet density; the well pressure properties still vary between the two temperature hypotheses. Measured temperatures may describe instrument bodies or different fluid channels; they do not establish the complete axial fluid profile.

The shortcut check reruns frozen scoreboard circulation samples with the entry 8 heat sources and cumulative exposure history. Its two isothermal evaluations retain the solved mass rate and use mean inlet/return or mean bit/return temperatures. This isolates the shortcut from a change in pumping mass rate. `diagnose.py observed-shortcut` also evaluates mean measured inlet/return at every saved full-solve sample, matching the trip shortcut's actual observed temperature inputs. It reuses the saved full pressure and requires no new circulation solve. The recorded archive pressure and temperatures are reproduction references only.

## Reductions

Primary and inferred assignments remain separate. Unassigned observations are counted and cannot identify tool losses. Per-length groups use the declared 25-gpm centres and 2.5% membership tolerance. Sorted depth stages have a maximum total span of 100 ft; each stage contributes one mean to the descriptive pressure/depth regression. At least three stages spanning 1,000 ft are required. The slope is expressed in psi per thousand ft. The Student-t interval describes the stage scatter and does not include geometry or thermal uncertainty.

Flow-step groups have a maximum total depth span of 5 ft within one excursion and assembly. Flow levels use 25-gpm centres; at least three observed level means separated by 25 gpm are required. Linear-flow and squared-flow regressions are descriptive checks. Their coefficients do not enter the model. Grouping rules use input channels only.

`assembly-summary.csv` includes window medians and an equal-excursion mean of excursion medians. Windows within one excursion are repeated observations. The results retain both 16A temperature limits. `rig_minutes` in `windows.csv` counts distinct pressure-bearing rig minutes in each 16A window.

## Earlier exploratory reduction

`exploratory.py` reproduces the described reduction from `pason_selected_1min.csv`. The original executable is unavailable, so exact reproduction of its undocumented details cannot be established. Segment breaks occur on entering bit depth below 200 ft or a gap above six hours. A unique run must cover the segment's hole-depth range within the 20-ft report-rounding allowance, with at least 5 ft of positive advance inside its range.

Operational details are explicit: a non-overlapping clock-aligned two-minute bin requires two consecutive one-minute records, flow above 100 and at most 2,000 gpm, a flow range at most 2% of its mean, bit motion at most 5 ft and separation from bottom of at least 10 ft. Pressure and temperatures do not select the bins. Missing comparison channels are flagged after selection. Segment labels in this reduction are exploratory and do not receive the independent assignment status of the raw-data archive. A selected-record gap can result from sensor selection.

This reproduction uses the same entry 8 pressure calculation and measured inlet mass-flow conversion as the raw-data comparison. No alternative connection or friction law is scored.

## Files and rebuilding

`diagnose.py shortcut`, `diagnose.py observed-shortcut` and `diagnose.py trips` write the calculation tables. Both support `--output` and resume completed rows. An empty output directory gives a complete fresh run. `exploratory.py` writes the separate one-minute reduction. `analyse.py` generates the summaries and plots from these tables. The P0 observation extracts are unchanged.

| File | Contents |
|---|---|
| `shortcut-check.csv`, `shortcut-summary.csv` | Full solves, archived references and isothermal errors |
| `windows.csv` | Every raw-data window, including exclusions, thermal limits and pressure terms |
| `exploratory-segments.csv`, `exploratory-windows.csv` | Reproduction from the selected one-minute archive |
| `near-surface.csv` | Evaluated windows with mean bit depth at most 500 ft |
| `depth-stages.csv`, `slopes.csv`, `slope-exclusions.csv` | Stage membership, descriptive slopes and inadequate groups |
| `flow-steps.csv` | Fixed-depth flow-step groups and descriptive fits |
| `assembly-summary.csv`, `event-summary.csv` | Per-assembly and per-excursion pressure summaries and ratio/depth/flow associations |
| `exclusions.csv`, `unassigned-periods.csv` | Unavailable comparisons and the periods of unassigned observations |
| `pressure-flags.csv` | Non-positive recorded pressure during selected circulation; retained in the comparison |
| `flow-conversion.csv`, `flow-bound.csv` | Pump-channel conversions and the conditional nominal-efficiency bound |
| `phase-reference.csv` | Model-only phase/property reference for the mass-conversion correction |
| `manifest.json` | Input, script and result hashes, with library versions |

The plot prefixes distinguish primary observations, secondary assignments and the earlier exploratory reduction. Residual means modelled pressure minus measured pressure.
