# FORGE 58-32 pressure-test inputs

This directory contains the [registered comparison method](protocol.md) and a target-free numerical input plan. The original motorless cohort has 62 windows across seven events on BHA 2. The plan carries an explicit disclosure that two report pressure readings were seen during input preparation. Pason pressure-window observations have not been inspected. The comparison is interpreted with that prior exposure disclosed.

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

The reference calculation is the original v1.5.0 legacy mode; the working calculation is entry 8 with entry 10 smooth Colebrook and zero roughness; entry 8 with Blasius is secondary. Catalogue alternatives are input sensitivities and cannot select a pipe specification from agreement. The primary skill uses equal event weights on identical paired samples. No measured pressure target is present. The [model-only budget](model-only/README.md) contains calculated pressure parts for all three calculations. The original reference retains the v1.5.0 equations with D6's numerical blend and D7's physical-boundary mesh clipping; unmodified v1.5.0 fails to converge on this assembly. Its calculated budget and the independent starting-profile check accompany the other calculations.

`predict_budget.py --output` calculates all three budgets by default. The original reference uses the usual seeds with the D6 numerical blend and D7 boundary clipping. Each original window also receives the declared starting-profile check. `plot_budget.py --data --output` plots the saved event budgets for all three calculations.

The [catalogue-scenario predictions](predictions/README.md) use the same harness and fixed settings. The dated [paired-coverage clarification](coverage-clarification.md) makes explicit that a comparison cohort requires convergence in all three calculations. `score_comparison.py` separates a single raw-target reduction from reproducible builds using its saved reduction. Its synthetic tests cover missing bins, insufficient native observations and zero values, with an unavailable event retained in the coverage tables. No pressure observation chooses a coefficient or scenario.
