# Entry 7: plastic-viscosity heat transfer and the Erge band, three yield-stress hypotheses

These are development comparisons on the frozen 16A and 16B samples. The calculation is entry 5's working calculation (entries 1–5 with D5: rotary heat and the S2 16B mud), with `annulus_model='herschel-bulkley-erge'`. This uses the Founargiotakis slot model with the transition band of Erge et al. (2015) for the annulus pressure loss and flow regime. For the film coefficients it uses Gnielinski's annulus correlation on the plastic viscosity, or laminar annulus values. Each sample's mud carries the Herschel–Bulkley rheology of one of entry 6's declared hypotheses ([`../../entry-6/hypotheses.py`](../../entry-6/hypotheses.py)), with the 10-s gels of [`../../entry-6/gel_inputs.csv`](../../entry-6/gel_inputs.csv):

- [`no-yield/`](no-yield/): no yield stress.
- [`gel/`](gel/): the 10-s gel at every temperature.
- [`gel-rising/`](gel-rising/): the gel, rising above 330 K as Alderman et al. (1988) measured.

PV is referenced to 26.7 °C, the film multiplier is 1.0, and exposure is cumulative with the one-hour floor. 16A and 16B use the NC50 and EIS connection scenarios. Nothing is fitted to a temperature, pressure or residual. The historical trial insulation conductivity remains, as disclosed in the development log.

**Each hypothesis folder.**

- `circulation.csv`, `run-in.csv` and `scoreboard.csv` come from the frozen scoreboard functions, run by `../score.py --hypothesis NAME`.
- `rheology-applied.csv` lists the yield stress, n and K given to every circulation sample.
- `rotary-heat-applied.csv` lists the rotary heat, as in entries 4 and 5.
- `manifest.json` records the settings, the commits and source hashes.

**Files from `../compare.py`.**

- `comparison.csv` sets each scoreboard row of the three hypotheses beside the legacy baseline and the working calculation.
- `summary.csv` gives the declared summary measures for each calculation.
- `assembly-changes.csv` gives the change from the working calculation, by assembly, in bit and return temperature and standpipe pressure.
- `derived-sha256.json` hashes these three files.

All 467 circulation cases and all nine originally available run-in events completed under every hypothesis, with the same sample counts as both reference calculations. Run-in transients keep their Dittus–Boelter films, so G4 equals the working calculation. The declaration, predictions and interpretation are in the [development log](../../../../docs/science/model-development.md). Source observations retain the attribution and CC BY 4.0 terms stated in the [16A](../../../forge16a/README.md) and [16B](../../../forge16b/README.md) archives.
