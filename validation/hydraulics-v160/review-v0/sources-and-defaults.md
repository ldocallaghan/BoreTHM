# Sources and proposed reference defaults

Sources accessed 27 October 2026. These choices precede held-out pressure predictions. The reference programme is a declared engineering scenario; its allowances do not identify the installed FORGE equipment.

## Formula sources

| Term | Formula or retained method | Source and qualification |
| --- | --- | --- |
| Straight-passage friction | Existing Bingham pressure gradient for mud; existing Newtonian laminar/Blasius gradient for water | Baseline `fluids.bingham_gradient` and `model1_coupled.hydraulics`; the existing Bingham reference is Bourgoyne et al., *Applied Drilling Engineering* (1986), chapter 4. No new roughness or fitted multiplier. |
| Expansion/contraction | With r = small area / large area: expansion K = (1-r)^2; contraction K = 0.5(1-r)^0.75; loss = K rho v_small^2 / 2 | [Modelica sudden-change documentation](https://doc.modelica.org/Modelica%204.0.0/Resources/helpOM/Modelica.Fluid.Dissipation.Utilities.SharedDocumentation.PressureLoss.Orifice.dp_suddenChange.html), citing Idelchik. Smooth turbulent restrictions, expansion Re > 3,300, contraction Re > 10,000. Bingham and annular applications carry approximation flags. Gradual means zero local loss, an idealisation. |
| Tool scaling | Reference pressure times density ratio times squared flow ratio | API RP 13D (2009), section 7.6.2, equation 103; the reference coefficient requires tool-specific evidence. |
| Surface equipment | C rho_ppg (Q_gpm / 100)^1.86 psi; cases 1 to 5 use C = 1.00, 0.36, 0.22, 0.15, 0.15 | API RP 13D (2009), section 7.3, equation 60/table 4. [API document text](https://studylib.net/doc/27198826/api-recommended-practice-13d-rheology-and-hydraulics-of-o...). Historic published layouts; no claim of current-edition compliance or verified rig piping. |
| Nozzles | Existing calculation, discharge coefficient 0.95 | Baseline implementation and [S2b protocol](../../forge16b/comparison_protocol_s2b.md). No change to the coefficient. |
| Property guard | Shared 5 MPa minimum property pressure in the new friction kernel | Retained numerical guard from baseline thermal friction. Exact old pressure behaviour remains available only in the explicit legacy mode. |

The linked API-authored text is dated 5 October 2009 and identifies itself as a review draft. Its equations reproduce the historical S2b method; the link does not verify the final published edition. Preserve that provenance qualification in implementation references.

## Connection defaults

The ordinary reference pipe retains its existing body dimensions. [NOV's GPDS/EIS catalogue](https://www.nov.com/products/gpds-and-eis-connections), 5.5-in / 21.9-lb/ft configuration, supplies a 7-in OD and 4-in joint bore. Assign this connection envelope to conventional, internally coated, externally coated and TK Drakon reference variants. For dual-wall and vacuum variants, the same envelope is an explicit transferred assumption; verified proprietary connection geometry is unavailable. Their existing 80-mm body bore remains unchanged, even when it is smaller than the assumed joint bore. Report that assumption in results.

Use an effective ordinary-pipe restriction length of 29 in, an assumption retained from S2b, with 0-in and 58-in sensitivities. Use spacing 2,378 ft / 75 = 31.7066667 ft from the 16B regular-pipe tally cited in S2b. This transfers a field tally to a reference programme; it is not a manufacturer-specified restriction schedule.

For reference HWDP, [Workstrings asset 91005000020000](https://www.workstringsinternational.com/assets/Spec-Sheets/HWDP/91005000020000-Imperial.pdf), sheet dated 1 August 2025, specifies 5.5-in body, 3.25-in bore and 7.25-in / 3.25-in HT55 joints, with approximate 31-ft spacing. Retain the current rounded reference HWDP body dimensions. Use 48 in as the effective restriction length, an assumption from the published 24-in pin plus 24-in box lengths. Run 0-in and 96-in length sensitivities. The combined physical lengths do not establish a constant hydraulic throat over 48 in. Centre pads remain unrepresented.

Drill collars do not receive a repeated pipe-joint allowance by default. Their actual segment transitions are represented explicitly. Custom pipes have no hydraulic joint unless supplied. Reject physically closed passages; do not silently shrink joint dimensions to make a programme feasible.

## MWD allowance and serial reference BHA

Use the mud-pulse 6.75-in configuration in [xBolt G2-L specifications, Rev 7, page 2](https://www.poweredbyextreme.com/wp-content/uploads/2024/07/xBolt-G2-L-Specifications-and-Fishing-Diagrams_Rev7.pdf). Its formula is pressure_psi = density_ppg times flow_gpm squared / 30,000. Normalise to 500 gpm and 1,000 kg/m3, approximately 69.5 psi; derive the exact SI reference value from the stated conversion constants in implementation. Use the 3.25-in collar-bore option, whose published maximum flow is 750 gpm. Flag extrapolation above this flow. Its temperature rating is 329 F (165 C); the allowance does not establish hot-well tool suitability.

Treat this as total internal tool loss across the pulser and collar. Their empty-body bores do not represent the probe-obstructed flow area. No extra empirical multiplier is added. The published tool choice is made before any FORGE error calculation.

Preserve the reference lower-assembly lengths while representing the allowance components separately, in surface-to-bit order:

| Component | Length | External/body bore | Source/status |
| --- | --- | --- | --- |
| Reference HWDP | 223 m | Existing 0.140 / 0.083 m | Existing Wu reference geometry; new connections as above |
| Plain drill collar | 132.076768 m | Existing 0.170 / 0.073 m | Remaining part of the existing 143-m collar interval |
| MWD pulser | 5.84 ft = 1.780032 m | 7 / 3.38 in | xBolt mud-pulse drawing |
| MWD collar | 30 ft = 9.144 m | 6.75 / 3.25 in | Same drawing; shared total-internal tool curve |
| Bit body | Existing 0.8 m | Existing reference treatment | Existing bit/nozzle/face model |

This is a proposed reference arrangement. Keep its full-tool extent and displaced collar length explicit. The zero-tool-loss sensitivity restores the calculated open-passage losses through the same geometry. Surface case 5 is primary, with zero surface loss also reported; the other API cases remain available. Reference wells are vertical, so no steering tool is assumed. A custom steering assembly requires supplied data.

## Unavailable information

The [HALO manufacturer sheet](https://scientificdrilling.com/assets/uploads/sites/3/2018/09/SC_TDS_HALO_9.24v3.pdf) has no operating pressure-loss curve. A pressure rating cannot supply that curve. Do not transfer the reference xBolt curve to HALO as an as-built value. Missing motor/no-load losses, valve ports and high-pressure surface layouts remain explicit omissions or source-based scenarios. No residual from the FORGE comparison is used to determine them.

## Field viscosity reference temperature

API RP 13B-1 (2009), sections 6.3.2.1 and 6.3.2.2, describes field tests near the sampling temperature and recording the sample temperature. [API-authored text, mirrored copy](https://pdfcoffee.com/api-rb-13b-1-pdf-free.html). It does not establish that every unlabelled field PV was measured at 120 F. The selected 56-32 DDR mud tables have no rheology test-temperature field.

For this study, 48.9 C is a declared input assumption with 26.7 C as a sensitivity. It is not a verified correction to the field record. A documented test temperature takes precedence. The existing `Mud.pv_ref_T` input changes the plastic-viscosity normalisation through the water-viscosity ratio at the reference temperatures. The current yield-point treatment is unchanged. Do not describe the whole Bingham apparent viscosity as a uniform temperature-independent correction factor.

Keep the original 16A/16B blind outputs and compare v1.5.0/26.7 C, v1.5.0/48.9 C and v1.6.0/48.9 C separately. Site-file PV, the default reference programme's rheology and `fluids.PV_REF_T` stay at 26.7 C.

## 56-32 field inputs and open source questions

The [input archive](../../forge56-32/README.md) transcribes the actual 5-in 19.5-lb/ft S-135 pipe tally with 4.5 IF connections. Its body differs from the built-in 5.5-in reference pipe. NOV's 5-in 19.5-lb/ft GPDS 50 catalogue entry gives a 6.625-in / 3.25-in connection envelope; using it would be a compatible connection scenario, not a verified installed machining schedule. Exact spacing and effective length remain declared inputs.

The field casing records report approximately 55-lb/ft 13.375-in casing and 36-lb/ft 9.625-in casing. Do not transfer the 16A 68/40-lb/ft IDs. The 55-lb/ft entry could be rounded from the standard 54.5-lb/ft geometry; that interpretation and the conductor wall need source confirmation or a stated assumption before a numerical case is complete. Unreported component IDs remain unfilled.

Manufacturer no-load facts are transcribed in [tool_specifications.csv](../../forge56-32/tool_specifications.csv), using the source member and PDF page. GeoGuidance pages 2 and 3 print 100-psi off-bottom values for the pictured 6.75/8-in configurations and 140 psi for the 9.62-in configuration. They give flow ranges but no reference flow/density. The bit workbook records 8-in 7/8-lobe 5.9-stage and 7-in 6/7-lobe 6.5-stage configurations, which do not exactly match those pictures. Keep the mismatch visible.

BICO's 7-in SSS100-B5 sheet prints 475-psi no-load drop and identifies clean-water surface testing at 72 F; its reference flow is not identified. The Discovery 7-in 8.5-stage sheet has no identified no-load pressure value. The Jarvis MWD sheet supplies no identified hydraulic curve. None of these gaps can be filled from standpipe residuals. The new tool-loss API requires a complete reference point; a constant-pressure interpretation would need an explicit model/input ruling before use.
