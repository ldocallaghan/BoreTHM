"""Plot the declared daily flow/stroke reductions without a fitted curve."""
import csv
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as dates
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent


def main():
    fig,axes=plt.subplots(3,1,figsize=(11,9),layout='constrained')
    for ax,well in zip(axes,('58-32','16A','16B')):
        with (HERE/'results'/(well+'-ratios-by-day.csv')).open() as f:rows=list(csv.DictReader(f))
        for combo in sorted({r['combination'] for r in rows}):
            group=[r for r in rows if r['combination']==combo]
            ax.scatter([datetime.strptime(r['day'],'%Y-%m-%d') for r in group],
                       [float(r['median_gal_stroke']) for r in group],s=17,label=combo)
        ax.set_title(well+(' drilling export: total strokes only' if well=='16A' else ': recorded pump combinations'))
        ax.set_ylabel('US gal per stroke')
        ax.xaxis.set_major_formatter(dates.DateFormatter('%d %b'))
        ax.legend(title='Active pumps',fontsize=8,ncol=4,loc='best')
        ax.grid(alpha=.2)
    axes[-1].axvspan(datetime(2023,5,4),datetime(2023,5,6),alpha=.12,color='black')
    axes[-1].text(.98,.30,'Liner-change report dates: 4-5 May; exact time unresolved',
                  ha='right',transform=axes[-1].transAxes,fontsize=8)
    axes[-1].set_xlabel('Source calendar date')
    fig.suptitle('Calculated daily median flow / summed stroke rate')
    fig.savefig(HERE/'results/daily-ratios.png',dpi=140,metadata={'Software':'Matplotlib'})
    plt.close(fig)


if __name__=='__main__':main()
