# FORGE 56-32 thermal sample and forecast protocol

The formation boundary is transferred from the FORGE 16A 216-day
temperature survey, as in the [pressure comparison](comparison_protocol.md).
Interpolate it by true vertical depth using the 56-32 survey, then hold
the end value beyond the log. The survey is an independent development
input for this forecast. Temperature measurements from 56-32 remain
reserved. A native formation survey or a profile reconstructed from
native temperature measurements requires a separate decision before use.

Centre drilling windows on the half hour and use the half-open interval
from 15 minutes before to 15 minutes after. A 10-second bin must have
valid flow above 300 US gal/min, bit within 5 ft of hole depth and
on-bottom penetration above 1 ft/h. Require at least 15 minutes of such
bins, at least 0.5 ft new-hole depth range and one assembly assignment
for all included bins. The calculation uses the qualified means. MWD
and return availability are recorded separately and do not select the
forecast windows. The raw 1-second samples contribute only valid/null
counts for these two channels, separated by pump state and for each
forecast sample. Target values are not carried into a calculation.

Assign the bottom-hole assembly by the crosswalk's calendar dates and
hole-depth interval. A missing out date for assembly 5 permits dates up
to the day before assembly 6 starts. Assembly 3's derived depth endpoint
is identified in the crosswalk and its original date range is retained.
For a trip, allow hole depth up to 5 ft shallower than the assembly's
reported starting depth, and require a unique assignment at its end.
Any ambiguous identity stays unresolved. Trip legs use the final recorded shallow point before the next return
to bottom. Search within the preceding off-bottom interval, over at
most 24 hours, with hole depth within 20 ft of the final depth. Require
at least 500 ft net descent across the trip. Mark starts deeper than
100 ft as partial trips. Each stage must descend, with upward travel
at most one tenth of its downward travel. Apply the same
[trip and pause flow thresholds](../forge16b/sanvean/README.md) to the
10-second records. A pause is associated with its preceding circulation;
trip stages record both the prior circulation and the one that follows.
Window times are local rig time.

Use the pressure study's nearest-in-section mud selection. Its primary
reference of 48.9 °C for reported plastic viscosity is an assumption.
The 6 March report prints 33 lbm/US gal with 97.6% water. This is
inconsistent with the recorded solids fraction. Its source row remains
in the archive and is excluded from density assignment. The input
temperature is the Pason inlet in the report's Fahrenheit
convention. Pumped exposure at each depth uses the pressure study's
cumulative clock. Use the assembly's documented nozzle area, or the
sum from the stated nozzle count and diameter when area is absent.
Geometry follows the recorded lengths and bore dimensions. For a mud
motor's internal thermal geometry use the bore of the adjacent sub.
Package no-load and tool loss rules are used for named tools. During
circulation the non-negative mean measured motor differential provides
motor heat. The v1.8.0 route applies it at the motor and the v1.7.0
route uses it as face heat, as in the field comparisons. Missing
differential supplies zero heat from this term. A blank
shock-tool bore takes the adjoining collar's bore for thermal and
distributed losses and is flagged. An unmeasured crossover takes the
drill-pipe envelope and is flagged. The ordinary connection envelope
comes from the pressure protocol. Hydrostatic casing geometry uses the
shoes present in the section, with the same nominal IDs as the pressure
study. Predictions report the bit bore temperature and a separate
84 ft above-bit bore proxy. The proxy is an assumption wherever the
MWD position is unavailable. The returned fluid is evaluated at surface.

The thermal forecast uses the release presets of BoreTHM v1.8.0 and
v1.7.0. The analytical comparator is evaluated on the same circulation
inputs. For a drilling pause, use the preceding circulation as the
initial thermal state and the radial wall and lumped tool calculations
as in the tool assessment. The analytical comparator supplies only a
circulating reference because it has no static solution. For a trip
stage, the current and previous preset use their last available
circulation as a fixed column, with formation temperature at uncovered
depths and a two-node tool. An initial tool temperature at a subsequent
stage uses the preceding circulation result at its sensor position.
At the surface use the transferred formation surface temperature.
The undisturbed formation comparator is also recorded at run-in sensor
depth. Persistence requires a target reading and becomes available only
after unsealing. Each missing input or unsuccessful calculation has an
explicit reason.

## MWD availability audit, 7 November 2026

The [availability interval](mwd-availability-intervals.csv) covers
16:10:06 through 17:24:58 on 23 February 2021, local rig time.
Bit depth spans 7,185 to 7,667 ft and hole depth spans 7,666 to 7,667 ft.
The pump rate spans 0 to 581 US gal/min. Of 4,493 seconds, 2,339 are
pumping and 2,026 meet the raw depth and flow screens before the
penetration-rate and assembly checks.

The 23 February daily report, p. 1, records the mud hammer assembly in
hole for this interval and the start of its withdrawal at 17:00.
It precedes the dated entry for BHA 10 in the [assembly crosswalk](bha_crosswalk.csv).
The conventional assembly assignment required by the Phase 0 protocol is
unavailable here. The interval cannot form a separate measure under those
rules. The [availability builder](mwd_availability.py) uses the finite
flag and the recorded operating inputs.

The 23 February MWD window is excluded because the mud hammer and
subsequent pull-out are outside the conventional assembly model.
The 56-32 thermal test therefore uses return temperature only.
