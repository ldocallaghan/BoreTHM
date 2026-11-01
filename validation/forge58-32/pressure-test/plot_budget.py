"""Plot the saved model-only event pressure budgets without target data."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


PARTS = [('surface_psi', 'Surface', '#8c6bb1'),
         ('pipe_bore_psi', 'Drill-pipe bore', '#41ab5d'),
         ('bha_bore_psi', 'BHA bores', '#238b8d'),
         ('bit_nozzles_psi', 'Bit nozzles', '#e6ab02'),
         ('annulus_psi', 'Annulus', '#df65b0'),
         ('buoyancy_psi', 'Buoyancy', '#737373')]
VARIANTS = [('original', 'Original'), ('working_entry10', 'Working'), ('secondary_entry8', 'Secondary')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with (args.data/'event-budget.csv').open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    events = list(dict.fromkeys(r['event_id'] for r in rows))
    fig, axes = plt.subplots(2, 4, figsize=(15, 7.5), sharey=True)
    for ax, event in zip(axes.flat, events):
        for x, (variant, _) in enumerate(VARIANTS):
            row = next((r for r in rows if r['event_id']==event and r['variant']==variant), None)
            if row is None or not row.get('spp_psi'):
                ax.text(x, 25., 'Unavailable', rotation=90, ha='center', va='bottom', fontsize=8)
                continue
            positive = negative = 0.
            for key, _, colour in PARTS:
                value = float(row[key])
                ax.bar(x, value, width=.7, bottom=positive if value>=0 else negative, color=colour)
                if value>=0:
                    positive += value
                else:
                    negative += value
            ax.text(x, positive+8., f"{float(row['spp_psi']):.0f}", ha='center', fontsize=8)
        ax.set_title(event.replace('58-32-', ''), fontsize=10)
        ax.set_xticks(range(3), [v[1] for v in VARIANTS], rotation=35, ha='right')
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
        ax.set_xlim(-.6,2.6)
    axes.flat[-1].axis('off')
    axes.flat[-1].legend(handles=[Patch(color=c,label=label) for _,label,c in PARTS],
                         loc='center', frameon=False)
    fig.supylabel('Modelled pressure contribution (psi)')
    fig.suptitle('FORGE 58-32: model-only event mean budgets, primary geometry', fontsize=13)
    fig.tight_layout(rect=(.02,0,1,.95))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
