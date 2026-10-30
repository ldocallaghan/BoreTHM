# Model development

This log records changes to BoreTHM's physical calculations and their comparison with development observations. A declaration describes the equations, inputs and predicted effects before a new comparison. Its subsequent score uses the same sample list and reports every gap, including deterioration. Reverted candidates remain in the disclosure table.

## Data statement

FORGE 16A and 16B are development data. Their observations have already been examined and cannot provide an independent validation of changes motivated by their errors. FORGE 56-32, 58-32 and 78B-32 remain reserved for later validation, with targets opened once in declared stages. The 56-32 and 58-32 input archives and pressure protocols remain unchanged. The 56-32 standpipe-pressure targets were opened once, on 28 October 2026, for the first unseen-well stage below. The 58-32 pressure targets and the 78B-32 targets remain unread.

No new parameter is fitted in the primary development comparison. The annulus film multiplier is 1.0. A film coefficient converts a fluid-to-wall temperature difference into heat transfer per unit area. `site_evaluation.FILM_MULT_FORGE = 0.75` is a fitted, retired sensitivity. The full site evaluator still calculates that historical sensitivity separately from its primary result; the scoreboard does not call it. The fitting routines in `studies.validate_forge16b` remain historical study functions and are excluded from the scoreboard.

There is an additional historical calibration that must be disclosed. The frozen 16B trial geometry uses effective insulated-pipe wall conductivity 4.9237482416889895 W/(m K), obtained by fitting 16B observations. Film multiplier 1.0 does not remove that fit. The baseline retains this conductivity to reproduce the archived calculation. Trial cases using it are labelled as calibrated geometry. The regular-pipe group does not use it. An unqualified claim of no calibration would be incorrect for the full baseline. An independently sourced insulation input is required before describing a later complete primary path as uncalibrated.

Recorded well geometry, flow, mud properties and initial conditions are observational inputs. They are distinguished from correlation coefficients and engineering assumptions. No correlation coefficient may be selected from a FORGE residual. One inherited reference-programme assumption also needs correction before a source-independent candidate can be scored: ordinary-pipe connection pitch was transferred from the 16B tally. It is disclosed below and is not represented as a manufacturer value.

## Gaps

The following sizes describe the earlier comparisons. They are context for declarations, not acceptance targets. Errors are modelled minus measured.

| Gap | Quantity | Earlier reported size | Scoreboard definition |
|---|---|---|---|
| G1 | Standpipe pressure, measured at the surface pump | 16A about -1,624 psi; 16B about -969 psi after reported motor differential subtraction | Signed psi and percentage residual by assembly. 16A uses standpipe minus raw reported differential. 16B uses unadjusted standpipe on motorless runs 12, 13, 15 and 16. |
| G2 | Hydraulic power represented as heat | 16A about 500 versus 928 kW; 16B about 244 versus 527 kW | Mean modelled in-hole friction, nozzle and motor-face power against measured standpipe pressure times inlet volumetric flow, over the same pressure-available samples in each well. Surface power is reported separately and is not added to in-hole heat. |
| G3 | Deep 16A bit-temperature bias | BHA 38 about -7, BHA 39 about -9 and BHA 42 about -19 °C | Bore-fluid temperature at the bit against bit-box observations, by every 16A assembly; the deep assemblies are marked. The sensor medium is unresolved, so this is a fixed calculation proxy. |
| G4 | 16A run-in peak error | Underprediction about 20–50 °C on partial legs | Event-level peak error using the existing conditional initial-state and fixed-column treatment. The tool's internal-fluid node at the bit and the static fluid-node treatment are the single declared comparison. |
| G5 | 16A surface return bias | About -6 °C; observations exceed even the optimistic recovery bound | Equal-sample pooled return bias across all frozen 16A primary samples. Source groups and their overlaps are retained; this is not a count of independent observations. |
| G6 | 16B regular-pipe and trial temperature biases | Independent regular pipe about -8.8 °C; trial runs about +1 to +3 °C | The original independent regular-pipe group, with its declared sensor positions, and each of the four trial runs. Early unresolved-position runs remain separately reported and are excluded from the original independent pool. |

The 16B numbers above mix historical protocols. The -969 psi and 244 kW figures use the later revised-rheology comparison. The original blind settings use the earlier recorded-mud substitutions. G1 also uses a different subset and pressure target from that pooled historical number. The baseline must reproduce the original calculation and state these differences; it must not be adjusted to reproduce rounded numbers from a different protocol. Measured pump power does not establish where that power becomes fluid heat, particularly when a motor performs mechanical work.

## Frozen comparison

The [scoreboard](../../validation/scoreboard/README.md) uses the original primary sample lists, recorded mud, PV referenced to 26.7 °C, film multiplier 1.0 and cumulative circulation exposure. PV means plastic viscosity, the slope of the Bingham fluid's stress versus shear-rate relation above its yield stress. Each sample has equal weight within its declared group. No sample is selected using a new prediction or residual. Failed and unavailable cases remain in the coverage counts.

The baseline runs the explicit original hydraulic mode. Its temperature, pressure and power outputs are checked against the archived blind calculations at 0.1 °C, 1 psi and 0.1% of power. These are reproduction checks, not tolerances for accepting a physical model. The scoreboard and baseline are then fixed. A later change to their samples, reductions or input conventions is itself a development entry.

The run-in comparison retains the original observed initial tool temperature and average leg speed. Its fluid column is calculated at the start of each leg using the original local circulation/static history. Two originally unavailable run-in events remain visible in the event inventory. Their absence cannot be counted as successful model agreement.

## Candidate disclosure

This table includes work performed before this log existed. Earlier development results are not new scores under the frozen scoreboard. A missing earlier prediction is stated explicitly.

| Candidate | Declared prediction | Development result available before this log | Disposition |
|---|---|---|---|
| Original hydraulic calculation, PV at 26.7 °C | Original comparison configuration | Archived 16A and 16B blind results | Baseline reference |
| Original calculation, PV at 48.9 °C | Higher plastic viscosity for the same field PV; changed pressure and heat transfer | Separate pressure rows in the [earlier development archive](../../validation/hydraulics-v160/pressure-comparisons/README.md) | Deferred heat-transfer candidate; excluded from entry 1 |
| Revised hydraulic calculation, PV at 48.9 °C, 16A NC50 scenario | Additional connection/component losses and local dissipation | Earlier pressure and temperature predictions exist; no six-gap scoreboard score | Provisional; entry 1 awaits its separate 26.7 °C score |
| Revised hydraulic calculation, PV at 48.9 °C, 16B EIS scenario | Additional losses and local dissipation | Earlier motorless pressure predictions exist | Provisional; no acceptance decision |
| Revised hydraulic calculation, PV at 48.9 °C, 16B GPDS55 scenario | Alternative catalogue connection dimensions | Earlier motorless pressure predictions exist | Historical geometry sensitivity; excluded from the single primary scoreboard variant |
| D1 endpoint correction alone | Remove an initial solver point below the bit | Invalid-step warnings continued | Reverted as an incomplete correction |
| D1 endpoint and overlapping-ramp correction | Restore a continuous numerical geometry transition | The same short-component case converged | Retained numerical correction; gap score pending |
| D2 boundary tolerance 1e-10 K | Reduce the turnaround power residual | Reduced the numerical residual; no independent physical justification for that precision | Return to the original boundary tolerance; diagnostic-only policy below |
| D3 programme forwarding | Pass the declared geometry to design comparisons | Programme-adapter tests passed | Retained API correction; no new physical coefficient |
| D4 aggregate trial adapter | Retain the original trial geometry and remove missing serial-table lookups | Four trial geometry tests pass; all 45 trial samples and all 22 diagnosis windows converge | Retained input-contract correction; frozen scoreboard unchanged |
| Entry 1, original 26.7 °C convention, NC50/EIS | Additional hydraulic losses and local heat; temperature effects estimated at tenths to a few °C | G1/G2 deficits decrease; G3 warms by 8.4–16.1 °C, worsening five assembly biases; G6 trials become warmer | not kept; BHA representation under correction |
| Entry 2 component diagnosis | Separate a length-dependent connection contribution from assembly-passage losses | The assumed 1.25-in motor passage is a large calculated contribution on 16A; connection losses also contribute | Diagnosis only; no model change or acceptance decision |
| Thermal geometry and heat-source separation | A should reproduce a heat-source effect; B should reproduce a thermal-geometry effect; compare with the single-pass power scale | A reproduces assembly mean bit rises within 0.02 °C; B changes them by less than 0.01 °C. A exceeds the bulk scale at the bit. | Diagnosis only; no model correction selected from it |
| D5 equipment representation | Remove a motor mandrel's full-length passage and invented bit IDs; pressure and dissipation should decrease | All 467 circulation cases and nine available run-in cases calculated, with explicit thermal-only instrument assumptions and unknown internal tool losses | Debugging correction; acceptance of integrated entry 1 remains pending |
| Entry 1 with D5, original 26.7 °C convention | Revised hydraulic losses with equipment-corrected assembly passages | 16A in-hole power 654 versus measured pump power 928 kW; G3 rises 1.3–3.7 °C from legacy; G6 regular bias -7.2 °C and trial bias +3.0 °C | Kept as the working development calculation, 28 October 2026; upheld by independent review, 29 October 2026 |
| Entry 3, cylindrical rock response (R1) | Exact wall-temperature step response replaces the logarithmic rock term; bit +0.2 to +2.2 °C and return +0.1 to +0.35 °C in the working calculation | Every expected score change met within 0.1 °C. Cold biases shrink, except BHA 35r1, which crosses zero; warm biases grow, including the trial bias, from +3.03 to +4.62 °C | Kept under its declared rule, 28 October 2026; upheld by independent review, 29 October 2026 |
| Entry 4, rotary heat (M2) | Measured surface rotary power released as wall friction along the string and as work at the bit, split by a soft-string torque balance; warmer everywhere, most where the string rotates fast and deep | Every expected score change met within 0.25 °C. Deep 16A biases shrink to -2.1, -2.8 and -13.6 °C; 16B regular pipe -1.40 °C, with its deep runs now warm; trial bias +7.55 °C | Kept under its declared rule, 28 October 2026; upheld by independent review, 29 October 2026 |
| Entry 5, measured 16B mud rheology (I1) | Measured PV and YP replace reference-mud fills on seven 16B assemblies; 16B standpipe pressure falls by 166–524 psi; EOW 11, 12, 16 and 17 warm by 4.8–10.9 °C | Every expected change met within 1.1 °C and 20 psi. 16B G1 biases fall to -435 to -546 psi; 16B regular pipe +2.40 °C, trial +9.08 °C | Kept under its declared rule, 29 October 2026 |
| Bingham annulus candidate, Wilson–Thomas criterion on the report YP (`bec37fe`) | Shared laminar-turbulent criterion for annulus pressure and heat transfer, Gnielinski on the wall apparent viscosity | Never scored. Model-only checks found the 16A annulus laminar on the YP and turbulent with a low-shear yield stress | Removed before scoring, 30 October 2026; replaced by entry 6 |
| Entry 6, Herschel–Bulkley annulus (A1), hypotheses no-yield, gel and gel-rising | Founargiotakis slot model for annulus pressure and regime; Gnielinski on the wall viscosity; all three cool 16A, by about 4–10, 7–34 and 14–34 °C at the bit | Every expected change met. RMS of the nine 16A assembly bit biases 10.0, 19.7 and 24.6 °C against 5.6 °C for the working calculation; 16A pressure and 16B water-like runs nearly unchanged | Not adopted under its declared rule, 30 October 2026; the downhole rheology is unmeasured |
| Entry 7, plastic-viscosity heat transfer and the Erge band (A2), the same three hypotheses | Gnielinski on PV (Chhabra and Richardson eq. 6.55 class) and the transition band of Erge et al. (2015); 16A bit about −1 to −2, −1 to −19 and −4 to −26 °C from the working calculation | Declared 30 October 2026; score pending | Not adoptable under its rule until the downhole rheology is measured |
| Historical annulus film multiplier 0.75 | Earlier fitted heat-transfer sensitivity | Fitted on 16B and evaluated separately | Retired sensitivity; excluded from primary scoring |
| Historical insulated-pipe conductivity fit | Reproduce the 16B trial insulation result | Used by the archived trial geometry | Baseline reproduction only; calibration explicitly disclosed |

## 27 October 2026: entry 1, hydraulic losses and heat placement

This is a retrospective declaration. The implementation and some development comparisons predate this log. The predictions below are written after those results were available and are not a blind registration. The source choices and interface can be inspected at `a1927b3` (27 October 2026, 15:32 +01:00), `8bbfe2c` (16:08 +01:00) and `56d1b57` (19:27 +01:00). No new entry-1 score is made here.

### Equations and parameters

The shared calculation uses the existing Bingham straight-passage pressure gradient for mud and the existing Newtonian gradient for water. Bingham yield stress is the stress below which the idealised fluid does not shear. For each repeated connection, the body-friction contribution over its restriction length is replaced by friction at the connection bore and external diameter. The expected number of connections is string length divided by connection pitch. Serial components retain separate passages.

For an area ratio r = small area / large area, abrupt expansion uses K = (1-r)^2 and contraction uses K = 0.5(1-r)^0.75. Each local loss is K rho v_small^2 / 2. A supplied tool curve scales as dp_ref (rho/rho_ref)(Q/Q_ref)^2. A complete tool curve replaces the internal losses it already includes. Surface pressure is C rho_ppg (Q_gpm/100)^1.86 psi. Each in-hole dissipative term supplies heat at its location, q' = Q_local dp/dz. Nozzle dissipation remains at the bit; surface losses and the signed density-column pressure contribution are excluded from in-hole dissipation. The same pressure-gradient kernel supplies pressure and heat.

| Parameter or treatment | Value and provenance | Qualification |
|---|---|---|
| Straight-passage friction | Existing Bingham and Newtonian laws; Bourgoyne et al., *Applied Drilling Engineering* (1986), chapter 4 | No new roughness or residual multiplier |
| Local-loss coefficients | Expansion 1 and contraction 0.5 with exponent 0.75; [Modelica 4.0.0 sudden-change documentation](https://doc.modelica.org/Modelica%204.0.0/Resources/helpOM/Modelica.Fluid.Dissipation.Utilities.SharedDocumentation.PressureLoss.Orifice.dp_suddenChange.html), citing Idelchik | Published smooth turbulent restrictions; transfer to annular/yield-stress flow is approximate |
| Tool scaling | Density times flow squared; API RP 13D, sixth edition (2009), section 7.6.2, equation 103 | Requires a tool-specific reference point |
| Surface layouts | C = 1.00, 0.36, 0.22, 0.15 or 0.15; exponent 1.86; API RP 13D, sixth edition (2009), section 7.3, equation 60 and table 4 | Layout 5 is the declared reference assumption; installed surface plumbing is unresolved |
| Nozzle discharge coefficient | Existing 0.95 | Retained baseline convention, no refit |
| Property pressure floor | Existing thermal-friction guard, 5 MPa, applied consistently to new pressure and heat | Numerical liquid-property approximation near the surface |
| Ordinary reference connection | 7-in OD and 4-in bore; [NOV GPDS/EIS catalogue](https://www.nov.com/products/gpds-and-eis-connections), 5.5-in / 21.9-lb/ft row | Dual-wall and vacuum variants retain their body bore internally; external envelope is transferred |
| Ordinary restriction length | 29 in | Inherited engineering assumption; not an as-built throat measurement |
| Ordinary reference pitch | Existing 2,378 ft / 75 from a 16B tally | FORGE-derived transfer, not source-independent. It cannot be described as a non-FORGE model constant; replace by a compatible catalogue pitch in a declaration before scoring the reference scenario. |
| Heavy-weight pipe connection | 7.25-in OD, 3.25-in bore, approximately 31-ft pitch; [Workstrings 91005000020000](https://www.workstringsinternational.com/assets/Spec-Sheets/HWDP/91005000020000-Imperial.pdf), 1 August 2025 | 48-in effective restriction is an assumption based on published pin/box lengths |
| Reference measurement-tool loss | xBolt G2-L, Rev 7, page 2: psi = ppg times gpm squared / 30,000; [manufacturer sheet](https://www.poweredbyextreme.com/wp-content/uploads/2024/07/xBolt-G2-L-Specifications-and-Fishing-Diagrams_Rev7.pdf) | 500-gpm, 1,000-kg/m³ normalisation; flow limit 750 gpm; 165 °C rating does not qualify a hot-well tool |
| Reference tool geometry | Pulser 1.780032 m, 7-in OD / 3.38-in bore; collar 9.144 m, 6.75-in OD / 3.25-in bore | Same manufacturer drawing; covered internal tool loss replaces empty-passage losses |
| Plain reference collar | 132.075968 m | Existing 143 m less the two stated tool lengths |
| Development assembly geometry | Recorded component dimensions and the previously declared NC50 or EIS catalogue scenario | Observational well inputs are retained separately from model coefficients; unknown tool operating losses remain unknown |

The 26.7 °C viscosity reference stays unchanged in this entry. A 48.9 °C field reference is an unverified input convention and belongs to a later heat-transfer entry. Recorded field dimensions do not establish installed connection machining. The inherited reference pitch and trial insulation calibration are explicit unresolved provenance issues, not hidden fitted parameters.

### Predicted effects before the next comparison

These are order estimates, not acceptance bands. At an illustrative 40 L/s, each additional 100 psi corresponds to about 28 kW of hydraulic power. With illustrative density 1,000 kg/m³ and heat capacity 4,000 J/(kg K), full conversion would add about 0.17 °C per 100 psi. These illustrative properties are not FORGE calibration values.

| Gap | Predicted direction and rough size |
|---|---|
| G1 | Pressure should increase at fixed flow as omitted restrictions are added. Tens to order 1,000 psi are plausible for the declared tool and connection scenarios; no specific fraction of the observed deficit is promised. |
| G2 | In-hole dissipative power should increase, of order tens to hundreds of kW for the illustrative pressure/flow range. Surface loss cannot supply downhole heat. |
| G3 | Extra heat could change bit temperature by tenths to a few °C. Internal exchange and rock heat transfer may change the local sign. A large deep-run temperature correction is not predicted from dissipation alone. |
| G4 | No direct new heating during pumps-off run-in. Any effect is through the preceding fluid/rock state, plausibly a few °C or less; its sign is conditional on that history. |
| G5 | The direct hydraulic-heating contribution should raise fluid energy, with a return-temperature effect of tenths to a few °C. Changed rock exchange can alter the net return response. |
| G6 | Similar modest heating is expected in regular pipe and trial runs. Additional trial overprediction would be a deterioration that must be reported. |

Status: retrospective declaration; no six-gap score or keep decision under this log.

## 27 October 2026: D1, short serial components

Commit `c98f02e` corrected a numerical geometry error. A component shorter than half the 1-m transition width could place an initial solver point below the bit. Closely spaced transitions could overwrite one another and make the blended equations discontinuous. The correction restricts the initial mesh to the well and uses non-negative piece-occupancy weights for overlapping transitions, with the same 1-m width and unchanged per-piece equations. The explicit legacy mode retains its original path.

The justification is the solver domain and continuity of its equations. Closing a field-data gap is not its justification. Endpoint correction alone did not resolve the overlapping-transition case. The combined correction converged on that same input. No signed change is predicted for G1 to G6; the purpose is to obtain valid solutions for declared geometry. Synthetic component tests retain this correction. A separate six-gap score has not been made.

## 27 October 2026: D3, programme forwarding

Commit `0b89980` corrected the design-comparison adapter after the evaluator acquired a hydraulic-programme argument. The adapter must pass the declared programme and casing shoe to the geometry builder. This is an interface correction, justified by the argument contract. No coefficient was chosen from a prediction error, and no physical improvement in G1 to G6 is claimed.

## 27–28 October 2026: D2, energy diagnostic and boundary accuracy

Commit `8e6d0b9` tightened the boundary-condition tolerance to 1e-10 K because a small turnaround residual exceeded an excessively precise power check. The pressure/heat source integrals agreed. This diagnostic discrepancy did not establish failure of the physical boundary-value solve.

Restore the original solver tolerance: profile tolerance 1e-4, with the solver's default boundary tolerance. Report assigned power, applied power and their residual. Flag a residual exceeding the larger of 1 W and 0.1% of the compared powers. A failed diagnostic evaluation is also flagged and returned. Neither case changes solver success or raises a diagnostic exception to the caller. Solver convergence and finite physical temperatures remain separate checks.

Prediction: the representative deep-well solve remains converged at the original tolerance, and its small power residual is acceptable at the declared reporting resolution. No material G1 to G6 change is expected from removing unnecessary boundary precision. Any actual convergence failure must be identified; tolerance tightening is permitted only for such a demonstrated convergence need. No physical gap score is authorised by this numerical check.

The original tolerance has been restored. The deep-well reference and both short-component convergence cases pass at that tolerance. Tests also confirm that a flagged residual or an exception inside the diagnostic leaves a converged solve successful. No tested case requires a tighter boundary tolerance. The six-gap candidate comparison remains pending.

## 28 October 2026: legacy baseline

The single baseline calculation completed in 265.5 seconds. Its 467 circulation cases converged, and all nine originally available run-in cases were reproduced. All 2,614 archive checks passed at the stated resolutions. The two unavailable run-in cases remain unavailable. The saved [scoreboard](../../validation/scoreboard/baseline/scoreboard.csv) and its individual predictions are the reference for subsequent entries. This is a reproduction of the original calculation, not a score of entry 1.

| Gap | Legacy baseline | Source within the scoreboard archive |
|---|---|---|
| G1 | Every 16A assembly and the four motorless 16B assemblies have separate psi and percentage residuals | `scoreboard.csv`: G1 rows, `bias` and `mean_percent_error` |
| G2 | 16A 500.04 versus 928.27 kW; original-protocol 16B 264.29 versus 526.52 kW | `scoreboard.csv`: G2 rows, `model_mean`, `measured_mean` |
| G3 | Bore-at-bit biases for BHA 38, 39 and 42 are -8.12, -9.68 and -19.81 °C; all assemblies are reported | `scoreboard.csv`: G3 rows, `bias`, `deep_run` |
| G4 | The nine available event peak errors range from -54.35 to -6.53 °C for the declared internal-fluid comparison | `run-in.csv`: `peak_error_C`; unavailable events have no numerical error |
| G5 | Pooled return bias -5.85 °C over the original 358 samples | `scoreboard.csv`: G5, group ALL, `bias`, `compared` |
| G6 | Independent regular-pipe bias -8.77 °C; pooled trial bias +1.99 °C, with every trial also reported separately | `scoreboard.csv`: G6 group rows, `bias` |

The G3 figures use the fixed bore-fluid proxy specified before this run. The earlier rounded gap description did not identify one of the unresolved bore/annulus and position alternatives. Those quantities are not silently interchanged. Source and result checksums identify the frozen scoreboard; later scoring changes require their own log entry.

## 28 October 2026: heat-transfer candidate inventory

These candidates are declared for G3, G5 and G6. None has been scored by this log. A Reynolds number compares inertial and viscous flow effects; a Nusselt number converts a heat-transfer coefficient into a dimensionless quantity. The hydraulic diameter of a concentric annulus is the outer diameter minus the inner diameter.

| Treatment | Physics and provenance | Rheology states and reference temperatures |
|---|---|---|
| Current calculation | Dittus–Boelter with plastic viscosity, Nu = 0.023 Re^0.8 Pr^n in its turbulent branch, laminar Nu = 4.36, film multiplier 1.0 | Intact, central and degraded rheology; each at PV reference 26.7 °C and 48.9 °C |
| Wall-viscosity and transition treatment | Apparent viscosity at the wall includes yield stress. For a Bingham fluid, mu_wall = mu_plastic / (1 - tau_y/tau_wall) in a yielded wall layer. Wilson–Thomas or a Hedström-number transition must be declared with its validity limits before implementation. Hedström number is rho tau_y D_h² / mu_plastic². [Thomas (2018)](https://papers.acg.uwa.edu.au/d/1805_16_Thomas/16_Thomas.pdf), equations 9–12, also identifies the corrected sign in the original Wilson–Thomas expression. | The same three rheology states and both reference temperatures; no state selected from residuals |
| Annulus heat transfer | Gnielinski's concentric-annulus correlation distinguishes inner and outer heat-transfer surfaces. Diameter ratio a = D_i/D_o gives inner factor 0.75 a^-0.17 and outer factor 0.9 - 0.15 a^0.6, with the liquid wall-property correction (Pr/Pr_wall)^0.11. See [Gnielinski (2009)](https://doi.org/10.1080/01457630802528661) and the [INL implementation](https://mooseframework.inl.gov/bison/source/materials/ADWallHTCGnielinskiAnnularMaterial.html). | The same three rheology states and both reference temperatures; extension from Newtonian data to mud requires an explicit approximation statement |

Intact rheology retains the recorded PV and yield point under the declared temperature treatment. Degraded rheology approaches the water-viscosity, zero-yield limit at recorded density. A central downhole state needs independent laboratory ageing evidence or an explicitly declared interpolation bracket before it receives numerical values. No degradation factor is inferred from the FORGE temperature gaps. The unknown field measurement temperature also cannot be identified from a better residual at 48.9 °C.

The candidate inventory is a design space, not permission to run all combinations. Each subsequent entry names one primary treatment. Additional variants require a stated input uncertainty and comparison purpose in that entry's declaration. Correlation changes may alter convection by tens of percent and temperatures by several °C, but coupled bore/annulus exchange prevents a reliable signed prediction at every sensor without calculation. A model-specific declaration must narrow these order estimates before scoring.

Reheating candidates for G4 and G5 are reserved for a separate declaration before their first implementation or comparison. Existing recovery-bound diagnostics do not establish recovery as the cause of any gap.

## 28 October 2026: entry 2, string-loss diagnosis

This entry changes no model function or parameter. Earlier pressure comparisons reported a 1,150–1,730 psi string-loss increase on 16A and 130–340 psi on 16B at similar depth/flow, including overpredictions for 16A BHA 38 and 39 and a smaller increase for deeper BHA 42. These are previously observed development results, not a result of the diagnosis declared here.

Explanation A is that the assumed NC50 connection bore dominates the increase. Its prediction is a connection contribution that grows with string length and is similar among assemblies at matched flow and depth. Explanation B is that a small passage in particular assemblies dominates. Its prediction is an assembly-specific component contribution that length and flow do not explain. Both mechanisms may contribute.

Use one representative pressure-available window per assembly in each well. Select the earliest window at the median bit-depth rank, ordered by depth, time and sample identifier; for an even count use the lower middle rank. The selection uses frozen inputs alone. The 16A set contains each bit-box assembly. The 16B set contains each pressure-available primary assembly, including the trial runs. Keep the same recorded mud and PV reference of 26.7 °C as the scoreboard.

Report pipe-body friction, repeated connections, each serial assembly component, local changes of area, supplied tool losses, nozzles and surface loss separately, including external annulus contributions. Each component row names its length, bore, outer diameter and source. A complete tool curve must not receive duplicated empty-body losses. Unknown proprietary operating losses remain unknown. The budget must sum to standpipe pressure within about 1 psi. No bore, effective length or coefficient is adjusted after this breakdown.

The diagnosis and entry-1 six-gap comparison await approval. Entry 1 will then receive a keep/revert recommendation with the before/after scoreboard. The acceptance decision remains separate from the numerical calculations.

## 28 October 2026: additional candidate declarations

These declarations precede the first entry-1 score on the frozen scoreboard. They add no model term and change no scoreboard input. The estimates below describe possible physical effects; they are not calculated changes on the development samples. A later implementation needs its own declaration and score. The approved historical insulation conductivity and connection pitch remain fixed for entry 1.

### Motor power and mechanical work

The present face source uses inlet flow times the rig's reported motor differential. That differential represents the increase above the off-bottom pressure and omits the motor's no-load pressure drop. Candidate M1 accounts for total motor hydraulic power, Q times (reported differential plus independently specified no-load drop), for G2, G3 and G6. Hydraulic power includes shaft work. An implementation must separate internal motor dissipation from shaft work and any subsequent bit heat, so the same power is counted once. A manufacturer's no-load value requires a documented motor match and flow basis. It cannot be inferred from a pressure residual.

The predicted direction is increased accounted motor power and additional heat where that power is dissipated. **Estimate:** at illustrative flow 20–50 L/s and omitted drop 100–500 psi, the additional hydraulic power is about 14–172 kW. The corresponding bulk temperature increment is of order 0.1–2 °C for water-like heat capacity and typical drilling mass rates. G3 and G6 may become warmer; an existing positive trial bias could increase. These are engineering estimates, not a promise that all hydraulic power becomes immediate face heat. BICO's [7-in SSS100-B5 sheet](https://bicodrilling.com/wp-content/uploads/2022/09/7-SSS100-B5.pdf) reports a separate no-load drop and rated flow range. It is an example of the required input, with no assumed match to either development well. Zhang et al. (2024), reference C2 below, include a motor heat source.

Candidate M2 adds rotary string friction and bit work for G5, with smaller effects expected on G3 and G6. Mechanical power is torque times angular speed, P = torque times 2 pi RPM / 60. The declared string-friction deposition is in the annulus along the deviated section; bit work is deposited at the bottom. Measured surface torque contains both contributions and other mechanical losses, so partitioning requires a physical torque balance. Motor shaft power already accounted for in M1 cannot be added again as an independent heat source. Raw torque and rotational-speed channels are needed from the 16A 1-s records in GDR 1283 and the 16B Pason records. No channel is extracted or compared at this stage.

The predicted direction is warmer return fluid, with smaller positive bit-temperature effects that depend on heat exchange along the string. **Estimate:** 10 kN m at 120 RPM supplies about 126 kW. If all of that power entered 40 kg/s of fluid with heat capacity 4 kJ/(kg K), it would supply about 0.8 °C of bulk warming. An order 0.5–3 °C return response and sub-degree to a few °C local response are provisional estimates. The partition and actual channel magnitudes are unresolved. References C1, C2 and C3 discuss rotational or mechanical heat; none provides a coefficient selected for FORGE.

### Rock conduction and exposure history

Candidate R1 replaces the approximate rock resistance ln(1 + 2 sqrt(t_D)) with the exact infinite-medium cylindrical response to a constant wall-temperature step. Here t_D = alpha t / a², a is the rock-boundary radius, and alpha = k/(rho c) is thermal diffusivity. For initially uniform rock, unit wall-temperature step and temperature fixed at infinity, the dimensionless Laplace-domain temperature is K0(r_D sqrt(s))/(s K0(sqrt(s))). K0 and K1 are modified Bessel functions; s is the dimensionless Laplace variable and r_D = r/a. Differentiation at the wall gives the transformed dimensionless conductance K1(sqrt(s))/(sqrt(s) K0(sqrt(s))). Invert and tabulate that conductance, then use its reciprocal as the step resistance multiplying 1/(2 pi k). This follows the cylindrical diffusion boundary-value problem described by Carslaw and Jaeger (1959), reference C4. It is a proposed derivation, with numerical inversion and radial-solver verification required before use.

R1 bears on G3, G5 and G6; G4 is affected through the preceding rock/fluid state. Review the 3,600-s exposure floor together with the response, including fresh-wall times of minutes. The early-time conductance has an inverse-square-root singularity for an ideal instantaneous temperature step. A finite time step or finite boundary evolution needs a physically stated treatment. **Estimate:** changes of order 10–30% in the rock conductance away from the floor, potentially larger at freshly exposed wall, could change local fluid temperatures by order 1–5 °C. For rock hotter than fluid, greater conductance increases fluid heating; the sign reverses where the inlet heats shallow rock. This estimate is not an evaluated response-function comparison.

The constant-flux time functions associated with Ramey (1962) and Hasan and Kabir (1994), references C5 and C6, are excluded from this replacement. Those functions give wall temperature in response to prescribed heat flux. R1 needs flux in response to prescribed wall temperature. Their time-domain responses are different; taking the reciprocal of a constant-flux response does not produce the constant-temperature response. Ramey discusses other boundary conditions as well; this exclusion concerns the constant-flux functions. A future model that prescribes flux would require a separately consistent formulation.

Candidate R2 replaces a single exposure clock with a history response, including measured inlet-temperature changes and pumps-off reheating, for G3, G4 and G6. For a linear rock problem, superpose temperature-step responses over the boundary history. Measured inlet history must first be propagated through the circulating fluid to the depth-dependent wall boundary; it cannot be imposed directly on every rock cell. The same history continues through static periods. Duhamel superposition follows the linear conduction theory in C4; variable properties would require a stated linearisation or a nonlinear time-domain solution.

After a pause, recovery towards the undisturbed rock state is predicted to increase the heat available to a cold returning circulation and can increase run-in peaks. A colder later inlet can reduce temperatures during the corresponding circulation. **Estimate:** order 1–10 °C local history effects and potentially larger transient peak changes; neither their occurrence nor their magnitude on FORGE has been established. G5 is also relevant when reheating supplies subsequent return heat. Compare a resolved radial rock history with the linear history response in a later declared entry; existing full-recovery bounds remain optimistic diagnostics. Neither candidate is implemented here.

### Properties and geometry

| Candidate | Gaps and predicted direction | Rough size, explicitly an estimate | Published basis and input requirement |
|---|---|---|---|
| R3: depth- and temperature-dependent rock properties | G3 and G6. Higher local k increases exchange with hotter rock; a decrease in k with temperature can reduce it. The heat-capacity change also alters recovery. The net temperature sign is depth- and history-dependent. | **Estimate:** tens of percent in local conductance and order 1–5 °C in fluid temperatures. | Allis et al. (2018), C7, report depth-dependent measured conductivity in 58-32 and temperature corrections for both conductivity and heat capacity. Use these as an explicitly transferred material input. Use a consistent k(T), rho c(T) and alpha(T), with an enthalpy formulation if properties vary during recovery. No 58-32 pressure or temperature comparison target is opened. |
| R4: hole enlargement in thermal terms | G3 and G5. A larger hole increases fluid inventory and changes the rock radius, while lower annular velocity can reduce the film coefficient. Competing effects prevent a universal sign; the prediction is a depth-localised response at measured enlargements. | **Estimate:** local film changes of tens of percent and order 0.1–3 °C fluid changes, conditional on actual enlargement. | Gilmour et al. (2021), GDR 1292, supply 16A logs. A later entry must identify the caliper and ultrasonic borehole-image (UBI) channels and their depth coverage. Preserve the hydraulic geometry for a thermal-only comparison, and declare any later hydraulic change separately. |
| R5: fluid thermal mass after flow changes | G3 and G5. Retaining rho c A times dT/dt delays the approach to a new circulating state; the sign opposes the immediate temperature change after a flow step. | **Estimate:** minutes to a circulation time of lag; transient differences of order 0.1–5 °C, decreasing at steady conditions. | C2 and C3 formulate transient fluid energy storage. Low priority because the 16A pause comparisons already identify limitations in starting circulation profiles; storage has not been established as their cause. |
| R6: formation temperature at depth | G3, especially BHA 42, and G5/G6 because the wells share the adopted profile. Residual drilling cooling would make an equilibrium correction warmer. Extending a positive gradient below the log endpoint would also warm that tail; different recovery evidence could change the direction. | **Estimate:** order 0–5 °C change in the temperature input, with a smaller coupled-fluid response; no lower or upper limit is established from the gaps. | The 216-day profile and its coverage are documented in the [16A archive](../../validation/forge16a/README.md), using Jones (2022), GDR 1421. Its endpoint is 10,740 ft MD. C4 supplies recovery physics. Any correction must be obtained from a recovery calculation or later logs acquired before injection, with acquisition dates checked. A residual alone cannot define the correction. |
| P1: independently specified insulated-pipe conductivity | G6 trial runs. Less effective conductivity reduces heat leakage into downward bore fluid, tending to cool it; a greater value reverses that effect. Annulus response can have a different sign. | **Estimate:** order 1–10 °C trial-temperature changes for a substantial insulation-resistance change; sign and size require the actual construction. | Ajima and Naganawa (2022), C8, provide an independently published effective-conductivity example. It is not a manufacturer value for Eavor's 16B pipe. Obtain a value and layer dimensions for that actual product before replacing the fitted 4.9237482416889895 W/(m K). A coating-material value cannot directly replace an effective whole-wall value. No verified manufacturer value for the actual trial pipe has yet been identified. |
| P2: catalogue connection pitch for the reference programme | Reference pressure and heat provenance; it bears on G1/G2 only if later transferred into a development geometry. A shorter pitch increases connection count and losses. It has no effect on the present frozen comparison. | **Estimate:** a 31.5-ft pitch gives about 0.66% more connections than 2,378 ft / 75; only the connection contribution scales by this fraction. | Workstrings International (2025), C9, gives approximate assembly length 31.5 ft for 5.5-in, 21.9-lb/ft pipe. That sheet's Delta 544 connection differs from the reference EIS envelope, so using its pitch would be a declared dimensional transfer. No connection bore or envelope changes are authorised by this declaration. |

### Measurement diagnostics declared without execution

These entries change no model and are not executed at this stage. Each has a distinguishing observable; a better model residual cannot determine a correction.

| Diagnostic | Declared comparison and interpretation |
|---|---|
| M3: Sanvean-to-rig clock alignment | Cross-correlate independent pressure-step records, using raw timing and sustained features. Estimate offsets separately across 1 November 2020 and check whether a clock-convention change explains them. Do not select an offset from temperature agreement. |
| M4: bit-box and top-sub response | Compare bit-box minus top-sub temperatures across on-bottom and off-bottom steps, allowing for sensor separation and fluid transport. A repeatable load-linked difference can distinguish local heating from a common inlet-history change. |
| M5: sensor response after pump start | Compare pressure/flow onset with the subsequent temperature response and the predicted transport arrival. Separate a sensor response time from fluid transit and wall recovery. No response constant is chosen from a model bias. |
| M6: flow and lag | Reconstruct flow-in from pump strokes and declared pump displacement, compare it with return-flow measurements, and check the corresponding bottoms-up transport lag. Bottoms-up lag is the travel time from the bit to surface. Different meter calibration and partial losses can both alter the balance; pit-volume records distinguish them. |
| M7: 16A losses | Read daily-report loss entries alongside pit-volume changes, accounting for recorded transfers and additions. Compare their times with pressure and return flow. A volume deficit without a documented transfer supports loss; neither temperature bias nor a cooler annotation quantifies it. |
| M8: inlet-temperature agreement | Compare rig and mud-log channels at matched times after establishing sensor locations and inlet/outlet identity. The existing rig mud-temperature channel is outlet-like, so it cannot automatically be relabelled as inlet. Record missing inlet measurements. |
| M9: pressure residual remaining after entry 1 | Examine documented tool curves and differential-channel tare drift; verify pressure-transducer location and the flow-meter basis. Pressure dependence on flow and assembly identity can distinguish missing restrictions from an additive tare error. No proprietary tool curve is fitted to the residual. |

### Later superhot design questions

These items have no development-gap assignment. Each needs a separate physical scope and independently sourced parameters before implementation.

| Item | Later design purpose |
|---|---|
| Thermal-cracking regime flag | Identify conditions where cooling-induced distributed cracking can invalidate an elastic intact-rock calculation. |
| Fracture opening and weak-plane strength | Represent existing fracture opening and failure along weak planes, with orientation-dependent strength. |
| Brittle-to-ductile transition and creep | Account for temperature- and time-dependent deformation where elastic brittle failure ceases to be adequate. |
| E(T) | Use temperature-dependent Young's modulus in the thermoelastic stress calculation. |
| Static-hot column pressure | Calculate pressure from the reheated density profile during a static period. |
| Pump-start gel and surge | Evaluate transient start-up pressure from gel breaking and motion-induced pressure. |
| Loss-zone boundary condition | Allow fluid and enthalpy to leave the well at a specified loss interval. |

### Verified references for these declarations

The following author/year identities and DOI or stable publication URLs were checked on 28 October 2026. The cited works support candidate physics or input provenance; the rough FORGE effect estimates above are declarations, not results copied from those papers.

| ID | Reference |
|---|---|
| C1 | Chang, X., Zhou, J., Guo, Y., He, S., Wang, L., Chen, Y., Tang, M. and Jian, R. (2018). *Heat Transfer Behaviors in Horizontal Wells Considering the Effects of Drill Pipe Rotation, and Hydraulic and Mechanical Frictions during Drilling Procedures*. Energies 11(9), 2414. [DOI 10.3390/en11092414](https://doi.org/10.3390/en11092414). |
| C2 | Zhang, S., Fu, J., Peng, C., Su, Y., Zhang, H. and Yang, M. (2024). *The Analysis of Transient Temperature in the Wellbore of a Deep Shale Gas Horizontal Well*. Processes 12(7), 1402. [DOI 10.3390/pr12071402](https://doi.org/10.3390/pr12071402). |
| C3 | Sui, D. and Langåker, V.H. (2018). *Downhole Temperature Modeling for Non-Newtonian Fluids in ERD Wells*. Modeling, Identification and Control 39(2), 131–149. [DOI 10.4173/mic.2018.2.7](https://doi.org/10.4173/mic.2018.2.7). |
| C4 | Carslaw, H.S. and Jaeger, J.C. (1959). *Conduction of Heat in Solids*, second edition, Clarendon Press. [Published book, ISBN 9780198533689](https://books.google.com/books?id=y20sAAAAYAAJ). |
| C5 | Ramey, H.J., Jr. (1962). *Wellbore Heat Transmission*. Journal of Petroleum Technology 14(4), 427–435. [DOI 10.2118/96-PA](https://doi.org/10.2118/96-PA). |
| C6 | Hasan, A.R. and Kabir, C.S. (1994). *Aspects of Wellbore Heat Transfer During Two-Phase Flow*. SPE Production & Facilities 9(3), 211–216. [DOI 10.2118/22948-PA](https://doi.org/10.2118/22948-PA). |
| C7 | Allis, R., Gwynn, M., Hardwick, C., Hurlbut, W. and Moore, J. (2018). *Thermal Characteristics of the FORGE site, Milford, Utah*. GRC Transactions 42. [Original paper](https://publications.mygeoenergynow.org/grc/1033913.pdf). Only material-property evidence is used in this declaration. |
| C8 | Ajima, K. and Naganawa, S. (2022). *Evaluating Wellbore Cooling Effect with Insulated Drill Pipes in Supercritical Geothermal Well Drilling*. GRC Transactions 46, 805–818. [Original paper](https://publications.mygeoenergynow.org/grc/1034636.pdf). |
| C9 | Workstrings International (2025). *Drill Pipe Performance Sheet*, asset WS41-42, 1 August 2025, page 1. [Supplier catalogue](https://www.workstringsinternational.com/assets/Spec-Sheets/Drill%20Pipe/WS41-42-Imperial.pdf). |
| C10 | Abate, J. and Valkó, P.P. (2004). *Multi-precision Laplace transform inversion*. International Journal for Numerical Methods in Engineering 60(5–7), 979–993. [Author's listing](https://valko.engr.tamu.edu/numerical-methods-for-the-inversion-of-the-laplace-transform). Added 28 October 2026 for entry 3. |
| C11 | Johancsik, C.A., Friesen, D.B. and Dawson, R. (1984). *Torque and Drag in Directional Wells: Prediction and Measurement*. Journal of Petroleum Technology 36(6), 987–992. [DOI 10.2118/11380-PA](https://doi.org/10.2118/11380-PA). First presented as SPE 11380 at the 1983 IADC/SPE Drilling Conference. Added 28 October 2026 for entry 4. |

The BICO motor sheet is undated; its identity and contents were checked directly, without assigning a publication year from its URL. GDR source identities are McLennan et al. (2021), GDR 1283, [DOI 10.15121/1776602](https://doi.org/10.15121/1776602); Gilmour et al. (2021), GDR 1292, [DOI 10.15121/1777912](https://doi.org/10.15121/1777912); Jones (2022), GDR 1421, [DOI 10.15121/1893533](https://doi.org/10.15121/1893533); and McLennan et al. (2023), GDR 1516, [DOI 10.15121/1998591](https://doi.org/10.15121/1998591). These identify the development-data inputs for future diagnostics; no new observation is extracted here.

## 28 October 2026: D4, aggregate trial geometry in the comparison adapter

The first entry-1 run exposed an input-contract error. The revised hydraulic adapter indexes a serial-component table for every assembly. The frozen 16B plan intentionally has no such rows for EOW 17–20: their existing trial geometry is aggregate. Indexing those missing keys raises an exception before a solve. This is a coding error independent of the magnitude or direction of any temperature residual.

The correction will use the existing trial geometry, retaining every segment and its original thermal layers, and add the same declared connection scenario to its ordinary and heavy-weight pipe. The partial insulated trial must retain its lower regular-pipe section. The trial heavy-weight pitch remains the recorded 913.42 ft / 30; the ordinary pitch remains the approved 2,378 ft / 75. Aggregate collar and assembly passages remain aggregate, with no invented serial dimensions or tool curves. Other assemblies keep their existing adapter path. The frozen scoreboard script and its reductions do not change.

Prediction: the 45 trial samples become calculable without changing their sample identifiers or recorded inputs; the other 422 samples and all 16A run-in inputs are unchanged. No signed physical improvement in G1–G6 is predicted from this correction. The incomplete first run is retained outside the result archive and will not supply the accepted entry-1 score.

## 28 October 2026: entry 2 component pressure result

The [component archive](../../validation/model-development/entry-2/README.md) contains 22 median-depth windows, one per pressure-available assembly. All converged in 114.5 seconds. Every named pressure budget sums to standpipe pressure within 1 psi. The calculation uses the original 26.7 °C rheology reference and the same declared NC50/EIS scenarios as entry 1. No model function or parameter was changed for the diagnosis.

| 16A assembly | String-pressure increase from legacy, psi | Current bore connection contribution, psi | Current assumed motor-passage contribution, psi |
|---|---|---|---|
| 18 | 1,064 | 261 | 728 |
| 23 | 1,143 | 340 | 827 |
| 30 | 1,227 | 402 | 850 |
| 34 | 1,295 | 448 | 883 |
| 35r1 | 1,445 | 541 | 944 |
| 35r2 | 1,406 | 531 | 914 |
| 38 | 1,497 | 585 | 959 |
| 39 | 1,635 | 653 | 1,037 |
| 42 | 1,366 | 513 | 882 |

String increases are from `entry-2/pressure-budget.csv`, `string_increase_psi`. Connection contributions sum `bore_joint_replacement_psi` and `bore_joint_local_psi` in that file. Motor contributions sum `bore_body_psi` and `bore_geometric_local_psi` over motor rows in `entry-2/component-budget.csv`. All values are calculated. The two coupled calculations also have different temperature/property profiles, so subtracting their totals does not isolate a single geometric cause.

The connection contribution is substantial, but it does not explain the complete 16A increase. The 1.25-in motor-as-passage representation supplies 959 and 1,037 psi in the selected BHA 38 and 39 windows, with respective lengths about 10.8 m. This supports the assembly-passage explanation within the calculation. It does not establish a real motor's operating loss: a motor flow path is not necessarily an empty straight tube. An independently documented passage or pressure curve would distinguish a physical restriction from an inappropriate passage idealisation. No such curve is fitted here.

BHA 42 contains about 85 m of heavy-weight pipe, compared with about 426 m in BHA 38 and 39. Its heavy-weight body/local contribution is about 105 psi, compared with 548 and 596 psi. Its top ordinary-pipe segment is also shorter, about 2,098 m against 2,216 and 2,402 m, and its flow is lower. The current adapter applies ordinary connection losses to that top segment; ordinary-pipe intervals recorded inside the BHA 42 assembly have no repeated-joint term. Total well depth therefore cannot represent connection count consistently across these assemblies. This is a disclosed adapter limitation for a later declaration; the diagnosis makes no correction to the scored candidate.

Across the thirteen selected 16B assemblies, string increases are about 105–328 psi and current bore connection contributions about 75–209 psi. Those are selected-window calculations, not well-wide means. Every component's geometry and source is in the component archive. Trial runs retain their original aggregate passages. Unknown proprietary operating losses remain unspecified.

No new solver failure or unavailable case occurred in the diagnosis. The existing local-loss validity flags identify 16B BHA 11 and 12 as outside the published Newtonian Reynolds-number range at some restrictions. All cases flag the annular or Bingham transfer approximation. These diagnostics do not reject converged solves. No energy residual was flagged. The relative importance of the calculated terms does not establish the cause of a measured temperature error.

## 28 October 2026: entry 1 six-gap score

The [entry-1 archive](../../validation/model-development/entry-1/README.md) compares the approved legacy baseline with the declared NC50/EIS candidate at the original 26.7 °C viscosity reference. The completed candidate calculation took 1,058.8 seconds (17 minutes 38.8 seconds). All 467 circulation samples converged. All nine originally available run-in events were calculated, and the same two originally unavailable events remain unavailable. No energy residual was flagged. Every comparison population is unchanged.

Every number in the following tables is from `validation/model-development/entry-1/comparison.csv`. Before and after refer to legacy and entry 1. Bias is model minus measurement. The `group` column identifies the assembly, event or population, and `before_compared` / `after_compared` give the counts. Pressure percentage errors are means of paired sample percentages, not percentages of the group means.

### G1: Standpipe pressure

Columns: `before_bias`, `after_bias`, `before_mean_percent_error` and `after_mean_percent_error`.

| Well / assembly | Samples | Before bias, psi | After bias, psi | Before, % | After, % |
|---|---|---|---|---|---|
| 16A / 18 | 15 | -1,529 | -402 | -54.7 | -14.4 |
| 16A / 23 | 13 | -1,858 | -566 | -56.9 | -17.4 |
| 16A / 30 | 29 | -1,604 | -87 | -50.7 | -2.7 |
| 16A / 34 | 9 | -1,477 | -76 | -45.9 | -2.3 |
| 16A / 35r1 | 5 | -1,884 | -297 | -50.8 | -8.0 |
| 16A / 35r2 | 4 | -1,767 | -235 | -50.1 | -6.7 |
| 16A / 38 | 20 | -1,358 | 270 | -42.1 | 8.4 |
| 16A / 39 | 25 | -1,270 | 473 | -38.6 | 14.4 |
| 16A / 42 | 15 | -2,464 | -935 | -59.8 | -22.7 |
| 16B / 12 | 12 | -157 | 56 | -13.4 | 4.8 |
| 16B / 13 | 14 | -441 | -261 | -37.8 | -22.4 |
| 16B / 15 | 4 | -433 | -239 | -36.3 | -20.1 |
| 16B / 16 | 15 | -462 | -259 | -37.1 | -20.8 |

### G2: Hydraulic power

Columns: `before_model_mean`, `after_model_mean` and `after_measured_mean`. All values are kW.

| Well | Paired samples | Before model | After model | Measured |
|---|---|---|---|---|
| 16A | 135 | 500.0 | 908.0 | 928.3 |
| 16B | 109 | 264.3 | 349.9 | 526.5 |

### G3: 16A bore-at-bit temperature

Columns: `before_bias` and `after_bias`, in °C.

| Group or event | Compared / planned | Before bias | After bias |
|---|---|---|---|
| 18 | 15 / 15 | -4.1 | 4.3 |
| 23 | 13 / 13 | -0.2 | 9.7 |
| 30 | 29 / 29 | 2.4 | 14.9 |
| 34 | 9 / 9 | -0.7 | 11.4 |
| 35r1 | 5 / 5 | -3.1 | 11.1 |
| 35r2 | 4 / 4 | -8.9 | 5.1 |
| 38 | 20 / 20 | -8.1 | 7.1 |
| 39 | 25 / 25 | -9.7 | 6.4 |
| 42 | 15 / 15 | -19.8 | -4.1 |

### G4: 16A run-in peak error

Columns: `before_bias` and `after_bias`, in °C.

| Group or event | Compared / planned | Before bias | After bias |
|---|---|---|---|
| 23-off004 | 1 / 1 | -28.4 | -23.7 |
| 23-off005 | 1 / 1 | -13.9 | -13.8 |
| 23-off006 | 0 / 1 | unavailable | unavailable |
| 35r2-off001 | 1 / 1 | -6.5 | -6.5 |
| 35r2-off006 | 1 / 1 | -41.0 | -33.9 |
| 35r2-off008 | 0 / 1 | unavailable | unavailable |
| 38-off009 | 1 / 1 | -9.4 | -6.0 |
| 39-off004 | 1 / 1 | -10.1 | -10.1 |
| 39-off007 | 1 / 1 | -46.5 | -36.5 |
| 42-off004 | 1 / 1 | -46.0 | -32.7 |
| 42-off013 | 1 / 1 | -54.4 | -43.5 |

### G5: 16A return temperature

Columns: `before_bias` and `after_bias`, in °C.

| Group or event | Compared / planned | Before bias | After bias |
|---|---|---|---|
| ALL | 358 / 358 | -5.8 | -4.0 |
| Sanvean on-bottom | 135 / 135 | -6.0 | -4.1 |
| rig inferred bit depth, return only | 223 / 223 | -5.8 | -3.9 |

### G6: 16B temperature

Columns: `before_bias` and `after_bias`, in °C.

| Group or event | Compared / planned | Before bias | After bias |
|---|---|---|---|
| independent regular pipe | 59 / 59 | -8.8 | -6.9 |
| trial | 45 / 45 | 2.0 | 3.3 |
| 3 | 3 / 3 | -4.8 | -3.8 |
| 4 | 2 / 2 | -24.2 | -23.3 |
| 11 | 4 / 4 | -16.2 | -14.8 |
| 12 | 12 / 12 | -18.3 | -17.3 |
| 13 | 14 / 14 | -8.4 | -6.7 |
| 15 | 4 / 4 | -4.2 | -2.2 |
| 16 | 15 / 15 | -4.8 | -2.5 |
| 17 | 14 / 14 | 3.2 | 5.1 |
| 18 | 10 / 10 | 1.7 | 2.5 |
| 19 | 10 / 10 | 1.2 | 1.9 |
| 20 | 11 / 11 | 1.5 | 2.8 |
| 27 | 5 / 5 | -3.8 | -1.2 |
| 38 | 5 / 5 | -1.6 | 1.1 |

### Recommendation and physical interpretation

**Recommendation: revert the integrated entry-1 candidate as currently scored. The decision is pending; no reversion has been performed.** The added pressure and dissipation terms reduce the G1/G2 deficits, but the complete change produces substantial thermal deterioration on several assemblies and retains unresolved passage/joint representations. Those limitations prevent treating the pressure improvement as confirmation of this implementation.

Calculated: all nine 16A assembly mean bit temperatures increase by 8.4–16.1 °C, exceeding the earlier tenths-to-a-few-degrees estimate. Absolute mean bit bias worsens on five assemblies. BHA 42 improves from -19.8 to -4.1 °C, while BHA 30 changes from +2.4 to +14.9 °C. G5 improves by about 1.8 °C but remains about 4.0 °C cold. The independent 16B regular-pipe pool improves from -8.8 to -6.9 °C; the trial pool deteriorates from +2.0 to +3.3 °C. G4 remains non-conservative on all nine available events, with errors about -43.5 to -6.0 °C.

Calculated: entry 2 identifies large losses in the assumed straight motor passages, with substantial connection contributions and incomplete repeated-joint coverage inside the BHA 42 assembly. These are properties of the current representation. They do not measure the physical motor pressure curve. The remaining 16B power deficit also shows that entry 1 does not complete the hydraulic-power accounting.

Inferred: changes in the serial thermal geometry or internal bore/annulus exchange could contribute to the larger-than-predicted bit warming. An alternative is that the location and concentration of the added heat dominate that response. A later declaration can separate them using fixed thermal geometry and separately changed heat-source placement. That diagnostic has not been run. The closer 16A total-power values do not establish where the measured pump power is dissipated or converted into mechanical work.

No additional candidate or measurement diagnostic from the 28 October inventory was executed. No golden was regenerated, no slow suite was run, and no held-out validation target was read. The original fitted trial conductivity and transferred pitch remain as approved. Acceptance or reversion will be recorded after the decision.

## 28 October 2026: thermal-geometry and heat-placement diagnostic declaration

Entry 1 is not kept as scored; its code remains on the development branch while the bottom-hole assembly (BHA) representation is corrected. Before D5, separate its thermal geometry from its hydraulic heat sources using the same frozen samples and original 26.7 °C rheology convention. The original fitted trial insulation conductivity and declared NC50/EIS connection scenarios remain fixed.

Case A combines the legacy thermal geometry with the entry-1 distributed heat sources. Case B combines the entry-1 thermal geometry with legacy distributed heat sources. Motor face heat is unchanged in both cases. Each source calculation retains its own passage geometry and its original nozzle/property convention. Source terms are evaluated at the mixed calculation's fluid temperatures. A study-only boundary-value solver will compose the existing conductance and source functions without replacing a package function or changing its coefficients. Matched legacy/legacy and entry-1/entry-1 controls must reproduce the archived temperatures within 0.1 °C before the mixed cases are accepted. The package model remains unchanged for this diagnostic.

Predictions: if heat placement explains the temperature rise, case A should reproduce it, with a change comparable to the added-power scale. If thermal geometry explains it, case B should reproduce most of the earlier 8–16 °C bit rise. The declared comparison scale is the additional in-hole dissipation divided by mass flow and heat capacity, Delta P / (m_dot c_p), evaluated per bit-temperature sample using the archived complete legacy and entry-1 power results and legacy bit heat capacity. Report the sign and both temperature changes for every assembly, retaining individual sample values and the original sensor proxy.

This power quotient is a bulk, single-pass heating scale. It is not generally a strict upper bound on a local temperature in a counterflow well: heat exchanged from the rising annulus into the descending bore can increase a local temperature response without increasing the net heat returned at surface by the same factor. The requested within-bound prediction will be tested and exceedances flagged, with no clipping and no failed solve caused by that diagnostic. A violation would require interpreting the bound's assumptions as well as the temperature split.

The diagnostic will not change the model or select a corrected geometry. D5 will be declared separately from equipment descriptions and source records before re-scoring. Its justification cannot be whether a gap closes.

The diagnostic population is every original bit-temperature window: 135 on 16A and 109 on 16B. Report bit and return changes over these same windows by assembly. The 223 additional return-only 16A windows are outside this bit/return pairing; the later full scoreboard retains them for G5. Before the mixed cases, repeat both matched controls at each of the 22 previously declared median-depth windows. These controls check the study composition and introduce no candidate variant.

## 28 October 2026: D5 declaration, assembly passage representation

This is an equipment-representation correction. A positive-displacement motor carries flow through a rotor/stator power section; a reported local mandrel bore cannot define a straight pipe over its full length. The original report cells also show blank bit IDs and three blank instrument bores. These records justify the correction independently of any measured pressure or temperature residual.

The [component audit](../../validation/model-development/d5/README.md) separates 248 original or explicitly transferred component records from earlier adopted dimensions, across all 22 assemblies. It lists small bores and every filled or transferred dimension, with source locators. The actual short 1.25-inch PUK-sub bore in 16A BHA 18 remains. The ordinary-pipe 4.276-inch interpretation and earlier cross-assembly transfers remain identified. No blank ID is replaced by a neighbouring component's ID.

Motor hydraulic loss will be a total-internal tool curve, using a verified matching manufacturer's no-load pressure and the declared density-times-flow-squared scaling. No complete configuration/reference-condition match has been verified in the present sources. Every motor will therefore add zero internal pressure and carry **motor loss unknown**. The reported motor ID will have no hydraulic role. Motor thermal sections will use the adjacent collar bore as an explicit assumption, with their recorded outside diameter and length retained. Geometric bore contractions at these assumed motor interfaces will also be excluded from internal hydraulics; external annulus changes remain. The existing face heat from reported differential is unchanged. In 16A, standpipe pressure minus raw reported differential includes the motor's off-bottom drop. A complete future motor curve must represent this same pressure definition.

Bits will be nozzle boundaries, with no bit-body passage loss. For serial assemblies their small finite body lengths remain in the audit but are omitted from thermal segmentation. Total depth and all other component lengths remain fixed; the top ordinary-pipe closure increases by the omitted bit length. This small placement approximation does not assign a numerical value to a blank bit bore. In the original trial aggregate, no separate bit-body segment existed.

The trial motor will be separated from the remaining compact BHA, keeping the earlier transferred Figure 90 convention and existing trial section lengths. The non-motor compact dimensions will be recalculated from the same source components after excluding the motor. Its thermal bore will be the adjacent 3.25-inch collar assumption. This is confined to removing the motor's local bore from its full-length flow representation; the partial insulated-string layout remains unchanged.

The BHA 23 MWD tool and BHA 38/39 PUK subs remain unknown. Without an authorised and separately declared thermal assumption, those assembly calculations will be reported as unavailable, with all planned samples retained in the scoreboard inventory. No observational residual will supply a missing dimension. Instrument and valve passages with reported bores retain their body losses; unquantified operating losses remain limitations.

Estimated directions before re-scoring: removing fictitious narrow motor and bit passages should decrease calculated G1 pressure and G2 dissipation, potentially by several hundred psi and hundreds of kilowatts on 16A. No numerical pressure deficit is used to size this correction. G3 and G6 temperatures may decrease, with the sign also depending on changed internal heat exchange. G5 may decrease by a few degrees; G4 changes only through its existing circulation starting states. These are estimates, with unknown motor losses preventing complete pressure accounting. The frozen scoreboard, samples, 26.7 °C reference convention and NC50/EIS scenarios remain unchanged. No diagnostic result is used to select these corrections.

### 28 October 2026: authorised thermal assumption for three instruments

The original IDs of the BHA 23 MWD tool and BHA 38/39 PUK subs remain unknown. A 3.25-inch thermal-only bore is now explicitly authorised for these three components. Their internal hydraulic loss will be zero and flagged as unknown, including restrictions inferred from their assumed thermal interfaces. Their recorded lengths and outside diameters remain unchanged. This is an engineering assumption, with no dimension inferred from a pressure or temperature residual.

The first D5 execution retains 467 planned circulation cases. The missing bores prevented 156 circulation calculations and five previously available run-in calculations; these input failures are preserved separately. Complete only those cases using the unchanged frozen circulation and run-in functions with this declared assumption. Retain the already completed unaffected predictions, restore the original sample and event order, and calculate the full frozen scoreboard from the merged results. No comparison measure or sample changes. Report both execution durations and the source qualification for the retained batch. This completion method avoids repeating unaffected solves and is declared before calculating the newly authorised cases.


## 28 October 2026: geometry and heat separation results

Source: [mixed-case archive](../../validation/model-development/geometry-heat/README.md), `assemblies.csv`, paired by well/BHA and case. All changes are °C from the legacy calculation. Complete denotes the original entry 1. Power scale is added in-hole dissipation / (mass flow × legacy bit heat capacity).

| Well | BHA | Samples | Complete bit | A bit | B bit | Complete return | A return | B return | Power scale |
|---|---|---|---|---|---|---|---|---|---|
| 16A | 18 | 15 | 8.41 | 8.40 | 0.00 | 1.64 | 1.64 | -0.00 | 2.03 |
| 16A | 23 | 13 | 9.86 | 9.85 | 0.00 | 1.67 | 1.67 | -0.00 | 2.19 |
| 16A | 30 | 29 | 12.55 | 12.54 | 0.00 | 1.96 | 1.96 | -0.00 | 2.63 |
| 16A | 34 | 9 | 12.17 | 12.16 | 0.00 | 1.89 | 1.89 | -0.00 | 2.54 |
| 16A | 35r1 | 5 | 14.21 | 14.20 | 0.00 | 2.01 | 2.01 | -0.00 | 2.70 |
| 16A | 35r2 | 4 | 13.98 | 13.97 | 0.00 | 1.90 | 1.90 | -0.00 | 2.61 |
| 16A | 38 | 20 | 15.20 | 15.19 | 0.00 | 1.99 | 1.99 | -0.00 | 2.76 |
| 16A | 39 | 25 | 16.07 | 16.06 | 0.00 | 2.10 | 2.10 | -0.00 | 2.96 |
| 16A | 42 | 15 | 15.71 | 15.70 | 0.00 | 1.71 | 1.71 | -0.00 | 2.60 |
| 16B | 11 | 4 | 1.52 | 1.52 | 0.00 | 0.62 | 0.62 | -0.00 | 0.70 |
| 16B | 12 | 12 | 1.06 | 1.06 | 0.00 | 0.47 | 0.47 | -0.00 | 0.54 |
| 16B | 13 | 14 | 1.76 | 1.76 | 0.00 | 0.40 | 0.40 | -0.00 | 0.52 |
| 16B | 15 | 4 | 2.09 | 2.09 | 0.00 | 0.44 | 0.44 | -0.00 | 0.57 |
| 16B | 16 | 15 | 2.38 | 2.38 | 0.00 | 0.45 | 0.45 | -0.00 | 0.61 |
| 16B | 17 | 14 | 1.95 | 1.95 | 0.00 | 0.40 | 0.40 | 0.00 | 0.56 |
| 16B | 18 | 10 | 0.82 | 0.82 | -0.00 | 0.53 | 0.53 | 0.00 | 0.61 |
| 16B | 19 | 10 | 0.68 | 0.68 | -0.00 | 0.25 | 0.25 | 0.00 | 0.31 |
| 16B | 20 | 11 | 1.31 | 1.31 | -0.00 | 0.20 | 0.20 | -0.00 | 0.31 |
| 16B | 27 | 5 | 2.75 | 2.75 | 0.00 | 0.27 | 0.27 | -0.00 | 0.45 |
| 16B | 3 | 3 | 0.99 | 1.00 | -0.00 | 0.52 | 0.52 | 0.00 | 0.57 |
| 16B | 38 | 5 | 2.72 | 2.71 | 0.00 | 0.24 | 0.24 | -0.00 | 0.42 |
| 16B | 4 | 2 | 0.90 | 0.90 | -0.00 | 0.49 | 0.49 | 0.00 | 0.53 |

![Thermal geometry and heat split](../../validation/model-development/geometry-heat/thermal-heat-split.png)

Calculated: 44/44 matched controls pass at 0.1 °C. The mixed calculations contain 488/488 converged cases. Runtime was 1265.9 seconds, including controls. Per-sample outcomes and exceedances remain in `samples.csv`.

The heat-placement prediction has two parts: reproduction of the temperature rise and a within-scale condition. Their outcomes must be assessed separately. The bulk quotient does not impose a strict upper bound on a local bit temperature in the coupled counterflow equations. A larger local response can occur through bore/annulus exchange and changed formation heat transfer. This diagnostic does not independently partition those two contributions. D5 is justified by the equipment records, with no correction selected from the diagnostic.

## 28 October 2026: entry 1 with D5, frozen scoreboard

Sources: [corrected comparison archive](../../validation/model-development/d5/results/README.md), `comparison.csv`. Legacy is the approved baseline; original entry 1 is the second scored calculation; D5 is the corrected assembly representation. Full counts stay visible. Paired means and biases below use identical available sample IDs in all three calculations. Unavailable cases supply no numerical improvement.

### G1: standpipe pressure

| Well | Group / event | D5 compared / planned | Legacy bias | Original entry 1 bias | D5 bias | D5 mean error % |
|---|---|---|---|---|---|---|
| 16A | 18 | 15/15 | -1529.48 | -402.07 | -1132.15 | -40.50 |
| 16A | 23 | 13/13 | -1858.21 | -565.73 | -1467.37 | -44.96 |
| 16A | 30 | 29/29 | -1603.63 | -87.14 | -943.34 | -29.81 |
| 16A | 34 | 9/9 | -1477.33 | -76.48 | -988.46 | -30.69 |
| 16A | 35r1 | 5/5 | -1884.25 | -297.16 | -1277.44 | -34.43 |
| 16A | 35r2 | 4/4 | -1767.19 | -234.98 | -1172.75 | -33.28 |
| 16A | 38 | 20/20 | -1357.52 | 270.36 | -708.68 | -21.95 |
| 16A | 39 | 25/25 | -1269.88 | 473.50 | -563.95 | -17.12 |
| 16A | 42 | 15/15 | -2463.80 | -935.37 | -1874.97 | -45.53 |
| 16B | 12 | 12/12 | -157.31 | 56.49 | 50.19 | 4.27 |
| 16B | 13 | 14/14 | -440.94 | -261.36 | -267.27 | -22.90 |
| 16B | 15 | 4/4 | -432.76 | -239.16 | -245.10 | -20.56 |
| 16B | 16 | 15/15 | -462.11 | -258.87 | -264.83 | -21.28 |

Columns: `legacy_paired_bias`, `entry1_paired_bias`, `d5_paired_bias`; coverage uses `d5_compared` / `d5_planned`. Where D5 is unavailable, prior results marked full use `legacy_bias` or `entry1_bias` and make no paired-change claim. Bias is in psi; percentages use `d5_paired_mean_percent_error`.

### G2: in-hole hydraulic power

| Well | Group / event | D5 compared / planned | Legacy model kW | Original entry 1 kW | D5 model kW | Measured kW |
|---|---|---|---|---|---|---|
| 16A | paired pressure samples | 135/135 | 500.04 | 908.00 | 654.21 | 928.27 |
| 16B | paired pressure samples | 109/109 | 264.29 | 349.88 | 342.54 | 526.52 |

Columns: `legacy_paired_model_mean`, `entry1_paired_model_mean`, `d5_paired_model_mean`, `d5_paired_measured_mean`; coverage uses `d5_compared` / `d5_planned`. Where D5 is unavailable, prior results marked full use `legacy_bias` or `entry1_bias` and make no paired-change claim. Power is in kW.

### G3: 16A bit temperature

| Well | Group / event | D5 compared / planned | Legacy bias | Original entry 1 bias | D5 bias |
|---|---|---|---|---|---|
| 16A | 18 | 15/15 | -4.11 | 4.30 | -2.01 |
| 16A | 23 | 13/13 | -0.19 | 9.67 | 1.13 |
| 16A | 30 | 29/29 | 2.38 | 14.93 | 6.08 |
| 16A | 34 | 9/9 | -0.75 | 11.42 | 1.68 |
| 16A | 35r1 | 5/5 | -3.13 | 11.09 | -0.36 |
| 16A | 35r2 | 4/4 | -8.91 | 5.06 | -6.13 |
| 16A | 38 | 20/20 | -8.12 | 7.09 | -4.98 |
| 16A | 39 | 25/25 | -9.68 | 6.39 | -6.28 |
| 16A | 42 | 15/15 | -19.81 | -4.09 | -17.58 |

Columns: `legacy_paired_bias`, `entry1_paired_bias`, `d5_paired_bias`; coverage uses `d5_compared` / `d5_planned`. Where D5 is unavailable, prior results marked full use `legacy_bias` or `entry1_bias` and make no paired-change claim. Bias is in °C.

### G4: 16A run-in peak

| Well | Group / event | D5 compared / planned | Legacy bias | Original entry 1 bias | D5 bias |
|---|---|---|---|---|---|
| 16A | 23-off004 | 1/1 | -28.41 | -23.69 | -28.85 |
| 16A | 23-off005 | 1/1 | -13.87 | -13.78 | -13.87 |
| 16A | 23-off006 | 0/1 | unavailable | unavailable | unavailable |
| 16A | 35r2-off001 | 1/1 | -6.53 | -6.53 | -6.53 |
| 16A | 35r2-off006 | 1/1 | -40.97 | -33.85 | -42.13 |
| 16A | 35r2-off008 | 0/1 | unavailable | unavailable | unavailable |
| 16A | 38-off009 | 1/1 | -9.38 | -5.96 | -9.92 |
| 16A | 39-off004 | 1/1 | -10.15 | -10.15 | -10.15 |
| 16A | 39-off007 | 1/1 | -46.47 | -36.45 | -48.87 |
| 16A | 42-off004 | 1/1 | -45.96 | -32.71 | -49.42 |
| 16A | 42-off013 | 1/1 | -54.35 | -43.50 | -56.51 |

Columns: `legacy_paired_bias`, `entry1_paired_bias`, `d5_paired_bias`; coverage uses `d5_compared` / `d5_planned`. Where D5 is unavailable, prior results marked full use `legacy_bias` or `entry1_bias` and make no paired-change claim. Bias is in °C.

### G5: 16A return temperature

| Well | Group / event | D5 compared / planned | Legacy bias | Original entry 1 bias | D5 bias |
|---|---|---|---|---|---|
| 16A | ALL | 358/358 | -5.85 | -4.00 | -5.09 |
| 16A | Sanvean on-bottom | 135/135 | -6.00 | -4.11 | -5.22 |
| 16A | rig inferred bit depth, return only | 223/223 | -5.75 | -3.94 | -5.02 |

Columns: `legacy_paired_bias`, `entry1_paired_bias`, `d5_paired_bias`; coverage uses `d5_compared` / `d5_planned`. Where D5 is unavailable, prior results marked full use `legacy_bias` or `entry1_bias` and make no paired-change claim. Bias is in °C.

### G6: 16B sensor temperature

| Well | Group / event | D5 compared / planned | Legacy bias | Original entry 1 bias | D5 bias |
|---|---|---|---|---|---|
| 16B | independent regular pipe | 59/59 | -8.77 | -6.90 | -7.19 |
| 16B | trial | 45/45 | 1.99 | 3.25 | 3.03 |
| 16B | 3 | 3/3 | -4.80 | -3.81 | -3.86 |
| 16B | 4 | 2/2 | -24.17 | -23.26 | -23.31 |
| 16B | 11 | 4/4 | -16.18 | -14.76 | -15.53 |
| 16B | 12 | 12/12 | -18.27 | -17.32 | -17.35 |
| 16B | 13 | 14/14 | -8.42 | -6.72 | -6.77 |
| 16B | 15 | 4/4 | -4.21 | -2.18 | -2.23 |
| 16B | 16 | 15/15 | -4.80 | -2.48 | -2.54 |
| 16B | 17 | 14/14 | 3.18 | 5.13 | 4.90 |
| 16B | 18 | 10/10 | 1.69 | 2.52 | 2.40 |
| 16B | 19 | 10/10 | 1.18 | 1.85 | 1.65 |
| 16B | 20 | 11/11 | 1.49 | 2.80 | 2.49 |
| 16B | 27 | 5/5 | -3.80 | -1.16 | -2.34 |
| 16B | 38 | 5/5 | -1.56 | 1.05 | -0.08 |

Columns: `legacy_paired_bias`, `entry1_paired_bias`, `d5_paired_bias`; coverage uses `d5_compared` / `d5_planned`. Where D5 is unavailable, prior results marked full use `legacy_bias` or `entry1_bias` and make no paired-change claim. Bias is in °C.

### Bit-temperature changes and energy scales by assembly

Source: `bit-energy-assemblies.csv`. L denotes change from legacy; E denotes change from original entry 1. Temperatures and power scales are °C. The bit and the frozen sensor proxy remain distinct in the per-sample archive.

| Well | BHA | Compared / planned | L bit change | L return change | L power scale | E bit change | E power scale |
|---|---|---|---|---|---|---|---|
| 16A | 18 | 15/15 | 2.11 | 0.65 | 0.77 | -6.31 | -1.26 |
| 16A | 23 | 13/13 | 1.32 | 0.51 | 0.61 | -8.54 | -1.57 |
| 16A | 30 | 29/29 | 3.70 | 0.89 | 1.13 | -8.84 | -1.50 |
| 16A | 34 | 9/9 | 2.43 | 0.76 | 0.94 | -9.74 | -1.60 |
| 16A | 35r1 | 5/5 | 2.77 | 0.78 | 0.97 | -11.44 | -1.72 |
| 16A | 35r2 | 4/4 | 2.78 | 0.76 | 0.95 | -11.20 | -1.65 |
| 16A | 38 | 20/20 | 3.13 | 0.82 | 1.04 | -12.07 | -1.72 |
| 16A | 39 | 25/25 | 3.40 | 0.89 | 1.14 | -12.67 | -1.82 |
| 16A | 42 | 15/15 | 2.22 | 0.72 | 0.93 | -13.49 | -1.66 |
| 16B | 11 | 4/4 | 0.75 | 0.39 | 0.44 | -0.78 | -0.26 |
| 16B | 12 | 12/12 | 1.02 | 0.46 | 0.52 | -0.03 | -0.01 |
| 16B | 13 | 14/14 | 1.70 | 0.40 | 0.51 | -0.06 | -0.01 |
| 16B | 15 | 4/4 | 2.03 | 0.43 | 0.56 | -0.06 | -0.01 |
| 16B | 16 | 15/15 | 2.31 | 0.44 | 0.60 | -0.07 | -0.01 |
| 16B | 17 | 14/14 | 1.70 | 0.38 | 0.53 | -0.25 | -0.04 |
| 16B | 18 | 10/10 | 0.68 | 0.50 | 0.57 | -0.14 | -0.04 |
| 16B | 19 | 10/10 | 0.45 | 0.22 | 0.27 | -0.23 | -0.04 |
| 16B | 20 | 11/11 | 0.98 | 0.18 | 0.27 | -0.33 | -0.04 |
| 16B | 27 | 5/5 | 1.45 | 0.21 | 0.32 | -1.31 | -0.13 |
| 16B | 3 | 3/3 | 0.92 | 0.50 | 0.54 | -0.07 | -0.03 |
| 16B | 38 | 5/5 | 1.47 | 0.19 | 0.30 | -1.25 | -0.12 |
| 16B | 4 | 2/2 | 0.84 | 0.46 | 0.50 | -0.06 | -0.03 |

Columns: `legacy_bit_change_C`, `legacy_return_change_C`, `legacy_bulk_scale_C`, `entry1_bit_change_C`, `entry1_bulk_scale_C`. The archive also provides `assembly-power-return.csv` for all assembly-level G2 and G5 descriptive comparisons. The frozen well-level measures are unchanged.

### Interpretation, coverage and recommendation

Calculated: the heat-source case A reproduces every assembly mean bit rise from the original entry 1 within 0.02 °C. Thermal-geometry case B changes every assembly mean by less than 0.01 °C. On 16A, A raises the bit by 8.40–16.06 °C and the return by 1.64–2.10 °C. The corresponding archived power scales are 2.03–2.96 °C. The reproduction part of the heat-source prediction is supported; its within-scale condition fails at the bit. The thermal-geometry prediction is unsupported at the declared 0.1 °C resolution. These statements describe the calculation before D5, including its erroneous motor passages.

The counterflow equations exchange heat between ascending annulus fluid and descending bore fluid along the string. The power quotient describes a single traversal of the added heat. It does not limit the local temperature response after internal exchange. The small return rise and larger bit rise can coexist within those equations. The diagnostic separates the heat-source and thermal-geometry changes; it does not measure the individual contributions from internal exchange and formation heat-transfer feedback. No claim that either is the sole amplification mechanism is made.

Calculated after D5: 16A bit rises from legacy are 1.32–3.70 °C, with power scales 0.61–1.14 °C. Relative to the original entry 1, the corrected bit is cooler by 6.31–13.49 °C. The motor and bit corrections remove fictitious straight-passage dissipation. All nine 16A pressure means remain low, by about 564–1,875 psi. The 16B motorless means range from about -267 to +50 psi. These residuals retain their declared pressure definitions. Motor off-bottom losses remain unknown, so this is incomplete equipment accounting.

Calculated: G2 changes from legacy 500.04 to 654.21 kW on 16A, against measured pump power 928.27 kW. On 16B it changes from 264.29 to 342.54 kW, against 526.52 kW. These comparisons do not establish that all measured pump power becomes fluid heat. The deep-run bit biases are -4.98, -6.28 and -17.58 °C for BHA 38, 39 and 42. The BHA 30 warm bias increases from +2.38 to +6.08 °C; BHA 23 and 34 also have larger absolute mean biases than legacy. The pooled return bias improves from -5.85 to -5.09 °C. The 16B regular-pipe bias improves from -8.77 to -7.19 °C, while the trial bias increases from +1.99 to +3.03 °C. All nine available run-in peaks remain low, with errors -56.51 to -6.53 °C. The correction does not resolve the thermal gaps.

All 467 circulation cases and all nine originally available run-in cases complete. The two original unavailable events remain excluded from numerical comparison. No completed circulation case has an energy-residual flag. The initial missing-input batch took 886.31 seconds. Authorised completion of 156 circulation cases and five run-in events took 168.88 seconds, giving 1,055.19 seconds of scoring execution. The 311 unaffected circulation predictions and four unaffected run-in predictions are retained. Only the three declared instrument records change between audit batches. Source hashes and the batch distinction are in `d5/results/manifest.json`; original input failures remain in `initial-input-unavailable.csv`. Every assembly's motor and thermal-only qualifications are listed in `assembly-qualifications.csv`.

**Recommendation: keep entry 1 with D5 as the working development calculation. The acceptance decision remains pending.** The hydraulic terms have explicit physical definitions and published correlations; D5 removes equipment representations that were unjustified independently of their residuals. The recommendation does not depend on reproducing a rounded historical gap. Unknown motor losses require verified equipment curves, and the thermal gaps require their separately declared physics entries. The fitted trial insulation conductivity and FORGE-derived 16B connection pitch remain disclosed. This development score provides no independent validation.

No golden regeneration or slow suite was performed. No 56-32, 58-32 or 78B-32 target was read. No model correction was chosen from the geometry/heat diagnostic. No additional measurement diagnostic was run.

## 28 October 2026: decision on entry 1 with D5

Entry 1 with D5 is kept as the working development calculation. Later entries are declared and scored against it, and each comparison continues to report the legacy baseline beside it. The decision is based on the physical definitions of the hydraulic terms and on the equipment records behind D5. The gap changes are mixed and did not decide it: G2, G5 and the deep-run G3 biases improve, while the BHA 23, 30 and 34 biases and the trial bias grow. A review of the D5 commits by someone who did not write them followed; its outcome is recorded under 29 October 2026.

## 28 October 2026: entry 3 declaration, cylindrical rock response (R1)

This entry implements candidate R1, declared above before the first entry-1 score.

### Change

The circulation model passes heat from the rock to the annulus fluid through a resistance per unit length, in series with the annulus film and any hole lining. The rock part has been R = ln(1 + 2 sqrt(t_D)) / (2 pi k), where t_D = alpha t / a², a is the hole radius, alpha is the rock diffusivity and t is the exposure time. This logarithm is a quasi-steady approximation. The model's stated problem is a cylindrical hole in infinite, initially uniform rock whose wall temperature changes by a step and is then held. Its exact solution gives R = 1 / (2 pi k G(t_D)), where G is the inverse Laplace transform of K1(sqrt(s)) / (sqrt(s) K0(sqrt(s))) (reference C4). The new module `rock_response.py` computes G once by the fixed Talbot inversion of Abate and Valkó (2004, reference C10), for t_D from 1e-6 to 1e12, and interpolates it in log-log coordinates.

`tests/test_rock_response.py` checks the result in three ways. The tabulated G agrees with its short-time series to within 1e-6 relative for t_D up to 1e-4, and its departure from the two-term long-time series decreases with time. A finite-volume radial conduction solve gives the same wall flux within 0.5% at t_D = 0.03, 0.3, 3 and 30. The interpolated table agrees with direct inversion within 2e-5 relative.

Against the exact response, the logarithm overstates the rock resistance by 9.2% at t_D = 0.29, 6.5% at t_D = 7 and 4.9% at t_D = 211. For the 16A hole radius of 0.111 m and the frozen rock properties, these are exposures of one hour, one day and 30 days.

### What stays the same

The calculation is otherwise the working calculation, entry 1 with D5. The one-hour exposure floor, the cumulative exposure clock, the rock properties and the formation profiles are unchanged. The exact response does not need the floor, but removing it would be a separate change with its own declaration. The legacy mode, `hydraulics_model='v1.5.0'`, keeps the logarithm and reproduces the baseline. The frozen scoreboard, its samples and its conventions are unchanged, and nothing is fitted.

### Decision rule

The change replaces an approximation by the exact solution of the boundary problem the model already states. It comes from published theory, and no residual entered its choice. It will therefore be kept whatever the score, unless the score exposes an implementation error. The score will be reported in full, including the gaps that are predicted to worsen.

### Predictions

These come from a model-only calculation with [`predict.py`](../../validation/model-development/entry-3/predict.py). It takes one window per assembly, at the lower median bit-depth rank among the frozen circulation samples, and solves the working calculation with each rock response. No measurement was read. Changes are the exact response minus the logarithm, from `predictions.csv`.

| Well and assemblies | Bit change, °C | Return change, °C |
|---|---|---|
| 16A, BHA 18 to 35r2 | +0.47 to +0.95 | +0.10 to +0.16 |
| 16A, BHA 38, 39 and 42 | +1.16, +1.27 and +1.68 | +0.19 to +0.22 |
| 16B regular pipe (EOW 11, 12, 13, 15, 16, 27 and 38) | +0.22 to +2.03 | +0.13 to +0.23 |
| 16B trial (EOW 17 to 20) | +0.71 to +2.23 | +0.20 to +0.35 |
| 16B early runs (EOW 3 and 4) | +0.16 and +0.17 | +0.13 and +0.15 |

The expected score changes follow from these, assuming each window represents its assembly:

| Gap | Working calculation | Expected after entry 3 |
|---|---|---|
| G3, BHA 38, 39 and 42 | -4.98, -6.28 and -17.58 °C | about -3.8, -5.0 and -15.9 °C |
| G3, BHA 23, 30 and 34 | +1.13, +6.08 and +1.68 °C | each about 0.8 °C warmer, so worse |
| G5, all 358 samples | -5.09 °C | about -4.9 °C |
| G6, independent regular pipe | -7.19 °C | about -6.0 °C |
| G6, trial | +3.03 °C | about +4.6 °C, so worse |

G6 compares bore temperature 22 ft or 84 ft above the bit, so the bit change is a proxy for it. G1 and G2 change only through temperature-dependent fluid properties, and no numerical prediction is made for them. The run-in comparison (G4) starts from the circulation state before each trip. A warmer starting state should raise the predicted peaks, but no size is predicted.

## 28 October 2026: entry 3 score

Source: [entry 3 archive](../../validation/model-development/entry-3/results/README.md), `comparison.csv` and `assembly-changes.csv`. The declaration is commit `8c21e95` and the implementation `6de7abe`. All 467 circulation cases and all nine originally available run-in events completed. The sample counts equal those of the working calculation and the legacy baseline in every row, so every comparison below is paired. The scoring run took 803 seconds.

### Pressure and power (G1, G2)

Standpipe pressure falls by 0.8–3.5 psi on the nine 16A assemblies and by 1.2–1.6 psi on the four motorless 16B assemblies. The warmer fluid has a lower viscosity. Modelled in-hole power changes from 654.21 to 653.92 kW on 16A and from 342.54 to 342.46 kW on 16B, against measured 928.27 and 526.52 kW. No numerical prediction was made for these.

### Temperatures (G3, G4, G5, G6)

Biases in °C, model minus measured.

| Gap and group | Legacy | Working calculation | Entry 3 | Declared expectation |
|---|---|---|---|---|
| G3, BHA 18 | -4.11 | -2.01 | -1.53 | |
| G3, BHA 23 | -0.19 | +1.13 | +1.90 | about 0.8 warmer |
| G3, BHA 30 | +2.38 | +6.08 | +6.87 | about 0.8 warmer |
| G3, BHA 34 | -0.75 | +1.68 | +2.55 | about 0.8 warmer |
| G3, BHA 35r1 | -3.13 | -0.36 | +0.52 | |
| G3, BHA 35r2 | -8.91 | -6.13 | -5.21 | |
| G3, BHA 38 | -8.12 | -4.98 | -3.83 | about -3.8 |
| G3, BHA 39 | -9.68 | -6.28 | -5.00 | about -5.0 |
| G3, BHA 42 | -19.81 | -17.58 | -15.92 | about -15.9 |
| G5, all 358 samples | -5.85 | -5.09 | -4.93 | about -4.9 |
| G6, independent regular pipe | -8.77 | -7.19 | -5.97 | about -6.0 |
| G6, trial | +1.99 | +3.03 | +4.62 | about +4.6 |

The nine run-in peak errors (G4) change by 0.00 to +0.44 °C and now range from -56.23 to -6.53 °C. The declaration expected a positive sign without a size.

Over every sample, the mean bit change by assembly is +0.50 to +1.69 °C on 16A and +0.16 to +2.28 °C on 16B. The single-window predictions were +0.47 to +1.68 °C and +0.16 to +2.23 °C. The return changes are +0.11 to +0.22 °C on 16A and +0.12 to +0.37 °C on 16B.

### Interpretation and decision

The exact response lowers the rock resistance by about 5–8% for exposures between one hour and 30 days. More heat therefore reaches the fluid from the rock, and every circulating temperature rises. Each warm bias becomes larger, and the cold biases become smaller except where they cross zero: BHA 35r1 moves from -0.36 to +0.52 °C, so its absolute bias grows by 0.17 °C. The calculated changes reproduce the model-only predictions to within 0.1 °C in every row of the declaration table. The predictions used the same code on one window per assembly, so this agreement shows that those windows represent their assemblies. It is not an independent test of the physics.

The trial bias grows from +3.03 to +4.62 °C. The trial geometry uses an insulation conductivity that was fitted to 16B with the logarithmic rock term, so the fit may have absorbed part of that term's error. This log does not allow a refit. The check is an independently sourced value for the trial pipe's insulation (candidate P1).

Under the rule declared before scoring, entry 3 is kept: the score shows no implementation error. The calculation with entry 3 becomes the working calculation for later entries. The largest remaining temperature gaps are the deep 16A bit (BHA 42 at -15.92 °C), the 16A return at -4.93 °C, the cold 16B regular-pipe runs and every run-in peak. All of them are cold.

With entry 3 in place, the legacy mode still reproduces the baseline: all 2,614 archive checks pass, and its scoreboard differs from the saved baseline by at most 1.2e-4 °C, 2e-9 psi and 7e-7 kW. The same differences appeared when the baseline was reproduced on this computer before the change. The fast test suite passes. No golden regeneration or slow suite was run. No 56-32, 58-32 or 78B-32 target was read.

## 28 October 2026: entry 4 declaration, rotary heat (M2)

This entry implements candidate M2, declared before the first entry-1 score. The working calculation is entry 1 with D5 and entry 3.

### Inputs

The top drive turns the string, and its mechanical power, omega times torque, becomes heat in the well. The rig records give this power for every sample. [`build_rotary.py`](../../validation/model-development/entry-4/build_rotary.py) reads the ten-second records of GDR 1283 (16A) and GDR 1516 (16B). It takes the on-bottom rows with flow above 300 gal/min in each sample's frozen window: the centred 30 minutes on 16A and the frozen source rows on 16B. From them it records the mean rotary speed, the mean torque, the median weight on bit and the mean power. It also records the median off-bottom rotating torque, from rows with flow above 300 gal/min and speed above 20 rpm in the two hours before the window and during it. Only drive channels, flow and the on-bottom flag are read.

The 16A ten-second export labels top-drive torque in kft-lbs, but the values are ft-lbf. The on-bottom rotating median is about 4,300, the daily report for 26 November 2020 gives 6,500 at 50 rpm, and the raw export labels the same channel ft-lbs.

On the samples, the measured on-bottom rotary power has a median of 39 kW on 16A (interquartile range 4.5–89.5 kW) and 147 kW on 16B (78–206 kW). The low 16A values are sliding intervals, where the motor turns the bit and the string barely rotates. For comparison, the modelled in-hole hydraulic power is 654 kW on 16A and 342 kW on 16B.

### Placement

The power has two destinations. Friction where the string touches the casing or rock heats the annulus fluid along the string. Torque that reaches the bottom does work at the bit. The new module `rotary_heat.py` splits them with the soft-string torque model of Johancsik, Friesen and Dawson (reference C11). Each element of string presses on the wall with a force set by its buoyed weight, its tension and the hole's curvature. Friction torque per unit length is the friction factor times that force times the contact radius, which is the tool-joint radius where the pipe has joints.

The friction factor is set for each sample from its measured off-bottom torque, with no weight on bit. The same factor, with the measured weight on bit, then gives the on-bottom friction torque. The rest of the measured on-bottom torque does work at the bit. If the calculated friction exceeds the measured torque, the friction is scaled down to it and the bit receives none. Six 16A samples have no off-bottom reference and use the median factor of their assembly. Across the windows below, the factors are 0.11–0.32. No factor is adjusted.

The friction heat enters the annulus fluid where it is generated, averaged over 30 m, about one survey-station spacing. The bit share is added to the heat released at the bit. A new optional source in the circulation solve, `annulus_heat`, carries the friction heat; legacy mode rejects it.

### Assumptions

Each of these is a simplification of the torque balance or of where the heat goes:

- All friction heat enters the fluid locally. Part of it enters the casing and rock and only some of that returns to the fluid during the sample, so this is an upper limit for the fluid.
- All bit work enters the fluid at the bit, which is also an upper limit, since part heats the rock face and the cuttings.
- Viscous drag from rotation is part of the measured torque and is placed with the friction.
- The string has no bending stiffness and does not buckle, one friction factor applies in casing and open hole, and axial friction is neglected because the string is rotating.
- All wall layers have the density of steel, and connection steel is added over the connection length.
- Rotary speed and torque vary within a window. The mean power is used, and the torque in the split is that power divided by the mean speed.

The run-in comparison (G4) receives no rotary heat, because the rotation before each trip is not part of the frozen event inputs. G2 remains hydraulic power and excludes rotary power.

### What stays the same

The frozen scoreboard, its samples and its conventions are unchanged. [`score.py`](../../validation/model-development/entry-4/score.py) runs the frozen circulation and run-in functions and adds each sample's rotary heat to its solve. Nothing is fitted to a temperature, pressure or residual.

### Decision rule

The rotary power is measured, and conservation of energy requires it to appear as heat in the well. The torque balance and the factors come from the drilling literature and the off-bottom records. The entry will therefore be kept whatever the score, unless the score exposes an implementation error. The fraction that reaches the fluid stays an open uncertainty, and the treatment above is its upper limit. The score will be reported in full, including the gaps that are predicted to worsen.

### Predictions

These come from a model-only calculation with [`predict.py`](../../validation/model-development/entry-4/predict.py), on the windows used for entry 3. No measurement of temperature or pressure was read. Changes are from the working calculation, in `predictions.csv`.

| Well | Rotary power in the windows, kW | Bit change, °C | Return change, °C |
|---|---|---|---|
| 16A, nine windows | 3.4–126 | +0.09 to +3.68 | +0.02 to +0.53 |
| 16B, thirteen windows | 36–327 | +0.33 to +13.30 | +0.13 to +1.14 |

Three 16A windows (BHA 30, 34 and 39) fall in sliding intervals with under 5 kW of rotary power, so they do not represent their assemblies. Where the power exceeds 20 kW, the 16A bit rises 0.020–0.029 °C per kW and the return 0.004–0.006 °C per kW. The expected score changes below scale each assembly's mean measured rotary power by its window's response per kW, using the 16A median of 0.027 °C per kW where the window was sliding:

| Gap | Working calculation | Expected after entry 4 |
|---|---|---|
| G3, BHA 38, 39 and 42 | -3.83, -5.00 and -15.92 °C | about -2.1, -3.0 and -13.7 °C |
| G3, BHA 23, 30 and 34 | +1.90, +6.87 and +2.55 °C | about +2.7, +7.7 and +3.7 °C, so worse |
| G5, all 358 samples | -4.93 °C | about -4.7 °C |
| G6, independent regular pipe | -5.97 °C | about -1.5 °C |
| G6, trial | +4.62 °C | about +7.4 °C, so worse |

G6 compares bore temperature 22 ft or 84 ft above the bit, so the bit change is a proxy for it. G1 and G2 change only through temperature-dependent fluid properties. G4 is unchanged, because the run-in profiles receive no rotary heat.

## 28 October 2026: entry 4 score

Source: [entry 4 archive](../../validation/model-development/entry-4/results/README.md), `comparison.csv`, `assembly-changes.csv` and `rotary-heat-applied.csv`. The implementation is commit `a25a9d5`, the inputs `b4b8b36` and the declaration `e157fdf`. All 467 circulation cases and all nine originally available run-in events completed with the same sample counts as both reference calculations, so every comparison below is paired. The scoring run took 705 seconds.

### Rotary heat applied

Every circulation sample received its rotary heat; two had none because the string was not rotating. The friction factors have a median of 0.19 on 16A (range 0.02–0.32) and 0.24 on 16B (0.09–0.34). The median friction heat is 32 kW on 16A and 61 kW on 16B, and the median bit heat 11 kW and 86 kW. In 133 samples the calculated on-bottom friction exceeded the measured torque, so the friction was scaled to it and the bit received none. Six 16A samples used their assembly's median factor.

### Pressure, power and run-in (G1, G2, G4)

Standpipe pressure falls by 0.8–5.4 psi on 16A and 4.0–6.1 psi on 16B, from the warmer fluid's lower viscosity. Modelled hydraulic power changes by under 0.4 kW in either well. The run-in errors are unchanged, as declared.

### Temperatures (G3, G5, G6)

Biases in °C, model minus measured.

| Gap and group | Legacy | Working calculation | Entry 4 | Declared expectation |
|---|---|---|---|---|
| G3, BHA 18 | -4.11 | -1.53 | -1.03 | |
| G3, BHA 23 | -0.19 | +1.90 | +2.77 | about +2.7 |
| G3, BHA 30 | +2.38 | +6.87 | +7.58 | about +7.7 |
| G3, BHA 34 | -0.75 | +2.55 | +3.56 | about +3.7 |
| G3, BHA 35r1 | -3.13 | +0.52 | +1.22 | |
| G3, BHA 35r2 | -8.91 | -5.21 | -2.36 | |
| G3, BHA 38 | -8.12 | -3.83 | -2.09 | about -2.1 |
| G3, BHA 39 | -9.68 | -5.00 | -2.78 | about -3.0 |
| G3, BHA 42 | -19.81 | -15.92 | -13.63 | about -13.7 |
| G5, all 358 samples | -5.85 | -4.93 | -4.70 | about -4.7 |
| G6, independent regular pipe | -8.77 | -5.97 | -1.40 | about -1.5 |
| G6, trial | +1.99 | +4.62 | +7.55 | about +7.4 |

The pooled 16B regular-pipe bias hides a split. The shallow runs stay cold: EOW 4, 11 and 12 at -22.09, -14.53 and -14.61 °C. The deep runs are now warm: EOW 15, 16, 27 and 38 at +4.82, +5.30, +5.70 and +10.20 °C, and EOW 13 is at -1.95 °C. All four trial runs are warm, at +4.10 to +9.92 °C.

### Interpretation and decision

Measured rotary power reaches 340 kW on 16B and 130 kW on 16A, and it warms every circulating temperature that has rotary input. Two 16A samples on BHA 42, 16A-s0357 and 16A-s0358, record zero on-bottom torque and so receive none. On 16A it closes about 1.7–2.9 °C of the BHA 35r2, 38, 39 and 42 cold biases and widens the warm biases of BHA 23, 30 and 34 by about 0.7–1.0 °C. On 16B its effect is larger, because the power is larger and much of it reaches the bit. The deep 16B runs move from cold to warm.

The predictions used the same code and inputs on one window per assembly, so their agreement with the score shows only that the windows and the per-kW scaling represented the assemblies.

The declaration placed all rotary heat in the fluid, which is an upper limit on the energy the fluid receives. It is not a bound on every local temperature, because where the heat is released changes the exchange with the string and the rock (see the review outcome below). The warm deep 16B runs and trial runs are consistent with that limit overstating the fluid's share, but other explanations remain open: the fitted trial insulation, the unresolved 16B sensor positions and the soft-string simplifications. In the 133 capped samples the torque balance found more friction than the measured on-bottom torque allows, which suggests the off-bottom rows can overstate the friction, for example when they include reaming. A measured partition would separate these. The 16A downhole-torque channel and the 16B bit-torque channel, if their basis can be established, would measure the torque reaching the bottom.

Under the rule declared before scoring, entry 4 is kept: the score shows no implementation error, and every expected change was met within 0.25 °C. The calculation with entries 1 to 4 and D5 becomes the working calculation. The largest remaining gaps are BHA 42 at -13.63 °C, the 16A return at -4.70 °C, the shallow 16B runs, the warm 16B deep and trial runs, and every run-in peak.

With entry 4 in place, the legacy mode still passes all 2,614 baseline checks. The fast test suite passes. No golden regeneration or slow suite was run. No 56-32, 58-32 or 78B-32 target was read.

## 28 October 2026: stage 1, FORGE 56-32 standpipe pressure

This is the first comparison with a well that played no part in development. The protocol (`a1927b3`), its amendment (`8bbfe2c`) and the input completion with the primary predictions (`b357326`) were committed before any 56-32 pressure value was read. The v1.6.0 calculation is the working calculation of entries 1 and 3 with D5; entry 4 is not applied, because the registered extract has no torque. The [comparison archive](../../validation/forge56-32/comparison/README.md) gives every table.

Only BHA 9 and BHA 10 have complete inputs. Their BICO motor's 475 psi no-load loss has no stated reference flow, so each prediction is an interval about 2,000 psi wide at these flows, with its lower end at a 700 gal/min reference. On the 196 secondary on-bottom windows, the lower end of the primary v1.6.0 interval (PV at 48.9 °C) has a median residual of -295 psi (-9.2%) on BHA 9 and +234 psi (+7.2%) on BHA 10. For v1.5.0 the same figures are -1,079 psi (-33.4%) and -696 psi (-21.7%). With PV at 26.7 °C, v1.6.0's lower end is -439 psi and +16 psi. The six primary off-bottom events are consistent with this at depth, and two shallow trip events disagree with every calculation in ways the inputs don't explain.

The difference between v1.5.0 and v1.6.0 comes mostly from the connection losses. Setting the NC50 restriction length to zero lowers the v1.6.0 prediction by 620–730 psi. That scenario is a catalogue transfer, the same one used for 16A, with no measured connection bore behind it. On this well, with those connection losses included, the median residual at the low end of the motor-loss range is within 10% for both assemblies, where v1.5.0's falls 20–35% short. The comparison can't establish the motor's actual loss, and it can't separate the connection scenario from the motor's reference flow.

This result was not used to change any entry, input or setting.


## 29 October 2026: independent review of D5, entry 3 and entry 4

A review by someone who did not write the commits reran the D5, entry 3 and entry 4 calculations, rederived the cylindrical rock response and the soft-string torque balance, and checked the declarations against the commit order. It found nothing that reverses a decision. D5 stays as the working equipment representation, and entries 3 and 4 stay kept within their declared scope. The reruns reproduced the archived results: for entry 4, to within 0.0007 °C in circulation temperature and 0.0004 psi in standpipe pressure.

### Corrections to the declarations

The declarations are left as committed. These statements in them were inaccurate or too broad:

- Entries 3 and 4 say that no measurement, or no measured temperature or pressure, was read by the prediction scripts. The scripts used no scored target and no residual: no bit, MWD or return temperature target and no standpipe-pressure target. They did use measured operating inputs, as declared elsewhere: the inlet temperature, the reported motor differential for the face heat, the flow, and the formation temperature and exposure, which come from observations. Entry 4 also used the measured rotary inputs.
- The entry 4 field inventory for `build_rotary.py` omitted the timestamps, which set the windows, and the 16B bit-depth and hole-depth columns, which are read and not used. A sample's off-bottom reference also needs at least three qualifying rows.
- Entry 4 called the placement of all rotary heat in the fluid an upper limit. It is an upper limit on the rotary energy the fluid receives, and not on each local temperature. In the review's check on a capped 16B sample, moving the whole 78.7 kW to the bit raised the bit temperature by 1.38 °C and lowered the return by 0.07 °C. The partition between friction and bit work is a separate uncertainty.

The results sections have been corrected where the review found the same kind of overstatement: the entry 3 pressure range, the BHA 35r1 bias that crosses zero, and the two entry 4 samples with no rotary input.

### Code changes from the review

- The continuous annulus source joined the cell values linearly, and its exact integral differed from the friction heat by up to 5.4 W in 467 samples (0.016%). It is now scaled so that its integral equals the friction heat, and the solve reports the integral exactly. In the review's check on 16A-s0218, this changes the bit temperature by 0.0001 °C. The archived entry 4 results were calculated before the change and are not rerun.
- The 16A and 16B energy diagnostics used the logarithmic rock term whatever the diagnosed solve had used. They now take the solve's rock term.
- The entry 3 and entry 4 comparison scripts treated a row as paired when the calculations compared the same number of samples. They now also require the same successful samples. The archived comparisons are unchanged under the stricter check.

### Left open

- Before entry 4 is used as evidence of how rotary heat divides between the wall and the bit, the off-bottom reference rows need an audit of the operation, axial movement, speed and depth in each. In the five capped samples the review examined, the off-bottom speed was 1.74 to 2.25 times the on-bottom speed, so the reference torque can include speed-dependent drag and reaming.
- The motor-loss candidates considered for D5 and not adopted should be listed with the reason for each, so that no unmatched manufacturer figure is later read as a verified loss.

## 29 October 2026: entry 5 declaration, measured 16B mud rheology (I1)

### Change

For 16B, the frozen scoreboard keeps the original S1 mud ("s1_original"). Where a run's mud report gave no plastic viscosity or yield point, S1 filled the field from BoreTHM's reference programme mud: PV 27 cP and YP 28 lbf/100 ft², a weighted-mud value. Seven assemblies carry these fills:

- EOW 11 and 12: PV and YP;
- EOW 13 and 15–18: YP.

They are inconsistent with the recorded low-solids, water-rich fluid. The S2 protocol (`validation/forge16b/comparison_protocol_s2.md`, committed at `d4a4c12`) replaces a missing PV or YP with the nearest actual measurement, in either time direction, within the same fluid system. If the system has no measurement, it uses water rheology at the recorded density.

This entry scores the working calculation with the S2 mud for 16B. The fills become PV 1–2 cP and YP 1 lbf/100 ft². For EOW 16–18 the rule also replaces a PV of 2 cP, which S1 carried from an earlier period sample, with the nearest measurement of 1 cP. Every donor, its source page and its time offset are in `validation/forge16b/s2/mud-revision-ledger.csv`. Some donors come from after the run, and some are days away. 16A uses the run-averaged daily-report measurements and is unchanged.

The fills matter now because the next entry's candidate makes the yield stress decide whether the annulus flow is laminar. They also matter for the 16B pressure: the working calculation already treats the annulus as laminar for these runs, and a laminar Bingham pressure loss includes a yield-stress term.

### Provenance

The S2 rule was adopted in the 16B whole-well study after its S1 comparison had been seen. That study's revised results, under the earlier calculation, are already in the [validation guide](validation.md): the EOW 11, 12, 16, 17 and 18 run means warmed by 0.4–8.5 °C. This entry is therefore not blind to the direction of the temperature change. Its justification is input consistency: measured values replace a value taken from a different mud. Agreement with the targets played no part.

### What stays the same

The calculation is entry 4's working calculation. The scoreboard samples, the 16B densities, the geometry, the PV reference temperature of 26.7 °C, the fitted trial insulation conductivity and the legacy baseline are unchanged. The baseline keeps S1's mud, so that it reproduces the original blind result.

### Decision rule

The entry replaces default values with measurements under a protocol committed before this development work. It will be kept whatever the score, unless the score exposes an implementation error. The score will be reported in full, including the gaps predicted to worsen.

### Predictions

These come from a model-only calculation with [`predict.py`](../../validation/model-development/entry-5/predict.py). It uses the 16B windows of entries 3 and 4 and solves the working calculation with each mud record. The inputs are the frozen operating inputs, the rotary inputs and the two mud records. No scored temperature or pressure target, and no residual, was read. Changes are S2 minus S1, from `predictions.csv`.

| EOW assembly | Mud, S1 → S2 (PV cP / YP lbf/100 ft²) | Bit change, °C | Return change, °C | Standpipe change, psi |
|---|---|---|---|---|
| 11 | 27/28 → 2/1 | +7.6 | −1.2 | −576 |
| 12 | 27/28 → 2/1 | +11.3 | −1.4 | −545 |
| 13 | 2/28 → 2/1 | −0.8 | −0.2 | −165 |
| 15 | 2/28 → 2/1 | −0.9 | −0.2 | −182 |
| 16 | 2/28 → 1/1 | +4.8 | −0.7 | −275 |
| 17 | 2/28 → 1/1 | +4.6 | −0.8 | −284 |
| 18 | 2/28 → 1/1 | 0.0 | −0.5 | −293 |
| 3, 4, 19, 20, 27, 38 | unchanged | 0 | 0 | 0 |

The expected score changes follow from these, assuming each window represents its assembly:

| Gap | Working calculation | Expected after entry 5 |
|---|---|---|
| G1, 16B BHA 12, 13, 15 and 16 | +43, −273, −253 and −272 psi | about −500, −440, −435 and −550 psi, so worse |
| G2, 16B | −184 kW | more negative, by the dissipation of the removed yield-stress loss |
| G6, EOW 11 and 12 | −14.53 and −14.61 °C | about −7 and −3 °C |
| G6, EOW 16 and 17 | +5.30 and +9.92 °C | about +10 and +14.5 °C, so worse |
| G6, independent regular pipe | −1.40 °C | about 3 °C warmer |
| G6, trial | +7.55 °C | about 1 °C warmer, so worse |

The G6 group values are rough, because the window changes within each group range widely. 16A (G1–G5 for 16A) is unchanged.

## 29 October 2026: entry 5 score

Source: [entry 5 archive](../../validation/model-development/entry-5/results/README.md), `comparison.csv` and `assembly-changes.csv`. The declaration is commit `72b5281`. All 467 circulation cases and all nine originally available run-in events completed with the same sample counts as both reference calculations, so every comparison below is paired. All 109 16B samples received their S2 mud. The scoring run took 727 seconds.

### Pressure and power (G1, G2)

| Gap and group | Legacy | Working calculation | Entry 5 | Declared expectation |
|---|---|---|---|---|
| G1, 16B BHA 12 | −157 psi | +43 psi | −481 psi | about −500 psi |
| G1, 16B BHA 13 | −441 psi | −273 psi | −439 psi | about −440 psi |
| G1, 16B BHA 15 | −433 psi | −253 psi | −435 psi | about −435 psi |
| G1, 16B BHA 16 | −462 psi | −272 psi | −546 psi | about −550 psi |
| G2, 16B | −262 kW | −184 kW | −239 kW | more negative |

The yield-stress term of the laminar annulus loss had supplied much of the 16B pressure that entry 1 appeared to gain. With the measured yield point of 1 lbf/100 ft², the 16B motorless runs are 435–546 psi below the measured standpipe pressure. The legacy baseline also uses the reference mud, so it is not a like-for-like comparison: EOW 13 and 15 happen to lie within 2 psi of their legacy deficits, EOW 16 is 84 psi further below, and EOW 12, where the reference mud also supplied a PV of 27 cP, is 324 psi further below. 16A pressures are unchanged.

### Temperatures (G6)

Biases in °C, model minus measured.

| Group | Legacy | Working calculation | Entry 5 | Declared expectation |
|---|---|---|---|---|
| EOW 11 | −16.18 | −14.53 | −5.94 | about −7 |
| EOW 12 | −18.27 | −14.61 | −3.63 | about −3 |
| EOW 13 | −8.42 | −1.95 | −2.72 | |
| EOW 15 | −4.21 | +4.82 | +3.89 | |
| EOW 16 | −4.80 | +5.30 | +10.14 | about +10 |
| EOW 17 | +3.18 | +9.92 | +14.75 | about +14.5 |
| EOW 18 | +1.69 | +4.10 | +4.19 | |
| Independent regular pipe | −8.77 | −1.40 | +2.40 | about 3 °C warmer |
| Trial | +1.99 | +7.55 | +9.08 | about 1 °C warmer |

The assembly means change as the window predictions did: EOW 11 and 12 by +8.5 and +10.9 °C, EOW 16 and 17 by +4.8 °C each, and EOW 13, 15 and 18 by under 1 °C. Return temperatures fall by 0.2–1.4 °C. Assemblies whose mud does not change, and all of 16A, differ from entry 4 by at most 0.0006 °C, from the exact rotary-source scaling added after entry 4 was scored. G3, G4 and G5 are unchanged.

### Interpretation and decision

The reference mud's PV of 27 cP on EOW 11 and 12 lowered the film coefficient and cooled those runs. Its YP of 28 lbf/100 ft² raised the 16B standpipe pressure. With measurements in their place, the two shallow cold runs move most of the way to the measurements, the deep and trial runs become warmer, and the 16B pressure deficit returns to about its legacy size. The current calculation does not explain the remaining 16B pressure deficit.

Under the rule declared before scoring, entry 5 is kept: the score shows no implementation error, and every expected change was met within 1.1 °C and 20 psi. The calculation with entries 1 to 5 and D5 becomes the working calculation. For the annulus heat-transfer entry, the 16B runs with measured mud are water-like: they have a yield point of 1 lbf/100 ft², except EOW 3 and 4 at 8 and 7.

With entry 5 in place, the legacy mode still passes all 2,614 baseline checks. The fast test suite passes. No 56-32, 58-32 or 78B-32 target was read.

## 30 October 2026: entry 6 declaration, Herschel–Bulkley annulus with three downhole yield-stress hypotheses (A1)

### Change

The candidate replaces two treatments in the annulus: the Bingham pressure loss with its apparent-viscosity criterion, and the Dittus–Boelter film coefficient on plastic viscosity. One flow treatment now gives both the annulus pressure loss and the annulus heat transfer. The bore, the bit nozzles, the local entry and exit losses and the run-in transient are unchanged. It is selected with `annulus_model='herschel-bulkley'` and a mud carrying a `fluids.HerschelBulkley` rheology.

**Rheology.** Each mud is a Herschel–Bulkley fluid, τ = τ0 + Kγⁿ, built from its report.

- The report's PV and YP give the 600 and 300 rpm dial readings, R600 = 2PV + YP and R300 = PV + YP.
- With a low-shear yield stress τ0 in the same dial units, n = ln((R600 − τ0)/(R300 − τ0))/ln 2 and K = (R300 − τ0)·0.5113 Pa/511ⁿ.
- The conversions are API RP 13D's: 1.0678 lbf/100 ft² per dial degree, and 1022 and 511 s⁻¹ at 600 and 300 rpm.
- K follows the plastic viscosity's temperature dependence, which is water's. Alderman et al. (1988) found that the high-shear viscosity of bentonite muds follows water's, with activation energies of 1.2–2.4 × 10³ K against water's 1.7 × 10³ K. They also found that n rises with temperature; n is held constant here.

**Flow.** The annulus is a slot, after Founargiotakis, Kelessidis and Maglione (2008).

- The slot's gap is h = (d_o − d_i)/2. The laminar wall stress τ_w solves their eq. 5 at the mean velocity.
- A wall stress gives the local flow index n′ (eq. 14) and K′ (eq. 15). The generalised Reynolds number is Re = ρV^(2−n′)(d_o − d_i)^n′/(K′ 12^(n′−1)) (eq. 13).
- Flow is laminar below Re1 = 3250 − 1150n′ and turbulent above Re2 = 4150 − 1150n′. Between them the Fanning friction factor is interpolated linearly in Re from 24/Re1 to the Dodge–Metzner value at Re2 (eqs. 18–21). Above Re2 it is the Dodge–Metzner value (eq. 16).
- The pressure gradient is 2fρV²/(d_o − d_i) (eq. 17), solved as their figure 2 describes.
- The friction factor is not allowed below the laminar 24/Re at the same Re. In Dodge and Metzner's chart the transitional and turbulent curves lie above the laminar line. Their correlation falls below it only for n′ under about 0.4, outside their data (n′ 0.36–1.0), which happens when the yield stress approaches the wall stress. Without the bound, the equations can have several roots there.
- The annulus body and the tool-joint passages both use this treatment.

**Heat transfer.**

- **Regime.** The position in the Founargiotakis band sets the regime, so heat transfer and friction change regime together.
- **Turbulent.** Gnielinski's annulus correlation (Gnielinski 2009, eqs. 22–24) applies, with separate factors for the string wall and the hole wall. Re and Pr use the wall viscosity μ_w = τ_w/γ_w, the rheology's viscosity at the wall stress. In turbulent flow the thermal resistance lies in the viscous wall layer. The 27 October candidate list named this wall apparent viscosity.
- **Laminar.** The fully developed values of Lundberg, Reynolds and Kays (1963) apply for each wall. Soares, Naccache and Souza Mendes (2003) found the inner-wall laminar Nusselt number insensitive to Herschel–Bulkley rheology.
- **In the band.** The film coefficient is linear in Re between the two, with the friction factor's weights. Gnielinski (2013) interpolates the same way between Re 2300 and 4000 in tubes.
- **Range.** Gnielinski states the annulus correlation for Re > 10⁴. His tube correlation of the same form is stated from Re 4000. Using the annulus form down to Re2, which is about 2,900–3,900 here, is our extension.

**Solution path.** Each candidate solve starts from the converged working solution of the same sample. If it does not converge from there, it falls back to the usual uniform-exposure seeds. The seeds alone also converge, to the same answers within 0.01 °C on the windows checked, but they need meshes of up to 15,000 nodes.

### Why it replaces the Wilson–Thomas candidate

`bec37fe` added a Bingham candidate: the Wilson and Thomas (2006) criterion with the report YP, shared with the pressure loss. It was never scored, and it is removed.

**Why.** Wilson and Thomas derived their criterion for Bingham fluids in pipes. A drilling mud's Bingham YP is extrapolated from 300 and 600 rpm, and it overstates the low-shear yield stress. For three field muds, Kelessidis et al. (2006) fitted Herschel–Bulkley yield stresses of 0–35% of the Bingham YP, none above the 3-rpm reading. The Founargiotakis model was built for drilling muds in annuli. Kelessidis, Dalamarinis and Maglione (2011) tested it on bentonite dispersions in a flow loop, where transition began between Re 2,800 and 4,000.

**What was seen.** Model-only checks found that the regime depends on which yield stress is used: with the YP, every 16A window is laminar under Wilson–Thomas; with Herschel–Bulkley and the 10-s gel, none is. These checks read no target.

### Hypotheses

The reports give no low-shear viscometer readings and no rheology test temperature. So the downhole yield stress τ0 is not measured. This entry declares three hypotheses and scores each.

| Hypothesis | τ0 | Basis |
|---|---|---|
| no-yield | 0 | The lowest value the reports allow; n and K are then the power-law fit to R600 and R300 |
| gel | The 10-s gel, at all temperatures | The gel is read at 3 rpm after 10 s at rest, so it is at least the 3-rpm reading, which Kelessidis et al. (2006) found no fitted yield stress to exceed. It is the upper estimate of the surface yield stress. |
| gel-rising | The 10-s gel up to T* = 330 K (57 °C); above it, gel × exp(E_H(1/T* − 1/T)) with E_H = 2.9 × 10³ K | Alderman et al. (1988, eqs. 8–9) found the yield stress of water-based muds constant up to a characteristic temperature T*, then rising exponentially with 1/T. T* and E_H are read from their fig. 8, for their unweighted mud, to about 10%. The factor is 1.8 at 80 °C, 2.7 at 100 °C and 3.4 at 110 °C. |

T* depends on the clay's surface chemistry, and deflocculants raise it. The FORGE muds' T* is not known, so gel-rising takes the one published value.

**Gel inputs.** The gels are in [`gel_inputs.csv`](../../validation/model-development/entry-6/gel_inputs.csv), built by [`build_gel.py`](../../validation/model-development/entry-6/build_gel.py) from report inputs only.

- **16A:** each run's mean 10-s gel over its report dates, the same rows and averaging that give its PV and YP, 4.0–8.0 lbf/100 ft².
- **16B:** the S2 rule applied to the gel.
  - EOW 3 and 4 have 3 lbf/100 ft²; EOW 3's value comes from the next day's sample.
  - The post-clean fluid of EOW 11–38 has no gel measurement, so τ0 is 0 under every hypothesis.

### Provenance

This entry is not blind. The gaps' directions are known from entries 1–5, and the 16A deep runs are colder than measured.

**Model-only work before this declaration.** None of it read a target.

- Sensitivity runs of the Wilson–Thomas package.
- Regime checks under Wilson–Thomas and Herschel–Bulkley.
- A scan of τ0 at 1, 2, 3 and 5 times the gel.
- A comparison of three viscosities for the turbulent film coefficient on four windows: the Metzner–Reed apparent viscosity, the wall viscosity and the plastic viscosity. The Metzner–Reed viscosity halved the film coefficient of the water-like 16B runs, whose n of 0.58–0.74 comes from dial readings of 2–5 degrees. The candidate uses the wall viscosity, which the 27 October list named.

### What stays the same

- **The working calculation.** Entries 1–5 with D5, including the rotary heat and the S2 16B mud.
- **The frozen setup.** The scoreboard samples, the PV reference temperature of 26.7 °C, the fitted trial insulation conductivity and the legacy baseline.
- **G4.** Run-in transients keep their Dittus–Boelter films, so G4 is not rescored.

### Decision rule

The three hypotheses are scored on the frozen scoreboard. None becomes the working calculation under this entry. Which one is correct depends on the downhole mud, and the reports do not measure that. A mud recap with low-shear readings and test temperature, or measured rheology of a FORGE-type mud at temperature, would decide. The hypothesis it supports would then be adopted in a later entry.

The score will be reported in full for each hypothesis, beside the working calculation. The discriminating measures are:

- the root-mean-square of the nine 16A assembly bit biases (G3, all assemblies);
- the 16A standpipe biases (G1);
- the 16A return bias (G5).

Differences under 2 °C in RMS bit bias will not be called. The water-like 16B runs do not discriminate, because τ0 is 0 there under every hypothesis.

If the score exposes an implementation error, it will be corrected in its own entry.

### Predictions

These come from a model-only calculation with [`predict.py`](../../validation/model-development/entry-6/predict.py), over the windows of entries 3 and 4. Changes are each hypothesis minus the working calculation, from `predictions.csv`. All 22 windows converged under every hypothesis. The last column gives the shares of the drill-pipe annulus that the slot model puts in laminar, transitional and turbulent flow at the solved temperatures.

| Window | Gel, lbf/100 ft² | Bit change, °C (no-yield / gel / gel-rising) | Standpipe change, psi | Drill-pipe annulus laminar/transitional/turbulent, % (no-yield; gel; gel-rising) |
|---|---|---|---|---|
| 16A BHA 18 | 4.0 | −5.6 / −14.3 / −19.4 | −73 / −53 / −38 | 0/0/100; 0/100/0; 21/79/0 |
| 16A BHA 23 | 5.0 | −4.1 / −7.2 / −16.5 | +2 / −4 / +23 | 0/0/100; 0/13/87; 0/100/0 |
| 16A BHA 30 | 7.5 | −6.4 / −29.8 / −31.8 | −85 / +19 / +35 | 0/0/100; 0/100/0; 100/0/0 |
| 16A BHA 34 | 8.0 | −7.8 / −34.0 / −34.0 | −80 / +8 / +14 | 0/0/100; 100/0/0; 100/0/0 |
| 16A BHA 35r1 | 7.0 | −6.6 / −12.5 / −29.2 | −5 / +5 / +65 | 0/0/100; 0/0/100; 0/100/0 |
| 16A BHA 35r2 | 7.0 | −7.6 / −14.1 / −30.0 | −1 / +14 / +67 | 0/0/100; 0/28/72; 0/100/0 |
| 16A BHA 38 | 5.0 | −6.3 / −12.8 / −13.9 | 0 / −6 / +5 | 0/0/100; 0/0/100; 0/0/100 |
| 16A BHA 39 | 5.0 | −9.5 / −14.4 / −14.9 | +11 / +9 / +23 | 0/0/100; 0/6/94; 0/31/69 |
| 16A BHA 42 | 4.5 | −8.9 / −16.3 / −20.2 | +1 / −13 / +12 | 0/0/100; 0/0/100; 0/15/85 |
| 16B EOW 3 | 3.0 | −2.0 / −6.4 / −6.4 | −8 / +4 / +4 | 0/0/100; 88/12/0; 88/12/0 |
| 16B EOW 4 | 3.0 | −1.7 / −6.1 / −6.1 | −6 / +11 / +11 | 0/0/100; 100/0/0; 100/0/0 |
| 16B EOW 11 | 0.0 | −0.1 / −0.1 / −0.1 | 0 / 0 / 0 | 0/0/100; 0/0/100; 0/0/100 |
| 16B EOW 12 | 0.0 | −0.6 / −0.6 / −0.6 | 0 / 0 / 0 | 0/0/100; 0/0/100; 0/0/100 |
| 16B EOW 13 | 0.0 | −0.5 / −0.5 / −0.5 | 0 / 0 / 0 | 0/0/100; 0/0/100; 0/0/100 |
| 16B EOW 15 | 0.0 | −0.4 / −0.4 / −0.4 | 0 / 0 / 0 | 0/0/100; 0/0/100; 0/0/100 |
| 16B EOW 16 | 0.0 | +0.5 / +0.5 / +0.5 | −2 / −2 / −2 | 0/0/100; 0/0/100; 0/0/100 |
| 16B EOW 17 | 0.0 | +0.7 / +0.7 / +0.7 | −3 / −3 / −3 | 0/0/100; 0/0/100; 0/0/100 |
| 16B EOW 18 | 0.0 | +0.1 / +0.1 / +0.1 | −3 / −3 / −3 | 0/0/100; 0/0/100; 0/0/100 |
| 16B EOW 19 | 0.0 | +1.3 / +1.3 / +1.3 | −4 / −4 / −4 | 0/0/100; 0/0/100; 0/0/100 |
| 16B EOW 20 | 0.0 | +1.9 / +1.9 / +1.9 | −5 / −5 / −5 | 0/0/100; 0/0/100; 0/0/100 |
| 16B EOW 27 | 0.0 | +1.9 / +1.9 / +1.9 | −5 / −5 / −5 | 0/0/100; 0/0/100; 0/0/100 |
| 16B EOW 38 | 0.0 | +1.4 / +1.4 / +1.4 | −3 / −3 / −3 | 0/0/100; 0/0/100; 0/0/100 |

Return temperatures change by +0.1 to +1.4 °C on 16A and by −0.4 to +0.05 °C on 16B.

Every hypothesis cools 16A. Even with no yield stress, the shear-thinning wall viscosity, at 1.3–1.6 times PV, and Gnielinski's lower annulus coefficient give a film coefficient below the current Dittus–Boelter value on PV. With the gel, BHA 30 and 34 are in the transition band or below it, where the laminar coefficient is two orders of magnitude lower. Under gel-rising, BHA 23, 35r1 and 35r2 also move into the band. The water-like 16B runs change by under 2 °C. EOW 3 and 4 become laminar with the gel and cool by about 6 °C.

The expected score changes follow from these, assuming each window represents its assembly:

| Measure | Working calculation | no-yield | gel | gel-rising |
|---|---|---|---|---|
| RMS of the nine 16A assembly bit biases (G3) | 5.6 °C | about 10 °C | about 20 °C | about 25 °C |
| G3, 16A BHA 38, 39 and 42 | −2.1, −2.8 and −13.6 °C | about −8, −12 and −22 °C | about −15, −17 and −30 °C | about −16, −18 and −34 °C |
| G3, 16A BHA 23, 30 and 34 | +2.8, +7.6 and +3.6 °C | about −1, +1 and −4 °C | about −4, −22 and −31 °C | about −14, −24 and −31 °C |
| G1, 16A | −573 to −1,881 psi | changes of −85 to +11 psi | changes of −53 to +19 psi | changes of −38 to +67 psi |
| G5, 16A return | −4.70 °C | about 0.3 °C warmer | about 0.7 °C warmer | about 0.9 °C warmer |
| G6, EOW 3 and 4 | −2.6 and −22.1 °C | about 2 °C colder | about 6 °C colder | about 6 °C colder |
| G6, other 16B runs | | within 2 °C | the same as no-yield | the same as no-yield |
| G1, 16B BHA 12, 13, 15 and 16 | −435 to −546 psi | within 3 psi | the same | the same |

All three hypotheses are expected to widen the 16A temperature gaps. If the score confirms it, then under every downhole yield stress the reports allow, the sourced annulus treatment leaves 16A colder than measured. Part of the agreement of the working calculation would then come from Dittus–Boelter on plastic viscosity, which has no basis for a yield-stress mud. Annulus effects still outside the model would also come into question: eccentricity, rotation and the flow disturbance at tool joints.

## 30 October 2026: entry 6 score

**Sources.** The [entry 6 archive](../../validation/model-development/entry-6/results/README.md): `summary.csv`, `comparison.csv` and `assembly-changes.csv`. The declaration is commit `492f1b8`, pushed before scoring.

**Coverage.** Under every hypothesis, all 467 circulation cases and all nine originally available run-in events completed. The sample counts match both reference calculations, so every comparison below is paired. G4 equals the working calculation.

**Run times.** The scoring runs took 2,076 s (no-yield), 1,837 s (gel) and 1,928 s (gel-rising).

### Declared summary measures

| Calculation | RMS of the nine 16A assembly bit biases | Mean of the nine | RMS of the 16A standpipe biases | 16A return bias (G5) |
|---|---|---|---|---|
| Legacy | 8.59 °C | −5.81 °C | 1,724 psi | −5.85 °C |
| Working calculation | 5.62 °C | −0.75 °C | 1,190 psi | −4.70 °C |
| no-yield | 10.04 °C | −7.73 °C | 1,213 psi | −4.35 °C |
| gel | 19.69 °C | −17.95 °C | 1,193 psi | −3.96 °C |
| gel-rising | 24.58 °C | −23.54 °C | 1,170 psi | −3.88 °C |

The declaration expected RMS values of about 10, 20 and 25 °C, and return biases 0.3, 0.7 and 0.9 °C warmer than the working calculation. The scores are 10.0, 19.7 and 24.6 °C, and 0.35, 0.74 and 0.82 °C warmer.

### 16A bit temperatures (G3)

Biases in °C, model minus measured.

| BHA | Legacy | Working calculation | no-yield | gel | gel-rising |
|---|---|---|---|---|---|
| 18 | −4.11 | −1.03 | −6.55 | −15.27 | −19.70 |
| 23 | −0.19 | +2.77 | −1.19 | −4.23 | −12.55 |
| 30 | +2.38 | +7.58 | +0.91 | −22.04 | −25.24 |
| 34 | −0.75 | +3.56 | −4.70 | −31.94 | −31.95 |
| 35r1 | −3.13 | +1.22 | −5.28 | −10.47 | −22.55 |
| 35r2 | −8.91 | −2.36 | −9.79 | −16.57 | −33.34 |
| 38 | −8.12 | −2.09 | −8.11 | −14.22 | −15.48 |
| 39 | −9.68 | −2.78 | −12.83 | −18.37 | −19.58 |
| 42 | −19.81 | −13.63 | −22.05 | −28.43 | −31.52 |

The assembly mean changes differ from the window predictions by at most 5.6 °C. The largest differences are in BHA 34 under no-yield (−11.1 against −7.8 °C) and BHA 35r1 under gel-rising (−23.6 against −29.2 °C). There, an assembly's samples lie on both sides of the transition band.

### Pressure and power (G1, G2)

- **16A standpipe.** Changes from the working calculation are −89 to +11 psi under no-yield, −56 to +18 psi under gel and −40 to +69 psi under gel-rising. The 16A deficits stay between 545 and 1,892 psi. The annulus loss is a small part of the 16A standpipe pressure, so its treatment does not settle the 16A deficit.
- **16B motorless runs.** These change by under 3 psi.
- **G2.** The modelled 16A in-hole power changes by −10 to −1 kW, and 16B by under 1 kW.

### 16B temperatures (G6)

- **Water-like runs.** For EOW 11–38 the three hypotheses are identical, since τ0 is 0 there. Bit temperatures change by −0.5 to +1.7 °C. The independent regular-pipe bias moves from +2.40 to +2.55 °C, and the trial bias from +9.08 to +9.97 °C.
- **EOW 3 and 4.** Under no-yield these cool by about 2 °C, to −4.54 and −23.76 °C. Under gel and gel-rising they cool by about 6 °C, to −8.7 and −28.0 °C.

### Interpretation and decision

Every expected change was met. The order of the hypotheses is as declared, and the RMS differences between them, 9.6 and 4.9 °C, are above the 2 °C threshold.

On 16A, the lower the downhole yield stress, the closer the score. no-yield is closest, but it is still 7.7 °C colder than the measurements on average across the nine assemblies. It is also 4.4 °C worse in RMS than the working calculation. Under gel and gel-rising, BHA 30 and 34 are in transitional or laminar flow and are 22–32 °C too cold. The 16A data are therefore inconsistent with a transitional or laminar annulus at those runs. That conclusion would fail only if some effect outside the model raises the laminar heat transfer several times over. Drill-string rotation is the main candidate for that; eccentricity would act the other way. The working calculation's closer agreement comes from Dittus–Boelter on plastic viscosity, which has no basis for a yield-stress mud. So that agreement is not evidence for its physics.

Two explanations fit the no-yield result.

- **Missing annulus physics.** The downhole yield stress is close to zero, and some annulus effect still outside the model raises the turbulent film coefficient. The candidates are rotation, the flow disturbance at tool joints and the entrance effect after each joint.
- **The wrong viscosity.** The wall-viscosity choice understates turbulent heat transfer for these muds. The 16A wall viscosities are 1.3–1.6 times PV. In the model-only check before the declaration, Gnielinski on PV gave 0.94–0.97 of the Dittus–Boelter film coefficient along BHA 38's annulus, and Gnielinski on the wall viscosity gave 0.75–0.84. So most of the no-yield cooling comes from the viscosity choice, which is still unsourced.

The non-Newtonian heat-transfer source requested (Chhabra and Richardson, chapter 6), a quantified rotation term (Abdelhafiz 2023) and the 16A mud recap would separate these explanations.

Under the rule declared before scoring, no hypothesis becomes the working calculation. Entries 1–5 with D5 remain the working calculation. The candidate stays in the package as `annulus_model='herschel-bulkley'`, unused by default. No 56-32, 58-32 or 78B-32 target was read.

## 30 October 2026: entry 7 declaration, plastic-viscosity heat transfer and the Erge transition band (A2)

### Change

Entry 7 changes two elements of entry 6's candidate. It is selected with `annulus_model='herschel-bulkley-erge'`. Entry 6's `annulus_model='herschel-bulkley'` is unchanged; its predictions reproduce exactly.

**Turbulent heat transfer on the plastic viscosity.** Gnielinski's annulus correlation (Gnielinski 2009, eqs. 22–24) now takes Re and Pr on the plastic viscosity at the local state, in place of entry 6's wall viscosity.

- Chhabra and Richardson (2008, §6.9) give two turbulent correlations for non-Newtonian fluids:
  - For purely viscous fluids, Yoo's (eq. 6.54), on the viscosity at the nominal wall shear rate.
  - For particulate suspensions with 0.42 ≤ n ≤ 0.89, the Sieder–Tate form on the Bingham plastic viscosity (eq. 6.55).
- A drilling mud is a suspension of bentonite and barite. The 16A muds' n values from PV, YP and the gel are 0.57–0.85, inside the range of eq. 6.55.
- Gnielinski on PV agrees with eq. 6.55 to within 2% at the working calculation's states, and it keeps separate factors for the string wall and the hole wall.
- The same book cites Peixinho et al. (2007): in fully turbulent flow, the yield stress does not affect heat transfer.

**The transition band of Erge et al. (2015).** It replaces Founargiotakis' band in both the pressure loss and the heat transfer.

- Erge et al.'s Reynolds number 12ρV²/τ_w and flow index N use the same slot as Founargiotakis. Their band (eqs. 17–18) is Re1 = 2100 [N^0.331 (1 + 1.402κ − 0.977κ²) − 0.019εN^−0.868 κ] and Re2 = 2900 N^(−0.039 Re1^0.307), with κ the local diameter ratio and N = n′.
- Eq. 17 follows from their stability analysis and is stated for 0.1 < N < 1. Eq. 18 is fitted to their measurements at κ = 0.5 and 0.15 < N < 0.4. The 16A muds' N of 0.27–0.39 and κ of 0.57 lie within or close to those ranges.
- Outside 0.15–0.4, eq. 18 is evaluated at the nearest end of the range. This keeps Re2 above Re1 up to N = 1, and it affects only the water-like 16B runs, which are far above Re2.
- Eccentricity is taken as zero, because the model does not represent the pipe's position in the hole. Full eccentricity would lower Re1 by 2–3% for these muds and Re2 by under 1%.
- For the 16A muds the band is about 2,000–4,900, against Founargiotakis' 2,800–3,850.
- In the band the friction factor is interpolated linearly from 24/Re1 to the Dodge–Metzner value at Re2, as Erge et al. do after Founargiotakis. Over this wider band the gradient can fall by up to about 5% with increasing velocity before the flow is turbulent; it rises outside the band. The heat transfer is interpolated with the same weights.

Everything else is entry 6's:

- the slot model and the bound on the friction factor;
- the laminar annulus values;
- the gel inputs and the three hypotheses (no-yield, gel, gel-rising);
- the solution path starting from the working solution.

### Provenance

This entry is not blind to entry 6's score, which showed every hypothesis too cold at 16A. Liam supplied both sources after that score: Chhabra and Richardson's §6.9 and Erge et al. (2015, SPE 167950). Before choosing, he saw model-only comparisons:

- the film coefficient under each viscosity at four window states;
- the two bands at each 16A window.

He chose Gnielinski on PV over eq. 6.55 as published, and Erge's band over Founargiotakis'. No new target was read.

**The basis for each element:**

- The viscosity follows the fluid class, a particulate suspension. Its effect is known in direction: it warms 16A relative to entry 6.
- The band follows the annulus geometry and the range of N, and its effect on temperature was not computed before the choice.

### What stays the same

As entry 6:

- the working calculation (entries 1–5 with D5);
- the scoreboard samples and the PV reference temperature of 26.7 °C;
- the fitted trial insulation;
- the legacy baseline;
- G4.

### Decision rule

This is entry 6's rule. The three hypotheses are scored on the frozen scoreboard, and none becomes the working calculation under this entry, because the downhole yield stress is unmeasured. The summary measures are:

- the RMS of the nine 16A assembly bit biases;
- the 16A standpipe biases;
- the 16A return bias.

RMS differences under 2 °C are not called. An implementation error found by the score is corrected in its own entry.

### Predictions

These come from a model-only calculation with [`predict.py`](../../validation/model-development/entry-7/predict.py), on the same windows. Changes are each hypothesis minus the working calculation, from `predictions.csv`. All 22 windows converged under every hypothesis.

| Window | Bit change, °C (no-yield / gel / gel-rising) | Standpipe change, psi | Drill-pipe annulus laminar/transitional/turbulent, % (no-yield; gel; gel-rising) |
|---|---|---|---|
| 16A BHA 18 | −1.6 / −8.4 / −11.8 | −79 / −58 / −45 | 0/30/70; 0/100/0; 0/100/0 |
| 16A BHA 23 | −1.4 / −4.3 / −11.1 | −3 / −5 / +24 | 0/0/100; 0/100/0; 0/100/0 |
| 16A BHA 30 | −2.2 / −15.3 / −23.3 | −94 / −14 / +23 | 0/0/100; 0/100/0; 0/100/0 |
| 16A BHA 34 | −2.0 / −19.3 / −26.3 | −91 / −25 / +7 | 0/2/98; 0/100/0; 0/100/0 |
| 16A BHA 35r1 | −1.0 / −5.3 / −17.7 | −15 / −4 / +70 | 0/0/100; 0/100/0; 0/100/0 |
| 16A BHA 35r2 | −1.1 / −7.4 / −18.6 | −13 / +7 / +68 | 0/0/100; 0/100/0; 0/100/0 |
| 16A BHA 38 | −1.2 / −1.3 / −4.4 | −12 / −33 / −5 | 0/0/100; 0/0/100; 0/67/33 |
| 16A BHA 39 | −1.9 / −4.4 / −9.3 | −11 / −15 / +21 | 0/0/100; 0/47/53; 0/100/0 |
| 16A BHA 42 | −1.9 / −2.3 / −11.9 | −9 / −31 / +21 | 0/0/100; 0/15/85; 0/91/9 |
| 16B EOW 3 | +0.1 / −3.9 / −4.2 | −13 / −1 / 0 | 0/0/100; 0/100/0; 0/100/0 |
| 16B EOW 4 | −0.1 / −4.3 / −4.3 | −11 / +6 / +6 | 0/0/100; 0/100/0; 0/100/0 |
| 16B EOW 11–38 | −0.6 to +0.6, the same under each | −5 to −1 | turbulent |

Return temperatures change by −0.05 to +0.12 °C on 16A under no-yield, +0.02 to +0.95 °C under gel and +0.14 to +1.23 °C under gel-rising. On 16B they change by under 0.15 °C.

**Reading the predictions:**

- No window is laminar. Erge's onset is low enough that the yield stress moves cells into the band and no further.
- With no yield stress, the plastic-viscosity film coefficient leaves 16A within about 2 °C of the working calculation.
- The gel hypotheses cool 16A through transitional cells, where the film coefficient is interpolated towards the laminar value.

The expected score changes follow, assuming each window represents its assembly:

| Measure | Working calculation | no-yield | gel | gel-rising |
|---|---|---|---|---|
| RMS of the nine 16A assembly bit biases (G3) | 5.6 °C | about 6.0 °C | about 9.6 °C | about 16.8 °C |
| Mean of the nine | −0.75 °C | about −2.3 °C | about −8.3 °C | about −15.7 °C |
| G3, 16A BHA 38, 39 and 42 | −2.1, −2.8 and −13.6 °C | about −3.3, −4.7 and −15.5 °C | about −3.4, −7.2 and −15.9 °C | about −6.5, −12.0 and −25.6 °C |
| G1, 16A | −573 to −1,881 psi | changes of −94 to −3 psi | changes of −58 to +7 psi | changes of −45 to +70 psi |
| G5, 16A return | −4.70 °C | within 0.1 °C | about 0.4 °C warmer | about 0.7 °C warmer |
| G6, EOW 3 and 4 | −2.6 and −22.1 °C | within 0.1 °C | about 4 °C colder | about 4 °C colder |
| G6, other 16B runs | | within 0.6 °C | the same as no-yield | the same as no-yield |

If the score confirms these, the hypotheses would still be ranked as in entry 6. The difference between no-yield and the working calculation, 0.4 °C in RMS, would be below the 2 °C threshold.
