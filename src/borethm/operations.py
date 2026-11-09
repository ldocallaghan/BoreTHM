"""Operating choices for evaluate: pipe, flow, limits, timings and fluids.

evaluate chooses the pipe, the flow, the tool and pump limits, the
connection and trip timings, the rate of penetration and the drilling and
trip fluids by fixed rules. Operations states any of them. A field left as
None keeps the evaluator's rule, so Operations() and no operations give the
same result.

A stated value is used as given. Where the evaluator would otherwise search
(the flow, the connection practice, the run-in staging, the rate of
penetration and the fluids), a stated value ends that search: if it fails a
check, the evaluation reports the check as failed and does not try another
value.
"""
from dataclasses import dataclass, field, fields
import math
from numbers import Real

from borethm import well_geometry as wg

# Built-in pipe types a site file may name, by their names.
PIPES = {pipe.name: pipe for pipe in (wg.TK_DRAKON, wg.INTERNALLY_COATED, wg.EXTERNALLY_COATED,
                                      wg.CONVENTIONAL, wg.DUAL_WALL, wg.VACUUM_INSULATED)}
# Pipes with no drill pipe on sale (data/materials.md).
NOT_COMMERCIAL = (wg.DUAL_WALL.name, wg.VACUUM_INSULATED.name)

# Unit of each field, as the result's operations record gives it.
UNITS = dict(pipes=None, flow='kg/s or L/s', flows='kg/s or L/s', tool_limit_C='C',
             coating_ratings_C='C', pump_pressure_limit_Pa='Pa', rig_pumps='pumps',
             min_annular_velocity_m_s='m/s', precirculation_min='min',
             connection_median_min='min', connection_p90_min='min', trip_hours='h',
             trip_scale=None, stage_spacing_m='m', stage_minutes='min', rop_m_h='m/h',
             drilling_fluid_kg_m3='kg/m3 at 20 C', trip_fluid_kg_m3='kg/m3 at 20 C')

# Plain names of the fields, for text.
LABELS = dict(pipes='pipes', flow='flow', flows='flows', tool_limit_C='tool limit',
              coating_ratings_C='coating ratings', pump_pressure_limit_Pa='pump pressure limit',
              rig_pumps='rig pumps', min_annular_velocity_m_s='hole-cleaning velocity',
              precirculation_min='circulation before a connection',
              connection_median_min='median connection', connection_p90_min='90th-percentile connection',
              trip_hours='trip', trip_scale='trip scale', stage_spacing_m='staging interval',
              stage_minutes='stage circulation', rop_m_h='rate of penetration',
              drilling_fluid_kg_m3='drilling fluid', trip_fluid_kg_m3='trip fluid')


def describe(name, value, flow_unit='kg/s'):
    """A stated value as text, such as 'tool limit 175 C'."""
    label = LABELS[name]
    if name == 'pipes':
        return label + ' ' + ', '.join(pipe.name for pipe in value)
    if name == 'flows':
        return label + ' ' + ', '.join(f'{v:g}' for v in value) + ' ' + flow_unit
    if name == 'coating_ratings_C':
        return label + ' ' + ', '.join(f'{pipe} {v:g} C' for pipe, v in value.items())
    if name == 'pump_pressure_limit_Pa':
        return f'{label} {value / 1e6:g} MPa'
    if name == 'trip_scale':
        return f'{label} {value:g}'
    unit = flow_unit if name == 'flow' else UNITS[name]
    return f'{label} {value:g} {unit}'


# Accepted ranges [low, high]. A value outside is most often a unit slip
# (psi for Pa, hours for minutes), so validate_operations rejects it.
RANGES = dict(flow=(1.0, 300.0), flows=(1.0, 300.0), tool_limit_C=(50.0, 400.0),
              coating_ratings_C=(50.0, 400.0), pump_pressure_limit_Pa=(1.0e6, 150.0e6),
              rig_pumps=(1, 10), min_annular_velocity_m_s=(0.05, 5.0),
              precirculation_min=(0.0, 240.0), connection_median_min=(0.1, 480.0),
              connection_p90_min=(0.1, 480.0), trip_hours=(0.5, 500.0), trip_scale=(0.05, 20.0),
              stage_spacing_m=(10.0, 10000.0), stage_minutes=(0.5, 600.0), rop_m_h=(0.1, 100.0),
              drilling_fluid_kg_m3=(990.0, 2600.0), trip_fluid_kg_m3=(990.0, 2600.0))

WATER_RHO_SURFACE = 998.2   # kg/m3, water at 20 C and 0.1 MPa, to 0.1 kg/m3
_NUMBERS = ('flow', 'tool_limit_C', 'pump_pressure_limit_Pa', 'min_annular_velocity_m_s',
            'precirculation_min', 'connection_median_min', 'connection_p90_min', 'trip_hours',
            'trip_scale', 'stage_spacing_m', 'stage_minutes', 'rop_m_h', 'drilling_fluid_kg_m3',
            'trip_fluid_kg_m3')


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f'operations.{name}: expected a finite number')
    return float(value)


@dataclass(frozen=True)
class Operations:
    """Operating choices for evaluate, in SI units. Every field is optional.

    None keeps the evaluator's rule, given here for each field:

    | Field | Meaning | When None |
    |---|---|---|
    | pipes | PipeType candidates, tried in order | TK-Drakon coated, internally coated, externally coated, conventional |
    | flow | one fixed flow | the flow search |
    | flows | the flows the search tries, ascending | 5 to 50 in steps of 5, then 60 to 100 in steps of 10 |
    | tool_limit_C | the downhole tool temperature limit [C] | 200 |
    | coating_ratings_C | pipe name to coating rating [C] | TK-Drakon coated: 204 |
    | pump_pressure_limit_Pa | the standpipe pressure limit [Pa] | 51.7e6 |
    | rig_pumps | number of rig pumps | 3 |
    | min_annular_velocity_m_s | the hole-cleaning annular velocity [m/s] | 1.245 |
    | precirculation_min | circulation after the last new hole before a connection [min] | FORGE 16B 10th percentile, 0.33 |
    | connection_median_min | median connection, pumps off [min] | FORGE 16B, 2.83 |
    | connection_p90_min | 90th-percentile connection, pumps off [min] | FORGE 16B, 6.33 |
    | trip_hours | time the bottom of the hole is static for a trip [h] | FORGE 16B speeds and surface time, scaled to depth |
    | trip_scale | a factor on that rule | 1 |
    | stage_spacing_m | run-in staging interval [m] | FORGE 16B 144.88, then the staging search |
    | stage_minutes | circulation at each run-in stage [min] | FORGE 16B 15.51, then the staging search |
    | rop_m_h | rate of penetration [m/h] | Model 3, iterated with the exposure for a coupled site |
    | drilling_fluid_kg_m3 | drilling fluid surface density at 20 C [kg/m3] | the common window's lower bound, iterated |
    | trip_fluid_kg_m3 | trip fluid surface density at 20 C [kg/m3] | the larger of the drilling fluid and the trip window's lower bound |
    | sources | field name to (basis, source) | empty |

    Flows follow the evaluator's flow grid: kg/s with water; with a
    weighted fluid the same number is the surface volume flow in L/s, so the
    pumps deliver the same volume whatever the fluid's weight. The result
    reports the flow and its unit as programme.flow and programme.flow_unit.

    A stated flow, connection practice (precirculation_min or
    connection_p90_min), run-in staging (stage_spacing_m or stage_minutes),
    rate of penetration or fluid is used as given, without the search for
    another value. A stated rate of penetration also ends the iteration of
    rate and exposure for a coupled site. A stated drilling fluid lighter
    than water's 998.2 kg/m3 is water. coating_ratings_C replaces the whole
    table, so a pipe it leaves out has no rating. pipes cannot be combined
    with a HydraulicProgramme that gives custom segments, which fix the
    string. Give at most one of flow and flows, and at most one of trip_hours
    and trip_scale.

    sources maps a field name to a (basis, source) pair, with the basis
    labels of a site's data_basis. validate_operations checks ranges and
    returns warnings.
    """
    pipes: tuple | None = None
    flow: float | None = None
    flows: tuple | None = None
    tool_limit_C: float | None = None
    coating_ratings_C: dict | None = None
    pump_pressure_limit_Pa: float | None = None
    rig_pumps: int | None = None
    min_annular_velocity_m_s: float | None = None
    precirculation_min: float | None = None
    connection_median_min: float | None = None
    connection_p90_min: float | None = None
    trip_hours: float | None = None
    trip_scale: float | None = None
    stage_spacing_m: float | None = None
    stage_minutes: float | None = None
    rop_m_h: float | None = None
    drilling_fluid_kg_m3: float | None = None
    trip_fluid_kg_m3: float | None = None
    sources: dict = field(default_factory=dict)

    def __post_init__(self):
        set_ = lambda name, value: object.__setattr__(self, name, value)
        for name in _NUMBERS:
            value = getattr(self, name)
            if value is not None:
                set_(name, _finite(value, name))
        if self.rig_pumps is not None and (isinstance(self.rig_pumps, bool)
                                           or not isinstance(self.rig_pumps, int)):
            raise ValueError('operations.rig_pumps: expected a whole number')
        if self.pipes is not None:
            if isinstance(self.pipes, (str, wg.PipeType)) or not all(
                    isinstance(pipe, wg.PipeType) for pipe in self.pipes):
                raise TypeError('operations.pipes: expected a sequence of PipeType')
            set_('pipes', tuple(self.pipes))
        if self.flows is not None:
            if isinstance(self.flows, (str, Real)):
                raise ValueError('operations.flows: expected a sequence of numbers')
            set_('flows', tuple(_finite(value, 'flows') for value in self.flows))
        if self.coating_ratings_C is not None:
            if not isinstance(self.coating_ratings_C, dict):
                raise ValueError('operations.coating_ratings_C: expected a mapping of pipe name to rating')
            ratings = {}
            for name, value in self.coating_ratings_C.items():
                if not isinstance(name, str):
                    raise ValueError('operations.coating_ratings_C: pipe names must be text')
                ratings[name] = _finite(value, f'coating_ratings_C.{name}')
            set_('coating_ratings_C', ratings)
        if not isinstance(self.sources, dict):
            raise ValueError('operations.sources: expected a mapping of field name to (basis, source)')
        sources = {}
        for name, pair in self.sources.items():
            if (isinstance(pair, str) or len(pair) != 2
                    or not all(isinstance(text, str) for text in pair)):
                raise ValueError(f'operations.sources.{name}: expected a (basis, source) pair of text')
            sources[name] = tuple(pair)
        set_('sources', sources)

    def stated(self):
        """The fields given a value, as {name: value}, without sources."""
        return {f.name: getattr(self, f.name) for f in fields(self)
                if f.name != 'sources' and getattr(self, f.name) is not None}

    def timings(self, base):
        """drilling_cycle Timings with the stated connection and staging
        times; base itself when none is stated."""
        from dataclasses import replace
        changes = {}
        for name, attribute in (('precirculation_min', 'fresh_circ_p10_min'),
                                ('connection_median_min', 'connection_median_min'),
                                ('connection_p90_min', 'connection_p90_min'),
                                ('stage_minutes', 'stage_minutes')):
            if getattr(self, name) is not None:
                changes[attribute] = getattr(self, name)
        if self.stage_spacing_m is not None:
            changes['stage_spacing_ft'] = self.stage_spacing_m / 0.3048
        return replace(base, **changes) if changes else base

    @property
    def fixed_connection(self):
        """True if the connection practice is stated, so the schedule search is off."""
        return self.precirculation_min is not None or self.connection_p90_min is not None

    @property
    def fixed_staging(self):
        """True if the run-in staging is stated, so the staging search is off."""
        return self.stage_spacing_m is not None or self.stage_minutes is not None


EMPTY = Operations()


def validate_operations(operations):
    """Check an Operations; return a list of warning strings.

    Invalid values raise ValueError. Ranges are inclusive:

    | Field | Accepted range | Unit |
    |---|---|---|
    | flow and each of flows | 1 to 300 | kg/s or L/s |
    | tool_limit_C | 50 to 400 | C |
    | each coating rating | 50 to 400 | C |
    | pump_pressure_limit_Pa | 1e6 to 150e6 | Pa |
    | rig_pumps | 1 to 10 | pumps |
    | min_annular_velocity_m_s | 0.05 to 5 | m/s |
    | precirculation_min | 0 to 240 | min |
    | connection_median_min, connection_p90_min | 0.1 to 480 | min |
    | trip_hours | 0.5 to 500 | h |
    | trip_scale | 0.05 to 20 | dimensionless |
    | stage_spacing_m | 10 to 10,000 | m |
    | stage_minutes | 0.5 to 600 | min |
    | rop_m_h | 0.1 to 100 | m/h |
    | drilling_fluid_kg_m3, trip_fluid_kg_m3 | 990 to 2,600 | kg/m3 at 20 C |

    flows must rise strictly. flow with flows, and trip_hours with
    trip_scale, raise ValueError. Each sources entry must name a field and
    use a site data_basis label. Warnings: a flow outside the evaluator's
    5 to 100 grid; a pipe with no drill pipe on sale; a coating rating for
    a pipe not among the candidates; a tool limit above 300 C; a pump
    limit above the reference pumps' 7,475 psi rating, above which the rig
    check finds no capacity; a median connection longer than the 90th
    percentile; a staging interval shorter than a stand; a rate of
    penetration above Model 3's 20 m/h ceiling; a drilling fluid below
    water's density; a trip fluid lighter than the drilling fluid; a stated
    field without a source.
    """
    if not isinstance(operations, Operations):
        raise TypeError('operations must be Operations or None')
    from borethm.site_evaluation import BASES, PUMP_MAX_PSI, SITE_FLOWS, SITE_PIPES
    o, errs, warns = operations, [], []

    def check(name, value):
        lo, hi = RANGES[name]
        if not lo <= value <= hi:
            unit = UNITS.get(name) or 'dimensionless'
            errs.append(f'{name} = {value:g} is outside {lo:g} to {hi:g} {unit}')
            return False
        return True

    for name, value in o.stated().items():
        if name in RANGES and isinstance(value, Real):
            check(name, value)
    if o.flow is not None and o.flows is not None:
        errs.append('flow and flows cannot both be given')
    if o.trip_hours is not None and o.trip_scale is not None:
        errs.append('trip_hours and trip_scale cannot both be given')
    if o.pipes is not None and not o.pipes:
        errs.append('pipes is empty')
    if o.flows is not None:
        if not o.flows:
            errs.append('flows is empty')
        elif all(check('flows', value) for value in o.flows):
            if any(b <= a for a, b in zip(o.flows, o.flows[1:])):
                errs.append('flows must rise strictly')
    for name, value in (o.coating_ratings_C or {}).items():
        lo, hi = RANGES['coating_ratings_C']
        if not lo <= value <= hi:
            errs.append(f'coating rating for {name!r} = {value:g} is outside {lo:g} to {hi:g} C')
    for name, (basis, source) in o.sources.items():
        if name not in UNITS:
            errs.append(f'sources names {name!r}, which is not an operations field')
        if basis not in BASES:
            errs.append(f'sources.{name}: {basis!r} is not one of ' + ', '.join(BASES))
        if not source:
            warns.append(f'operations.{name} has no source')
    if errs:
        raise ValueError('operations: ' + '; '.join(errs))

    grid = (min(SITE_FLOWS), max(SITE_FLOWS))
    for value in ((o.flow,) if o.flow is not None else ()) + (o.flows or ()):
        if not grid[0] <= value <= grid[1]:
            warns.append(f'operations flow {value:g} is outside the evaluator\'s flow grid, '
                         f'{grid[0]:g} to {grid[1]:g}')
    candidates = o.pipes if o.pipes is not None else SITE_PIPES
    for pipe in o.pipes or ():
        if pipe.name in NOT_COMMERCIAL:
            warns.append(f'operations pipe {pipe.name!r} is not a drill pipe on sale (data/materials.md)')
    for name in o.coating_ratings_C or {}:
        if name not in {pipe.name for pipe in candidates}:
            warns.append(f'operations coating rating for {name!r}, which is not a candidate pipe')
    if o.tool_limit_C is not None and o.tool_limit_C > 300.0:
        warns.append(f'operations tool limit {o.tool_limit_C:g} C is above 300 C, the ceiling '
                     'for any downhole electronics in geo_constants')
    psi = 6894.757
    if o.pump_pressure_limit_Pa is not None and o.pump_pressure_limit_Pa > PUMP_MAX_PSI * psi:
        warns.append(f'operations pump limit {o.pump_pressure_limit_Pa / 1e6:.1f} MPa is above the '
                     f'reference pumps\' {PUMP_MAX_PSI:,.0f} psi rating; the rig check finds no '
                     'capacity above it')
    if None not in (o.connection_median_min, o.connection_p90_min) and \
            o.connection_median_min > o.connection_p90_min:
        warns.append('operations connection_median_min is longer than connection_p90_min')
    if o.stage_spacing_m is not None and o.stage_spacing_m < 93.62 * 0.3048:
        warns.append(f'operations stage_spacing_m {o.stage_spacing_m:g} m is shorter than a '
                     'stand, 28.5 m')
    if o.rop_m_h is not None and o.rop_m_h > 20.0:
        warns.append(f'operations rop_m_h {o.rop_m_h:g} m/h is above Model 3\'s 20 m/h ceiling')
    if o.drilling_fluid_kg_m3 is not None and o.drilling_fluid_kg_m3 < WATER_RHO_SURFACE:
        warns.append(f'operations drilling_fluid_kg_m3 {o.drilling_fluid_kg_m3:g} is below water\'s '
                     f'{WATER_RHO_SURFACE:g} kg/m3; the drilling fluid is water')
    if o.trip_fluid_kg_m3 is not None and o.trip_fluid_kg_m3 < WATER_RHO_SURFACE:
        warns.append(f'operations trip_fluid_kg_m3 {o.trip_fluid_kg_m3:g} is below water\'s '
                     f'{WATER_RHO_SURFACE:g} kg/m3; the trip fluid is water')
    if None not in (o.drilling_fluid_kg_m3, o.trip_fluid_kg_m3) and \
            o.trip_fluid_kg_m3 < o.drilling_fluid_kg_m3:
        warns.append('operations trip_fluid_kg_m3 is lighter than drilling_fluid_kg_m3')
    for name in o.stated():
        if name not in o.sources:
            warns.append(f'operations.{name} has no source')
    return warns


# ------------------------------------------------------------ site files
TOML_KEYS = tuple(UNITS) + ('sources',)


def operations_from_dict(value):
    """Parse the optional [operations] table of a site file.

    Keys are Operations field names. pipes names built-in pipe types;
    coating_ratings_C is a table of pipe name to rating; sources is a table
    of field name to [basis, source]. Unknown keys and wrong types raise
    ValueError naming the key.
    """
    if not isinstance(value, dict):
        raise ValueError('expected a table')
    for name in value:
        if name not in TOML_KEYS:
            raise ValueError(f'{name}: unknown key')
    arguments = {}
    for name, item in value.items():
        if name == 'pipes':
            if not isinstance(item, list) or not all(isinstance(text, str) for text in item):
                raise ValueError('pipes: expected an array of pipe names')
            for text in item:
                if text not in PIPES:
                    raise ValueError(f'pipes: unknown pipe {text!r}; choose from '
                                     + ', '.join(repr(key) for key in PIPES))
            arguments[name] = tuple(PIPES[text] for text in item)
        elif name == 'flows':
            if not isinstance(item, list):
                raise ValueError('flows: expected an array of numbers')
            for index, number in enumerate(item):
                if isinstance(number, bool) or not isinstance(number, (int, float)):
                    raise ValueError(f'flows[{index}]: expected a number')
            arguments[name] = tuple(item)
        elif name == 'coating_ratings_C':
            if not isinstance(item, dict):
                raise ValueError('coating_ratings_C: expected a table of pipe name to rating')
            for pipe, number in item.items():
                if isinstance(number, bool) or not isinstance(number, (int, float)):
                    raise ValueError(f'coating_ratings_C.{pipe}: expected a number')
            arguments[name] = dict(item)
        elif name == 'sources':
            if not isinstance(item, dict):
                raise ValueError('sources: expected a table of field name to [basis, source]')
            for key, pair in item.items():
                if not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(text, str) for text in pair):
                    raise ValueError(f'sources.{key}: expected [basis, source]')
            arguments[name] = {key: tuple(pair) for key, pair in item.items()}
        elif name == 'rig_pumps':
            if isinstance(item, bool) or not isinstance(item, int):
                raise ValueError('rig_pumps: expected a whole number')
            arguments[name] = item
        else:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise ValueError(f'{name}: expected a number')
            arguments[name] = item
    try:
        return Operations(**arguments)
    except (TypeError, ValueError) as error:
        raise ValueError(str(error).removeprefix('operations.')) from None


def operations_toml(operations):
    """The [operations] table for an Operations, as TOML text."""
    import json
    rows = ['[operations]']
    tables = []
    for name, value in operations.stated().items():
        if name == 'pipes':
            rows.append('pipes = [' + ', '.join(json.dumps(pipe.name) for pipe in value) + ']')
        elif name == 'flows':
            rows.append('flows = [' + ', '.join(repr(v) for v in value) + ']')
        elif name == 'coating_ratings_C':
            tables.append('[operations.coating_ratings_C]')
            tables += [f'{json.dumps(pipe)} = {rating!r}' for pipe, rating in value.items()]
        else:
            rows.append(f'{name} = {value!r}')
    if operations.sources:
        tables.append('[operations.sources]')
        tables += [f'{name} = [{json.dumps(basis)}, {json.dumps(source)}]'
                   for name, (basis, source) in operations.sources.items()]
    return '\n'.join(rows + ([''] + tables if tables else [])) + '\n'


TEMPLATE = '''
# Operations: optional. Each key states a choice the evaluator otherwise
# makes by its own rule; leave a key out to keep that rule. Remove the
# leading "# " from [operations] and from each key you state. A stated
# flow, connection practice, staging, rate of penetration or fluid is used
# as given: if it fails a check, the result reports the failure and the
# evaluator does not search for another value.
# [operations]
# Pipe candidates, tried in order. Default: the four below. Also accepted:
# "dual-wall" and "vacuum-insulated (sensitivity)", which are not on sale.
# pipes = ["TK-Drakon coated", "internally coated", "externally coated", "conventional"]
# One fixed flow, kg/s with water or L/s at surface with a weighted fluid,
# 1 to 300. Default: the search over flows below. Give flow or flows.
# flow = 30.0
# The flows the search tries, rising. Default:
# flows = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100]
# Downhole tool temperature limit, C, 50 to 400. Default 200.
# tool_limit_C = 200.0
# Standpipe pressure limit, Pa, 1e6 to 150e6. Default 51.7e6 (7,500 psi).
# pump_pressure_limit_Pa = 51.7e6
# Rig pumps, 1 to 10. Default 3 (each 1,980 hydraulic hp, 7,475 psi).
# rig_pumps = 3
# Hole-cleaning annular velocity, m/s, 0.05 to 5. Default 1.245.
# min_annular_velocity_m_s = 1.245
# Circulation after the last new hole before a connection, min, 0 to 240.
# Default 0.33 (FORGE 16B, 10th percentile). Stating it or
# connection_p90_min ends the connection schedule search.
# precirculation_min = 0.33
# Connection with the pumps off, min, 0.1 to 480. Defaults: FORGE 16B
# median 2.83 and 90th percentile 6.33.
# connection_median_min = 2.83
# connection_p90_min = 6.33
# Time the bottom of the hole is static for a trip, h, 0.5 to 500.
# Default: FORGE 16B tripping speeds and surface time, scaled to the
# target depth. trip_scale, 0.05 to 20, multiplies that rule. Give one.
# trip_hours = 17.5
# trip_scale = 1.0
# Run-in staging: interval, m, 10 to 10,000, and circulation at each
# stage, min, 0.5 to 600. Defaults: FORGE 16B 144.88 m and 15.51 min,
# then a search over shorter intervals and longer stages. Stating either
# ends the search.
# stage_spacing_m = 144.88
# stage_minutes = 15.51
# Rate of penetration, m/h, 0.1 to 100. Default: Model 3, iterated with
# the wall's exposure for a coupled site.
# rop_m_h = 10.0
# Drilling and trip fluid surface densities at 20 C, kg/m3, 990 to 2,600.
# Defaults: the common windows' lower bounds, iterated with the
# circulation. A value below water's 998.2 is water.
# drilling_fluid_kg_m3 = 1100.0
# trip_fluid_kg_m3 = 1150.0
# Coating ratings, C, by pipe name. Default: TK-Drakon coated 204. A
# stated table replaces the default, so a pipe left out has no rating.
# [operations.coating_ratings_C]
# "TK-Drakon coated" = 204.0
# Sources for stated values, [basis, source], with the data_basis labels.
# [operations.sources]
# tool_limit_C = ["assumed", "Replace with the tool's rating sheet"]
'''
