# Revised V0 execution record

Baseline: `f61a5d918285948c7254f1458c83992cdfb935cb`, on `hydraulics-v1.6.0`. The commit containing this record registers the protocol and input preparation before V2. It contains no package implementation or model result.

## Environment

Input extraction used Python 3.12.14 and pdfplumber 0.11.9, with the standard library for CSV, ZIP and workbook XML. The repository environment is Python 3.14.4, BoreTHM 1.5.0, NumPy 2.5.3, SciPy 1.18.1, iapws 1.5.5 and Matplotlib 3.11.2. No numerical solve ran in either environment.

Source downloads remain in `C:/Users/Liam/Downloads/FORGE 16A`. The extractor opens only `1295.zip`. The [inventory](source-inventory.json) identifies that source and the earlier input-only confirmation of 58-32 BHA records. No additional 78B source data was accessed in this stage.

## Extraction and reproducibility

Commands below run from the repository root in PowerShell. Set the interpreter path to a Python environment with the extraction versions above. The second extraction writes to an external directory so it can be compared with the prepared archive.

```powershell
$dataPython = 'PATH_TO_PYTHON_EXECUTABLE'
$rawFolder = 'C:/Users/Liam/Downloads/FORGE 16A'
$rebuildFolder = '../experiments/hydraulics-v160/revised-v0/rebuild'
& $dataPython validation/forge56-32/build_extracts.py --raw $rawFolder --output validation/forge56-32
& $dataPython validation/forge56-32/prepare_pressure.py --data validation/forge56-32
& $dataPython validation/forge56-32/audit_extracts.py --data validation/forge56-32
& $dataPython validation/forge56-32/build_extracts.py --raw $rawFolder --output $rebuildFolder
& $dataPython validation/forge56-32/prepare_pressure.py --data $rebuildFolder
& $dataPython validation/forge56-32/audit_extracts.py --data $rebuildFolder
& $dataPython validation/forge56-32/audit_extracts.py --data validation/forge56-32 --compare $rebuildFolder
```

During parser development, `build_extracts.py --skip-rig` rebuilt report inputs while preserving the rig extraction. The complete independent rebuild above checks the final parser, including the source-row aggregation.

The [rebuild verification](rebuild-verification.json) compares SHA-256 hashes of every generated file, including the candidate list. The manually transcribed manufacturer table is separate from these generated outputs. [Evidence manifest](evidence-manifest.json) identifies the prepared files and source archives. Manufacturer source-member hashes are in [source_reports.json](../../forge56-32/source_reports.json).

## Checks and stage boundary

```powershell
.venv/Scripts/python.exe tools/check_links.py
git diff --check
git diff --exit-code f61a5d918285948c7254f1458c83992cdfb935cb -- src tests docs README.md CHANGELOG.md pyproject.toml uv.lock
git diff --cached --check
git status --short
```

The audit reconciles 2,506,182 source rows and 250,629 input bins. Target checks are restricted to availability counts: 2,476,669 finite standpipe readings and 29,513 missing. No target range, mean, residual or model prediction is produced. It checks the preserved source conflicts and the candidate cutoff, and rejects model imports in the extraction/preparation scripts.

Results: all eighteen generated files matched the independent rebuild exactly. Input/provenance audits, JSON parsing and script syntax checks passed. The link checker passed across 85 Markdown files, and the whitespace checks passed. The baseline package, tests and documentation-site files were unchanged. Authored Markdown contained no searched mojibake markers.

Physical regression tests and the S2b calculation replay belong to V1 and later stages. This V0 changes no tracked baseline package, documentation-site, test, default, version or golden file. The abandoned harness and previous V0 draft directories remain uncommitted. No push, merge, tag or release is performed.
