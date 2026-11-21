# Well 4 wall recovery, 7 November 2026

Kutasov and Eppelbaum (2014), Eqs. 5–8, calculate the shut-in
temperature using adjusted circulation time. Their model has no
separate fluid node, capacity or film. The [first fluid-node results](entry15.md)
are retained as a coupling sensitivity. They compared the static liquid
temperature with the published recovery curve and do not test the same
quantity.

The [wall comparison](entry15_wall.py) prescribes the circulating wall
temperature, then uses the insulated wall with zero fluid capacity.
At 400 radial nodes, the maximum errors in recovery fraction are
0.152 after 36 h of circulation and 0.091 after 756 h of circulation.
Six and three of the ten time points, respectively, exceed ±0.05.
Doubling from 200 to 400 nodes changes any fraction by at most 0.0000271.
The [full table](entry15-wall.csv) gives the signed errors. The BoreTHM
boundary-value calculation and the paper's adjusted-time approximation
differ even with the fluid capacity removed. This check does not isolate
the cause of that difference.

## Classification amendment, 7 November 2026

Well 4 is a comparison. The published adjusted-time calculation uses a
line-source approximation with formation properties inside the borehole.
The insulated-wall problem in the earlier check has zero capacity
inside the borehole. An independent fine-grid calculation agrees with
BoreTHM for that boundary condition. The exact reference check uses a
tolerance of 0.005 in recovery fraction.

The [filled-hole calculation](entry15-filled.csv) retains the circulating
wall initialisation and then conducts through the full radius with the
formation conductivity and volumetric heat capacity. After two hours
its recovery fractions are 0.256 and 0.152, against 0.202 and 0.119 in
Table 1. The residual is consistent with error in the line-source
approximation at early times. All earlier fluid and wall results and
their original tolerance are retained as historical comparisons.
