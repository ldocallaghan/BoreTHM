"""Build the motorless pressure results from saved pressure tables; no model solves."""
import csv
import json
import statistics as st
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent
OUT=HERE
read=lambda name:list(csv.DictReader((OUT/name).open(newline='',encoding='utf-8')))
samples=read('pressure-samples.csv')
runs=read('pressure-run-summary.csv')
budgets=read('scenario-budgets.csv')
runbudgets=read('scenario-run-summary.csv')
components=read('bha-components.csv')
audit=json.loads((OUT/'audit.json').read_text())

def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n|'+ '|'.join('---' for _ in headers)+'|\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows)+'\n'

def fixed(r):
    return r['joint_length_in']=='29.0' and r['local_shape']=='sudden' and r['surface_case']=='5'

nominal=[r for r in budgets if fixed(r)]
source={r['case_id']:r for r in samples}
enriched=[{**source[r['case_id']],**r} for r in nominal]
with (OUT/'nominal-sample-accounting.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=list(enriched[0]));writer.writeheader();writer.writerows(enriched)

text='''# Motorless FORGE 16B: S2b pressure accounting

## Finding and scope

The unchanged model accounts for 42–49% of the mean measured standpipe pressure on EOW 12, 13, 15 and 16 under the revised S2 mud rule. Resolving the recorded lower-assembly passages adds about 30–37 psi of bore friction; abrupt component transitions add about 24–27 psi. Representative tool joints add about 72–285 psi across the four run means, depending on their declared geometry. The API top-drive surface case adds about 35 psi.

With 29-in representative joint restrictions, abrupt transitions and the API top-drive surface case, mean accounted fractions range from 57% to 79%, leaving mean residuals of 249–532 psi. These are conditional geometric scenarios. The installed joint machining, the surface piping downstream of the pressure tap and the HALO/float/filter operating restrictions remain unresolved. Their unknown losses are not zero. No scenario is selected by its residual and no coefficient is inferred from pressure agreement.

The other historic API surface cases are retained. Applying their most restrictive layout can bring some sample totals above measured pressure, while the run-mean residuals remain positive in the 29-in abrupt scenarios. That layout includes a kelly and is not established for this top-drive rig. The tabulated range is not a confidence interval or an as-built pressure bound. No cause is assigned to the temperature discrepancies.

Forty-five fixed half-hour samples are evaluated under both original and revised mud rules, with equal sample weights. All 90 circulation replays converge and reproduce saved S2 pressure and temperature endpoints exactly. External estimates are post-processing only; they are never supplied to a circulation solve. The [frozen protocol](../comparison_protocol_s2b.md) states the method and source assumptions.

## What the existing model includes

| Requested term | Included treatment | Excluded contribution / separate estimate |
|---|---|---|
| Pipe body friction | Ordinary 5.5-in pipe, 4.670-in bore; midpoint fluid properties per constant-geometry piece | No roughness allowance or joint restriction in this term |
| Tool joints | No separate hydraulic joint term | Both internal and annular replacement-length friction, plus entry/exit losses, are estimated in two catalogue geometries |
| BHA components | HWDP is a distinct segment; lower components are represented by length-weighted bore and OD | Serial recorded bores and ODs replace the aggregate losses in the diagnostic; transition losses are additional; tool-specific mechanisms remain unquantified |
| Bit nozzles | Recorded total nozzle area; local density and mass flow; discharge coefficient 0.95 | No new nozzle adjustment or fitted coefficient |
| Annulus | Concentric clean-fluid friction using recorded hole/casing geometry and aggregate string segments | Joint effects and serial component OD increments are reported separately; eccentricity, rotation and cuttings are not added |
| Surface lines | None | All five historic API connection cases, and zero allowance, are retained as separate scenarios |
| Density-column correction | Signed annulus-minus-bore density integral over TVD | Separate from the six dissipative categories; retained when summing standpipe pressure |

BHA means bottom-hole assembly, including heavy-weight drill pipe (HWDP). Pressure losses are in psi. Standpipe pressure (SPP) is a pressure difference. The raw Pason differential channel is shown as recorded and is not subtracted on these motorless runs. Its negative values prevent interpreting it as a strictly positive motor loss.

## Included terms: revised-mud primary

'''
keys=['measured_spp_psi_mean','pipe_body_psi_mean','bha_hwdp_psi_mean','bha_lower_aggregate_psi_mean','bit_nozzles_psi_mean','annulus_psi_mean','density_column_psi_mean','model_spp_psi_mean']
text+=table(['EOW','n','Measured SPP','Pipe','HWDP','Lower BHA','Nozzles','Annulus','Density column','Model total'],
    [[r['run'],r['n'],*[f'{float(r[k]):.1f}' for k in keys]] for r in runs if r['rheology_case']=='s2_revised'])
text+='''Tool-joint and surface terms are zero in the included model total. HWDP plus lower BHA gives the requested BHA category. Each sample's original six-term split and signed density correction is in [pressure-samples.csv](pressure-samples.csv); [model-pieces.csv](model-pieces.csv) retains the exact pieces. The [run table](pressure-run-summary.csv) reports both mud versions and per-sample extrema.

## External estimates and source limits

The [recorded assembly inputs](../component_inputs_s1.csv) give the lengths and bores of every lower component and all 30 HWDP joints. The bit's gauge OD would describe a sealed annulus if treated as a solid cylinder; it does not resolve junk-slot flow. The existing aggregate OD is retained over the short bit-body interval only and is labelled in [bha-components.csv](bha-components.csv). No drawing dimension is edited.

[NOV's connection tables](https://www.nov.com/products/gpds-and-eis-connections) give two 5.5-in, 24.7-lb/ft geometries compatible with the recorded FH connection family: EIS 7.000-in OD / 4.000-in ID and GPDS 55 7.250-in OD / 3.500-in ID. The installed machining is unknown. A 29-in effective restriction length is assumed, with 0-in and 58-in sensitivities. The pipe tally on EOW p266 gives 2,378 ft per 75 joints; its use for earlier runs is an explicit transferred input. HWDP joint OD follows each catalogue scenario, with its recorded 3.625-in bore retained; internal machining and centre pads are unresolved. Joint-length body losses are subtracted before replacement losses are added.

The [Modelica Association's documented Idelchik correlations](https://doc.modelica.org/Modelica%204.0.0/Resources/helpOM/Modelica.Fluid.Dissipation.Utilities.SharedDocumentation.PressureLoss.Orifice.dp_suddenChange.html) supply abrupt expansion and contraction coefficients from area ratios. Zero local loss is also retained for gradual-transition scenarios. These correlations describe smooth turbulent Newtonian flow. All revised-mud geometric checks exceed their stated Reynolds-number thresholds, but applying them to Bingham mud and annular changes remains an approximation. Original S1 mud has 3,990 joint and 60 BHA transition rows outside those Reynolds thresholds; their estimates are retained and flagged, not treated as validated predictions.

For surface equipment, API RP 13D (2009), §7.3 equation60/table4, gives P = C rho_ppg (Q_gpm/100)^1.86 psi, with the five C values 1.00, 0.36, 0.22, 0.15 and 0.15. Case5 represents a top-drive system; all are generic complete layouts. No as-built dimensions or exact Pason pressure-tap position were found. Including a complete layout is conditional because part could be upstream of that tap. The old standard is used for explicit scenarios, not as a claim of current-edition compliance.

API §7.6.2 requires a tool-specific reference pressure-loss coefficient. The [HALO manufacturer sheet](https://scientificdrilling.com/assets/uploads/sites/3/2018/09/SC_TDS_HALO_9.24v3.pdf) identifies an integrated steering assembly and MWD pulser but provides no operating loss curve. Its 20,000-psi hydrostatic rating is not an operating loss. The recorded float and filter subs likewise lack port/open-area data. A full numerical estimate of these terms cannot be obtained from body IDs alone without an unsupported coefficient. Their open-passage friction is estimated above, and the following dynamic heads give pressure per unit *additional* local-loss coefficient K at the recorded bore. Actual K and additional loss remain blank in the evidence, not set to zero. The motor contribution is zero because no motor is documented.

'''
tool_names=['HALO RSS','Black box','Float sub','Filter sub']
text+=table(['EOW',*[name+' psi per K' for name in tool_names]],[[run,*[f"{st.mean(float(c['extra_internal_psi_per_K']) for c in components if c['run']==run and c['rheology_case']=='s2_revised' and c['component']==name):.2f}" for name in tool_names]] for run in ['12','13','15','16']])
text+='''These heads use the recorded unobstructed body bore as their velocity reference. An internal probe can have a smaller actual flow area. The table does not assert a sharp orifice, assign K = 1 to a tool or use the remaining residual to infer K.

## Representative 29-in abrupt-joint scenarios

Both catalogue geometries and all surface cases remain in the archive. The table below uses surface case5 only, to show the top-drive scenario explicitly. Components are increments to the unchanged model. Serial-annulus correction is about −0.02 to −0.04 psi and remains included without rounding it to zero in the CSV.

'''
primary=[r for r in runbudgets if r['rheology_case']=='s2_revised' and fixed(r)]
text+=table(['EOW','Joint geometry','Serial BHA bore','Joint bore','Joint annulus','Joint local','BHA local','Surface','Accounted','Mean sample fraction','Residual'],
    [[r['run'],r['joint_geometry'],*[f'{float(r[k]):.1f}' for k in ['bha_bore_increment_psi_mean','joint_internal_increment_psi_mean','joint_annulus_increment_psi_mean','joint_local_increment_psi_mean','bha_local_increment_psi_mean','surface_lines_estimate_psi_mean','accounted_psi_mean']],f"{100*float(r['accounted_fraction_mean']):.1f}%",f"{float(r['remaining_residual_psi_mean']):.1f}"] for r in primary])
text+='''The fraction is the mean of per-sample accounted/measured ratios; it need not equal the ratio of the displayed run means. Residual is measured SPP minus accounted pressure, with the differential left untouched. No proprietary tool allowance has been supplied.

![Motorless pressure accounting](pressure-accounting.png)

*Revised S2 mud; representative 29-in restrictions and abrupt local changes. Both connection geometries use API surface case5. Black ticks are measured run-mean SPP. Negative density-column corrections remain in each total. No missing tool loss is assigned to fill the gap.*

### Surface and geometry sensitivity

'''
text+=table(['EOW','Joint geometry','Case5 accounted / residual','Case1 accounted / residual'],[
    [run,name,*[f"{float(next(r for r in runbudgets if r['run']==run and r['rheology_case']=='s2_revised' and r['joint_geometry']==name and r['joint_length_in']=='29.0' and r['local_shape']=='sudden' and r['surface_case']==case)['accounted_psi_mean']):.1f} / {float(next(r for r in runbudgets if r['run']==run and r['rheology_case']=='s2_revised' and r['joint_geometry']==name and r['joint_length_in']=='29.0' and r['local_shape']=='sudden' and r['surface_case']==case)['remaining_residual_psi_mean']):.1f}" for case in ['5','1']]] for run in ['12','13','15','16'] for name in ['EIS','GPDS55']])
text+='''[scenario-budgets.csv](scenario-budgets.csv) contains all 6,480 sample scenarios: both mud versions, both joint geometries, three restricted lengths, two local-loss shapes, all five API surface layouts and zero surface allowance. [scenario-run-summary.csv](scenario-run-summary.csv) gives their run summaries. No cases are selected by agreement. Larger assumed allowances can over-account individual pressures; the remaining residual is not a measured HALO loss.

## Sample-by-sample primary accounting

The next table retains every revised-primary sample. Both representative joint geometries use 29-in restrictions, abrupt local changes and surface case5. The complete included and estimated split, fractions and residuals for both mud versions are in [nominal-sample-accounting.csv](nominal-sample-accounting.csv).

'''
def paired(row,name):
    return next(b for b in nominal if b['case_id']==row['case_id'] and b['joint_geometry']==name)
text+=table(['Sample time','EOW','MD ft','Measured','Model','EIS accounted / residual','GPDS accounted / residual','Raw differential'],[
    [r['time'],r['run'],f"{float(r['depth_ft_MD']):.0f}",f"{float(r['measured_spp_psi']):.1f}",f"{float(r['model_spp_psi']):.1f}",*[f"{float(paired(r,n)['accounted_psi']):.1f} / {float(paired(r,n)['remaining_residual_psi']):.1f}" for n in ['EIS','GPDS55']],f"{float(r['raw_differential_psi']):.1f}"] for r in samples if r['rheology_case']=='s2_revised'])
text+='''## Reported differential on motorless runs

'''
text+=table(['EOW','n','Mean psi','Minimum psi','Maximum psi','Negative sample windows'],[[r['run'],r['n'],*[f'{float(r[k]):.2f}' for k in ['raw_differential_psi_mean','raw_differential_psi_min','raw_differential_psi_max']],sum(float(s['raw_differential_psi'])<0 for s in samples if s['run']==r['run'] and s['rheology_case']=='s2_revised')] for r in runs if r['rheology_case']=='s2_revised'])
text+='''The original S1 diagnostic also includes EOW14, which has no accepted temperature sample. The present accounting introduces no EOW14 sample. Its [original differential table](../s1/motorless-differential.csv) is preserved.

## Archive and provenance

'''
text+=f"All {audit['replays']} replays converged in {audit['duration_s']:.2f} seconds of summed case time, including pressure post-processing. Maximum temperature-endpoint difference and SPP difference from S2 are both zero. The independent audit checks 1,000 serial-component rows, all scenario sums and source preservation. All {audit['existing_calculation_files_unchanged']} calculation files in the S2 hash list, 69 input/source files and 66 S1/S2 archive files are unchanged. No fit or model replacement was used.\n\n"
text+='''[plan.json](plan.json) freezes inputs and hashes; [audit.json](audit.json) records verification. [bha-transitions.csv](bha-transitions.csv) retains local coefficients and applicability flags. [tool-joints.csv.gz](tool-joints.csv.gz) retains the connection calculations. [replayed-profiles.npz](replayed-profiles.npz) contains saved bore/annulus profiles, keyed by original S2 case ID. [execution-manifest.json](execution-manifest.json) records published file hashes.

The source data are GDR1516, [DOI 10.15121/1998591](https://doi.org/10.15121/1998591), CC BY4.0. This diagnostic adds pressure calculations and aggregation to those extracts; original downloads remain unchanged. The source report locators and estimate references are listed in the protocol. No new temperature prediction is substituted for S1 or S2.
'''
(OUT/'results.md').write_text(text,encoding='utf-8')

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,2,figsize=(11.6,5),sharey=True,constrained_layout=True)
for ax,name in zip(axes,['EIS','GPDS55']):
    rr=[r for r in primary if r['joint_geometry']==name]
    x=np.arange(4);bottom=np.zeros(4)
    for label,keys,colour in [
        ('Unchanged model',['model_spp_psi_mean'],'#426a8c'),
        ('Serial BHA + local',['bha_bore_increment_psi_mean','bha_annulus_increment_psi_mean','bha_local_increment_psi_mean'],'#d99b45'),
        ('Joint restriction + local',['joint_internal_increment_psi_mean','joint_annulus_increment_psi_mean','joint_local_increment_psi_mean'],'#6c9c83'),
        ('Generic surface case 5',['surface_lines_estimate_psi_mean'],'#aaa0c2')]:
        vals=np.array([sum(float(r[k]) for k in keys) for r in rr])
        ax.bar(x,vals,bottom=bottom,label=label,color=colour,width=.65);bottom+=vals
    measured=[float(r['measured_spp_psi_mean']) for r in rr]
    ax.plot(x,measured,'k_',ms=25,mew=2.5,label='Measured SPP')
    ax.set_xticks(x,[r['run'] for r in rr]);ax.set_xlabel('EOW assembly');ax.set_title(name+' joint geometry (assumed)')
    ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True);ax.set_ylim(0,1400)
axes[0].set_ylabel('Run-mean pressure, psi')
handles,labels=axes[1].get_legend_handles_labels()
fig.legend(handles,labels,loc='outside lower center',ncol=3,frameon=False)
fig.suptitle('Motorless 16B: pressure accounted for in two declared scenarios\n29-in joint restrictions; abrupt changes; revised S2 mud',fontsize=13)
fig.savefig(OUT/'pressure-accounting.png',dpi=170)
plt.close(fig)
print('Wrote pressure results, nominal sample table and pressure figure')
