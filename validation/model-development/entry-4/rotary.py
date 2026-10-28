"""Per-sample rotary heat for entry 4, from `rotary_inputs.csv`.

The friction factor comes from each sample's off-bottom rotating torque.
Where a sample has no off-bottom reference, the median factor of the other
samples in the same assembly is used, and the row says so.
"""
import csv
from pathlib import Path
import statistics as st

import numpy as np

from borethm import rotary_heat as rh

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FT = 0.3048
PPG = 119.82642731689663


def _survey(path):
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    return tuple(np.array([float(r[k]) for r in rows]) for k in ('md_ft', 'inc_deg', 'azi_deg'))


SURVEYS = {'16A': _survey(ROOT/'validation/forge16a/survey_16a.csv'),
           '16B': _survey(ROOT/'src/borethm/data/forge16b/survey_16b.csv')}


def inputs():
    with open(HERE/'rotary_inputs.csv', encoding='utf-8') as f:
        return {r['sample_id']: r for r in csv.DictReader(f)}


def value(row, key):
    return None if row.get(key) in (None, '') else float(row[key])


class Rotary:
    def __init__(self, plan, geometry):
        self.rows = inputs()
        self.geometry = geometry
        self.plan = plan
        self.factors = {}

    def _partition(self, sample, factor=None):
        row = self.rows[sample['id']]
        md, inc, azi = SURVEYS[sample['well']]
        off = value(row, 'torque_off_ft_lbf')
        rpm = value(row, 'rpm_on') or 0.0
        # The mean of speed times torque is the measured power; the torque
        # used is that power divided by the mean speed.
        torque = (value(row, 'rotary_power_on_W') or 0.0)/(2*np.pi*rpm/60) if rpm > 0 else 0.0
        return rh.partition(self.geometry(sample, self.plan, 'current'), md*FT, inc, azi,
                            sample['density_ppg']*PPG, rpm, torque,
                            None if factor is not None else off*rh.FT_LBF,
                            (value(row, 'wob_on_klbf') or 0.0)*rh.KLBF, friction_factor=factor)

    def factor(self, well, bha):
        key = (well, bha)
        if key not in self.factors:
            values = [self._partition(s).friction_factor for s in self.plan['samples']
                      if s['well'] == well and s['run'] == bha and value(self.rows[s['id']], 'torque_off_ft_lbf') is not None]
            self.factors[key] = st.median(values)
        return self.factors[key]

    def heat(self, sample):
        """RotaryHeat and the basis of its friction factor."""
        row = self.rows[sample['id']]
        if value(row, 'torque_off_ft_lbf') is not None:
            return self._partition(sample), 'own off-bottom reference'
        return self._partition(sample, self.factor(sample['well'], sample['run'])), 'assembly median friction factor'
