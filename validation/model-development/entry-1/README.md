# Hydraulic losses and heat placement

This archive scores entry 1 using the fixed [scoreboard](../../scoreboard/README.md). Both calculations use recorded mud with plastic viscosity referenced to 26.7 °C, film multiplier 1.0 and cumulative exposure. The legacy predictions are the approved [baseline](../../scoreboard/baseline/scoreboard.csv). The candidate adds the previously declared hydraulic terms, using the NC50 connection scenario on 16A and EIS on 16B. No later heat-source or rock-response candidate is included.

The historical trial insulation-conductivity fit and the transferred connection pitch remain disclosed inputs. The trial geometry remains aggregate, including the partial insulated-pipe string. Proprietary tool operating losses are unspecified. These comparisons cannot establish installed connection geometry or a complete physical heat budget.

| File | Quantity and columns |
|---|---|
| [comparison.csv](comparison.csv) | All six gaps, including every declared assembly or event. `before_bias` and `after_bias` are model minus measurement; `change_bias` is after minus before. Counts accompany each side. Pressure is psi, power is kW and temperature is °C. |
| [scoreboard.csv](scoreboard.csv) | Candidate reductions from the unchanged scoreboard. `model_mean`, `measured_mean` and `bias` retain that script's definitions. |
| [circulation.csv](circulation.csv) | Every circulation sample, solver status and the individual physical predictions. |
| [run-in.csv](run-in.csv) | Every original run-in event, with unavailable cases retained. |
| [manifest.json](manifest.json) | Settings and source/result checksums, including the baseline identity. |
| [pressure-bias.png](pressure-bias.png) | G1 assembly biases from `comparison.csv`, `before_bias` and `after_bias`. |
| [temperature-bias.png](temperature-bias.png) | G3 assembly biases and G6 group/trial biases from the same columns. |

G1 compares 16A standpipe minus raw reported differential and 16B unadjusted motorless standpipe. G2 compares in-hole dissipative/face power with measured surface hydraulic power; surface losses and useful mechanical work make those distinct quantities. G3 uses the fixed bore-at-bit sensor proxy. G4 retains the conditional partial-leg initial states. G5 preserves overlapping return-sample populations. G6 separates regular-pipe and trial groups. No alternative sensor proxy or rheology convention is selected after calculation.

The [development log](../../../docs/science/model-development.md) records the result and recommendation. Acceptance remains a separate decision.
