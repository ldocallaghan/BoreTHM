# Pressure-input consistency diagnosis

## Declaration, 1 November 2026

**Measured data status.** FORGE 58-32 pressure is development data following the [registered comparison](../../forge58-32/pressure-test/README.md). The earlier source exposure and subsequent access record remain part of that comparison. This diagnosis follows `7bf08b1`. FORGE 16A and 16B are also development data. Their existing results remain unchanged. No reserved thermal target or 78B-32 observation is used.

**Inferred purpose.** Identify which recorded pressure input or pressure-channel interpretation could explain the inconsistent pressure accounting. A source record may justify an input for a later entry. No input is adopted here. No package function, registered comparison file or existing development result changes. There is no skill score or fitted acceptance threshold.

## Source inventory and extraction

**Measured source plan.** Search the complete daily reports in GDR 1006, both the separate report archive and the end-of-well daily-report attachment. Search the end-of-well report, the bit summary and dull records, and the supplied mud log. Search public primary rig and pump specifications for the named Kenai Rig 10 equipment. For 16A use GDR 1283 rig exports and daily reports; for 16B use the original Pason archive and daily reports identified by the existing source manifests. Archive-member listings may identify these documents; no source is selected using a pressure residual.

**Calculated provenance.** Each extract records the archive and nested member, its SHA-256, PDF page and extracted line or table-row range, or native CSV row range. Full-page text is searched, including pages with no match; the search inventory records null results. A textual extraction is checked visually where a source table or ambiguous dimension is used. Unrelated thermal channels are excluded from the extracts. Source archives remain external. Missing, encrypted or unreadable sources are recorded as gaps and work continues.

**Measured facts to reproduce.** Check summary reports 9–11 for their printed drilling flow, pressure and depth intervals, including report 10's bit pressure drop and jet velocity. Check the two report-10 slow-circulation records. Check reports 6–9 for the ordinary-pipe and heavy-weight drill-pipe inventory, grades and thread labels; distinguish inventory quantities from the installed BHA. Check report 8's kelly change and rig name. Recompute the registered windows' flow-to-stroke relationship from the saved input projection. Calculate triplex displacement as `3*pi*D^2*L/(4*231)` US gal per stroke for dimensions in inches; the equivalent `D^2*L` and illustrative liner/stroke combinations do not identify installed equipment.

## Common reduction rules

**Calculated method.** Retain native source clocks and finite zero and negative pressure values. Treat non-finite values and the source null `-999.25` as missing. Missing strokes are not zero. Valid pump combinations require non-negative finite stroke rates and a positive sum. Ratio checks retain every finite flow value, with nonphysical signs flagged. Report unavailable cases and native coverage separately. No pressure-based clipping, alignment, offset subtraction or sample exclusion is applied.

**Calculated time treatment.** For native one-second 58-32 observations, gaps above two seconds restart a continuous period. Duplicate timestamps retain their native row identities. A day is the half-open source-calendar interval from midnight to midnight. Events retain the existing identifiers and extend from their first registered window start to their last end. No new event is selected. Time-zone and report-clock alignment remain unverified.

## A. Pressure channel

**Calculated A1, zero offset.** Identify contiguous periods with both pumps exactly zero. Discard their first 60 seconds, then require at least 60 seconds of remaining observations. Report the median finite pressure, native counts and retained duration for each period. Summarise the retained observations within each event interval expanded by two hours on each side, and separately for each day 3–6 August. Clip to the requested scope after settling; a clipped portion must still span at least 60 seconds. Record scopes with no qualifying period.

**Inferred A1 outcomes.** A nonzero retained reading indicates a pressure-channel offset or another source of recorded pressure during pump-off conditions. It does not establish a correction. Values close to zero weaken a constant-offset explanation but cannot establish transducer location or dynamic calibration.

**Calculated A2, report agreement.** Transcribe each drilling-parameter interval and its reported pressure. Use an explicitly printed reporting time interval where available. If only a date is available, use that source-calendar day and flag its uncertain relationship to the reporting period. Also require bit depth within the printed drilling interval, bit within 5 ft of hole depth, penetration above 1 ft/h and positive summed pump strokes. Report median pressure and flow on those native observations, counts, depth coverage and the report difference. If a required depth or penetration channel is absent, report the primary selection unavailable; any substitute is labelled as a post-declaration change. Never infer a time shift from pressure agreement.

**Calculated A3, slow circulation.** On 5 August, retain each contiguous period with pump 1 at 50–53 strokes/min inclusive and pump 2 zero. Keep brief periods visible. Give duration, native count and median pressure, flow and stroke rate for each period and separately for each recorded stroke-rate value. Compare with the reported 51 and 52 strokes/min records. A source-time mismatch or absence of a matching period is reported explicitly.

**Inferred A2/A3 outcomes.** Agreement would support consistency with the rig's own reported pressure. Disagreement would leave timing, calibration and channel identity as alternatives. Agreement does not establish that either source is the standpipe pressure calculated by the model.

## B. Flow derivation

**Calculated B1.** Across the complete 58-32 Pason record, compute `Flow In/(pump1_spm+pump2_spm)` on eligible native rows. Summarise count, median and range by day and pump combination: pump 1 alone, pump 2 alone or both. Preserve every exact ratio change and its time and native row in a compressed extract. Separately report changes of ratio rounded to 0.01 US gal per stroke, including one-row changes, so last-digit rounding is distinguishable from a different configured displacement. Gaps and combination changes start new segments. The 0.01 resolution is fixed here and is not selected from pressure. No pressure channel enters B1.

**Calculated B2/B3.** Compare ratio-change times with every recorded liner, pump or configuration change. Search all pages of the source inventory for pump make and model, stroke length, liner diameter, displacement and efficiency. Record each search and its result. A similarly named pump or rig is not identification of the installed equipment. Manufacturer specifications apply only if a primary record identifies that equipment. Unresolved sources become enquiries.

**Calculated B4.** Where independently recorded liner and stroke dimensions exist, calculate theoretical triplex displacement and each registered window's implied flow at 100% efficiency and at any efficiency explicitly stated by the applicable source. If the pump is not triplex, use its named manufacturer's displacement definition and flag the difference. No assumed efficiency is fitted. Record discrepancies without overwriting P3 inputs.

**Inferred B outcomes.** A near-constant ratio across dates and pump combinations supports a configured displacement. A different independently sourced displacement could identify a flow-input error. Without an installed liner/stroke source, flow remains unverified. A displacement calculated backwards from pressure is a bound only and cannot supply an input.

## C. Bit nozzles

**Calculated check.** Search the bit summary, daily bit tables and dull records for bit run 2, Smith XR+, 12.25 in. Transcribe nozzle counts and diameters, and evidence of an open or centre port. Compute total flow area as the sum of circular opening areas. Preserve conflicts and distinguish a documented absence from an unreported port. A pressure-derived effective area is not a correction.

**Inferred outcomes.** Consistent source records strengthen the recorded area; a source discrepancy identifies an unresolved input. An unrecorded port remains a source gap, not an invented opening.

## D. String and surface equipment

**Calculated D1/D2.** Compare the inventory, Figure 14 and the registered primary catalogue scenario. Identify which body size, nominal weight, grade and thread labels are confirmed. Distinguish those from unmeasured body and joint bores, effective restriction length and connection pitch. Record every HWDP thread conflict and the actual bore source. Do not replace installed machining with a nominal catalogue value.

**Calculated D3.** Record the square-to-hex kelly change and compare the sourced dimensions with API RP 13D, sixth edition (2009), section 7.3, equation 60 and table 4. State which surface-case choice the kelly supports and which remaining layout dimensions are unknown. No surface case changes, including in diagnostic solves, are made in this entry.

**Inferred outcomes.** Confirmed dimensions may justify a later input change. Unconfirmed passages and surface layout remain candidates. Agreement with pressure does not identify a connection.

## E. Mud density

**Calculated check.** Transcribe all reported mud densities for 3–6 August. For every event and calculation, give `observed_median/predicted_median` as the uniform hydraulic-pressure scale factor that would reconcile the medians, and multiply the event's median input density by that factor. Label this a density-equivalent bound at fixed velocities and friction factors, not a fluid-property recalculation. Real changes in density can also change Reynolds number and friction factor. Compare the bound with the reported range. No scaled density becomes an input.

**Inferred outcomes.** Bounds outside the reported density range weaken density alone as an explanation. Overlap would leave density possible but unproven; only the source record supplies an adopted value in later work.

## F. Other development-well flow records

**Calculated check.** Apply B1 to the complete available native 16A and 16B rig records by pump combination, retaining their own timestamps and sample cadence. Use explicit stroke and flow channel names from their headers. Identify whether a source is actually a Pason export. A missing pump channel makes the corresponding combined ratio unavailable; do not infer strokes from flow. Search all daily-report pages for liner and stroke, and record absent information. Existing result archives are not recalculated.

**Inferred outcomes.** A stable flow/stroke ratio supports a derived channel on that rig. A variable ratio can reflect a configuration change, independent measurement or channel synchronisation; it does not identify one without records. Report the implications as source questions only.

## Conditional model-only calculations

**Calculated declaration.** If a primary record establishes a numerical correction to displacement, nozzle area, installed passage dimensions or density for the registered period, replay the original and working calculations with the registered harness and settings. For each of the seven events choose the existing paired window nearest its event-median flow, with earliest timestamp breaking a tie. This selection uses input flow only. Apply each source-established correction separately, then all such corrections together. Preserve the other settings and report pressure terms and solver failures. Use reported slow-circulation equipment and operating inputs only if their depths, flow and mud state are adequately identified; otherwise report the calculation unavailable. No measured pressure selects a case or coefficient.

**Inferred prediction.** A lower sourced flow or density lowers calculated pressure; a larger sourced nozzle area or passage generally lowers its relevant loss. Opposite corrections have the opposite expected sign. A reduction of the discrepancy supports consistency of those independently supplied inputs, without proving the remaining assumptions. These are development comparisons with no skill score. If no new numerical correction is independently established, no new solve is warranted and that outcome is recorded.

## Outputs and decisions

**Calculated archive plan.** Preserve source extracts and reproducible build scripts, the ratio-change tables and check reductions, with hashes of inputs and code. Record every departure from this declaration and its reason. Keep the P3 archives and interpretation byte-identical. Add the findings to the development log and disclosure table, with corrected-input candidates for later adoption and an enquiry list for the rig contractor, Pason or the FORGE team. No candidate is adopted in entry 11.

## Findings

**Calculated.** The [source extracts and check results](results/README.md) preserve every declared check, its coverage and source citations. [manifest.json](manifest.json) identifies the code and inherited inputs. The [enquiry list](results/enquiries.csv) distinguishes missing records from independently supported dimensions.

**Inferred.** Flow behaves as a configured-displacement channel, but an installed 2017 correction is not established. Existing nozzle records agree with the registered area. No input is adopted and no comparison is rescored. The later public rig specification remains time-qualified.

## Sources and attribution

**Measured source records.** Source data are Nash and Moore (2018), *Utah FORGE: Logs and Data from Deep Well 58-32 (MU-ESW1)*, [GDR 1006](https://doi.org/10.15121/1452735); McLennan et al. (2021), *Utah FORGE: Well 16A(78)-32 Drilling Data*, [GDR 1283](https://doi.org/10.15121/1776602); and McLennan et al. (2023), *Utah FORGE: Well 16B(78)-32 Drilling Data*, [GDR 1516](https://doi.org/10.15121/1998591). These datasets are distributed under CC BY 4.0. The extracts select channels and report cells, preserve null handling and calculate the declared reductions. Original downloads are unchanged and are not included. Kenai Drilling's separate public equipment sheet is identified by URL and hash in the source inventory; only factual extracts are included here.

**Calculated labelling convention.** A measured source record means a value printed or exported by its source. The label does not establish that a report entry was independently measured or calibrated. Calculated quantities and inferred explanations are distinguished in the findings.

**Calculated storage.** Bulky native reductions are rebuildable external files, with sizes and SHA-256 hashes in `manifest.json`. Compact results and source extracts remain here. The results document also gives source-derived pump arithmetic, approximate pressure-scale bounds and a sweep qualification of the earlier depth comparison. These additions adopt no input and change no P3 file.
