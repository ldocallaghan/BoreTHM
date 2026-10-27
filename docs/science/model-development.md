# Model development

This log records changes to BoreTHM's physical calculations and their comparison with development observations. A declaration describes the equations, inputs and predicted effects before a new comparison. Its subsequent score uses the same sample list and reports every gap, including deterioration. Reverted candidates remain in the disclosure table.

## Data statement

FORGE 16A and 16B are development data. Their observations have already been examined and cannot provide an independent validation of changes motivated by their errors. FORGE 56-32, 58-32 and 78B-32 remain reserved for later validation, with targets opened once in declared stages. The 56-32 and 58-32 input archives and pressure protocols remain unchanged. Their pressure target values have not been inspected or compared. The 78B-32 targets remain unread.

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

The justification is the solver domain and continuity of its equations. Closing a field-data gap is not its justification. Endpoint correction alone did not resolve the overlapping-transition case. The combined correction converged on that same input. No signed change is predicted for G1–G6; the purpose is to obtain valid solutions for declared geometry. Synthetic component tests retain this correction. A separate six-gap score has not been made.

## 27–28 October 2026: D2, energy diagnostic and boundary accuracy

Commit `8e6d0b9` tightened the boundary-condition tolerance to 1e-10 K because a small turnaround residual exceeded an excessively precise power check. The pressure/heat source integrals agreed. This diagnostic discrepancy did not establish failure of the physical boundary-value solve.

Restore the original solver tolerance: profile tolerance 1e-4, with the solver's default boundary tolerance. Report assigned power, applied power and their residual. Flag a residual exceeding the larger of 1 W and 0.1% of the compared powers. A failed diagnostic evaluation is also flagged and returned. Neither case changes solver success or raises a diagnostic exception to the caller. Solver convergence and finite physical temperatures remain separate checks.

Prediction: the representative deep-well solve remains converged at the original tolerance, and its small power residual is acceptable at the declared reporting resolution. No material G1–G6 change is expected from removing unnecessary boundary precision. Any actual convergence failure must be identified; tolerance tightening is permitted only for such a demonstrated convergence need. No physical gap score is authorised by this numerical check.

The original tolerance has been restored. The deep-well reference and both short-component convergence cases pass at that tolerance. Tests also confirm that a flagged residual or an exception inside the diagnostic leaves a converged solve successful. No tested case requires a tighter boundary tolerance. The six-gap candidate comparison remains pending.

## 27 October 2026: D3, programme forwarding

Commit `0b89980` corrected the design-comparison adapter after the evaluator acquired a hydraulic-programme argument. The adapter must pass the declared programme and casing shoe to the geometry builder. This is an interface correction, justified by the argument contract. No coefficient was chosen from a prediction error, and no physical improvement in G1–G6 is claimed.

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
