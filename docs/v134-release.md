# v1.3.4 release verification

The three STOP reviews were accepted before C7. The corrected programme remains NO-GO for this programme and these assumptions at Soultz and United Downs. Pannonian is NO-GO, Larderello CONDITIONAL and Newberry GO. The sampled lever searches and the one pair at each deep site establish no full-site minimum.

The [release CI run](https://github.com/ldocallaghan/geothermal-thermo-hydraulic-model/actions/runs/38186784798) completed successfully on 12 October 2026, from source commit `3be5452536aab133bd41e7472dfc66e40c377a32`. It regenerated all five reference evaluations and the complete single-lever and pair study in a fresh directory, compared their physical rows with the reviewed checkpoints, then ran the complete fast and slow suite against the new pins.

| Check | Result |
|---|---|
| Full fast and slow regression suite | 455 passed; 0 failed, 0 errors, 0 skipped |
| Test-suite elapsed time | 3509.92 s (58.50 min) |
| Fresh reference and lever generation | 3408.34 s (56.81 min) |
| Retained evidence checksums | 112 files verified before import |
| Runtime | Python 3.14.4; packages from requirements-lock.txt |

The new pins are [the site table](../tests/golden/v134_site_table.json) and [the lever tables](../tests/golden/v134_lever_tables.json). Their [CI evidence manifest](../results/v1.3.4/ci/38186784798-1/manifest.json) links the full reference outputs, every trial and each bracket. The [JUnit report](../results/v1.3.4/ci/38186784798-1/tests.xml) records the tests and their timing. Earlier golden tables retain their historical modes and files.

C7 updates the README, reader summary and changelog, and advances citation and package metadata to 1.3.4. Public evaluation and the five-site command select the corrected release; historical tests and diagnostic figures request their earlier modes explicitly. Only the two release pins and their CI evidence were imported; the original STOP-review evidence remains available in the repository history and its existing paths.

The release retains the deferred work and triggers in the README. In particular, the near-threshold Soultz casing results trigger follow-up on the common event timeline; no operating range is claimed.
