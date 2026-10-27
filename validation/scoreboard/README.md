# Development scoreboard

The scoreboard compares physical-model changes on the frozen FORGE 16A and 16B development samples. The [development log](../../docs/science/model-development.md) defines the gaps and records candidate declarations. No validation-well target is read.

The single script uses recorded mud, PV referenced to 26.7 °C, film multiplier 1.0 and cumulative exposure. The baseline uses the original hydraulic mode. It retains the original 16B mud substitutions and the explicitly disclosed fitted trial insulation conductivity. Later revised-rheology results do not replace the original blind settings.

The circulation sample plan is `validation/forge16b/s2/plan.json`; only its `s1_original` 16B and `blind_original` 16A definitions are used. The script calculates new predictions; saved predictions are used solely for reproduction checks. Individual rows and coverage counts accompany every aggregate.

G1 uses 16A standpipe minus raw differential and unadjusted 16B motorless standpipe. G2 compares in-hole friction/nozzle/motor-face power with standpipe times measured inlet flow, on paired pressure-available samples. These are different physical quantities when power is dissipated at the surface or converted into mechanical work.

G3 uses bore fluid at the bit as a fixed proxy for the unresolved bit-box sensor. G5 pools the original return samples with equal sample weights and preserves their source groups. G6 uses the original independent regular-pipe group (EOW 11, 12, 13, 15, 16, 27 and 38) and the separate trial runs (17–20). Positions are 22 ft for EOW 11–16 and 84 ft for 17–20, 27 and 38. Early unresolved-position runs 3 and 4 are reported separately.

G4 uses the eleven original run-in legs, retaining their original availability. The primary tool comparison is the internal-fluid node at the bit with a static fluid node. Initial tool temperature is the first observation, leg speed is the observed endpoint mean, and the modelled fluid column is frozen at leg start. Local circulation/static histories and earlier conditioning follow the original transient study. This conditional comparison does not represent a blind complete trip from the surface.

The numerical reproduction resolutions are 1 psi, 0.1 °C and 0.1% of power. Diagnostics report discrepancies without changing a solve's convergence flag. The script, input extraction and aggregation rules become fixed with the baseline. Any subsequent change is recorded in the development log.
