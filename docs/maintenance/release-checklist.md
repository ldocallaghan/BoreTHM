# Preparing the v1.3.5 release

This is a maintainer checklist for the current candidate. Candidate changes and evidence are recorded in [release verification](../releases/v1.3.5.md).

## Editorial and publication checkpoint

Liam approved restructuring the summary as a scientific outreach briefing on 12 October 2026. It now leads with the research question and combines selected local-case counts with the independent programme failures. The detailed case table remains in the README. The reader-facing draft notice and implementation-status notes were removed as part of that approved restructure. The new wording is ready for Liam's final personal review before outreach; the accepted final text has not yet been recorded.

After Liam accepts or edits the wording, record that decision here and the accepted wording and verification in the release record. Regenerate and visually check the PDF after any edits. Its links use the BoreTHM repository on `main`; use `v1.3.5` for a frozen release copy when tagging. Confirm the citation date is the actual release date, and publish through the normal release process with the existing CI gate. The current citation date is provisional for this candidate. No v1.3.5 tag has been created.

Run `python tools/verify_v135_docs.py`, preserve model and data identity, and check the regenerated two-page PDF after editorial changes. Keep the existing CI gates for publication.
