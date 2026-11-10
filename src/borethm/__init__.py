"""Thermal and borehole-stability calculations for geothermal drilling.

Names in __all__ form the public interface and follow semantic versioning.
Other modules and objects are internal.
"""
from importlib import import_module
from importlib.metadata import version

__version__ = version('borethm')

_EXPORTS = {
    'HydraulicJoint': ('hydraulic_losses','HydraulicJoint'),
    'DownholeTool': ('hydraulic_losses','DownholeTool'),
    'HerschelBulkley': ('fluids','HerschelBulkley'),
    'Mud': ('fluids', 'Mud'),
    'LocalLoss': ('hydraulic_losses','LocalLoss'),
    'ReferenceToolLoss': ('hydraulic_losses','ReferenceToolLoss'),
    'SurfaceLoss': ('hydraulic_losses','SurfaceLoss'),
    'LossModel': ('hydraulic_losses', 'LossModel'),
    'HydraulicProgramme': ('programme','HydraulicProgramme'),
    'named_pipes': ('_api', 'named_pipes'),
    'Operations': ('operations', 'Operations'),
    'validate_operations': ('operations', 'validate_operations'),
    'operation_defaults': ('operations', 'operation_defaults'),
    'operations_from_dict': ('operations', 'operations_from_dict'),
    'evaluate': ('site_evaluation', 'evaluate'),
    'result_dict': ('site_evaluation', 'result_dict'),
    'export_result': ('site_evaluation', 'export_result'),
    'SiteProfile': ('site_evaluation', 'SiteProfile'),
    'StressProfile': ('site_evaluation', 'StressProfile'),
    'validate_site': ('site_evaluation', 'validate_site'),
    'data_bases': ('_api', 'data_bases'),
    'load_site': ('site_files', 'load_site'),
    'site_text': ('site_files', 'site_text'),
    'site_well': ('site_evaluation', 'site_well'),
    'layered_geotherm': ('site_evaluation', 'layered_geotherm'),
    'named_sites': ('site_evaluation', 'named_sites'),
    'find_site': ('site_evaluation', 'find_site'),
    'circulating_temperatures': ('_api', 'circulating_temperatures'),
    'resolve_physics': ('physics', 'resolve'),
    'fluid_props': ('model1_coupled', 'fluid_props'),
    'hydrostatic_pressure': ('model1_coupled', 'P_of_z'),
    'pressure_column': ('pressure', 'column'),
    'exposure_seconds': ('model1_coupled', 'exposure_seconds'),
    'hydraulics': ('model1_coupled', 'hydraulics'),
    'mud_window': ('site_evaluation', 'mud_window'),
    'thermal_hoop_stress': ('site_evaluation', 'thermal_hoop_stress'),
    'breakout_check': ('site_evaluation', 'breakout_eff'),
    'breakout_width': ('model5_convergence_confinement', 'breakout_width'),
    'wall_temperatures': ('wall_thermal', 'run'),
    'WallGrid': ('_api', 'WallGrid'),
    'wall_grid_radius': ('wall_thermal', 'r_max_for'),
    'tool_trip_in': ('tool_thermal', 'trip_in'),
    'tool_temperatures': ('tool_thermal', 'run'),
    'ToolSegment': ('tool_thermal', 'Segment'),
    'ToolHistory': ('tool_thermal', 'History'),
    'tool_loss_defaults': ('tool_losses', 'defaults'),
    'water_properties': ('water_table', 'props'),
    'water_table_info': ('water_table', 'water_table_info'),
    'prepare_water_table': ('water_table', 'prepare_water_table'),
    'release_reference_row': ('studies.release_v134', 'reference_row'),
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
