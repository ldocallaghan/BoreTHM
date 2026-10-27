# S2b execution and reproducibility

Baseline: `85f23db51f6661e6ca09bd05c16b9ffb48881d83`, branch `forge16b-wholewell`, model/package version 1.5.0. No model function was edited or replaced. No fit entry point was called. Original S1 and S2 outputs are preserved by hash in the plan.

PowerShell commands, run from the repository root:

```powershell
$env:BORETHM_CACHE_DIR=(Resolve-Path '../experiments/forge16a-validation/s1/cache').Path
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
& .venv/Scripts/python.exe -m borethm.studies.forge16b_hydraulics prepare --data validation/forge16b --s2 validation/forge16b/s2 --output ../experiments/forge16b-wholewell/s2b
& .venv/Scripts/python.exe -m borethm.studies.forge16b_hydraulics run --data validation/forge16b --output ../experiments/forge16b-wholewell/s2b
& .venv/Scripts/python.exe -m borethm.studies.forge16b_hydraulics summarise --data validation/forge16b --output ../experiments/forge16b-wholewell/s2b
& .venv/Scripts/python.exe ../experiments/forge16b-wholewell/s2b_audit.py
& .venv/Scripts/python.exe ../experiments/forge16b-wholewell/s2b_report.py
& .venv/Scripts/python.exe ../experiments/forge16b-wholewell/s2b_publish.py
```

Both original and revised mud are replayed, 90 cases in total. Every replay converges; its saved S2 pressure and bore/return temperature endpoints are reproduced exactly. Summed case time is 48.4421 seconds, including external pressure calculations. There are 6,480 scenario budgets. No estimate is supplied to the temperature solver. The independent audit reconstructs 1,000 serial-component pressure rows and checks all scenario sums.

The raw log is retained outside the repository at `experiments/forge16b-wholewell/s2b-run.log` in the workspace. The first draft calculation stopped on the bit row: its gauge OD equals the hole diameter, which cannot be used as a sealed annular cylinder. No output table from that draft was published. The corrected external estimate retains the existing aggregate annulus OD over the short bit-body interval, as stated in the protocol and component table. The draft plan is retained outside the repo at `experiments/forge16b-wholewell/s2b-bit-gauge-draft/`; its initial error was a division by zero in the external annulus estimate. No circulation function or recorded dimension changed.

Runtime: Python 3.14.4; borethm 1.5.0; numpy 2.5.3; scipy 1.18.1; iapws 1.5.5; matplotlib 3.11.2. Source-PDF text checks used the bundled read-only environment with pypdf 6.10.0. Poppler rendered EOW p75 for visual confirmation against the recorded components. Sources and access dates are in the protocol.

For replay on another machine, supply the same checkout/calculation hashes and original input archive. A new output directory can be prepared from the archived S2 plan/results. This creates a fresh provenance snapshot without changing the sample list. Alternatively copy this frozen plan and its hash to an external output directory and use `run`; all paths listed in its `source_hashes` and `preserved_archives` must retain their recorded contents. New unlisted archive files do not affect those checks. A writable existing water-property cache avoids rebuilding the table. The published `replayed-profiles.npz` keys are original case ID plus `_z`, `_Td` and `_Tu`.

The report and audit helpers in the archive retain the local workspace layout used for execution. To regenerate only tables and figures elsewhere, place them beside an `s2b/` output directory containing the raw CSVs, and decompress `tool-joints.csv.gz` there. The publisher also expects the sibling repository directory and should be adapted to that destination layout. Its copying and compression do not affect numerical results.
