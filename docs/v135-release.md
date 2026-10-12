# v1.3.5 reader patch: verification and editorial review

This release candidate updates framing and reader readiness, then deliberately pauses model expansion for specialist feedback. Its baseline is v1.3.4 commit `1d19ac81e1de11e93ad492f876a1f5eca5a50b45`. The package metadata advances to 1.3.5 while the calculation mode, defaults and retained numerical evidence remain v1.3.4.

The project name is BoreTHM. The README, reader summary, PDF title and footer, citation title and package name (`borethm`) reflect the rename. The GitHub repository URL and retained calculation provenance remain the same.

The README is organised as a project guide, with setup and usage before result interpretation and example findings. Detailed derivations, diagnostic figures and the bibliography are in the [methods guide](methods.md); the full approximation and follow-up record is in [development priorities](development.md). The reader summary links to those priorities, and its PDF has been regenerated to preserve working links. The scientific results and their qualification are unchanged.

The [README](../README.md) and [reader summary](summary.md) place favourable target-depth cases beside the common-programme failures. Eight of nine Soultz cases and two of four United Downs cases have open target drilling intervals in the saved reference solution. These selected scenarios are not probabilities of successful drilling. Both deep sites remain NO-GO for this programme and these assumptions. The whole-hole pressure windows, tool schedules and INDETERMINATE coating qualification are reported separately.

## Evidence and calculation identity

The retained evidence was generated in [CI run 38186784798](https://github.com/ldocallaghan/geothermal-thermo-hydraulic-model/actions/runs/38186784798) at source commit `3be5452536aab133bd41e7472dfc66e40c377a32` and imported at `1d19ac8`. It is not newly generated v1.3.5 evidence. The [v1.3.4 release record](v134-release.md), [manifest](../results/v1.3.4/ci/38186784798-1/manifest.json) and [JUnit report](../results/v1.3.4/ci/38186784798-1/tests.xml) retain that provenance and its 455 passing tests.

| Reader output | Retained source under `results/v1.3.4/ci/38186784798-1/` |
|---|---|
| Case labels, strengths, target bounds and stability-cycle verdicts | `reference/{site}.json`: `cycle.cases[]`; UCS divided by 1,000,000 |
| Common-programme bounds and statuses | Reference JSON: `windows`, `status`; density bounds divided by 1,000 |
| Best attempted tool peaks and reference-practice run-in | `levers/{site}/L4/summary.json`: selected base trial, `metrics.tool_peaks_C`, `practice_run_in_peak_C` |
| Coating maxima, rating and qualification | Reference JSON: `tools.coating` |

The L4 base trial is selected by all settings: TK-Drakon coated pipe, 4,000 m shoe, 40/50 L/s, PV fraction 1, allowance 0.02 SG, delay 0 h, BHP null and coating rating 204 °C. Best attempted means the minimum peak in its retained schedule search. It is distinct from the reference-practice tool and coating histories.

Open target drilling intervals are counted using unrounded `drill_SG <= drill_SG_hi + 1e-9`, matching the existing diagnostic comparison. Displayed bounds use three decimal places; the verdict is copied from `cycle.cases[].verdict` and also reflects connections and the trip. It excludes the independent whole-hole, tool and equipment gates. Each site's reference thermal/hydraulic solution is reused across cases without scenario-by-scenario coupled reruns.

## Checks performed on 12 October 2026

| Check | Result |
|---|---|
| Offline reader evidence checks | All 13 rows, counts 8/9 and 2/4, four signed common windows, settings-matched tool schedules, coating status and five-site statuses verified |
| Retained evidence integrity | All 112 SHA-256 checksums matched |
| Existing fast suite | 357 passed, 98 slow tests deselected, 0 failures; 14.41 s |
| Supported numerical environment | Python 3.14.4; exact packages in `requirements-lock.txt`; single-threaded BLAS |
| Summary export | Two A4 pages, clickable source links, visually checked |
| Scope and formatting | Model source, data, physical defaults, numerical thresholds, workflow and goldens unchanged; relative links and metadata checked; `git diff --check` passed |

Commands, from the repository root in PowerShell:

```powershell
python tools/verify_v135_docs.py
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
.venv/Scripts/python.exe -m pytest --junitxml=.venv/v135-fast-tests.xml
git diff --check
```

The offline checker imports no model code and performs no physical solves. The summary renderer is also outside `src/`, so neither utility changes the model-source fingerprint. Run `python tools/render_summary.py` with ReportLab and pypdf available to reproduce the [two-page PDF](../output/pdf/summary-v135.pdf) from `docs/summary.md`. The draft PDF links to the candidate branch; update those links to the release tag when publishing.

No slow physical study or golden regeneration was needed for this documentation patch. The existing push fast check and scheduled/manual slow checks remain in the workflow. The verification table records local checks; no new full-suite CI run is claimed for this candidate.

## Deliberate pause and limitations

The base deep-site verdicts persist across the A1-A9 comparisons performed, which generally change one approximation at a time. No evaluated single-lever setting or evaluated pair reopened either deep site; one pair per site and sampled continuous settings do not establish a complete envelope. The circulation/FORGE checks, strength calibration and other well checks do not validate the entire 10-13 km programme.

H-01's proximity trigger is already met; implementation is deferred by project priority because other gates still fail and no operating range is claimed. Revisit before a near-threshold feasibility claim, or when specialist feedback or new data makes timing decision-relevant. Coolant delivery and fluid displacement retain distinct triggers. Pannonian's historical 0.041 °C tool threshold remains unresolved. A demonstrated defect can still require correction during the development pause.

Immediate exposure and the skin heuristic preserve the initial drilling demand in the base model. The delay experiments are unsupported hypotheses. Near-bit pre-cooling and breakout growth remain separate unresolved questions. Reader interest, usable observations or a discriminating hypothesis may justify a small new specification. Neither that study nor the FORGE image-log follow-up starts in this release. Outreach execution, application editing and automated follow-ups are outside this patch.

## Editorial and publication checkpoint

**Pending Liam's editorial pass.** The summary retains its draft notice. Its proposed lead describes favourable local cases, independent programme failures and unresolved qualification together; accepted wording has not yet been recorded.

After Liam accepts or edits the wording, record that decision here, remove the draft notice, regenerate and visually check the PDF, change its branch links to `v1.3.5`, confirm the citation date is the actual release date, and publish through the normal release process with the existing CI gate. The current citation date is provisional for this candidate. No v1.3.5 tag has been created.
