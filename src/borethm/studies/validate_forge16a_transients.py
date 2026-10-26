"""FORGE 16A conditional transient comparison with unchanged v1.5.0 models.

The local history follows the 16B pauses study. Earlier observed circulation
is one preconditioning spell because earlier string depths/assemblies are
unresolved. Run-in comparisons are partial, initially observed legs, not
blind surface-to-bottom trip predictions. No sensor-transfer model is added.
"""
import argparse
import bisect
import json
import math
import statistics as st
import time
from pathlib import Path

import numpy as np
import borethm as bt
from borethm import tool_thermal as tt, wall_thermal as wt
from borethm.studies import validate_forge16a as v

# Set by the explicit-output CLI before preparing or running a study.
ROOT=S1=PRIMARY=None


def read_csv(path):
    import csv
    with Path(path).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))


def snapshot(folder):
    return {p.relative_to(folder).as_posix():v.digest(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def record(run):
    rr=v.read(f'sanvean_BHA{run}_10s.csv')
    for r in rr:r['epoch']=v.epoch(r['time'])
    return rr


def off(r):
    return (v.number(r['flow_gpm_count'])==v.number(r['raw_count']) and v.number(r['raw_count'],0)>0
            and 0<=v.number(r['minimum_flow_gpm']) and v.number(r['maximum_flow_gpm'])<=100)


def pumping(r):
    return (v.number(r['flow_gpm_count'])==v.number(r['raw_count']) and v.number(r['raw_count'],0)>0
            and 100<v.number(r['flow_gpm'])<=2000 and np.isfinite(v.number(r['bit_depth_ft'])))


def prepare():
    if (ROOT/'plan.json').exists():raise FileExistsError('Frozen S2 plan exists')
    inventory=read_csv(ROOT/'observed-off-spells.csv')
    events=[];excluded=[]
    for run in v.RUNS:
        rr=record(run)
        for raw in (r for r in inventory if r['run']==run):
            r={k:(raw[k] if k in ('run','spell_id','start','end_last_bin','first_temperature_time','last_temperature_time') else float(raw[k])) for k in raw}
            i,j=int(r['start_i']),int(r['end_i'])
            local=rr[i:j+1]
            sensed=[x for x in local if v.number(x['bit_box_C_count'],0)>0]
            if not sensed:excluded.append(dict(event_id=r['spell_id'],reason='no bit-box temperature'));continue
            complete=(r['temperature_coverage_fraction']>=.8 and sensed[0]['epoch']-local[0]['epoch']<=20
                      and local[-1]['epoch']-sensed[-1]['epoch']<=20)
            static=(r['near_bottom_fraction']>=.9 and r['depth_max_ft']-r['depth_min_ft']<=100)
            descending=(r['net_down_ft']>=500 and r['upward_motion_ft']<=.1*r['downward_motion_ft'])
            prior=[x for x in rr[max(0,i-30):i] if pumping(x)]
            if static and complete and len(prior)>=6:
                kind='pause'
            elif descending and complete:
                kind='run-in leg'
            else:
                excluded.append(dict(event_id=r['spell_id'],reason='not stationary near bottom or clear descending leg with endpoint/temperature coverage and prior circulation'))
                continue
            events.append(dict(**r,event_id=r['spell_id'],kind=kind,
                observed_initial_C=v.number(sensed[0]['bit_box_C']),observed_end_C=v.number(sensed[-1]['bit_box_C']),
                observed_peak_C=max(v.number(x['bit_box_C']) for x in sensed),
                instantaneous_source_peak_C=max(v.number(x['bit_box_C_max'],v.number(x['bit_box_C'])) for x in sensed),
                washout=run in ('35r1','35r2')))
    events.sort(key=lambda e:(e['start'],e['run']))
    plan=dict(prepared_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
         baseline=PRIMARY['baseline'],S1_snapshot=snapshot(S1),diagnostics_snapshot=snapshot(ROOT.parent/'diagnostics'),
         primary_source_hashes=PRIMARY['source_hashes'],calculation_hashes=PRIMARY['calculation_hashes'],
         study_sha256=v.digest(v.__file__),script_sha256=v.digest(__file__),inventory_sha256=v.digest(ROOT/'observed-off-spells.csv'),
         events=events,excluded=excluded,
         method=dict(selection='Complete valid 10-second flow bins, maximum <=100 gpm, spells >=60 s; gaps >20 s break a spell. Temperature coverage >=80%, first/last temperature within 20 s of endpoints. Pause: >=90% bins within 100 ft of bottom and bit range <=100 ft, with >=60 s known pumping in preceding 5 min. Run-in leg: net descent >=500 ft, upward motion <=10% of downward motion. All eligible events included.',
             boundary_profiles='Local pumping >100 gpm, grouping contiguous identical circulation/string-in flags at each depth. Mean input per spell, bit rounded up to 200 ft, flow to 25 gpm, inlet to 2 F, motor DP to 50 psi, clock to 30 min; rounding declared before prediction. Existing primary cumulative exposure only; no recovery feedback into circulating profiles. Every boundary solve is a new S2 input calculation, not a rerun of S1 sample scoring.',
             earlier_history='For each wall depth, earlier rig-record circulation is one conditioning spell using the first available local circulation boundary at that depth; if this boundary is later than the event it is explicitly recorded. The immediately preceding rig pumps-off period is added to the initial history. This conditional initial-state approximation follows the 16B pre-record method; unobserved previous string states are not reconstructed.',
             local_history='From first reach/current run start to event time, use each local pumping/static spell with actual durations. Static string occupancy uses median bit depth in that spell. Unknown flow is reported and treated as static; missing time is a static interval. The separate wall model allows recovery, but its wall state is not passed back into circulation.',
             wall='wall_temperatures with n=120, growth=1.2, measured formation and 16B rock properties. Well-mixed fluid node with laminar Nu=4.36 primary, no-node (C=0, wall temperature) sensitivity. As in the 16B pauses study, casing/cement layers are not resolved by the radial solver; casing ID is its inner rock radius.',
             pause='Two positions: bit and 40 ft above. Wall/static-fluid history through pause feeds existing two-node tool model; tool starts at preceding circulation Td with steady steel temperature. Compare both steel and internal-fluid nodes to unresolved bit-box medium. Absolute curves plus temperature rises relative to first observation time; observed 10-second means at bin centres.',
             run_in='Each observed leg is conditional on its first measured temperature, setting both tool nodes to that value. Freeze the modelled fluid column at leg start, following the existing fixed-column trip treatment; solve wall points every <=200 ft over the leg. tool_trip_in uses net endpoint depth/time as mean speed, measured initial T0, no pumping stages inside the selected fully off leg. Depth-origin translation permits a partial leg. Compare at bit and 40 ft above, steel and internal-fluid nodes. Average-speed timing and fixed-column limitations are retained, not corrected by a new model.',
             inlet='The rig mud channel is outlet-like. Use the last drilled depth at the start of a local circulation spell and the S1 mud log at that depth for inlet; no inverse-inlet or recovery-diagnostic correction. Earlier conditioning uses first available local input boundary. Sensor location remains unresolved.',
             outputs='Time series, measured/modelled 10-second-mean peaks and rises, timing/depth coverage, model-node/position alternatives, final solver failures. No selecting the better node, event or static treatment after errors. Figures: the longest eligible pause and longest run-in leg per run, selected by duration before prediction.'))
    v.dump(ROOT/'plan.json',plan);(ROOT/'plan.sha256').write_text(v.digest(ROOT/'plan.json')+'\n')
    v.csv_out(ROOT/'events.csv',events);v.csv_out(ROOT/'excluded-spells.csv',excluded)
    (ROOT/'execution-source.py').write_bytes(Path(__file__).read_bytes())
    print('Frozen S2 events',len(events),'pauses',sum(e['kind']=='pause' for e in events),'run-in legs',sum(e['kind']=='run-in leg' for e in events))


class Study:
    def __init__(self):
        self.plan=json.loads((ROOT/'plan.json').read_text())
        assert v.digest(ROOT/'plan.json')==(ROOT/'plan.sha256').read_text().strip()
        permitted=[self.plan['script_sha256']]
        if (ROOT/'runner-revision.json').exists():
            permitted.append(json.loads((ROOT/'runner-revision.json').read_text())['revised_script_sha256'])
        assert v.digest(__file__) in permitted
        assert snapshot(S1)==self.plan['S1_snapshot']
        assert snapshot(ROOT.parent/'diagnostics')==self.plan['diagnostics_snapshot']
        self.records={run:record(run) for run in v.RUNS}
        self.path=v.survey();self.form=v.formation('216',self.path)[0]
        self.mudlog=v.mudlog()
        cr=v.read('rig_history_1min.csv')
        self.rig_times=np.array([v.epoch(r['time']) for r in cr])
        self.rig_circ=np.cumsum([v.number(r['circulating_fraction'],0)*60 for r in cr])
        dep=[];last=0.
        for r in cr:last=max(last,v.number(r['hole_depth_ft'],last));dep.append(last*v.FT)
        self.rig_depth=np.array(dep)
        self.rig_pumping=np.array([v.number(r['circulating_fraction'],0)>0 for r in cr])
        self.profiles={};self.walls={};self.geometries={}
        self.inputs={r['run']:r for r in PRIMARY['mud_and_nozzles']}
        (ROOT/'profiles').mkdir(exist_ok=True);(ROOT/'series').mkdir(exist_ok=True)

    def fluid(self,run):
        p=self.inputs[run]
        return v.Mud(p['mud_weight_ppg']*119.8264273,pv_ref=p['pv_cP']*.001,yield_point=p['yp_lbf_100ft2']*.4788025898)

    def geometry(self,run,bit):
        bit=max(float(bit),1.)
        key=run,bit
        if key not in self.geometries:
            # Preserve the reported bottom-up component order where part of
            # the listed string is still above surface during running in.
            full=v.geometry(run,max(bit,6000.),PRIMARY['components'])
            cut=full.md_bit-bit*v.FT;top=0.;segs=[]
            for seg in full.string:
                end=top+seg.length
                if end>cut:segs.append(v.wg.StringSegment(end-max(top,cut),seg.pipe))
                top=end
            holes=[v.wg.HoleInterval(h.md_top,min(h.md_bottom,bit*v.FT+1e-6),h.r_wall,h.layers)
                   for h in full.hole if h.md_top<bit*v.FT]
            self.geometries[key]=v.wg.WellGeometry(segs,holes,self.path)
        return self.geometries[key]

    def profile(self,run,rows):
        mean=lambda k:float(np.mean([v.number(r[k],0) for r in rows]))
        bit=math.ceil(mean('bit_depth_ft')/200)*200
        q=max(100.,round(mean('flow_gpm')/25)*25)
        h=mean('hole_depth_ft')
        tinF=round(float(np.interp(h,*self.mudlog['temp_in_F']))/2)*2
        dp=max(0.,round(mean('motor_differential_psi')/50)*50)
        epoch=round(rows[0]['epoch']/1800)*1800
        key=run,bit,q,tinF,dp,epoch
        identity=__import__('hashlib').sha256(json.dumps(key).encode()).hexdigest()[:20]
        dest=ROOT/'profiles'/f'{identity}.json'
        if key not in self.profiles:
            if dest.exists():r=json.loads(dest.read_text())
            else:
                began=time.perf_counter();r=dict(key=key,profile_id=identity,success=False)
                try:
                    g=self.geometry(run,bit);fluid=self.fluid(run);tin=(tinF-32)/1.8
                    rho=float(v.m1.fluid_props(np.array([tin]),np.array([v.m1.P_SURF]),fluid)[0][0]);Q=q*v.GPM
                    now=float(np.interp(epoch,self.rig_times,self.rig_circ))
                    ex=v.m1.smooth_exposure(v.m1.exposure_from_history(self.rig_circ,self.rig_depth,now),g.md_bit)
                    sol=v.m1.solve_seeded(ex,v.m1.exposure_breaks(ex,g.md_bit),m_dot=Q*rho,T_inj=tin,geotherm=self.form,
                         geometry=g,target_rock_T=float(self.form(self.path.tvd(g.md_bit))),Q_face=dp*v.PSI*Q,
                         k_rock=v.K_ROCK,rhocp_rock=v.RHOCP_ROCK,friction_heat=True,tfa=self.inputs[run]['tfa_m2'],
                         film_mult=1.,fluid=fluid,verbose=False)
                    ga=g.at(np.clip(sol['z'],.01,g.md_bit-.01))
                    ha=v.m1.h_dittus(sol['m_dot'],ga['A_ann'],ga['Dh_ann'],sol['Tu'],v.m1.P_of_z(ga['tvd']),fluid=fluid)
                    hb=v.m1.h_dittus(sol['m_dot'],ga['A_bore'],ga['Dh_bore'],sol['Td'],v.m1.P_of_z(ga['tvd']),fluid=fluid)
                    r.update(success=bool(sol['success']),solver_status=int(sol['sol'].status),solver_message=str(sol['sol'].message),
                             seed_success=bool(sol['seed']['success']) if sol['seed'] else None,
                             z=sol['z'].tolist(),Td=sol['Td'].tolist(),Tu=sol['Tu'].tolist(),h_ann=ha.tolist(),h_bore=hb.tolist())
                    if not all(np.all(np.isfinite(r[field])) for field in ('z','Td','Tu','h_ann','h_bore')):
                        r.update(success=False,exception='Non-finite circulation boundary array')
                        for field in ('z','Td','Tu','h_ann','h_bore'):
                            r[field]=[x if math.isfinite(x) else None for x in r[field]]
                except Exception as err:r['exception']=f'{type(err).__name__}: {err}'
                r['duration_s']=time.perf_counter()-began;v.dump(dest,r)
                print('profile',identity,run,bit,q,r['success'],round(r['duration_s'],2),flush=True)
            self.profiles[key]=r
        r=self.profiles[key]
        if not r['success']:raise RuntimeError('Circulation boundary failed: '+identity)
        return r

    def at(self,profile,z,field):return float(np.interp(z,profile['z'],profile[field]))

    def static(self,run,z,bit,fluid):
        radius=8.835*v.INCH/2 if z<5110*v.FT else 8.75*v.INCH/2
        string=0.
        if bit*v.FT>=z:
            string=float(self.geometry(run,bit).at(np.array([z]))['r_out'][0])
        rock=float(self.form(self.path.tvd(z)))
        rho,cp,_,k=[float(x[0]) for x in v.m1.fluid_props(np.array([rock]),v.m1.P_of_z(np.array([self.path.tvd(z)])),fluid)]
        return rho*cp*math.pi*(radius**2-string**2),wt.NU_LAMINAR*k/(2*(radius-string)),radius

    def wall(self,run,z,end,node):
        key=run,round(z,6),end,node
        if key in self.walls:return self.walls[key]
        rr=self.records[run];ts=np.array([r['epoch'] for r in rr]);stop=int(np.searchsorted(ts,end,side='left'))
        rr=rr[:stop];fluid=self.fluid(run);states=[];notes=[];elapsed=0.
        if not rr:raise ValueError('No local wall history')
        initial_t=rr[0]['epoch']
        now=float(np.interp(initial_t,self.rig_times,self.rig_circ))
        exposure=v.m1.exposure_from_history(self.rig_circ,self.rig_depth,now)
        pre=max(0.,float(exposure(z)))
        if pre>0:
            available=[r for r in self.records[run] if pumping(r) and v.number(r['bit_depth_ft'])*v.FT>=z]
            if not available:raise ValueError('No local conditioning boundary at wall depth')
            first=available[0];prof=self.profile(run,[first])
            states.append(wt.State('circulating',pre,T_fluid=self.at(prof,z,'Tu'),h=self.at(prof,z,'h_ann')))
            elapsed+=pre
            notes.append(dict(kind='preconditioning',duration_s=pre,profile=prof['profile_id'],later_boundary=first['epoch']>=end))
            j=int(np.searchsorted(self.rig_times,initial_t,side='right'))
            on=np.flatnonzero(self.rig_pumping[:j])
            gap=max(0.,initial_t-(self.rig_times[on[-1]]+60)) if len(on) else 0.
            if gap:
                cap,hs,a=self.static(run,z,0,fluid)
                states.append(wt.State('static',gap,h=hs,C=cap if node else 0));elapsed+=gap
                notes.append(dict(kind='pre-record static, string position unresolved; absent assumed',duration_s=gap))
            i=0
        else:
            i=next((j for j,r in enumerate(rr) if v.number(r['hole_depth_ft'],0)*v.FT>=z),len(rr))
        while i<len(rr):
            if v.number(rr[i]['hole_depth_ft'],0)*v.FT<z:i+=1;continue
            c=pumping(rr[i]) and v.number(rr[i]['bit_depth_ft'])*v.FT>=z
            inside=v.number(rr[i]['bit_depth_ft'],0)*v.FT>=z
            j=i
            while j+1<len(rr) and rr[j+1]['epoch']-rr[j]['epoch']<=20:
                cc=pumping(rr[j+1]) and v.number(rr[j+1]['bit_depth_ft'])*v.FT>=z
                inn=v.number(rr[j+1]['bit_depth_ft'],0)*v.FT>=z
                if cc!=c or (not c and inn!=inside):break
                j+=1
            group=rr[i:j+1];duration=min(end,rr[j]['epoch']+10)-rr[i]['epoch']
            if duration<=0:break
            if c:
                prof=self.profile(run,group)
                states.append(wt.State('circulating',duration,T_fluid=self.at(prof,z,'Tu'),h=self.at(prof,z,'h_ann')))
                notes.append(dict(kind='circulating',duration_s=duration,profile=prof['profile_id']))
            else:
                bit=float(np.median([v.number(r['bit_depth_ft'],0) for r in group]))
                cap,hs,a=self.static(run,z,bit,fluid)
                states.append(wt.State('static',duration,h=hs,C=cap if node else 0.))
                notes.append(dict(kind='static',duration_s=duration,string_in=inside,
                                  unknown_flow_bins=sum(v.number(r['flow_gpm_count'])<v.number(r['raw_count']) for r in group)))
            elapsed+=duration
            if j+1<len(rr) and rr[j+1]['epoch']>rr[j]['epoch']+10:
                gap=rr[j+1]['epoch']-rr[j]['epoch']-10
                cap,hs,a=self.static(run,z,0,fluid)
                states.append(wt.State('static',gap,h=hs,C=cap if node else 0.));elapsed+=gap
                notes.append(dict(kind='unobserved gap, static/absent assumed',duration_s=gap))
            i=j+1
        if not states:raise ValueError('Empty wall history')
        a=8.835*v.INCH/2 if z<5110*v.FT else 8.75*v.INCH/2
        result=bt.wall_temperatures(states,float(self.form(self.path.tvd(z))),a,v.K_ROCK,v.RHOCP_ROCK,n=120,growth=1.2)
        offset=end-elapsed
        value=result.T_node if node else result.T_wall
        # During circulation the boundary fluid temperature is the local Tu;
        # the node trace is NaN because it is prescribed, not integrated.
        value=value.copy();before=0.
        for state in states:
            after=before+state.duration
            if state.kind=='circulating':value[(result.t>before)&(result.t<=after+1e-6)]=state.T_fluid
            before=after
        if not np.isfinite(value[-1]):value[-1]=result.ends[-1][1]
        out=dict(t=result.t+offset,T=value,notes=notes,wall=result.T_wall)
        self.walls[key]=out
        return out

    def run_event(self,event):
        dest=ROOT/'series'/f'{event["event_id"]}.json'
        if dest.exists():return
        began=time.perf_counter();run=event['run'];rr=self.records[run]
        i,j=int(event['start_i']),int(event['end_i']);local=rr[i:j+1]
        sensed=[r for r in local if v.number(r['bit_box_C_count'],0)>0]
        start=local[0]['epoch'];end=local[-1]['epoch']+10
        obs_t=np.array([r['epoch']+5-start for r in sensed]);obs=np.array([v.number(r['bit_box_C']) for r in sensed])
        out=dict(event_id=event['event_id'],run=run,kind=event['kind'],success=False,observed_t_s=obs_t.tolist(),observed_C=obs.tolist(),alternatives=[])
        try:
            for node in (True,False):
                for above in (0,40):
                    fluid=self.fluid(run)
                    if event['kind']=='pause':
                        bit=st.median(v.number(r['bit_depth_ft']) for r in local);z=(bit-above)*v.FT
                        prior=[r for r in rr[max(0,i-30):i] if pumping(r)]
                        prof=self.profile(run,prior)
                        wall=self.wall(run,z,end,node)
                        Tout=lambda t:float(np.interp(start+t,wall['t'],wall['T']))
                        ga=self.geometry(run,bit).at(np.array([z]));Tflow=self.at(prof,z,'Td');Tann=self.at(prof,z,'Tu')
                        rho,cp,_,k=[float(x[0]) for x in v.m1.fluid_props(np.array([Tflow]),v.m1.P_of_z(ga['tvd']),fluid)]
                        lump=bt.ToolLump.of_pipe(float(ga['r_bore'][0]),float(ga['r_out'][0]),rho*cp)
                        _,hsout,_=self.static(run,z,bit,fluid);hsin=wt.NU_LAMINAR*k/lump.D_in
                        Ts0=tt.steady_steel(Tflow,Tann,self.at(prof,z,'h_bore'),self.at(prof,z,'h_ann'),lump)
                        hist=tt.run(lump,[tt.Segment(end-start,Tout,hsout,hsin)],Ts0,Tflow,dt=5.)
                        model_t=hist.t;notes=wall['notes']
                    else:
                        md0=v.number(sensed[0]['bit_depth_ft'])-above;md1=v.number(sensed[-1]['bit_depth_ft'])-above
                        duration=sensed[-1]['epoch']-sensed[0]['epoch']
                        depths=np.linspace(md0*v.FT,md1*v.FT,max(2,int(np.ceil((md1-md0)/200))+1))
                        column=[];notes=[]
                        for z in depths:
                            wall=self.wall(run,float(z),start,node)
                            column.append(float(wall['T'][-1]));notes.extend(wall['notes'])
                        T0=float(obs[0]);g=self.geometry(run,v.number(sensed[-1]['bit_depth_ft']));ga=g.at(np.array([depths[-1]]))
                        rho,cp,_,k=[float(x[0]) for x in v.m1.fluid_props(np.array([T0]),v.m1.P_of_z(ga['tvd']),fluid)]
                        lump=bt.ToolLump.of_pipe(float(ga['r_bore'][0]),float(ga['r_out'][0]),rho*cp)
                        _,hsout,_=self.static(run,float(depths[-1]),v.number(sensed[-1]['bit_depth_ft']),fluid)
                        hsin=wt.NU_LAMINAR*k/lump.D_in
                        col=lambda x:float(np.interp(x+depths[0],depths,column))
                        hist,travel=bt.tool_trip_in(lump,col,float(depths[-1]-depths[0]),float((depths[-1]-depths[0])/duration),T0,hsout,hsin,dt=10.)
                        model_t=hist.t+obs_t[0]
                    for medium,array in (('internal fluid',hist.T_f),('steel',hist.T_s)):
                        predicted=np.interp(obs_t,model_t,array)
                        if not (np.all(np.isfinite(array)) and np.all(np.isfinite(predicted))):
                            out['numerical_issue']=dict(static_treatment='fluid node' if node else 'no node',
                                above_bit_ft=above,tool_quantity=medium,
                                nonfinite_indices=np.flatnonzero(~np.isfinite(array)).tolist())
                            raise RuntimeError('Non-finite tool-temperature history; excluded without altering inputs')
                        out['alternatives'].append(dict(static_treatment='fluid node' if node else 'no node',above_bit_ft=above,
                            tool_quantity=medium,t_s=model_t.tolist(),temperature_C=array.tolist(),
                            predicted_at_observation_C=predicted.tolist(),history_notes=notes))
            out['success']=True
        except Exception as err:out['exception']=f'{type(err).__name__}: {err}'
        out['duration_s']=time.perf_counter()-began;v.dump(dest,out)
        print('event',event['event_id'],event['kind'],out['success'],round(out['duration_s'],2),out.get('exception',''),flush=True)

    def run(self):
        for event in self.plan['events']:self.run_event(event)


def main():
    """Prepare or execute a fresh comparison, preserving archived evidence."""
    global ROOT,S1,PRIMARY
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('inventory','prepare','run'))
    p.add_argument('--output',type=Path,required=True,help='Study root containing s1/plan.json; writes s2/ beneath it')
    p.add_argument('--data',type=Path,default=v.DATA,help='External validation/forge16a archive (required outside a checkout)')
    a=p.parse_args()
    v.DATA=v.require_path(a.data, 'FORGE 16A archive; use --data').resolve()
    ROOT=a.output.resolve()/'s2'
    S1=a.output.resolve()/'s1'
    ROOT.mkdir(parents=True,exist_ok=True)
    from borethm.studies.forge16a_inventory import write_inventory
    if a.action=='inventory':
        write_inventory(ROOT)
        return
    PRIMARY=json.loads((S1/'plan.json').read_text())
    if a.action=='prepare':
        if not (ROOT/'observed-off-spells.csv').exists():write_inventory(ROOT)
        prepare()
    else:Study().run()


if __name__=='__main__':
    main()
