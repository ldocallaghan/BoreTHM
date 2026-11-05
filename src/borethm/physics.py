"""Named sets of default physics.

physics='v1.8.0' is the package default and 'v1.7.0' restores the previous
defaults. An explicitly passed keyword overrides its row of the preset.
"""
from contextlib import contextmanager
from contextvars import ContextVar

PRESETS = {
    'v1.8.0': dict(annulus_model='herschel-bulkley-erge', friction='colebrook', roughness=0.,
                   ordinary_joint_transition='tapered', taper_angle_deg=11.5,
                   tool_defaults=True, motor_no_load=True, rheology_from_pv_yp=True),
    'v1.7.0': dict(annulus_model='v1.6.0', friction='blasius', roughness=0.,
                   ordinary_joint_transition='abrupt', taper_angle_deg=None,
                   tool_defaults=False, motor_no_load=False, rheology_from_pv_yp=False),
}
DEFAULT = 'v1.8.0'
_active = ContextVar('borethm_physics', default=DEFAULT)


def check(physics):
    if physics not in PRESETS:
        raise ValueError(f'physics must be one of {tuple(PRESETS)}')
    return physics


def current(physics=None):
    """physics if given, otherwise the active default."""
    return _active.get() if physics is None else check(physics)


@contextmanager
def using(physics):
    """Make physics the default inside a with block; None leaves it unchanged."""
    token = _active.set(current(physics))
    try:
        yield
    finally:
        _active.reset(token)


def resolve(physics=None, annulus_model=None, friction=None, roughness=None, hydraulics_model=None):
    """Every resolved setting as a dictionary, with its name under 'physics'.

    hydraulics_model 'v1.5.0' reproduces the original calculation, so it takes
    the v1.7.0 preset. A keyword that is not None overrides the preset.
    """
    name = 'v1.7.0' if hydraulics_model == 'v1.5.0' else current(physics)
    settings = dict(PRESETS[name], physics=name)
    for key, value in (('annulus_model', annulus_model), ('friction', friction), ('roughness', roughness)):
        if value is not None:
            settings[key] = value
    return settings
