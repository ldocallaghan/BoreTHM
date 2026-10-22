# Material properties for the circulation model

| Property | Value | Source |
|---|---|---|
| Steel (drill pipe, casing) | 45 W/m·K | Wu et al. (2025), Tables 3 to 5 |
| Internally coated drill pipe | 1 mm coating, 0.47 W/m·K | Vetsak et al. (2024), as cited by Wu et al. (2025) |
| Externally coated drill pipe | 1 mm coating, 1.31 W/m·K | Vetsak et al. (2024), as cited by Wu et al. (2025) |
| Dual-wall drill pipe | phenolic resin fill, 80 mm bore, 0.092 W/m·K | Xiao et al. (2022), as cited by Wu et al. (2025) |
| TK-Drakōn coated drill pipe | 0.51–0.76 mm internal coating, 0.162 W/m·K | NOV Tuboscope flyer (2024) |
| Vacuum-insulated tubing | about 0.04 W/m·K averaged over body and connection; body as low as 0.001–0.005; industry range 0.02–0.08 | Dufrene et al. (2025) |
| Cement sheath | 1 W/m·K as a central value, sensitivity 0.1–10 | Dufrene et al. (2025), simulation choice |

Dufrene, C., Cambre, E., Sfeir, J., Kozikowski, M., Bois, A.-P. (2025).
"Enhancing Thermal Efficiency in Super-Hot Geothermal Systems: Optimizing
Premium Connections for Advanced Vacuum Insulated Tubulars." *Proceedings, 50th
Workshop on Geothermal Reservoir Engineering*, Stanford, SGP-TR-229. They find
70–80% of a vacuum-insulated string's heat loss is at the connections.

Vacuum-insulated tubing is a production tubular. None of the sources here
describes a drill pipe built that way, so for drilling it is a sensitivity.

## Reference pipe and equipment evidence

The site programmes use internally coated NOV TK-Drakon pipe with the
properties listed below. The published coating properties define this reference configuration.

The dual-wall sensitivity uses the 80 mm bore and phenolic fill at
0.092 W/m·K from Xiao, D. et al. (2022), "Wellbore cooling and heat energy
utilization method for deep shale gas horizontal well drilling", *Applied
Thermal Engineering* 213, 118684, as used by Wu et al. (2025). That modelling
study does not identify a commercial drill-pipe product with those properties.
The source search recorded on 8 October 2026 identified no matching product
or field trial. Sandia and Drill Cool Systems field-tested a prototype
insulated drill pipe around 2000 (Champness and Finger, OSTI 751131).
These records do not qualify the modelled dual-wall geometry for drilling.

The equipment sources describe:

- Eavor's internally and externally coated IDP, run at FORGE 16B in 2023
  (`src/borethm/data/forge16b/`); the fitted effective conductivity matches a 1 mm
  coating at 0.47 W/m·K.
- NOV Tuboscope's TK-Drakōn internal coating, launched November 2024: applied
  20–30 mils (0.51–0.76 mm) thick at 0.162 W/m·K, rated to 204 °C "or all
  temperatures commonly encountered during the drilling process, provided that
  circulation is maintained" (NOV flyer D392006697-MKT-001 Rev 01, 2024; also
  Energy Global, "Keeping fluids cool in the hottest wells", December 2025).
  The model's TK-Drakon pipe type is 0.635 mm, the middle of that range, on
  5-1/2-inch pipe. Its coating resistance is about 1.8 times that of Eavor's 1 mm
  coating at 0.47 W/m·K, and about 1/70 of the dual-wall pipe's.
- Vacuum-insulated production tubing. Its use as drill pipe is a model sensitivity.

Pro-Pipe Service and Sales (Alberta) is developing an insulated drill pipe,
with field trials at 300 °C and a 5,000 m string planned for 2027 (Emissions
Reduction Alberta project page). Its construction and conductivity are not
published, so it is not modelled.

## Hole cleaning

The sources used here do not establish a universal minimum annular velocity.
Finger and Blankenship (2010), *Handbook of Best Practices for Geothermal
Drilling* (SAND2010-6048), calls for "high annular velocity to lift the cuttings"
without a numerical requirement.

The model takes its hole-cleaning reference from practice: the
annular velocity at which a comparable hole was actually drilled and cleaned.
FORGE 16B was drilled through the trial interval, at 60 to 70° inclination in
9-1/2-inch open hole, at 600 to 700 gal/min. The rig's daily reports give the
annular velocity around the 5-1/2-inch drill pipe as 245.1 ft/min at 600 gal/min
(1.245 m/s) and 286.0 ft/min at 700 gal/min (`src/borethm/data/forge16b/rig_hydraulics.csv`).
The reference is the lower, 1.245 m/s. It is a deviated-hole value, so it is
also used for vertical hole, where cuttings settle less readily and it is
conservative. No vertical value from practice is available: Wu et al. (2025)
run 600 gal/min in a 0.22 m hole with 139.7 mm pipe (1.67 m/s), but as a
modelling choice, not a field observation.

## Rig pump capacity

The flow a rig can deliver at a given standpipe pressure is taken from NOV's
technical marketing sheet for the 14-P-220 triplex mud pump, a 2,200 hp pump
rated for 7,500 psi: at the rated 105 strokes/min it delivers 1,980 hydraulic
hp, which is 1,215 gal/min at 2,795 psi on 9-inch liners, 960 gal/min at
3,535 psi on 8-inch, and so on to 454 gal/min at 7,475 psi on 5.5-inch. A
pump's flow at a pressure is therefore about 1,980 x 1,714 / psi gal/min, up
to 1,215. FORGE 16B's rig had at least three mud pumps (its daily reports
mention "No. 3 mud pump"; the Pason record has a third pump channel) and ran
5.5-inch liners; the model takes three pumps of the 14-P-220's rating as a reference rig assumption. The pump models on FORGE's rig
are not given, and these records do not qualify a rig for the deep programmes.

## Bit nozzles

Nozzle pressure drop is ρQ²/(2C_d²A²) with a discharge coefficient
C_d = 0.95. This reproduces the FORGE rig's own figure: 192 psi for eight 14/32-inch nozzles at 600 gal/min and
8.40 lb/gal, against 193 psi in the daily report. Where a bit's nozzles aren't
known, the model uses that FORGE bit's total flow area, 1.203 in² (776 mm²),
as a stated default.
