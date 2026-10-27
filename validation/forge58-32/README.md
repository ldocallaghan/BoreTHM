# FORGE 58-32 pressure-comparison inputs

Input extracts for the second pressure well. The [protocol](comparison_protocol.md) applies the shared off-bottom sampling rules and fixes the BHA assignment before targets are read. Observations remain restricted to availability counts.

## Sources

Nash and Moore (2018), *Utah FORGE: Logs and Data from Deep Well 58-32 (MU-ESW1)*, Energy and Geoscience Institute at the University of Utah. [GDR 1006](https://gdr.openei.org/submissions/1006), [DOI 10.15121/1452735](https://doi.org/10.15121/1452735), CC BY 4.0. Download `1006.zip`: 2,399,231,901 bytes, SHA-256 `43615d79d000104ae698de23dd5aee6a981bcaa9b9a72548690556eef5fb6caa`.

The extractor opens only this archive. It streams the daily files in `Pason_Logs.zip`; pressure is counted for finite/missing availability only. Empty trailing CSV fields are discarded after checking that they are empty. Header/unit rows and unparseable time rows are counted separately. Source null -999.25 and non-finite values are missing; zero is retained. Flow outside 0–2,000 US gpm is unavailable input. Source row locators accompany every ten-second bin.

## Files and rebuild

| Files | Content |
| --- | --- |
| `rig_inputs_10s.csv` | 340,028 input bins from 3,397,398 source records; depth/flow extrema, input means and counts |
| `target_availability.json` | Per-file pressure finite/missing counts, with no values or ranges |
| `bha_reports.csv`, `bha_components.csv` | Dated BHA identity, complete reported component lists and available component OD/lengths; passage IDs remain unreported |
| `mud_reports.csv` | Reported density, PV/YP and the explicit reference-temperature convention |
| `bit_inputs.csv` | Whitelisted bit/jet cells from the input part of the DDR bit table |
| `survey.csv` | 59 source MD/inclination/azimuth/TVD stations, in ft/degrees |
| `casing_records.csv`, `operations.csv` | Dated casing headers and input-only chronology; mixed observation passages suppressed |
| `source_reports.json`, `extract-summary.json` | Source hashes and extraction counts |
| `motor_mapping.csv` | Reported motor status and source locators; unverified motor makers/sheets excluded |
| `off_bottom_windows.csv`, `off_bottom_events.csv` | Short-window candidates and event membership, with assignment and exclusion status |
| `old_off_bottom_qualification.csv`, `off_bottom_counts.csv` | Ten-minute comparison and counts by BHA/reason |

From the repository root, using Python 3.12 with pdfplumber 0.11.9:

```powershell
python validation/forge58-32/build_extracts.py --raw PATH_TO_DOWNLOADS
python validation/hydraulics-v160/prepare_pressure_windows.py --data validation/forge58-32 --well 58-32
```

No script imports BoreTHM or solves a model. Inlet temperature is an input; return temperature and PT-log values are excluded. The time zone is unverified. The pressure period stops before 14 September to separate subsequent completion operations. The raw one-foot drilling dataset and PT logs are not used to choose windows.

Early DDRs state assemblies as one text line; later DDRs give component OD/length tables. Both formats retain source locators. Table lengths are preserved as reported; a later adapter must distinguish individual and quantity-total lengths before constructing geometry. Unknown passage IDs need sourced catalogue inputs and sensitivities before numerical scoring. A short bit-only assembly record does not prove motor absence. No compatible motor no-load sheet has been established for 58-32, so documented motor windows are excluded from the interval score.
