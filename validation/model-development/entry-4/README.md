# Entry 4: rotary-drive inputs and heat

`rotary_inputs.csv` gives, for each of the 467 frozen circulation samples, the surface rotary speed, top-drive torque, weight on bit and measured rotary power while on bottom, and the off-bottom rotating torque before the sample. Rebuild it with

```
python validation/model-development/entry-4/build_rotary.py --gdr1283 <GDR 1283 ZIP> --gdr1516 <GDR 1516 ZIP>
```

Each argument also accepts the extracted member: `16A(78)-32_time_data_10s_intervals_standard.csv` from GDR 1283 (McLennan et al. 2021) and `16B_Pason.zip` from GDR 1516 (McLennan et al. 2023). The window rules are in the script's docstring, and `rotary_inputs_manifest.json` records the source and output hashes. Only rig drive channels, flow and the on-bottom flag are read. No temperature, pressure or residual enters the extract.

`rotary.py` turns each row into heat with `borethm.rotary_heat.partition`. The friction factor comes from the sample's own off-bottom torque; six 16A samples have no off-bottom reference and use the median factor of their assembly. `predict.py` gives the model-only predictions in `predictions.csv`, and `score.py` runs the frozen scoreboard functions with the rotary heat added. The declaration and results are in the [development log](../../../docs/science/model-development.md).

The source observations retain the attribution and CC BY 4.0 terms stated in the [16A](../../forge16a/README.md) and [16B](../../forge16b/README.md) archives.
