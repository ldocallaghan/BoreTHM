# Release checklist

## v1.5.1

- [x] Review the property and geometry reuse and the assessment-scoped solve cache.
- [x] Remove the shared-search prototype after its macOS exact comparisons fail.
- [x] Compare all five exports exactly in each of the 12 CI environments.
- [x] Record three timings per site, stage shares and the coating trial.
- [x] Check Pyodide result copying and reproduce the full Newberry export exactly.
- [x] Preserve every saved result, golden and benchmark file.
- [ ] Build the 1.5.1 distributions and check a fresh wheel installation.
- [ ] Compare all five exports from the 1.5.1 wheel against the baseline.
- [ ] Pass the release fast compatibility matrix and full physical suite on CI.
- [ ] Check links, API page equality and the strict documentation build.
- [ ] Review the final diff and verified checks before tagging.
- [ ] Confirm the citation date against the actual tag date.
- [ ] Tag v1.5.1 and publish the GitHub release.
- [ ] Verify PyPI installation, Pages deployment and the Zenodo archive.

See the [v1.5.1 release record](../releases/v1.5.1.md) for verification and
publication status.

## v1.5.0

- [x] Review the packaged TOML starter, generated site files and input checks.
- [x] Review the five result readings and the updated user documentation.
- [x] Add a strict documentation build and a release-triggered Pages workflow.
- [x] Move the two saved-file breakout-timing tests into the fast suite.
- [x] Check published values against retained evidence in the fast suite.
- [x] Build and check the wheel and source distribution.
- [x] Check a fresh wheel installation outside the checkout.
- [x] Compare public names and signatures with v1.4.3, allowing the documented additions.
- [x] Compare the five reference exports and preserve all saved numerical evidence.
- [x] Pass the local fast suite, link checker and strict documentation build.
- [x] Pass the fast suite across Python 3.11 to 3.14 on Linux, Windows and macOS, and check wheel installation on all three platforms.
- [x] Pass the full physical suite on CI at the release candidate.
- [x] Review the complete diff and verified release checks before tagging.
- [x] Confirm the citation date against the actual tag date.
- [x] Tag v1.5.0 and publish the GitHub release.
- [x] Allow the release tag in the `github-pages` environment and verify deployment.
- [x] Verify the PyPI installation, documentation website and Zenodo archive.

See the [v1.5.0 release record](../releases/v1.5.0.md) for the checks and
publication status. The citation date and tag date are both 23 October 2026.

## v1.4.0

- [x] Move the models and data into the package without changing the calculation.
- [x] Document the public interface and the replacement commands.
- [x] Build and check the wheel and source distribution, including a clean installation.
- [x] Pass the fast suite on Python 3.11 to 3.14.
- [x] Configure the PyPI and TestPyPI trusted publishers and GitHub environments.
- [x] Publish to TestPyPI and check installation in a fresh environment.
- [x] Assemble benchmark dataset 1.0 from retained inputs and outputs, with a manifest and separate upload ZIP.
- [x] Update reader documentation and add contribution, support and issue guides.
- [x] Check documentation links and the hashes of protected evidence.
- [x] Pass the complete fast and slow suite on CI at the final candidate commit; retain the run and its JUnit report.
- [x] Review the final diff against v1.3.6, the README, API page and dataset before tagging.
- [x] Accept the release and confirm that the citation date matches the tag date, 22 October 2026.
- [x] Tag v1.4.0 and publish the GitHub release; verify the PyPI publishing job.
- [x] Check `pip install borethm` in a fresh environment from PyPI.
- [x] Check the software's Zenodo archive, then add its all-versions DOI to the citation, README and NOTICE. Add an ORCID iD if supplied.
- [x] Upload the benchmark ZIP as a separate Zenodo dataset record and add its DOI to the dataset guide and README.

See the [release record](../releases/v1.4.0.md) for the commands and validation requirements. Keep publication checks open until their results have been confirmed.

## v1.3.6

- [x] Reproduce the paired breakout-timing values within 0.002 SG.
- [x] Record the complete fixed delay scans and opening brackets.
- [x] Check the scientific page's result-derived numbers against the saved JSON files.
- [x] Run the eight breakout-timing regressions, including fresh paired calculations.
- [x] Run the complete fast and slow suites.
- [x] Verify the final diff and the hashes of protected files.
- [x] Prepare local HTML previews of the scientific page and README section.
- [x] Accept the scientific page and README wording before publication.
- [x] Set `CITATION.cff`'s release date to the tag date, 19 October 2026.

Publication uses the annotated tag `v1.3.6` and the [GitHub release](https://github.com/ldocallaghan/BoreTHM/releases/tag/v1.3.6).
