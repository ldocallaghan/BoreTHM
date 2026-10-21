"""Generate docs/api.md from the installed package's public docstrings."""
import inspect
from pathlib import Path

import borethm


def render():
    rows = [
        '# Python API', '',
        'Names listed here and in `borethm.__all__` follow semantic versioning from '
        '1.4.0 and change incompatibly only with a major release. '
        'Other modules and objects are internal and may change in any release.', '',
        'Import these names from `borethm`. Temperatures are in degrees C and '
        'pressures in Pa unless stated otherwise; SG denotes density relative '
        'to 1,000 kg/m3.', '',
        'Construct a pipe with `uniform_wall` or `PipeType` and `Layer`. '
        '`WellGeometry.single` builds a single-segment well; `StringSegment`, '
        '`HoleInterval`, `open_hole`, `cased` and `Survey` describe other geometries. '
        '`WallState` supplies a wall history and `ToolLump.of_pipe` constructs '
        'the heat capacities needed by `tool_trip_in`.', '',
        '```python',
        'from borethm import uniform_wall, WellGeometry, thermal_hoop_stress',
        'pipe = uniform_wall(k=45.0, r_in=0.05, r_out=0.06)',
        'well = WellGeometry.single(3000.0, pipe, r_hole=0.11)',
        'stress_Pa = thermal_hoop_stress(300.0, 150.0)',
        '```', '',
    ]
    for name in borethm.__all__:
        rows += ['## ' + name, '']
        if name == '__version__':
            rows += ['The installed package version, read from its distribution metadata.', '']
            continue
        obj = getattr(borethm, name)
        signature = str(inspect.signature(obj)).replace('borethm.site_evaluation.', '')
        signature = signature.replace('<built-in function callable>', 'Callable')
        rows += ['```python', name + signature, '```', '', inspect.getdoc(obj), '']
    return '\n'.join(rows)


if __name__ == '__main__':
    destination = Path(__file__).resolve().parents[1] / 'docs/api.md'
    destination.write_text(render(), encoding='utf-8', newline='\n')
