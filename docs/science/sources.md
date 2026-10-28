# Sources and related work

This page provides the scientific context and bibliography. Input-specific provenance remains beside the data: [site parameters](../../src/borethm/data/sites/stress_sources.md), [material properties](../../src/borethm/data/materials.md), [FORGE 16B extracts](../../src/borethm/data/forge16b/README.md), [FORGE 16A extracts](../../validation/forge16a/README.md) and [Newberry extracts](../../src/borethm/data/newberry/README.md).

## Related work

The use of insulated drill pipe to keep the bit cool in hot rock is well established. Sandia National Laboratories and Drill Cool Systems built insulated drill pipe in the 1990s and tested it in the laboratory and in a geothermal well, comparing circulating temperatures with those in conventional pipe (Finger et al., 2000). A later DOE-funded project to develop it for high-temperature drilling stopped after its first phase, because a pipe strong enough for the hole left too small a bore for the flow (Champness et al., 2008). Eavor ran internally and externally coated pipe at Utah FORGE in 2023 and has published its field experience and coating properties (Vetsak et al., 2024). Circulating temperatures in wells have been calculated analytically since Raymond (1969), Holmes and Swift (1970) and Kabir et al. (1996), and numerically with Sandia's GEOTEMP (Mitchell, 1981) and GEOTEMP2 (Mitchell et al., 1984), which Ujyo et al. (2026) have extended to supercritical water as GEOTEMPSC; they find that circulation cools the rock only a few metres from the wall. Model 1 is a steady-state model of the same kind. The recovery of the temperature around a borehole after circulation stops has been treated with line-source solutions since Bullard (1947) and Lachenbruch and Brewer (1959). Wu et al. (2025) compared conventional, coated and dual-wall pipe in deep vertical and horizontal wells with a transient thermo-hydraulic model, and Pearce and Pink (2024, 2025) concluded that superhot wells can be drilled by combining existing technologies, with insulated pipe the main means of keeping tools below their 175 to 200 °C limits.

The mechanics of borehole stability used here are also established. The stress concentration around a borehole, breakout formation under a Mohr-Coulomb criterion and the use of breakout width to infer stress are standard (Zoback, 2007). Cooling a borehole wall adds a thermal hoop stress that suppresses breakouts and promotes tensile fractures, the combination studied by Hals and Berre (2012). In practice, the Japan Beyond-Brittle Project describes drilling at Kakkonda into rock above 500 °C with continuous circulation, and sets a target of cooling the hole below 160 °C (Muraoka et al., 2014), and Kruszewski and Wittig (2018) reviewed the failures in 20 wells drilled into supercritical conditions, many of them in casing and cement under thermal load. On the production side, Eavor's Geretsried project now reports about 8.5 MW of heat from its first loop, more than 2 MW per lateral pair falling to an expected 1.3 MW after five years (Eavor, 2026), and Beckers and Johnston (2022) estimated about 22 MW of heat and 2.2 MW of electricity from a 7.5 km loop with more than 90 km of laterals at 30 °C/km.

BoreTHM combines circulating temperatures with wall thermal stress and fluid-pressure constraints for named site programmes. The circulation component has been compared with a published simulator and temperatures measured at FORGE. Some 16B runs were used to fit parameters; its partial-insulation run was predicted without further fitting. The 16A comparison fits nothing and reports the observed disagreements and conditional diagnostics. Rock strength is calibrated at UD-1, with separate checks at Soultz and Newberry. The [validation guide](validation.md) describes the scope and limitations of each comparison. Analytical checks test specified equations, while regression tests check numerical repeatability against saved outputs. None of these checks validates a complete deep drilling programme.

## References

Abate, J., Valkó, P.P., 2004. Multi-precision Laplace transform inversion. International Journal for Numerical Methods in Engineering 60 (5–7), 979–993.

American Petroleum Institute, 2009. Rheology and Hydraulics of Oil-well Drilling Fluids. API Recommended Practice 13D, sixth edition.

Anawe, P.A.L., Folayan, J.A., 2018. Data analyses on temperature-dependent behaviour of water based drilling fluid rheological models. Data in Brief 21, 289–298. https://doi.org/10.1016/j.dib.2018.09.100

Bada, G., Dövényi, P., Horváth, F., Szafián, P., Windhoffer, G., 2007. Present-day stress field in the Pannonian Basin and the surrounding Alpine-Carpathian-Dinaric orogens. Földtani Közlöny 137 (3).

Beckers, K.F., Johnston, H.E., 2022. Techno-economic performance of Eavor-Loop 2.0. Proceedings, 47th Workshop on Geothermal Reservoir Engineering, Stanford University, SGP-TR-223.

Bertani, R., et al., 2018. The first results of the DESCRAMBLE project. Proceedings, 43rd Workshop on Geothermal Reservoir Engineering, Stanford University, SGP-TR-213.

Bourgoyne, A.T., Millheim, K.K., Chenevert, M.E., Young, F.S., 1986. Applied Drilling Engineering. SPE Textbook Series 2. Society of Petroleum Engineers.

British Geological Survey, 2024. United Downs 1 borehole image interpretation. NERC EDS National Geoscience Data Centre. https://doi.org/10.5285/a040a246-8691-428b-b146-13874e743b0a. Contains NERC materials ©NERC 2024.

Bullard, E.C., 1947. The time necessary for a bore hole to attain temperature equilibrium. Geophysical Supplements to the Monthly Notices of the Royal Astronomical Society 5, 127–130.

Carslaw, H.S., Jaeger, J.C., 1959. Conduction of Heat in Solids, 2nd edition. Oxford University Press.

Champness, T., Worthen, T., Finger, J., 2008. Development and application of insulated drill pipe for high temperature, high pressure drilling. Drill Cool Systems Inc., final report to DOE/NETL.

Cladouhos, T.T., 2012. Newberry EGS Demonstration: Well 55-29 Stimulation Data. AltaRock Energy. Geothermal Data Repository, submission 271. https://doi.org/10.15121/1357916. CC-BY 4.0.

Clean Air Task Force, 2022. Superhot Rock Energy: A Vision for Firm, Global Zero-Carbon Energy.

Davatzes, N.C., Hickman, S.H., 2011. Preliminary analysis of stress in the Newberry EGS well NWG 55-29. Geothermal Resources Council Transactions 35.

Eavor, 2026. Technical update from Geretsried: what we built, what we learned and what comes next. 21 May 2026. https://eavor.com/blog/technical-update-from-geretsried-what-we-built-what-we-learned-and-what-comes-next/

Finger, J.T., Jacobson, R.D., Champness, A.T., 2000. Development and testing of insulated drillpipe. IADC/SPE Drilling Conference, New Orleans. SAND2000-0285C.

Ghassemi, A., Tao, Q., Diek, A., 2009. Influence of coupled chemo-poro-thermoelastic processes on pore pressure and stress distributions around a wellbore in swelling shale. Journal of Petroleum Science and Engineering 67, 57–64.

Hals, K.M.D., Berre, I., 2012. Thermal fracturing of geothermal wells and the effects of borehole orientation. arXiv:1212.2763.

Holmes, C.S., Swift, S.C., 1970. Calculation of circulating mud temperatures. Journal of Petroleum Technology 22 (6), 670–674.

Holtzman, B.K., Groebner, N., Mittal, T., 2023. Quench-spallation drilling: a novel drilling head design for routine heat mining above the brittle-ductile transition. Geothermal Resources Council Transactions 47, 2960–2978.

IAPWS, 1992. Revised Release on the Values of Temperature, Pressure and Density of Ordinary and Heavy Water Substances at their Respective Critical Points. R2-83(1992). https://iapws.org/public/documents/CU3rZ/crits.pdf

Jaeger, J.C., 1956. Conduction of heat in an infinite region bounded internally by a circular cylinder of a perfect conductor. Australian Journal of Physics 9 (2), 167–179.

Jaeger, J.C., Cook, N.G.W., Zimmerman, R.W., 2007. Fundamentals of Rock Mechanics, 4th edition. Blackwell.

Gilmour, B., Wooden, J., Pulka, F., Rose, B., Barker, C. and Borchardt, E., 2021. Utah FORGE: Well 16A(78)-32 Logs. Geothermal Data Repository, submission 1292. https://doi.org/10.15121/1777912. CC-BY 4.0.

Johancsik, C.A., Friesen, D.B., Dawson, R., 1984. Torque and drag in directional wells: prediction and measurement. Journal of Petroleum Technology 36 (6), 987–992.

Jones, C., 2022. Utah FORGE: Deep Wells Temperature Surveys as of September 2022. Geothermal Data Repository, submission 1421. https://doi.org/10.15121/1893533. CC-BY 4.0.

Kabir, C.S., Hasan, A.R., Kouba, G.E., Ameen, M.M., 1996. Determining circulating fluid temperature in drilling, workover, and well-control operations. SPE Drilling & Completion 11 (2), 74–79.

Kruszewski, M., Wittig, V., 2018. Review of failure modes in supercritical geothermal drilling projects. Geothermal Energy 6, 28.

Lachenbruch, A.H., Brewer, M.C., 1959. Dissipation of the temperature effect of drilling a well in Arctic Alaska. U.S. Geological Survey Bulletin 1083-C, 73–109.

Liotta, D., Brogi, A. Pliocene-Quaternary fault kinematics in the Larderello geothermal area (Italy): insights for the interpretation of the present stress field. Manuscript submitted to Geothermics.

McLennan, J., Nash, G., Moore, J., Skowron, G. and Woolsey, S., 2021. Utah FORGE: Well 16A(78)-32 Drilling Data. Geothermal Data Repository, submission 1283. https://doi.org/10.15121/1776602. CC-BY 4.0.

McLennan, J., Mock, B., Swearingen, L., Baldwin, R., Hodder, M., Vetsak, A., Kuhns, A.T., Breland, J., England, K., 2023. Utah FORGE: Well 16B(78)-32 Drilling Data. Geothermal Data Repository, submission 1516. https://doi.org/10.15121/1998591. CC-BY 4.0.

Mitchell, R.F., 1981. Downhole temperature prediction for drilling geothermal wells. Sandia National Laboratories, SAND-81-0036C.

Mitchell, R.F., Mondy, L.A., Duda, L.E., 1984. GEOTEMP2: advanced wellbore thermal simulator. Sandia National Laboratories.

Moore, J.C., Chang, C., McNeill, L., Thu, M.K., Yamada, Y., Huftile, G., 2011. Growth of borehole breakouts with time after drilling: implications for state of stress, NanTroSEIZE transect, SW Japan. Geochemistry, Geophysics, Geosystems 12 (4), Q04D09. https://doi.org/10.1029/2010GC003417

Muraoka, H., Asanuma, H., Tsuchiya, N., Ito, T., Mogi, T., Ito, H., 2014. The Japan Beyond-Brittle Project. Scientific Drilling 17, 51–59.

NOV, 2014. 14-P-220 triplex mud pump. Technical marketing sheet.

NOV, 2024. TK-Drakōn insulating coating. Tuboscope product flyer D392006697-MKT-001.

Pearce, R., Pink, T., 2024. Drilling for superhot geothermal energy: a technology gap analysis. Cascade Institute, technical paper 2024-6.

Pearce, R., Pink, T., 2025. Drilling for superhot geothermal energy: a technology gap analysis. Proceedings, 50th Workshop on Geothermal Reservoir Engineering, Stanford University, SGP-TR-229.

Raymond, L.R., 1969. Temperature distribution in a circulating drilling fluid. Journal of Petroleum Technology 21 (3), 333–341.

Reinecker, J., Gutmanis, J., Foxford, A., Cotton, L., Dalby, C., Law, R., 2021. Geothermal exploration and reservoir modelling of the United Downs deep geothermal project, Cornwall (UK). Geothermics 97, 102226.

Timoshenko, S.P., Goodier, J.N., 1970. Theory of Elasticity, 3rd edition. McGraw-Hill.

Ujyo, S., Hyodo, M., Okabe, T., Naganawa, S., Burnell, J., 2026. A wellbore hydrothermal simulation technology applicable to supercritical conditions. Proceedings, 51st Workshop on Geothermal Reservoir Engineering, Stanford University, SGP-TR-230.

Valley, B., Evans, K.F., 2007. Stress state at Soultz-sous-Forêts to 5 km depth from wellbore failure and hydraulic observations. Proceedings, 32nd Workshop on Geothermal Reservoir Engineering, Stanford University, SGP-TR-183.

Vetsak, A., Besoiu, C., Zatonski, V., Torre, A., Hodder, M., Toews, M., 2024. The insulated drill pipe: field experience and thermal model validation. SPE/IADC Drilling Conference. https://doi.org/10.2118/217753-MS

Wenning, Q.C., Berthet, T., Ask, M., Zappone, A., Rosberg, J.-E., Almqvist, B.S.G., 2017. Image log analysis of in situ stress orientation, breakout growth, and natural geologic structures to 2.5 km depth in central Scandinavian Caledonides: results from the COSC-1 borehole. Journal of Geophysical Research: Solid Earth 122 (5), 3999–4019. https://doi.org/10.1002/2016JB013776

Wu, Y., Zhang, Y., Bettir, N., Ashok, P., van Oort, E., 2025. A comprehensive evaluation of drill pipe insulation for downhole temperature management using physics-based models. Proceedings, 50th Workshop on Geothermal Reservoir Engineering, Stanford University, SGP-TR-202.

Xiao, D., Hu, Y., Wang, Y., Deng, H., Zhang, J., Tang, B., Xi, J., Tang, S., Li, G., 2022. Wellbore cooling and heat energy utilization method for deep shale gas horizontal well drilling. Applied Thermal Engineering 213, 118684.

Zoback, M.D., 2007. Reservoir Geomechanics. Cambridge University Press.
