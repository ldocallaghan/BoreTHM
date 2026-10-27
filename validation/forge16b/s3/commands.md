# S3 verification commands

Run from the repository root, with the original v1.5.0 environment:

```powershell
$env:BORETHM_CACHE_DIR=(Resolve-Path '../experiments/forge16a-validation/s1/cache').Path
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
& .venv/Scripts/python.exe -m pytest --durations=10 --junitxml=../experiments/forge16b-wholewell/s3/fast-tests.xml --basetemp=../experiments/forge16b-wholewell/s3/pytest-temp
& .venv/Scripts/python.exe -m pytest tests/test_forge16b_evidence.py -q
& .venv/Scripts/python.exe tools/check_links.py
$env:BORETHM_DOCS_REF='main'
& ../experiments/own-site-v150/c4/docs-venv/Scripts/python.exe -m mkdocs build --strict --site-dir ../experiments/forge16b-wholewell/s3/site
git diff --check
git status --short
```

Fast suite: 616 passed, 104 skipped in 40.02 s. The JUnit duration is 40.002 s. The 22 archive tests were rerun after final evidence publication. Numerical Python/library versions and source commands are in the [S2b commands](../s2b/commands.md). Documentation uses MkDocs 1.6.1 and Material 9.7.7 in the existing documentation environment. The theme prints an informational notice about a future MkDocs version; it is separate from build diagnostics, and the strict build passes.

Logs and the rendered website are retained outside the repository under `experiments/forge16b-wholewell/s3/` in the workspace. The verification JSON and patch are copied here for review. The review patch includes new S2b code/protocol/tests and tracked documentation changes; it excludes the earlier S0/S1/S2 evidence and generated CSV/profile payloads. Those are listed and hashed in their stage manifests.

The final audit reads the 64-file S0 baseline hash list, the frozen 48-file 16A archive and the 66-file S1/S2 preservation list in the S2b plan. It also checks every published stage output hash and scans tracked UTF-8 text plus new S2b text for mojibake. The separate [S2b audit](../s2b/s2b_audit.py) reconstructs component losses and all pressure budgets. No model function is modified by either audit.

No commit, merge, push, tag, release or website deployment was run.
