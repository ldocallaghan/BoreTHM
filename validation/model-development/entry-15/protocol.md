# Entry 15 comparison protocol

The development events are FORGE 16A transients and FORGE 16B run 17. The held-out events in 16B are opened only after the development scores and adoption decision are committed. Temperature targets for 56-32, 58-32 and 78B-32 are reserved for separate validation.

| Measure | Sample | Temperature statistic |
| --- | --- | --- |
| D1 | Eleven 16A run-in legs | Bit-box peak during the leg |
| D2 | Seven 16A legs with a detected restart | Bit-box peak in the first five minutes after pump-on |
| D3 | Each run 17 trip stage, bit and Black Box separately | Stage peak, first-five-minute restart peak and end of following circulation |
| D4 | Eligible run 17 amended pumps-off events, bit and Black Box separately | Rise across the event and first-five-minute restart peak |
| H1 | Eligible Black Box stages on runs 11–16 | As D3 |
| H2 | Eligible bit and Black Box pauses on runs 11–16 | As D4 |
| H3 | Pason EYE TEMP on EOWR staged trips other than run 17, with stages identified using input channels | First reading after pump-on and last reading of the circulation |
| H4 | Zhang et al. (2026), Tables 2 and 3, values already published | Before and after circulation at each stage. Use the instrument named in the daily reports or the MWD if unspecified, and record the assumption. |

For each measure report bias (calculated minus measured), RMSE for the primary configuration in K, fraction of measured values inside the band, and skill as 1 minus the ratio of the new RMSE to the v1.8.0 RMSE. Use identical samples in each paired comparison. Report the v1.8.0 frozen-column calculation, persistence and the undisturbed formation temperature for every measure. The published run 17 RMSEs for stages 1 and 3 were 2.4 and 2.9 °C at the bit and 4.1 and 4.7 °C for the BHA sensor. The comparison was in-sample and the sensor positions were assumed.

The [event index](event-index.csv) records the D1 through D4 and H1
through H2 event and sensor keys. It is generated from recorded timing
and availability flags. This index contains neither target temperatures
nor predictions.

## Run 17 circulation boundary inputs

The [run 17 boundary ledger](run17-boundaries.csv) identifies the
last contiguous Pason circulation above 100 US gal/min that reached
the final bit depth of each event and had a recorded inlet temperature.
It covers eight trip stages and sixteen connections. The event times
use the archived seven-second shift from Sanvean to Pason. At a partial
ten-second bin, the calculation clips the duration at the event start
and weights the input averages by the observed interval lengths.

The ledger describes the last observed boundary inputs at one depth per
event. The earlier circulation periods and the movement through the
well are needed to initialise the radial rock field. The short windows
on the outgoing trip can contribute to that history without resetting
the entire rock or liquid column.

The [extractor](run17_boundaries.py) reads only time, depths, pump output
and inlet temperature from the 10 Second Data member of GDR 1516's
16B Pason archive. The nested archive SHA-256 is
`858a6eaf56c2cb3cbf45b59f431e59f82fc0ef2502ced244608d4d7b76ac54a2`.

## Run 17 connection replay check

The [pause-02 replay](run17-connection-pilot.csv) uses the Pason
restart flow and inlet temperature for the first five minutes and
carries the fluid, rock and layered tools through the pause and
restart. The pilot holds the geometry at the preceding circulation
depth, lumps earlier exposure into the last circulation and uses a
fixed volumetric heat capacity. It uses the midpoint of the recorded
Black Box axial span and a 0.25 m tool contact length or the cell
length if shorter. The pilot applies recorded flow through the
five-minute window. It has no quasi-steady handover.

The [replay calculation](run17_connection.py), run with `--pilot`,
refines the axial grid from 49 to 89 cells, the radial grid from 40 to
80 nodes and the maximum step from 10 to 5 seconds together, on the
tally-entry depths. The axial grids include faces at the tool contacts.
The bit peak moves by less than 0.001 °C. The Black Box peak moves by
−0.132 °C at the slow limit and −0.012 °C at the fast limit. The joint
refinement does not isolate the discretisation responsible, and the
slow-limit change is above 0.1 K, so convergence is judged axis by axis
with the recorded contacts. The maximum single-step energy residual is
0.0002 J. The first pilot, with the
cell-averaged transport this replay replaced, moved the Black Box peak
by 0.156 and 0.351 °C on 46 and 86 cells. The axis-by-axis refinement is
in [run17-connection-refinement.csv](run17-connection-refinement.csv).
Event forecasts remain pending.

### Parcel transport and recorded carrier lengths

The [parcel refinement runs](run17-parcel-refinement.csv) retain
temperature fronts through descent and restart. Rock and tool heat
exchange adds a uniform temperature increment to the parcels in each
thermal cell. Transport shifts those parcels without resetting them
to cell averages. The carrier faces are fixed across the axial grids.
The recorded bit contact is 1.25 ft (EOWR p. 102, Fig. 90). The Black
Box spans 107.97–113.94 ft above the bit in the geometry archive.

The axial grids have 49, 89 and 169 cells. The radial grids have 40,
80 and 160 nodes. The time-step sequence starts at 10, 5 and 2.5 s.
The fast-limit Black Box difference of 0.115 K between 5 and 2.5 s
required a [finer time sequence](run17-parcel-time-fine.csv) at 2.5,
1.25 and 0.625 s.

| Restart peak | Axial difference, K | Radial difference, K | Time difference, K | Axial order | Radial order | Time order |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bit, slow | <0.00001 | <0.00001 | <0.00001 | unresolved | 1.18 | unresolved |
| Bit, fast | <0.00001 | 0.00002 | 0.00021 | unresolved | 1.93 | unresolved |
| Black Box, slow | 0.00309 | 0.06166 | 0.01423 | unresolved | 1.47 | 1.64 |
| Black Box, fast | 0.00075 | 0.00200 | 0.01915 | unresolved | 4.13 | 1.75 |

Differences are absolute changes over the finest pair on each axis.
Order is log base 2 of the ratio of successive absolute differences
when the signed changes agree. Reversals leave the order unresolved.
All finest-pair differences are below 0.1 K for this connection
pilot. The largest single-step energy residual is 0.00076 J.

Changing from 0.25 m to the recorded carrier length moves the fast
Black Box peak by 0.339 K and the slow peak by 0.026 K. The bit
changes by less than 0.001 K. The pilot uses the recorded lengths.
Full event history, motion and the quasi-steady handover remain to be
verified.

### Input-only held-out stage keys

The [H3 stage index](h3-stage-index.csv) uses Pason time, depth and
flow, the archived trip timings for runs 11–16, and the documented
assembly makeup end for runs 20, 27 and 38. For other runs, a start
requires a rig row within 100 ft of surface and within 10 ft of the
reported incoming hole depth before the first circulation on bottom
inside the assembly's drilled interval. Stages follow the Phase 0
flow rule, including a circulation beginning on the first bottom row.
The [builder](heldout_stages.py) reads no temperature targets.

The index has 72 candidate stages across the configured EOW
assemblies. Run 13 has no qualifying circulation stage, run 18 has
an unresolved trip start, and run 26 has no documented MWD. The
run 3 and run 4 offsets remain bracketed. Run 17 is development
data and is outside H3.

The [H4 case keys](h4-case-index.csv) associate the published 9,255 ft
and 9,863 ft trips with the Pason stage candidates for assemblies 20
and 27. The case keys use an 84 ft MWD proxy pending confirmation
of the instrument that supplied the published values. Stage matching
and the temperature observations remain sealed for the held-out
comparison.

### Run 17 restart throughput

The [run 17 throughput table](run17-flush.csv) uses the recorded
Pason pump output and the string geometry at the end of each
trip stage or connection. The flush volume is the bore volume
plus the annulus volume alongside the lower assembly, including
heavy-weight drill pipe. A zero-flow row resets the restart
counter. The [builder](run17_flush.py) locates the boundary inside
the recorded time bin without rounding to the next pump sample.

Four trip stages reach the handover volume during their following
circulation, 944–998 s after the recorded circulation start. The
other four and all sixteen five-minute connection restart windows
stay in transient circulation. The table identifies the switch
times. The quasi-steady temperature solve at that boundary remains
to be connected to the column history.

### Run 17 stage-03 descent check

The [stage-03 replay](run17-descent-pilot.csv) follows the recorded
Pason depth changes with a 1.25 s step cap. It integrates the occupied
bore and annulus volumes on a fixed depth grid and changes the bore
cell boundaries without averaging away parcel fronts. The two
coupling limits and both float-valve assumptions use the recorded
tool lengths. The [replay builder](run17_descent.py) keeps the deepest
depth reached so far, omitting 1.08 ft of cumulative backtracking
from this pilot.

The pilot uses the lumped earlier circulation at the last boundary
that reached the final depth. It holds the earlier drill string out
of the hole during preconditioning shut-in and uses a fixed water
volumetric heat capacity. It uses the inlet temperature for the
surface fill with a float. The recorded bit gauge equals the open-hole
diameter, so the outside displacement-film equation cannot be applied
to that geometry. The bit uses the static limit during motion.
No event convergence claim follows from the single grid in this
check. The summed absolute energy residual is under 0.024 J in
each configuration. This check covers descent and does not include
the following circulation.

The daily reports for the two H4 trips were checked with temperature
values masked. Daily report 41, pp. 1–2, records installing and
testing the MWD on assembly 20 and describes cooling it during the
staged descent. The MWD proxy is consistent with the report. Daily
report 49, p. 1, lists both an MWD test and a Black Box for assembly
27. The staged readings are unattributed, so that case retains the
84 ft MWD proxy as an assumption. The report also lists a float
sub for assembly 27. The daily reports do not identify the exact
channel exported into the published table.
[FORGE 16B daily reports, GDR 1516](https://gdr.openei.org/submissions/1516)
