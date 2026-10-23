"""Thermal and borehole-stability calculations for geothermal drilling.

Names in __all__ form the public interface and follow semantic versioning.
Other modules and objects are internal.
"""
from importlib import import_module
from importlib.metadata import version

__version__ = version('borethm')

_EXPORTS = {
    'evaluate': ('site_evaluation', 'evaluate'),
    'result_dict': ('site_evaluation', 'result_dict'),
    'export_result': ('site_evaluation', 'export_result'),
    'SiteProfile': ('site_evaluation', 'SiteProfile'),
    'StressProfile': ('site_evaluation', 'StressProfile'),
    'validate_site': ('site_evaluation', 'validate_site'),
    'load_site': ('site_files', 'load_site'),
    'layered_geotherm': ('site_evaluation', 'layered_geotherm'),
    'named_sites': ('site_evaluation', 'named_sites'),
    'find_site': ('site_evaluation', 'find_site'),
    'circulating_temperatures': ('_api', 'circulating_temperatures'),
    'hydraulics': ('model1_coupled', 'hydraulics'),
    'mud_window': ('site_evaluation', 'mud_window'),
    'thermal_hoop_stress': ('site_evaluation', 'thermal_hoop_stress'),
    'breakout_check': ('site_evaluation', 'breakout_eff'),
    'breakout_width': ('model5_convergence_confinement', 'breakout_width'),
    'wall_temperatures': ('wall_thermal', 'run'),
    'tool_trip_in': ('tool_thermal', 'trip_in'),
    'water_properties': ('water_table', 'props'),
    'WellGeometry': ('well_geometry', 'WellGeometry'),
    'PipeType': ('well_geometry', 'PipeType'),
    'WallState': ('wall_thermal', 'State'),
    'ToolLump': ('tool_thermal', 'Lump'),
    'Layer': ('well_geometry', 'Layer'),
    'StringSegment': ('well_geometry', 'StringSegment'),
    'HoleInterval': ('well_geometry', 'HoleInterval'),
    'Survey': ('well_geometry', 'Survey'),
    'uniform_wall': ('well_geometry', 'uniform_wall'),
    'open_hole': ('well_geometry', 'open_hole'),
    'cased': ('well_geometry', 'cased'),
}

__all__ = [*_EXPORTS, '__version__']


def __getattr__(name):
    # Resolve exports on demand so python -m can execute command modules once.
    if name in _EXPORTS:
        module, attribute = _EXPORTS[name]
        value = getattr(import_module('.' + module, __name__), attribute)
        globals()[name] = value
        return value
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def __dir__():
    return sorted(set(globals()) | set(__all__))
