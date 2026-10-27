# Hydraulic pressure and heat: revised V0 review

Baseline: `f61a5d918285948c7254f1458c83992cdfb935cb`, after the FORGE 16B merge. Branch: `hydraulics-v1.6.0`. This stage prepares source inputs and the pressure protocol. No package calculation, default, version, golden file or published result is changed.

## Review material

- [Interface and accounting](interface.md): joint/component/tool fields, shared friction, surface losses and source placement.
- [Sources and defaults](sources-and-defaults.md): every proposed coefficient/default, with assumptions and applicability.
- [56-32 input archive](../../forge56-32/README.md): source extracts, rebuild command and input conflicts.
- [Pressure protocol](../../forge56-32/comparison_protocol.md): off-bottom primary comparison, on-bottom secondary comparison and separate rheology variants.
- [Execution record](commands.md): extraction, reproducibility and preservation checks.

## Proposed calculation

Add catalogue-based joints, serial BHA geometry and local losses. Supplied tool losses use a documented pressure/flow/density reference; whole-tool curves replace the internal losses they already include. Surface equipment enters standpipe pressure only. Bore dissipation heats the bore and external annular dissipation heats the annulus. The pressure and heat paths share the Bingham/Newtonian gradient and property guard. The existing heat-transfer correlations and fitted parameters remain unchanged.

Reference programmes use the cited connection allowances, API surface case 5 and the published MWD hydraulic allowance, with zero-tool and zero-surface sensitivities. Field data use their own equipment. The existing `pv_ref_T` input accommodates the field assumption of 48.9 C with 26.7 C separately reported; site/default rheology stays at 26.7 C. No claim is made that the field reference temperature is verified by API practice.

## Data prepared

The 56-32 archive has 250,629 ten-second input bins from 2,506,182 source rows, 97 survey stations and eleven BHA sheets. It includes component, bit, mud, casing, pipe and operating inputs. Target outputs contain availability counts only: 2,476,669 finite standpipe readings and 29,513 missing.

The pressure-specific flow/depth rules identify 18 off-bottom candidates and 1,022 on-bottom candidates. Four off-bottom candidates have a unique provisional BHA assignment; fourteen need exact trip/assembly reconciliation. These candidates are not model runs or complete score cases. The rules use ten-minute operational steadiness, without the earlier harness's thermal warm-up requirement. No target value selected a window.

The 58-32 daily reports provide BHA records, so it can follow the same input/protocol preparation before V2 as the second pressure well. No further access to 78B data was made in this stage. The abandoned harness and earlier V0 drafts remain separate, uncommitted working material.

## Points for review

1. **Motor references are incomplete.** The GeoGuidance figures do not identify reference flow or density, and the recorded 7-in/8-in configurations do not exactly match the pictured motors. BICO supplies a no-load value with a clean-water test basis but no identified reference flow; Discovery has no identified no-load value. A rho-Q-squared curve cannot yet be assigned as a fully sourced field input. The options are additional manufacturer information or an explicitly approved alternative treatment; no coefficient has been inferred from measured pressure.
2. **Some geometry and timing remain unresolved.** Preserve unknown passage IDs, rounded casing weights, the source depth-cell error and calendar-only trip boundaries. Their treatment must be committed before pressure comparison. No complete primary result can be claimed from the present candidate list.
3. **The precision requirements need the declared calculation context.** Applying the shared 5 MPa guard changes legacy pressure even with added losses zero. The proposed exact-baseline test uses an explicit legacy mode. S2b formula replay uses frozen property/evaluation points; a production-mode comparison must show guard and sampling differences separately. This interpretation is presented for acceptance before V1, not silently substituted for an exact test.

V0 stops here, before implementation. The protocol is committed before target comparison; later source rulings require a new pre-comparison commit. No model has been run on 56-32 or 58-32, and no pressure residual has been calculated.
