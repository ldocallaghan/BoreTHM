"""Write the derived tool-loss defaults from the published source table.

The package computes the same values from src/borethm/data/tool_losses.csv
when it runs. This file is the readable copy, and a test checks that it agrees.
"""
import csv
from pathlib import Path

from borethm import tool_losses

OUTPUT = Path(__file__).resolve().parents[1]/'src/borethm/data/tool_loss_defaults.csv'
FIELDS = ('tool_class', 'band_in', 'flow_ref_gpm', 'dp_ref_psi_in_water', 'exponent', 'low_psi', 'high_psi', 'status', 'sources')


def rows():
    for (tool_class, band), d in sorted(tool_losses.defaults().items()):
        yield dict(tool_class=tool_class, band_in=band, flow_ref_gpm=d.flow_ref_gpm,
                   dp_ref_psi_in_water=round(d.dp_ref_psi, 3), exponent=round(d.exponent, 4),
                   low_psi='' if d.low_psi is None else round(d.low_psi, 3),
                   high_psi='' if d.high_psi is None else round(d.high_psi, 3),
                   status=d.status, sources=';'.join(d.sources))


def main():
    with OUTPUT.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows())


if __name__ == '__main__':
    main()
