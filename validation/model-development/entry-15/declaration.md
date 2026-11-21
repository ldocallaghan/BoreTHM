# Entry 15 declaration, 7 November 2026

The candidate follows the temperature history of a radial rock field and a static fluid node at each depth, using the existing finite-volume wall solver. Circulation supplies the fluid temperature and film at each exposed depth. Casing contributes a series resistance. The tool and wall continue exchanging heat as the string descends. The 16B formation profile is mapped by survey TVD and each circulating period uses the recorded inlet.

Zhang et al. (2026), [Geothermics 136, 103598](https://doi.org/10.1016/j.geothermics.2026.103598), Eqs. 4–25, gives the displacement method. The parcel inventory uses the string geometry at the trip-in state. A float valve closes the bore to intake. Unknown valve status requires both intake assumptions. The pump restart uses volume advection down the bore and up the annulus with wall exchange, until one string volume plus the BHA annulus volume passes.

The static film alternatives are the existing laminar floor (Nu = 4.36 on hydraulic diameter) and natural convection from Thomas and de Vahl Davis as reproduced by [Keyhani, Kulacki and Christensen (1983)](https://doi.org/10.1115/1.3245606), Eqs. 2–4. Their correlations use gap-based Rayleigh number up to 200,000, radius ratios 1–10, aspect ratios 1–33 and Prandtl numbers 0.5–10,000. Regime boundaries are reported for Prandtl number 1. Unresolved regimes or geometry outside those ranges allow a sensitivity only. The range is needed because a yield-stress suppression criterion for the recorded mud and geometry has not been established.

The planned layered radial tool uses Zhang et al., Eqs. 26–52, including a positive annulus hydraulic diameter and the actual bore radius for the inner film. The Sanvean bit range is bore fluid to steel mid-wall. The Black Box range spans the wall with mid-wall as centre. EYE TEMP uses bore fluid at the recorded axial offset and is compared only while pumping. Source pages for run-specific tool geometry and float-valve choices must accompany an executable event configuration.

The [recovery verification](../../benchmarks/entry15.md) fails the required Well 4 tolerance with conduction-floor coupling. The integrated moving column, radial tool, pump-on wall exchange and event configuration remain incomplete. Consequently the direction, size and band width of model-only changes for D1, D2, D3 and D4 are unavailable. There is no event score.

## Adoption rule

1. The Kutasov benchmark passes, and the Brown et al. pump-off case passes if it stays a benchmark after section 1.7.
2. On D1 and D3 (bit and Black Box peaks during stages), the RMSE against the band centre is lower than the v1.8.0 method's on the same samples.
3. G1, G2, G3, G5 and G6 change by no more than 0.05 K or 1 psi. The steady circulation calculation is not touched; only the 16B formation mapping changes, by about 0.10 K at the bit, and that is reported separately.

If rule 2 fails, report it and don't adopt. The held-out measures are still scored for both configurations.
