# FORGE 16B downhole sensor extracts

Clifton Barker (2023), *Utah FORGE: Sanvean Technologies Drilling Data
from Well 16B(78)-32*, Geothermal Data Repository submission 1561,
[DOI 10.15121/2205632](https://doi.org/10.15121/2205632). The source is
the GameChanger Viewer 3.3.0.26 time export. The extract selects
channels, resolves repeated timestamps and converts EYE temperature
from °F to °C. Source timestamps are local rig time. The GDR 1516
Pason data supply inlet and return temperature for EOWR run 17.

## Channel and sample definitions

The inputs are taken from the export's Surface group. Use Surface Total Pump
Output when it exists. Surface Flow is the fallback if Total Pump
Output is absent. The Black Box copies are cross-checked on
paired rows; units labelled arbitrary are compared numerically as
stored. Source rows at the same second use the last row in export
order. Missing seconds remain missing. Availability means a finite
numeric reading. The duplicate Custom2 temperature contributes only
an availability flag. EYE, the surface-delivered measurement-while-
drilling temperature, can be absent as a column.

Run numbers in these files are the end-of-well report (EOWR) assembly
numbers. The Sanvean exports use 4–10 for EOWR 11–17. Temperature
channels from runs 11–16 are reserved for later comparison and stored
separately. For these files, the only check of temperatures at this
stage counts readings below −10 °C or above 350 °C, after converting
EYE from °F. Run 17 is development data.

## Event selection

Trip-in starts at the first row of each export and ends at the first
row with bit depth within 5 ft of positive hole depth. A circulation
period is a contiguous span above 100 US gal/min lasting more than
60 s. Each such period separates trip stages. A stage records the
elapsed time and depths, seconds below 50 US gal/min, net depth
change divided by elapsed time, and the duration and mean flow of
its following circulation. A circulation that starts on the first
bottom row can still be the following circulation. A stage that has
no following circulation is retained with empty circulation fields.

A drilling pump-off event starts after the first bottom row and
ends by the last row within 5 ft of hole depth. Flow must stay
below 50 US gal/min for at least 60 s and the immediately preceding
circulation must stay above 100 US gal/min for at least 600 s.
Durations are based on the sampling intervals, with gaps breaking
contiguous flow periods. A duration of at most 10 min is a connection,
over 10 min through 120 min is a stop, and over 120 min is a long stop.
Largest bit movement is the difference between maximum and minimum
bit depth during the pause. Rotation is averaged over the pause.

Report sensor availability separately for each event, including
the first five minutes after pump-on following a pause. Eligibility is
evaluated per sensor: a gap over 10 s, including at the edges of
the observation window, excludes that channel. Recorded Sanvean
data loss above 1% or bit movement above 100 ft excludes the whole
drilling pause. The movement exclusion concerns the pause sample;
trips require movement by definition. Counts retain candidates with
exclusion flags and distinguish them from eligible events. Only
counts are reported for the reserved runs.

The run 17 descriptive comparison reports temperatures from the
bit sensor and the Black Box mean. Steady circulation for this
description is the portion after the first five minutes of a
stage's circulation. EYE update behaviour is assessed from changed
finite readings, and from coverage while flow is above 100 or below
50 US gal/min. No interpolation is applied to downhole temperatures.


## Extract integrity and source cross-checks

The [extract manifest](extracts.csv) gives the source export and input
hashes and the counts of duplicate seconds. The following SHA-256
checksums identify the reserved gzip files. The aggregate range check
counts individual readings after duplicate resolution.

| EOWR run | Rows | Outside range | Sealed SHA-256 |
| ---: | ---: | ---: | --- |
| 11 | 26136 | 0 | `4e678a73e30d53ebcfd09103ab411108ffba0ab8c57148160b5efd6af5c78535` |
| 12 | 120471 | 0 | `86fd55a3b2bcecad38765410505b596531e2a09c98ecd1134a17c04d46e72775` |
| 13 | 91289 | 0 | `055d3005ef8a008a2f3ef9fdafb2c5a494032da9381a7a82e7ac58eb7619d2f4` |
| 14 | 30861 | 0 | `a793535cc83d48ef3261620a0aaba46722585d9a8bbdc1202cd4dc89c4e488f0` |
| 15 | 107860 | 0 | `b5ed83f5d83acddd8bd977eee047519dc94eda35ab0736dd7da2a6df8f6f97af` |
| 16 | 65538 | 0 | `745388013f91a6ebcf1e5d5210239502930561392a4e76cb9534530e1d43ae39` |

The [surface cross-check](surface-channel-comparison.csv) gives paired
counts and numeric differences between the Surface and Black Box copies.
For runs 12 and 13, Surface Total Pump Output agrees with the Black Box
on every paired row and correlates with Pason flow at 0.998 and 0.993.
Surface Flow differs from the Black Box by mean absolute values of
266 and 423 US gal/min, with lower Pason correlations of 0.951 and
0.862. The Total Pump Output channel supplies the event flow in both
runs.
Pason minus Sanvean offsets in [the clock table](clock-alignment.csv)
maximise the mean of the bit-depth and flow correlations on a common
overlap. Run 17 Pason temperatures use the nearest aligned 10-second
record within five seconds. The selected Pason CSV can be rebuilt with
the column selector in [the GDR 1516 build script](../build_extracts.py).

## Sensor positions and trip history

The [geometry table](sanvean_sensor_geometry.csv) gives carrier
dimensions and the supporting drawing pages. The Sanvean deck calls
the bit instrument a "centerline mounted sensor" (p. 8). The GDR
fileset names also say "CNTRLN". The radial position within either
instrument's carrier wall is unknown. The Black Box distance is the
interval occupied by its carrier, with its midpoint used in the
depth-by-depth timing calculation. The EOWR comments distinguish the
22 ft Eye location from the survey and gamma offsets. For run 17 the
84 ft assumption is within the pulser's span in Figure 90. Appendix B
gives a longer motor and pulser, so the geometric offset remains
uncertain. EOWR Figure 60 reports 9.5 in bit gauge and a separate
6.375 in body OD. Run 11's listed filter sub does not establish a float.

The deck and EOWR agree on the seven assembly numbers and their
contractor counterparts. The source labels for runs 12 and 15–16
include different bit serials from the EOWR drawings. The run 14–16
exports select SN2232, while the GDR fileset titles for EOWR 15–16
also name SN5104. These are source differences. The temperature
channels here come from the seven specified viewer exports, and the
geometry comes from the EOWR figures.

The [trip history](trip-history.csv) uses the last recorded bottom
pass before the incoming export and reports incomplete near-surface
coverage. The [static time table](static-time-by-depth.csv) follows
the bit and the Black Box carrier midpoint on the Pason clock in
25 ft depth increments. A depth's clock starts at the last recorded
circulation above 100 US gal/min with the bit at least that deep.
An incoming circulation stage can reset the clock at depths it reaches.
These are rig-history timings and do not measure thermal recovery.

The [run 17 observations](bha-17-development.csv) describe the two
sensors by stage and pause. The [EYE update table](bha-17-eye-updates.csv)
separates availability from changes in the recorded value.
