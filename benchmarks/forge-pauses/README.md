# FORGE 16B pauses and trips

`expected.json` is the retained `tests/golden/forge_pauses.json`. It contains the attenuation factors and observed, modelled and leave-one-out predicted return-temperature anomalies. Both the mixed-fluid-node model and no-node sensitivity are present. Anomalies are in degrees F, durations in hours, and start times in Unix seconds. The source clock has no time zone; it is read as UTC to preserve the recorded clock consistently.

`inputs.json` records the pause-classification thresholds, depth spacing, casing radii and unfitted effective insulation conductivity. The source data and credits are in [data/forge16b](../data/forge16b/README.md). `cycle_timings.csv` identifies the pauses; the Pason record supplies their minute-by-minute histories.

The complete history and geometry recipes remain in `validate_forge_pauses` and `validate_forge16b`. They have not been exported as a separate time-dependent input format. The attenuation factor is fitted on trips, with each trip predicted from the others; short pauses are reported outside that fit. Existing tolerances cover the factors, observed anomalies and unattenuated model anomalies. No numerical tolerance is added for the retained `pred` diagnostics.
