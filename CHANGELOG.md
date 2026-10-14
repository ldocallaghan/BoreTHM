# Changelog

## v1.3.5 (14 October 2026)

The project is renamed BoreTHM, and the package `borethm`. The README is rewritten as a guide to the project, and the documentation is reorganised under `docs/` into guides, scientific pages, maintenance notes and an archive of the v1.3.4 reviews. The two-page summary (`docs/guides/summary.md`, with a PDF in `output/pdf/`) is rewritten. It sets the open target drilling intervals in eight of nine Soultz cases and two of four United Downs cases beside the failures of the complete programme; both sites remain NO-GO.

The code licence changes from MIT to Apache 2.0, which adds an explicit patent grant. Documentation, figures, results and the summary PDF are licensed under CC BY 4.0. Data keep their source licences, listed in `NOTICE`. Releases up to v1.3.4 remain under MIT.

The calculation, its inputs and the reference results are those of v1.3.4.

## v1.3.4: NO-GO for this programme and these assumptions at the deep sites (12 October 2026)

The confirmed mixture, fluid-feedback and depth-coverage errors are corrected. Each verdict belongs to the stated programme and assumptions. No evaluated design lever or permitted pair reopens either deep site; no full-site minimum or complete operating envelope is established.

| Site | v1.3.3 | v1.3.4 | Required / simulated drilling SG | Required / simulated trip SG | Reason |
|---|---|---|---|---|---|
| Soultz | NO-GO | NO-GO | 1.378925 / 1.378840 | 1.443624 / 1.443545 | conserved hot mud lowers column pressure; whole-hole feedback and target coverage retain closed windows; run-in fails |
| United Downs | NO-GO | NO-GO | 1.331318 / 1.331733 | 1.401337 / 1.401158 | corrected trip pressure and target coverage retain closed windows; the bit remains above 200 °C |
| Larderello | CONDITIONAL | CONDITIONAL | 1.036244 / 1.036329 | 1.094193 / 1.094057 | shallow prescription now supplies the simulated fluid, hydraulics and tools; target metadata is 2,400 m |
| Pannonian | INDETERMINATE | NO-GO | 1.458734 / 1.459278 | 1.544787 / 1.545152 | corrected all-depth windows are closed; coating qualification remains unknown |
| Newberry | GO | GO | 0.998201 / 0.998201 | 0.998201 / 0.998201 | water satisfies the corrected common windows and all evaluated gates |

Weights are surface densities at 20 °C. Closed windows have no valid prescription, even when an attempted lower-bound weight is simulated. The complete before-and-after bounds, controlling cases and isolated C1 pressure changes are in `docs/archive/v1.3.4/checkpoint-1.md`.

- **Conserved composition, C1.** Mud density uses component volumes at fixed barite mass fraction, conductivity uses the local volume fraction and heat capacity uses mass fractions. The historical adapter retains the prior mixture law. Independent component-volume tests and the four-state table check the correction.
- **Prescribed fluid and depth coverage, C2 to C4.** Every fluid pass reruns the whole-hole requirement through circulation, hydraulics, drilling rate and tools. The heavier trip fluid occupies the column from trip start. Every depth has its own exposure check; the target and final stand are included. Binding bounds are refined twice. Public entry points validate inputs and export the effective target, retaining the former input as legacy metadata.
- **Robustness, C5.** `docs/science/approximation-comparisons.md` records A1 to A9. NO-GO holds for this programme across those comparisons at both deep sites. Pannonian's historical 0.041 °C tool margin is numerically unresolved; the corrected closer schedule has more tool margin but closed pressure windows.
- **Design levers, C6.** `docs/science/design-comparisons.md` records L1 to L8 and one pair per site. Coating-only thresholds and Soultz's bit-only flow boundary are checked at half tolerance. Unknown equipment qualification and numerical failures stay explicit. Near-threshold Soultz casing results trigger a follow-up on the common event timeline.
- **Release and reproduction, C7.** The README and summary lead with the corrected programme, levers and open cooling question. Python API and command-line defaults select v1.3.4; historical regression modes remain explicit. Citation and package metadata advance to 1.3.4. Reviewed reference and lever tables are generated in CI, with their bracketing evidence; earlier golden files remain unchanged.

## v1.3.3: one consistent operating programme (October 2026)

Every part of an evaluation now works from the same operating programme:
one pressure budget for the wall in every state, a weighted drilling fluid
coupled to the circulation it sets, the tools and the coating through the
cycle, one fluid for every case down the hole, and a status for each part.
The two well-characterised sites become NO-GO in their worst case.

| Site | v1.3.2 | v1.3.3 | Drilling fluid (limit while circulating), SG | Trip fluid at end and start (limit at start), SG | Safe pause | Margin | Reason |
|---|---|---|---|---|---|---|---|
| Soultz | CONDITIONAL | NO-GO | 1.31 (1.34) to 1.31 (1.30) | 1.30 (1.37) to 1.32 and 1.35 (1.35) | 47 to 23 h | Shmin 3.1% at friction 1.0 to already closed | the mud's friction lowers the circulating limit; the column heats through the trip |
| United Downs | CONDITIONAL | NO-GO | 1.26 (1.29) to 1.27 (1.22) | 1.27 (1.32) to 1.28 and 1.31 (1.30) | 35 to 19 h | 2.2% to already closed | as Soultz; and the bit at 206 C with the mud |
| Pannonian Basin | CONDITIONAL | INDETERMINATE | 1.42 (2.48) to 1.40 (2.43) | 1.39 (2.50) to 1.41 and 1.45 (2.48) | 77 to 17 h | 12.9% to 9.5% | the coating above its rating running in; no one fluid suits every stress case |
| Larderello | GO | CONDITIONAL | water (1.32) to water (1.32) | water | more than a week | none within 20% | water too light for the rock just drilled at 1.5 km: 1.04 SG drilling and 1.09 SG trip fluid |
| Newberry | GO | GO | water (1.34) | water | more than a week to 74 h | 15.2% to 18.3% | the column heats through the pause |

The flow ceilings of 70 kg/s at Soultz and 60 kg/s at United Downs are no
longer reported, as both sites are NO-GO at the flow used. Water's column is
now 0.94 to 0.98 SG at the targets, against the 1.02 SG of the constant
10 MPa/km gradient used before.

- **One pressure budget** (`pressure.py`). The pressure on the wall in each
  state is the wellhead pressure, the fluid column integrated at its
  temperature in that state, the annular friction while circulating and an
  allowance of 0.02 SG for surge and swab on each bound through a trip (an
  assumption). The annulus is open at atmospheric pressure, with
  backpressure only if the return would boil, which it does at no site;
  Model 1's loop operating pressure of 5 MPa is kept only for the surface
  heat product. While drilling and through a connection the column has
  Model 1's annulus temperatures, and at the end of a trip the open hole has
  the static fluid's temperature at depths no more than 250 m apart. The
  water columns reproduce the review's figures within 0.001 SG. Every SG is
  an equivalent static density at the target.
- **A weighted drilling fluid** (`fluids.py`). A barite-weighted water-based
  mud, its water following IAPWS-95 and its barite expanding only
  thermally, with Bingham rheology from Anawe and Folayan (2018) and the
  pressure losses of Bourgoyne et al. (1986). The weight is iterated with the
  circulation, hydraulics and budget it sets, to 0.002 SG, in three passes at
  each site that needs it. Flows are volumes at surface. The mud's plastic
  viscosity, about thirty times water's at the bottom of the hole, triples
  the circulating friction at the deep sites (0.07 to 0.10 SG); halving it is
  a sensitivity, and it does not open the window. The circulating
  temperature at the bit exceeds 150 C at the deep sites, where conventional
  water-based muds start to break down, and is flagged.
- **The tool and the coating through the cycle** (`tool_thermal.py`). The
  bottom-hole assembly is lumped into the steel of the collars and the fluid
  inside them, the tool. It is checked while drilling, through the
  connection on fresh rock and running back in through the column at the
  end of the trip. Above 200 C the circulation schedule is searched;
  Soultz needs staging every 36 m on the way in (about 70% of the time
  circulating), and United Downs fails, at 206 C at the bit while drilling.
  The deepest coated pipe exceeds TK-Drakon's 204 C rating on the way in at
  the three deep sites, which makes the status INDETERMINATE where nothing
  else fails. A schedule counts as found however much it circulates, and
  the coating's time above its rating on the way in is overstated, since
  staging is taken to cool the string's fluid and not the column.
- **The safe pause** lets the column heat through the pause, which shortens
  it at every site but Larderello, where it stays above a week.
- **Common windows.** For every case and state, the range of the fluid's
  density at surface that holds the wall and stays below the fracture limit
  is found at every 100 m from the bottom to the casing shoe, each depth with
  its own history, and the prescription is the fluid within every range,
  with the bound, state, case and depth that bind it. The upper bounds bind
  at the casing shoe at Soultz and in the Pannonian Basin. The site verdict
  is unchanged in meaning; the prescription is a separate result.
- **Statuses.** Every evaluation carries a status for the solver, the tool,
  the coating, hole cleaning, the pumps, the frictional admissibility of each
  case and stability in each state. The label is INDETERMINATE when a run did
  not converge, whatever else the evaluation says, or when only the coating
  is above its rating; NO-GO with the failing parts; CONDITIONAL with its
  conditions, among them the prescription where it is heavier than water or
  empty; or GO. The searches over flow reject runs that did not converge.
- **Outputs.** `report()` and `verdict_lines()` print from the result, with
  no fixed narrative. `export_result()` writes the same result as JSON with
  the versions behind it, and `python src/site_evaluation.py --site <name>
  --json <path>` runs one site.
- **New sites.** `examples/site_template.py` documents every input with its
  units, range and source; `validate_site()` checks them; `examples/new_site.py`
  rebuilds Soultz from the template and reproduces its row; `docs/guides/new-site.md`
  is the guide, and `docs/guides/summary.md` a two-page summary for readers.
- **Tests and reproducibility.** The v1.3.3 site table is pinned from a
  golden made in the continuous integration, which runs the fast tests on
  every push and the slow suite weekly and on demand, on Python 3.14.4 and the
  lock file's versions; a minimal `pyproject.toml` records the package. A test
  checks that the wall solver's early minutes converge at the breakout's
  reference depth: within 0.7 K at the end of a connection, and within 1.3 K
  after the first 20 seconds. The v1.2 and v1.3 tables stay pinned, and
  `evaluate(circulation="v1.3")` reproduces v1.3.2.
- **Housekeeping.** `data/materials.md` no longer says the site runs choose
  the dual-wall pipe. The README gives the operating programme, the
  assumption and the heuristic behind the verdict at exposure, and the
  limitations this version adds.

- **Coupling.** Model 3 now takes the coolant temperature at the face from
  the site's own circulation, where it used its own scalar-gradient Model 1;
  the rate of penetration and the wall's exposure are iterated to a fixed
  point (2%, at most ten passes; one or two at every site); the thermal
  stress takes the site's E_rock scaled by Model 2's temperature factor, where
  it used the generic 50 GPa; and switching the thermal stress off now
  reaches every state of the cycle. Rerun on the v1.3.2 table with nothing
  else changed, no verdict moves. At Soultz the coolant at the face is 184 C
  against the 135 C Model 3's own run gave, so the rate of penetration falls
  from 4.3 to 3.9 m/h; at the other deep sites it is 3.8 to 3.9 m/h. The rock is
  then circulated against for longer before each trip, the reference rock
  is 1 to 2 C cooler through connections and trips, the trip fluid is up to
  0.005 SG lighter, and the safe pause is longer (Soultz 47 to 55 h, United
  Downs 35 to 37 h, Pannonian 77 to 82 h). The site stiffness raises the
  thermal stress at United Downs (60 GPa) and Soultz (55 GPa), which shows
  only where the wall is cooled: with the one-hour formation allowance the
  drilling fluid is 1.155 SG at Soultz (1.169) and 1.117 at United Downs
  (1.142). At United Downs the flow ceiling rises from 60 to 70 kg/s and the
  Shmin margin at friction 1.0 from 2.2 to 2.6% (SHmax held) and 4.6 to 5.8%
  (scaled). Larderello does not change.
- **The FORGE trip test.** The pinned results came from a Model 1 solve that
  had not converged: the circulation before the 13.5-hour trip of 27 May
  (BHA13 at 9,600 ft, 675 gal/min) failed from all four starting profiles,
  and the last unconverged attempt, with 385 C at the bit, was used. What an
  unconverged solve returns depends on floating-point detail, so the check
  gave different results on different machines: the no-node factor was 0.357
  here and 0.391 for the reviewers, and the continuous integration passed
  and failed the same code on different runners. v1.3.2 put the difference
  down to the Python version, which was wrong. Two more starting profiles
  are tried after the four, and from them the solve converges to 106 C at the
  bit, in agreement with the neighbouring flows and depths; the check now
  refuses an unconverged circulation. The repinned factors are 0.555 (0.549
  before) and 0.391 without the fluid node (0.357), the misfit 12.4 and
  13.3 F (12.8 and 16.3), and the 13.5-hour trip's modelled anomaly falls
  from 12.3 to 8.4 F. The Pason times are now read as UTC, so that the
  pinned epochs do not depend on the machine's time zone.

## v1.3.2: the margins on the window (October 2026)

Additions from a review of v1.3.1. No verdict changes.

- **Shmin margin.** For each site, Shmin is reduced in every stress case, with
  SHmax held and with SHmax scaled with it, until the window over the cycle
  closes. The frictional cap on SHmax below the data couples the two: at the
  friction coefficient of 0.8 the worst cases at Soultz and United Downs lie
  within a few MPa of the cap, so a lower Shmin pulls SHmax down and the
  window stays open (none within 20% at Soultz; 19% at United Downs, in a
  stress state needing friction 1.55). With the cap at 1.0, SHmax can stay on
  its trend, and the window closes for a fall of 3.1% at Soultz and 2.2% at
  United Downs (friction at least 0.87 and 0.84), or 6.6% and 4.6% with SHmax
  scaled. The review's estimate of about 2% assumed SHmax held without the
  cap. Both sets are reported, with the friction each closure needs. The
  response is not monotonic, because at large reductions the cap binds even
  at 1.0, so the reductions are scanned and the first closure refined.
- **Flow ceiling.** For each site, the highest flow from the one used at which
  the verdict over the cycle holds: 70 kg/s at Soultz and 60 kg/s at United
  Downs, both within three 14-P-220 pumps; the pump limit elsewhere. The
  circulating table no longer gives a flow for GO, which over the cycle read
  as a target past the ceiling.
- **Drilling-state label.** When a connection sets a fluid heavier than water,
  the drilling state of that case is CONDITIONAL. The site verdict is
  unaffected.
- **README.** The opening states the margin and points to the trip fluid up
  the open hole (Fig. 8); the cycle table gives the flow range; Section 5
  discusses the Shmin margin.
- **The FORGE trip test.** The reviewer's environment runs Python 3.11
  against 3.14 in the lock file, which accounts for the difference in the
  no-node fit factor.

## v1.3.1: the wall is held by fluid weight (October 2026)

Corrections from a review of v1.3. No base verdict changes; the README is
reframed around the v1.3 result.

- **Connection on freshly drilled rock.** The rock the bit has just drilled is
  circulated against only until the pumps stop, then sits through the
  connection at static pressure. From the 10-second Pason record over the
  whole well (303 connections), that circulation is 20 s at the 10th
  percentile and 1 min at the median; the base case uses the 10th percentile,
  the median is a sensitivity. The connection durations now come from the same
  record: 2.8 min at the median and 6.3 min at the 90th percentile, against
  2.0 and 5.0 min from the 1-minute record over the trial week. The review
  found United Downs without a window here; that comparison added the
  circulating friction to the requirement and also took it off the limit. With
  it counted once, United Downs needs 1.26 SG against 1.29.
- **Drilling fluid against the limit while circulating.** When a connection
  sets the drilling fluid, the fluid is now also checked against the fracture
  limit less the circulating friction. At the highest flow within the pump
  limit, both well-characterised sites become NO-GO in their worst case, so a
  higher flow narrows the window over the cycle.
- **The one-hour formation allowance** now applies to the fresh-rock
  connection as well as to drilling, since both fall within that hour.
- **Full stress field in the first minutes.** The site output reports the
  failed depth from the full stress field after 0 to 10 minutes of cooling
  against the uncooled depth: the cooled skin pushes it from 1.9 to 2.1 cm at
  Soultz after a minute, and below the uncooled depth within 5 minutes.
- **When breakouts form.** Moore et al. (2011) imaged breakouts at the bit
  minutes after drilling, widening over 30 minutes to 3 days; Wenning et al.
  (2017) logged breakout growth over more than a year in crystalline rock in
  the COSC-1 borehole. The README cites both: the one-hour allowance is a
  sensitivity the data do not support, and later growth is unmodelled.
- **README.** Section 5 leads with the verdicts over the cycle; the
  assessment while circulating is kept for comparison. The opening, Section 1
  and Section 3.2 say that the wall is held by fluid weight and that cooling
  serves the tools and slows creep. The comparison with FORGE 16B's trips is
  described as too coarse to confirm or reject the reheating model. The narrow
  windows are stated. Fig. 8 adds the trip fluid needed up the open hole.
- **The FORGE trip test.** The review reported a no-node fit factor of 0.391
  against 0.357 pinned, with numpy 2.4.4 and scipy 1.17.1. Those versions
  reproduce the pinned values exactly here, so the difference has another
  cause, and the tolerance is unchanged.

### Verdicts, v1.3 → v1.3.1 (target 400 °C)

| Site | Verdict | Drilling fluid (limit) | Trip fluid (limit) |
|---|---|---|---|
| Upper Rhine / Soultz | CONDITIONAL, unchanged | 1.31 SG (1.34), unchanged | 1.30 SG (1.37) |
| United Downs | CONDITIONAL, unchanged | 1.25 → 1.26 SG (1.29) | 1.27 SG (1.32) |
| Larderello | GO | water | water |
| Pannonian Basin | CONDITIONAL, unchanged | 1.42 SG (2.48) | 1.39 SG (2.50) |
| Newberry | GO | water | water |

## v1.3: the wall through the drilling cycle (October 2026)

The verdicts now follow the borehole wall through a bit run and the trip that
ends it, with the rock behind the wall resolved in temperature and stress.

### Wall temperature through the cycle

- **Transient wall model** (`wall_thermal.py`). Implicit finite volumes for
  radial conduction on a log-spaced grid. While circulating, the wall exchanges
  heat with the annulus at Model 1's temperature and film coefficient. With
  the pumps off, the fluid in the hole is one well-mixed volume coupled to the
  wall by the laminar film (Nu 4.36); the case with no fluid is a sensitivity.
  The solver is checked against the constant-temperature cylinder (Carslaw and
  Jaeger, 1959) to within 1.2% and the recovery after constant heat flow to
  within 2%, by numerical Laplace inversion (Abate and Valkó, 2004), and for
  grid convergence and energy conservation. The line source (Bullard, 1947)
  differs from the cylinder by 6 to 13% over the times of interest and is
  reported for comparison only.
- **Cycle timings from FORGE 16B** (`drilling_cycle.py`), from the Pason
  1-minute record and the daily reports: trips at 1,694 ft/h out and 1,833 ft/h
  in, 3.9 h of routine surface time, connections of 2.0 min (median) and
  5.0 min (90th percentile), 94 ft stands. The first trip in the record began
  on 21 May.
- **Check against FORGE 16B's trips** (`validate_forge_pauses.py`). The return
  temperature over the first bottoms-up after each of the five trips is
  compared with a plug-flow column of the modelled fluid temperatures, scaled
  by one factor fitted on four trips and used to predict the fifth in turn:
  0.55, with a misfit of 13 °F against anomalies of −10 to +38 °F (16 °F with
  no fluid in the hole). The comparison was first planned at the bottom of the
  hole alone, which the returns cannot resolve, and on the pauses with the bit
  on bottom, most of which were surveys or reduced-flow circulation; both were
  dropped. Five trips through a plug-flow column are weak evidence.

### Failure behind the wall

- **Stresses in the rock** (`model5_convergence_confinement.py`): the Kirsch
  field with wellbore pressure (Jaeger et al., 2007) and the plane-strain
  thermal stresses of the temperature field (Timoshenko and Goodier, 1970),
  with Mohr-Coulomb at the local temperature.
- **Width judged at the wall, with the temperature of the rock behind it.**
  In elastic Mohr-Coulomb the failed region reaches wider just behind the wall
  than at the wall, so the extent of failure in the rock is not a breakout
  width. The width is judged at the wall, with the temperature of the rock at
  the depth the uncooled breakout reaches (about 3 cm at Soultz). This replaces
  the planned measure, the extent of failure at any radius.
- **Recalibration.** UD-1's weak-zone strength becomes 119 to 147 MPa (from
  118 to 147), with the intact bound unchanged. Soultz widths at 5 km rise by
  up to 3°, with every window still open. Newberry's volcanics are matched at
  25 to 40 K of cooling; the granodiorite is still not reproduced.

### Verdicts over the cycle

- **Drilling, connection and trip.** Each case of stress and strength is
  checked while drilling (circulating pressure), after a 90th-percentile
  connection and at the end of a trip (static pressure). Drilling is judged as
  the bit exposes the rock: elastic failure is immediate, and the rock at the
  breakout's depth is then still at formation temperature. The drilling fluid
  is the lightest static weight that holds the wall while drilling and through
  a connection; the safe pause is how long the wall holds at that weight with
  the pumps off; the trip fluid is what the wall needs at the end of the trip.
  A one-hour allowance for breakouts to form is a sensitivity.
- **Sensitivities:** half and double trip time, no fluid in the hole, the
  dual-wall pipe, the highest flow within the pump limit, and the trip
  verdict up the open hole.
- **Rig capacity.** The flow for GO is compared with three pumps of the rating
  of NOV's 14-P-220 triplex pump (1,980 hydraulic hp, up to 1,215 gal/min); all
  three sites' flows are within it.

### Verdicts, v1.2.2 → v1.3 (target 400 °C)

| Site | v1.2.2, while circulating | v1.3, over the cycle | Drilling fluid | Trip fluid (limit) |
|---|---|---|---|---|
| Upper Rhine / Soultz | CONDITIONAL, 1.07 SG | CONDITIONAL | 1.31 SG | 1.30 SG (1.37) |
| United Downs | CONDITIONAL, 1.07 SG | CONDITIONAL | 1.25 SG | 1.27 SG (1.32) |
| Larderello | GO | GO | water | water (1.33) |
| Pannonian Basin | CONDITIONAL, 1.06 SG | CONDITIONAL | 1.42 SG | 1.39 SG (2.50) |
| Newberry | GO | GO | water | water (1.36) |

No verdict changes, but the weights do. The drilling fluid rises because the
wall is judged as the bit exposes it, before circulation has cooled the rock
the breakout grows into, so it is close to the uncooled weight; with a
one-hour allowance it would be 1.14 SG at Soultz and 1.12 SG at United Downs.
At Soultz that weight holds the hole through a 44-hour trip; at United Downs
it holds for 23 hours, and the fluid must be raised to 1.27 SG for a 52-hour
trip. The v1.2.2 table, while circulating, is kept unchanged as a column of
the site table.

### Other

- New figures show the trip check (Fig. 3), the failure margin around the hole
  at Soultz (Fig. 6) and the wall at Soultz through a bit run and a trip
  (Fig. 8). The Soultz dashboard shows the fluid weights through the cycle.
- README: the reheating check, the stresses behind the wall, the cycle table,
  and limitations for thermo-poroelastic effects (Ghassemi et al., 2009), surge
  and swab, bit life, the single source of cycle timings and the time
  breakouts take to form.
- The v1.2.2 site table is pinned with the circulation model of v1.2; the
  v1.3 table is pinned alongside it.

## v1.2.2: the verdicts hold while circulating (October 2026)

Corrections from a review of v1.2.1. No verdict changes.

- **Trips.** v1.2.1 checked the breakout bound at static fluid weight, citing
  connections and trips, but with the circulating wall temperature. That
  pairing holds for a connection, minutes with the wall still cool, but not
  for a trip: at 11 to 13 km a bit change takes the bottom of the hole out of
  circulation for a day or more, and the wall loses most of its cooling. The
  README and the code now say that the cooled verdicts hold while circulating
  and that the uncooled sensitivity is the guide to a trip. Modelling the
  reheating over the drilling cycle, with the mitigations it allows, is left
  for v1.3.
- **Flow for GO** now requires every case to be within the frictional cap,
  not only the worst-verdict case. No result changes.
- **README.** The opening carries the rig-capacity caveat on higher flows.
- **Fig. 6.** The site names on the right panel no longer run together.

## v1.2.1: commercial pipe as the base case (October 2026)

Corrections from a review of v1.2.

- **The site verdicts now use pipe that can be bought.** v1.2 tried pipe types
  from best insulated to worst and picked the dual-wall pipe, which exists
  only in a modelling study. The base case is now the best-insulated pipe that
  is commercially available, TK-Drakōn coated pipe; dual-wall pipe and
  vacuum-insulated tubing are sensitivities.
- **Flow for GO.** For each site the table also gives the lowest flow at which
  the same pipe gives GO within the pump limit, with its standpipe pressure,
  flagged where it exceeds the 700 gal/min at which FORGE 16B was drilled.
- **Circulating pressure on the fracture bound.** The annular friction loss,
  as an equivalent density (0.02 to 0.04 SG at the sites), is added to the
  fluid weight on the upper bound of the window. The breakout bound stays at
  static fluid weight, which the wall sees whenever circulation stops. The
  static check on both bounds is a sensitivity.
- **Solver seeds.** A solve with a depth-varying exposure that fails from one
  starting profile is retried from others. Where it converges the answer is
  the same to within 0.01 °C; before, which FORGE samples failed, and so
  dropped out of a run mean, depended on library versions, and one slow test
  failed on another machine. `requirements-lock.txt` records the versions the
  reference results were made with.
- **README.** The models' accuracy is stated by model; Eavor's full 47 to
  75 °F estimate of the pipe's benefit is quoted; the Fig. 1 caption notes the
  TK-Drakōn case is above the tool limit at 30 kg/s; the Holtzman et al. (2023)
  reference is completed.

### Verdicts, v1.2 → v1.2.1 (target 400 °C)

| Site | v1.2 (dual-wall pipe) | v1.2.1 (TK-Drakōn) | Flow for GO |
|---|---|---|---|
| Upper Rhine / Soultz | GO | CONDITIONAL [GO..CONDITIONAL], 1.07 SG | 60 kg/s |
| United Downs | GO | CONDITIONAL [GO..CONDITIONAL], 1.07 SG | 80 kg/s |
| Larderello | GO | GO | |
| Pannonian Basin | GO | CONDITIONAL [GO..CONDITIONAL], 1.06 SG | 70 kg/s |
| Newberry | GO | GO | |

Each change follows from the pipe: TK-Drakōn needs 35 to 50 kg/s to keep the
bit below 200 °C, and the wall is then at 184 to 188 °C, against 60 to 65 °C
with dual-wall pipe. With circulating pressure on the fracture bound, United
Downs is NO-GO in its worst case with an uncooled wall or with the 63° limit.

## v1.2: circulation checked against field data (October 2026)

The circulation model (Model 1) was rebuilt on real well and string geometry,
benchmarked against a published simulator and validated against the FORGE
16B insulated drill pipe trial. The sites were rerun with it, Newberry was
added, and the README now places the work in its literature.

### Circulation model

- **Well and string geometry.** Model 1 runs along measured depth through a
  survey, casing and cement, and a string of segments (drill pipe, heavy-weight
  pipe, collars), each with its own pipe type. Rock temperature is taken at
  true vertical depth.
- **Named pipe types.** The pipe wall is a set of layers in series, with an
  optional fraction of bare tool joints. Conventional, internally and
  externally coated and dual-wall pipe follow Wu et al. (2025); NOV's
  TK-Drakōn coating (0.635 mm at 0.162 W/m·K) is the best-insulated pipe that is
  commercially available; vacuum-insulated tubing is a sensitivity. The 0.02 and 0.10 W/m·K
  walls are gone; the old 0.02 wall survives only as "legacy vacuum tubing"
  for the earlier results.
- **Exposure time by depth.** The rock term can take each depth's time since
  the bit passed, from a rate of penetration or a drilling record, at least
  one hour.
- **Hydraulics.** Friction loss in each piece of pipe and annulus, bit nozzle
  loss, buoyancy and standpipe pressure against a 51.7 MPa pump limit, and the
  lowest annular velocity against a hole-cleaning reference: the 1.245 m/s at
  which FORGE 16B was drilled and cleaned. No published minimum could be
  checked.
- **Friction heating**, found missing by the benchmark: the dual-wall pipe
  there loses about 70 MPa to friction and warms the mud by about 18 °C.
- **Numerics.** Changes of string or hole are ramped over 1 m in a single
  domain, an exposure history is smoothed, a solve can be seeded from an
  earlier one, friction heat uses liquid properties, and a solution outside the
  water table's range is reported as failed.

### Benchmark and validation

- **Wu et al. (2025)** (`benchmark_utaustin.py`): conventional and dual-wall
  pipe within 7 °C; coated pipe 30 to 60 °C hotter with their stated 1 mm
  coatings and 10 to 36 °C colder with their conductivity across the whole
  wall. Nothing fitted.
- **FORGE 16B** (`validate_forge16b.py`): an annulus film multiplier of 0.75
  fitted on the runs without insulated pipe, Eavor's pipe at an effective
  4.9 W/m·K fitted on BHA 11 (close to a 1 mm coating at 0.47 W/m·K), and BHA 12
  predicted blind to within 7 °F, or 4 to 6 °F with the film unfitted. The
  sites use the unfitted film, with 0.75 as a sensitivity.

### Sites

- **Flow and pipe.** Each site is drilled on Wu et al.'s well design. The flow
  is the larger of the survival and hole-cleaning flows within the pump limit,
  on the best-insulated pipe that allows it; this replaces the lowest
  survivable flow. Hole cleaning sets 30 kg/s everywhere, on dual-wall pipe.
- **Newberry** added, for 400 °C at 3.6 km, with the NWG 55-29 cross-check
  (`crosscheck_newberry.py`). The volcanic breakout width is matched at 25 to
  35 K of wall cooling, but the model also breaks out the granodiorite, where
  none were logged, so Newberry is speculative. Its friction coefficient
  (0.55, and 0.70) is the one its stresses were derived with; stress cases can
  now carry their own.
- **Commercial-pipe sensitivity.** The dual-wall pipe exists only in a
  modelling study, so each site also reports the verdict with TK-Drakōn.

### Verdicts, v1.1.1 → v1.2 (target 400 °C)

| Site | v1.1.1 | v1.2, dual-wall pipe | v1.2, commercial pipe | Why |
|---|---|---|---|---|
| Upper Rhine / Soultz | CONDITIONAL [GO..CONDITIONAL] | GO | CONDITIONAL [GO..CONDITIONAL] | wall 148 → 64 °C: hole cleaning sets 30 kg/s, on dual-wall pipe |
| United Downs | CONDITIONAL [GO..CONDITIONAL] | GO | CONDITIONAL [GO..CONDITIONAL] | wall 165 → 65 °C, the same reason |
| Larderello | GO | GO | GO | wall 55 → 48 °C |
| Pannonian Basin | CONDITIONAL [GO..CONDITIONAL] | GO | CONDITIONAL [GO..CONDITIONAL] | wall 139 → 62 °C, the same reason |
| Newberry | (new) | GO | GO | wall 49 °C; speculative |

The uncooled and 63° sensitivities don't depend on the circulation and are
unchanged: both well-characterised sites are NO-GO with an uncooled wall and
the 63° limit together.

### README

The introduction treats the loop as a way of drilling, with its heat a
by-product: a single closed loop is conduction-limited to a few MW, and the
case for superhot rock assumes open-loop flow. A related-work section, the
benchmark and validation, the Newberry cross-check and the commercial-pipe
results are new; the figures are regenerated; the data credits cover the
FORGE and NWG 55-29 datasets.

## v1.1.1: how far the verdicts depend on wall cooling (October 2026)

Corrections from a review of v1.1. The verdicts themselves are unchanged;
what changed is how honestly the output and README describe them.

- **The "no wall cooling" sensitivity was not uncooled.** It removed the
  thermal hoop stress but left the wall at the cooled temperature, so the
  rock kept the strength gained from cooling. It now puts the wall at rock
  temperature. Uncooled, no case is GO at either well-characterised site:
  Soultz needs at least 1.33 SG against a fracture limit of 1.37, United
  Downs 1.29 against 1.32.
- **New sensitivity: an uncooled wall with UD-1's 63° breakout limit.**
  Both well-characterised sites are NO-GO under it (Soultz 1.58 against
  1.37 SG, United Downs 1.54 against 1.32), and Pannonian at worst.
- **README.** The summary and the site assessment now say that the open
  mud-weight window at both sites comes from cooling the wall, with the
  uncooled and combined numbers. The limitations add that the cooling at the
  targets (235–252 K) is about six times the 0–40 K the UD-1 calibration
  covered, that applying the full thermal stress at the wall surface makes the
  cooled results an upper bound, and that the calibrated rock strength holds
  only for the stresses assumed with it. United Downs is described as measured
  or calibrated, not measured. UD-1's deviated section, drilled through
  breakouts up to 90°, is noted as consistent with the 90° criterion.
- **Pannonian.** The full strike-slip range spans GO to CONDITIONAL with the
  wall cooled and CONDITIONAL to NO-GO without, not "GO to NO-GO" as v1.1's
  notes said (that dated from an earlier rule). The equal-stress worst case is
  now described as the wall yielding all round, not as a 180° breakout.
- **Tests.** The water-property table is now loaded on first use, so the fast
  test suite no longer builds it on a fresh clone (seconds, not minutes).

## v1.1: stability calibrated against UD-1 (October 2026)

Models 1 to 4 are unchanged. What changed is the hole-stability calculation,
the site data it runs on, and how results are presented.
`evaluate(site, v10=True)` still reproduces the v1.0 table exactly, and the
test suite holds it to that (`tests/golden/v10_site_table.json`).

### Why

v1.0 ruled out United Downs as NO-GO on stability. UD-1, drilled there to
5,275 m MD (5,058 m TVD) with breakouts, shows the stability calculation was
the problem: v1.0's stress inputs were not the site's, pore pressure never
entered the breakout check, the verdict demanded breakouts be suppressed
entirely, and the cooled wall's thermal stress was ignored.

### Verdicts, v1.0 → v1.1 (target 400 °C)

| Site | v1.0 | v1.1 | Tier |
|---|---|---|---|
| Upper Rhine / Soultz | CONDITIONAL | CONDITIONAL [GO..CONDITIONAL], +0.5 MPa | evidence-based |
| United Downs | NO-GO (stability) | CONDITIONAL [GO..CONDITIONAL], +2.9 MPa | evidence-based |
| Larderello | GO | GO | speculative |
| Pannonian Basin | GO | CONDITIONAL [GO..CONDITIONAL], +3.1 MPa | speculative |

The README gives the reason for each change.

### Stability physics

- **Stress profiles with depth.** Each site supplies Sv, Shmin and SHmax as
  gradient plus intercept, a pore-pressure profile, its source, and the depth
  range the data cover. Results report how far the target lies below the data.
- **Frictional admissibility.** Effective S1/S3 is checked against
  ((1+μ²)^½+μ)², with μ = 0.8, the value the United Downs SHmax was derived
  with (0.6 and 0.85 as sensitivities). Below a profile's data, SHmax is capped
  at the frictional limit. An inadmissible stress state can't be GO.
- **Effective-stress breakout check.** Kirsch hoop stress, Mohr-Coulomb in
  effective stress, no filter-cake credit beyond Pw − Pp.
- **Per-site rock strength**, in place of a global 200 MPa.
- **Breakout width**, in closed form.
- **Mud window and width verdict.** GO if the breakout is within 90° at
  hydrostatic mud (Zoback 2007), CONDITIONAL if heavier mud below Shmin (less
  0.05 SG) gets it there, NO-GO if not. Tensile fractures are reported, with
  zero wall tensile strength, but don't bound the window: UD-1 logged them and
  still reached TD.
- **Thermal hoop stress** at the cooled wall, with the wall temperature from
  Model 1's circulating bottom-hole temperature. Strength, thermal stress,
  isotropic closure and Model 4's creep closure all use that one wall
  temperature; v1.0's 200 °C assumption is gone.
- **Cases.** A site can carry several stress cases (a measured range, or regime
  bounds) and several strength cases; every pair is run, the table row is the
  worst (worst verdict, then narrowest mud window), and the verdict shows the
  range.

### Calibration and checks

- **UD-1.** `src/calibrate_ud1.py` fits rock strength to the BGS image log of
  UD-1 (24 breakouts in the 12.25" section), with wall cooling while drilling
  bracketed at 0–40 K. Weak zones 118–147 MPa (median), intact rock at least
  172–203 MPa; United Downs carries these as four strength cases. The widest
  breakout in a trouble-free section, 63°, is reported as a site-calibrated
  sensitivity on the 90° limit.
- **Soultz.** `src/crosscheck_soultz.py`: breakouts at 5 km with an open window,
  and a breakout onset depth consistent with GPK4, with nothing fitted.

### Data

- **Data basis.** Every site input states its basis and source. Sites without
  measured or calibrated stress and strength, checked against a well, are
  reported separately as speculative: Larderello and Pannonian.
- **United Downs stresses** now follow Reinecker et al. (2021): Sv 25.275 MPa/km,
  Shmin 13.21 MPa/km + 3 MPa, SHmax 25.99 MPa/km + 5.9 MPa, pore pressure
  9.494 MPa/km below a 61 m fluid level. SHmax/Shmin falls from 2.55 to 1.97.
  v1.0's ratios (Shmin 0.55 Sv, SHmax 1.40 Sv) were attributed in the code to
  Pine & Batchelor and the Rosemanowes experiment, but were never traced to a
  value in a source. The published profile replaces them because it is the
  site's own, checked against the paper.
- **Soultz stresses** follow Valley & Evans (2007), valid 1.5–5.0 km, with
  SHmax as a measured range (0.90–1.05 Sv). **Soultz strength** is their lab UCS
  of unaltered granite, 100–130 MPa, replacing an unsourced 170 MPa.
- **Larderello and Pannonian** have no published stress magnitudes or rock
  strengths that we found; their stresses are bounded by the faulting regime
  (Liotta & Brogi; Bada et al. 2007). Pannonian's interior is strike-slip,
  locally transtensional today; v1.0 assumed extension.
- **Temperatures.** United Downs follows Reinecker et al.'s ~180 °C at 5 km
  (v1.0: 190 °C), which moves 400 °C from 12.5 to 12.9 km. Larderello follows
  the Venelle-2 well (507–517 °C at 2.9 km; Bertani et al. 2018), which puts
  400 °C at 2.4 km, where v1.0 had 2.85 km.
- Sources and transcriptions: `data/ud1/`, `data/sites/stress_sources.md`.

### Also

- A pytest suite (`tests/`), with the v1.0 anchors, a frozen v1.0 table, and
  tests for every v1.1 change.
- Figures regenerated: `comparative_sites.png` (breakout width and data depth by
  site), `site_dashboard.png`; new `ud1_calibration.png`. Model 1–3 figures are
  unchanged because those models are.

## v1.0

Four European sites scored for a 400 °C target with Models 1 to 5.
