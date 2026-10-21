# FORGE 16B circulation comparison

`expected.json` copies `tests/golden/validate_forge16b.json` without changing any value. It includes the fitted annulus-film multiplier and effective insulated-pipe conductivity, run means, the BHA 12 blind prediction, and the temperature-change decomposition. The unfitted chain is included too. MWD means and temperature changes are in degrees F; conductivity is W/(m K). `tolerances.json` retains the existing fitted-value and temperature assertions and identifies the unfitted decomposition as a diagnostic without a separate acceptance assertion.

`inputs.json` records the thermal constants, sensor offset, nozzle sizes and available dimensional parameters from `validate_forge16b`. The complete source extracts are under [data/forge16b](../data/forge16b/README.md), with their original headers and CC BY 4.0 credits. The measured bit depth, flow and inlet temperature vary through the saved Pason record.

The survey and temperature interpolation, casing construction and changing drill-string recipes remain references to `survey`, `formation_temperature`, `hole` and `string` in that module. They have not been converted into a complete independent input deck. The source guide describes the assumed casing wall and sensor position.

The film multiplier is fitted on regular-pipe runs, then effective insulation conductivity on BHA 11. BHA 12 is predicted with those parameters fixed. The benchmark records the retained fit and prediction, without repeating either calculation during dataset construction.
