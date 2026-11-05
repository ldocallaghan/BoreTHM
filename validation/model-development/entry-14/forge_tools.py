"""The v1.8.0 tool defaults on the entry 13 tapered_primary geometry.

Tools are identified from the assembly names in the frozen geometry, by the
rules in options.json. The default of each class and size band is entered as
an explicit figure, so the rest of the frozen calculation runs unchanged. A
class with no published figure has a default of zero and adds nothing.
"""
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys

from borethm import hydraulic_losses as hl
from borethm import tool_losses, well_geometry as wg

HERE = Path(__file__).resolve().parent
ENTRY13 = HERE.parent/'entry-13'
OPTIONS = json.loads((HERE/'options.json').read_text(encoding='utf-8'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if str(ENTRY13) not in sys.path:
    sys.path.insert(0, str(ENTRY13))
import predict as entry13  # noqa: E402


def figure(tool_class, collar_in):
    """The default as an explicit figure, or None for a class with no source."""
    default = tool_losses.default_for(tool_class, collar_in)
    if not default.sources:
        return None
    return hl.DownholeTool(tool_class, collar_in, default.dp_ref_psi*hl.PSI, default.flow_ref_gpm*hl.GPM,
                           tool_losses.WATER_PPG*hl.PPG, default.exponent,
                           source=f'generic {tool_class} allowance, {default.band_in} in band')


def classes(name):
    """The tool classes a segment's assembly name identifies."""
    found = []
    if name == OPTIONS['trial_compact_bha']['name']:
        return list(OPTIONS['trial_compact_bha']['tools'])
    for rule in OPTIONS['tool_rules']:
        if any(text in name for text in rule['names_containing']) and not any(text in name for text in rule.get('exclude', ())):
            found.append(rule['tool_class'])
    return found


def with_tools(g):
    """The geometry with each identified tool's default on its own segment."""
    string = []
    for segment in g.string:
        od = 2*segment.pipe.r_out/.0254
        named = [figure(c, OPTIONS['trial_compact_bha']['collar_in'] if segment.pipe.name == OPTIONS['trial_compact_bha']['name'] else od)
                 for c in classes(segment.pipe.name)]
        string.append(replace(segment, tools=tuple(t for t in named if t is not None)))
    return wg.WellGeometry(string, g.hole, g.survey)


def identified(g):
    """(segment name, tool class, collar size, band, default psi at the reference flow, reference flow) rows."""
    rows = []
    for segment in g.string:
        od = 2*segment.pipe.r_out/.0254
        for c in classes(segment.pipe.name):
            collar = OPTIONS['trial_compact_bha']['collar_in'] if segment.pipe.name == OPTIONS['trial_compact_bha']['name'] else od
            d = tool_losses.default_for(c, collar)
            rows.append(dict(segment=segment.pipe.name, tool_class=c, collar_in=collar, band_in=d.band_in,
                             default_psi=d.dp_ref_psi, flow_ref_gpm=d.flow_ref_gpm, exponent=d.exponent, status=d.status))
    return rows
