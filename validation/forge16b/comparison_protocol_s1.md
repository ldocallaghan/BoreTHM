# FORGE 16B comparison: S1 calculation protocol

27 October 2026. Baseline `85f23db51f6661e6ca09bd05c16b9ffb48881d83`. The [S0 protocol](comparison_protocol.md), its source extracts and its 109 candidate samples remain unchanged. The following input decisions were made before whole-well predictions or errors were calculated. The separate water reproduction check uses the existing trial samples and saved parameters.

## Trial reproduction comes first

Recalculate the four original trial series on their original half-hour samples, using the original water properties, exposure clock and aggregate geometry. Reuse the saved film coefficient and insulated-pipe conductivity for each of the two saved chains. Invoke no fitting entry point. Compare their means with the existing golden values using the existing 1 °F regression tolerance, also publishing unrounded differences and solver status. All 146 solves must converge before whole-well calculations begin.

These checks preserve two distinct saved conductivities: 4.9237482416889895 W/(m K) in the fitted chain and 4.7025289484090305 W/(m K) in its unfitted-film chain. The whole-well comparison uses the S0-declared single fixed conductivity, 4.9237482416889895 W/(m K), for both film coefficients. Consequently, its film-1.0 insulated-pipe cases are not numerically the saved unfitted chain. No conductivity is refitted.

## Sensor positions and geometry

For EOW 3, report bore temperature at 22, 69 and 84 ft above the bit, labelled unresolved. For EOW 4, report 22 and 84 ft, also unresolved. EOW 27 and 38 use 84 ft as an assumption, with a 22-ft sensitivity. Retain 22 ft for EOW 11–16 and 84 ft for the four trial runs. Publish the full spread over the requested positions, with each branch's error retained. No position is selected by its temperature error. The sensor medium remains the existing trial's bore-fluid interpretation; annulus values are retained alongside it.

The newly inspected EOW p160 drawing for EOW 38 says `Eye = 85` and gives a survey offset of 85 ft. Retain the instructed 84-ft assumption and 22-ft sensitivity; save 85-ft interpolation as a source-position diagnostic. This does not change the solve or choose a position from the errors.

Keep `validate_forge16b.geometry` unchanged for EOW 17–20. EOW 17's motor is 35 ft in Figure 90 and 41.87 ft in Appendix B; this source discrepancy remains explicit. Other assemblies use their own lengths and dimensions in `component_inputs_s1.csv`. EOW 4 borrows matching dimensions from EOW 3; EOW 27 borrows matching component dimensions from the EOW 38 drawing. Both substitutions are flagged by component. Non-HWDP components, including collars and crossovers, use length-weighted body OD and bore ID in one compact assembly, following the existing 16A study. Heavy-weight drill pipe remains a distinct segment. The trial runs retain their existing separate-collar aggregate geometry. Ordinary pipe fills the remaining length, at 5.5-inch OD and 4.670-inch ID. No component length is adjusted to improve agreement.

For EOW 3 and 4, represent the 16-inch surface casing to 1,136 ft, with its existing assumed 15-inch ID and cement to 22-inch borehole; below it, the hole is 14.75 inches. The later 11.75-inch casing is absent. Deeper runs retain the existing 16B casing geometry. No model function is altered.

## Recorded mud and missing rheology

Use the same Mud construction and unit conversions as the 16A study: density in lb/US gal times 119.8264273 gives kg/m³ at 20 °C; PV in cP times 0.001 gives Pa s; YP in lbf/100 ft² times 0.4788025898 gives Pa. Actual density measurement temperature is unreported.

Use source sample timestamps, not report dates, to associate mud observations. A run's input is the arithmetic mean of mud samples within its drilling interval, as defined by the S0 drilling criteria and depth bounds. If that interval contains no mud sample, use the latest earlier sample in the same fluid system, flagged. Fill each missing PV or YP in an associated mud row from the nearest strictly earlier measurement in the same system, flagged. If none exists, use the existing reference PV of 27 cP or reference YP of 28 lbf/100 ft², flagged. Average only after this completion step. Publish every source row, donor and default. No missing value becomes zero. A density outside the existing Mud constructor's domain is an input failure and must be reported; do not clip it.

Keep separate fluid histories before intermediate casing cementing at 3 May 21:50, between that event and the mud-pit drain/clean on 12 May, and after the drain/clean completed at approximately 15:30 on 12 May (EOW pp218, 236). These conservative boundaries prevent carry-forward across the documented displacement/clean-out operations even where the reports repeat the same generic low-solids mud label. The 12 May 15:00 sample overlaps the cleaning operation and is not carried into the later system. Do not borrow a later measurement to fill an earlier missing one. The two mud rows split across PDF pages 236/237 and 239/240, missed by the S0 table extractor, are separately transcribed in `mud_supplement_s1.csv`; the S0 extract is preserved.

Run water-property sensitivity cases for every sample. Water uses the existing 16B treatment (`fluid=None`) with the same measured flow and inlet. Each fluid's mass rate uses its own calculated inlet density. The mud/water change therefore retains volumetric flow, as the existing evaluators do.

End each mud-association drilling interval once the running maximum of hole depth exceeds its run's depth-out by more than 0.5 ft. Later depth-channel resets and re-entry at the same depth do not extend a drilling run. This input check precedes whole-well predictions.

## Motor load and clocks

For documented motor assemblies, face heat is `max(0, reported differential pressure) × volumetric flow`. For documented motorless assemblies, motor-face heat is zero. Retain raw negative and positive differential values. Publish the motorless channel's distribution and per-run means as a diagnostic; apply no inferred zero correction.

Use the saved ten-minute history's observed circulating count times ten seconds to reconstruct cumulative circulation. Missing flow contributes no observed circulation and remains counted as missing. Report incomplete bins and time gaps. Keep maximum drilled depth monotonic, with missing depth forward-filled, following the existing study treatment. The history uses the existing left-edge timestamp convention; a partial bin contributes only its recorded circulating rows. No missing interval is classified as a known stop.

The optimistic recovery diagnostic caps each depth's original exposure at observed circulation since the end of the last continuously observed pumps-off interval longer than two hours. Apply the existing one-hour floor and smoothing after that cap, exactly as in the 16A diagnostic. This is a full-recovery bound, not a transient wall-reheating calculation.

For each of the 109 samples, calculate both fluid choices, film multipliers 1.0 and 0.75, and cumulative/full-recovery clocks: 872 planned solves. Positions are interpolated from each solution and do not require extra solves. Preserve every exception and solver failure. Report primary recorded-mud, film-1.0 cumulative results first, followed by sensitivities and the recovery bound. Publish errors in °C and °F by run and predeclared 500-ft MD bin. Pooled metrics distinguish independent regular-pipe periods, trial film-fit periods and fitted-IDP periods; unresolved early positions are reported separately. Do not pool multiple position branches as extra independent observations.

Freeze the plan, source hashes and calculation hashes before the first whole-well solve. Checkpoint each result. S1 ends with the result tables, comparison figure and failure report. Pressure/energy comparisons with 16A remain S2 work.

## Pre-comparison construction correction

The first attempted early-hole solve used a standalone 2.91-ft crossover between the collars and heavy-weight pipe. Its two geometry changes were less than the existing 1-m blending width apart, and the solve emitted convergence warnings without completing a result. That study construction has been replaced by the existing 16A aggregation of non-HWDP components. All component dimensions and lengths are unchanged. The attempted plan, script and log are retained in the private execution evidence. No whole-well temperature result or error had been produced before this correction. The original 109 samples remain unchanged.
