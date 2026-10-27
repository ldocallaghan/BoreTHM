"""Summarise frozen S1 predictions; this script imports no model code."""
import csv
import hashlib
import json
import math
import shutil
import statistics as st
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]/'geothermal-thermo-hydraulic-model'
DATA=ROOT/'validation/forge16b'
OUT=HERE/'comparison'
ARCHIVE=DATA/'s1'
plan=json.loads((OUT/'plan.json').read_text())
results=[json.loads(line) for line in (OUT/'results.jsonl').read_text().splitlines()]
assert len(results)==len(plan['cases'])==872
assert len({r['case_id'] for r in results})==872
samples={s['sample_id']:s for s in plan['samples']}
lookup={(r['sample_id'],r['fluid'],r['film_mult'],r['exposure']):r for r in results}
def read(path):
    with path.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def save(name,rows):
    rows=list(rows);keys=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def metric(records,position):
    good=[r for r in records if r['success']]
    errors=[r[f'bore_{position}ft_C']-samples[r['sample_id']]['measured_MWD_C'] for r in good]
    means=dict(n=len(records),converged=len(good),failed=len(records)-len(good),complete=len(good)==len(records))
    if not errors:return means
    obs=st.mean(samples[r['sample_id']]['measured_MWD_C'] for r in good)
    pred=st.mean(r[f'bore_{position}ft_C'] for r in good)
    means.update(measured_mean_C=obs,model_mean_C=pred,bias_C=st.mean(errors),MAE_C=st.mean(map(abs,errors)),
                 RMSE_C=math.sqrt(st.mean(x*x for x in errors)),max_abs_error_C=max(map(abs,errors)))
    means.update(measured_mean_F=obs*1.8+32,model_mean_F=pred*1.8+32)
    for key in ['bias','MAE','RMSE','max_abs_error']:means[key+'_F']=means[key+'_C']*1.8
    return means
groups=defaultdict(list);depthgroups=defaultdict(list)
for r in results:
    s=samples[r['sample_id']]
    for pos in s['requested_positions_ft']:
        key=(r['eow_bha'],r['fluid'],r['film_mult'],r['exposure'],pos)
        groups[key].append(r)
        depthgroups[(*key,int(s['bit_ft']//500)*500)].append(r)
run_metrics=[];depth_metrics=[]
for (bha,fluid,film,clock,pos),rr in sorted(groups.items()):
    run_metrics.append(dict(eow_bha=bha,fluid=fluid,film_mult=film,exposure=clock,position_ft=pos,**metric(rr,pos)))
for (bha,fluid,film,clock,pos,lo),rr in sorted(depthgroups.items()):
    depth_metrics.append(dict(eow_bha=bha,fluid=fluid,film_mult=film,exposure=clock,position_ft=pos,
                              depth_bin_start_ft=lo,depth_bin_end_ft=lo+500,**metric(rr,pos)))
save('run-metrics.csv',run_metrics);save('depth-metrics.csv',depth_metrics)
flat=[]
for r in results:
    s=samples[r['sample_id']]
    for pos in s['requested_positions_ft']:
        row=dict(case_id=r['case_id'],sample_id=s['sample_id'],eow_bha=r['eow_bha'],time=s['time'],
                 depth_ft_MD=s['bit_ft'],pipe_type=s['pipe_type'],fit_role=s['fit_role'],
                 fluid=r['fluid'],film_mult=r['film_mult'],exposure=r['exposure'],position_ft=pos,
                 position_unresolved=s['nominal_position_ft'] is None,success=r['success'],
                 measured_C=s['measured_MWD_C'],measured_F=s['measured_MWD_C']*1.8+32)
        if r['success']:
            pred=r[f'bore_{pos}ft_C'];err=pred-s['measured_MWD_C']
            row.update(bore_C=pred,bore_F=pred*1.8+32,annulus_C=r[f'annulus_{pos}ft_C'],error_C=err,error_F=err*1.8,
                       position_spread_C=r['requested_position_spread_C'],position_spread_F=r['requested_position_spread_C']*1.8,
                       return_C=r['return_C'])
        flat.append(row)
save('sample-comparisons.csv',flat)
pool=defaultdict(list)
for r in results:
    s=samples[r['sample_id']];n=r['eow_bha']
    if n in (3,4):
        for pos in s['requested_positions_ft']:
            pool[('early unresolved position',r['fluid'],r['film_mult'],r['exposure'],pos)].append(r)
    else:
        role='independent regular pipe'
        if n in (17,20):role='trial film-fit runs'
        if n==18:role='trial IDP-fit run'
        if n==19:role='trial held-out IDP run, fitted conductivity'
        pos=s['nominal_position_ft']
        pool[(role,r['fluid'],r['film_mult'],r['exposure'],'nominal')].append((r,pos))
pooled=[]
for (role,fluid,film,clock,label),rr in pool.items():
    if label!='nominal':m=metric(rr,label)
    else:
        # Transform the requested nominal branches to one temporary common key.
        projected=[{**r,'bore_0ft_C':r[f'bore_{p}ft_C']} if r['success'] else r for r,p in rr]
        m=metric(projected,0)
    pooled.append(dict(group=role,fluid=fluid,film_mult=film,exposure=clock,position=label,**m))
save('pooled-metrics.csv',pooled)
recovery=[];spreads=[]
for n in sorted({s['eow_bha'] for s in samples.values()}):
    ss=[s for s in samples.values() if s['eow_bha']==n]
    for pos in ss[0]['requested_positions_ft']:
        cold=[lookup[s['sample_id'],'recorded_mud',1.,'cumulative'] for s in ss]
        warm=[lookup[s['sample_id'],'recorded_mud',1.,'full_recovery'] for s in ss]
        good=[(s,c,w) for s,c,w in zip(ss,cold,warm) if c['success'] and w['success']]
        if good:
            cm=st.mean(c[f'bore_{pos}ft_C'] for _,c,_ in good);wm=st.mean(w[f'bore_{pos}ft_C'] for _,_,w in good)
            obs=st.mean(s['measured_MWD_C'] for s,_,_ in good)
            recovery.append(dict(eow_bha=n,position_ft=pos,n=len(ss),paired_converged=len(good),
                measured_mean_C=obs,cumulative_mean_C=cm,full_recovery_mean_C=wm,change_C=wm-cm,
                cumulative_mean_F=cm*1.8+32,full_recovery_mean_F=wm*1.8+32,change_F=(wm-cm)*1.8,
                measured_mean_bracketed=min(cm,wm)<=obs<=max(cm,wm)))
    for fluid in ['recorded_mud','water']:
        for film in [1.,.75]:
            for clock in ['cumulative','full_recovery']:
                rr=[lookup[s['sample_id'],fluid,film,clock] for s in ss]
                good=[r for r in rr if r['success']]
                values=[r['requested_position_spread_C'] for r in good]
                if values:spreads.append(dict(eow_bha=n,fluid=fluid,film_mult=film,exposure=clock,
                     positions_ft=';'.join(map(str,ss[0]['requested_positions_ft'])),n=len(rr),converged=len(good),
                     mean_position_spread_C=st.mean(values),max_position_spread_C=max(values),
                     mean_position_spread_F=st.mean(values)*1.8,max_position_spread_F=max(values)*1.8))
save('recovery-bracket.csv',recovery);save('position-spreads.csv',spreads)
motorless=[]
inventory={int(r['eow_bha']):r for r in read(DATA/'period_inventory.csv')}
for n in [12,13,14,15,16]:
    ss=[s for s in samples.values() if s['eow_bha']==n];xs=[s['reported_differential_psi'] for s in ss]
    row=dict(eow_bha=n,candidate_windows=len(xs),accepted_10s_EYE_rows=int(inventory[n]['valid_eye_rows']),
             accepted_10s_mean_psi=float(inventory[n]['reported_differential_psi_mean']),motor_face_heat_psi=0.)
    if xs:row.update(candidate_mean_psi=st.mean(xs),candidate_min_psi=min(xs),candidate_max_psi=max(xs),
                      candidate_median_psi=st.median(xs),negative_candidate_windows=sum(x<0 for x in xs))
    motorless.append(row)
save('motorless-differential.csv',motorless)
failures=[r for r in results if not r['success']]
(OUT/'solver-failures.json').write_text(json.dumps(failures,indent=2)+'\n')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':10})
fig,axes=plt.subplots(1,2,figsize=(14,5.6))
first=True
for n in sorted({s['eow_bha'] for s in samples.values()}):
    ss=sorted([s for s in samples.values() if s['eow_bha']==n],key=lambda s:s['bit_ft'])
    good=[s for s in ss if lookup[s['sample_id'],'recorded_mud',1.,'cumulative']['success'] and
                             lookup[s['sample_id'],'recorded_mud',1.,'full_recovery']['success']]
    if not good:continue
    depth=[s['bit_ft'] for s in good];obs=[s['measured_MWD_C'] for s in good]
    axes[0].plot(depth,obs,'ko',ms=3,label='Measured EYE' if first else None)
    for clock,col,label in [('cumulative','tab:blue','Cumulative exposure'),('full_recovery','tab:orange','Full-recovery bound')]:
        rr=[lookup[s['sample_id'],'recorded_mud',1.,clock] for s in good]
        nominal=[s['nominal_position_ft'] or 22 for s in good]
        prediction=[r[f'bore_{p}ft_C'] for r,p in zip(rr,nominal)]
        low=[min(r[f'bore_{p}ft_C'] for p in s['requested_positions_ft']) for r,s in zip(rr,good)]
        high=[max(r[f'bore_{p}ft_C'] for p in s['requested_positions_ft']) for r,s in zip(rr,good)]
        axes[0].plot(depth,prediction,'o-',color=col,ms=2,lw=1,label=label if first else None)
        axes[0].fill_between(depth,low,high,color=col,alpha=.16)
        error=[p-o for p,o in zip(prediction,obs)]
        axes[1].plot(depth,error,'o-',color=col,ms=3,lw=1,label=label if first else None)
        axes[1].fill_between(depth,[p-o for p,o in zip(low,obs)],[p-o for p,o in zip(high,obs)],color=col,alpha=.16)
    first=False
for a in axes:
    a.set_xlabel('Bit depth [ft MD]');a.grid(alpha=.25)
    a.axvspan(7584,9800,color='.6',alpha=.09)
axes[0].set_ylabel('Temperature [°C]');axes[0].set_title('Observed EYE and modelled bore fluid');axes[0].legend(fontsize=9)
axes[1].set_ylabel('Model minus measured [°C]');axes[1].set_title('Errors at the same 109 sample windows');axes[1].axhline(0,color='k',lw=.7)
fig.suptitle('FORGE 16B whole well: recorded mud, film multiplier 1.0')
fig.text(.5,.015,'Shading around curves: requested position range. Early 22-ft line is a branch, not a resolved position. Grey depth band: original trial (includes fitted inputs).',ha='center',fontsize=8)
fig.tight_layout(rect=(0,.045,1,.94));fig.savefig(OUT/'wholewell-comparison.png',dpi=160);fig.savefig(OUT/'wholewell-comparison.svg');plt.close(fig)

fig,ax=plt.subplots(figsize=(13,5.5))
ns=sorted({s['eow_bha'] for s in samples.values()})
for j,(fluid,film,label,col,shift) in enumerate([('recorded_mud',1.,'Recorded mud, film 1.0','tab:blue',-.18),
                                              ('recorded_mud',.75,'Recorded mud, film 0.75','tab:green',0),
                                              ('water',1.,'Water, film 1.0','tab:red',.18)]):
    for i,n in enumerate(ns):
        mm=[r for r in run_metrics if r['eow_bha']==n and r['fluid']==fluid and r['film_mult']==film and r['exposure']=='cumulative' and 'bias_C' in r]
        if not mm:continue
        nominal=next(s for s in samples.values() if s['eow_bha']==n)['nominal_position_ft'] or 22
        chosen=next(r for r in mm if r['position_ft']==nominal)
        y=chosen['bias_C'];lo=min(r['bias_C'] for r in mm);hi=max(r['bias_C'] for r in mm)
        ax.errorbar(i+shift,y,yerr=[[max(0,y-lo)],[max(0,hi-y)]],fmt='o',color=col,capsize=3,label=label if i==0 else None)
ax.set_xticks(range(len(ns)),[str(n)+(' *' if n in [3,4] else '') for n in ns])
ax.set(xlabel='EOW BHA (* unresolved EYE position)',ylabel='Mean model minus measured [°C]',title='Cumulative exposure: fluid and film sensitivities')
ax.axhline(0,color='k',lw=.7);ax.grid(alpha=.25);ax.legend(fontsize=9)
fig.text(.5,.015,'Whiskers span run-mean errors over requested positions. No position is chosen by its error. All variants use the same observed sample windows.',ha='center',fontsize=8)
fig.tight_layout(rect=(0,.04,1,1));fig.savefig(OUT/'fluid-film-sensitivities.png',dpi=160);fig.savefig(OUT/'fluid-film-sensitivities.svg');plt.close(fig)

primary=[r for r in run_metrics if r['fluid']=='recorded_mud' and r['film_mult']==1 and r['exposure']=='cumulative']
text='''# FORGE 16B whole-well comparison: S1 review

## Existing trial water check

The check was completed before whole-well predictions. Both saved calculation chains use their original samples and their own saved film and pipe-conductivity parameters; no fitting entry point was called. All 150 solves converged. The largest absolute difference from a saved run mean is '''+f"{max(abs(float(r['difference_F'])) for r in read(HERE/'trial-reproduction.csv')):.8f} °F"+''', within the existing 1 °F regression tolerance.

| Trial BHA | Saved fitted-chain water result, °F | Reproduced, °F | Saved unfitted-chain water result, °F | Reproduced, °F |
|---|---:|---:|---:|---:|
'''
trialrows=read(HERE/'trial-reproduction.csv')
for n in [10,11,12,13]:
    a=next(r for r in trialrows if r['chain']=='saved_fitted' and r['run']==f'BHA{n}')
    b=next(r for r in trialrows if r['chain']=='saved_unfitted' and r['run']==f'BHA{n}')
    text+=f"| {n} | {float(a['saved_mean_F']):.6f} | {float(a['computed_mean_F']):.6f} | {float(b['saved_mean_F']):.6f} | {float(b['computed_mean_F']):.6f} |\n"
text+='''
The whole-well comparisons below use the newly frozen observation windows and recorded mud, with water as a separate sensitivity. Their run averages need not reproduce the old trial averages. Insulated-pipe cases use the one previously fitted conductivity specified at S0, 4.9237482416889895 W/(m K), with both film multipliers. The saved unfitted chain above used its own different fitted conductivity, 4.7025289484090305 W/(m K).

## Primary comparison

Baseline `85f23db51f6661e6ca09bd05c16b9ffb48881d83`, branch `forge16b-wholewell`. Primary inputs are recorded period mud, film multiplier 1.0 and cumulative exposure. Errors below are modelled bore fluid minus measured EYE; positive means too hot. Each half-hour sample has equal weight. MD is measured depth along the hole; EOW is the End of Well Report assembly number.

| EOW BHA | Position above bit, ft | Samples | Measured mean, °C | Model mean, °C | Bias, °C (°F) | MAE, °C | RMSE, °C |
|---|---:|---:|---:|---:|---:|---:|---:|
'''
for r in primary:
    if 'bias_C' in r:
        text+=f"| {r['eow_bha']} | {r['position_ft']} | {r['n']} | {r['measured_mean_C']:.2f} | {r['model_mean_C']:.2f} | {r['bias_C']:+.2f} ({r['bias_F']:+.2f}) | {r['MAE_C']:.2f} | {r['RMSE_C']:.2f} |\n"
    else:text+=f"| {r['eow_bha']} | {r['position_ft']} | {r['n']} | unavailable | failed | unavailable | unavailable | unavailable |\n"
text+='''
EOW 3/4 positions remain unresolved: every requested branch is shown. EOW 27/38 use 84 ft as the assumed position and 22 ft as sensitivity. EOW 38's newly inspected drawing states EYE = 85 ft; the instructed 84-ft treatment is retained, with the 85-ft interpolation saved in the raw results. EOW 14 and 26 have no S0 candidate sample and are not added here.

![Whole-well comparison](wholewell-comparison.png)

The grey depth band is the original trial. EOW 17/20 supplied the prior film fit; EOW 18 supplied the pipe-conductivity fit; EOW 19 was held out but depends on that fitted conductivity. The other periods contributed to neither fit. The unresolved early positions are excluded from the independent-period pool.

| Group, primary settings | Samples | Bias, °C | MAE, °C | RMSE, °C |
|---|---:|---:|---:|---:|
'''
for r in pooled:
    if r['fluid']=='recorded_mud' and r['film_mult']==1 and r['exposure']=='cumulative' and r['position']=='nominal':
        if 'bias_C' in r:text+=f"| {r['group']} | {r['n']} | {r['bias_C']:+.2f} | {r['MAE_C']:.2f} | {r['RMSE_C']:.2f} |\n"
text+='''
## Fluid, film and recovery sensitivities

The water sensitivities keep measured volumetric flow and inlet temperature, using water inlet density to obtain mass flow. Film 0.75 is a fixed historical sensitivity, not a new fit. The recovery bound caps exposure at observed circulation since the last continuously observed pumps-off spell longer than two hours, retaining the existing one-hour floor. It assumes full recovery and does not establish that recovery occurred.

![Fluid and film sensitivities](fluid-film-sensitivities.png)

| EOW BHA | Position, ft | Cumulative mean, °C | Full-recovery mean, °C | Change, °C | Measured mean bracketed? |
|---|---:|---:|---:|---:|---|
'''
for r in recovery:text+=f"| {r['eow_bha']} | {r['position_ft']} | {r['cumulative_mean_C']:.2f} | {r['full_recovery_mean_C']:.2f} | {r['change_C']:+.2f} | {'Yes' if r['measured_mean_bracketed'] else 'No'} |\n"
text+='''
This table uses recorded mud and film 1.0. All fluid/film/clock variants are retained in [run-metrics.csv](run-metrics.csv); [depth-metrics.csv](depth-metrics.csv) gives errors by run and predeclared 500-ft MD bin. All errors are supplied in °C and °F. [recovery-bracket.csv](recovery-bracket.csv) retains paired counts and Fahrenheit changes.

| EOW BHA | Requested positions, ft | Mean position spread, °C | Maximum position spread, °C |
|---|---|---:|---:|
'''
for r in spreads:
    if r['eow_bha'] in [3,4,27,38] and r['fluid']=='recorded_mud' and r['film_mult']==1 and r['exposure']=='cumulative':
        text+=f"| {r['eow_bha']} | {r['positions_ft']} | {r['mean_position_spread_C']:.3f} | {r['max_position_spread_C']:.3f} |\n"
text+='''
Position spreads are calculated separately within each matched sample, not from a range of independent observations. [position-spreads.csv](position-spreads.csv) contains all variants.

## Mud provenance and motorless-pressure diagnostic

| EOW BHA | Mud density, lb/US gal | PV, cP | YP, lbf/100 ft² | Earlier-value fields | Reference fields | Whole mud sample carried? |
|---|---:|---:|---:|---:|---:|---|
'''
for r in plan['mud']:
    if r['eow_bha'] in [s['eow_bha'] for s in samples.values()]:
        text+=f"| {r['eow_bha']} | {r['density_ppg']:.4f} | {r['PV_cP']:.3f} | {r['YP_lbf_100ft2']:.3f} | {r['carried_fields']} | {r['reference_fields']} | {'Yes' if r['period_sample_carried'] else 'No'} |\n"
text+='''
PV denotes plastic viscosity and YP yield point. Field counts refer to completed source rows before averaging, not additional independent measurements. [mud-assignment-ledger.csv](mud-assignment-ledger.csv) identifies each original sample, every donor and each reference value. The 12 May pit cleaning separates the rheology histories. No earlier measurement is borrowed across that boundary. This leaves reference YP in much of the pre-trial and early-trial primary comparison; those results are conditional on that default. All recorded densities are treated as 20 °C surface densities, following the 16A treatment; the field measurement temperature is unknown.

| Motorless EOW BHA | Candidate windows | Candidate mean differential, psi | Candidate range, psi | Accepted 10-s EYE-row mean, psi |
|---|---:|---:|---:|---:|
'''
for r in motorless:
    mean=f"{r['candidate_mean_psi']:+.2f}" if 'candidate_mean_psi' in r else 'none'
    span=f"{r['candidate_min_psi']:+.2f} to {r['candidate_max_psi']:+.2f}" if 'candidate_mean_psi' in r else 'none'
    text+=f"| {r['eow_bha']} | {r['candidate_windows']} | {mean} | {span} | {r['accepted_10s_mean_psi']:+.2f} |\n"
text+='''
The motorless channel is not identically zero. It cannot be interpreted as verified motor-only loss. The two averaging columns use different sampling weights. No zero-offset correction is applied; motor-face heat is zero on these assemblies. Raw values, including negative values, remain in the inputs. Pressure/energy comparisons with 16A are deferred to S2.

## Execution and checks

'''
text+=f"Completed **{len(results)} / {len(plan['cases'])} planned solves**, with **{len(failures)} failed results**. The separate trial replay completed 150 converged solves. Main solve time summed over cases was {sum(r['duration_s'] for r in results):.1f} s. Failures and exceptions are retained in [solver-failures.json](solver-failures.json).\n\n"
text+='The first separate-crossover construction emitted convergence warnings and was interrupted before producing a whole-well result. It was corrected to the existing 16A aggregation of non-HWDP components; all source dimensions and lengths were retained. The original attempt is saved privately. No temperature error was used to select an aggregation, filter, sample or parameter. The [S1 protocol](../comparison_protocol_s1.md) records this correction and the S0 rulings.\n\n'
text+='The cumulative history contains '+str(plan['clock_summary']['missing_flow_rows'])+' missing-flow rows, '+str(plan['clock_summary']['incomplete_bins'])+' incomplete ten-minute bins and '+str(plan['clock_summary']['gaps_over_600s'])+' gaps longer than ten minutes. Missing coverage contributes no observed circulation and is not classified as a known stop. These are limits on both exposure clocks.\n\n'
text+='Runtime versions: '+', '.join(k+' '+v for k,v in plan['versions'].items())+'. Calculations use the existing water-property cache with BLAS/OMP threads limited to one. No model function, constant, default, golden result or tolerance was changed. No fitting, commit, merge, push, tag or release was performed.\n\n'
text+='The primary/variant outputs and source hashes are retained with this review. Commands are in [commands.md](commands.md). S1 stops here for review before energy-budget and matched-well comparisons.\n'
control=json.loads((HERE/'water-path-control/water-path-check.json').read_text())
assert control['passed'] and control['main_plan_unchanged']
control_max=max(r['max_abs_point_difference_C'] for r in control['checks'])
control_text=('A further implementation control replayed all 150 identical legacy sample/parameter combinations through the new whole-well study water path, using the legacy clock. '
              f'All converged; the largest sample difference from the original entry point was {control_max:.9g} °C. '
              'This check was performed after the whole-well run, without changing its plan or results. '
              'The original golden replay above was completed first, before whole-well predictions. '
              'Details are in [water-path-check.csv](water-path-check.csv).\n\n')
text=text.replace('## Primary comparison',control_text+'The frozen S1 protocol anticipated 146 replay solves in error. The original entry point returns 75 samples per chain (22 + 20 + 16 + 17), so each complete check actually ran 150. This is a count correction; no replay sample was added or removed.\n\n## Primary comparison')
findings='''## Findings

The sign of the discrepancy changes within 16B. The recorded-mud primary underpredicts every pre-trial run mean, with biases of −18.27 to −4.21 °C for EOW 11–16. The four trial means are overpredicted by +1.18 to +3.18 °C. The late EOW 27 and 38 mean biases are −3.80 and −1.56 °C, but their mean absolute errors are 11.84 and 5.49 °C: the small signed means conceal sample scatter. A single description of 16B as overpredicted does not cover this expanded comparison.

The early recorded-mud comparison depends materially on missing-rheology substitutions. EOW 11 and 12 use reference PV and YP; their water sensitivities have biases of −5.59 and −6.60 °C. Replacing the entire mud treatment with water therefore changes their mean predictions by more than 10 °C. This is a fluid-property sensitivity, not an isolated test of PV, and does not identify the true field rheology. Reducing the film multiplier to 0.75 lowers the predictions and increases the pre-trial underprediction.

Full recovery brackets the measured run mean in EOW 15, 16, 27 and 38. It leaves the other pre-trial means too cold and increases the trial overprediction. At EOW 27/38 it raises primary mean temperatures by 23.54/27.49 °C. This optimistic bound does not establish recovery as the explanation of the discrepancies. The requested EYE position brackets change primary predictions by less than 0.10 °C per sample and cannot account for those larger residuals.

'''
text=text.replace('## Fluid, film and recovery sensitivities',findings+'## Fluid, film and recovery sensitivities')
(OUT/'S1-review.md').write_text(text,encoding='utf-8')
summary=dict(planned_cases=len(plan['cases']),completed_cases=len(results),failed_cases=len(failures),
             solve_duration_sum_s=sum(r['duration_s'] for r in results),samples=len(samples),
             main_plan_sha256=hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest(),versions=plan['versions'])
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
