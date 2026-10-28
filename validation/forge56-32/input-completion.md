# Input completion and calculation for the 56-32 comparison

This amendment completes the inputs that the [protocol](comparison_protocol.md) and its [first amendment](protocol-amendment.md) left open, and fixes how the comparison is calculated. It is committed with the primary model predictions, before any 56-32 standpipe or differential pressure value is read. The window selections, BHA assignments and motor mapping committed at `8bbfe2c` are unchanged. [`compare_pressure.py`](compare_pressure.py) implements everything below.

## Calculations compared

The protocol compares v1.5.0 with v1.6.0. Since it was registered, v1.6.0 has gained the development entries recorded in the [development log](../../docs/science/model-development.md): the hydraulic losses of entry 1 with the D5 equipment representation, and the cylindrical rock response of entry 3. The v1.6.0 calculation here is the branch's working calculation. Entry 4's rotary heat is not applied, because the registered input extract holds no torque channel; on 16A and 16B it changed standpipe pressure by under 7 psi.

| Name | Mode | PV reference | Role |
|---|---|---|---|
| `legacy_26.7` | v1.5.0 | 26.7 °C | original calculation |
| `legacy_48.9` | v1.5.0 | 48.9 °C | input convention only |
| `current_48.9` | v1.6.0 | 48.9 °C | primary |
| `current_26.7` | v1.6.0 | 26.7 °C | sensitivity |

## Assemblies with complete inputs

Only BHA 9 and BHA 10 have complete inputs. Both carry the BICO SSS100-B5 motor, mapped as eligible with a flag in `motor_mapping.csv`, and every other component has a recorded bore. The others are excluded and counted:

- BHA 1: motor maker unknown.
- BHA 2 and BHA 3: the crossover sub has no recorded OD or bore, and no compatible catalogue entry has been sourced, so the geometry is incomplete under the first amendment.
- BHA 4 to BHA 7: no same-OD motor sheet, and the shock tool has no recorded bore.
- BHA 8 and BHA 11: the Discovery motor has no published no-load value.

This leaves 14 of the 18 primary off-bottom windows, in six events, and 199 of the secondary on-bottom windows. Three secondary windows have no inlet temperature and are excluded as incomplete input; no fallback is used.

## Geometry

The string is built from the BHA sheet in order. Body OD and bore come from the sheet; stabiliser blade OD is not a flow obstruction. The bit is a nozzle boundary with no body passage, as in D5, and its length is added to the drill pipe. Above the assembly is 5-in, 19.5-lb/ft drill pipe with a 4.276-in bore. Its 4 1/2 IF (NC50) connections use the catalogue scenario used for 16A: 6.625-in OD, 3.25-in bore, 29-in restriction and 31.5-ft pitch. Heavy-weight pipe has the same connection envelope around its recorded bore. Connection lengths of 0 in and 58 in are reported as sensitivities from the same temperature solution. Five primary windows have the bit shallower than the assembly's length, during trips; only the lower part of the assembly is then in the hole.

In v1.6.0 the motor carries the BICO whole-tool curve and no internal passage loss. Its thermal bore is 3.25 in, the bore of the adjacent UBHO, as a thermal-only assumption. The original calculation cannot resolve closely spaced short components, so in v1.5.0 items 2 to 5 (motor, UBHO, stabiliser and monel collar) form one length-weighted compact assembly, as in the 16A and 16B original calculations. Collars, jars and heavy-weight pipe stay separate.

Casing follows the first amendment's nominal IDs: the 20-in conductor to 129 ft (19.000 in), 13.375-in casing to 382 ft (12.615 in) and 9.625-in casing to 3,494 ft (8.921 in), with cement between strings out to the next casing or the recorded hole size. Below 3,494 ft the hole is open at 8.75 in. The well's own survey maps measured to vertical depth.

## Motor loss

The BICO sheet gives 475 psi no-load pressure, 300–700 gal/min, tested with clean water at 72 °F. The loss is `475 psi (rho/rho_ref)(Q/Q_ref)^2`, with rho_ref the water density at 72 °F and 101,325 Pa from BoreTHM's water properties. Q_ref = 700 gal/min gives the lower bound and 300 gal/min the upper bound. In v1.6.0 the loss and its heat are part of the solve. In v1.5.0, which accepts no tool curve, the same loss is added to the calculated standpipe pressure; the compact assembly's friction then counts the motor's thermal bore a second time, which adds a few psi. Windows with flow outside 300–700 gal/min are flagged.

## Bit nozzles

BHA 10's jets (three 13/32 in and three 14/32 in) give 0.840 in², which matches its printed TFA and the bit workbook. BHA 9's printed jets, three 14/32 in and four 13/32 in, give 0.969 in², but its printed TFA and the workbook both give 0.840 in². The first amendment prefers recorded jets, but here two separate records agree against the jet text, so 0.840 in² is used for BHA 9 and the jet-derived area is reported as a sensitivity. The nozzle coefficient stays 0.95.

## Fluid, temperatures and heat transfer

Mud density and the paired PV and yield point follow the registered rule: the nearest sample in the same hole section, ties to the earlier sample. This reproduces every value in `candidate_windows.csv`. The inlet temperature is the window mean of the Pason inlet channel, read as °F. The formation temperature is the FORGE 16A 216-day profile against vertical depth, constant beyond its end. Rock properties are the FORGE values, the film multiplier is 1.0, and exposure is the cumulative circulation clock from the ten-second extract, counting bins with valid flow above 100 gal/min, with the 1-hour floor.

Off-bottom windows have no face heat. Secondary windows use the non-negative reported motor differential times flow as face heat, which needs the differential channel; those predictions are calculated after the targets are read, with no other change.

## Surface loss and outputs

API surface case 5 is primary for v1.6.0. Cases 1 to 4 and no surface loss are reported from the same temperature solution. For each window and calculation, the outputs are the predicted standpipe pressure, or for motor intervals the lower and upper bounds, and the flags. The measured target is the mean standpipe pressure over the window's source rows; the secondary target subtracts the mean raw differential over the same rows. Event summaries, residuals and interval coverage follow the first amendment.
