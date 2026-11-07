# FORGE 16B downhole sensor extracts

Clifton Barker (2023), *Utah FORGE: Sanvean Technologies Drilling Data
from Well 16B(78)-32*, Geothermal Data Repository submission 1561,
[DOI 10.15121/2205632](https://doi.org/10.15121/2205632). The source is
the GameChanger Viewer 3.3.0.26 time export. The extract selects
channels, resolves repeated timestamps and converts EYE temperature
from °F to °C. Source timestamps are local rig time. The GDR 1516
Pason data supply inlet and return temperature for EOWR run 17.

## Channel and sample definitions

The inputs are taken from the export's Surface group. Use Surface Flow
when it exists, or Surface Total Pump Output when the first channel
is unavailable in that file. The Black Box copies are cross-checked on
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
the first five minutes after the end of a pause. Eligibility is
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
