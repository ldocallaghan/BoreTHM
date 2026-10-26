# Pause outlier boundary and starting-state audit

The existing profiles and event curves were read without rerunning circulation, wall or tool histories. The checks reconstruct every pause profile key from its recorded preceding five-minute inputs and verify all saved primary starting temperatures against that profile and the existing steady-steel formula.

| Event | Pause MD ft | Profile bit MD ft | Flow gal/min | Inlet °F | Bore at pause °C | Model initial range °C | Model peak range °C | Measured peak °C |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 23-off016 | 7258.5 | 7400 | 225 | 126 | 106.05 | 105.98–106.72 | 106.02–106.91 | 79.50 |
| 30-off009 | 7594.1 | 7600 | 225 | 120 | 98.63 | 98.62–98.75 | 98.63–98.98 | 83.00 |
| 30-off010 | 7594.5 | 7600 | 250 | 120 | 95.11 | 95.10–95.24 | 95.11–95.86 | 83.10 |
| 30-off011 | 7594.5 | 7600 | 250 | 120 | 95.11 | 95.10–95.24 | 95.12–96.23 | 83.20 |
| 34-off008 | 8151.2 | 8400 | 350 | 118 | 94.63 | 94.59–94.98 | 94.64–95.05 | 85.80 |
| 35r1-off005 | 8371.5 | 8400 | 275 | 120 | 107.45 | 107.43–107.59 | 107.47–108.89 | 90.40 |
| 35r1-off006 | 8340.1 | 8400 | 275 | 120 | 107.41 | 107.39–107.59 | 107.43–107.65 | 89.90 |
| 35r2-off015 | 8529.1 | 8600 | 325 | 120 | 104.23 | 104.20–104.43 | 104.22–104.47 | 94.81 |
| 39-off018 | 9209.0 | 9400 | 300 | 92 | 106.55 | 106.52–106.81 | 106.61–108.12 | 94.65 |
| 39-off019 | 9210.2 | 9400 | 225 | 92 | 120.68 | 120.64–120.93 | 120.67–120.94 | 95.00 |
| 42-off020 | 10665.0 | 10800 | 175 | 92 | 154.74 | 154.71–154.92 | 154.74–155.25 | 114.41 |

All eleven named cases use successful, converged profiles and their correct run identifiers. Every target and the 40-ft position lie within its named profile. The high model temperature is already present at pump stop; it was not produced by a surge in calculated reheating during the pause. The CSV and JSON include every neighbouring selected pause, the exact profile identifier and its unrounded input means.

The reduced recorded flows produce hot steady circulation profiles. Each pause independently starts the tool at that steady profile, even when the preceding low-flow period is short or variable. The measured temperature retains its preceding thermal history. This declared quasi-steady starting-state approximation explains the artificial jumps between modelled pauses; it does not establish why the field measurement differs. The code implements the recorded method, with no wrong profile key, run, unit conversion or starting-temperature selection found for the named outliers. No numerical result is changed and no event is rerun.

For example, 42-off019 uses 500 gal/min and starts its internal-fluid node at 96.05 °C; 42-off020 uses 175 gal/min and starts at 154.74 °C; 42-off021 uses 375 gal/min and starts at 114.27 °C. Their measured peaks are 116.30, 114.41 and 116.29 °C. The 175 gal/min profile is a steady calculation applied to a brief, varying low-flow record, not an observed 40 °C heat rise. The named outliers are not evidence for rapid rock reheating.

A small endpoint-clamping approximation also occurs: 23-off012 has a median pause depth of 7,005.8 ft while the rounded preceding profile ends at 7,000 ft. Its interpolation is clamped over the final 5.8 ft. This is reported explicitly in the full audit. The calculation interpolates the declared rounded profile, using its endpoint over that final 5.8 ft. This approximation is retained and disclosed; it is not a mismatched run or profile. It does not explain any named hot outlier.
