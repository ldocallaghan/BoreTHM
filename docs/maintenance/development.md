# Maintenance priorities and modelling triggers

This page records implementation priorities for maintainers. The caveats for users are in [limitations and open questions](../science/limitations.md). New physics or a new site needs a separate specification.

The deferred work has explicit triggers:

| Deferred item | Trigger for bringing it back |
|---|---|
| Programme schema and full cache invalidation, P-01/P-02 | Repeated runs cannot be traced with the release JSON, or an external user requests it |
| Common event timeline, H-01 | A4 or A5 changes the decision, or a lever is within 0.02 SG or 5 °C of a threshold |
| Coolant advection in the string, H-02 | A3 straddles tool survival at a site whose verdict depends on it |
| Fluid displacement, W-03 | A6 straddles the site verdict |
| Full flow and stress envelopes, D-03 | A lever reopens a site and an operating range must be claimed |
| Tied bound labels: report every tied case in `lo_by` and `hi_by`, keeping `case` as the first, and have `describe_bound()` print "all cases" when every case ties | The next release that regenerates the evidence |
| Near-bit thermal model, growth law and thermo-poroelasticity | Specialist interest, usable observations or a clearly discriminating hypothesis justify a separately scoped study; the breakout formation-delay experiment becoming decision-relevant is another trigger |

**H-01 trigger met; not yet implemented.** Soultz L2's 0.00137 SG trip width and its L2+L4 pair's 0.00949 SG drilling deficit meet the proximity trigger. The evaluated programmes still fail other gates, and no operating range is claimed. Revisit before claiming a near-threshold programme is feasible, or when new data make the timing approximation decision-relevant. Coolant delivery (H-02) and fluid displacement (W-03) retain their distinct triggers above.

Near-bit pre-cooling and the FORGE image-log follow-up can be justified by specialist interest, usable observations or a discriminating hypothesis.

## FORGE image-log follow-up

The [16B image-log inventory](../../src/borethm/data/forge16b/image_logs_inventory.md) identifies repeated coverage suitable for investigating breakout-width changes. The proposed follow-up is to obtain matched image intervals, establish logging direction and interpretation provenance, and compare widths at the same depths while accounting for the different circulation histories. Much of the overlap is in deviated hole, so predicting widths would require the corresponding stress calculation. The inventory is complete; the paired-width analysis has not been performed. This work requires a separate specification.
