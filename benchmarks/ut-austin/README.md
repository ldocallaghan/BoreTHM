# UT Austin insulated drill pipe comparison

`expected.json` is an unchanged copy of `tests/golden/benchmark_utaustin.json`. It records Wu et al.'s base-case temperatures, BoreTHM's corresponding temperatures and its whole-wall-conductivity sensitivity, plus BoreTHM's standpipe pressures. Temperatures are degrees C; `spp_MPa` is MPa. The existing regression uses an absolute tolerance of 0.5 in each field's unit. It does not assert agreement with the paper.

`inputs.json` exports the mud and rock constants, four pipe-layer definitions, the alternative whole-wall layers, and the available string dimensions. The base-case defaults are 600 US gal/min, a 24 degrees C/km gradient and frictional heating enabled. Exposure is 1,500 minutes. The published inputs and source credits are in [utaustin2025.md](../data/benchmarks/utaustin2025.md).

The geometry recipes are code references to `benchmark_utaustin.well` and `well_geometry.wu2025_well`. The horizontal survey and full casing/string construction have not been serialised. They must be reconstructed from those definitions before an independent calculation. The expected golden covers the base cases and standpipe pressures; it does not contain the paper's full temperature and flow sweeps.

The case uses no fitted parameter. Values read from the paper's figures have their own reading uncertainty, documented in the source guide. That uncertainty is separate from the BoreTHM regression tolerance.
