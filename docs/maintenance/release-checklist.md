# Preparing the v1.3.5 release

This is a maintainer checklist for the current candidate. Candidate changes and evidence are recorded in [release verification](../releases/v1.3.5.md).

## Editorial and publication checkpoint

**Pending Liam's editorial pass.** The summary retains its draft notice. Its proposed lead describes favourable local cases, independent programme failures and unresolved qualification together; accepted wording has not yet been recorded.

After Liam accepts or edits the wording, record that decision here and the accepted wording and verification in the release record. Remove the draft notice, regenerate and visually check the PDF, change its branch links to `v1.3.5`, confirm the citation date is the actual release date, and publish through the normal release process with the existing CI gate. The current citation date is provisional for this candidate. No v1.3.5 tag has been created.

Run `python tools/verify_v135_docs.py`, preserve model and data identity, and check the regenerated two-page PDF after editorial changes. Keep the existing CI gates for publication.
