# Release checklist

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
- [ ] Tag v1.4.0 and publish the GitHub release; verify the PyPI publishing job.
- [ ] Check `pip install borethm` in a fresh environment from PyPI.
- [ ] Check the software's Zenodo archive, then add its all-versions DOI to the citation, README and NOTICE. Add an ORCID iD if supplied.
- [ ] Upload the benchmark ZIP as a separate Zenodo dataset record and add its DOI to the dataset guide and README.

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
