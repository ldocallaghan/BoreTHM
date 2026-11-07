# Circulation benchmark results

These calculations use the inputs and acceptance limits in the
[benchmark definitions](../README.md). The
[rebuild script](../run_circulation.py) runs both sets of cases.

| Case | Flow direction | Closed form versus independent numerical solution, max K | Matched BoreTHM difference, max K | Result |
| --- | --- | ---: | ---: | --- |
| Holmes and Swift | Forward | 1.38e-9 | 1.85e-7 | Pass |
| Holmes and Swift | Reverse | 1.49e-9 | 2.40e-7 | Pass |
| Khaled FORGE | Forward | 7.76e-10 | 1.98e-7 | Pass |
| Khaled FORGE | Reverse | 8.45e-10 | 6.56e-8 | Pass |

The first-order pipe equation gives the annulus temperature in terms
of the pipe temperature and its derivative. Substituting it into the
annulus equation gives the second-order equation in
[the implementation](../kabir1996.py). Applying the surface inlet
and bottom turnaround conditions to its two exponential terms gives
both profiles. For reverse flow the characteristic equation is
`AB λ² + B λ − 1 = 0`. The boundary system uses the annulus inlet
minus the formation surface temperature, the formation gradient and
a negative sign on the positive-rate coefficient in the unshifted
form. The derivative of the independently solved forward profile
confirms the sign used to find its maximum. This checks the Appendix
B and C expressions against the balances and boundary conditions.

The positive-rate exponential is evaluated relative to the bottom and
the negative-rate exponential relative to the surface. The matched
BoreTHM benchmark freezes the conductances in its test harness.
The harness reverses the signs of both energy derivatives and changes
the inlet boundary for reverse circulation. The package's normal
solver offers forward circulation. The release-physics comparison
therefore reports forward circulation with variable fluid properties.

With the 44 h Hasan and Kabir rock response and BoreTHM's fixed
conductances, the calculated annulus maximum for the Holmes and Swift
case is at 14,103 ft. Kabir et al. report 13,776 ft with their
conductances. The release-physics profiles differ from the matched
analytical forward profiles by up to 38.65 K for Holmes and Swift
and 6.61 K for Khaled FORGE. The Khaled FORGE case gives 90.90 °C
at the bottom with release physics and 84.29 °C under the matched
assumptions. The paper's semisteady 114 °C comes from its own model.
See [the full comparison table](kabir-comparison.csv).

| Brown et al. case | Published maximum, °C | BoreTHM maximum, °C | Error, K | Tolerance, K | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Steel | 178.7 | 169.56 | −9.14 | ±3.574 | Fail |
| Insulated | 73.6 | 69.82 | −3.78 | ±1.472 | Fail |

Both BoreTHM calculations converged. Brown et al. use an effective
formation radius obtained from an internal heat-transfer calculation
and approximate the wall temperature by the annulus temperature.
BoreTHM uses a constant-wall-temperature cylinder solution and an
explicit annulus film. These differences limit reproduction of the
published maxima. Their separate contributions to the errors have not
been established. See [the results table](brown-comparison.csv).
