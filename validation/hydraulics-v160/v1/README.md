# V1 hydraulic implementation review

The shared hydraulic calculation is implemented and checked. This is the V1 STOP; held-out pressure comparisons and golden changes have not started. The implementation commit is the commit containing this report.

The protocol amendment was committed and pushed as `8bbfe2c44658dade8972a647970e3308047b6380` before target access. Its [review](../review-v0-amendment/README.md) includes the mapping reported before freezing, the old/new counts and both well protocols. The frozen selections give 18 motor-interval windows in nine events on 56-32 and 62 motorless windows in seven events on 58-32. For 56-32, 103 Discovery candidate windows are excluded: 90 have no-load availability as the primary exclusion and 13 also have conflicting event assignments. Rated-flow failure is reported independently, including overlaps. Sampling qualification does not establish complete numerical geometry.

## Changes to review

- [Review patch](V1-review.patch): package code, tests and documentation, together with the protocol amendment; large raw extracts and replay tables are omitted from the patch.
- [Shared losses](../../../src/borethm/hydraulic_losses.py): Bingham/Newtonian gradients, joint replacement and local losses, whole-tool coverage and surface equipment.
- [Programme](../../../src/borethm/programme.py): reference allowances and strict custom configuration. Site-file and evaluator overrides preserve the supplied profile.
- [Public API](../../../docs/api.md) and [changelog](../../../CHANGELOG.md).
- [Replay script](replay_s2b.py), [saved evidence](evidence/) and [energy-check script](check_energy.py).

The explicit v1.5.0 mode retains the original pressure and thermal friction calculation. It rejects new loss settings. The new mode shares density, viscosity and the 5 MPa property guard between pressure and dissipation. Supplied tool curves replace covered internal losses when requested. Their mechanical-power basis must be supplied correctly; the model treats the declared loss as dissipation and records that assumption.

The reference string retains its total lower-assembly length. The plain collar is 132.075968 m. Dual-wall and vacuum variants have hydraulic joint bore equal to body bore; the external connection envelope is a flagged transfer. The MWD reference is a published hydraulic allowance, with flow/temperature qualification flags. Custom strings receive no reference tool curve, and fixed custom strings are excluded from automatic pipe-substitution sensitivities.

Pressure integrates the shared gradients through the well. The hydraulic source uses the existing numerical geometry-blend width, with non-negative weights that sum to one. Endpoint reflection preserves the integrated loss of short tools, including a component shorter than half that width. This numerical placement is checked independently of the legacy midpoint contract. The annulus cumulative integral supplies partial-depth wall-pressure queries; surface equipment adds no downhole annulus loss or heat.

## S2b replay

All 90 frozen original/revised states and 6,480 scenarios reproduce with the package formula kernels at their archived property/evaluation points. Legacy standpipe pressure is identical to the archive. The maximum scenario-total difference is 6.82e-13 psi. No coefficient or acceptance tolerance was fitted. The replay took 83.00 seconds.

The full production calculation uses integrated properties and source placement. Across all scenarios its difference from the frozen-point replay is -2.124553 to 0.414479 psi. [Production reconciliation](evidence/production-reconciliation.csv) separates body integration, joint replacement, joint-local integration, geometric locals (including casing transitions), bottom nozzle state, buoyancy integration and surface inlet density. The `production_guard_delta_psi` column isolates the guard change on that production geometry. The largest unexplained arithmetic remainder is 6.27e-13 psi.

Applying only the guard to the original legacy geometry/sampling changes pressure by -0.110971 to -0.040049 psi, or -0.010995% to -0.006544%. The changelog records this diagnostic separately. The following production column uses EIS, 29-in restriction, abrupt changes and surface case 5; every other scenario remains in the CSV.

| EOW BHA | Archived mud | States | Guard-only change, psi | Production nominal change, psi |
| --- | --- | ---: | ---: | ---: |
| 12 | s1_original | 12 | -0.110971 to -0.072497 | -0.252078 to 0.034265 |
| 12 | s2_revised | 12 | -0.060942 to -0.040049 | -0.237125 to 0.082679 |
| 13 | s1_original | 14 | -0.058304 to -0.052364 | 0.154940 to 0.330314 |
| 13 | s2_revised | 14 | -0.061865 to -0.055720 | 0.164021 to 0.343108 |
| 15 | s1_original | 4 | -0.058846 to -0.056117 | 0.258887 to 0.288119 |
| 15 | s2_revised | 4 | -0.062463 to -0.059570 | 0.270701 to 0.300663 |
| 16 | s1_original | 15 | -0.059337 to -0.051512 | 0.210597 to 0.295991 |
| 16 | s2_revised | 15 | -0.053130 to -0.046141 | 0.227101 to 0.315048 |

This replay retains the archived 26.7 C rheology convention to test the original formulas. Field reruns with the assumed 48.9 C convention remain separate later work. Original S1/S2 numerical archives and S2b numerical evidence are unchanged. The S2b report's two citation-only file hashes are updated with their original hashes retained in its manifest; no numerical check is relaxed.

## Energy and tests

| Synthetic fluid | Assigned in-hole power, W | Applied heat, W | Residual, W | Tolerance, W |
| --- | ---: | ---: | ---: | ---: |
| water | 81892.551759 | 81892.551712 | -0.00004724 | 0.018189 |
| reference Bingham mud at 1200 kg/m3 | 130021.548172 | 130021.556914 | 0.00874157 | 0.023002 |

These variable-property checks use a synthetic 1,500-m reference well with supplied local restrictions. Assigned power sums pressure-gradient terms times their own local volumetric flows, plus nozzle and face input. Applied power is reconstructed from the equation sources and solved turnaround jump. The numerical tolerance is 0.01 W + 1e-7 of total power, allowing boundary-solver round-off. Surface loss and the signed density-column correction contribute zero heat. An energy-check failure makes a new-mode solve unsuccessful.

The fast suite passed **658 tests** in **48.77 s**; slow tests were excluded. It includes bit-exact comparisons against the frozen v1.5.0 pressure function, independent water/Bingham hand calculations, all API surface cases, tool scaling and overlap checks, short-component integral preservation, strict site-file parsing and evaluator precedence. Published benchmark snapshots remain unchanged: their comparisons explicitly assert that the newly added optional fields are absent. Link checking and the strict documentation build passed.

## Reproduction

Run from the repository root. The existing water-property cache is reused without rebuilding it. These are two existing environments; no dependency or version update was made.

```powershell
$env:BORETHM_CACHE_DIR=(Resolve-Path ../experiments/profiling-2026-10-23/warm-cache).Path
.venv/Scripts/python.exe -m pytest -m 'not slow' --basetemp=PATH_TO_NEW_EMPTY_TEST_DIRECTORY --junitxml=PATH_TO_TEST_REPORT --tb=short
.venv/Scripts/python.exe validation/hydraulics-v160/v1/replay_s2b.py --output validation/hydraulics-v160/v1/evidence
.venv/Scripts/python.exe validation/hydraulics-v160/v1/check_energy.py
.venv/Scripts/python.exe tools/build_api_docs.py
.venv/Scripts/python.exe tools/check_links.py
../experiments/profiling-2026-10-23/docs-venv/Scripts/python.exe -m mkdocs build --strict --site-dir ../experiments/hydraulics-v160/v1/site
git diff --check
```

Python 3.14.4; NumPy 2.5.3; SciPy 1.18.1; iapws 1.5.5; pytest 9.1.1. The separate documentation environment uses Python 3.14.4, MkDocs 1.6.1 and Material 9.7.7. Distribution metadata remains 1.5.0 pending the later release stage. [Checks and versions](evidence/checks.json) and the file manifest identify this review's evidence.

## Stage boundary

No 56-32 or 58-32 pressure target was inspected during the amendment or V1. Earlier inventory exposure remains disclosed in the original protocol. Missing catalogue passage IDs and their ranges, together with the remaining fluid-system ledgers, must be completed from inputs before numerical scoring. Committed BHA assignments and exclusions are frozen. No 78B source was accessed in these stages.

V2 pressure comparisons, slow tests and golden regeneration remain unrun. Built-in site verdict changes and the 16A/16B temperature reruns belong to later review stages. There is no version change, merge, tag or release.
