# FORGE records and thermal coverage

The 16A and 16B comparisons in this folder use development measurements.
The 56-32 conditions and coverage use measured inputs and target
availability. The [thermal forecast](../../forge56-32/thermal_protocol.md)
defines the 56-32 sample set.

## 16A records

The [run-in attribution table](16a-run-in-attribution.csv) uses the
eleven partial run-in legs selected in the original 16A transient
study. All eleven scored the bit-box channel. The position of the
bit-box sensing element is unresolved. The separate PUK carrier spans
describe the assembly dimensions. The source has surface flow and
standpipe pressure merged onto the Sanvean clock. It has no independent
downhole pressure or flow channel for these legs. Pump-on is the first
valid flow bin above 100 US gal/min within 15 minutes of the leg.
The table separates each selected leg's maximum from the maximum in
the first five minutes after pump-on. Blank dwell indicates the record
does not establish a bottom dwell before restart.

[Pressure alignment](16a-pressure-clock.csv) compares Sanvean's merged
surface pressure with the GDR 1283 rig pressure in minute bins. The
rig timestamps are only available to the minute. The Sanvean runs
start on 14 November, after the 1 November clock change, so the earlier
offset cannot be estimated. The pressure match checks the two recorded
surface clocks. It does not establish independent tool timing.

The [static time table](16a-static-time-by-depth.csv) uses the latest
circulating bin with bit depth at or below each evaluated depth. It
checks the depths every 25 ft. Pason times are minute estimates and
Sanvean times have 10-second resolution. A temperature spike is a
single-bin reversal with adjacent differences above 10 K. The table
also records the longest repeated temperature and flags any reading
above the 16A undisturbed formation profile. The separate raw check
counts flow above 100,000 US gal/min and finds the instantaneous peak
in each selected leg from the original exports. A missing float
entry in the assembly tables leaves float use unresolved.

The [bit and top-sub steps](16a-bit-and-top-sub-steps.csv) pair the last
six valid bins in one drilling state and the first six in the other.
The switch can have up to 120 seconds of unclassified rows and the
combined range of flow must be at most 25 US gal/min. The two channels
can respond differently to rotation and bit contact even at similar
flow. The [residual table](16a-sensor-residuals.csv) uses the bit bore
and the bore 40 ft above the bit as proxies, respectively. Earlier
assemblies without a frozen comparison or with unknown geometry have
empty residuals.

**Measured records.** The 18 and 19 December daily reports (GDR 1283,
p. 1) list 279.30 ft of 5 in heavy-weight drill pipe with a 3 in bore
on BHA 42. The same tables list two further sections as drill pipe,
2,185.39 and 1,226.43 ft, both with a printed 3.25 in bore. The drilling
summary describes heavy-weight push pipe in the vertical and curve
sections without a tally specific to that function. The extra
3,411.82 ft cannot be classified from these sources alone. The
summary names the Vibe Scout agitator on BHAs 41 and 42 (pp. 58–60,
Tables 23–24). The daily tables do not assign it a separate
geometry or pressure-loss curve. No pipe inspection class was found
in the reviewed assembly tables or summary. The inlet boundary is
the depth-indexed TEMPIN channel from the 16A mud log. Daily-report
PV and YP lack a measurement temperature. The reference stays at
26.7 °C, with 48.9 °C as the declared sensitivity.
[FORGE 16A drilling summary](https://gdr.openei.org/submissions/1296)

## 16B formation boundary

**Calculated.** The [paired sample table](formation-and-sensor-samples.csv)
uses the packaged 16B formation profile in one calculation and the
full 16A 216-day measured profile evaluated by the 16B survey's true
vertical depth in the other. The endpoint is constant. The package
profile is also a transfer from the 16A survey. The difference here is
the source tabulation and interpolation. Both use the v1.8.0 preset,
the frozen inputs, and the working installed geometry and tool
assignments. The resulting changes are model-only.

## 56-32 analogue ranges

**Calculated.** The [conditions table](56-32-condition-coverage.csv)
compares the distribution of inputs with those of the 16A and 16B
development samples. The development circulation and preceding-pause
ages use the minute input records. A missing minute at the comparison
time leaves the two ages unreported. The [assembly mix](development-assembly-mix.csv)
separates development rows by motor and insulated-pipe use.
Static timings for the development records are in the
[16A timing table](16a-static-time-by-depth.csv) and
[16B timing table](../../forge16b/sanvean/static-time-by-depth.csv).

**Inferred.** For each 56-32 drilling sample, the
[analogue table](56-32-conditional-residual-ranges.csv) uses development
residuals from the same motor status, within 500 m true vertical depth,
100 US gal/min, 10 K inlet temperature and 0.7 lbm/US gal density.
The 10th and 90th percentiles are shown when at least three residuals
exist. These are descriptive ranges from development comparisons.
They do not estimate coverage probabilities. The
[run-in analogue table](56-32-trip-analogues.csv) uses the 16A partial
legs whose end depth is within 500 m measured depth of each stage.
The differences in initial state and trip coverage limit transfer.
