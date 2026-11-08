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

## Event amendment, 7 November 2026

For Phase 1, a drilling pause follows at least 600 s of circulation above
100 US gal/min. That circulation may end up to 120 s before the pause.
The next circulation must start within 120 s after the pause. The recorded
ramp may separate the two flow thresholds. Missing records do not count
as a ramp.

The per-record Sanvean loss values are averaged over the observed event and
the first five minutes of the following circulation. A mean above 1%
excludes the Sanvean temperature and its duplicate. The Black Box and MWD
retain their own coverage checks. The amendment uses input and availability
columns. See the [amended counts](events-2026-11-07/event-counts.csv) and
[builder](amend_events.py). The original archive records the Phase 0 rule.

## Depth reference correction, 7 November 2026

The [dated correction table](depth-reference-corrections.csv) applies
constant offsets to the derived bit depths of three incoming trips.
The source archives retain their original readings. The screen looks
for a drop greater than 50 ft within 30 s, with flow below 50 US gal/min
and hook load at or below the recorded Pason slips threshold throughout.
Overlapping windows are counted once. The [audit builder](depth_reference_audit.py)
screens the archived run 11–17 trip bounds and the H3 candidate trips
using operating channels only.

| Assembly | Pason reset | Sanvean reset | Subtract before reset, ft | Pason hook load across reset, klbs | Pason block height across reset, ft | Pason bit and hole at arrival, ft |
| --- | --- | --- | ---: | --- | --- | --- |
| 13 | 15 May 17:59:10 | 15 May 17:58:53 | 472.90 | 38.9 to 38.9 | −146.56 to −146.56 | 5,960.26 and 5,960.26 |
| 17 | 21 May 06:19:20 | 21 May 06:19:10 | 488.28 | 33.7 to 36.5 | −251.77 to −250.57 | 7,579.20 and 7,583.98 |
| 20 | 26 May 20:42:50 | unavailable | 193.40 | 41.0 to 41.0 | −757.20 to −757.20 | 9,251.43 and 9,255.40 |

Pason flow is zero across all three resets and its slips threshold
is 52 klbs. Run 17's one-second Sanvean input shows a flat block
height of −251.77 ft and 33.7 klbs hook load at the reset. This
compares with approximately 140 klbs when the string hangs. The
recorded depth afterwards follows the descent to the hole bottom.
The correction applies to the incoming trip before the reset in
each clock. Stage selection uses the archived timing and the depth
at each selected pump-on uses the corrected input.

The [independent stand check](run17-stand-check.csv) counts complete
positive block-height returns of 50–120 ft in the slips. The mean
loaded downward travel is 89.01 ft over 61 complete loaded cycles in
the one-second Sanvean input. The check anchors to the last bit
reading of 7,578.47 ft. Sanvean's first finite bit and block row
at 05:58:10 has 61 subsequent complete slip cycles and an implied
start of 2,149.11 ft, compared with 2,291.29 ft recorded and
1,803.01 ft corrected. Adding four earlier complete Pason cycles
gives 65 stands and an implied Pason start of 1,793.09 ft. The
first Pason value is 1,792.80 ft recorded and 1,304.52 ft corrected.
The stand count does not corroborate the subtraction. It counts
complete visible cycles only and provides no independent basis for
recovering the roughly 5.5 additional stand lengths implied by the
corrected Pason start. The correction follows the local reset
evidence and the subsequent match at bottom.

The [Pason screen](depth-reference-screen.csv) reports the three
candidates and the other trips checked. The [one-second Sanvean
screen](depth-reference-screen-sanvean.csv) independently identifies
the run 13 and run 17 candidates and finds none on runs 11, 12 or
14–16. It uses Pason's recorded slips threshold at the aligned time.
Run 20 is outside the Sanvean exports.

Daily report 41 records the MWD test at about 4,978 ft on run 20,
close to the uncorrected early Pason depth. The corrected first
three H3 pump-on depths are 4,785.49 ft. The report does not give
an independent depth reference for those early readings. The
correction follows the stationary-block reset and the later
bottom agreement. [GDR 1516 daily reports](https://gdr.openei.org/submissions/1516)

## Depth rebuild from rig motion, 7 November 2026

This section supersedes the depth reference correction above. The
constant subtractions in `depth-reference-corrections.csv` are kept so
the earlier archive can be rebuilt, and no replay input uses them.
[`depth_rebuild.py`](depth_rebuild.py) writes the outputs in
[`depth-rebuild-2026-11-07/`](depth-rebuild-2026-11-07/), and
`depth_reference.rebuilt_depth` applies them. The script reads only
bit depth, hole depth, block height, hook load and the Pason hookload
threshold. It reads no temperature channel.

**Method.** The rig bit-depth channel contains tally resets: steps in
the recorded depth with no matching string motion. The rebuilt depth is
the recorded depth plus a piecewise-constant offset. Drilling samples
anchor the offset. A drilling sample advances the hole depth by more
than 0.1 ft with the bit within 5 ft of the hole depth, and its offset
is hole depth minus bit depth. Between two anchors the offset follows
the recorded increments with the resets removed. The trip out takes its
offset forward from the earlier anchor and the trip in takes its offset
backward from the later anchor, split at the shallowest recorded depth.
A gap in which the bit never rises 500 ft above the hole depth is a
connection or stop and keeps the recorded depth. After the last anchor
only the trip out is rebuilt.

**Reset rules.** A reset is a bit step larger than 20 ft that also
satisfies one of these conditions:

- one-second sampling: the step exceeds the block travel bound of
  20 ft/s, or the block is still (within 5 ft) and the hook stays on
  the same side of the slips threshold;
- ten-second sampling: the step is faster than 12 ft/s downward or
  6 ft/s upward;
- either sampling: the string is in the slips and the block is still.

A step that moves the hole depth by more than half the bit step
re-references both channels and is left to the anchors. The slips
threshold is the Pason Hookload Threshold, 52 klbs from 26 April 2023
12:46. At one second, the block travel during a reset step is removed
from the reset size while the string hangs. At ten seconds the whole
step is taken as the reset, because the Pason block channel does not
resolve strokes. Block encoder resets faster than 20 ft/s are skipped
in the block-travel check.

**Pason and Sanvean.** The Sanvean one-second offsets are rebuilt per
run (11 to 17). Over each Sanvean trip the Pason offset is taken from
the one-second sample within 15 s of the clock-aligned time whose
recorded depth matches. The Pason rebuild then propagates from those
fixed samples and its own anchors.

**Checks.**

| Check | Result |
|---|---|
| Block-travel rebuild against the rebuilt depth, runs 11 to 17 ([sanvean-block-check.csv](depth-rebuild-2026-11-07/sanvean-block-check.csv)) | maximum difference 2.2 to 29.0 ft per trip |
| Run 17 start | rebuilt 2,094.13 ft, block travel 2,123.10 ft, recorded 2,291.29 ft; the stand count gives 2,149.11 ft |
| Pason-only rebuild against the one-second rebuild ([pason-only-check.csv](depth-rebuild-2026-11-07/pason-only-check.csv)) | p95 0 to 0.2 ft on runs 11, 12, 14 and 16; 0 ft on run 13; 149.1 ft on run 15; 75.7 ft on run 17 |
| Synthetic records (`tests/test_depth_rebuild.py`) | resets in slips and while hanging, coarse sampling, trip out, connections, the trip after the last anchor and a reset undone at bottom |

The block check differs by up to 29 ft on run 17 over a 4.8 h trip
with six resets. The block rebuild counts travel while the hook is
above the threshold at either end of a step. Counting only steps with
the hook above the threshold at both ends gives 11.9 ft on run 17 and
up to 22.2 ft on the other runs.

The Pason-only errors on runs 15 and 17 come from resets under 150 ft
taken while the string hung. Ten-second sampling cannot separate these
from string motion. Where only Pason data exist (assemblies 3, 4, 19,
20, 27 and 38 in the entry 15 stage index), the rebuilt depth carries
this uncertainty, up to about 150 ft. On run 19 a single ten-second
sample reads 495 ft shallow at bottom on 25 May 02:21:50 and the next
returns to bottom as drilling resumes. The pair cancels to within the
7.5 ft the string moved in the restoring step.

**Scope.** The offsets were checked through the drilling assemblies
used in entry 15, to 17 June 2023. Pason segments after the last
anchor on 8 July 2023, and the casing and completion strings run in
late June and July, are unchecked and are not replay inputs.

**Effect on entry 15.** [`rebuild_events.py`](rebuild_events.py)
rebuilds the amended event archive in `events-2026-11-07-depth/` with
the same rules and the rebuilt depths. Event counts and eligibility
are unchanged from the 7 November amendment. Pump-on depths in the H3
stage index change on assemblies 12, 15, 16, 19, 20 and 27. The
largest change is on assembly 19, where two mid-trip tally corrections
(+286.39 ft at 24 May 21:19:50 and +201.01 ft at 25 May 00:14:30) move
the early stages 495 ft deeper than recorded.

## Bit-depth steps, 8 November 2026

Most steps in the rig bit-depth channel are depths the driller typed in
from the pipe tally. A typed value replaces the integrated depth in one
step with the block still, and it lands on a whole foot, a tenth of a
foot or the hole depth. [`depth_steps.py`](depth_steps.py) classifies
every candidate step in the Pason and one-second Sanvean records and
writes [`depth-steps-2026-11-08/steps.csv`](depth-steps-2026-11-08/steps.csv).
It reads time, bit depth, hole depth, block height, hook load and the
slips threshold only.

The thresholds were set from the rig channels only. The classes are
tested in this order.

| Rule | Value |
|---|---|
| Candidate | a step `depth_rebuild.tally_resets` flags, or any step over 20 ft spanning more than 10 s |
| Merge | consecutive candidates of the same sign form one event |
| Gap | a constituent step spans more than 10 s |
| Encoder reset | the block moves faster than 20 ft/s |
| Zero reset | lands on 0 ft |
| Glitch and restore | an opposite event within 180 s cancels it to within 20 ft plus the string motion between them |
| Typed entry | lands on a whole foot or the hole depth, with under 5 ft of block travel |
| Typed entry, tenth | lands on a tenth of a foot, with under 5 ft of block travel, and holds flat for the next sample |
| Pick-up entry | the hook goes from the slips to hanging within the event, with under 5 ft of block travel; the value is uncertain by that travel |
| Motion | coarser than 2 s, hanging at both ends, more than 5 ft of block travel in the direction of the bit step; not a step |
| Unresolved entry | any other candidate; an entry of unknown value |
| Clock match | a Pason event inside a Sanvean trip takes the Sanvean class and value when exactly one Sanvean event lies within 15 s of the aligned time |

| Record | Events | Typed | Typed, tenth | Pick-up | Zero reset | Glitch and restore | Motion | Unresolved |
|---|---|---|---|---|---|---|---|---|
| Sanvean, runs 11 to 17 | 19 | 19 | 0 | 0 | 0 | 0 | 0 | 0 |
| Pason, whole record | 96 | 58 | 5 | 3 | 9 | 2 | 6 | 13 |

Every Pason event inside a Sanvean trip matches one Sanvean event. No
event spans a data gap or an encoder reset. The glitch is the 25 May
02:21:50 excursion to 8,085.60 ft on run 19, restored at 02:23:00. The six
motion events are pulls on 16 and 17 June just over the 6 ft/s ascent
limit. Seven typed entries on runs 12 and 13 set the hole depth with the
bit (14 May 21:10, 15 May 18:45, 20:12, 20:43 and 23:28 on the clocks
where each appears).
