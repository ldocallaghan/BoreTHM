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

The [replay calculation](run17_connection.py) refines the axial grid
from 46 to 86 cells, the radial grid from 40 to 80 nodes and the
maximum step from 10 to 5 seconds together. The bit peak moves by
about 0.014 °C. The Black Box peak moves by 0.156 °C at the slow
limit and 0.351 °C at the fast limit. The Black Box exceeds the
0.1 K convergence requirement in this pilot. The joint refinement
does not isolate the responsible discretisation. The maximum
single-step energy residual is 0.000043 J. Event forecasts remain
pending.

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
