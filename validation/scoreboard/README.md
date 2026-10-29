# Development scoreboard

The scoreboard compares physical-model changes on the frozen FORGE 16A and 16B development samples. The [development log](../../docs/science/model-development.md) defines the gaps and records candidate declarations. No validation-well target is read.

The single script uses recorded mud, PV referenced to 26.7 °C, film multiplier 1.0 and cumulative exposure. The baseline uses the original hydraulic mode. It retains the original 16B mud substitutions and the explicitly disclosed fitted trial insulation conductivity. Later revised-rheology results do not replace the original blind settings.

The circulation sample plan is `validation/forge16b/s2/plan.json`; only its `s1_original` 16B and `blind_original` 16A definitions are used. The script calculates new predictions; saved predictions are used solely for reproduction checks. Individual rows and coverage counts accompany every aggregate.

G1 uses 16A standpipe minus raw differential and unadjusted 16B motorless standpipe. G2 compares in-hole friction/nozzle/motor-face power with standpipe times measured inlet flow, on paired pressure-available samples. These are different physical quantities when power is dissipated at the surface or converted into mechanical work.

G3 uses bore fluid at the bit as a fixed proxy for the unresolved bit-box sensor. G5 pools the original return samples with equal sample weights and preserves their source groups. G6 uses the original independent regular-pipe group (EOW 11, 12, 13, 15, 16, 27 and 38) and the separate trial runs (17–20). Positions are 22 ft for EOW 11–16 and 84 ft for 17–20, 27 and 38. Early unresolved-position runs 3 and 4 are reported separately.

G4 uses the eleven original run-in legs, retaining their original availability. The primary tool comparison is the internal-fluid node at the bit with a static fluid node. Initial tool temperature is the first observation, leg speed is the observed endpoint mean, and the modelled fluid column is frozen at leg start. Local circulation/static histories and earlier conditioning follow the original transient study. This conditional comparison does not represent a blind complete trip from the surface.

The numerical reproduction resolutions are 1 psi, 0.1 °C and 0.1% of power. Diagnostics report discrepancies without changing a solve's convergence flag. The script, input extraction and aggregation rules become fixed with the baseline. Any subsequent change is recorded in the development log.

## Reproduction

The original transient study supplies event indices and its recorded component inputs. Extract them once, without running a model:

```text
python validation/scoreboard/scoreboard.py freeze-transients --study ORIGINAL_16A_STUDY
```

The committed `transient-inputs.json` is that extract, with source checksums. Subsequent runs need only the checkout archives:

```text
python validation/scoreboard/scoreboard.py run --mode legacy --output EMPTY_OUTPUT_DIRECTORY
```

The `current` mode is reserved for the declared candidate comparison. It retains the same samples, mud convention and primary sensor proxies, using the previously declared NC50 scenario for 16A and EIS for 16B. Its run-in conditioning profiles are recalculated using that hydraulic mode. The development entries are scored through their own scripts on the frozen functions, with results under `validation/model-development/`; see the [development log](../../docs/science/model-development.md).

## Baseline archive

| File | Contents |
|---|---|
| [scoreboard.csv](baseline/scoreboard.csv) | Every gap, population count and bias; psi percentages apply to pressure, and power is in kW. Temperature differences are in °C. |
| [circulation.csv](baseline/circulation.csv) | Every original primary sample, its predictions, observations and solver status. |
| [run-in.csv](baseline/run-in.csv) | All original run-in events, peak errors and unavailable cases. |
| [baseline-reproduction.csv](baseline/baseline-reproduction.csv) | Archived and recalculated values with each numerical resolution and comparison result. |
| [manifest.json](baseline/manifest.json) | Settings, historical calibration disclosure, runtime versions and normalised-LF source/result checksums. |

The full calculation took 265.5 seconds on the recorded runtime. All 467 circulation cases and the nine originally available run-in cases succeeded. All 2,614 reproduction checks passed. Two originally unavailable run-in cases are retained. Subsequent metadata completion made the already-used 26.7 °C reference explicit and omitted percentages of Celsius temperatures; no numerical prediction was rerun. Source-data attribution remains in the [16A](../forge16a/README.md) and [16B](../forge16b/README.md) archives, under CC BY 4.0.
