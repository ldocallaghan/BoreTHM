# FORGE 58-32 model-only thermal forecast

These are the declared forecasts of the [58-32 thermal protocol](../thermal_protocol.md), calculated with BoreTHM 1.9.0 from PyPI before any 58-32 return temperature or PT-log value was read. The [manifest](manifest.json) gives the package version and path, the hashes of every input and code file, the code commit and the prediction counts.

`predictions.csv` has one row for each drilling window in [conditions.csv](../thermal/samples/conditions.csv). For the primary (scaled) and secondary (Pason) flow it gives the return and bit temperatures of the v1.9.0 defaults and of `physics='v1.7.0'`, the analytical comparator's return, and the part D quantities: the model rock-heat bound, the conduction bound, the larger of the two, the hydraulic power and the energy limit, 1.25 times the sum of the bound and the hydraulic power, all in watts. A window whose inputs are incomplete has its reason in `input_status` and no prediction. `components_as_drill_pipe` lists the components given the ordinary-pipe envelope.

`log-predictions.csv` has one row for each point of [log-points.csv](../thermal/samples/log-points.csv): the log, the measured depth, the rig time and the seconds since circulation ended. For each flow and physics it gives the headline forecast (`_C`), the cased-hole sensitivity (`_cased_reheated_C`) and the annulus temperature at the end of circulation; it also gives the analytical comparator's circulating annulus temperature and the PT118 formation temperature. `cased` marks depths above the 2,172 ft shoe, where the headline forecast is the annulus temperature at the end of circulation.

Rebuild from the repository root with BoreTHM 1.9.0 installed from PyPI:

```bash
python -m validation.forge58-32.thermal.predict_thermal validation/forge58-32/thermal/samples validation/forge58-32/predictions-v1.9.0 --workers 4
```
