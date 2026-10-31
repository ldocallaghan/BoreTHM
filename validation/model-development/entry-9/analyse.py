"""Reduce and plot the declared pressure comparisons without changing inputs."""
from collections import Counter, defaultdict
import json
import math
import hashlib
import importlib.metadata
from pathlib import Path
import platform

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from diagnose import DECLARATION, HERE, ROOT, finite, read, write

OUT = HERE/'results'
KEYS = ('well','role','assembly','variant')


def numeric(rows):
    result = []
    for source in rows:
        row = dict(source)
        for key in ['bit_depth_ft','flow_gpm','measured_spp_psi','modelled_spp_psi',
                    'residual_psi','measured_modelled_ratio']:
            row[key] = finite(row.get(key))
        result.append(row)
    return result


def clustered(rows, field, span):
    """Non-overlapping groups, each with a maximum total span."""
    groups = []
    for row in sorted(rows, key=lambda r:r[field]):
        if not groups or row[field]-groups[-1][0][field]>span:
            groups.append([])
        groups[-1].append(row)
    return groups


def regression(x, y):
    fit = stats.linregress(x,y)
    half = float(stats.t.ppf(.975,len(x)-2)*fit.stderr) if len(x)>2 else None
    return dict(slope=float(fit.slope), intercept=float(fit.intercept),
                stderr=float(fit.stderr), ci95_half=half,
                r_squared=float(fit.rvalue**2))


def slopes(rows):
    groups = defaultdict(list)
    for r in rows:
        centre = round(r['flow_gpm']/25)*25
        if centre>0 and abs(r['flow_gpm']/centre-1)<=.025:
            groups[tuple(r[k] for k in KEYS)+(r['excursion'],centre)].append(r)
    summaries, stages, omitted = [], [], []
    for key, items in sorted(groups.items()):
        base = dict(zip((*KEYS,'excursion','flow_centre_gpm'),key))
        groups_at_depth = clustered(items,'bit_depth_ft',100.)
        means = []
        for i, group in enumerate(groups_at_depth):
            row = {**base, 'stage':i+1, 'windows':len(group),
                   'window_ids':';'.join(r['window_id'] for r in group)}
            for field in ['bit_depth_ft','flow_gpm','measured_spp_psi','modelled_spp_psi']:
                row[field] = float(np.mean([r[field] for r in group]))
            means.append(row)
            stages.append(row)
        span = max(r['bit_depth_ft'] for r in means)-min(r['bit_depth_ft'] for r in means)
        if len(means)<3 or span<1000:
            omitted.append({**base,'stages':len(means),'depth_span_ft':span,
                            'reason':'fewer than three stages or span below 1000 ft'})
            continue
        row = {**base, 'stages':len(means), 'windows':len(items), 'depth_span_ft':span,
               'depth_min_ft':min(r['bit_depth_ft'] for r in means),
               'depth_max_ft':max(r['bit_depth_ft'] for r in means),
               'flow_min_gpm':min(r['flow_gpm'] for r in items),
               'flow_max_gpm':max(r['flow_gpm'] for r in items)}
        x = np.array([r['bit_depth_ft'] for r in means])/1000
        for kind in ['measured','modelled']:
            fit = regression(x,[r[kind+'_spp_psi'] for r in means])
            for field,value in fit.items():row[kind+'_'+field] = value
        row['slope_ratio'] = row['measured_slope']/row['modelled_slope'] if row['modelled_slope'] else None
        summaries.append(row)
    return summaries, stages, omitted


def flow_steps(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[tuple(r[k] for k in KEYS)+(r['excursion'],)].append(r)
    answer = []
    for key, items in sorted(groups.items()):
        for depth_group in clustered(items,'bit_depth_ft',5.):
            levels = defaultdict(list)
            for r in depth_group:
                levels[round(r['flow_gpm']/25)*25].append(r)
            values = []
            for _, group in sorted(levels.items()):
                values.append({field:float(np.mean([r[field] for r in group])) for field in
                               ['flow_gpm','measured_spp_psi','modelled_spp_psi']})
            if len(values)<3 or min(np.diff([v['flow_gpm'] for v in values]))<25:
                continue
            row = dict(zip((*KEYS,'excursion'),key))
            row.update(levels=len(values),windows=len(depth_group),
                non_positive_pressure_windows=sum(r['measured_spp_psi']<=0 for r in depth_group),
                depth_min_ft=min(r['bit_depth_ft'] for r in depth_group),
                depth_max_ft=max(r['bit_depth_ft'] for r in depth_group),
                flow_min_gpm=values[0]['flow_gpm'],flow_max_gpm=values[-1]['flow_gpm'],
                level_flows_gpm=';'.join(str(v['flow_gpm']) for v in values),
                level_measured_spp_psi=';'.join(str(v['measured_spp_psi']) for v in values),
                level_modelled_spp_psi=';'.join(str(v['modelled_spp_psi']) for v in values),
                window_ids=';'.join(r['window_id'] for r in depth_group))
            for kind in ['measured','modelled']:
                y = np.array([v[kind+'_spp_psi'] for v in values])
                q = np.array([v['flow_gpm'] for v in values])
                for exponent in [1,2]:
                    fit = regression((q/100)**exponent,y)
                    for field,value in fit.items():row[f'{kind}_q{exponent}_{field}'] = value
            answer.append(row)
    return answer


def summaries(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[tuple(r[k] for k in KEYS)].append(r)
    answer = []
    for key,items in sorted(groups.items()):
        events = defaultdict(list)
        for r in items:events[r['excursion']].append(r)
        row = dict(zip(KEYS,key))
        row.update(windows=len(items),excursions=len(events),
            bit_min_ft=min(r['bit_depth_ft'] for r in items),bit_max_ft=max(r['bit_depth_ft'] for r in items),
            flow_min_gpm=min(r['flow_gpm'] for r in items),flow_max_gpm=max(r['flow_gpm'] for r in items))
        for field in ['measured_spp_psi','modelled_spp_psi','residual_psi','measured_modelled_ratio']:
            row[field+'_median'] = float(np.median([r[field] for r in items]))
            row[field+'_min'] = min(r[field] for r in items)
            row[field+'_max'] = max(r[field] for r in items)
            row[field+'_event_mean'] = float(np.mean([np.median([r[field] for r in event]) for event in events.values()]))
        for field in ['bit_depth_ft','flow_gpm']:
            if len(items)>2 and len({r[field] for r in items})>1:
                row['ratio_spearman_'+field] = float(stats.spearmanr([r[field] for r in items],
                    [r['measured_modelled_ratio'] for r in items]).statistic)
        answer.append(row)
    return answer


def exclusions(rows):
    counts = Counter((r['well'],r['role'],r['assembly'],r['status'],r.get('reason',''))
                     for r in rows if r['status']!='ok')
    return [dict(zip(('well','role','assembly','status','reason','windows'),(*k,v)))
            for k,v in sorted(counts.items())]


def shortcut_summary():
    groups = defaultdict(list)
    for r in read(OUT/'shortcut-check.csv'):
        groups[r['well'],r['assembly']].append(r)
    answer = []
    for (well,assembly),items in sorted(groups.items()):
        good = [r for r in items if r['success'] in ('True',True)]
        row = dict(well=well,assembly=assembly,samples=len(items),converged=len(good))
        if good:
            row['max_archive_difference_psi'] = max(abs(float(r['archive_difference_psi'])) for r in good)
            row['max_archive_bit_difference_C'] = max(abs(float(r['bit_C'])-float(r['archive_bit_C'])) for r in good)
            row['max_archive_return_difference_C'] = max(abs(float(r['return_C'])-float(r['archive_return_C'])) for r in good)
            for kind in ['inlet_return','bit_return','observed_inlet_return']:
                x = [float(r[kind+'_error_percent']) for r in good]
                row[kind+'_error_min_percent'] = min(x)
                row[kind+'_error_max_percent'] = max(x)
                row[kind+'_error_median_percent'] = float(np.median(x))
        answer.append(row)
    return answer


def unassigned_periods(rows):
    groups = defaultdict(list)
    for r in rows:
        if r['well']!='16B' or r['assembly']:
            continue
        t = r['start']
        if t<'2023-05-03':name='surface and intermediate section before 3 May'
        elif t<'2023-05-13':name='3–12 May particle and clean-out operations'
        elif '2023-05-27'<=t<'2023-06-04':name='27 May–3 June assemblies outside run definitions'
        elif '2023-06-04'<=t<'2023-06-17':name='4–16 June assemblies outside run definitions'
        elif t>='2023-06-18 10:24:40':name='after target depth'
        else:name='other unresolved transition or shallow visit'
        groups[name].append(r)
    return [dict(period=k,windows=len(v),excursions=len({r['excursion'] for r in v}),
                 start=min(r['start'] for r in v),end=max(r['end'] for r in v),
                 bit_min_ft=min(r['bit_depth_ft'] for r in v),bit_max_ft=max(r['bit_depth_ft'] for r in v))
            for k,v in sorted(groups.items())]


def flow_conversion():
    rows = []
    for well in ['16A','16B']:
        for r in read(HERE/f'inputs/{well.lower()}-pump-displacement.csv'):
            row = dict(well=well,date=r['date'],rows=r['rows'],
                       recorded_gal_per_stroke=r['median_gal_per_stroke'])
            for diameter in [5.,5.5,6.]:
                row[f'triplex_{diameter:g}in_12in_95percent_gal_per_stroke'] = 3*math.pi/4*diameter**2*12/231*.95
            rows.append(row)
    write(OUT/'flow-conversion.csv',rows)
    write(OUT/'flow-bound.csv',[dict(assumed_efficiency=.95,maximum_efficiency=1.,
        maximum_true_recorded_flow_ratio=1/.95,
        maximum_true_recorded_quadratic_pressure_ratio=1/.95**2,
        maximum_missing_fraction_of_true_quadratic_pressure=1-.95**2,
        condition='correct liner, stroke, stroke count and a nominal 95-percent flow conversion')])


def plots(rows, prefix):
    for kind in ['depth','flow','assembly']:
        fig,axes = plt.subplots(1,2,figsize=(12,7))
        for ax,well in zip(axes,['16A','16B']):
            selected = [r for r in rows if r['well']==well]
            assemblies = sorted({r['assembly'] for r in selected},key=lambda x:float(x.replace('r','.')))
            for colour_index,assembly in enumerate(assemblies):
                v = [r for r in selected if r['assembly']==assembly]
                for variant in sorted({r['variant'] for r in v}):
                    group = [r for r in v if r['variant']==variant]
                    marker = '^' if variant=='measured_high' else 'o'
                    if kind=='depth':x = [r['bit_depth_ft']/1000 for r in group]
                    elif kind=='flow':x = [r['flow_gpm'] for r in group]
                    else:x = [assemblies.index(assembly)]*len(group)
                    short = variant.removeprefix('measured_').replace('inlet_return','mean')
                    ax.scatter(x,[r['residual_psi'] for r in group],s=10,alpha=.45,marker=marker,
                               color=plt.get_cmap('tab20')(colour_index%20),label=f'{assembly} {short}')
            ax.axhline(0,color='black',lw=.7)
            ax.set_title(well)
            ax.set_ylabel('Modelled minus measured standpipe pressure, psi')
            ax.set_xlabel({'depth':'Bit depth, thousand ft MD','flow':'Flow, gpm','assembly':'Assembly'}[kind])
            if kind=='assembly':ax.set_xticks(range(len(assemblies)),assemblies,rotation=45)
            if assemblies:ax.legend(loc='upper center',bbox_to_anchor=(.5,-.18),fontsize=6,ncol=3,frameon=False)
            ax.grid(alpha=.15)
        fig.suptitle(prefix.replace('-',' ').capitalize()+' comparison')
        fig.tight_layout(rect=(0,0,1,.94))
        fig.savefig(OUT/f'{prefix}-residual-{kind}.png',dpi=150)
        plt.close(fig)
    fig,axes = plt.subplots(1,2,figsize=(12,5))
    for ax,well in zip(axes,['16A','16B']):
        group = [r for r in rows if r['well']==well]
        ax.scatter([r['measured_spp_psi'] for r in group],[r['modelled_spp_psi'] for r in group],s=10,alpha=.4)
        limit = max([r['measured_spp_psi'] for r in group]+[r['modelled_spp_psi'] for r in group]+[1])
        ax.plot([0,limit],[0,limit],color='black',lw=.7)
        ax.set(xlabel='Measured standpipe pressure, psi',ylabel='Modelled standpipe pressure, psi',title=well)
        ax.grid(alpha=.15)
    fig.tight_layout();fig.savefig(OUT/f'{prefix}-measured-modelled.png',dpi=150);plt.close(fig)
    fig,axes = plt.subplots(1,2,figsize=(12,5))
    for ax,well in zip(axes,['16A','16B']):
        group = [r for r in rows if r['well']==well]
        ax.scatter([r['bit_depth_ft']/1000 for r in group],[r['measured_spp_psi'] for r in group],s=10,alpha=.4,label='Measured')
        ax.scatter([r['bit_depth_ft']/1000 for r in group],[r['modelled_spp_psi'] for r in group],s=10,alpha=.4,label='Modelled')
        ax.set(xlabel='Bit depth, thousand ft MD',ylabel='Standpipe pressure, psi',title=well)
        ax.legend();ax.grid(alpha=.15)
    fig.tight_layout();fig.savefig(OUT/f'{prefix}-pressure-depth.png',dpi=150);plt.close(fig)
    fig,axes = plt.subplots(2,3,figsize=(13,7))
    for panel,well in zip(axes,['16A','16B']):
        group = [r for r in rows if r['well']==well]
        assemblies = sorted({r['assembly'] for r in group},key=lambda x:float(x.replace('r','.')))
        for ax,field,label in zip(panel,['bit_depth_ft','flow_gpm','assembly'],['Bit depth, ft MD','Flow, gpm','Assembly']):
            for i,assembly in enumerate(assemblies):
                v = [r for r in group if r['assembly']==assembly]
                x = [assemblies.index(assembly)]*len(v) if field=='assembly' else [r[field] for r in v]
                ax.scatter(x,[r['measured_modelled_ratio'] for r in v],s=8,alpha=.4,color=plt.get_cmap('tab20')(i%20))
            ax.axhline(1,color='black',lw=.7)
            ax.set(xlabel=label,ylabel=f'{well}: measured / modelled pressure')
            if field=='assembly':ax.set_xticks(range(len(assemblies)),assemblies,rotation=45)
            ax.grid(alpha=.15)
    fig.tight_layout();fig.savefig(OUT/f'{prefix}-ratios.png',dpi=150);plt.close(fig)


def slope_plots(summaries,stages,role):
    rows = [r for r in summaries if r['role']==role]
    if not rows:return
    fig,axes = plt.subplots((len(rows)+1)//2,2,figsize=(11,3*((len(rows)+1)//2)),squeeze=False)
    for ax,row in zip(axes.ravel(),rows):
        v = [s for s in stages if all(s[k]==row[k] for k in (*KEYS,'excursion','flow_centre_gpm'))]
        x = np.array([s['bit_depth_ft'] for s in v])/1000
        for kind,colour in [('measured','C0'),('modelled','C1')]:
            ax.scatter(x,[s[kind+'_spp_psi'] for s in v],label=kind.capitalize(),color=colour,s=18)
            ax.plot(x,row[kind+'_intercept']+row[kind+'_slope']*x,color=colour,lw=.8)
        ax.set(title=f'{row["well"]} assembly {row["assembly"]}, {row["flow_centre_gpm"]} gpm centre',
               xlabel='Bit depth, thousand ft MD',ylabel='Standpipe pressure, psi')
        ax.legend(fontsize=8);ax.grid(alpha=.15)
    for ax in axes.ravel()[len(rows):]:ax.set_visible(False)
    fig.tight_layout();fig.savefig(OUT/f'{role}-slopes.png',dpi=150);plt.close(fig)


def main():
    raw = numeric(read(OUT/'windows.csv'))
    exploratory = numeric(read(OUT/'exploratory-windows.csv'))
    valid = [r for r in raw if r['status']=='ok']
    all_valid = valid+[r for r in exploratory if r['status']=='ok']
    sl,st,om = slopes(all_valid)
    write(OUT/'slopes.csv',sl);write(OUT/'depth-stages.csv',st);write(OUT/'slope-exclusions.csv',om)
    write(OUT/'flow-steps.csv',flow_steps(all_valid))
    write(OUT/'assembly-summary.csv',summaries(all_valid))
    events = defaultdict(list)
    for r in all_valid:events[tuple(r[k] for k in KEYS)+(r['excursion'],)].append(r)
    write(OUT/'event-summary.csv',[{**summaries(v)[0],'excursion':key[-1]}
                                  for key,v in sorted(events.items())])
    write(OUT/'near-surface.csv',[r for r in all_valid if r['bit_depth_ft']<=500])
    write(OUT/'exclusions.csv',exclusions(raw+exploratory))
    write(OUT/'shortcut-summary.csv',shortcut_summary())
    write(OUT/'unassigned-periods.csv',unassigned_periods(raw))
    write(OUT/'pressure-flags.csv',[dict(well=r['well'],window_id=r['window_id'],assembly=r['assembly'],
          start=r['start'],flow_gpm=r['flow_gpm'],measured_spp_psi=r['measured_spp_psi'],
          flag='non-positive recorded pressure during selected circulation')
          for r in raw if r['measured_spp_psi'] is not None and r['measured_spp_psi']<=0])
    flow_conversion()
    for role in ['primary','secondary','exploratory']:
        plots([r for r in all_valid if r['role']==role],role)
        slope_plots(sl,st,role)
    inputs = [HERE/'inputs/manifest.json',HERE/'diagnose.py',HERE/'exploratory.py',Path(__file__),
              ROOT/'validation/forge16b/pason_selected_1min.csv',ROOT/'validation/forge16b/s2/plan.json',
              ROOT/'validation/model-development/entry-8/score.py',
              ROOT/'validation/scoreboard/scoreboard.py',
              ROOT/'validation/model-development/entry-4/rotary.py',
              ROOT/'validation/model-development/entry-4/rotary_inputs.csv',
              ROOT/'validation/model-development/entry-6/hypotheses.py',
              ROOT/'validation/model-development/entry-6/gel_inputs.csv',
              *sorted((ROOT/'validation/forge16a').glob('sanvean_BHA*_10s.csv')),
              *sorted((ROOT/'src/borethm').glob('*.py')),
              *[(ROOT/'src/borethm/studies'/name) for name in
                ['forge16_energy.py','pressure_comparison.py','validate_forge16a.py',
                 'validate_forge16b.py','validate_forge16b_wholewell.py']]]
    sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = dict(declaration_commit=DECLARATION,model_commit='a0819322610b772a259a2c48a8050495e6e43fd6',
        settings=dict(annulus_model='herschel-bulkley-erge',rheology='entry 6 no-yield',
                      pv_ref_T_C=26.7,surface_case=5,hydraulics_model='v1.6.0',
                      surface_state='recorded flow with measured inlet density on 16B; nominal density on 16A'),
        versions={'python':platform.python_version(),**{k:importlib.metadata.version(k) for k in
                  ['borethm','numpy','scipy','iapws','matplotlib']}},
        inputs_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in inputs},
        files_sha256={p.name:sha(p) for p in sorted(OUT.iterdir())
                      if p.is_file() and p.name!='manifest.json'})
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(successful_predictions=len(valid),slope_groups=len(sl),
                         flow_step_groups=len(flow_steps(all_valid))),indent=2))


if __name__ == '__main__':
    main()
