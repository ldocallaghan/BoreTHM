# FORGE 58-32 pressure-test inputs

This directory contains the [registered comparison method](protocol.md) and a target-free numerical input plan. The original motorless cohort has 62 windows across seven events on BHA 2. The plan carries an explicit disclosure that two report pressure readings were seen during input preparation. Pason pressure-window observations were opened on 1 November 2026. The comparison is interpreted with that prior exposure disclosed. These pressure observations are now development data; the thermal targets remain reserved.

The source data are Nash and Moore (2018), *Utah FORGE: Logs and Data from Deep Well 58-32 (MU-ESW1)*, [GDR 1006](https://gdr.openei.org/submissions/1006), [DOI 10.15121/1452735](https://doi.org/10.15121/1452735), CC BY 4.0. Geothermal Resource Group's end-of-well report, PDF p29, Figure 14, supplies the full BHA 2 drawing. [references.json](references.json) identifies the published pipe scenarios and nominal casing bore.

`bha2-figure14.json` is a manual transcription of the drawing's factual dimensions, ordered from the bit upward. The daily summary prints eleven of seventeen component rows. `build_inputs.py` combines their more precise lengths with the six additional diagram rows, preserving the 0.79-ft difference from the reported assembly total. The nine heavy-weight joints have a total length of 272 ft. Their quantity does not multiply that total.

The ordinary-pipe size and connection machining remain unconfirmed. The 4-in primary and separate catalogue alternatives are declared assumptions. The original BHA IDs and sampling exclusions remain unchanged. Jar/shock losses and the installed surface layout have no finite sourced loss band. Input readiness means the registered data requirements are met under those assumptions.

| File | Content |
|---|---|
| `protocol.json` | Fixed model settings, catalogue scenarios and hashes of the original target-free inputs |
| `inputs/windows.csv` | Every planned window, with inlet coverage and mud transfer provenance |
| `inputs/events.csv` | Seven event identities and their window counts and input ranges |
| `inputs/components.csv` | All seventeen source components, with dimension provenance and model roles |
| `inputs/source-bins.csv` | Native source member/row locators for each of the 372 selected input bins |
| `inputs/circulation-clock.csv.gz` | Cumulative preparation-period circulation history, with no target channel |
| `inputs/geometry.json` | Source-length sums and the preserved total-length discrepancy |
| `inputs/coverage.json`, `inputs/manifest.json` | Input qualifications and reproducible checksums |

Run `build_inputs.py` from the repository root with an empty `--output` directory to rebuild the plan. Its optional `--raw` argument points to a directory containing `1006.zip`; this checks the end-of-well PDF checksum. It never opens the raw Pason archive. The existing rig projection is checked against its frozen compressed and uncompressed hashes before parsing, and its exact input-column whitelist is checked before data rows are used. No BoreTHM function is imported and no pressure prediction is calculated.

Mud is the nearest recorded measurement within the declared section, with the time offset retained even when the measurement is later than the window. The field PV test temperature and fluid-system continuity are unknown. The numerical protocol uses 26.7 °C for both models and records the assumed polymer-fluid section separately from the source measurements. The earlier extract's 48.9 °C convention columns remain historical source metadata.

The reference calculation is the original v1.5.0 legacy mode; the working calculation is entry 8 with entry 10 smooth Colebrook and zero roughness; entry 8 with Blasius is secondary. Catalogue alternatives are input sensitivities and cannot select a pipe specification from agreement. The primary skill uses equal event weights on identical paired samples. The input and model-only archives contain no measured pressure target. The [model-only budget](model-only/README.md) contains calculated pressure parts for all three calculations. The original reference retains the v1.5.0 equations with D6's numerical blend and D7's physical-boundary mesh clipping; unmodified v1.5.0 fails to converge on this assembly. Its calculated budget and the independent starting-profile check accompany the other calculations.

`predict_budget.py --output` calculates all three budgets by default. The original reference uses the usual seeds with the D6 numerical blend and D7 boundary clipping. Each original window also receives the declared starting-profile check. `plot_budget.py --data --output` plots the saved event budgets for all three calculations.

The [catalogue-scenario predictions](predictions/README.md) use the same harness and fixed settings. The dated [paired-coverage clarification](coverage-clarification.md) makes explicit that a comparison cohort requires convergence in all three calculations. `score_comparison.py` separates a single raw-target reduction from reproducible builds using its saved reduction. Its synthetic tests cover missing bins, insufficient native observations and zero values, with an unavailable event retained in the coverage tables. No pressure observation chooses a coefficient or scenario.

The [results archive](results/summary.csv) reports the registered pressure comparison. [Coverage](results/coverage.csv) retains all 62 windows and seven events. [Event results](results/events.csv) and [contrasts](results/contrasts.csv) distinguish event-weighted from window-weighted measures and preserve each catalogue scenario and the common cohort. [Window results](results/windows.csv) include target availability and solver status. [The primary plots](results/primary.png) show the measured comparison and residuals. The development log gives the interpretation and limits.

`results/access.json` records the source-member hashes and code commit, including the initial header-check failure and the compatibility correction. `results/manifest.json` identifies inputs, numerical predictions and every generated output. Rebuilds use the saved target reduction and do not reopen the raw archive. The primary and sensitivity predictions remain those committed before access.

### Interpretation and limits

**Calculated sign.** All three calculations overpredict every primary window and event. Event residuals are 139.9–274.3% of the measured event median, from `residual_percent` in [events.csv](results/events.csv), with `scenario=primary` and `cohort=scenario`. All `residual_psi` values in the corresponding [window results](results/windows.csv) are positive. The limit declared before access expected missing jar and shock-sub operating losses to make the calculations read low. The dominant error has the opposite sign and cannot be explained by adding those losses.

**Calculated bit-nozzle comparison.** The measured event median is already at or close to the original calculation's bit-nozzle pressure loss alone in these events. Values come from [event-budget.csv](results/event-budget.csv), columns `median_target_psi` and `bit_nozzles_psi`, for the primary scenario, scenario cohort and original calculation. The nozzle term is an event mean; the measured value is an event median, as registered.

| Event | Measured median, psi | Calculated nozzles alone, psi |
| --- | --- | --- |
| 58-32-off0081 | 205.3 | 207.6 |
| 58-32-off0084 | 470.6 | 485.7 |
| 58-32-off0092 | 510.3 | 488.7 |
| 58-32-off0096 | 513.6 | 510.9 |

**Calculated consistency check.** The remaining frictional losses are non-negative, including positive BHA-bore and annular losses. An absent ordinary-pipe segment has zero loss, and the original calculation has no separate surface-line allowance. The small buoyancy contribution is negative, only -0.05 to -0.21 psi in these four original event budgets. It cannot offset the additional losses. With the recorded nozzles, Pason `Flow In` and reported mud weight, a hydraulic calculation must also account for flow through the recorded BHA and the return path. This fixed input set cannot match the measured pressure while retaining those positive losses. At least one of these inputs, the recorded passages or the pressure channel is inconsistent with the others.

**Calculated depth increment.** From off0162 to off0192, the measured event median rises by 9.0 psi. The original calculation adds 161.1 psi and the working calculation adds 294.5 psi, from differences in `target_psi` and `predicted_psi` in [events.csv](results/events.csv). Flow is similar: the event medians of `flow_gpm` in [inputs/windows.csv](inputs/windows.csv) are 841.6 and 836.5 US gpm. These are shallow circulation events; the registered bit depths remain 552–1,884 ft with an approximately 581-ft BHA across the full comparison.

**Calculated flow scaling.** Between off0081 and off0084, at nearly the same depth, the measured event median rises with flow to the power 1.949. This is `ln(P_84/P_81) / ln(Q_84/Q_81)`, using `target_psi` in [events.csv](results/events.csv) and the event medians of `flow_gpm` in [inputs/windows.csv](inputs/windows.csv): 205.3 to 470.6 psi and 572.34 to 875.90 US gpm. The event depth ranges are 552.4 ft and 571.3–580.3 ft. **Inferred.** The near-quadratic response is consistent with a circulating pressure. A constant-factor flow error preserves that exponent, so this response is also consistent with such an error; it does not establish one.

**Inferred skill interpretation.** The registered negative skill remains the stage result. When every calculation reads high, a calculation that adds pressure scores worse regardless of the physical merit of those added terms. The working calculation includes API surface case 5, repeated joint losses and smooth Colebrook pipe friction, and predicts more pressure in every event. Its negative skill follows from that direction of change against these inconsistent inputs. This is the reverse of the registered check: if every calculation read low, added pressure could produce positive skill while every calculation still read low. Here the added pressure produces negative skill while every calculation reads high. The 58-32 result neither supports nor counts against the entry 8 and entry 10 changes until the input inconsistency is resolved. No tool-loss value is inferred from a residual and no correction is fitted.

**Calculated input relationship.** Across the 62 registered windows, `Flow In` divided by summed pump strokes is 5.5574–5.5576 US gal per stroke, within the rounded 5.55–5.57 range. For each window, the ratio uses its six registered ten-second bin means of `flow_gpm`, `pump1_spm` and `pump2_spm` in the [input projection](../rig_inputs_10s.csv.gz), located by [source-bins.csv](inputs/source-bins.csv). **Inferred.** Flow is probably derived from strokes multiplied by a configured displacement. That is unconfirmed. No candidate input is selected from this relationship.

**Inferred candidate inputs and source checks.** Each remains unresolved. These are checks for later work; none is run here.

| Candidate input | Check that would test it |
| --- | --- |
| Pason `Flow In` and its possible configured displacement | Rig pump liner and stroke records, including pump type and the configured volume per stroke |
| Bit nozzle area | Bit record with the installed nozzle count and diameters |
| Ordinary-pipe and heavy-weight drill-pipe (HWDP) bores | Installed string records with body and connection passages |
| Mud density | Mud reports and the density measurements used for these periods |
| Pressure channel | Daily-report pump pressures against the corresponding rig records |

**Inferred scope and equipment limit.** One motorless assembly and seven shallow events give weak evidence about other assemblies or depths in either direction. Every calculation omits the same unquantified operating losses for the jar and shock sub, together with any other tool without a published curve. Agreement or disagreement cannot identify the installed pipe or select a catalogue scenario. No new scenario, coefficient or registered measure is introduced after access. The calculations and archived results remain unchanged. FORGE 58-32 pressure is now development data and cannot be treated as unseen in later entries.
