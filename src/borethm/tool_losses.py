"""Generic pressure-loss allowances for downhole tools, from published sheets.

data/tool_losses.csv holds one row per published figure. A default for a tool
class and size band follows one rule, stated in the development log:

1. Each used row is converted to water at 8.34 lbm/galUS and the band's
   reference flow, using its own exponent where it gives two points or a
   formula, and 2 otherwise. Density scales linearly.
2. Variants of one tool family in one band reduce to one value, their median,
   so that a maker with a long table counts once.
3. The default is the median across sources. The exponent is the median of
   the exponents of sources with two points or a formula, or 2 with none.
4. Motor figures count only with a stated flow. A class and band with no
   usable figure has a default of zero, with a warning wherever it is used.

These are allowances for a tool of the class. A maker's figure for the actual
tool should be entered when it is available.
"""
import csv
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
import math
import statistics

TOOL_CLASSES = ('mwd_pulser', 'rotary_steerable', 'mud_motor', 'filter_sub', 'float_sub')
# Collar size band [in] and its reference flow [US gal/min].
BANDS = {4.75: 250., 6.75: 600., 8.0: 800., 9.5: 1000.}
WATER_PPG = 8.34


@dataclass(frozen=True)
class ToolDefault:
    """Default for one class and size band: dp_ref_psi at flow_ref_gpm in water."""
    tool_class: str
    band_in: float
    dp_ref_psi: float
    flow_ref_gpm: float
    exponent: float
    sources: tuple
    low_psi: float | None
    high_psi: float | None

    @property
    def status(self):
        return 'no source' if not self.sources else 'single source' if len(self.sources) == 1 else 'multiple sources'


def band_of(collar_in):
    """The size band nearest to a collar size [in]; equal distances take the smaller."""
    if isinstance(collar_in, bool) or not math.isfinite(collar_in) or collar_in <= 0:
        raise ValueError('collar size must be positive and finite')
    return min(BANDS, key=lambda band: (abs(band-collar_in), band))


def source_rows():
    """The published figures, as dictionaries of the table's text fields."""
    text = files('borethm').joinpath('data/tool_losses.csv').read_text(encoding='utf-8')
    return list(csv.DictReader(text.splitlines()))


def _converted(row, flow_ref):
    """Water pressure drop [psi] at flow_ref, and the row's exponent or None."""
    if row['form'] == 'formula':
        return WATER_PPG*flow_ref**2/float(row['formula_c']), 2.
    density = WATER_PPG/float(row['density_ppg'])
    q1, p1 = float(row['flow_1_gpm']), float(row['dp_1_psi'])
    if row['form'] == 'point':
        return p1*density*(flow_ref/q1)**2, None
    if row['form'] != 'points':
        raise ValueError(f"tool table: form {row['form']!r} cannot be converted")
    q2, p2 = float(row['flow_2_gpm']), float(row['dp_2_psi'])
    exponent = math.log(p2/p1)/math.log(q2/q1)
    return p1*density*(flow_ref/q1)**exponent, exponent


@lru_cache(maxsize=None)
def defaults():
    """Mapping of (tool_class, band) to ToolDefault for every class and band."""
    rows = [row for row in source_rows() if row['used'] == 'yes']
    table = {}
    for tool_class in TOOL_CLASSES:
        for band, flow in BANDS.items():
            grouped = {}
            for row in rows:
                if row['tool_class'] == tool_class and band_of(float(row['collar_in'])) == band:
                    grouped.setdefault(row['source'], []).append(_converted(row, flow))
            values = {k: statistics.median(v[0] for v in items) for k, items in grouped.items()}
            exponents = [statistics.median(n for _, n in items if n is not None)
                         for items in grouped.values() if any(n is not None for _, n in items)]
            table[tool_class, band] = ToolDefault(
                tool_class, band, statistics.median(values.values()) if values else 0., flow,
                statistics.median(exponents) if exponents else 2., tuple(sorted(values)),
                min(values.values()) if values else None, max(values.values()) if values else None)
    return table


def default_for(tool_class, collar_in):
    """The ToolDefault for a tool class at the band nearest to collar_in [in]."""
    if tool_class not in TOOL_CLASSES:
        raise ValueError(f'tool class must be one of {TOOL_CLASSES}')
    return defaults()[tool_class, band_of(collar_in)]
