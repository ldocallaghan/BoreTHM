# v1.3.4 first checkpoint: C1 to C4

This is the first STOP review in the supplied v1.3.4 specification. These are verdicts for the stated programme and assumptions. C5 and C6 have not begun, and the v1.3.3 goldens are unchanged.

The earlier development-plan changes were reverted to `6170a12`. The v1.3.4 work has separate commits for C1 (`3028b17`), C4 (`1c69f19`), C2 (`42d0f99`) and C3 (`1a5da44`). Commit `b9b666b` rejects invalid circulation candidates encountered in the United Downs search and adds checkpoint resumption.

## Site verdicts

| Site | v1.3.3 | C1 to C4 | Current reasons |
|---|---|---|---|
| Soultz | NO-GO | NO-GO | the wall is not held: drilling, trip, drilling common window, trip common window; tool: running in needs continuous circulation |
| United Downs | NO-GO | NO-GO | the wall is not held: drilling, trip, drilling common window, trip common window; tool: 206 C at the bit while drilling |
| Larderello | CONDITIONAL | CONDITIONAL | a drilling fluid of 1.036 SG at surface; a trip fluid of 1.094 SG at surface |
| Pannonian | INDETERMINATE | NO-GO | the wall is not held: drilling common window, trip common window |
| Newberry | GO | GO | All evaluated gates pass |

## Reasons for the changes

Soultz remains NO-GO because the lower demands exceed the fracture ceilings. C1 lowers hot-column pressure, C2 feeds the whole-hole weights through the thermal and tool calculations, and C3 adds the youngest rock at the target. Its drilling lower bound now binds at a target-depth connection, and the trip lower bound binds at the target. The corrected run-in tool search also fails to find a schedule short of continuous circulation.

United Downs remains NO-GO with closed drilling and trip windows and a drilling tool temperature of 205.7 C. The tool already failed in v1.3.3. The corrected lower bounds rise, and the target is now included in the trip coverage.

Larderello remains CONDITIONAL. C2 replaces the previously simulated water with the required drilling and trip fluids, and reruns their hydraulics and tool gates. At the same 30 L/s selected flow, the circulating friction rises from 0.01819 to 0.12118 SG and bit coolant falls from 70.59 to 66.45 C. The drilling lower bound binds at a 1,300 m connection; the included target sets the trip bounds. C4 exports the effective 2,400 m target and retains 2,850 m only under the explicitly named legacy key.

Pannonian changes from INDETERMINATE to NO-GO because the corrected whole-hole windows are explicit stability gates. No common fluid satisfies the stated stress scenarios: the lower bounds bind at the target and the upper bounds at the 4,000 m shoe. The coating qualification remains indeterminate as a separate component. The heavier simulated trip fluid also changes the tool result from PASS to PASS with the schedule found.

Newberry remains GO with water for drilling and the trip. Its pressure windows remain open after the exposure and final-stand checks, and the corrected circulation reproduces the earlier bit temperature and friction.

These are results of the combined corrections. The isolated composition comparison below establishes C1's pressure direction without attributing every combined change to C1.

## Prescribed and simulated fluids

Values are surface SG at 20 C. The prescribed value is the minimum whole-hole requirement, including the constraint that trip fluid is at least as heavy as drilling fluid. A closed window has no feasible prescription: its lower bound is shown as the density attempted, so a numerical match does not establish feasibility. In v1.3.3 the trip thermal and tool calculations used the drilling fluid; the trip weight was a reported requirement.

| Site | Fluid | v1.3.3 required | v1.3.3 simulated | C1 to C4 required | C1 to C4 simulated | Difference, SG | Window |
|---|---|---:|---:|---:|---:|---:|---|
| Soultz | drilling | 1.362764 | 1.363161 | 1.378925 | 1.378840 | +0.000085 | closed |
| Soultz | trip | 1.397606 | 1.363161 | 1.443624 | 1.443545 | +0.000079 | closed |
| United Downs | drilling | 1.316845 | 1.316977 | 1.331318 | 1.331733 | -0.000415 | closed |
| United Downs | trip | 1.361895 | 1.316977 | 1.401337 | 1.401158 | +0.000179 | closed |
| Larderello | drilling | 1.035798 | 0.998201 | 1.036244 | 1.036329 | -0.000085 | open |
| Larderello | trip | 1.088357 | 0.998201 | 1.094193 | 1.094057 | +0.000136 | open |
| Pannonian | drilling | 1.441526 | 1.442625 | 1.458734 | 1.459278 | -0.000544 | closed |
| Pannonian | trip | 1.489202 | 1.442625 | 1.544787 | 1.545152 | -0.000364 | closed |
| Newberry | drilling | 0.998201 | 0.998201 | 0.998201 | 0.998201 | +0.000000 | open |
| Newberry | trip | 0.998201 | 0.998201 | 0.998201 | 0.998201 | +0.000000 | open |

## Binding bounds

Depths are measured depth in metres. A water lower bound with no controlling rock case is shown as `water floor`. Each row gives the state and case that sets the common bound.

| Site | Fluid / bound | v1.3.3 SG | v1.3.3 depth, state and case | C1 to C4 SG | C1 to C4 depth, state and case |
|---|---|---:|---|---:|---|
| Soultz | drilling / lower | 1.362764 | 10699.5 m; fresh rock; SHmax upper bound (1.05 Sv), lab UCS 100 | 1.378925 | 10700.0 m; connection; SHmax upper bound (1.05 Sv), lab UCS 100 |
| Soultz | drilling / upper | 1.303509 | 4000.0 m; drilling; SHmax lower bound (0.90 Sv), lab UCS 100 | 1.312559 | 4000.0 m; drilling; SHmax lower bound (0.90 Sv), lab UCS 100 |
| Soultz | trip / lower | 1.397606 | 10671.5 m; trip; SHmax upper bound (1.05 Sv), lab UCS 100 | 1.443624 | 10700.0 m; trip; SHmax upper bound (1.05 Sv), lab UCS 100 |
| Soultz | trip / upper | 1.353204 | 4000.0 m; trip; SHmax lower bound (0.90 Sv), lab UCS 100 | 1.364611 | 4000.0 m; trip; SHmax lower bound (0.90 Sv), lab UCS 100 |
| United Downs | drilling / lower | 1.316845 | 12856.6 m; fresh rock; Reinecker et al. (2021), weak zones, 40 K | 1.331318 | 12857.1 m; connection; Reinecker et al. (2021), weak zones, 40 K |
| United Downs | drilling / upper | 1.274195 | 12856.6 m; drilling; Reinecker et al. (2021), intact, 0 K | 1.285186 | 12857.1 m; drilling; Reinecker et al. (2021), intact, 0 K |
| United Downs | trip / lower | 1.361895 | 12828.6 m; trip; Reinecker et al. (2021), weak zones, 40 K | 1.401337 | 12857.1 m; trip; Reinecker et al. (2021), weak zones, 40 K |
| United Downs | trip / upper | 1.349783 | 12828.6 m; trip; Reinecker et al. (2021), intact, 0 K | 1.365025 | 12857.1 m; trip; Reinecker et al. (2021), intact, 0 K |
| Larderello | drilling / lower | 1.035798 | 1471.5 m; fresh rock; Shmin 0% of floor-to-Sv | 1.036244 | 1300.0 m; connection; Shmin 0% of floor-to-Sv |
| Larderello | drilling / upper | 1.330160 | 2399.5 m; drilling; Shmin 0% of floor-to-Sv | 1.229740 | 2400.0 m; drilling; Shmin 0% of floor-to-Sv |
| Larderello | trip / lower | 1.088357 | 2371.5 m; trip; Shmin 0% of floor-to-Sv | 1.094193 | 2400.0 m; trip; Shmin 0% of floor-to-Sv |
| Larderello | trip / upper | 1.328415 | 2371.5 m; trip; Shmin 0% of floor-to-Sv | 1.331191 | 2400.0 m; trip; Shmin 0% of floor-to-Sv |
| Pannonian | drilling / lower | 1.441526 | 9713.5 m; fresh rock; Shmin 100% of floor-to-Sv | 1.458734 | 9714.0 m; connection; Shmin 100% of floor-to-Sv |
| Pannonian | drilling / upper | 1.284891 | 4000.0 m; drilling; Shmin 0% of floor-to-Sv | 1.293107 | 4000.0 m; drilling; Shmin 0% of floor-to-Sv |
| Pannonian | trip / lower | 1.489202 | 9685.5 m; trip; Shmin 100% of floor-to-Sv | 1.544787 | 9714.0 m; trip; Shmin 100% of floor-to-Sv |
| Pannonian | trip / upper | 1.337659 | 4000.0 m; trip; Shmin 0% of floor-to-Sv | 1.348415 | 4000.0 m; trip; Shmin 0% of floor-to-Sv |
| Newberry | drilling / lower | 0.998201 | water floor | 0.998201 | water floor |
| Newberry | drilling / upper | 1.233030 | 3629.0 m; drilling; Davatzes & Hickman (2011), mu 0.7, log-derived granodiorite p10 | 1.236660 | 3629.5 m; drilling; Davatzes & Hickman (2011), mu 0.7, log-derived granodiorite p10 |
| Newberry | trip / lower | 0.998201 | water floor | 0.998201 | water floor |
| Newberry | trip / upper | 1.230177 | 3601.0 m; trip; Davatzes & Hickman (2011), mu 0.7, log-derived granodiorite p10 | 1.233409 | 3629.5 m; trip; Davatzes & Hickman (2011), mu 0.7, log-derived granodiorite p10 |

## C1 direction at the deep sites

The following comparison holds surface density and the full corrected trip temperature profile fixed. It changes only the mixture composition accounting. It isolates C1 from the fluid feedback and added depth coverage.

| Site | Surface SG | Legacy bottomhole pressure, MPa | Conserved bottomhole pressure, MPa | Change, MPa | v1.3.3 trip width, SG | C1 to C4 trip width, SG |
|---|---:|---:|---:|---:|---:|---:|
| Soultz | 1.443545 | 143.437 | 140.174 | -3.263 | -0.044403 | -0.079013 |
| United Downs | 1.401158 | 167.049 | 163.519 | -3.530 | -0.012112 | -0.036312 |

C1 lowers hot-column pressure in both deep sites, as the spec expects. The combined C1 to C4 trip widths are reported separately; those changes also include the heavier simulated fluids and the newly checked final stand.

## Numerical checks and timing

The default suite passed 336 tests with 89 slow tests deselected in 18.17 s. The focused Larderello and coverage run passed six tests in 81.11 s. The v1.3.3 regression passed all four tests in 1,560.34 s (26 min), with three numerical warnings. Its saved table was reproduced with C1 to C3 disabled. All five corrected selected drilling and trip solves passed their solver checks, and every prescribed versus simulated density difference was below 0.002 SG.

| Site | Checkpoint evaluation, s | Fluid passes | Fluid converged | Window refinement converged | Largest refinement change, SG | Largest binding-depth movement, m |
|---|---:|---:|---|---|---:|---:|
| Soultz | 266.54 | 3 | True | True | 0.000000 | 0.0 |
| United Downs | 723.56 | 3 | True | True | 0.000000 | 0.0 |
| Larderello | 116.05 | 2 | True | True | 0.000000 | 0.0 |
| Pannonian | 293.92 | 3 | True | True | 0.000000 | 0.0 |
| Newberry | 31.09 | 1 | True | True | 0.000000 | 0.0 |

The run uses Python 3.14.4 and the lock-file packages: NumPy 2.5.3, SciPy 1.18.1, IAPWS 1.5.5 and Matplotlib 3.11.2. The JSON evidence records the source commit for each site. Soultz and Larderello were run at `1a5da44`; the remaining sites use `b9b666b`.

BVP divide warnings and a heat-transfer power warning occurred during the circulation search. The search rejected a diverged United Downs candidate whose surface temperature was outside the saturation-pressure domain. Selected drilling and trip solves must pass their solver gates; an unsuccessful solve produces INDETERMINATE.

Raw per-site results and the full comparison are in [the checkpoint evidence](../results/v1.3.4/checkpoint-1/comparison.json). No reviewed golden files were regenerated. To rerun the checkpoint, use `python src/checkpoint_v134.py --output results/v1.3.4/checkpoint-1`. The site CLI defaults to v1.3.4; API callers select it with `evaluate(site, circulation="v1.3.4")`.

## Review boundary

Work stops here as required by the first STOP. After this review, C5 will test the remaining approximations with the nine ledger comparisons. C6 will follow its own review boundary. C7, the merge to main and the v1.3.4 tag remain after all three reviews.

The five base evaluations sum to 23.9 minutes of measured run time; the two deep sites account for 16.5 minutes. The remaining effort estimate stays at 5 to 10 hours for C5 and 10 to 20 hours for C6, plus calculation time and the STOP reviews. Ten full evaluations of each deep site would take about 2.8 hours at these measured costs. Several lever searches could therefore need overnight runs. The cheap ledger comparisons should avoid that full-evaluation cost where their definitions allow it.
