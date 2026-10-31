"""Plots of the declared score and secondary slopes, from saved results only."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from score import typed, frozen, VARIANTS

HERE = Path(__file__).resolve().parent
COLOURS = dict(zip(VARIANTS, ('#555555','#0072B2','#E69F00','#D55E00','#009E73','#CC79A7')))
LABELS = dict(baseline='Entry 8',smooth='Smooth Colebrook',steel='Steel roughness example',
              gradual='Zero connection-local loss',gpds='GPDS55 scenario',fh='Conventional FH scenario')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=HERE/'results')
    args = parser.parse_args()
    root = args.results
    output = root/'figures'
    output.mkdir(parents=True, exist_ok=True)

    def save(fig, name):
        fig.savefig(output/name, dpi=160)
        plt.close(fig)

    def legend(fig, ax):
        handles, names = ax.get_legend_handles_labels()
        fig.legend(handles, names, loc='outside lower center', ncol=3, fontsize=8)

    summary = typed(root/'summary.csv')
    fig, axes = plt.subplots(2,3,figsize=(13,8),constrained_layout=True)
    panels = [('G1 assembly-bias RMS [psi]',('G1_16A_RMS_psi','G1_16B_RMS_psi'),('16A','16B')),
              ('G2 power bias [kW]',('G2_16A_bias_kW','G2_16B_bias_kW'),('16A','16B')),
              ('G3 assembly-bias RMS [°C]',('G3_16A_RMS_C',),('16A',)),
              ('G4 event peak-error RMS [°C]',('G4_peak_error_RMS_C',),('16A',)),
              ('G5 pooled return bias [°C]',('G5_16A_return_bias_C',),('16A',)),
              ('G6 downhole bias [°C]',('G6_regular_bias_C','G6_trial_bias_C'),('Regular','Trial'))]
    for ax,(title,fields,ticks) in zip(axes.flat,panels):
        for i,row in enumerate(summary):
            v=row['candidate']
            ax.scatter(np.arange(len(fields))+(i-2.5)*.1,[row[f] for f in fields],
                       color=COLOURS[v],label=LABELS[v],s=25)
        ax.axhline(0,color='.6',linewidth=.7)
        ax.set_xticks(np.arange(len(fields)),ticks)
        ax.set_title(title,fontsize=10)
        ax.grid(axis='y',alpha=.2)
    fig.suptitle('Entry 10: all six development gaps\nData: summary.csv; trial geometry retains its historical insulation fit')
    legend(fig,axes[0,0]);save(fig,'six-gap-summary.png')

    comparisons = typed(root/'comparison.csv')
    for filename,definition,title in [
        ('pressure-assemblies.png',[('G1','16A'),('G1','16B')],'Standpipe bias by assembly [psi]'),
        ('temperature-assemblies.png',[('G3','16A'),('G6','16B')],'Downhole proxy bias by assembly [°C]')]:
        fig,axes=plt.subplots(1,2,figsize=(13,5),constrained_layout=True)
        for ax,(gap,well) in zip(axes,definition):
            subset=[r for r in comparisons if r['gap']==gap and r['well']==well and r['group'] not in ('trial','independent regular pipe')]
            groups=sorted({r['group'] for r in subset},key=lambda a:(int(a.split('r')[0]),a))
            for i,v in enumerate(VARIANTS):
                values={r['group']:r['after_bias'] for r in subset if r['candidate']==v}
                ax.scatter(np.arange(len(groups))+(i-2.5)*.1,[values[g] for g in groups],
                           color=COLOURS[v],label=LABELS[v],s=25)
            ax.axhline(0,color='.5',linewidth=.7)
            ax.set_xticks(np.arange(len(groups)),groups,rotation=30)
            ax.set_xlabel('Assembly');ax.set_title(well);ax.grid(axis='y',alpha=.2)
        fig.suptitle(title+'\nData: comparison.csv; bias = modelled minus measured')
        legend(fig,axes[0]);save(fig,filename)

    slopes=typed(root/'secondary/slopes.csv')
    keys=[('17',500.),('19',600.),('20',600.),('27',400.),('27',600.),('38',600.)]
    fig,axes=plt.subplots(1,2,figsize=(13,5),constrained_layout=True)
    for ax,field,label in zip(axes,('modelled_slope','slope_ratio'),('Slope [psi per 1,000 ft]','Measured / modelled slope')):
        for i,v in enumerate(VARIANTS):
            values={(str(int(r['assembly'])),r['flow_centre_gpm']):r for r in slopes if r['candidate']==v}
            ax.scatter(np.arange(6)+(i-2.5)*.1,[values[k][field] for k in keys],color=COLOURS[v],label=LABELS[v],s=28)
        if field=='modelled_slope':
            ax.scatter(np.arange(6),[values[k]['measured_slope'] for k in keys],color='black',marker='_',s=170,label='Measured slope')
        else:
            ax.axhline(1,color='black',linewidth=.7)
        ax.set_xticks(np.arange(6),['17 / 500','19 insulated / 600','20 / 600','27 / 400','27 / 600','38 / 600'],rotation=30)
        ax.set_xlabel('EOW assembly / flow [gpm]');ax.set_ylabel(label);ax.grid(axis='y',alpha=.2)
    fig.suptitle('Secondary trip slopes\nData: secondary/slopes.csv; EOW 19 adds insulated pipe; ratios do not select a variant')
    legend(fig,axes[0]);save(fig,'secondary-trip-slopes.png')

    before=typed(root/'baseline/circulation.csv');after=typed(root/'smooth/circulation.csv')
    event_before=typed(root/'baseline/run-in.csv');event_after=typed(root/'smooth/run-in.csv')
    def pairs(rows,gap):
        answer=[]
        for r in rows:
            if not r['success']:continue
            if gap=='G1A' and r['well']=='16A' and r['raw_spp_psi'] is not None and r['raw_differential_psi'] is not None:
                answer.append((r['raw_spp_psi']-r['raw_differential_psi'],r['spp_psi']))
            if gap=='G1B' and r['well']=='16B' and r['bha'] in frozen.MOTORLESS and r['raw_spp_psi'] is not None:
                answer.append((r['raw_spp_psi'],r['spp_psi']))
            if gap in ('G2A','G2B') and r['well']==('16A' if gap=='G2A' else '16B'):
                if r['measured_hydraulic_W'] is not None and r['model_hydraulic_W'] is not None:
                    answer.append((r['measured_hydraulic_W']/1000.,r['model_hydraulic_W']/1000.))
            if gap=='G3' and r['well']=='16A' and r['measured_bit_C'] is not None:
                answer.append((r['measured_bit_C'],r['bit_C']))
            if gap=='G5' and r['well']=='16A' and r['measured_return_C'] is not None:
                answer.append((r['measured_return_C'],r['return_C']))
            if gap=='G6' and r['well']=='16B':
                proxy='bore_84ft_C' if r['bha'] in frozen.TRIAL|{'27','38'} else 'bore_22ft_C'
                answer.append((r['measured_bit_C'],r[proxy]))
        return np.asarray(answer)
    fig,axes=plt.subplots(2,4,figsize=(16,8),constrained_layout=True)
    for ax,gap,title in zip(axes.flat,('G1A','G1B','G2A','G2B','G3','G5','G6','G4'),
        ('16A standpipe minus raw differential [psi]','16B motorless standpipe [psi]',
         '16A hydraulic power [kW]','16B hydraulic power [kW]',
         '16A bit proxy [°C]','16A return [°C]','16B downhole proxy [°C]','16A run-in peak [°C]')):
        arrays=[]
        for v,rows,ev in [('baseline',before,event_before),('smooth',after,event_after)]:
            a=np.asarray([(r['measured_peak_C'],r['model_peak_C']) for r in ev if r['success']]) if gap=='G4' else pairs(rows,gap)
            arrays.append(a)
            ax.scatter(a[:,0],a[:,1],s=10,alpha=.6,color=COLOURS[v],label=LABELS[v])
        low=min(a.min() for a in arrays);high=max(a.max() for a in arrays)
        ax.plot([low,high],[low,high],color='.4',linewidth=.7)
        ax.set_title(title,fontsize=9);ax.set_xlabel('Measured');ax.set_ylabel('Modelled')
        ax.grid(alpha=.15)
    fig.suptitle('Primary comparison with frozen development observations\nData: baseline and smooth circulation.csv / run-in.csv; unresolved sensor medium remains a proxy')
    legend(fig,axes[0,0]);save(fig,'primary-observations.png')

    plan=frozen.read_json(frozen.PLAN)
    depth={r['id']:r['bit_ft'] for r in plan['samples']}
    flow={r['id']:r['flow_gpm'] for r in plan['samples']}
    fig,axes=plt.subplots(2,3,figsize=(13,7),constrained_layout=True)
    for row_axes,well in zip(axes,('16A','16B')):
        selected=[r for r in after if r['success'] and r['well']==well and r['raw_spp_psi'] is not None
                  and (r['raw_differential_psi'] is not None if well=='16A' else r['bha'] in frozen.MOTORLESS)]
        groups=sorted({r['bha'] for r in selected},key=lambda a:(int(a.split('r')[0]),a))
        residual=[r['spp_psi']-r['raw_spp_psi']+(r['raw_differential_psi'] if well=='16A' else 0.) for r in selected]
        xs=([flow[r['sample_id']] for r in selected],[depth[r['sample_id']]/1000 for r in selected],
            [groups.index(r['bha']) for r in selected])
        for ax,x,label in zip(row_axes,xs,('Flow [gpm]','Bit MD [1,000 ft]','Assembly')):
            ax.scatter(x,residual,s=10,alpha=.6,color=COLOURS['smooth']);ax.axhline(0,color='.5',linewidth=.7)
            ax.set_xlabel(label);ax.set_ylabel(well+' residual [psi]');ax.grid(alpha=.15)
            if label=='Assembly':ax.set_xticks(np.arange(len(groups)),groups,rotation=30)
    fig.suptitle('Primary standpipe residuals\nData: smooth/circulation.csv and frozen operating inputs; residual = modelled minus pressure target')
    save(fig,'primary-pressure-residuals.png')
    frozen.write_json(output/'manifest.json',dict(matplotlib=matplotlib.__version__,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        figures_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob('*.png')}))


if __name__=='__main__':
    main()
