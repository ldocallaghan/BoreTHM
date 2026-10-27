# FORGE 16B and 16A: S2 protocol revision and energy comparison

27 October 2026. Baseline `85f23db51f6661e6ca09bd05c16b9ffb48881d83`. This revision is made after S1 review, from the recorded inputs and the reviewed ruling. The original S1 protocol, its 109 sample windows and all S1 results remain unchanged. The 16A blind comparison also remains unchanged. No parameter is fitted and no model function, constant, default, golden result or regression tolerance is changed.

## Revised 16B mud inputs

The S1 reference PV of 27 cP and YP of 28 lbf/100 ft² describe the reference programme mud. Applying them to missing cells in 16B's low-solids, approximately 99.5% water mud is inconsistent with the recorded fluid description. This is the reason for revising the missing-cell rule. Preserve S1's primary as version 1 and label the revised primary version 2.

Keep S1's run-associated source mud rows and recorded density means. For a missing PV or YP, select the nearest actual measurement in either time direction within the same fluid system, resolving an exact time tie to the earlier measurement. Save the donor, its signed time difference and source locator. If the system has no measurement of that field, use water viscosity (`pv_ref=None`) or zero yield point, at the recorded mud density. Do not replace recorded density or the mixture's thermal properties with pure water.

Retain the S1 fluid-system boundaries at intermediate cementing and the 12 May pit drain/clean. Add a boundary at 17 June 14:00, when the report records building and pumping high-viscosity hole-cleaning sweeps after TD (EOW p321). The subsequent 18 June 05:00 `Other Location` rheology sample must not be carried backwards into the drilling-fluid system. The sweep passing the bit during the final drilling interval is flagged as context; no transient composition is inferred. These distinctions use report inputs, before the new predictions.

Rerun only the 109 cumulative-clock, film-1.0 primary samples with revised mud. Recalculate the original 109 primary cases separately to recover their profiles for diagnostics and verify agreement with the saved S1 predictions. This does not replace S1. The original recovery and film sensitivities retain their version-1 input definitions; no revised recovery experiment is implied.

## 16A sensitivity and replay

Retain all 358 frozen primary sample centres and original inputs, including the 135 Sanvean downhole samples and 223 return-only samples. Replay the original primary to obtain profiles and check its temperatures against the archive. Then run a labelled sensitivity using water viscosity and zero yield point at each recorded mud density. Use the unchanged Mud mixture, inlet-density mass-flow conversion and existing solver. Keep all four sensor branches: bore/annulus at the bit and 40 ft above it. No closest-endpoint scoring is introduced. Preserve the 216-day formation profile with its constant endpoint and the original geometry, exposure and washout flags.

There are 934 planned solves: two versions of 109 16B primary samples and two rheology treatments of 358 16A primary samples. Store solver flags and failures. Replay differences are reported separately, with the existing seeded-solve agreement of 0.01 °C as a diagnostic flag; published blind values and regression tolerances are unchanged.

## Regime and annulus film

An annulus has a depth-dependent Reynolds number and film coefficient. Save a profile on cells split at every geometry change and a uniform grid no coarser than 25 m, sampled at cell midpoints. Report per-sample length-weighted means and laminar length fractions, with minima and maxima. Also save values at every requested sensor position and at the bit. Use actual local temperatures and the existing approximate pressure profile.

Thermal Reynolds number is the model's `m_dot * Dh / (area * plastic_viscosity)`. The heat-transfer correlation uses a laminar floor below Re 2300. The reported annulus film coefficient is the unchanged `h_dittus` output times the declared film multiplier, not the overall rock conductance. For Bingham hydraulics, separately report the apparent-viscosity Reynolds number from `bingham_gradient`, whose transition is 2100. Water-rheology cases use the existing Newtonian transition at 2300. Keep these regime labels distinct.

## Pressure, power and temperature rise

For 16B, use the already frozen same-window standpipe and raw differential means. For 16A, use the Sanvean `Surface_Pump Pressure(psi)` and `Surface_Differential Pressure(psi)` extract at the exact frozen sample centre, matching the time support of its operating inputs. Keep pressure values and valid counts. Do not infer missing pressure, apply an offset or replace the 223 return-only samples' missing Sanvean pressure with another channel.

Call unchanged `hydraulics` with the solved temperatures and the appropriate fluid. Report its string, annulus, nozzle and buoyancy terms. Compare modelled SPP both with raw measured SPP and with measured SPP minus the raw reported differential. These residuals can include motor/MWD losses absent from the pressure model. Do not label the differential as a verified motor-only loss. Retain the approved non-negative motor-face load, with zero face heat on documented motorless 16B assemblies; keep all raw differential values.

Measured hydraulic power is measured SPP times measured inlet volumetric flow. Report the corresponding modelled pressure power at that same inlet flow. Also report local-volume hydraulic dissipation from the pressure model, and separately integrate the actual circulation solver's distributed friction-heating term. These are different diagnostics: the existing thermal friction routine uses its Newtonian friction-factor treatment and a 5 MPa liquid-property floor, while `hydraulics` uses Bingham pressure loss when yield point is positive. Do not change either function or silently equate the terms.

Report motor-face heat and nozzle heat separately. Integrate rock exchange and the temperature-rise contributions from the unchanged differential equations on a grid no coarser than 1 m, including geometry and exposure blending boundaries and their midpoints. Retain the existing 1-m geometric blending in these diagnostic source terms. Report the quadrature closure against predicted outlet-minus-inlet, including the internal-exchange heat-capacity term. This verifies the implemented temperature balance; it is not a claim that temperature rise alone measures pump dissipation. Do not count internal pipe exchange as an external energy source.

Compare modelled and observed outlet-minus-inlet temperature rise at every available primary sample. For 16A, preserve its original mud-log inlet/outlet treatment. For 16B, retain its paired Pason inlet/outlet means. Report hydraulic-power equivalents in °C only with their declared heat-capacity conversion.

## Matched depths and interpretation

Use the predeclared 500-ft MD bins. Publish sample-level inputs and a bin comparison over all bins shared by the two downhole series. Include unmatched bins and counts. Keep run identity, measured downhole channel/temperature, all fixed model sensor branches, TVD and formation temperature. Include flow, inlet, string/BHA and hole geometry, recorded density and rheology, nozzle area, cooler annotations, penetration rate, raw differential and motor-face load, annulus Reynolds numbers and film coefficients. Report the original 16A primary and revised 16B primary side by side, with the 16A sensitivity and earlier 16B version separately labelled.

Use observed pumps-off intervals longer than two hours as explicitly labelled trip proxies. Give time since a confirmed surface trip only where bit-depth evidence establishes it. Missing confirmation is missing, not zero elapsed time. The 16A off-event list does not establish complete string movements. Do not select samples, depth bins, sensor positions or input values from their temperature errors.

Report per-run and per-depth results, with pooled statistics accompanied by those breakdowns. Preserve 16A washout flags and 16B trial fitting roles. Do not establish recovery, rheology or friction as a cause solely from a sensitivity. Stop after the revised-primary, sensitivity, energy and matched-depth tables and figures; documentation integration and release work remain later stages.
