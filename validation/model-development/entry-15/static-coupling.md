# Static fluid coupling

The slow limit uses the existing lumped conduction film, Nu = 4.36 on hydraulic diameter. The fast limit keeps the full liquid heat capacity but sets the film resistance to zero. It shares the new temperature between the liquid and the first rock control volume by adding their energy equations. Casing resistance, when present, remains in series. This corresponds to the well-mixed interior of [Jaeger (1956)](https://www.publish.csiro.au/ph/pdf/PH560167). Neither limit sets an empirical convection coefficient.

[Keyhani, Kulacki and Christensen (1983)](https://doi.org/10.1115/1.3245606) give gap-based correlations for a vertical annulus with differentially heated walls, up to a Rayleigh number of 200,000 and aspect ratio of 33. Their flow regimes also depend on Prandtl number and geometry. MacGregor and Emery (1969) investigated opposing plane walls. The plane layer has a different geometry from the borehole annulus.

[Diment (1967)](https://doi.org/10.1190/1.1439885) and [Sammel (1968)](https://doi.org/10.1190/1.1439977) describe convection in water-filled wells with an axial temperature gradient. A threshold based on that gradient and bore radius cannot be applied to a Rayleigh number based on the radial wall-to-liquid temperature difference and annular gap. The [long vertical Bingham channel study](https://www.sciencedirect.com/science/article/pii/S0377025713001225) treats flow between parallel plates. Transfer of its yield condition to a concentric annulus with transient radial heating has not been established.

[Luheshi (1983)](https://doi.org/10.1111/j.1365-246X.1983.tb01902.x) models the thermal contrast between formation and borehole fluid and motivates a radially resolved conduction sensitivity. This differs from the lumped slow limit, which averages fluid temperature across the section.

Pending the event geometry and Rayleigh audit, the protocol fallback is the fast limit for Newtonian low-solids fluid and the slow limit for mud with a positive recorded yield point. Both limits are retained for each event. The fallback is an assumption about the bounds and does not identify the actual flow regime.


The [16A leg table](../../benchmarks/entry15-rayleigh-16a.csv) samples the
existing conduction-floor model at each leg's final bit depth and time.
It uses the reported yield point and reference plastic viscosity, the
local plastic viscosity from the mud model, and thermal expansion from
a centred density difference at local pressure. The surface-to-bit
length provides a nominal aspect ratio. This ratio does not estimate
the height of an individual convection cell. The eleven gap Rayleigh
numbers span 0.84 million to 5.94 million and the nominal aspect ratios
span 39,312 to 109,792. Both ranges exceed the Keyhani correlation
limits. The yield points span 4.79 to 7.18 Pa.

The [benchmark table](../../benchmarks/entry15-rayleigh-benchmarks.csv)
uses the slow liquid and wall temperatures. The Well 4 estimates use
water properties at nominal hydrostatic pressure. The Khaled estimate
uses the reported bulk properties with water thermal expansion at the
calculated temperature and nominal hydrostatic pressure. No continuous
static column height is specified for these local calculations, so the
aspect ratio is left blank. Rayleigh numbers span 0.64 million to
731 million across the Well 4 geometries and 0.40 million to 7.11 million
for Khaled.

The 16A table also reports the buoyancy stress across the gap,
ρ g β |ΔT| multiplied by the gap, and the ratio of recorded yield
point to that stress. The ratio spans 0.66–3.44. It uses local mud
density and thermal expansion from the same calculation as the
Rayleigh number. The recorded yield point describes surface mud.
The ratio has no validated onset threshold for this annulus, and
some 16A legs could convect. The slow primary and the two limits
remain the declared assumptions.
