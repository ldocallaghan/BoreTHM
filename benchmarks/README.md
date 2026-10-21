# BoreTHM benchmark dataset 1.0

Use these reference cases to compare another thermal or borehole-stability model with BoreTHM. Expected outputs are copied from the regression goldens and saved evidence shipped at v1.3.6. Building this dataset runs no models and changes no reference values.

The dataset has its own version, 1.0, separate from the software version. A match to a reference result checks reproducibility of the stated calculation. It does not establish agreement with field observations or suitability for a particular well.

## Cases

**[UT Austin insulated drill pipe](ut-austin/README.md).** The vertical and horizontal base cases compare BoreTHM with Wu et al. (2025), including four pipe types and standpipe pressures. The paper's results and the two interpretations of coated pipe are kept separately. The regression tolerance is not an agreement criterion for the paper.

**[FORGE 16B circulation](forge-circulation/README.md).** The May 2023 insulated drill pipe trial provides fitted film and conductivity values, run temperatures, the BHA 12 blind prediction and the decomposition of the temperature change. The unfitted chain is retained beside the fitted results. Temperatures in this golden are in degrees F.

**[FORGE pauses](forge-pauses/README.md).** The retained return-temperature anomalies cover pauses and trips, with the mixed-fluid-node model and its no-node sensitivity. The attenuation factor is fitted on trips; short pauses are excluded from that fit. Temperature anomalies are in degrees F.

**[Soultz stability cross-check](soultz-crosscheck/README.md).** The wall-only comparison against GPK3/GPK4 records breakout widths at 5 km and onset depths for the published stress cases, strength brackets and wall cooling. It uses the historical v1.2.2 golden still checked by the current tests.

**[v1.3.4 site reference table](site-reference-v134/README.md).** Five built-in sites provide whole-programme fluid windows and equipment gates. The saved programme records accompany the projected reference table. Surface fluid density and target-depth SG equivalents are distinct quantities.

**[v1.3.6 breakout timing](breakout-timing-v136/README.md).** Soultz and United Downs include paired zero- and one-hour formation-delay cases and the fixed 0–120 minute scan. The retained drilling-fluid windows first open between 15 and 20 minutes at Soultz and between 10 and 15 minutes at United Downs. The complete programmes remain NO-GO. These brackets do not measure breakout formation time.

## Files, units and tolerances

Each case has `inputs.json`, an unchanged `expected.json`, and `tolerances.json` describing its existing regression assertions. `evidence/` contains the original saved records where available. Fields without an existing numerical acceptance assertion are identified; the dataset does not assign them a new tolerance.

`sites/` contains all five `SiteProfile` records, including stress gradients and strength cases, exported with `dataclasses.asdict`. Its `units.json` describes the profile fields, and each case's `inputs.json` includes input units. Callable geotherms are represented by code references and CSV temperature samples on the saved programme depth grids. Those site designs are vertical, so measured depth equals true vertical depth in these tables. Samples do not replace the function definitions, and do not describe the full surface-to-target temperature profile.

Geometry recipes for the UT Austin and FORGE cases remain code references. Pipe layers and the available dimensional constants are machine-readable, but these cases are not complete language-independent input decks. Reconstructing their surveys, casing intervals and changing strings still requires the cited input-construction functions. No general geometry or function serialiser has been added.

Lengths are m, pressures Pa and temperatures degrees C unless the case says otherwise. FORGE CSV headers retain their field units, including ft, degrees F and US gal/min. The Soultz golden stores UCS in MPa. SG is density relative to 1,000 kg/m3: a pressure-equivalent SG at depth is different from the surface SG of mud at 20 degrees C. See each case's unit record before comparing values.

`sources.json` records file origins and copied-file hashes. Its input-code links identify the packaged definitions used for export. Existing provenance inside the goldens and evidence remains unchanged. `manifest.json` gives the SHA-256 of every dataset file except itself.

Newberry's fitted stress coefficients are copied exactly from the retained programme input record. This preserves the reference inputs across the last-digit round-off differences of least-squares libraries on different platforms. Other profile fields are exported from their dataclass definitions.

## Sources and licences

BoreTHM's reference results, exported inputs and dataset documentation are CC BY 4.0; the licence text is in [LICENSE](LICENSE). Third-party data keep their source licences and credits, as detailed in [NOTICE](NOTICE) and the guides under `data/`.

The FORGE and Newberry extracts are CC BY 4.0. The BGS UD-1 image interpretation is supplied under the Open Government Licence: Contains NERC materials ©NERC 2024. Contains data supplied by UKRI. Paper references and source guides provide attribution for published parameters; the papers themselves are not included. Data guides are retained as source records, including their original extraction commands.

## Build and check

From a BoreTHM source checkout with the package installed:

```sh
python tools/build_benchmarks.py --zip ../borethm-benchmarks-1.0.zip
python -m pytest tests/test_benchmarks.py
```

The ZIP must be outside the repository. It contains one `borethm-benchmarks-1.0/` directory, including the manifest and licence records. Output bytes and ZIP entries are deterministic. Existing results and goldens are only read.

## How to cite

Cite Liam O'Callaghan, *BoreTHM benchmark dataset*, version 1.0. A separate dataset DOI will be added here after its Zenodo deposit. Cite the software separately using its `CITATION.cff`, and acknowledge the field-data sources used by the selected case. The dataset has not yet been deposited on Zenodo.
