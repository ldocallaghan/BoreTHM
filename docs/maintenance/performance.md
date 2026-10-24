# Evaluation performance

Measurements on 23–24 October 2026 show that circulation solves dominate the
five built-in site assessments. Water-property interpolation accounts for
much of their cost, and several solves repeat identical inputs. A fixed-flow
design-study case spends more time on wall temperature and pressure windows.

The installed package also runs in Pyodide under Node.js. Input validation
is quick after startup, and a complete Newberry evaluation takes about
51 seconds. This supports further work on a browser site-file helper;
browser deployment and numerical acceptance still need their own checks.

## Baseline and environment

The baseline is `main` at `b9a8a93f49f1b53b7bd71a713b8ca4988e7c21c6`
(BoreTHM 1.5.0 plus its publication record). The source was exported from Git,
built as a wheel and installed without editable mode in a fresh environment
outside the checkout. Dependencies came from `requirements-lock.txt`.
Installed-package checks and `pip check` passed.

| Item | Recorded environment |
|---|---|
| CPU | AMD Ryzen 7 5700G, 8 cores, 16 logical processors |
| Memory | 31.40 GiB visible, 14.81 GiB initially free |
| OS | Windows 11 Pro N, 10.0.26300, x64 |
| Python | CPython 3.14.4, MSC v.1944, AMD64 |
| Numerical libraries | NumPy 2.5.3, SciPy 1.18.1, IAPWS 1.5.5 |
| Other locked libraries | Matplotlib 3.11.2, pytest 9.1.1 |
| BLAS | OpenBLAS 0.3.34.106.0 for NumPy; 0.3.31.dev for SciPy |
| Threads | OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1, MKL_NUM_THREADS=1 |
| Power plan | Balanced; AC sleep disabled in the existing configuration |

Runtime BLAS inspection confirmed one thread in both loaded libraries.
Build 1.6.1, setuptools 84.2.1 and threadpoolctl 3.6.0 were confined to the measurement environment.
Browsers and desktop applications remained open. Initial host CPU load was
6%; mean host utilisation during the timed CLI runs ranged from 6.90% to
9.46%, including the evaluation. These are desktop-session measurements.

All runs were serial. `BORETHM_CACHE_DIR` selected external experiment
directories. Every measurement output was outside the checkout.

## Wall time and first use

Each entry is a fresh `borethm-evaluate --site KEY --json PATH` process,
including startup, evaluation, the text report and JSON export. There was
no profiler. Three rounds were run, with the second round in reverse site
order. The water-property disk cache was warm; Python processes were fresh.

| Site | Run 1 / 2 / 3 (s) | Median (s) | Range (s) |
|---|---|---|---|
| Soultz | 207.01 / 200.12 / 202.44 | 202.44 | 200.12–207.01 |
| Larderello | 78.94 / 78.23 / 78.21 | 78.23 | 78.21–78.94 |
| United Downs | 611.86 / 608.62 / 610.22 | 610.22 | 608.62–611.86 |
| Pannonian | 258.06 / 255.85 / 254.80 | 255.85 | 254.80–258.06 |
| Newberry | 30.30 / 30.42 / 30.03 | 30.30 | 30.03–30.42 |

| Empty-cache operation, measured once | Wall time (s) | Files written | Bytes |
|---|---:|---:|---:|
| borethm-water-table | 151.46 | 1 | 849,034 |
| First Soultz assessment, independent empty cache | 354.19 | 1 | 849,034 |

The cold assessment includes its own table construction. Both independently
constructed tables had SHA256
`88b6bdb033cca6b8224443cc21af350d113758ccbe83769ad4429155cb2596e0`.
The warm cache received a byte copy of the independently built table.
The operating-system file cache was not cleared. Cold-run repeatability
was not measured.

## Profiling method and stages

`cProfile` supplied function times and call counts. Selective
[`sys.monitoring`](https://docs.python.org/3.14/library/sys.monitoring.html)
events observed stage boundaries and solve arguments from outside the package.
No model function was replaced and no package source was instrumented.
The observer's nested-stage accounting and argument identity were checked
independently, and solve counts agree with cProfile for every site.

Profiles surround `site_evaluation.main` after imports and observer setup.
They include site selection, validation, evaluation, reporting and JSON.
The CLI default `circulation="v1.3.4"` selects the `_evaluate_v13` path.
Their durations are diagnostic: use the unprofiled table for wall-time
estimates. cProfile overhead can change relative shares, especially for
many short calls. Extra observer time ranged from 0.056 to 0.497 seconds.

Each interval is assigned to the innermost active named stage. Thus a
circulation solve called from the pipe/flow search is charged to the solve;
its time is excluded from the pipe/flow row. Wall-temperature and stability
work called by the cycle or whole-hole windows is charged to those deeper
stages. The remaining time in a parent is orchestration and its other work.
The columns sum to 100% before rounding. Observer callback time is excluded. Values below 0.005% round to 0.00%.

| Stage/function | Soultz | Larderello | United Downs | Pannonian | Newberry |
|---|---:|---:|---:|---:|---:|
| Fluid-loop orchestration (`drilling_fluid`) | 0.00% | 0.01% | 0.00% | 0.00% | 0.02% |
| Pipe and flow search (`choose_circulation`, `flow_for_go`) | 0.02% | 0.03% | 0.02% | 0.02% | 0.07% |
| Circulation (`model1_coupled.solve`) | 69.23% | 87.64% | 89.77% | 82.15% | 70.49% |
| Wall temperature (`wall_thermal` entry points) | 17.46% | 7.81% | 7.54% | 12.34% | 19.21% |
| Stability (`stability_inputs`, `_stability`, `_ref_depth`) | 1.47% | 0.40% | 0.29% | 0.60% | 1.06% |
| Connection/trip cycle (`site_cycle`, temperature profiles) | 0.40% | 0.49% | 0.12% | 0.29% | 0.69% |
| Whole-hole windows (`common_windows`) | 9.71% | 3.41% | 2.08% | 4.20% | 7.98% |
| Equipment (`tool_gates`, tool thermal model) | 1.69% | 0.15% | 0.16% | 0.36% | 0.37% |
| Report and export (`report`, `export_result`, `result_dict`, `reading`) | 0.01% | 0.04% | 0.00% | 0.02% | 0.05% |
| Other evaluation work | 0.01% | 0.03% | 0.01% | 0.01% | 0.07% |

`wall_thermal` entry points are `run`, `cooling_shape`, `cylinder_recovery`
and `line_source_recovery`. The connection/trip group also observes
`trip_temperatures`, `pause_temperatures` and `trip_profile`. Equipment
includes `tool_thermal.run` and `tool_thermal.trip_in`.

### Inclusive parent-function times

These are cumulative cProfile seconds, including child work. These rows
overlap and must not be added. They show the full cost and invocation count
of parent operations whose exclusive shares above may be small.

| Function | Soultz | Larderello | United Downs | Pannonian | Newberry |
|---|---:|---:|---:|---:|---:|
| `drilling_fluid` | 179.01 (1 calls) | 61.16 (1 calls) | 535.12 (1 calls) | 229.09 (1 calls) | 25.61 (1 calls) |
| `choose_circulation` | 177.67 (5 calls) | 87.95 (4 calls) | 707.55 (5 calls) | 264.39 (6 calls) | 27.90 (4 calls) |
| `site_cycle` | 7.45 (4 calls) | 1.50 (3 calls) | 8.88 (4 calls) | 6.66 (4 calls) | 1.92 (2 calls) |
| `common_windows` | 68.99 (12 calls) | 10.91 (9 calls) | 70.64 (12 calls) | 50.17 (12 calls) | 9.49 (6 calls) |
| `tool_gates` | 9.62 (4 calls) | 2.47 (3 calls) | 5.48 (4 calls) | 5.08 (4 calls) | 0.19 (2 calls) |

## Repeated circulation solves

A repeated call has the same complete bound arguments as an earlier call.
The comparison preserves scalar types, floating-point bits, array shapes,
dtypes and bytes, geometry, fluid state, callable code/defaults/closure
values, and any previous-solution seed. Module globals are the unchanged
baseline values. No rounding or callable evaluation is used to find matches.

| Site | Calls | Unique | Repeated | Profiled repeated time (s) | Share of accounted profile |
|---|---|---|---|---|---|
| Soultz | 76 | 52 | 24 | 67.461 | 25.62% |
| Larderello | 46 | 26 | 20 | 43.165 | 41.97% |
| United Downs | 302 | 202 | 100 | 241.690 | 30.51% |
| Pannonian | 88 | 57 | 31 | 91.252 | 27.98% |
| Newberry | 42 | 18 | 24 | 15.503 | 39.24% |

Repeated-call costs establish an upper bound on possible reuse savings. Callers
modify returned solution records, including previous-state and hydraulic
information. Reuse would need independent result records, complete keys and
checks for effects on later calls. No reuse was implemented.

## Water properties

The scalar water-property wrapper is `borethm.water_props.water`. Its LRU statistics below are read after the run, outside the
profiled scope. The cache has a maximum size of 200,000. It started empty
in each fresh process.

| Site | Scalar wrapper calls | LRU hits / misses / size | `water_table.props` calls | Interpolator calls | Lookup union (s) | IAPWS own time (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|
| soultz | 0 | 0 / 0 / 0 | 600,342 | 2,423,097 | 132.4143 | 0.1435 |
| larderello | 0 | 0 / 0 / 0 | 298,546 | 1,217,090 | 64.2438 | 0.0929 |
| united-downs | 0 | 0 / 0 / 0 | 2,342,778 | 9,397,707 | 506.6154 | 0.5497 |
| pannonian | 0 | 0 / 0 / 0 | 798,812 | 3,230,843 | 188.9763 | 0.1757 |
| newberry | 0 | 0 / 0 / 0 | 93,790 | 421,350 | 20.7552 | 0.0817 |

The lookup total adds cumulative time in the disjoint `water_table.props`
and `water_table.cp` wrappers and the interpolator's caller-edge time for
calls from outside `water_table`. Interpolator work already inside a
wrapper is excluded from that direct-call contribution. The caller records
are saved in each measurement. This is a library view overlapping the
stage view, so lookup time must not be added to the stage totals.

IAPWS own time is the sum of own time in functions defined by that library;
it does not double-count nested cumulative timings. Raw profiles retain
its individual functions and calls. First-use table construction was
measured separately in the first-use timings above.

## Memory

A separate unprofiled United Downs assessment reached a peak resident
working set of **122.82 MiB** (128,790,528 bytes), measured with the
OS-maintained `GetProcessMemoryInfo` peak. It includes the interpreter,
libraries and harness; startup is included in the process peak. Resident
memory immediately before evaluation was 76.89 MiB. No sampling thread or
profiler ran in this process. Its exported result matched the reference.

## A fixed-flow design-study trial

The measured trial is coating qualification at 300 °C, the existing `L5`
comparison in `borethm.studies.levers`, at Soultz and 40 L/s. Settings were
TK-Drakon coated pipe, a 4,000 m shoe, PV fraction 1.0, 0.02 SG allowance,
zero breakout formation delay and no imposed bottom-hole pressure.

The installed `levers.trial` function ran once in each fresh process, with
an explicit external output root. The existing broader CLI runs searches;
the external harness selected one existing trial directly. The flow came
from the baseline programme snapshot. No saved trial or rating-only
physics record was reused.

Unprofiled command wall time was **52.596 s**, including imports and setup.
The trial call took 51.400 s; its profiled counterpart took 69.378 s.

| Stage | Share of accounted study profile |
|---|---:|
| Fluid-loop orchestration | 0.04% |
| Pipe/flow selection remainder | 0.01% |
| Circulation solves | 12.08% |
| Wall temperature | 50.00% |
| Stability | 4.18% |
| Connection/trip cycle remainder | 1.14% |
| Whole-hole windows | 28.04% |
| Equipment checks | 4.42% |
| Report/export | 0.09% |
| Other | <0.005% |

There were 13 circulation solves, including two repeated argument sets.
The complete trial returned NO-GO in both runs. Exports match after excluding
only `elapsed_seconds` and `evidence`, the output-file path. The normal
Soultz assessment spends 69.23% on circulation, so this trial needs a
different optimisation priority. One trial does not describe every study.

## Pyodide under Node.js

The same unmodified wheel installed through micropip with IAPWS 1.5.5 and
Pyodide's own NumPy and SciPy. Installation resolved the declared dependencies.
No model code or solver settings were changed.

| Component | Pyodide environment |
|---|---|
| Node.js | 24.17.0 |
| Pyodide | 314.0.7 |
| Python | 3.14.2 |
| Target | wasm32, Emscripten 5.0.3, ABI 2026_0 |
| NumPy / SciPy | 2.4.6 / 1.18.0 |
| IAPWS / micropip | 1.5.5 / 0.11.1 |

The versioned assets were downloaded first and checked against available
upstream hashes. Runtime loading from local assets took 1.346 s; loading
NumPy, SciPy and micropip took 1.410 s; installing the two pure-Python
wheels took 0.399 s. These exclude network transfer and are single runs.

| Asset | Downloaded artifact bytes |
|---|---|
| numpy-2.4.6-cp314-cp314-pyemscripten_2026_0_wasm32.whl | 2,960,568 |
| scipy-1.18.0-cp314-cp314-pyemscripten_2026_0_wasm32.whl | 14,029,750 |
| micropip-0.11.1-py3-none-any.whl | 115,486 |
| iapws-1.5.5-py3-none-any.whl | 117,421 |
| pyodide-314.0.7.tgz | 6,488,647 |
| Total external artifacts | 23,711,872 |
| Baseline BoreTHM wheel, supplied locally | 877,280 |
| Warm water table, supplied locally | 849,034 |

External runtime artifacts total 22.61 MiB, plus
1.65 MiB of locally supplied package/cache data.
The npm archive contains the runtime in compressed form. Its size is not a
browser transfer measurement. The selected browser core files (module loader,
generated module, wasm, standard library and lock index), scientific wheels,
IAPWS, BoreTHM and water table total 32,480,746 file bytes
(30.98 MiB) before HTTP transport compression.
Registry metadata and npm tooling dependencies are excluded from these
runtime-asset totals. Actual browser transfer and first-visit latency were
not measured.

| Operation | Native Python (s) | Pyodide in Node (s) |
|---|---|---|
| Import borethm | 0.003630 | 0.007378 |
| Resolve load_site / validate_site APIs and their imports | 1.008507 | 2.357689 |
| load_site, packaged template | 0.007898 | 0.001072 |
| validate_site, packaged template | 0.002128 | 0.009615 |
| One recorded circulation solve | 0.709748 | 2.000968 |
| Newberry evaluation main, including report and JSON | 29.163 | 51.338 |

The package imports lazily, so the separate API-resolution row includes the
larger scientific imports. The template passed validation with no warnings.
For input checks, startup and asset delivery dominate the subsequent
millisecond-scale calls.

The solve used Soultz call index 14, the replayable call nearest the median
of all 76 recorded Soultz solve durations (0.993 s versus a 0.995 s median
under profiling). It uses water, 25 kg/s, 40 °C injection, the recorded
10,700 m geometry and geotherm, 160 initial nodes and friction heating.
Native reconstruction matched the original complete argument fingerprint
exactly. Both runtimes used the same warm water-table bytes.

Pyodide took 2.82 times the native solve time.
It converged in three iterations with 544 nodes; native Python used two
iterations and 508 nodes. NumPy/SciPy versions and platform builds differ,
and their individual effects have not been isolated in this environment comparison.
The delivered bit temperatures differed by 0.0000224 °C, the largest fluid
profile difference was 0.0001244 °C, and exported thermal power differed by
7.982 W (2.805e-6 relative). No numerical tolerance was changed.

The single solve suggested a full Newberry run would fit within 30 minutes,
so it was attempted. The measured evaluation-main comparison is
1.76 times native. Both scopes start after importing the evaluation
module and include reporting and JSON. The extra native result matched the
original native reference exactly. Pyodide retained GO and every categorical
assessment field. There were 151 differing numeric leaves, with a largest
relative difference of 2.048e-14, and four version-metadata differences:
Python, NumPy, SciPy and optional Matplotlib (absent in Pyodide).

The default `/home/pyodide/.cache/borethm` directory was writable in Node's
Pyodide memory filesystem. The measurements explicitly supplied a warm
table in another memory-filesystem directory. Persistence across page loads
was not tested. A browser helper would need an explicit table delivery or
cache-persistence design for evaluations. File upload/download, browser
workers, content-security policy and CORS were not tested. This was a Node
compatibility and timing experiment, with no browser application built.

The setup follows the official [Node usage](https://pyodide.org/en/stable/usage/index.html)
and [package-loading guidance](https://pyodide.org/en/314.0.7/usage/loading-packages.html).

## Opportunities ranked by measured eligible cost

The estimates below describe measured scope or explicit hypothetical
speed-ups. None is an achieved wall-time saving. Interpolation occurs inside
solves, so its opportunity overlaps repeated-solve reuse; the estimates
cannot be added. Profiler bias also limits projections onto unprofiled time.

| Priority | Candidate and kind | Evidence and conditional saving | Risk to saved results |
|---|---|---|---|
| 1 | Share interpolation setup across water properties; reuse or a focused compiled component | Lookup union consumes about 50–64% of profiled site time. `props` requests four properties at the same points. Halving the whole lookup slice would reduce profiled total cost by about 25–32%; no implementation has demonstrated this. | Changed interpolation arithmetic, clipping or rounding can change numbers. Preserve boundaries and operation semantics; verify all exports and physical regressions. |
| 2 | Reuse identical circulation calls within one assessment; repeated calls removed or cached | 20–100 repeated calls per site account for 25.62–41.97% of accounted profiles. This is an upper bound if all repeated cost could be avoided with negligible copy/cache cost. | Mutable solution dictionaries, continuation seeds and callable state require complete keys and independent returned records. Equality must be checked through the whole assessment. |
| 3 | Rework pressure-window work after locating its detailed loops; vectorisation or reuse | Exclusive whole-hole windows take 2.08–9.71% of normal site profiles and 28.04% of the study. Halving that slice would save 1.04–4.86% and 14.02%, respectively, in the measured profiles. | Case ordering, tied bounds and floating-point comparisons affect exported labels and decisions. No duplicate-window or vectorisable-loop saving has yet been measured. |
| 4 | Reduce wall-model Python loop/allocation overhead; vectorisation or a focused compiled loop | `wall_thermal.run` own time is 17.29 s for Soultz and 22.42 s for United Downs, about 6.6% and 2.8% of their profiles. It is 13.04 s, about 18.9%, in the study. Even eliminating all of that own time could save no more than those shares; the actual saving is unknown. | Time steps depend on previous steps. Preserve that order and the existing spatial discretisation; compiled arithmetic can alter rounding. The entire 50% study wall stage is not eligible Python overhead. |
| 5 | Change solver tolerances, node counts or wall discretisation; numerical settings | Circulation consumes 69.23–89.77% of ordinary assessments, but no alternative setting was measured, so no saving estimate is supported. | These change computed numbers. They require a separate calculation-change specification, physical regressions and release review. |

Batch and first-use opportunities have different scopes:

| Candidate and kind | Evidence and conditional saving | Risk / limitation |
|---|---|---|
| Run independent sites or trials in separate processes; parallel cases | The five native medians sum to 1,177.04 s. Five perfectly independent concurrent site jobs would have a 610.22 s lower bound from United Downs, a theoretical 48.2% batch wall-time reduction. No parallel run was measured. | Does not shorten one assessment. CPU/memory contention and shared cache/output writes need measurement and isolation. Existing single-thread settings were retained. |
| Retain or distribute a checked warm table; caching/reuse | Empty-cache table construction costs 151.46 s once. Cold Soultz exceeds its warm median by 151.75 s. Existing native disk caching already provides reuse. | A distributed browser asset needs provenance and invalidation. Download cost and persistent browser storage remain unmeasured. |

Report/JSON assembly is below 0.06% of ordinary site profiles. The scalar
water LRU is unused in this path. Neither is a useful priority for reducing
the measured evaluation times.

## What the measurements support

For current users, investigate repeated circulation calls and water-table
interpolation first. Their eligible costs are large enough to justify small,
separately verified experiments. Preserve a warm cache for repeat use.
No speed-up or calculation change was implemented here.

For a site-file helper, the package's own parser and validation work in
Pyodide and take milliseconds after startup. The scientific runtime adds a
substantial asset and import cost. A complete warm Newberry assessment was
feasible in Node, but only one site was timed in that runtime. Browser UX,
worker execution and numerical acceptance need separate work before making
a browser evaluation promise.

For a compiled core, the strongest ordinary-assessment candidate is the
water-property interpolation interface. The study also identifies wall-model
loop overhead as worth inspecting. SciPy and NumPy already execute compiled
code, so rewriting the entire application in Rust has no demonstrated saving.
This job did not measure streaming updates, live telemetry or a real-time
deadline; it cannot establish suitability for live drilling monitoring.

## Result preservation and evidence

All three native unprofiled exports match for each site. Cold and warm
Soultz match. Every profiled site export and the separate memory export
match the unprofiled reference, with no fields excluded. The study excludes
only elapsed time and its evidence path. Cross-runtime differences are
reported separately above and are not treated as exact equality.

The 426 protected source/evidence hashes still match the baseline,
and the checkout remains clean. Nothing under results, tests/golden or
benchmarks was written. Raw profiles, complete function rows, solve argument
records, JSON exports, environment records, download hashes and command logs
are retained in the external experiment folder. No package change,
optimisation, version change, tag or publication forms part of these results.

## Repeating the native measurements

The [profiling tool](../../tools/profile_evaluation.py) runs the native wall
timings, stage/function profiles and a separate peak-memory assessment for
the slowest selected site. It requires Python 3.12 or later for selective
execution events. The package's supported Python versions are unchanged.

Create and activate a fresh virtual environment outside the checkout.
Use Python 3.14.4 to repeat the recorded environment. From the repository
root, install the locked dependencies, build a wheel and install it without
editable mode:

```sh
python -m pip install -r requirements-lock.txt
python -m pip install build==1.6.1 threadpoolctl==3.6.0
python -m build --wheel --outdir ../borethm-profile-wheel
python -m pip install --force-reinstall --no-deps ../borethm-profile-wheel/borethm-1.5.0-py3-none-any.whl
python tools/profile_evaluation.py --output ../borethm-profile-run
```

Use the wheel filename produced by the checked-out version. The default
runs all five sites three times without a profiler, profiles each once and
measures peak memory separately for the site with the largest median.
It runs serially and sets the three BLAS thread variables to one before
imports. `--sites newberry soultz` selects a subset; `--repeats 1` provides
a shorter check. Timings from one repeat do not establish repeatability.

The output must be a new or empty directory outside the checkout. Its
`cache/` directory is warmed before timing; `--cache-dir PATH` can select an
existing external cache. Initial table construction can take several
minutes. The tool compares every repeat, profiled export and memory export
with the first unprofiled export, with no fields excluded, and verifies that
tracked model/evidence hashes remain unchanged.

`summary.md` and `summary.json` contain the comparison tables, environment,
commands and equality results. Each `profiles/SITE/` directory retains the
raw `evaluation.prof`, all function rows, both top-25 lists, stage shares
and solve argument fingerprints. `memory/SITE/` contains the separate
resident-peak record. The peak method is recorded: Windows process working
set counters, or `getrusage` on Linux/macOS. Other systems report the peak
as unavailable. Module globals are outside solve fingerprints, so matching
arguments remain a candidate for reuse investigation.

The study trial and Pyodide experiment above were separate measurements;
the native profiling tool does not rerun them.

## Appendix: top functions

Own time is time within a function excluding its children. Cumulative
time includes its children. Both sets below come directly from cProfile;
neither is a set of additive stage totals. File names and baseline line
numbers identify each function.

### Soultz: median-runtime site

#### Top 25 by cumulative time

| Function | Calls | Own time (s) | Cumulative time (s) |
|---|---:|---:|---:|
| `site_evaluation.py:2880 main` | 1 | 0.0001 | 263.8029 |
| `site_evaluation.py:905 evaluate` | 1 | 0.0000 | 263.7538 |
| `site_evaluation.py:2386 _evaluate_v13` | 1 | 0.0005 | 263.7501 |
| `site_evaluation.py:729 circulate` | 41 | 0.0006 | 182.3954 |
| `site_evaluation.py:746 solve` | 41 | 0.0565 | 182.3476 |
| `model1_coupled.py:207 solve` | 76 | 0.0202 | 182.2893 |
| `_bvp.py:711 solve_bvp` | 76 | 0.0699 | 181.0711 |
| `site_evaluation.py:2301 drilling_fluid` | 1 | 0.0011 | 179.0141 |
| `site_evaluation.py:1053 _evaluate_v12` | 4 | 0.0003 | 177.6802 |
| `site_evaluation.py:843 choose_circulation` | 5 | 0.0011 | 177.6664 |
| `_bvp.py:647 fun_p` | 14,970 | 0.0277 | 172.8124 |
| `model1_coupled.py:272 odes` | 14,970 | 1.3850 | 172.7811 |
| `model1_coupled.py:243 derivs` | 97,732 | 1.6040 | 170.8564 |
| `_bvp.py:347 solve_newton` | 509 | 0.1669 | 151.4209 |
| `model1_coupled.py:57 fluid_props` | 597,923 | 0.9795 | 145.1228 |
| `fluids.py:113 props` | 554,116 | 12.2885 | 135.1985 |
| `water_table.py:84 props` | 600,342 | 3.3835 | 131.3978 |
| `fluids.py:78 _water` | 556,535 | 0.4771 | 123.2706 |
| `_rgi.py:375 __call__` | 2,423,097 | 17.8401 | 116.5084 |
| `_bvp.py:276 collocation_fun` | 4,730 | 0.2232 | 106.2441 |
| `_bvp.py:322 col_fun` | 4,221 | 0.0035 | 95.5779 |
| `site_evaluation.py:1592 common_windows` | 12 | 0.1628 | 68.9901 |
| `model1_coupled.py:181 conductances` | 97,732 | 2.7563 | 61.2529 |
| `model1_coupled.py:74 h_dittus` | 202,828 | 3.5081 | 52.9271 |
| `_rgi.py:492 _prepare_xi` | 2,423,097 | 9.2786 | 52.5706 |

#### Top 25 by own time

| Function | Calls | Own time (s) | Cumulative time (s) |
|---|---:|---:|---:|
| `_rgi.py:635 _find_out_of_bounds` | 2,423,097 | 25.2886 | 26.2372 |
| `_rgi.py:632 _find_indices` | 2,423,097 | 19.4189 | 28.2582 |
| `_rgi.py:375 __call__` | 2,423,097 | 17.8401 | 116.5084 |
| `wall_thermal.py:112 run` | 2,048 | 17.2919 | 45.9751 |
| `_linalg.py:374 solve` | 203,288 | 15.0359 | 16.6267 |
| `well_geometry.py:237 tvd` | 2,822,059 | 14.7705 | 21.8271 |
| `<method 'reduce' of 'numpy.ufunc' objects>` | 5,438,939 | 13.1978 | 13.1978 |
| `fluids.py:113 props` | 554,116 | 12.2885 | 135.1985 |
| `_rgi.py:492 _prepare_xi` | 2,423,097 | 9.2786 | 52.5706 |
| `numeric.py:97 zeros_like` | 2,423,097 | 7.0122 | 8.2707 |
| `fromnumeric.py:86 _wrapreduction_any_all` | 4,865,009 | 5.7809 | 19.2998 |
| `_methods.py:96 _clip` | 1,972,150 | 4.6878 | 5.5169 |
| `_function_base_impl.py:1549 interp` | 5,301,298 | 4.3877 | 10.4824 |
| `<built-in method numpy.array>` | 5,872,740 | 4.1092 | 5.4741 |
| `model1_coupled.py:74 h_dittus` | 202,828 | 3.5081 | 52.9271 |
| `<built-in method numpy._core._multiarray_umath.interp>` | 5,301,298 | 3.4967 | 3.4967 |
| `water_table.py:84 props` | 600,342 | 3.3835 | 131.3978 |
| `fromnumeric.py:2474 any` | 4,861,972 | 3.0107 | 22.3008 |
| `water_table.py:78 _clip` | 601,275 | 2.9015 | 12.3934 |
| `_aliases.py:70 asarray` | 3,322,211 | 2.8388 | 9.2759 |
| `model1_coupled.py:181 conductances` | 97,732 | 2.7563 | 61.2529 |
| `well_geometry.py:297 at` | 200,825 | 2.7012 | 11.4132 |
| `_shape_base_impl.py:607 column_stack` | 622,071 | 2.5720 | 3.3901 |
| `<method 'reshape' of 'numpy.ndarray' objects>` | 4,881,360 | 2.5691 | 2.5691 |
| `<built-in method numpy.asarray>` | 14,405,130 | 2.5535 | 2.5535 |

### United Downs: slowest site

#### Top 25 by cumulative time

| Function | Calls | Own time (s) | Cumulative time (s) |
|---|---:|---:|---:|
| `site_evaluation.py:2880 main` | 1 | 0.0001 | 792.6420 |
| `site_evaluation.py:905 evaluate` | 1 | 0.0000 | 792.5751 |
| `site_evaluation.py:2386 _evaluate_v13` | 1 | 0.0012 | 792.5713 |
| `site_evaluation.py:729 circulate` | 155 | 0.0022 | 711.5323 |
| `site_evaluation.py:746 solve` | 155 | 0.2137 | 711.3475 |
| `model1_coupled.py:207 solve` | 302 | 0.0759 | 711.1272 |
| `site_evaluation.py:1053 _evaluate_v12` | 4 | 0.0003 | 707.5572 |
| `site_evaluation.py:843 choose_circulation` | 5 | 0.0051 | 707.5466 |
| `_bvp.py:711 solve_bvp` | 302 | 0.2375 | 706.5825 |
| `_bvp.py:647 fun_p` | 55,384 | 0.0996 | 676.3202 |
| `model1_coupled.py:272 odes` | 55,384 | 5.4784 | 676.2078 |
| `model1_coupled.py:243 derivs` | 381,360 | 6.1439 | 668.6782 |
| `_bvp.py:347 solve_newton` | 1,932 | 0.6802 | 590.5379 |
| `model1_coupled.py:57 fluid_props` | 2,340,739 | 3.9531 | 562.2326 |
| `fluids.py:113 props` | 2,286,656 | 49.4735 | 546.8068 |
| `site_evaluation.py:2301 drilling_fluid` | 1 | 0.0025 | 535.1192 |
| `water_table.py:84 props` | 2,342,778 | 12.5947 | 505.3841 |
| `fluids.py:78 _water` | 2,288,695 | 1.9573 | 497.2496 |
| `_rgi.py:375 __call__` | 9,397,707 | 68.7128 | 445.6017 |
| `_bvp.py:276 collocation_fun` | 17,503 | 0.8896 | 418.2871 |
| `_bvp.py:322 col_fun` | 15,571 | 0.0136 | 375.5615 |
| `model1_coupled.py:181 conductances` | 381,360 | 10.4228 | 236.5617 |
| `model1_coupled.py:344 _friction_gradient` | 762,720 | 6.9722 | 203.5135 |
| `_rgi.py:492 _prepare_xi` | 9,397,707 | 35.3175 | 198.7278 |
| `model1_coupled.py:74 h_dittus` | 765,504 | 12.6021 | 198.2046 |

#### Top 25 by own time

| Function | Calls | Own time (s) | Cumulative time (s) |
|---|---:|---:|---:|
| `_rgi.py:635 _find_out_of_bounds` | 9,397,707 | 97.5416 | 100.9399 |
| `_rgi.py:632 _find_indices` | 9,397,707 | 75.1635 | 109.1838 |
| `_rgi.py:375 __call__` | 9,397,707 | 68.7128 | 445.6017 |
| `fluids.py:113 props` | 2,286,656 | 49.4735 | 546.8068 |
| `<method 'reduce' of 'numpy.ufunc' objects>` | 19,744,217 | 47.0015 | 47.0015 |
| `_rgi.py:492 _prepare_xi` | 9,397,707 | 35.3175 | 198.7278 |
| `numeric.py:97 zeros_like` | 9,397,707 | 27.0470 | 31.8690 |
| `wall_thermal.py:112 run` | 2,644 | 22.4168 | 59.7706 |
| `fromnumeric.py:86 _wrapreduction_any_all` | 18,816,576 | 22.2438 | 71.5356 |
| `well_geometry.py:237 tvd` | 3,026,838 | 20.3769 | 29.9437 |
| `_linalg.py:374 solve` | 264,695 | 19.7326 | 21.8110 |
| `_methods.py:96 _clip` | 7,035,534 | 16.9955 | 20.1703 |
| `<built-in method numpy.array>` | 19,013,126 | 12.8129 | 17.2678 |
| `model1_coupled.py:74 h_dittus` | 765,504 | 12.6021 | 198.2046 |
| `water_table.py:84 props` | 2,342,778 | 12.5947 | 505.3841 |
| `fromnumeric.py:2474 any` | 18,804,988 | 11.4065 | 82.9051 |
| `water_table.py:78 _clip` | 2,343,925 | 11.0167 | 47.9689 |
| `model1_coupled.py:181 conductances` | 381,360 | 10.4228 | 236.5617 |
| `well_geometry.py:297 at` | 766,406 | 10.3138 | 43.8009 |
| `<method 'reshape' of 'numpy.ndarray' objects>` | 18,848,510 | 9.9029 | 9.9029 |
| `_shape_base_impl.py:607 column_stack` | 2,369,373 | 9.7576 | 12.9006 |
| `_aliases.py:70 asarray` | 10,592,923 | 9.4121 | 30.6049 |
| `model1_coupled.py:329 friction_factor` | 762,756 | 8.3389 | 8.5794 |
| `comparative_sites.py:33 gt` | 503,998 | 7.8402 | 20.5017 |
| `<built-in method numpy.zeros>` | 20,190,085 | 7.2564 | 7.2564 |
