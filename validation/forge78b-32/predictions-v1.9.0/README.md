# FORGE 78B-32 model-only thermal forecast

These are the declared forecasts of the [78B-32 thermal protocol](../thermal_protocol.md), calculated with BoreTHM 1.9.0 from PyPI before any 78B-32 downhole temperature, return temperature or Sanvean reading was read. The [manifest](manifest.json) gives the package version and path, the hashes of every input and code file, the code commit and the prediction counts.

`predictions.csv` has one row for each drilling window in [windows.csv](../thermal/samples/windows.csv). For the v1.9.0 defaults and for `physics='v1.7.0'` it gives the solver status, the surface return temperature (`_return_C`), the temperature delivered to the bit (`_bit_C`), and the drill-string fluid temperature at the downhole sensor (`_sensor_C`) and at the lower and upper Sanvean sensors (`_sanvean_lower_C`, `_sanvean_upper_C`) where the assembly carries them. The analytical comparator gives the annulus temperature at surface for the return and the tubing temperature at each sensor. A window whose inputs are incomplete has its reason in `input_status` and no prediction. `component_flags` lists the components given the drill-pipe envelope or a collar diameter, and `drill_pipe` names the pipe above the assembly.

Which windows each part scores is set by the `part_` columns of `windows.csv`.

Rebuild from the repository root with BoreTHM 1.9.0 installed from PyPI:

```bash
python -m validation.forge78b-32.thermal.predict_thermal validation/forge78b-32/thermal/samples validation/forge78b-32/predictions-v1.9.0 --workers 3
```
