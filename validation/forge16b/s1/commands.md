# S1 commands and execution record

Run from the repository root. Baseline: `85f23db51f6661e6ca09bd05c16b9ffb48881d83`; branch `forge16b-wholewell`. `$work` is outside the repository. Source selection and extraction commands remain in the S0 execution record.

```powershell
$work = '..\experiments\forge16b-wholewell\s1'
$env:BORETHM_CACHE_DIR = (Resolve-Path '..\experiments\forge16a-validation\s1\cache').Path
.\.venv\Scripts\python.exe -u "$work\trial_check.py"
```

The original trial replay ran first. Its 150 samples completed successfully with the existing saved parameters, without calling fitting routines. The published copy of `trial_check.py` is byte-identical to the executed script. It writes beside itself; run an external copy when repeating it.

Source drawings were transcribed with `build_inputs.py`, and the S1 protocol was written before whole-well predictions. An initial mud-association draft included later depth-channel resets; its saved input tables were corrected before any solve by ending a run at its first completed depth interval. Those draft inputs remain in the private execution directory.

The first separate-crossover geometry was attempted with default BLAS threads, then single-thread BLAS. Both attempts were interrupted during the first case after convergence warnings, without a completed result. The script, plan and both logs are preserved privately. The study construction was corrected to the existing 16A non-HWDP aggregation, preserving all recorded lengths and dimensions. No package calculation was edited. The completed run uses these commands:

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m borethm.studies.validate_forge16b_wholewell prepare --data validation/forge16b --output "$work\comparison" --selected '..\experiments\forge16b-wholewell\scratch\pason-selected-10s.csv' --trial-check "$work\trial-reproduction.json"
.\.venv\Scripts\python.exe -m borethm.studies.validate_forge16b_wholewell run --data validation/forge16b --output "$work\comparison"
.\.venv\Scripts\python.exe "$work\check_water_path.py"
.\.venv\Scripts\python.exe "$work\report_s1.py"
.\.venv\Scripts\python.exe "$work\audit_s1.py"
.\.venv\Scripts\python.exe tools/check_links.py
git diff --check
git status --short
```

Scripts used for report generation and arithmetic checks are retained with the execution evidence. The frozen plan, result checkpoints and source hashes are retained. The full original plan uses local calculation paths; the published execution manifest records their repository-relative names and hashes, plus the original plan hash. No sample, filter, fitted parameter, golden result or tolerance was altered after temperature errors were calculated. There was no commit, merge, push, tag or release.
