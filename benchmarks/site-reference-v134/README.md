# v1.3.4 site reference table

`expected.json` is the unchanged `tests/golden/v134_site_table.json`, including its original provenance. It covers Soultz, United Downs, Larderello, the Pannonian Basin and Newberry. `evidence/` retains the corresponding checkpoint records with site inputs, selected operating programmes and full window descriptions.

`inputs.json` identifies the site, programme and depth-grid fields in each evidence file. The five profiles in `sites/` export the built-in scalar, stress and strength inputs. Their callable geotherms are described by source-code references and sampled on each saved programme depth grid. Those samples do not serialise the complete temperature function. Geometry and fluid-model assumptions remain in the cited evaluation code and the retained programme records.

Temperatures are degrees C, depths m, and all `weights_SG` and window bounds are surface SG at 20 degrees C. Bound records name the operating state, stress/strength case and measured depth. `tolerances.json` describes the existing ordered comparison rules: SG values within 0.002, temperatures within 0.1 degrees C, target depths within 0.1 m and bound-location depths within 100 m. Status and gate values are exact. Provenance and elapsed times are not physical acceptance criteria.

The source data guides are under `data/`. Their measured, calibrated, assumed and extrapolated inputs retain the distinctions recorded in each profile. A reference match does not improve the evidence basis of a speculative site.
