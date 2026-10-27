# FORGE 56-32 pressure-comparison inputs

Input extracts for the planned unfitted comparison of BoreTHM v1.5.0 and v1.6.0 standpipe pressure. Stationary off-bottom circulation is primary; on-bottom pressure minus reported differential is secondary. The [comparison protocol](comparison_protocol.md) defines the method before predictions or errors are calculated.

The [review amendment](protocol-amendment.md) replaces the original off-bottom rule with short windows and event weighting. All eleven BHAs contain motors, so this well supplies the motor-interval measure; motorless primary observations come from 58-32. Current selections are in `off_bottom_windows.csv`, event membership in `off_bottom_events.csv` and old/new counts in `off_bottom_counts.csv`. The [motor mapping](motor_mapping.csv) records all exclusions. The original ten-minute files below remain reproducible historical inputs.

## Sources and attribution

Bristol, Caldwell, Welch, Stroud and colleagues (2021), *Utah FORGE: Well 56-32 Drilling Data and Logs*, Energy and Geoscience Institute at the University of Utah. [GDR 1295](https://gdr.openei.org/submissions/1295), [DOI 10.15121/1777170](https://doi.org/10.15121/1777170), [OEDI record](https://data.openei.org/submissions/9753). The source drilling dataset is supplied under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Manufacturer specifications retain their own attribution; this archive includes transcribed input facts and source hashes, without redistributing their PDF sheets.

The source is the downloaded `1295.zip`. Its SHA-256 is `7ffa76e05cbd89984f04b15cac00dcf88df425ecac79a011c8f1c300a7067781`. Read source archives in place; the large CSV members are streamed without unpacking them to disk. No other well's download is opened by the extractor.

## Rebuild

Use Python with `pdfplumber` installed. Run from the repository root, substituting the download folder:

```powershell
python validation/forge56-32/build_extracts.py --raw PATH_TO_DOWNLOADS --output validation/forge56-32
python validation/forge56-32/prepare_pressure.py --data validation/forge56-32
python validation/forge56-32/audit_extracts.py --data validation/forge56-32
```

To check an independent rebuild, add `--compare PATH_TO_REBUILD` to the audit command. It compares SHA-256 hashes of all eighteen generated files.

`tool_specifications.csv` is a manual transcription of manufacturer facts from the cited pages; rebuilding the source extracts preserves it. The audit reads inputs and availability counts only. No script imports BoreTHM or calculates a model result. No pressure/temperature target series is written. The input history contains inlet temperature; measured return/downhole temperature and pressure are excluded.

## Extracts

| File | Contents |
| --- | --- |
| `rig_inputs_10s.csv.gz` | 250,629 input bins from 2,506,182 native rows, with source-row locators, validity counts and within-bin depth/flow extrema |
| `survey.csv`, `survey-source.json` | 97 source survey stations and original headings; depths/elevation are ft, UTM coordinates are metres |
| `bha_runs.csv` | Eleven BHA sheets, their dates/depths and preserved source conflicts |
| `bha_components.csv` | 87 component entries, lengths and separate body/stabiliser dimensions; unknown IDs remain blank |
| `bit_records.csv` | Sixteen workbook records with source row, bit/TFA, motor configuration and original Excel date serial |
| `bha_crosswalk.csv` | Provisional sheet/workbook mapping, with stated endpoint tolerances |
| `mud_reports.csv` | 28 selected DDR mud samples; density, PV/YP, gels and the explicit reference-temperature assumption |
| `casing_records.csv` | 94 dated casing entries, including the original shoes and weights |
| `pipe_tallies.csv` | Reported pipe size, count, weight, grade and connection entries |
| `operations.csv`, `operating_notes.csv` | Structured operating chronology and daily BHA descriptions; mixed observation passages are suppressed |
| `tool_specifications.csv` | Manufacturer no-load facts and missing reference quantities, with source page |
| `candidate_windows.csv`, `window-preparation.json` | Input-only window candidates and source-readiness flags; no score or target values |
| `target_availability.json` | Finite/missing target counts per weekly source, without values or ranges |
| `source_reports.json`, `report_extraction_audit.json`, `extract-summary.json` | Source hashes and parsing/coverage accounting |

## Derived-extract changes

The extractor selects permitted input columns, groups them by source-clock ten-second bins and records means/counts. It preserves depth and flow extrema for movement/state checks. Empty/non-numeric/non-finite values and the Pason null convention -999.25 are missing. Zero is preserved. Flow outside 0 to 2,000 US gpm is flagged unavailable input. Source rows are retained as locators; the four weekly exports are not combined with overlapping standard/one-second exports.

Report transcription strips surrounding whitespace and retains field/source-cell text where needed. Decimal and explicit fractional dimensions are converted to numeric inches. Source geometry and bit numbering are retained separately. A date in BHA 3's depth-out cell stays unresolved; the 3,500-ft candidate is derived from depth-in plus printed footage and flagged. BHA 5 lacks a date-out. Workbook and sheet endpoints can differ; the crosswalk does not erase them.

Pressure, motor differential and measured thermal targets are represented only by finite/missing counts. There are 2,476,669 finite standpipe readings and 29,513 missing entries in the four weekly files. These are source-row counts, not independent pressure samples. No target physical-range filtering or model comparison has been performed.

## Coverage and interpretation

The Pason source clock covers 8 February 2021 at 04:30 through 9 March at 06:00. Its time zone is unverified. The pressure preparation stops before 28 February to separate the supplied drilling BHAs from later completion work. Do not treat calendar-only BHA dates as exact trip boundaries. Daily-report and Pason clock relationships still need input-based reconciliation where exact events are used.

Pason labels inlet/return as Degrees. The input inlet is treated as Fahrenheit under the report convention and flagged. The selected mud tables do not state the PV measurement temperature; 48.9 C is an assumption and 26.7 C a sensitivity. The reported mud inlet temperature does not establish the rheology test temperature. No site-file or package default has changed.

Several motor/shock passage IDs and casing dimensions are absent. Manufacturer off-bottom pressure figures lack complete reference-flow/density information, and some motor configurations do not match the pictured sheets. The candidate list therefore remains input preparation. Its 18 off-bottom and 1,022 on-bottom candidates are not a certified complete primary score set. Source rulings and any amendments must be committed before targets are read for comparison.

Prior inventory work exposed one report's pressure summary. That is disclosed in the protocol. No model prediction has been calculated for 56-32. Preserve that distinction in any later publication.

The input history uses deterministic gzip compression. [rig-inputs.json](rig-inputs.json) records compressed and uncompressed SHA-256 hashes and sizes; decompression preserves the original CSV bytes. The same recorded zlib version reproduces the compressed bytes; the uncompressed hash checks CSV identity across compression-library versions.
