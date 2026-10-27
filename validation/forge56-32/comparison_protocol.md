# FORGE 56-32 pressure comparison protocol

The [sampling and motor-loss amendment](protocol-amendment.md) governs the current comparison. It replaces the off-bottom sampling and motor treatment below, and adds the registered geometry and timing treatments. The original protocol is retained here to document what was registered at `a1927b3`.

Protocol registered before any 56-32 model prediction or pressure residual. Baseline: `f61a5d918285948c7254f1458c83992cdfb935cb`. This protocol and its input preparation were committed before pressure comparison. Any source clarification or protocol amendment must have a new commit before target pressure is read. Earlier access to one report's observed pressure summary is disclosed below.

## Question and comparisons

Does the revised hydraulic calculation improve standpipe-pressure accounting on a well that has not previously been compared with BoreTHM? Primary observations are stationary off-bottom circulation at steady flow. Secondary observations are on-bottom drilling, with reported differential subtracted from measured standpipe pressure and the limitations of that adjustment stated.

Compare v1.5.0 and v1.6.0 on the same input windows. Primary revised rheology uses the explicit 48.9 C assumption where field PV is supplied, with 26.7 C as a sensitivity. Retain a v1.5.0/26.7 C baseline, v1.5.0/48.9 C input-only variant and v1.6.0/48.9 C variant. This separates the input convention from hydraulic changes. Do not adjust any coefficient using the observations.

## Sources and exposure

Use the four full-channel weekly files in `1295.zip!56-32_Pason_Archive.zip`, the well's own survey, BHA sheets, bit workbook, manufacturer sheets and daily reports. [Extract README](README.md) identifies the archive, attribution and rebuild commands. Standard/10-second exports without standpipe pressure are not pressure sources.

Before this protocol, file headers and some first rows had been inspected. During earlier inventory work the BHA 5 sheet, including its observed pressure summary, was viewed. Current extraction emits only finite/missing counts for target channels. No pressure residual or model prediction has been calculated. This is a comparison unseen by the model development process; describe the actual prior exposure when publishing it.

78B-32 is excluded from this release's work. Existing development data are 16A and 16B, including motorless S2b. The 58-32 daily reports do provide BHA records, satisfying the second-well input requirements. It follows the same input-preparation and protocol-commit sequence before pressure comparison. This file defines the 56-32 method.

## Input-only window method

`prepare_pressure.py` supplies the reproducible candidate list. It reads input extracts only. The selection uses flow, bit/hole depth and the source On Bottom ROP channel. Weight on bit, pressure, differential and temperature targets do not select windows.

Use non-overlapping ten-minute intervals ending on source-clock minute 00, 10, 20, 30, 40 and 50. At least 54 of the 60 ten-second bins must have finite flow and bit/hole depth. No gap between available bins may exceed 60 seconds. Every available flow minimum in the interval must exceed 100 US gpm. Flow's 90th-minus-10th percentile divided by its median must be at most 0.10. The quantiles use sorted ten-second bin means at indices floor(0.1(N-1)) and floor(0.9(N-1)); each bin has equal nominal ten-second weight. This defines operational flow steadiness, not thermal equilibrium. No additional thermal warm-up cut is imposed.

Primary intervals require at least 90% of available bins to have hole minimum minus bit maximum at least 50 ft. Bit depth must span at most 5 ft across the interval and remain at least 100 ft. These rules exclude movement and bottom contact. Secondary intervals require at least 90% of bins within 5 ft of bottom, flow above 300 gpm and On Bottom ROP above 1 ft/h. Record that this is a depth/penetration proxy; no documented binary on-bottom flag is available in the selected raw columns.

The candidate centre is five minutes before interval end. Record every window ID and input mean. Source-null values are missing; finite zero stays a reading. Flow outside 0 to 2,000 gpm is flagged unavailable input, following the existing 16A gross-error convention. No pressure threshold selects a window. The preparation period ends before 28 February 2021, after the last supplied drilling BHA date-out, to keep later completion operations separate.

## BHA, casing and fluid inputs

Use the bit workbook and separate BHA sheets as distinct numbering systems. A provisional crosswalk requires bit depth-in within 10 ft and depth-out within 2 ft of the BHA sheet. This allows the explicitly recorded drill-out difference; every discrepancy remains in the source ledger. Where the depth-out cell contains a date, retain it as unresolved and record depth-in plus stated footage as a derived candidate. Do not silently replace the printed source.

Calendar dates are not exact trip boundaries. A candidate currently receives a BHA only if its date and hole depth identify a unique sheet. Endpoints and same-day overlaps remain unresolved. Before scoring, reconcile these with input-only daily operating events and record the mapping in a committed amendment. Exclude mixed/uncertain assembly intervals from the complete-input score, but publish their input-based exclusion counts. A missing motor entry in the workbook cannot establish a motorless assembly.

Represent components in series using their reported length, body OD and passage ID. Keep stabiliser/gauge OD separate. A blank motor/shock passage remains missing; a connection size or nominal motor OD is not its bore. A supplied whole-tool curve replaces the internal passage losses it already includes. Missing dimensions and the unknown fluid path around probes are not fitted from pressure. Cases without a declared geometry treatment cannot be presented as complete predictions.

Use casing present at the time, using the daily casing table's reported dates and shoes. Source records report 20-in conductor, 13.375-in surface casing at about 382 ft and 9.625-in intermediate casing at about 3,494 ft. Preserve source discrepancies with nominal hole-section depths. Missing casing IDs/wall thickness and rounded weights need an explicitly sourced or assumed treatment, committed before scoring. Do not borrow 16A's 68-lb/ft surface casing or 40-lb/ft intermediate casing for this well. The 56-32 records report approximately 55 and 36 lb/ft respectively.

Use recorded mud density. The candidate preparation chooses the nearest dated density and paired non-missing PV/YP within the same nominal hole section; equal time distance selects the earlier sample. Only drilling-period samples before 28 February are eligible. Section boundaries at 382 and 3,506 ft are input proxies, not proof of fluid-system continuity. Record that assumption; an identified fluid-system change overrides it in a committed pre-score amendment. Never transfer across a documented fluid-system change. If no measured PV/YP exists in the section, use water rheology at recorded density and label it. No weighted reference-mud fallback is supplied.

The selected mud tables do not state a rheology measurement temperature. Set `pv_ref_T=48.9` as a declared assumption for supplied field PV; set 26.7 C for the sensitivity. A documented actual test temperature takes precedence and must be incorporated before scoring. Site-file rheology and `fluids.PV_REF_T` remain unchanged. Reported inlet/outlet temperature is not a rheology test temperature.

Use Pason inlet temperature under the report's Fahrenheit convention and flag the ambiguous raw Degrees label. Missing inlet coverage is an input flag. Any fallback or unit correction requires a source-based amendment before target inspection. Use the existing FORGE 216-day formation profile against TVD as a declared transferred boundary, constant past its endpoint; the well's own survey maps MD to TVD. Keep the existing FORGE rock properties, film multiplier 1.0 and cumulative circulation clock. Do not fit a boundary or heat-transfer coefficient to pressure.

## Motor and other loss inputs

[Tool specification facts](tool_specifications.csv) are manufacturer inputs, not observed pressure. GeoGuidance prints off-bottom pressures but no reference flow or density for those values. Most recorded motors do not exactly match the pictured configurations. BICO's 475-psi no-load value specifies clean water at 72 F but has no identified reference flow. The Discovery sheet has no identified no-load reference. These gaps currently prevent a fully specified manufacturer-based primary motor loss.

Before numerical primary scoring, obtain or approve the reference flow/density and configuration mapping, or a separately specified manufacturer-constant treatment. Do not assign a flow-range midpoint as a published reference, treat motor differential rating as no-load loss, transfer a curve solely by outside diameter, or infer any coefficient from measured standpipe pressure. Record input assumptions and provenance before pressure is unsealed.

Use actual bit jets where explicitly recorded on the BHA sheet, keeping its printed TFA and the workbook TFA as cross-checks. If only TFA exists, use that reported area and flag the absent jet schedule. Retain nozzle coefficient 0.95. Identify bit-body annular flow assumptions; gauge OD does not form a sealed cylindrical obstruction.

For documented 5-in 19.5-lb/ft pipe with 4.5 IF connections, use matching catalogue connection scenarios chosen before errors are read. Effective joint length is a declared input, with the S2b 29-in assumption and 0/58-in sensitivities available. Use the recorded tally/spacing if established; any transferred spacing is labelled. API surface case 5 is the main declared layout scenario, with zero and the other published cases reported. Exact high-pressure plumbing and tap position remain unknown. Do not select the smallest residual across scenarios.

Primary off-bottom cases have no rock-cutting face input. Count the declared no-load motor loss once, with its internal heat placement stated. Secondary cases retain the existing study treatment of non-negative reported motor differential as the separate face input. Its zero offset and relationship to total motor loss are uncertain; preserve the raw signed channel. Do not duplicate that input through a whole-tool allowance.

## Measures and missing results

For each window, report observed standpipe pressure, legacy/revised prediction, signed residual (predicted minus measured) in psi and percent of measured. A zero denominator gives a missing percentage and a retained absolute residual. Report median and min/max residual per BHA; include planned, input-complete, converged and target-available counts. Primary and secondary tables remain separate. Secondary target is measured standpipe pressure minus raw reported differential, with both original channels preserved in the later evidence.

Publish the component pressure budget, signed density-column correction, hydraulic/property flags and source completeness. State whether generic surface layouts include pipe upstream of the measurement tap. Unknown proprietary/tool loss means an incomplete budget, even when a subtotal contains zero for it.

There is no fitted acceptance threshold. Do not remove a case because of its target value or error. Preserve convergence failures and missing targets as explicit statuses with the planned window ID. Report any permitted numerical retry unchanged and retain both attempts. Measures added after target inspection are post hoc.

## Input completeness

The committed candidate list is an input-only preparation result, not a certified complete primary score set. Manufacturer reference points, assembly boundaries and missing geometry treatments require sourced treatments. Freeze their amendments before pressure targets are read. The inventory and candidate preparation can be reproduced without accessing pressure values beyond finite/null counts, and without importing BoreTHM.
