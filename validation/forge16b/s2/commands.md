# S2 commands and calculation identity

Baseline: `85f23db51f6661e6ca09bd05c16b9ffb48881d83`, branch `forge16b-wholewell`. Run from the repository root. All numerical execution outputs are outside the repository; selected evidence is subsequently copied into the source archive.

```powershell
$env:BORETHM_CACHE_DIR = (Resolve-Path '..\experiments\forge16a-validation\s1\cache').Path
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m borethm.studies.forge16_energy prepare --data16a validation/forge16a --data16b validation/forge16b --plan16a '..\experiments\forge16a-validation\s1\plan.json' --output '..\experiments\forge16b-wholewell\s2'
.\.venv\Scripts\python.exe -m borethm.studies.forge16_energy run --data16a validation/forge16a --data16b validation/forge16b --output '..\experiments\forge16b-wholewell\s2'
.\.venv\Scripts\python.exe '..\experiments\forge16b-wholewell\s2_q4_inputs.py'
.\.venv\Scripts\python.exe '..\experiments\forge16b-wholewell\s2_report.py'
.\.venv\Scripts\python.exe '..\experiments\forge16b-wholewell\s2_audit.py'
.\.venv\Scripts\python.exe tools/check_links.py
git diff --check
git status --short
```

The input-only draft of the plan was replaced before any new solve to remove stale S1 fallback-count metadata; no numerical input or method changed in that correction. The draft remains privately saved. The final plan and script were hashed before calculation. All source rows, rheology donors and versions are retained with the evidence.

The original 16A private input plan supplies its already frozen geometry and sample inputs. A published input subset and component table accompany the S2 evidence; local runtime paths are omitted from the public manifest. The full original plans remain in the external execution folder. The existing water-property cache is reused without modifying a model function or module attribute.

The S2 protocol is a labelled revision after S1 review, not a replacement of the earlier blind result. S1 and 16A source/output identities are checked against their saved hashes. No fitting, commit, merge, push, tag or release is performed. S3 documentation integration is outside this stage.

For a replay after publication, the source snapshot predates the new `s2/` evidence directory. Copy only the `source_b` paths listed in the frozen plan into an external input directory, preserving names and verifying hashes; point `--data16b` at that copy. Copy `plan.json` and `plan.sha256` into a fresh external output directory and run with the recorded package code. Do not prepare a different sample plan to replay these cases.

Runtime versions: Python 3.14.4, borethm 1.5.0, numpy 2.5.3, scipy 1.18.1, iapws 1.5.5, matplotlib 3.11.2.

Final verification: 934 converged cases; all 467 original-primary replays match their saved temperatures exactly. Independent checks cover all 934 Reynolds/film profiles and 54 mud-field assignments. The 64 recorded baseline files, original 16A archive and original S1 evidence remain unchanged. The link checker passed across 61 Markdown files, git diff --check passed, and the new text passed UTF-8/mojibake checks. No fast or slow suite was rerun at this numerical-study stage.
