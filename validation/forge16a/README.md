# Utah FORGE well 16A(78)-32

Source extracts for a comparison of BoreTHM's existing thermal calculations with measurements from a second FORGE well. The source files are accompanied by frozen circulation results and conditional transient comparisons. The [validation guide](../../docs/science/validation.md#forge-16a-blind-circulation-comparison) presents the blind result before its diagnostics and explains their limitations.

## Sources and attribution

- McLennan, J., Nash, G., Moore, J., Skowron, G. and Woolsey, S. (2021), *Utah FORGE: Well 16A(78)-32 Drilling Data*, Geothermal Data Repository, submission 1283. [DOI: 10.15121/1776602](https://doi.org/10.15121/1776602).
- Gilmour, B., Wooden, J., Pulka, F., Rose, B., Barker, C. and Borchardt, E. (2021), *Utah FORGE: Well 16A(78)-32 Logs*, Geothermal Data Repository, submission 1292. [DOI: 10.15121/1777912](https://doi.org/10.15121/1777912).
- Jones, C. (2022), *Utah FORGE: Deep Wells Temperature Surveys as of September 2022*, Geothermal Data Repository, submission 1421. [DOI: 10.15121/1893533](https://doi.org/10.15121/1893533).

The source datasets are distributed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). These files are derived extracts. Changes comprise column selection, unit-labelled headers, removal of source nulls, flow quality flags, time-bin averages, transcription of report cells and recalculation of formation-log true vertical depth from the directional survey. The original downloads are unchanged and are not included here. Each report transcription retains its archive, member name, report date, page and SHA256. Original source disclaimers remain in the downloads.

The formation-temperature workbook was compiled from the logs in submission 1292 and the survey in submission 1283. The same formation data were used in the 16B study. This comparison does not independently test the formation-temperature profile.

## Rebuild

Supply the downloaded `1283.zip`, `1292.zip` and `Utah FORGE Deep Well Temperature Profiles_Sept 2022.xlsx` in one directory:

```text
python validation/forge16a/build_extracts.py --raw "PATH/TO/FORGE 16A" --reports
```

The core extractor uses the Python standard library. The optional `--reports` step uses `pdfplumber` (0.11.9 in the recorded extraction environment). It reads the ruled cells of the daily-report PDFs. It requires no thermal-model installation or import. The Sanvean output CSVs and nested archives are read directly; large archives are not unpacked. One run package at a time is read into memory. `--output` can select a separate destination for checking a rebuild. `--skip-sanvean` refreshes the rig, survey and temperature extracts while retaining existing Sanvean series.

`build_report_tables.py` can also be run separately with `--raw` and `--output`. `audit_extracts.py --data PATH` checks row accounting, produces the run input table and checks the clock relation using depth and flow only. The extraction helpers perform no BoreTHM calculation, parameter fitting or prediction-error calculation.

## Extracts

| File | Contents |
| --- | --- |
| `sanvean_BHA*_10s.csv` | All 14 supplied runs in 10-second mean bins, with raw counts, valid counts, sensor maxima and drilling-qualified sensor means/counts. Units are in column names. |
| `run_inventory.csv` | Source dates, depth and flow coverage, sensor counts, quality counts and observed phase durations. |
| `run_inputs.csv` | Per-run drilling coverage, mud-log inlet/outlet ranges, report mud properties, nozzle candidates and unresolved sensor offsets. |
| `sanvean_sources.json` | Original column names, archive member locators and channel coverage/ranges. |
| `mud_log_by_depth.csv` | Horizon's one-foot log, including inlet/outlet temperature, flow, penetration and gain/loss channels. Temperatures are Fahrenheit, confirmed by the graphical log's annotations. |
| `rig_history_1min.csv` | Rig channels averaged by the timestamp actually present, with a circulating fraction and flow-valid count. The nominal 10-second CSV records timestamps to the minute, with repeated entries per minute. It has no usable bit-depth channel. |
| `rig_mud_channel_matches.csv` | Same-depth rig `MUD TEMP` and mud-log inlet/outlet values for channel identification. These are source-to-source differences. |
| `clock_alignment.csv` | Depth/flow agreement for the best three integer-hour shifts from a fixed -12 to +12 hour check, per run. |
| `survey_16a.csv` | All 422 survey stations, with original workbook row locators. Numeric values are read directly from XLSX XML, avoiding accidental date conversion. |
| `formation_temperature_57day.csv` / `formation_temperature_216day.csv` | Measured temperatures thinned at 10 ft MD, retaining the final point. TVD is interpolated from the survey; the workbook's polynomial TVD is retained in a separate column. |
| `daily_well_inputs.csv` | Daily mud properties and BHA descriptions. |
| `bha_components.csv` | Reported component dimensions and lengths. Missing cells remain empty. Overlapping PDF text that prevents numerical transcription is retained in a separate source-text column. |
| `bit_records.csv` / `casing_records.csv` | Reported bits, nozzles and casing entries, with source locators. |
| `operating_notes.csv` | Contextual report excerpts concerning cooling, losses, string components and sensors. A keyword match alone does not establish fluid loss. |
| `extract-summary.json` / `source_checks.json` / `report_extraction_audit.json` | Coverage, extraction accounting and report parsing records. |

## Coverage and interpretation

Nine exports have a bit-box temperature channel: BHA 18, 23, 30, 34, 35r1, 35r2, 38, 39 and 42. BHA 42 has no top-sub channel. BHA 9, 10 and 14 have lower-mandrel channels; those names remain distinct. The other early exports contain top-sub channels. The 14 exports contain 1,077,515 records.

The source flow filter accepts 0 to 2,000 US gal/min and flags all other finite values. It removes 121 records, including 15 above 100,000 gal/min. This is a conservative gross-error rule chosen from source units and operating ranges before thermal errors are computed; it is not a fitted threshold. Valid counts and invalid counts are explicit, and invalid flow is never replaced with zero. Missing values and the source sentinel -999.25 are blank. Circulation for the history clock means flow above 100 gal/min. Qualified drilling requires flow above 300 gal/min, the on-bottom flag, bit within 5 ft of hole depth, and penetration above 1 ft/h. Phase durations use elapsed source time and do not bridge gaps above 60 seconds. Downward motion with pumps off is a subset of the pumps-off duration, not the duration of a complete trip.

The rig mud-temperature channel is outlet-like: over 14,558 matched drilling minutes, its mean absolute difference from mud-log outlet is 1.70 degF, compared with 16.82 degF from inlet. Its exact physical sensor location is not established. It does not supply the inlet boundary. Inlet comes from the depth log; the transient fallback is the last depth-log value before the event. The clocks require no integer-hour offset in the depth/flow check.

The survey ends at 10,955 ft MD and 8,558.83 ft TVD, at 68.6 degrees inclination. The Sanvean maximum bit depth is about 10,961 ft. The 216-day workbook log stops at 10,740 ft MD and 219.36 degC; it does not cover the final approximately 221 ft of the Sanvean record. The 57-day log stops at 8,728 ft MD. Its recovery label is measured from cementing on 3 January; the 216-day label is measured from rig release on 12 January. Tail treatment must remain explicit in any later model comparison.

The daily reports locate a PUK sub above the motor, but do not establish the exact sensing-element offsets or map both exported temperature names to physical locations. The Sanvean PDFs are plotted records. All 55 members of the inner raw-data/configuration ZIPs are encrypted; the supplied output CSVs are readable. The comparison retains both bore and annulus predictions at the bit and 40 ft above it. Transient checks retain both existing tool nodes. No interpretation is selected for its agreement.

The 24 October report records mud coolers being rigged up before drilling. The later inlet-temperature fall does not establish the cooler's start date. Cooling is represented through measured inlet temperature only. A 7 November report records seepage losses; the BHA 35 deployments also have documented pipe washouts. Those are different hydraulic disruptions and are flagged separately.

See [the comparison protocol](comparison_protocol.md) for the method established before prediction errors are examined.

## Archived comparisons

`circulation-primary.csv` contains the 358 primary comparison records: 135 Sanvean on-bottom samples and 223 overlapping return-only rig samples. `circulation-metrics.csv` and `return-metrics.csv` contain the full configuration summaries. `recovery-summary.csv`, `inlet-counterfactual.csv` and `return-recovery-bracket.csv` are labelled diagnostics; they do not replace the blind result. `transient-events.csv` includes all 74 selected transient events and their unavailable cases; `transient-comparisons.csv` retains both tool quantities and static treatments.

`evidence-manifest.json` identifies the v1.5.0 calculation, source inputs and original output hashes. The S1 predictions are frozen. `forge16a_evidence.primary_summary()` recomputes their statistics without solving the model. The new golden test checks those archival summaries; it is not a numerical rerun or a test of a future model against the original field data.

For a separate new comparison, the circulation study accepts `prepare` and `run`, with an explicit output directory. The transient runner uses the study root containing `s1/plan.json` and writes `s2/` beneath it:

```text
python -m borethm.studies.validate_forge16a prepare --output STUDY/s1
python -m borethm.studies.validate_forge16a_transients prepare --output STUDY
python -m borethm.studies.validate_forge16a_transients run --output STUDY
```

Preparing the circulation input plan performs no circulation solves. The transient runner calls the unchanged wall/tool functions, including the recorded initial-history approximations and unavailable cases. A fresh run is separate from the archived blind evidence. The pre-calculation input definition remains in `comparison_protocol.md`; executed diagnostics and the direct-MD log-extension sensitivity are identified in the archived tables.

## Archive location and installed studies

The extracted records and comparison tables are checkout evidence under `validation/forge16a/`. They are excluded from the wheel and source distribution. No 16A data file is needed by the installed public model. Study modules accept an external archive through `--data PATH`; in a source checkout they use this directory by default. The archival summary functions also accept an explicit data-directory argument.

The [pause boundary audit](pause-outliers.md) traces the high pause predictions to their steady circulation starting states. Its [full table](pause-boundary-audit.csv) includes neighbouring selected events, profile identifiers, depths and the unrounded flow means. No event was rerun or numerical result revised for that audit.
