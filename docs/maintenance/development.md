# Maintenance priorities and modelling triggers

This page records implementation priorities for maintainers. Reader-facing caveats are in [limitations and open questions](../science/limitations.md). Model expansion is paused for specialist feedback; corrections to demonstrated defects remain in scope. New physics or a new site needs a separate specification.

The deferred work has explicit triggers:

| Deferred item | Trigger for bringing it back |
|---|---|
| Programme schema and full cache invalidation, P-01/P-02 | Repeated runs cannot be traced with the release JSON, or an external user requests it |
| Common event timeline, H-01 | A4 or A5 changes the decision, or a lever is within 0.02 SG or 5 °C of a threshold |
| Coolant advection in the string, H-02 | A3 straddles tool survival at a site whose verdict depends on it |
| Fluid displacement, W-03 | A6 straddles the site verdict |
| Full flow and stress envelopes, D-03 | A lever reopens a site and an operating range must be claimed |
| Near-bit thermal model, growth law and thermo-poroelasticity | Specialist interest, usable observations or a clearly discriminating hypothesis justify a separately scoped study; L7 becoming decision-relevant is another trigger |

**H-01 trigger met; implementation deferred by project priority.** Soultz L2's 0.00137 SG trip width and its L2+L4 pair's 0.00949 SG drilling deficit meet the proximity trigger. The evaluated programmes still fail other gates, and no operating range is claimed. Revisit before claiming a near-threshold programme is feasible, or when specialist feedback or new data makes the timing approximation decision-relevant. Coolant delivery (H-02) and fluid displacement (W-03) retain their distinct triggers above. Model expansion is paused to seek external feedback; a demonstrated defect can still require correction. This pause leaves the cooling question open.

Near-bit pre-cooling and the FORGE image-log follow-up can be justified by specialist interest, usable observations or a discriminating hypothesis. Neither study starts through the documentation update.
