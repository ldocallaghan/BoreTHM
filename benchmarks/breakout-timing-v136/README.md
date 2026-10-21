# v1.3.6 breakout timing

`expected.json` copies `tests/golden/v136_breakout_timing.json`, preserving all paired-case and scan values and their original provenance. `evidence/` includes the two scan summaries and all twenty retained full programme records. Each scan summary's evidence filenames resolve within that folder.

`inputs.json` exports the retained programme settings for zero and one hour of breakout formation delay and the fixed scan grid. Site stress and strength cases are in [Soultz](../sites/soultz.json) and [United Downs](../sites/united-downs.json). All built-in cases were evaluated; the paired results are not limited to central stress or strength. Geometry and geotherm functions remain code references as described in the main dataset guide.

`drill_SG` is pressure-equivalent SG at the target, including connection checks. `drill_rho_surface` and window `lo`/`hi` are kg/m3 at 20 degrees C; dividing the latter by 1,000 gives surface SG. Bound-location `md` is m measured depth. These quantities must be compared separately.

Existing tests compare SG values within 0.002, target and bound depths within 0.01 m, and discrete settings, states, verdicts and scan brackets exactly. The first sampled drilling-fluid window opens between 15 and 20 minutes at Soultz and between 10 and 15 minutes at United Downs. Every complete programme remains NO-GO. The scans have no interpolation or refinement and do not establish a measured formation time.
