"""Summarise S2 numerical evidence without further model solves."""
import csv
import gzip
import json
import math
import statistics as st
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np

FINDINGS='''## Findings

The 16B revision raises the EOW 11 and 12 model means by 7.69 and 8.48 °C, leaving biases of −8.49 and −9.80 °C. EOW 16 changes from −4.80 to +0.14 °C, while trial EOW 17 changes from +3.18 to +8.74 °C. Several other runs are unchanged. The revision removes the input-inconsistent reference fallback; it does not remove the changing sign of the field discrepancy.

At 16A BHA 42, the unchanged blind bias of −19.87 to −18.69 °C becomes +12.72 to +13.89 °C with water rheology, a model-mean increase of 32.57–32.60 °C. All nine run means become too hot in this sensitivity. Across all 358 16A samples, mean return-temperature error worsens from −5.85 to −7.98 °C. Water rheology at recorded density is a diagnostic sensitivity, not an established description of the measured drilling mud.

All reported annulus profile cells are on the turbulent heat-transfer branch. Minimum sampled thermal Re is 7,445 for original 16A and 5,113 for original 16B; the sensitivities increase those minima. The strong temperature changes occur within that branch. Mean length-weighted annulus film increases from 2,020 to 6,928 W/(m² K) across the same 358 16A samples. In contrast, the apparent-viscosity hydraulic test gives mean laminar length fractions of 29.7% in original 16A, 71.4% in original 16B and 4.6% in revised 16B. These distinct model tests must not be conflated. Higher downhole predictions accompany higher film coefficients even though the calculated friction-heating input decreases.

The model underpredicts measured SPP minus raw differential by a mean 1,624 psi in original 16A and 969 psi in revised 16B. Measured mean SPP × inlet flow is 928/527 kW for 16A/16B. The model's distributed friction plus nozzle and motor-face heat is 500/244 kW on the same pressure-supported samples. Motor/MWD losses and the meaning of the differential remain uncertain, so this pressure gap cannot be assigned to distributed friction alone. The temperature equivalent of all measured hydraulic power, using inlet mass flow and heat capacity, averages 5.88/2.98 °C. Rock exchange and internal transfer remain essential to interpreting the thermal results.

Ten predeclared depth bins have downhole observations in both wells. The Q4 tables retain the geometry, temperature boundaries and rheology differences, with actual depth ranges and unmatched bins. They do not identify a unique cause of the residuals or select a corrective parameter.

'''

HERE=Path(__file__).resolve().parent/'s2'
plan=json.loads((HERE/'plan.json').read_text())
rows=[json.loads(x) for x in (HERE/'results.jsonl').read_text().splitlines()]
assert len(rows)==len(plan['cases'])==934
samples={s['id']:s for s in plan['samples']};lookup={(r['sample'],r['rheology_case']):r for r in rows}
def read(p):
    with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def save(name,rr):
    rr=list(rr);keys=list(dict.fromkeys(k for r in rr for k in r))
    with (HERE/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rr)
def avg(rr,key):
    xs=[r[key] for r in rr if isinstance(r.get(key),(int,float)) and not isinstance(r[key],bool) and math.isfinite(r[key])]
    return st.mean(xs) if xs else None
def fmt(value,digits=2):return f'{value:.{digits}f}' if value is not None else 'unavailable'
def temp(r,branch):
    s=samples[r['sample']]
    if r['rheology_case']=='blind_original':return float(s['saved_primary'][branch.replace('_0ft','_bit')])
    if r['rheology_case']=='s1_original':return float(s['saved_primary'][branch])
    return r[branch]
def met(pairs):
    errors=[m-o for m,o in pairs]
    if not errors:return dict(n=0)
    return dict(n=len(errors),measured_mean_C=st.mean(o for _,o in pairs),model_mean_C=st.mean(m for m,_ in pairs),
        bias_C=st.mean(errors),MAE_C=st.mean(map(abs,errors)),RMSE_C=math.sqrt(st.mean(x*x for x in errors)),
        max_abs_C=max(map(abs,errors)),bias_F=st.mean(errors)*1.8,MAE_F=st.mean(map(abs,errors))*1.8,
        RMSE_F=math.sqrt(st.mean(x*x for x in errors))*1.8)
metrics=defaultdict(list);depth_metrics=defaultdict(list)
for r in rows:
    if not r['success']:continue
    s=samples[r['sample']]
    channels=[('EYE',s['measured_MWD_C'],[f'bore_{p}ft_C' for p in s['requested_positions_ft']])] if s['well']=='16B' else [
        (ch,s['measured_'+ch],['bore_0ft_C','bore_40ft_C','annulus_0ft_C','annulus_40ft_C'])
        for ch in ['bit_box_C','top_sub_C'] if 'measured_'+ch in s]
    channels.append(('return',s['measured_return_C'],['return_C']))
    for ch,obs,branches in channels:
        for branch in branches:
            pair=(temp(r,branch),obs)
            metrics[s['well'],s['run'],r['rheology_case'],ch,branch].append(pair)
            metrics[s['well'],'ALL',r['rheology_case'],ch,branch].append(pair)
            if s['well']=='16A' and not s['washout']:metrics[s['well'],'ALL excluding washout',r['rheology_case'],ch,branch].append(pair)
            depth_metrics[s['well'],s['run'],r['rheology_case'],ch,branch,int(s['bit_ft']//500)*500].append(pair)
mm=[dict(well=w,run=run,rheology_case=mode,channel=ch,branch=branch,**met(pairs)) for (w,run,mode,ch,branch),pairs in metrics.items()]
dd=[dict(well=w,run=run,rheology_case=mode,channel=ch,branch=branch,depth_bin_start_ft=lo,depth_bin_end_ft=lo+500,**met(pairs)) for (w,run,mode,ch,branch,lo),pairs in depth_metrics.items()]
save('temperature-metrics.csv',mm);save('temperature-depth-metrics.csv',dd)
def get(w,run,mode,ch,branch):return next(r for r in mm if (r['well'],r['run'],r['rheology_case'],r['channel'],r['branch'])==(w,run,mode,ch,branch))
brows=[]
for s in plan['samples']:
    if s['well']!='16B':continue
    for p in s['requested_positions_ft']:
        if any(x['run']==s['run'] and x['position_ft']==p for x in brows):continue
        old=get('16B',s['run'],'s1_original','EYE',f'bore_{p}ft_C');new=get('16B',s['run'],'s2_revised','EYE',f'bore_{p}ft_C')
        brows.append(dict(run=s['run'],position_ft=p,n=old['n'],measured_mean_C=old['measured_mean_C'],
            S1_v1_model_mean_C=old['model_mean_C'],S2_v2_model_mean_C=new['model_mean_C'],
            S1_v1_bias_C=old['bias_C'],S2_v2_bias_C=new['bias_C'],change_model_C=new['model_mean_C']-old['model_mean_C'],
            S1_v1_MAE_C=old['MAE_C'],S2_v2_MAE_C=new['MAE_C']))
save('16b-primary-revision.csv',brows)
arows=[]
for run in ['18','23','30','34','35r1','35r2','38','39','42','ALL','ALL excluding washout']:
    branches=['bore_0ft_C','bore_40ft_C','annulus_0ft_C','annulus_40ft_C']
    old=[get('16A',run,'blind_original','bit_box_C',branch) for branch in branches]
    new=[get('16A',run,'water_rheology_sensitivity','bit_box_C',branch) for branch in branches]
    arows.append(dict(run=run,n=old[0]['n'],measured_mean_C=old[0]['measured_mean_C'],
        blind_bias_min_C=min(x['bias_C'] for x in old),blind_bias_max_C=max(x['bias_C'] for x in old),
        sensitivity_bias_min_C=min(x['bias_C'] for x in new),sensitivity_bias_max_C=max(x['bias_C'] for x in new),
        model_mean_change_min_C=min(n['model_mean_C']-o['model_mean_C'] for o,n in zip(old,new)),
        model_mean_change_max_C=max(n['model_mean_C']-o['model_mean_C'] for o,n in zip(old,new))))
save('16a-rheology-sensitivity.csv',arows)

energy=[]
for r in rows:
    s=samples[r['sample']]
    energy.append({**r,'source':s.get('source','Pason frozen on-bottom windows'),'time':s['time'],'depth_ft_MD':s['bit_ft'],
        'measured_spp_psi':s['spp_psi'],'raw_differential_psi':s['raw_differential_psi'],
        'motor_heat_psi':s['motor_heat_psi'],'pressure_source':s['pressure_source'],'pressure_count':s['pressure_count'],
        'flow_gpm':s['flow_gpm'],'inlet_C':s['T_in_C'],'measured_return_C':s['measured_return_C'],
        'washout':s.get('washout',False),'fit_role':s.get('fit_role','not fitted')})
save('energy-samples.csv',energy)
keys=['spp','measured_spp_psi','raw_spp_residual_psi','adjusted_spp_residual_psi','measured_hydraulic_power_W',
      'model_spp_at_inlet_flow_W','hydraulic_local_friction_power_W','thermal_friction_power_W','thermal_nozzle_power_W',
      'motor_face_power_W','rock_exchange_W','model_rise_C','measured_rise_C','rise_error_C',
      'thermal_laminar_length_fraction','hydraulic_laminar_length_fraction','Re_thermal_length_mean','h_annulus_W_m2K_length_mean',
      'rise_distributed_friction_C','rise_rock_C','rise_internal_cp_C','rise_nozzle_C','rise_motor_C','rise_closure_error_C']
egroups=defaultdict(list)
for r in energy:
    if not r['success']:continue
    egroups[r['well'],r['run'],r['rheology_case']].append(r)
    egroups[r['well'],'ALL',r['rheology_case']].append(r)
    if r['well']=='16A' and not r['washout']:egroups[r['well'],'ALL excluding washout',r['rheology_case']].append(r)
esummary=[]
for (well,run,mode),rr in egroups.items():
    pp=[r for r in rr if r['measured_spp_psi'] is not None]
    out=dict(well=well,run=run,rheology_case=mode,n=len(rr),n_pressure=len(pp))
    for key in keys:
        # Pressure/power comparisons use only the same samples as measured SPP.
        pressure_key=key in keys[:10]
        out[key+'_mean']=avg(pp if pressure_key else rr,key)
    for key in ['raw_spp_residual_psi','adjusted_spp_residual_psi','rise_error_C']:
        used=pp if 'spp' in key else rr
        vals=[x[key] for x in used if isinstance(x.get(key),(int,float))]
        out[key+'_MAE']=st.mean(map(abs,vals)) if vals else None
    esummary.append(out)
save('energy-run-summary.csv',esummary)

geometry={r['sample']:{k:(v if k in ['sample','well','run','pipe_type'] else float(v)) for k,v in r.items()} for r in read(HERE/'geometry-samples.csv')}
q4=[]
for r in energy:
    s=samples[r['sample']]
    if s['well']=='16A' and s['source']!='Sanvean on-bottom':continue
    row={**geometry[s['id']],**r,'depth_bin_start_ft':int(s['bit_ft']//500)*500,
        'measured_downhole_C':s['measured_MWD_C'] if s['well']=='16B' else s['measured_bit_box_C'],
        'measured_channel':'EYE' if s['well']=='16B' else 'bit box',
        'top_sub_measured_C':s.get('measured_top_sub_C'),'sensor_medium':'bore interpretation' if s['well']=='16B' else 'unresolved bore/annulus',
        'sensor_positions_ft':';'.join(map(str,s['requested_positions_ft'])),'position_unresolved':s['nominal_position_ft'] is None,
        'cooler_context':s['cooler_context'],'ROP_ft_h':s['rop_ft_h'],
        'hours_since_last_observed_off_over2h':s['hours_since_last_observed_off_over2h'],
        'hours_since_near_surface_trip_proxy':s['hours_since_near_surface_trip_proxy'],
        'confirmed_surface_trip_time_available':s['confirmed_surface_trip_time_available']}
    row['model_sensor_bore_C']=temp(r,f"bore_{s['nominal_position_ft']}ft_C") if s['well']=='16B' and s['nominal_position_ft'] is not None else None
    q4.append(row)
save('matched-sample-inputs.csv',q4)
bgroups=defaultdict(list)
for r in q4:bgroups[r['well'],r['rheology_case'],r['depth_bin_start_ft']].append(r)
bkeys=['depth_ft_MD','bit_tvd_ft','formation_at_bit_C','flow_gpm','inlet_C','measured_downhole_C',
       'bore_0ft_C','bore_40ft_C','annulus_0ft_C','annulus_40ft_C','bore_84ft_C','annulus_84ft_C','model_sensor_bore_C',
       'density_ppg','pv_ref_cP','yp_lbf_100ft2','tfa_in2','ordinary_pipe_OD_in','ordinary_pipe_ID_in','open_hole_diameter_in',
       'Re_thermal_length_mean','h_annulus_W_m2K_length_mean','thermal_laminar_length_fraction','hydraulic_laminar_length_fraction',
       'measured_spp_psi','raw_differential_psi','motor_heat_psi','ROP_ft_h','hours_since_last_observed_off_over2h',
       'hours_since_near_surface_trip_proxy']
bins=[]
for (well,mode,lo),rr in bgroups.items():
    good=[r for r in rr if r['success']]
    out=dict(well=well,rheology_case=mode,bin_start_ft=lo,bin_end_ft=lo+500,n=len(rr),converged=len(good),
        runs=';'.join(sorted({r['run'] for r in rr})),actual_depth_min_ft=min(r['depth_ft_MD'] for r in rr),actual_depth_max_ft=max(r['depth_ft_MD'] for r in rr),
        cooler_context=' | '.join(sorted({r['cooler_context'] for r in rr})),
        fit_roles=' | '.join(sorted({r['fit_role'] for r in rr})),washout_samples=sum(r['washout'] for r in rr))
    out.update({k:avg(good,k) for k in bkeys});bins.append(out)
save('matched-bin-inputs.csv',bins)
paired=[]
for lo in sorted({r['bin_start_ft'] for r in bins}):
    aa=next((r for r in bins if (r['well'],r['rheology_case'],r['bin_start_ft'])==('16A','blind_original',lo)),None)
    bb=next((r for r in bins if (r['well'],r['rheology_case'],r['bin_start_ft'])==('16B','s2_revised',lo)),None)
    row=dict(bin_start_ft=lo,bin_end_ft=lo+500,shared=aa is not None and bb is not None,n_16A=aa['n'] if aa else 0,n_16B=bb['n'] if bb else 0)
    if aa and bb:
        row['sample_depth_ranges_overlap']=max(aa['actual_depth_min_ft'],bb['actual_depth_min_ft'])<=min(aa['actual_depth_max_ft'],bb['actual_depth_max_ft'])
        row['gap_between_sample_depth_ranges_ft']=max(0,max(aa['actual_depth_min_ft'],bb['actual_depth_min_ft'])-min(aa['actual_depth_max_ft'],bb['actual_depth_max_ft']))
    for prefix,item in [('A',aa),('B',bb)]:
        if item:row.update({prefix+'_'+k:v for k,v in item.items() if k not in ['well','bin_start_ft','bin_end_ft']})
    paired.append(row)
save('matched-primary-comparison.csv',paired)

# Compact cell-level archive, preserving depth-dependent regimes and film.
with gzip.open(HERE/'annulus-profiles.csv.gz','wt',newline='',encoding='utf-8') as f:
    fields=['case_id','well','run','rheology_case','md_m','cell_length_m','annulus_T_C','Re_thermal','thermal_laminar',
            'h_annulus_W_m2K','Re_hydraulic_apparent','hydraulic_laminar','mu_Pas','rho_kg_m3','velocity_m_s','Dh_annulus_m']
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for r in rows:
        p=HERE/'profiles'/(r['case_id']+'.npz')
        if not p.exists():continue
        with np.load(p) as data:
            for i,z in enumerate(data['z']):
                row={k:r[k] for k in ['case_id','well','run','rheology_case']}
                row.update(md_m=float(z),cell_length_m=float(data['length_m'][i]))
                for k in fields[6:]:
                    v=data[k][i];row[k]=bool(v) if k.endswith('laminar') else float(v)
                w.writerow(row)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,ax=plt.subplots(1,2,figsize=(14,5.5))
for mode,col,label in [('s1_original','tab:blue','16B S1 primary'),('s2_revised','tab:orange','16B revised primary')]:
    first=True
    for run in sorted({s['run'] for s in samples.values() if s['well']=='16B'},key=int):
        rr=[r for r in rows if r['well']=='16B' and r['run']==run and r['rheology_case']==mode and r['success']]
        rr.sort(key=lambda r:samples[r['sample']]['bit_ft'])
        x=[samples[r['sample']]['bit_ft'] for r in rr]
        y=[temp(r,f"bore_{samples[r['sample']]['nominal_position_ft'] or 22}ft_C")-samples[r['sample']]['measured_MWD_C'] for r in rr]
        ax[0].plot(x,y,'o-',ms=3,lw=1,color=col,label=label if first else None);first=False
aruns=['18','23','30','34','35r1','35r2','38','39','42']
for i,run in enumerate(aruns):
    r=next(r for r in arows if r['run']==run)
    for mode,col,shift in [('blind','tab:blue',-.12),('sensitivity','tab:orange',.12)]:
        lo=r[mode+'_bias_min_C'];hi=r[mode+'_bias_max_C'];mid=(lo+hi)/2
        ax[1].errorbar(i+shift,mid,yerr=[[mid-lo],[hi-mid]],fmt='o',capsize=4,color=col,
                       label=('16A blind' if mode=='blind' else 'Water rheology, recorded density') if i==0 else None)
ax[0].set(xlabel='Bit depth [ft MD]',ylabel='Model minus EYE [°C]',title='16B missing-rheology protocol revision')
ax[1].set_xticks(range(len(aruns)),aruns);ax[1].set(xlabel='16A BHA',ylabel='Mean model minus bit box [°C]',title='16A rheology sensitivity; four-branch ranges')
for x in ax:x.axhline(0,color='k',lw=.8);x.grid(alpha=.25);x.legend(fontsize=8)
fig.tight_layout();fig.savefig(HERE/'rheology-comparison.png',dpi=160);plt.close(fig)
fig,ax=plt.subplots(1,2,figsize=(13,5.5))
for well,mode,col in [('16A','blind_original','tab:blue'),('16B','s2_revised','tab:orange')]:
    rr=[r for r in energy if r['well']==well and r['rheology_case']==mode and r['success']]
    pp=[r for r in rr if r['measured_spp_psi'] is not None and 'adjusted_spp_residual_psi' in r]
    ax[0].scatter([r['spp_minus_raw_differential_psi'] for r in pp],[r['spp']/6894.757 for r in pp],s=12,alpha=.65,color=col,label=well)
    ax[1].scatter([r['measured_rise_C'] for r in rr],[r['model_rise_C'] for r in rr],s=12,alpha=.6,color=col,label=well)
for x in ax:
    limits=x.get_xlim()+x.get_ylim();lo=min(limits);hi=max(limits);x.plot([lo,hi],[lo,hi],'k--',lw=.8);x.grid(alpha=.25);x.legend()
ax[0].set(xlabel='Measured SPP minus raw differential [psi]',ylabel='Modelled SPP [psi]',title='Pressure comparison; motor/MWD losses remain uncertain')
ax[1].set(xlabel='Measured outlet minus inlet [°C]',ylabel='Modelled outlet minus inlet [°C]',title='Paired temperature rise')
fig.tight_layout();fig.savefig(HERE/'energy-comparison.png',dpi=160);plt.close(fig)

text='''# FORGE 16B and 16A: S2 review

## Protocol revision and preserved evidence

The revised missing-rheology rule was fixed from the inputs after S1 review. Missing PV/YP uses the nearest actual measurement in either time direction within the same fluid system; a system without a measurement uses water viscosity or zero yield point at recorded density. The original S1 primary remains version 1. The new 16B primary is version 2. The 16A blind result remains unchanged; its water-rheology run is a sensitivity. No parameter was fitted and no model function, constant, default, golden or regression tolerance was changed.

The earlier weighted-programme reference PV 27 cP and YP 28 lbf/100 ft² are inconsistent with the reported low-solids water-rich 16B mud. The revised early low-solids assignments use PV 2 cP and YP 1 lbf/100 ft². The [donor ledger](mud-revision-ledger.csv) includes signed time offsets; no donor crosses a fluid-system boundary. The post-TD high-viscosity sweep/logging fluid is separated from drilling fluid using the 17 June operations report. Some nearest measurements remain days away from the selected sample, so the actual contemporaneous rheology remains uncertain.

PV means plastic viscosity; YP means yield point. MD is measured depth along the hole; TVD is true vertical depth. Error signs are model minus measurement. Annulus film means the model's local convective coefficient, not overall conductance through casing and rock.

## 16B primary: both protocol versions

| EOW BHA | Position, ft above bit | Samples | S1 v1 bias, °C | Revised v2 bias, °C | Change in model, °C |
|---|---:|---:|---:|---:|---:|
'''
for r in brows:text+=f"| {r['run']} | {r['position_ft']} | {r['n']} | {r['S1_v1_bias_C']:+.2f} | {r['S2_v2_bias_C']:+.2f} | {r['change_model_C']:+.2f} |\n"
text+='''
The original 109 windows, geometry and sensor interpretations are unchanged. EOW 3/4 remain unresolved across the listed positions. EOW 27/38 retain the assumed 84-ft position and 22-ft sensitivity. All original S1 recovery/film sensitivities remain tied to version 1; they have not been silently reinterpreted with the revised mud.

## 16A water-rheology sensitivity

| 16A BHA | Bit-box samples | Unchanged blind bias range, °C | Water-rheology sensitivity bias range, °C | Change in model mean, °C |
|---|---:|---:|---:|---:|
'''
for r in arows:text+=f"| {r['run']} | {r['n']} | {r['blind_bias_min_C']:+.2f} to {r['blind_bias_max_C']:+.2f} | {r['sensitivity_bias_min_C']:+.2f} to {r['sensitivity_bias_max_C']:+.2f} | {r['model_mean_change_min_C']:+.2f} to {r['model_mean_change_max_C']:+.2f} |\n"
text+='''
Each range preserves the four predetermined bore/annulus and bit/40-ft branches. No closest endpoint is selected. The sensitivity retains recorded density and the mixture's thermal properties; only viscosity and yield point change. All 358 primary samples were evaluated, including 223 return-only samples. Top-sub comparisons, per-depth results and °F errors are in [temperature-metrics.csv](temperature-metrics.csv) and [temperature-depth-metrics.csv](temperature-depth-metrics.csv). BHA 35 washout flags remain explicit.

![Rheology comparison](rheology-comparison.png)

## Regime, heat transfer and energy

The heat-transfer routine uses Reynolds number based on plastic viscosity, with the laminar floor at Re < 2300. Bingham hydraulics separately uses apparent viscosity, including YP, with a threshold of 2100. The existing distributed thermal-friction routine uses the Newtonian friction-factor treatment on plastic viscosity and a 5 MPa liquid-property floor. These existing treatments are reported separately; none was changed for this study.

The full depth-dependent Reynolds numbers, both regime flags, annulus film and viscosity are in [annulus-profiles.csv.gz](annulus-profiles.csv.gz). [energy-samples.csv](energy-samples.csv) includes per-sample depth-weighted summaries and sensor-position values. A mean Reynolds number is not used to classify the whole annulus; laminar length fractions are reported directly.

| Well / treatment / BHA | Samples / pressure | Thermal laminar length, mean % | Annulus film, length mean W/(m² K) | Measured SPP, mean psi | Model SPP, mean psi | Adjusted SPP residual, mean psi | Rise error, mean °C |
|---|---:|---:|---:|---:|---:|---:|---:|
'''
for r in esummary:
    if r['run'] not in ['ALL','ALL excluding washout'] and r['rheology_case'] in ['blind_original','s2_revised']:
        text+=f"| {r['well']} / {r['run']} | {r['n']} / {r['n_pressure']} | {100*r['thermal_laminar_length_fraction_mean']:.1f} | {r['h_annulus_W_m2K_length_mean_mean']:.1f} | {fmt(r['measured_spp_psi_mean'],0)} | {fmt(r['spp_mean']/6894.757 if r['spp_mean'] is not None else None,0)} | {fmt(r['adjusted_spp_residual_psi_mean'],0)} | {r['rise_error_C_mean']:+.2f} |\n"
text+='''
Pressure columns use only the same samples with measured SPP. Temperature-rise columns use all listed samples. There are 135 Sanvean pressure comparisons in 16A and 109 Pason comparisons in 16B; 16A's 223 return-only samples have no substituted pressure. The adjusted residual is model SPP minus (measured SPP minus raw reported differential). It can include unmodelled motor/MWD losses and an uncertain differential zero. Raw-pressure comparisons and valid counts remain in the CSV.

| Well / primary treatment | Pressure samples | Measured SPP × inlet flow, kW | Thermal distributed friction, kW | Thermal nozzle heat, kW | Motor-face heat, kW | Local-volume hydraulic friction, kW |
|---|---:|---:|---:|---:|---:|---:|
'''
for r in esummary:
    if r['run']=='ALL' and r['rheology_case'] in ['blind_original','s2_revised']:
        text+=f"| {r['well']} | {r['n_pressure']} | {r['measured_hydraulic_power_W_mean']/1000:.1f} | {r['thermal_friction_power_W_mean']/1000:.1f} | {r['thermal_nozzle_power_W_mean']/1000:.1f} | {r['motor_face_power_W_mean']/1000:.1f} | {r['hydraulic_local_friction_power_W_mean']/1000:.1f} |\n"
text+='''
All power means above use the same pressure-supported subset. The heat and pressure friction terms are not assumed equal. Nozzle and motor heat are separately identified. Rock exchange and the internal heat-capacity contribution are retained in the temperature-balance columns; internal pipe exchange is not treated as a new external power source. The complete budget and all sensitivities are in [energy-run-summary.csv](energy-run-summary.csv).

![Pressure and temperature rise](energy-comparison.png)

## Q4: matched depth bins

These are the predeclared 500-ft MD bins with observations in both wells. They are not exact depth matches: [matched-primary-comparison.csv](matched-primary-comparison.csv) includes actual depth ranges, gaps between their sampled ranges, TVD and formation temperature. Equal MD does not imply equal formation temperature. All unmatched bins are retained in that file.

| MD bin, ft | n 16A / 16B | Measured downhole mean, °C A / B | Model bore-at-bit A / declared-position bore B, °C | Mean annulus Re A / B | Mean film A / B, W/(m² K) | Mean PV A / B, cP | Mean YP A / B, lbf/100 ft² |
|---|---:|---:|---:|---:|---:|---:|---:|
'''
for r in paired:
    if not r['shared']:continue
    text+=f"| {r['bin_start_ft']}–{r['bin_end_ft']} | {r['n_16A']} / {r['n_16B']} | {r['A_measured_downhole_C']:.2f} / {r['B_measured_downhole_C']:.2f} | {r['A_bore_0ft_C']:.2f} / {r['B_model_sensor_bore_C']:.2f} | {r['A_Re_thermal_length_mean']:.0f} / {r['B_Re_thermal_length_mean']:.0f} | {r['A_h_annulus_W_m2K_length_mean']:.0f} / {r['B_h_annulus_W_m2K_length_mean']:.0f} | {r['A_pv_ref_cP']:.2f} / {r['B_pv_ref_cP']:.2f} | {r['A_yp_lbf_100ft2']:.2f} / {r['B_yp_lbf_100ft2']:.2f} |\n"
text+='''
The displayed model columns identify fixed branches; the full table retains all 16A sensor branches and 16B positions without selecting by error. The per-sample [matched-sample-inputs.csv](matched-sample-inputs.csv) includes flow, inlet, cooler annotations, ROP, raw differential, face-heat load, nozzle area, geometry and time since observed stop/trip proxies. [string-segments.csv](string-segments.csv) lists each actual modelled string. Bin means and both sensitivities are in [matched-bin-inputs.csv](matched-bin-inputs.csv).

The 16A recorded long stops are trip proxies, not confirmed string movements. A missing confirmed surface-trip time remains missing. 16B's near-surface proxy is labelled separately. Cooler operation and fluid sweeps are contextual observations, not fitted heat-removal or composition corrections.

## Verification and scope

'''
good=[r for r in rows if r['success']];replays=[r for r in good if 'max_saved_temperature_difference_C' in r]
text+=f"Completed {len(rows)}/{len(plan['cases'])} planned cases, with {len(rows)-len(good)} failures. Maximum replay difference from the preserved earlier primary is {max(r['max_saved_temperature_difference_C'] for r in replays):.9g} °C. Maximum absolute temperature-balance quadrature closure is {max(abs(r['rise_closure_error_C']) for r in good):.6f} °C. Summed solve/diagnostic execution time is {sum(r['duration_s'] for r in rows):.1f} s.\n\n"
text+='The original S1 and 16A evidence are preserved. The revised 16B donor rule is a labelled protocol change made after seeing S1; no sample or filter was changed. This sensitivity does not establish that the true field fluid had water rheology. The [S2 protocol](../comparison_protocol_s2.md) records the definitions before these new results. Commands and versions are in [commands.md](commands.md). Work stops after S2; there is no documentation integration, commit, merge, push, tag or release.\n'
text=text.replace('## 16B primary: both protocol versions',FINDINGS+'## 16B primary: both protocol versions')
text=text.replace('Temperature-rise columns use all listed samples.','Annulus and temperature-rise columns use all listed samples.')
(HERE/'S2-review.md').write_text(text,encoding='utf-8')
summary=dict(cases=len(rows),failures=len(rows)-len(good),cases_by_type=dict(Counter(r['well']+' '+r['rheology_case'] for r in rows)),
             max_replay_difference_C=max(r['max_saved_temperature_difference_C'] for r in replays),
             max_abs_closure_C=max(abs(r['rise_closure_error_C']) for r in good),
             versions=plan['versions'],sum_case_duration_s=sum(r['duration_s'] for r in rows))
(HERE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
