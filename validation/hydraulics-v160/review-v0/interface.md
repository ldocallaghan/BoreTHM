# Proposed hydraulic interface and accounting

This document describes an interface for review. The names below are proposed additions; they are not implemented API calls.

## Geometry and supplied losses

All Python dimensions use metres, pressure uses Pa, volumetric flow uses m3/s and density uses kg/m3. Existing positional constructors retain their order. New fields have defaults.

| Owner | Proposed field or type | Meaning |
| --- | --- | --- |
| `PipeType` | `hydraulic_joint: HydraulicJoint \| None = None` | Optional joint OD, bore, effective restriction length and spacing, plus transition treatment and source. Independent of the existing thermal `joint_fraction`. |
| `HydraulicJoint` | `outer_diameter`, `bore_diameter`, `restriction_length`, `spacing`, `transition`, `source` | Fractional expected joint count is segment length / spacing. Effective length cannot exceed spacing. Transition is `abrupt` or the zero-local-loss `gradual` idealisation. |
| `StringSegment` | `local_loss: LocalLoss \| None = None` | Optional supplied bore/annulus coefficients, with an explicitly named reference area and source. Automatic geometric transitions are separately reported. |
| `StringSegment` | `tool_loss: ReferenceToolLoss \| None = None` | A supplied reference pressure loss with density and flow scaling. |
| `ReferenceToolLoss` | `dp_ref`, `flow_ref`, `density_ref`, `basis`, `span_segments`, `source` | `basis="additional"` adds a published additional loss. `basis="total_internal"` replaces modelled internal losses across the declared contiguous component group. Default span is one component. |

The group starts at the segment carrying the curve and includes the stated number of segments, in surface-to-bit order. Overlapping groups, non-positive reference flow/density and ambiguous source coverage are rejected. Within a total-internal group, do not add body friction, internal joint losses or internal transitions already represented by the curve. Keep the external annulus losses and boundary transitions outside the declared tool. Spread tool heat uniformly over its covered length. Report the replacement and its extent in the budget.

Automatic geometric transitions occur once at a physical change, including casing changes on the annular return path. Numerical mesh subdivisions do not create extra losses. Use the actual flow direction when identifying contraction and expansion. Spread each event over an explicitly recorded adjacent component interval, identically in pressure and heat integration. User coefficients describe additional restrictions and must not duplicate an automatically represented transition.

Joint corrections replace body friction over the effective restriction length, then add the entry and exit losses. The correction can be negative when the joint passage is larger than the body passage. The total passage dissipation must remain non-negative. Do not cap a specified joint bore to the pipe-body bore.

The existing thermal joint treatment remains independent. Helpers such as `PipeType.with_joints` must preserve the new hydraulic fields. A bare geometry with no supplied client tool curve receives no hidden reference tool allowance.

## Calculation mode and surface equipment

Add keyword arguments at the end of the existing circulation, `hydraulics` and evaluator interfaces:

```python
hydraulics_model="v1.6.0"  # alternative: "v1.5.0"
surface=None              # SurfaceLoss.api_case(5), .coefficient(0.15), or None
```

The surface coefficient has the units implied by the API psi/ppg/gpm formula. It is not a constant pressure. Use a typed surface object in Python to avoid treating an integer coefficient as a case number. The evaluator's built-in reference programme supplies case 5; low-level calls default to no surface term.

In the new calculation mode, pressure and thermal sources use the same local friction-gradient kernel: existing Bingham treatment for mud and existing Newtonian treatment for water, with the same density, viscosity and property pressure. The property-pressure guard is `max(P, 5e6)` for this kernel. Actual pressure and guard activation are both reported. This is a liquid-property guard, not proof of a single-phase state at the actual pressure.

The legacy calculation mode preserves the original pressure sampling and separate thermal friction treatment exactly. It disables all new terms and rejects supplied new-loss settings. Baseline precision tests exercise this mode. Additional tests exercise the new mode with zero added terms and quantify the guard/shared-gradient change separately.

## Site files and evaluator

Add an optional typed `programme` field to `SiteProfile`, parsed by the strict site loader. An evaluator override takes precedence over that field. Missing programme data selects the documented built-in reference programme, preserving existing site-file validity. Explicit custom strings do not acquire the built-in MWD allowance implicitly.

Illustrative TOML, with nested joint/tool records using the same names and SI units as Python:

```toml
[programme]
hydraulics_model = "v1.6.0"
reference = "wu2025-with-hydraulic-allowances"

[programme.surface]
case = 5

# Alternative to case: coefficient = 0.15
# Explicitly disable the surface term with enabled = false.
# Custom strings use [[programme.segments]] and optional
# [programme.segments.hydraulic_joint], .local_loss and .tool_loss records.
```

Case, coefficient and disabled settings are mutually exclusive. Unknown nested keys fail with a useful message. Store source strings and assumed/default status in the evaluated programme and output. Reject geometry with closed annuli or non-positive passages. The exact parser and dataclass exports are implemented and tested at V1.

## Pressure and heat budget

Keep existing result keys for string, annulus, nozzle, density-column correction, standpipe pressure and pump-limit status. Add named component terms for body friction, joint replacement increments, local losses, tool curves and surface equipment. The detailed terms sum to the existing subtotals and standpipe pressure. Each term records its interval, source, property evaluation, regime and approximation flags.

Surface pressure affects the pump check only. The annulus pressure profile used by the stability calculation includes the same annular joint and local losses as the standpipe calculation. Distribute these contributions consistently through `pressure.annulus_friction`; querying a partial interval must not count a complete local event twice.

For a local volumetric flow Q = mass flow / local density, distributed heat is pressure gradient times Q, in W/m. Bore losses heat the bore; annular losses heat the annulus. Nozzle and existing motor-face heat retain their turnaround placement. The signed density-column correction produces no dissipative heat. Surface heat is excluded because the inlet temperature is the boundary condition.

A supplied motor curve must identify whether it includes useful mechanical power. Do not interpret all motor pressure power as fluid heat or duplicate the existing face-heat input. This release adds no motor-efficiency model. Inputs that cannot distinguish these contributions remain qualified or excluded from complete energy accounting.

For field PV, the existing `Mud(..., pv_ref_T=...)` argument already represents the measurement reference temperature. Study adapters will pass the reported temperature when available, otherwise the declared 48.9 C assumption, and expose 26.7 C as a separate sensitivity. Preserve the original S1 archives. Site-file PV and the default remain referenced to `fluids.PV_REF_T = 26.7 C`. This is an input change; computed film coefficients may change although their correlations do not.

For the 56-32 off-bottom protocol, the manufacturer's no-load curve must include an identified reference flow and density before constructing `ReferenceToolLoss`. The provided GeoGuidance pressure table lacks those reference quantities. Its printed scalar is not automatically a complete rho-Q-squared curve. A manufacturer-constant interpretation would require an explicit additional input-model decision; it is not implemented by this proposal.

Per-solve diagnostics compare integrated applied sources against the independently summed assigned in-hole dissipation plus the existing face input, with explicit absolute/relative residuals. Compare like definitions and the same local flow. This checks source assignment; it does not establish that measured pump power is completely represented. Set and justify numerical tolerances in V1 using integration error, without adjusting physical coefficients.

## S2b replay contract

Use the unchanged [S2b protocol](../../forge16b/comparison_protocol_s2b.md), its 90 archived original/revised cases and saved temperature profiles. Retain both catalogue-joint scenarios and every published surface/length/transition sensitivity.

First replay each formula at the archived property and midpoint evaluation points. Body subtraction, local increments and surface terms must reproduce their archived values to arithmetic precision. Then run the package on the frozen profiles with the corresponding configuration. Report separately any differences from serial-component midpoint sampling, property guarding, nozzle sampling and density integration. Require equality when those evaluation choices are identical. Any remaining difference blocks acceptance. Do not refit, overwrite the archive or relax its checks to conceal a discrepancy.
