# FORGE 78B-32 thermal forecast inputs

These files hold the inputs and code of the 78B-32 blind thermal forecast. The [protocol](../thermal_protocol.md) gives the rules. No file here contains a downhole temperature, a return temperature, a Sanvean reading, a report outlet or maximum temperature, or a pressure.

## Source

Utah FORGE well 78B-32 data, [GDR 1330](https://gdr.openei.org/submissions/1330). `1330.zip`: 15,431,810,676 bytes, SHA-256 `b56e77dbc8b5081352418fc8976e9c20da1f57bdd67fdc25961134ea99ced79f`.

The formation reference is the FORGE 16A 216-day temperature survey in this repository, [formation_temperature_216day.csv](../../forge16a/formation_temperature_216day.csv).

## Files

| File | Content |
| --- | --- |
| `list_archive.py` | Archive members, column headings with digits masked, and LAS curve mnemonics and units; prints no data row |
| `count_availability.py`, `availability/` | Counts of finite readings and of updates of the held-back channels by day, depth band and drilling window; flags only |
| `sanvean_headers.py` | Sanvean output file names, column headings and row counts |
| `build_inputs.py` | Builds `inputs/` from the archive after checking its hash; drops held-back report cells before any record is built |
| `inputs/rig_inputs_10s.csv.gz` | Pason ten-second time, depths, pump output, on-bottom ROP, rotary speed, weight on bit, block height, `TEMP IN` and pump strokes |
| `inputs/operations.csv` | Daily-report operations rows, with any description that mentions a pressure or a temperature suppressed |
| `inputs/mud_reports.csv` | Mud checks: density, rheology and the "In" temperature; the outlet cell is dropped |
| `inputs/report_flows.csv`, `inputs/bit_reports.csv`, `inputs/bha_reports.csv`, `inputs/casing_reports.csv` | Drilling parameters, bit records with nozzles, assembly lines and casing rows of the daily reports, without pressures |
| `inputs/survey-source.csv` | The 78B-32 directional survey as supplied |
| `check_flow_inlet.py`, `inputs/flow-check.csv`, `inputs/inlet-check.csv`, `inputs/flow-inlet-summary.json` | Pason flow and inlet against the daily reports |
| `build_bha_sheets.py`, `inputs/bha-sheets-ocr.txt`, `inputs/bha_sheets.csv`, `inputs/bha_components.csv` | BHA sheets of the end-of-well report read by OCR, with the corrections checked against the page images listed in the script |
| `inputs/manifest.json` | Source hashes, counts and output hashes |
| `common.py` | Clock, survey, formation, assembly assignment, sensor positions, nozzles, mud, casing and string geometry |
| `prepare_thermal.py` | The drilling windows, in `samples/` |
| `samples/windows.csv` | One row per window: inputs, assembly, inlet source and flag, sensor positions, mud, nozzle area, input status and the parts the window belongs to |
| `samples/qualified-bins.csv.gz` | The qualified ten-second bins of each window |
| `predict_thermal.py` | The forecasts, in [predictions-v1.9.0](../predictions-v1.9.0/README.md) |
| `extract_targets.py` | Run only after the declaration is public: extracts the targets into `../targets/` and records their hashes |
| `score_thermal.py` | Scores the forecasts as declared |

## Rebuild

From the repository root. The builders need pdfplumber 0.11.10 and openpyxl; the OCR pass of `build_bha_sheets.py --ocr` needs rapidocr-onnxruntime 1.4.4 and pypdfium2. The preparation and forecast need BoreTHM 1.9.0 installed from PyPI.

```bash
python validation/forge78b-32/thermal/build_inputs.py PATH/1330.zip
python validation/forge78b-32/thermal/check_flow_inlet.py
python validation/forge78b-32/thermal/build_bha_sheets.py
python validation/forge78b-32/thermal/count_availability.py PATH/1330.zip validation/forge78b-32/thermal/availability
python -m validation.forge78b-32.thermal.prepare_thermal validation/forge78b-32/thermal/samples
python -m validation.forge78b-32.thermal.predict_thermal validation/forge78b-32/thermal/samples validation/forge78b-32/predictions-v1.9.0 --workers 3
```

The builders open the archive read-only. `build_inputs.py` reads the Pason columns named in `inputs/manifest.json` and no other. The preparation and forecast scripts read only the committed extracts and import no target.

After the declaration commit is public:

```bash
python validation/forge78b-32/thermal/extract_targets.py PATH/1330.zip validation/forge78b-32/targets
python validation/forge78b-32/thermal/score_thermal.py validation/forge78b-32/scores
```
