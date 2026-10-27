# Utah FORGE 16B whole-well comparison inputs

This directory contains source extracts and the input protocol for a whole-well comparison of circulating temperatures and hydraulic inputs. The [protocol](comparison_protocol.md) identifies the fixed filtering and sampling rules. Reader-facing results are archived for the [original comparison](s1/results.md), [rheology and energy comparisons](s2/results.md) and [motorless pressure accounting](s2b/results.md).

## Sources and licence

McLennan, J., Mock, B., Swearingen, L., Baldwin, R., Hodder, M., Vetsak, A., Kuhns, A.T., Breland, J. and England, K. (2023), *Utah FORGE: Well 16B(78)-32 Drilling Data*, Geothermal Data Repository, submission 1516, [DOI 10.15121/1998591](https://doi.org/10.15121/1998591). Source files are used under CC BY 4.0. Changes comprise column selection and null handling, observational quality flags, time/depth aggregation and transcription of report cells. Original downloads are unchanged. Page locators and source hashes accompany transcriptions.

The adopted formation-temperature data are the existing 16A 216-day log used in the packaged 16B study: Jones, C. (2022), *Utah FORGE: Deep Wells Temperature Surveys as of September 2022*, GDR submission 1421, [DOI 10.15121/1893533](https://doi.org/10.15121/1893533), CC BY 4.0. This input is shared with the existing comparisons.

The Pason EYE channel is present in the raw download, despite the earlier packaged trial data guide stating that no downhole time series was available. The whole-well extraction selects that channel by its header and retains the existing trial extracts unchanged.

## Files

| File | Contents |
|---|---|
| `source_manifest.json` | Download/member hashes, source column names and baseline identity. |
| `run_definitions.csv` | EOW/contractor BHA crosswalk, depth intervals, pipe types and sensor evidence. |
| `period_inventory.csv` | Source coverage, quality counts, operating ranges and candidate counts per period. |
| `period_input_summary.csv` | Per-period operating ranges, cooler context and mud-report locators. Mud ranges are contextual, not applied inputs. |
| `candidate_samples.csv` | 109 proposed half-hour comparisons, containing observations and paired inputs only. |
| `excluded_windows.csv` | Every rejected comparison window and its reasons. |
| `rejected_eye_rows.csv`, `isolated_jump_spells.csv` | Source-row quality flags and the reference values used for isolated-jump rejection. |
| `daily_eye_means_unfiltered.csv`, `trial_mean_check.csv` | Raw daily checks against the trial report, with filtered daily values separately labelled. |
| `pason_selected_1min.csv` | Selected one-minute channel means, counts and qualified EYE coverage. It is not a replacement for the raw source when reapplying quality rules. |
| `circulation_history_10min.csv`, `observed_off_spells.csv` | Whole-record circulation counts and directly observed pumps-off intervals for later exposure-clock inputs. |
| `mud_samples.csv`, `report_pages.csv`, `operating_notes.csv` | Mud cells and contextual report excerpts with page/date/hash locators. |
| `report_parse_audit.json` | Parsing coverage and merged-cell rows; partial rows preserve density/PV/YP but leave uncertain remaining fields blank. |
| `mud_log_versions.csv`, `mud_temperatures_by_depth.csv` | Header dates and hashes of all 54 mud-temperature logs, with paired depths from the final compiled log. |
| `surface_channel_crosscheck.csv`, `.json` | Observation-to-observation Pason/LAS temperature checks. |
| `surface_crosscheck_rejected.csv` | Physically invalid source pairs excluded from the channel-comparison statistics. |

S0 coverage differs from the four original trial averages. The candidate list applies drilling-progress requirements and temperature-quality rules, with explicit losses from limited or unchanging telemetry. See the [input summary](input-summary.md) for coverage tables and input uncertainties.

## Rebuild

Use an extraction environment with pandas 3.0.1; report-cell transcription also uses pdfplumber 0.11.9. These helpers are outside the installed model and introduce no model dependency. Supply the downloaded `1516.zip` and an external scratch directory:

```text
python validation/forge16b/build_extracts.py --raw PATH/1516.zip --scratch SCRATCH
python validation/forge16b/read_reports.py --pdf "SCRATCH/End of Well Report-16B78-32-May_2024.pdf"
python validation/forge16b/read_mud_logs.py --archive "SCRATCH/16B mud temp logs.zip" --pason-selected SCRATCH/pason-selected-10s.csv
```

The first command streams the source's 412 columns and stores only selected columns in scratch. A provenance sidecar verifies the input archive and selected-file hashes before cache reuse. The scratch PDF and mud-log ZIP are the corresponding members of `1516.zip`; copying them does not require unpacking the large Pason CSV. `--output` selects a separate destination for a rebuild, with `run_definitions.csv` supplied there. None of these commands imports or runs the BoreTHM model. Source extracts remain outside `src/borethm/` and are not runtime package data.
