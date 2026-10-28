"""Plot saved mixed-geometry results without running another calculation."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    args=parser.parse_args()
    with (args.archive/'assemblies.csv').open(newline='') as stream:rows=list(csv.DictReader(stream))
    fig,axes=plt.subplots(2,2,figsize=(13,8),sharex='col')
    for col,well in enumerate(('16A','16B')):
        a=[r for r in rows if r['well']==well and r['case']=='A']
        a.sort(key=lambda r:(int(r['bha'][:2]),r['bha']))
        b={r['bha']:r for r in rows if r['well']==well and r['case']=='B'}
        x=np.arange(len(a))
        for row,(field,reference,label) in enumerate((('bit_change_C','archived_bit_rise_C','Bit change, °C'),('return_change_C','archived_return_rise_C','Return change, °C'))):
            ax=axes[row,col]
            ax.bar(x-.2,[float(r[field]) for r in a],.4,label='A: legacy thermal geometry, new heat',color='#197e88')
            ax.bar(x+.2,[float(b[r['bha']][field]) for r in a],.4,label='B: new thermal geometry, legacy heat',color='#c68837')
            ax.plot(x,[float(r[reference]) for r in a],'ko',ms=4,label='Complete entry 1')
            ax.plot(x,[float(r['bulk_heating_scale_C']) for r in a],'^',color='#a3485b',ms=5,label='Added power / mass flow / heat capacity')
            ax.axhline(0,color='#888',lw=.7);ax.set_ylabel(label);ax.grid(axis='y',alpha=.18)
            ax.set_xticks(x,[r['bha'] for r in a],rotation=45);ax.set_title('FORGE '+well)
            if row==1:ax.set_xlabel('Bottom-hole assembly')
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=2,fontsize=8,bbox_to_anchor=(.5,.025))
    fig.text(.06,.005,'Source: assemblies.csv, bit_change_C, return_change_C, archived_*_rise_C and bulk_heating_scale_C. Equal sample means.',fontsize=8)
    fig.tight_layout(rect=(0,.12,1,1));fig.savefig(args.archive/'thermal-heat-split.png',dpi=180);plt.close(fig)


if __name__=='__main__':main()
