# FORGE 58-32 thermal forecast inputs

These files hold the inputs and code of the 58-32 blind thermal forecast. The [protocol](../thermal_protocol.md) gives the rules. No file here contains a return temperature, a PT-log value or a report outlet temperature.

## Sources

Nash and Moore (2018), *Utah FORGE: Logs and Data from Deep Well 58-32 (MU-ESW1)*, Energy and Geoscience Institute at the University of Utah, [GDR 1006](https://gdr.openei.org/submissions/1006), [DOI 10.15121/1452735](https://doi.org/10.15121/1452735), CC BY 4.0. `1006.zip`: SHA-256 `43615d79d000104ae698de23dd5aee6a981bcaa9b9a72548690556eef5fb6caa`.

The formation reference is the University of Utah PT log of 8 November 2018, `UOFU_MU-ESW1_PT118.las` in `58-32_Temp_Pres_11_08_18.zip` (SHA-256 `04de1f0aebe92e6b3963fcc43f054033d0898cab3d9a238f78d8038ec2826ec8`).

## Files

| File | Content |
| --- | --- |
| `read_pt_headers.py`, `pt-headers.csv` | Whitelisted `~Well` keys of the PT logs and the workbook's sheet names |
| `build_thermal_inputs.py` | Builds everything in `inputs/` from the two archives |
| `inputs/operations-extended.csv` | Every operations row of every summary report, with pressure and temperature descriptions suppressed |
| `inputs/report_clock_10s.csv.gz`, `inputs/report-clock-intervals.csv` | Circulation clock for 27 to 31 August from the report operations |
| `inputs/pump_pressure_10s.csv.gz` | Ten-second means and counts of Pason `Pump Pressure` (native column 8) |
| `inputs/formation-pt118.csv` | PT118 temperature in 10 ft bins, with true vertical depth from the 58-32 survey |
| `inputs/manifest.json` | Source hashes, the flow constant and the rows behind it, counts and output hashes |
| `common.py` | Clock, assembly runs, nozzles, mud, casing and string geometry |
| `prepare_thermal.py` | Part A windows and the part B log schedule, in `samples/` |
| `samples/conditions.csv` | One row per drilling window: inputs, assembly, nozzle area, flows, inlet, pump pressure and input status |
| `samples/runs.csv` | Runs between trips to surface and their assembly status |
| `samples/log-plan.csv`, `samples/log-points.csv` | Log timing on the rig clock, the preceding circulation, and every forecast point |

## Rebuild

From the repository root, with BoreTHM 1.9.0 installed from PyPI and pdfplumber 0.11.9 and openpyxl for the builders:

```bash
python validation/forge58-32/thermal/read_pt_headers.py PATH/1006.zip validation/forge58-32/thermal/pt-headers.csv
python validation/forge58-32/thermal/build_thermal_inputs.py --raw-1006 PATH/1006.zip --pt118 PATH/58-32_Temp_Pres_11_08_18.zip
python -m validation.forge58-32.thermal.prepare_thermal validation/forge58-32/thermal/samples
```

The builders open the archives read-only. `build_thermal_inputs.py` checks both archive hashes before reading. It reads the Pason date, time and pump-pressure columns, after checking the single or split heading, and no other Pason column. The preparation script imports no model and reads only the committed extracts.
