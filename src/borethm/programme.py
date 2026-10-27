"""Typed hydraulic programme and strict data-only site-file parsing."""
from dataclasses import dataclass, fields, replace
import math

from borethm import well_geometry as wg
from borethm.hydraulic_losses import HydraulicJoint, LocalLoss, ReferenceToolLoss, SurfaceLoss, PSI, GPM, PPG

REFERENCE = 'wu2025-with-hydraulic-allowances'
_DEFAULT = object()


@dataclass(frozen=True)
class HydraulicProgramme:
    """Hydraulic mode, surface layout and reference or custom string.

    Python lengths are metres and losses use SI. reference_programme()
    selects the documented built-in allowances, including surface case 5.
    A custom string must explicitly supply its own tool curves. Optional
    hole intervals otherwise retain the reference well's casing scenario.
    """
    hydraulics_model: str = 'v1.6.0'
    reference: str | None = REFERENCE
    segments: tuple = ()
    hole: tuple = ()
    surface: SurfaceLoss | None = None
    transitions: str = 'abrupt'
    joints: bool = True
    tools: bool = True
    joint_restriction_length: float = 29*wg.INCH
    hwdp_restriction_length: float = 48*wg.INCH

    def __post_init__(self):
        for name in ('joints','tools'):
            if type(getattr(self,name)) is not bool:
                raise ValueError(f'programme.{name} must be a boolean')
        if not all(isinstance(s,wg.StringSegment) for s in self.segments) or not all(isinstance(h,wg.HoleInterval) for h in self.hole):
            raise TypeError('programme segments and hole must contain typed geometry records')
        if self.hydraulics_model not in ('v1.5.0','v1.6.0'):
            raise ValueError('programme.hydraulics_model must be v1.5.0 or v1.6.0')
        if self.reference not in (None,REFERENCE):
            raise ValueError('unknown programme.reference')
        if bool(self.segments)==bool(self.reference):
            raise ValueError('programme requires either a reference or custom segments')
        if self.transitions not in ('abrupt','gradual'):
            raise ValueError('programme.transitions must be abrupt or gradual')
        if self.surface is not None and not isinstance(self.surface,SurfaceLoss):
            raise TypeError('programme.surface must be SurfaceLoss or None')
        if self.hydraulics_model=='v1.5.0' and (self.surface is not None or self.transitions!='abrupt' or self.reference and (self.joints or self.tools)):
            raise ValueError('legacy programme rejects new losses; disable reference joints/tools and surface')
        for name in ('joint_restriction_length','hwdp_restriction_length'):
            value=getattr(self,name)
            if isinstance(value,bool) or not math.isfinite(value) or value<0:
                raise ValueError(f'programme.{name} must be non-negative and finite')

    @classmethod
    def reference_programme(cls,hydraulics_model='v1.6.0',surface=_DEFAULT,**kwargs):
        if surface is _DEFAULT:
            surface=SurfaceLoss.api_case(5) if hydraulics_model=='v1.6.0' else None
        if hydraulics_model=='v1.5.0':
            kwargs.setdefault('joints',False)
            kwargs.setdefault('tools',False)
        return cls(hydraulics_model=hydraulics_model,surface=surface,**kwargs)

    def geometry(self,depth,pipe,survey=None,shoes=wg.WU_SHOES):
        def reference_hole():
            # A shallow programme can end inside a casing. Keep only the
            # intervals actually reached, with no reversed open-hole tail.
            intervals=wg.wu2025_hole(max(depth,shoes[-1]),shoes)
            return tuple(replace(h,md_bottom=min(h.md_bottom,depth)) for h in intervals if h.md_top<depth)
        if self.segments:
            if not math.isclose(sum(s.length for s in self.segments),depth,abs_tol=1e-6,rel_tol=0):
                raise ValueError('custom programme segment lengths must sum to the circulation depth')
            return wg.WellGeometry(self.segments,self.hole or reference_hole(),survey)
        if self.hydraulics_model=='v1.5.0':
            return wg.wu2025_well(depth,pipe,survey,shoes)
        if self.joints:
            transferred=pipe.name in (wg.DUAL_WALL.name,wg.VACUUM_INSULATED.name)
            joint=HydraulicJoint(7*wg.INCH,2*pipe.r_bore if transferred else 4*wg.INCH,
                self.joint_restriction_length,2378*0.3048/75,self.transitions,
                'NOV GPDS/EIS catalogue; 29-in effective length and 16B tally pitch assumed; '+
                ('external envelope transferred; joint bore equals body bore' if transferred else 'reference connection scenario'))
            pipe=replace(pipe,hydraulic_joint=joint)
            hw=replace(wg.WU_HWDP,hydraulic_joint=HydraulicJoint(7.25*wg.INCH,3.25*wg.INCH,
                self.hwdp_restriction_length,31*.3048,self.transitions,
                'Workstrings 91005000020000, 1 Aug 2025; 48-in effective length assumed'))
        else:
            hw=wg.WU_HWDP
        lower=wg.WU_L_HWDP+wg.WU_L_COLLAR+wg.WU_L_BIT
        if depth<=lower:
            raise ValueError('reference programme depth must exceed the fixed lower assembly length')
        pulser=wg.PipeType('reference MWD pulser',(wg.Layer(3.38*wg.INCH/2,7*wg.INCH/2,wg.K_STEEL),),
                           source='xBolt G2-L Rev 7, p2')
        collar=wg.PipeType('reference MWD collar',(wg.Layer(3.25*wg.INCH/2,6.75*wg.INCH/2,wg.K_STEEL),),
                           source='xBolt G2-L Rev 7, p2')
        tool=ReferenceToolLoss((1000/PPG)*500**2/30000*PSI,500*GPM,1000.,'total_internal',2,
            'xBolt G2-L Rev 7 p2, 6.75-in mud-pulse allowance; not verified field hardware',
            (0.,750*GPM),165.) if self.tools else None
        string=(wg.StringSegment(depth-lower,pipe),wg.StringSegment(wg.WU_L_HWDP,hw),
                wg.StringSegment(132.075968,wg.WU_COLLAR),wg.StringSegment(1.780032,pulser,tool_loss=tool),
                wg.StringSegment(9.144,collar),wg.StringSegment(wg.WU_L_BIT,wg.WU_COLLAR))
        return wg.WellGeometry(string,self.hole or reference_hole(),survey)


def _keys(value,allowed,key):
    if not isinstance(value,dict):
        raise ValueError(f'{key}: expected a table')
    extra=set(value)-set(allowed)
    if extra:
        raise ValueError(f'{key}.{sorted(extra)[0]}: unknown key')


def _record(cls,value,key):
    _keys(value,{f.name for f in fields(cls)},key)
    numeric={f.name for f in fields(cls)}-{'source','transition','basis','flow_range'}
    for name,item in value.items():
        if name in numeric and (isinstance(item,bool) or not isinstance(item,(int,float)) or not math.isfinite(item)):
            raise ValueError(f'{key}.{name}: expected a finite number')
        if name in ('source','transition','basis') and not isinstance(item,str):
            raise ValueError(f'{key}.{name}: expected text')
    try:
        return cls(**value)
    except (TypeError,ValueError) as error:
        raise ValueError(f'{key}: {error}') from None


def programme_from_dict(value):
    """Parse the optional programme TOML table; unknown nested keys fail."""
    allowed={f.name for f in fields(HydraulicProgramme)}
    _keys(value,allowed,'programme')
    values=dict(value)
    if 'surface' in values:
        s=values['surface']
        _keys(s,{'case','coefficient','enabled','source'},'programme.surface')
        if sum(k in s for k in ('case','coefficient','enabled'))!=1:
            raise ValueError('programme.surface: choose exactly one of case, coefficient, enabled=false')
        if 'enabled' in s:
            if s['enabled'] is not False:
                raise ValueError('programme.surface.enabled must be false')
            values['surface']=None
        elif 'case' in s:
            values['surface']=SurfaceLoss.api_case(s['case'])
        else:
            values['surface']=SurfaceLoss.coefficient(s['coefficient'],s.get('source','site-supplied surface coefficient'))
    for name in ('joints','tools'):
        if name in values and type(values[name]) is not bool:
            raise ValueError(f'programme.{name}: expected a boolean')
    if 'segments' in values:
        if 'reference' in values:
            raise ValueError('programme: reference and segments are mutually exclusive')
        if not isinstance(values['segments'],list) or not values['segments']:
            raise ValueError('programme.segments: expected a non-empty array of tables')
        segments=[]
        for i,s in enumerate(values['segments']):
            key=f'programme.segments[{i}]'
            _keys(s,{'length','name','bore_diameter','outer_diameter','conductivity','source','joint_fraction',
                     'hydraulic_joint','local_loss','tool_loss'},key)
            try:
                for name in ('length','bore_diameter','outer_diameter','conductivity','joint_fraction'):
                    if name in s and (isinstance(s[name],bool) or not isinstance(s[name],(float,int)) or not math.isfinite(s[name])):
                        raise ValueError(f'{name} must be a finite number')
                for name in ('name','source'):
                    if name in s and not isinstance(s[name],str):
                        raise ValueError(f'{name} must be text')
                pipe=wg.PipeType(s.get('name',f'segment {i}'),
                    (wg.Layer(s['bore_diameter']/2,s['outer_diameter']/2,s.get('conductivity',wg.K_STEEL)),),
                    s.get('joint_fraction',0.),s.get('source','site-supplied geometry'),
                    _record(HydraulicJoint,s['hydraulic_joint'],key+'.hydraulic_joint') if 'hydraulic_joint' in s else None)
                if not 0 < pipe.r_bore < pipe.r_out or pipe.layers[0].k<=0:
                    raise ValueError('require 0 < bore < OD and positive conductivity')
                segments.append(wg.StringSegment(s['length'],pipe,
                    _record(LocalLoss,s['local_loss'],key+'.local_loss') if 'local_loss' in s else None,
                    _record(ReferenceToolLoss,s['tool_loss'],key+'.tool_loss') if 'tool_loss' in s else None))
            except (KeyError,TypeError,ValueError) as error:
                raise ValueError(f'{key}: {error}') from None
        values.update(reference=None,segments=tuple(segments))
    if 'hole' in values:
        if not isinstance(values['hole'],list):
            raise ValueError('programme.hole: expected an array of tables')
        holes=[]
        for i,h in enumerate(values['hole']):
            _keys(h,{'md_top','md_bottom','r_wall','layers'},f'programme.hole[{i}]')
            for name in ('md_top','md_bottom','r_wall'):
                if name not in h or isinstance(h[name],bool) or not isinstance(h[name],(float,int)) or not math.isfinite(h[name]):
                    raise ValueError(f'programme.hole[{i}].{name}: expected a finite number')
            if not 0<=h['md_top']<h['md_bottom'] or h['r_wall']<=0:
                raise ValueError(f'programme.hole[{i}]: require increasing depths and positive radius')
            for row in h.get('layers',[]):
                if len(row)!=3 or any(isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x) for x in row) or not 0<row[0]<row[1] or row[2]<=0:
                    raise ValueError(f'programme.hole[{i}].layers: require [positive inner radius, larger outer radius, positive conductivity]')
            layers=tuple(wg.Layer(*row) for row in h.get('layers',[]))
            holes.append(wg.HoleInterval(h['md_top'],h['md_bottom'],h['r_wall'],layers))
        values['hole']=tuple(holes)
    if 'surface' not in values and not values.get('segments') and values.get('hydraulics_model','v1.6.0')=='v1.6.0':
        values['surface']=SurfaceLoss.api_case(5)
    if values.get('hydraulics_model')=='v1.5.0':
        values.setdefault('joints',False)
        values.setdefault('tools',False)
    return HydraulicProgramme(**values)
