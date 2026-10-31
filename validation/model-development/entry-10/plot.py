"""Plot the model-only predictions without loading measured observations."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=HERE/'predictions/model-only.csv')
    parser.add_argument('--output', type=Path, default=HERE/'predictions')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with args.input.open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    variants = ('smooth', 'steel', 'gpds', 'fh', 'gradual')
    labels = ('Smooth Colebrook', 'Steel roughness example', 'GPDS55 scenario',
              'Conventional FH scenario', 'Zero connection-local loss')
    colours = ('#0072B2', '#E69F00', '#009E73', '#CC79A7', '#D55E00')
    metrics = (('spp_psi_change', 'Standpipe pressure change [psi]'),
               ('model_hydraulic_kW_change', 'Hydraulic power change [kW]'),
               ('sensor_bore_C_change', 'Frozen-position bore proxy change [°C]'),
               ('return_C_change', 'Return temperature change [°C]'))
    for well in ('16A', '16B'):
        assemblies = sorted({r['assembly'] for r in rows if r['well'] == well},
                            key=lambda a: (int(a.split('r')[0]), a))
        x = np.arange(len(assemblies))
        fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
        for ax, (column, label) in zip(axes.flat, metrics):
            for i, (variant, name, colour) in enumerate(zip(variants, labels, colours)):
                lookup = {r['assembly']: r for r in rows
                          if r['well'] == well and r['variant'] == variant}
                ax.scatter(x+(i-2)*.12, [float(lookup[a][column]) for a in assemblies],
                           s=25, color=colour, label=name)
            ax.axhline(0, color='.5', linewidth=.7)
            ax.set_xticks(x, assemblies)
            ax.set_xlabel('Assembly')
            ax.set_ylabel(label)
            ax.grid(axis='y', alpha=.2)
        fig.suptitle(f'FORGE {well}: model-only changes from entry 8\n'
                     'One operating window per assembly; no measured target comparison')
        handles, names = axes[0, 0].get_legend_handles_labels()
        fig.legend(handles, names, loc='outside lower center', ncol=3, fontsize=9)
        fig.savefig(args.output/f'{well.lower()}-model-only.png', dpi=160)
        plt.close(fig)


if __name__ == '__main__':
    main()
