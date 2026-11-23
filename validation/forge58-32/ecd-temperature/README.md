# FORGE 58-32: circulating temperature and ECD at the bit

This calculation asks how much the temperature of the circulating mud changes the equivalent circulating density (ECD) at the bit, and how closely that temperature needs to be known. It is a model calculation. No downhole pressure measurement is used.

## Cases and windows

The bottom-hole pressure while drilling is the static mud column plus the annular friction loss (`pressure.bottomhole_pressure`, state `"drilling"`). It is calculated with the same mud under three temperature treatments:

- A: surface temperature, viscosity as reported. Density is at the mud's reference temperature, `fluids.T_REF`, 20 °C, and PV at the report's reference temperature, 48.9 °C;
- B: the static formation temperature, the PT118 profile used as the forecast's geotherm;
- C: the circulating temperatures of the BoreTHM 1.9.0 solve.

The windows are drilling windows of the [thermal forecast](../predictions-v1.9.0/README.md) with the primary flow: the deepest of the 760 scored windows, and the scored windows nearest a half and a quarter of its bit depth. The circulation solve was repeated with the committed inputs and gave the committed return temperature exactly in all three.

| Window | Sample | Assembly | Bit, ft MD | Mud, ppg | PV, cP | YP, lbf/100 ft² | Predicted return, °C |
|---|---|---:|---:|---:|---:|---:|---:|
| Shallow | 58t-0074 | 2 | 1,887.74 | 9.1 | 16 | 24 | 53.01 |
| Mid-depth | 58t-0246 | 5 | 3,766.09 | 9.4 | 15 | 20 | 61.33 |
| Deepest | 58t-0821 | 20 | 7,530.58 | 8.6 | 6 | 13 | 56.59 |

The settings are the v1.9.0 defaults: the Herschel-Bulkley annulus with the Erge et al. (2015) transition band, the no-yield power law from PV and YP, and smooth Colebrook pipe friction. Density is the barite and IAPWS-95 water model. PV follows water's viscosity from its 48.9 °C reference, and YP is constant. In cases A and C the annulus is laminar in all three windows.

## Results

In the deepest window the formation is at 199 °C at the bit and the circulating mud at 53 °C. There, the static formation temperature gives an ECD at the bit 0.0477 SG (0.40 ppg, 155.6 psi) below case C. Surface temperature gives an ECD 0.0158 SG (0.13 ppg, 51.5 psi) above it. A shift of 2 °C in the whole circulating profile changes it by 0.0015 SG (0.013 ppg, 5.0 psi).

ECD at the bit, SG (ppg):

| Window | A | B | C |
|---|---:|---:|---:|
| Shallow | 1.1085 (9.25) | 1.1040 (9.21) | 1.0949 (9.14) |
| Mid-depth | 1.1628 (9.70) | 1.1389 (9.50) | 1.1399 (9.51) |
| Deepest | 1.0572 (8.82) | 0.9937 (8.29) | 1.0414 (8.69) |

| Window | Difference | ECD, SG | ECD, ppg | Total, psi | Column, psi | Friction, psi |
|---|---|---:|---:|---:|---:|---:|
| Shallow | C − B | -0.0091 | -0.08 | -7.5 | -4.3 | -3.2 |
| Shallow | C − A | -0.0136 | -0.11 | -11.1 | -10.3 | -0.9 |
| Mid-depth | C − B | +0.0010 | +0.01 | +1.6 | +8.6 | -7.1 |
| Mid-depth | C − A | -0.0230 | -0.19 | -37.5 | -28.5 | -9.0 |
| Deepest | C − B | +0.0477 | +0.40 | +155.6 | +141.2 | +14.4 |
| Deepest | C − A | -0.0158 | -0.13 | -51.5 | -44.8 | -6.8 |

![ECD and fluid temperature against depth, deepest window](ecd-profile.png)

In every window the hotter column is the lighter one. The column part of each difference comes from density. The friction part comes from PV, which follows water's viscosity and falls as the mud warms. With PV fixed, density alone changes the friction by +0.1 to +0.8 psi (`differences.csv`).

## Sensitivity

The whole annulus temperature profile of case C in the deepest window was shifted. The change in ECD at the bit is:

| Shift, °C | ECD, SG | ECD, ppg | Total, psi | Column, psi | Friction, psi |
|---:|---:|---:|---:|---:|---:|
| -10 | +0.0079 | +0.066 | +25.7 | +15.4 | +10.2 |
| -2 | +0.0015 | +0.013 | +5.0 | +3.2 | +1.8 |
| +2 | -0.0015 | -0.013 | -5.0 | -3.3 | -1.7 |
| +10 | -0.0076 | -0.063 | -24.7 | -17.4 | -7.3 |

Density gives about two thirds of the change through the column. PV gives the rest through the annular friction. With PV fixed, the friction changes by less than 0.3 psi for any shift (`sensitivity.csv`).

## Limits

This is a model calculation, and no downhole pressure measurement is used or compared. The mud is a water-based mud, with an annulus temperature at the bit of 53 to 61 °C in these windows; the formation reaches 199 °C at the deepest bit depth. The rheology is the v1.9.0 assumption: PV scaled with water's viscosity, a constant YP, no yield stress at low shear and no measured high-temperature rheology. The calculation does not show the effect in an oil-based mud or at higher circulating temperatures. Cuttings, pipe rotation, eccentricity, surge and swab are not included.

Run `python -m borethm.studies.ecd_temperature` from the repository root to write the CSV files and the figure in this folder.
