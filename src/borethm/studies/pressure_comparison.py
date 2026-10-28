"""Unfitted pressure comparisons using recorded FORGE programme inputs.

The development-data entry point reuses the registered 16A and 16B samples,
rock properties, exposure clocks and rheology. It reports the original
calculation at both field viscosity reference temperatures and the revised
hydraulic calculation. Previously fitted temperature parameters stay fixed.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import replace
from functools import lru_cache
import json
import math
from pathlib import Path
import statistics
import time

import numpy as np

from borethm import fluids, hydraulic_losses as hl, model1_coupled as m1
from borethm import well_geometry as wg
from borethm._paths import repository_path
from borethm.studies import forge16_energy as energy
from borethm.studies import validate_forge16a as a
from borethm.studies import validate_forge16b as b
from borethm.studies import validate_forge16b_wholewell as whole

FT, INCH, GPM, PSI = whole.FT, whole.INCH, whole.GPM, whole.PSI
VARIANTS = (('v1.5.0-26.7', 'v1.5.0', 26.7),
            ('v1.5.0-48.9', 'v1.5.0', 48.9),
            ('v1.6.0-48.9', 'v1.6.0', 48.9))


def write_csv(path, rows):
    rows=list(rows)
    fields=list(dict.fromkeys(k for row in rows for k in row))
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fields,lineterminator='\n')
        writer.writeheader();writer.writerows(rows)


def summaries(rows):
    """One median prediction and observation per event, then equal event weights."""
    groups={}
    for row in rows:
        key=tuple(row[k] for k in ('well','role','bha','variant','scenario','event_id'))
        groups.setdefault(key,[]).append(row)
    events=[]
    for key,items in sorted(groups.items()):
        row=dict(zip(('well','role','bha','variant','scenario','event_id'),key))
        good=[r for r in items if r['status']=='ok']
        row.update(windows=len(items),converged=sum(r.get('solver_success',False) for r in items),
                   compared=len(good),failed=sum(r['status']=='solver_failure' for r in items),
                   missing_target=sum(r['status']=='missing_target' for r in items))
        if good:
            for field in ('comparison_target_psi','predicted_low_psi','predicted_high_psi',
                          'flow_gpm','bit_depth_ft'):
                row[field]=statistics.median(r[field] for r in good)
            for end in ('low','high'):
                residual=row['predicted_'+end+'_psi']-row['comparison_target_psi']
                row['residual_'+end+'_psi']=residual
                row['residual_'+end+'_percent']=100*residual/row['comparison_target_psi'] if row['comparison_target_psi'] else None
            if any(r.get('is_motor_interval') for r in good):
                row['interval_coverage']=row['predicted_low_psi']<=row['comparison_target_psi']<=row['predicted_high_psi']
        events.append(row)
    groups={}
    for row in events:
        key=tuple(row[k] for k in ('well','role','bha','variant','scenario'))
        groups.setdefault(key,[]).append(row)
    bhas=[]
    for key,items in sorted(groups.items()):
        row=dict(zip(('well','role','bha','variant','scenario'),key))
        row.update(planned_events=len(items),compared_events=sum(r['compared']>0 for r in items),
                   planned_windows=sum(r['windows'] for r in items),compared_windows=sum(r['compared'] for r in items),
                   failed_windows=sum(r['failed'] for r in items),missing_target_windows=sum(r['missing_target'] for r in items))
        good=[r for r in items if r['compared']]
        for field in ('comparison_target_psi','predicted_low_psi','predicted_high_psi',
                      'residual_low_psi','residual_high_psi','residual_low_percent','residual_high_percent'):
            values=[r[field] for r in good if r.get(field) is not None]
            if values:
                row[field+'_median']=statistics.median(values)
                row[field+'_min']=min(values);row[field+'_max']=max(values)
        coverage=[r['interval_coverage'] for r in good if 'interval_coverage' in r]
        if coverage:row.update(interval_covered_events=sum(coverage),interval_coverage_fraction=sum(coverage)/len(coverage))
        bhas.append(row)
    return events,bhas


def entry1_geometry(s,components,legacy,scenario):
    """Serial recorded passages with the declared connection scenarios.

    The short bit-body annulus retains the existing aggregate envelope,
    as in the motorless pressure accounting. Gauge OD is not a cylindrical
    blockage. Unknown proprietary tool operating losses remain unspecified.
    """
    if s['well']=='16B' and s['run'] in ('17','18','19','20'):
        # The trial protocol retains aggregate assemblies. Preserve both
        # ordinary-pipe sections in the partial insulated string.
        segments=[]
        for original in legacy.string:
            pipe=original.pipe
            if pipe.name==b.HWDP.name:
                joint=hl.HydraulicJoint((7. if scenario=='EIS' else 7.25)*INCH,
                    2*pipe.r_bore,29*INCH,b.HWDP_JOINT_FT*FT,
                    source='S2b connection scenario; trial HWDP bore and recorded pitch')
            elif pipe.name==b.DRILL_PIPE.name or pipe.name.startswith('IDP,'):
                od,jid=(7.,4.) if scenario=='EIS' else (7.25,3.5)
                joint=hl.HydraulicJoint(od*INCH,jid*INCH,29*INCH,(2378/75)*FT,
                    source='S2b NOV connection scenario; original trial ordinary-pipe pitch')
            else:
                segments.append(original)
                continue
            segments.append(replace(original,pipe=replace(pipe,hydraulic_joint=joint)))
        return wg.WellGeometry(segments,legacy.hole,legacy.survey)
    records=components[s['run']]
    bottom=[]
    for component in records:
        od=component['od_in']
        inside=component['primary_id_in'] if s['well']=='16A' else component['id_in']
        if 'bit' in component['component'].lower():
            od=2*float(legacy.at(np.array([legacy.md_bit]))['r_out'][0])/INCH
        pipe=whole.steel(component['component'],od,inside)
        if component['kind']=='HWDP':
            joint_od=7. if scenario=='EIS' else 7.25 if scenario=='GPDS55' else 6.625
            joint=hl.HydraulicJoint(joint_od*INCH,inside*INCH,29*INCH,
                component['length_ft']*FT/30 if s['well']=='16B' else 31.5*FT,
                source='S2b 29-in effective restriction; recorded HWDP bore; catalogue connection scenario')
            pipe=replace(pipe,hydraulic_joint=joint)
        bottom.append(wg.StringSegment(component['length_ft']*FT,pipe))
    regular=legacy.md_bit-sum(c.length for c in bottom)
    if regular<=0:raise ValueError('Assembly longer than circulation depth')
    od,jid=(7.,4.) if scenario=='EIS' else (7.25,3.5) if scenario=='GPDS55' else (6.625,3.25)
    pipe=replace(legacy.string[0].pipe,hydraulic_joint=hl.HydraulicJoint(od*INCH,jid*INCH,29*INCH,
        (2378/75 if s['well']=='16B' else 31.5)*FT,
        source='S2b NOV connection scenarios' if s['well']=='16B' else 'NOV GPDS50 compatible connection scenario; 31.5-ft catalogue pitch'))
    return wg.WellGeometry([wg.StringSegment(regular,pipe),*reversed(bottom)],legacy.hole,legacy.survey)


@lru_cache(maxsize=1)
def assembly_audit():
    """Original unknowns and declared D5 interpretations, never targets."""
    return json.loads(repository_path('validation/model-development/d5/components.json').read_text(encoding='utf-8'))


def unknown_motor(source):
    """Zero internal loss placeholder, explicitly qualified as unmeasured."""
    return hl.ReferenceToolLoss(0.,1.,1000.,basis='total_internal',
        source='motor loss unknown; '+source,unresolved=True,include_boundary_changes=False)


def serial_development_geometry(s,components,legacy,scenario):
    """D5: motor thermal bores are separate from internal tool pressure loss.

    Unknown non-motor bores prevent a calculation. A bit is represented only
    by the nozzle boundary. The pre-correction adapter remains available as
    entry1_geometry for reproducing the declared diagnostic and its archive.
    """
    rows=[r for r in assembly_audit() if r['well']==s['well'] and r['bha']==s['run']]
    if not rows:raise ValueError('Assembly is absent from the component audit')
    if s['well']=='16B' and s['run'] in ('17','18','19','20'):
        original=entry1_geometry(s,components,legacy,scenario)
        # Keep the original trial layout and its transferred Figure 90 basis.
        # Separate the motor from the residual compact assembly, excluding
        # the reported motor mandrel from the thermal weighted mean.
        source=[r for r in rows if 2<=r['item']<=10]
        motor=next(r for r in source if r['motor'])
        other=[r for r in source if not r['motor']]
        total=sum(r['length_ft'] for r in other)
        od=sum(r['length_ft']*r['adopted_od_in'] for r in other)/total
        inside=sum(r['length_ft']*r['thermal_id_in'] for r in other)/total
        end=original.string[-1];length=motor['length_ft']*FT
        remainder=wg.StringSegment(end.length-length,whole.steel('trial non-motor compact BHA',od,inside))
        section=wg.StringSegment(length,whole.steel('trial motor; motor loss unknown',motor['adopted_od_in'],motor['thermal_id_in']),
            tool_loss=unknown_motor(motor['source']))
        return wg.WellGeometry([*original.string[:-1],remainder,section],legacy.hole,legacy.survey)
    bottom=[]
    for row in rows:
        if row['bit']:continue
        inside=row['thermal_id_in']
        if inside is None:
            raise ValueError(f"Unknown component bore: {s['well']} BHA {s['run']} item {row['item']}")
        name=row['component']+('; motor loss unknown' if row['motor'] else '')
        pipe=whole.steel(name,row['adopted_od_in'],inside)
        if row['kind']=='HWDP':
            joint_od=7. if scenario=='EIS' else 7.25 if scenario=='GPDS55' else 6.625
            pipe=replace(pipe,hydraulic_joint=hl.HydraulicJoint(joint_od*INCH,inside*INCH,29*INCH,
                row['length_ft']*FT/30 if s['well']=='16B' else 31.5*FT,
                source='S2b declared connection scenario; recorded HWDP bore and pitch'))
        bottom.append(wg.StringSegment(row['length_ft']*FT,pipe,
            tool_loss=unknown_motor(row['source']) if row['motor'] else None))
    regular=legacy.md_bit-sum(c.length for c in bottom)
    if regular<=0:raise ValueError('Assembly longer than circulation depth')
    od,jid=(7.,4.) if scenario=='EIS' else (7.25,3.5) if scenario=='GPDS55' else (6.625,3.25)
    pipe=replace(legacy.string[0].pipe,hydraulic_joint=hl.HydraulicJoint(od*INCH,jid*INCH,29*INCH,
        (2378/75 if s['well']=='16B' else 31.5)*FT,source='Declared NC50/EIS connection scenario'))
    return wg.WellGeometry([wg.StringSegment(regular,pipe),*reversed(bottom)],legacy.hole,legacy.survey)


def development(output,limit=None):
    source=repository_path('validation/forge16b/s2/plan.json')
    plan=json.loads(source.read_text(encoding='utf-8'))
    data_a=repository_path('validation/forge16a');data_b=repository_path('validation/forge16b')
    ta,ca,da,_=energy.clock_a(data_a);_,tb,cb,db=whole.clock(data_b)
    samples=[s for s in plan['samples'] if s['well']=='16A' or int(s['run']) in (12,13,15,16)]
    output.mkdir(parents=True,exist_ok=True)
    destination=output/'development-cases.jsonl'
    rows=[json.loads(line) for line in destination.read_text().splitlines()] if destination.exists() else []
    done={r['case_id'] for r in rows};processed=0
    for s in samples:
        for variant,mode,reference in VARIANTS:
            scenarios=('EIS','GPDS55') if s['well']=='16B' and mode=='v1.6.0' else ('NC50',) if mode=='v1.6.0' else ('legacy',)
            for scenario in scenarios:
                case_id=s['id']+'-'+variant+'-'+scenario
                if case_id in done:continue
                if limit is not None and processed>=limit:break
                row=dict(case_id=case_id,window_id=s['id'],event_id=s['id'],well=s['well'],bha=s['run'],
                    role='development',variant=variant,hydraulics_model=mode,pv_ref_T_C=reference,scenario=scenario,
                    time=s['time'],flow_gpm=s['flow_gpm'],bit_depth_ft=s['bit_ft'],
                    measured_spp_psi=s['spp_psi'],raw_differential_psi=s['raw_differential_psi'],
                    comparison_target_psi=s['spp_psi']-(s['raw_differential_psi'] or 0.) if s['spp_psi'] is not None and s['well']=='16A' else s['spp_psi'],
                    target_treatment='SPP minus raw reported differential' if s['well']=='16A' else 'unadjusted SPP',
                    is_motor_interval=False,solver_success=False,status='missing_target' if s['spp_psi'] is None else 'pending')
                if s['spp_psi'] is not None:
                    started=time.perf_counter()
                    try:
                        if s['well']=='16B':
                            legacy=whole.geometry(s,plan['components_b'],plan['k_idp']);form=b.T_FORM
                            fluid,pv,yp=energy.fluid_for(s,'s2_revised');times,circ,depth=tb,cb,db
                        else:
                            legacy=a.geometry(s['run'],s['bit_ft'],plan['components_a']);form=a.formation('216',legacy.survey)[0]
                            fluid,pv,yp=energy.fluid_for(s,'blind_original');times,circ,depth=ta,ca,da
                        fluid=fluids.Mud(s['density_ppg']*energy.PPG,
                            pv_ref=pv*.001 if pv is not None else None,
                            yield_point=yp*energy.YP_PA,pv_ref_T=reference)
                        geometry=serial_development_geometry(s,plan['components_a' if s['well']=='16A' else 'components_b'],legacy,scenario) if mode=='v1.6.0' else legacy
                        q=s['flow_gpm']*GPM
                        rho=float(m1.fluid_props(np.array([s['T_in_C']]),np.array([m1.P_SURF]),fluid)[0][0]);mass=q*rho
                        exposure=m1.smooth_exposure(m1.exposure_from_history(circ,depth,float(np.interp(s['time_s'],times,circ))),geometry.md_bit)
                        breaks=m1.exposure_breaks(exposure,geometry.md_bit)
                        surface=hl.SurfaceLoss.api_case(5) if mode=='v1.6.0' else None
                        result=m1.solve_seeded(exposure,breaks,m_dot=mass,T_inj=s['T_in_C'],geotherm=form,
                            geometry=geometry,target_rock_T=float(form(geometry.survey.tvd(geometry.md_bit))),
                            Q_face=s['motor_heat_psi']*PSI*q,k_rock=b.K_ROCK,rhocp_rock=b.RHOCP_ROCK,
                            friction_heat=True,tfa=s['tfa_m2'],film_mult=1.,fluid=fluid,verbose=False,
                            hydraulics_model=mode,surface=surface)
                        hydraulic=m1.hydraulics(mass,geometry,result=result,fluid=fluid,tfa=s['tfa_m2'],hydraulics_model=mode,surface=surface)
                        row.update(solver_success=bool(result['success']),solver_status=int(result['sol'].status),
                            solver_message=str(result['sol'].message),nodes=len(result['sol'].x),
                            energy_check_passed=result.get('energy_check',{}).get('passed'),
                            predicted_low_psi=hydraulic['spp']/PSI,predicted_high_psi=hydraulic['spp']/PSI,
                            bit_C=float(result['Td'][-1]),return_C=float(result['Tu'][0]),
                            mass_rate_kg_s=mass,density_ppg=s['density_ppg'],PV_cP=pv,YP_lbf_100ft2=yp,
                            inlet_C=s['T_in_C'],bit_TVD_ft=float(geometry.survey.tvd(geometry.md_bit)/FT),
                            flags=json.dumps(hydraulic.get('flags',[])),unknown_proprietary_tool_loss=True)
                        for field in ('dp_string','dp_annulus','dp_bit','dp_buoyancy','dp_surface'):
                            row[field+'_psi']=hydraulic.get(field,0.)/PSI
                        residual=row['predicted_low_psi']-row['comparison_target_psi']
                        row.update(residual_low_psi=residual,residual_high_psi=residual,
                            residual_low_percent=100*residual/row['comparison_target_psi'] if row['comparison_target_psi'] else None,
                            residual_high_percent=100*residual/row['comparison_target_psi'] if row['comparison_target_psi'] else None)
                        row['status']='ok' if result['success'] else 'solver_failure'
                    except Exception as error:
                        row.update(status='solver_failure',exception=f'{type(error).__name__}: {error}')
                    row['duration_s']=time.perf_counter()-started
                rows.append(row);done.add(case_id);processed+=1
                with destination.open('a',encoding='utf-8') as stream:stream.write(json.dumps(row,allow_nan=False)+'\n')
                print(case_id,row['status'],flush=True)
            if limit is not None and processed>=limit:break
        if limit is not None and processed>=limit:break
    write_csv(output/'development-windows.csv',rows)
    events,bhas=summaries(rows)
    write_csv(output/'development-events.csv',events);write_csv(output/'development-bha.csv',bhas)
    return rows


def plots(output):
    """Plot each saved development window without a residual-based selection."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,
                         'axes.spines.right':False,'svg.hashsalt':'BoreTHM pressure comparisons'})
    with (output/'development-windows.csv').open(newline='',encoding='utf-8') as stream:
        rows=[r for r in csv.DictReader(stream) if r['status']=='ok']
    colours={'v1.5.0-26.7':'#67717d','v1.5.0-48.9':'#b27a2b','v1.6.0-48.9':'#227c85'}
    markers={'legacy':'o','EIS':'s','GPDS55':'^','NC50':'s'}
    for kind,xfield,yfield,xlabel,ylabel in (
        ('measured-modelled','comparison_target_psi','predicted_low_psi','Comparison pressure, psi','Modelled pressure, psi'),
        ('residual-flow','flow_gpm','residual_low_psi','Flow, US gal/min','Model minus comparison pressure, psi'),
        ('residual-depth','bit_depth_ft','residual_low_psi','Bit depth, ft measured depth','Model minus comparison pressure, psi'),
        ('residual-bha','bha','residual_low_psi','Bottom-hole assembly','Model minus comparison pressure, psi')):
        fig,axes=plt.subplots(1,2,figsize=(12,5.2))
        for ax,well in zip(axes,('16B','16A')):
            selected=[r for r in rows if r['well']==well]
            bhas=sorted({r['bha'] for r in selected})
            keys=sorted({(r['variant'],r['scenario']) for r in selected})
            for variant,scenario in keys:
                items=[r for r in selected if (r['variant'],r['scenario'])==(variant,scenario)]
                x=[bhas.index(r['bha']) if xfield=='bha' else float(r[xfield]) for r in items]
                y=[float(r[yfield]) for r in items]
                ax.scatter(x,y,s=18,alpha=.55,color=colours[variant],marker=markers[scenario],
                           label=variant+(' '+scenario if scenario!='legacy' else ''))
            if kind=='measured-modelled' and selected:
                bounds=[float(r[field]) for r in selected for field in (xfield,yfield)]
                lo,hi=min(bounds),max(bounds)
                ax.plot([lo,hi],[lo,hi],color='#999999',linewidth=.8,linestyle='--')
            else:ax.axhline(0.,color='#999999',linewidth=.8)
            if xfield=='bha':ax.set_xticks(range(len(bhas)),bhas)
            ax.set(xlabel=xlabel,ylabel=ylabel,title='FORGE '+well+' development data')
            ax.grid(alpha=.15);ax.set_axisbelow(True);ax.legend(fontsize=7,loc='best')
        fig.subplots_adjust(bottom=.22,wspace=.27)
        fig.text(.06,.08,'Source: development-windows.csv; x='+xfield+'; y='+yfield+
                 '; colour=variant; marker=scenario.',fontsize=8)
        fig.text(.06,.035,'16A comparison pressure subtracts the raw reported differential. '
                 '16B uses the unadjusted standpipe pressure. Only status=ok rows are drawable.',fontsize=8)
        for suffix in ('png','svg'):
            metadata={'Date':None} if suffix=='svg' else None
            fig.savefig(output/('development-'+kind+'.'+suffix),dpi=170,metadata=metadata)
        plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--limit',type=int)
    parser.add_argument('--plot-existing',action='store_true',help='Plot saved comparison CSVs without new solves')
    args=parser.parse_args()
    if args.plot_existing:plots(args.output)
    else:development(args.output,args.limit)


if __name__=='__main__':main()
