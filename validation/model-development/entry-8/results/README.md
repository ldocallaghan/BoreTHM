# Entry 8: one regime criterion for annulus pressure and heat transfer

These are development comparisons on the frozen 16A and 16B samples. The calculation is entry 5's working calculation (entries 1–5 with D5: rotary heat and the S2 16B mud), with `annulus_model='herschel-bulkley-erge'`: the Founargiotakis slot model with the transition band of Erge et al. (2015) for the annulus pressure loss and flow regime, and Gnielinski's annulus correlation on the plastic viscosity for turbulent heat transfer. Each sample's mud carries the power law through its 600 and 300 rpm readings (entry 6's hypothesis no-yield). The solve starts from the usual seeds.

The score is run at three annulus film multipliers by [`../score.py`](../score.py):

- [`film-1.00/`](film-1.00/): the score.
- [`film-0.85/`](film-0.85/) and [`film-1.05/`](film-1.05/): the declared uncertainty band.

PV is referenced to 26.7 °C and exposure is cumulative with the one-hour floor. 16A and 16B use the NC50 and EIS connection scenarios. Nothing is fitted to a temperature, pressure or residual. The historical trial insulation conductivity remains, as disclosed in the development log.

**Each film folder.**

- `circulation.csv`, `run-in.csv` and `scoreboard.csv` come from the frozen scoreboard functions.
- `rheology-applied.csv` lists n and K given to every circulation sample.
- `rotary-heat-applied.csv` lists the rotary heat, as in entries 4 and 5.
- `regime.csv` gives, for every circulation sample, the shares of drill-pipe annulus length that are laminar and transitional at the solved state, and the shares that would be laminar and transitional at that state with a yield stress equal to the 10-s gel.
- `manifest.json` records the settings, the commits and source hashes.

**Files from [`../compare.py`](../compare.py).**

- `comparison.csv` sets each scoreboard row of the three film multipliers beside the legacy baseline, the working calculation and entry 7's no-yield score.
- `summary.csv` gives the declared summary measures for each calculation.
- `assembly-changes.csv` gives the change from the working calculation, by assembly, in bit and return temperature and standpipe pressure.
- `entry7-reproduction.csv` gives, for every circulation sample at film multiplier 1.0, the difference from entry 7's no-yield score and whether it is within the declared tolerance.
- `regime-summary.csv` gives the mean regime shares by assembly.
- `derived-sha256.json` hashes these files.

All 467 circulation cases and all nine originally available run-in events completed at every film multiplier, with the same sample counts as the reference calculations. Run-in transients keep their Dittus–Boelter films, so G4 equals the working calculation. The declaration, predictions and interpretation are in the [development log](../../../../docs/science/model-development.md). Source observations retain the attribution and CC BY 4.0 terms stated in the [16A](../../../forge16a/README.md) and [16B](../../../forge16b/README.md) archives.
