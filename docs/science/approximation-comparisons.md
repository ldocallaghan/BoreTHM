# Approximation and numerical comparisons

This study tests how the retained Soultz and United Downs programmes respond to individual approximations, with separate resolution checks at Pannonian. The base deep-site verdicts remain NO-GO for this programme and these assumptions in the comparisons performed. The comparison IDs A1-A9 identify the saved runs and are defined below.

## How the margins are read

Pressure margin is the common-window width, upper minus lower, in surface SG at 20 C. A negative width means no one fluid holds every stated case below the fracture limit. The ledger also saves the actual fluid slack against each lower and upper bound. Those slacks distinguish a lighter trip fluid failing the breakout bound from a small change in the family of feasible weights.

Tool margin is 200 C minus the maximum of drilling, connection and run-in temperatures. Run-in uses the best stage attempted in the existing schedule search, including failed attempts. Its peak and the original FORGE-practice peak are both saved. A positive change in a margin moves towards passing; a negative change moves towards failure.

The pipe, surface fluid weights, flow and exposure rate remain at the reviewed values. Each comparison changes one approximation. These comparisons hold the programme fixed without repeating its flow or fluid design search. The separate design study reruns the coupled evaluation for each new physical setting. The reconstruction reproduces the reviewed status and window bounds, and uses the exposure rate actually supplied to that circulation solve.

| Site | Drilling width, SG | Trip width, SG | Drilling / connection / best run-in, C | Tool margin, C | Verdict |
|---|---:|---:|---|---:|---|
| Soultz | -0.066366 | -0.079013 | 196.992 / 197.315 / 201.207 | -1.207 | NO-GO |
| United Downs | -0.046132 | -0.036312 | 205.702 / 206.065 / 224.476 | -24.476 | NO-GO |
| Pannonian | -0.165628 | -0.196372 | 184.717 / 185.062 / 192.845 | +7.155 | NO-GO |

## Soultz

| ID | Comparison | Change in drilling width, SG | Change in trip width, SG | Change in tool margin, C | Best run-in peak, C | Verdict | Reopens site |
|---|---|---:|---:|---:|---:|---|---|
| A1 | budget profile, one update | -0.000172 | -0.000562 | -1.221958 | 202.429 | NO-GO | no |
| A2 | Model 3 face load | +0.000008 | +0.000004 | +0.018191 | 201.189 | NO-GO | no |
| A3 | instant, optimistic | +0.000000 | +0.000000 | +0.000000 | 201.207 | NO-GO | no |
| A3 | one turnover, adverse | +0.000000 | +0.000000 | -177.416715 | 378.623 | NO-GO | no |
| A4 | staging time added | +0.000000 | -0.006566 | -0.032419 | 201.239 | NO-GO | no |
| A5 | column advances during run-in | +0.000000 | +0.000000 | -0.087738 | 201.294 | NO-GO | no |
| A6 | uniform trip fluid | +0.000000 | +0.000000 | +0.000000 | 201.207 | NO-GO | no |
| A6 | drilling fluid throughout | +0.000000 | +0.000138 | +2.845464 | 198.361 | NO-GO | no |
| A7 | partial-depth binding ceiling | -0.052363 | -0.038053 | +0.000000 | 201.207 | NO-GO | no |
| A8 | 0.00 SG per bound | +0.000000 | +0.040297 | +0.000000 | 201.207 | NO-GO | no |
| A8 | 0.04 SG per bound | +0.000000 | -0.040260 | +0.000000 | 201.207 | NO-GO | no |
| A9 | radial spacing halved | -0.000721 | -0.000005 | -0.000030 | 201.207 | NO-GO | no |
| A9 | timesteps halved | +0.000061 | -0.000176 | +0.072453 | 201.134 | NO-GO | no |
| A9 | window spacing halved | +0.000000 | +0.000000 | +0.000000 | 201.207 | NO-GO | no |
| A9 | all three halved | -0.000659 | -0.000181 | +0.072425 | 201.134 | NO-GO | no |

## United Downs

| ID | Comparison | Change in drilling width, SG | Change in trip width, SG | Change in tool margin, C | Best run-in peak, C | Verdict | Reopens site |
|---|---|---:|---:|---:|---:|---|---|
| A1 | budget profile, one update | -0.000285 | +0.000034 | -2.076258 | 226.552 | NO-GO | no |
| A2 | Model 3 face load | +0.000005 | -0.000006 | +0.033994 | 224.442 | NO-GO | no |
| A3 | instant, optimistic | +0.000000 | +0.000000 | +0.000000 | 224.476 | NO-GO | no |
| A3 | one turnover, adverse | +0.000000 | +0.000000 | -162.275634 | 386.751 | NO-GO | no |
| A4 | staging time added | +0.000000 | -0.005537 | -0.497784 | 224.974 | NO-GO | no |
| A5 | column advances during run-in | +0.000000 | +0.000000 | -0.865907 | 225.342 | NO-GO | no |
| A6 | uniform trip fluid | +0.000000 | +0.000000 | +0.000000 | 224.476 | NO-GO | no |
| A6 | drilling fluid throughout | +0.000000 | +0.000095 | +3.647013 | 220.829 | NO-GO | no |
| A7 | not binding | +0.000000 | +0.000000 | +0.000000 | 224.476 | NO-GO | no |
| A8 | 0.00 SG per bound | +0.000000 | +0.039905 | +0.000000 | 224.476 | NO-GO | no |
| A8 | 0.04 SG per bound | +0.000000 | -0.039853 | +0.000000 | 224.476 | NO-GO | no |
| A9 | radial spacing halved | -0.001305 | -0.000004 | -0.000251 | 224.476 | NO-GO | no |
| A9 | timesteps halved | -0.000629 | -0.000128 | +0.095944 | 224.380 | NO-GO | no |
| A9 | window spacing halved | -0.000682 | +0.000000 | +0.000000 | 224.476 | NO-GO | no |
| A9 | all three halved | -0.001251 | -0.000132 | +0.095696 | 224.380 | NO-GO | no |

## What each comparison changes

**A1, property pressures.** Model 1 is run with the circulating budget profile in absolute pressure, then with that profile updated once. The same final property-pressure profile is used for the subsequent thermal gate check. It is a comparison of the pressure approximation at fixed programme inputs; it does not add a coupled pressure model to the base.

**A2, face load.** Model 3 supplies the face heat at the reviewed coolant temperature. That heat replaces 30 kW in Model 1 and the gate calculations. Exposure is held fixed so this row isolates the face-load approximation.

| Site | Model 3 face load, kW | Base load, kW |
|---|---:|---:|
| Soultz | 29.203 | 30.000 |
| United Downs | 27.761 | 30.000 |

**A3, stage delivery.** The optimistic case uses immediate steady coolant. The adverse case holds the flowing fluid at the column temperature at the stage depth for one internal-string turnover, then supplies steady coolant for any remaining stage time. Turnover uses the stage-depth string volume and the inlet volume flow. Forced films stay at the base values. The whole stage history is retained so a hot peak before cold delivery is counted; this is a bracket, with no advection model.

| Site | Bottom-depth turnover, min | Base stage duration, min | Optimistic run-in peak, C | Adverse run-in peak, C |
|---|---:|---:|---:|---:|
| Soultz | 49.29 | 15.51 | 201.207 | 378.623 |
| United Downs | 47.54 | 15.51 | 224.476 | 386.751 |

**A4, staging clock.** The base schedule duration is added to the nominal static trip. Where no schedule passes, the comparison uses FORGE practice, which is the schedule the existing output reports in that circumstance. The duration is applied to the open-hole static nodes, including the bottom. It does not credit staging with cooling the bottom or iterate a revised staging schedule into the clock.

| Site | Added static time, h | Stages | Schedule basis |
|---|---:|---:|---|
| Soultz | 11.891 | 46 | FORGE practice; no passing schedule found |
| United Downs | 15.768 | 61 | FORGE practice; no passing schedule found |

**A5, evolving column.** Each existing open-hole static node is solved through the trip plus the possible elapsed run-in and staging time. The tool samples its depth at trip-end time plus elapsed run-in time, including stage pauses. The cased column remains frozen as in the base static-node model. The ledger saves that limitation, and this row does not implement the deferred common event timeline.

**A6, trip fluid.** The adverse breakout bracket keeps the drilling fluid through the trip and run-in. This reduces actual lower-bound slack even when the window-width change is slightly positive because the static temperatures change. The lighter fluid also changes the tool heat capacity and stage coolant. Both effects are shown separately.

| Site | Change in actual trip-fluid lower slack, SG | Change in actual trip-fluid upper slack, SG | Change in tool margin, C | Verdict |
|---|---:|---:|---:|---|
| Soultz | -0.064567 | +0.064705 | +2.8455 | NO-GO |
| United Downs | -0.069330 | +0.069425 | +3.6470 | NO-GO |

**A7, shallow circulation.** Soultz binds at the 4,000 m shoe on the upper drilling and trip bounds. Each ceiling is recalculated with the bit at that depth, retaining the original casing intervals and rebuilding the shorter string with its BHA. These are local binding-ceiling comparisons; deeper constraints retain their reviewed values. Both local ceiling changes are adverse. United Downs has no shallow common bound, so its entry is not binding.

**A8, surge and swab.** The prescribed brackets are zero and 0.04 SG per bound. At United Downs, zero allowance gives an open trip window in the family of fluid weights, while the drilling window and tool gates retain NO-GO. The actual reviewed trip weight and its slacks are saved, and the separate L6 design comparison tests reweighting with the full evaluation.

The 0.02 SG base value remains an assumption for these deep wells. Salih, Hadi and Al Saba (2024) report a 9.51 ppg water-based mud and a 9.92 ppg closed-string surge ECD at 60 m/min, a difference of about 0.049 SG. Their field-case simulation shows the dependence on speed and annular clearance; it does not establish a universal allowance for the 10 to 13 km geothermal programme. The zero to 0.04 SG ledger range is the evaluated comparison range. [Primary paper and case description](https://ijcpe.uobaghdad.edu.iq/index.php/ijcpe/article/view/1186).

**A9, resolution.** Radial log spacing is halved using twice the intervals and the same outer radius. Every existing wall timestep is split into two; tool integration and run-in steps are also halved. The depth-window spacing goes from 100 m to 50 m, with its existing local refinement. Separate changes and their combined change are reported. Static-node and pause caches are discarded for every comparison.

## Pannonian thresholds

The corrected programme's original FORGE staging peak is 203.171 C. Its selected closer-stage schedule gives 192.845 C. The corrected site is NO-GO because its common pressure windows are closed.

| Corrected programme comparison | Change in drilling width, SG | Change in trip width, SG | Change in tool margin, C | Any 20% threshold exceeded | Verdict |
|---|---:|---:|---:|---|---|
| radial spacing halved | -0.001380 | -0.000007 | -0.0001 | no | NO-GO |
| timesteps halved | +0.000086 | -0.000226 | +0.1035 | no | NO-GO |
| window spacing halved | -0.000157 | +0.000000 | +0.0000 | no | NO-GO |
| all three halved | -0.001484 | -0.000233 | +0.1034 | no | NO-GO |

The historical v1.3.3 peak reproduces at 199.958997626 C, leaving 0.041002374 C. Its 20% threshold is 0.008200475 C.

| Historical v1.3.3 comparison | Peak, C | Change in margin, C | Numerical threshold assessment |
|---|---:|---:|---|
| radial spacing halved | 199.959394 | -0.000396 | change below 20% of margin |
| timesteps halved | 199.860372 | +0.098626 | unresolved |
| radial spacing and timesteps halved | 199.860763 | +0.098235 | unresolved |

Halving the timestep changes the historical margin by about 0.099 C, greater than its entire 0.041 C margin. The 20% margin check therefore makes that historical tool-threshold claim unresolved, even though both calculated peaks remain below 200 C. The corrected schedule has several degrees of margin and does not exceed the same 20% rule.

## Decision relevance and conclusion

None of these brackets changes either deep-site verdict to CONDITIONAL or GO. Some corrections improve an individual margin: the lower face load helps slightly, and lighter trip fluid helps the tool while reducing breakout slack. Those effects do not remove the independent pressure failures. The A3 brackets do not reopen a deep site, A4 and A5 remain adverse, and A6 does not straddle the site verdict. The corresponding deferred modelling stays behind its stated triggers.

The base deep-site verdicts remain NO-GO for this programme and these assumptions across the A1-A9 comparisons performed. These generally change one approximation at a time and do not cover every joint uncertainty. The historical Pannonian 0.041 C tool margin is unresolved under the 20% margin check, while the corrected programme remains NO-GO on its common pressure windows.

## Evidence and reproduction

The [comparison runner](../../src/borethm/studies/robustness.py) and [saved outputs](../../results/robustness/) retain the settings, signed changes and numerical checks. Reproduce the comparisons with `python -m borethm.studies.robustness` from the repository root. The [historical review](../archive/v1.3.4/approximation-review.md) records the original runtime and test evidence.
