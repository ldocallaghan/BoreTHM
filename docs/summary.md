# Quenchwell v1.3.4: a summary for readers

*Draft for Liam O'Callaghan to edit. The figures quoted here are from the reviewed v1.3.4 checkpoint and lever study; release regression files are generated in CI.*

## Soultz: NO-GO for this programme and these assumptions

The reference case reaches 400 °C at 10.7 km at Soultz-sous-Forêts. Its measured stresses cover 1.5 to 5 km and are extrapolated to the target; laboratory granite strengths span 100 to 130 MPa. The corrected programme uses TK-Drakon coated pipe at 40 L/s and simulates a 1.379 SG drilling fluid and 1.444 SG trip fluid at surface.

The worst cases leave both whole-hole fluid windows closed. Drilling needs at least 1.378925 SG against a 1.312559 SG upper bound; trip needs 1.443624 SG against 1.364611 SG. No surface weight satisfies a closed window. The bit is below its 200 °C limit at 197.0 °C, but the best attempted run-in schedule reaches 201.2 °C. The pipe coating also exceeds the manufacturer's stated 204 °C temperature rating during run-in; qualification for that cycle is unknown.

Conserving the barite and water masses makes hot mud lighter than the previous constant-volume mixture. Holding the temperature profile and surface weight fixed, that correction lowers Soultz's trip bottomhole pressure by 3.263 MPa. The full calculation feeds the required drilling and trip fluids back through circulation and every gate. It checks every depth at its own exposure, including the target and final stand. These corrections are documented beside the previous result in [the first checkpoint](v134-checkpoint-1.md).

Across the five sites, the stated programme gives NO-GO at Soultz, United Downs and Pannonian, CONDITIONAL at Larderello with 1.036 SG drilling and 1.094 SG trip fluids, and GO at Newberry with water. Larderello is evaluated and exported at 2,400 m. The Pannonian coating remains unqualified even though its closed windows already decide NO-GO.

## The design study: NO-GO for this programme and these assumptions

No evaluated single lever or permitted pair reopens either deep site. Deeper casing opens Soultz's trip window, but drilling and tools still fail. Low viscosity can open the United Downs drilling window, while zero surge and swab allowance opens its trip window; neither change clears every gate. Stronger insulation cools the tools but leaves pressure and pump failures. Constant-BHP managed-pressure drilling fails the evaluated control and window constraints, with some high-pressure trials numerically unresolved.

Raising the coating rating to about 274.34 °C at Soultz or 287.45 °C at United Downs clears only that temperature gate. Both thresholds were checked at half the search tolerance. Soultz's bit-only lower-flow boundary is near 39 L/s, with run-in still failing. These subgate thresholds supply no full-site minimum. The continuous searches sampled selected settings and do not establish complete operating envelopes.

The pair of a 10.2 km casing shoe and dual-wall pipe at Soultz cools the tool but leaves the drilling window closed and needs about 121 MPa standpipe pressure. The lower-viscosity fluid and one-hour failure-delay hypothesis at United Downs open drilling but leave trip stability and run-in survival failing. MPD and trip-speed or flow control are operating practice; casing is well design. The modeled insulated replacements and higher cycle-rated coating are hypothetical, and the failure-free delay lacks supporting observations. The [lever tables](levers.md) give every setting, prescription and availability source.

## The open cooling question

In the base model the rock that governs breakout width is still at formation temperature when the bit exposes it. Fluid weight holds the wall; cooling protects the tools and slows creep. The width is judged at the wall using the temperature at the depth reached by an uncooled breakout with water in the hole, the existing skin heuristic. Images logged within minutes in sediment support an early check, but do not determine the timing or growth law in hot crystalline rock. Assuming an hour or two of failure-free cooling opens drilling windows in L7 while leaving other failures.

The [A1 to A9 ledger](robustness.md) keeps both deep sites NO-GO across its optimistic and adverse comparisons for the base programme. Pannonian's historical 0.041 °C tool margin is unresolved because its timestep change exceeds 20% of that margin. Source checks and numerical brackets describe the evidence; they assign no probability to stresses extrapolated many kilometres below measurements.

## Questions for the next data

1. What governs breakout width in hot crystalline rock in the first minutes after exposure? Paired images at the bit and after pauses would test the immediate-exposure rule and the skin heuristic.
2. Which high-temperature drilling fluids are used at roughly 1.2 to 1.5 SG, and what are their plastic viscosity and yield point through circulation and hot trips? The published 1.3 SG formate system measured after 200 °C ageing supplies context, while the water-viscosity endpoint remains an idealised bound.
3. How are insulating coatings and managed-pressure equipment qualified for the full temperature cycle? A pressure rating or steady circulating-temperature rating does not establish survival through connections and repeated trips.

Stress measurements closer to the targets would reduce the largest input uncertainty. The close margins in Soultz's casing lever and pair also meet the brief's trigger to revisit the common event timeline before an operating-range claim. The remaining deferred models and their triggers are listed in the README.
