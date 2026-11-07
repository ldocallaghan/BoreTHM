# Circulation comparison amendment, 7 November 2026

Brown, Holmes, Zatonski and Toews (2023), *Enablement of High-Temperature
Well Drilling for Multilateral Closed-Loop Geothermal Systems*, 48th Stanford
Geothermal Workshop, SGP-TR-224. [Paper](https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2023/Holmes.pdf)

The original Table 5 results were 9.14 K low for steel and 3.78 K low for
insulated pipe, outside the respective tolerances of ±3.574 K and ±1.472 K.
Those thresholds assumed the case was fully specified. Equations 13–15 use
an effective formation radius with a fitted Fourier number that the paper
does not provide. Table 5 is now a comparison. A diagnostic removed only
the annulus-to-formation film resistance, consistent with the paper's
wall approximation. It yielded 169.62 °C and 69.87 °C, still 9.08 K and
3.73 K below the paper. See [the diagnostic](brown-no-outer-film.csv).

The pump-off case is also a comparison. Figure 21 gives about 233 minutes
to 150 °C at 5 km, but the paper does not give the initial radial rock
temperature profile or axial fluid state needed to reproduce that transient.
This classification precedes any pump-off result.

In [the Kabir decomposition](kabir-decomposition.csv), each individual
change starts from the matched forward solution. At fixed film conductances,
variable fluid properties move the bit temperature by −22.25 K in Holmes
and Swift and −1.46 K in Khaled. With constant properties, distributed
friction adds 2.31 K and 3.67 K. Nozzle dissipation alone adds 0.30 K and
1.37 K at the bit. The recorded Phase 0 run had friction and face heat
disabled, so the two heat sensitivities do not explain its discrepancy.
The published case inputs specify zero separate bit heat.

The matched films are evaluated with the release correlation at the inlet.
Re-evaluating them with the same constant properties leaves the profile
within 0.000001 K. With variable properties, re-evaluating films also
changes the bore film and couples both streams to the local temperature.
The combined release calculation shifts the bit by −38.65 K and +6.61 K.
These effects do not add linearly. The annulus is laminar throughout Holmes
and Swift and turbulent throughout Khaled under the release regime criterion.
The table gives the Reynolds number ranges.
