# Soultz wall-stability cross-check

`expected.json` copies `tests/golden/soultz_crosscheck_v122.json`. Each row records the strength source, UCS in MPa, wall cooling in K, breakout widths in degrees at 5 km, onset depths in m TVD and verdicts. Arrays follow the order of the Soultz stress cases in [the site input](../sites/soultz.json). Onsets use the retained 10 m search grid; a null onset means no breakout was found within the searched interval.

`inputs.json` records the strength brackets, cooling cases and observed GPK4 onset depths from `crosscheck_soultz`. The site profile exports the linear stress parameters and their published sources. The geotherm remains a function reference with samples on the site programme grid; use its defining code for the 1.5–5 km cross-check interval. [The stress-source guide](../data/sites/stress_sources.md) credits Valley and Evans (2007).

The existing historical regression compares widths to 0.001 degrees and onsets and verdicts exactly. Its separate physical checks compare the onset with the observed interval. The later cooled-zone sensitivity has no retained golden in this case and is not included. No strength is fitted to Soultz when assembling the dataset.
