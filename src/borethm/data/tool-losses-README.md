# Downhole tool-loss table

`tool_losses.csv` has one row per published figure for a downhole tool. `tool_loss_defaults.csv` holds the defaults derived from it, written by `tools/build_tool_losses.py` with the rule in `borethm/tool_losses.py`. These defaults are generic allowances. A maker's figure for the actual tool should be entered when it is available.

## Columns

| Column | Meaning |
|---|---|
| `tool_class` | `mwd_pulser`, `rotary_steerable` or `mud_motor`. MWD means measurement while drilling, a mud pulser sends its data to surface as pressure pulses, and a rotary steerable tool steers while the string rotates |
| `source`, `maker`, `model` | The source family that counts once in the median, and the tool as printed |
| `collar_printed`, `collar_in` | Collar size as printed, and in inches for the choice of band |
| `form` | `point`, `points` (two flows), `formula` or `recorded` (a figure that cannot enter the rule) |
| `flow_1_gpm`, `dp_1_psi`, `flow_2_gpm`, `dp_2_psi` | Printed pressure drops and flows |
| `formula_c` | The constant C in density × flow² / C, in lbm/galUS and US gal/min |
| `density_ppg`, `density_basis` | The density used for conversion, and whether it was printed |
| `printed` | The figure as printed |
| `document`, `edition`, `locator`, `url`, `sha256` | The document, its date, the place in it, and the file retrieved on 5 November 2026 |
| `used`, `note` | Whether the row enters the rule, and any limit |

## Bands and reference flows

| Band, in | Reference flow, US gal/min |
|---|---|
| 4.75 | 250 |
| 6.75 | 600 |
| 8 | 800 |
| 9.5 | 1,000 |

A tool or a table row takes the band nearest to its collar size.

## Classes with no usable figure

No published figure with a stated flow was found for a mud motor at no load. The sheets retrieved print one no-load or off-bottom figure for a whole flow range, so those rows are recorded and not used. No published figure was found for a filter sub or a float sub, so those classes have no rows. Each of these classes has a default of zero, with a warning in every result that uses it.

Rotary steerable tools have no figure in the 8-in band, so that band also has a default of zero with a warning. The 9.5-in rows for MWD pulsers and rotary steerable tools each have a single source.

Scientific Drilling's HALO and TiTAN22 figures are not public and are not in the table.

## Limits of the figures

The sheets state a fluid only in some cases, and none states a mud rheology. Where no density is printed the table takes water and says so. The formula sheets print no output unit, and psi is inferred from their field-unit form. The figures come from marketing and technical data sheets, whose test conditions are mostly not stated.
