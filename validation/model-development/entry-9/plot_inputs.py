"""Plot observation coverage without reading pressure or temperature values."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    coverage=read(HERE/'inputs/coverage.csv')
    fig,axes=plt.subplots(1,2,figsize=(13,8),sharex=True)
    for ax,well in zip(axes,['16A','16B']):
        counts=[r for r in coverage if r['well']==well]
        positions={r['assembly']:i for i,r in enumerate(counts)}
        data=read(HERE/f'inputs/{well.lower()}-steady-windows.csv')
        for status,colour,marker,label in [
                ('known','#2473a6','o','Source-based assembly'),
                ('inferred','#b76119','^','Report-sequence inference'),
                ('unassigned','#9b9b9b','o','Unassigned')]:
            selected=[r for r in data if ('unassigned' if not r['assembly'] else
                      'inferred' if r['assignment']=='report sequence inferred' else 'known')==status]
            ax.scatter([float(r['bit_depth_ft']) for r in selected],
                       [positions[r['assembly']] for r in selected],s=13,alpha=.55,
                       color=colour,marker=marker,label=label,rasterized=True)
        labels=[(r['assembly'] or 'Unassigned')+f"  (n={r['windows']})" for r in counts]
        ax.set_yticks(range(len(counts)),labels)
        ax.invert_yaxis()
        ax.set_title(well)
        ax.set_xlabel('Recorded bit depth, ft MD')
        ax.set_xlim(-150,11500)
        ax.grid(axis='x',alpha=.2)
        ax.set_axisbelow(True)
    axes[0].set_ylabel('Recorded assembly label and two-minute window count')
    axes[1].legend(loc='upper center',bbox_to_anchor=(.5,-.1),frameon=False)
    fig.suptitle('Off-bottom observation coverage\nDots represent accepted input windows; no pressure comparison is shown')
    fig.tight_layout(rect=(0,.04,1,.94))
    fig.savefig(HERE/'input-coverage.png',dpi=160)
    plt.close(fig)


if __name__=='__main__':
    main()
