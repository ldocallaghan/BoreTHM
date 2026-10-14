# Preparing the v1.3.5 release

This is the maintainer checklist for the v1.3.5 release. Its changes and evidence are recorded in [release verification](../releases/v1.3.5.md).

## Editorial and publication checkpoint

Liam approved restructuring the summary as a scientific outreach briefing on 12 October 2026. It now leads with the research question and combines selected local-case counts with the independent programme failures. The detailed case table remains in the README. The reader-facing draft notice and implementation-status notes were removed as part of that approved restructure. Liam accepted the summary wording on 14 October 2026, as it stood after the reader-wording edits of that day. The accepted text, the licence change and their verification are recorded in the [release record](../releases/v1.3.5.md).

After Liam accepts or edits the wording, record that decision here and the accepted wording and verification in the release record. Regenerate and visually check the PDF after any edits. Its links use the BoreTHM repository on `main`; use `v1.3.5` for a frozen release copy when tagging. Confirm the citation date is the actual release date, and publish through the normal release process with the existing CI gate. The citation date is set to the release date, 14 October 2026; change it if the tag is made on another day.

Run `python tools/verify_v135_docs.py`, preserve model and data identity, and check the regenerated two-page PDF after editorial changes. Keep the existing CI gates for publication.
