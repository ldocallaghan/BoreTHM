# Development priorities and unresolved questions

Model expansion is paused while specialist feedback is sought on the evaluated programmes. Corrections to demonstrated defects remain in scope. This document records the unresolved assumptions and the triggers for separately scoped modelling work; it does not initiate those studies.

For a concise overview, see [scope and limitations](../README.md#scope-and-limitations). The [reader summary](summary.md) sets out questions for specialist discussion.

## Assumptions and deferred work

The [robustness ledger](robustness.md) compares A1 to A9 at the deep sites, covering property pressures and face heat, delivery and staging of coolant, the changing trip column and the uniform-fluid bound, shallow circulation, surge and swab, and numerical resolution. The base deep-site verdicts remain NO-GO for this programme and these assumptions across the A1-A9 comparisons performed. None of the optimistic comparisons reopens a site. These comparisons generally change one approximation at a time and do not cover every joint uncertainty. They assign no probability to extrapolated inputs and do not establish robustness of every lever or combination.

Pannonian's historical 199.959 °C tool peak leaves 0.041 °C below its limit. Halving the timestep changes the peak by about 0.099 °C, above 20% of that margin, so the historical threshold is unresolved. The corrected closer-staging result has a larger tool margin; its pressure windows are still closed.

Stress and temperature extrapolation, the skin heuristic and the time taken for failure in hot crystalline rock remain unresolved physical questions. Strength at UD-1 is calibrated with the assumed stress profile, and the two cannot be checked independently there. The circulation validation is at FORGE's depth and temperature, well below the targets. Newberry's well check reproduces the volcanic breakouts but also predicts failure in the granodiorite where none was logged. Larderello and Pannonian retain unsourced strength assumptions.

The rheology is one reference mud, with a fixed yield point and a viscosity law scaled from water. The barite heat capacity and expansion are constant approximations whose source values are checked in the lever report. A published 1.3 SG potassium-formate system retained 30 mPa s PV after 200 °C ageing, measured after cooling to 49 °C; that result does not qualify the modeled fluid through a 400 °C trip. The manufacturer's 204 °C coating rating does not quantify survival through the hotter full cycle. The cited onshore MPD pressure rating supplies a mechanical bound with an explicit thermal-qualification unknown.

The tool is a lumped collar and enclosed-fluid model. Staging supplies steady coolant without advective travel in the string, and its duration is absent from the base trip clock. The trip column is frozen during run-in, with the uniform heavier fluid present immediately. Casing and cement integrity, string loads and fatigue, circulation losses, and coupling of creep to the drilling cycle require separate well-design work. The hole-cleaning reference and cycle timings come from one well; the rig check uses three pumps of one published rating. The 0.02 SG surge and swab allowance is a sensitivity assumption, with no verified field range for these 10 to 13 km wells.

The deferred work has explicit triggers:

| Deferred item | Trigger for bringing it back |
|---|---|
| Programme schema and full cache invalidation, P-01/P-02 | Repeated runs cannot be traced with the release JSON, or an external user requests it |
| Common event timeline, H-01 | A4 or A5 changes the decision, or a lever is within 0.02 SG or 5 °C of a threshold |
| Coolant advection in the string, H-02 | A3 straddles tool survival at a site whose verdict depends on it |
| Fluid displacement, W-03 | A6 straddles the site verdict |
| Full flow and stress envelopes, D-03 | A lever reopens a site and an operating range must be claimed |
| Near-bit thermal model, growth law and thermo-poroelasticity | Specialist interest, usable observations or a clearly discriminating hypothesis justify a separately scoped study; L7 becoming decision-relevant is another trigger |

**H-01 trigger met; implementation deferred by project priority.** Soultz L2's 0.00137 SG trip width and its L2+L4 pair's 0.00949 SG drilling deficit meet the proximity trigger. The evaluated programmes still fail other gates, and no operating range is claimed. Revisit before claiming a near-threshold programme is feasible, or when specialist feedback or new data makes the timing approximation decision-relevant. Coolant delivery (H-02) and fluid displacement (W-03) retain their distinct triggers above. Model expansion is paused to seek external feedback; a demonstrated defect can still require correction. This pause leaves the cooling question open. The source files and retained trial checksums keep this release's comparisons traceable; the trial cache checks model and schedule sources, benchmark data and runtime versions.

The most useful next evidence is early and repeated image logs in hot crystalline rock, and qualified fluid rheology at the reported weights and temperatures. Full-cycle coating and MPD-equipment qualification is also needed. The focused questions are set out in [the reader summary](summary.md), also available as a [two-page PDF](../output/pdf/summary-v135.pdf). The FORGE image-log study and near-bit thermal work remain possible follow-ups under separate specifications. Breakout-timing data is one possible basis for near-bit pre-cooling work, alongside reader interest, usable observations or a discriminating hypothesis. Software interfaces and examples enable external use; practical usefulness remains for readers and users to establish.

