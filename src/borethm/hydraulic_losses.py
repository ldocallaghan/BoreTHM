"""Shared passage losses and distributed dissipation, in SI units.

Surface cases: API RP 13D, sixth edition (2009), section 7.3,
equation 60/table 4. Sudden changes: Idelchik, as documented by Modelica
4.0.0, dp_suddenChange (expansion Re > 3300, contraction Re > 10000).
Annular and Bingham use of the local correlations is an approximation.
"""
from dataclasses import dataclass
import math

import numpy as np

PROPERTY_FLOOR = 5e6
PSI = 6894.757
GPM = 6.30902e-5
PPG = 119.826
SURFACE_CASES = {1: 1.0, 2: .36, 3: .22, 4: .15, 5: .15}


def _finite(value, name, positive=False):
    if isinstance(value, bool) or not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f'{name} must be finite and '+('positive' if positive else 'non-negative'))


@dataclass(frozen=True)
class HydraulicJoint:
    """Repeated connection geometry [m], independent of thermal joints.

    restriction_length is the effective narrow-passage length; spacing is
    the connection pitch. transition is abrupt or the zero-local-loss
    gradual idealisation. source records the catalogue and assumptions.
    """
    outer_diameter: float
    bore_diameter: float
    restriction_length: float
    spacing: float
    transition: str = 'abrupt'
    source: str = ''

    def __post_init__(self):
        for name in ('outer_diameter','bore_diameter','spacing'):
            _finite(getattr(self,name),name,True)
        _finite(self.restriction_length,'restriction_length')
        if self.bore_diameter >= self.outer_diameter or self.restriction_length > self.spacing:
            raise ValueError('joint requires bore < OD and restriction length <= spacing')
        if self.transition not in ('abrupt','gradual'):
            raise ValueError('transition must be abrupt or gradual')


@dataclass(frozen=True)
class LocalLoss:
    """Additional component K values; reference areas are m2.

    None uses that component's body bore/annulus area. These coefficients
    must exclude geometric transitions already represented automatically.
    """
    bore_coefficient: float = 0.0
    annulus_coefficient: float = 0.0
    bore_reference_area: float | None = None
    annulus_reference_area: float | None = None
    source: str = ''

    def __post_init__(self):
        for name in ('bore_coefficient','annulus_coefficient'):
            _finite(getattr(self,name),name)
        for name in ('bore_reference_area','annulus_reference_area'):
            if getattr(self,name) is not None:
                _finite(getattr(self,name),name,True)


@dataclass(frozen=True)
class ReferenceToolLoss:
    """Tool pressure loss [Pa] at reference flow [m3/s] and density [kg/m3].

    Scales as density times flow squared. total_internal replaces internal
    passage losses over span_segments contiguous segments, including the
    segment carrying this input; additional supplies an extra restriction.
    Optional flow_range is m3/s and temperature_max_C is a qualification.
    include_boundary_changes=False excludes internal entry/exit restrictions
    inferred from a thermal-only bore. unresolved qualifies an omitted loss
    and requires zero reference pressure; it never makes a solve fail.
    """
    dp_ref: float
    flow_ref: float
    density_ref: float
    basis: str = 'additional'
    span_segments: int = 1
    source: str = ''
    flow_range: tuple | None = None
    temperature_max_C: float | None = None
    include_boundary_changes: bool = True
    unresolved: bool = False

    def __post_init__(self):
        _finite(self.dp_ref,'dp_ref')
        _finite(self.flow_ref,'flow_ref',True)
        _finite(self.density_ref,'density_ref',True)
        if type(self.include_boundary_changes) is not bool or type(self.unresolved) is not bool:
            raise ValueError('tool boundary and unresolved qualifiers must be boolean')
        if self.unresolved and self.dp_ref != 0:
            raise ValueError('an unresolved tool loss must have zero reference pressure')
        if self.basis not in ('additional','total_internal'):
            raise ValueError('tool basis must be additional or total_internal')
        if type(self.span_segments) is not int or self.span_segments < 1:
            raise ValueError('span_segments must be a positive integer')
        if self.flow_range is not None:
            if len(self.flow_range)!=2 or not 0 <= self.flow_range[0] < self.flow_range[1] or not all(map(math.isfinite,self.flow_range)):
                raise ValueError('flow_range must contain two increasing positive finite flows')
        if self.temperature_max_C is not None and not math.isfinite(self.temperature_max_C):
            raise ValueError('temperature_max_C must be finite')

    def pressure(self, density, flow):
        return self.dp_ref*(np.asarray(density)/self.density_ref)*(np.asarray(flow)/self.flow_ref)**2


@dataclass(frozen=True)
class SurfaceLoss:
    """API surface-layout coefficient, in the psi/ppg/US-gpm convention."""
    value: float
    source: str = ''

    def __post_init__(self):
        _finite(self.value,'surface coefficient')
        if not isinstance(self.source,str):
            raise ValueError('surface source must be text')

    @classmethod
    def api_case(cls, case):
        if type(case) is not int or case not in SURFACE_CASES:
            raise ValueError('surface case must be an integer from 1 to 5')
        return cls(SURFACE_CASES[case],f'API RP 13D, sixth edition (2009), section 7.3, equation 60/table 4, case {case}')

    @classmethod
    def coefficient(cls, value, source='user-supplied surface coefficient'):
        return cls(value,source)

    def pressure(self, density, flow):
        return self.value*(density/PPG)*(flow/GPM/100.)**1.86*PSI


def passage_gradient(rho, mu, yield_point, mass_rate, area, dh, annulus=False, friction='blasius'):
    """Positive friction gradient [Pa/m], apparent Re and velocity [m/s].

    Takes already evaluated properties so frozen-point formula replays do
    not change their sampling. Mud uses the retained Bingham treatment.
    """
    from borethm import fluids, model1_coupled as m1
    velocity=mass_rate/(np.asarray(rho)*area)
    if yield_point > 0:
        gradient,re=fluids.bingham_gradient(rho,mu,yield_point,velocity,dh,annulus)
    else:
        re=np.asarray(rho)*velocity*dh/mu
        gradient=m1.friction_factor(re,friction)*np.asarray(rho)*velocity**2/(2*dh)
    return gradient,re,velocity


def local_change(area_up, area_down, rho, mass_rate, mu, dh_small):
    """Sudden-change loss [Pa], K, plastic Re and correlation-domain flag."""
    small=np.minimum(area_up,area_down)
    ratio=small/np.maximum(area_up,area_down)
    expansion=np.asarray(area_down)>area_up
    k=np.where(expansion,(1-ratio)**2,.5*(1-ratio)**.75)
    velocity=mass_rate/(rho*small)
    re=rho*velocity*dh_small/mu
    valid=(re>np.where(expansion,3300.,10000.)) | (k==0)
    return k*.5*rho*velocity**2,k,re,valid


def joint_increment(rho, mu, yield_point, mass_rate, body_area, body_dh,
                    joint_area, joint_dh, restriction_length, annulus=False,
                    transition='abrupt', friction='blasius'):
    """Replacement and entry/exit loss [Pa] for one connection.

    The body subtraction can give a negative increment. It replaces only
    the declared restriction length, with the remaining body retained.
    """
    body=passage_gradient(rho,mu,yield_point,mass_rate,body_area,body_dh,annulus,friction)[0]
    joint=passage_gradient(rho,mu,yield_point,mass_rate,joint_area,joint_dh,annulus,friction)[0]
    local=0.
    if transition=='abrupt':
        # Both directions use the smaller passage's hydraulic diameter.
        dh=np.where(np.asarray(body_area)<=joint_area,body_dh,joint_dh)
        local=local_change(body_area,joint_area,rho,mass_rate,mu,dh)[0]+local_change(joint_area,body_area,rho,mass_rate,mu,dh)[0]
    return (joint-body)*restriction_length,local


class LossModel:
    """Prepared geometry-only loss placement, shared by pressure and heat."""

    def __init__(self, geometry, friction='blasius', transitions='abrupt'):
        from borethm import model1_coupled as m1
        if transitions not in ('abrupt','gradual'):
            raise ValueError('transitions must be abrupt or gradual')
        self.geometry=geometry
        self.friction=friction
        self.transitions=transitions
        self.top,self.bottom=m1._pieces(geometry)
        self.length=self.bottom-self.top
        self.replaced=np.zeros(len(geometry.string),bool)
        self.tool_owner=np.full(len(geometry.string),-1,int)
        self.tools=[]
        for i,segment in enumerate(geometry.string):
            if segment.tool_loss is None:
                continue
            tool=segment.tool_loss
            stop=i+tool.span_segments
            if stop>len(geometry.string) or np.any(self.tool_owner[i:stop]>=0):
                raise ValueError('tool spans must be contiguous, within the string and non-overlapping')
            self.tool_owner[i:stop]=len(self.tools)
            if tool.basis=='total_internal':
                self.replaced[i:stop]=True
            self.tools.append((i,stop,tool,sum(s.length for s in geometry.string[i:stop])))
        # Boundary local losses are assigned over the downstream bore piece,
        # or the upward annulus piece. Internal boundaries of a replaced tool
        # are excluded. Hole changes are included on the upward return path.
        self.boundaries=[]
        for j,boundary in enumerate(self.top[1:],1):
            left=geometry.at(np.array([boundary-1e-5]))
            right=geometry.at(np.array([boundary+1e-5]))
            il=int(geometry.segment_index(boundary-1e-5))
            ir=int(geometry.segment_index(boundary+1e-5))
            internal=(self.tool_owner[il]>=0 and self.tool_owner[il]==self.tool_owner[ir] and self.replaced[il] and self.replaced[ir])
            excluded_boundary=any(owner>=0 and not self.tools[owner][2].include_boundary_changes
                                  for owner in (self.tool_owner[il],self.tool_owner[ir]))
            for annulus in (False,True):
                if (internal or excluded_boundary) and not annulus:
                    continue
                area='A_ann' if annulus else 'A_bore'
                dh='Dh_ann' if annulus else 'Dh_bore'
                up,down=(right,left) if annulus else (left,right)
                a,b=float(up[area][0]),float(down[area][0])
                if a==b:
                    continue
                small_dh=float((up if a<=b else down)[dh][0])
                owner=j-1 if annulus else j
                self.boundaries.append((annulus,owner,a,b,small_dh,float(boundary)))
        for i,segment in enumerate(geometry.string):
            joint=segment.pipe.hydraulic_joint
            if joint is not None:
                for h in geometry.hole:
                    # Check the actual intersecting intervals below as well as
                    # the geometry's ordinary body-clearance check.
                    top=0 if i==0 else geometry._seg_ends[i-1]
                    bottom=geometry._seg_ends[i]
                    if top<h.md_bottom and bottom>h.md_top and joint.outer_diameter>=2*h.r_wall:
                        raise ValueError('hydraulic joint closes the annulus')

    def _at_geometry(self, z, temperature, pressure, mass_rate, fluid=None, annulus=False, geometry_z=None, guard=True):
        """Named gradients, properties and approximation flags at MD [m]."""
        from borethm import model1_coupled as m1
        zz=np.atleast_1d(z).astype(float)
        sample=zz if geometry_z is None else np.broadcast_to(geometry_z,zz.shape)
        temperature=np.broadcast_to(temperature,zz.shape)
        g=self.geometry.at(sample)
        p=np.broadcast_to(pressure,zz.shape)
        prop_p=np.maximum(p,PROPERTY_FLOOR) if guard else p
        rho,cp,mu,_=m1.fluid_props(np.clip(temperature,1,480),prop_p,fluid)
        rho,cp,mu=(np.broadcast_to(x,zz.shape) for x in (rho,cp,mu))
        tau=getattr(fluid,'yield_point',0.)
        area=g['A_ann' if annulus else 'A_bore']
        dh=g['Dh_ann' if annulus else 'Dh_bore']
        body,re,velocity=passage_gradient(rho,mu,tau,mass_rate,area,dh,annulus,self.friction)
        seg=self.geometry.segment_index(sample)
        piece=np.clip(np.searchsorted(self.bottom,sample,side='left'),0,len(self.bottom)-1)
        body=np.asarray(body).copy()
        if not annulus:
            body=np.where(self.replaced[seg],0.,body)
        terms={k:np.zeros_like(zz) for k in ('joint_replacement','joint_local','geometric_local','supplied_local','tool')}
        flags=[]
        for i,s in enumerate(self.geometry.string):
            mask=seg==i
            if not np.any(mask):
                continue
            joint=s.pipe.hydraulic_joint
            if joint is not None and (annulus or not self.replaced[i]):
                if annulus:
                    diameter=2*g['r_wall'][mask]
                    ja=np.pi*(diameter**2-joint.outer_diameter**2)/4
                    jd=diameter-joint.outer_diameter
                else:
                    ja=np.full(mask.sum(),np.pi*joint.bore_diameter**2/4)
                    jd=joint.bore_diameter
                inc,loc=joint_increment(rho[mask],mu[mask],tau,mass_rate,area[mask],dh[mask],ja,jd,joint.restriction_length,annulus,joint.transition,self.friction)
                terms['joint_replacement'][mask]=inc/joint.spacing
                terms['joint_local'][mask]=loc/joint.spacing
                if joint.transition=='abrupt':
                    small_dh=np.where(area[mask]<=ja,dh[mask],jd)
                    entry=local_change(area[mask],ja,rho[mask],mass_rate,mu[mask],small_dh)
                    exit_=local_change(ja,area[mask],rho[mask],mass_rate,mu[mask],small_dh)
                    if not np.all(entry[3] & exit_[3]):
                        flags.append('joint_local_outside_Newtonian_Re_domain')
                if annulus or tau>0:
                    flags.append('joint_local_annular_or_Bingham_approximation')
            if s.local_loss is not None and (annulus or not self.replaced[i]):
                spec=s.local_loss
                k=spec.annulus_coefficient if annulus else spec.bore_coefficient
                ref=spec.annulus_reference_area if annulus else spec.bore_reference_area
                a=area[mask] if ref is None else ref
                terms['supplied_local'][mask]=k*.5*rho[mask]*(mass_rate/(rho[mask]*a))**2/s.length
        if self.transitions=='abrupt':
            for ann,owner,a,b,small_dh,depth in self.boundaries:
                mask=(piece==owner)
                if ann!=annulus or not np.any(mask):
                    continue
                loss,k,r,valid=local_change(a,b,rho[mask],mass_rate,mu[mask],small_dh)
                terms['geometric_local'][mask]+=loss/self.length[owner]
                if not np.all(valid):
                    flags.append('local_change_outside_Newtonian_Re_domain')
                if annulus or tau>0:
                    flags.append('local_change_annular_or_Bingham_approximation')
        if not annulus:
            for i,stop,tool,length in self.tools:
                mask=(seg>=i)&(seg<stop)
                flow=mass_rate/rho[mask]
                terms['tool'][mask]=tool.pressure(rho[mask],flow)/length
                if np.any(mask):
                    flags.append('supplied_tool_loss_treated_as_dissipation')
                    if tool.unresolved:
                        flags.append('internal_tool_loss_unknown')
                if tool.flow_range is not None and np.any((flow<tool.flow_range[0])|(flow>tool.flow_range[1])):
                    flags.append('tool_flow_outside_published_range')
                if tool.temperature_max_C is not None and np.any(np.asarray(temperature)[mask]>tool.temperature_max_C):
                    flags.append('tool_temperature_outside_published_rating')
        total=body+sum(terms.values())
        if np.any(total < -1e-8):
            raise ValueError('negative total passage dissipation')
        return dict(body=body,**terms,total=total,rho=rho,cp=cp,mu=mu,re=re,velocity=velocity,
                    property_pressure=prop_p,guard_active=p<prop_p,flags=sorted(set(flags)))

    def gradients(self,z,temperature,pressure,mass_rate,fluid=None,annulus=False,guard=True,blend=True):
        """Shared gradients with the existing geometry-blend width.

        Convolve piece occupancy with a unit-area box of width BLEND.
        Weights remain non-negative and sum to one even for short tools.
        Pressure and thermal source assignment use these identical weights.
        """
        from borethm import model1_coupled as m1
        zz=np.atleast_1d(z).astype(float)
        temp=np.broadcast_to(temperature,zz.shape)
        p=np.broadcast_to(pressure,zz.shape)
        out=self._at_geometry(zz,temp,p,mass_rate,fluid,annulus,guard=guard)
        if not blend or len(self.top)==1:
            return out
        width=min(m1.BLEND,self.geometry.md_bit)
        near=np.zeros(zz.shape,bool)
        for b in self.top[1:]:
            near|=np.abs(zz-b)<width/2
        if not np.any(near):
            return out
        names=('body','joint_replacement','joint_local','geometric_local','supplied_local','tool','total','re','velocity')
        for key in names:
            out[key][near]=0.
        for i,(a,b) in enumerate(zip(self.top,self.bottom)):
            # Reflect at the well ends. This preserves each component's
            # integral even when a bit/tool is shorter than half the blend.
            L=self.geometry.md_bit
            weight=np.zeros_like(zz)
            for lo,hi in ((a,b),(-b,-a),(2*L-b,2*L-a)):
                weight+=np.maximum(0.,np.minimum(zz+width/2,hi)-np.maximum(zz-width/2,lo))/width
            mask=near & (weight>0)
            if not np.any(mask):
                continue
            value=self._at_geometry(zz[mask],temp[mask],p[mask],mass_rate,fluid,annulus,
                                    np.full(mask.sum(),(a+b)/2),guard)
            for key in names:
                out[key][mask]+=weight[mask]*value[key]
            out['flags'].extend(value['flags'])
        out['flags']=sorted(set(out['flags']+['hydraulic_geometry_blend']))
        return out

    def integration_grid(self,result=None):
        from borethm import model1_coupled as m1
        L=self.geometry.md_bit
        half_width=min(m1.BLEND,L)/2
        edges=np.r_[self.top,self.bottom,-self.top,-self.bottom,2*L-self.top,2*L-self.bottom]
        cuts=[self.top,self.bottom,np.clip(edges-half_width,0,L),np.clip(edges+half_width,0,L)]
        if result is not None:
            cuts.append(np.asarray(result['z']))
        cuts.append(np.asarray(self.geometry.survey.md))
        cuts=np.unique(np.concatenate(cuts))
        cuts=cuts[(cuts>=0)&(cuts<=self.geometry.md_bit)]
        x,w=np.polynomial.legendre.leggauss(8)
        half=np.diff(cuts)/2
        z=((cuts[:-1]+cuts[1:])[:,None]/2+half[:,None]*x).ravel()
        weights=(half[:,None]*w).ravel()
        return z,weights


def check_legacy(geometry,surface,transitions):
    if surface is not None or transitions!='abrupt' or any(s.pipe.hydraulic_joint is not None or s.local_loss is not None or s.tool_loss is not None for s in geometry.string):
        raise ValueError('v1.5.0 mode rejects new hydraulic loss settings')


def heat_gradients(model,z,td,tu,mass_rate,fluid=None,P_surface=1e5):
    """Applied bore/down and annulus/up temperature gradients [K/m]."""
    from borethm import model1_coupled as m1
    p=m1.P_of_z(model.geometry.survey.tvd(z),P_surface)
    bore=model.gradients(z,td,p,mass_rate,fluid)
    ann=model.gradients(z,tu,p,mass_rate,fluid,True)
    # Retain the circulation equation's enthalpy heat capacities. Only the
    # friction kernel's liquid density/viscosity use the shared pressure guard.
    return (bore['total']/bore['rho']/m1._cp(td,p,fluid),
            -ann['total']/ann['rho']/m1._cp(tu,p,fluid))


def energy_check(model,result,fluid,Q_face,tfa,P_surface):
    """Compare assigned dissipation with applied equation sources [W].

    Integrate each named pressure term times its own local volumetric flow.
    Surface and density-column terms do not enter this balance. Compare to
    the applied temperature source times m*cp and the solved turnaround jump.
    """
    from borethm import model1_coupled as m1
    z,w=model.integration_grid(result)
    td=np.interp(z,result['z'],result['Td'])
    tu=np.interp(z,result['z'],result['Tu'])
    p=m1.P_of_z(model.geometry.survey.tvd(z),P_surface)
    b=model.gradients(z,td,p,result['m_dot'],fluid)
    a=model.gradients(z,tu,p,result['m_dot'],fluid,True)
    keys=('body','joint_replacement','joint_local','geometric_local','supplied_local','tool')
    assigned={side:{key:float(np.sum(val[key]*result['m_dot']/val['rho']*w)) for key in keys}
              for side,val in (('bore',b),('annulus',a))}
    bit_p=m1.P_of_z(model.geometry.survey.tvd(model.geometry.md_bit),P_surface)
    rho_bit=float(m1.fluid_props(np.array([result['Td'][-1]]),np.array([max(bit_p,PROPERTY_FLOOR)]),fluid)[0][0])
    nozzle_W=float(m1.nozzle_dp(result['m_dot'],rho_bit,tfa)*result['m_dot']/rho_bit)
    total=sum(sum(v.values()) for v in assigned.values())+nozzle_W+Q_face
    hd,hu=heat_gradients(model,z,td,tu,result['m_dot'],fluid,P_surface)
    bore_applied=float(np.sum(result['m_dot']*m1._cp(td,p,fluid)*hd*w))
    ann_applied=float(np.sum(-result['m_dot']*m1._cp(tu,p,fluid)*hu*w))
    cp_bit=float(m1._cp(np.array([result['Td'][-1]]),np.array([bit_p]),fluid)[0])
    turnaround=float(result['m_dot']*cp_bit*(result['Tu'][-1]-result['Td'][-1]))
    applied=bore_applied+ann_applied+turnaround
    residual=applied-total
    tolerance=max(1.,.001*max(abs(total),abs(applied)))
    passed=bool(math.isfinite(residual) and math.isfinite(tolerance) and abs(residual)<=tolerance)
    return dict(enabled=True,assigned_terms_W=assigned,nozzle_W=nozzle_W,face_W=Q_face,
                assigned_W=total,applied_bore_W=bore_applied,applied_annulus_W=ann_applied,
                applied_turnaround_W=turnaround,applied_W=applied,residual_W=residual,
                relative_residual=residual/max(abs(total),1.),tolerance_W=tolerance,
                passed=passed,flagged=not passed,
                status='within reporting resolution' if passed else 'power residual flagged',
                surface_W_in_hole=0.,density_column_W=0.)


def hydraulics(mass_rate, geometry, result=None, T_avg=80., tfa=7.759e-4,
               friction='blasius', bit=True, fluid=None, P_surface=1e5,
               surface=None, transitions='abrupt', guard=True):
    """Standpipe budget using the same local gradients as circulation heat."""
    from borethm import model1_coupled as m1
    _finite(mass_rate,'mass flow',True)
    if surface is not None and not isinstance(surface,SurfaceLoss):
        raise TypeError('surface must be SurfaceLoss or None')
    model=LossModel(geometry,friction,transitions)
    top,bot=model.top,model.bottom
    mid,weights=model.integration_grid(result)
    if result is None:
        tb=ta=np.full_like(mid,T_avg)
        p=np.full_like(mid,m1.P_of_z(geometry.survey.tvd(geometry.md_bit/2),P_surface))
    else:
        tb=np.interp(mid,result['z'],result['Td'])
        ta=np.interp(mid,result['z'],result['Tu'])
        p=m1.P_of_z(geometry.survey.tvd(mid),P_surface)
    bore=model.gradients(mid,tb,p,mass_rate,fluid,guard=guard)
    ann=model.gradients(mid,ta,p,mass_rate,fluid,True,guard=guard)
    lengths=weights
    bit_t=T_avg if result is None else float(result['Td'][-1])
    bit_p=m1.P_of_z(geometry.survey.tvd(geometry.md_bit),P_surface) if result is not None else float(p[0])
    rho_bit=float(m1.fluid_props(np.array([bit_t]),np.array([max(bit_p,PROPERTY_FLOOR) if guard else bit_p]),fluid)[0][0])
    dp_bit=float(m1.nozzle_dp(mass_rate,rho_bit,tfa)) if bit else 0.
    # The survey is linear between stations; cuts include those stations.
    eps=1e-4
    slope=(geometry.survey.tvd(mid+eps)-geometry.survey.tvd(mid-eps))/(2*eps)
    dp_buoy=float(np.sum((ann['rho']-bore['rho'])*m1.G_GRAV*slope*weights))
    tin=T_avg if result is None else float(result['Td'][0])
    rho_in=float(m1.fluid_props(np.array([tin]),np.array([P_surface]),fluid)[0][0])
    dp_surface=0. if surface is None else float(surface.pressure(rho_in,mass_rate/rho_in))
    dpb=bore['total']*weights
    dpa=ann['total']*weights
    spp=float(dpb.sum()+dpa.sum())+dp_bit+dp_buoy+dp_surface
    names=('body','joint_replacement','joint_local','geometric_local','supplied_local','tool')
    totals={side:{key:float(np.sum(values[key]*lengths)) for key in names} for side,values in (('bore',bore),('annulus',ann))}
    pieces=[]
    for j,(a,b) in enumerate(zip(top,bot)):
        mask=(mid>=a)&(mid<b)
        def regime(re):
            from borethm import fluids
            lam=(re<=fluids.RE_CRITICAL) if getattr(fluid,'yield_point',0)>0 else (re<2300.)
            return 'laminar' if np.all(lam) else ('turbulent' if not np.any(lam) else 'mixed')
        pieces.append(dict(md_top=float(a),md_bottom=float(b),dp_bore=float(dpb[mask].sum()),dp_ann=float(dpa[mask].sum()),v_ann=float(ann['velocity'][mask].min()),
            bore_terms={key:float(np.sum(bore[key][mask]*weights[mask])) for key in names},annulus_terms={key:float(np.sum(ann[key][mask]*weights[mask])) for key in names},
            bore_Re=float(np.min(bore['re'][mask])),annulus_Re=float(np.min(ann['re'][mask])),
            actual_property_profile_pressure=float(np.mean(p[mask])),
            property_pressure=float(np.mean(bore['property_pressure'][mask])),guard_active=bool(np.any(bore['guard_active'][mask])),
            bore_regime=regime(bore['re'][mask]),annulus_regime=regime(ann['re'][mask])))
    # Save the cumulative annulus integral for partial-depth pressure queries.
    cumulative_z=np.r_[0.,mid,geometry.md_bit]
    cumulative_dp=np.r_[0.,np.cumsum(dpa)-dpa/2,float(dpa.sum())]
    return dict(pieces=pieces,dp_string=float(dpb.sum()),dp_annulus=float(dpa.sum()),dp_bit=dp_bit,dp_buoyancy=dp_buoy,
        dp_surface=dp_surface,spp=spp,over_pump_limit=spp>m1.PUMP_LIMIT,v_ann_min=float(ann['velocity'].min()),
        cleans_hole=float(ann['velocity'].min())>=m1.HOLE_CLEANING_V,pump_power=spp*mass_rate/rho_in,
        terms=totals,hydraulics_model='v1.6.0',property_guard_Pa=PROPERTY_FLOOR if guard else None,
        flags=sorted(set(bore['flags']+ann['flags'])),
        annulus_profile=dict(md=cumulative_z,dp=cumulative_dp),geometry_blend_m=m1.BLEND,
        local_events=[dict(conduit='annulus' if ann else 'bore',depth_m=depth,
            support_top_m=float(model.top[owner]),support_bottom_m=float(model.bottom[owner]),area_up_m2=a,area_down_m2=b,
            source='Idelchik sudden-change geometry estimate; numerical blend applied') for ann,owner,a,b,dh,depth in model.boundaries],
        sources=[s.pipe.source for s in geometry.string]+[s.local_loss.source for s in geometry.string if s.local_loss is not None]+
            [s.pipe.hydraulic_joint.source for s in geometry.string if s.pipe.hydraulic_joint is not None]+
            [s.tool_loss.source for s in geometry.string if s.tool_loss is not None]+([surface.source] if surface else []))
